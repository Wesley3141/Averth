"""Tests for the Langfuse importer and the vendor-supplied (billed) cost path.

Langfuse observations carry the vendor's own calculated costs
(calculatedTotalCost). Those dollars are recorded as billed — higher
confidence than our price-table estimates — and surfaced separately in
pnl()["data_quality"].
"""
import json

import pytest

from averth.importers import langfuse
from averth.importers.common import tracker_from_ledger
from averth.tracker import Tracker


def _write(tmp_path, obj):
    p = tmp_path / "lf.json"
    p.write_text(json.dumps(obj))
    return str(p)


def _gen(obs_id, model="gpt-5.6", usage=None, cost=None, level="DEFAULT",
         metadata=None):
    obs = {"id": obs_id, "type": "GENERATION", "model": model,
           "level": level, "metadata": metadata or {}}
    if usage is not None:
        obs["usageDetails"] = usage
    if cost is not None:
        obs["calculatedTotalCost"] = cost
    return obs


def test_billed_cost_path(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 1000, "output": 500}, cost=0.0125),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["cost_billed"] == pytest.approx(0.0125)
    assert p["data_quality"]["billed"] == pytest.approx(0.0125)
    assert p["billed_models"] == ["openai:gpt-5.6"]
    # tokens recorded but do not drive dollars
    assert p["data_quality"]["measured"] == pytest.approx(0.0)


def test_tokens_fallback_without_billed_cost(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 1000, "output": 500}),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["cost_billed"] == pytest.approx(0.0)
    assert p["data_quality"]["measured"] > 0
    assert p["billed_models"] == []


def test_missing_usage_flagged_unknown(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage=None, cost=None),  # no usage, no billed cost
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    assert ledger["missing_usage_models"] == ["openai:gpt-5.6"]
    assert ledger["unknown_usage_calls"] == 1
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["unknown_usage_calls"] == 1
    assert p["data_quality"]["unknown_calls"] == 1
    # $0.00 recorded, and the bucket shows it as unknown — never as free
    assert p["cost_total"] == pytest.approx(0.0)


def test_error_level_marks_failure(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 10, "output": 10}, level="ERROR"),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["successes"] == 0
    assert p["inferred_outcomes"] == 1


def test_retry_and_escalation_markers(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 10, "output": 10},
             metadata={"averth_retry": "timeout"}),
        {"id": "s1", "type": "SPAN",
         "metadata": {"averth_escalation_minutes": 5,
                      "averth_escalation_reason": "stuck"}},
        _gen("g2", usage={"input": 10, "output": 10}),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["retries"] == 1
    assert p["escalations"] == 1
    assert p["cost_human"] > 0


def test_bare_list_accepted(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 10, "output": 10}),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, [trace]))
    assert ledger["attempts"][0]["case_id"] == "t1"


def test_nonpositive_billed_cost_falls_back(tmp_path):
    trace = {"id": "t1", "observations": [
        _gen("g1", usage={"input": 1000, "output": 500}, cost=0.0),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, {"data": [trace]}))
    tracker = tracker_from_ledger(ledger)
    p = tracker.pnl()
    # zero/negative vendor cost is not a real billed figure: tokens-x-price
    assert p["cost_billed"] == pytest.approx(0.0)
    assert p["data_quality"]["measured"] > 0


def test_tracker_billed_api_directly():
    t = Tracker("billed-unit")
    t.start_attempt(case_id="c1")
    t.log_model_billed_cost("anthropic", "claude-sonnet-4-6", 0.02,
                            input_tokens=100, output_tokens=50)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["cost_billed"] == pytest.approx(0.02)
    assert p["billed_models"] == ["anthropic:claude-sonnet-4-6"]
    assert p["data_quality"]["billed"] == pytest.approx(0.02)


def test_input_cached_tokens_field_is_read(tmp_path):
    # Regression, 2026-10-22: the real AcruxCore msg-06 trace uses
    # input_cached_tokens, which was missing from the alias list, so
    # that trace totalled $0.001556 with cached 0 instead of $0.001972.
    trace = {"id": "t1", "observations": [
        _gen("g1", model="glm-5.3",
             usage={"input": 316, "output": 253,
                    "input_cached_tokens": 1600}),
    ]}
    ledger = langfuse.load_langfuse(_write(tmp_path, [trace]))
    attempt = ledger["attempts"][0]
    assert attempt["cached_tokens"] == 1600
    assert attempt["total_cost"] == pytest.approx(0.001972, abs=1e-6)
