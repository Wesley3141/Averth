"""Tests for the hostile-review round-2 fixes (2026-10-01).

Covers: NaN/inf rejection, OTel success parsing, --policy-cap 0, duplicate
end events, branch-retroactive waste, the retry-tool lens, export/reimport
retry-reason fidelity, and insights edge cases (materiality floor, n<20 tail,
tool dominance, budget breach).
"""
import json
import math

import pytest

from averth import Tracker, policy
from averth.importers import common, jsonl as jsonl_imp, otel
from averth.insights import findings


def make_tracker():
    return Tracker("review2")


# ---- NaN/inf rejection (ledger poisoning) ----

def test_nan_tokens_rejected():
    t = make_tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5-nano", float("nan"), 10)


def test_inf_cost_rejected():
    t = make_tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_tool_call("x", float("inf"))


def test_inf_business_value_rejected():
    t = make_tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.end_attempt(success=True, business_value=float("inf"))


def test_negative_business_value_allowed():
    t = make_tracker()
    t.start_attempt()
    a = t.end_attempt(success=True, business_value=-5.0)
    assert a["business_value"] == -5.0


def test_export_is_valid_json_after_rejection():
    # a rejected NaN must not leave the ledger in a state that exports NaN
    # (Python's json emits NaN, which is invalid JSON and poisons reimport)
    t = make_tracker()
    t.start_attempt()
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    t.end_attempt(success=True)
    blob = policy.export_ledger(t, "/tmp/review2-ledger.json")
    raw = open(blob).read()
    assert "NaN" not in raw and "Infinity" not in raw
    parsed = json.loads(raw)  # strict parse
    p = common.tracker_from_ledger(parsed).pnl()
    assert math.isfinite(p["cost_total"])


# ---- OTel success parsing (I1) ----

def _otel_spans(extra_attrs):
    base = {"traceId": "t1", "spanId": "s1", "name": "llm",
            "startTimeUnixNano": "1000", "endTimeUnixNano": "2000"}
    base.update(extra_attrs)
    return [base]


def _otel_p(attrs):
    import tempfile, os
    spans = _otel_spans(attrs)
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(spans, f)
        ledger = otel.load_otel(path)
    finally:
        os.unlink(path)
    return common.tracker_from_ledger(ledger).pnl()


def test_otel_success_string_false_is_false():
    attrs = {"attributes": {"averth.success": "false",
                            "gen_ai.request.model": "gpt-5-nano",
                            "gen_ai.usage.input_tokens": 100,
                            "gen_ai.usage.output_tokens": 10}}
    p = _otel_p(attrs)
    assert p["successes"] == 0
    assert p["attempts"] == 1


def test_otel_success_string_true_is_true():
    attrs = {"attributes": {"averth.success": "True",
                            "gen_ai.request.model": "gpt-5-nano",
                            "gen_ai.usage.input_tokens": 100,
                            "gen_ai.usage.output_tokens": 10}}
    p = _otel_p(attrs)
    assert p["successes"] == 1


# ---- --policy-cap 0 (P1) ----

def test_policy_cap_zero_stops_everything():
    t = make_tracker()
    t.start_attempt(case_id="a")
    t.log_tool_call("x", 0.01)
    t.end_attempt(success=True)
    ledger = common.ledger_from_tracker(t)
    sim = policy.simulate_policy(ledger, max_cost_per_attempt=0)
    assert sim["would_stop"] == 1


# ---- duplicate end (C6) ----

def test_duplicate_end_does_not_create_phantom_attempt():
    events = [
        {"type": "model", "case_id": "c1", "model": "gpt-5-nano",
         "input_tokens": 1000, "output_tokens": 100},
        {"type": "end", "case_id": "c1", "success": True},
        {"type": "end", "case_id": "c1", "success": True},  # duplicate
    ]
    t = common.events_to_tracker("dup", events)
    assert len(t.attempts) == 1
    assert t.pnl()["attempts"] == 1


# ---- branch-retroactive waste (M1) ----

def test_branch_retry_marks_prior_branch_steps_waste():
    t = make_tracker()
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="a")
    t.log_tool_call("search", 0.50, branch="a")
    t.log_retry("bad branch", branch="a")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="a")  # redo
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="b")
    a = t.end_attempt(success=True)
    # pre-retry branch-a model step + tool are waste; redo and branch b live
    assert a["waste_tokens"] == 1100
    assert a["retry_tool_cost"] == pytest.approx(0.50)
    assert t.pnl()["cost_retry_tools"] == pytest.approx(0.50)


