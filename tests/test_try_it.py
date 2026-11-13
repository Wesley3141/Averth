"""Tests for the one-command try-it (``averth try``).

The fixture trajectory is the public case-study trace
(mini-SWE-agent v1.0.0, django__django-15930). Every number asserted
here is a published case-study number; a mismatch is a defect, not a
rounding note.
"""

import json
import os
import shutil

import pytest

averth = pytest.importorskip("averth")
from averth.cli import main  # noqa: E402
from averth.importers import common, miniswe  # noqa: E402
from averth import try_report  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "try-it", "fixtures")
TRAJ = os.path.join(FIXTURES, "django-15930.traj.json")
EVENTS = os.path.join(FIXTURES, "trace-events-django-15930.jsonl")
CHECKS = os.path.join(FIXTURES, "case-study-1-checks.json")
ALLOWLIST = os.path.join(FIXTURES, "case-study-1-allowlist.json")
LEDGER = os.path.join(REPO, "case-study-1", "v0-run", "evidence_ledger.json")
MODEL = "claude-sonnet-4-20250514"


def _fixture_events():
    with open(EVENTS, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pnl_for_traj():
    ledger = miniswe.load_miniswe(TRAJ, model=MODEL)
    return common.tracker_from_ledger(ledger).pnl()


# --- converter -------------------------------------------------------


def test_converter_reproduces_published_events():
    mine = miniswe.miniswe_events(TRAJ, model=MODEL)
    assert mine == _fixture_events()


def test_converter_model_inferred_from_path(tmp_path):
    named = tmp_path / ("django__django-15930_claude-sonnet-4-20250514"
                        ".traj.json")
    shutil.copy(TRAJ, named)
    assert miniswe.miniswe_events(str(named)) == _fixture_events()


def test_converter_missing_model_is_a_clean_error():
    with pytest.raises(ValueError, match="--model"):
        miniswe.miniswe_events(TRAJ, model=None)


def test_converter_rejects_non_trajectory(tmp_path):
    bad = tmp_path / "nope.json"
    bad.write_text(json.dumps({"data": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a mini-SWE-agent trajectory"):
        miniswe.miniswe_events(str(bad))


def test_converter_rejects_empty_messages(tmp_path):
    bad = tmp_path / "empty.traj.json"
    bad.write_text(json.dumps({"instance_id": "x", "messages": []}),
                   encoding="utf-8")
    with pytest.raises(ValueError, match="no messages"):
        miniswe.miniswe_events(str(bad))


def test_converter_missing_exit_status_is_outcome_unknown():
    traj = json.loads(open(TRAJ, encoding="utf-8").read())
    del traj["info"]["exit_status"]
    # Build events from the modified trajectory via a temp file.
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".traj.json",
                                     delete=False) as f:
        json.dump(traj, f)
        tmp = f.name
    try:
        evs = miniswe.miniswe_events(tmp, model=MODEL)
        assert not [e for e in evs if e["type"] == "end"]
        ledger = miniswe.load_miniswe(tmp, model=MODEL)
        tracker = common.tracker_from_ledger(ledger)
        assert tracker.pnl()["unknown_outcome"] == 1
    finally:
        os.unlink(tmp)


# --- meter numbers ---------------------------------------------------


def test_meter_numbers_match_the_published_case_study():
    p = _pnl_for_traj()
    assert p["attempts"] == 1
    assert p["successes"] == 1
    assert p["retries"] == 0
    assert round(p["cost_total"], 2) == 0.98
    assert round(p["cost_model"], 2) == 0.91
    assert round(p["cost_tools"], 2) == 0.07
    assert p["cost_billed"] == 0.0
    assert round(p["avg_context_growth"], 1) == 9.9
    assert round(p["context_tax"], 2) == 0.68
    dq = p["data_quality"]
    assert round(dq["measured"], 2) == 0.91
    assert round(dq["estimated"], 2) == 0.07
    assert dq["billed"] == 0.0


# --- V0 ledger --------------------------------------------------------


def test_v0_ledger_summary_matches_the_published_case_study():
    summary, verified = try_report.load_v0_ledger(LEDGER, CHECKS)
    assert verified is True
    assert summary["counts"] == {"VERIFIED": 2, "EXTERNAL-UNVERIFIABLE": 2}
    assert summary["unknown"] == 2
    assert summary["unknown_rate"] == 0.5
    assert summary["runs_total"] == 2
    assert summary["superseded_runs_retained"] == 0
    assert [j["status"] for j in summary["judgments"]] == [
        "VERIFIED", "VERIFIED", "EXTERNAL-UNVERIFIABLE",
        "EXTERNAL-UNVERIFIABLE",
    ]
    # Each judgment carries its cited observation.
    assert summary["judgments"][0]["criterion_text"] == (
        "the FAIL_TO_PASS test passes with the agent patch")
    assert "test_annotate_with_full_when" in summary["judgments"][0]["command"]
    assert summary["judgments"][0]["exit_code"] == 0
    assert summary["judgments"][0]["output_digest"].startswith("sha256:")


def test_v0_ledger_without_checks_is_labelled_unverified():
    summary, verified = try_report.load_v0_ledger(LEDGER)
    assert verified is None
    assert summary["counts"]["VERIFIED"] == 2


def test_v0_ledger_digest_mismatch_refuses(tmp_path):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        try_report.load_v0_ledger(LEDGER, str(tampered))


def test_v0_ledger_rejects_non_ledger(tmp_path):
    bad = tmp_path / "ledger.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a V0 evidence ledger"):
        try_report.load_v0_ledger(str(bad))


def test_v0_ledger_rejects_malformed_shapes(tmp_path):
    def _write(obj):
        bad = tmp_path / "ledger.json"
        bad.write_text(json.dumps(obj), encoding="utf-8")
        return str(bad)

    with pytest.raises(ValueError, match="judgments"):
        try_report.load_v0_ledger(_write({"judgments": "oops"}))
    with pytest.raises(ValueError, match="judgments"):
        try_report.load_v0_ledger(_write({"judgments": [42]}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": "two"}}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": "high"}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": True}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": float("nan")}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": float("inf")}}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": float("nan")}}}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": True}}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": "two"}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": True}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": 1.5}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": "two"}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": True}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": 1.5}}))
    with pytest.raises(ValueError, match="runs_total"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "runs_total": "two"}}))
    missing = tmp_path / "nope.json"
    with pytest.raises(ValueError, match="--ledger"):
        try_report.load_v0_ledger(str(missing))
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        try_report.load_v0_ledger(str(bad_json))
    with pytest.raises(ValueError, match="--checks"):
        try_report.load_v0_ledger(LEDGER, str(missing))


