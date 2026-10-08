"""No-change repeatability probe for the deployment gate.

Submits the SAME configuration as both baseline and candidate N times
and reports how often the gate fails it. Per PRE_REGISTRATION.md, a
gate whose no-change failure rate exceeds 5% is too noisy to enforce.

Usage:
    python nochange_probe.py --host localhost:8077 --config config.json \
        --n 10 --battery-n 30 [--wait 120]

config.json: {"version": "prod-v7", "model": "...", "prompt": "..."}
The same config is sent as both baseline and candidate, so any failure
is a false alarm (model nondeterminism, battery sampling, or a gate
bug). Requires a running gate; live evaluations need ANTHROPIC_API_KEY
on the gate side.
"""
import argparse
import json
import sys
import time
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="localhost:8077")
ap.add_argument("--config", required=True)
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--battery-n", type=int, default=30)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--wait", type=int, default=120)
ap.add_argument("--mode", default="mock", choices=["mock", "live"])
args = ap.parse_args()

with open(args.config) as f:
    cfg = json.load(f)

fails = 0
results = []
for i in range(args.n):
    body = json.dumps({
        "change_id": f"nochange-probe-{i}",
        "baseline": cfg,
        "candidate": cfg,
        "battery": {"n": args.battery_n, "split": "dev", "seed": args.seed},
        "mode": args.mode,
    }).encode()
    req = urllib.request.Request(
        f"http://{args.host}/v1/gate/evaluations?wait_seconds={args.wait}",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=args.wait + 60) as r:
            payload = json.load(r)
    except Exception as e:
        print(f"run {i}: HTTP error: {e}")
        fails += 1
        continue
    res = payload.get("result") or {}
    ok = res.get("would_pass", False)
    results.append(ok)
    if not ok:
        fails += 1
        print(f"run {i}: FALSE ALARM "
              f"(violations: {res.get('violations')})")
    else:
        print(f"run {i}: pass "
              f"(cpar={res.get('candidate', {}).get('cost_per_correctly_classified')})")
    time.sleep(1)

rate = fails / args.n
print(f"\nno-change fail rate: {fails}/{args.n} = {rate:.1%}")
print("VERDICT: too noisy to enforce" if rate > 0.05
      else "VERDICT: within the 5% false-alarm budget")
sys.exit(1 if rate > 0.05 else 0)
