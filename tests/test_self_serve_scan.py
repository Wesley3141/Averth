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
    selected, skipped, checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert [s["source"] for s in selected] == ["codex", "claude"]
    assert skipped == []
    assert total_found == 2
    assert checked[0].endswith(os.path.join(".claude", "projects"))
    assert checked[1].endswith(os.path.join(".codex", "sessions"))


def test_discovery_empty_home_selects_nothing(tmp_path):
    selected, skipped, checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert selected == []
    assert skipped == []
    assert total_found == 0


def test_discovery_caps_at_ten_newest(tmp_path):
    paths = []
    for i in range(12):
        p = _claude_session(tmp_path, name="s%02d.jsonl" % i)
        _touch(p, 1000 + i)
        paths.append(p)
    selected, _skipped, _checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert len(selected) == 10
    assert total_found == 12
    assert selected[0]["path"] == str(paths[11])
    assert selected[-1]["path"] == str(paths[2])


def test_discovery_excludes_codex_subagent_rollouts(tmp_path):
    _codex_rollout(tmp_path, name="main.jsonl")
    _codex_rollout(tmp_path, name="sub.jsonl", subagent=True)
    selected, skipped, _checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert [os.path.basename(s["path"]) for s in selected] == ["main.jsonl"]
    assert len(skipped) == 1
    assert skipped[0]["source"] == "codex"
    assert "subagent" in skipped[0]["reason"]
    assert total_found == 2


def test_discovery_skipped_subagent_past_the_cap(tmp_path):
    for i in range(10):
        p = _codex_rollout(tmp_path, name="main%02d.jsonl" % i)
        _touch(p, 2000 + i)
    old = _codex_rollout(tmp_path, name="sub.jsonl", subagent=True)
    _touch(old, 1000)
    selected, skipped, _checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert len(selected) == 10
    assert len(skipped) == 1
    assert skipped[0]["path"] == str(old)
    assert total_found == 11


def test_discovery_skips_fifo_without_hanging(tmp_path):
    main = _codex_rollout(tmp_path, name="main.jsonl")
    fifo_dir = tmp_path / ".codex" / "sessions" / "2026" / "11" / "11"
    fifo = fifo_dir / "pipe.jsonl"
    os.mkfifo(fifo)
    selected, skipped, _checked, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert [s["path"] for s in selected] == [str(main)]
    assert total_found == 1
    assert any(s["path"] == str(fifo)
               and "not a regular file" in s["reason"]
               for s in skipped)
    # The guard itself must not block on the FIFO either.
    assert local_scan._is_codex_subagent(str(fifo)) is False


def test_is_codex_subagent_past_line_50(tmp_path):
    path = tmp_path / "r.jsonl"
    records = [{"type": "event_msg", "payload": {}}] * 60
    records.append({"type": "session_meta",
                    "payload": {"id": "c1",
                                "source": {"subagent": {}}}})
    _write_jsonl(path, records)
    assert local_scan._is_codex_subagent(str(path)) is True


def test_is_codex_subagent_nickname_role_and_payload_shapes(tmp_path):
    def _meta(payload, extra=None):
        rec = {"type": "session_meta", "payload": payload}
        if extra:
            rec.update(extra)
        return rec

    path = tmp_path / "nick.jsonl"
    _write_jsonl(path, [_meta({"id": "c1", "source": "cli",
                               "agent_nickname": "helper"})])
    assert local_scan._is_codex_subagent(str(path)) is True
    path = tmp_path / "role.jsonl"
    _write_jsonl(path, [_meta({"id": "c1", "source": "cli",
                               "agent_role": "subagent"})])
    assert local_scan._is_codex_subagent(str(path)) is True
    path = tmp_path / "flat.jsonl"
    _write_jsonl(path, [{"type": "session_meta",
                         "source": {"subagent": {}}}])
    assert local_scan._is_codex_subagent(str(path)) is True
    path = tmp_path / "main.jsonl"
    _write_jsonl(path, [_meta({"id": "c1", "source": "cli"})])
    assert local_scan._is_codex_subagent(str(path)) is False


def test_discovery_ignores_non_jsonl(tmp_path):
    p = tmp_path / ".claude" / "projects" / "proj" / "notes.txt"
    p.parent.mkdir(parents=True)
    p.write_text("not a session", encoding="utf-8")
    selected, _skipped, _c, total_found = \
        local_scan.discover_sessions(tmp_path)
    assert selected == []
    assert total_found == 0


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


