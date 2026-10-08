"""Fetch the pinned support-ticket battery.

Source (per SOURCE_RESEARCH.md): GitHub issues on microsoft/vscode labeled
*question, state closed. 6,731 closed at research time.

Label mapping (documented heuristic, deterministic; raw signals preserved
per task for audit):
  state_reason == "duplicate"   -> DUPLICATE
  state_reason == "not_planned" -> WONTFIX
  state_reason == "completed":
      "bug" in labels (any label containing 'bug') -> BUG_FIX
      config keywords in title/body                  -> CONFIG
      escalation labels present                      -> ESCALATED
      otherwise                                      -> HOWTO

reopened = any issue event == "reopened" (the customer-side counter-signal:
reopen after close ~= acceptance failed).
sla_breach (v1 proxy): time_to_close_hours > 72. Illustrative; the partner's
real SLA replaces it.

Usage:
  GITHUB_TOKEN=... python fetch_tasks.py --n 600 [--repo microsoft/vscode]
                                        [--out tasks.json]
  Token optional but strongly recommended: unauthenticated = 60 req/hr
  (a 600-issue pull takes ~10h); authenticated = 5,000/hr (~10 min).
  Responses are cached in .fetch_cache/ so re-runs resume.

Output: {"dev": [...], "heldout": [...], "meta": {...}} pinned to --out.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

API = "https://api.github.com"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     ".fetch_cache")

CONFIG_KEYWORDS = re.compile(
    r"settings\.json|launch\.json|tasks\.json|\benv\b|environment variable"
    r"|config|configuration|install|path|proxy|certificate|permission denied",
    re.I)
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
ESCALATION_LABELS = {"triage", "needs more info", "under discussion",
                     "feature-request"}


def _req(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "averth-benchmark/0.1"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r), dict(r.headers)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            reset = e.headers.get("X-RateLimit-Reset")
            wait = max(int(reset) - int(time.time()) + 5, 5) if reset else 300
            print(f"  rate limited; sleeping {wait}s", flush=True)
            time.sleep(wait)
            return _req(url, token)
        raise


def _cached(key, url, token):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^a-zA-Z0-9_-]", "_", key) + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    data, _ = _req(url, token)
    with open(path, "w") as f:
        json.dump(data, f)
    return data


def assign_label(issue):
    sr = issue.get("state_reason") or ""
    if sr == "duplicate":
        return "DUPLICATE"
    if sr == "not_planned":
        return "WONTFIX"
    labels = {(l.get("name") or "").lower() for l in issue.get("labels", [])}
    if any(re.search(r"\bbug\b", l) for l in labels):
        return "BUG_FIX"
    if labels & ESCALATION_LABELS:
        return "ESCALATED"
    text = (issue.get("title") or "") + "\n" + (issue.get("body") or "")
    if CONFIG_KEYWORDS.search(text):
        return "CONFIG"
    return "HOWTO"


def scrub(text):
    return EMAIL_RE.sub("[redacted]", text or "")


def to_task(repo, issue, events):
    from datetime import datetime
    created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
    hours = (closed - created).total_seconds() / 3600
    return {
        "id": f"{repo}#{issue['number']}",
        "title": scrub(issue.get("title") or ""),
        "body": scrub((issue.get("body") or ""))[:6000],
        "resolution_label": assign_label(issue),
        "resolution_summary": f"state_reason={issue.get('state_reason')}",
        "reopened": any(e.get("event") == "reopened" for e in events),
        "time_to_close_hours": round(hours, 1),
        "sla_breach": hours > 72,
        # raw signals preserved for audit
        "_raw": {"state_reason": issue.get("state_reason"),
                 "labels": [l.get("name") for l in issue.get("labels", [])],
                 "comments": issue.get("comments"),
                 "closed_at": issue.get("closed_at")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="microsoft/vscode")
    ap.add_argument("--label", default="*question")
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--sort", default="created",
                    choices=["created", "updated", "comments"],
                    help="issues list sort; 'comments' surfaces high-engagement "
                         "tickets, which reopen more often (top-up runs)")
    ap.add_argument("--dev-fraction", type=float, default=0.6)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "tasks.json"))
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    from urllib.parse import quote
    # Total count via the search API (list endpoint doesn't return totals).
    search_url = (f"{API}/search/issues?q=repo:{args.repo}+label:"
                  f"{quote(args.label, safe='')}+state:closed&per_page=1")
    total = _req(search_url, token)[0]["total_count"]
    pages = max((total + 99) // 100, 1)
    print(f"  {total} closed issues, {pages} pages", flush=True)
    # Random pages: page 1 is recency-biased (bulk not_planned triage), so
    # sequential enumeration would skew the battery.
    import random as _random
    prng = _random.Random(20261007)
    if args.sort == "comments":
        # top-up mode: take the highest-engagement pages sequentially
        page_order = list(range(1, (args.n + 99) // 100 + 2))
    else:
        page_order = prng.sample(range(1, pages + 1),
                                 min(pages, (args.n + 99) // 100 + 2))
    issues = []
    print(f"enumerating closed '{args.label}' issues on {args.repo} ...",
          flush=True)
    for page in page_order:
        url = (f"{API}/repos/{args.repo}/issues?labels={quote(args.label)}"
               f"&state=closed&per_page=100&page={page}&sort={args.sort}"
               f"&direction=desc")
        batch, _ = _req(url, token)
        for it in batch:
            if "pull_request" in it:  # drop PRs
                continue
            if len((it.get("body") or "")) < 50:
                continue
            issues.append(it)
            if len(issues) >= args.n:
                break
        print(f"  page {page}: {len(issues)} collected", flush=True)
        if len(issues) >= args.n:
            break

    tasks = []
    for i, it in enumerate(issues):
        events = _cached(f"events_{it['number']}",
                         f"{API}/repos/{args.repo}/issues/{it['number']}/events",
                         token)
        tasks.append(to_task(args.repo, it, events))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(issues)} enriched", flush=True)

    # stratified split: keep reopened tickets represented in both splits
    reopened = [t for t in tasks if t["reopened"]]
    clean = [t for t in tasks if not t["reopened"]]
    import random
    rng = random.Random(7)
    rng.shuffle(reopened)
    rng.shuffle(clean)
    n_dev = int(len(tasks) * args.dev_fraction)
    n_re_dev = int(len(reopened) * args.dev_fraction)
    dev = reopened[:n_re_dev] + clean[:n_dev - n_re_dev]
    held = reopened[n_re_dev:] + clean[n_dev - n_re_dev:]
    rng.shuffle(dev)
    rng.shuffle(held)

    labels = {}
    for t in tasks:
        labels[t["resolution_label"]] = labels.get(t["resolution_label"], 0) + 1
    meta = {"source": "github", "repo": args.repo, "label": args.label,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sampling": "random pages across full closed set (seed 20261007); "
                        "page 1 excluded from bias by randomization",
            "n": len(tasks), "n_dev": len(dev), "n_heldout": len(held),
            "reopened": len(reopened),
            "reopened_rate": round(len(reopened) / len(tasks), 4),
            "label_counts": labels,
            "note": "labels are deterministic heuristics; raw signals in "
                    "_raw per task"}
    with open(args.out, "w") as f:
        json.dump({"dev": dev, "heldout": held, "meta": meta}, f, indent=1)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
