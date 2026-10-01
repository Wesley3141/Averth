# agentpnl

The economic meter for enterprise agents. Instrument one agent, get its actual P&L.

## Installation

```bash
pip install git+https://github.com/Wesley3141/agentpnl.git
```

Optional extras:

```bash
pip install "agentpnl[langchain] @ git+https://github.com/Wesley3141/agentpnl.git"   # LangChain callback handler
pip install "agentpnl[openai] @ git+https://github.com/Wesley3141/agentpnl.git"        # OpenAI trace import
```

Requires Python 3.9+.

## Read-only posture

The meter makes no network calls and exfiltrates no data: it records
cost/token/timing metadata only; the sanitized ledger contains no prompts,
no completions, no tool payloads, and no customer data. The library has no
network dependencies in its core; extras pull in only what they need.

## Instrument

```python
from agentpnl import Tracker
from agentpnl.report import report_text

t = Tracker("support-resolution", budget_per_success=6.00)

t.start_attempt(case_id="T-00001")
t.log_model_call("anthropic", "claude-sonnet-4-5", 3200, 850)
t.log_tool_call("crm_lookup")
t.log_retry("confidence check failed", extra_model_cost=0.014)
t.log_escalation(4.5, "low confidence")
t.end_attempt(success=True, business_value=11.20)

print(report_text(t.pnl(), token_dashboard_per_success=0.03))
```

What it meters: model spend (per-provider pricing tables), tool calls, retries, and human review time, attributed to accepted business outcomes. Output: attempts, autonomous completions, reopen rate, escalation rate, fully-loaded cost per successful outcome, business value, net value, and budget breaches.

It implements the five cost layers (see `../research/agent-pnl/five-cost-layers.md`):
context compounding per step, external tool spend, yield ratio (terminal-path
tokens / total), heavy-tail isolation (p50/p95/max, top-5% budget share), and
per-model attribution plus loaded human-review cost.

The `budget_per_success` + `on_breach` hook is Phase-1 (built only after a
buyer confirms who owns that authority and will pay for it). The Phase-0
pilot is read-only: the customer runs the meter inside their own environment,
exports a sanitized ledger, and we replay hypothetical policies offline:

```python
from agentpnl import policy as P
P.export_ledger(t, "ledger.json")   # metadata only: no prompts, no customer data
ledger = P.load_ledger("ledger.json")
sim = P.simulate_policy(ledger, max_cost_per_attempt=6.00, yield_floor=0.50)
print(P.policy_text(sim))
# "Had policy X existed, 619 of 2000 runs would have been stopped,
#  exposing $1,094.91 (85% of total spend)."
```

Pitch: "No write access. No raw prompts or customer data leave your
environment." Business value in dollars is optional in V1 (see report.py):
cost per accepted outcome is objectively measurable; value often is not.

Run `python3 demo.py` for a simulated 2,000-ticket month across all five cost layers. The demo's punchline: the token dashboard says $0.20 per success; the fully loaded number is $0.82 (4.1x), with 4.7x context compounding across steps, 95% yield ratio, and the top 5% of attempts consuming 61% of the budget.

## LangChain integration

Zero-code instrumentation for LangChain agents. Three lines, no manual
logging calls: the handler opens and closes attempts and meters model calls,
tool use, and errors behind the scenes.

```python
from agentpnl import Tracker
from agentpnl.integrations.langchain import AgentPNLCallbackHandler

tracker = Tracker("support-agent", budget_per_success=6.00)
handler = AgentPNLCallbackHandler(tracker)
agent.invoke(..., config={"callbacks": [handler]})
```

## Trace importers

Already have traces? Import them instead of instrumenting. Supported formats:
OpenTelemetry (`otel`), LangSmith (`langsmith`), and newline-delimited JSON
(`jsonl`). Each importer parses a trace file into a sanitized cost ledger
(same schema as `policy.export_ledger`).

```python
from agentpnl.importers import jsonl, common

ledger = jsonl.load_jsonl("run-2026-09.json")     # cost metadata only
tracker = common.tracker_from_ledger(ledger)      # back into a Tracker
```

OpenTelemetry and LangSmith work the same way via `otel.load_otel` and
`langsmith.load_langsmith`. Imported ledgers contain no prompts, completions,
or customer data.

## CLI

Build a P&L report from a trace file without writing code:

```bash
agentpnl trace run-2026-09.json --format jsonl --html report.html
agentpnl trace trace.otel.json --format otel --agent support-agent \
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