def test_extract_traj_parses_returncodes(tmp_path):
    traj = tmp_path / "run.traj.json"
    traj.write_text(json.dumps({
        "info": {"model_stats": {"instance_cost": 0.5}},
        "messages": [
            {"role": "assistant",
             "content": "```bash\npytest tests/test_a.py\n```"},
            {"role": "user", "content": [
                {"type": "text",
                 "text": "<returncode>1</returncode>\nFAILED"}]},
            {"role": "assistant",
             "content": "```bash\nmake\n```"},
            {"role": "user", "content": [
                {"type": "text", "text": "<returncode>0</returncode>"}]},
            {"role": "assistant",
             "content": "```bash\nls\n```"},
            # No following user message: outcome stays unknown.
        ]}), encoding="utf-8")
    ev = default_checks.extract_traj(str(traj))
    assert [c["outcome"] for c in ev["commands"]] == [False, True, None]
    assert "returncode" in ev["commands"][0]["outcome_note"]
    assert "returncode" in ev["commands"][2]["outcome_note"]
    checks = default_checks.judge_default_checks(
        default_checks.merge_evidence([ev]), 0.5)
    assert _verdicts(checks)["D1"] == "FAILED"
    assert _verdicts(checks)["D2"] == "VERIFIED"


def test_extract_traj_case_study_fixture_has_no_false_sentence(tmp_path):
    traj = os.path.join(REPO, "try-it", "fixtures",
                        "django-15930.traj.json")
    ev = default_checks.extract_traj(traj)
    assert len(ev["commands"]) > 0
    assert any(c["outcome"] is not None for c in ev["commands"])
    assert all("carries no per-command exit status" not in c["outcome_note"]
               and "trajectory text carries no" not in c["outcome_note"]
               for c in ev["commands"])


def test_extract_claude_non_utf8_line_is_counted_not_fatal(tmp_path):
    path = tmp_path / "s.jsonl"
    with open(path, "wb") as f:
        f.write((json.dumps(_claude_assistant(
            "msg_01", usage=USAGE, content=[
                _bash_use("call_1", "pytest")])) + "\n").encode("utf-8"))
        f.write(b"\xff\xfe not utf8\n")
        f.write((json.dumps({"type": "result", "sessionId": "sess-1",
                             "total_cost_usd": 0.05}) + "\n")
                .encode("utf-8"))
    ev = default_checks.extract_claude(str(path))
    assert [c["command"] for c in ev["commands"]] == ["pytest"]
    assert ev["unparseable_lines"] == 1
    assert ev["recorded_cost"] == 0.05


def test_extract_codex_non_utf8_line_late_is_counted(tmp_path):
    path = tmp_path / "r.jsonl"
    records = [{"type": "event_msg", "payload": {}}] * 59
    records.append({"type": "response_item",
                    "payload": {"type": "function_call",
                                "name": "exec_command", "call_id": "c1",
                                "arguments": json.dumps(
                                    {"command": "pytest"})}})
    with open(path, "wb") as f:
        for record in records:
            f.write((json.dumps(record) + "\n").encode("utf-8"))
        f.write(b"\xff bad bytes\n")
    ev = default_checks.extract_codex(str(path))
    assert [c["command"] for c in ev["commands"]] == ["pytest"]
    assert ev["unparseable_lines"] == 1


def test_extract_claude_tool_use_without_id_never_claims_outcome(tmp_path):
    path = tmp_path / "s.jsonl"
    records = [
        _claude_assistant("msg_01", usage=USAGE, content=[
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "pytest"}},
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "make"}}]),
        # A stray tool_result with no tool_use_id must not resolve
        # either command.
        {"type": "user", "sessionId": "sess-1",
         "message": {"role": "user", "content": [
             {"type": "tool_result", "content": "ok",
              "is_error": False}]}},
    ]
    _write_jsonl(path, records)
    ev = default_checks.extract_claude(str(path))
    assert [c["command"] for c in ev["commands"]] == ["pytest", "make"]
    assert all(c["outcome"] is None for c in ev["commands"])


