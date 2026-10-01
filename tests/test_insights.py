"""Tests for averth.insights: every rule fires only above its
materiality threshold, findings rank by dollars, and the text renderer
stays honest."""

from averth import Tracker
from averth.insights import findings, top_insight, findings_text


def _pnl_with(**kw):
    """Build a pnl dict from a driven tracker, then override keys."""
    t = Tracker("insights-test")
    t.start_attempt(case_id="C-1")
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    p = t.pnl()
    p.update(kw)
    return p


def _ids(p):
    return [f["id"] for f in findings(p)]


def test_no_findings_on_clean_spend():
    t = Tracker("clean")
    for _ in range(20):
        t.start_attempt()
        # model-dominant, no waste, no retries, no escalation: clean
        t.log_model_call("anthropic", "claude-sonnet-4-5", 100_000, 10_000)
        t.log_tool_call("x", 0.10)
        t.end_attempt(success=True)
    p = t.pnl()
    assert findings(p) == []
    assert top_insight(p) is None
    assert "No material findings" in findings_text(p)


def test_failed_spend_threshold():
    t = Tracker("t")
    t.start_attempt(case_id="ok")
    t.log_tool_call("x", 8.00)
    t.end_attempt(success=True)
    t.start_attempt(case_id="bad")
    t.log_tool_call("x", 2.00)
    t.end_attempt(success=False)  # 20% failed share
    ids = _ids(t.pnl())
    assert "failed_spend" in ids

    # below threshold: no finding
    t2 = Tracker("t2")
    t2.start_attempt()
    t2.log_tool_call("x", 9.00)
    t2.end_attempt(success=True)
    t2.start_attempt()
    t2.log_tool_call("x", 1.00)
    t2.end_attempt(success=False)  # 10% < 15%
    assert "failed_spend" not in _ids(t2.pnl())


def test_tail_concentration_fires():
    t = Tracker("t")
    for _ in range(95):
        t.start_attempt()
        t.log_tool_call("x", 0.10)
        t.end_attempt(success=True)
    for _ in range(5):
        t.start_attempt()
        t.log_tool_call("x", 20.00)  # top 5% = $100 of $109.50 = 91%
        t.end_attempt(success=True)
    p = t.pnl()
    assert "tail_concentration" in _ids(p)
    f = next(f for f in findings(p) if f["id"] == "tail_concentration")
    assert f["dollars"] == p["tail"]["top5pct_share"] * p["cost_total"]
    assert "p95" in f["action"]


def test_retry_waste_names_top_reason():
    t = Tracker("t")
    t.start_attempt()
    t.log_model_call("openai", "gpt-5-nano", 10_000_000, 0)
    t.log_retry("stale context")
    t.log_model_call("openai", "gpt-5-nano", 100_000_000, 0)  # retry dominates
    t.end_attempt(success=True)
    ids = _ids(t.pnl())
    assert "retry_waste" in ids
    f = next(f for f in findings(t.pnl()) if f["id"] == "retry_waste")
    assert "stale context" in f["detail"]
    assert "stale context" in f["action"]


def test_human_dominance_fires():
    t = Tracker("t")
    t.start_attempt()
    t.log_tool_call("x", 0.10)
    t.log_escalation(60.0, "hard case")  # $70.20 human vs $0.10 tools
    t.end_attempt(success=True)
    ids = _ids(t.pnl())
    assert "human_dominance" in ids


def test_context_tax_fires():
    t = Tracker("t")
    for _ in range(5):
        t.start_attempt()
        t.log_model_call("anthropic", "claude-sonnet-4-5", 1_000, 10)
        t.log_model_call("anthropic", "claude-sonnet-4-5", 100_000, 10)
        t.end_attempt(success=True)
    ids = _ids(t.pnl())
    assert "context_tax" in ids


def test_unpriced_spend_is_info_not_alarm():
    t = Tracker("t")
    t.start_attempt()
    t.log_model_cost_estimate("mystery", "m", 5.00, 1000, 100)
    t.end_attempt(success=True)
    fs = findings(t.pnl())
    f = next(f for f in fs if f["id"] == "unpriced_spend")
    assert f["severity"] == "info"
    assert "mystery:m" in f["detail"]


def test_cache_savings_credited():
    t = Tracker("t")
    t.start_attempt()
    t.log_model_call("openai", "gpt-5-nano", 1_000_000_000, 0,
                     cached_input_tokens=1_000_000_000)
    t.end_attempt(success=True)
    fs = findings(t.pnl())
    f = next(f for f in fs if f["id"] == "cache_savings")
    assert f["severity"] == "info"
    assert f["dollars"] > 0


def test_findings_rank_by_dollars():
    t = Tracker("t")
    # failed-spend and tool-dominance both fire; tool dollars ($208) must
    # outrank failed dollars ($200) — ranking is strictly by dollars
    for _ in range(80):
        t.start_attempt()
        t.log_tool_call("x", 0.10)
        t.end_attempt(success=True)
    for _ in range(20):  # 20% fail at $10 each = $200 failed of $208
        t.start_attempt()
        t.log_tool_call("x", 10.00)
        t.end_attempt(success=False)
    fs = findings(t.pnl())
    dollars = [f["dollars"] for f in fs]
    assert dollars == sorted(dollars, reverse=True)
    assert top_insight(t.pnl())["id"] == "tool_dominance"


def test_findings_text_renders_actions():
    t = Tracker("t")
    t.start_attempt()
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=False)
    text = findings_text(t.pnl(), limit=1)
    assert "1. [HIGH]" in text
    assert "->" in text  # every finding carries its action
