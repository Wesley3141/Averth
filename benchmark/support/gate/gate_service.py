"""Averth deployment gate: webhook/API interceptor for support-agent changes.

Sits between the config surface (LaunchDarkly flag flip, prompt-registry
update, dashboard change) and production. On a proposed change it runs the
shadow support-ticket battery against BOTH the current agent and the
proposed config, and returns pass/fail against the FinOps-governed Cost
per Acceptable Resolution threshold plus a no-regression check.

This is a DELTA gate: the proposed payload must contain the actual change
(full prompt text and/or model id). A gate that only re-measures the
current agent is a retroactive monitor, not a gate.

Evaluations are ASYNC: config surfaces cap webhooks at 10-30s, but a live
shadow battery takes minutes. POST enqueues and returns 202; the caller
polls (or long-polls with ?wait_seconds=) for the decision.

Stdlib only (no new dependencies). See INTERCEPTOR_SPEC.md.

Endpoints:
  GET  /v1/health
  GET  /v1/thresholds
  POST /v1/gate/evaluations[?wait_seconds=N] -> 202 {evaluation_id, poll}
       body: {"change_id", "proposed": {"model", "prompt", "haiku_model"},
              "threshold": {"max_cost_per_acceptable_resolution",
                            "min_acceptance_rate"},
              "battery": {"n", "split", "seed"}, "mode": "mock"|"live"}
  GET  /v1/gate/evaluations/{id} -> {status, result}

Mock mode is NEVER a real gate decision: stamped "mock": true.
"""
import hashlib
import hmac
import json
import os
import queue
import random
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

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
# Acceptance may not regress more than this vs the current agent.
MAX_ACCEPT_REGRESSION_PP = 5.0

_corpus_built = False


def _ensure_corpus(tasks_path):
    global _corpus_built
    if _corpus_built:
        return
    with open(tasks_path) as f:
        data = json.load(f)
    # Dev-only corpus: the shadow battery must not leak heldout labels
    # through the similar-ticket tool.
    build_corpus(data["dev"])
    _corpus_built = True


def _live_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def build_variant(proposed):
    """Turn a proposed-config payload into an agent function.

    proposed: {"model": <sonnet model id>, "prompt": <full final system
    prompt text>, "haiku_model": <haiku model id>}. Missing keys fall back
    to the pinned arm-A defaults, so a partial proposal still evaluates.
    """
    model = proposed.get("model", support_agent.SONNET)
    haiku_model = proposed.get("haiku_model", support_agent.HAIKU)
    prompt = proposed.get("prompt")  # None -> pinned final system prompt

    def variant(task):
        return support_agent.resolve_ticket(
            task, model_haiku=haiku_model, model_sonnet=model,
            final_system=prompt)
    return variant


def _run_arm(tasks, agent_fn, mode):
    """Run one arm of the battery. Returns (grades, summary, cost)."""
    real_client = support_agent.client
    if mode == "mock":
        from runner import MockClient
        support_agent.client = MockClient()
    try:
        grades = []
        # The Tracker ledger is process-global; diff around this arm so
        # repeated evaluations don't accumulate each other's cost.
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
    cost = TRACKER.pnl().get("cost_total", 0) - cost_before
    return grades, summary, cost


def _arm_metrics(summary, cost):
    accepted = summary["accepted"]
    return {
        "n": summary["n"],
        "accepted": accepted,
        "acceptance_rate": round(summary["acceptance_rate"], 4),
        "cost_per_acceptable_resolution":
            round(cost / accepted, 6) if accepted else None,
        "total_cost": round(cost, 6),
    }


def evaluate(change_id, proposed, threshold, tasks, mode="mock"):
    """Delta-gate decision: current agent vs proposed config.

    Runs the shadow battery twice (baseline + proposed variant) and
    passes the change only if the PROPOSED config is within the
    FinOps threshold AND does not regress acceptance vs baseline.
    """
    if mode == "live" and not _live_available():
        raise RuntimeError(
            "live evaluation requested but ANTHROPIC_API_KEY is not set")
    if mode not in ("mock", "live"):
        raise ValueError(f"unknown mode {mode!r}")

    _, base_summary, base_cost = _run_arm(
        tasks, support_agent.resolve_ticket, mode)
    _, prop_summary, prop_cost = _run_arm(
        tasks, build_variant(proposed), mode)

    base = _arm_metrics(base_summary, base_cost)
    prop = _arm_metrics(prop_summary, prop_cost)

    max_cpar = threshold.get("max_cost_per_acceptable_resolution")
    min_acc = threshold.get("min_acceptance_rate", 0.0)
    violations = []
    cpar = prop["cost_per_acceptable_resolution"]
    if cpar is None:
        violations.append("proposed config: shadow battery produced zero "
                          "accepted resolutions")
    elif max_cpar is not None and cpar > max_cpar:
        violations.append(
            f"proposed cost per acceptable resolution ${cpar:.4f} exceeds "
            f"threshold ${max_cpar:.4f}")
    if prop["acceptance_rate"] < min_acc:
        violations.append(
            f"proposed acceptance rate {prop['acceptance_rate']:.1%} below "
            f"floor {min_acc:.1%}")
    reg_pp = (base["acceptance_rate"] - prop["acceptance_rate"]) * 100
    if reg_pp > MAX_ACCEPT_REGRESSION_PP:
        violations.append(
            f"proposed acceptance regressed {reg_pp:.1f}pp vs current agent "
            f"(limit {MAX_ACCEPT_REGRESSION_PP:.0f}pp)")

    decision = {
        "change_id": change_id,
        "pass": not violations,
        "violations": violations,
        "baseline": base,
        "proposed": prop,
        "delta": {
            "cost_per_acceptable_resolution":
                (round(cpar - base["cost_per_acceptable_resolution"], 6)
                 if cpar is not None and
                 base["cost_per_acceptable_resolution"] is not None else None),
            "acceptance_rate_pp": round(-reg_pp, 2),
        },
        "threshold_applied": threshold,
        "proposed_config": proposed,
        "mode": mode,
    }
    if mode == "mock":
        decision["note"] = ("MOCK MODE: plumbing validation only. This is "
                            "NOT a real gate decision.")
    return decision