def test_codex_command_dict_and_list_argument_shapes():
    assert default_checks._codex_command(
        {"command": "pytest -q"}) == "pytest -q"
    assert default_checks._codex_command(
        {"cmd": ["pytest", "-q"]}) == "pytest -q"
    assert default_checks._codex_command(
        json.dumps({"cmd": ["go", "build", "./..."]})) == "go build ./..."
    assert default_checks._codex_command(
        json.dumps({"command": "make"})) == "make"
    assert default_checks._codex_command("not json") is None
    assert default_checks._codex_command({"other": 1}) is None
    assert default_checks._codex_command(["pytest"]) is None


def test_extract_from_file_never_loads_whole_file(tmp_path, monkeypatch):
    claude = _claude_session(tmp_path)
    orig_load = json.load

    def _boom(*args, **kwargs):
        raise AssertionError("json.load must not be called to sniff")

    monkeypatch.setattr(json, "load", _boom)
    try:
        ev = default_checks.extract_from_file(str(claude))
    finally:
        monkeypatch.setattr(json, "load", orig_load)
    assert ev["source"] == "claude"
    assert ev["commands"]


def test_extract_from_file_large_jsonl_streams(tmp_path):
    plain = tmp_path / "big.jsonl"
    with open(plain, "w", encoding="utf-8") as f:
        for i in range(20000):
            f.write(json.dumps({"type": "model", "case_id": "x%d" % i,
                                "model": "claude-sonnet-4-20250514",
                                "input_tokens": 10,
                                "output_tokens": 5}) + "\n")
    assert plain.stat().st_size > 1024 * 1024
    ev = default_checks.extract_from_file(str(plain))
    assert ev["source"] == "unknown"
    assert ev["commands"] == []


def test_top_level_key_scanner_chunk_boundaries():
    # The "messages" key split across feeds, nested keys ignored, a
    # bare list closing the scan at once.
    s = default_checks._TopLevelKeyScanner()
    s.feed('{"info": {"model": "x", "nested": {"messages": true}}, "me')
    assert "messages" not in s.keys
    s.feed('ssages": [], "other": 1}')
    assert s.keys == {"info", "messages", "other"}
    assert s.closed
    s2 = default_checks._TopLevelKeyScanner()
    s2.feed('[{"messages": []}]')
    assert s2.closed and s2.keys == set()


def test_extract_from_file_finds_messages_past_64k(tmp_path):
    # Regression: three of the 50 public-audit trajectories carry
    # "messages" past byte 64 KiB (large leading "info" object), and
    # a fixed 64 KiB sniff prefix read them as "no tool records"
    # (every check NOT OBSERVED). The scanner must find the key
    # wherever it sits.
    traj = tmp_path / "run.traj.json"
    padding = "x" * (100 * 1024)
    traj.write_text(json.dumps({
        "info": {"model_stats": {"instance_cost": 0.5},
                 "padding": padding},
        "messages": [
            {"role": "assistant",
             "content": "```bash\npytest tests/test_a.py\n```"},
            {"role": "user", "content": [
                {"type": "text",
                 "text": "<returncode>0</returncode>\nPASSED"}]},
        ]}), encoding="utf-8")
    assert traj.stat().st_size > 64 * 1024
    ev = default_checks.extract_from_file(str(traj))
    assert ev["source"] == "traj"
    assert [c["command"] for c in ev["commands"]] == [
        "pytest tests/test_a.py"]
    assert ev["commands"][0]["outcome"] is True
    assert ev["recorded_cost"] == 0.5


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


# --- heredoc writes are not test/build runs ---------------------------


HEREDOC_WRITE = (
    "cat <<'EOF' > test_fix.py\n"
    "import unittest\n"
    "from unittest.mock import Mock\n"
    "print('pytest')\n"
    "EOF")


def test_classify_command_heredoc_write_is_not_a_test_or_build():
    # The write's rc 0 is the file creation succeeding, not a passing
    # test: the body mentions unittest/pytest only because that is
    # what the written script contains. Regression: three of the
    # 50-trace audit's seven D1 VERIFIED verdicts rested on such a
    # write (django__django-11532, django__django-14493,
    # sphinx-doc__sphinx-7910).
    assert default_checks.classify_command(HEREDOC_WRITE) == (None, [])
    # Append form, also seen in the audit data.
    assert default_checks.classify_command(
        "cat <<'EOF' >> tests/test_x.py\nimport unittest\nEOF") == (None, [])
    # Redirect before the heredoc marker.
    assert default_checks.classify_command(
        "cat > test_fix.py <<'EOF'\nimport unittest\nEOF") == (None, [])
    # A heredoc write chained with a genuine run in the same fence:
    # the write is ignored, the run still classifies.
    kind, _targets = default_checks.classify_command(
        HEREDOC_WRITE + "\npytest -q")
    assert kind == "test"
    # Plain `cat` of a test file is not a run either.
    assert default_checks.classify_command(
        "cat tests/test_a.py")[0] is None


