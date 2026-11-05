#!/usr/bin/env python3
"""Adapter 1: generic recorded-run converter (wave 1).

Convert a raw harness, CI, or log record into the V0 recorded-run
ledger JSON shape that cli.py --runs accepts. This script never
executes anything. A command string in the input is data only: it is
copied into the output ledger, never passed to a shell, never run,
never imported. If a transcript contains a destructive command, the
converter records the text and does nothing with it. That property
is tested, not just documented.

Input format A: structured JSON.
  A JSON object with a "runs" list, or a bare JSON list of run
  objects. Each run object may carry: label, command (required),
  working_directory, start_timestamp, end_timestamp (ISO 8601,
  or null), exit_code (integer, required), stdout, stderr, and
  output_digest. If output_digest is absent, it is computed as
  sha256 of stdout plus stderr. Runs with an unparseable timestamp
  are kept, with a warning on stderr, because V0 itself will treat
  a run with no parseable start timestamp as not citable. That
  behaviour is honest, not a silent pass.

Input format B: delimited log text.
  Records are separated by blank lines. Each record is a set of
  "key: value" lines, one per line, with these keys: label,
  command, working_directory, start_timestamp, end_timestamp,
  exit_code, stdout, stderr. The stdout and stderr values are
  literal text on their lines, not commands to run. A record
  without command or without exit_code is rejected with an error
  naming the record number. No other parsing is attempted: this
  converter does not guess a command from free prose, and it does
  not split a shell pipeline into runs.

Output format: a JSON object with "final_edit_marker" (from
--final-edit-marker, or null) and a "runs" list in exactly the
shape load_recorded_runs accepts: label, command,
working_directory, start_timestamp, end_timestamp, exit_code,
stdout, stderr, output_digest.

Usage:
  python3 recorded_run_converter.py --input runs.json --out ledger.json
  python3 recorded_run_converter.py --input runs.log --format log \
      --out ledger.json --final-edit-marker 2026-11-04T12:00:00Z

Limits, stated plainly: a converted run is Tier 1 evidence, the
same as any imported run. Conversion does not make a log
trustworthy, does not prove the command ran where claimed, and
does not prove correctness. A run with no timestamp, or with a
timestamp before the final edit marker, will not be cited by V0.
If the source log itself is incomplete, the honest V0 output is
a high unknown rate, not a pass.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def _digest(stdout, stderr):
    return "sha256:" + hashlib.sha256(((stdout or "") + (stderr or "")).encode()).hexdigest()


def _validate_run(raw, where):
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: run must be an object")
    command = raw.get("command")
    if not command or not isinstance(command, str):
        raise ValueError(f"{where}: run needs a non-empty string command")
    exit_code = raw.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise ValueError(f"{where}: run needs an integer exit_code")
    return {
        "label": raw.get("label", ""),
        "command": command,
        "working_directory": raw.get("working_directory", ""),
        "start_timestamp": raw.get("start_timestamp"),
        "end_timestamp": raw.get("end_timestamp"),
        "exit_code": exit_code,
        "stdout": raw.get("stdout", ""),
        "stderr": raw.get("stderr", ""),
        "output_digest": raw.get("output_digest") or _digest(raw.get("stdout", ""), raw.get("stderr", "")),
    }


def convert_json_text(text):
    data = json.loads(text)
    if isinstance(data, dict):
        raw_runs = data.get("runs")
        if raw_runs is None:
            raise ValueError('JSON input needs a "runs" list')
    elif isinstance(data, list):
        raw_runs = data
    else:
        raise ValueError("JSON input must be an object with runs, or a list of runs")
    runs = []
    for i, raw in enumerate(raw_runs, start=1):
        runs.append(_validate_run(raw, f"run {i}"))
    return runs


def convert_log_text(text):
    runs = []
    blocks = [b for b in text.split("\n\n") if b.strip()]
    for i, block in enumerate(blocks, start=1):
        raw = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            raw[key.strip()] = value.strip()
        if "exit_code" in raw:
            try:
                raw["exit_code"] = int(raw["exit_code"])
            except ValueError:
                raise ValueError(f"record {i}: exit_code must be an integer")
        runs.append(_validate_run(raw, f"record {i}"))
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert raw run records to a V0 ledger")
    ap.add_argument("--input", required=True, help="Input JSON or log file")
    ap.add_argument("--out", required=True, help="Output ledger JSON file")
    ap.add_argument("--format", choices=["auto", "json", "log"], default="auto")
    ap.add_argument("--final-edit-marker", default=None)
    args = ap.parse_args(argv)
    text = Path(args.input).read_text()
    fmt = args.format
    if fmt == "auto":
        fmt = "json" if args.input.endswith(".json") else "log"
    if fmt == "json":
        runs = convert_json_text(text)
    else:
        runs = convert_log_text(text)
    for r in runs:
        if not r["start_timestamp"]:
            print(f"warning: run {r['label'] or r['command']!r} has no start timestamp; V0 will not cite it", file=sys.stderr)
    out = {"final_edit_marker": args.final_edit_marker, "runs": runs}
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"converted {len(runs)} runs to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