def test_second_branch_retry_discards_the_redo():
    t = make_tracker()
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="a")
    t.log_retry("bad", branch="a")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="a")  # redo
    t.log_retry("still bad", branch="a")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)  # merge, terminal
    a = t.end_attempt(success=True)
    assert a["waste_tokens"] == 2200


# ---- export -> reimport retry-reason fidelity (H5) ----

def test_retry_reasons_survive_export_reimport(tmp_path):
    t = make_tracker()
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    t.log_retry("stale context")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    t.end_attempt(success=True)
    path = str(tmp_path / "ledger.json")
    policy.export_ledger(t, path)
    p2 = common.tracker_from_ledger(policy.load_ledger(path)).pnl()
    assert p2["top_retry_reasons"] == [("stale context", 1)]
    assert p2["cost_retry_path"] == pytest.approx(t.pnl()["cost_retry_path"])


# ---- JSONL hardening (C4) ----

def test_jsonl_rejects_nan_and_allows_negative_value(tmp_path):
    good = (b'{"type": "model", "case_id": "c", "model": "gpt-5-nano",'
            b' "input_tokens": 100, "output_tokens": 10}\n'
            b'{"type": "end", "case_id": "c", "success": true,'
            b' "business_value": -12.5}\n')
    p = tmp_path / "good.jsonl"
    p.write_bytes(good)
    t = common.tracker_from_ledger(jsonl_imp.load_jsonl(str(p)))
    assert t.pnl()["business_value"] == pytest.approx(-12.5)

    bad = (b'{"type": "model", "case_id": "c", "model": "gpt-5-nano",'
           b' "input_tokens": 100, "output_tokens": 10}\n'
           b'{"type": "tool", "case_id": "c", "name": "x", "cost": NaN}\n')
    q = tmp_path / "bad.jsonl"
    q.write_bytes(bad)
    with pytest.raises(ValueError):
        jsonl_imp.load_jsonl(str(q))


# ---- insights edge cases ----

def _rich_tracker():
    # model-heavy baseline so tool/human dominance don't fire spuriously
    t = Tracker("edge")
    for _ in range(25):
        t.start_attempt()
        t.log_model_call("anthropic", "claude-sonnet-4-5", 100_000, 10_000)
        t.end_attempt(success=True)
    return t


def test_materiality_floor_silences_dust():
    t = Tracker("dust")
    t.start_attempt()
    t.log_tool_call("x", 0.00002)
    t.end_attempt(success=False)  # 100% failed share, but $0.00002 total
    assert findings(t.pnl()) == []


def test_tail_finding_requires_n20():
    t = Tracker("small")
    for _ in range(10):
        t.start_attempt()
        cost = 100.0 if _ == 0 else 1.0
        t.log_tool_call("x", cost)
        t.end_attempt(success=True)
    # one $100 run of $109 total: extreme concentration, but n < 20
    p = t.pnl()
    assert p["tail"]["tail_label"] == "costliest run"
    assert "tail_concentration" not in [f["id"] for f in findings(p)]


def test_tool_dominance_fires():
    t = Tracker("tools")
    for _ in range(5):
        t.start_attempt()
        t.log_model_call("openai", "gpt-5-nano", 1000, 100)
        t.log_tool_call("big_api", 10.00)
        t.end_attempt(success=True)
    ids = [f["id"] for f in findings(t.pnl())]
    assert "tool_dominance" in ids


def test_budget_breach_fires():
    t = Tracker("budget", budget_per_success=1.00,
               on_breach=lambda a, e: None)
    for _ in range(5):
        t.start_attempt()
        t.log_tool_call("x", 5.00)
        t.end_attempt(success=True)
    p = t.pnl()
    assert p["budget_breaches"] == 5
    assert "budget_breach" in [f["id"] for f in findings(p)]


def test_reopened_counts_successful_only():
    t = make_tracker()
    t.start_attempt(case_id="ok")
    t.log_tool_call("x", 50.00)
    t.end_attempt(success=True, reopened=True)
    t.start_attempt(case_id="bad")
    t.log_tool_call("x", 50.00)
    t.end_attempt(success=False, reopened=True)  # never accepted: not counted
    p = t.pnl()
    assert p["reopened_successful"] == 1