# ---- async job layer: one worker thread, serialized evaluations ----

_jobs = {}
_jobs_lock = threading.Lock()
_job_queue = queue.Queue()
_MAX_JOBS = 100


def _worker():
    while True:
        job_id, fn = _job_queue.get()
        try:
            result = fn()
            with _jobs_lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
        except Exception as e:  # fail closed: errors never green-light
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(e)[:300]
        finally:
            _job_queue.task_done()


_worker_thread = None


def ensure_worker():
    global _worker_thread
    if _worker_thread is None:
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()


def submit_evaluation(change_id, proposed, threshold, tasks, mode):
    """Enqueue an evaluation. Returns the job id."""
    ensure_worker()
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        if len(_jobs) >= _MAX_JOBS:
            oldest = min(_jobs, key=lambda k: _jobs[k]["created"])
            del _jobs[oldest]
        _jobs[job_id] = {"status": "running", "created": time.time(),
                         "result": None, "error": None,
                         "change_id": change_id}
    _job_queue.put((job_id,
                    lambda: evaluate(change_id, proposed, threshold, tasks,
                                     mode)))
    return job_id


def get_job(job_id):
    with _jobs_lock:
        return dict(_jobs.get(job_id)) if job_id in _jobs else None


def wait_job(job_id, timeout_s):
    """Poll until done/error or timeout. Returns the job dict or None."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job = get_job(job_id)
        if job and job["status"] in ("done", "error"):
            return job
        time.sleep(0.25)
    return get_job(job_id)


class Handler(BaseHTTPRequestHandler):
    server_version = "AverthGate/0.2"

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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/v1/health":
            self._json(200, {"ok": True, "service": "averth-gate",
                             "version": "0.2"})
        elif path == "/v1/thresholds":
            self._json(200, {"threshold": DEFAULT_THRESHOLD,
                             "governed_by": "FinOps (partner-configured)"})
        elif path.startswith("/v1/gate/evaluations/"):
            job_id = path.rsplit("/", 1)[-1]
            job = get_job(job_id)
            if not job:
                self._json(404, {"error": "unknown evaluation"})
                return
            out = {"evaluation_id": job_id, "status": job["status"]}
            if job["status"] == "done":
                out["result"] = job["result"]
            elif job["status"] == "error":
                out["error"] = job["error"]
                out["pass"] = False  # fail closed
            self._json(200, out)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/v1/gate/evaluations":
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
            if mode == "live" and not _live_available():
                self._json(503, {"error": "live evaluation requested but "
                                          "ANTHROPIC_API_KEY is not set"})
                return
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
            job_id = submit_evaluation(change_id, proposed, threshold,
                                       tasks, mode)
            poll = f"/v1/gate/evaluations/{job_id}"
            # Long-poll: callers behind 10-30s webhook caps pass
            # ?wait_seconds=25 to block for the decision.
            wait_s = parse_qs(parsed.query).get("wait_seconds", [0])
            try:
                wait_s = max(0, int(wait_s[0]))
            except (ValueError, IndexError):
                wait_s = 0
            if wait_s:
                job = wait_job(job_id, wait_s)
                if job and job["status"] == "done":
                    self._json(200, {"evaluation_id": job_id,
                                     "status": "done",
                                     "result": job["result"]})
                    return
                if job and job["status"] == "error":
                    self._json(200, {"evaluation_id": job_id,
                                     "status": "error",
                                     "error": job["error"], "pass": False})
                    return
            self._json(202, {"evaluation_id": job_id, "status": "running",
                             "poll": poll,
                             "note": "poll GET until status is done"})
        except (KeyError, ValueError) as e:
            self._json(400, {"error": f"bad request: {e}"})
        except Exception as e:  # fail closed
            self._json(500, {"error": "gate error (fail closed)",
                             "pass": False, "detail": str(e)[:200]})

    def log_message(self, *a):
        pass  # quiet; production deployments add structured logging


def main():
    port = int(os.environ.get("AVERTH_GATE_PORT", "8077"))
    ensure_worker()
    print(f"averth gate listening on :{port} (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
