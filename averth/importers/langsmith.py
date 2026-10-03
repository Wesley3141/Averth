"""Importer for LangSmith run-export JSON.

Accepted input: a JSON list of run dicts as produced by a LangSmith
dataset/run export. Each run is expected to carry some of:

    id, name, run_type ("llm" | "tool" | "chain" | ...),
    trace_id, parent_run_ids, start_time, end_time, error,
    serialized {"kwargs": {"name": ...}} or {"name": ...},
    outputs {"llm_output": {"token_usage": {"prompt_tokens": ...,
                                            "completion_tokens": ...}}},
    extra {"metadata": {...}}

Mapping (documented here):

  case identity   trace_id. Fallback when absent: parent_run_ids[0] if the
                  run has a parent, else the run's own id.
  attempt bounds  A "chain" run with no parent_run_ids is the root of one
                  case. Success semantics: a case is failed only if the
                  chronologically-LAST run (by start_time) has a truthy
                  "error". An errored run followed by a clean run is a
                  recovered retry (success=True), not a failure.
  model call      run_type "llm" -> model event. Model name from
                  serialized["kwargs"]["name"], else serialized["name"],
                  else the run name. Tokens from
                  outputs["llm_output"]["token_usage"]
                  (prompt_tokens / completion_tokens), else extra.metadata
                  keys prompt_tokens/completion_tokens (or input_tokens /
                  output_tokens). When no usable token usage is present the
                  call is still costed at $0.00, but its "provider:model"
                  key is added to tracker.missing_usage (surfaced as
                  missing_usage_models in pnl() and the ledger) so missing
                  data is never presented as a measured $0.00.
                  Provider from extra.metadata["ls_provider"] when present,
                  else guessed from the model name.
  tool call       run_type "tool" -> tool event with the run name.
  retry marker    extra.metadata {"averth_retry": reason} -> retry event;
                  an explicit falsy value (False, 0, "false", "no", "0")
                  means "not a retry" and emits no event;
                  optional "averth_retry_branch" scopes the waste marking
                  to one parallel branch.
  escalation      extra.metadata {"averth_escalation_minutes": n,
                  "averth_escalation_reason": r} -> escalation event.
  cache / branch  extra.metadata {"averth_cached_input_tokens": n} on an
                  llm run -> cached input tokens; {"averth_branch": b}
                  tags the run's branch for branch-scoped retry accounting.
  business value  extra.metadata {"averth_business_value": v} on the root
                  chain -> end event business_value.

Non-root chains emit no events themselves; they only group their children.
Unknown model names fall back to the documented estimate in
common.FALLBACK_PRICE and are collected in tracker.unpriced_models.
"""

import json
from datetime import datetime, timezone

from .common import (events_to_tracker, ledger_from_tracker, guess_provider,
                     _parse_bool_tristate)


def _parse_time(value):
    # C-LS1: every parsed time is coerced to tz-aware UTC so a mix of
    # "Z"-suffixed, offset, and naive timestamps can never produce the
    # offset-naive/offset-aware TypeError that used to kill the import.
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _metadata(run):
    extra = run.get("extra") or {}
    return extra.get("metadata") or {}


def _llm_tokens(run):
    """Return (input_tokens, output_tokens, has_usage).

    has_usage is False when the run reported no usable token usage
    (missing keys or malformed values): the call is still costed at
    $0.00, but the caller flags it in tracker.missing_usage so missing
    data is never presented as measured $0.00 (H-LS1).
    """
    outputs = run.get("outputs") or {}
    usage = (outputs.get("llm_output") or {}).get("token_usage") or {}
    meta = _metadata(run)
    prompt = usage.get("prompt_tokens", usage.get("input_tokens",
                       meta.get("prompt_tokens", meta.get("input_tokens"))))
    completion = usage.get("completion_tokens", usage.get("output_tokens",
                             meta.get("completion_tokens",
                                      meta.get("output_tokens"))))
    # C5: negative token counts are malformed exports, never legitimate
    # economics (they would produce negative cost).
    try:
        in_tok = max(0.0, float(prompt or 0))
        out_tok = max(0.0, float(completion or 0))
    except (TypeError, ValueError):
        return 0.0, 0.0, False
    has_usage = prompt is not None or completion is not None
    return in_tok, out_tok, has_usage


def _llm_model(run):
    serialized = run.get("serialized") or {}
    kwargs = serialized.get("kwargs") or {}
    return (kwargs.get("name") or serialized.get("name")
            or run.get("name") or "unknown")


