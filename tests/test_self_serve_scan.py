"""Tests for the zero-config self-serve scan (``averth try`` with no
trace argument): local session discovery, trace-observed evidence
extraction, the five default checks, the PR receipt, and CLI scan /
explicit-trace behavior.

All session fixtures below are SYNTHETIC, built to the documented
Claude Code / Codex transcript formats. None of them claims to be a
real session: no local Claude/Codex sessions exist on this machine.
"""

import json
import os

import pytest

averth = pytest.importorskip("averth")
from averth import default_checks, local_scan, receipt as receipt_mod  # noqa: E402
from averth.cli import main  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            if isinstance(record, str):
                f.write(record + "\n")
            else:
                f.write(json.dumps(record) + "\n")
    return path


def _claude_assistant(msg_id, usage=None, content=None, session="sess-1",
                      **extra):
    rec = {"type": "assistant", "sessionId": session,
           "uuid": "line-%s" % msg_id,
           "message": {"id": msg_id,
                       "model": "claude-sonnet-4-20250514"}}
    if usage is not None:
        rec["message"]["usage"] = usage
    if content is not None:
        rec["message"]["content"] = content
    rec.update(extra)
    return rec


def _claude_tool_result(tool_use_id, is_error):
    return {"type": "user", "sessionId": "sess-1",
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id,
                 "content": "ok", "is_error": is_error}]}}


def _bash_use(tool_id, command):
    return {"type": "tool_use", "id": tool_id, "name": "Bash",
            "input": {"command": command}}


def _edit_use(tool_id, file_path):
    return {"type": "tool_use", "id": tool_id, "name": "Edit",
            "input": {"file_path": file_path}}


USAGE = {"input_tokens": 1000, "output_tokens": 500}


def _claude_session(tmp_path, name="session-1.jsonl", cost=0.05):
    """A synthetic Claude session: pytest + make pass, cli.py edited.

    Two model calls (both priced), a passing pytest of
    tests/test_cli.py run twice (one duplicate invocation), a passing
    bare ``make``, an Edit of averth/cli.py, and a result record
    carrying total_cost_usd.
    """
    path = tmp_path / ".claude" / "projects" / "proj" / name
    records = [
        _claude_assistant("msg_01", usage=USAGE, content=[
            _bash_use("call_1", "pytest tests/test_cli.py"),
            _edit_use("call_2", "averth/cli.py")]),
        _claude_tool_result("call_1", False),
        _claude_tool_result("call_2", False),
        _claude_assistant("msg_02", usage=USAGE, content=[
            _bash_use("call_3", "pytest tests/test_cli.py"),
            _bash_use("call_4", "make")]),
        _claude_tool_result("call_3", False),
        _claude_tool_result("call_4", False),
        {"type": "result", "sessionId": "sess-1", "is_error": False,
         "total_cost_usd": cost},
    ]
    return _write_jsonl(path, records)


def _codex_rollout(tmp_path, name="rollout-1.jsonl", subagent=False):
    """A synthetic Codex rollout: pytest + go build, no exit codes."""
    path = tmp_path / ".codex" / "sessions" / "2026" / "11" / "11" / name
    meta = {"type": "session_meta",
            "payload": {"id": "codex-1", "cwd": "/tmp/shop",
                        "cli_version": "0.130.0",
                        "model_provider": "openai", "source": "cli"}}
    if subagent:
        meta["payload"]["source"] = {"subagent": {"other": "guardian"}}
    records = [
        meta,
        {"type": "turn_context", "payload": {"model": "gpt-5.2"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps(
                         {"command": "pytest tests/test_x.py"})}},
        {"type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c1",
                     "output": "ok"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c2",
                     "arguments": json.dumps(
                         {"command": "go build ./..."})}},
        {"type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c2",
                     "output": "ok"}},
        {"type": "event_msg",
         "payload": {"type": "token_count",
                     "info": {"total_token_usage": {
                         "input_tokens": 1000,
                         "cached_input_tokens": 0,
                         "output_tokens": 100,
                         "reasoning_output_tokens": 0}}}},
    ]
    return _write_jsonl(path, records)


