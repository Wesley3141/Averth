"""Hardening tests: the new five-layer semantics introduced in the
hardening pass — cache pricing, branch-scoped retry waste, failed-as-waste
yield, retry-path dollar accounting, context tax, interpolated percentiles,
and legacy-ledger compatibility."""

import pytest

from averth import Tracker
from averth.importers import common


def make_tracker(**kw):
    return Tracker("hardening-test", **kw)


# ---- prompt-cache pricing (layer 5) ----

def test_cached_input_priced_at_discount():
    # gpt-5-nano: $0.05/1M in, $0.40/1M out. 1M in, 100k cached, 1M out.
    # cost = 900k*0.05 + 100k*0.05*0.10 + 1M*0.40 = 0.045 + 0.0005 + 0.40
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 1_000_000,
                     cached_input_tokens=100_000)
    a = t.end_attempt(success=True)
    assert a["total_cost"] == pytest.approx(0.4455)
    assert a["cache_savings"] == pytest.approx(0.0045)  # 100k*0.05*0.9
    assert a["cached_tokens"] == 100_000
    p = t.pnl()
    assert p["cache_savings"] == pytest.approx(0.0045)
    assert p["cached_tokens"] == 100_000


def test_cached_tokens_clamped_to_input():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1_000, 100,
                     cached_input_tokens=9_999_999)
    a = t.end_attempt(success=True)
    assert a["cached_tokens"] == 1_000  # never more than input


def test_negative_tokens_raise():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5-nano", -5, 100)
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5-nano", 100, 100,
                         cached_input_tokens=-1)
    t.end_attempt(success=True)


def test_custom_cache_discount_override():
    t = make_tracker(cache_read_discount=0.50)
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0,
                     cached_input_tokens=1_000_000)
    a = t.end_attempt(success=True)
    # all input cached at 50%: 1M * 0.05 * 0.5 = 0.025
    assert a["total_cost"] == pytest.approx(0.025)
    assert a["cache_savings"] == pytest.approx(0.025)


# ---- branch-scoped retry (layer 3 under concurrency) ----

def test_branch_scoped_retry_marks_only_that_branch():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100,
                     branch="research")                       # waste (retroactive)
    t.log_retry("branch research returned junk", branch="research")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 2000, 100,
                     branch="research")                       # redo: fresh, terminal
    t.log_model_call("anthropic", "claude-sonnet-4-5", 3000, 100,
                     branch="billing")                        # terminal
    t.log_model_call("anthropic", "claude-sonnet-4-5", 4000, 100)  # merge, terminal
    a = t.end_attempt(success=True)
    assert a["total_tokens"] == 10400
    # branch retry is retroactive for past steps; the redo starts fresh
    assert a["waste_tokens"] == 1100  # only the discarded research step
    assert t.pnl()["yield_ratio"] == pytest.approx(1 - 1100 / 10400)


def test_global_retry_still_marks_all_branches():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100, branch="a")
    t.log_retry("everything is suspect")  # no branch: attempt-global
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100, branch="a")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100, branch="b")
    a = t.end_attempt(success=True)
    assert a["waste_tokens"] == 2200


# ---- failed attempts are waste (layer 3) ----

def test_failed_attempt_tokens_are_all_waste():
    t = make_tracker()
    t.start_attempt(case_id="C-ok")
    t.log_model_call("openai", "gpt-5-nano", 1000, 500)
    t.end_attempt(success=True)
    t.start_attempt(case_id="C-bad")
    t.log_model_call("openai", "gpt-5-nano", 3000, 1500)  # no retry marker
    t.end_attempt(success=False)
    a = t.attempts[1]
    assert a["waste_tokens"] == 4500  # all of it, despite no retry marker
    assert t.pnl()["yield_ratio"] == pytest.approx(1 - 4500 / 6000)


# ---- retry-path dollar accounting (fixes the old "$0.00 retries" line) ----

def test_retry_path_cost_sums_steps_and_extra():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0)   # 0.05 terminal
    t.log_retry("bad", extra_model_cost=0.010)
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0)   # 0.05 waste
    a = t.end_attempt(success=True)
    assert a["retry_path_cost"] == pytest.approx(0.05 + 0.010)
    assert a["terminal_model_cost"] == pytest.approx(0.05)
    p = t.pnl()
    assert p["cost_retry_path"] == pytest.approx(0.06)
    assert p["per_success"]["retry_path"] == pytest.approx(0.06)
    assert p["per_success"]["model"] == pytest.approx(0.05)
    # fully loaded still adds up with no double counting
    ps = p["per_success"]
    assert ps["fully_loaded"] == pytest.approx(
        ps["model"] + ps["retry_path"] + ps["tools"] + ps["human"])


