#!/usr/bin/env python3
"""Run one operator-approved allowlist command and record it.

This script is the only execution path for adapter 3. It runs
at most one command, only if that command appears exactly in
the allowlist file, and only if the operator passes
--i-approved-this-allowlist. Without that flag it prints the
command it would run and exits without running anything.

Usage:
  python3 allowlist_runner.py --repo <dir> --allowlist allowlist.json \
      --command "npm test" --out run.json --i-approved-this-allowlist

Output is one ledger-shaped run record, suitable for merging
into a recorded-run ledger that cli.py --runs accepts. It is
Tier 2, this tool's local observation, not Tier 3 attestation.
"""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_ledger import sha256_text
from runner_allowlist import load_allowlist, validate_command
from trace_adapter import normalize_command


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run one allowlisted command and record it")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--allowlist", required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--i-approved-this-allowlist", action="store_true")
    args = ap.parse_args(argv)
    allowlist = load_allowlist(args.allowlist)
    entry = validate_command(args.command, allowlist)
    if entry is None:
        print(f"refused: command is not in the allowlist, not run: {args.command!r}")
        return 2
    if not args.i_approved_this_allowlist:
        print(f"would run (not run, no confirmation flag): {args.command!r}")
        return 0
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        ap.error("--repo must be a real directory")
    import shlex

    argv_list = shlex.split(args.command)
    start = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(argv_list, cwd=str(repo), capture_output=True,
                              text=True, timeout=allowlist.get("timeout_seconds", 300))
        output, exit_code = proc.stdout + proc.stderr, proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        exit_code, stdout, stderr = 124, exc.stdout or "", exc.stderr or ""
    end = datetime.now(timezone.utc)
    record = {
        "label": entry.get("label", args.command),
        "command_raw": args.command,
        "command_normalized": normalize_command(args.command),
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
    import json

    Path(args.out).write_text(json.dumps(record, indent=2) + "\n")
    print(f"recorded: {args.out} exit={exit_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
