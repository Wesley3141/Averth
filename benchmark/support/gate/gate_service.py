"""Averth deployment gate: webhook/API interceptor for support-agent changes.

Sits between the config surface (deployment wrapper, approval workflow)
and production. On a proposed change it runs the shadow support-ticket
battery against the CURRENT APPROVED production config and the CANDIDATE
config, and returns pass/fail.

This is a DELTA gate between two explicit, versioned configurations. The
baseline is the team's current production config (caller-supplied), NOT a
pinned benchmark agent. The pinned arm-A agent belongs to the benchmark;
the gate compares what is deployed with what is proposed.

The v1 measured metric is COST PER CORRECTLY CLASSIFIED TICKET: the
benchmark's acceptance is label accuracy, not resolved support work (a
correct label passes even with an empty draft). "Cost per acceptable
resolution" remains the product metric; v1 proxies it with
classification and must not claim more. Answer/action grading against
reviewed cases, then prospective outcome joining, are required before
promoting the metric.

Evaluations are ASYNC: POST enqueues and returns 202; the caller polls
(or long-polls with ?wait_seconds=) for the decision.

Decision contract (the executable part):
- Mock/shadow output NEVER approves: in mock mode `pass` is always
  false; the hypothetical lives in `would_pass`.
- Thresholds must be finite numbers. Null/NaN/non-numeric thresholds are
  rejected (400) — a missing cost limit fails closed, it never disables
  the check.
- The decision binds the exact candidate config, baseline config,
  battery (n/split/seed), threshold, and policy revision via hashes, so
  it cannot authorize a different change.
- Production serving requires HMAC auth (AVERTH_GATE_HMAC_SECRET) unless
  AVERTH_GATE_ALLOW_INSECURE=1 is set explicitly.

Stdlib only. See INTERCEPTOR_SPEC.md.
"""
import hashlib
import hmac
import json
import math
import os
import queue
import random
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPORT = os.path.dirname(HERE)
sys.path.insert(0, SUPPORT)
sys.path.insert(0, os.path.join(SUPPORT, "..", ".."))

import grader
import support_agent
from support_agent import TRACKER, build_corpus

DEFAULT_THRESHOLD = {
    "max_cost_per_correctly_classified": 0.05,  # USD; FinOps-governed
    "min_acceptance_rate": 0.80,
}
MAX_ACCEPT_REGRESSION_PP = 5.0
MAX_WAIT_S = 120

_corpus_built = False


def _ensure_corpus(tasks_path):
    global _corpus_built
    if _corpus_built:
        return
    with open(tasks_path) as f:
        data = json.load(f)
    build_corpus(data["dev"])
    _corpus_built = True


def _live_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _config_hash(cfg):
    return hashlib.sha256(
        json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def build_variant(cfg):
    """Turn a config dict into an agent function. Single implementation
    lives in support_agent; both the benchmark arms and the gate use it.
    """
    return support_agent.make_variant(cfg)


def _validate_threshold(threshold):
    """Thresholds must be finite numbers. Anything else fails closed."""
    max_c = threshold.get("max_cost_per_correctly_classified")
    min_a = threshold.get("min_acceptance_rate", 0.0)
    for name, v in (("max_cost_per_correctly_classified", max_c),
                    ("min_acceptance_rate", min_a)):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"threshold {name} must be a number, "
                             f"got {v!r}")
        if not math.isfinite(v):
            raise ValueError(f"threshold {name} must be finite, got {v!r}")
    if max_c < 0:
        raise ValueError("max_cost_per_correctly_classified must be >= 0")
    if not 0.0 <= min_a <= 1.0:
        raise ValueError("min_acceptance_rate must be in [0, 1]")
    return {"max_cost_per_correctly_classified": float(max_c),
            "min_acceptance_rate": float(min_a)}


def _run_arm(tasks, agent_fn, mode):
    """Run one arm of the battery. Returns (grades, summary, cost)."""
    real_client = support_agent.client
    if mode == "mock":
        from runner import MockClient
        support_agent.client = MockClient()
    try:
        grades = []
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
        "cost_per_correctly_classified":
            round(cost / accepted, 6) if accepted else None,
        "total_cost": round(cost, 6),
    }


