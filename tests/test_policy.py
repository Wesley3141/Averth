"""Tests for averth.policy: sanitized ledger roundtrip and offline simulation."""

import json
import os

import pytest

from averth import Tracker
from averth import policy as P

SCHEMA_KEYS = {
    "case_id", "model", "tools", "retry_cost", "retries",
    "human_min", "human_cost", "ai_cost", "total_cost",
    "total_tokens", "waste_tokens", "context_growth",
    "context_tax", "retry_path_cost", "terminal_model_cost",
    "cached_tokens", "cache_savings",
    "success", "reopened", "business_value", "per_model",
}


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
    for a in ledger["attempts"]:
        assert SCHEMA_KEYS.issubset(set(a.keys())), f"missing keys: {SCHEMA_KEYS - set(a.keys())}"


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
    # are metadata only: no prompts, completions, or payloads
    for a in blob["attempts"]:
        for ev in a.get("events", []):
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
    assert sim["would_stop"] == 1
    stopped_ids = {w["case_id"] for w in sim["worst"]}
    assert stopped_ids == {"expensive"}
    assert sim["exposed_spend"] == pytest.approx(expensive)
    total = sum(a["total_cost"] for a in ledger["attempts"])
    assert sim["exposed_share"] == pytest.approx(expensive / total)
    # worst offenders sorted descending
    assert sim["worst"][0]["case_id"] == "expensive"


def test_simulate_policy_yield_floor(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)

    # 'expensive' has ~half its tokens on the retry path; cheap/failed have none
    sim = P.simulate_policy(ledger, yield_floor=0.75)
    assert sim["would_stop"] == 1
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
    assert sim["would_stop"] == 0
    assert sim["exposed_spend"] == 0.0
    assert sim["exposed_share"] == 0.0


def test_policy_text_renders():
    sim = {"policy": {"max_cost_per_attempt": 6.0, "yield_floor": 0.5},
           "attempts": 10, "would_stop": 3,
           "would_stop_failed": 2, "would_stop_success": 1,
           "saved_spend": 32.5, "collateral_spend": 10.0,
           "exposed_spend": 42.5, "exposed_share": 0.85,
           "worst": [{"case_id": "C-9", "total_cost": 20.0,
                      "success": False, "reasons": ["cost $20.00 > cap $6.00"]},
                     {"case_id": "C-2", "total_cost": 12.5,
                      "success": True, "reasons": ["yield 40% < floor 50%"]}]}
    text = P.policy_text(sim)
    assert "3 of 10 runs" in text
    assert "$32.50" in text and "$10.00" in text
    assert "C-9" in text and "C-2" in text
    # honest split: failed-stop savings vs destroyed good outcomes
    assert "2 failed" in text and "pure savings $32.50" in text
    assert "1 that went on to succeed" in text and "collateral $10.00" in text


def test_simulate_policy_splits_saved_vs_collateral(tmp_path):
    t = build_tracker()
    path = str(tmp_path / "ledger.json")
    P.export_ledger(t, path)
    ledger = P.load_ledger(path)
    # cap between cheap and expensive: stops the (successful) expensive run
    cheap = ledger["attempts"][0]["total_cost"]
    expensive = ledger["attempts"][1]["total_cost"]
    sim = P.simulate_policy(ledger, max_cost_per_attempt=(cheap + expensive) / 2)
    assert sim["would_stop"] == 1
    assert sim["would_stop_failed"] == 0
    assert sim["would_stop_success"] == 1
    assert sim["saved_spend"] == pytest.approx(0.0)
    assert sim["collateral_spend"] == pytest.approx(expensive)
    assert sim["saved_spend"] + sim["collateral_spend"] == pytest.approx(
        sim["exposed_spend"])
