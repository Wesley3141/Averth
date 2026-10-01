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
     "output_tokens": number (default 0),
     "cached_input_tokens": number (default 0),
     "branch": str (optional)}
        One LLM call. "provider" is the vendor key used by pricing
        (openai, anthropic, google, xai). If omitted, the provider is guessed
        from the model name with guess_provider(). "cached_input_tokens"
        are priced at the Tracker's cache_read_discount and the saving is
        reported. "branch" scopes retry-path marking to one parallel branch
        (see Tracker.log_retry).

    {"type": "tool", "case_id": str, "name": str,
     "cost": number (optional), "latency_ms": number (optional),
     "branch": str (optional)}
        One tool call. If "cost" is omitted, pricing.tool_call_cost(name)
        is used. "latency_ms" is recorded as attempt metadata only; it does
        not change cost. "branch" tags which parallel branch made the call so
        retry-path tool spend is attributed to the discarded path.

    {"type": "retry", "case_id": str, "reason": str (optional),
     "branch": str (optional)}
        With "branch", declares that branch's work in the attempt discarded:
        all of that branch's steps, past and future, count as retry-path
        waste. Without "branch", marks the following steps as retry-path
        (earlier steps are assumed to stand — see Tracker.log_retry).

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


def _apply_model_cost(tracker, provider, model, input_tokens, output_tokens,
                      cost, cached_tokens=0, branch=None):
    """Apply a model call to the open attempt with an explicit cost.

    Mirrors Tracker.log_model_call's bookkeeping for the fallback path where
    pricing has no entry for the model.
    """
    cur = tracker._cur
    cur["model"] += cost
    cur["steps"].append({
        "in": input_tokens, "out": output_tokens, "cost": cost,
        "retry": tracker._step_is_waste(branch), "in_price": 0.0,
        "cached": cached_tokens, "branch": branch,
    })
    key = "%s:%s" % (provider, model)
    cur["per_model"][key] = cur["per_model"].get(key, 0.0) + cost
    cur["events"].append(("model", provider, model, cost))
    cur["cached_tokens"] += cached_tokens


def _log_model_call(tracker, provider, model, input_tokens, output_tokens,
                    cached_tokens=0, branch=None):
    """log_model_call with a documented fallback for unpriced models."""
    try:
        tracker.log_model_call(provider, model, input_tokens, output_tokens,
                               cached_input_tokens=cached_tokens,
                               branch=branch)
    except KeyError:
        key = "%s:%s" % (provider, model)
        tracker.unpriced_models.add(key)
        cost = (input_tokens / 1e6 * FALLBACK_PRICE[0]
                + output_tokens / 1e6 * FALLBACK_PRICE[1])
        _apply_model_cost(tracker, provider, model,
                          input_tokens, output_tokens, cost,
                          cached_tokens=cached_tokens, branch=branch)


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
            etype = ev["type"]
            # C6: never auto-start on an "end" event. A duplicate end (or a
            # stray end with no open attempt) is ignored instead of
            # fabricating a phantom zero-cost attempt.
            if etype == "end" and not started:
                continue
            if not started:
                tracker.start_attempt(case_id=cid)
                started = True
            if etype == "start":
                pass  # auto-start already handled this
            elif etype == "model":
                provider = ev.get("provider") or guess_provider(ev.get("model"))
                _log_model_call(tracker, provider, ev["model"],
                                ev.get("input_tokens", 0) or 0,
                                ev.get("output_tokens", 0) or 0,
                                cached_tokens=ev.get("cached_input_tokens", 0) or 0,
                                branch=ev.get("branch"))
            elif etype == "tool":
                tracker.log_tool_call(ev["name"], cost=ev.get("cost"),
                                      branch=ev.get("branch"))
                if ev.get("latency_ms") is not None:
                    cur = tracker._cur
                    cur["tool_latency_ms"] = (cur.get("tool_latency_ms", 0.0)
                                             + ev["latency_ms"])
            elif etype == "retry":
                tracker.log_retry(reason=ev.get("reason", ""),
                                  branch=ev.get("branch"))
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
    "context_tax", "retry_path_cost", "retry_tool_cost",
    "terminal_model_cost",
    "cached_tokens", "cache_savings",
    "success", "reopened", "business_value", "per_model",
    "tool_latency_ms",
    # events carry no prompts or customer data (cost/token/timing metadata
    # only) and preserve retry reasons across export -> reimport (H5)
    "events", "tool_steps",
)


def ledger_from_tracker(tracker, agent_name=None):
    """Return the sanitized ledger dict for a Tracker (no file written).

    Same schema as policy.export_ledger: {"agent": name, "attempts": [...]},
    metadata only, never prompts or customer data. The unpriced_models flag
    list is included so estimated (non-vendor) model spend stays flagged
    as an estimate after the round trip instead of looking exact.
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
    # .get for backward compatibility with ledgers written before the
    # unpriced_models flag was exported.
    tracker.unpriced_models = set(ledger.get("unpriced_models", []))
    return tracker
