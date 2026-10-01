"""Tests for the Tracker: five-layer cost math, aggregation, and budget hooks."""

import math

import pytest

from agentpnl import Tracker, BudgetBreach
from agentpnl import pricing


def make_tracker(**kw):
    kw.setdefault("budget_per_success", None)
    return Tracker("test-agent", **kw)


def test_cost_aggregation_layers():
    """model + tools + retry + human labor aggregate into ai_cost/total_cost."""
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1_000_000, 1_000_000)  # 3 + 15 = 18.0
    t.log_tool_call("web_search")          # 0.005
    t.log_tool_call("custom_api", 0.020)   # explicit override
    t.log_retry("confidence check failed", extra_model_cost=0.010)
    t.log_escalation(2.0, "low confidence")  # 2 * 1.17 = 2.34
    a = t.end_attempt(success=True, business_value=11.20)

    assert a["model"] == pytest.approx(18.0)
    assert a["tools"] == pytest.approx(0.025)
    assert a["retries"] == 1
    assert a["retry_cost"] == pytest.approx(0.010)
    assert a["human_min"] == pytest.approx(2.0)
    assert a["human_cost"] == pytest.approx(2.34)
    assert a["ai_cost"] == pytest.approx(18.0 + 0.025 + 0.010)
    assert a["total_cost"] == pytest.approx(18.0 + 0.025 + 0.010 + 2.34)
    assert a["business_value"] == pytest.approx(11.20)
    assert a["success"] is True


def test_per_success_fully_loaded():
    t = make_tracker()
    for i in range(3):
        t.start_attempt(case_id=f"C-{i}")
        t.log_tool_call("x", 1.00)   # $1 each
        t.end_attempt(success=(i < 2))  # 2 successes, 1 failure
    p = t.pnl()
    assert p["attempts"] == 3
    assert p["successes"] == 2
    assert p["success_rate"] == pytest.approx(2 / 3)
    # $3 total / 2 successes
    assert p["per_success"]["fully_loaded"] == pytest.approx(1.50)
    assert p["per_success"]["tools"] == pytest.approx(1.50)
    assert p["per_success"]["model"] == pytest.approx(0.0)


def test_per_success_zero_successes():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=False)
    p = t.pnl()
    assert p["successes"] == 0
    assert p["per_success"]["fully_loaded"] == 0.0


def test_yield_ratio_marks_retry_path():
    """Tokens after log_retry are waste-path; yield = terminal/total."""
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 500)   # 1500 terminal tokens
    t.log_retry("dead end")
    t.log_model_call("openai", "gpt-5-nano", 2000, 1000)  # 3000 waste tokens
    a = t.end_attempt(success=True)
    assert a["total_tokens"] == 4500
    assert a["waste_tokens"] == 3000
    p = t.pnl()
    assert p["yield_ratio"] == pytest.approx(1 - 3000 / 4500)


def test_yield_ratio_no_waste():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 500)
    t.end_attempt(success=True)
    assert t.pnl()["yield_ratio"] == pytest.approx(1.0)


def test_tail_p50_p95_top5pct():
    """20 attempts costing $1..$20: interpolated p50=10.5, p95=19.05,
    top5% (=$20) share=20/210."""
    t = make_tracker()
    for i in range(1, 21):
        t.start_attempt(case_id=f"C-{i}")
        t.log_tool_call("x", float(i))
        t.end_attempt(success=True)
    p = t.pnl()["tail"]
    assert p["p50"] == pytest.approx(10.5)
    assert p["p95"] == pytest.approx(19.05)
    assert p["max"] == pytest.approx(20.0)
    assert p["top5pct_share"] == pytest.approx(20.0 / 210.0)


def test_tail_percentile_interpolation():
    """Linear interpolation, not nearest-rank: 4 values 1..4 -> p50=2.5."""
    t = make_tracker()
    for i in range(1, 5):
        t.start_attempt(case_id=f"C-{i}")
        t.log_tool_call("x", float(i))
        t.end_attempt(success=True)
    p = t.pnl()["tail"]
    assert p["p50"] == pytest.approx(2.5)
    assert p["p95"] == pytest.approx(3.85)  # rank 0.95*3=2.85 -> 3*0.15+4*0.85


def test_reopened_and_escalation_flags():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.end_attempt(success=True)
    t.start_attempt(case_id="C-2")
    t.log_escalation(5.0, "needed a human")
    t.end_attempt(success=True, reopened=True)
    p = t.pnl()
    assert p["reopened"] == 1
    assert p["escalations"] == 1


def test_budget_breach_hook_fires():
    fired = []

    def on_breach(attempt, breach):
        fired.append((attempt, breach))

    t = make_tracker(budget_per_success=1.00, on_breach=on_breach)
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=True)
    assert len(fired) == 1
    attempt, breach = fired[0]
    assert isinstance(breach, BudgetBreach)
    assert attempt["case_id"] == "C-1"
    # still recorded in pnl breach count
    assert t.pnl()["budget_breaches"] == 1


def test_budget_breach_raises_without_callback():
    t = make_tracker(budget_per_success=1.00)
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 5.00)
    with pytest.raises(BudgetBreach):
        t.end_attempt(success=True)


def test_budget_no_breach_under_cap():
    fired = []
    t = make_tracker(budget_per_success=100.00, on_breach=lambda a, b: fired.append(b))
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=True)
    assert fired == []
    assert t.pnl()["budget_breaches"] == 0


def test_context_growth():
    """Context compounding: input-token growth first -> last step."""
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    t.log_model_call("openai", "gpt-5-nano", 4000, 100)
    a = t.end_attempt(success=True)
    assert a["context_growth"] == pytest.approx(4.0)
    assert t.pnl()["avg_context_growth"] == pytest.approx(4.0)


def test_context_growth_single_step():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    a = t.end_attempt(success=True)
    assert a["context_growth"] == pytest.approx(1.0)


def test_per_model_attribution():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0)      # 0.05
    t.log_model_call("anthropic", "claude-haiku-4-5", 1_000_000, 0)  # 0.80
    t.end_attempt(success=True)
    pm = t.pnl()["per_model"]
    assert pm["openai:gpt-5-nano"] == pytest.approx(0.05)
    assert pm["anthropic:claude-haiku-4-5"] == pytest.approx(0.80)


def test_unknown_model_raises():
    t = make_tracker()
    t.start_attempt(case_id="C-1")
    with pytest.raises(KeyError):
        t.log_model_call("openai", "no-such-model", 100, 100)


def test_lifecycle_errors():
    t = make_tracker()
    with pytest.raises(RuntimeError):
        t.log_tool_call("x", 1.0)          # no attempt started
    t.start_attempt(case_id="C-1")
    with pytest.raises(RuntimeError):
        t.start_attempt(case_id="C-2")      # previous attempt not ended
    t.end_attempt(success=True)


def test_custom_human_cost_per_min():
    t = make_tracker(human_cost_per_min=2.00)
    t.start_attempt(case_id="C-1")
    t.log_escalation(3.0)
    a = t.end_attempt(success=True)
    assert a["human_cost"] == pytest.approx(6.00)
