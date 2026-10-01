"""Phase-0 policy simulation: replay a recorded ledger offline.

Read-only means read-only. There is no live enforcement in the pilot. This
module answers one question from historical data:

    "Had policy X existed, which runs would have been stopped, and what
     would it have saved?"

The customer runs the meter inside their own environment (Tracker), exports
the sanitized ledger (metadata only — no prompts, no customer data), and we
run the simulation here. Live kill/model-routing is Phase-1, built only after
a buyer confirms who owns that authority and will pay for it.
"""

import json


def export_ledger(tracker, path):
    """Write a sanitized economic ledger: per-attempt cost metadata only.

    Never contains prompts, completions, tool payloads, or customer data —
    the Tracker only ever records cost/token/timing metadata.
    """
    ledger = {
        "agent": tracker.agent_name,
        # estimated (non-vendor) model spend stays flagged after export;
        # without this, reimported ledgers would present estimates as exact
        "unpriced_models": sorted(tracker.unpriced_models),
        "attempts": [
            {k: a[k] for k in (
                "case_id", "model", "tools", "retry_cost", "retries",
                "human_min", "human_cost", "ai_cost", "total_cost",
                "total_tokens", "waste_tokens", "context_growth",
                "context_tax", "retry_path_cost", "retry_tool_cost",
                "terminal_model_cost",
                "cached_tokens", "cache_savings",
                "success", "reopened", "business_value", "per_model",
                "tool_latency_ms",
                # events: metadata only, preserves retry reasons (H5)
                "events", "tool_steps")}
            for a in tracker.attempts
        ],
    }
    with open(path, "w") as f:
        json.dump(ledger, f, indent=2)
    return path


def load_ledger(path):
    with open(path) as f:
        return json.load(f)


def simulate_policy(ledger, max_cost_per_attempt=None, yield_floor=None):
    """Replay the ledger against hypothetical policies.

    Returns the runs that would have been stopped and the exposed spend.
    Stopped runs are split honestly: stopping a FAILED run saves pure waste;
    stopping a run that went on to SUCCEED destroys a good outcome, so its
    cost is reported as collateral, not savings. A policy with high
    collateral is a bad policy even when its "exposed spend" looks large.
    """
    attempts = ledger["attempts"]
    stopped = []
    for a in attempts:
        reasons = []
        if max_cost_per_attempt is not None and a["total_cost"] > max_cost_per_attempt:
            reasons.append("cost $%.2f > cap $%.2f"
                           % (a["total_cost"], max_cost_per_attempt))
        y = 1 - a["waste_tokens"] / a["total_tokens"] if a["total_tokens"] else 1.0
        if yield_floor is not None and y < yield_floor:
            reasons.append("yield %.0f%% < floor %.0f%%" % (y * 100, yield_floor * 100))
        if reasons:
            stopped.append({"case_id": a["case_id"], "total_cost": a["total_cost"],
                            "success": a["success"], "reasons": reasons})
    stopped_failed = [s for s in stopped if not s["success"]]
    stopped_success = [s for s in stopped if s["success"]]
    saved = sum(s["total_cost"] for s in stopped_failed)
    collateral = sum(s["total_cost"] for s in stopped_success)
    exposed = saved + collateral
    total = sum(a["total_cost"] for a in attempts)
    return {
        "policy": {"max_cost_per_attempt": max_cost_per_attempt,
                   "yield_floor": yield_floor},
        "attempts": len(attempts),
        "would_stop": len(stopped),
        "would_stop_failed": len(stopped_failed),
        "would_stop_success": len(stopped_success),
        "saved_spend": saved,
        "collateral_spend": collateral,
        "exposed_spend": exposed,
        "exposed_share": exposed / total if total else 0.0,
        "worst": sorted(stopped, key=lambda s: -s["total_cost"])[:10],
    }


def policy_text(sim):
    p = sim["policy"]
    L = [f"Policy replay: max_cost_per_attempt=${p['max_cost_per_attempt']}, "
         f"yield_floor={p['yield_floor']}"]
    L.append(
        f"Would have stopped {sim['would_stop']} of {sim['attempts']} runs: "
        f"{sim['would_stop_failed']} failed "
        f"(pure savings ${sim['saved_spend']:,.2f}) and "
        f"{sim['would_stop_success']} that went on to succeed "
        f"(collateral ${sim['collateral_spend']:,.2f} — good outcomes this "
        f"policy would have destroyed).")
    for w in sim["worst"]:
        L.append(f"  {w['case_id']}: ${w['total_cost']:.2f} "
                 f"({'success' if w['success'] else 'FAILED'}) — "
                 f"{'; '.join(w['reasons'])}")
    return "\n".join(L)