# --- report extras ----------------------------------------------------


def test_try_extras_carry_the_published_comparison():
    p = _pnl_for_traj()
    summary, _ = try_report.load_v0_ledger(LEDGER, CHECKS)
    html = try_report.build_try_extras(
        p, recorded=0.3205, v0=summary, digest_verified=True,
        source_note="Trace: django-15930.traj.json (mini-SWE-agent "
        "trajectory). Token counts are characters/4 estimates from the "
        "trajectory text, not provider-recorded usage.")
    assert "3.07x" in html
    assert "$0.3205" in html
    assert "$0.98" in html
    assert "VERIFIED" in html
    assert "50.0%" in html
    assert "Checks digest verified" in html
    assert "no cost per accepted outcome is claimed" in html
    assert "characters/4 estimates" in html
    # Recorded is operator-supplied, never stated as fact.
    assert "operator-supplied" in html
    assert "The operator supplied $0.3205" in html
    # All five verdict rows render, zeros included.
    for verdict in ("VERIFIED", "FAILED", "NOT OBSERVED",
                    "EXTERNAL-UNVERIFIABLE", "NOT APPLICABLE"):
        assert verdict in html
    # V0 rows cite their observations.
    assert "the FAIL_TO_PASS test passes with the agent patch" in html
    assert "test_annotate_with_full_when" in html
    assert "exit 0" in html
    assert "output digest" in html
    assert "sha256:081d" in html
    assert "superseded and retained, never cited: 0" in html
    assert "report generated" in html


def test_try_extras_escape_source_note():
    p = _pnl_for_traj()
    html = try_report.build_try_extras(
        p, source_note='Trace: <img src=x onerror=alert(1)>.traj.json')
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_try_extras_reject_nonpositive_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=0.0)


def test_try_extras_reject_nonfinite_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=float("nan"))
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=float("inf"))


def test_try_extras_recorded_cross_check():
    p = _pnl_for_traj()
    html = try_report.build_try_extras(
        p, recorded=0.3205, traj_recorded=0.32052914999999993)
    assert "agrees with the operator-supplied figure" in html
    html = try_report.build_try_extras(
        p, recorded=99.0, traj_recorded=0.32052914999999993)
    assert "differs from the operator-supplied" in html


def test_try_summary_lines():
    p = _pnl_for_traj()
    summary, verified = try_report.load_v0_ledger(LEDGER, CHECKS)
    lines = try_report.try_summary_lines(
        p, recorded=0.3205, v0=summary, digest_verified=verified,
        source_note="Trace: django-15930.traj.json (mini-SWE-agent "
        "trajectory). Token counts are characters/4 estimates.")
    assert any("3.07x" in line for line in lines)
    assert any("unknown rate 50.0%" in line for line in lines)
    assert any("characters/4 estimates" in line for line in lines)
    assert any("No human accepted this run" in line for line in lines)
    assert any("operator-supplied" in line for line in lines)
    assert any("checks digest verified" in line for line in lines)
    # All five verdicts, zeros included.
    v0_line = [l for l in lines if l.startswith("V0 verdicts:")][0]
    assert "FAILED 0" in v0_line
    assert "NOT OBSERVED 0" in v0_line


def test_try_summary_lines_unverified_digest():
    p = _pnl_for_traj()
    summary, _ = try_report.load_v0_ledger(LEDGER)
    lines = try_report.try_summary_lines(p, v0=summary)
    assert any("checks digest NOT verified" in line for line in lines)


def test_try_summary_lines_traj_recorded_cross_check():
    p = _pnl_for_traj()
    lines = try_report.try_summary_lines(
        p, recorded=0.3205, traj_recorded=0.32052914999999993)
    assert any("agrees with the operator-supplied figure" in line
               for line in lines)
    lines = try_report.try_summary_lines(
        p, recorded=99.0, traj_recorded=0.32052914999999993)
    assert any("WARNING: trajectory's own recorded cost is $0.3205"
               in line for line in lines)


def test_try_summary_lines_reject_bad_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.try_summary_lines(p, recorded=0.0)
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.try_summary_lines(p, recorded=float("nan"))


# --- CLI --------------------------------------------------------------


def test_try_traj_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--recorded", "0.3205",
               "--ledger", LEDGER, "--checks", CHECKS])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Fully loaded:         $0.98" in out
    assert "Retries:               0" in out
    assert "Recorded cost (operator-supplied): $0.3205" in out
    assert "3.07x" in out
    assert "unknown rate 50.0%" in out
    assert "Cost per completed run" in out
    assert "No human accepted this run" in out
    assert "characters/4 estimates" in out
    assert "checks digest verified" in out
    assert "FAILED 0" in out
    html_file = tmp_path / "django-15930-try.html"
    assert html_file.exists()
    html = html_file.read_text(encoding="utf-8")
    assert "Metered estimate vs recorded cost" in html
    assert "What the evidence supports (V0)" in html
    assert "characters/4 estimates" in html
    assert "http" not in html  # self-contained: no external references
    assert "per completed run" in html
    assert '<div class="s">per completed run</div>' in html
    assert "<h2>Cost per completed run</h2>" in html
    assert "operator-supplied" in html
    assert "Cited observation" in html
    assert "test_annotate_with_full_when" in html
    assert "output digest" in html


def test_try_auto_detects_traj_without_format_flag(tmp_path, monkeypatch,
                                                  capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL])
    assert rc == 0
    assert (tmp_path / "django-15930-try.html").exists()


def test_try_jsonl_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", EVENTS, "--format", "jsonl"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Fully loaded:         $0.98" in out
    assert (tmp_path / "trace-events-django-15930-try.html").exists()
    html = (tmp_path / "trace-events-django-15930-try.html").read_text(
        encoding="utf-8")
    # The default cost-basis line never claims reported token usage.
    assert "reported token/cache usage" not in html
    assert "trace-supplied token counts" in html


