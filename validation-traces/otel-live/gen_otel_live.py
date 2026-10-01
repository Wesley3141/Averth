"""Live OTel trace generator for averth validation (no hand-fixing).

Runs two realistic agent workflows under the real OpenTelemetry SDK and
exports genuine spans (real timestamps, real durations from real HTTP calls
to public read-only endpoints, real recorded exceptions) to OTLP-style JSON
matching the shape averth/importers/otel.py consumes.

Usage:
    ~/workspace/.venvs-otel-validation/bin/python gen_otel_live.py

Writes: trace-a-sequential-retry.json, trace-b-parallel-fanout.json
"""

import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- exporter
def _anyvalue(v):
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    return {"stringValue": str(v)}


class JsonFileExporter(SpanExporter):
    """Serialize SDK spans to the OTLP JSON dialect the importer expects.

    One deliberate edge case: a span carrying the private attribute
    ``averth.test.drop_end_ts`` is emitted WITHOUT endTimeUnixNano, to
    exercise the importer's missing-timestamp path. The private attribute
    itself is stripped from the emitted span.
    """

    def __init__(self):
        self.spans = []
        self._lock = threading.Lock()

    def export(self, spans):
        with self._lock:
            for s in spans:
                ctx = s.get_span_context()
                attrs = dict(s.attributes or {})
                drop_end = attrs.pop("averth.test.drop_end_ts", False)
                out = {
                    "traceId": format(ctx.trace_id, "032x"),
                    "spanId": format(ctx.span_id, "016x"),
                    "name": s.name,
                    "startTimeUnixNano": str(s.start_time),
                    "attributes": [
                        {"key": k, "value": _anyvalue(v)}
                        for k, v in attrs.items()
                    ],
                    "status": {
                        "code": {
                            StatusCode.OK: "STATUS_CODE_OK",
                            StatusCode.ERROR: "STATUS_CODE_ERROR",
                            StatusCode.UNSET: "STATUS_CODE_UNSET",
                        }[s.status.status_code]
                    },
                }
                if not drop_end:
                    out["endTimeUnixNano"] = str(s.end_time)
                self.spans.append(out)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


_exporter = JsonFileExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer("averth.validation", "0.1.0")


