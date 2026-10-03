"""Tests for averth.policy: sanitized ledger roundtrip and offline simulation."""

import json
import os

import pytest

from averth import Tracker
from averth import policy as P
from averth.policy import LEDGER_ATTEMPT_KEYS
from averth.importers.common import tracker_from_ledger


def build_tracker():
    t = Tracker("policy-test")
    # cheap clean run
    t.start_attempt(case_id="cheap")
    t.log_model_call("openai", "gpt-5-nano", 1000, 500)
    t.log_tool_call("web_search")
    t.end_attempt(success=True)
    # expensive run (retry-heavy)
    t.start_attempt(case_id="expensive")
    t.log_model_call("anthropic", "claude-opus-4-6", 500_000, 100_000)
    t.log_retry("bad draft")
    t.log_model_call("anthropic", "claude-opus-4-6", 800_000, 200_000)
    t.log_escalation(10.0, "manual review")
    t.end_attempt(success=True, reopened=True)
    # failed cheap run
    t.start_attempt(case_id="failed")
    t.log_tool_call("x", 0.50)
    t.end_attempt(success=False)
    return t


def test_export_load_roundtrip_preserves_schema(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    assert ledger["agent"] == "policy-test"
    assert len(ledger["attempts"]) == 3
    # Exact key match against the single source of truth: a dropped key
    # (e.g. "events") must fail here, not slip through a subset check.
    for a in ledger["attempts"]:
        assert set(a.keys()) == set(LEDGER_ATTEMPT_KEYS), \
            f"key drift: {set(a.keys()) ^ set(LEDGER_ATTEMPT_KEYS)}"


def test_export_load_roundtrip_preserves_values(tmp_path):
    t = build_tracker()
    before = [dict(a) for a in t.attempts]
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    for a_before, a_after in zip(before, ledger["attempts"]):
        for k in LEDGER_ATTEMPT_KEYS:
            v0, v1 = a_before[k], a_after[k]
            if k == "events":
                # tuples become lists over JSON; compare element-wise
                assert [list(e) for e in v0] == [list(e) for e in v1], \
                    "value drift on events"
            elif isinstance(v0, float):
                assert v1 == pytest.approx(v0), f"value drift on {k}"
            else:
                assert v1 == v0, f"value drift on {k}"


def test_retry_reasons_survive_export_reimport(tmp_path):
    # The ledger's promise (H5): retry reasons are metadata that must
    # survive export -> reimport, verbatim.
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    reasons = [e[1] for a in ledger["attempts"]
               for e in a["events"] if e[0] == "retry"]
    assert "bad draft" in reasons
    # ... and through the rehydration path, not just the file
    t2 = tracker_from_ledger(ledger)
    reasons2 = [e[1] for a in t2.attempts
                for e in a["events"] if e[0] == "retry"]
    assert "bad draft" in reasons2


def test_tracker_from_ledger_pnl_matches(tmp_path):
    t = build_tracker()
    p1 = t.pnl()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    t2 = tracker_from_ledger(P.load_ledger(path))
    p2 = t2.pnl()
    for k in ("cost_total", "cost_model", "cost_tools", "cost_human",
              "attempts", "successes", "budget_breaches"):
        assert p2[k] == pytest.approx(p1[k]), f"pnl drift on {k}"


def test_older_ledger_outcome_provenance_is_unknown(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    for attempt in ledger["attempts"]:
        del attempt["outcome_inferred"]
    restored = tracker_from_ledger(ledger)
    assert restored.pnl()["inferred_outcomes"] == len(ledger["attempts"])


def test_ledger_contains_no_payload_data(tmp_path):
    """The ledger is cost metadata only: no prompts, completions, or payloads."""
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    raw = open(path).read()
    blob = json.loads(raw)
    forbidden = {"prompt", "completion", "payload", "message", "content", "input", "output"}
    for a in blob["attempts"]:
        assert forbidden.isdisjoint(set(a.keys())), f"leak: {set(a.keys()) & forbidden}"
    # events ARE exported (retry reasons must survive reimport), but they
    # are metadata only: no prompts, completions, or payloads. The key must
    # be present (a .get() default would let a dropped key pass silently).
    for a in blob["attempts"]:
        assert "events" in a
        for ev in a["events"]:
            assert ev[0] in ("model", "tool", "retry", "escalation")
            for field in ev[1:]:
                assert isinstance(field, (str, int, float))


def test_simulate_policy_cost_cap_stops_right_runs(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)

    cheap = ledger["attempts"][0]["total_cost"]
    expensive = ledger["attempts"][1]["total_cost"]
    assert expensive > cheap

    cap = (cheap + expensive) / 2
    sim = P.simulate_policy(ledger, max_cost_per_attempt=cap)
    assert sim["attempts"] == 3
    assert sim["flagged_runs"] == 1
    stopped_ids = {w["case_id"] for w in sim["worst"]}
    assert stopped_ids == {"expensive"}
    assert sim["flagged_spend"] == pytest.approx(expensive)
    total = sum(a["total_cost"] for a in ledger["attempts"])
    assert sim["flagged_share"] == pytest.approx(expensive / total)
    # worst offenders sorted descending
    assert sim["worst"][0]["case_id"] == "expensive"


def test_simulate_policy_yield_floor(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)

    # 'expensive' has ~half its tokens on the retry path; cheap/failed have none
    sim = P.simulate_policy(ledger, yield_floor=0.75)
    assert sim["flagged_runs"] == 1
    stopped_ids = {w["case_id"] for w in sim["worst"]}
    assert "expensive" in stopped_ids
    assert "cheap" not in stopped_ids
    assert "failed" not in stopped_ids
    for w in sim["worst"]:
        assert any("yield" in r for r in w["reasons"])


def test_simulate_policy_no_filters_stops_nothing(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    sim = P.simulate_policy(P.load_ledger(path))
    assert sim["flagged_runs"] == 0
    assert sim["flagged_spend"] == 0.0
    assert sim["flagged_share"] == 0.0


def test_policy_text_renders_on_real_sim_output(tmp_path):
    # policy_text must be tested on real simulate_policy output, not just a
    # hand-built dict (a hand-built dict can't catch key renames).
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    cheap = ledger["attempts"][0]["total_cost"]
    expensive = ledger["attempts"][1]["total_cost"]
    sim = P.simulate_policy(ledger,
                            max_cost_per_attempt=(cheap + expensive) / 2)
    assert sim["flagged_runs"] == 1
    text = P.policy_text(sim)
    assert "1 of 3 completed runs" in text
    assert "expensive" in text
    assert "does not estimate" in text
    assert "pure savings" not in text


def test_simulate_policy_splits_saved_vs_collateral(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    # cap between cheap and expensive: stops the (successful) expensive run
    cheap = ledger["attempts"][0]["total_cost"]
    expensive = ledger["attempts"][1]["total_cost"]
    sim = P.simulate_policy(ledger, max_cost_per_attempt=(cheap + expensive) / 2)
    assert sim["flagged_runs"] == 1
    assert sim["flagged_failed"] == 0
    assert sim["flagged_success"] == 1
    assert sim["flagged_failed_spend"] == pytest.approx(0.0)
    assert sim["flagged_success_spend"] == pytest.approx(expensive)
    assert sim["flagged_failed_spend"] + sim["flagged_success_spend"] == pytest.approx(
        sim["flagged_spend"])
