"""Fetch labeled GitHub issues -> tasks.json with dev/heldout splits.

Ground truth: 'bug' vs 'feature request' labels (canonical classes).
Component labels captured for the routing subtask.
Public inputs, pinned at fetch time; reruns use the pinned file.
"""
import json, subprocess, random, sys

REPO = "langchain-ai/langchain"
PER_LABEL = 120
BODY_CHARS = 2000

def gh_issues(label, per_page=100):
    out = []
    page = 1
    while len(out) < PER_LABEL:
        r = subprocess.run(
            ["gh", "api", f"repos/{REPO}/issues?state=all&labels={label}"
             f"&per_page={per_page}&page={page}",
             "-q", ".[] | select(.pull_request == null) | "
                   "{number, title, body, labels: [.labels[].name]}"],
            capture_output=True, text=True, timeout=60)
        batch = [json.loads(l) for l in r.stdout.strip().split("\n") if l.strip()]
        if not batch:
            break
        out.extend(batch)
        page += 1
    return out[:PER_LABEL]

def canonical(labels):
    low = [l.lower() for l in labels]
    is_bug = any("bug" == l or l.startswith("bug:") for l in low)
    is_feat = any("feature request" in l or "enhancement" in l for l in low)
    if is_bug and not is_feat:
        return "bug"
    if is_feat and not is_bug:
        return "feature_request"
    return None

def main():
    random.seed(20261007)
    tasks = []
    seen = set()
    for label in ["bug", "feature%20request"]:
        for iss in gh_issues(label):
            if iss["number"] in seen:
                continue
            cls = canonical(iss["labels"])
            if cls is None:
                continue
            seen.add(iss["number"])
            body = (iss.get("body") or "")[:BODY_CHARS]
            tasks.append({
                "id": f"{REPO}#{iss['number']}",
                "title": iss["title"] or "",
                "body": body,
                "class": cls,
                "labels": iss["labels"],
            })
    random.shuffle(tasks)
    # stratified split: 60% dev, 40% heldout
    by_cls = {"bug": [], "feature_request": []}
    for t in tasks:
        by_cls[t["class"]].append(t)
    dev, heldout = [], []
    for cls, items in by_cls.items():
        n_dev = int(len(items) * 0.6)
        dev.extend(items[:n_dev])
        heldout.extend(items[n_dev:])
    random.shuffle(dev); random.shuffle(heldout)
    out = {"repo": REPO, "dev": dev, "heldout": heldout,
           "note": "pinned 2026-10-07; reruns use this file"}
    with open("tasks.json", "w") as f:
        json.dump(out, f)
    print(f"total={len(tasks)} dev={len(dev)} heldout={len(heldout)}")
    print(f"dev bug={sum(1 for t in dev if t['class']=='bug')} "
          f"feat={sum(1 for t in dev if t['class']=='feature_request')}")
    print(f"heldout bug={sum(1 for t in heldout if t['class']=='bug')} "
          f"feat={sum(1 for t in heldout if t['class']=='feature_request')}")

if __name__ == "__main__":
    main()
