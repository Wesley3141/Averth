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
                  case failed ONLY if the error is terminal (see
                  "recovered attempt" below). A recovered error does not
                  make the whole attempt a failed run for zero outcomes.
  recovered       An attempt is RECOVERED, not terminally failed, when
  attempt         (a) at least one span has ERROR status, (b) no explicit
                  averth.success override is present, and (c) at least one
                  substantive span (a model call or a tool call) that is
                  itself not ERROR starts after the last ERROR span.
                  The recovered attempt ends success=True, with
                  outcome_inferred=True (there is no acceptance label in
                  an OTLP export; "recovered" means "completed downstream
                  after discarding a failed segment", NOT "all work
                  succeeded" and NOT "a human accepted the outcome").
                  A case whose last substantive span is ERROR, or that
                  has only non-substantive spans (agent.run, debug.note)
                  after its last ERROR, is terminally failed, exactly as
                  before. An explicit averth.success override always wins.
                  This is stricter than the LangSmith importer's rule
                  (failed only if the chronologically last run errored),
                  because an OTLP export's last span by time is often a
                  parent or debug span, not work.
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
  recovered       In a RECOVERED attempt only, retry waste is scoped to
  retry scope     the failed segment instead of the whole attempt, because
                  the Tracker has no "clear the global retry flag" event:
                  a global (unscoped) retry would taint every
                  post-recovery step as waste forever, which is exactly
                  the bug this rule fixes. Scoping, in priority order:
                  (1) an explicit averth.branch on the span, unchanged;
                  (2) a span-name prefix matching branch + digits
                  (branch0, branch2, ...) -- the naming the OTel live
                  validation generator uses -- which tags every model/tool
                  event on that branch, so a branch retry retroactively
                  marks that branch's past work (including a dead branch's
                  model calls) as waste while leaving other branches and
                  the fan-in merge terminal;
                  (3) otherwise a unique scope for that one ERROR span
                  (otel:recovered:<span id>), which tags only that span's
                  own model/tool event, so only the failed call itself is
                  waste and every post-recovery step stays terminal.
                  In a terminally failed attempt, retry scoping is
                  unchanged (global retries stay global), so existing
                  global-retry tests are unaffected. Total cost never
                  changes under this rule; only its allocation between
                  failed, retry-path, and terminal buckets changes.
                  Ambiguity, flagged, not hidden: in a fan-out, a dead
                  branch that never recovers still leaves the attempt
                  "recovered" if a downstream merge completes, because
                  the merge is substantive work after the last ERROR.
                  That success is attempt-level completion after
                  discarding a branch, not branch-level success, and the
                  dead branch's cost stays visible as retry-path spend.
                  Likewise, a human escalation that precedes the failure
                  (Trace A: review.human before refund_api ERROR) is NOT
                  retry cost and is NOT removed by recovery; it stays in
                  the attempt total. If a trace cannot distinguish "the
                  last ERROR was superseded" from "the last ERROR was
                  ignored", this rule chooses superseded when substantive
                  work follows it, and the caller must not read the
                  resulting success as an acceptance label.
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
import re

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


def _is_error_span(span):
    """True when an OTLP span carries an ERROR status code."""
    status = span.get("status") or {}
    return str(status.get("code", "")).upper() in ("ERROR", "STATUS_CODE_ERROR")


def _span_tool_name(span, attrs):
    """Tool name for a span, mirroring the event loop's detection."""
    tool = _first(attrs, "tool.name", "mcp.tool.name")
    if tool is None and span.get("name", "").startswith("tool."):
        tool = span["name"].split(".", 1)[1]
    return tool


def _span_work_kind(span, attrs):
    """'model', 'tool', or None: whether this span produces a work event.

    Non-work spans (agent.run parents, debug.note, escalation-only spans)
    never count as recovery evidence: a debug note after a terminal error
    must not turn a failed attempt into a recovered one.
    """
    if _first(attrs, "gen_ai.request.model", "gen_ai.response.model",
              "llm.model") is not None:
        return "model"
    if _span_tool_name(span, attrs) is not None:
        return "tool"
    return None


def _branch_digit_prefix(name):
    """Span-name prefix matching branch + digits (branch0, branch2, ...).

    Only this narrow pattern is trusted as an inferred branch. Arbitrary
    prefixes (payment, llm, tool, review) are NOT grouped: without a
    parentSpanId there is no evidence two spans sharing a subsystem name
    are the same parallel branch, and grouping them would invent waste
    attribution. A trace whose branches are named anything else must use
    an explicit averth.branch attribute to get branch-scoped waste.
    """
    prefix = name.split(".", 1)[0] if "." in name else ""
    return prefix if re.fullmatch(r"branch\d+", prefix or "") else None


