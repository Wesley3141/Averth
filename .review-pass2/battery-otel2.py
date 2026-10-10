"""Follow-up hostile probes for otel.py."""
import json, os, sys, tempfile

sys.path.insert(0, "/home/hatch/workspace/averth")
from averth.importers import otel
from averth.importers import common as C


def load(spans):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spans, f)
        path = f.name
    try:
        return otel.load_otel(path)
    finally:
        os.unlink(path)


def span(trace="t1", name="s", attrs=None, span_id="s1", **kw):
    s = {"traceId": trace, "spanId": span_id, "name": name,
         "startTimeUnixNano": "1000000000", "endTimeUnixNano": "2000000000"}
    s.update(kw)
    s["attributes"] = attrs or {}
    return s


MODEL = {"gen_ai.request.model": "gpt-4o",
         "gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 50}


def show(tag, fn):
    try:
        print("OK   %-44s -> %s" % (tag, fn()))
    except Exception as e:
        print("RAISE %-44s -> %s: %s" % (tag, type(e).__name__, e))


def p1():
    # THE direct I1 analog: averth.retry="false" (string) -> retry event?
    l = load([span(attrs={**MODEL, "averth.retry": "false"})])
    a = l["attempts"][0]
    return "retries=%d (want 0; string 'false' must not be a marker)" % a["retries"]

def p2():
    l = load([span(attrs={**MODEL, "averth.retry": "False"})])
    return "retries=%d (want 0)" % l["attempts"][0]["retries"]

def p3():
    l = load([span(attrs={**MODEL, "averth.retry": "no"})])
    return "retries=%d (want 0)" % l["attempts"][0]["retries"]

def p4():
    # legitimate retry still works
    l = load([span(attrs={**MODEL, "averth.retry": "timeout, retrying"})])
    return "retries=%d (want 1)" % l["attempts"][0]["retries"]

def p5():
    # escalation_minutes="false"
    l = load([span(attrs={**MODEL, "averth.escalation_minutes": "false"})])
    a = l["attempts"][0]
    return "human_min=%s events=%s (want 0.0, no escalation event)" % (
        a["human_min"], [e for e in a["events"] if e[0] == "escalation"])

def p6():
    # business_value garbage reset, WITH model spans so the case exists
    l = load([
        span(trace="t1", span_id="a",
             attrs={**MODEL, "averth.business_value": 5.0},
             startTimeUnixNano="1000000000", endTimeUnixNano="1100000000"),
        span(trace="t1", span_id="b",
             attrs={**MODEL, "averth.business_value": "abc"},
             startTimeUnixNano="1200000000", endTimeUnixNano="1300000000"),
    ])
    return "business_value=%s (want 5.0)" % l["attempts"][0]["business_value"]

def p7():
    # business_value inf with a real model span
    l = load([span(attrs={**MODEL, "averth.business_value": "1e999"})])
    return "business_value=%s" % l["attempts"][0]["business_value"]

def p8():
    # override-only case: spans carry averth.success=false but no model/tool
    l = load([span(attrs={"averth.success": "false"})])
    return "attempts=%d (explicit failure signal lost?)" % len(l["attempts"])

def p9():
    # branch=False -> str "False"?
    l = load([span(attrs={**MODEL, "averth.branch": False})])
    t = C.events_to_tracker("x", [])
    return "branch stored=%r" % (l["attempts"][0]["events"],)

def p10():
    # fractional tokens on fallback path: check raw steps via events_to_tracker path
    t = C.events_to_tracker("x", [{"type": "model", "case_id": "c",
        "provider": "unknown", "model": "mystery-1",
        "input_tokens": 150.9, "output_tokens": 50},
        {"type": "end", "case_id": "c", "success": True, "business_value": 0.0}])
    s = t.attempts[0]["steps"][0]
    return "step in=%r out=%r (want ints 150/50 like priced path)" % (s["in"], s["out"])

def p11():
    # same but priced model -> int truncation?
    t = C.events_to_tracker("x", [{"type": "model", "case_id": "c",
        "provider": "openai", "model": "gpt-4o-mini",
        "input_tokens": 150.9, "output_tokens": 50},
        {"type": "end", "case_id": "c", "success": True, "business_value": 0.0}])
    s = t.attempts[0]["steps"][0]
    return "step in=%r out=%r" % (s["in"], s["out"])

def p12():
    # retry=False(bool) with branch: does reason "False" + branch "False" appear?
    l = load([span(attrs={**MODEL, "averth.retry": False, "averth.branch": False})])
    a = l["attempts"][0]
    return "retries=%d events=%s" % (a["retries"], a["events"])

def p13():
    # success override True then explicit False: last wins?
    l = load([
        span(trace="t1", span_id="a", attrs={**MODEL, "averth.success": "true"},
             startTimeUnixNano="1000000000", endTimeUnixNano="1100000000"),
        span(trace="t1", span_id="b", attrs={**MODEL, "averth.success": "false"},
             startTimeUnixNano="1200000000", endTimeUnixNano="1300000000"),
    ])
    return "success=%s (last-wins?)" % l["attempts"][0]["success"]

def p14():
    # dual span: model + branch-scoped retry -> is the span's own call tainted?
    l = load([span(attrs={**MODEL, "averth.retry": "bad branch",
                           "averth.branch": "b"})])
    a = l["attempts"][0]
    return ("terminal=%.6f retry_path=%.6f (docstring: own call NOT tainted?)"
            % (a["terminal_model_cost"], a["retry_path_cost"]))

def p15():
    # dual span: model + GLOBAL retry -> own call stands (M2b)?
    l = load([span(attrs={**MODEL, "averth.retry": "redo"})])
    a = l["attempts"][0]
    return ("terminal=%.6f retry_path=%.6f (M2b: own call stands -> terminal>0)"
            % (a["terminal_model_cost"], a["retry_path_cost"]))

def p16():
    # status code numeric 2 (proto enum) -> not treated as error; ok
    l = load([span(attrs=MODEL, )])
    s = span(attrs=MODEL); s["status"] = {"code": 2}
    l = load([s])
    return "success=%s (numeric code 2 ignored)" % l["attempts"][0]["success"]

def p17():
    # _parse_bool direct: whitespace / case variants
    from averth.importers.otel import _parse_bool as pb
    vals = ["false", "False", "FALSE", " false ", "0", "no", "N", "f",
            "true", "True", "1", "yes", "y", "Y", "t",
            "maybe", "", "2", "00", "off", "on"]
    return {v: pb(v) for v in vals}

def p18():
    # escalation reason non-string (dict) -> str() repr
    l = load([span(attrs={**MODEL, "averth.escalation_minutes": 5,
                           "averth.escalation_reason": {"a": 1}})])
    a = l["attempts"][0]
    return "events=%s" % ([e for e in a["events"] if e[0] == "escalation"],)

def p19():
    # tool span with negative duration (clock skew) -> latency omitted
    s = span(name="tool.x", attrs={"tool.name": "x"},
             startTimeUnixNano="2000000000", endTimeUnixNano="1000000000")
    l = load([s])
    return "tool_latency_ms=%s (want 0.0 default)" % l["attempts"][0]["tool_latency_ms"]

def p20():
    # empty spans list
    return load([])


for tag, fn in sorted([(k, v) for k, v in list(globals().items())
                       if k.startswith("p") and k[1:].isdigit()],
                      key=lambda kv: int(kv[0][1:])):
    show(tag, fn)
