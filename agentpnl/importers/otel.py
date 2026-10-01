"""Importer for OpenTelemetry OTLP span JSON exports.

Accepted input: a JSON list of spans, or {"spans": [...]}.

Attribute mapping (documented here because vendors emit several dialects):

  case identity   trace_id -> case_id  (spans missing trace_id are grouped
                  under their own span_id so nothing is silently merged)
  model name      gen_ai.request.model, gen_ai.response.model, or llm.model
  input tokens    gen_ai.usage.input_tokens, gen_ai.usage.prompt_tokens,
                  llm.usage.input_tokens, llm.usage.prompt_tokens,
                  llm.token_count.prompt
                  (first non-empty value wins)
  output tokens   gen_ai.usage.output_tokens, gen_ai.usage.completion_tokens,
                  llm.usage.output_tokens, llm.usage.completion_tokens,
                  llm.token_count.completion
  tool call       attribute tool.name (or mcp.tool.name), or a span whose
                  name starts with "tool." (the part after the prefix is the
                  tool name). Span duration becomes the tool event's
                  latency_ms.
  failure         status.code in ("ERROR", "STATUS_CODE_ERROR") marks the
                  whole case failed.
  retry marker    attribute agentpnl.retry -> retry event (reason = value);
                  optional agentpnl.branch scopes the waste marking to one
                  parallel branch instead of the whole attempt. On a span
                  that is both a model call and a retry marker, the model
                  event is emitted first: the retry marks FOLLOWING steps
                  as retry-path, it does not retroactively taint the call
                  on its own span (for branch-scoped retries the branch
                  work is still caught by the retroactive branch rule).
  escalation      attribute agentpnl.escalation_minutes -> escalation event;
                  agentpnl.escalation_reason supplies the reason.
  cache           gen_ai.usage.cache_read_input_tokens (or the llm.usage /
                  agentpnl.cached_input_tokens equivalents) -> cached input
                  tokens, priced at the Tracker's cache_read_discount
  branch          attribute agentpnl.branch on a model span tags that call's
                  branch for branch-scoped retry accounting
  overrides       agentpnl.business_value and agentpnl.success set the end
                  event fields explicitly when present.

Provider is guessed from the model name (gpt -> openai, claude -> anthropic,
gemini -> google, grok -> xai); unknown names fall back to the documented
estimate in common.FALLBACK_PRICE and are collected in
tracker.unpriced_models.

Spans accept OTLP JSON attribute lists ([{"key": k, "value": {...}}]) as
well as flat dict attributes, since exporters vary.
"""

import json

from .common import events_to_tracker, ledger_from_tracker, guess_provider


def _plain(value):
    """Unwrap an OTLP AnyValue into a plain Python value."""
    if isinstance(value, dict):
        for key in ("stringValue", "boolValue", "intValue", "doubleValue"):
            if key in value:
                return value[key]
        if "arrayValue" in value:
            return [_plain(v) for v in value["arrayValue"].get("values", [])]
        if "kvlistValue" in value:
            return {kv.get("key"): _plain(kv.get("value"))
                    for kv in value["kvlistValue"].get("values", [])}
        return value
    return value


def _attributes(span):
    raw = span.get("attributes", {})
    if isinstance(raw, dict):
        return {k: _plain(v) for k, v in raw.items()}
    out = {}
    for item in raw or []:
        if isinstance(item, dict) and "key" in item:
            out[item["key"]] = _plain(item.get("value"))
    return out


