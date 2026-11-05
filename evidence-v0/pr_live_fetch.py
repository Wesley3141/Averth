#!/usr/bin/env python3
"""Wave 2: live PR evidence fetch, credential-free, NOT live-verified.

This module extends the fixture-based pr_evidence_converter
toward a live fetch, using only public data and no
credentials, no GitHub token, no login. It calls the public
GitHub REST API with urllib, unauthenticated, which is rate
limited for unauthenticated callers and may return 403 or
404 for a private repo, a deleted repo, or a rate limit.
Those failures are returned as errors, never as evidence.

What it fetches, for one public pull request:
  - The pull request itself: number, title, state, head
    commit SHA, files changed list.
  - The files list: filenames and patch text where the API
    returns it. Patch text is a claim about a diff, not a
    run record, and stays Tier 0 unless a CI run record
    backs it.
  - Reviews and issue comments: author, body, and any
    claims listed in them. Claims are Tier 0, exactly as
    in the fixture converter, unless a CI check run with
    the exact same command string is also present.
  - Check runs for the head commit: name, status,
    conclusion, started_at, completed_at. A check run
    becomes a ledger run with label set to the check name
    and command set to "ci-check: <name>". That command
    string is a ledger label, not a shell command, and it
    will only be cited by a V0 check that names exactly
    that string. A check run with conclusion success maps
    to exit 0, failure or cancelled maps to exit 1, and
    any other conclusion maps to exit 1 with a note in
    stdout, because an unfinished or skipped check is not
    a pass. A check run with no completed_at is kept with
    no end timestamp, and V0 will treat a missing start
    timestamp as not citable.

Status, stated plainly, and this is the binding label for
any use of this module in wave 2: NOT live-verified. The
code is implemented, and its conversion logic is tested
with mocked API responses, but no live GitHub API run was
verified with the tools available to this wave. Do not
cite any output of this module as live-verified, do not
cite it as a merge certifier, and do not claim a real PR
was fetched until a real fetch is run and its output is
recorded with the PR number, repo, and fetch time. The
fixture converter remains the verified path in this wave.

Usage:
  python3 pr_live_fetch.py --repo owner/repo --pr 123 \
      --ledger-out ledger.json --claims-out claims.json
  python3 pr_live_fetch.py --repo owner/repo --pr 123 \
      --ledger-out ledger.json --claims-out claims.json \
      --final-edit-marker 2026-11-04T12:00:00Z

No token is read from the environment, no credential file
is read, and no token argument exists. If the operator
wants authenticated rate limits, that is a separate,
explicitly authorised change, not a silent fallback.
"""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.github.com"
USER_AGENT = "averth-evidence-v0-live-fetch (public, unauthenticated)"


def _get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GitHub API request failed for {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"GitHub API request failed for {url}: {exc}") from exc


def fetch_pr_data(repo, pr_number, getter=None):
    """Fetch PR, files, reviews, comments, and check runs.

    getter, when given, is a test double taking a URL and
    returning parsed JSON. In production use it is None and
    _get is used. Returns a dict with pr, files, reviews,
    comments, and check_runs keys.
    """
    get = getter or _get
    pr = get(f"{API_BASE}/repos/{repo}/pulls/{pr_number}")
    files = get(f"{API_BASE}/repos/{repo}/pulls/{pr_number}/files?per_page=100")
    reviews = get(f"{API_BASE}/repos/{repo}/pulls/{pr_number}/reviews?per_page=100")
    comments = get(f"{API_BASE}/repos/{repo}/issues/{pr_number}/comments?per_page=100")
    head_sha = pr.get("head", {}).get("sha", "")
    check_runs = []
    if head_sha:
        checks = get(f"{API_BASE}/repos/{repo}/commits/{head_sha}/check-runs?per_page=100")
        check_runs = checks.get("check_runs", []) if isinstance(checks, dict) else []
    return {
        "pr": pr,
        "files": files if isinstance(files, list) else [],
        "reviews": reviews if isinstance(reviews, list) else [],
        "comments": comments if isinstance(comments, list) else [],
        "check_runs": check_runs,
    }


def convert_live(data, repo, pr_number):
    """Convert fetched PR data to ledger runs plus Tier 0 claims.

    CI check runs become Tier 1 ledger runs, exactly like
    fixture CI runs. Every other claim, including patch
    text, review bodies, and comment bodies, stays Tier 0.
    A review or comment body is listed as one Tier 0 claim
    per body, not split into sentences, because splitting
    would invent claim boundaries.
    """
    runs = []
    for check in data.get("check_runs", []):
        conclusion = check.get("conclusion")
        exit_code = 0 if conclusion == "success" else 1
        note = ""
        if conclusion not in ("success", "failure", "cancelled"):
            note = f"check conclusion was {conclusion!r}, not success, so this run is recorded as exit 1, not a pass"
        runs.append({
            "label": check.get("name", ""),
            "command": f"ci-check: {check.get('name', '')}",
            "working_directory": "",
            "start_timestamp": check.get("started_at"),
            "end_timestamp": check.get("completed_at"),
            "exit_code": exit_code,
            "stdout": note,
            "stderr": "",
            "output_digest": None,
        })
    tier0 = []
    for f in data.get("files", []):
        if f.get("patch"):
            tier0.append({
                "author": "",
                "claim": f"diff for {f.get('filename', '')} (patch text, not a run record)",
                "tier": 0,
                "note": "Patch text is a claim about a diff, not evidence a check ran.",
            })
    for item in list(data.get("reviews", [])) + list(data.get("comments", [])):
        body = item.get("body", "") or ""
        author = ""
        user = item.get("user") or {}
        if isinstance(user, dict):
            author = user.get("login", "")
        if body.strip():
            tier0.append({
                "author": author,
                "claim": body,
                "tier": 0,
                "note": "Review or comment body, no CI run record supplied for it. Not evidence.",
            })
    claims = {
        "pr_number": pr_number,
        "repo": repo,
        "files_changed": [f.get("filename", "") for f in data.get("files", [])],
        "tier0_claims": tier0,
        "note": "Live fetch path, NOT live-verified in wave 2. No GitHub API run was verified with the tools available to this wave. Do not cite as live-verified or as a merge certifier.",
        "live_fetch_status": "not_live_verified",
    }
    return runs, claims


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch a public PR and convert it to a V0 ledger plus Tier 0 claims")
    ap.add_argument("--repo", required=True, help="owner/repo, public only")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--ledger-out", required=True)
    ap.add_argument("--claims-out", required=True)
    ap.add_argument("--final-edit-marker", default=None)
    args = ap.parse_args(argv)
    data = fetch_pr_data(args.repo, args.pr)
    runs, claims = convert_live(data, args.repo, args.pr)
    # Fill output digests the way recorded_run_converter does.
    import hashlib
    for r in runs:
        if not r.get("output_digest"):
            r["output_digest"] = "sha256:" + hashlib.sha256(((r.get("stdout") or "") + (r.get("stderr") or "")).encode()).hexdigest()
    Path(args.ledger_out).write_text(json.dumps({"final_edit_marker": args.final_edit_marker, "runs": runs}, indent=2) + "\n")
    Path(args.claims_out).write_text(json.dumps(claims, indent=2) + "\n")
    print(f"fetched PR {args.pr} in {args.repo}: {len(runs)} check runs, {len(claims['tier0_claims'])} Tier 0 claims")
    print("WARNING: live fetch path is NOT live-verified in wave 2. Do not cite as live-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
