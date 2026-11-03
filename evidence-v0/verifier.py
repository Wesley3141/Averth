"""verifier: judge each human-written check against recorded runs.

Status rules, exactly:
- NOT APPLICABLE is judged before evidence, with a recorded reason.
- recorded_run: cite only a run whose normalised command matches the
  required command AND whose start is at/after the final edit marker.
  A run before the marker is superseded: retained, never cited, and
  its presence alone yields NOT OBSERVED with a stale flag.
  Cited run exit 0 -> VERIFIED; exit non-zero -> FAILED.
  No cited run -> NOT OBSERVED. NOT OBSERVED is a statement about
  the records, never proof the work never happened, and never FAILED.
- If a check names an artifact with an expected digest and the repo
  snapshot digest differs, a would-be VERIFIED is downgraded to
  NOT OBSERVED with a digest_mismatch flag (the observed state does
  not match the expected revision). A FAILED stands: a real failure
  is a real failure.
- artifact_presence: the tool scanned the repo now. Present (and
  digest-matching if expected) -> VERIFIED, Tier 2. Absent -> FAILED,
  because the scan itself ran and the artifact was not there. (A
  "build artifact exists" criterion where no build was ever run must
  instead be written as a recorded_run check for the build command,
  which yields NOT OBSERVED when no build was recorded.)
- external: EXTERNAL-UNVERIFIABLE unless a human_confirmation record
  with a named tester, a named procedure, and a pass/fail result is
  supplied; then VERIFIED/FAILED at Tier 4, scoped to that procedure.

A successful shell command is never proof of complete correctness:
every VERIFIED row carries the check's scope limitation verbatim.
"""
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from evidence_ledger import is_superseded, parse_time, sha256_text
from trace_adapter import normalize_command

# Execution allowlist for --execute mode. The ONLY commands this tool
# will ever run are pytest invocations whose arguments are relative
# test paths/nodes inside the repo. No shell, no arbitrary command
# from a README, PR, issue, or transcript is ever executed.
ALLOWED_PYTEST_FLAGS = {"-q", "-v", "--tb=short", "--tb=line"}


def execute_allowed(command_str, repo_path, interpreter=None):
    """Return an argv list if the command is allowlisted, else None."""
    try:
        parts = shlex.split(str(command_str))
    except ValueError:
        return None
    if len(parts) < 4:
        return None
    if parts[1:3] != ["-m", "pytest"]:
        return None
    repo = Path(repo_path).resolve()
    for arg in parts[3:]:
        if arg in ALLOWED_PYTEST_FLAGS:
            continue
        if arg.startswith("-"):
            return None
        if arg.startswith("/") or ".." in Path(arg).parts:
            return None
        if not (repo / arg.split("::")[0]).exists():
            return None
    return [interpreter or sys.executable] + parts[1:]


def run_allowlisted(command_str, repo_path, interpreter=None):
    """Execute one allowlisted check and return a v0_recorder run.

    The interpreter is the operator's explicit choice (--python), or
    sys.executable by default. It is recorded in the run's raw
    command. A run that fails because the interpreter lacks pytest
    records that failure honestly (exit 1, 'No module named pytest');
    it is not silently retried under a different interpreter.
    """
    argv = execute_allowed(command_str, repo_path, interpreter=interpreter)
    if argv is None:
        raise ValueError(f"command is not allowlisted and will not run: {command_str!r}")
    start = datetime.now(timezone.utc)
    proc = subprocess.run(argv, cwd=str(repo_path), capture_output=True,
                          text=True, timeout=300)
    end = datetime.now(timezone.utc)
    output = proc.stdout + proc.stderr
    return {
        "label": f"v0 run: {command_str}",
        "command_raw": " ".join(argv),
        "command_normalized": normalize_command(" ".join(argv)),
        "working_directory": str(repo_path),
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
        "exit_code": proc.returncode,
        "output_digest": sha256_text(output),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "source": "v0_recorder",
        "trust_tier": 2,
    }


def _base(check):
    return {
        "criterion_id": check["id"],
        "criterion_text": check.get("text", ""),
        "criterion_source": check.get("source", ""),
        "expected_evidence": check.get("expected_evidence", ""),
        "check_type": check.get("check_type"),
        "evidence_id": None,
        "evidence_source": "none",
        "trust_tier": None,
        "flags": [],
        "scope_limitation": check.get(
            "scope_limitation",
            "A successful command is not proof of complete correctness; "
            "this row proves only what its cited observation shows.",
        ),
        "recommended_next_action": check.get("recommended_next_action", ""),
    }


