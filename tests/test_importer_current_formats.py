"""Current-format validation for the LangSmith and OTel importers.

These tests lock in compatibility with the export shapes LangSmith and
OpenTelemetry produce today (October 2026):

- LangSmith: run-export JSON list; token usage under
  outputs.llm_output.token_usage, with extra.metadata as fallback.
- OTel: OTLP JSON with gen_ai.* semantic conventions, both the
  attribute-list form ([{"key","value"}]) and the flat-dict form.

If an exporter changes its shape, these tests fail loudly instead of the
importer silently misreading the trace.
"""
import json

from averth.importers import langsmith, otel
from averth.importers.common import tracker_from_ledger


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj))
    return str(p)


def _ls_run(rid, rtype, trace_id, parents, **kw):
    run = {"id": rid, "name": kw.get("name", rid), "run_type": rtype,
           "trace_id": trace_id, "parent_run_ids": parents,
           "start_time": "2026-10-01T10:00:00Z",
           "end_time": "2026-10-01T10:01:00Z", "error": None,
           "serialized": kw.get("serialized", {}),
           "outputs": kw.get("outputs", {}),
           "extra": {"metadata": kw.get("metadata", {})}}
    return run


def test_langsmith_current_shape(tmp_path):
    """Canonical current LangSmith export: usage under
    outputs.llm_output.token_usage, provider in extra.metadata."""
    runs = [
        _ls_run("root", "chain", "trace-1", []),
        _ls_run("llm1", "llm", "trace-1", ["root"],
                name="ChatOpenAI",
                serialized={"kwargs": {"name": "gpt-5.6"}},
                outputs={"llm_output": {"token_usage": {
                    "prompt_tokens": 1500, "completion_tokens": 400,
                    "total_tokens": 1900}}},
                metadata={"ls_provider": "openai"}),
    ]
    ledger = langsmith.load_langsmith(_write(tmp_path, "ls.json", runs))
    p = tracker_from_ledger(ledger).pnl()
    assert p["attempts"] == 1
    assert p["cost_model"] > 0
    assert p["data_quality"]["measured"] == p["cost_model"]
    assert ledger["missing_usage_models"] == []


def test_langsmith_metadata_usage_fallback(tmp_path):
    """Some SDK versions report usage only in extra.metadata."""
    runs = [
        _ls_run("root", "chain", "trace-1", []),
        _ls_run("llm1", "llm", "trace-1", ["root"],
                serialized={"kwargs": {"name": "gpt-5.6"}},
                outputs={},
                metadata={"ls_provider": "openai",
                          "prompt_tokens": 800, "completion_tokens": 200}),
    ]
    ledger = langsmith.load_langsmith(_write(tmp_path, "ls.json", runs))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cost_model"] > 0
    assert ledger["missing_usage_models"] == []


def test_langsmith_no_usage_flagged_unknown(tmp_path):
    """No usage anywhere: $0.00 recorded as unknown, never as free."""
    runs = [
        _ls_run("root", "chain", "trace-1", []),
        _ls_run("llm1", "llm", "trace-1", ["root"],
                serialized={"kwargs": {"name": "gpt-5.6"}},
                outputs={}, metadata={"ls_provider": "openai"}),
    ]
    ledger = langsmith.load_langsmith(_write(tmp_path, "ls.json", runs))
    assert ledger["missing_usage_models"] == ["openai:gpt-5.6"]
    assert ledger["unknown_usage_calls"] == 1
    p = tracker_from_ledger(ledger).pnl()
    assert p["data_quality"]["unknown_calls"] == 1


def _otel_span(trace_id, span_id, name, attrs_list=None, attrs_dict=None,
               status="STATUS_CODE_OK"):
    span = {"traceId": trace_id, "spanId": span_id, "name": name,
            "startTimeUnixNano": "1758000000000000000",
            "endTimeUnixNano": "1758000001000000000",
            "status": {"code": status}}
    if attrs_list is not None:
        span["attributes"] = attrs_list
    else:
        span["attributes"] = attrs_dict or {}
    return span


def _kv(key, svalue=None, ivalue=None):
    if svalue is not None:
        return {"key": key, "value": {"stringValue": svalue}}
    return {"key": key, "value": {"intValue": str(ivalue)}}


def test_otel_attribute_list_shape(tmp_path):
    """OTLP JSON attribute-list form with stable gen_ai conventions."""
    spans = {"spans": [
        _otel_span("t1", "s1", "llm.chat", attrs_list=[
            _kv("gen_ai.request.model", svalue="gpt-5.6"),
            _kv("gen_ai.usage.input_tokens", ivalue=2000),
            _kv("gen_ai.usage.output_tokens", ivalue=500),
        ]),
    ]}
    ledger = otel.load_otel(_write(tmp_path, "otel.json", spans))
    p = tracker_from_ledger(ledger).pnl()
    assert p["attempts"] == 1
    assert p["cost_model"] > 0
    assert p["data_quality"]["measured"] == p["cost_model"]


def test_otel_flat_dict_shape(tmp_path):
    """Some exporters emit attributes as a flat dict, not a list."""
    spans = {"spans": [
        _otel_span("t1", "s1", "llm.chat", attrs_dict={
            "gen_ai.response.model": "gpt-5.6",
            "gen_ai.usage.input_tokens": 2000,
            "gen_ai.usage.output_tokens": 500,
        }),
    ]}
    ledger = otel.load_otel(_write(tmp_path, "otel.json", spans))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cost_model"] > 0


def test_otel_error_status_fails_case(tmp_path):
    spans = {"spans": [
        _otel_span("t1", "s1", "llm.chat", attrs_dict={
            "gen_ai.request.model": "gpt-5.6",
            "gen_ai.usage.input_tokens": 100,
            "gen_ai.usage.output_tokens": 50,
        }, status="ERROR"),
    ]}
    ledger = otel.load_otel(_write(tmp_path, "otel.json", spans))
    p = tracker_from_ledger(ledger).pnl()
    assert p["successes"] == 0
