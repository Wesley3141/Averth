"""Importer for Langfuse trace exports.

Accepted input: Langfuse API trace JSON — either a bare list of traces or
{"data": [...]} as returned by GET /api/public/traces. Each trace carries
an "observations" list; generation observations carry the usage and cost.

Mapping (documented here):

  case identity   trace "id".
  model call      observation "type" == "GENERATION" -> model event.
                  Model name from observation "model". Tokens from
                  "usageDetails" (also accepts "usage_details"): keys
                  "input"/"output"/"total", "promptTokens"/"completionTokens",
                  or "prompt_tokens"/"completion_tokens" (first non-empty
                  wins per side).
  billed cost     "calculatedTotalCost" on a generation, when present and
                  positive, is the vendor's own metering and is recorded
                  as a vendor-supplied (billed) cost — higher confidence
                  than our price-table estimate. Tokens are still recorded
                  when reported (for token accounting) but do not drive
                  the dollars. A non-positive or non-numeric calculated
                  cost falls back to tokens-x-price.
  missing usage   a generation with no usable token usage and no billed
                  cost is still recorded, but flagged usage_known=False:
                  $0.00 recorded as unknown, never as free.
  failure         observation "level" == "ERROR" marks the case failed.
  retry marker    observation metadata {"averth_retry": reason} -> retry
                  event (same falsy-means-not-a-retry rule as the other
                  importers).
  escalation      metadata {"averth_escalation_minutes": n} -> escalation
                  event (positive finite minutes only).
  business value  trace-level or root-observation metadata
                  {"averth_business_value": v}.
  spans           "type" == "SPAN" observations are boundaries only (no
                  cost event); their metadata markers are still honored.

Provider is guessed from the model name; unknown names fall back to the
documented estimate and are collected in tracker.unpriced_models.
"""

import json
import math

from .common import (events_to_tracker, ledger_from_tracker, guess_provider,
                     _parse_bool_tristate)


def _num(value, default=0.0):
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return num if math.isfinite(num) else default


def _first(d, *keys):
    for key in keys:
        if d.get(key) not in (None, ""):
            return d[key]
    return None


def _usage_tokens(obs):
    """Return (input_tokens, output_tokens, has_usage) for a generation."""
    usage = obs.get("usageDetails") or obs.get("usage_details") or {}
    if not isinstance(usage, dict):
        return 0.0, 0.0, False
    in_raw = _first(usage, "input", "promptTokens", "prompt_tokens",
                    "input_tokens")
    out_raw = _first(usage, "output", "completionTokens", "completion_tokens",
                     "output_tokens")
    in_tok = _num(in_raw)
    out_tok = _num(out_raw)
    has_usage = in_raw is not None or out_raw is not None
    return in_tok, out_tok, has_usage


def _billed_cost(obs):
    """Vendor-supplied cost, or None to fall back to tokens-x-price."""
    raw = obs.get("calculatedTotalCost")
    if raw in (None, ""):
        return None
    try:
        cost = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cost) or cost <= 0:
        return None
    return cost


def _meta(obs):
    meta = obs.get("metadata") or {}
    return meta if isinstance(meta, dict) else {}


def _retry_marker_present(value):
    if value is None or value == "":
        return False
    tri = _parse_bool_tristate(value)
    if tri is False:
        return False
    if tri is None and not value:
        return False
    return True


def load_langfuse(path, agent_name="langfuse-import"):
    """Parse a Langfuse trace-export JSON file and return a sanitized ledger."""
    with open(path) as f:
        data = json.load(f)
    traces = data["data"] if isinstance(data, dict) and "data" in data \
        else data

    events = []
    missing_usage = set()
    for trace in traces:
        case_id = trace.get("id") or "unknown"
        observations = trace.get("observations") or []
        failed = False
        business_value = 0.0
        for obs in observations:
            otype = (obs.get("type") or "").upper()
            meta = _meta(obs)
            if (obs.get("level") or "").upper() == "ERROR":
                failed = True
            if _retry_marker_present(meta.get("averth_retry")):
                events.append({"type": "retry", "case_id": case_id,
                               "reason": str(meta.get("averth_retry"))})
            esc_raw = meta.get("averth_escalation_minutes")
            if esc_raw not in (None, ""):
                esc_minutes = _num(esc_raw)
                if esc_minutes > 0:
                    events.append({"type": "escalation", "case_id": case_id,
                                   "minutes": esc_minutes,
                                   "reason": str(meta.get(
                                       "averth_escalation_reason") or "")})
            bv = meta.get("averth_business_value")
            if bv is not None:
                business_value = _num(bv, business_value)
            if otype != "GENERATION":
                continue
            model = obs.get("model") or "unknown"
            in_tok, out_tok, has_usage = _usage_tokens(obs)
            provider = meta.get("ls_provider") or guess_provider(model)
            billed = _billed_cost(obs)
            if not has_usage and billed is None:
                missing_usage.add("%s:%s" % (provider, model))
            events.append({"type": "model", "case_id": case_id,
                           "provider": provider, "model": model,
                           "input_tokens": in_tok, "output_tokens": out_tok,
                           "billed_cost": billed,
                           "usage_known": has_usage or billed is not None})
        # trace-level business value overrides observation-level
        tbv = _meta(trace).get("averth_business_value")
        if tbv is not None:
            business_value = _num(tbv, business_value)
        events.append({"type": "end", "case_id": case_id,
                       "success": not failed, "outcome_inferred": True,
                       "business_value": business_value})

    tracker = events_to_tracker(agent_name, events)
    tracker.missing_usage.update(missing_usage)
    return ledger_from_tracker(tracker)