def test_try_digest_mismatch_writes_no_report(tmp_path, monkeypatch, capsys):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", str(tampered)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "digest mismatch" in err
    assert not (tmp_path / "django-15930-try.html").exists()


def test_try_checks_without_ledger_is_an_error(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--checks", CHECKS])
    assert rc == 2
    assert "--checks needs --ledger" in capsys.readouterr().err


def test_try_missing_model_is_a_clean_error(capsys):
    rc = main(["try", TRAJ])
    assert rc == 2
    assert "--model" in capsys.readouterr().err


def test_try_missing_file_is_an_error(capsys):
    rc = main(["try", "/no/such/trace.traj.json"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_try_bad_recorded_is_an_error(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--recorded", "0"])
    assert rc == 2
    assert "positive dollar figure" in capsys.readouterr().err

# --- model validation ------------------------------------------------


def test_try_unknown_model_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", "gpt-99-nonexistent"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown model 'gpt-99-nonexistent'" in err
    assert "averth pricing" in err
    assert not (tmp_path / "django-15930-try.html").exists()


def test_try_typo_model_is_refused(capsys):
    rc = main(["try", TRAJ, "--model", "claude-sonnet-4-2025051"])
    assert rc == 2
    assert "unknown model" in capsys.readouterr().err


def test_pricing_lists_model_names(capsys):
    rc = main(["pricing"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "models priced : 35" in out
    assert "claude-sonnet-4-20250514" in out
    assert "gpt-4o" in out
    # Each bare name is listed once, even when priced under two keys.
    listed = [line.strip() for line in out.splitlines()
              if line.startswith("    ") and not line.strip().startswith("(")]
    assert len(listed) == len(set(listed))
    assert listed.count("glm-5") == 1


# --- format detection --------------------------------------------------


def test_detect_try_format_single_line_jsonl(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "one.jsonl"
    f.write_text('{"type": "model", "case_id": "x"}', encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"


def test_detect_try_format_skips_typeless_first_line(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "head.jsonl"
    f.write_text('{"note": "header"}\n{"type": "model", "case_id": "x"}\n',
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"


def test_detect_try_format_finds_messages_past_1mib(tmp_path):
    # Same class as the default-checks sniff bug: a trajectory whose
    # leading "info" object pushes "messages" past a fixed prefix
    # must still detect as traj (the old 1 MiB prefix missed it).
    from averth.cli import _detect_try_format

    f = tmp_path / "big.traj.json"
    f.write_text(json.dumps({
        "info": {"padding": "x" * (2 * 1024 * 1024)},
        "messages": [
            {"role": "assistant",
             "content": "```bash\npytest\n```"},
        ]}), encoding="utf-8")
    assert f.stat().st_size > 1024 * 1024
    assert _detect_try_format(str(f)) == "traj"


def test_detect_try_format_rejects_garbage(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "nope.json"
    f.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(ValueError, match="none of the supported shapes"):
        _detect_try_format(str(f))
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="is empty"):
        _detect_try_format(str(empty))
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xd8\xff\x00\x01")
    with pytest.raises(ValueError, match="not readable text"):
        _detect_try_format(str(binary))
    text = tmp_path / "text.txt"
    text.write_text("hello world, this is not json at all",
                    encoding="utf-8")
    with pytest.raises(ValueError, match="mini-SWE-agent trajectory"):
        _detect_try_format(str(text))


def test_detect_try_format_claude_session(tmp_path):
    # R4: a Claude session file must detect as claude, not jsonl.
    from averth.cli import _detect_try_format

    f = tmp_path / "session.jsonl"
    records = [
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "usage": {"input_tokens": 1000,
                               "output_tokens": 500},
                     "content": [{"type": "tool_use", "id": "c1",
                                  "name": "Bash",
                                  "input": {"command": "pytest"}}]}},
        {"type": "user", "sessionId": "s1",
         "message": {"role": "user", "content": [
             {"type": "tool_result", "tool_use_id": "c1",
              "content": "ok", "is_error": False}]}},
    ]
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_claude_session_leading_system_record(
        tmp_path):
    # A session whose first lines are system/summary records (before
    # any assistant record) still detects as claude via the weak
    # marker, never as jsonl.
    from averth.cli import _detect_try_format

    f = tmp_path / "session.jsonl"
    records = [
        {"type": "system", "sessionId": "s1"},
        {"type": "summary", "sessionId": "s1", "summary": "x"},
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "text", "text": "hi"}]}},
    ]
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_claude_session_user_first(tmp_path):
    # A session whose first record is a user record (with a
    # message.content list) detects as claude at once.
    from averth.cli import _detect_try_format

    f = tmp_path / "session.jsonl"
    records = [
        {"type": "user", "sessionId": "s1",
         "message": {"role": "user", "content": [
             {"type": "text", "text": "run the tests"}]}},
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "text", "text": "ok"}]}},
    ]
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_codex_rollout(tmp_path):
    # R4: a Codex rollout file must detect as codex, not jsonl.
    from averth.cli import _detect_try_format

    f = tmp_path / "rollout.jsonl"
    records = [
        {"type": "session_meta",
         "payload": {"id": "codex-1", "cwd": "/tmp/shop",
                     "cli_version": "0.130.0",
                     "model_provider": "openai", "source": "cli"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps({"command": "pytest"})}},
    ]
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "codex"


def test_detect_try_format_codex_rollout_metadata_only(tmp_path):
    # A rollout with only metadata records in its first lines (no
    # response_item yet) still detects as codex via the weak marker.
    from averth.cli import _detect_try_format

    f = tmp_path / "rollout.jsonl"
    f.write_text(
        '{"type": "session_meta", "payload": {"id": "codex-1", '
        '"source": "cli"}}\n'
        '{"type": "turn_context", "payload": {"model": "gpt-5.2"}}\n'
        '{"type": "event_msg", "payload": {"type": "token_count", '
        '"info": {"total_token_usage": {"input_tokens": 100, '
        '"output_tokens": 10}}}}\n',
        encoding="utf-8")
    assert _detect_try_format(str(f)) == "codex"


