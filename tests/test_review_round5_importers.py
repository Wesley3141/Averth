"""Regression tests for review-pass-2 round-5 importer findings.

One focused test per numbered fix:
  OTel  (otel.py):        H1, H2, H3, H4, M1, M6
  LangSmith (langsmith):  C-LS1, H-LS1, H-LS2, H-LS3, M-LS6
  JSONL (jsonl.py):       H1, H2
  common.py:              missing_usage_models ledger round-trip,
                          LEDGER_ATTEMPT_KEYS single source of truth
"""

import json
import os
import tempfile

import pytest

from averth import policy
from averth.importers import common, otel, langsmith, jsonl
from averth.importers.common import (_parse_bool_tristate,
                                     ledger_from_tracker, tracker_from_ledger)
from averth.tracker import Tracker


def _tmp_json(data):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def _otel_span(name, trace_id, attrs, start_ns=1_000_000_000):
    return {"name": name, "traceId": trace_id, "attributes": dict(attrs),
            "startTimeUnixNano": start_ns,
            "endTimeUnixNano": start_ns + 1_000_000_000}


def _otel_ledger(spans):
    path = _tmp_json(spans)
    try:
        return otel.load_otel(path)
    finally:
        os.unlink(path)


def _model_attrs(**kw):
    base = {"gen_ai.request.model": "gpt-5-nano",
            "gen_ai.usage.input_tokens": 1000,
            "gen_ai.usage.output_tokens": 100}
    base.update(kw)
    return base


def _ls_run(rid, trace_id, run_type="llm", name="ChatOpenAI",
            start_time="2026-09-30T10:00:00.000000Z", error=None,
            parent_run_ids=None, meta=None, outputs=None):
    run = {"id": rid, "trace_id": trace_id, "run_type": run_type,
           "name": name, "start_time": start_time, "error": error,
           "parent_run_ids": parent_run_ids or [],
           "serialized": {"kwargs": {"name": "gpt-5-nano"}},
           "outputs": outputs or {},
           "extra": {"metadata": meta or {}}}
    return run


def _langsmith_ledger(runs):
    path = _tmp_json(runs)
    try:
        return langsmith.load_langsmith(path)
    finally:
        os.unlink(path)


# ---------- shared helper ----------

def test_parse_bool_tristate():
    assert _parse_bool_tristate(True) is True
    assert _parse_bool_tristate(False) is False
    for s in ("true", "True", "TRUE", " true ", "yes", "YES", "1"):
        assert _parse_bool_tristate(s) is True, s
    for s in ("false", "False", "FALSE", " false ", "no", "NO", "0"):
        assert _parse_bool_tristate(s) is False, s
    for v in (None, "", "maybe", "validation failed", 0, 1, 2.5, [], {}):
        assert _parse_bool_tristate(v) is None, v


# ---------- OTel ----------

def test_otel_h1_retry_false_variants_create_no_retry():
    # H1: explicit falsy retry markers ("false", "False", "no", False, 0)
    # must not create a retry event — and must not move terminal spend
    # into the retry path.
    for marker in ("false", "False", "no", False, 0):
        spans = [
            _otel_span("llm", "t1", _model_attrs(**{"averth.retry": marker}),
                       start_ns=1_000_000_000),
            _otel_span("llm", "t1", _model_attrs(), start_ns=2_000_000_000),
        ]
        a = tracker_from_ledger(_otel_ledger(spans)).attempts[0]
        assert a["retries"] == 0, marker
        assert a["retry_path_cost"] == 0, marker
        # both calls stay terminal: 2 x (1000*0.05 + 100*0.4)/1e6
        assert a["terminal_model_cost"] == pytest.approx(0.00018), marker