def _recovery_scopes(ordered):
    """Compute (recovered, scope_by_span_id) for one case's ordered spans.

    ordered is a list of (span, attrs) sorted by start time, the same
    order the event loop emits. recovered follows the module docstring:
    an ERROR exists and a non-ERROR substantive span starts after the
    last ERROR span. scope_by_span_id maps id(span) -> branch scope for
    recovered cases only; it is empty for terminally failed cases, where
    the old global-retry behaviour is preserved exactly.
    """
    error_positions = [i for i, (span, _attrs) in enumerate(ordered)
                       if _is_error_span(span)]
    if not error_positions:
        return False, {}
    last_error = error_positions[-1]
    recovered = any(
        _span_work_kind(span, attrs) is not None
        and not _is_error_span(span)
        for span, attrs in ordered[last_error + 1:])
    if not recovered:
        return False, {}
    scopes = {}
    for idx, (span, attrs) in enumerate(ordered):
        explicit = _branch_name(_brand(attrs, "branch"))
        if explicit is not None:
            scopes[id(span)] = explicit
            continue
        prefix = _branch_digit_prefix(span.get("name", ""))
        if prefix is not None:
            scopes[id(span)] = prefix
            continue
        if (_retry_marker_present(_brand(attrs, "retry"))
                or _is_error_span(span)):
            sid = span.get("spanId") or span.get("span_id") or "pos-%d" % idx
            scopes[id(span)] = "otel:recovered:%s" % sid
    return True, scopes


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
        # C-START: a case with zero billable spans still ran; without a start
        # marker its "end" is stray and the case is silently dropped.
        events.append({"type": "start", "case_id": case_id})
        ordered = sorted(case["spans"], key=lambda sa: _span_times(sa[0])[0])
        # Recovered-attempt rule (see module docstring): computed once per
        # case, before any event is emitted, because retry scoping during
        # emission depends on it. Terminally failed cases get an empty
        # scope map and keep the old behaviour exactly.
        recovered, scope_by_id = _recovery_scopes(ordered)
        for span, attrs in ordered:
            # Scope for this span: in a recovered case, the recovery
            # scope (explicit branch, branch-digit prefix, or the unique
            # scope of that one ERROR span); otherwise the old explicit
            # branch only, so global retries stay global.
            scope = scope_by_id.get(id(span)) if recovered else \
                _branch_name(_brand(attrs, "branch"))
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
                # U-OTEL: usage_known=False when neither token attribute was
                # present. Without this, missing usage defaults to True in
                # common.py and renders as $0.00 measured — looking free.
                has_usage = in_key is not None or out_key is not None
                ev = {"type": "model", "case_id": case_id,
                      "provider": guess_provider(model), "model": model,
                      "input_tokens": in_tok, "output_tokens": out_tok,
                      "usage_known": has_usage}
                if cached_tok:
                    ev["cached_input_tokens"] = cached_tok
                # M6: False/None/"" -> no branch; only non-empty strings.
                # In a recovered case, scope is the recovery scope above
                # (explicit branch, branch-digit prefix, or unique ERROR
                # scope), so a branch retry retroactively marks only that
                # segment as waste and post-recovery steps stay terminal.
                if scope is not None:
                    ev["branch"] = scope
                events.append(ev)

            # Tool-first ordering for recovered scoping: a branch retry
            # retroactively marks only PAST steps, so the failed tool
            # call must be logged before its retry event, otherwise the
            # retry finds no tool step to mark and the tool waste is
            # silently lost. Model spans already emit the model event
            # first (M2b); tool spans previously emitted the tool event
            # after the retry, which lost exactly this marking.
            tool = _first(attrs, "tool.name", "mcp.tool.name")
            if tool is None and name.startswith("tool."):
                tool = name.split(".", 1)[1]
            if not model and tool:
                ev = {"type": "tool", "case_id": case_id, "name": str(tool)}
                if latency_ms is not None:
                    ev["latency_ms"] = latency_ms
                # Recovered case only: carry the recovery scope so the
                # failed tool call itself is waste while a later
                # successful call of the same tool stays terminal.
                if recovered and scope is not None:
                    ev["branch"] = scope
                events.append(ev)

            # H1: explicit falsy retry markers ("false", False, 0, "no")
            # mean "not a retry" and emit no event; True/"true"/"yes"/"1"
            # or a free-text reason emits the retry event.
            if _retry_marker_present(_brand(attrs, "retry")):
                ev = {"type": "retry", "case_id": case_id,
                      "reason": str(_brand(attrs, "retry"))}
                # M6: same branch rule as the model event. In a recovered
                # case this is the recovery scope, never a global retry:
                # the Tracker has no clear-retry event, so a global retry
                # here would taint every post-recovery step as waste.
                if scope is not None:
                    ev["branch"] = scope
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

            # Model and tool events are already emitted above (model
            # first, then tool, then retry, so a branch retry finds the
            # failed step in the past). Nothing more to emit here.

        # Recovered attempts end success=True (outcome still inferred
        # unless an explicit override exists); terminally failed attempts
        # keep the old rule. An explicit override always wins.
        if case["success_override"] is not None:
            success = case["success_override"]
        elif recovered:
            success = True
        else:
            success = not case["failed"]
        events.append({"type": "end", "case_id": case_id, "success": success,
                       "outcome_inferred": case["success_override"] is None,
                       "business_value": case["business_value"]})

    tracker = events_to_tracker(agent_name, events)
    return ledger_from_tracker(tracker)