def test_extra_model_cost_contract_no_double_count():
    """extra_model_cost is for spend NOT otherwise logged as a step."""
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    # the failed call was never logged via log_model_call; its spend arrives here
    t.log_retry("llm call failed outright", extra_model_cost=0.020)
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0)  # the retry itself
    a = t.end_attempt(success=True)
    assert a["model"] == pytest.approx(0.05)   # only the logged step
    assert a["retry_cost"] == pytest.approx(0.020)
    assert a["ai_cost"] == pytest.approx(0.07)


# ---- context tax in dollars (layer 1) ----

def test_context_tax_hand_computed():
    # sonnet $3.00/1M in. inputs 1000 -> 2000 -> 4000.
    # tax = (2000-1000)*3 + (4000-1000)*3 per 1M = 0.003 + 0.009 = 0.012
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 10)
    t.log_model_call("anthropic", "claude-sonnet-4-5", 2000, 10)
    t.log_model_call("anthropic", "claude-sonnet-4-5", 4000, 10)
    a = t.end_attempt(success=True)
    assert a["context_tax"] == pytest.approx(0.012)
    p = t.pnl()
    assert p["context_tax"] == pytest.approx(0.012)
    assert p["context_tax_per_success"] == pytest.approx(0.012)


def test_context_tax_zero_when_flat():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 10)
    t.log_model_call("openai", "gpt-5-nano", 1000, 10)
    a = t.end_attempt(success=True)
    assert a["context_tax"] == pytest.approx(0.0)


# ---- waste shares, retry reasons, costliest ----

def test_failed_and_reopened_spend_shares():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 4.00)
    t.end_attempt(success=False)                    # $4 failed
    t.start_attempt(case_id="C-2")
    t.log_tool_call("x", 4.00)
    t.end_attempt(success=True, reopened=True)      # $4 reopened
    t.start_attempt(case_id="C-3")
    t.log_tool_call("x", 2.00)
    t.end_attempt(success=True)                     # $2 clean
    p = t.pnl()
    assert p["cost_failed"] == pytest.approx(4.00)
    assert p["failed_spend_share"] == pytest.approx(0.40)
    assert p["cost_reopened"] == pytest.approx(4.00)
    assert p["reopened_spend_share"] == pytest.approx(0.40)


def test_top_retry_reasons_ranked():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_retry("timeout")
    t.log_retry("timeout")
    t.log_retry("bad schema")
    t.end_attempt(success=True)
    reasons = t.pnl()["top_retry_reasons"]
    assert reasons[0] == ("timeout", 2)
    assert reasons[1] == ("bad schema", 1)


def test_costliest_attempts_table():
    t = make_tracker()
    for i, cost in enumerate([1.0, 5.0, 3.0]):
        t.start_attempt(case_id="C-%d" % i)
        t.log_tool_call("x", cost)
        t.end_attempt(success=(i != 1))
    top = t.pnl()["costliest_attempts"]
    assert [c["case_id"] for c in top] == ["C-1", "C-2", "C-0"]
    assert top[0]["total_cost"] == pytest.approx(5.0)
    assert top[0]["success"] is False


def test_unpriced_spend_surfaced_in_pnl():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_cost_estimate("mystery", "model-x", 2.50, 1000, 100)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["unpriced_spend"] == pytest.approx(2.50)
    assert p["unpriced_models"] == ["mystery:model-x"]


def test_estimate_with_branch_and_cached_tokens():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_cost_estimate("mystery", "model-x", 1.00, 2000, 200,
                              cached_input_tokens=500, branch="b")
    t.log_retry("r", branch="b")
    t.log_model_cost_estimate("mystery", "model-x", 1.00, 2000, 200,
                              branch="b")
    a = t.end_attempt(success=True)
    assert a["cached_tokens"] == 500
    # second estimate step is branch-b retry path
    assert a["retry_path_cost"] == pytest.approx(1.00)
    assert a["terminal_model_cost"] == pytest.approx(1.00)


# ---- legacy ledger compatibility ----

def test_pnl_survives_legacy_ledger_without_new_keys():
    legacy = {"agent": "old", "attempts": [{
        "case_id": "L-1", "model": 1.0, "tools": 0.5, "retry_cost": 0.0,
        "retries": 0, "human_min": 0.0, "human_cost": 0.0, "ai_cost": 1.5,
        "total_cost": 1.5, "total_tokens": 1000, "waste_tokens": 0,
        "context_growth": 1.0, "success": True, "reopened": False,
        "business_value": 0.0, "per_model": {"openai:gpt-5-nano": 1.0},
        "tool_latency_ms": 0.0}]}
    t = common.tracker_from_ledger(legacy)
    p = t.pnl()  # must not raise
    assert p["cost_total"] == pytest.approx(1.5)
    assert p["cost_retry_path"] == pytest.approx(0.0)
    assert p["cost_model_terminal"] == pytest.approx(1.0)  # degrades to model
    assert p["context_tax"] == pytest.approx(0.0)
