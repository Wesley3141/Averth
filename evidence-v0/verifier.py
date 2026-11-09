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

# Execution allowlist for --execute mode. Without an allowlist file,
# the ONLY commands this tool will ever run are pytest invocations
# whose arguments are relative test paths/nodes inside the repo.
# With an operator-written allowlist file (cli --allowlist), any
# command listed exactly, token for token, may run, any runner,
# with the destructive-command review warning in run_via_allowlist.
# No shell, no arbitrary command from a README, PR, issue, or
# transcript is ever executed.
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


def run_via_allowlist(command_str, repo_path, allowlist):
    """Execute one command listed exactly in an allowlist file.

    Wave 3 generic execution path: unlike run_allowlisted,
    which is pytest only, this path works for any runner,
    because the gate is exact listing, not the runner name.
    The operator must have written the allowlist, named an
    approver, and the caller must pass the loaded allowlist
    dict. A command not listed exactly is refused, never
    run. Warning, kept verbatim from wave 1: an allowlist
    does not make a command safe in general. If the listed
    command itself deletes files, it will run, because the
    operator approved that exact command. Review the listed
    commands before approving them, and never approve a
    list copied from an untrusted source. Quoting limit:
    listed commands are split with shlex, so prefer script
    files over -c code.
    """
    import shlex as _shlex
    from runner_allowlist import validate_command as _validate
    entry = _validate(command_str, allowlist)
    if entry is None:
        raise ValueError(f"command is not in the allowlist, not run: {command_str!r}")
    argv_list = _shlex.split(command_str)
    repo = Path(repo_path).resolve()
    start = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(argv_list, cwd=str(repo), capture_output=True,
                              text=True, timeout=allowlist.get("timeout_seconds", 300))
        output, exit_code = proc.stdout + proc.stderr, proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        exit_code, stdout, stderr = 124, exc.stdout or "", exc.stderr or ""
    except OSError as exc:
        # A missing runner binary is not a run: it propagates to
        # the CLI, which refuses with exit 2 and stale removal
        # instead of a traceback.
        raise OSError(f"cannot execute allowlisted command {command_str!r}: {exc}") from exc
    end = datetime.now(timezone.utc)
    return {
        "label": entry.get("label", command_str),
        "command_raw": command_str,
        "command_normalized": normalize_command(command_str),
        "working_directory": str(repo),
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
        "exit_code": exit_code,
        "output_digest": sha256_text(output),
        "stdout": stdout,
        "stderr": stderr,
        "source": "allowlist_recorder",
        "trust_tier": 2,
    }


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
    try:
        proc = subprocess.run(argv, cwd=str(repo_path), capture_output=True,
                              text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        # A timed-out run is recorded honestly, exit 124,
        # mirroring run_via_allowlist, not a crash.
        end = datetime.now(timezone.utc)
        output = (exc.stdout or "") + (exc.stderr or "")
        return {
            "label": f"v0 run: {command_str}",
            "command_raw": " ".join(argv),
            "command_normalized": normalize_command(" ".join(argv)),
            "working_directory": str(repo_path),
            "start_timestamp": start.isoformat(),
            "end_timestamp": end.isoformat(),
            "exit_code": 124,
            "output_digest": sha256_text(output),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "source": "v0_recorder",
            "trust_tier": 2,
        }
    except OSError as exc:
        # A missing interpreter is not a run: it propagates to
        # the CLI, which refuses with exit 2 and stale removal
        # instead of a traceback.
        raise OSError(f"cannot execute {command_str!r}: {exc}") from exc
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


_DEFAULT_SCOPE_LIMITATION = (
    "A successful command is not proof of complete correctness; "
    "this row proves only what its cited observation shows."
)


def _validate_check(check):
    """Refuse a malformed check with ValueError, mirroring load_checks.

    judge() is a directly unit-tested entry point, so it must not
    crash (KeyError/AttributeError/TypeError) or silently VERIFIED
    garbage when called outside load_checks. Only the fields
    judge() actually reads are validated here: the id, the
    check_type, the applicability, the required_command of a
    recorded_run check, artifact_path and expected_digest
    whenever present, test_target whenever present (a string,
    or null, which the fixture checks files use for "no test
    target"), the human_confirmation shape, and the string
    fields judge() copies into the row (text, source,
    expected_evidence, recommended_next_action,
    not_applicable_reason). A whitespace-only string is not a
    name: the non-empty checks strip, as in load_checks.
    """
    if not isinstance(check, dict):
        raise ValueError("each check must be a JSON object")
    cid = check.get("id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError(f"check id missing or not a string: {cid!r}")
    ctype = check.get("check_type")
    if ctype not in ("recorded_run", "artifact_presence", "external", "inferred"):
        raise ValueError(f"check {cid}: unknown check_type {ctype!r}")
    if ("applicability" in check
            and check["applicability"] not in ("applies", "not_applicable")):
        raise ValueError(f"check {cid}: bad applicability")
    if ctype == "recorded_run":
        rc = check.get("required_command")
        if not isinstance(rc, str) or not rc.strip():
            raise ValueError(f"check {cid}: recorded_run needs a non-empty string required_command")
    for field in ("artifact_path", "expected_digest"):
        if field in check and (not isinstance(check[field], str) or not check[field].strip()):
            raise ValueError(f"check {cid}: {field} must be a non-empty string")
    if ctype == "artifact_presence" and "artifact_path" not in check:
        raise ValueError(f"check {cid}: artifact_presence needs a non-empty string artifact_path")
    if "test_target" in check and check["test_target"] is not None \
            and not isinstance(check["test_target"], str):
        raise ValueError(f"check {cid}: test_target must be a string or null")
    for field in ("text", "source", "expected_evidence",
                  "recommended_next_action", "not_applicable_reason"):
        if field in check and not isinstance(check[field], str):
            raise ValueError(f"check {cid}: {field} must be a string")
    if "human_confirmation" in check:
        rec = check["human_confirmation"]
        if not isinstance(rec, dict):
            raise ValueError(f"check {cid}: human_confirmation must be a JSON object")
        for field in ("tester", "procedure"):
            if field in rec and (not isinstance(rec[field], str) or not rec[field].strip()):
                raise ValueError(f"check {cid}: human_confirmation {field} must be a non-empty string")


def _validate_judging_inputs(runs, snapshot):
    """Refuse malformed judging inputs with ValueError, never a crash.

    judge() is a directly unit-tested entry point: a caller may hand
    it runs that never passed load_recorded_runs, so the shape of
    the runs list and the snapshot must be checked here. A run entry
    that is not a dict, or a snapshot that is not a dict, is a caller
    error, refused with ValueError. The fields of a cited run are
    checked separately in judge(), after citation: a cited run
    whose evidence identity is missing or wrong-typed (label,
    command_raw, trust_tier, source, output_digest, exit_code)
    returns NOT OBSERVED with a missing_* or invalid_* flag, never a
    VERIFIED on malformed evidence. working_directory must be a
    string (the loaders record an absent one as ""); end_timestamp
    may be absent (the loaders record it as None), but a
    wrong-typed value is refused the same way. A run missing an
    exit code stays NOT OBSERVED with missing_exit_code.
    """
    if not isinstance(runs, list):
        raise ValueError("runs must be a list of recorded-run dicts")
    for r in runs:
        if not isinstance(r, dict):
            raise ValueError("each recorded run must be a JSON object")
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a dict of artifact path to digest")


def _cited_run_field_flags(run):
    """Return every flag for a cited run with malformed evidence, or [].

    The verdict's evidence identity must be real: the evidence id
    comes from a non-empty string label or command_raw, the source
    must name where the run was observed, the output digest must
    be a non-empty string, the trust tier must be an integer in
    1 to 4 (not a bool), and the exit code must be an integer
    (not a bool). A string "0" compares equal to 0 and a float
    0.0 compares equal to 0, so either would produce a false
    verdict if it reached the exit-code comparison. working_directory
    must be a string (an absent one is recorded as "" by the
    loaders); end_timestamp may be absent (None), but a wrong-typed
    value is malformed evidence, not metadata. Each field is
    validated on its own, so a wrong-typed label cannot hide
    behind a usable command_raw (or the reverse): a list label is
    invalid_label even when command_raw names the run, and a
    wrong-typed trust tier is invalid_trust_tier even when the
    run otherwise verifies. A label or command_raw that is simply
    absent is not invalid on its own: the joint missing_evidence_id
    covers the case where neither names the run. A trust tier that
    is simply absent is not invalid either: the loaders always
    record one, and a direct judge() caller that omits it gets
    tier None, the honest default, not a flag. Every applicable
    flag is collected, not just the first: a run missing its exit
    code and another field must name both, not hide the second
    behind the first.
    """
    flags = []
    exit_code = run.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        flags.append("invalid_exit_code")
    label = run.get("label")
    command_raw = run.get("command_raw")
    if "label" in run and not (isinstance(label, str) and label.strip()):
        flags.append("invalid_label")
    if "command_raw" in run and not (isinstance(command_raw, str) and command_raw.strip()):
        flags.append("invalid_command_raw")
    if not ((isinstance(label, str) and label.strip())
            or (isinstance(command_raw, str) and command_raw.strip())):
        flags.append("missing_evidence_id")
    tier = run.get("trust_tier")
    if ("trust_tier" in run and (not isinstance(tier, int)
                                 or isinstance(tier, bool)
                                 or tier < 1 or tier > 4)):
        flags.append("invalid_trust_tier")
    source = run.get("source")
    if not (isinstance(source, str) and source.strip()):
        flags.append("missing_source")
    if not isinstance(run.get("working_directory"), str):
        flags.append("missing_working_directory")
    digest = run.get("output_digest")
    if not (isinstance(digest, str) and digest.strip()):
        flags.append("missing_output_digest")
    end = run.get("end_timestamp")
    if end is not None and not isinstance(end, str):
        flags.append("missing_end_timestamp")
    return flags


def _base(check):
    lim = check.get("scope_limitation", _DEFAULT_SCOPE_LIMITATION)
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
        "scope_limitation": lim if isinstance(lim, str) else _DEFAULT_SCOPE_LIMITATION,
        "recommended_next_action": check.get("recommended_next_action", ""),
    }


def judge(check, runs, snapshot, final_edit_marker):
    _validate_check(check)
    _validate_judging_inputs(runs, snapshot)
    row = _base(check)
    if check.get("applicability") == "not_applicable":
        row["status"] = "NOT APPLICABLE"
        row["recommended_next_action"] = (
            check.get("not_applicable_reason", "Criterion does not apply to this change.")
        )
        return row

    ctype = check.get("check_type")
    if ctype == "inferred":
        # Wave 3: an inferred check is never a human check and
        # never a pass. It records that a command was observed,
        # and stays NOT OBSERVED, so a workflow with no human
        # checks can never pass by inference alone.
        row["status"] = "NOT OBSERVED"
        row["evidence_source"] = "inferred"
        row["trust_tier"] = None
        row["flags"].append("inferred_not_human")
        row["scope_limitation"] = (
            "INFERRED, not human acceptance: this row was generated "
            "from an observed command, not written by a human, and "
            "it is never VERIFIED and never presented as acceptance."
        )
        row["recommended_next_action"] = (
            "Supply 3 to 5 human-written checks, or a named human "
            "confirmation, if this behaviour is to be judged."
        )
        row["after_final_edit"] = None
        return row

    if ctype == "recorded_run":
        wanted = normalize_command(check["required_command"])
        candidates = [r for r in runs if r.get("command_normalized") == wanted]
        cited = [r for r in candidates if not is_superseded(r, final_edit_marker)]
        # A run with no parseable timestamp cannot be trusted as
        # after-final-edit evidence; treat it as not citable.
        cited = [r for r in cited if parse_time(r.get("start_timestamp")) is not None]
        if cited:
            run = max(cited, key=lambda r: parse_time(r.get("start_timestamp")))
            # Identity is selected type- and whitespace-aware: a
            # wrong-typed or blank label, command_raw, or trust tier
            # never lands verbatim in the row. A list label does
            # not become the evidence id, a dict command_raw does
            # not become the command, and a tier of 99 does not
            # become the trust tier; each falls back to None, and
            # the field flags below decide the verdict.
            label = run.get("label")
            command_raw = run.get("command_raw")
            row["evidence_id"] = (
                label if isinstance(label, str) and label.strip()
                else command_raw if isinstance(command_raw, str) and command_raw.strip()
                else None)
            row["evidence_source"] = run.get("source")
            tier = run.get("trust_tier")
            row["trust_tier"] = (
                tier if isinstance(tier, int) and not isinstance(tier, bool)
                and 1 <= tier <= 4 else None)
            row["command"] = (
                command_raw if isinstance(command_raw, str) and command_raw.strip()
                else None)
            row["working_directory"] = run.get("working_directory")
            # An int or float epoch start_timestamp is a
            # legitimate timestamp representation under the
            # tool's own contract (parse_time documents epoch
            # seconds, millis, micros, and nanos), so it is
            # accepted, but it is normalised to ISO in the row
            # rather than recorded verbatim as a bare number:
            # a bare epoch in a ledger row reads as an
            # unlabelled integer, while end_timestamp must be a
            # string or null. A string timestamp is recorded
            # verbatim, as before.
            _start = run.get("start_timestamp")
            if isinstance(_start, (int, float)) and not isinstance(_start, bool):
                _parsed = parse_time(_start)
                row["start_timestamp"] = (
                    _parsed.isoformat() if _parsed is not None else _start)
            else:
                row["start_timestamp"] = _start
            row["end_timestamp"] = run.get("end_timestamp")
            row["exit_code"] = run.get("exit_code")
            row["output_digest"] = run.get("output_digest")
            row["test_target"] = check.get("test_target")
            row["after_final_edit"] = True
            field_flags = _cited_run_field_flags(run)
            if run.get("exit_code") is None:
                # A missing exit code is reported as missing, not
                # invalid: the run is real, it simply has no exit
                # code to decide the check. Any other malformed
                # field is reported alongside it, never hidden
                # behind the missing exit code.
                field_flags = ["missing_exit_code"] + [
                    f for f in field_flags if f != "invalid_exit_code"]
            if field_flags:
                row["status"] = "NOT OBSERVED"
                row["flags"].extend(field_flags)
                if field_flags == ["missing_exit_code"]:
                    # Missing exit code alone: the cited run is
                    # real and its identity is intact; only the
                    # verdict is unknown, never a pass and never
                    # a failure. It cannot decide a check, so the
                    # check stays NOT OBSERVED.
                    row["recommended_next_action"] = (
                        "Re-record the run with an exit code; a run "
                        "without an exit code cannot decide a check."
                    )
                    return row
                # A cited run whose evidence is missing or
                # wrong-typed cannot decide a check: its verdict
                # would rest on an evidence id, source, digest, or
                # exit code that is not what it claims to be. The
                # evidence identity is reset so the row does not
                # present malformed evidence as its identity, and
                # every wrong-typed value is neutralised rather
                # than recorded as if it were real.
                row["evidence_id"] = None
                row["evidence_source"] = "none"
                row["trust_tier"] = None
                if "invalid_exit_code" in field_flags:
                    row["exit_code"] = None
                if ("missing_evidence_id" in field_flags
                        or "invalid_command_raw" in field_flags):
                    row["command"] = None
                if not isinstance(run.get("working_directory"), str):
                    row["working_directory"] = None
                if not (isinstance(run.get("output_digest"), str)
                        and run.get("output_digest").strip()):
                    row["output_digest"] = None
                end = run.get("end_timestamp")
                if end is not None and not isinstance(end, str):
                    row["end_timestamp"] = None
                row["recommended_next_action"] = (
                    "Re-record the run with complete evidence fields; "
                    "a run missing a field cannot decide a check."
                )
                return row
            if run.get("exit_code") == 0:
                row["status"] = "VERIFIED"
                # Digest check: observed state must match the expected
                # revision, or the VERIFIED cannot stand.
                art = check.get("artifact_path")
                exp = check.get("expected_digest")
                if (art and exp and isinstance(art, str)
                        and isinstance(exp, str) and snapshot.get(art) != exp):
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
            # Distinguish the two honest reasons for no cited
            # run: a parseable run before the marker is
            # superseded, a run with no parseable start is
            # not citable for a different reason. Labelling
            # the second case superseded_only was misleading.
            if any(parse_time(r.get("start_timestamp")) is not None
                   for r in candidates):
                row["flags"].append("superseded_only")
                row["recommended_next_action"] = (
                    "Re-run the prescribed command after the final edit and "
                    "record the new run; the superseded run is retained in "
                    "history and is never cited."
                )
            else:
                row["flags"].append("no_parseable_timestamp")
                row["recommended_next_action"] = (
                    "Re-record the run with a parseable start timestamp; "
                    "a run without one is retained but never cited."
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
        # _validate_check already refused a missing or non-string
        # artifact_path, and a non-string expected_digest, so the
        # lookup below cannot crash on an unhashable value.
        art = check.get("artifact_path")
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
        # _validate_check already refused a non-dict confirmation
        # and a non-string tester/procedure, but the VERIFIED
        # condition re-checks the shape so this branch is safe on
        # its own: a dict tester must never produce VERIFIED with
        # a dict repr in the evidence id.
        if (isinstance(rec, dict)
                and isinstance(rec.get("tester"), str) and rec["tester"].strip()
                and isinstance(rec.get("procedure"), str) and rec["procedure"].strip()
                and rec.get("result") in ("pass", "fail")):
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
