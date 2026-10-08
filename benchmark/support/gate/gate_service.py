"""Averth deployment gate: webhook/API interceptor for support-agent changes.

Sits between the config surface (LaunchDarkly flag flip, prompt-registry
update, dashboard change) and production. On a proposed change it runs the
shadow support-ticket battery and returns pass/fail against the
FinOps-governed Cost per Acceptable Resolution threshold.

Stdlib only (no new dependencies). See INTERCEPTOR_SPEC.md for how
config dashboards call this.

Endpoints:
  GET  /v1/health      -> {"ok": true}
  GET  /v1/thresholds   -> current FinOps-governed thresholds
  POST /v1/gate/evaluate -> pass/fail decision for a proposed change

POST body:
  {"change_id": "ld-flag-123",
   "proposed": {"model": "claude-sonnet-4-5", "prompt_version": "v14",
                "config": {...}},
   "threshold": {"max_cost_per_acceptable_resolution": 0.05,
                 "min_acceptance_rate": 0.80},   # optional; defaults apply
   "battery": {"n": 20, "split": "dev", "seed": 7},
   "mode": "mock"}   # "mock" = plumbing only; "live" needs ANTHROPIC_API_KEY

Mock mode is NEVER a real gate decision: the response is stamped
"mock": true and the note says so explicitly.
"""
import hashlib
import hmac
import json
import os
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPORT = os.path.dirname(HERE)
sys.path.insert(0, SUPPORT)
sys.path.insert(0, os.path.join(SUPPORT, "..", ".."))

import grader
import support_agent
from support_agent import TRACKER, build_corpus

DEFAULT_THRESHOLD = {
    "max_cost_per_acceptable_resolution": 0.05,  # USD; FinOps-governed
    "min_acceptance_rate": 0.80,
}

_corpus_built = False


def _ensure_corpus(tasks_path):
    global _corpus_built
    if _corpus_built:
        return
    with open(tasks_path) as f:
        data = json.load(f)
    # Dev-only corpus: the gate's shadow battery must not leak heldout
    # labels through the similar-ticket tool.
    build_corpus(data["dev"])
    _corpus_built = True


def _live_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def evaluate(change_id, proposed, threshold, tasks, mode="mock",
            agent_fn=None):
    """Core gate decision. Pure logic; testable without HTTP.

    agent_fn: callable(task) -> (prediction, _). Defaults to the pinned
    arm-A agent. Inject a variant (e.g. a proposed prompt/model wrapped as
    a function) to shadow-test a PROPOSED config; the default measures the
    CURRENT agent against the threshold. The HTTP layer currently uses the
    default — proposed-config A/B is the v2 extension (see
    INTERCEPTOR_SPEC.md).
    """
    if mode == "live" and not _live_available():
        raise RuntimeError(
            "live evaluation requested but ANTHROPIC_API_KEY is not set")
    if mode not in ("mock", "live"):
        raise ValueError(f"unknown mode {mode!r}")
    agent_fn = agent_fn or support_agent.resolve_ticket

    real_client = support_agent.client
    if mode == "mock":
        # swap in the deterministic mock client (plumbing only)
        from runner import MockClient
        support_agent.client = MockClient()
    try:
        grades = []
        # The Tracker ledger is process-global; diff around this evaluation
        # so repeated gate calls in one process don't accumulate cost.
        cost_before = TRACKER.pnl().get("cost_total", 0)
        for t in tasks:
            try:
                pred, _ = agent_fn(t)
                g = grader.grade(pred, t)
            except Exception as e:
                try:
                    TRACKER.end_attempt(success=False)
                except Exception:
                    pass
                g = {"task_id": t["id"], "predicted": "ERROR",
                     "actual": t["resolution_label"], "accepted": False,
                     "reopened": False, "sla_breach": False,
                     "time_to_close_hours": None, "response_draft": "",
                     "error": str(e)[:200]}
            grades.append(g)
    finally:
        support_agent.client = real_client

    summary = grader.summarize(grades)
    total_cost = TRACKER.pnl().get("cost_total", 0) - cost_before
    accepted = summary["accepted"]
    cpar = (total_cost / accepted) if accepted else None

    max_cpar = threshold.get("max_cost_per_acceptable_resolution")
    min_acc = threshold.get("min_acceptance_rate", 0.0)
    violations = []
    if cpar is None:
        violations.append("shadow battery produced zero accepted resolutions")
    else:
        if max_cpar is not None and cpar > max_cpar:
            violations.append(
                f"cost per acceptable resolution ${cpar:.4f} exceeds "
                f"threshold ${max_cpar:.4f}")
    if summary["acceptance_rate"] < min_acc:
        violations.append(
            f"acceptance rate {summary['acceptance_rate']:.1%} below floor "
            f"{min_acc:.1%}")

    decision = {
        "change_id": change_id,
        "pass": not violations,
        "violations": violations,
        "cost_per_acceptable_resolution":
            round(cpar, 6) if cpar is not None else None,
        "acceptance_rate": round(summary["acceptance_rate"], 4),
        "accepted": accepted,
        "n_evaluated": len(grades),
        "total_shadow_cost": round(total_cost, 6),
        "threshold_applied": threshold,
        "proposed": proposed,
        "mode": mode,
    }
    if mode == "mock":
        decision["note"] = ("MOCK MODE: plumbing validation only. This is "
                            "NOT a real gate decision.")
    return decision


