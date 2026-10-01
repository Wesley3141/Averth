"""Adversarial synthetic production workload for averth.

Generates long-horizon support-agent traffic with the pathologies real
production traces have: retry storms, human escalations, multi-model routing,
per-call-priced tools (some failing), heavy-tail runaways, quadratic-ish
context growth, prompt-cache hits, parallel branch fan-out, and
failed-then-reopened runs. Seeded for reproducibility: the same seed always
produces the same ledger.

This is the stress harness the meter is validated against, and it ships so a
prospect can see what the report looks like on production-shaped traffic
before instrumenting anything real:

    python -m averth.cli simulate --attempts 5000 --seed 7 --html out.html

Two outputs:
  generate(...)   -> a fully-driven Tracker (meter directly)
  write_jsonl(...) -> EVENT-schema JSONL (round-trips through `averth trace`)

The workload is deliberately hostile to naive metering: runaways must land
in the tail, dead branches must not smear the productive merge step's yield,
failed attempts must read as 100% waste, and cache hits must show up as
savings rather than vanishing.
"""

import json
import random

from .tracker import Tracker

HUMAN_VALUE_PER_CASE = 11.20  # what the human team costs per resolved ticket

ROUTER = ("openai", "gpt-5-nano")
WORKER = ("anthropic", "claude-haiku-4-5")
PLANNER = ("anthropic", "claude-sonnet-4-5")
JUDGE = ("anthropic", "claude-opus-4-6")

TOOLS = [
    ("vector_retrieval", None, 0.00),
    ("crm_lookup", None, 0.00),
    ("web_search", None, 0.08),
    ("enrichment_api", 0.30, 0.10),   # per-hit priced, outside the LLM bill
    ("sandbox_run", 0.45, 0.12),
    ("browser_action", None, 0.05),
]

RETRY_REASONS = [
    "answer failed confidence check",
    "tool timeout, retrying",
    "validation schema mismatch",
    "retrieved stale context, refetching",
    "judge rejected draft",
]