def judge(check, runs, snapshot, final_edit_marker):
    row = _base(check)
    if check.get("applicability") == "not_applicable":
        row["status"] = "NOT APPLICABLE"
        row["recommended_next_action"] = (
            check.get("not_applicable_reason", "Criterion does not apply to this change.")
        )
        return row

    ctype = check.get("check_type")
    if ctype == "recorded_run":
        wanted = normalize_command(check["required_command"])
        candidates = [r for r in runs if r["command_normalized"] == wanted]
        cited = [r for r in candidates if not is_superseded(r, final_edit_marker)]
        # A run with no parseable timestamp cannot be trusted as
        # after-final-edit evidence; treat it as not citable.
        cited = [r for r in cited if parse_time(r.get("start_timestamp")) is not None]
        if cited:
            run = max(cited, key=lambda r: parse_time(r["start_timestamp"]))
            row["evidence_id"] = run["label"] or run["command_raw"]
            row["evidence_source"] = run["source"]
            row["trust_tier"] = run["trust_tier"]
            row["command"] = run["command_raw"]
            row["working_directory"] = run["working_directory"]
            row["start_timestamp"] = run["start_timestamp"]
            row["end_timestamp"] = run["end_timestamp"]
            row["exit_code"] = run["exit_code"]
            row["output_digest"] = run["output_digest"]
            row["test_target"] = check.get("test_target")
            row["after_final_edit"] = True
            if run["exit_code"] == 0:
                row["status"] = "VERIFIED"
                # Digest check: observed state must match the expected
                # revision, or the VERIFIED cannot stand.
                art = check.get("artifact_path")
                exp = check.get("expected_digest")
                if art and exp and snapshot.get(art) != exp:
                    row["status"] = "NOT OBSERVED"
                    row["flags"].append("digest_mismatch")
                    row["scope_limitation"] += (
                        " Downgraded from VERIFIED: the repo snapshot digest "
                        "for the named artifact does not match the expected "
                        "digest, so the cited run cannot verify the current revision."
                    )
            else:
                row["status"] = "FAILED"
            return row
        if candidates:
            row["flags"].append("superseded_only")
            row["recommended_next_action"] = (
                "Re-run the prescribed command after the final edit and "
                "record the new run; the superseded run is retained in "
                "history and is never cited."
            )
        else:
            row["recommended_next_action"] = (
                "Run the prescribed command in an instrumented run and "
                "record the result; absence from the records is not proof "
                "the work never happened."
            )
        row["status"] = "NOT OBSERVED"
        row["after_final_edit"] = None
        return row

    if ctype == "artifact_presence":
        art = check["artifact_path"]
        row["evidence_source"] = "v0_recorder"
        row["trust_tier"] = 2
        row["artifact_path"] = art
        if art in snapshot:
            exp = check.get("expected_digest")
            if exp and snapshot[art] != exp:
                row["status"] = "FAILED"
                row["flags"].append("digest_mismatch")
                row["recommended_next_action"] = "Resolve the artifact digest mismatch."
            else:
                row["status"] = "VERIFIED"
                row["artifact_digest"] = snapshot[art]
        else:
            row["status"] = "FAILED"
            row["recommended_next_action"] = "Produce the named artifact and re-run."
        return row

    if ctype == "external":
        rec = check.get("human_confirmation")
        if rec and rec.get("tester") and rec.get("procedure") and rec.get("result") in ("pass", "fail"):
            row["status"] = "VERIFIED" if rec["result"] == "pass" else "FAILED"
            row["trust_tier"] = 4
            row["evidence_source"] = "human"
            row["evidence_id"] = f"human confirmation: {rec['tester']}, {rec['procedure']}"
            row["scope_limitation"] = (
                "Scoped to exactly the named tester, procedure, hardware "
                "and revision in the confirmation record; it does not "
                "transfer to other hardware, procedures, or revisions."
            )
        else:
            row["status"] = "EXTERNAL-UNVERIFIABLE"
            row["recommended_next_action"] = (
                "Supply a named human/hardware confirmation record "
                "(tester, procedure, result), or drop the claim."
            )
        return row

    raise ValueError(f"unknown check_type: {ctype!r}")


def judge_all(checks, runs, snapshot, final_edit_marker):
    return [judge(c, runs, snapshot, final_edit_marker) for c in checks]
