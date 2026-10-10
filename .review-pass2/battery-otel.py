"""Hostile battery for averth/importers/otel.py (review pass 2)."""
import json, os, sys, tempfile, traceback

sys.path.insert(0, "/home/hatch/workspace/averth")
from averth.importers import otel


def load(spans):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spans, f)
        path = f.name
    try:
        return otel.load_otel(path)
    finally:
        os.unlink(path)


def span(trace="t1", name="s", attrs=None, status=None, otlp_attrs=False,
         span_id="s1", **kw):
    s = {"traceId": trace, "spanId": span_id, "name": name,
         "startTimeUnixNano": "1000000000", "endTimeUnixNano": "2000000000"}
    s.update(kw)
    if otlp_attrs:
        s["attributes"] = [{"key": k, "value": {"stringValue": str(v)}}
                            for k, v in (attrs or {}).items()]
    else:
        s["attributes"] = attrs or {}
    if status:
        s["status"] = status
    return s


def show(tag, fn):
    try:
        r = fn()
        print("OK   %-46s -> %s" % (tag, r))
    except Exception as e:
        print("RAISE %-46s -> %s: %s" % (tag, type(e).__name__, e))


# ---- 1. I1 fix: string "false" must not become success=True ----
def t_success_false_str():
    l = load([span(attrs={"averth.success": "false",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s" % l["attempts"][0]["success"]

def t_success_FALSE_caps():
    l = load([span(attrs={"averth.success": "FALSE",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s" % l["attempts"][0]["success"]

def t_success_zero_str():
    l = load([span(attrs={"averth.success": "0",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s" % l["attempts"][0]["success"]

def t_success_no_str():
    l = load([span(attrs={"averth.success": "no",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s" % l["attempts"][0]["success"]

def t_success_true_str():
    l = load([span(attrs={"averth.success": "true",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s" % l["attempts"][0]["success"]

def t_success_garbage():
    # unparseable value: silently ignored (falls back to status)?
    l = load([span(attrs={"averth.success": "maybe",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s (garbage ignored?)" % l["attempts"][0]["success"]

def t_success_garbage_clobbers():
    # span1 explicit false, span2 garbage "maybe" -> does garbage reset override?
    l = load([
        span(trace="t1", span_id="a", attrs={"averth.success": "false",
              "gen_ai.request.model": "gpt-4o",
              "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 50},
             startTimeUnixNano="1000000000", endTimeUnixNano="1100000000"),
        span(trace="t1", span_id="b", attrs={"averth.success": "maybe"},
             startTimeUnixNano="1200000000", endTimeUnixNano="1300000000"),
    ])
    return "success=%s (want False)" % l["attempts"][0]["success"]

def t_success_otlp_boolvalue():
    l = load([span(otlp_attrs=True, attrs={"gen_ai.request.model": "gpt-4o"})])
    # inject real OTLP boolValue manually
    s = span()
    s["attributes"] = [{"key": "averth.success", "value": {"boolValue": False}},
                       {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                       {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "100"}},
                       {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "50"}}]
    l = load([s])
    return "success=%s (want False)" % l["attempts"][0]["success"]

def t_success_overrides_status_error():
    l = load([span(status={"code": "STATUS_CODE_ERROR"},
                   attrs={"averth.success": "true",
                          "gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50})])
    return "success=%s (override beats status?)" % l["attempts"][0]["success"]


# ---- 2. truthiness traps on other averth.* attributes ----
def t_retry_false_bool():
    l = load([
        span(trace="t1", span_id="a",
             attrs={"gen_ai.request.model": "gpt-4o",
                    "gen_ai.usage.input_tokens": 1000, "gen_ai.usage.output_tokens": 500,
                    "averth.retry": False},
             startTimeUnixNano="1000000000", endTimeUnixNano="1100000000"),
        span(trace="t1", span_id="b",
             attrs={"gen_ai.request.model": "gpt-4o",
                    "gen_ai.usage.input_tokens": 1000, "gen_ai.usage.output_tokens": 500},
             startTimeUnixNano="1200000000", endTimeUnixNano="1300000000"),
    ])
    a = l["attempts"][0]
    return "retries=%s terminal=%.6f retry_path=%.6f (want retries=0, terminal>0)" % (
        a["retries"], a["terminal_model_cost"], a["retry_path_cost"])

def t_retry_zero_int():
    l = load([span(attrs={"averth.retry": 0})])
    a = l["attempts"][0]
    return "retries=%s (want 0)" % a["retries"]

def t_escalation_false_bool():
    l = load([span(attrs={"averth.escalation_minutes": False})])
    a = l["attempts"][0]
    return "human_min=%s (want 0, no event)" % a["human_min"]

def t_branch_false_bool():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 100,
                          "gen_ai.usage.output_tokens": 50,
                          "averth.branch": False})])
    a = l["attempts"][0]
    return "steps=%s" % (a.get("events"),)


# ---- 3. token extraction ----
def t_tokens_otlp_intvalue_string():
    # OTLP JSON encodes int64 as STRINGS
    s = span()
    s["attributes"] = [
        {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
        {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "1500"}},
        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "300"}}]
    l = load([s])
    a = l["attempts"][0]
    return "total_tokens=%s cost=%.6f" % (a["total_tokens"], a["total_cost"])

def t_tokens_dialect_first_wins():
    l = load([span(attrs={"gen_ai.request.model": "claude-3-5-sonnet-20241022",
                          "gen_ai.usage.prompt_tokens": 200,
                          "llm.usage.prompt_tokens": 999})])
    a = l["attempts"][0]
    return "total_tokens=%s (want 200+0=200)" % a["total_tokens"]

def t_tokens_negative_clamped():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": -50,
                          "gen_ai.usage.output_tokens": 50})])
    a = l["attempts"][0]
    return "total_tokens=%s (want 50)" % a["total_tokens"]

def t_tokens_list_typeerror():
    # array where scalar expected -> silent 0?
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": [1000000],
                          "gen_ai.usage.output_tokens": 50})])
    a = l["attempts"][0]
    return "total_tokens=%s model_cost=%.6f (1M tokens vanished?)" % (
        a["total_tokens"], a["model"])

def t_tokens_garbage_string():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": "abc",
                          "gen_ai.usage.output_tokens": 50})])
    a = l["attempts"][0]
    return "total_tokens=%s (want 50, input->0)" % a["total_tokens"]

def t_tokens_inf():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": "1e999",
                          "gen_ai.usage.output_tokens": 50})])
    return "survived: %s" % l["attempts"][0]["total_tokens"]

def t_tokens_huge_int():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 10**400,
                          "gen_ai.usage.output_tokens": 50})])
    return "survived"

def t_tokens_over_cap():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 10**13,
                          "gen_ai.usage.output_tokens": 50})])
    return "survived"