def _write_traj_with_fences(tmp_path, fences):
    """Write a mini-SWE-agent traj whose assistant messages are the
    given (bash text, returncode-or-None) fences in order."""
    messages = []
    for bash_text, rc in fences:
        messages.append({"role": "assistant",
                         "content": "```bash\n%s\n```" % bash_text})
        if rc is not None:
            messages.append({"role": "user", "content": [
                {"type": "text",
                 "text": "<returncode>%d</returncode>" % rc}]})
    traj = tmp_path / "run.traj.json"
    traj.write_text(json.dumps({
        "info": {"model_stats": {"instance_cost": 0.5}},
        "messages": messages}), encoding="utf-8")
    return str(traj)


def _traj_d1_d2(tmp_path, fences):
    ev = default_checks.extract_traj(_write_traj_with_fences(
        tmp_path, fences))
    return _verdicts(default_checks.judge_default_checks(
        default_checks.merge_evidence([ev]), 0.5))


def test_d1_heredoc_write_alone_is_not_observed(tmp_path):
    verdicts = _traj_d1_d2(tmp_path, [(HEREDOC_WRITE, 0)])
    assert verdicts["D1"] == "NOT OBSERVED"
    assert verdicts["D2"] == "NOT OBSERVED"


def test_d1_heredoc_write_plus_genuine_pytest_is_verified(tmp_path):
    verdicts = _traj_d1_d2(tmp_path, [(HEREDOC_WRITE, 0),
                                      ("pytest -q", 0)])
    assert verdicts["D1"] == "VERIFIED"


def test_d1_heredoc_write_plus_failing_pytest_is_failed(tmp_path):
    verdicts = _traj_d1_d2(tmp_path, [(HEREDOC_WRITE, 0),
                                      ("pytest -q", 1)])
    assert verdicts["D1"] == "FAILED"


WAVE2_TRAJS = os.path.expanduser(
    "~/workspace/research/averth-strategy-2026-11-11/self-serve-scan"
    "/wave2/trajs")


@pytest.mark.skipif(not os.path.isdir(WAVE2_TRAJS),
                    reason="wave 2 audit trajectories not present")
def test_d1_audit_traces_heredoc_verdicts_corrected():
    # The three audit traces whose D1 VERIFIED rested on a heredoc
    # write's rc 0. django__django-11532 also ran a genuine pytest
    # (rc 1), so it judges FAILED on that run; the other two ran no
    # genuine test command, so they judge NOT OBSERVED.
    expected = {"django__django-11532": "FAILED",
                "django__django-14493": "NOT OBSERVED",
                "sphinx-doc__sphinx-7910": "NOT OBSERVED"}
    for instance, verdict in expected.items():
        ev = default_checks.extract_traj(os.path.join(
            WAVE2_TRAJS, instance + ".traj.json"))
        checks = default_checks.judge_default_checks(
            default_checks.merge_evidence([ev]), 0.5)
        assert _verdicts(checks)["D1"] == verdict, instance


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
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "VERIFIED"
    assert "name matching only" in checks[2]["observation"]
    assert "named tests passed" in checks[2]["observation"]
    ev = _evidence(commands=[_cmd("pytest tests/test_other.py", True)],
                   edited=["averth/cli.py"])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "FAILED"
    assert "averth/cli.py" in checks[2]["observation"]


def test_d3_named_run_outcome_gates_the_verdict():
    # A named run that FAILED cannot VERIFY the touched files, even
    # when every stem matches — D3's own citation says it failed.
    ev = _evidence(commands=[_cmd("pytest tests/test_cli.py", False)],
                   edited=["averth/cli.py"])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "FAILED"
    assert "named tests failed" in checks[2]["observation"]
    # A named run with an unknown outcome is NOT OBSERVED, not
    # VERIFIED on name matching alone.
    ev = _evidence(commands=[_cmd("pytest tests/test_cli.py", None)],
                   edited=["averth/cli.py"])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "NOT OBSERVED"
    assert "outcome is unknown" in checks[2]["observation"]
    # A failing named run with unmatched files is still FAILED.
    ev = _evidence(commands=[_cmd("pytest tests/test_other.py", False)],
                   edited=["averth/cli.py"])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "FAILED"