def _num(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _nonneg(value, default=0):
    """_num clamped at zero: negative counters are malformed attributes,
    never legitimate economics (they would produce negative cost)."""
    return max(0.0, _num(value, default))


def _first(attrs, *keys):
    for key in keys:
        if attrs.get(key) not in (None, ""):
            return attrs[key]
    return None


def _parse_bool(value):
    """Parse an OTel attribute as a boolean. bool("false") is True, so a
    naive bool() cast silently flips string "false" to True (I1)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("1", "true", "t", "yes", "y"):
        return True
    if s in ("0", "false", "f", "no", "n"):
        return False
    return None


def _span_times(span):
    start = _num(span.get("startTimeUnixNano") or span.get("start_time_unix_nano"), 0)
    end = _num(span.get("endTimeUnixNano") or span.get("end_time_unix_nano"), start)
    return start, end


def load_otel(path, agent_name="otel-import"):
    """Parse an OTLP span JSON file and return a sanitized ledger dict."""
    with open(path) as f:
        data = json.load(f)
    spans = data["spans"] if isinstance(data, dict) else data

    cases = {}
    for span in spans:
        attrs = _attributes(span)
        trace_id = (span.get("traceId") or span.get("trace_id")
                    or span.get("spanId") or span.get("span_id") or "unknown")
        case = cases.setdefault(trace_id, {"spans": [], "failed": False,
                                           "business_value": 0.0,
                                           "success_override": None})
        case["spans"].append((span, attrs))

        status = span.get("status") or {}
        code = str(status.get("code", "")).upper()
        if code in ("ERROR", "STATUS_CODE_ERROR"):
            case["failed"] = True
        if attrs.get("agentpnl.business_value") is not None:
            case["business_value"] = _num(attrs["agentpnl.business_value"])
        if attrs.get("agentpnl.success") is not None:
            case["success_override"] = _parse_bool(attrs["agentpnl.success"])

    events = []
    for case_id, case in cases.items():
        ordered = sorted(case["spans"], key=lambda sa: _span_times(sa[0])[0])
        for span, attrs in ordered:
            name = span.get("name", "")
            start, end = _span_times(span)
            latency_ms = (end - start) / 1e6 if end >= start else None

            # M2b: on a dual-attribute span (model call + retry marker), the
            # model event comes first. A retry event marks the FOLLOWING
            # steps as retry-path (the documented event semantics); emitting
            # it before the span's own model call would misattribute that
            # call as post-retry work.
            model = _first(attrs, "gen_ai.request.model",
                           "gen_ai.response.model", "llm.model")
            if model:
                in_tok = _nonneg(_first(attrs, "gen_ai.usage.input_tokens",
                                        "gen_ai.usage.prompt_tokens",
                                        "llm.usage.input_tokens",
                                        "llm.usage.prompt_tokens",
                                        "llm.token_count.prompt"))
                out_tok = _nonneg(_first(attrs, "gen_ai.usage.output_tokens",
                                         "gen_ai.usage.completion_tokens",
                                         "llm.usage.output_tokens",
                                         "llm.usage.completion_tokens",
                                         "llm.token_count.completion"))
                cached_tok = _nonneg(_first(attrs,
                                            "gen_ai.usage.cache_read_input_tokens",
                                            "llm.usage.cache_read_input_tokens",
                                            "agentpnl.cached_input_tokens"))
                ev = {"type": "model", "case_id": case_id,
                      "provider": guess_provider(model), "model": model,
                      "input_tokens": in_tok, "output_tokens": out_tok}
                if cached_tok:
                    ev["cached_input_tokens"] = cached_tok
                if attrs.get("agentpnl.branch") not in (None, ""):
                    ev["branch"] = str(attrs["agentpnl.branch"])
                events.append(ev)

            if attrs.get("agentpnl.retry") not in (None, ""):
                ev = {"type": "retry", "case_id": case_id,
                      "reason": str(attrs["agentpnl.retry"])}
                if attrs.get("agentpnl.branch") not in (None, ""):
                    ev["branch"] = str(attrs["agentpnl.branch"])
                events.append(ev)
            if attrs.get("agentpnl.escalation_minutes") not in (None, ""):
                events.append({"type": "escalation", "case_id": case_id,
                               "minutes": _nonneg(attrs["agentpnl.escalation_minutes"]),
                               "reason": str(attrs.get("agentpnl.escalation_reason", ""))})

            if model:
                continue

            tool = _first(attrs, "tool.name", "mcp.tool.name")
            if tool is None and name.startswith("tool."):
                tool = name.split(".", 1)[1]
            if tool:
                ev = {"type": "tool", "case_id": case_id, "name": str(tool)}
                if latency_ms is not None:
                    ev["latency_ms"] = latency_ms
                events.append(ev)

        success = (not case["failed"]) if case["success_override"] is None \
            else case["success_override"]
        events.append({"type": "end", "case_id": case_id, "success": success,
                       "business_value": case["business_value"]})

    tracker = events_to_tracker(agent_name, events)
    return ledger_from_tracker(tracker)
