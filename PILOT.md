# Customer pilot: evidence required for an accurate Averth report

Averth can measure the cost structure of recorded agent runs. A customer-facing
cost **per accepted outcome** needs the customer's own acceptance decision for
each run. A trace that ended without an error is not proof that its result was
useful, accepted, or never reopened.

## Ask for one workflow and one representative period

Request these inputs before promising a dollar result:

1. **Run records:** a JSONL, OpenTelemetry, or LangSmith export with stable
   run/case IDs, model names, token counts (including cache reads if known),
   tool calls, retries, timestamps, and attempt boundaries. Generic process
   documents can explain the workflow, but cannot substitute for run records.
2. **Outcome labels:** a case-ID join to the customer's system of record with
   accepted/resolved status, review or escalation, and reopen status. Agree
   in writing on what counts as one outcome and the time window for reopens.
3. **Actual cost inputs:** model billing or contracted prices for the period,
   paid tool/API fees, and the customer's loaded hourly rate and measured
   minutes for human review. Mark absent inputs as estimates or unknown.
4. **Comparison baseline:** the current monthly case volume and existing
   spend or dashboard view. Business value in dollars is optional unless the
   customer has a defensible value or avoided-work baseline.

Before sharing a ledger, the customer should inspect and redact case IDs,
tool names, and retry/escalation reasons. Those caller-provided strings are
exported verbatim; prompts, completions, and tool payloads are not recorded.

## What we return

- A report for the agreed workflow and period, with run count, labeled
  outcomes, model/tool/human costs, cost per accepted outcome, failed-run and
  expensive-tail concentration, and the top observed retry reasons.
- A short data-quality note identifying measured costs, estimates, missing
  token usage, inferred outcomes, pricing-table date, and any missing joins.
- One proposed change to test, with the affected run IDs and a **prospective**
  measurement plan. A historical policy screen identifies runs to inspect; it
  does not claim savings or predict lost outcomes.

Reconcile model spend against the customer's bill before presenting precise
dollar savings. If outcome labels or billing data are absent, return the cost
structure and the missing-data list, and withhold a claim about accepted
outcome economics or realized savings.
