"""Tests for wave 3: universal ingestion to any workflow shape.

No test here makes a network call, executes a transcript
command, or uses a credential. The only executions are
operator approved allowlist runs of tiny local scripts in
tmp directories, and the CLI observe mode on tmp fixtures.
Unknown input must never crash and never become a false
VERIFIED or FAILED: it becomes NOT OBSERVED with the
missing evidence named.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evidence_ledger import parse_time, snapshot_repo
from universal_ingest import (
    detect_runner,
    infer_checks_from_runs,
    ingest_text,
    parse_any_time,
    record_to_run,
)
from verifier import judge, run_via_allowlist


def _run(command, exit_code=0, label="r", start="2026-11-04T01:00:00Z"):
    return {
        "label": label,
        "command_raw": command,
        "command_normalized": command,
        "working_directory": "",
        "start_timestamp": start,
        "end_timestamp": start,
        "exit_code": exit_code,
        "output_digest": "sha256:x",
        "source": "imported",
        "trust_tier": 1,
    }


def _check(cid, command):
    return {"id": cid, "text": "t", "check_type": "recorded_run",
            "required_command": command, "applicability": "applies"}


def test_ingest_python_json():
    runs, s = ingest_text(json.dumps({"runs": [{
        "id": "run-1", "command": "python -m pytest -q test_a.py",
        "start_timestamp": "2026-11-04T01:00:00Z", "exit_code": 0}]}))
    assert len(runs) == 1 and s["runs"] == 1
    assert runs[0]["label"] == "run-1"
    assert runs[0]["runner"] == "python"
    assert runs[0]["command_raw"] == "python -m pytest -q test_a.py"


def test_ingest_node_rust_go_shell():
    text = "\n".join([
        json.dumps({"command": "npm test", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"}),
        json.dumps({"command": "cargo test", "exit_code": 1, "start_timestamp": "2026-11-04T01:00:00Z"}),
        json.dumps({"command": "go test ./...", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"}),
        json.dumps({"command": "sh build.sh", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"}),
    ])
    runs, s = ingest_text(text)
    assert [r["runner"] for r in runs] == ["npm", "cargo", "go", "sh"]
    assert [r["exit_code"] for r in runs] == [0, 1, 0, 0]


def test_runner_detection_all_listed():
    for cmd, want in [
        ("pytest -q", "pytest"), ("yarn test", "yarn"), ("pnpm test", "pnpm"),
        ("gradle test", "gradle"), ("mvn test", "mvn"), ("dotnet test", "dotnet"),
        ("phpunit", "phpunit"), ("rspec", "rspec"), ("jest", "jest"),
        ("vitest run", "vitest"), ("make test", "make"), ("docker run app", "docker"),
    ]:
        assert detect_runner(cmd) == want, cmd
    assert detect_runner("zig build") == "generic"
    assert detect_runner("") == "unknown"


def test_check_judged_only_from_own_runner():
    runs = [_run("npm test", 0, "npm-run"), _run("cargo test", 1, "cargo-run")]
    row = judge(_check("C1", "cargo test"), runs, {}, "2026-11-04T00:00:00Z")
    assert row["status"] == "FAILED"
    assert row["evidence_id"] == "cargo-run"
    row2 = judge(_check("C2", "npm test"), runs, {}, "2026-11-04T00:00:00Z")
    assert row2["status"] == "VERIFIED" and row2["evidence_id"] == "npm-run"
    row3 = judge(_check("C3", "go test ./..."), runs, {}, "2026-11-04T00:00:00Z")
    assert row3["status"] == "NOT OBSERVED"


def test_multilanguage_repo_mixed_runs():
    runs, _ = ingest_text(json.dumps([
        {"command": "python -m pytest -q", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"},
        {"command": "npm test", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"},
        {"command": "cargo test", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"},
    ]))
    assert len(runs) == 3
    for cmd in ("python -m pytest -q", "npm test", "cargo test"):
        assert judge(_check("X", cmd), runs, {}, "2026-11-04T00:00:00Z")["status"] == "VERIFIED"


def test_frontend_build_and_lint():
    runs, _ = ingest_text(json.dumps([
        {"command": "npm run build", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"},
        {"command": "npm run lint", "exit_code": 1, "start_timestamp": "2026-11-04T01:00:00Z"},
    ]))
    assert judge(_check("B", "npm run build"), runs, {}, "2026-11-04T00:00:00Z")["status"] == "VERIFIED"
    assert judge(_check("L", "npm run lint"), runs, {}, "2026-11-04T00:00:00Z")["status"] == "FAILED"


def test_no_tests_workflow_never_passes():
    runs, _ = ingest_text(json.dumps([
        {"command": "npm run build", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"},
    ]))
    checks = infer_checks_from_runs(runs)
    assert len(checks) == 1 and checks[0]["check_type"] == "inferred"
    row = judge(checks[0], runs, {}, "2026-11-04T00:00:00Z")
    assert row["status"] == "NOT OBSERVED"
    assert "inferred_not_human" in row["flags"]
    assert "INFERRED" in row["scope_limitation"]


def test_no_exit_code_is_not_observed_not_failed():
    runs = [_run("cargo test", None, "no-exit")]
    row = judge(_check("C1", "cargo test"), runs, {}, "2026-11-04T00:00:00Z")
    assert row["status"] == "NOT OBSERVED"
    assert "missing_exit_code" in row["flags"]


def test_malformed_jsonl_does_not_crash():
    text = '{"command": "npm test", "exit_code": 0}\nnot json at all\n{"command": "cargo test", "exit_code": 0}\n'
    runs, s = ingest_text(text)
    assert len(runs) == 2
    assert s["unparseable"] == 1


def test_otel_span_records():
    spans = [
        {"name": "test run", "spanId": "s1", "traceId": "t1",
         "attributes": {"command": "npm test"},
         "startTimeUnixNano": 1760000000000000000, "endTimeUnixNano": 1760000060000000000,
         "status": {"code": "STATUS_CODE_OK"}},
        {"name": "test run", "spanId": "s2", "traceId": "t1",
         "attributes": {"command": "cargo test"},
         "startTimeUnixNano": 1760000000000000000, "endTimeUnixNano": 1760000060000000000,
         "status": {"code": "STATUS_CODE_UNSET"}},
    ]
    runs, _ = ingest_text(json.dumps(spans))
    assert len(runs) == 2
    assert runs[0]["exit_code"] == 0 and runs[0]["label"] == "s1"
    assert runs[1]["exit_code"] is None
    assert runs[0]["start_timestamp"] is not None


def test_otel_span_name_alone_never_becomes_a_run():
    spans = [{"name": "npm test", "spanId": "s9", "traceId": "t9",
              "startTimeUnixNano": 1760000000000000000,
              "endTimeUnixNano": 1760000060000000000,
              "status": {"code": "STATUS_CODE_OK"}}]
    runs, summary = ingest_text(json.dumps(spans))
    assert runs == []
    assert summary["events_without_command"] == 1


def test_plain_text_log_blocks_and_shell_lines():
    text = "label: node run\ncommand: npm test\nstart_timestamp: 2026-11-04T01:00:00Z\nexit_code: 0\n\n$ cargo test exit 1\n"
    runs, s = ingest_text(text)
    assert len(runs) == 2
    assert runs[0]["command_raw"] == "npm test"
    assert runs[1]["command_raw"] == "cargo test" and runs[1]["exit_code"] == 1


def test_pretty_json_and_array_and_unknown_fields():
    pretty = '{\n  "command": "go test ./...",\n  "exit_code": 0,\n  "weird_field": "kept"\n}\n'
    runs, _ = ingest_text(pretty)
    assert len(runs) == 1 and runs[0]["raw_record"]["weird_field"] == "kept"
    runs2, _ = ingest_text('[{"command": "make test", "exit_code": 0}]')
    assert runs2[0]["runner"] == "make"


def test_parse_any_time_epoch_and_common_forms():
    assert parse_any_time(1760000000) is not None
    assert parse_any_time(1760000000000) is not None
    assert parse_any_time(1760000000000000000) is not None
    assert parse_any_time("1760000000") is not None
    assert parse_any_time("2026-11-04 01:00:00") is not None
    assert parse_any_time("2026/11/04 01:00:00") is not None
    assert parse_any_time("not a time") is None
    assert parse_any_time(None) is None
    assert parse_time("1760000000") is not None
    assert parse_time("2026-11-04 01:00:00") is not None


def test_numeric_out_of_range_epoch_never_crashes():
    for bad in (999999999999, 253402300800, 1e30, -1e30):
        assert parse_any_time(bad) is None
        runs, s = ingest_text(json.dumps([{"command": "npm test", "exit_code": 0,
                                           "start_timestamp": bad}]))
        assert len(runs) == 1
        assert runs[0]["start_timestamp"] is None
    assert parse_time(999999999999) is None


def test_unparseable_timestamp_is_not_observed():
    runs = [_run("npm test", 0, "bad-time", start="whenever")]
    row = judge(_check("C1", "npm test"), runs, {}, "2026-11-04T00:00:00Z")
    assert row["status"] == "NOT OBSERVED"


def test_artifact_any_repo_digest(tmp_path):
    (tmp_path / "main.rs").write_text("fn main() {}")
    (tmp_path / "app.js").write_text("console.log(1)")
    (tmp_path / "app.bin").write_bytes(b"\x00\x01\x02")
    snap, _ = snapshot_repo(tmp_path)
    for name in ("main.rs", "app.js", "app.bin"):
        expected = "sha256:" + hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        assert snap[name] == expected


def test_allowlist_generic_runner_runs_and_refuses(tmp_path):
    script = tmp_path / "hello.sh"
    script.write_text("#!/bin/sh\necho hello\n")
    allow = {"workflow": "w", "approved_by": "op", "runner": "sh",
             "commands": [{"label": "hello", "command": "sh hello.sh"}]}
    run = run_via_allowlist("sh hello.sh", tmp_path, allow)
    assert run["exit_code"] == 0 and run["source"] == "allowlist_recorder"
    try:
        run_via_allowlist("sh other.sh", tmp_path, allow)
    except ValueError:
        return
    raise AssertionError("unlisted command should be refused")


def test_cli_observe_mode_never_passes(tmp_path):
    from cli import main
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "index.js").write_text("console.log(1)")
    ingest = tmp_path / "runs.json"
    ingest.write_text(json.dumps([{"command": "npm test", "exit_code": 0,
                                   "start_timestamp": "2026-11-04T01:00:00Z"}]))
    out = tmp_path / "out"
    rc = main(["--repo", str(repo), "--ingest", str(ingest),
               "--infer-checks", "--out", str(out), "--report-id", "wave3-observe"])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["coverage"]["criteria_total"] == 1
    assert ledger["judgments"][0]["status"] == "NOT OBSERVED"
    assert ledger["judgments"][0]["check_type"] == "inferred"
    assert ledger["ingest_summary"][0]["runs"] == 1


def test_cli_ingest_multilanguage_judges_human_checks(tmp_path):
    from cli import main
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")
    checks = tmp_path / "checks.json"
    checks.write_text(json.dumps({"task_intent": "multi", "task_intent_source": "test",
                                  "checks": [_check("C1", "cargo test"),
                                             _check("C2", "npm test")]}))
    ingest = tmp_path / "runs.jsonl"
    ingest.write_text(
        '{"command": "cargo test", "exit_code": 0, "start_timestamp": "2026-11-04T01:00:00Z"}\n'
        '{"command": "npm test", "exit_code": 1, "start_timestamp": "2026-11-04T01:00:00Z"}\n')
    out = tmp_path / "out"
    rc = main(["--repo", str(repo), "--checks", str(checks), "--ingest", str(ingest),
               "--out", str(out), "--report-id", "wave3-multi",
               "--final-edit-marker", "2026-11-04T00:00:00Z"])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    by_id = {j["criterion_id"]: j["status"] for j in ledger["judgments"]}
    assert by_id == {"C1": "VERIFIED", "C2": "FAILED"}


def test_record_preserves_id_and_verbatim_command():
    rec = {"id": "abc-123", "command": "  npm   test  ", "exit_code": 0}
    run = record_to_run(rec)
    assert run["label"] == "abc-123"
    assert run["command_raw"] == "  npm   test  "
