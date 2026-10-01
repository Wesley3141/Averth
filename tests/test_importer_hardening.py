"""Importer hardening: cached-token and branch fields survive every
importer (OTel attributes, LangSmith metadata, strict JSONL schema), and
the strict schema rejects cached>input while accepting branch."""

import json
import os
import tempfile

import pytest

from averth.importers import otel, langsmith, jsonl
from averth.importers.common import tracker_from_ledger


def _tmp(data):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def _span(name, trace_id, attrs):
    return {"name": name, "traceId": trace_id,
            "attributes": dict(attrs)}


def test_otel_cache_read_tokens_and_branch():
    spans = [
        _span("llm", "t1", {"gen_ai.request.model": "claude-sonnet-4-5",
                            "gen_ai.usage.input_tokens": 4000,
                            "gen_ai.usage.output_tokens": 100,
                            "gen_ai.usage.cache_read_input_tokens": 1000,
                            "averth.branch": "research",
                            "averth.case_id": "C-1"}),
        _span("retry", "t1", {"averth.retry": "junk branch",
                              "averth.case_id": "C-1"}),
        _span("llm", "t1", {"gen_ai.request.model": "claude-sonnet-4-5",
                            "gen_ai.usage.input_tokens": 4000,
                            "gen_ai.usage.output_tokens": 100,
                            "averth.branch": "billing",
                            "averth.case_id": "C-1"}),
    ]
    path = _tmp(spans)
    try:
        ledger = otel.load_otel(path)
    finally:
        os.unlink(path)
    p = tracker_from_ledger(ledger).pnl()
    assert p["cached_tokens"] == 1000
    # global retry (no branch on retry span) marks the later model step waste
    assert p["yield_ratio"] == pytest.approx(0.5)


def test_otel_branch_scoped_retry_on_span():
    spans = [
        _span("llm", "t1", {"gen_ai.request.model": "gpt-5-nano",
                            "gen_ai.usage.input_tokens": 1000,
                            "gen_ai.usage.output_tokens": 100,
                            "averth.branch": "a",
                            "averth.case_id": "C-1"}),
        _span("retry", "t1", {"averth.retry": "a junk",
                              "averth.branch": "a",
                              "averth.case_id": "C-1"}),
        _span("llm", "t1", {"gen_ai.request.model": "gpt-5-nano",
                            "gen_ai.usage.input_tokens": 1000,
                            "gen_ai.usage.output_tokens": 100,
                            "averth.branch": "a",
                            "averth.case_id": "C-1"}),
        _span("llm", "t1", {"gen_ai.request.model": "gpt-5-nano",
                            "gen_ai.usage.input_tokens": 1000,
                            "gen_ai.usage.output_tokens": 100,
                            "averth.branch": "b",
                            "averth.case_id": "C-1"}),
    ]
    path = _tmp(spans)
    try:
        ledger = otel.load_otel(path)
    finally:
        os.unlink(path)
    p = tracker_from_ledger(ledger).pnl()
    # branch retry is retroactive for the pre-retry step; the post-retry
    # redo on the same branch starts fresh (1100 of 3300 tokens waste)
    assert p["yield_ratio"] == pytest.approx(1 - 1100 / 3300)


def _ls_run(run_id, **extra_meta):
    return {"id": run_id, "name": "llm", "run_type": "llm",
            "trace_id": "trace-1",
            "outputs": {"llm_output": {"token_usage":
                                       {"prompt_tokens": 4000,
                                        "completion_tokens": 100}}},
            "extra": {"metadata": dict(extra_meta)}}


def test_langsmith_cached_and_branch_from_metadata():
    run = _ls_run("r1", case_id="C-1", model="gpt-5-nano",
                  averth_cached_input_tokens=800,
                  averth_branch="planner")
    path = _tmp([run])
    try:
        ledger = langsmith.load_langsmith(path)
    finally:
        os.unlink(path)
    p = tracker_from_ledger(ledger).pnl()
    assert p["cached_tokens"] == 800


def _jsonl_text(lines):
    return "\n".join(json.dumps(l) for l in lines)


def _loads_jsonl(text):
    """Parse JSONL text via a temp file (jsonl importer is path-based)."""
    import tempfile
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write(text)
    f.close()
    try:
        return jsonl.load_jsonl(f.name)
    finally:
        os.unlink(f.name)


def test_jsonl_accepts_branch_and_cached():
    ledger = _loads_jsonl(_jsonl_text([
        {"type": "start", "case_id": "C-1"},
        {"type": "model", "case_id": "C-1", "model": "gpt-5-nano",
         "input_tokens": 2000, "output_tokens": 50,
         "cached_input_tokens": 500, "branch": "x"},
        {"type": "end", "case_id": "C-1", "success": True},
    ]))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cached_tokens"] == 500
    assert p["cache_savings"] > 0


def test_jsonl_rejects_cached_exceeding_input():
    with pytest.raises(ValueError, match="cached_input_tokens"):
        _loads_jsonl(_jsonl_text([
            {"type": "start", "case_id": "C-1"},
            {"type": "model", "case_id": "C-1", "model": "gpt-5-nano",
             "input_tokens": 100, "output_tokens": 50,
             "cached_input_tokens": 5000},
            {"type": "end", "case_id": "C-1", "success": True},
        ]))


def test_jsonl_rejects_negative_cached():
    with pytest.raises(ValueError, match="cached_input_tokens"):
        _loads_jsonl(_jsonl_text([
            {"type": "start", "case_id": "C-1"},
            {"type": "model", "case_id": "C-1", "model": "gpt-5-nano",
             "input_tokens": 100, "output_tokens": 50,
             "cached_input_tokens": -3},
            {"type": "end", "case_id": "C-1", "success": True},
        ]))
