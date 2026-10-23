# POC NEW 44: SmolAgents GAIA, next slice (GPT-4o) — clean-run test, batch 4

Status: PASS (clean run). No one contacted, nothing sent, nothing posted,
no private data used. This is a clean-run diagnosis test only, not a
value pitch: does the upgraded Averth run by itself cleanly on a new
public workflow slice, or does it fail?

## Upgraded Averth used

- Repo: ~/workspace/averth, commit fafab07
  ("Fix Langfuse cached alias: input_cached_tokens"), price table v6
  (verified 2026-10-22). The Averth output header confirms v6.
- This lane uses the jsonl importer only; the Claude, Langfuse, and
  OTel wave-3/4 fixes are not exercised here. The zero-token guard is
  not triggered (this trace has model events).

## Workflow and source — same scaffold as poc-new-24, disjoint slice

- Workflow: Hugging Face smolagents CodeAgent runs on GAIA questions,
  model gpt-4o, with planning turn, code-execution steps, and a
  final_answer() call per attempt.
- Source (traces): https://huggingface.co/datasets/smolagents/gaia-traces
  — file data/train-00000-of-00001.parquet, 1,204 rows, columns
  model_id, system_prompt, messages. Every row ends with a user
  observation, never with an assistant message or a result record.
- Source (ground truth): https://huggingface.co/datasets/smolagents/GAIA-annotated
  — file 2023/validation/metadata.jsonl, 165 validation questions with
  task_id, Question, Level, Final answer. The gaia-benchmark/GAIA repo
  itself is gated (401 without an agreed account) and was NOT used;
  GAIA-annotated is its ungated mirror for the validation metadata.

## Sample and conversion, reproducible — and the overlap check