def test_otel_h1_retry_true_and_reason_still_create_event():
    spans = [
        _otel_span("llm", "t1", _model_attrs(), start_ns=1_000_000_000),
        _otel_span("retry", "t1", {"averth.retry": "true"},
                   start_ns=2_000_000_000),
        _otel_span("retry2", "t1", {"averth.retry": "validation failed"},
                   start_ns=3_000_000_000),
    ]
    p = tracker_from_ledger(_otel_ledger(spans)).pnl()
    assert p["attempts"] == 1
    assert tracker_from_ledger(_otel_ledger(spans)).attempts[0]["retries"] == 2


def test_otel_h2_garbage_success_does_not_clobber_explicit_false():
    # H2: unparseable averth.success ("maybe" -> None) must not overwrite
    # the earlier explicit "false".
    spans = [
        _otel_span("llm", "t1", _model_attrs(**{"averth.success": "false"}),
                   start_ns=1_000_000_000),
        _otel_span("llm", "t1", _model_attrs(**{"averth.success": "maybe"}),
                   start_ns=2_000_000_000),
    ]
    p = tracker_from_ledger(_otel_ledger(spans)).pnl()
    assert p["attempts"] == 1
    assert p["successes"] == 0


def test_otel_h3_garbage_business_value_keeps_explicit_value():
    # H3: garbage business_value must not reset an explicit $5.00 to $0.00.
    spans = [
        _otel_span("llm", "t1", _model_attrs(**{"averth.business_value": 5.0}),
                   start_ns=1_000_000_000),
        _otel_span("llm", "t1", _model_attrs(**{"averth.business_value": "abc"}),
                   start_ns=2_000_000_000),
    ]
    p = tracker_from_ledger(_otel_ledger(spans)).pnl()
    assert p["business_value"] == pytest.approx(5.0)


def test_otel_h4_non_scalar_token_attribute_raises_naming_it():
    # H4: a list where a token count belongs must fail loud, naming the
    # attribute — never silently zero $1.00 of spend.
    spans = [_otel_span("llm", "t1",
                        _model_attrs(**{"gen_ai.usage.input_tokens": [1000000]}))]
    with pytest.raises(ValueError, match="gen_ai.usage.input_tokens"):
        _otel_ledger(spans)


def test_otel_h4_numeric_string_tokens_still_parse():
    # OTLP intValue-as-string dialect must keep working.
    spans = [_otel_span("llm", "t1",
                        _model_attrs(**{"gen_ai.usage.input_tokens": "1500"}))]
    a = tracker_from_ledger(_otel_ledger(spans)).attempts[0]
    assert a["total_tokens"] == 1600


def test_otel_m1_falsy_escalation_minutes_creates_no_event():
    # M1: falsy escalation markers must not fabricate a human-escalation
    # event; only positive finite minutes emit one.
    for marker in ("false", False, 0, "0", -3):
        spans = [_otel_span("llm", "t1",
                            _model_attrs(**{"averth.escalation_minutes": marker}))]
        a = tracker_from_ledger(_otel_ledger(spans)).attempts[0]
        assert a["human_min"] == 0, marker
        assert not [e for e in a["events"] if e[0] == "escalation"], marker
    spans = [_otel_span("llm", "t1",
                        _model_attrs(**{"averth.escalation_minutes": 4.5}))]
    a = tracker_from_ledger(_otel_ledger(spans)).attempts[0]
    assert a["human_min"] == pytest.approx(4.5)


def test_otel_m6_branch_false_means_no_branch():
    # M6: False/None/"" must not become the literal branch name "False".
    # Observable end-to-end: with the bug, model and retry spans both get
    # branch "False", so the retry is branch-scoped and retro-marks the
    # model step as waste. Fixed, the retry is global (forward-only):
    # past work stands, no "False" string appears in any event.
    spans = [
        _otel_span("llm", "t1", _model_attrs(**{"averth.branch": False}),
                   start_ns=1_000_000_000),
        _otel_span("retry", "t1", {"averth.retry": "true",
                                   "averth.branch": False},
                   start_ns=2_000_000_000),
    ]
    a = tracker_from_ledger(_otel_ledger(spans)).attempts[0]
    assert a["retries"] == 1
    assert a["retry_path_cost"] == 0
    assert a["terminal_model_cost"] == pytest.approx(0.00009)
    for e in a["events"]:
        assert "False" not in e


