# averth: 5-minute quickstart (pilot)

Meter one production agent for two weeks. Read-only. The meter runs inside
your environment and records cost/token/timing metadata only. It makes no
network calls and exfiltrates no data: the sanitized ledger contains no
prompts, no completions, no tool payloads, and no customer data.

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

t = Tracker("support-agent", budget_per_success=6.00)

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

On LangChain, the same data is captured with three lines, no manual calls:

```python
from averth.integrations.langchain import AverthCallbackHandler

handler = AverthCallbackHandler(tracker)
agent.invoke(..., config={"callbacks": [handler]})
```

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
success flags. No prompts, no completions, no payloads, no customer data.

## 4. Send us the ledger

Email the JSON to the pilot address. We return within 48 hours:

- fully loaded cost per accepted outcome (model + tools + retries + human review)
- yield ratio and tail concentration (which % of runs burn which % of budget)
- the offline policy replay: "had policy X existed, these N runs would have
  been stopped, exposing $Y of spend"

That is the whole pilot. Two weeks, one workflow, read-only, free.