def _touch(path, mtime):
    os.utime(path, (mtime, mtime))


# --- discovery -------------------------------------------------------


def test_discovery_finds_both_sources_newest_first(tmp_path):
    claude = _claude_session(tmp_path)
    codex = _codex_rollout(tmp_path)
    _touch(claude, 1000)
    _touch(codex, 2000)
    selected, skipped, checked = local_scan.discover_sessions(tmp_path)
    assert [s["source"] for s in selected] == ["codex", "claude"]
    assert skipped == []
    assert checked[0].endswith(os.path.join(".claude", "projects"))
    assert checked[1].endswith(os.path.join(".codex", "sessions"))


def test_discovery_empty_home_selects_nothing(tmp_path):
    selected, skipped, checked = local_scan.discover_sessions(tmp_path)
    assert selected == []
    assert skipped == []


def test_discovery_caps_at_ten_newest(tmp_path):
    paths = []
    for i in range(12):
        p = _claude_session(tmp_path, name="s%02d.jsonl" % i)
        _touch(p, 1000 + i)
        paths.append(p)
    selected, _skipped, _checked = local_scan.discover_sessions(tmp_path)
    assert len(selected) == 10
    assert selected[0]["path"] == str(paths[11])
    assert selected[-1]["path"] == str(paths[2])


def test_discovery_excludes_codex_subagent_rollouts(tmp_path):
    _codex_rollout(tmp_path, name="main.jsonl")
    _codex_rollout(tmp_path, name="sub.jsonl", subagent=True)
    selected, skipped, _checked = local_scan.discover_sessions(tmp_path)
    assert [os.path.basename(s["path"]) for s in selected] == ["main.jsonl"]
    assert len(skipped) == 1
    assert skipped[0]["source"] == "codex"
    assert "subagent" in skipped[0]["reason"]


def test_discovery_ignores_non_jsonl(tmp_path):
    p = tmp_path / ".claude" / "projects" / "proj" / "notes.txt"
    p.parent.mkdir(parents=True)
    p.write_text("not a session", encoding="utf-8")
    selected, _skipped, _c = local_scan.discover_sessions(tmp_path)
    assert selected == []


# --- extraction ------------------------------------------------------


def test_extract_claude_commands_edits_and_cost(tmp_path):
    path = _claude_session(tmp_path)
    ev = default_checks.extract_claude(str(path))
    commands = [c["command"] for c in ev["commands"]]
    assert commands == ["pytest tests/test_cli.py",
                        "pytest tests/test_cli.py", "make"]
    assert all(c["outcome"] is True for c in ev["commands"])
    assert ev["edited_files"] == ["averth/cli.py"]
    assert ev["recorded_cost"] == 0.05


def test_extract_claude_unmatched_tool_use_is_outcome_unknown(tmp_path):
    path = tmp_path / "s.jsonl"
    records = [
        _claude_assistant("msg_01", usage=USAGE, content=[
            _bash_use("call_1", "pytest")]),
        # No tool_result for call_1: the session was cut off.
        {"type": "result", "sessionId": "sess-1", "is_error": False},
    ]
    _write_jsonl(path, records)
    ev = default_checks.extract_claude(str(path))
    assert ev["commands"][0]["outcome"] is None
    assert ev["recorded_cost"] is None


def test_extract_claude_sidechain_tool_use_skipped(tmp_path):
    path = tmp_path / "s.jsonl"
    records = [
        _claude_assistant("msg_01", usage=USAGE, content=[
            _bash_use("call_1", "pytest")], isSidechain=True),
        _claude_assistant("msg_02", usage=USAGE, content=[
            _bash_use("call_2", "go build ./...")]),
        _claude_tool_result("call_2", False),
    ]
    _write_jsonl(path, records)
    ev = default_checks.extract_claude(str(path))
    assert [c["command"] for c in ev["commands"]] == ["go build ./..."]


def test_extract_codex_commands_without_exit_codes(tmp_path):
    path = _codex_rollout(tmp_path)
    ev = default_checks.extract_codex(str(path))
    assert [c["command"] for c in ev["commands"]] == [
        "pytest tests/test_x.py", "go build ./..."]
    assert all(c["outcome"] is None for c in ev["commands"])
    assert ev["recorded_cost"] is None