def test_d3_uses_only_the_last_test_command():
    ev = _evidence(
        commands=[_cmd("pytest tests/test_cli.py", True),
                  _cmd("pytest tests/test_other.py", True)],
        edited=["averth/cli.py"])
    # The earlier matching run does not save the later one.
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D3"] == "FAILED"


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


def test_d1_mixed_source_note_names_earlier_passing_runs():
    ev = _evidence(commands=[_cmd("pytest", True), _cmd("pytest", None)])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D1"] == "NOT OBSERVED"
    assert "1 earlier test run(s) passed" in checks[0]["observation"]
    assert "latest run's outcome is unknown" in checks[0]["observation"]


def test_d3_mixed_source_note_names_earlier_passing_runs():
    ev = _evidence(commands=[_cmd("pytest", True), _cmd("pytest", None)],
                   edited=["averth/cli.py"])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D3"] == "NOT OBSERVED"
    assert "1 earlier test run(s) passed" in checks[2]["observation"]


def test_d3_traj_format_limitation_is_stated(tmp_path):
    traj = tmp_path / "run.traj.json"
    traj.write_text(json.dumps({
        "info": {"model_stats": {"instance_cost": 0.1}},
        "messages": [
            {"role": "assistant",
             "content": "```bash\nls\n```"},
            {"role": "user", "content": [
                {"type": "text", "text": "<returncode>0</returncode>"}]},
        ]}), encoding="utf-8")
    ev = default_checks.merge_evidence(
        [default_checks.extract_traj(str(traj))])
    checks = default_checks.judge_default_checks(ev, 0.1)
    assert _verdicts(checks)["D3"] == "NOT OBSERVED"
    assert "mini-SWE-agent edits files via bash" in \
        checks[2]["observation"]


def test_jsonl_trace_not_observed_states_format_limitation(tmp_path):
    plain = tmp_path / "events.jsonl"
    plain.write_text(json.dumps({"type": "model", "case_id": "x"}) + "\n",
                     encoding="utf-8")
    ev = default_checks.merge_evidence(
        [default_checks.extract_from_file(str(plain))])
    checks = default_checks.judge_default_checks(ev, 0.01)
    assert all(c["verdict"] == "NOT OBSERVED" for c in checks)
    assert "carry no tool-use records" in checks[0]["observation"]
    assert "carry no tool-use records" in checks[2]["observation"]
    assert "carry no tool-use records" in checks[3]["observation"]


def test_d4_threshold_five_duplicates_fail():
    ev = _evidence(commands=[_cmd("pytest", True),
                             _cmd("pytest", True)])
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D4"] == "VERIFIED"
    assert "1 duplicate invocation" in checks[3]["observation"]
    ev = _evidence(commands=[_cmd("pytest", True)] * 5)
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D4"] == "VERIFIED"
    assert "4 duplicate invocation" in checks[3]["observation"]
    ev = _evidence(commands=[_cmd("pytest", True)] * 6)
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D4"] == "FAILED"
    assert "5 duplicate invocation" in checks[3]["observation"]
    assert "retry" not in checks[3]["name"].lower()
    assert checks[3]["name"] == "duplicate-invocation overhead"
    assert "retries" not in checks[3]["observation"].lower()
    assert "duplicate-invocation overhead" in checks[3]["observation"]
    assert "pinned judgment call" in checks[3]["observation"]
    assert "threshold: 5+ fails" in checks[3]["observation"]
    ev = _evidence(commands=[])
    assert _verdicts(
        default_checks.judge_default_checks(ev, 0.0))["D4"] == "NOT OBSERVED"


def test_d5_within_five_percent_verifies():
    ev = _evidence(recorded=1.00, claude_sessions=1, claude_with_cost=1)
    assert _verdicts(default_checks.judge_default_checks(
        ev, 1.04))["D5"] == "VERIFIED"
    assert _verdicts(default_checks.judge_default_checks(
        ev, 1.06))["D5"] == "FAILED"


