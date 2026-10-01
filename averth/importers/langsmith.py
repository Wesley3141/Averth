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
                  case: the case's events are bounded by it and its truthy
                  "error" field (or any truthy "error" on the case's runs)
                  sets success=False.
  model call      run_type "llm" -> model event. Model name from
                  serialized["kwargs"]["name"], else serialized["name"],
                  else the run name. Tokens from
                  outputs["llm_output"]["token_usage"]
                  (prompt_tokens / completion_tokens), else extra.metadata
                  keys prompt_tokens/completion_tokens (or input_tokens /
                  output_tokens). Default 0 when nothing is present.
                  Provider from extra.metadata["ls_provider"] when present,
                  else guessed from the model name.
  tool call       run_type "tool" -> tool event with the run name.
  retry marker    extra.metadata {"averth_retry": reason} -> retry event;
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
from datetime import datetime

from .common import events_to_tracker, ledger_from_tracker, guess_provider


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _metadata(run):
    extra = run.get("extra") or {}
    return extra.get("metadata") or {}


def _llm_tokens(run):
    outputs = run.get("outputs") or {}
    usage = (outputs.get("llm_output") or {}).get("token_usage") or {}
    meta = _metadata(run)
    prompt = usage.get("prompt_tokens", usage.get("input_tokens",
                       meta.get("prompt_tokens", meta.get("input_tokens", 0))))
    completion = usage.get("completion_tokens", usage.get("output_tokens",
                             meta.get("completion_tokens",
                                      meta.get("output_tokens", 0))))
    # C5: negative token counts are malformed exports, never legitimate
    # economics (they would produce negative cost).
    try:
        return max(0.0, float(prompt or 0)), max(0.0, float(completion or 0))
    except (TypeError, ValueError):
        return 0.0, 0.0


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
    for case_id, case in cases.items():
        ordered = sorted(case["runs"],
                         key=lambda r: (_parse_time(r.get("start_time"))
                                        or datetime.min))
        failed = False
        business_value = 0.0
        for run in ordered:
            if run.get("error"):
                failed = True
            meta = _metadata(run)
            rtype = run.get("run_type")

            if _brand(meta, "retry") not in (None, ""):
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
            if _brand(meta, "business_value") not in (None, ""):
                try:
                    business_value = float(_brand(meta, "business_value"))
                except (TypeError, ValueError):
                    pass

            if rtype == "llm":
                model = _llm_model(run)
                in_tok, out_tok = _llm_tokens(run)
                provider = meta.get("ls_provider") or guess_provider(model)
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
    return ledger_from_tracker(tracker)