# ---------- LangSmith ----------

def test_langsmith_c_ls1_mixed_tz_timestamps_do_not_crash():
    # C-LS1: tz-aware, naive, and missing start_time in one case must not
    # raise TypeError; missing timestamps sort first (tz-aware min).
    runs = [
        _ls_run("r1", "t1", start_time="2026-09-30T10:00:05.000000Z"),
        _ls_run("r2", "t1", start_time="2026-09-30T10:00:06"),
        _ls_run("r3", "t1", start_time=None),
    ]
    p = tracker_from_ledger(_langsmith_ledger(runs)).pnl()
    assert p["attempts"] == 1


def test_langsmith_h_ls1_missing_usage_flagged_not_silent_zero():
    # H-LS1: a priced model with no token usage must land in
    # tracker.missing_usage instead of a silent $0.00.
    run = _ls_run("r1", "t1", meta={"ls_provider": "openai"})
    ledger = _langsmith_ledger([run])
    assert ledger["missing_usage_models"] == ["openai:gpt-5-nano"]
    t = tracker_from_ledger(ledger)
    assert t.missing_usage == {"openai:gpt-5-nano"}
    assert t.pnl()["missing_usage_models"] == ["openai:gpt-5-nano"]
    assert t.pnl()["cost_total"] == 0


def test_langsmith_h_ls1_explicit_zero_usage_is_not_missing():
    # An explicit 0-token report is measured zero, not missing data.
    run = _ls_run("r1", "t1", meta={"ls_provider": "openai"},
                  outputs={"llm_output": {"token_usage":
                                           {"prompt_tokens": 0,
                                            "completion_tokens": 0}}})
    ledger = _langsmith_ledger([run])
    assert ledger["missing_usage_models"] == []


def test_langsmith_h_ls2_business_value_only_from_root_run():
    # H-LS2: per the docstring, business_value is read from the root chain
    # only — a non-root run's value is ignored.
    root = _ls_run("root", "t1", run_type="chain", name="agent",
                   start_time="2026-09-30T10:00:00.000000Z",
                   meta={"averth_business_value": 50})
    llm = _ls_run("r1", "t1", start_time="2026-09-30T10:00:05.000000Z",
                  parent_run_ids=["root"],
                  meta={"averth_business_value": 999},
                  outputs={"llm_output": {"token_usage":
                                           {"prompt_tokens": 10,
                                            "completion_tokens": 5}}})
    p = tracker_from_ledger(_langsmith_ledger([root, llm])).pnl()
    assert p["business_value"] == pytest.approx(50.0)

    # no root value at all -> non-root value ignored, stays 0.0
    root2 = _ls_run("root", "t2", run_type="chain", name="agent",
                    start_time="2026-09-30T10:00:00.000000Z")
    llm2 = _ls_run("r1", "t2", start_time="2026-09-30T10:00:05.000000Z",
                   parent_run_ids=["root"],
                   meta={"averth_business_value": 999})
    p2 = tracker_from_ledger(_langsmith_ledger([root2, llm2])).pnl()
    assert p2["business_value"] == pytest.approx(0.0)


def test_langsmith_h_ls3_error_then_clean_is_recovered():
    # H-LS3: an errored run followed by a clean run is recovered
    # (success=True); a case whose LAST run errored is a failure.
    recovered = [
        _ls_run("r1", "t1", start_time="2026-09-30T10:00:00.000000Z",
                error="rate limit, retried"),
        _ls_run("r2", "t1", start_time="2026-09-30T10:00:05.000000Z"),
    ]
    still_failed = [
        _ls_run("r1", "t2", start_time="2026-09-30T10:00:00.000000Z"),
        _ls_run("r2", "t2", start_time="2026-09-30T10:00:05.000000Z",
                error="timeout"),
    ]
    t = tracker_from_ledger(_langsmith_ledger(recovered + still_failed))
    by_case = {a["case_id"]: a for a in t.attempts}
    assert by_case["t1"]["success"] is True
    assert by_case["t2"]["success"] is False