def test_d5_recorded_zero_is_a_recorded_cost_not_an_absence(tmp_path):
    path = _claude_session(tmp_path, cost=0.0)
    ev = default_checks.merge_evidence(
        [default_checks.extract_claude(str(path))])
    assert ev["recorded_cost"] == 0.0
    checks = default_checks.judge_default_checks(ev, 0.0)
    assert _verdicts(checks)["D5"] == "VERIFIED"
    checks = default_checks.judge_default_checks(ev, 1.0)
    assert _verdicts(checks)["D5"] == "FAILED"
    assert "recorded $0.0000" in checks[4]["observation"]
    assert "inf" not in checks[4]["observation"]
    assert "no ratio" in checks[4]["observation"]


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
        {"id": "D5", "name": "trace-recorded vs estimated cost",
         "verdict": "FAILED",
         "observation": "recorded $0.0500 vs metered estimate $0.0210"},
    ]
    text = receipt_mod.render_receipt(
        sources=["claude/session-1.jsonl"], estimated_cost=0.021,
        recorded_cost=0.05, checks=checks, unknown_rate=0.0)
    assert "# Averth Agent PR Receipt (trace-observed)" in text
    assert "Verified Agent PR Receipt" not in text
    assert "Outcome: 2 of 2 checks resolved, 1 FAILED, 0 unknown" in text
    assert "Metered estimate (total) | $0.02 ESTIMATED" in text
    assert ("Recorded cost (trace-reported, not verified against any "
            "invoice or bill) | $0.05") in text
    assert "| D1 tests executed | VERIFIED |" in text
    assert "Unknown rate: 0.0%" in text
    assert "Bar: under 15% for a resolvable receipt" in text
    assert "This receipt is under the bar." in text
    assert "On the 50-trace public audit" in text
    assert "median 3.22x, 0/50 within 10%" in text
    assert "## What to do next" in text
    assert "Paste this whole receipt into the PR description." in text
    assert "reconcile against the invoice first (D5 FAILED)" in text
    assert "No cost per accepted outcome" in text
    assert "Estimates are not bills" in text
    assert "The recorded figure is what the trace reports" in text
    assert "does not verify it against any invoice or bill" in text
    assert "trace-observed, not human-written" in text


def test_receipt_unknown_rate_over_bar_states_the_implication():
    checks = [{"id": "D1", "name": "tests executed",
               "verdict": "NOT OBSERVED",
               "observation": "no test command observed in trace"}]
    text = receipt_mod.render_receipt(
        sources=[], estimated_cost=0.01, recorded_cost=None,
        checks=checks, unknown_rate=1.0)
    assert "At 100.0%, treat the FAILED/NOT OBSERVED rows as unproven" \
        in text
    assert "do not present this receipt as verification" in text
    assert "1 of 1 checks could not be resolved" in text


def test_receipt_what_to_do_next_ready_when_all_resolve():
    checks = [{"id": "D1", "name": "tests executed",
               "verdict": "VERIFIED", "observation": "ok"}]
    text = receipt_mod.render_receipt(
        sources=[], estimated_cost=0.01, recorded_cost=0.01,
        checks=checks, unknown_rate=0.0)
    assert "Ready to paste as-is." in text


def test_receipt_records_two_dp_in_table_four_dp_in_observation():
    checks = [{"id": "D5", "name": "trace-recorded vs estimated cost",
               "verdict": "FAILED",
               "observation": "recorded $0.3205 vs metered estimate "
                              "$0.9832 (4dp figures; ratio 3.07x; agree "
                              "within 5%)"}]
    text = receipt_mod.render_receipt(
        sources=["x.traj.json"], estimated_cost=0.9832,
        recorded_cost=0.3205, checks=checks, unknown_rate=0.0)
    assert "| $0.32 |" in text
    assert "recorded $0.3205 vs metered estimate $0.9832" in text


def test_receipt_suppresses_ratio_when_recorded_is_zero():
    checks = [{"id": "D5", "name": "trace-recorded vs estimated cost",
               "verdict": "FAILED",
               "observation": "recorded $0.0000 vs metered estimate "
                              "$1.0000; no ratio (recorded cost is "
                              "$0.00)"}]
    text = receipt_mod.render_receipt(
        sources=["claude/s.jsonl"], estimated_cost=1.0,
        recorded_cost=0.0, checks=checks, unknown_rate=0.0)
    assert "Metered estimate / recorded cost" not in text
    assert "ZeroDivisionError" not in text


def test_receipt_source_kind_labels_an_explicit_trace():
    checks = []
    text = receipt_mod.render_receipt(
        sources=["django-15930.traj.json"],
        source_kind="mini-SWE-agent trajectory",
        estimated_cost=0.98, recorded_cost=0.3205, checks=checks,
        unknown_rate=0.6)
    assert ("Source: `django-15930.traj.json` (mini-SWE-agent "
            "trajectory)") in text
    assert "Source sessions:" not in text
    text = receipt_mod.render_receipt(
        sources=["claude/s.jsonl"], estimated_cost=0.02,
        recorded_cost=None, checks=checks, unknown_rate=1.0)
    assert "Source sessions: `claude/s.jsonl`" in text