def test_detect_try_format_unhashable_type_is_a_clean_error(
        tmp_path, monkeypatch, capsys):
    # R4 rework: a record whose "type" is a list must never raise
    # TypeError: it decides nothing, and the file is refused with a
    # clean error instead of a traceback.
    from averth.cli import _detect_try_format

    f = tmp_path / "bad.jsonl"
    f.write_text(json.dumps({"type": ["model"], "case_id": "x"})
                 + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="none of the supported"):
        _detect_try_format(str(f))
    monkeypatch.chdir(tmp_path)
    rc = main(["try", str(f)])
    err = capsys.readouterr().err
    assert rc == 2
    assert err.startswith("averth: error:")
    assert "Traceback" not in err
    # Mixed with valid JSONL, the bad record is skipped and the
    # file still detects as jsonl.
    records = [
        {"type": ["model"], "case_id": "x"},
        {"type": "start", "case_id": "c1"},
        {"type": "model", "case_id": "c1",
         "model": "claude-sonnet-4-20250514",
         "input_tokens": 100, "output_tokens": 10},
        {"type": "end", "case_id": "c1", "success": True},
    ]
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"


def test_detect_try_format_mixed_claude_and_jsonl_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    # R4 rework regression: a stray Claude assistant record followed
    # by valid Averth JSONL must not silently detect as claude and
    # report $0.00 — the file mixes shapes, so detection refuses.
    from averth.cli import _detect_try_format

    records = [
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "usage": {"input_tokens": 1000,
                               "output_tokens": 500},
                     "content": [{"type": "text", "text": "hi"}]}},
        {"type": "start", "case_id": "ctrl-1"},
        {"type": "model", "case_id": "ctrl-1",
         "model": "claude-sonnet-4-20250514",
         "input_tokens": 5000, "output_tokens": 1000},
        {"type": "end", "case_id": "ctrl-1", "success": True},
    ]
    f = tmp_path / "mixed.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous"):
        _detect_try_format(str(f))
    monkeypatch.chdir(tmp_path)
    rc = main(["try", str(f)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "ambiguous" in err


def test_try_pure_jsonl_control_meters_three_cents(
        tmp_path, monkeypatch, capsys):
    # Control for the mixed-format regression: the same JSONL
    # records without the stray assistant record meter $0.03
    # (5000 in / 1000 out tokens on claude-sonnet-4-20250514).
    monkeypatch.chdir(tmp_path)
    records = [
        {"type": "start", "case_id": "ctrl-1"},
        {"type": "model", "case_id": "ctrl-1",
         "model": "claude-sonnet-4-20250514",
         "input_tokens": 5000, "output_tokens": 1000},
        {"type": "end", "case_id": "ctrl-1", "success": True},
    ]
    f = tmp_path / "ctrl.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    rc = main(["try", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Fully loaded: $0.03" in " ".join(out.split())


def test_detect_try_format_weak_marker_conflict_is_ambiguous(tmp_path):
    # Decisive weak markers from both sides, in either order:
    # ambiguous, never first-weak-wins.
    from averth.cli import _detect_try_format

    claude_weak = [
        {"type": "system", "sessionId": "s1"},
        {"type": "summary", "sessionId": "s1", "summary": "x"},
    ]
    codex_weak = [
        {"type": "session_meta", "payload": {"id": "c1"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
    ]
    for records in (claude_weak + codex_weak,
                    codex_weak + claude_weak):
        f = tmp_path / "conflict.jsonl"
        f.write_text("\n".join(json.dumps(r) for r in records),
                     encoding="utf-8")
        with pytest.raises(ValueError, match="ambiguous"):
            _detect_try_format(str(f))


def test_detect_try_format_weak_marker_then_strong_at_line_11(
        tmp_path):
    # Ten weak Claude records, then a Codex response_item at line
    # 11: the extended scan finds the strong marker and Codex wins.
    from averth.cli import _detect_try_format

    records = [{"type": "system", "sessionId": "s1", "n": i}
               for i in range(10)]
    records.append(
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps({"command": "pytest"})}})
    f = tmp_path / "late.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "codex"


def test_detect_try_format_weak_codex_then_strong_claude_at_line_11(
        tmp_path):
    # Mirror case: ten weak Codex records, then a Claude assistant
    # record at line 11: the extended scan finds it and Claude wins.
    from averth.cli import _detect_try_format

    records = [{"type": "session_meta", "payload": {"id": "c%d" % i}}
               for i in range(10)]
    records.append(
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "text", "text": "hi"}]}})
    f = tmp_path / "late.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in records),
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_single_weak_record_files(tmp_path):
    # One generic weak record alone decides nothing; one bare
    # assistant/user record (no message.content list) decides alone.
    from averth.cli import _detect_try_format

    for rtype in ("system", "session_meta"):
        f = tmp_path / "one.jsonl"
        f.write_text(json.dumps({"type": rtype}) + "\n",
                     encoding="utf-8")
        with pytest.raises(ValueError, match="none of the supported"):
            _detect_try_format(str(f))
    f = tmp_path / "bare.jsonl"
    f.write_text(json.dumps({"type": "assistant",
                             "sessionId": "s1"}) + "\n",
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_comment_led_files(tmp_path):
    # `#` comment lines are skipped before parsing and do not count
    # against the window.
    from averth.cli import _detect_try_format

    f = tmp_path / "led.jsonl"
    lines = ["# Averth JSONL export",
             "# generated 2026-11-12",
             json.dumps({"type": "start", "case_id": "c1"}),
             json.dumps({"type": "model", "case_id": "c1",
                         "model": "claude-sonnet-4-20250514",
                         "input_tokens": 100, "output_tokens": 10}),
             json.dumps({"type": "end", "case_id": "c1",
                         "success": True})]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"
    # Comments interleaved with the first records do not consume
    # the 10-line window: a strong marker at dict line 10 still
    # decides.
    records = [{"type": "system", "sessionId": "s1", "n": i}
               for i in range(9)]
    records.append(
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "text", "text": "hi"}]}})
    lines = []
    for i, r in enumerate(records):
        if i % 3 == 0:
            lines.append("# comment %d" % i)
        lines.append(json.dumps(r))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_strong_marker_after_unknown_lines(tmp_path):
    # No strong marker in the first 10 lines extends the scan to
    # 50 even with no weak markers at all.
    from averth.cli import _detect_try_format

    unknown = {"type": "zzz", "sessionId": "s1"}
    strong = {"type": "assistant", "sessionId": "s1", "uuid": "u1",
              "message": {"id": "m1",
                          "model": "claude-sonnet-4-20250514",
                          "content": [{"type": "text", "text": "hi"}]}}
    # 39 unknown-type lines, then the strong marker at line 40.
    f = tmp_path / "late.jsonl"
    lines = [json.dumps(unknown) for _ in range(39)]
    lines.append(json.dumps(strong))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"
    # 10 unknown-type lines, then the strong marker at line 11.
    f = tmp_path / "eleven.jsonl"
    lines = [json.dumps(unknown) for _ in range(10)]
    lines.append(json.dumps(strong))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_sixty_comment_lines(tmp_path):
    # Comment lines do not count toward the raw-line cap: a strong
    # marker after 60 of them still decides.
    from averth.cli import _detect_try_format

    f = tmp_path / "led.jsonl"
    lines = ["# comment %d" % i for i in range(60)]
    lines.append(json.dumps(
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "text", "text": "hi"}]}}))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def test_detect_try_format_line_51_boundary(tmp_path):
    # A strong marker past the 50-line extension is never seen:
    # once the extension is exhausted, the weak markers decide.
    from averth.cli import _detect_try_format

    unknown = {"type": "zzz", "sessionId": "s1"}
    claude_strong = {"type": "assistant", "sessionId": "s1",
                     "uuid": "u1",
                     "message": {"id": "m1",
                                 "model": "claude-sonnet-4-20250514",
                                 "content": [{"type": "text",
                                              "text": "hi"}]}}
    codex_strong = {"type": "response_item",
                    "payload": {"type": "function_call",
                                "name": "exec_command", "call_id": "c1",
                                "arguments": json.dumps({"command": "ls"})}}
    # Claude-weak in the first 10, Codex strong at line 51: the
    # weak markers decide, the line-51 strong marker is unseen.
    f = tmp_path / "a.jsonl"
    lines = [json.dumps({"type": "system", "sessionId": "s1"})
             for _ in range(2)]
    lines += [json.dumps(unknown) for _ in range(48)]
    lines.append(json.dumps(codex_strong))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"
    # Codex-weak in the first 10, Claude strong at line 51.
    f = tmp_path / "b.jsonl"
    lines = [json.dumps({"type": "session_meta", "payload": {}})
             for _ in range(2)]
    lines += [json.dumps(unknown) for _ in range(48)]
    lines.append(json.dumps(claude_strong))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "codex"
    # Weak conflict in the first 10, then a strong marker at
    # line 11: the strong marker decides, no ambiguity.
    f = tmp_path / "c.jsonl"
    lines = [json.dumps({"type": "system", "sessionId": "s1"})
             for _ in range(2)]
    lines += [json.dumps({"type": "session_meta", "payload": {}})
              for _ in range(2)]
    lines += [json.dumps(unknown) for _ in range(6)]
    lines.append(json.dumps(claude_strong))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert _detect_try_format(str(f)) == "claude"


