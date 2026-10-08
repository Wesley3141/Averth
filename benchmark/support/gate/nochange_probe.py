"""No-change repeatability probe for the deployment gate (mock only).

Submits the SAME configuration as both baseline and candidate N times
and reports how often the gate fails it. Any completed failure on an
unchanged config is a false alarm (model nondeterminism, battery
sampling, or a gate bug).

THIS IS A MOCK-MODE DIAGNOSTIC. It never produces an
enforcement-readiness verdict: mock results cannot authorize or qualify
enforcement. Live repeated probes are intentionally DISABLED — the
runner's ledger stop is a between-ticket check, not an evaluation-wide
hard spend cap, so repeated live probing has no safe budget bound yet.

Usage:
    python nochange_probe.py --host localhost:8077 --config config.json \
        --n 10 --battery-n 30 [--hmac-secret ...] [--budget-usd 10]

Trial outcomes are classified separately:
  completed-pass / completed-fail : the gate finished the evaluation
  http-error   : the request itself failed (connection, 4xx, 5xx)
  incomplete   : the job was still running at the poll timeout
Only completed-fail counts as a false alarm. http-error and incomplete
are infrastructure problems, not gate decisions.

Budget: --budget-usd (default 10.00) is the total experiment budget.
Mock spend is $0, so the budget is trivially satisfied and is recorded
in the report for when live probing is re-enabled.
"""
import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.request
import urllib.error

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="localhost:8077")
ap.add_argument("--config", required=True,
                help="JSON config sent as BOTH baseline and candidate")
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--battery-n", type=int, default=30)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--wait", type=int, default=120,
                help="seconds to poll one trial before calling it "
                     "incomplete")
ap.add_argument("--hmac-secret", default=None,
                help="sign requests with X-Averth-Signature")
ap.add_argument("--budget-usd", type=float, default=10.0,
                help="total experiment budget in USD (mock spend is $0)")
ap.add_argument("--mode", default="mock", choices=["mock", "live"])
args = ap.parse_args()

if args.mode == "live":
    print("ERROR: live repeated probes are disabled. The runner's ledger "
          "stop is a between-ticket check, not an evaluation-wide hard "
          "spend cap, so repeated live probing has no safe budget bound. "
          "Re-enable only with a true pre-flight spend cap.",
          file=sys.stderr)
    sys.exit(2)

with open(args.config) as f:
    cfg = json.load(f)


def _signed(body):
    headers = {"Content-Type": "application/json"}
    if args.hmac_secret:
        sig = hmac.new(args.hmac_secret.encode(), body,
                       hashlib.sha256).hexdigest()
        headers["X-Averth-Signature"] = sig
    return headers


def _post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"http://{args.host}{path}", data=body,
                                 headers=_signed(body))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode()[:200]
        except Exception:
            detail = ""
        return e.code, {"http_error": f"{e.code} {detail}"}
    except Exception as e:
        return None, {"http_error": f"connection: {e}"}


def _poll(poll_path, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        req = urllib.request.Request(f"http://{args.host}{poll_path}")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)
        except Exception as e:
            return {"outcome": "http-error", "detail": f"poll: {e}"}
        status = payload.get("status")
        if status == "done":
            return {"outcome": "completed", "result": payload["result"]}
        if status == "error":
            return {"outcome": "completed",
                    "result": {"would_pass": False,
                               "violations": [payload.get("error",
                                                          "job error")]}}
        time.sleep(2)
    return {"outcome": "incomplete", "detail": "poll timeout"}


outcomes = {"completed-pass": 0, "completed-fail": 0, "http-error": 0,
            "incomplete": 0}
for i in range(args.n):
    status, payload = _post(
        f"/v1/gate/evaluations?wait_seconds={args.wait}",
        {"change_id": f"nochange-probe-{i}", "baseline": cfg,
         "candidate": cfg,
         "battery": {"n": args.battery_n, "split": "dev",
                     "seed": args.seed},
         "mode": "mock"})
    if status is None or (isinstance(status, int) and status >= 400):
        outcomes["http-error"] += 1
        print(f"run {i}: HTTP-ERROR {payload.get('http_error')}")
        continue
    if payload.get("status") == "done":
        trial = {"outcome": "completed", "result": payload["result"]}
    elif payload.get("status") == "error":
        trial = {"outcome": "completed",
                 "result": {"would_pass": False, "violations": [
                     payload.get("error", "job error")]}}
    elif payload.get("status") == "running" and payload.get("poll"):
        trial = _poll(payload["poll"], args.wait)
    else:
        trial = {"outcome": "http-error",
                 "detail": f"unexpected response: {str(payload)[:120]}"}
    if trial["outcome"] == "completed":
        res = trial["result"]
        if res.get("would_pass"):
            outcomes["completed-pass"] += 1
            print(f"run {i}: completed-pass")
        else:
            outcomes["completed-fail"] += 1
            print(f"run {i}: completed-fail (false alarm; violations: "
                  f"{res.get('violations')})")
    else:
        outcomes[trial["outcome"]] += 1
        print(f"run {i}: {trial['outcome'].upper()} "
              f"({trial.get('detail', '')})")
    time.sleep(1)

completed = outcomes["completed-pass"] + outcomes["completed-fail"]
false_alarms = outcomes["completed-fail"]
rate = (false_alarms / completed) if completed else None
print(f"\ncompleted: {completed}/{args.n} "
      f"(pass={outcomes['completed-pass']}, "
      f"fail={outcomes['completed-fail']}, "
      f"http-error={outcomes['http-error']}, "
      f"incomplete={outcomes['incomplete']})")
if rate is not None:
    print(f"no-change false-alarm rate over completed trials: {rate:.1%}")
print(f"experiment budget: ${args.budget_usd:.2f}; mock spend $0.00 "
      f"(within budget)")
print("MOCK DIAGNOSTIC ONLY: this run cannot produce an "
      "enforcement-readiness verdict.")