def test_receipt_escapes_hostile_session_names():
    checks = [{"id": "D1", "name": "tests executed",
               "verdict": "NOT OBSERVED",
               "observation": "no test command observed in trace"}]
    hostile = ("claude/a`b<img src=x onerror=alert(1)>evil|name\n"
               "[x](https://example.com)\x7f")
    text = receipt_mod.render_receipt(
        sources=[hostile], estimated_cost=0.01, recorded_cost=None,
        checks=checks, unknown_rate=1.0)
    assert "evil\\|name" in text
    assert "[x](https://example.com)" not in text
    assert "\n[x]" not in text
    assert "<img" not in text
    # The hostile backtick is escaped, never bare in the source text.
    assert "a\\`b" in text
    assert "\x7f" not in text


def test_receipt_escapes_hostile_commands_in_observations():
    checks = [{"id": "D1", "name": "tests executed",
               "verdict": "NOT OBSERVED",
               "observation": "`pytest` ran <img src=x onerror=alert(1)>"}]
    text = receipt_mod.render_receipt(
        sources=["claude/s.jsonl"], estimated_cost=0.01,
        recorded_cost=None, checks=checks, unknown_rate=1.0)
    assert "<img" not in text
    assert "&lt;img" in text


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
    checks = [{"id": "D5", "name": "trace-recorded vs estimated cost",
               "verdict": "EXTERNAL-UNVERIFIABLE", "observation": "x"}]
    text = receipt_mod.render_receipt(
        sources=["codex/r.jsonl"], estimated_cost=0.02,
        recorded_cost=0.05,
        recorded_note=receipt_mod.recorded_note_for(checks),
        checks=checks, unknown_rate=0.2)
    assert "not comparable: Codex subscription billing" in text
    assert "Metered estimate / recorded cost" not in text