def test_extract_codex_exit_code_field_is_honoured(tmp_path):
    path = tmp_path / "r.jsonl"
    records = [
        {"type": "session_meta",
         "payload": {"id": "c1", "source": "cli"}},
        {"type": "response_item",
         "payload": {"type": "function_call", "name": "exec_command",
                     "call_id": "c1",
                     "arguments": json.dumps({"command": "pytest"})}},
        {"type": "response_item",
         "payload": {"type": "function_call_output", "call_id": "c1",
                     "output": "FAILED", "exit_code": 1}},
    ]
    _write_jsonl(path, records)
    ev = default_checks.extract_codex(str(path))
    assert ev["commands"][0]["outcome"] is False


def test_extract_from_file_sniffs_shapes(tmp_path):
    claude = _claude_session(tmp_path)
    assert default_checks.extract_from_file(
        str(claude))["source"] == "claude"
    codex = _codex_rollout(tmp_path)
    assert default_checks.extract_from_file(
        str(codex))["source"] == "codex"
    plain = tmp_path / "events.jsonl"
    plain.write_text(json.dumps({"type": "model", "case_id": "x"}) + "\n",
                     encoding="utf-8")
    ev = default_checks.extract_from_file(str(plain))
    assert ev["source"] == "unknown"
    assert ev["commands"] == []


def test_extract_traj_reads_fences_and_instance_cost(tmp_path):
    traj = tmp_path / "run.traj.json"
    traj.write_text(json.dumps({
        "info": {"model_stats": {"instance_cost": 0.3205}},
        "messages": [
            {"role": "assistant",
             "content": "let me test:\n```bash\npytest tests/test_a.py\n```"},
            {"role": "user", "content": [{"type": "text", "text": "ok"}]},
        ]}), encoding="utf-8")
    ev = default_checks.extract_traj(str(traj))
    assert [c["command"] for c in ev["commands"]] == [
        "pytest tests/test_a.py"]
    assert ev["commands"][0]["outcome"] is None
    assert ev["recorded_cost"] == 0.3205


# --- classification --------------------------------------------------


@pytest.mark.parametrize("command, kind", [
    ("pytest", "test"),
    ("python -m pytest tests/", "test"),
    ("python3 -m unittest discover", "test"),
    ("npm test", "test"),
    ("npm run test", "test"),
    ("yarn test", "test"),
    ("go test ./...", "test"),
    ("cargo test", "test"),
    ("make test", "test"),
    ("go build ./...", "build"),
    ("cargo build", "build"),
    ("npm run build", "build"),
    ("make", "build"),
    ("make build", "build"),
    ("tsc -p tsconfig.json", "build"),
    ("python script.py", None),
    ("make lint", None),
    ("git status", None),
])
def test_classify_command(command, kind):
    got, _targets = default_checks.classify_command(command)
    assert got == kind


def test_classify_command_extracts_test_file_targets():
    _kind, targets = default_checks.classify_command(
        "pytest tests/test_cli.py tests/test_x.py -q")
    assert targets == ["tests/test_cli.py", "tests/test_x.py"]
    _kind, targets = default_checks.classify_command("pytest -q")
    assert targets == []


# --- the five checks ---------------------------------------------------


def _evidence(commands=(), edited=(), recorded=None, has_codex=False,
              claude_sessions=0, claude_with_cost=0):
    ev = {"source": "scan", "commands": list(commands),
          "edited_files": list(edited), "recorded_cost": recorded,
          "sessions": [], "unparseable_lines": 0,
          "has_codex": has_codex, "claude_sessions": claude_sessions,
          "claude_with_cost": claude_with_cost, "sources": []}
    return ev


def _cmd(command, outcome=None):
    return {"command": command, "outcome": outcome,
            "outcome_note": "synthetic", "session": "s"}


def _verdicts(checks):
    return {c["id"]: c["verdict"] for c in checks}