class _Gen:
    """Drives a Tracker and mirrors every call as an EVENT-schema dict."""

    def __init__(self, tracker, rng, record_events):
        self.t = tracker
        self.rng = rng
        self.record_events = record_events
        self.events = []
        self.ctx_in = 0

    # -- mirrored primitives --
    def start(self, case_id):
        self.t.start_attempt(case_id=case_id)
        if self.record_events:
            self.events.append({"type": "start", "case_id": case_id})

    def model(self, provider, model, out_base, cache_frac=0.0, branch=None):
        r = self.rng
        # state accumulation tax: every step re-sends grown history
        self.ctx_in = min(int(self.ctx_in * r.uniform(1.15, 1.60)), 190_000)
        in_tok = self.ctx_in
        out_tok = r.randint(int(out_base * 0.6), int(out_base * 1.4))
        cached = int(in_tok * cache_frac) if cache_frac else 0
        self.t.log_model_call(provider, model, in_tok, out_tok,
                              cached_input_tokens=cached, branch=branch)
        if self.record_events:
            ev = {"type": "model", "case_id": self.t._cur["case_id"],
                  "provider": provider, "model": model,
                  "input_tokens": in_tok, "output_tokens": out_tok}
            if cached:
                ev["cached_input_tokens"] = cached
            if branch:
                ev["branch"] = branch
            self.events.append(ev)

    def tool(self, name, cost=None, fail_rate=0.0, branch=None):
        r = self.rng
        failed = r.random() < fail_rate
        self.t.log_tool_call(name, cost=cost, branch=branch)
        if self.record_events:
            ev = {"type": "tool", "case_id": self.t._cur["case_id"],
                  "name": name}
            if cost is not None:
                ev["cost"] = cost
            if branch:
                ev["branch"] = branch
            self.events.append(ev)
        if failed:
            reason = "tool %s failed" % name
            self.t.log_retry(reason)
            if self.record_events:
                self.events.append({"type": "retry",
                                    "case_id": self.t._cur["case_id"],
                                    "reason": reason})
        return failed

    def retry(self, reason=None, branch=None):
        reason = reason or self.rng.choice(RETRY_REASONS)
        self.t.log_retry(reason, branch=branch)
        if self.record_events:
            ev = {"type": "retry", "case_id": self.t._cur["case_id"],
                  "reason": reason}
            if branch:
                ev["branch"] = branch
            self.events.append(ev)

    def escalate(self, lo=2.0, hi=12.0, reason="low confidence"):
        minutes = self.rng.uniform(lo, hi)
        self.t.log_escalation(minutes, reason)
        if self.record_events:
            self.events.append({"type": "escalation",
                                "case_id": self.t._cur["case_id"],
                                "minutes": minutes, "reason": reason})

    def end(self, success, reopened=False, value=HUMAN_VALUE_PER_CASE):
        self.t.end_attempt(success=success,
                           business_value=value if success else 0.0,
                           reopened=reopened)
        if self.record_events:
            self.events.append({"type": "end",
                                "case_id": self.t.attempts[-1]["case_id"],
                                "success": bool(success),
                                "business_value": value if success else 0.0,
                                "reopened": bool(reopened)})

    # -- workload shapes --
    def _router_triage(self):
        self.ctx_in = 900
        self.model(*ROUTER, out_base=120, cache_frac=0.70)
        name, cost, fail = self.rng.choice(TOOLS[:3])
        self.tool(name, cost=cost, fail_rate=0.05)

    def quick_resolve(self):
        self._router_triage()
        for _ in range(self.rng.randint(1, 3)):
            self.model(*WORKER, out_base=300)
        self.end(success=True)

    def standard(self):
        self._router_triage()
        self.model(*PLANNER, out_base=500)
        for _ in range(self.rng.randint(1, 3)):
            name, cost, fail = self.rng.choice(TOOLS)
            self.tool(name, cost=cost, fail_rate=fail)
            self.model(*WORKER, out_base=350)
        # 12%: parallel fan-out — one branch dies, merge step is productive
        if self.rng.random() < 0.12:
            self.model(*PLANNER, out_base=200)  # fan-out plan
            for branch in ("research", "billing", "history"):
                self.model(*WORKER, out_base=250, branch=branch)
            dead = self.rng.choice(["research", "billing", "history"])
            self.tool("web_search", branch=dead)  # dead branch burns a tool
            self.retry("branch %s returned conflicting data" % dead,
                       branch=dead)
            self.model(*WORKER, out_base=300, branch=dead)
            self.model(*PLANNER, out_base=400)  # merge: NOT waste
        self.end(success=True, reopened=self.rng.random() < 0.05)

    def retry_storm(self):
        self._router_triage()
        for _ in range(self.rng.randint(2, 6)):
            self.retry()
            self.model(*PLANNER, out_base=450)
            if self.rng.random() < 0.5:
                name, cost, fail = self.rng.choice(TOOLS)
                self.tool(name, cost=cost, fail_rate=0.15)
        self.end(success=self.rng.random() < 0.60)

    def escalation(self):
        self._router_triage()
        self.model(*PLANNER, out_base=600)
        name, cost, fail = self.rng.choice(TOOLS)
        self.tool(name, cost=cost, fail_rate=fail)
        self.retry("judge rejected draft")
        self.model(*JUDGE, out_base=900)  # expensive fallback
        self.escalate()
        self.end(success=True)

    def failed_clean(self):
        self._router_triage()
        for _ in range(self.rng.randint(2, 5)):
            self.model(*WORKER, out_base=300)
        self.end(success=False)

    def runaway(self):
        # heavy tail: recursive loop, context explosion, eventual failure
        self._router_triage()
        for _ in range(self.rng.randint(20, 70)):
            self.model(*PLANNER, out_base=300)
            if self.rng.random() < 0.35:
                self.tool("web_search", fail_rate=0.10)
            if self.rng.random() < 0.30:
                self.retry()
        self.end(success=False)


def generate(seed=42, attempts=2000, agent_name="synthetic-support",
            record_events=False):
    """Drive a Tracker with adversarial synthetic production traffic.

    Returns (tracker, events). events is None unless record_events=True.
    Deterministic for a fixed seed.
    """
    rng = random.Random(seed)
    tracker = Tracker(agent_name)
    g = _Gen(tracker, rng, record_events)
    for i in range(attempts):
        g.start("S-%05d" % i)
        r = rng.random()
        if r < 0.55:
            g.quick_resolve()
        elif r < 0.75:
            g.standard()
        elif r < 0.85:
            g.retry_storm()
        elif r < 0.91:
            g.escalation()
        elif r < 0.95:
            g.failed_clean()
        elif r < 0.98:
            # reopened success: accepted, then the customer came back
            g._router_triage()
            g.model(*WORKER, out_base=300)
            g.end(success=True, reopened=True)
        else:
            g.runaway()
    return tracker, (g.events if record_events else None)


def write_jsonl(path, seed=42, attempts=2000, agent_name="synthetic-support"):
    """Write the synthetic workload as EVENT-schema JSONL for `averth trace`."""
    _, events = generate(seed=seed, attempts=attempts, agent_name=agent_name,
                         record_events=True)
    with open(path, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return path