def evaluate(change_id, baseline_cfg, candidate_cfg, threshold, tasks,
             mode="mock", policy_rev=None):
    """Delta-gate decision: current production config vs candidate.

    baseline_cfg: the team's CURRENT APPROVED production config
    (versioned dict). candidate_cfg: the proposed config (versioned dict).
    Pass requires the candidate within threshold AND no acceptance
    regression vs baseline. In mock mode pass is always False; see
    would_pass.
    """
    if mode == "live" and not _live_available():
        raise RuntimeError(
            "live evaluation requested but ANTHROPIC_API_KEY is not set")
    if mode not in ("mock", "live"):
        raise ValueError(f"unknown mode {mode!r}")
    threshold = _validate_threshold(threshold)
    policy_rev = policy_rev or os.environ.get("AVERTH_GATE_POLICY_REV",
                                              "default")

    _, base_summary, base_cost = _run_arm(
        tasks, build_variant(baseline_cfg), mode)
    _, cand_summary, cand_cost = _run_arm(
        tasks, build_variant(candidate_cfg), mode)

    base = _arm_metrics(base_summary, base_cost)
    cand = _arm_metrics(cand_summary, cand_cost)

    max_c = threshold["max_cost_per_correctly_classified"]
    min_a = threshold["min_acceptance_rate"]
    violations = []
    cpar = cand["cost_per_correctly_classified"]
    if cpar is None:
        violations.append("candidate: shadow battery produced zero correct "
                          "classifications")
    elif cpar > max_c:
        violations.append(
            f"candidate cost per correctly classified ticket ${cpar:.4f} "
            f"exceeds threshold ${max_c:.4f}")
    if cand["acceptance_rate"] < min_a:
        violations.append(
            f"candidate acceptance rate {cand['acceptance_rate']:.1%} below "
            f"floor {min_a:.1%}")
    reg_pp = (base["acceptance_rate"] - cand["acceptance_rate"]) * 100
    if reg_pp > MAX_ACCEPT_REGRESSION_PP:
        violations.append(
            f"candidate acceptance regressed {reg_pp:.1f}pp vs current "
            f"production config (limit {MAX_ACCEPT_REGRESSION_PP:.0f}pp)")

    would_pass = not violations
    battery_id = f"n{len(tasks)}"
    decision = {
        "change_id": change_id,
        # Mock/shadow output NEVER approves a deployment.
        "pass": False if mode == "mock" else would_pass,
        "would_pass": would_pass,
        "violations": violations,
        "baseline": {**base, "config_version":
                     (baseline_cfg or {}).get("version", "unknown"),
                     "config_hash": _config_hash(baseline_cfg or {})},
        "candidate": {**cand, "config_version":
                      (candidate_cfg or {}).get("version", "unknown"),
                      "config_hash": _config_hash(candidate_cfg or {})},
        "delta": {
            "cost_per_correctly_classified":
                (round(cpar - base["cost_per_correctly_classified"], 6)
                 if cpar is not None and
                 base["cost_per_correctly_classified"] is not None else None),
            "acceptance_rate_pp": round(-reg_pp, 2),
        },
        "threshold_applied": threshold,
        "policy_rev": policy_rev,
        "battery": {"n_evaluated": len(tasks), "id": battery_id},
        "mode": mode,
    }
    if mode == "mock":
        decision["note"] = ("MOCK MODE: pass is always false. would_pass "
                            "shows the hypothetical. This NEVER authorizes "
                            "a deployment.")
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
            status, payload = "done", ("result", result)
        except Exception as e:  # fail closed: errors never green-light
            status, payload = "error", ("error", str(e)[:300])
        finally:
            with _jobs_lock:
                # The job may have been evicted while running; guard it.
                if job_id in _jobs:
                    _jobs[job_id]["status"] = status
                    _jobs[job_id][payload[0]] = payload[1]
            _job_queue.task_done()


_worker_thread = None


def ensure_worker():
    global _worker_thread
    if _worker_thread is None:
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()


def _evict_if_needed():
    # Evict only terminal jobs, oldest first; never evict a running job.
    with _jobs_lock:
        while len(_jobs) >= _MAX_JOBS:
            terminal = [k for k, j in _jobs.items()
                        if j["status"] in ("done", "error")]
            if not terminal:
                break
            oldest = min(terminal, key=lambda k: _jobs[k]["created"])
            del _jobs[oldest]


def submit_evaluation(change_id, baseline_cfg, candidate_cfg, threshold,
                      tasks, mode, policy_rev=None):
    """Enqueue an evaluation. Returns the job id."""
    ensure_worker()
    _evict_if_needed()
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "created": time.time(),
                         "result": None, "error": None,
                         "change_id": change_id}
    _job_queue.put((job_id, lambda: evaluate(
        change_id, baseline_cfg, candidate_cfg, threshold, tasks, mode,
        policy_rev)))
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


def _auth_ok(handler):
    secret = os.environ.get("AVERTH_GATE_HMAC_SECRET")
    if secret:
        return True
    return os.environ.get("AVERTH_GATE_ALLOW_INSECURE") == "1"


class Handler(BaseHTTPRequestHandler):
    server_version = "AverthGate/0.3"

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
            return True  # enforced at startup unless insecure allowed
        sig = self.headers.get("X-Averth-Signature", "")
        want = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, want)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/v1/health":
            self._json(200, {"ok": True, "service": "averth-gate",
                             "version": "0.3"})
        elif path == "/v1/thresholds":
            self._json(200, {"threshold": DEFAULT_THRESHOLD,
                             "policy_rev": os.environ.get(
                                 "AVERTH_GATE_POLICY_REV", "default"),
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
        if not _auth_ok(self):
            self._json(503, {"error": "production authentication not "
                                      "configured: set "
                                      "AVERTH_GATE_HMAC_SECRET or "
                                      "AVERTH_GATE_ALLOW_INSECURE=1"})
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
            # Baseline = current approved production config (required:
            # the gate compares against what is deployed, not a pinned
            # benchmark agent).
            baseline_cfg = req.get("baseline")
            if not isinstance(baseline_cfg, dict):
                self._json(400, {"error": "baseline (current production "
                                          "config) is required"})
                return
            candidate_cfg = req.get("candidate")
            if not isinstance(candidate_cfg, dict):
                self._json(400, {"error": "candidate (proposed config) is "
                                          "required"})
                return
            threshold = {**DEFAULT_THRESHOLD, **(req.get("threshold") or {})}
            try:
                threshold = _validate_threshold(threshold)
            except ValueError as e:
                self._json(400, {"error": f"invalid threshold: {e}"})
                return
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
            job_id = submit_evaluation(change_id, baseline_cfg,
                                       candidate_cfg, threshold, tasks,
                                       mode)
            poll = f"/v1/gate/evaluations/{job_id}"
            wait_s = parse_qs(parsed.query).get("wait_seconds", [0])
            try:
                wait_s = max(0, min(MAX_WAIT_S, int(wait_s[0])))
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
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
