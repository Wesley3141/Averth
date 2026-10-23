# POC new-04: Semantic Kernel agent workflow — clean-run test

## Verdict: PASS (converted JSONL run, exit 0)

This is a clean-run test only, not a value pitch and not proof of operator value.
Averth ran by itself on the converted file with no crash and no invented
model price. It did NOT natively ingest a Semantic Kernel trace: Averth has
no Semantic Kernel importer, so manual conversion to its JSONL event schema
was required first. That scope limit is part of the verdict.

## Workflow and source

- Workflow: Semantic Kernel (.NET) function-calling workflow with
  `ToolCallBehavior.AutoInvokeKernelFunctions`. Prompt: "What time it is?"
  1st LLM call requests the TimePlugin GetCurrentTime function, the tool
  runs and returns the time, 2nd LLM call produces the final answer.
- Source (public, read in full): Systenics, "Function calling using
  Semantic Kernel", 2024-03-18,
  https://systenics.ai/blog/2024-03-18-function-calling-with-semantic-kernel/
- The article describes the model only as gpt-4 function calling and shows
  `AddOpenAIChatCompletion("<Model-Name>", "<API-Key>")` with the model name
  as a placeholder. No specific model version is named, so no GPT-4o price
  was assumed. The conversion uses model "gpt-4" exactly as described.

## Published numbers used, verbatim from the source

- 1st LLM call: prompt tokens 54, completion tokens 13, total 67.
- Tool: 1 request, TimePlugin-GetCurrentTime({}), succeeded,
  result 18-03-2024 03:55:06.
- 2nd LLM call: prompt tokens 90, completion tokens 21, total 111.
- Final response: "The current time is 03:55:06 UTC on March 18, 2024."
- Totals: 144 input tokens, 34 output tokens, 178 tokens, 2 model calls,
  1 tool call, 0 retries, 0 failures in the published run.

## Conversion method

Manual, mechanical, no tokens invented and no split invented:

- `poc-new-04-semantic-kernel-events.jsonl` (same directory):
  start, model (gpt-4, 54 in / 13 out), tool (TimePlugin-GetCurrentTime,
  no cost passed, so Averth's built-in default applies), model (gpt-4,
  90 in / 21 out), end (success true, because the published final answer
  is the correct current time).
- No retries were added: the published run has none. No acceptance label
  beyond the published correct final answer was claimed.

## Averth run (upgraded Averth, commit fd84a0f)

Command, run from ~/workspace/averth:

    PYTHONPATH=. python3 -m averth.cli trace \
      ~/workspace/goals/agent-p-l-validation/files/poc-new-04-semantic-kernel-events.jsonl \
      --format jsonl \
      --html ~/workspace/goals/agent-p-l-validation/files/poc-new-04-semantic-kernel.html

- CLI exit code: 0. No error, no crash.
- Price table: v5 (verified 2026-10-22, reported 1 day old at run time).
- Attempts: 1. Autonomous completions: 1 (100.0%). Retries: 0.
  Human escalations: 0. Failed runs: $0.00 (0%).
- Total cost: $0.002246.
  - Model/API (terminal): $0.000246, all ESTIMATED (fallback prices).
  - Tool calls: $0.002, built-in per-call estimate for
    TimePlugin-GetCurrentTime (not in the tool price table, default used).
  - Retry path: $0.00. Human review: $0.00.
  - Cost per successful outcome: $0.002246 (cost per completed run here;
    the only acceptance evidence is the published correct final answer).
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices): $0.00. Vendor-supplied (billed): $0.00.
  Estimated (fallback prices): $0.002246. Unpriced model flagged by name:
  openai:gpt-4. Averth's header states: "Do not quote this report as
  measured spend or as a bill."
- Context growth: 1.7x input growth first-to-last step (90 / 54).
  Context tax: $0.00 (0% of model spend).
- Yield: 100% of tokens on the terminal path (0% burned on retries,
  because the published run has none).
- Heavy tail: p50 / p95 / max all $0.002246 (n=1, so these are trivial).
- Averth findings line: "No material findings: spend is clean across
  all five layers."

## What PASS means here, and what it does not mean

PASS means: the upgraded CLI accepts the converted file, exits 0,
does not crash on an unpriced model, and flags the fallback estimate
and the tool default estimate by name instead of presenting them as
a bill. The old "Measured" label trap does not appear: the priced
bucket is $0.00 and the header says ESTIMATED.

PASS does not mean:

- Native Semantic Kernel ingestion works. It does not exist; conversion
  was manual. A real Semantic Kernel / MLflow / OpenTelemetry trace
  file was not found in public search (only code samples, docs, and
  illustrative traces), so this lane could not test a native SK trace.
- The dollars are a bill. They are not. Model spend is a fallback
  estimate because the article names no specific model version, and
  89% of the total ($0.002 of $0.002246) is the built-in tool default,
  not a measured tool cost.
- This proves operator value. It does not. n=1, a clean run, no waste,
  no retries, no failures, and Averth itself reports no material
  findings. A clean-run PASS is not a value POC.

## Files

- Events: poc-new-04-semantic-kernel-events.jsonl (same directory)
- HTML report: poc-new-04-semantic-kernel.html (same directory)
- Upgraded Averth commit verified: fd84a0f
