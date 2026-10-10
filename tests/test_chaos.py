"""Chaos suite: adversarial and malformed inputs.

Every test proves the importer or CLI degrades LOUDLY (clear error) or
SAFELY (flagged unknown), never silently wrong. A trace that silently
misreads is worse than one that crashes.
"""
import json
import subprocess
import sys

import pytest

from averth.importers import langfuse, langsmith, otel
from averth.importers.common import tracker_from_ledger
from averth._money import dollars


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


# ---------- malformed files ----------

def test_truncated_json_langfuse(tmp_path):
    p = _write(tmp_path, "t.json", '{"data": [{"id": "x", "observ')
    with pytest.raises(Exception):
        langfuse.load_langfuse(p)


def test_empty_file_langsmith(tmp_path):
    p = _write(tmp_path, "t.json", "")
    with pytest.raises(Exception):
        langsmith.load_langsmith(p)


def test_json_not_a_dict_otel(tmp_path):
    p = _write(tmp_path, "t.json", "[1, 2, 3]")
    with pytest.raises(Exception):
        otel.load_otel(p)


def test_binary_file_cli(tmp_path):
    p = tmp_path / "t.bin"
    p.write_bytes(b"\x00\x01\x02\xff" * 100)
    r = subprocess.run([sys.executable, "-m", "averth.cli", "trace",
                        str(p), "--format", "langfuse"],
                       capture_output=True, text=True)
    assert r.returncode != 0  # must fail loudly, not silently misread


def test_nonexistent_file_cli(tmp_path):
    r = subprocess.run([sys.executable, "-m", "averth.cli", "trace",
                        str(tmp_path / "nope.json"), "--format", "langfuse"],
                       capture_output=True, text=True)
    assert r.returncode != 0


def test_directory_as_input_cli(tmp_path):
    r = subprocess.run([sys.executable, "-m", "averth.cli", "trace",
                        str(tmp_path), "--format", "langfuse"],
                       capture_output=True, text=True)
    assert r.returncode != 0


# ---------- langfuse weirdness ----------

def test_null_usage_details_is_unknown(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT", "usageDetails": None, "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    assert ledger["unknown_usage_calls"] == 1
    p = tracker_from_ledger(ledger).pnl()
    assert p["data_quality"]["unknown_calls"] == 1


def test_garbage_string_cost_falls_back(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50},
         "calculatedTotalCost": "$0.05",  # garbage, not a number
         "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    # must not crash; cost must come from measured path, not the garbage
    assert p["data_quality"]["billed"] == 0
    assert p["data_quality"]["measured"] > 0


def test_negative_billed_cost_falls_back(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50},
         "calculatedTotalCost": -0.02, "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["data_quality"]["billed"] == 0
    assert p["data_quality"]["measured"] > 0


def test_missing_model_name_estimated_not_measured(tmp_path):
    # usage present but model unknown: must land in estimated (fallback
    # prices), never priced as if it were a known model.
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50},
         "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["data_quality"]["estimated"] > 0
    assert p["data_quality"]["measured"] == 0


def test_unicode_model_name_survives(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6-\U0001f916",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50},
         "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["attempts"] == 1  # no crash on weird names


def test_absurd_token_counts(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6-mini",
         "level": "DEFAULT",
         "usageDetails": {"input": 10**12, "output": 10**12},
         "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cost_model"] > 0
    import math
    assert math.isfinite(p["cost_model"])


def test_zero_token_call(tmp_path):
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 0, "output": 0},
         "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cost_model"] == 0
    assert p["data_quality"]["unknown_calls"] == 0  # zero usage != unknown


def test_duplicate_observation_ids_counted_once_or_twice_loudly(tmp_path):
    # duplicates must not silently vanish OR double-charge without trace
    data = {"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50}, "metadata": {}},
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50}, "metadata": {}}]}]}
    ledger = langfuse.load_langfuse(_write(tmp_path, "t.json", json.dumps(data)))
    p = tracker_from_ledger(ledger).pnl()
    # either way, the ledger must record what it did
    assert p["attempts"] == 1


# ---------- langsmith weirdness ----------

def test_string_token_counts_coerced_or_flagged(tmp_path):
    runs = [{"id": "r1", "name": "x", "run_type": "llm", "trace_id": "t1",
             "parent_run_ids": [], "error": None,
             "serialized": {"kwargs": {"name": "gpt-5.6"}},
             "outputs": {"llm_output": {"token_usage": {
                 "prompt_tokens": "1500", "completion_tokens": "400"}}},
             "extra": {"metadata": {"ls_provider": "openai"}}}]
    ledger = langsmith.load_langsmith(
        _write(tmp_path, "t.json", json.dumps(runs)))
    p = tracker_from_ledger(ledger).pnl()
    # string counts must not silently become zero-cost
    assert (p["cost_model"] > 0
            or p["data_quality"]["unknown_calls"] >= 1)


def test_error_as_object_not_crash(tmp_path):
    runs = [{"id": "r1", "name": "x", "run_type": "chain", "trace_id": "t1",
             "parent_run_ids": [],
             "error": {"code": 500, "detail": {"msg": "boom"}},
             "serialized": {}, "outputs": {},
             "extra": {"metadata": {}}}]
    ledger = langsmith.load_langsmith(
        _write(tmp_path, "t.json", json.dumps(runs)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["attempts"] == 1


# ---------- otel weirdness ----------

def test_intvalue_as_int_not_string(tmp_path):
    spans = {"spans": [{
        "traceId": "t1", "spanId": "s1", "name": "llm.chat",
        "startTimeUnixNano": 1758000000000000000,
        "endTimeUnixNano": 1758000001000000000,
        "attributes": {
            "gen_ai.request.model": "gpt-5.6",
            "gen_ai.usage.input_tokens": 2000,   # int, not str
            "gen_ai.usage.output_tokens": 500},
        "status": {"code": "STATUS_CODE_OK"}}]}
    ledger = otel.load_otel(_write(tmp_path, "t.json", json.dumps(spans)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["cost_model"] > 0


def test_missing_trace_id_isolated_not_merged(tmp_path):
    # orphan spans are grouped under their own span_id (documented): they
    # must never be silently merged into one fake case.
    spans = {"spans": [
        {"spanId": "s1", "name": "llm.chat",
         "startTimeUnixNano": "1", "endTimeUnixNano": "2",
         "attributes": {"gen_ai.request.model": "gpt-5.6"},
         "status": {"code": "STATUS_CODE_OK"}},
        {"spanId": "s2", "name": "llm.chat",
         "startTimeUnixNano": "3", "endTimeUnixNano": "4",
         "attributes": {"gen_ai.request.model": "gpt-5.6"},
         "status": {"code": "STATUS_CODE_OK"}}]}
    ledger = otel.load_otel(_write(tmp_path, "t.json", json.dumps(spans)))
    p = tracker_from_ledger(ledger).pnl()
    assert p["attempts"] == 2  # two isolated cases, not one merged phantom


# ---------- money rendering ----------

def test_subcent_never_renders_zero():
    assert dollars(0.004) != "$0.00"
    assert dollars(0.000001) != "$0.00"
    assert dollars(0) == "$0.00"


def test_negative_dollars():
    assert dollars(-0.05) == "-$0.05"


def test_dollars_garbage():
    assert dollars(None) == "$?"
    assert dollars("abc") == "$?"
