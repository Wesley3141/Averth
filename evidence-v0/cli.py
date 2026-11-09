#!/usr/bin/env python3
"""V0 evidence verifier CLI. Read-only by default, explicit trigger.

Usage (from this directory):
  python3 cli.py --repo <repo path> --checks <checks.json> --out <out dir>
                 [--runs <recorded-run ledger.json>] [--execute]
                 [--trace <events.jsonl>] [--final-edit-marker <ISO-8601>]
                 [--report-id <id>]

Safety:
- The target repo is never modified, except that the operator-chosen
  --out directory may live under it if the operator explicitly puts
  it there. No .claude/settings.json, git hook, CI, PR, or production
  service is ever touched.
- Only explicitly allowlisted commands are ever executed, and
  only with --execute. Without --allowlist, that means pytest
  only. With an operator-written --allowlist file, any command
  listed exactly, token for token, may run, any runner, with
  the destructive-command review warning in verifier.py.
  Without --execute, no command runs at all.
- Universal ingest (--ingest) never executes anything. It
  converts any supported input shape to ledger runs, counts
  unparseable records, and never invents a timestamp, an
  exit code, or a verdict.
- No network, no model calls, no credentials, no uploads. The default
  upload set is empty; this tool has no upload path.
- The repo path must be a real directory, and must not be the user's
  home directory or the filesystem root.
"""
import argparse
import hashlib
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_ledger import build_ledger, git_state, is_superseded, parse_time, snapshot_repo
from reporter import write_outputs
from requirement_spec import load_checks, verify_checks_unchanged
from trace_adapter import load_recorded_runs, load_trace_events
from universal_ingest import infer_checks_from_runs, ingest_file
from verifier import judge_all, run_allowlisted, run_via_allowlist


def _resolve(path):
    """Resolve a user-supplied path, falling back to the raw path.

    Path.resolve() raises RuntimeError on a symlink loop. A loop
    in --checks, --out, or --repo must refuse with exit 2, not a
    traceback, so resolution failure falls back to the unresolved
    path and the loaders refuse it (ELOOP) on the existing exit-2
    paths. A loop in --repo is caught by the is_dir check below
    (stat fails, so it is not a directory) and refused via
    ap.error, which exits 2.
    """
    try:
        return Path(path).resolve()
    except (RuntimeError, OSError):
        return Path(path)


def _remove_stale_outputs(out_dir, keep=()):
    """Best-effort removal of a previous run's outputs after a refusal.

    A refused run must not leave a pass-looking report behind in a
    reused --out dir, so a refusal removes the previous ledger and
    report. `keep` names outputs that must be left in place: a
    collision refusal keeps a colliding output file only when that
    file IS the frozen input, which the caller decides by digest
    (see _refuse_input_collision); at load time, before any digest
    exists, the colliding file is kept. A failure to remove is
    warned about on stderr: the refusal itself is what matters,
    and the operator sees the error on stderr. A removal failure
    does not change the exit code.
    """
    for name in ("evidence_ledger.json", "evidence_report.md"):
        if name in keep:
            continue
        try:
            (out_dir / name).unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"warning: could not remove stale output {out_dir / name}: {exc}",
                  file=sys.stderr)


def _input_collision(path, out_dir):
    """Return the output names an input path collides with, or [].

    A path names an output file when it resolves to the same
    path, or is the same file through a hardlink or symlink
    (samefile), where the output file exists.
    """
    resolved = _resolve(path)
    colliding = []
    for output_path in (out_dir / "evidence_ledger.json",
                        out_dir / "evidence_report.md"):
        if resolved == output_path:
            colliding.append(output_path.name)
            continue
        try:
            if os.path.samefile(resolved, output_path):
                colliding.append(output_path.name)
        except OSError:
            pass
    return colliding