def _claude_session_file(tmp_path, name="session.jsonl", usage=True):
    """A minimal meterable Claude session file (synthetic)."""
    records = [
        {"type": "assistant", "sessionId": "s1", "uuid": "u1",
         "message": {"id": "m1", "model": "claude-sonnet-4-20250514",
                     "content": [{"type": "tool_use", "id": "c1",
                                  "name": "Bash",
                                  "input": {"command": "pytest"}}]}},
        {"type": "user", "sessionId": "s1",
         "message": {"role": "user", "content": [
             {"type": "tool_result", "tool_use_id": "c1",
              "content": "ok", "is_error": False}]}},
        {"type": "result", "sessionId": "s1", "is_error": False,
         "total_cost_usd": 0.05},
    ]
    if isinstance(usage, dict):
        records[0]["message"]["usage"] = usage
    elif usage:
        records[0]["message"]["usage"] = {"input_tokens": 1000,
                                          "output_tokens": 500}
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(r) for r in records),
                    encoding="utf-8")
    return path


def _codex_rollout_file(tmp_path, name="rollout.jsonl"):
    """A minimal meterable Codex rollout file (synthetic)."""
    records = [
        {"type": "session_meta",
         "payload": {"id": "codex-1", "cwd": "/tmp/shop",
                     "cli_version": "0.130.0",
                     "model_provider": "openai", "source": "cli"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps(
                         {"command": "pytest tests/test_x.py"})}},
        {"type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c1",
                     "output": "ok"}},
        {"type": "event_msg",
         "payload": {"type": "token_count",
                     "info": {"total_token_usage": {
                         "input_tokens": 1000,
                         "cached_input_tokens": 0,
                         "output_tokens": 100,
                         "reasoning_output_tokens": 0}}}},
    ]
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(r) for r in records),
                    encoding="utf-8")
    return path


def test_try_claude_session_file_auto_detected(tmp_path, monkeypatch,
                                              capsys):
    # R4: a single Claude session file meters directly, auto-detected.
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path)
    rc = main(["try", str(path)])
    assert rc == 0
    assert (tmp_path / "session-try.html").exists()
    receipt = (tmp_path / "session-try-receipt.md").read_text(
        encoding="utf-8")
    assert ("Source: `claude/%s` (Claude session)"
            % str(path).lstrip(os.sep)) in receipt
    html = (tmp_path / "session-try.html").read_text(encoding="utf-8")
    assert "Claude session" in html
    out = capsys.readouterr().out
    # Pinned metered values: 1000 in / 500 out tokens on
    # claude-sonnet-4-20250514 = $0.0105 estimated against the
    # trace-recorded $0.05 (ratio 0.21x). The report pads the
    # "Fully loaded" column, so that assertion normalizes
    # whitespace.
    assert "Fully loaded: $0.01" in " ".join(out.split())
    assert "recorded $0.0500 vs metered estimate $0.0105" in receipt
    assert "ratio 0.21x" in receipt


