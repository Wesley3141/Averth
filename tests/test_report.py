"""Tests for averth.report.write_html."""

from averth import Tracker
from averth.policy import simulate_policy
from averth.report import report_text, write_html


def _build_tracker():
    t = Tracker("support-bot-v2")
    # attempt 1: cheap success
    t.start_attempt(case_id="C-001")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 3200, 850)
    t.log_tool_call("crm_lookup")
    t.end_attempt(success=True, business_value=11.20)
    # attempt 2: retry-heavy success
    t.start_attempt(case_id="C-002")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 8000, 1200)
    t.log_retry("validation failed", extra_model_cost=0.012)
    t.log_model_call("anthropic", "claude-sonnet-4-5", 9500, 1500)
    t.log_tool_call("erp_lookup")
    t.end_attempt(success=True, business_value=9.80)
    # attempt 3: failed attempt
    t.start_attempt(case_id="C-003")
    t.log_model_call("openai", "gpt-5.6-mini", 20000, 3000)
    t.log_retry("timeout")
    t.log_retry("timeout")
    t.log_model_call("openai", "gpt-5.6-mini", 24000, 3500)
    t.end_attempt(success=False)
    # attempt 4: escalation (human review)
    t.start_attempt(case_id="C-004")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 15000, 4000)
    t.log_escalation(6.0, "low confidence on refund amount")
    t.end_attempt(success=True, business_value=14.00)
    return t


def test_write_html_basic(tmp_path):
    t = _build_tracker()
    out = tmp_path / "report.html"
    path = write_html(str(out), t)
    assert path == str(out)
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "support-bot-v2" in body
    assert "Fully loaded" in body
    per_success = t.pnl()["per_success"]["fully_loaded"]
    assert f"${per_success:,.2f}" in body or f"${per_success:.2f}" in body
    assert "<svg" in body
    assert "Generated locally by averth. No data leaves your environment." in body
    assert "Reconcile against the customer&#x27;s invoice" in body


def test_zero_model_trace_is_not_a_cost_report(tmp_path):
    # Google ADK lane: tool-only input (21 tool uses, 0 model events,
    # 0 tokens) produced a $0.04 receipt with 100% failed-run share,
    # 100% yield, and 1.0x context growth, all vacuous. Now the
    # report must banner itself and suppress those percentages.
    t = Tracker("tool-only")
    t.start_attempt(case_id="C-001")
    t.log_tool_call("web_search")
    t.end_attempt(success=False)
    text = report_text(t.pnl())
    assert "NOT A COST REPORT" in text
    assert "Yield ratio: n/a" in text
    assert "Context compounding: n/a" in text
    assert "Failed runs:   n/a" in text
    assert "100% of spend, zero outcomes" not in text
    out = tmp_path / "tool-only.html"
    write_html(str(out), t)
    body = out.read_text(encoding="utf-8")
    assert "NOT A COST REPORT" in body


def test_write_html_with_policy(tmp_path):
    t = _build_tracker()
    from averth.policy import export_ledger, load_ledger
    ledger_path = tmp_path / "ledger.json"
    export_ledger(t, str(ledger_path))
    ledger = load_ledger(str(ledger_path))
    sim = simulate_policy(ledger, max_cost_per_attempt=0.50)
    assert sim["flagged_runs"] > 0
    out = tmp_path / "report-policy.html"
    write_html(str(out), t, policy_sim=sim)
    body = out.read_text(encoding="utf-8")
    assert "Historical policy screen" in body
    assert "does not estimate savings" in body
    assert f"${sim['flagged_failed_spend']:,.2f}" in body
    assert "pure savings" not in body


def test_unknown_only_yield_is_na_not_zero(tmp_path):
    from averth.importers import claude
    import json, tempfile, os
    rec = {"type": "assistant", "sessionId": "sess-u",
           "message": {"id": "msg_u", "model": "claude-haiku-4-5-20251001",
                      "usage": {"input_tokens": 100, "output_tokens": 50}}}
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(rec) + "\n")
        path = f.name
    try:
        ledger = claude.load_claude(path)
        from averth.importers.common import tracker_from_ledger
        t = tracker_from_ledger(ledger)
        text = report_text(t.pnl())
        assert "Yield ratio: n/a (no known outcome" in text
        assert "Failed runs:   $0.00" in text
    finally:
        os.unlink(path)
