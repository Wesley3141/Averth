"""Tests for wave 2: normaliser, timestamps, artifact snapshot, live fetch.

No test here makes a network call, executes a transcript
command, or uses a credential. The live fetch test uses a
test double getter returning canned API JSON. The artifact
test uses only tmp files. The normaliser test uses only
in-memory text.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from artifact_snapshot import sha256_file, snapshot_artifact
from pr_live_fetch import convert_live, fetch_pr_data
from timestamp_capture import marker_from_directory, missing_fact_verdict, validate_iso
from trace_normaliser import normalise_text


def test_normaliser_jsonl_passthrough():
    text = '{"type": "model", "case_id": "a", "input_tokens": 3}\n{"type": "tool", "case_id": "a"}\n'
    events, bad = normalise_text(text)
    assert len(events) == 2 and bad == 0
    assert events[0]["type"] == "model" and events[0]["case_id"] == "a"


def test_normaliser_json_array():
    text = '[{"type": "model", "case_id": "b"}, {"type": "retry", "case_id": "b"}]'
    events, bad = normalise_text(text)
    assert len(events) == 2 and bad == 0


def test_normaliser_pretty_printed_and_counts_bad():
    text = '{\n  "type": "model",\n  "case_id": "c"\n}\nnot json at all\n{"type": "end", "case_id": "c"}\n'
    events, bad = normalise_text(text)
    assert len(events) == 2
    assert bad == 1
    assert events[0]["case_id"] == "c"


def test_normaliser_does_not_invent_type_or_case():
    events, bad = normalise_text('{"foo": 1}\n')
    assert len(events) == 1
    assert "type" not in events[0] and "case_id" not in events[0]


def test_validate_iso_accepts_z_and_offset():
    assert validate_iso("2026-11-04T12:00:00Z") is not None
    assert validate_iso("2026-11-04T12:00:00+00:00") is not None
    assert validate_iso("not a time") is None
    assert validate_iso(None) is None


def test_missing_timestamp_is_not_observed():
    status, reason = missing_fact_verdict(None, "2026-11-04T12:00:00Z")
    assert status == "NOT OBSERVED"
    assert "not citable" in reason


def test_superseded_run_is_not_observed():
    status, reason = missing_fact_verdict("2026-11-04T11:00:00Z", "2026-11-04T12:00:00Z")
    assert status == "NOT OBSERVED"
    assert "superseded" in reason


def test_citable_run_after_marker():
    status, _ = missing_fact_verdict("2026-11-04T13:00:00Z", "2026-11-04T12:00:00Z")
    assert status == "CITABLE"


def test_marker_from_directory(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    marker = marker_from_directory(str(tmp_path))
    assert marker is not None


def test_artifact_snapshot_copies_and_digests(tmp_path):
    src = tmp_path / "app.bin"
    src.write_text("binary-content-here")
    snap = tmp_path / "snapshot"
    entry = snapshot_artifact(str(src), str(snap), name="app.bin")
    assert entry["sha256_digest"] == sha256_file(snap / "app.bin")
    assert (snap / "snapshot.json").exists()
    record = json.loads((snap / "snapshot.json").read_text())
    assert record["artifacts"][0]["name"] == "app.bin"


def test_artifact_snapshot_rejects_url(tmp_path):
    snap = tmp_path / "snapshot"
    try:
        snapshot_artifact("https://example.com/app.bin", str(snap), name="app.bin")
    except ValueError:
        return
    raise AssertionError("URL source should be rejected, never a digest")


def test_artifact_snapshot_rejects_missing_file(tmp_path):
    snap = tmp_path / "snapshot"
    try:
        snapshot_artifact(str(tmp_path / "nope.bin"), str(snap), name="nope.bin")
    except ValueError:
        return
    raise AssertionError("missing source should be rejected")


def test_live_fetch_uses_getter_and_maps_conclusions():
    def getter(url):
        if url.endswith("/pulls/123"):
            return {"number": 123, "head": {"sha": "abc123"}}
        if "/files" in url:
            return [{"filename": "src/a.py", "patch": "@@ -1 +1 @@\n-x\n+y"}]
        if "/reviews" in url:
            return [{"user": {"login": "rev"}, "body": "looks good"}]
        if "/comments" in url:
            return []
        if "/check-runs" in url:
            return {"check_runs": [
                {"name": "CI", "conclusion": "success", "started_at": "2026-11-04T10:00:00Z", "completed_at": "2026-11-04T10:05:00Z"},
                {"name": "lint", "conclusion": "failure", "started_at": "2026-11-04T10:00:00Z", "completed_at": "2026-11-04T10:02:00Z"},
            ]}
        raise AssertionError(f"unexpected url {url}")

    data = fetch_pr_data("owner/repo", 123, getter=getter)
    runs, claims = convert_live(data, "owner/repo", 123)
    assert len(runs) == 2
    assert runs[0]["exit_code"] == 0 and runs[1]["exit_code"] == 1
    assert runs[0]["command"] == "ci-check: CI"
    assert claims["live_fetch_status"] == "not_live_verified"
    assert any(c["tier"] == 0 for c in claims["tier0_claims"])
