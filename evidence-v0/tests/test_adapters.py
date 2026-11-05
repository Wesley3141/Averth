"""Tests for wave 1 adapters: normalize fix, converter, allowlist, PR converter.

No test here executes a command taken from a transcript. The
converter tests assert that a destructive command string is
recorded as data and never run, by checking that a sentinel
file the string would create does not exist after conversion.
The allowlist execution test uses a command listed exactly in
a test allowlist, run through allowlist_runner, not a
transcript command.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pr_evidence_converter import convert as pr_convert
from recorded_run_converter import convert_json_text, convert_log_text
from runner_allowlist import load_allowlist, validate_command
from trace_adapter import normalize_command


def test_normalize_keeps_distinct_runners():
    assert normalize_command("npm test") == "npm test"
    assert normalize_command("cargo test") == "cargo test"
    assert normalize_command("make test") == "make test"
    assert normalize_command("go test ./...") == "go test ./..."
    assert normalize_command("npm test") != normalize_command("cargo test")
    assert normalize_command("cargo test") != normalize_command("make test")


def test_normalize_drops_only_python_interpreter():
    assert normalize_command("python -m pytest -q test_x.py") == "-m pytest -q test_x.py"
    assert normalize_command("python3 -m pytest -q test_x.py") == "-m pytest -q test_x.py"
    assert normalize_command("/venv/bin/python -m pytest -q test_x.py") == "-m pytest -q test_x.py"
    assert normalize_command("pytest -q test_x.py") == "pytest -q test_x.py"


def test_converter_json_mode_computes_digest():
    runs = convert_json_text(json.dumps({"runs": [
        {"label": "npm", "command": "npm test", "exit_code": 0, "stdout": "ok", "stderr": ""},
    ]}))
    assert len(runs) == 1
    assert runs[0]["command"] == "npm test"
    assert runs[0]["output_digest"].startswith("sha256:")


def test_converter_never_executes_transcript_command(tmp_path):
    sentinel = tmp_path / "should-not-exist.txt"
    text = json.dumps({"runs": [
        {"label": "evil", "command": f"touch {sentinel}", "exit_code": 0, "stdout": "", "stderr": ""},
    ]})
    runs = convert_json_text(text)
    assert runs[0]["command"] == f"touch {sentinel}"
    assert not sentinel.exists()


def test_converter_log_mode():
    text = (
        "label: npm run\ncommand: npm test\n"
        "start_timestamp: 2026-11-04T20:00:00Z\n"
        "end_timestamp: 2026-11-04T20:05:00Z\nexit_code: 0\nstdout: ok\n"
    )
    runs = convert_log_text(text)
    assert runs[0]["command"] == "npm test"
    assert runs[0]["exit_code"] == 0


def test_converter_rejects_missing_command():
    try:
        convert_json_text(json.dumps({"runs": [{"label": "x", "exit_code": 0}]}))
    except ValueError:
        return
    raise AssertionError("converter should reject a run with no command")


def _allowlist(tmp_path):
    data = {
        "workflow": "test",
        "approved_by": "test",
        "approved_date": "2026-11-04",
        "runner": "npm",
        "allowed_flags": ["test"],
        "allowed_relative_paths": [],
        "timeout_seconds": 60,
        "commands": [{"label": "npm tests", "command": "npm test"}],
    }
    p = tmp_path / "allowlist.json"
    p.write_text(json.dumps(data))
    return load_allowlist(str(p))


def test_allowlist_accepts_exact_listed_command(tmp_path):
    allowlist = _allowlist(tmp_path)
    assert validate_command("npm test", allowlist) is not None


def test_allowlist_rejects_unlisted_and_shell_commands(tmp_path):
    allowlist = _allowlist(tmp_path)
    assert validate_command("npm run lint", allowlist) is None
    assert validate_command("npm test; rm -rf /", allowlist) is None
    assert validate_command("npm test | sh", allowlist) is None
    assert validate_command("cargo test", allowlist) is None
    assert validate_command("npm test ../outside", allowlist) is None
    assert validate_command("npm test /abs/path", allowlist) is None


def test_pr_converter_separates_ci_runs_from_tier0_claims():
    fixture = {
        "pr_number": 999,
        "repo": "example/repo",
        "files_changed": ["src/main.rs"],
        "ci_runs": [{"label": "CI", "command": "cargo test", "exit_code": 0, "stdout": "ok", "stderr": ""}],
        "review_comments": [{"author": "A", "body": "checked", "claims": ["cargo test", "device checked manually"]}],
    }
    runs, claims = pr_convert(fixture)
    assert len(runs) == 1 and runs[0]["command"] == "cargo test"
    assert len(claims["tier0_claims"]) == 1
    assert claims["tier0_claims"][0]["claim"] == "device checked manually"
    assert claims["tier0_claims"][0]["tier"] == 0


def test_allowlist_runner_runs_only_listed_command(tmp_path):
    # Runner is python3, command is exactly listed, output is captured.
    # This proves the mechanism, not a transcript command: the
    # command comes from the test allowlist file, not from any log.
    # A script file is used, not -c code, because shlex splitting
    # strips quotes from -c arguments and would change the code.
    repo = Path(__file__).resolve().parent.parent
    cmd = f"{sys.executable} tests/fixtures/print_ok.py"
    allowlist_path = tmp_path / "allowlist.json"
    allowlist_path.write_text(json.dumps({
        "workflow": "test", "approved_by": "test", "approved_date": "2026-11-04",
        "runner": sys.executable, "allowed_flags": [], "allowed_relative_paths": [],
        "timeout_seconds": 60,
        "commands": [{"label": "print ok", "command": cmd}],
    }))
    out = tmp_path / "run.json"
    proc = subprocess.run(
        [sys.executable, "allowlist_runner.py", "--repo", str(repo),
         "--allowlist", str(allowlist_path), "--command", cmd,
         "--out", str(out), "--i-approved-this-allowlist"],
        cwd=str(repo),
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record = json.loads(out.read_text())
    assert record["exit_code"] == 0
    assert record["source"] == "allowlist_recorder"
    # Without the confirmation flag, nothing runs.
    out2 = tmp_path / "run2.json"
    proc2 = subprocess.run(
        [sys.executable, "allowlist_runner.py", "--repo", str(repo),
         "--allowlist", str(allowlist_path), "--command", cmd,
         "--out", str(out2)],
        cwd=str(repo),
        capture_output=True, text=True, timeout=60)
    assert proc2.returncode == 0
    assert not out2.exists()