# ---------------------------------------------------------------- helpers
def http_get(url, timeout=12):
    """Real public read-only HTTP call (urllib, no credentials)."""
    req = urllib.request.Request(url, headers={"User-Agent": "averth-validation/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(4096)
    return resp.status, len(body)


def llm_span(name, model, in_tok, out_tok, sleep_s=0.4, attrs=None, parent_ctx=None):
    """Child span for one LLM call, using gen_ai.* / llm.* attribute dialects."""
    with tracer.start_as_current_span(name, context=parent_ctx) as span:
        span.set_attribute("gen_ai.system", "averth-validation")
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.usage.input_tokens", in_tok)
        span.set_attribute("gen_ai.usage.output_tokens", out_tok)
        for k, v in (attrs or {}).items():
            span.set_attribute(k, v)
        time.sleep(sleep_s)  # realistic inference-latency shape
        return span.get_span_context().span_id


def llm_span_openinference(name, model, prompt_tok, completion_tok, sleep_s=0.4, parent_ctx=None):
    """LLM call instrumented with the OpenInference llm.token_count.* dialect only."""
    with tracer.start_as_current_span(name, context=parent_ctx) as span:
        span.set_attribute("gen_ai.system", "averth-validation")
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("llm.token_count.prompt", prompt_tok)
        span.set_attribute("llm.token_count.completion", completion_tok)
        time.sleep(sleep_s)


def tool_span(name, tool, url=None, fail=False, parent_ctx=None, extra=None,
              retry_reason=None):
    """Tool-call span. fail=True raises a REAL exception (localhost:9 refused)."""
    with tracer.start_as_current_span(name, context=parent_ctx) as span:
        if tool is not None:
            span.set_attribute("tool.name", tool)
        for k, v in (extra or {}).items():
            span.set_attribute(k, v)
        if fail:
            try:
                http_get("http://127.0.0.1:9/refund", timeout=3)
            except Exception as exc:  # real ConnectionRefusedError
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("averth.retry",
                                   retry_reason or "%s connection refused" % tool)
        else:
            status, nbytes = http_get(url)
            span.set_attribute("http.status_code", status)
            span.set_attribute("http.response_bytes", nbytes)


# ================================================================ trace A
def run_trace_a():
    """Sequential chain: plan -> tool -> draft -> FAILED tool -> retry -> tools -> summary."""
    with tracer.start_as_current_span("agent.run") as parent:
        parent.set_attribute("averth.business_value", 12.50)
        pctx = trace.set_span_in_context(parent)

        llm_span("llm.plan", "claude-sonnet-4-5", 2400, 380, parent_ctx=pctx)
        tool_span("tool.crm_lookup", "crm_lookup",
                  url="https://httpbin.org/get?customer=acct-12345", parent_ctx=pctx)
        llm_span("llm.draft", "claude-sonnet-4-5", 3100, 640, parent_ctx=pctx)

        # escalation: a few minutes of human review inside the run
        with tracer.start_as_current_span("review.human", context=pctx) as esc:
            esc.set_attribute("averth.escalation_minutes", 3)
            esc.set_attribute("averth.escalation_reason", "refund amount above auto-approve limit")
            time.sleep(0.2)

        # the failing tool call: real exception, ERROR status, retry marker
        tool_span("tool.refund_api", "refund_api", fail=True, parent_ctx=pctx)

        # retry path: re-plan with OpenInference token dialect, then succeed
        llm_span_openinference("llm.retry_plan", "claude-sonnet-4-5",
                               2900, 310, parent_ctx=pctx)
        tool_span("tool.refund_api", "refund_api",
                  url="https://httpbin.org/get?fallback=true", parent_ctx=pctx)

        llm_span("llm.summarize", "claude-haiku-4-5", 1200, 210, parent_ctx=pctx)

        # malformed: unpriced model + negative input tokens
        llm_span("llm.audit", "deepseek-v3.2", -500, 150, sleep_s=0.2, parent_ctx=pctx)

        # tool via name prefix only (no tool.name attribute)
        tool_span("tool.webhook", None,
                  url="https://httpbin.org/get?event=refund_issued", parent_ctx=pctx)

        # malformed: usage tokens but no model attribute -> importer skips
        with tracer.start_as_current_span("llm.untracked", context=pctx) as span:
            span.set_attribute("gen_ai.usage.input_tokens", 800)
            span.set_attribute("gen_ai.usage.output_tokens", 120)
            time.sleep(0.1)

        # malformed: exporter drops endTimeUnixNano for this span
        with tracer.start_as_current_span("debug.note", context=pctx) as span:
            span.set_attribute("averth.test.drop_end_ts", True)
            span.set_attribute("note", "cache warm, no action")
            time.sleep(0.1)


# ================================================================ trace B
def _branch(i, name, pctx):
    if i == 0:
        llm_span("branch0.llm", "gpt-5.6-mini", 1800, 260, parent_ctx=pctx)
        tool_span("branch0.tool", "web_search",
                  url="https://httpbin.org/get?q=pricing", parent_ctx=pctx)
    elif i == 1:
        llm_span_openinference("branch1.llm", "gemini-3-flash", 2200, 410, parent_ctx=pctx)
        tool_span("branch1.tool", "crm_lookup",
                  url="https://httpbin.org/delay/1", parent_ctx=pctx)  # slow branch
    elif i == 2:
        llm_span("branch2.llm", "grok-4", 2600, 520, parent_ctx=pctx)
        # fails twice: retry does not recover; the branch stays dead
        tool_span("branch2.tool", "payment_api", fail=True, parent_ctx=pctx)
        llm_span("branch2.llm2", "grok-4", 900, 120, sleep_s=0.2, parent_ctx=pctx)
        tool_span("branch2.tool_retry", "payment_api", fail=True, parent_ctx=pctx,
                  extra={"averth.retry": "payment_api connection refused, second attempt"})
    else:
        # negative-token malformed span on a priced model
        llm_span("branch3.llm", "gpt-5.6-mini", -100, -40, sleep_s=0.2, parent_ctx=pctx)
        tool_span("branch3.tool", "vector_retrieval",
                  url="https://httpbin.org/get?q=embed", parent_ctx=pctx)


def run_trace_b():
    """Parallel fan-out/fan-in: 4 concurrent branches, one dies twice, then a merge LLM."""
    with tracer.start_as_current_span("agent.run") as parent:
        parent.set_attribute("averth.business_value", 25.00)
        pctx = trace.set_span_in_context(parent)
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(_branch, i, n, pctx)
                    for i, n in enumerate(["web", "crm", "pay", "vec"])]
            for f in futs:
                f.result()  # propagate real exceptions if any
        # fan-in merge
        llm_span("llm.merge", "gpt-5.6", 4200, 880, sleep_s=0.5, parent_ctx=pctx)


def main():
    run_trace_a()
    trace_a = {"spans": _exporter.spans}
    _exporter.spans = []
    run_trace_b()
    trace_b = {"spans": _exporter.spans}
    _exporter.spans = []

    pa = os.path.join(HERE, "trace-a-sequential-retry.json")
    pb = os.path.join(HERE, "trace-b-parallel-fanout.json")
    with open(pa, "w") as f:
        json.dump(trace_a, f, indent=2)
    with open(pb, "w") as f:
        json.dump(trace_b, f, indent=2)
    print("wrote %s (%d spans)" % (pa, len(trace_a["spans"])))
    print("wrote %s (%d spans)" % (pb, len(trace_b["spans"])))


if __name__ == "__main__":
    main()