def _output_matches_digest(path, expected_digest):
    """True only when the bytes read through path hash to expected_digest.

    A colliding entry is the frozen input only when its bytes are
    the frozen bytes: a link in the reversed direction (the checks
    path swapped to a link to a distinct stale output) reads
    different bytes and must not be kept, while the forward
    direction (an output entry planted as a link to the checks
    file) reads the frozen bytes and is kept. lstat first: a
    non-regular entry that is not a symlink is never kept and
    never read, so a FIFO cannot block the read. A symlink is
    followed with stat and kept only when its target is a regular
    file; a dangling link or a link loop never matches. The open
    uses O_NONBLOCK so a swap to a FIFO between the stat and the
    open still cannot block: the read then sees no bytes, the
    digest does not match, and the entry is removed.
    """
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        try:
            st = os.stat(path)
        except OSError:
            return False
    if not stat.S_ISREG(st.st_mode):
        return False
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return False
    try:
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            digest.update(chunk)
    except OSError:
        return False
    finally:
        os.close(fd)
    return "sha256:" + digest.hexdigest() == expected_digest


def _refuse_input_collision(path, label, out_dir, expected_digest=None):
    """Refuse when an input file names an output file.

    Returns True (already refused: an error line is printed and
    stale outputs are removed except a colliding file that IS the
    frozen input, which is left byte-identical) or False (no
    collision). `label` names the input in the error line, for
    example "checks file". When expected_digest is given (the
    load-time checks digest, at the post-load re-checks), a
    colliding entry is kept only when the bytes read through it
    hash to that digest: the forward direction (an output entry
    planted as a link to the checks file) reads the frozen bytes
    and is kept, while the reversed direction (the checks path
    swapped to a link to a distinct stale output) reads different
    bytes and is removed like any other stale output. A
    non-regular colliding entry is never kept. When no digest is
    given (the load-time check, before any digest exists), every
    colliding entry is kept, as before.
    """
    colliding = _input_collision(path, out_dir)
    if not colliding:
        return False
    print(f"error: cannot load {label} {path}: "
          f"the {label} must not be one of the output files", file=sys.stderr)
    if expected_digest is None:
        keep = tuple(colliding)
    else:
        keep = tuple(name for name in colliding
                     if _output_matches_digest(out_dir / name, expected_digest))
    _remove_stale_outputs(out_dir, keep=keep)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="V0 local evidence verifier")
    ap.add_argument("--repo", required=True, help="Target repo / fixture directory")
    ap.add_argument("--checks", help="Human-written acceptance-check JSON file; omit for observe-only mode, which never passes")
    ap.add_argument("--out", required=True, help="Output directory for ledger JSON + Markdown report")
    ap.add_argument("--runs", help="Recorded-run ledger JSON to import (Tier 1)")
    ap.add_argument("--ingest", action="append", default=[],
                    help="Universal ingest input file, any supported shape (repeatable); never executed, never a verdict by itself")
    ap.add_argument("--allowlist", help="Operator-written allowlist JSON for --execute; any listed command, any runner, exact match only")
    ap.add_argument("--infer-checks", action="store_true",
                    help="Generate INFERRED rows from observed runs; inferred rows are always NOT OBSERVED, never human acceptance")
    ap.add_argument("--execute", action="store_true",
                    help="Also execute checks in the repo and record them (Tier 2): pytest only without --allowlist, any exactly listed command with --allowlist")
    ap.add_argument("--trace", help="Optional JSONL trace file, summarised only, never judged")
    ap.add_argument("--final-edit-marker", help="ISO-8601 marker; runs before it are superseded")
    ap.add_argument("--report-id", default="v0-evidence-report")
    ap.add_argument("--python", default=sys.executable,
                    help="Interpreter for --execute runs (must have pytest; "
                         "system python3 on this machine does not)")
    args = ap.parse_args(argv)

    repo = _resolve(args.repo)
    home = Path.home().resolve()
    if not repo.is_dir() or repo == home or repo == Path("/"):
        ap.error("--repo must be a real directory, not home or filesystem root")
    out_dir = _resolve(args.out)
    # An input file that names one of the output files would let
    # the run overwrite its own input with ledger/report content
    # at rc 0. Refuse before loading anything, for every input
    # kind, not just --checks: --runs, --trace, --ingest, and
    # --allowlist are all inputs, and the allowlist case is the
    # worst, because the operator's security policy file would be
    # overwritten with a ledger while the run reports success.
    for label, path in (
            ("checks file", args.checks),
            ("recorded-runs file", args.runs),
            ("trace file", args.trace),
            ("allowlist file", args.allowlist),
            *[("ingest file", p) for p in args.ingest]):
        if path and _refuse_input_collision(path, label, out_dir):
            return 2
    runs = []
    ledger_marker = None
    ingest_summaries = []
    if args.runs:
        try:
            imported, ledger_marker = load_recorded_runs(args.runs)
        except (ValueError, OSError) as exc:
            print(f"error: cannot load recorded runs {args.runs}: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
        runs.extend(imported)
    for ingest_path in args.ingest:
        try:
            ingested, summary = ingest_file(ingest_path)
        except (ValueError, OSError) as exc:
            print(f"error: cannot load ingest file {ingest_path}: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
        if summary.get("formats") == ["unreadable"]:
            # The file could not be read at all (missing, FIFO,
            # non-UTF-8): refuse like the other loaders, instead
            # of silently completing with a clean-looking empty
            # report. Genuinely unparseable content (bad lines,
            # plain_log_unparseable) stays tolerant as before.
            print(f"error: cannot load ingest file {ingest_path}: "
                  f"{summary.get('error', 'unreadable')}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
        runs.extend(ingested)
        ingest_summaries.append(summary)
    if args.checks:
        try:
            spec = load_checks(args.checks)
        except (ValueError, OSError) as exc:
            print(f"error: cannot load checks file {args.checks}: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
    else:
        spec = {"task_intent": "observe only, no human checks supplied",
                "task_intent_source": "cli observe mode",
                "checks": []}
    if args.infer_checks:
        spec = dict(spec)
        spec["checks"] = list(spec["checks"]) + infer_checks_from_runs(runs)
    try:
        snapshot, latest_mtime = snapshot_repo(repo)
    except (ValueError, OSError) as exc:
        # An unreadable file in the target repo (for example a
        # symlink to a device that fails to read) used to escape
        # with an uncaught traceback and exit 1. Refuse like
        # every other loader, with stale removal.
        print(f"error: cannot snapshot repo {repo}: {exc}", file=sys.stderr)
        _remove_stale_outputs(_resolve(args.out))
        return 2
    commit, dirty, commit_note = git_state(repo)

    if args.final_edit_marker:
        marker = parse_time(args.final_edit_marker)
    elif ledger_marker:
        marker = parse_time(ledger_marker)
    else:
        marker = latest_mtime

    allowlist = None
    if args.allowlist:
        from runner_allowlist import load_allowlist
        try:
            allowlist = load_allowlist(args.allowlist)
        except (ValueError, OSError) as exc:
            print(f"error: cannot load allowlist {args.allowlist}: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
    if args.execute:
        for check in spec["checks"]:
            if check.get("check_type") == "recorded_run" and check.get("applicability", "applies") == "applies":
                try:
                    if allowlist is not None:
                        runs.append(run_via_allowlist(check["required_command"], repo, allowlist))
                    else:
                        runs.append(run_allowlisted(check["required_command"], repo,
                                                    interpreter=args.python))
                except ValueError as exc:
                    # Refusal is a feature, not a crash: a command that
                    # is not allowlisted is simply not run, and its
                    # check stays NOT OBSERVED in the report.
                    print(f"skipped (not allowlisted, not run): {exc}")
                except OSError as exc:
                    # A launch failure (missing interpreter or runner
                    # binary) is a refusal, not a crash: no ledger or
                    # report is written, and stale outputs are removed
                    # rather than left pass-looking. (A timeout is
                    # not a launch failure: both runners record it
                    # honestly as exit 124, so it never reaches here.)
                    print(f"error: cannot execute {check['required_command']}: {exc}",
                          file=sys.stderr)
                    _remove_stale_outputs(_resolve(args.out))
                    return 2

    for r in runs:
        r["superseded"] = is_superseded(r, marker)

    judgments = judge_all(spec["checks"], runs, snapshot, marker)
    if args.trace:
        try:
            trace_summary = load_trace_events(args.trace)
        except (ValueError, OSError) as exc:
            print(f"error: cannot load trace file {args.trace}: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
    else:
        trace_summary = None
    if args.checks:
        # The checks file is frozen at load. Re-hash before the
        # ledger is built and written: a net change between load and
        # the re-hash (a single comparison: an edit reverted
        # byte-for-byte before the re-hash escapes detection, as
        # does any edit made after the re-hash) means the judgments
        # no longer describe the frozen check set, so refuse to
        # write output at all. A checks file that cannot be re-read
        # at this point (deleted, replaced by a directory, replaced
        # by a non-regular file, unreadable) refuses the same way.
        try:
            verify_checks_unchanged(args.checks, spec["checks_digest"])
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            _remove_stale_outputs(_resolve(args.out))
            return 2
        # The re-hash passes on byte-identical content, so a
        # checks path swapped after load to a symlink (or
        # hardlink) to an output file, with the output pre-seeded
        # with the identical bytes, would pass the re-hash and
        # then be destroyed by the write. Re-run the collision
        # check before anything is written, with the same
        # semantics as the load-time check, except the keep is
        # digest-gated: only an entry whose bytes hash to the
        # load-time digest is the frozen input and is kept.
        if _refuse_input_collision(args.checks, "checks file", out_dir,
                                   expected_digest=spec["checks_digest"]):
            return 2
    ledger = build_ledger(
        report_id=args.report_id, repo_path=repo, checks_spec=spec,
        judgments=judgments, runs=runs, snapshot=snapshot, commit=commit,
        workspace_dirty=dirty, commit_note=commit_note,
        final_edit_marker=marker, trace_summary=trace_summary,
    )
    if ingest_summaries:
        ledger["ingest_summary"] = ingest_summaries
    if args.checks:
        # The checks path can be swapped to an output file after
        # the post-verify collision check, during build_ledger, so
        # check again immediately before anything is written.
        # The keep is digest-gated, as at the post-verify check:
        # only an entry whose bytes hash to the load-time digest
        # is the frozen input and is kept.
        if _refuse_input_collision(args.checks, "checks file", out_dir,
                                   expected_digest=spec["checks_digest"]):
            return 2
    try:
        json_path, md_path = write_outputs(ledger, _resolve(args.out))
    except (RecursionError, OSError) as exc:
        # Belt and braces behind the load_checks depth bound: a
        # deeply nested record from another loader can still make
        # the ledger unserialisable. A stale output path can also
        # fail to write (for example a directory left in place of
        # the ledger). Refuse with exit 2 and remove any stale
        # outputs rather than leaving a traceback.
        if isinstance(exc, RecursionError):
            detail = f"output is nested too deeply to write: {exc}"
        else:
            detail = f"could not write output: {exc}"
        print(f"error: {detail}", file=sys.stderr)
        _remove_stale_outputs(_resolve(args.out))
        return 2
    if args.checks and _input_collision(args.checks, out_dir):
        # The checks path was swapped to an output file during the
        # writes themselves. Post-write the colliding file is a
        # newly written ledger or report, not the frozen input, so
        # it must not be kept: remove both outputs and refuse.
        # Unlinking both entries also leaves the planted checks
        # link dangling instead of reading ledger content.
        print(f"error: cannot load checks file {args.checks}: "
              "the checks file must not be one of the output files",
              file=sys.stderr)
        _remove_stale_outputs(out_dir)
        return 2
    cov = ledger["coverage"]
    print(f"ledger: {json_path}")
    print(f"report: {md_path}")
    print(f"checks digest: {ledger['checks_digest'] or 'none (observe-only mode)'}")
    print(f"counts: {cov['counts']}")
    print(f"unknown rate: {cov['unknown_rate']}")
    print(f"runs: {cov['runs_total']} ({cov['superseded_runs_retained']} superseded, retained, never cited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