def t_tokens_fractional():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 150.9,
                          "gen_ai.usage.output_tokens": 50})])
    a = l["attempts"][0]
    return "total_tokens=%s (150.9 truncated?)" % a["total_tokens"]

def t_tokens_zero_explicit():
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
                          "gen_ai.usage.input_tokens": 0,
                          "gen_ai.usage.output_tokens": 0})])
    a = l["attempts"][0]
    return "total_cost=%.6f (want 0)" % a["total_cost"]

def t_cached_tokens():
    l = load([span(attrs={"gen_ai.request.model": "claude-3-5-sonnet-20241022",
                          "gen_ai.usage.input_tokens": 1000,
                          "gen_ai.usage.output_tokens": 100,
                          "gen_ai.usage.cache_read_input_tokens": 900})])
    a = l["attempts"][0]
    return "cached=%s savings=%.6f" % (a["cached_tokens"], a["cache_savings"])


# ---- 4. malformed spans ----
def t_no_trace_no_span_id():
    # two spans, neither has trace_id NOR span_id -> "unknown" merge?
    s1 = {"name": "a", "attributes": {"gen_ai.request.model": "gpt-4o",
          "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 10}}
    s2 = {"name": "b", "attributes": {"gen_ai.request.model": "gpt-4o",
          "gen_ai.usage.input_tokens": 200, "gen_ai.usage.output_tokens": 20}}
    l = load([s1, s2])
    return "attempts=%d (docstring says no silent merge)" % len(l["attempts"])

def t_span_name_none():
    return load([{"traceId": "t1", "name": None, "attributes": {}}]) and "survived"

def t_span_not_dict():
    return load(["just a string"]) and "survived"

def t_status_not_dict():
    return load([span(status="ERROR")]) and "survived"

def t_spans_key_missing():
    return load({"resourceSpans": []}) and "survived"

def t_spans_not_list():
    return load({"spans": {"traceId": "t1"}}) and "survived"

def t_model_nonstring():
    return load([span(attrs={"gen_ai.request.model": 12345})]) and "survived"

def t_business_value_garbage_resets():
    l = load([
        span(trace="t1", span_id="a", attrs={"averth.business_value": 5.0},
             startTimeUnixNano="1000000000", endTimeUnixNano="1100000000"),
        span(trace="t1", span_id="b", attrs={"averth.business_value": "abc"},
             startTimeUnixNano="1200000000", endTimeUnixNano="1300000000"),
    ])
    return "business_value=%s (want 5.0, garbage must not reset)" % l["attempts"][0]["business_value"]

def t_business_value_inf():
    return load([span(attrs={"averth.business_value": "1e999"})]) and "survived"

def t_tool_name_and_model():
    # span carrying both model and tool.name: tool silently dropped?
    l = load([span(name="tool.search", attrs={"gen_ai.request.model": "gpt-4o",
          "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 10,
          "tool.name": "web_search"})])
    a = l["attempts"][0]
    return "tools=%s events=%s" % (a["tools"], a["events"])

def t_tool_span_latency():
    s = span(name="tool.web_search", attrs={"tool.name": "web_search"},
             startTimeUnixNano="1000000000", endTimeUnixNano="3500000000")
    l = load([s])
    a = l["attempts"][0]
    return "tool_latency_ms=%s (want 2500)" % a["tool_latency_ms"]

def t_tool_cost_default():
    l = load([span(name="tool.web_search", attrs={"tool.name": "web_search"})])
    a = l["attempts"][0]
    return "tools_cost=%.6f (arbitrary default?)" % a["tools"]

def t_end_to_end_math():
    # hand-check: gpt-4o 1000 in / 500 out. pricing?
    from averth import pricing
    pin, pout = pricing.MODEL_PRICES.get("openai:gpt-4o", (None, None))
    l = load([span(attrs={"gen_ai.request.model": "gpt-4o",
          "gen_ai.usage.input_tokens": 1000, "gen_ai.usage.output_tokens": 500})])
    a = l["attempts"][0]
    if pin is None:
        return "gpt-4o unpriced, model_cost=%.6f unpriced=%s" % (a["model"], l["unpriced_models"])
    want = 1000/1e6*pin + 500/1e6*pout
    return "model=%.6f want=%.6f match=%s" % (a["model"], want, abs(a["model"]-want) < 1e-12)


for tag, fn in sorted([(k, v) for k, v in list(globals().items()) if k.startswith("t_")]):
    show(tag, fn)
