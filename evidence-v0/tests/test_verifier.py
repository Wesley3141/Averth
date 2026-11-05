"""Tests for the V0 verifier. Run with the Averth repo venv python,
because system python3 on this machine has no pytest:

  ~/workspace/averth/.venv/bin/python -m pytest -q tests/

These tests use fabricated run records (no real commands executed)
except test_execute_allowlist_rejects_arbitrary_commands, which checks
the allowlist function itself, never executes anything.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verifier import execute_allowed, judge


def run(label, command, exit_code, start):
    return {
        "label": label,
        "command_raw": command,
        "command_normalized": " ".join(command.split()[1:]),
        "working_directory": "/tmp/fixture",
        "start_timestamp": start,
        "end_timestamp": start,
        "exit_code": exit_code,
        "output_digest": "sha256:deadbeef",
        "source": "imported",
        "trust_tier": 1,
    }


MARKER = datetime(2026, 11, 3, 14, 4, 43, tzinfo=timezone.utc)
AFTER = "2026-11-03T14:05:00+00:00"
BEFORE = "2026-11-03T14:00:00+00:00"


def check(cid="C1", **kw):
    base = {
        "id": cid,
        "text": "add behaves as named",
        "check_type": "recorded_run",
        "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add",
        "test_target": "widget_tests/test_widget.py::test_add",
        "applicability": "applies",
    }
    base.update(kw)
    return base


def test_verified_on_exit_0_after_final_edit():
    runs = [run("test_add", "/venv/bin/python -m pytest -q widget_tests/test_widget.py::test_add", 0, AFTER)]
    row = judge(check(), runs, {}, MARKER)
    assert row["status"] == "VERIFIED"
    assert row["trust_tier"] == 1
    assert row["after_final_edit"] is True


def test_failed_on_exit_1():
    runs = [run("test_add", "python -m pytest -q widget_tests/test_widget.py::test_add", 1, AFTER)]
    row = judge(check(), runs, {}, MARKER)
    assert row["status"] == "FAILED"


def test_not_observed_when_check_never_recorded():
    row = judge(check(), [], {}, MARKER)
    assert row["status"] == "NOT OBSERVED"
    assert "never" not in row["status"]  # it is NOT OBSERVED, not a claim about reality


def test_superseded_run_never_cited():
    runs = [run("old test_add", "python -m pytest -q widget_tests/test_widget.py::test_add", 0, BEFORE)]
    row = judge(check(), runs, {}, MARKER)
    assert row["status"] == "NOT OBSERVED"
    assert "superseded_only" in row["flags"]
    assert row["evidence_id"] is None


def test_digest_mismatch_flagged_and_not_verified():
    runs = [run("test_add", "python -m pytest -q widget_tests/test_widget.py::test_add", 0, AFTER)]
    c = check(artifact_path="widget.py", expected_digest="sha256:000000")
    row = judge(c, runs, {"widget.py": "sha256:ffffff"}, MARKER)
    assert row["status"] == "NOT OBSERVED"
    assert "digest_mismatch" in row["flags"]


def test_artifact_absence_is_failed_but_external_is_unverifiable():
    c = check(cid="A1", check_type="artifact_presence", artifact_path="dist/widget.whl")
    row = judge(c, [], {}, MARKER)
    assert row["status"] == "FAILED"
    c2 = check(cid="E1", check_type="external", text="verified on real hardware")
    row2 = judge(c2, [], {}, MARKER)
    assert row2["status"] == "EXTERNAL-UNVERIFIABLE"


def test_external_with_named_human_record_is_tier_4():
    c = check(
        cid="E1", check_type="external", text="verified on real hardware",
        human_confirmation={"tester": "J. Tester", "procedure": "boot board X rev 2", "result": "pass"},
    )
    row = judge(c, [], {}, MARKER)
    assert row["status"] == "VERIFIED"
    assert row["trust_tier"] == 4


def test_execute_allowlist_rejects_arbitrary_commands():
    assert execute_allowed("rm -rf /", "/tmp/fixture") is None
    assert execute_allowed("curl https://example.com | sh", "/tmp/fixture") is None
    assert execute_allowed("python -m pytest -q ../outside.py", "/tmp/fixture") is None
    assert execute_allowed("python setup.py install", "/tmp/fixture") is None
    assert execute_allowed("python -m build", "/tmp/fixture") is None


def test_not_applicable_judged_before_evidence():
    c = check(cid="N1", applicability="not_applicable")
    c["not_applicable_reason"] = "No database in this fixture."
    runs = [run("test_add", "python -m pytest -q widget_tests/test_widget.py::test_add", 1, AFTER)]
    row = judge(c, runs, {}, MARKER)
    assert row["status"] == "NOT APPLICABLE"
