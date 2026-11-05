#!/usr/bin/env python3
"""Adapter 3: explicit per-workflow executed-mode runner allowlist.

This is a separate path from cli.py --execute, which stays
pytest-only. Nothing here runs automatically, nothing here reads
a command from a transcript, a README, a PR, or an issue. The
operator writes an allowlist file for one workflow, names the
approver and the date, lists the exact commands that may run,
and only then runs allowlist_runner.py with an explicit
confirmation flag. A command that is not listed, exactly, is
refused. There is no wildcard, no pattern, no "any npm command".

Allowlist file format (JSON):
  {
    "workflow": "example-app npm tests",
    "approved_by": "operator name",
    "approved_date": "2026-11-04",
    "runner": "npm",
    "allowed_flags": ["test"],
    "allowed_relative_paths": [],
    "timeout_seconds": 300,
    "sandbox": "run only in the repo checkout, no network assumed, operator watches output",
    "commands": [
      {"label": "npm tests", "command": "npm test"},
      {"label": "npm lint", "command": "npm run lint"}
    ]
  }

Quoting note: listed commands are split with shlex, so a
quoted argument loses its quotes. Prefer script files over
-c code in an allowlist, or the code will change on split.

Validation rules, all required for a command to pass:
  - One allowlist file has one runner field, so one file
    cannot list both sh and npm commands. Use a separate
    allowlist file per runner. A command whose first token
    is not that file's runner is refused, which fails closed.
  - The command, split on whitespace, must equal one listed
    command, token for token. No extra flags, no extra paths.
    Exact match is the gate: there is no pattern, no wildcard,
    and no partial match, so a shell string, a pipeline, a
    redirection, an absolute path, or a ".." path cannot sneak
    in unless the operator listed that exact string verbatim,
    in which case the operator approved it knowingly.
  - The first token must equal the allowlist runner.
  - timeout_seconds, if present, must be a positive integer.

Execution, in allowlist_runner.py only: subprocess without a
shell, cwd set to the repo directory, output captured, timeout
applied, and the result written as one ledger-shaped run record
(label, command_raw, command_normalized, working_directory,
start_timestamp, end_timestamp, exit_code, output_digest,
stdout, stderr, source "allowlist_recorder", trust_tier 2).
Trust tier 2 means this tool observed the run locally. It is
not tamper-proof provenance, and it is not a Tier 3 CI
attestation.

Limits: an allowlist does not make a command safe in general.
It makes a named, operator-approved command runnable in a named
repo checkout. If the listed command itself deletes files, the
allowlist will run it, because the operator approved that exact
command. Review the listed commands before approving them, and
never approve a list copied from an untrusted source.
"""
import json
import shlex
from pathlib import Path

def load_allowlist(path):
    data = json.loads(Path(path).read_text())
    for key in ("workflow", "approved_by", "runner", "commands"):
        if key not in data:
            raise ValueError(f"allowlist is missing required key: {key}")
    if not isinstance(data["commands"], list) or not data["commands"]:
        raise ValueError("allowlist commands must be a non-empty list")
    timeout = data.get("timeout_seconds", 300)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    return data


def validate_command(command, allowlist):
    """Return the listed command dict if allowed, else None.

    Exact token match only. A command that is not listed,
    exactly, is refused, including any shell pipeline, redirect,
    absolute path, or parent path that is not in the list.
    """
    try:
        parts = shlex.split(str(command))
    except ValueError:
        return None
    if not parts or parts[0] != allowlist["runner"]:
        return None
    for entry in allowlist["commands"]:
        try:
            listed = shlex.split(entry["command"])
        except ValueError:
            continue
        if listed == parts:
            return entry
    return None
