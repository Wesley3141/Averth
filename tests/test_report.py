"""Tests for averth.report.write_html."""

from averth import Tracker
from averth.policy import simulate_policy
from averth.report import write_html


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


def test_write_html_with_policy(tmp_path):
    t = _build_tracker()
    from averth.policy import export_ledger, load_ledger
    ledger_path = tmp_path / "ledger.json"
    export_ledger(t, str(ledger_path))
    ledger = load_ledger(str(ledger_path))
    sim = simulate_policy(ledger, max_cost_per_attempt=0.50)
    assert sim["would_stop"] > 0
    out = tmp_path / "report-policy.html"
    write_html(str(out), t, policy_sim=sim)
    body = out.read_text(encoding="utf-8")
    assert "Policy replay" in body
    assert "would have been stopped" in body
    assert f"${sim['exposed_spend']:,.2f}" in body
