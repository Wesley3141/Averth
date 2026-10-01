"""Fetch raw trajectory rows from SWE-bench/SWE-smith-trajectories (split=tool).

Mechanical fetch only: pulls rows at fixed offsets via the public
HuggingFace datasets-server rows API and stores each row's raw fields
(messages JSON string, instance_id, resolved, model, traj_id, patch)
verbatim in raw/<traj_id>.json. No record content is edited.
"""
import json
import os
import sys
import urllib.request

DATASET = "SWE-bench/SWE-smith-trajectories"
SPLIT = "tool"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

# fixed offsets spread across the 24,100-row split; chosen before any
# inspection of row content (mechanical sampling, not cherry-picking)
OFFSETS = [0, 2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000,
           18000, 20000, 22000, 23000, 500, 9500, 17500]


def fetch(offset):
    url = ("https://datasets-server.huggingface.co/rows?dataset=%s"
           "&config=default&split=%s&offset=%d&length=1"
           % (DATASET, SPLIT, offset))
    with urllib.request.urlopen(url, timeout=90) as r:
        return json.load(r)


def main():
    os.makedirs(OUT, exist_ok=True)
    got = 0
    for off in OFFSETS:
        d = fetch(off)
        rows = d.get("rows") or []
        if not rows:
            print("offset %d: no rows" % off, file=sys.stderr)
            continue
        row = rows[0]["row"]
        traj_id = row["traj_id"]
        path = os.path.join(OUT, traj_id + ".json")
        with open(path, "w") as f:
            json.dump(row, f)
        got += 1
        print("saved %s (resolved=%s, n_msgs_chars=%d)"
              % (traj_id, row["resolved"], len(row["messages"])))
    print("fetched %d raw rows -> %s" % (got, OUT))


if __name__ == "__main__":
    main()
