"""averth: the economic meter for enterprise agents.

Instrument one workflow to measure its recorded cost structure:

    from averth import Tracker

    t = Tracker("invoice-resolution", budget_per_success=5.00)

    t.start_attempt(case_id="INV-1042")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 3200, 850)
    t.log_tool_call("erp_lookup")
    t.log_retry("validation failed", extra_model_cost=0.012)
    t.log_escalation(4.5, "low confidence on tax code")
    t.end_attempt(success=True, business_value=11.20)

    from averth.report import report_text
    print(report_text(t.pnl(), token_dashboard_per_success=1.91))

The tracker records model spend, tool calls, retries, and human review time,
then attributes them to caller-labeled outcomes. The budget hook fires after
an attempt ends; it does not interrupt a run in progress.
"""

from .tracker import Tracker, BudgetBreach
from . import pricing

__all__ = ["Tracker", "BudgetBreach", "pricing"]