def test_d1_verified_failed_and_not_observed():
    ev = _evidence(commands=[_cmd("pytest", True)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D1"] == "VERIFIED"
    ev = _evidence(commands=[_cmd("pytest", False)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D1"] == "FAILED"
    ev = _evidence(commands=[_cmd("pytest", None)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D1"] == "NOT OBSERVED"
    ev = _evidence(commands=[_cmd("ls", True)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D1"] == "NOT OBSERVED"


def test_d1_judges_the_last_test_run():
    ev = _evidence(commands=[_cmd("pytest", False), _cmd("pytest", True)])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D1"] == "VERIFIED"
    assert "observed 2 time(s)" in checks[0]["observation"]


def test_d2_build_verdicts():
    ev = _evidence(commands=[_cmd("go build ./...", True)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D2"] == "VERIFIED"
    ev = _evidence(commands=[_cmd("go build ./...", False)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D2"] == "FAILED"
    ev = _evidence(commands=[])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D2"] == "NOT OBSERVED"


def test_d3_full_suite_pass_verifies_touched_files():
    ev = _evidence(commands=[_cmd("pytest", True)],
                   edited=["averth/cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "VERIFIED"


def test_d3_named_tests_match_by_stem():
    ev = _evidence(commands=[_cmd("pytest tests/test_cli.py", True)],
                   edited=["averth/cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "VERIFIED"
    ev = _evidence(commands=[_cmd("pytest tests/test_other.py", True)],
                   edited=["averth/cli.py"])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "FAILED"
    assert "averth/cli.py" in checks[2]["observation"]


def test_d3_not_observed_paths():
    # No edited files.
    ev = _evidence(commands=[_cmd("pytest", True)])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "NOT OBSERVED"
    # Edited files but no test command.
    ev = _evidence(commands=[_cmd("make", True)],
                   edited=["averth/cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "NOT OBSERVED"
    # Full-suite run with unknown outcome.
    ev = _evidence(commands=[_cmd("pytest", None)],
                   edited=["averth/cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "NOT OBSERVED"


def test_d3_test_files_themselves_need_no_match():
    ev = _evidence(commands=[_cmd("pytest tests/test_cli.py", True)],
                   edited=["tests/test_cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "NOT OBSERVED"


def test_d4_threshold_three_duplicates_fail():
    ev = _evidence(commands=[_cmd("pytest", True),
                             _cmd("pytest", True)])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D4"] == "VERIFIED"
    assert "1 duplicate invocation" in checks[3]["observation"]
    ev = _evidence(commands=[_cmd("pytest", True)] * 4)
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D4"] == "FAILED"
    assert "3 duplicate invocation" in checks[3]["observation"]
    assert "retries" not in checks[3]["observation"].lower()
    assert "duplicate-invocation overhead" in checks[3]["observation"]
    ev = _evidence(commands=[])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D4"] == "NOT OBSERVED"


def test_d5_within_five_percent_verifies():
    ev = _evidence(recorded=1.00, claude_sessions=1, claude_with_cost=1)
    assert _verdicts(default_checks.judge_default_checks(
        ev, 1.04))["D5"] == "VERIFIED"
    assert _verdicts(default_checks.judge_default_checks(
        ev, 1.06))["D5"] == "FAILED"


def test_d5_not_observed_and_partial_and_codex():
    ev = _evidence(recorded=None)
    assert _verdicts(
        default_checks.judge_default_checks(ev, 1.0))["D5"] == "NOT OBSERVED"
    ev = _evidence(recorded=0.5, claude_sessions=2, claude_with_cost=1)
    checks = default_checks.judge_default_checks(ev, 0.5)
    assert _verdicts(checks)["D5"] == "NOT OBSERVED"
    assert "partial" in checks[4]["observation"]
    ev = _evidence(recorded=0.5, has_codex=True)
    checks = default_checks.judge_default_checks(ev, 0.5)
    assert _verdicts(checks)["D5"] == "EXTERNAL-UNVERIFIABLE"
    assert "subscription" in checks[4]["observation"]


def test_unknown_rate_counts_not_observed_and_unverifiable():
    checks = [{"verdict": "VERIFIED"}, {"verdict": "NOT OBSERVED"},
              {"verdict": "EXTERNAL-UNVERIFIABLE"},
              {"verdict": "FAILED"}, {"verdict": "VERIFIED"}]
    assert default_checks.unknown_rate(checks) == pytest.approx(0.4)


def test_full_claude_fixture_judges_all_five(tmp_path):
    path = _claude_session(tmp_path)
    ev = default_checks.merge_evidence(
        [default_checks.extract_claude(str(path))])
    checks = default_checks.judge_default_checks(ev, 0.021)
    verdicts = _verdicts(checks)
    assert verdicts["D1"] == "VERIFIED"
    assert verdicts["D2"] == "VERIFIED"
    assert verdicts["D3"] == "VERIFIED"
    assert verdicts["D4"] == "VERIFIED"  # 1 duplicate < threshold 3
    assert verdicts["D5"] == "FAILED"    # $0.021 vs recorded $0.05
    assert all("default checks" not in c["observation"] for c in checks)


def test_full_codex_fixture_judges(tmp_path):
    path = _codex_rollout(tmp_path)
    ev = default_checks.merge_evidence(
        [default_checks.extract_codex(str(path))])
    checks = default_checks.judge_default_checks(ev, 0.01)
    verdicts = _verdicts(checks)
    assert verdicts["D1"] == "NOT OBSERVED"  # no exit code in format
    assert verdicts["D2"] == "NOT OBSERVED"
    assert verdicts["D3"] == "NOT OBSERVED"  # no edited files
    assert verdicts["D4"] == "VERIFIED"      # no duplicates
    assert verdicts["D5"] == "EXTERNAL-UNVERIFIABLE"


# --- receipt -----------------------------------------------------------


def test_receipt_renders_tables_and_footer():
    checks = [
        {"id": "D1", "name": "tests executed", "verdict": "VERIFIED",
         "observation": "`pytest` (succeeded; is_error=false)"},
        {"id": "D5", "name": "billed vs estimated cost",
         "verdict": "FAILED",
         "observation": "recorded $0.0500 vs metered estimate $0.0210"},
    ]
    text = receipt_mod.render_receipt(
        sources=["claude/session-1.jsonl"], estimated_cost=0.021,
        recorded_cost=0.05, checks=checks, unknown_rate=0.0)
    assert "# Averth Verified Agent PR Receipt" in text
    assert "Metered estimate (total) | $0.02 ESTIMATED" in text
    assert "Recorded cost (trace) | $0.05" in text
    assert "| D1 tests executed | VERIFIED |" in text
    assert "Unknown rate: 0.0%" in text
    assert "No cost per accepted outcome" in text
    assert "Estimates are not bills" in text
    assert "trace-observed, not human-written" in text


def test_receipt_escapes_hostile_session_names():
    checks = [{"id": "D1", "name": "tests executed",
               "verdict": "NOT OBSERVED",
               "observation": "no test command observed in trace"}]
    hostile = "claude/evil|name\n[x](https://example.com)"
    text = receipt_mod.render_receipt(
        sources=[hostile], estimated_cost=0.01, recorded_cost=None,
        checks=checks, unknown_rate=1.0)
    assert "evil\\|name" in text
    assert "[x](https://example.com)" not in text
    assert "\n[x]" not in text


def test_receipt_path_for_html():
    assert receipt_mod.receipt_path_for_html(
        "/tmp/x-try.html") == "/tmp/x-try-receipt.md"
    assert receipt_mod.receipt_path_for_html(
        "/tmp/x") == "/tmp/x-receipt.md"


def test_receipt_heading_is_the_default_checks_label():
    text = receipt_mod.render_receipt(
        sources=[], estimated_cost=0.01, recorded_cost=None, checks=[],
        unknown_rate=0.0)
    assert "## Default checks (trace-observed)" in text
    assert "default checks (default checks" not in text


def test_receipt_suppresses_ratio_when_recorded_not_comparable():
    checks = [{"id": "D5", "name": "billed vs estimated cost",
               "verdict": "EXTERNAL-UNVERIFIABLE", "observation": "x"}]
    text = receipt_mod.render_receipt(
        sources=["codex/r.jsonl"], estimated_cost=0.02,
        recorded_cost=0.05,
        recorded_note=receipt_mod.recorded_note_for(checks),
        checks=checks, unknown_rate=0.2)
    assert "not comparable: Codex subscription billing" in text
    assert "Metered estimate / recorded cost" not in text


def test_receipt_recorded_note_for_codex():
    checks = [{"id": "D5", "name": "billed vs estimated cost",
               "verdict": "EXTERNAL-UNVERIFIABLE", "observation": "x"}]
    assert receipt_mod.recorded_note_for(checks) is not None
    assert "subscription" in receipt_mod.recorded_note_for(checks)
    checks = [{"id": "D5", "name": "billed vs estimated cost",
               "verdict": "VERIFIED", "observation": "x"}]
    assert receipt_mod.recorded_note_for(checks) is None


# --- CLI ---------------------------------------------------------------


def test_cli_scan_no_sessions_is_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = main(["try"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no local Claude Code or Codex sessions found" in err
    assert str(tmp_path / ".claude" / "projects") in err
    assert str(tmp_path / ".codex" / "sessions") in err


def test_cli_scan_runs_on_fake_sessions(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _claude_session(tmp_path)
    _codex_rollout(tmp_path)
    rc = main(["try"])
    out = capsys.readouterr().out
    assert rc == 0
    assert (tmp_path / "averth-scan.html").exists()
    assert (tmp_path / "averth-scan-receipt.md").exists()
    receipt = (tmp_path / "averth-scan-receipt.md").read_text(
        encoding="utf-8")
    assert "# Averth Verified Agent PR Receipt" in receipt
    assert "D5 billed vs estimated cost" in receipt
    assert "EXTERNAL-UNVERIFIABLE" in receipt  # Codex present
    assert "Averth Verified Agent PR Receipt" in out  # printed in scan
    assert "Local scan: 2 session(s) scanned" in out


def test_cli_scan_all_parse_failures_is_exit_2(tmp_path, monkeypatch,
                                               capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    bad = tmp_path / ".claude" / "projects" / "proj" / "bad.jsonl"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json\n", encoding="utf-8")
    rc = main(["try"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "failed to parse" in err


def test_cli_scan_subagent_only_is_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _codex_rollout(tmp_path, name="sub.jsonl", subagent=True)
    rc = main(["try"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "subagent rollout(s) found but excluded" in err


def test_cli_scan_rejects_format_and_model_flags(tmp_path, monkeypatch,
                                                 capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _claude_session(tmp_path)
    assert main(["try", "--format", "traj"]) == 2
    assert main(["try", "--model", "gpt-5"]) == 2


def test_cli_scan_receipt_override(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _claude_session(tmp_path)
    rc = main(["try", "--receipt", "custom.md"])
    assert rc == 0
    assert (tmp_path / "custom.md").exists()
    assert not (tmp_path / "averth-scan-receipt.md").exists()


def test_cli_explicit_traj_writes_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    traj = os.path.join(REPO, "try-it", "fixtures",
                        "django-15930.traj.json")
    rc = main(["try", traj, "--model", "claude-sonnet-4-20250514"])
    out = capsys.readouterr().out
    assert rc == 0
    receipt_path = tmp_path / "django-15930-try-receipt.md"
    assert receipt_path.exists()
    receipt = receipt_path.read_text(encoding="utf-8")
    assert "# Averth Verified Agent PR Receipt" in receipt
    assert "D5 billed vs estimated cost" in receipt
    # Case study: recorded $0.3205 vs metered estimate $0.98 -> FAILED.
    assert "recorded $0.3205" in receipt
    assert "FAILED" in receipt
    # Explicit mode writes the receipt file but does not print it.
    assert "Averth Verified Agent PR Receipt" not in out
    assert "Receipt written to" in out


def test_cli_explicit_receipt_refused_without_force(tmp_path, monkeypatch,
                                                    capsys):
    monkeypatch.chdir(tmp_path)
    traj = os.path.join(REPO, "try-it", "fixtures",
                        "django-15930.traj.json")
    assert main(["try", traj, "--model",
                 "claude-sonnet-4-20250514"]) == 0
    rc = main(["try", traj, "--model", "claude-sonnet-4-20250514"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "already exists" in err
