# Averth

The economic meter for enterprise agents. Instrument one agent, get its actual P&L.

## Installation

```bash
pip install git+https://github.com/Wesley3141/Averth.git
```

Optional extras:

```bash
pip install "averth[langchain] @ git+https://github.com/Wesley3141/Averth.git"   # LangChain callback handler
pip install "averth[openai] @ git+https://github.com/Wesley3141/Averth.git"        # OpenAI trace import
```

Requires Python 3.9+.

## Read-only posture

The meter makes no network calls and exfiltrates no data: it records
cost/token/timing metadata only; the sanitized ledger contains no prompts,
no completions, no tool payloads, and no customer data. The library has no
network dependencies in its core; extras pull in only what they need.

## Instrument

```python
from averth import Tracker
from averth.report import report_text

t = Tracker("support-resolution", budget_per_success=6.00)

t.start_attempt(case_id="T-00001")
t.log_model_call("anthropic", "claude-sonnet-4-5", 3200, 850)
t.log_tool_call("crm_lookup")
t.log_retry("confidence check failed", extra_model_cost=0.014)
t.log_escalation(4.5, "low confidence")
t.end_attempt(success=True, business_value=11.20)

print(report_text(t.pnl(), token_dashboard_per_success=0.03))
```

What it meters: model spend (per-provider pricing tables, with prompt-cache
reads priced at a documented 10% discount via `cached_input_tokens`),
tool calls, retries (branch-scoped under concurrency via `branch=`), and
human review time, attributed to accepted business outcomes. Output: attempts,
autonomous completions, reopen rate, escalation rate, fully-loaded cost per
successful outcome (terminal model + retry-path + tools + human, shown as
separate lines), context tax in dollars, cache savings, failed-run and
reopened waste lenses, top retry reasons, costliest attempts, business value,
net value, and budget breaches.

It implements the five cost layers (see `../research/agent-pnl/five-cost-layers.md`):
context compounding per step, external tool spend, yield ratio (terminal-path
tokens / total), heavy-tail isolation (p50/p95/max, top-5% budget share), and
per-model attribution plus loaded human-review cost.

The `budget_per_success` + `on_breach` hook is Phase-1 (built only after a
buyer confirms who owns that authority and will pay for it). The Phase-0
pilot is read-only: the customer runs the meter inside their own environment,
exports a sanitized ledger, and we replay hypothetical policies offline:

```python
from averth import policy as P
P.export_ledger(t, "ledger.json")   # metadata only: no prompts, no customer data
ledger = P.load_ledger("ledger.json")
sim = P.simulate_policy(ledger, max_cost_per_attempt=6.00, yield_floor=0.50)
print(P.policy_text(sim))
# "Would have stopped 1020 of 2000 runs: 426 failed (pure savings $297.18)
#  and 594 that went on to succeed (collateral $897.79 — good outcomes this
#  policy would have destroyed)."
```

Pitch: "No write access. No raw prompts or customer data leave your
environment." Business value in dollars is optional in V1 (see report.py):
cost per accepted outcome is objectively measurable; value often is not.

Run `python3 demo.py` for a simulated 2,000-ticket month across all five cost layers. The demo's punchline: the token dashboard says $0.20 per success; the fully loaded number is $0.82 (4.1x), with 4.7x context compounding across steps, a 6% token yield ratio (failed runs and retry paths burn the rest), and the top 5% of attempts consuming 61% of the budget.

Yield counts failed attempts as waste: a failed attempt has no terminal path,
so its tokens are 100% waste by definition. A high success rate can still
mean a single-digit yield when the failures are the expensive runs.

## Adversarial simulation

`averth simulate` generates a seeded hostile workload — quick resolutions,
retry storms, escalations, clean failures, reopened tickets, and 2% runaways
that burn most of the budget — with 1.15-1.6x context growth, multi-model
routing (a 70% cache-hit triage router), and parallel 3-branch fan-out:

```bash
averth simulate --attempts 2000 --seed 42 --html sim.html
averth simulate --attempts 500 --seed 7 --jsonl sim.jsonl
averth trace --format jsonl sim.jsonl   # reproduces the identical P&L
```

Same seed always produces the identical P&L to the cent. The JSONL round-trip
through the real importer is asserted in the test suite
(`tests/test_stress.py`). Use it to stress the meter before trusting it on a
customer trace: 20k attempts meter in about a second.

## Known limits (honest, not marketing)

- Prompt-cache pricing uses a documented 10% cache-read discount
  (Anthropic's published rate), overridable via `Tracker(cache_read_discount=...)`.
  It is flagged as an assumption, never presented as the provider's invoice figure.
- `extra_model_cost` on a retry is for spend NOT otherwise logged as a step;
  logging the same spend twice would double-count.
- Waste figures are lenses, not additive partitions: a failed attempt's
  retry-path spend appears in both the failed-runs and retry-path lines.
- The JSONL importer's strict schema rejects malformed events (including
  `cached_input_tokens > input_tokens`); the live Tracker API clamps or
  ignores instead of raising, because it must never break an agent run.
- Pre-hardening ledgers load without crashing; new fields degrade to
  documented defaults (retry-path cost unknown, context tax $0).

## LangChain integration

Zero-code instrumentation for LangChain agents. Three lines, no manual
logging calls: the handler opens and closes attempts and meters model calls,
tool use, and errors behind the scenes.

```python
from averth import Tracker
from averth.integrations.langchain import AverthCallbackHandler

tracker = Tracker("support-agent", budget_per_success=6.00)
handler = AverthCallbackHandler(tracker)
agent.invoke(..., config={"callbacks": [handler]})
```

## Trace importers

Already have traces? Import them instead of instrumenting. Supported formats:
OpenTelemetry (`otel`), LangSmith (`langsmith`), and newline-delimited JSON
(`jsonl`). Each importer parses a trace file into a sanitized cost ledger
(same schema as `policy.export_ledger`).

```python
from averth.importers import jsonl, common

ledger = jsonl.load_jsonl("run-2026-09.json")     # cost metadata only
tracker = common.tracker_from_ledger(ledger)      # back into a Tracker
```

OpenTelemetry and LangSmith work the same way via `otel.load_otel` and
`langsmith.load_langsmith`. Imported ledgers contain no prompts, completions,
or customer data.

## CLI

Build a P&L report from a trace file without writing code:

```bash
averth trace run-2026-09.json --format jsonl --html report.html
averth trace trace.otel.json --format otel --agent support-agent \
    --policy-cap 6.00 --policy-yield 0.50
```

`--format` is one of `otel`, `langsmith`, `jsonl`. The text report prints to
stdout; `--html` writes a one-page HTML report (defaults to
`<inputfile>.html` in the current directory). `--policy-cap` and
`--policy-yield` replay a hypothetical offline policy and print what it would
have stopped.

## License

MIT. See `LICENSE`.

This is the pilot instrument for the agent-P&L thesis: read-only telemetry in, P&L report out. See `~/workspace/research/agent-pnl/PLAN.md`.
