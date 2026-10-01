"""Simulated support agent, one month, instrumented with agentpnl.

Exercises all five cost layers:
  1. context compounding — input tokens grow across steps in an attempt
  2. external tool spend — enrichment/search/sandbox calls outside the LLM bill
  3. yield vs waste      — retries mark dead-end token paths
  4. heavy tail          — 2% of attempts go runaway and burn 60%+ of budget
  5. multi-model + labor — haiku triage, sonnet planning, opus fallback, humans
"""

import random
import sys
import json
sys.path.insert(0, ".")

from agentpnl import Tracker
from agentpnl.report import report_text

random.seed(42)
breaches = []
t = Tracker("support-resolution", budget_per_success=6.00,
            on_breach=lambda a, e: breaches.append(a["case_id"]))

CASES = 2000
HUMAN_VALUE_PER_CASE = 11.20  # what the human team costs per resolved ticket


def model_step(ctx, provider, model, base_in, base_out):
    # context compounds: each step re-sends accumulated history,
    # capped by a realistic 200K context window
    ctx["in"] = min(int(ctx["in"] * random.uniform(1.25, 1.7)), 190000)
    t.log_model_call(provider, model, ctx["in"],
                     random.randint(int(base_out * 0.7), int(base_out * 1.3)))


for i in range(CASES):
    t.start_attempt(case_id=f"T-{i:05d}")
    r = random.random()
    # layer 5: cheap triage model first
    ctx = {"in": 900}
    model_step(ctx, "anthropic", "claude-haiku-4-5", 900, 120)
    t.log_tool_call("vector_retrieval")

    if r < 0.02:
        # layer 4: runaway tail — recursive loop, max steps, fails
        for _ in range(random.randint(18, 26)):
            model_step(ctx, "anthropic", "claude-sonnet-4-5", 0, 300)
            t.log_tool_call("web_search")
        t.log_retry("hit max steps, abandoning", extra_model_cost=0.05)
        t.end_attempt(success=False)
        continue

    # layer 5: planning model for the real work
    model_step(ctx, "anthropic", "claude-sonnet-4-5", 0, 500)
    t.log_tool_call("crm_lookup")
    if random.random() < 0.25:
        # layer 2: enrichment API outside the LLM bill
        t.log_tool_call("enrichment_api", cost=0.30)

    if r < 0.32:
        # layer 3: dead-end retry — validation failed, second path
        t.log_retry("answer failed confidence check", extra_model_cost=0.014)
        model_step(ctx, "anthropic", "claude-sonnet-4-5", 0, 450)
        model_step(ctx, "anthropic", "claude-sonnet-4-5", 0, 380)

    if r < 0.10:
        # layer 5: escalation + expensive fallback on the hard ones
        t.log_escalation(random.uniform(2, 8), "low confidence")
        if random.random() < 0.4:
            model_step(ctx, "anthropic", "claude-opus-4-6", 0, 900)
        t.end_attempt(success=True, business_value=HUMAN_VALUE_PER_CASE,
                      reopened=random.random() < 0.06)
    elif r < 0.80:
        t.end_attempt(success=True, business_value=HUMAN_VALUE_PER_CASE,
                      reopened=random.random() < 0.04)
    else:
        t.end_attempt(success=False)

p = t.pnl()
dashboard_per_success = p["cost_model"] / p["successes"] if p["successes"] else 0.0
print(report_text(p, token_dashboard_per_success=dashboard_per_success))
print()
print(f"Budget breaches captured by on_breach hook: {len(breaches)}")
print()
print("=" * 60)
print("PHASE-0 PILOT FLOW: customer runs the meter locally, exports the")
print("sanitized ledger (metadata only, no prompts/customer data), we replay")
print("policies offline. No live enforcement.")
print("=" * 60)
from agentpnl import policy as P

P.export_ledger(t, "/tmp/agentpnl-ledger.json")
ledger = P.load_ledger("/tmp/agentpnl-ledger.json")
print(f"Ledger exported: {len(ledger['attempts'])} attempts, "
      f"{len(json.dumps(ledger)):,} bytes, no prompts or customer data.")
print()
sim = P.simulate_policy(ledger, max_cost_per_attempt=6.00, yield_floor=0.50)
print(P.policy_text(sim))