def test_try_claude_session_file_explicit_format(tmp_path, monkeypatch,
                                                capsys):
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path)
    rc = main(["try", str(path), "--format", "claude"])
    assert rc == 0
    receipt = (tmp_path / "session-try-receipt.md").read_text(
        encoding="utf-8")
    assert ("Source: `claude/%s` (Claude session)"
            % str(path).lstrip(os.sep)) in receipt


def test_try_claude_session_cache_heavy_dollars(tmp_path, monkeypatch,
                                                capsys):
    # Cache-heavy usage pins the cache pricing: 1000 in / 8000
    # cache_read / 500 cache_creation / 500 out on
    # claude-sonnet-4-20250514 = $0.0144 estimated against the
    # trace-recorded $0.05.
    monkeypatch.chdir(tmp_path)
    usage = {"input_tokens": 1000, "cache_read_input_tokens": 8000,
             "cache_creation_input_tokens": 500, "output_tokens": 500}
    path = _claude_session_file(tmp_path, usage=usage)
    rc = main(["try", str(path)])
    assert rc == 0
    receipt = (tmp_path / "session-try-receipt.md").read_text(
        encoding="utf-8")
    assert "recorded $0.0500 vs metered estimate $0.0144" in receipt


def test_try_codex_rollout_file_explicit_format(tmp_path, monkeypatch,
                                               capsys):
    # R4: a single Codex rollout meters directly.
    monkeypatch.chdir(tmp_path)
    path = _codex_rollout_file(tmp_path)
    rc = main(["try", str(path), "--format", "codex"])
    assert rc == 0
    assert (tmp_path / "rollout-try.html").exists()
    receipt = (tmp_path / "rollout-try-receipt.md").read_text(
        encoding="utf-8")
    assert ("Source: `codex/%s` (Codex rollout)"
            % str(path).lstrip(os.sep)) in receipt
    assert "EXTERNAL-UNVERIFIABLE" in receipt  # D5, Codex billing
    assert "not comparable: Codex subscription billing" in receipt
    html = (tmp_path / "rollout-try.html").read_text(encoding="utf-8")
    assert "Codex rollout" in html
    out = capsys.readouterr().out
    # Pinned metered value: 1000 in / 100 out tokens on gpt-5.2
    # = $0.00315.
    assert "Total cost: $0.00315" in " ".join(out.split())


