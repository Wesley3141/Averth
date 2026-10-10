"""Generate realistic fake production traces for prospect-simulation testing.

Scenario: 'Acme Support' — a customer-support agent handling tickets.
25 tickets over ~2 weeks. Each ticket: triage call -> knowledge-base lookup
-> response call. ~20% hit a retry (timeout), ~12% fail outright.

Cost realism:
- Most observations carry vendor calculatedTotalCost (billed bucket).
- Some carry only usageDetails (measured bucket: tokens x our prices).
- A few carry neither (unknown bucket: must render as missing, not free).
- Retries are marked via metadata so the retry path is attributed.
- No outcome labels (all inferred -> cost-per-success must read UNKNOWN).

Outputs (written to argv[1] or ./sim-traces/):
  langfuse.json   — Langfuse export shape ({data: [{observations: [...] }]})
  langsmith.json  — LangSmith run-export shape ([{run_type...}])
  otel.json       — OTLP JSON shape ({spans: [...]})
"""
import json
import os
import random
import sys

random.seed(20261010)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sim-traces")
os.makedirs(OUT, exist_ok=True)

MODELS = [("gpt-5.6", 0.55), ("gpt-5.6-mini", 0.45)]
N_TICKETS = 25

# per-call token ranges: (input_lo, input_hi, output_lo, output_hi)
TRIAGE = (800, 2000, 100, 400)
LOOKUP = (1500, 4000, 200, 600)
RESPOND = (2500, 6000, 400, 1200)


def pick_model():
    r = random.random()
    cum = 0.0
    for m, p in MODELS:
        cum += p
        if r < cum:
            return m
    return MODELS[0][0]


def billed_cost(model, i, o):
    """Fake vendor-calculated cost: roughly tokens x plausible rates."""
    rate = 0.000004 if "mini" in model else 0.000008
    return round((i + o) * rate * random.uniform(0.9, 1.1), 6)


tickets = []
for t in range(N_TICKETS):
    n_calls = random.choice([2, 2, 3, 3, 3, 4, 5])
    calls = []
    failed = random.random() < 0.12
    retry_at = random.randrange(n_calls) if random.random() < 0.20 else None
    for c in range(n_calls):
        spec = [TRIAGE, LOOKUP, RESPOND][min(c, 2)]
        model = pick_model()
        i = random.randint(spec[0], spec[1])
        o = random.randint(spec[2], spec[3])
        # cost provenance: 70% billed, 22% measured-only, 8% unknown
        r = random.random()
        if r < 0.70:
            cost = billed_cost(model, i, o)
            usage = {"input": i, "output": o}
        elif r < 0.92:
            cost = None
            usage = {"input": i, "output": o}
        else:
            cost = None
            usage = None
        calls.append({"model": model, "input": i, "output": o,
                      "cost": cost, "usage": usage,
                      "retry": (c == retry_at)})
    tickets.append({"id": f"ticket-{t+1:03d}", "calls": calls,
                    "failed": failed})


# ---- Langfuse ----
lf_traces = []
for tk in tickets:
    obs = []
    for j, c in enumerate(tk["calls"]):
        o = {"id": f"{tk['id']}-g{j}", "type": "GENERATION",
             "model": c["model"],
             "level": "ERROR" if (tk["failed"] and j == len(tk["calls"]) - 1)
             else "DEFAULT",
             "metadata": {}}
        if c["usage"]:
            o["usageDetails"] = {"input": c["input"], "output": c["output"]}
        if c["cost"] is not None:
            o["calculatedTotalCost"] = c["cost"]
        if c["retry"]:
            o["metadata"]["averth_retry"] = "timeout"
        obs.append(o)
    lf_traces.append({"id": tk["id"], "observations": obs})
with open(os.path.join(OUT, "langfuse.json"), "w") as f:
    json.dump({"data": lf_traces}, f)

# ---- LangSmith ----
ls_runs = []
for tk in tickets:
    ls_runs.append({"id": f"{tk['id']}-root", "name": "support-agent",
                    "run_type": "chain", "trace_id": tk["id"],
                    "parent_run_ids": [],
                    "start_time": "2026-09-28T10:00:00Z",
                    "end_time": "2026-09-28T10:02:00Z",
                    "error": None,
                    "serialized": {}, "outputs": {},
                    "extra": {"metadata": {}}})
    for j, c in enumerate(tk["calls"]):
        outputs = {}
        if c["usage"]:
            outputs = {"llm_output": {"token_usage": {
                "prompt_tokens": c["input"],
                "completion_tokens": c["output"]}}}
        # failure rule reads the chronologically-last run: error goes on the
        # last LLM run so failed tickets actually register as failed
        is_last = (j == len(tk["calls"]) - 1)
        ls_runs.append({"id": f"{tk['id']}-llm{j}", "name": "ChatOpenAI",
                        "run_type": "llm", "trace_id": tk["id"],
                        "parent_run_ids": [f"{tk['id']}-root"],
                        "start_time": "2026-09-28T10:00:10Z",
                        "end_time": "2026-09-28T10:00:40Z",
                        "error": ("ticket reopened" if tk["failed"]
                                  and is_last else None),
                        "serialized": {"kwargs": {"name": c["model"]}},
                        "outputs": outputs,
                        "extra": {"metadata": {
                            "ls_provider": "openai",
                            **({"averth_retry": "timeout"} if c["retry"]
                               else {})}}})
with open(os.path.join(OUT, "langsmith.json"), "w") as f:
    json.dump(ls_runs, f)

# ---- OTel ----
spans = []
base = 1758000000000000000
for ti, tk in enumerate(tickets):
    for j, c in enumerate(tk["calls"]):
        attrs = [{"key": "gen_ai.request.model",
                  "value": {"stringValue": c["model"]}}]
        # drop usage on a few spans: exercises the unknown-usage path
        drop_usage = (ti * 7 + j) % 29 == 0
        if c["usage"] and not drop_usage:
            attrs += [
                {"key": "gen_ai.usage.input_tokens",
                 "value": {"intValue": str(c["input"])}},
                {"key": "gen_ai.usage.output_tokens",
                 "value": {"intValue": str(c["output"])}}]
        if c["retry"]:
            attrs.append({"key": "averth.retry",
                          "value": {"stringValue": "timeout"}})
        spans.append({
            "traceId": tk["id"], "spanId": f"{ti}-{j}",
            "name": "llm.chat",
            "startTimeUnixNano": str(base + ti * 10_000_000_000 + j * 1_000_000_000),
            "endTimeUnixNano": str(base + ti * 10_000_000_000 + j * 1_000_000_000 + 500_000_000),
            "attributes": attrs,
            "status": {"code": "ERROR" if (tk["failed"] and
                                           j == len(tk["calls"]) - 1)
                       else "STATUS_CODE_OK"}})
with open(os.path.join(OUT, "otel.json"), "w") as f:
    json.dump({"spans": spans}, f)

n_calls = sum(len(t["calls"]) for t in tickets)
n_billed = sum(1 for t in tickets for c in t["calls"] if c["cost"] is not None)
n_measured = sum(1 for t in tickets for c in t["calls"]
                 if c["cost"] is None and c["usage"] is not None)
n_unknown = sum(1 for t in tickets for c in t["calls"]
                if c["cost"] is None and c["usage"] is None)
print(f"wrote {OUT}: {N_TICKETS} tickets, {n_calls} calls "
      f"(billed={n_billed} measured={n_measured} unknown={n_unknown} "
      f"failed_tickets={sum(1 for t in tickets if t['failed'])})")
