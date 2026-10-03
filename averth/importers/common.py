"""Shared core for all trace importers.

Intermediate EVENT schema: every importer (OTel, LangSmith, JSONL) first
converts its source format into a flat, ordered list of these event dicts,
then hands them to events_to_tracker().

Event types (each event is a plain dict):

    {"type": "start", "case_id": str}
        Pure no-op readability marker. events_to_tracker() SKIPS "start"
        events entirely: an attempt auto-starts on the first real event
        for a case. A lone "start" with no other events creates nothing
        (it must not fabricate a phantom failed attempt).

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
        With "branch", declares that branch's work SO FAR in the attempt
        discarded: the branch's existing (past) steps are retroactively
        marked as retry-path waste. Work logged on the branch AFTER the
        retry is the redo and starts fresh — it is NOT pre-tainted (this
        matches Tracker.log_retry semantics exactly; an earlier version of
        this docstring wrongly said "past and future"). Without "branch",
        marks the following steps as retry-path (earlier steps are assumed
        to stand — see Tracker.log_retry).

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
from .. import pricing
# Single source of truth for the ledger attempt keys (extracted here from
# policy.py so the dict-form export in ledger_from_tracker and the file
# export in policy.export_ledger can never drift).
from ..policy import LEDGER_ATTEMPT_KEYS


# USD per 1M tokens (input, output) used when pricing.MODEL_PRICES has no
# entry for a model. Documented estimate, never a real vendor price.
# M1: single source of truth — was duplicated here and in pricing.py.
FALLBACK_PRICE = pricing.ESTIMATED_MODEL_PRICES


def guess_provider(model_name):
    """Guess the pricing provider key from a model name.

    M2 HEURISTIC WARNING: this is name-guessing, not identification. A
    fine-tuned, proxied, or renamed model containing "gpt" (e.g.
    "gpt-custom" via a gateway) gets OpenAI list prices applied SILENTLY —
    the dollars look exact but the vendor attribution may be wrong. Always
    pass an explicit "provider" in the event (or model registry) for
    production traces; treat guessed-provider spend as lower-confidence.
    Returns "unknown" when nothing matches, which prices the call at the
    documented fallback estimate and flags it in unpriced_models (honest)
    instead of inventing a vendor (dishonest).
    """
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


def _parse_bool_tristate(value):
    """Parse a marker attribute as True / False / None (tri-state).

    Accepts real booleans and the strings "true"/"false"/"yes"/"no"/
    "1"/"0" (case-insensitive, whitespace stripped). Anything else —
    including None, numbers, and free text — yields None: present but
    not a boolean claim. Importers use this so an explicit "not a
    retry" / "not a failure" marker can never be truthiness-flipped
    into an event (bool("false") is True), while non-boolean values
    are left for each caller's own gate logic.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0"):
            return False
    return None


def _apply_model_cost(tracker, provider, model, input_tokens, output_tokens,
                      cost, cached_tokens=0, cache_saving=0.0, branch=None):
    """Apply a model call to the open attempt with an explicit cost.

    Mirrors Tracker.log_model_call's bookkeeping for the fallback path where
    pricing has no entry for the model. Cached tokens are priced at the
    Tracker's cache_read_discount (same discount math as log_model_call)
    and the saving is recorded, so the EVENT-schema docstring holds on the
    fallback path too.
    """
    cur = tracker._cur
    cur["model"] += cost
    cur["cache_savings"] += cache_saving
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
        # H-A: the fallback path applies the same cache-discount math as
        # log_model_call (priced at tracker.cache_read_discount, saving
        # recorded) — cached tokens were previously priced at the full
        # fallback rate with saving 0.0, contradicting the EVENT schema
        # docstring. cached > input is clamped like log_model_call.
        d = tracker.cache_read_discount
        pin, pout = FALLBACK_PRICE
        cached = min(cached_tokens, input_tokens)
        cost = ((input_tokens - cached) / 1e6 * pin
                + cached / 1e6 * pin * d
                + output_tokens / 1e6 * pout)
        saving = cached / 1e6 * pin * (1.0 - d)
        _apply_model_cost(tracker, provider, model,
                          input_tokens, output_tokens, cost,
                          cached_tokens=cached, cache_saving=saving,
                          branch=branch)


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
        start_seen = False
        for ev in groups[cid]:
            etype = ev["type"]
            # H-B: "start" is a pure readability marker and never creates an
            # attempt by itself — a lone "start" creates nothing. We remember
            # it only so a later "end" for the same case still closes a real
            # (possibly zero-cost) attempt instead of being dismissed as a
            # stray end.
            if etype == "start":
                start_seen = True
                continue
            # C6: a stray "end" with no "start" and no open attempt is
            # ignored instead of fabricating a phantom zero-cost attempt.
            if etype == "end" and not started and not start_seen:
                continue
            if not started:
                tracker.start_attempt(case_id=cid)
                started = True
            if etype == "model":
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


# Attempt keys kept in the exported ledger: imported from policy.py
# (single source of truth — the same tuple policy.export_ledger uses,
# so the two export paths share one schema).
# "missing_usage_models" is a top-level ledger key, not an attempt key.

def ledger_from_tracker(tracker, agent_name=None):
    """Return the sanitized ledger dict for a Tracker (no file written).

    Same schema as policy.export_ledger: {"agent": name, "attempts": [...]},
    cost/token/timing metadata only — never prompts, completions, or tool
    payloads. Caller-provided free text (case_id, tool names,
    retry/escalation reasons) is included verbatim and may contain customer
    data; redact before sharing. The unpriced_models flag
    list is included so estimated (non-vendor) model spend stays flagged
    as an estimate after the round trip instead of looking exact.
    """
    return {
        "agent": agent_name or tracker.agent_name,
        "unpriced_models": sorted(tracker.unpriced_models),
        # Models whose calls reported no token usage: $0.00 here is missing
        # data, not free inference. getattr so foreign tracker-likes that
        # predate the field still export.
        "missing_usage_models": sorted(getattr(tracker, "missing_usage", [])),
        # C2: stamp which price table produced these dollars.
        "price_vintage": tracker.price_vintage,
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
    # Same for ledgers written before the missing_usage flag was exported.
    tracker.missing_usage = set(ledger.get("missing_usage_models", []))
    # C2: restore the price vintage the dollars were computed under, so
    # reports on old ledgers stamp the old vintage instead of today's.
    # None (legacy ledgers) means "vintage unknown" — reports say so.
    # A wrong-typed or key-missing vintage is rejected loudly here, at
    # the rehydrate boundary, instead of detonating two layers later in
    # report_text with an opaque TypeError.
    vintage = ledger.get("price_vintage")
    if vintage is not None:
        if not isinstance(vintage, dict):
            raise ValueError(
                "ledger has a malformed price_vintage: expected a dict, "
                "got %r" % (vintage,))
        missing = [k for k in ("version", "updated", "age_days", "stale",
                               "stale_after_days") if k not in vintage]
        if missing:
            raise ValueError(
                "ledger has a malformed price_vintage: missing key(s) %s"
                % ", ".join(missing))
    tracker.price_vintage = vintage
    return tracker