def _brand(meta, name):
    """Read an averth_* metadata key, falling back to the pre-rebrand
    agentpnl_* name so runs logged before the rename still parse."""
    v = meta.get("averth_" + name)
    if v is None:
        v = meta.get("agentpnl_" + name)
    return v


def _retry_marker_present(value):
    """True when a retry marker should emit a retry event.

    Explicit falsy values (False, 0, "false", "no", "0", "") mean "not a
    retry" and are ignored (M-LS6). True / "true" / "yes" / "1" / any
    other non-empty value (a free-text reason) emits the retry event.
    """
    if value is None or value == "":
        return False
    tri = _parse_bool_tristate(value)
    if tri is False:
        return False
    if tri is None and not value:
        return False
    return True


def load_langsmith(path, agent_name="langsmith-import"):
    """Parse a LangSmith run-export JSON file and return a sanitized ledger dict."""
    with open(path) as f:
        runs = json.load(f)

    cases = {}
    for run in runs:
        parents = run.get("parent_run_ids") or []
        trace_id = run.get("trace_id") or (parents[0] if parents else None) \
            or run.get("id") or "unknown"
        case = cases.setdefault(trace_id, {"runs": [], "root": None})
        case["runs"].append(run)
        if run.get("run_type") == "chain" and not parents:
            case["root"] = run

    events = []
    missing_usage = set()
    for case_id, case in cases.items():
        # C-LS1: tz-aware fallback keeps the sort key homogeneous with
        # the tz-aware _parse_time results.
        ordered = sorted(case["runs"],
                         key=lambda r: (_parse_time(r.get("start_time"))
                                        or datetime.min.replace(tzinfo=timezone.utc)))
        # H-LS3: a case is failed only if the chronologically-LAST run
        # errored. An errored run followed by a clean run is a recovered
        # retry, not a failure (LangSmith's native retry shape is an
        # errored attempt plus a successful sibling; the old
        # any-truthy-error rule made every recovered retry a failure).
        failed = bool(ordered and ordered[-1].get("error"))
        business_value = 0.0
        for run in ordered:
            meta = _metadata(run)
            rtype = run.get("run_type")

            # M-LS6: explicit falsy retry markers mean "not a retry".
            if _retry_marker_present(_brand(meta, "retry")):
                ev = {"type": "retry", "case_id": case_id,
                      "reason": str(_brand(meta, "retry"))}
                if _brand(meta, "retry_branch") not in (None, ""):
                    ev["branch"] = str(_brand(meta, "retry_branch"))
                events.append(ev)
            if _brand(meta, "escalation_minutes") not in (None, ""):
                try:
                    minutes = float(_brand(meta, "escalation_minutes"))
                except (TypeError, ValueError):
                    minutes = 0.0
                # C5: negative or non-numeric escalation minutes are malformed
                events.append({"type": "escalation", "case_id": case_id,
                               "minutes": max(0.0, minutes),
                               "reason": str(_brand(meta, "escalation_reason") or "")})
            # H-LS2: business_value is read from the root chain run only
            # (per the module docstring), not from any run.
            if run is case["root"] \
                    and _brand(meta, "business_value") not in (None, ""):
                try:
                    business_value = float(_brand(meta, "business_value"))
                except (TypeError, ValueError):
                    pass

            if rtype == "llm":
                model = _llm_model(run)
                in_tok, out_tok, has_usage = _llm_tokens(run)
                provider = meta.get("ls_provider") or guess_provider(model)
                # H-LS1: no usable token usage -> flag the provider:model
                # key as missing data instead of presenting $0.00 as a
                # measured cost.
                if not has_usage:
                    missing_usage.add("%s:%s" % (provider, model))
                ev = {"type": "model", "case_id": case_id,
                      "provider": provider, "model": model,
                      "input_tokens": in_tok, "output_tokens": out_tok}
                try:
                    cached = float(_brand(meta, "cached_input_tokens") or 0)
                except (TypeError, ValueError):
                    cached = 0.0
                if cached > 0:
                    ev["cached_input_tokens"] = cached
                if _brand(meta, "branch") not in (None, ""):
                    ev["branch"] = str(_brand(meta, "branch"))
                events.append(ev)
            elif rtype == "tool":
                events.append({"type": "tool", "case_id": case_id,
                               "name": str(run.get("name") or "tool")})
            # non-root chains: boundaries only, no event of their own

        events.append({"type": "end", "case_id": case_id,
                       "success": not failed, "business_value": business_value})

    tracker = events_to_tracker(agent_name, events)
    tracker.missing_usage.update(missing_usage)
    return ledger_from_tracker(tracker)
