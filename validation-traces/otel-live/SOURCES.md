# Provenance

Both trace files in this directory were generated live on 2026-09-30 by
`gen_otel_live.py`, run with:

    ~/workspace/.venvs-otel-validation/bin/python gen_otel_live.py

The script drives the real OpenTelemetry Python SDK (`opentelemetry-sdk`):
every span is a genuine SDK span with real nanosecond timestamps and real
durations. Nothing is synthetic:

* LLM-call spans do real `time.sleep()` calls to give inference-latency shape.
* Tool-call spans perform real public read-only HTTP calls (no credentials):
  `https://httpbin.org/get`, `https://httpbin.org/delay/1`.
* The failing tool spans raise a REAL `ConnectionRefusedError` (connecting to
  `http://127.0.0.1:9/refund`), recorded on the span with
  `span.record_exception()` and `StatusCode.ERROR`.
* Parallel branches run in real threads via `ThreadPoolExecutor` with explicit
  OTel context propagation.
* Spans are serialized by a custom `SpanExporter` to the OTLP JSON field
  naming the importer consumes (`traceId`, `spanId`, `startTimeUnixNano`,
  `endTimeUnixNano`, attribute lists, `STATUS_CODE_*` statuses), matching
  `tests/fixtures/otel_spans.json`.

One deliberate edge case: the exporter drops `endTimeUnixNano` for the span
carrying the private attribute `agentpnl.test.drop_end_ts` (stripped before
emission), to exercise the importer's missing-timestamp path. That attribute
is a generation-time test hook, not hand-fixing of the trace content.

Both files were fed to the CLI exactly as written, with zero hand-fixing:

    python3 -m agentpnl.cli trace trace-a-sequential-retry.json --format otel
    python3 -m agentpnl.cli trace trace-b-parallel-fanout.json --format otel
