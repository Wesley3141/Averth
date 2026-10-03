# averth: 5-minute quickstart (pilot)

Meter one production agent for two weeks. Read-only. The meter runs inside
your environment and records cost/token/timing metadata only. It makes no
network calls and exfiltrates no data: the sanitized ledger contains no
prompts, no completions, and no tool payloads. (Caller-provided free text —
case IDs, tool names, retry/escalation reasons — is exported verbatim, so
redact anything sensitive before the ledger leaves your environment.)

## 1. Install (30 seconds)

```bash
pip install git+https://github.com/Wesley3141/Averth.git
```

Optional extras:

```bash
pip install "averth[langchain] @ git+https://github.com/Wesley3141/Averth.git"   # LangChain callback handler
pip install "averth[openai] @ git+https://github.com/Wesley3141/Averth.git"        # OpenAI trace import
```

## 2. Instrument your agent's attempt loop (3 minutes)

Use the Tracker directly around each resolved case:

```python
from averth import Tracker

# budget_per_success arms a post-hoc hook: end_attempt() raises BudgetBreach
# (or calls your on_breach callback) when a single attempt costs more than
# this. The attempt is recorded before the raise, so no data is lost — but
# plan for the exception in your loop, or pass on_breach= to handle it
# without raising.
t = Tracker("support-agent", budget_per_success=6.00,
            on_breach=lambda attempt, breach: print("over budget:", breach))

# per resolved case:
t.start_attempt(case_id="case-12345")
t.log_model_call("openai", "gpt-5.6-mini", 8200, 1400)  # provider, model, in/out tokens
t.log_tool_call("zendesk_lookup", 0.004)               # external tool/API cost
t.log_model_call("openai", "gpt-5.6-mini", 31000, 900) # context growth is metered
t.log_retry("confidence check failed")                 # marks subsequent tokens as waste-path
t.log_escalation(4.5, "low confidence")                # human reviewer minutes
t.end_attempt(success=True, business_value=11.20)      # reopened=True if it reopens
```

Record what you already have: model token counts, tool/API spend, retry
loops, human review minutes, and whether the case was accepted/resolved.
Failed runs, reopens, and escalations are first-class: end with
`success=False` or `reopened=True`.

On LangChain, model calls, tool use, and errors are captured with three
lines, no manual calls:

```python
from averth.integrations.langchain import AverthCallbackHandler

handler = AverthCallbackHandler(tracker)
agent.invoke(..., config={"callbacks": [handler]})
```

Scope note: the handler meters what the framework exposes — model token
counts, tool calls (counted, and costed at documented estimates unless you
log explicit costs), and chain errors. It cannot see business value, human
review minutes, retry costs, or reopened flags; for fully loaded cost per
accepted outcome on those dimensions, use the manual API above alongside
the handler.

Prefer existing traces? Import one instead of instrumenting:

```bash
averth trace run-2026-09.json --format jsonl --html report.html
```

`--format` also accepts `otel` and `langsmith`.

## 3. Export the sanitized ledger (30 seconds)

```python
from averth import policy as P
P.export_ledger(t, "averth-ledger.json")
```

The ledger is cost metadata only: per-attempt tokens, tool spend, timings,
success flags. No prompts, no completions, no payloads. (Case IDs, tool
names, and retry/escalation reasons are exported verbatim — redact anything
sensitive before sharing.)

## 4. Send us the ledger

Email the JSON to wesleyd3141@gmail.com. We return within 48 hours:

- fully loaded cost per accepted outcome (model + tools + retries + human review)
- yield ratio and tail concentration (which % of runs burn which % of budget)
- the offline policy replay: "had policy X existed, these N runs would have
  been stopped, exposing $Y of spend"

That is the whole pilot. Two weeks, one workflow, read-only, free.