- Question join, fixed before any outcome was inspected, identical to
  poc-new-24: the trace question is taken from message 0 after
  "Here is the task:", normalized (lowercase, whitespace collapsed),
  and must START WITH exactly one normalized validation Question.
  Trace questions carry an attached-file appendix after the question
  ("To solve the task above, you will have to use this attached file:
  ..."), which is why exact equality fails while prefix matching
  matches. The appendix is dropped for the join; the question text
  itself is never edited.
- Qualifying rows, whole file: 71 rows in file order meet (a) unique
  prefix match, (b) at least 1 assistant turn, (c) non-empty
  final-answer extraction.
- Sample rule, applied in file order, no outcome filtering: SKIP the
  first 20 qualifying rows, TAKE the next 20. Result: trace rows
  20-39, 20 distinct task_ids, levels L1 x9, L2 x10, L3 x1.
  First-20-in-file-order is reproducible, not claimed representative
  of GAIA as a whole.
- Overlap check, asserted programmatically in the converter, not
  eyeballed: the first 20 qualifying rows reproduce poc-new-24's
  sample exactly (same trace rows 0-19, same task_ids), and the
  next-20 sample has ZERO task_id overlap and ZERO trace_row overlap
  with poc-new-24/sample.json. This lane is disjoint from poc-new-24.
- Final answer extraction: the last message's text after the literal
  marker "Last output from code snippet:". Verified on inspected
  traces in poc-new-24 that this is the final_answer() tool output,
  not a mid-run code print.
- Grading (primary, conservative, same as poc-new-24): normalized
  exact equality (lowercase, whitespace collapsed, surrounding quotes
  and one trailing period stripped) between the extracted final answer
  and the validation "Final answer". Result: 13 of 20 correct (65.0%).
  Secondary audit only: 5 more submitted answers CONTAIN the expected
  answer as a substring, and 2 are wrong under both gradings, so
  contains-grading would give 18 of 20 (90.0%). The containing cases
  are NOT upgraded to correct, and the rollup must pick one grading
  and apply it consistently; mixing strict here with contains elsewhere
  would inflate this lane from 65% to 90%.
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
  "Observation:" user message, named "code_execution" (64 events).
  The dataset does not name the tool per step, so tool spend is purely
  Averth's built-in per-call estimate, not a measured tool cost. The
  planning turn (followed by "Now proceed and carry out this plan.")
  gets no tool event.
- Retry events: one when an observation contains "Error" or
  "Traceback" (7 events). This is a LOWER BOUND; silent wrong turns
  are not counted.
- Converted events: 225 lines — 114 model, 64 tool, 7 retry, 20 start,
  20 end. Model tokens (estimated): input 1,120,667, output 28,490.
  Assistant turns per attempt: 3 to 10, total 114. All 20 rows report
  model_id gpt-4o.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/convert.py
  (contains the skip-first-20 / take-next-20 logic and the overlap
  assertions; it fails loudly if the first 20 do not reproduce
  poc-new-24 or if any overlap is found).

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/python -m averth.cli trace <events file> --format jsonl
--html <report.html> --agent smolagents-gaia-gpt4o-next

- CLI exit code: 0, verified on a separate re-run (not just the tee
  pipeline). No error, no traceback, no unknown-event rejection. HTML
  report written to
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/report.html.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run

- Attempts: 20
- Autonomous completions (graded correct, strict): 13 (65.0%)
- Failed attempts: 7 (35.0%)
- Retries: 7 — all "error observation"
- Total cost: $3.28
  - Priced (tokens x vendor prices; token provenance unverified):
    $3.09 — openai:gpt-4o at $2.50 input / $10.00 output per 1M.
    Independently checked: 1,120,667 x $2.50/1M = $2.8017, plus
    28,490 x $10.00/1M = $0.2849, sum $3.0866, matches $3.09.
  - Vendor-supplied (billed): $0.00.
  - Estimated (built-in tool estimates): $0.19 (64 code_execution
    events).
- Fully loaded cost per successful outcome: $0.25
  (model terminal $0.11, retry path $0.13, tool calls $0.01,
  human review $0.00 at the assumed $70.20/hr rate, not measured).
- Failed runs: $1.26 (38% of spend, zero outcomes).
- Retry path: $1.66 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 45% of tokens on the terminal path.
- Context compounding: 6.2x input growth first-to-last step;
  context tax $2.13 (69% of model spend). This is the smolagents
  memory-replay shape (every step re-sends accumulated memory)
  showing up as dollars, but computed from chars/4 estimates, not
  from recorded token counts.
- Heavy tail: p50 $0.10 / p95 $0.50 / max $0.55 per attempt;
  top 5% consumed 17% of budget.
- Human escalations: 0. Reopened: 0.
- Cost basis printed by Averth: ESTIMATED, with the warning that
  $0.19 uses built-in tool estimates. No dollar here is a bill.

## Comparison with poc-new-24 (same scaffold, disjoint slice)

- Attempts 20 vs 20; strict completions 13 (65.0%) vs 11 (55.0%);
  contains-grading 18 (90.0%) vs 19 (95.0%) — the gap between strict
  and contains is a grading-formatting effect in both slices, not a
  capability difference, and is why strict is kept primary in both.
- Total $3.28 vs $1.84: this slice has more turns (114 vs 98) and
  roughly double the estimated input tokens (1,120,667 vs 562,249),
  so the higher total is a token-volume difference, not a price
  difference (same gpt-4o list prices, same converter rules).
- Context growth 6.2x vs 3.7x; context tax $2.13 (69% of model spend)
  vs $0.79 (47%); yield 45% vs 31%; retries 7 vs 6.

## Anomalies noted (do not hide them; none blocked the run)

1. No recorded tokens, cache, or bills anywhere in this dataset, so
   "Priced" here means list prices x estimated tokens. Do not quote
   $3.28 as measured spend.
2. Traces end with a user observation; there is no native completion
   or result marker, so the end label is joined ground truth. Without
   the join, Averth would auto-end every attempt as failed.
3. Strict vs contains grading moves this lane from 65% to 90%.
   The strict figure is reported as primary; the rollup must not mix
   gradings across lanes.
4. Strict grading penalizes formatting, not just correctness, in
   this slice: "b,e" vs expected "b, e" (comma spacing), "*A
   Nightmare on Elm Street*" vs expected without asterisks, and
   "corn starch, ..." vs expected "cornstarch, ..." are all counted
   wrong under strict grading. Two of the seven strict failures are
   wrong under both gradings; the other five are contains-cases.
5. Tool spend ($0.19) is a built-in estimate for an invented-uniform
   tool name; the real per-step tool mix is not in the dataset and
   is not priced.
6. Retry count (7) is a lower bound from error-marker observations
   only; most failed attempts show no error marker at all.
7. No "-$0" priced-bucket artifact in this run's output, and no
   "Measured" label appears. Model-key double prefix (the poc-new-24
   first-run error) did not recur: model "gpt-4o" with provider
   "openai" prices correctly.

## What this does NOT prove

- No billed cost, no recorded tokens, no cache data: every model
  dollar is a chars/4 estimate at list prices. This run proves Averth
  can ingest and report a new, disjoint SmolAgents/GAIA trace slice
  by itself, with exit 0, a complete report, and an honestly labelled
  cost basis. It does not prove an operator would use it repeatedly,
  act on a finding, or pay for it.
- No change was tested here. The retry finding (error observations)
  and the context-tax finding (memory replay) are report outputs, not
  tested fixes, and no saving is claimed.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/events.jsonl (225 lines)
- Sample list with submitted vs expected answers: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/sample.json
- Validation ground truth used (copy of poc-new-24's): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/gaia_validation_metadata.json
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/report.html
- Averth text output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-44/averth-output.txt
