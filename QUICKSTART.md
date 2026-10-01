# agentpnl — 5-minute quickstart (pilot)

Meter one production agent for two weeks. Read-only. The meter runs inside
your environment; no prompts or customer data ever leave it.

## 1. Install (30 seconds)

```bash
pip install git+https://github.com/YOUR-ORG/agentpnl.git
```

## 2. Wrap your agent's attempt loop (3 minutes)

```python
from agentpnl import Tracker, ModelStep

t = Tracker("support-agent", budget_per_success=6.00)

# per resolved case:
a = t.start_attempt("case-12345", model="gpt-4.1")
a.step(ModelStep(in_tokens=8200, out_tokens=1400))   # model call
a.tool("zendesk_lookup", 0.004)                     # external tool/API cost
a.step(ModelStep(in_tokens=31000, out_tokens=900))  # context grows: metered
t.end_attempt("case-12345", success=True, human_min=4)  # reviewer time, if any
```

Record what you already have: model token counts, tool/API spend, retry
loops, human review minutes, and whether the case was accepted/resolved.
Failed runs, reopens, and escalations are first-class: end with
`success=False` or `reopened=True`.

## 3. Export the sanitized ledger (30 seconds)

```python
from agentpnl import policy as P
P.export_ledger(t, "agentpnl-ledger.json")
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
