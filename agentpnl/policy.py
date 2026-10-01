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
                "success", "reopened", "business_value", "per_model")}
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
    """
    attempts = ledger["attempts"]
    stopped = []
    for a in attempts:
        reasons = []
        if max_cost_per_attempt and a["total_cost"] > max_cost_per_attempt:
            reasons.append(f"cost ${a['total_cost']:.2f} > cap ${max_cost_per_attempt:.2f}")
        y = 1 - a["waste_tokens"] / a["total_tokens"] if a["total_tokens"] else 1.0
        if yield_floor is not None and y < yield_floor:
            reasons.append(f"yield {y:.0%} < floor {yield_floor:.0%}")
        if reasons:
            stopped.append({"case_id": a["case_id"], "total_cost": a["total_cost"],
                            "success": a["success"], "reasons": reasons})
    exposed = sum(s["total_cost"] for s in stopped)
    total = sum(a["total_cost"] for a in attempts)
    return {
        "policy": {"max_cost_per_attempt": max_cost_per_attempt,
                   "yield_floor": yield_floor},
        "attempts": len(attempts),
        "would_stop": len(stopped),
        "exposed_spend": exposed,
        "exposed_share": exposed / total if total else 0.0,
        "worst": sorted(stopped, key=lambda s: -s["total_cost"])[:10],
    }


def policy_text(sim):
    p = sim["policy"]
    L = [f"Policy replay: max_cost_per_attempt=${p['max_cost_per_attempt']}, "
         f"yield_floor={p['yield_floor']}"]
    L.append(f"Would have stopped {sim['would_stop']} of {sim['attempts']} runs, "
             f"exposing ${sim['exposed_spend']:,.2f} "
             f"({sim['exposed_share']:.0%} of total spend).")
    for w in sim["worst"]:
        L.append(f"  {w['case_id']}: ${w['total_cost']:.2f} "
                 f"({'success' if w['success'] else 'FAILED'}) — {'; '.join(w['reasons'])}")
    return "\n".join(L)
