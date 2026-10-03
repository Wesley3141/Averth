"""Phase-0 policy screening: inspect a recorded ledger offline.

Read-only means read-only. There is no live enforcement in the pilot. This
module answers one question from historical data:

    "Which completed runs crossed the proposed thresholds, and how much
     historical spend is associated with those runs?"

The customer runs the meter inside their own environment (Tracker), exports
the sanitized ledger (cost/token/timing metadata only — no prompts,
completions, or tool payloads; but caller-provided free text such as
case_id, tool names, and retry reasons is exported verbatim, so redact
anything sensitive before sharing), and we
run the screen here. Live kill/model-routing is Phase-1, built only after
a buyer confirms who owns that authority and will pay for it.
"""

import json


# Attempt keys kept in the exported ledger. Single source of truth: both
# export_ledger and importers/common.ledger_from_tracker derive from this,
# so a future edit cannot silently drop keys from one path (silent data
# loss on round trip).
LEDGER_ATTEMPT_KEYS = (
    "case_id", "model", "tools", "retry_cost", "retries",
    "human_min", "human_cost", "ai_cost", "total_cost",
    "total_tokens", "waste_tokens", "context_growth",
    "context_tax", "retry_path_cost", "retry_tool_cost",
    "terminal_model_cost",
    "cached_tokens", "cache_savings",
    "success", "outcome_inferred", "reopened", "business_value", "per_model",
    "tool_latency_ms",
    # events: metadata only, preserves retry reasons (H5)
    "events", "tool_steps",
)


def export_ledger(tracker, path):
    """Write a sanitized economic ledger: per-attempt cost metadata only.

    Never contains prompts, completions, or tool payloads — the Tracker
    only ever records cost/token/timing metadata for those. BUT it does
    contain caller-provided free text verbatim: case_id, tool names, and
    retry/escalation reasons. That free text CAN contain customer data
    (a reason string is an arbitrary caller string), so scrub or redact
    sensitive values before the ledger leaves your environment; the export
    makes no sanitization guarantee on free-text fields. NaN is refused
    loudly (allow_nan=False): a NaN literal is invalid JSON for every
    non-Python consumer, and silently emitting one would poison the file.
    """
    ledger = {
        "agent": tracker.agent_name,
        # estimated (non-vendor) model spend stays flagged after export;
        # without this, reimported ledgers would present estimates as exact
        "unpriced_models": sorted(tracker.unpriced_models),
        # model keys whose calls reported no token usage ($0.00 is missing
        # data, not free inference); restored by tracker_from_ledger so the
        # flag survives the round trip like unpriced_models.
        "missing_usage_models": sorted(tracker.missing_usage),
        # C2: stamp which price table produced these dollars, so a ledger
        # read months later cannot be mistaken for current-price dollars.
        "price_vintage": tracker.price_vintage,
        "attempts": [
            {k: a.get(k, True) if k == "outcome_inferred" else a[k]
             for k in LEDGER_ATTEMPT_KEYS}
            for a in tracker.attempts
        ],
    }
    with open(path, "w") as f:
        json.dump(ledger, f, indent=2, allow_nan=False)
    return path


def load_ledger(path):
    with open(path) as f:
        return json.load(f)


def simulate_policy(ledger, max_cost_per_attempt=None, yield_floor=None):
    """Screen completed runs against proposed thresholds.

    This is retrospective classification, not a live-policy replay. The
    ledger has final outcomes and aggregate costs, but no decision-time
    snapshots. In particular, a final yield cannot be known mid-run and a
    cost cap cannot recover spend incurred before it fires. The returned
    dollars are historical spend on flagged runs, never projected savings.

    Boundary semantics: the stop condition is strict `>` — a run costing
    exactly max_cost_per_attempt is NOT stopped ("exceeded the cap" means
    strictly over). Same for the yield floor: exactly at the floor passes.
    """
    attempts = ledger["attempts"]
    flagged = []
    for a in attempts:
        reasons = []
        if max_cost_per_attempt is not None and a["total_cost"] > max_cost_per_attempt:
            reasons.append("cost $%.2f > cap $%.2f"
                           % (a["total_cost"], max_cost_per_attempt))
        y = 1 - a["waste_tokens"] / a["total_tokens"] if a["total_tokens"] else 1.0
        if yield_floor is not None and y < yield_floor:
            reasons.append("yield %.0f%% < floor %.0f%%" % (y * 100, yield_floor * 100))
        if reasons:
            flagged.append({"case_id": a["case_id"], "total_cost": a["total_cost"],
                            "success": a["success"], "reasons": reasons})
    flagged_failed = [s for s in flagged if not s["success"]]
    flagged_success = [s for s in flagged if s["success"]]
    failed_spend = sum(s["total_cost"] for s in flagged_failed)
    success_spend = sum(s["total_cost"] for s in flagged_success)
    flagged_spend = failed_spend + success_spend
    total = sum(a["total_cost"] for a in attempts)
    return {
        "policy": {"max_cost_per_attempt": max_cost_per_attempt,
                   "yield_floor": yield_floor},
        "attempts": len(attempts),
        "flagged_runs": len(flagged),
        "flagged_failed": len(flagged_failed),
        "flagged_success": len(flagged_success),
        "flagged_failed_spend": failed_spend,
        "flagged_success_spend": success_spend,
        "flagged_spend": flagged_spend,
        "flagged_share": flagged_spend / total if total else 0.0,
        "worst": sorted(flagged, key=lambda s: -s["total_cost"])[:10],
    }


def policy_text(sim):
    p = sim["policy"]
    L = [f"Historical policy screen: max_cost_per_attempt=${p['max_cost_per_attempt']}, "
         f"yield_floor={p['yield_floor']}"]
    L.append(
        f"Flagged {sim['flagged_runs']} of {sim['attempts']} completed runs: "
        f"{sim['flagged_failed']} failed "
        f"(${sim['flagged_failed_spend']:,.2f} historical spend) and "
        f"{sim['flagged_success']} successful "
        f"(${sim['flagged_success_spend']:,.2f} historical spend).")
    L.append("This screen uses final outcomes and costs. It does not estimate "
             "when a live policy could act, savings, or lost outcomes.")
    for w in sim["worst"]:
        L.append(f"  {w['case_id']}: ${w['total_cost']:.2f} "
                 f"({'success' if w['success'] else 'FAILED'}) — "
                 f"{'; '.join(w['reasons'])}")
    return "\n".join(L)
