"""Fetch raw mini-SWE-agent trajectories from the public SWE-bench S3 bucket.

Mechanical fetch only: downloads the .traj.json files named below verbatim
from s3://swe-bench-submissions (anonymous read) into raw/, plus the entry's
metadata.yaml for provenance. No record content is edited.
"""
import json
import os
import sys
import urllib.request

BASE = ("https://s3.amazonaws.com/swe-bench-submissions/bash-only/"
        "20250726_mini-v1.0.0_claude-sonnet-4-20250514")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw")

# every ~42nd key of the 504-key trajs/ listing: mechanical spread, no
# cherry-picking
KEYS = [
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/astropy__astropy-12907/astropy__astropy-12907.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-11265/django__django-11265.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-12663/django__django-12663.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-13786/django__django-13786.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-14771/django__django-14771.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-9296/django__django-9296.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/psf__requests-1921/psf__requests-1921.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/pytest-dev__pytest-5787/pytest-dev__pytest-5787.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/scikit-learn__scikit-learn-25232/scikit-learn__scikit-learn-25232.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/sphinx-doc__sphinx-9320/sphinx-doc__sphinx-9320.traj.json",
    "bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/sympy__sympy-16886/sympy__sympy-16886.traj.json",
]


def get(url, path):
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    for key in KEYS:
        name = key.rsplit("/", 1)[-1]
        size = get("https://s3.amazonaws.com/swe-bench-submissions/" + key,
                   os.path.join(OUT, name))
        print("saved %s (%d bytes)" % (name, size))
    get("https://raw.githubusercontent.com/m0at/experiments/main/evaluation/verified/"
        "20250726_mini-v1.0.0_claude-sonnet-4-20250514/metadata.yaml",
        os.path.join(HERE, "metadata.yaml"))
    print("saved metadata.yaml")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