def test_receipt_recorded_note_for_codex():
    checks = [{"id": "D5", "name": "trace-recorded vs estimated cost",
               "verdict": "EXTERNAL-UNVERIFIABLE", "observation": "x"}]
    assert receipt_mod.recorded_note_for(checks) is not None
    assert "subscription" in receipt_mod.recorded_note_for(checks)
    checks = [{"id": "D5", "name": "trace-recorded vs estimated cost",
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
    assert "Run Claude Code or Codex once" in err
    assert "averth try <trace-file>" in err


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
    assert "# Averth Agent PR Receipt (trace-observed)" in receipt
    assert "D5 trace-recorded vs estimated cost" in receipt
    assert "EXTERNAL-UNVERIFIABLE" in receipt  # Codex present
    assert "Averth Agent PR Receipt (trace-observed)" in out  # printed
    assert "copy from the line below to the end of the output" in out
    assert "Local scan: 2 session(s) scanned (of 2 found)" in out
    assert "Default checks (trace-observed):" in out


def test_cli_scan_reports_total_found_past_the_cap(tmp_path, monkeypatch,
                                                   capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    for i in range(12):
        p = _claude_session(tmp_path, name="s%02d.jsonl" % i)
        _touch(p, 1000 + i)
    rc = main(["try"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "10 session(s) scanned (of 12 found; newest 10)" in out


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
    assert str(bad) in err
    assert "meter one file explicitly" in err


def test_cli_scan_no_usage_is_exit_2_with_next_step(tmp_path, monkeypatch,
                                                    capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Tool records but no usage records: the importer meters nothing.
    path = tmp_path / ".claude" / "projects" / "proj" / "s.jsonl"
    records = [
        _claude_assistant("msg_01", content=[
            _bash_use("call_1", "pytest")]),
        _claude_tool_result("call_1", False),
    ]
    _write_jsonl(path, records)
    rc = main(["try"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no usage records found" in err
    assert "averth try <trace-file>" in err


def test_cli_scan_subagent_only_is_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _codex_rollout(tmp_path, name="sub.jsonl", subagent=True)
    rc = main(["try"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "subagent rollout(s) found but excluded" in err
    assert "pass a rollout file explicitly" in err


def test_cli_scan_rejects_format_and_model_flags(tmp_path, monkeypatch,
                                                 capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _claude_session(tmp_path)
    assert main(["try", "--format", "traj"]) == 2
    err = capsys.readouterr().err
    assert "--format" in err
    assert main(["try", "--model", "gpt-5"]) == 2
    err = capsys.readouterr().err
    assert "--model" in err
    assert main(["try", "--format", "traj", "--model", "gpt-5"]) == 2
    err = capsys.readouterr().err
    assert "--format" in err and "--model" in err
    assert main(["try", "--recorded", "0.05"]) == 2
    err = capsys.readouterr().err
    assert "--recorded" in err
    assert "trace's own recorded cost" in err


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
    assert "# Averth Agent PR Receipt (trace-observed)" in receipt
    assert "D5 trace-recorded vs estimated cost" in receipt
    assert "Source: `django-15930.traj.json` (mini-SWE-agent " \
        "trajectory)" in receipt
    # Case study: recorded $0.3205 vs metered estimate $0.98 -> FAILED.
    assert "recorded $0.3205" in receipt
    assert "FAILED" in receipt
    # Explicit mode writes the receipt file but does not print it.
    assert "Averth Agent PR Receipt (trace-observed)" not in out
    assert "Receipt written to" in out
    assert "Markdown for pasting into a GitHub PR description" in out
    # D5 FAILED: the P&L must not call the run clean.
    assert "No material findings" not in out
    assert "Default checks (trace-observed):" in out


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

# --- collision guards ---------------------------------------------------


def test_cli_receipt_equal_to_html_is_refused(tmp_path, monkeypatch,
                                              capsys):
    monkeypatch.chdir(tmp_path)
    traj = os.path.join(REPO, "try-it", "fixtures",
                        "django-15930.traj.json")
    for extra in ([], ["--force"]):
        rc = main(["try", traj, "--model", "claude-sonnet-4-20250514",
                   "--out", "same.html", "--receipt", "same.html"]
                  + extra)
        assert rc == 2
        assert "same as the HTML report path" in capsys.readouterr().err
        assert not (tmp_path / "same.html").exists()


def test_cli_receipt_equal_to_trace_is_refused_and_trace_survives(
        tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    src = os.path.join(REPO, "try-it", "fixtures",
                       "django-15930.traj.json")
    copy = tmp_path / "copy.traj.json"
    copy.write_bytes(open(src, "rb").read())
    before = copy.read_bytes()
    rc = main(["try", str(copy), "--model", "claude-sonnet-4-20250514",
               "--receipt", str(copy), "--force"])
    assert rc == 2
    assert "same as the input trace" in capsys.readouterr().err
    assert copy.read_bytes() == before


def test_cli_out_equal_to_trace_is_refused_and_trace_survives(
        tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    src = os.path.join(REPO, "try-it", "fixtures",
                       "django-15930.traj.json")
    copy = tmp_path / "copy.traj.json"
    copy.write_bytes(open(src, "rb").read())
    before = copy.read_bytes()
    rc = main(["try", str(copy), "--model", "claude-sonnet-4-20250514",
               "--out", str(copy), "--force"])
    assert rc == 2
    assert "same as the input trace" in capsys.readouterr().err
    assert copy.read_bytes() == before


def test_cli_receipt_is_a_directory_with_force_writes_nothing(
        tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "receiptdir").mkdir()
    traj = os.path.join(REPO, "try-it", "fixtures",
                        "django-15930.traj.json")
    rc = main(["try", traj, "--model", "claude-sonnet-4-20250514",
               "--receipt", "receiptdir", "--force"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "is a directory" in err
    assert not (tmp_path / "django-15930-try.html").exists()


def test_cli_scan_receipt_equal_to_html_is_refused(tmp_path, monkeypatch,
                                                   capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _claude_session(tmp_path)
    rc = main(["try", "--out", "same.html", "--receipt", "same.html",
               "--force"])
    assert rc == 2
    assert "same as the HTML report path" in capsys.readouterr().err
    assert not (tmp_path / "same.html").exists()


def test_cli_explicit_fifo_trace_is_refused(tmp_path, monkeypatch,
                                            capsys):
    monkeypatch.chdir(tmp_path)
    fifo = tmp_path / "pipe.traj.json"
    os.mkfifo(fifo)
    rc = main(["try", str(fifo), "--model", "claude-sonnet-4-20250514"])
    assert rc == 2
    assert "not a regular file" in capsys.readouterr().err
