# POC NEW 24: SmolAgents GAIA (GPT-4o) — clean-run test, batch 3

Status: PASS (clean run). No one contacted, nothing sent, nothing posted,
no private data used. This is a clean-run diagnosis test only, not a
value pitch: does the upgraded Averth run by itself cleanly on a new
public workflow, or does it fail?

## Upgraded Averth used

- Repo: ~/workspace/averth, commit 071d0e1
  ("Fix wave 3: Claude dedupe max, outcome unknown, Haiku dated alias,
  zero-token guard"), price table v6 (verified 2026-10-22).
- This lane uses the jsonl importer only; the Claude, Langfuse, and
  OTel wave-3 fixes are not exercised here. The zero-token guard is not
  triggered either (this trace has model events).

## Workflow and source — a scaffold not used in batches 1 or 2

- Workflow: Hugging Face smolagents CodeAgent runs on GAIA questions,
  model gpt-4o, with planning turn, code-execution steps, and a
  final_answer() call per attempt.
- Source (traces): https://huggingface.co/datasets/smolagents/gaia-traces
  — file data/train-00000-of-00001.parquet, 1,204 rows, columns
  model_id, system_prompt, messages (list of content/role, 3 to 30
  messages per row). Every row ends with a user observation, never
  with an assistant message or a result record.
- Source (ground truth): https://huggingface.co/datasets/smolagents/GAIA-annotated
  — file 2023/validation/metadata.jsonl, 165 validation questions with
  task_id, Question, Level, Final answer. The gaia-benchmark/GAIA repo
  itself is gated (401 without an agreed account) and was NOT used;
  GAIA-annotated is its ungated mirror for the validation metadata.

## Sample and conversion, reproducible

- Question join, fixed before any outcome was inspected: the trace
  question is taken from message 0 after "Here is the task:", normalized
  (lowercase, whitespace collapsed), and must START WITH exactly one
  normalized validation Question. Trace questions carry an
  attached-file appendix after the question ("To solve the task above,
  you will have to use this attached file: ..."), which is why exact
  equality fails (only 53 of 1,204 rows match exactly) while prefix
  matching matches 71 rows uniquely. The appendix is dropped for the
  join; the question text itself is never edited.
- Sample rule, applied in file order, no outcome filtering: the first
  20 rows that (a) prefix-match a unique validation question,
  (b) have at least 1 assistant turn, (c) have a non-empty final-answer
  extraction. Result: trace rows 0-19, 20 distinct task_ids, levels
  L1 x7, L2 x11, L3 x2. First-20-in-file-order is reproducible, not
  claimed representative of GAIA as a whole.
- Final answer extraction: the last message's text after the literal
  marker "Last output from code snippet:". Verified on inspected
  traces that this is the final_answer() tool output, not a mid-run
  code print: the preceding assistant turn calls final_answer(...) with
  the same string.
- Grading (primary, conservative): normalized exact equality
  (lowercase, whitespace collapsed, surrounding quotes and one trailing
  period stripped) between the extracted final answer and the
  validation "Final answer". Result: 11 of 20 correct (55.0%).
  Secondary audit: 19 of 20 submitted answers CONTAIN the expected
  answer as a substring. The 8 strict-wrong-but-containing cases are
  sentence-length final_answer() calls (for example, expected "Fred",
  submitted "Fred did not give a gift."; expected "3", submitted "The
  ISBN-10 check digit for the Tropicos ID 100370510 is 3"). GAIA asks
  for answers in as few words as possible, so the strict label is kept
  as primary and the containing cases are NOT upgraded to correct.
  The one case wrong under both gradings is the fish-bag volume task
  (submitted a sentence about the paper, expected "0.1777").
  Whoever rolls up the 40 POCs must pick one grading and apply it
  consistently; mixing strict here with contains elsewhere would
  inflate this lane from 55% to 95%.
- End label: success = the graded outcome above. This is a JOINED
  label from validation ground truth, not a marker in the trace.
- Token limits, stated plainly: the dataset records NO per-call token
  counts, NO cache counts, and NO billed dollar costs. Per assistant
  turn, input tokens = chars of the system prompt plus all preceding
  messages, divided by 4; output tokens = chars of that assistant turn,
  divided by 4. This mirrors the chars/4 convention of earlier POCs and
  mirrors smolagents' real behaviour of re-sending accumulated memory
  each step, so input grows step to step. Every model dollar below is
  therefore vendor list prices applied to ESTIMATED tokens, and Averth
  says so itself ("token provenance unverified").
- Tool events: one per assistant turn immediately followed by an
  "Observation:" user message, named "code_execution" (56 events).
  The dataset does not name the tool per step (managed agents such as
  search_agent appear inside code text, not parsed), so tool spend is
  purely Averth's built-in per-call estimate, not a measured tool cost.
  The planning turn (followed by "Now proceed and carry out this
  plan.") gets no tool event.
- Retry events: one when an observation contains "Error" or
  "Traceback" (6 events). This is a LOWER BOUND; silent wrong turns
  are not counted. Dataset-wide, 77 of 2,822 observations carry such a
  marker.
- Converted events: 200 lines — 98 model, 56 tool, 6 retry, 20 start,
  20 end. Model tokens (estimated): input 562,249, output 26,841.
  Assistant turns per attempt: 2 to 9, total 98.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/convert.py

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/python -m averth.cli trace <events file> --format jsonl
--html <report.html> --agent smolagents-gaia-gpt4o

- CLI exit code: 0. No error, no traceback, no unknown-event
  rejection. HTML report written to
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/report.html.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run

- Attempts: 20
- Autonomous completions (graded correct, strict): 11 (55.0%)
- Failed attempts: 9 (45.0%)
- Retries: 6 — all "error observation"
- Total cost: $1.84
  - Priced (tokens x vendor prices; token provenance unverified):
    $1.67 — openai:gpt-4o at $2.50 input / $10.00 output per 1M.
    Independently checked: 562,249 x $2.50/1M = $1.4056, plus
    26,841 x $10.00/1M = $0.2684, sum $1.674, matches $1.67.
  - Vendor-supplied (billed): $0.00.
  - Estimated (built-in tool estimates): $0.17 (56 code_execution
    events).
- Fully loaded cost per successful outcome: $0.17
  (model terminal $0.05, retry path $0.10, tool calls $0.02,
  human review $0.00 at the assumed $70.20/hr rate, not measured).
- Failed runs: $1.02 (55% of spend, zero outcomes).
- Retry path: $1.13 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 31% of tokens on the terminal path.
- Context compounding: 3.7x input growth first-to-last step;
  context tax $0.79 (47% of model spend). This is the smolagents
  memory-replay shape (every step re-sends accumulated memory)
  showing up as dollars, but computed from chars/4 estimates, not
  from recorded token counts.
- Heavy tail: p50 $0.07 / p95 $0.18 / max $0.18 per attempt;
  top 5% consumed 10% of budget.
- Human escalations: 0. Reopened: 0.
- Cost basis printed by Averth: ESTIMATED, with the warning that
  $0.17 uses built-in tool estimates. No dollar here is a bill.

## Anomalies noted (do not hide them; none blocked the run)

1. Model-key double prefix on the first run (converter error, not an
   Averth bug): passing model "openai:gpt-4o" produced the unpriced key
   "openai:openai:gpt-4o" and all $0.81 fell back to estimated prices.
   Averth flagged the key as unpriced instead of pricing it silently.
   Fixed by emitting model "gpt-4o" with provider "openai" explicit;
   the rerun prices correctly at $1.67 model spend. Lesson for other
   converters: Averth keys are provider:model, so never put the
   provider inside the model field.
2. No recorded tokens, cache, or bills anywhere in this dataset, so
   "Priced" here means list prices x estimated tokens. Do not quote
   $1.84 as measured spend.
3. Traces end with a user observation; there is no native completion
   or result marker, so the end label is joined ground truth. Without
   the join, Averth would auto-end every attempt as failed.
4. Strict vs contains grading moves this lane from 55% to 95%.
   The strict figure is reported as primary; the rollup must not mix
   gradings across lanes.
5. Tool spend ($0.17) is a built-in estimate for an invented-uniform
   tool name; the real per-step tool mix (web search, file inspection,
   managed search agent) is not in the dataset and is not priced.
6. Retry count (6) is a lower bound from error-marker observations
   only; most failed attempts show no error marker at all.

## What this does NOT prove

- No billed cost, no recorded tokens, no cache data: every model
  dollar is a chars/4 estimate at list prices. This run proves Averth
  can ingest and report a new SmolAgents/GAIA trace set by itself,
  with exit 0, a complete report, and an honestly labelled cost basis.
  It does not prove an operator would use it repeatedly, act on a
  finding, or pay for it.
- No change was tested here. The retry finding (error observations)
  and the context-tax finding (memory replay) are report outputs, not
  tested fixes, and no saving is claimed.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/events.jsonl (200 lines)
- Sample list with submitted vs expected answers: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/sample.json
- Validation ground truth used: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/gaia_validation_metadata.json
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/report.html
- Averth text output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-24/averth-output.txt