class Handler(BaseHTTPRequestHandler):
    server_version = "AverthGate/0.1"

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_hmac(self, body):
        secret = os.environ.get("AVERTH_GATE_HMAC_SECRET")
        if not secret:
            return True  # HMAC enforced only when a secret is configured
        sig = self.headers.get("X-Averth-Signature", "")
        want = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, want)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/v1/health":
            self._json(200, {"ok": True, "service": "averth-gate",
                             "version": "0.1"})
        elif path == "/v1/thresholds":
            self._json(200, {"threshold": DEFAULT_THRESHOLD,
                             "governed_by": "FinOps (partner-configured)"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/v1/gate/evaluate":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if not self._check_hmac(body):
            self._json(401, {"error": "bad signature"})
            return
        try:
            req = json.loads(body)
        except Exception:
            self._json(400, {"error": "invalid JSON"})
            return
        try:
            change_id = req["change_id"]
            proposed = req.get("proposed", {})
            threshold = {**DEFAULT_THRESHOLD, **(req.get("threshold") or {})}
            battery = req.get("battery", {})
            mode = req.get("mode", "mock")
            n = int(battery.get("n", 20))
            split = battery.get("split", "dev")
            seed = int(battery.get("seed", 7))
            tasks_path = os.path.join(SUPPORT, "tasks.json")
            if not os.path.exists(tasks_path):
                self._json(503, {"error": "ticket battery not built yet; "
                                          "run fetch_tasks.py first"})
                return
            _ensure_corpus(tasks_path)
            with open(tasks_path) as f:
                pool = json.load(f)[split][:]
            rng = random.Random(seed)
            rng.shuffle(pool)
            tasks = pool[:n]
            t0 = time.time()
            decision = evaluate(change_id, proposed, threshold, tasks,
                                mode=mode)
            decision["elapsed_s"] = round(time.time() - t0, 1)
            self._json(200, decision)
        except RuntimeError as e:
            self._json(503, {"error": str(e)})
        except (KeyError, ValueError) as e:
            self._json(400, {"error": f"bad request: {e}"})
        except Exception as e:  # fail closed: never green-light on error
            self._json(500, {"error": "gate error (fail closed)",
                             "pass": False, "detail": str(e)[:200]})

    def log_message(self, *a):
        pass  # quiet; production deployments add structured logging


def main():
    port = int(os.environ.get("AVERTH_GATE_PORT", "8077"))
    print(f"averth gate listening on :{port} (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