def test_try_codex_subagent_rollout_file_auto_detected(
        tmp_path, monkeypatch, capsys):
    # R4 rework: a real subagent rollout (session_meta source is an
    # object, which is what excludes it from the scan) still meters
    # directly when passed explicitly, auto-detected as codex.
    monkeypatch.chdir(tmp_path)
    path = _codex_rollout_file(tmp_path)
    records = [json.loads(line) for line in
               path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    records[0]["payload"]["source"] = {
        "subagent": {"other": "guardian"}}
    path.write_text("\n".join(json.dumps(r) for r in records),
                    encoding="utf-8")
    from averth.local_scan import _is_codex_subagent
    assert _is_codex_subagent(str(path)) is True
    rc = main(["try", str(path)])
    assert rc == 0
    receipt = (tmp_path / "rollout-try-receipt.md").read_text(
        encoding="utf-8")
    assert ("Source: `codex/%s` (Codex rollout)"
            % str(path).lstrip(os.sep)) in receipt


def test_try_codex_rollout_file_auto_detected(tmp_path, monkeypatch,
                                             capsys):
    monkeypatch.chdir(tmp_path)
    path = _codex_rollout_file(tmp_path)
    rc = main(["try", str(path)])
    assert rc == 0
    receipt = (tmp_path / "rollout-try-receipt.md").read_text(
        encoding="utf-8")
    assert ("Source: `codex/%s` (Codex rollout)"
            % str(path).lstrip(os.sep)) in receipt
    assert "EXTERNAL-UNVERIFIABLE" in receipt  # D5, Codex billing
    assert "not comparable: Codex subscription billing" in receipt
    html = (tmp_path / "rollout-try.html").read_text(encoding="utf-8")
    assert "Codex rollout" in html
    out = capsys.readouterr().out
    assert "Total cost: $0.00315" in " ".join(out.split())


def test_try_comment_led_claude_session_meters(tmp_path, monkeypatch,
                                               capsys):
    # Round-4 fix 6: detection alone is not the product behavior —
    # a comment-led session must meter end to end, not just detect
    # as claude and then fail at parse. 60 leading `#` lines, the
    # round-3 failure shape.
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    commented = ["# exported from claude"] * 60 + lines
    path.write_text("\n".join(commented) + "\n", encoding="utf-8")
    rc = main(["try", str(path)])
    assert rc == 0
    receipt = (tmp_path / "session-try-receipt.md").read_text(
        encoding="utf-8")
    assert "recorded $0.0500 vs metered estimate $0.0105" in receipt


def test_try_comment_led_codex_rollout_meters(tmp_path, monkeypatch,
                                             capsys):
    # Round-4 fix 6, Codex half: a comment-led rollout meters end
    # to end with the same pinned dollars as the uncommented file.
    monkeypatch.chdir(tmp_path)
    path = _codex_rollout_file(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    commented = ["# rollout notes", "#", ""] + lines
    path.write_text("\n".join(commented) + "\n", encoding="utf-8")
    rc = main(["try", str(path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Total cost: $0.00315" in " ".join(out.split())


def test_try_comment_led_jsonl_events_meter(tmp_path, monkeypatch,
                                           capsys):
    # Round-4 fix 5, end to end: a commented Averth JSONL events
    # file meters the events it contains.
    monkeypatch.chdir(tmp_path)
    events = _fixture_events()
    path = tmp_path / "events.jsonl"
    path.write_text("# case-study events\n" + "\n".join(
        json.dumps(e) for e in events) + "\n", encoding="utf-8")
    rc = main(["try", str(path)])
    assert rc == 0
    assert (tmp_path / "events-try-receipt.md").exists()


def test_try_codex_two_snapshots_pin_deltas_reasoning_cache(
        tmp_path, monkeypatch, capsys):
    # Round-4 fix 7: the single-snapshot $0.00315 pin is blind to
    # three bugs — summing cumulative snapshots instead of deltas,
    # dropping reasoning tokens, and pricing cached tokens at the
    # full input rate. Two snapshots with nonzero reasoning and
    # cache distinguish all three: expected $0.006195; sum-snapshots
    # gives $0.00973, drop-reasoning $0.004795, cached-at-full-price
    # $0.006825.
    monkeypatch.chdir(tmp_path)
    records = [
        {"type": "session_meta",
         "payload": {"id": "codex-1", "cwd": "/tmp/shop",
                     "cli_version": "0.130.0",
                     "model_provider": "openai", "source": "cli"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps(
                         {"command": "pytest tests/test_x.py"})}},
        {"type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c1",
                     "output": "ok"}},
        {"type": "event_msg",
         "payload": {"type": "token_count",
                     "info": {"total_token_usage": {
                         "input_tokens": 1000,
                         "cached_input_tokens": 200,
                         "output_tokens": 100,
                         "reasoning_output_tokens": 50}}}},
        {"type": "event_msg",
         "payload": {"type": "token_count",
                     "info": {"total_token_usage": {
                         "input_tokens": 1500,
                         "cached_input_tokens": 400,
                         "output_tokens": 200,
                         "reasoning_output_tokens": 100}}}},
    ]
    path = tmp_path / "rollout.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records),
                    encoding="utf-8")
    rc = main(["try", str(path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Total cost: $0.006195" in " ".join(out.split())


def test_try_codex_rollout_without_function_calls_meters(
        tmp_path, monkeypatch, capsys):
    # Round-4 (optional): a rollout with token counts but no
    # function-call records still meters — spend is observed, the
    # missing commands are an evidence gap, not a failure.
    monkeypatch.chdir(tmp_path)
    records = [
        {"type": "session_meta",
         "payload": {"id": "codex-1", "cwd": "/tmp/shop",
                     "cli_version": "0.130.0",
                     "model_provider": "openai", "source": "cli"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
        {"type": "event_msg",
         "payload": {"type": "token_count",
                     "info": {"total_token_usage": {
                         "input_tokens": 1000,
                         "cached_input_tokens": 0,
                         "output_tokens": 100,
                         "reasoning_output_tokens": 0}}}},
    ]
    path = tmp_path / "rollout.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records),
                    encoding="utf-8")
    rc = main(["try", str(path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Total cost: $0.00315" in " ".join(out.split())


def test_try_session_file_without_usage_is_a_clean_error(
        tmp_path, monkeypatch, capsys):
    # Tool records but no usage records: the error names what is
    # missing instead of calling the file an "empty export".
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path, usage=False)
    rc = main(["try", str(path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no usage records found" in err
    assert "empty export" not in err
    # The next step names every accepted form, the concrete
    # `averth try <file>` form, and the trajectory --model note.
    assert "Claude session" in err
    assert "Codex rollout" in err
    assert "mini-SWE-agent trajectory" in err
    assert "Averth JSONL" in err
    assert "Langfuse export" in err
    assert "averth try <file>" in err
    assert "<trace-file>" not in err
    assert "For a trajectory, add --model NAME" in err
    assert not (tmp_path / "session-try.html").exists()
    assert not (tmp_path / "session-try-receipt.md").exists()


def test_try_claude_session_model_flag_is_ignored(tmp_path, monkeypatch,
                                                  capsys):
    # --model applies to trajectories only; passing it with a
    # session file is ignored, not an error, and the session's own
    # model still prices the run.
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path)
    rc = main(["try", str(path), "--model", "some-other-model"])
    assert rc == 0
    receipt = (tmp_path / "session-try-receipt.md").read_text(
        encoding="utf-8")
    assert "recorded $0.0500 vs metered estimate $0.0105" in receipt


def test_try_cross_format_session_is_a_wrong_format_error(
        tmp_path, monkeypatch, capsys):
    # A Claude session forced as codex (and the mirror) meters
    # nothing, because the importer skips foreign records: the
    # error names what the file looks like instead of calling it
    # empty or usage-less.
    monkeypatch.chdir(tmp_path)
    path = _claude_session_file(tmp_path)
    rc = main(["try", str(path), "--format", "codex"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "looks like claude, not codex" in err
    assert "no usage records found" not in err
    assert "empty export" not in err
    path = _codex_rollout_file(tmp_path, name="rollout2.jsonl")
    rc = main(["try", str(path), "--format", "claude"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "looks like codex, not claude" in err
    assert "no usage records found" not in err
    assert "empty export" not in err


def test_try_traj_without_usage_names_model(tmp_path, monkeypatch,
                                           capsys):
    # Round-4 fix 1: a trajectory with messages but no usage
    # records hits the empty-export error; the --model sentence
    # belongs there too, not only in the claude/codex branch.
    monkeypatch.chdir(tmp_path)
    traj = tmp_path / "no-usage-claude-sonnet-4-20250514.traj.json"
    traj.write_text(json.dumps({
        "instance_id": "x",
        "messages": [{"role": "user", "content": "hi"}]}),
        encoding="utf-8")
    rc = main(["try", str(traj)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "contains no traces" in err
    assert "For a trajectory, add --model NAME" in err


def test_try_wrong_format_traj_hint_is_runnable(tmp_path, monkeypatch,
                                               capsys):
    # Round-4 fix 2: the retry hinted by the wrong-format error
    # must work as written. For a trajectory, "--format auto"
    # alone fails with "no model named", so the hint names
    # "--format auto --model NAME".
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--format", "claude"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "--format auto --model NAME" in err
    # The hinted command, with a real model, meters the file.
    rc = main(["try", TRAJ, "--format", "auto", "--model", MODEL])
    assert rc == 0


def test_try_cross_format_traj_names_model(tmp_path, monkeypatch,
                                          capsys):
    # Round-4 fix 2, same defect in the other branch: a trajectory
    # forced as claude whose importer skips every record also needs
    # the --model note — "pass --format traj" alone fails with
    # "no model named" when the file name carries no priced model.
    monkeypatch.chdir(tmp_path)
    traj = tmp_path / "one-line.traj.json"
    traj.write_text(json.dumps({
        "instance_id": "x",
        "messages": [{"role": "user", "content": "hi"}]}),
        encoding="utf-8")
    rc = main(["try", str(traj), "--format", "claude"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "looks like traj, not claude" in err
    assert "For a trajectory, add --model NAME" in err


def test_try_wrong_format_names_detected_format(capsys):
    rc = main(["try", TRAJ, "--format", "jsonl", "--model", MODEL])
    err = capsys.readouterr().err
    assert rc == 2
    assert "does not parse as jsonl" in err
    assert "looks like traj" in err
    assert "traj|jsonl|langfuse|claude|codex" in err


def test_try_unsupported_file_is_an_error(tmp_path, capsys):
    bad = tmp_path / "not-a-trace.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    rc = main(["try", str(bad)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "none of the supported shapes" in err
    assert "pass --format" not in err


def test_try_empty_file_is_an_error(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    rc = main(["try", str(empty)])
    assert rc == 2
    assert "is empty" in capsys.readouterr().err


def test_try_binary_file_is_an_error(tmp_path, capsys):
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xd8\xff\x00\x01")
    rc = main(["try", str(binary)])
    assert rc == 2
    assert "not readable text" in capsys.readouterr().err


def test_try_directory_is_an_error(tmp_path, capsys):
    rc = main(["try", str(tmp_path)])
    assert rc == 2
    assert "is a directory" in capsys.readouterr().err


def test_try_empty_langfuse_is_an_error(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"data": []}), encoding="utf-8")
    rc = main(["try", str(empty)])
    assert rc == 2
    assert "contains no traces" in capsys.readouterr().err


def test_try_missing_ledger_is_named(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", "nope.json"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "V0 ledger file not found" in err
    assert "--ledger" in err


def test_try_recorded_nan_inf_are_errors(capsys):
    for bad in ("nan", "inf", "-1"):
        rc = main(["try", TRAJ, "--model", MODEL, "--recorded", bad])
        assert rc == 2
        assert "positive dollar figure" in capsys.readouterr().err


# --- output path -------------------------------------------------------


def test_try_bad_out_parent_fails_before_report(tmp_path, monkeypatch,
                                               capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL,
               "--out", str(tmp_path / "nope" / "report.html")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "does not exist" in captured.err
    assert "Fully loaded" not in captured.out
    # A parent path that exists as a file is reported as such, not as
    # a missing directory.
    blocker = tmp_path / "blocker.json"
    blocker.write_text("{}", encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL,
               "--out", str(blocker / "report.html")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "is not a directory" in captured.err
    assert "Fully loaded" not in captured.out


def test_try_overwrite_refused_and_force(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL])
    assert rc == 0
    first = (tmp_path / "django-15930-try.html").read_text(encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL])
    err = capsys.readouterr().err
    assert rc == 2
    assert "already exists" in err
    assert "pass --force" in err
    assert (tmp_path / "django-15930-try.html").read_text(
        encoding="utf-8") == first
    rc = main(["try", TRAJ, "--model", MODEL, "--force"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "overwriting" in captured.err


def test_try_digest_mismatch_warns_about_stale_report(
        tmp_path, monkeypatch, capsys):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", CHECKS])
    assert rc == 0
    before = (tmp_path / "django-15930-try.html").read_text(encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", str(tampered)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "digest mismatch" in err
    assert "previous report remains" in err
    assert (tmp_path / "django-15930-try.html").read_text(
        encoding="utf-8") == before


def test_try_hostile_filename_is_escaped(tmp_path, monkeypatch, capsys):
    evil = tmp_path / "<img src=x onerror=alert(1)>.traj.json"
    shutil.copy(TRAJ, evil)
    monkeypatch.chdir(tmp_path)
    rc = main(["try", str(evil), "--model", MODEL,
               "--out", "report.html"])
    assert rc == 0
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<img src=x" not in html
    assert "&lt;img" in html


# --- converter hardening ----------------------------------------------


def test_converter_skips_non_string_text_parts(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "user", "content": [
            {"type": "text", "text": 123},
            {"type": "text", "text": "hello"}]},
        {"role": "assistant", "content": "```bash\necho hi\n```"},
    ], "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert [e for e in events if e["type"] == "model"][0]["input_tokens"] == 1


def test_converter_rejects_non_dict_message(tmp_path):
    traj = {"instance_id": "x", "messages": ["oops"],
            "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    with pytest.raises(ValueError, match="message 0"):
        miniswe.miniswe_events(str(f), model=MODEL)


def test_converter_tolerates_non_dict_info(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "assistant", "content": "hi"}],
        "info": "Submitted"}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert not [e for e in events if e["type"] == "end"]


def test_converter_bash_fence_variants(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "assistant", "content": "```bash echo hi```"},
        {"role": "assistant", "content": "```bash \necho hi\n```"},
        {"role": "assistant", "content": "```BASH\necho hi\n```"},
    ], "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert len([e for e in events if e["type"] == "tool"]) == 3


def test_infer_model_matches_basename_only():
    assert miniswe._infer_model("/tmp/notes-about-gpt-4o/traj.json") is None
    assert miniswe._infer_model("mygpt-4o-model.traj.json") is None
    assert miniswe._infer_model(
        "django__django-15930_claude-sonnet-4-20250514.traj.json") == MODEL
    assert miniswe.is_priced_model(MODEL) is True
    assert miniswe.is_priced_model("gpt-99-nonexistent") is False
    assert miniswe.is_priced_model("anthropic:" + MODEL) is True


# --- report byte identity ----------------------------------------------


def test_write_html_without_try_extras_is_unchanged(tmp_path):
    from averth.report import write_html

    ledger = miniswe.load_miniswe(TRAJ, model=MODEL)
    tracker = common.tracker_from_ledger(ledger)
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    c = tmp_path / "c.html"
    write_html(str(a), tracker, try_extras=None)
    write_html(str(b), tracker, try_extras="")
    # None and "" render identically: no stray blank line is added.
    assert a.read_bytes() == b.read_bytes()
    write_html(str(c), tracker, try_extras="<p>EXTRA</p>")
    html_c = c.read_text(encoding="utf-8")
    assert html_c.count("<p>EXTRA</p>") == 1
    assert "<p>EXTRA</p>\n</main>" in html_c
