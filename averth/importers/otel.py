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
  retry marker    attribute averth.retry -> retry event (reason = value);
                  an explicit falsy value (False, 0, "false", "no", "0")
                  means "not a retry" and emits no event; True/"true"/
                  "yes"/"1" or any other non-empty value emits the event.
                  optional averth.branch scopes the waste marking to one
                  parallel branch instead of the whole attempt. On a span
                  that is both a model call and a retry marker, the model
                  event is emitted first: the retry marks FOLLOWING steps
                  as retry-path, it does not retroactively taint the call
                  on its own span (for branch-scoped retries the branch
                  work is still caught by the retroactive branch rule).
  escalation      attribute averth.escalation_minutes -> escalation event
                  (only for a positive finite number of minutes; falsy or
                  non-numeric values emit nothing);
                  averth.escalation_reason supplies the reason.
  cache           gen_ai.usage.cache_read_input_tokens (or the llm.usage /
                  averth.cached_input_tokens equivalents) -> cached input
                  tokens, priced at the Tracker's cache_read_discount
  branch          attribute averth.branch on a model span tags that call's
                  branch for branch-scoped retry accounting; only a
                  non-empty string names a branch (False/None/"" mean
                  "no branch")
  overrides       averth.business_value and averth.success set the end
                  event fields explicitly when present.

Provider is guessed from the model name (gpt -> openai, claude -> anthropic,
gemini -> google, grok -> xai); unknown names fall back to the documented
estimate in common.FALLBACK_PRICE and are collected in
tracker.unpriced_models.

Spans accept OTLP JSON attribute lists ([{"key": k, "value": {...}}]) as
well as flat dict attributes, since exporters vary.
"""

import json
import math

from .common import (events_to_tracker, ledger_from_tracker, guess_provider,
                     _parse_bool_tristate)


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


def _first(attrs, *keys):
    for key in keys:
        if attrs.get(key) not in (None, ""):
            return attrs[key]
    return None


def _first_named(attrs, *keys):
    """_first, but returns (attribute name, value) so error messages can
    name the offending attribute."""
    for key in keys:
        if attrs.get(key) not in (None, ""):
            return key, attrs[key]
    return None, None


def _token_count(value, attr_name):
    """Validate one token-count attribute (H4).

    Accepts scalars: int/float (bool rejected — it is a type error, not a
    count) and numeric strings (OTLP intValue can arrive as a string).
    None/missing/"" -> 0 default. A non-scalar value (list, dict, ...)
    raises ValueError naming the attribute instead of silently zeroing
    real spend. Negative counts are clamped to 0 (malformed attributes,
    never legitimate economics).
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        raise ValueError("token attribute %r must be a number, got %r"
                         % (attr_name, value))
    if isinstance(value, (int, float)):
        num = float(value)
    elif isinstance(value, str):
        try:
            num = float(value)
        except ValueError:
            raise ValueError("token attribute %r must be numeric, got %r"
                             % (attr_name, value))
    else:
        raise ValueError("token attribute %r must be a scalar number, got %r"
                         % (attr_name, value))
    if not math.isfinite(num):
        raise ValueError("token attribute %r must be finite, got %r"
                         % (attr_name, value))
    return max(0.0, num)


def _retry_marker_present(value):
    """True when a retry marker should emit a retry event.

    Explicit falsy values (False, 0, "false", "no", "0", "") mean "not a
    retry" and are ignored. True / "true" / "yes" / "1" / any other
    non-empty value (a free-text reason) emits the retry event.
    """
    if value is None or value == "":
        return False
    tri = _parse_bool_tristate(value)
    if tri is False:
        return False
    if tri is None and not value:
        return False
    return True


def _branch_name(value):
    """Only a non-empty string names a branch; False/None/"" (and any
    non-string) mean "no branch" instead of the literal name "False"."""
    return value if isinstance(value, str) and value != "" else None


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


def _brand(attrs, name):
    """Read an Averth-specific OTel attribute."""
    return attrs.get("averth." + name)


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
        # H3: garbage must never clobber an earlier explicit value —
        # write only when the numeric parse succeeds, keep the previous
        # value otherwise (fail-loud inf is left to end_attempt's finite
        # check).
        bv = _brand(attrs, "business_value")
        if bv is not None:
            try:
                parsed_bv = float(bv)
            except (TypeError, ValueError, OverflowError):
                parsed_bv = None
            if parsed_bv is not None:
                case["business_value"] = parsed_bv
        # H2: an unparseable value ("maybe") parses to None and must not
        # clobber an earlier explicit override.
        sv = _brand(attrs, "success")
        if sv is not None:
            parsed_success = _parse_bool(sv)
            if parsed_success is not None:
                case["success_override"] = parsed_success

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
                # H4: token attributes must be scalar; a non-scalar value
                # (list, dict, ...) raises ValueError naming the attribute
                # instead of silently zeroing spend.
                in_key, in_raw = _first_named(attrs, "gen_ai.usage.input_tokens",
                                              "gen_ai.usage.prompt_tokens",
                                              "llm.usage.input_tokens",
                                              "llm.usage.prompt_tokens",
                                              "llm.token_count.prompt")
                in_tok = _token_count(in_raw, in_key)
                out_key, out_raw = _first_named(attrs, "gen_ai.usage.output_tokens",
                                                "gen_ai.usage.completion_tokens",
                                                "llm.usage.output_tokens",
                                                "llm.usage.completion_tokens",
                                                "llm.token_count.completion")
                out_tok = _token_count(out_raw, out_key)
                cached_key, cached_raw = _first_named(attrs,
                                                      "gen_ai.usage.cache_read_input_tokens",
                                                      "llm.usage.cache_read_input_tokens",
                                                      "averth.cached_input_tokens")
                cached_tok = _token_count(cached_raw, cached_key)
                ev = {"type": "model", "case_id": case_id,
                      "provider": guess_provider(model), "model": model,
                      "input_tokens": in_tok, "output_tokens": out_tok}
                if cached_tok:
                    ev["cached_input_tokens"] = cached_tok
                # M6: False/None/"" -> no branch; only non-empty strings.
                branch = _branch_name(_brand(attrs, "branch"))
                if branch is not None:
                    ev["branch"] = branch
                events.append(ev)

            # H1: explicit falsy retry markers ("false", False, 0, "no")
            # mean "not a retry" and emit no event; True/"true"/"yes"/"1"
            # or a free-text reason emits the retry event.
            if _retry_marker_present(_brand(attrs, "retry")):
                ev = {"type": "retry", "case_id": case_id,
                      "reason": str(_brand(attrs, "retry"))}
                # M6: same branch rule as the model event.
                branch = _branch_name(_brand(attrs, "branch"))
                if branch is not None:
                    ev["branch"] = branch
                events.append(ev)
            # M1: falsy/garbage escalation markers ("false", 0, negatives,
            # non-finite) fabricate nothing — the event is emitted only for
            # a positive finite number of minutes.
            esc_raw = _brand(attrs, "escalation_minutes")
            if esc_raw not in (None, ""):
                esc_minutes = _num(esc_raw)
                if math.isfinite(esc_minutes) and esc_minutes > 0:
                    events.append({"type": "escalation", "case_id": case_id,
                                   "minutes": esc_minutes,
                                   "reason": str(_brand(attrs, "escalation_reason") or "")})

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
                       "outcome_inferred": case["success_override"] is None,
                       "business_value": case["business_value"]})

    tracker = events_to_tracker(agent_name, events)
    return ledger_from_tracker(tracker)
