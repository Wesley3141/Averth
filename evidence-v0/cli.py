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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_ledger import build_ledger, git_state, is_superseded, parse_time, snapshot_repo
from reporter import write_outputs
from requirement_spec import load_checks
from trace_adapter import load_recorded_runs, load_trace_events
from universal_ingest import infer_checks_from_runs, ingest_file
from verifier import judge_all, run_allowlisted, run_via_allowlist


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

    repo = Path(args.repo).resolve()
    home = Path.home().resolve()
    if not repo.is_dir() or repo == home or repo == Path("/"):
        ap.error("--repo must be a real directory, not home or filesystem root")
    runs = []
    ledger_marker = None
    ingest_summaries = []
    if args.runs:
        imported, ledger_marker = load_recorded_runs(args.runs)
        runs.extend(imported)
    for ingest_path in args.ingest:
        ingested, summary = ingest_file(ingest_path)
        runs.extend(ingested)
        ingest_summaries.append(summary)
    if args.checks:
        spec = load_checks(args.checks)
    else:
        spec = {"task_intent": "observe only, no human checks supplied",
                "task_intent_source": "cli observe mode",
                "checks": []}
    if args.infer_checks:
        spec = dict(spec)
        spec["checks"] = list(spec["checks"]) + infer_checks_from_runs(runs)
    snapshot, latest_mtime = snapshot_repo(repo)
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
        allowlist = load_allowlist(args.allowlist)
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

    for r in runs:
        r["superseded"] = is_superseded(r, marker)

    judgments = judge_all(spec["checks"], runs, snapshot, marker)
    trace_summary = load_trace_events(args.trace) if args.trace else None
    ledger = build_ledger(
        report_id=args.report_id, repo_path=repo, checks_spec=spec,
        judgments=judgments, runs=runs, snapshot=snapshot, commit=commit,
        workspace_dirty=dirty, commit_note=commit_note,
        final_edit_marker=marker, trace_summary=trace_summary,
    )
    if ingest_summaries:
        ledger["ingest_summary"] = ingest_summaries
    json_path, md_path = write_outputs(ledger, Path(args.out).resolve())
    cov = ledger["coverage"]
    print(f"ledger: {json_path}")
    print(f"report: {md_path}")
    print(f"counts: {cov['counts']}")
    print(f"unknown rate: {cov['unknown_rate']}")
    print(f"runs: {cov['runs_total']} ({cov['superseded_runs_retained']} superseded, retained, never cited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
