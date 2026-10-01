"""Shared core for all trace importers.

Intermediate EVENT schema: every importer (OTel, LangSmith, JSONL) first
converts its source format into a flat, ordered list of these event dicts,
then hands them to events_to_tracker().

Event types (each event is a plain dict):

    {"type": "start", "case_id": str}
        Optional explicit attempt boundary. events_to_tracker() auto-starts
        an attempt on the first event seen for a case, so "start" is a no-op
        marker kept for readability.

    {"type": "model", "case_id": str, "model": str,
     "provider": str (optional), "input_tokens": number (default 0),
     "output_tokens": number (default 0)}
        One LLM call. "provider" is the vendor key used by pricing
        (openai, anthropic, google, xai). If omitted, the provider is guessed
        from the model name with guess_provider().

    {"type": "tool", "case_id": str, "name": str,
     "cost": number (optional), "latency_ms": number (optional)}
        One tool call. If "cost" is omitted, pricing.tool_call_cost(name)
        is used. "latency_ms" is recorded as attempt metadata only; it does
        not change cost.

    {"type": "retry", "case_id": str, "reason": str (optional)}
        Marks the following steps in this case as retry-path (waste) tokens.

    {"type": "escalation", "case_id": str, "minutes": number,
     "reason": str (optional)}
        Human review time, costed at the Tracker's loaded per-minute rate.

    {"type": "end", "case_id": str, "success": bool,
     "business_value": number (default 0.0), "reopened": bool (default False)}
        Closes the attempt. A case with no "end" event is auto-ended with
        success=False (a trace that never finished is not a success).

Pricing fallback: model names missing from pricing.MODEL_PRICES do not crash
the import. They are costed at FALLBACK_PRICE (1.00 USD per 1M input tokens,
3.00 USD per 1M output tokens) and their "provider:model" key is collected
in tracker.unpriced_models so the caller can review and add real prices.
"""

from ..tracker import Tracker


# USD per 1M tokens (input, output) used when pricing.MODEL_PRICES has no
# entry for a model. Documented estimate, never a real vendor price.
FALLBACK_PRICE = (1.00, 3.00)


def guess_provider(model_name):
    """Guess the pricing provider key from a model name."""
    name = (model_name or "").lower()
    if "gpt" in name or "o1" in name or "o3" in name:
        return "openai"
    if "claude" in name:
        return "anthropic"
    if "gemini" in name:
        return "google"
    if "grok" in name:
        return "xai"
    return "unknown"


def _apply_model_cost(tracker, provider, model, input_tokens, output_tokens, cost):
    """Apply a model call to the open attempt with an explicit cost.

    Mirrors Tracker.log_model_call's bookkeeping for the fallback path where
    pricing has no entry for the model.
    """
    cur = tracker._cur
    cur["model"] += cost
    cur["steps"].append((input_tokens, output_tokens, cost, cur["in_retry_path"]))
    key = "%s:%s" % (provider, model)
    cur["per_model"][key] = cur["per_model"].get(key, 0.0) + cost
    cur["events"].append(("model", provider, model, cost))


def _log_model_call(tracker, provider, model, input_tokens, output_tokens):
    """log_model_call with a documented fallback for unpriced models."""
    try:
        tracker.log_model_call(provider, model, input_tokens, output_tokens)
    except KeyError:
        key = "%s:%s" % (provider, model)
        tracker.unpriced_models.add(key)
        cost = (input_tokens / 1e6 * FALLBACK_PRICE[0]
                + output_tokens / 1e6 * FALLBACK_PRICE[1])
        _apply_model_cost(tracker, provider, model,
                          input_tokens, output_tokens, cost)


def events_to_tracker(agent_name, events):
    """Build a Tracker from an ordered list of EVENT-schema dicts.

    Events are grouped by case_id (first-seen order). Each group becomes one
    or more attempts: an attempt auto-starts on the first event for a case,
    "end" closes it, and any events after an "end" start a new attempt for
    the same case. A case with no "end" event is auto-ended with
    success=False.
    """
    tracker = Tracker(agent_name)
    if not hasattr(tracker, "unpriced_models"):
        tracker.unpriced_models = set()

    groups = {}
    order = []
    for ev in events:
        cid = ev["case_id"]
        if cid not in groups:
            groups[cid] = []
            order.append(cid)
        groups[cid].append(ev)

    for cid in order:
        started = False
        for ev in groups[cid]:
            if not started:
                tracker.start_attempt(case_id=cid)
                started = True
            etype = ev["type"]
            if etype == "start":
                pass  # auto-start already handled this
            elif etype == "model":
                provider = ev.get("provider") or guess_provider(ev.get("model"))
                _log_model_call(tracker, provider, ev["model"],
                                ev.get("input_tokens", 0) or 0,
                                ev.get("output_tokens", 0) or 0)
            elif etype == "tool":
                tracker.log_tool_call(ev["name"], cost=ev.get("cost"))
                if ev.get("latency_ms") is not None:
                    cur = tracker._cur
                    cur["tool_latency_ms"] = (cur.get("tool_latency_ms", 0.0)
                                             + ev["latency_ms"])
            elif etype == "retry":
                tracker.log_retry(reason=ev.get("reason", ""))
            elif etype == "escalation":
                tracker.log_escalation(ev["minutes"], reason=ev.get("reason", ""))
            elif etype == "end":
                tracker.end_attempt(
                    success=ev.get("success", False),
                    business_value=ev.get("business_value", 0.0) or 0.0,
                    reopened=ev.get("reopened", False))
                started = False
            else:
                raise ValueError("unknown event type: %r" % (etype,))
        if started:
            tracker.end_attempt(success=False)
    return tracker


# Attempt keys kept in the exported ledger. Must match the key list in
# policy.export_ledger (same schema, dict form here instead of a file).
LEDGER_ATTEMPT_KEYS = (
    "case_id", "model", "tools", "retry_cost", "retries",
    "human_min", "human_cost", "ai_cost", "total_cost",
    "total_tokens", "waste_tokens", "context_growth",
    "success", "reopened", "business_value", "per_model",
    "tool_latency_ms",
)


def ledger_from_tracker(tracker, agent_name=None):
    """Return the sanitized ledger dict for a Tracker (no file written).

    Same schema as policy.export_ledger: {"agent": name, "attempts": [...]},
    metadata only, never prompts or customer data.
    """
    return {
        "agent": agent_name or tracker.agent_name,
        "unpriced_models": sorted(tracker.unpriced_models),
        "attempts": [
            {k: a[k] for k in LEDGER_ATTEMPT_KEYS}
            for a in tracker.attempts
        ],
    }


def tracker_from_ledger(ledger):
    """Rehydrate a Tracker from a ledger dict so pnl() works on imported data."""
    tracker = Tracker(ledger["agent"])
    tracker.attempts = [dict(a) for a in ledger["attempts"]]
    tracker.unpriced_models = set(ledger.get("unpriced_models", []))
    return tracker
