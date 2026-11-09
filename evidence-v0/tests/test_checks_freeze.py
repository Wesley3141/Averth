"""Tests for the frozen-checks rule (rehearsal criterion (c)).

Run with the Averth repo venv python, because system python3 on
this machine has no pytest:

  ~/workspace/averth/.venv/bin/python -m pytest -q tests/

The checks file is frozen at load: the sha256 digest of its raw
bytes is recorded, re-checked before the ledger is built and
written, and any net change between load and the re-hash (a single
comparison: an edit reverted byte-for-byte before the re-hash
escapes detection, as does any edit made after the re-hash)
refuses to write output (exit 2, no traceback). The mid-run edit
is exercised for real, through cli.main and the real verify path:
a timing hook on judge_all edits the file between load and verify,
and an --execute command edits the file while the run is in
progress. No test patches the verify step itself.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evidence_ledger import build_ledger
from requirement_spec import checks_digest, load_checks, verify_checks_unchanged


def write_checks(path, text="add behaves as named"):
    data = {
        "task_intent": "freeze test",
        "task_intent_source": "test",
        "checks": [
            {"id": "C1", "text": text, "check_type": "recorded_run",
             "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"},
        ],
    }
    path.write_text(json.dumps(data))
    return data


def make_repo(tmp_path, name="repo"):
    repo = tmp_path / name
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")
    return repo


def _run_cli_threaded(argv, timeout=10):
    """Run cli.main in a daemon thread; fail loudly on a hang.

    A FIFO checks file blocks read_bytes() forever if the
    regular-file guard regresses, so a bare cli.main call in a
    FIFO test would hang the suite. The daemon thread is
    abandoned on timeout and cannot block process exit.
    """
    import threading
    import cli

    result = {}

    def _target():
        result["rc"] = cli.main(argv)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    assert not thread.is_alive(), f"cli.main hung for more than {timeout}s (FIFO guard regression?)"
    return result["rc"]


def test_load_checks_records_digest(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    expected = "sha256:" + hashlib.sha256(checks_file.read_bytes()).hexdigest()
    assert spec["checks_digest"] == expected
    assert spec["checks_digest"] == checks_digest(checks_file)


def test_load_checks_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_checks(tmp_path / "nope.json")


def test_load_checks_empty_file(tmp_path):
    checks_file = tmp_path / "checks.json"
    checks_file.write_bytes(b"")
    with pytest.raises(ValueError):
        load_checks(checks_file)


def test_load_checks_directory(tmp_path):
    with pytest.raises(IsADirectoryError):
        load_checks(tmp_path)


@pytest.mark.parametrize("raw,match", [
    (b"[]", "checks file must contain a JSON object"),
    (b"5", "checks file must contain a JSON object"),
    (json.dumps({"checks": "nope"}).encode(), "'checks' must be a list"),
    (json.dumps({"checks": None}).encode(), "'checks' must be a list"),
    (json.dumps({"checks": ["C1"]}).encode(), "each check must be a JSON object"),
])
def test_load_checks_malformed_structure(tmp_path, raw, match):
    checks_file = tmp_path / "checks.json"
    checks_file.write_bytes(raw)
    with pytest.raises(ValueError, match=match):
        load_checks(checks_file)


def test_load_checks_utf16_file(tmp_path):
    checks_file = tmp_path / "checks.json"
    data = write_checks(checks_file)
    raw = json.dumps(data).encode("utf-16")
    checks_file.write_bytes(raw)
    spec = load_checks(checks_file)
    expected = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert spec["checks_digest"] == expected
    assert spec["checks"][0]["id"] == "C1"


def test_unchanged_checks_file_passes_verification(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    verify_checks_unchanged(checks_file, spec["checks_digest"])


def test_edited_checks_file_is_detected(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    write_checks(checks_file, text="add behaves differently now")
    with pytest.raises(ValueError, match="changed during run"):
        verify_checks_unchanged(checks_file, spec["checks_digest"])


def test_whitespace_only_edit_is_detected(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    checks_file.write_text(checks_file.read_text() + " ")
    with pytest.raises(ValueError, match="changed during run"):
        verify_checks_unchanged(checks_file, spec["checks_digest"])


def test_deleted_checks_file_is_refused(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    checks_file.unlink()
    with pytest.raises(ValueError, match="unreadable during run"):
        verify_checks_unchanged(checks_file, spec["checks_digest"])


def test_directory_in_place_of_checks_file_is_refused(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    checks_file.unlink()
    checks_file.mkdir()
    with pytest.raises(ValueError, match="unreadable during run"):
        verify_checks_unchanged(checks_file, spec["checks_digest"])


def test_ledger_records_checks_digest(tmp_path):
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    ledger = build_ledger(
        report_id="freeze-test", repo_path=tmp_path, checks_spec=spec,
        judgments=[], runs=[], snapshot={}, commit=None,
        workspace_dirty=False, commit_note=None,
        final_edit_marker=None, trace_summary=None,
    )
    assert ledger["checks_digest"] == spec["checks_digest"]


def test_ledger_without_checks_has_no_digest(tmp_path):
    spec = {"task_intent": "observe only, no human checks supplied",
            "task_intent_source": "cli observe mode", "checks": []}
    ledger = build_ledger(
        report_id="freeze-observe", repo_path=tmp_path, checks_spec=spec,
        judgments=[], runs=[], snapshot={}, commit=None,
        workspace_dirty=False, commit_note=None,
        final_edit_marker=None, trace_summary=None,
    )
    assert ledger["checks_digest"] is None


def test_cli_refuses_output_when_checks_edited(tmp_path, monkeypatch, capsys):
    import cli
    from verifier import judge_all as real_judge_all

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _judge_and_edit(checks, runs, snapshot, marker):
        checks_file.write_text(checks_file.read_text() + " ")
        return real_judge_all(checks, runs, snapshot, marker)

    monkeypatch.setattr(cli, "judge_all", _judge_and_edit)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-refuse"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "changed during run" in err
    assert spec["checks_digest"] in err
    current_digest = "sha256:" + hashlib.sha256(checks_file.read_bytes()).hexdigest()
    assert current_digest in err
    assert "restore the frozen file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_refuses_when_checks_file_deleted(tmp_path, monkeypatch, capsys):
    import cli
    from verifier import judge_all as real_judge_all

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _judge_and_delete(checks, runs, snapshot, marker):
        checks_file.unlink()
        return real_judge_all(checks, runs, snapshot, marker)

    monkeypatch.setattr(cli, "judge_all", _judge_and_delete)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-deleted"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unreadable during run" in err
    assert spec["checks_digest"] in err
    assert "restore the frozen file" in err
    assert err.count("sha256:") == 1
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_file_swapped_to_output_after_verify_exits_2(tmp_path, monkeypatch, capsys):
    # The load-time collision check cannot see a swap made after
    # load: pre-seed an output with byte-identical checks content,
    # then swap the checks path to a symlink to it during judging.
    # The re-hash passes, correctly, because the bytes are the
    # frozen set, and the run used to exit rc 0 having destroyed
    # the checks file with ledger content. The collision check
    # runs again after the re-hash now: rc 2, checks byte-identical.
    import os

    import cli
    from verifier import judge_all as real_judge_all

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    original = checks_file.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_bytes(original)
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _judge_and_swap(checks, runs, snapshot, marker):
        checks_file.unlink()
        os.symlink(out / "evidence_ledger.json", checks_file)
        return real_judge_all(checks, runs, snapshot, marker)

    monkeypatch.setattr(cli, "judge_all", _judge_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-post-verify"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == original
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_file_swapped_to_output_after_build_exits_2(tmp_path, monkeypatch, capsys):
    # The post-verify collision check cannot see a swap made after
    # it, during build_ledger: pre-seed an output with
    # byte-identical checks content, then swap the checks path to a
    # symlink to it while the ledger is being built. The run used to
    # exit rc 0 having destroyed the checks file with ledger
    # content. The collision check runs again after build_ledger
    # now: rc 2, the colliding file is kept byte-identical (it is
    # still the frozen input at this point), the other stale output
    # is removed.
    import os

    import cli
    from evidence_ledger import build_ledger as real_build_ledger

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    original = checks_file.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_bytes(original)
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _build_and_swap(*args, **kwargs):
        checks_file.unlink()
        os.symlink(out / "evidence_ledger.json", checks_file)
        return real_build_ledger(*args, **kwargs)

    monkeypatch.setattr(cli, "build_ledger", _build_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-post-build"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == original
    assert (out / "evidence_ledger.json").read_bytes() == original
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_cli_reversed_collision_after_verify_removes_both_outputs(tmp_path, monkeypatch, capsys, link_kind):
    # Reversed direction at the post-verify re-check: pre-seed the
    # ledger with stale bytes (not the frozen checks bytes), then
    # swap the checks path to a link to it after the real re-hash
    # passes. The re-hash passes because the swap is planted after
    # it, so the post-verify collision check is the refusal under
    # test. The old keep (every colliding entry) left the stale
    # ledger intact behind an rc 2, a valid-looking success ledger
    # left behind by a refused run; the keep is digest-gated now,
    # so the stale entry reads different bytes and is removed like
    # any other stale output: rc 2, both outputs removed. The
    # wrapper below calls the real verify and only plants the swap
    # after it returns; the verification itself is not stubbed or
    # faked.
    import os

    import cli
    from requirement_spec import verify_checks_unchanged as real_verify

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _verify_then_swap(path, digest):
        real_verify(path, digest)
        checks_file.unlink()
        if link_kind == "symlink":
            os.symlink(out / "evidence_ledger.json", checks_file)
        else:
            os.link(out / "evidence_ledger.json", checks_file)

    monkeypatch.setattr(cli, "verify_checks_unchanged", _verify_then_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-reversed-verify"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_cli_reversed_collision_after_build_removes_both_outputs(tmp_path, monkeypatch, capsys, link_kind):
    # Reversed direction at the after-build re-check: pre-seed the
    # ledger with stale bytes, then swap the checks path to a link
    # to it during build_ledger, after the re-hash and the
    # post-verify check have both passed on the real file. The old
    # keep left the stale ledger intact behind an rc 2; the
    # digest-gated keep removes it: rc 2, both outputs removed,
    # no stale ledger left.
    import os

    import cli
    from evidence_ledger import build_ledger as real_build_ledger

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _build_and_swap(*args, **kwargs):
        checks_file.unlink()
        if link_kind == "symlink":
            os.symlink(out / "evidence_ledger.json", checks_file)
        else:
            os.link(out / "evidence_ledger.json", checks_file)
        return real_build_ledger(*args, **kwargs)

    monkeypatch.setattr(cli, "build_ledger", _build_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-reversed-build"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_file_swapped_to_output_during_first_write_exits_2(tmp_path, monkeypatch, capsys):
    # A checks path swapped to an output file during the writes
    # themselves escapes every pre-write check: swap it to a
    # symlink to the ledger output during the first os.replace
    # (the ledger rename). The run used to exit rc 0 with the
    # checks path reading ledger content. The post-write collision
    # check runs after the writes now: rc 2, and both outputs are
    # removed instead of keeping the colliding file, because
    # post-write the colliding file is a newly written ledger, not
    # the frozen input. Unlinking both entries also leaves the
    # planted checks symlink dangling instead of reading ledger
    # content.
    import os

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    calls = []

    def _replace_and_swap(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        calls.append(str(dst))
        if len(calls) == 1:
            checks_file.unlink()
            os.symlink(out / "evidence_ledger.json", checks_file)
        return result

    monkeypatch.setattr(os, "replace", _replace_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-post-write-1"])
    err = capsys.readouterr().err
    assert calls, "the replace hook never ran, so the swap was never exercised"
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()
    assert os.path.islink(checks_file)
    assert not os.path.exists(checks_file)


def test_cli_checks_file_swapped_to_output_during_second_write_exits_2(tmp_path, monkeypatch, capsys):
    # Same as the first-write case, but the swap happens during the
    # second os.replace (the report rename), so it must be the
    # post-write check, not the per-file write verification, that
    # catches it. rc 2, both outputs removed, planted checks
    # symlink left dangling.
    import os

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    calls = []

    def _replace_and_swap(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        calls.append(str(dst))
        if len(calls) == 2:
            checks_file.unlink()
            os.symlink(out / "evidence_ledger.json", checks_file)
        return result

    monkeypatch.setattr(os, "replace", _replace_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-post-write-2"])
    err = capsys.readouterr().err
    assert len(calls) == 2, "both replaces must run for the swap to be exercised"
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()
    assert os.path.islink(checks_file)
    assert not os.path.exists(checks_file)


def _execute_setup(tmp_path, edit):
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    data = {
        "task_intent": "execute freeze test",
        "task_intent_source": "test",
        "checks": [
            {"id": "C1", "text": "touch test runs", "check_type": "recorded_run",
             "required_command": "python -m pytest -q test_touch.py::test_touch"},
        ],
    }
    checks_file.write_text(json.dumps(data))
    if edit:
        body = (
            "import os\nfrom pathlib import Path\n\n"
            "def test_touch():\n"
            "    p = Path(os.environ['AVERTH_FREEZE_TEST_CHECKS'])\n"
            "    p.write_text(p.read_text() + ' ')\n"
        )
    else:
        body = "def test_touch():\n    assert True\n"
    (repo / "test_touch.py").write_text(body)
    return repo, checks_file


def test_cli_execute_happy_path(tmp_path):
    import cli

    repo, checks_file = _execute_setup(tmp_path, edit=False)
    spec = load_checks(checks_file)
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-exec-ok",
                   "--execute", "--python", sys.executable])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["checks_digest"] == spec["checks_digest"]


def test_cli_execute_edits_checks_file(tmp_path, monkeypatch, capsys):
    import cli

    repo, checks_file = _execute_setup(tmp_path, edit=True)
    monkeypatch.setenv("AVERTH_FREEZE_TEST_CHECKS", str(checks_file))
    spec = load_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-exec-edit",
                   "--execute", "--python", sys.executable])
    err = capsys.readouterr().err
    assert rc == 2
    assert "changed during run" in err
    assert spec["checks_digest"] in err
    current_digest = "sha256:" + hashlib.sha256(checks_file.read_bytes()).hexdigest()
    assert current_digest in err
    assert "restore the frozen file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_plus_infer_checks(tmp_path):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    runs_file = tmp_path / "runs.json"
    runs_file.write_text(json.dumps({
        "runs": [{
            "label": "t",
            "command": "python -m pytest -q widget_tests/test_widget.py::test_add",
            "start_timestamp": "2026-11-03T14:04:43.309141+00:00",
            "end_timestamp": "2026-11-03T14:04:44.000000+00:00",
            "exit_code": 0,
            "output_digest": "sha256:abc",
            "working_directory": str(repo),
            "source": "imported",
            "trust_tier": 1,
        }],
        "final_edit_marker": "2026-11-03T14:04:43.309135+00:00",
    }))
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file), "--infer-checks",
                   "--out", str(out), "--report-id", "freeze-infer"])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["checks_digest"] == spec["checks_digest"]
    assert any(j["criterion_id"] == "I1" for j in ledger["judgments"])


def test_cli_observe_only(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--out", str(out),
                   "--report-id", "freeze-observe"])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["checks_digest"] is None
    report = (out / "evidence_report.md").read_text()
    assert "Checks digest: none (observe-only mode" in report
    assert "checks digest: none (observe-only mode)" in capsys.readouterr().out


def test_cli_writes_digest_for_unedited_run(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    spec = load_checks(checks_file)
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-ok"])
    assert rc == 0
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["checks_digest"] == spec["checks_digest"]
    report = (out / "evidence_report.md").read_text()
    assert spec["checks_digest"] in report
    assert f"checks digest: {spec['checks_digest']}" in capsys.readouterr().out


def test_cli_missing_checks_file_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(tmp_path / "nope.json"),
                   "--out", str(out), "--report-id", "freeze-missing"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_empty_checks_file_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_bytes(b"")
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-empty"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_directory_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(tmp_path),
                   "--out", str(out), "--report-id", "freeze-dir"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("bad_check", [
    {"id": ["C1"], "check_type": "recorded_run",
     "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"},
    {"id": {"x": 1}, "check_type": "recorded_run",
     "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"},
    {"id": 7, "check_type": "recorded_run",
     "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"},
    {"id": "C1", "check_type": "artifact_presence",
     "artifact_path": ["app.py"]},
    {"id": "C1", "check_type": "recorded_run",
     "required_command": ["pytest"]},
    {"id": "C1", "check_type": "external", "text": 123},
    {"id": "C1", "check_type": "external", "text": "t", "source": ["x"]},
    {"id": "C1", "check_type": "external", "text": "t",
     "expected_evidence": {"e": 1}},
    {"id": "C1", "check_type": "external", "text": "t",
     "recommended_next_action": 5},
    {"id": "C1", "check_type": "external", "text": "t",
     "not_applicable_reason": ["n/a"]},
])
def test_cli_non_string_check_field_exits_2(tmp_path, bad_check, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad field test",
        "task_intent_source": "test",
        "checks": [bad_check],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-field"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("checks", [
    [{"id": "C1", "check_type": "bogus", "text": "t"}],
    [{"id": "C1", "check_type": ["recorded_run"], "text": "t"}],
    [{"id": "C1", "text": "t"}],
    [{"id": "C1", "check_type": "external", "text": "t",
      "applicability": "sometimes"}],
    [{"id": "C1", "check_type": "external", "text": "t"},
     {"id": "C1", "check_type": "external", "text": "t"}],
])
def test_cli_bad_check_shape_exits_2(tmp_path, checks, capsys):
    # A bogus or missing check_type, a bad applicability, or a
    # duplicated check id used to be unpinned at the CLI: with the
    # load-time validation removed, a bogus check_type reaches
    # judge() and escapes with an uncaught ValueError traceback.
    # Every shape must refuse at load with exit 2 and stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad shape test",
        "task_intent_source": "test",
        "checks": checks,
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-shape"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("field,bad", [
    ("task_intent", 123),
    ("task_intent", ["x"]),
    ("task_intent", {"a": 1}),
    ("task_intent", None),
    ("task_intent_source", 123),
    ("task_intent_source", ["x"]),
    ("task_intent_source", {"a": 1}),
    ("task_intent_source", None),
])
def test_cli_non_string_task_intent_exits_2(tmp_path, field, bad, capsys):
    # A non-string task_intent or task_intent_source used to load
    # rc 0 and land verbatim in the ledger and the report.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    data = {
        "task_intent": "t",
        "task_intent_source": "s",
        "checks": [{"id": "C1", "text": "t", "check_type": "external"}],
    }
    data[field] = bad
    checks_file.write_text(json.dumps(data))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-intent"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_list_test_target_with_cited_run_exits_2(tmp_path, capsys):
    # A list test_target used to land verbatim in a VERIFIED row
    # when a cited exit-0 run was present. It must refuse at load
    # with exit 2 and stale removal, like every other non-string
    # check field.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "test target test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "pytest",
                    "test_target": ["widget_tests/test_widget.py"]}],
    }))
    runs_file = tmp_path / "runs.json"
    runs_file.write_text(json.dumps({"runs": [{
        "label": "t", "command": "pytest",
        "start_timestamp": "2026-11-04T01:00:00Z",
        "exit_code": 0, "stdout": "ok", "stderr": ""}]}))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--final-edit-marker", "2026-11-04T00:00:00Z",
                   "--out", str(out), "--report-id", "freeze-bad-target"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_run_allowlisted_timeout_records_124(tmp_path, monkeypatch):
    # A timed-out --execute run is recorded honestly as exit 124
    # in both runners, not a crash and not a refusal. The 124
    # recording used to be entirely unpinned.
    import subprocess
    import sys

    from verifier import run_allowlisted

    repo = make_repo(tmp_path)

    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 300,
                                        output="partial out",
                                        stderr="partial err")

    monkeypatch.setattr(subprocess, "run", _boom)
    run = run_allowlisted("python -m pytest app.py -q", repo,
                          interpreter=sys.executable)
    assert run["exit_code"] == 124
    assert run["source"] == "v0_recorder"
    assert run["trust_tier"] == 2
    assert run["stdout"] == "partial out"
    assert run["stderr"] == "partial err"


def test_run_via_allowlist_timeout_records_124(tmp_path, monkeypatch):
    # The allowlist runner records a timeout the same way.
    import subprocess

    from verifier import run_via_allowlist

    repo = make_repo(tmp_path)
    allowlist = {"workflow": "w", "approved_by": "op",
                 "runner": "nosuchbin-xyz",
                 "commands": [{"command": "nosuchbin-xyz run"}]}

    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 300,
                                        output="partial out",
                                        stderr="partial err")

    monkeypatch.setattr(subprocess, "run", _boom)
    run = run_via_allowlist("nosuchbin-xyz run", repo, allowlist)
    assert run["exit_code"] == 124
    assert run["source"] == "allowlist_recorder"
    assert run["trust_tier"] == 2
    assert run["stdout"] == "partial out"
    assert run["stderr"] == "partial err"


def test_cli_execute_missing_allowlist_runner_exits_2(tmp_path, capsys):
    # The only --execute launch-failure test used --python
    # (run_allowlisted). An allowlist naming a missing runner
    # binary must refuse the same way: rc 2, no traceback, stale
    # outputs removed.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "execute test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "nosuchbin-xyz run"}],
    }))
    allowlist_file = tmp_path / "allowlist.json"
    allowlist_file.write_text(json.dumps({
        "workflow": "w", "approved_by": "op", "runner": "nosuchbin-xyz",
        "commands": [{"command": "nosuchbin-xyz run"}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--allowlist", str(allowlist_file), "--execute",
                   "--out", str(out), "--report-id", "freeze-bad-runner"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot execute" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_execute_missing_interpreter_exits_2(tmp_path, capsys):
    # A --execute run with a missing interpreter used to crash
    # with a FileNotFoundError traceback, exit 1, and stale
    # outputs left in place. It must refuse with exit 2 and
    # stale removal, like every other loader refusal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "execute test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "python -m pytest app.py -q"}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--execute", "--python", "/nonexistent/python",
                   "--out", str(out), "--report-id", "freeze-bad-python"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot execute" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fresh_outputs_are_not_executable(tmp_path, capsys):
    # Fresh outputs used to be created mode 0o777 minus umask
    # (0o770 under umask 007): executable files for a JSON ledger
    # and a Markdown report. They must carry no execute bits.
    import os
    import stat

    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-mode"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    for name in ("evidence_ledger.json", "evidence_report.md"):
        mode = stat.S_IMODE(os.stat(out / name).st_mode)
        assert mode & 0o111 == 0, (name, oct(mode))


def test_load_checks_deeply_nested_raises_value_error(tmp_path):
    checks_file = tmp_path / "checks.json"
    checks_file.write_bytes(("[" * 20000 + "]" * 20000).encode())
    with pytest.raises(ValueError, match="nested too deeply"):
        load_checks(checks_file)


def test_cli_deeply_nested_checks_file_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_bytes(("[" * 20000 + "]" * 20000).encode())
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-nested"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def _nested_checks_text(depth):
    """Checks JSON text with a list nested `depth` deep inside a check field.

    Built as text, not via json.dumps, so the test setup itself never
    hits the encoder's recursion limit.
    """
    nested = "[" * depth + "]" * depth
    return (
        '{"task_intent": "nested field test", "task_intent_source": "test", '
        '"checks": [{"id": "C1", "check_type": "recorded_run", '
        '"required_command": "python -m pytest -q widget_tests/test_widget.py::test_add", '
        f'"notes": {nested}}}]}}'
    )


def test_load_checks_deeply_nested_field_raises_value_error(tmp_path):
    # A ~1000-deep nested field inside a check is refused at load by
    # the depth bound. The notes field is never copied into the
    # ledger, so this test pins the bound, not a reporter crash;
    # the ledger-reaching case is a deeply nested task_intent.
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_checks_text(1000))
    with pytest.raises(ValueError, match="nested too deeply"):
        load_checks(checks_file)


def test_load_checks_moderately_nested_field_loads(tmp_path):
    # The depth bound is 100; a field nested well under it must load.
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_checks_text(50))
    spec = load_checks(checks_file)
    assert spec["checks"][0]["id"] == "C1"


def test_cli_deeply_nested_field_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_checks_text(1000))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-nested-field"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("bad_confirmation", [
    ["alice", "manual check", "pass"],
    "alice/manual check/pass",
])
def test_cli_non_dict_human_confirmation_exits_2(tmp_path, bad_confirmation, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad confirmation test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "hardware check", "check_type": "external",
                    "human_confirmation": bad_confirmation}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-confirmation"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_unbalanced_quote_required_command_judged_not_observed(tmp_path, capsys):
    # An unbalanced quote used to raise ValueError from judge_all and
    # crash the run. normalize_command now falls back to a plain
    # split, so the check is judged (NOT OBSERVED, no run matches)
    # and the run completes normally: rc 0, ledger written.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "unbalanced quote test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "unbalanced quote",
                    "check_type": "recorded_run",
                    "required_command": "python -m pytest 'unclosed"}],
    }))
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-unbalanced-quote"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["judgments"][0]["criterion_id"] == "C1"
    assert ledger["judgments"][0]["status"] == "NOT OBSERVED"


@pytest.mark.parametrize("bad_limitation", [
    {"note": "not a string"},
    42,
    ["a", "b"],
])
def test_cli_non_string_scope_limitation_exits_2(tmp_path, bad_limitation, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad limitation test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "bad limitation",
                    "check_type": "recorded_run",
                    "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add",
                    "scope_limitation": bad_limitation}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-limitation"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_recursion_error_writing_outputs_exits_2(tmp_path, monkeypatch, capsys):
    # Belt and braces behind the load_checks depth bound: if writing
    # the outputs raises RecursionError (for example a deeply nested
    # record from another loader), the run refuses with exit 2 and
    # removes stale outputs instead of leaving a traceback.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _boom(ledger, out_dir):
        raise RecursionError("simulated deep output")

    monkeypatch.setattr(cli, "write_outputs", _boom)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-recursion"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "output is nested too deeply" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()

def _nested_task_intent_text(depth):
    """Checks JSON text with task_intent nested `depth` deep.

    Built as text, not via json.dumps, so the test setup itself never
    hits the encoder's recursion limit. task_intent is copied
    verbatim into the ledger, so a deeply nested task_intent is the
    ledger-reaching case: it parses fine in the C JSON scanner but
    used to crash uncaught in the reporter when the ledger was
    written.
    """
    nested = "[" * depth + "]" * depth
    return (
        '{"task_intent": ' + nested + ', "task_intent_source": "test", '
        '"checks": [{"id": "C1", "check_type": "recorded_run", '
        '"required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"}]}'
    )


def test_load_checks_deeply_nested_task_intent_raises_value_error(tmp_path):
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_task_intent_text(1000))
    with pytest.raises(ValueError, match="nested too deeply"):
        load_checks(checks_file)


def test_cli_deeply_nested_task_intent_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_task_intent_text(1000))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-nested-intent"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_load_checks_depth_boundary(tmp_path):
    # The depth bound is 100. _nested_checks_text(97) reaches max
    # depth 100 and loads; _nested_checks_text(98) reaches 101 and
    # is refused. This pins the bound: changing MAX_CHECKS_DEPTH
    # to 60 or 500 would fail this test.
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(_nested_checks_text(97))
    spec = load_checks(checks_file)
    assert spec["checks"][0]["id"] == "C1"
    checks_file.write_text(_nested_checks_text(98))
    with pytest.raises(ValueError, match="nested too deeply"):
        load_checks(checks_file)


def _write_cited_run(tmp_path, repo):
    """Runs file with one exit-0 run cited by the checks below.

    The run starts after the final edit marker, so it is cited
    rather than superseded, and its command matches the
    required_command of the checks that use it.
    """
    runs_file = tmp_path / "runs.json"
    runs_file.write_text(json.dumps({
        "runs": [{
            "label": "t",
            "command": "python -m pytest -q widget_tests/test_widget.py::test_add",
            "start_timestamp": "2026-11-03T14:04:43.309141+00:00",
            "end_timestamp": "2026-11-03T14:04:44.000000+00:00",
            "exit_code": 0,
            "output_digest": "sha256:abc",
            "working_directory": str(repo),
            "source": "imported",
            "trust_tier": 1,
        }],
        "final_edit_marker": "2026-11-03T14:04:43.309135+00:00",
    }))
    return runs_file


@pytest.mark.parametrize("bad_path,digest", [
    (["app.py"], "sha256:abc"),
    ({"path": "app.py"}, "sha256:abc"),
    (["app.py"], None),
    (123, "sha256:abc"),
    ({"path": "app.py"}, None),
    (123, None),
])
def test_cli_recorded_run_bad_artifact_path_exits_2(tmp_path, bad_path, digest, capsys):
    # artifact_path / expected_digest on a recorded_run check were
    # never validated: with a cited exit-0 run, a list artifact_path
    # plus an expected_digest crashed the judge (unhashable snapshot
    # lookup), and without the digest the same garbage judged
    # VERIFIED. Both must now refuse at load.
    import cli

    repo = make_repo(tmp_path)
    runs_file = _write_cited_run(tmp_path, repo)
    check = {"id": "C1", "text": "artifact check", "check_type": "recorded_run",
             "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add",
             "artifact_path": bad_path}
    if digest is not None:
        check["expected_digest"] = digest
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad artifact path test",
        "task_intent_source": "test",
        "checks": [check],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-bad-artifact"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("bad_digest", [
    ["sha256:abc"],
    {"d": "sha256:abc"},
    123,
    "",
])
def test_cli_recorded_run_bad_expected_digest_exits_2(tmp_path, bad_digest, capsys):
    # Bad expected_digest alone was a mutation-proven escape:
    # removing only the expected_digest half of the load_checks
    # validation left all freeze tests passing. A valid
    # artifact_path with a non-string expected_digest must refuse
    # at load, the same as a bad artifact_path.
    import cli

    repo = make_repo(tmp_path)
    runs_file = _write_cited_run(tmp_path, repo)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad expected digest test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "artifact check", "check_type": "recorded_run",
                    "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add",
                    "artifact_path": "app.py",
                    "expected_digest": bad_digest}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-bad-digest"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("bad_confirmation", [
    {"tester": {"a": 1}, "procedure": "p", "result": "pass"},
    {"tester": "alice", "procedure": ["step"], "result": "pass"},
    {"tester": "", "procedure": "p", "result": "pass"},
    {"tester": "alice", "procedure": "", "result": "pass"},
])
def test_cli_bad_human_confirmation_inner_field_exits_2(tmp_path, bad_confirmation, capsys):
    # A dict tester used to judge VERIFIED, with the dict repr in
    # the evidence id, contradicting the "named tester, named
    # procedure" rule. tester and procedure must be non-empty
    # strings when present.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "bad confirmation field test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "hardware check", "check_type": "external",
                    "human_confirmation": bad_confirmation}],
    }))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-bad-confirmation-field"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fifo_checks_file_exits_2(tmp_path, capsys):
    import os

    repo = make_repo(tmp_path)
    fifo = tmp_path / "checks.json"
    os.mkfifo(fifo)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(fifo),
                            "--out", str(out), "--report-id", "freeze-fifo"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "not a regular file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_checks_file_replaced_by_fifo_exits_2(tmp_path, monkeypatch, capsys):
    import os
    import cli
    from verifier import judge_all as real_judge_all

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _judge_and_fifo(checks, runs, snapshot, marker):
        checks_file.unlink()
        os.mkfifo(checks_file)
        return real_judge_all(checks, runs, snapshot, marker)

    monkeypatch.setattr(cli, "judge_all", _judge_and_fifo)
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--out", str(out), "--report-id", "freeze-fifo-swap"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not a regular file" in err
    assert "Traceback" not in err
    # The re-hash refusal names the load-time digest exactly once
    # and states the redo: a FIFO swapped in at verify time is an
    # unreadable case, not a bare error.
    assert err.count("sha256:") == 1
    assert "restore the frozen file" in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_checks_file_is_output_file_exits_2(tmp_path, output_name, capsys):
    # --checks naming one of the output files would let the run
    # overwrite its own frozen input. The run refuses with exit 2
    # and the pre-seeded file is left byte-identical: the refusal
    # must not remove stale outputs here, because the output file
    # IS the input file.
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    checks_file = out / output_name
    checks_file.write_text(json.dumps({
        "task_intent": "self-destruct test",
        "task_intent_source": "test",
        "checks": [
            {"id": "C1", "text": "add behaves as named", "check_type": "recorded_run",
             "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add"},
        ],
    }))
    before = checks_file.read_bytes()
    # The other stale output must be removed even though the
    # colliding file is kept: a refused run must not leave a
    # pass-looking report behind.
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-self"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_checks_file_hardlinked_to_output_exits_2(tmp_path, output_name, capsys):
    import os
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    before = checks_file.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    os.link(checks_file, out / output_name)
    # The other stale output must be removed even though the
    # colliding file is kept: a refused run must not leave a
    # pass-looking report behind.
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-hardlink"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_checks_file_symlinked_to_output_exits_2(tmp_path, output_name, capsys):
    # Symlink mirror of the hardlink collision test: an output
    # path symlinked to the checks file collides the same way,
    # via resolve, and the run refuses with exit 2, leaving the
    # checks file byte-identical and removing the other stale
    # output.
    import os
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    before = checks_file.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    os.symlink(checks_file, out / output_name)
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-symlink-collision"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_runs_file_is_output_file_exits_2(tmp_path, output_name, capsys):
    # --runs naming one of the output files used to be
    # overwritten with ledger content at rc 0: the collision
    # check covered only --checks. Every input kind refuses
    # the same way now, leaving the input byte-identical and
    # removing the other stale output.
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    runs_file = out / output_name
    runs_file.write_text(json.dumps({"runs": []}))
    before = runs_file.read_bytes()
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-runs-self"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert runs_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_trace_file_is_output_file_exits_2(tmp_path, output_name, capsys):
    # --trace naming one of the output files: same refusal as
    # --checks, before anything is loaded.
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    trace_file = out / output_name
    trace_file.write_text(
        '{"type": "model", "case_id": "c1", "input_tokens": 10, '
        '"output_tokens": 5}\n')
    before = trace_file.read_bytes()
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-trace-self"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert trace_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_ingest_file_is_output_file_exits_2(tmp_path, output_name, capsys):
    # --ingest naming one of the output files: same refusal as
    # --checks, before anything is loaded.
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    ingest_file = out / output_name
    ingest_file.write_text(json.dumps(
        {"command": "pytest", "exit_code": 0,
         "start_timestamp": "2026-11-04T01:00:00Z"}))
    before = ingest_file.read_bytes()
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--out", str(out), "--report-id", "freeze-ingest-self"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert ingest_file.read_bytes() == before
    assert not (out / other_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_allowlist_file_is_output_file_exits_2(tmp_path, output_name, capsys):
    # --allowlist naming one of the output files: the worst case
    # of the four, because the operator's security policy file
    # would have been overwritten with a ledger while the run
    # reported success. Same refusal as --checks.
    import cli

    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    allowlist_file = out / output_name
    allowlist_file.write_text(json.dumps({
        "workflow": "w", "approved_by": "op", "runner": "pytest",
        "commands": [{"command": "pytest -q"}],
    }))
    before = allowlist_file.read_bytes()
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--allowlist", str(allowlist_file),
                   "--out", str(out), "--report-id", "freeze-allowlist-self"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert allowlist_file.read_bytes() == before
    assert not (out / other_name).exists()


def test_cli_stale_ledger_directory_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").mkdir()
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-ledger-dir"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not write output" in err
    assert "could not remove stale output" in err
    assert "Traceback" not in err
    assert not (out / "evidence_report.md").exists()
    assert (out / "evidence_ledger.json").is_dir()


def _make_symlink_loop(tmp_path):
    """Two symlinks pointing at each other: resolving either loops."""
    loop1 = tmp_path / "loop1"
    loop2 = tmp_path / "loop2"
    loop1.symlink_to(loop2)
    loop2.symlink_to(loop1)
    return loop1


def test_cli_symlink_loop_checks_exits_2(tmp_path, capsys):
    # Path.resolve() raises RuntimeError on a symlink loop; the
    # three unguarded resolve() calls in cli.main used to let it
    # escape as a traceback with exit 1.
    import cli

    repo = make_repo(tmp_path)
    loop = _make_symlink_loop(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(loop),
                   "--out", str(out), "--report-id", "freeze-loop-checks"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load checks file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_symlink_loop_out_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    loop = _make_symlink_loop(tmp_path)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(loop), "--report-id", "freeze-loop-out"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert list(tmp_path.rglob("evidence_ledger.json")) == []
    assert list(tmp_path.rglob("evidence_report.md")) == []


def test_cli_symlink_loop_repo_exits_2(tmp_path, capsys):
    import cli

    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    loop = _make_symlink_loop(tmp_path)
    out = tmp_path / "out"
    # --repo must be a real directory: a symlink loop fails the
    # is_dir check and argparse exits 2 (SystemExit), never a
    # traceback.
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--repo", str(loop), "--checks", str(checks_file),
                  "--out", str(out), "--report-id", "freeze-loop-repo"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--repo must be a real directory" in err
    assert "Traceback" not in err

@pytest.mark.parametrize("name,content", [
    ("entry string", '{"runs": ["not a dict"]}'),
    ("entry null", '{"runs": [null]}'),
    ("entry list", '{"runs": [["pytest"]]}'),
    ("invalid JSON", "{not json"),
    ("top-level string", '"just a string"'),
    ("runs null", '{"runs": null}'),
    ("stdout int", '{"runs": [{"command": "pytest", "stdout": 123}]}'),
    ("label int", '{"runs": [{"command": "pytest", "label": 123}]}'),
    ("command int", '{"runs": [{"command": 123}]}'),
    ("marker int", '{"runs": [], "final_edit_marker": 123}'),
    ("missing file", None),
])
def test_cli_malformed_runs_file_exits_2(tmp_path, name, content, capsys):
    # A malformed --runs file used to crash the CLI with a
    # traceback and exit 1, leaving a stale pass-looking ledger
    # and report behind: a string run entry (AttributeError),
    # invalid JSON (JSONDecodeError), a top-level string (the
    # loader's own ValueError escaping uncaught), "runs": null
    # (TypeError), a non-string stdout (TypeError on +), and a
    # missing file (FileNotFoundError). Every shape must now
    # refuse with exit 2 and stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    runs_file = tmp_path / "runs.json"
    if content is not None:
        runs_file.write_text(content)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-bad-runs"])
    err = capsys.readouterr().err
    assert rc == 2, name
    assert "cannot load recorded runs" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fifo_runs_file_exits_2(tmp_path, capsys):
    import os

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    fifo = tmp_path / "runs.json"
    os.mkfifo(fifo)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--runs", str(fifo),
                            "--out", str(out), "--report-id", "freeze-fifo-runs"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load recorded runs" in err
    assert "not a regular file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_missing_trace_file_exits_2(tmp_path, capsys):
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(tmp_path / "nope.jsonl"),
                   "--out", str(out), "--report-id", "freeze-no-trace"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load trace file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fifo_trace_file_exits_2(tmp_path, capsys):
    import os

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    fifo = tmp_path / "trace.jsonl"
    os.mkfifo(fifo)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--trace", str(fifo),
                            "--out", str(out), "--report-id", "freeze-fifo-trace"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load trace file" in err
    assert "not a regular file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("name,line", [
    ("list input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": [100], "output_tokens": 5}'),
    ("dict input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": {"n": 100}, "output_tokens": 5}'),
    ("list output_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": 100, "output_tokens": [5]}'),
    ("dict output_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": 100, "output_tokens": {"n": 5}}'),
    ("list type",
     '{"type": ["model"], "case_id": "c1"}'),
    ("dict type",
     '{"type": {"name": "model"}, "case_id": "c1"}'),
    ("list case_id",
     '{"type": "model", "case_id": ["c1"]}'),
    ("dict case_id",
     '{"type": "model", "case_id": {"id": "c1"}}'),
    ("bool input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": true, "output_tokens": 5}'),
    ("bool output_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": 100, "output_tokens": false}'),
    ("float input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": 12.5, "output_tokens": 5}'),
    ("string input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": "abc", "output_tokens": 5}'),
    ("bool case_id",
     '{"type": "model", "case_id": true}'),
    ("float case_id",
     '{"type": "model", "case_id": 1.5}'),
    ("negative input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": -5, "output_tokens": 5}'),
    ("negative output_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": 100, "output_tokens": -5}'),
    ("negative string input_tokens",
     '{"type": "model", "case_id": "c1", "input_tokens": "-5", "output_tokens": 5}'),
])
def test_cli_malformed_trace_content_exits_2(tmp_path, name, line, capsys):
    # A trace line that parses but carries a wrong-typed field the
    # summary reads used to crash the CLI: int() on a list/dict
    # token count, an unhashable type in the counts dict, an
    # unhashable case_id in the cases set. Every shape must now
    # refuse with exit 2 and stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(line + "\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-bad-trace"])
    err = capsys.readouterr().err
    assert rc == 2, name
    assert "cannot load trace file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_trace_string_input_tokens_counts(tmp_path, capsys):
    # Positive control for the accepted-string branch: a numeric
    # string token count parses as an int, so "10" counts as 10.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": "c1", "input_tokens": "10", '
        '"output_tokens": 5}\n')
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-string-tokens"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["input_tokens_total"] == 10
    assert ledger["trace_summary"]["output_tokens_total"] == 5


def test_cli_trace_integral_float_tokens_counts(tmp_path, capsys):
    # Positive control for the integral-float branch: 12.0 counts
    # as 12, while a non-integral float such as 12.5 refuses.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": "c1", "input_tokens": 12.0, '
        '"output_tokens": 5.0}\n')
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-float-tokens"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["input_tokens_total"] == 12
    assert ledger["trace_summary"]["output_tokens_total"] == 5


def test_cli_trace_string_output_tokens_counts(tmp_path, capsys):
    # Positive control: a numeric string output count parses as an
    # int, like the input count in the test above.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": "c1", "input_tokens": 5, '
        '"output_tokens": "10"}\n')
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-string-out"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["input_tokens_total"] == 5
    assert ledger["trace_summary"]["output_tokens_total"] == 10


def test_cli_trace_int_case_id_counts(tmp_path, capsys):
    # Positive control: an int case_id is accepted, like a string
    # one, and counts as one case.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": 7, "input_tokens": 10, '
        '"output_tokens": 5}\n')
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-int-case"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["cases"] == 1
    assert ledger["trace_summary"]["input_tokens_total"] == 10


@pytest.mark.parametrize("name,content", [
    ("invalid JSON", "{not json"),
    ("top-level list", "[1, 2]"),
    ("commands not a list", '{"workflow": "w", "approved_by": "op", "runner": "pytest", "commands": "pytest"}'),
    ("entry not an object", '{"workflow": "w", "approved_by": "op", "runner": "pytest", "commands": ["pytest"]}'),
    ("missing file", None),
])
def test_cli_bad_allowlist_exits_2(tmp_path, name, content, capsys):
    # A missing, invalid, or malformed --allowlist file used to
    # crash the CLI with a traceback and exit 1. Every shape
    # must now refuse with exit 2 and stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    allowlist_file = tmp_path / "allowlist.json"
    if content is not None:
        allowlist_file.write_text(content)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--allowlist", str(allowlist_file),
                   "--out", str(out), "--report-id", "freeze-bad-allowlist"])
    err = capsys.readouterr().err
    assert rc == 2, name
    assert "cannot load allowlist" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fifo_allowlist_exits_2(tmp_path, capsys):
    import os

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    fifo = tmp_path / "allowlist.json"
    os.mkfifo(fifo)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--allowlist", str(fifo),
                            "--out", str(out), "--report-id", "freeze-fifo-allowlist"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load allowlist" in err
    assert "not a regular file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_verify_checks_unchanged_survives_fifo_swapper(tmp_path):
    """A FIFO swapped in between the stat and the read used to hang.

    The single-open read closes that window: the fd opened is the
    file fstat'd, so a swap can only produce a prompt refusal
    (ValueError) or a matching digest, never a blocked open. The
    verify loop runs in a thread with a bounded join, so a
    regression fails the test instead of hanging the suite.
    """
    import os
    import threading

    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    digest = checks_digest(checks_file)
    regular = checks_file.read_bytes()
    stop = threading.Event()
    swaps = []
    refusals = []

    def swapper():
        while not stop.is_set():
            swaps.append(1)
            try:
                checks_file.unlink()
            except FileNotFoundError:
                pass
            try:
                os.mkfifo(checks_file)
            except FileExistsError:
                pass
            try:
                checks_file.unlink()
            except FileNotFoundError:
                pass
            checks_file.write_bytes(regular)

    def verifier():
        for _ in range(500):
            try:
                verify_checks_unchanged(checks_file, digest)
            except (ValueError, OSError) as exc:
                # Keep the message, not just a count: a torn-read
                # "changed during run" refusal is not a FIFO
                # refusal, and the torn reads outnumber the FIFO
                # hits, so a bare count would pass even if the
                # FIFO case were never exercised.
                refusals.append(str(exc))

    swap_thread = threading.Thread(target=swapper, daemon=True)
    verify_thread = threading.Thread(target=verifier, daemon=True)
    swap_thread.start()
    verify_thread.start()
    verify_thread.join(timeout=20)
    stop.set()
    swap_thread.join(timeout=5)
    assert not verify_thread.is_alive(), "verify_checks_unchanged hung on a FIFO swap"
    assert len(swaps) > 0, "the swapper never ran, so the test proved nothing"
    assert len(refusals) > 0, "no refusal was observed, so the FIFO case was never exercised"
    assert any("not a regular file" in m for m in refusals), \
        "no FIFO refusal was observed, so the FIFO case was never exercised"
    assert not swap_thread.is_alive()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_fifo_stale_output_exits_2(tmp_path, output_name, capsys):
    # A FIFO left in place of a stale output used to hang the
    # happy path forever in write_outputs. Both output paths are
    # checked up front now: the run refuses with exit 2, the
    # FIFO is unlinked by stale removal, and the other stale
    # output is removed too.
    import os

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    os.mkfifo(out / output_name)
    other_name = ("evidence_report.md" if output_name == "evidence_ledger.json"
                  else "evidence_ledger.json")
    (out / other_name).write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--out", str(out), "--report-id", "freeze-fifo-output"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert not (out / output_name).exists()
    assert not (out / other_name).exists()


def test_cli_checks_file_replaced_by_directory_exits_2(tmp_path, monkeypatch, capsys):
    import cli
    from verifier import judge_all as real_judge_all

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")

    def _judge_and_dir(checks, runs, snapshot, marker):
        checks_file.unlink()
        checks_file.mkdir()
        return real_judge_all(checks, runs, snapshot, marker)

    monkeypatch.setattr(cli, "judge_all", _judge_and_dir)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-dir-swap"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unreadable during run" in err
    assert err.count("sha256:") == 1
    assert "restore the frozen file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_judge_rejects_malformed_judging_inputs(tmp_path):
    """Direct judge() calls with malformed runs/snapshot refuse, never crash."""
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    with pytest.raises(ValueError):
        judge(check, None, {}, "2026-11-04T00:00:00Z")
    with pytest.raises(ValueError):
        judge(check, ["not a dict"], {}, "2026-11-04T00:00:00Z")
    with pytest.raises(ValueError):
        judge(check, [None], {}, "2026-11-04T00:00:00Z")
    with pytest.raises(ValueError):
        judge(check, [], None, "2026-11-04T00:00:00Z")
    art_check = {"id": "C1", "text": "t", "check_type": "artifact_presence",
                 "artifact_path": "app.py", "applicability": "applies"}
    with pytest.raises(ValueError):
        judge(art_check, [], None, "2026-11-04T00:00:00Z")


def test_judge_rejects_malformed_check_shapes(tmp_path):
    """Direct judge() calls with malformed check shapes refuse, never crash."""
    from verifier import judge

    marker = "2026-11-04T00:00:00Z"
    # Non-dict check.
    with pytest.raises(ValueError):
        judge(["not a dict"], [], {}, marker)
    # Missing, non-string, and whitespace-only id.
    with pytest.raises(ValueError):
        judge({"check_type": "external"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": 7, "check_type": "external"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "  ", "check_type": "external"}, [], {}, marker)
    # recorded_run with missing, non-string, and whitespace required_command.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "recorded_run"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "recorded_run",
               "required_command": ["pytest"]}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "recorded_run",
               "required_command": "  "}, [], {}, marker)
    # artifact_presence with missing and non-string artifact_path.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "artifact_presence"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "artifact_presence",
               "artifact_path": ["app.py"]}, [], {}, marker)
    # Non-string expected_digest.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "recorded_run",
               "required_command": "pytest",
               "expected_digest": ["sha256:abc"]}, [], {}, marker)
    # Non-dict human_confirmation, and a dict tester.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "human_confirmation": ["x"]}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "human_confirmation": {"tester": {"a": 1}, "procedure": "p",
                                      "result": "pass"}}, [], {}, marker)
    # A bad applicability, and the string fields judge() copies
    # into the row: none of these used to be validated here, so
    # a direct judge() call landed them verbatim in a row.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "applicability": "sometimes"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "text": 123}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "source": ["x"]}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "expected_evidence": {"e": 1}}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "recommended_next_action": 5}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "external",
               "applicability": "not_applicable",
               "not_applicable_reason": ["n/a"]}, [], {}, marker)
    # An unknown check_type, including the bypass the NOT
    # APPLICABLE early return used to open: a bogus type with
    # applicability not_applicable returned NOT APPLICABLE
    # instead of refusing.
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "bogus"}, [], {}, marker)
    with pytest.raises(ValueError):
        judge({"id": "C1", "check_type": "bogus",
               "applicability": "not_applicable",
               "not_applicable_reason": "n/a"}, [], {}, marker)


def test_judge_rejects_non_string_test_target(tmp_path):
    """Direct judge() calls with a non-string test_target refuse.

    A list test_target used to land verbatim in a VERIFIED row.
    Null stays allowed: the fixture checks files use it for "no
    test target", and an absent test_target is the same.
    """
    from verifier import judge

    marker = "2026-11-04T00:00:00Z"
    for bad in (["x"], {"t": 1}, 123):
        with pytest.raises(ValueError):
            judge({"id": "C1", "check_type": "recorded_run",
                   "required_command": "pytest",
                   "test_target": bad}, [], {}, marker)
    # Null and absent test_target still judge: the row records None.
    row = judge({"id": "C1", "check_type": "recorded_run",
                 "required_command": "pytest",
                 "test_target": None}, [], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert row.get("test_target") is None
    row = judge({"id": "C1", "check_type": "recorded_run",
                 "required_command": "pytest"}, [], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert row.get("test_target") is None


def test_judge_external_bad_result_is_unverifiable(tmp_path):
    """An external confirmation with a result outside {pass, fail} never decides.

    A truthy result such as "maybe" used to be unpinned: on a
    mutated copy it judged FAILED with trust tier 4 and a human
    evidence id. Only pass/fail decide.
    """
    from verifier import judge

    marker = "2026-11-04T00:00:00Z"

    def external(result):
        rec = {"tester": "op", "procedure": "bench"}
        if result is not None:
            rec["result"] = result
        return {"id": "C1", "text": "t", "check_type": "external",
                "human_confirmation": rec}

    for bad in ("maybe", 123, None):
        row = judge(external(bad), [], {}, marker)
        assert row["status"] == "EXTERNAL-UNVERIFIABLE", bad
    # An explicit null result is the same as a missing one: it
    # never decides either.
    row = judge({"id": "C1", "text": "t", "check_type": "external",
                 "human_confirmation": {"tester": "op", "procedure": "bench",
                                        "result": None}}, [], {}, marker)
    assert row["status"] == "EXTERNAL-UNVERIFIABLE"
    row = judge(external("pass"), [], {}, marker)
    assert row["status"] == "VERIFIED"
    row = judge(external("fail"), [], {}, marker)
    assert row["status"] == "FAILED"


def test_judge_cited_run_missing_fields_is_not_observed(tmp_path):
    """A cited run missing evidence fields never verifies on malformed evidence."""
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    marker = "2026-11-04T00:00:00Z"

    def cited(**overrides):
        run = {
            "label": "t",
            "command_raw": "pytest",
            "command_normalized": "pytest",
            "working_directory": "/tmp/fixture",
            "start_timestamp": "2026-11-04T01:00:00Z",
            "end_timestamp": "2026-11-04T02:00:00Z",
            "exit_code": 0,
            "output_digest": "sha256:abc",
            "source": "imported",
            "trust_tier": 1,
        }
        run.update(overrides)
        return run

    # Control: a complete cited run verifies.
    row = judge(check, [cited()], {}, marker)
    assert row["status"] == "VERIFIED"
    # No evidence id at all: label and command_raw both gone.
    run = cited()
    del run["label"]
    del run["command_raw"]
    row = judge(check, [run], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_evidence_id" in row["flags"]
    assert row["evidence_id"] is None
    # A list label with no usable command_raw never becomes the evidence id.
    row = judge(check, [cited(label=["x"], command_raw=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_evidence_id" in row["flags"]
    # A missing source verifies with evidence_source None under the old code.
    row = judge(check, [cited(source=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_source" in row["flags"]
    # A missing working directory (None, not the loader's "" default).
    row = judge(check, [cited(working_directory=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_working_directory" in row["flags"]
    # A missing output digest.
    row = judge(check, [cited(output_digest=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_output_digest" in row["flags"]
    # A wrong-typed end timestamp (an absent one is None, which the
    # loaders legitimately record, so only a wrong type refuses).
    row = judge(check, [cited(end_timestamp=["x"])], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_end_timestamp" in row["flags"]
    # A run with no end timestamp at all still verifies: the loaders
    # record it as None and the verdict does not depend on it.
    row = judge(check, [cited(end_timestamp=None)], {}, marker)
    assert row["status"] == "VERIFIED"


def test_judge_cited_run_bad_exit_code_is_not_observed(tmp_path):
    """A cited run with a non-integer exit code never decides a check."""
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    marker = "2026-11-04T00:00:00Z"

    def cited(exit_code):
        return {
            "label": "t",
            "command_raw": "pytest",
            "command_normalized": "pytest",
            "working_directory": "/tmp/fixture",
            "start_timestamp": "2026-11-04T01:00:00Z",
            "end_timestamp": "2026-11-04T02:00:00Z",
            "exit_code": exit_code,
            "output_digest": "sha256:abc",
            "source": "imported",
            "trust_tier": 1,
        }

    # A string "0", a bool, a list, and a float 0.0 all used to
    # decide the check ("0" and True and [0] as FAILED, 0.0 as
    # VERIFIED with the verbatim non-int value in the ledger).
    for bad in ("0", True, [0], 0.0):
        row = judge(check, [cited(bad)], {}, marker)
        assert row["status"] == "NOT OBSERVED", bad
        assert "invalid_exit_code" in row["flags"], bad
        assert row["exit_code"] is None, bad


def test_judge_cited_run_missing_exit_code_and_field_reports_all_flags(tmp_path):
    """A cited run missing its exit code AND another field names every flag.

    The missing exit code used to short-circuit past the other
    field checks, so only missing_exit_code was reported and the
    malformed values stayed in the row as its evidence identity.
    Every applicable flag is now reported, the identity is reset,
    and each wrong-typed value is neutralised to None.
    """
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    marker = "2026-11-04T00:00:00Z"

    def cited(**overrides):
        run = {
            "label": "t",
            "command_raw": "pytest",
            "command_normalized": "pytest",
            "working_directory": "/tmp/fixture",
            "start_timestamp": "2026-11-04T01:00:00Z",
            "end_timestamp": "2026-11-04T02:00:00Z",
            "exit_code": 0,
            "output_digest": "sha256:abc",
            "source": "imported",
            "trust_tier": 1,
        }
        run.update(overrides)
        return run

    # Missing exit code plus a missing source: both flags, identity reset.
    row = judge(check, [cited(exit_code=None, source=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_exit_code" in row["flags"]
    assert "missing_source" in row["flags"]
    assert row["evidence_id"] is None
    assert row["evidence_source"] == "none"
    assert row["trust_tier"] is None
    # Missing exit code plus a wrong-typed working directory: both
    # flags, and the wrong-typed value is neutralised, not recorded.
    row = judge(check, [cited(exit_code=None, working_directory=123)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_exit_code" in row["flags"]
    assert "missing_working_directory" in row["flags"]
    assert row["working_directory"] is None
    # Invalid exit code plus a missing output digest: both flags,
    # and both values are neutralised.
    row = judge(check, [cited(exit_code="0", output_digest=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "invalid_exit_code" in row["flags"]
    assert "missing_output_digest" in row["flags"]
    assert row["exit_code"] is None
    assert row["output_digest"] is None
    # Missing evidence id: the command is cleared too, so the row
    # cannot present the malformed command_raw as its evidence.
    row = judge(check, [cited(label=["x"], command_raw=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_evidence_id" in row["flags"]
    assert row["evidence_id"] is None
    assert row["command"] is None
    # Missing exit code alone keeps the old behaviour: the flag,
    # and the cited run's identity intact.
    row = judge(check, [cited(exit_code=None)], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert row["flags"] == ["missing_exit_code"]
    assert row["evidence_id"] == "t"


def test_judge_epoch_start_timestamp_is_normalised_to_iso(tmp_path):
    # An int or float epoch start_timestamp is a legitimate
    # timestamp representation under the tool's own contract, so
    # it is accepted, but it is normalised to ISO in the row
    # rather than recorded verbatim as a bare number: a bare
    # epoch in a ledger row reads as an unlabelled integer. A
    # string timestamp is recorded verbatim, as before.
    from evidence_ledger import parse_time
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    marker = "2026-11-01T00:00:00Z"
    run = {
        "label": "t",
        "command_raw": "pytest",
        "command_normalized": "pytest",
        "working_directory": "/tmp/fixture",
        "start_timestamp": 1793754000,
        "end_timestamp": "2026-11-08T02:00:00Z",
        "exit_code": 0,
        "output_digest": "sha256:abc",
        "source": "imported",
        "trust_tier": 1,
    }
    row = judge(check, [run], {}, marker)
    assert row["status"] == "VERIFIED"
    assert row["start_timestamp"] == parse_time(1793754000).isoformat()
    assert isinstance(row["start_timestamp"], str)
    # A string timestamp is recorded verbatim, as before.
    run["start_timestamp"] = "2026-11-08T01:00:00Z"
    row = judge(check, [run], {}, marker)
    assert row["status"] == "VERIFIED"
    assert row["start_timestamp"] == "2026-11-08T01:00:00Z"
    # A float epoch is normalised the same way, not recorded
    # verbatim as a bare number.
    run["start_timestamp"] = 1793754000.5
    row = judge(check, [run], {}, marker)
    assert row["status"] == "VERIFIED"
    assert row["start_timestamp"] == parse_time(1793754000.5).isoformat()
    assert isinstance(row["start_timestamp"], str)


def test_judge_cited_run_malformed_identity_fields_are_not_observed(tmp_path):
    """A cited run with a wrong-typed label, command_raw, or trust tier never verifies.

    Each field is validated on its own: a list label used to
    verify with the list recorded verbatim as the evidence id,
    a list command_raw verified with the list as the command,
    and a trust tier of 99 verified with 99 recorded as the tier.
    """
    from verifier import judge

    check = {"id": "C1", "text": "t", "check_type": "recorded_run",
             "required_command": "pytest", "applicability": "applies"}
    marker = "2026-11-04T00:00:00Z"

    def cited(**overrides):
        run = {
            "label": "t",
            "command_raw": "pytest",
            "command_normalized": "pytest",
            "working_directory": "/tmp/fixture",
            "start_timestamp": "2026-11-04T01:00:00Z",
            "end_timestamp": "2026-11-04T02:00:00Z",
            "exit_code": 0,
            "output_digest": "sha256:abc",
            "source": "imported",
            "trust_tier": 1,
        }
        run.update(overrides)
        return run

    # A wrong-typed label never becomes the evidence id, even
    # though command_raw names the run.
    for bad_label in (["x"], 123, {"x": 1}, "   "):
        row = judge(check, [cited(label=bad_label)], {}, marker)
        assert row["status"] == "NOT OBSERVED", bad_label
        assert "invalid_label" in row["flags"], bad_label
        assert row["evidence_id"] is None, bad_label
    # A wrong-typed command_raw never becomes the command, even
    # though the label names the run.
    for bad_command in (["pytest"], "   ", None):
        row = judge(check, [cited(command_raw=bad_command)], {}, marker)
        assert row["status"] == "NOT OBSERVED", bad_command
        assert "invalid_command_raw" in row["flags"], bad_command
        assert row["command"] is None, bad_command
    # A wrong-typed trust tier never lands in the row.
    for bad_tier in (["x"], {"t": 1}, "1", 99, 0, True):
        row = judge(check, [cited(trust_tier=bad_tier)], {}, marker)
        assert row["status"] == "NOT OBSERVED", bad_tier
        assert "invalid_trust_tier" in row["flags"], bad_tier
        assert row["trust_tier"] is None, bad_tier
    # Missing exit code plus a malformed label: both flags, identity reset.
    row = judge(check, [cited(exit_code=None, label=["x"])], {}, marker)
    assert row["status"] == "NOT OBSERVED"
    assert "missing_exit_code" in row["flags"]
    assert "invalid_label" in row["flags"]
    assert row["evidence_id"] is None
    # An absent label is not invalid: the command_raw names the run.
    run = cited()
    del run["label"]
    row = judge(check, [run], {}, marker)
    assert row["status"] == "VERIFIED"
    assert row["evidence_id"] == "pytest"
    # An absent trust tier is not invalid: the row records tier None.
    run = cited()
    del run["trust_tier"]
    row = judge(check, [run], {}, marker)
    assert row["status"] == "VERIFIED"
    assert row["trust_tier"] is None
    # Every tier in 1 to 4 still verifies.
    for tier in (1, 2, 3, 4):
        row = judge(check, [cited(trust_tier=tier)], {}, marker)
        assert row["status"] == "VERIFIED", tier
        assert row["trust_tier"] == tier, tier


@pytest.mark.parametrize("bad_exit", ['"0"', "true", "[0]", "0.0"])
def test_cli_recorded_run_bad_exit_code_exits_2(tmp_path, bad_exit, capsys):
    # A --runs file with a non-integer exit_code used to load and
    # judge: "0" as FAILED, 0.0 as VERIFIED. It must now refuse
    # at load with exit 2 and stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    runs_file = tmp_path / "runs.json"
    runs_file.write_text(
        '{"runs": [{"label": "t", "command": "pytest", '
        '"start_timestamp": "2026-11-03T14:04:43.309141+00:00", '
        f'"exit_code": {bad_exit}}}]}}')
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-bad-exit"])
    err = capsys.readouterr().err
    assert rc == 2, bad_exit
    assert "cannot load recorded runs" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_output_symlink_to_victim_exits_2(tmp_path, output_name, capsys):
    # A stale output planted as a symlink to an arbitrary victim
    # file used to be followed by the write, overwriting the victim
    # with ledger/report content, rc 0. The single-open write
    # refuses a symlink with ELOOP: rc 2, victim byte-identical.
    import os

    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    out = tmp_path / "out"
    out.mkdir()
    os.symlink(victim, out / output_name)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-symlink-output"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    assert not (out / output_name).exists()
    assert not (out / output_name).is_symlink()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_output_symlink_swap_mid_run_exits_2(tmp_path, output_name, monkeypatch, capsys):
    # A symlink planted after the load-time collision check used to
    # defeat it: the write followed the link and overwrote the
    # frozen checks file with ledger/report content, rc 0. The
    # collision check runs again after build_ledger now, and
    # samefile is symmetric: an output entry linked to the checks
    # file also names the checks file as an output, so the run
    # refuses rc 2 before anything is written, checks file
    # byte-identical. The colliding entry is kept (it names the
    # checks file through the planted link); the other output is
    # removed.
    import os

    import cli
    from evidence_ledger import build_ledger as real_build_ledger

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    original = checks_file.read_bytes()
    out = tmp_path / "out"

    def _build_and_swap(*args, **kwargs):
        out.mkdir(parents=True, exist_ok=True)
        target = out / output_name
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        os.symlink(checks_file, target)
        return real_build_ledger(*args, **kwargs)

    monkeypatch.setattr(cli, "build_ledger", _build_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-symlink-swap"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == original
    assert os.path.islink(out / output_name)
    other = ("evidence_report.md" if output_name == "evidence_ledger.json"
             else "evidence_ledger.json")
    assert not (out / other).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_output_hardlink_to_victim_exits_2(tmp_path, output_name, capsys):
    # Hardlink mirror of the symlink-to-victim test: a stale
    # output planted as a hardlink to an arbitrary victim file
    # used to be followed by the write, overwriting the victim
    # with ledger/report content, rc 0. The write-outputs
    # pre-check refuses a link count other than 1 before either
    # file is touched: rc 2, victim byte-identical.
    import os

    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    out = tmp_path / "out"
    out.mkdir()
    os.link(victim, out / output_name)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-hardlink-output"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "could not write output" in err
    assert "hardlinked to another file" in err
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    assert not (out / output_name).exists()


@pytest.mark.parametrize("output_name", ["evidence_ledger.json", "evidence_report.md"])
def test_cli_output_hardlink_swap_mid_run_exits_2(tmp_path, output_name, monkeypatch, capsys):
    # Hardlink mirror of the symlink-swap test: a hardlink
    # planted after the load-time collision check used to defeat
    # it, and the write followed the link and overwrote the
    # frozen checks file with ledger/report content, rc 0. The
    # collision check runs again after build_ledger now, and
    # samefile is symmetric, so the run refuses rc 2 before
    # anything is written, checks file byte-identical. The
    # colliding entry is kept (it is a hardlink to the checks
    # file); the other output is removed.
    import os

    import cli
    from evidence_ledger import build_ledger as real_build_ledger

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    original = checks_file.read_bytes()
    out = tmp_path / "out"

    def _build_and_swap(*args, **kwargs):
        out.mkdir(parents=True, exist_ok=True)
        target = out / output_name
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        os.link(checks_file, target)
        return real_build_ledger(*args, **kwargs)

    monkeypatch.setattr(cli, "build_ledger", _build_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-hardlink-swap"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "must not be one of the output files" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == original
    assert os.path.samefile(out / output_name, checks_file)
    other = ("evidence_report.md" if output_name == "evidence_ledger.json"
             else "evidence_ledger.json")
    assert not (out / other).exists()


def test_cli_output_hardlink_flip_between_check_and_replace_is_harmless(tmp_path, monkeypatch, capsys):
    # The old check-then-ftruncate write had a real escape: a
    # hardlink flipped in between the fstat and the ftruncate
    # truncated the victim before the write. The rename write has
    # no such window: the flip replaces the output path itself,
    # and the victim inode is untouched by construction, so the
    # run completes rc 0 with the victim intact.
    import os

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text("do not overwrite\n")
    flipped = []

    def _replace_and_flip(src, dst):
        if not flipped:
            flipped.append(1)
            try:
                victim.unlink()
            except FileNotFoundError:
                pass
            os.link(dst, victim)
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _replace_and_flip)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-flip"])
    err = capsys.readouterr().err
    assert flipped, "os.replace was never called, so the flip was never exercised"
    assert rc == 0
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["report_id"] == "freeze-flip"


def test_cli_rewrite_changes_output_inode(tmp_path, capsys):
    # Rename semantics: a rewrite replaces the output path with a
    # fresh temp file, so the inode changes. (The temp inode is
    # allocated while the old file still exists, so it cannot be
    # the same inode.)
    import os

    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    (out / "evidence_report.md").write_text("# old report\n")
    before = {name: os.stat(out / name).st_ino
              for name in ("evidence_ledger.json", "evidence_report.md")}
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-inode"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    for name in ("evidence_ledger.json", "evidence_report.md"):
        assert os.stat(out / name).st_ino != before[name], name
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["report_id"] == "freeze-inode"


def test_cli_output_hardlink_planted_after_precheck_exits_2(tmp_path, monkeypatch, capsys):
    # The write-outputs pre-check catches a hardlink planted
    # before it runs, but the _write_one lstat is the guard for
    # a hardlink planted after the pre-check and before the
    # write. Plant one inside the lstat call itself: the write
    # must refuse rc 2 with the checks file byte-identical,
    # never rename over the planted link.
    import os

    import cli

    real_lstat = os.lstat
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    original = checks_file.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    planted = []

    def _lstat_and_plant(path, *args, **kwargs):
        st = real_lstat(path, *args, **kwargs)
        if not planted and str(path).endswith("evidence_ledger.json"):
            planted.append(1)
            os.unlink(path)
            os.link(checks_file, path)
            st = real_lstat(path, *args, **kwargs)
        return st

    monkeypatch.setattr(os, "lstat", _lstat_and_plant)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-late-hardlink"])
    err = capsys.readouterr().err
    assert planted, "the lstat hook never ran, so the plant was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "hardlinked to another file" in err
    assert "Traceback" not in err
    assert checks_file.read_bytes() == original
    # The planted link itself is gone after the refusal: the
    # poisoned output-path entry is unlinked, so no link to the
    # checks file is left behind at the output path.
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_symlink_flip_exits_2(tmp_path, monkeypatch, capsys):
    # The old rename write closed the temp fd before os.replace
    # and chmod'ed the output by path afterwards, and never
    # identity-checked the temp entry: swapping the temp for a
    # symlink to a victim before the replace left the ledger
    # path as a symlink to the victim and chmod'ed the victim
    # under a success exit code. The write now verifies, while
    # the temp fd is still open, that the output path names the
    # temp inode, so a swapped temp refuses rc 2 and the victim
    # keeps its mode and bytes.
    import os
    import stat

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o644)
    flipped = []

    def _replace_and_flip(src, dst):
        if not flipped and ".tmp-" in str(src):
            flipped.append(1)
            os.unlink(src)
            os.symlink(victim, src)
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _replace_and_flip)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-temp-symlink"])
    err = capsys.readouterr().err
    assert flipped, "os.replace was never called, so the flip was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert victim.read_text() == "do not overwrite\n"
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_hardlink_flip_exits_2(tmp_path, monkeypatch, capsys):
    # Same escape as the symlink flip, through a hardlink: the
    # swapped temp made the ledger path the victim inode, so the
    # ledger read back the victim's bytes and the victim's mode
    # changed under a success exit code. The post-rename
    # identity check sees the victim inode and the link count
    # of 2 and refuses rc 2 instead.
    import os
    import stat

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o644)
    flipped = []

    def _replace_and_flip(src, dst):
        if not flipped and ".tmp-" in str(src):
            flipped.append(1)
            os.unlink(src)
            os.link(victim, src)
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _replace_and_flip)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-temp-hardlink"])
    err = capsys.readouterr().err
    assert flipped, "os.replace was never called, so the flip was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert victim.read_text() == "do not overwrite\n"
    assert os.stat(victim).st_nlink == 1
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_swap_after_replace_exits_2(tmp_path, monkeypatch, capsys):
    # The identity check itself is the last guard: a swap
    # planted after the rename, inside the verification lstat,
    # must be seen by that lstat, so the write refuses rc 2
    # instead of leaving a symlinked output behind. There is
    # no chmod by path anymore for the swap to redirect.
    import os
    import stat

    import cli

    real_replace = os.replace
    real_lstat = os.lstat
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o644)
    replaced = []
    swapped = []

    def _replace_and_mark(src, dst):
        result = real_replace(src, dst)
        if str(dst).endswith("evidence_ledger.json"):
            replaced.append(1)
        return result

    def _lstat_and_swap(path, *args, **kwargs):
        if (replaced and not swapped
                and str(path).endswith("evidence_ledger.json")):
            # The first lstat of the ledger after its replace
            # is the verification: plant the swap, then return
            # the post-swap stat, so the check sees it.
            swapped.append(1)
            os.unlink(path)
            os.symlink(victim, path)
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "replace", _replace_and_mark)
    monkeypatch.setattr(os, "lstat", _lstat_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-post-rename"])
    err = capsys.readouterr().err
    assert replaced, "os.replace was never called"
    assert swapped, "the verification lstat never ran, so the swap was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert victim.read_text() == "do not overwrite\n"
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_setuid_mode_is_masked(tmp_path, capsys):
    # A pre-planted setuid stale output used to make the
    # rewritten ledger setuid, because the recorded mode was
    # restored unmasked. The preserved mode is now masked to
    # the permission bits, so the rewrite keeps 0755, never
    # 4755.
    import os
    import stat

    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o4755)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-setuid"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    mode = stat.S_IMODE(os.stat(out / "evidence_ledger.json").st_mode)
    assert mode == 0o755, oct(mode)


def test_cli_output_temp_mode_tamper_exits_2(tmp_path, monkeypatch, capsys):
    # The written file's mode is verified through its open fd: if
    # the temp inode's mode is changed after the fchmod, the
    # post-rename check must refuse rc 2 instead of writing a
    # ledger whose mode an attacker chose. Tamper inside fchmod
    # itself, after the real call, so the mode the fd reports
    # afterwards is not the expected one.
    import os

    import cli

    real_fchmod = os.fchmod
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o644)
    tampered = []

    def _fchmod_and_tamper(fd, mode, *args, **kwargs):
        real_fchmod(fd, mode, *args, **kwargs)
        if not tampered:
            tampered.append(1)
            real_fchmod(fd, 0o777)

    monkeypatch.setattr(os, "fchmod", _fchmod_and_tamper)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-mode-tamper"])
    err = capsys.readouterr().err
    assert tampered, "the fchmod hook never ran, so the tamper was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_setuid_tamper_fresh_exits_2(tmp_path, monkeypatch, capsys):
    # The mode is compared including setuid, setgid, and sticky
    # bits: a tamper that adds only setuid to a fresh output's temp
    # inode must refuse rc 2, even though the permission bits are
    # unchanged. Tamper inside os.replace, after the real rename,
    # so the fd's mode is setuid plus the expected mode when the
    # post-rename check reads it back. The tamper mode is computed
    # from the live umask (a fresh temp is created 0o666 minus
    # umask), so the permission bits match the expected mode under
    # any umask and only the setuid bit differs. No fchmod runs on
    # the fresh-file path, so the replace hook is the only place
    # to plant this tamper.
    import os

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    tampered = []
    current_umask = os.umask(0)
    os.umask(current_umask)
    tamper_mode = 0o4000 | (0o666 & ~current_umask)

    def _replace_and_tamper(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        if not tampered:
            tampered.append(1)
            os.chmod(dst, tamper_mode)
        return result

    monkeypatch.setattr(os, "replace", _replace_and_tamper)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-setuid-tamper-fresh"])
    err = capsys.readouterr().err
    assert tampered, "the replace hook never ran, so the tamper was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_setuid_tamper_preexisting_exits_2(tmp_path, monkeypatch, capsys):
    # Same special-bits-only tamper, on the pre-existing-file path:
    # the ledger is pre-seeded at 0o755, so fchmod runs with the
    # expected mode 0o755; tamper inside fchmod, after the real
    # call, to 0o4755. The permission bits are unchanged, so only
    # the unmasked comparison catches it.
    import os

    import cli

    real_fchmod = os.fchmod
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    os.chmod(out / "evidence_ledger.json", 0o755)
    tampered = []

    def _fchmod_and_tamper(fd, mode, *args, **kwargs):
        real_fchmod(fd, mode, *args, **kwargs)
        if not tampered:
            tampered.append(1)
            real_fchmod(fd, 0o4755)

    monkeypatch.setattr(os, "fchmod", _fchmod_and_tamper)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-setuid-tamper-pre"])
    err = capsys.readouterr().err
    assert tampered, "the fchmod hook never ran, so the tamper was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_content_tamper_exits_2(tmp_path, monkeypatch, capsys):
    # The bytes read back through the fd must hash to the digest
    # of the bytes written: if the temp inode's content is changed
    # after the write, the post-rename check must refuse rc 2
    # instead of writing a ledger whose bytes an attacker chose.
    # Tamper inside os.replace, appending to the temp file before
    # the real rename.
    import os

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    tampered = []

    def _replace_and_tamper(src, dst, *args, **kwargs):
        if not tampered:
            tampered.append(1)
            with open(src, "ab") as f:
                f.write(b"tampered")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", _replace_and_tamper)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-content-tamper"])
    err = capsys.readouterr().err
    assert tampered, "the replace hook never ran, so the tamper was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "content changed" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_temp_write_failure_exits_2(tmp_path, monkeypatch, capsys):
    # A failure during the temp write itself (a disk error, a
    # crash) must refuse rc 2 with no partial output and no orphan
    # temp file. Patch os.write to raise OSError once, on the
    # first write to a temp fd: the temp is unlinked by _write_one's
    # cleanup, and the CLI removes the stale outputs rather than
    # leaving a pass-looking report. The temp fds are identified
    # through an os.open wrapper, so no other os.write caller in
    # the process is disturbed.
    import os

    import cli

    real_open = os.open
    real_write = os.write
    temp_fds = set()
    raised = []

    def _open_and_record(path, *args, **kwargs):
        fd = real_open(path, *args, **kwargs)
        if os.path.basename(str(path)).startswith(".evidence_"):
            temp_fds.add(fd)
        return fd

    def _write_once(fd, data, *args, **kwargs):
        if fd in temp_fds and not raised:
            raised.append(1)
            raise OSError("simulated temp write failure")
        return real_write(fd, data, *args, **kwargs)

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"old": "ledger"}\n')
    (out / "evidence_report.md").write_text("# old report\n")
    monkeypatch.setattr(os, "open", _open_and_record)
    monkeypatch.setattr(os, "write", _write_once)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-temp-write-fail"])
    err = capsys.readouterr().err
    assert raised, "the write hook never ran, so the failure was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()
    assert list(out.glob(".evidence_*.tmp-*")) == []


def test_write_one_temp_write_failure_keeps_target(tmp_path, monkeypatch):
    # The same failure one layer down: _write_one raises OSError,
    # and the pre-existing target is byte-identical afterwards,
    # because the target is only ever replaced by rename, never
    # opened for writing. A refused run must not leave a
    # pass-looking report behind, so the CLI removes stale outputs
    # on a write failure; the byte-identical property therefore
    # belongs to _write_one, not to the CLI path, and is pinned
    # here directly.
    import os

    from reporter import _write_one

    real_open = os.open
    real_write = os.write
    temp_fds = set()
    raised = []

    def _open_and_record(path, *args, **kwargs):
        fd = real_open(path, *args, **kwargs)
        if os.path.basename(str(path)).startswith(".out"):
            temp_fds.add(fd)
        return fd

    def _write_once(fd, data, *args, **kwargs):
        if fd in temp_fds and not raised:
            raised.append(1)
            raise OSError("simulated temp write failure")
        return real_write(fd, data, *args, **kwargs)

    target = tmp_path / "out.json"
    target.write_text('{"old": "ledger"}\n')
    original = target.read_bytes()
    monkeypatch.setattr(os, "open", _open_and_record)
    monkeypatch.setattr(os, "write", _write_once)
    with pytest.raises(OSError, match="simulated temp write failure"):
        _write_one(target, b'{"new": "ledger"}\n')
    assert raised, "the write hook never ran, so the failure was never exercised"
    assert target.read_bytes() == original
    assert list(tmp_path.glob(".out.json.tmp-*")) == []


def test_cli_output_first_file_swapped_during_second_write_exits_2(tmp_path, monkeypatch, capsys):
    # write_outputs writes the ledger then the report. If the
    # already-written ledger is swapped for a symlink to a victim
    # during the report write, the old code exited rc 0 with the
    # poisoned ledger in place, because nothing re-checked the
    # first file after the second was written. Both paths are
    # re-checked after both writes now, so the swap refuses rc 2
    # and the victim keeps its mode and bytes.
    import os
    import stat

    import cli

    real_replace = os.replace
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    calls = []

    def _replace_and_swap(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        calls.append(str(dst))
        if len(calls) == 2:
            # Second write (the report) is done: swap the
            # already-written ledger for a symlink to the victim.
            # Swapping on the first call would be caught by the
            # ledger's own post-rename check instead, so the
            # cross-write re-check is only exercised here.
            ledger = out / "evidence_ledger.json"
            os.unlink(ledger)
            os.symlink(victim, ledger)
        return result

    monkeypatch.setattr(os, "replace", _replace_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-cross-swap"])
    err = capsys.readouterr().err
    assert len(calls) == 2, "both writes must have run for the swap to be exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_first_file_swapped_during_final_recheck_exits_2(tmp_path, monkeypatch, capsys):
    # The final re-check reads the first file, then the second: a
    # swap of the ledger during the report's check escaped the old
    # single pass, because the ledger had already been checked
    # clean and nothing looked at it again. Both paths are
    # re-checked twice in a row now, so the next pass catches the
    # swap. Arm the hook only in the final phase (after both
    # writes): swap the ledger for a symlink to a victim during
    # the second lstat of the report path after the writes, which
    # is the report's check in the first re-check pass. The
    # report's own post-rename verification lstat is the first
    # one after the writes, so it must not arm the hook.
    import os
    import stat

    import cli

    real_replace = os.replace
    real_lstat = os.lstat
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    ledger_path = out / "evidence_ledger.json"
    md_path = out / "evidence_report.md"
    replaces = []
    md_lstats_after_writes = []
    swapped = []

    def _replace_and_count(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        replaces.append(str(dst))
        return result

    def _lstat_and_swap(path, *args, **kwargs):
        if len(replaces) >= 2 and str(path) == str(md_path):
            md_lstats_after_writes.append(1)
            if len(md_lstats_after_writes) == 2 and not swapped:
                swapped.append(1)
                os.unlink(ledger_path)
                os.symlink(victim, ledger_path)
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "replace", _replace_and_count)
    monkeypatch.setattr(os, "lstat", _lstat_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-final-recheck"])
    err = capsys.readouterr().err
    assert swapped, "the lstat hook never fired, so the swap was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "replaced during the write" in err
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_output_first_file_swapped_during_second_final_recheck_pass_exits_2(tmp_path, monkeypatch, capsys):
    # The two-pass final re-check reads the ledger, then the
    # report, twice: a swap of the ledger during the report's
    # lstat in the second pass escaped the old loop, because the
    # ledger had already been checked clean in that pass and
    # nothing looked at it again, so the run exited rc 0 with a
    # poisoned ledger behind a valid report. A final re-check of
    # the ledger follows the two passes now and catches it. Arm
    # the hook only in the final phase (after both writes): swap
    # the ledger for a symlink to a victim during the third lstat
    # of the report path after the writes, which is the report's
    # check in the second re-check pass. The report's own
    # post-rename verification lstat is the first one after the
    # writes and the first pass's report check is the second, so
    # neither arms the hook.
    import os
    import stat

    import cli

    real_replace = os.replace
    real_lstat = os.lstat
    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    victim = tmp_path / "victim.txt"
    victim.write_text("do not overwrite\n")
    os.chmod(victim, 0o600)
    out = tmp_path / "out"
    out.mkdir()
    ledger_path = out / "evidence_ledger.json"
    md_path = out / "evidence_report.md"
    replaces = []
    md_lstats_after_writes = []
    swapped = []

    def _replace_and_count(src, dst, *args, **kwargs):
        result = real_replace(src, dst, *args, **kwargs)
        replaces.append(str(dst))
        return result

    def _lstat_and_swap(path, *args, **kwargs):
        if len(replaces) >= 2 and str(path) == str(md_path):
            md_lstats_after_writes.append(1)
            if len(md_lstats_after_writes) == 3 and not swapped:
                swapped.append(1)
                os.unlink(ledger_path)
                os.symlink(victim, ledger_path)
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "replace", _replace_and_count)
    monkeypatch.setattr(os, "lstat", _lstat_and_swap)
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-final-recheck-2"])
    err = capsys.readouterr().err
    assert swapped, "the lstat hook never fired, so the swap was never exercised"
    assert rc == 2
    assert "could not write output" in err
    assert "replaced during the write" in err
    assert "Traceback" not in err
    assert victim.read_text() == "do not overwrite\n"
    assert stat.S_IMODE(os.stat(victim).st_mode) == 0o600
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_deeply_nested_allowlist_exits_2(tmp_path, capsys):
    # A deeply nested --allowlist file used to escape the loader
    # with an uncaught RecursionError (traceback, exit 1).
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    allowlist_file = tmp_path / "allowlist.json"
    allowlist_file.write_text("[" * 20000 + "]" * 20000)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--allowlist", str(allowlist_file),
                   "--out", str(out), "--report-id", "freeze-deep-allowlist"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load allowlist" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_deeply_nested_ingest_file_exits_2(tmp_path, capsys):
    # A deeply nested --ingest file used to escape with an uncaught
    # RecursionError from the JSON parser (traceback, exit 1), because
    # the ingest_file call had no try/except at all.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    ingest_file = tmp_path / "ingest.json"
    ingest_file.write_text("[" * 20000 + "]" * 20000)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--out", str(out), "--report-id", "freeze-deep-ingest"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load ingest file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_deeply_nested_ingest_record_exits_2(tmp_path, capsys):
    # A genuinely 1000-deep nested field inside an otherwise valid
    # record used to be accepted by ingest and then crash the
    # ledger write: the retained raw_record made json.dumps raise
    # RecursionError after ingest had already accepted the run.
    # The explicit depth bound refuses it at load instead.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    nested = 1
    for _ in range(1000):
        nested = [nested]
    ingest_file = tmp_path / "ingest.json"
    ingest_file.write_text(json.dumps({
        "command": "pytest", "exit_code": 0, "stdout": "ok",
        "start_timestamp": "2026-11-08T12:00:00Z", "nested": nested}))
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--out", str(out), "--report-id", "freeze-deep-record"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load ingest file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_shallow_nested_ingest_record_loads(tmp_path, capsys):
    # Below the bound a nested record is ingested as a run: a
    # depth-50 nested field loads rc 0 with the run recorded.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "ingest depth test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "pytest"}],
    }))
    nested = "leaf"
    for _ in range(50):
        nested = [nested]
    ingest_file = tmp_path / "ingest.json"
    ingest_file.write_text(json.dumps({
        "command": "pytest", "exit_code": 0, "stdout": "ok",
        "start_timestamp": "2026-11-08T12:00:00Z", "nested": nested}))
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--final-edit-marker", "2026-11-01T00:00:00Z",
                   "--out", str(out), "--report-id", "freeze-shallow-record"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert len(ledger["runs"]) == 1
    assert ledger["runs"][0]["command_raw"] == "pytest"


def test_cli_deeply_nested_ingest_bare_array_exits_2(tmp_path, capsys):
    # A 5000-deep bare array used to parse under the C scanner and
    # complete rc 0 with an honest unparseable: 1 count, because
    # the parser only refuses past its own RecursionError limit.
    # The explicit depth bound refuses it at load now, so the
    # parse/write threshold split is gone.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    ingest_file = tmp_path / "ingest.json"
    ingest_file.write_text("[" * 5000 + "]" * 5000)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--out", str(out), "--report-id", "freeze-deep-bare"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load ingest file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_deeply_nested_runs_file_exits_2(tmp_path, capsys):
    # A deeply nested --runs file used to be unpinned: the
    # RecursionError catch in load_recorded_runs had no test,
    # while deeply nested allowlist, ingest, and checks all did.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    runs_file = tmp_path / "runs.json"
    runs_file.write_text("[" * 20000 + "]" * 20000)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--runs", str(runs_file),
                   "--out", str(out), "--report-id", "freeze-deep-runs"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load recorded runs" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_missing_ingest_file_exits_2(tmp_path, capsys):
    # A missing --ingest file used to complete rc 0 with a
    # clean-looking empty report, unlike the other loaders,
    # whose missing files refuse rc 2 with stale removal.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(tmp_path / "nope.json"),
                   "--out", str(out), "--report-id", "freeze-no-ingest"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load ingest file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_fifo_ingest_file_exits_2(tmp_path, capsys):
    # A FIFO --ingest file is unreadable the same way: refuse
    # rc 2, never hang, never silently complete.
    import os

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    fifo = tmp_path / "ingest.json"
    os.mkfifo(fifo)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = _run_cli_threaded(["--repo", str(repo), "--checks", str(checks_file),
                            "--ingest", str(fifo),
                            "--out", str(out), "--report-id", "freeze-fifo-ingest"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load ingest file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_deeply_nested_trace_line_is_unparseable(tmp_path, capsys):
    # A trace line nested too deeply to parse is counted
    # unparseable, like a line that is not JSON at all: the
    # summary tolerates bad lines, it never crashes on them.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": "c1", "input_tokens": 10, "output_tokens": 5}\n'
        + "[" * 20000 + "]" * 20000 + "\n")
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-deep-trace"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["events_by_type"].get("unparseable", 0) == 1
    assert ledger["trace_summary"]["input_tokens_total"] == 10


def test_record_to_run_never_stringifies_identity_fields():
    # --ingest used to str() a wrong-typed label, command, or
    # working directory into a run, so the judge verified on the
    # Python repr: a dict label verified with evidence_id
    # "{'x': 1}". Identity is never invented from a repr now.
    from universal_ingest import record_to_run

    # A dict or list label falls back to the command, the
    # documented last-resort label.
    run = record_to_run({"label": {"x": 1}, "command": "pytest", "exit_code": 0,
                         "start_timestamp": "2026-11-04T01:00:00Z"})
    assert run is not None
    assert run["label"] == "pytest"
    run = record_to_run({"label": ["x"], "command": "pytest", "exit_code": 0})
    assert run is not None
    assert run["label"] == "pytest"
    # A scalar int id is a usable label in its string form.
    run = record_to_run({"id": 7, "command": "pytest", "exit_code": 0})
    assert run is not None
    assert run["label"] == "7"
    # A dict working directory becomes "", never its repr.
    run = record_to_run({"command": "pytest", "exit_code": 0,
                         "working_directory": {"a": 1}})
    assert run is not None
    assert run["working_directory"] == ""
    # A dict command means no run at all, never a repr command.
    assert record_to_run({"command": {"c": "pytest"}, "exit_code": 0}) is None
    # A list command still joins, as before.
    run = record_to_run({"command": ["pytest", "-q"], "exit_code": 0})
    assert run is not None
    assert run["command_raw"] == "pytest -q"


def test_record_to_run_never_stringifies_command_parts():
    # The argv and list-command joins used to str() every element,
    # so a dict element became its Python repr inside the command:
    # {"argv": ["pytest", {"evil": 1}]} produced command_raw
    # "pytest {'evil': 1}", which a check could then verify on.
    # A non-string element now means no command, hence no run.
    from universal_ingest import record_to_run

    assert record_to_run({"argv": ["pytest", {"evil": 1}],
                          "exit_code": 0}) is None
    assert record_to_run({"argv": [{"a": 1}], "exit_code": 0}) is None
    assert record_to_run({"command": ["pytest", {"a": 1}],
                          "exit_code": 0}) is None
    assert record_to_run({"attributes": {"command": ["pytest", {"a": 1}]},
                          "exit_code": 0}) is None
    assert record_to_run({"argv": ["pytest", 3], "exit_code": 0}) is None
    # All-string elements still join, as before.
    run = record_to_run({"argv": ["pytest", "-q"], "exit_code": 0})
    assert run is not None
    assert run["command_raw"] == "pytest -q"
    run = record_to_run({"command": ["pytest", "tests/"], "exit_code": 0})
    assert run is not None
    assert run["command_raw"] == "pytest tests/"


def test_record_to_run_deeply_nested_record_refuses():
    # The depth bound is also enforced at the retention point:
    # a record nested deeper than the bound never becomes a run,
    # however it reached record_to_run, so a retained raw_record
    # can always be written into the ledger.
    from universal_ingest import record_to_run

    nested = 1
    for _ in range(1000):
        nested = [nested]
    with pytest.raises(ValueError, match="nested too deeply"):
        record_to_run({"command": "pytest", "exit_code": 0,
                       "start_timestamp": "2026-11-08T01:00:00Z",
                       "nested": nested})
    nested = "leaf"
    for _ in range(50):
        nested = [nested]
    run = record_to_run({"command": "pytest", "exit_code": 0,
                         "start_timestamp": "2026-11-08T01:00:00Z",
                         "nested": nested})
    assert run is not None
    assert run["command_raw"] == "pytest"


def test_record_to_run_ingest_depth_boundary():
    # The depth bound is 100, measured from the record root: a
    # record whose deepest leaf sits at depth 100 loads, depth 101
    # refuses. This pins the bound: changing MAX_INGEST_DEPTH to 60
    # or 500, or > to >=, would fail this test. The record root is
    # depth 1 and the "nested" field value is depth 2, so 98 nested
    # lists put the leaf at depth 100 and 99 put it at 101. A
    # list-wrapped record's own limit is one level lower, because
    # the wrapping list is depth 1 and the record is depth 2.
    from universal_ingest import ingest_text, record_to_run

    nested = "leaf"
    for _ in range(98):
        nested = [nested]
    run = record_to_run({"command": "pytest", "exit_code": 0,
                         "start_timestamp": "2026-11-08T01:00:00Z",
                         "nested": nested})
    assert run is not None
    assert run["command_raw"] == "pytest"
    nested = "leaf"
    for _ in range(99):
        nested = [nested]
    with pytest.raises(ValueError, match="nested too deeply"):
        record_to_run({"command": "pytest", "exit_code": 0,
                       "start_timestamp": "2026-11-08T01:00:00Z",
                       "nested": nested})
    nested = "leaf"
    for _ in range(97):
        nested = [nested]
    runs, _summary = ingest_text(_nested_ingest_text(nested))
    assert len(runs) == 1
    assert runs[0]["command_raw"] == "pytest"
    nested = "leaf"
    for _ in range(98):
        nested = [nested]
    with pytest.raises(ValueError, match="nested too deeply"):
        ingest_text(_nested_ingest_text(nested))


def _nested_ingest_text(nested):
    # A list-wrapped ingest file holding one record with the given
    # nested field value, so the depth check measures from the
    # parsed file root (the wrapping list) rather than the record.
    return json.dumps([{"command": "pytest", "exit_code": 0, "stdout": "ok",
                        "start_timestamp": "2026-11-08T12:00:00Z",
                        "nested": nested}])


def test_cli_ingested_dict_label_never_verifies_on_repr(tmp_path, capsys):
    # End-to-end mirror of the record_to_run test: an ingested
    # exit-0 run with a dict label used to judge VERIFIED with
    # evidence_id "{'x': 1}" and no flags. It now verifies on the
    # command fallback, and the repr appears nowhere in the ledger.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "ingest identity test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "pytest"}],
    }))
    ingest_file = tmp_path / "ingest.jsonl"
    ingest_file.write_text(json.dumps({
        "label": {"x": 1}, "command": "pytest", "exit_code": 0,
        "stdout": "ok", "start_timestamp": "2026-11-08T12:00:00Z"}) + "\n")
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--final-edit-marker", "2026-11-01T00:00:00Z",
                   "--out", str(out), "--report-id", "freeze-ingest-label"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger_text = (out / "evidence_ledger.json").read_text()
    assert "{'x': 1}" not in ledger_text
    ledger = json.loads(ledger_text)
    row = ledger["judgments"][0]
    assert row["status"] == "VERIFIED"
    assert row["evidence_id"] == "pytest"


def test_cli_ingested_argv_repr_never_appears_in_ledger(tmp_path, capsys):
    # End-to-end mirror of the record_to_run test: an ingested
    # record whose argv carries a dict element used to land in
    # the ledger as the repr command "pytest {'evil': 1}". The
    # record now yields no run at all, so the repr appears
    # nowhere in the ledger and the check stays NOT OBSERVED.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    checks_file.write_text(json.dumps({
        "task_intent": "ingest identity test",
        "task_intent_source": "test",
        "checks": [{"id": "C1", "text": "t", "check_type": "recorded_run",
                    "required_command": "pytest"}],
    }))
    ingest_file = tmp_path / "ingest.jsonl"
    ingest_file.write_text(json.dumps({
        "argv": ["pytest", {"evil": 1}], "exit_code": 0,
        "stdout": "ok", "start_timestamp": "2026-11-08T12:00:00Z"}) + "\n")
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--ingest", str(ingest_file),
                   "--final-edit-marker", "2026-11-01T00:00:00Z",
                   "--out", str(out), "--report-id", "freeze-ingest-argv"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger_text = (out / "evidence_ledger.json").read_text()
    assert "{'evil': 1}" not in ledger_text
    ledger = json.loads(ledger_text)
    assert ledger["judgments"][0]["status"] == "NOT OBSERVED"


def test_cli_unreadable_repo_file_exits_2(tmp_path, capsys):
    # An unreadable file in the target repo used to escape the
    # snapshot with an uncaught traceback and exit 1. It refuses
    # with exit 2 and stale removal now, like every other loader.
    import os

    import cli

    repo = make_repo(tmp_path)
    os.symlink("/proc/self/mem", repo / "poison.txt")
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--out", str(out), "--report-id", "freeze-poison-repo"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot snapshot repo" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_non_utf8_trace_file_exits_2(tmp_path, capsys):
    # A non-UTF-8 trace file refuses correctly but was unpinned:
    # the decode raises UnicodeDecodeError, a ValueError, so the
    # trace loader refusal path handles it.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_bytes(
        b'{"type": "model", "case_id": "c1", "input_tokens": 10}\n\xff\n')
    out = tmp_path / "out"
    out.mkdir()
    (out / "evidence_ledger.json").write_text('{"stale": "pass-looking"}\n')
    (out / "evidence_report.md").write_text("# stale pass-looking report\n")
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-non-utf8"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "cannot load trace file" in err
    assert "Traceback" not in err
    assert not (out / "evidence_ledger.json").exists()
    assert not (out / "evidence_report.md").exists()


def test_cli_trace_zero_case_id_counts(tmp_path, capsys):
    # A model event with case_id 0 used to count its tokens but
    # not count as a case (cases == 0): the count used
    # `if case_id:`. Zero is a case id, not an absence.
    import cli

    repo = make_repo(tmp_path)
    checks_file = tmp_path / "checks.json"
    write_checks(checks_file)
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text(
        '{"type": "model", "case_id": 0, "input_tokens": 10, '
        '"output_tokens": 5}\n')
    out = tmp_path / "out"
    rc = cli.main(["--repo", str(repo), "--checks", str(checks_file),
                   "--trace", str(trace_file),
                   "--out", str(out), "--report-id", "freeze-zero-case"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "Traceback" not in err
    ledger = json.loads((out / "evidence_ledger.json").read_text())
    assert ledger["trace_summary"]["cases"] == 1
    assert ledger["trace_summary"]["input_tokens_total"] == 10
