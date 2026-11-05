#!/usr/bin/env python3
"""Adapter 7: PR and review evidence converter, fixture-based.

This wave is fixture-based, not live-verified. It makes no
network call, reads no GitHub API, and fetches no live PR. It
converts a fixture JSON file into two outputs, and it keeps
the two kinds of material strictly separate:

  - Ledger runs: runs recorded in a CI log, in recorded-run
    shape (label, command, start and end timestamps, exit
    code, stdout, stderr). These become Tier 1 ledger runs,
    exactly like any imported run. A CI run with no parseable
    start timestamp is kept, and V0 will not cite it.
  - Tier 0 claims: anything claimed in a PR body, a diff
    summary, or a review comment that is not backed by a CI
    run record. These are listed, with author and text, and
    are never turned into ledger runs. A claim in a comment
    is not evidence, however specific it sounds.

Input fixture format (JSON):
  {
    "pr_number": 123,
    "repo": "owner/repo",
    "files_changed": ["src/a.py"],
    "ci_runs": [ {label, command, start_timestamp,
                  end_timestamp, exit_code, stdout, stderr} ],
    "review_comments": [ {author, body, claims: [strings]} ]
  }

Output: a ledger JSON object (final_edit_marker from
--final-edit-marker, or null, plus a runs list) and a claims
JSON object (pr_number, repo, files_changed, tier0_claims).
A claim that names a command is still Tier 0 unless a CI run
with that exact command, a parseable timestamp, and exit code
is also present in ci_runs. Matching is by exact command
string, not by keyword.

Usage:
  python3 pr_evidence_converter.py --input pr-fixture.json \
      --ledger-out ledger.json --claims-out claims.json

Live version, not implemented in this wave: fetch the full
diff, the CI check runs, and the review thread through the
GitHub API with the operator's permission, convert each CI
check run to the same ledger shape, and list every other
claim as Tier 0. Until that version exists and is tested
against a real PR, every report from this converter must say
fixture-based, not live-verified, and must not be cited as a
merge certifier. V0 fits PR triage only, never a merge
decision on its own.
"""
import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recorded_run_converter import _validate_run


def convert(fixture):
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a JSON object")
    ci_runs = fixture.get("ci_runs", [])
    runs = [_validate_run(r, f"ci run {i}") for i, r in enumerate(ci_runs, start=1)]
    known_commands = {r["command"] for r in runs}
    tier0 = []
    for comment in fixture.get("review_comments", []):
        for claim in comment.get("claims", []):
            if claim in known_commands:
                continue
            tier0.append({
                "author": comment.get("author", ""),
                "claim": claim,
                "tier": 0,
                "note": "Body or comment claim, no CI run record supplied for it. Not evidence.",
            })
    claims = {
        "pr_number": fixture.get("pr_number"),
        "repo": fixture.get("repo", ""),
        "files_changed": fixture.get("files_changed", []),
        "tier0_claims": tier0,
        "note": "Fixture-based, not live-verified. No GitHub API call was made.",
    }
    return runs, claims


def main(argv=None):
    ap = argparse.ArgumentParser(description="Convert a PR fixture to a V0 ledger plus Tier 0 claims")
    ap.add_argument("--input", required=True)
    ap.add_argument("--ledger-out", required=True)
    ap.add_argument("--claims-out", required=True)
    ap.add_argument("--final-edit-marker", default=None)
    args = ap.parse_args(argv)
    fixture = json.loads(Path(args.input).read_text())
    runs, claims = convert(fixture)
    Path(args.ledger_out).write_text(json.dumps({"final_edit_marker": args.final_edit_marker, "runs": runs}, indent=2) + "\n")
    Path(args.claims_out).write_text(json.dumps(claims, indent=2) + "\n")
    print(f"converted {len(runs)} CI runs and {len(claims['tier0_claims'])} Tier 0 claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