def test_langsmith_m_ls6_retry_false_variants_create_no_retry():
    # M-LS6: explicit falsy averth_retry markers mean "not a retry".
    for marker in (False, 0, "false", "no", "0", ""):
        run = _ls_run("r1", "t1", run_type="tool", name="lookup",
                      meta={"averth_retry": marker})
        t = tracker_from_ledger(_langsmith_ledger([run]))
        assert t.attempts[0]["retries"] == 0, marker
    # ...while true-ish values and free-text reasons still emit the event.
    for marker in (True, "true", "yes", "1", "no results returned"):
        run = _ls_run("r1", "t1", run_type="tool", name="lookup",
                      meta={"averth_retry": marker})
        t = tracker_from_ledger(_langsmith_ledger([run]))
        assert t.attempts[0]["retries"] == 1, marker


# ---------- JSONL ----------

def _loads_jsonl(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write(text)
    f.close()
    try:
        return jsonl.load_jsonl(f.name)
    finally:
        os.unlink(f.name)


def test_jsonl_h1_unhashable_type_raises_valueerror_with_line():
    # H1: the documented contract is ValueError naming the line number —
    # a list "type" must not escape as bare TypeError.
    text = ('{"type": "model", "case_id": "x", "model": "m",'
            ' "input_tokens": 1, "output_tokens": 1}\n'
            '{"type": ["model"], "case_id": "x"}\n')
    with pytest.raises(ValueError, match="line 2"):
        _loads_jsonl(text)


def test_jsonl_h2_docstring_documents_branch_on_tool_events():
    # H2: the field-rules docstring must document that tool events accept
    # "branch" (retry-path tool spend attribution).
    assert '"branch" (model, tool, retry events)' in jsonl.__doc__


# ---------- common.py ----------

def test_common_missing_usage_models_round_trip():
    t = Tracker("agent-x")
    t.missing_usage.add("openai:gpt-5-nano")
    t.missing_usage.add("anthropic:claude-x")
    ledger = ledger_from_tracker(t)
    assert ledger["missing_usage_models"] == ["anthropic:claude-x",
                                              "openai:gpt-5-nano"]
    t2 = tracker_from_ledger(ledger)
    assert t2.missing_usage == {"openai:gpt-5-nano", "anthropic:claude-x"}
    # legacy ledgers without the key degrade gracefully
    t3 = tracker_from_ledger({"agent": "agent-x", "attempts": []})
    assert t3.missing_usage == set()


def test_common_ledger_attempt_keys_single_source_of_truth():
    assert common.LEDGER_ATTEMPT_KEYS is policy.LEDGER_ATTEMPT_KEYS


def test_common_malformed_price_vintage_rejected_loudly():
    # A wrong-typed vintage must fail at the rehydrate boundary with a
    # clear ValueError, not later in report_text with an opaque TypeError.
    bad_string = {"agent": "x", "attempts": [],
                  "price_vintage": "2026-01-01"}
    with pytest.raises(ValueError, match="malformed price_vintage"):
        tracker_from_ledger(bad_string)
    bad_keys = {"agent": "x", "attempts": [],
                "price_vintage": {"version": 2}}
    with pytest.raises(ValueError, match="missing key"):
        tracker_from_ledger(bad_keys)


def test_common_vintage_absent_or_none_still_degrades_gracefully():
    # Legacy ledgers: absent or None vintage means "vintage unknown",
    # not an error.
    for ledger in ({"agent": "x", "attempts": []},
                   {"agent": "x", "attempts": [], "price_vintage": None}):
        t = tracker_from_ledger(ledger)
        assert t.price_vintage is None
        assert t.pnl()["price_vintage"] is None
