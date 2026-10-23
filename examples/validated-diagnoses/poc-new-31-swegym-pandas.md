# POC-new-31: SWE-Gym pandas (OpenHands, GPT-4o) — full main run

## Verdict: PASS (clean-run diagnosis only, not a value POC)

No one contacted, nothing sent, nothing posted, no private data used.
Averth: `~/workspace/averth` at commit `fafab07`, price table v6
(verified in this run: `averth pricing` exits 0, 18 models, 8 tools, fresh).
CLI exit 0 on all three runs below, no crash.

## Source

- Dataset: `SWE-Gym/OpenHands-Sampled-Trajectories`, split `train.raw`,
  6,055 rows, 3 parquet shards.
  Dataset page: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
- Fields used: `instance_id`, `run_id`, `resolved`, `messages`
  (system / user / assistant-with-tool_calls / tool-observation),
  cross-checked against `test_result.report.resolved`.
- Pandas rows in the dataset: 1,044 rows, 737 distinct issues,
  70 resolved (6.7% of pandas rows). All pandas rows are
  GPT-4o-2024-08-06 OpenHands runs except 5 Claude-3.5-Sonnet rows.
- Overlap: earlier lanes used different dataset families for pandas-adjacent
  work (poc-new-11/12 used tarsur385 SWE-bench Verified trajectories;
  poc-new-09 used nebius SWE-rebench Qwen trajectories). No trajectory
  (instance_id + run_id) in this lane was used by an earlier lane; within
  this lane every case_id (instance_id + shard + row index) is unique.

## The slice problem, stated before the numbers

The lane brief asked for "the first 20 pandas rows in file order".
I ran that slice literally, and it is not a usable pandas diagnosis:

- **Slice A, literal first 20 pandas rows in global file order**
  (shard 0 rows 224-1143): 20 attempts, 0 resolved, $8.67 total,
  342 model events, 334 tool events, 3 retries, context 16.4x,
  context tax $6.90. It is 5 distinct issues repeated across small
  temperature pilot runs (t02-t05, maxiter 30), all unresolved.
- **Slice B, systematic main-run slice** (main run, every 37th row,
  indices 0, 37, ..., 703; 20 rows, step chosen from the row count
  737//20, not from any outcome): 20 attempts, 0 resolved, $27.28 total,
  581 model events, 533 tool events, 42 retries, context 22.6x,
  context tax $23.83.

Both are 0/20, and that is not cherry-picking in reverse: file order in
this dataset puts unresolved rows first. The first resolved row of the
main run is at main-run index 152; the first 100 main-run rows are
0 resolved. Any "first 20" slice for pandas is 0/20 by construction,
so quoting 0% as a pandas solve rate would be an ordering artifact.
The systematic slice landing 0/20 is also plausible on its own:
at the true 7.6% base rate, P(0/20) is about 0.20.

**Primary result below is therefore the full main run, all 737 rows,
outcome-blind (no row excluded for its outcome).** The two 20-row
slices are kept as an ordering-bias audit, not as the diagnosis.
The parent rollup should count this lane once, as the full-run
diagnosis, not as three POCs.

## Primary slice: full main run

- Run: `gpt-4o-2024-08-06_maxiter_50_N_v2.1-no-hint-train-t1-run_1`,
  the largest pandas run_id group (737 rows). The whole run sits in
  shard 2; the resolved label agrees with `test_result.report.resolved`
  on all 737 rows (0 mismatches, checked).
- Attempts: 737. Resolved (dataset's own label): 56 (7.6%).
  Failed: 681.

## Conversion (mechanical, no tokens or outcomes invented)

Script: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-31/convert.py`
Events (full run): `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-31/events-full-main.jsonl`
(38,858 events). Sample list:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-31/sample-full-main.json`.
20-row slice events: `events-literal.jsonl` (slice A),
`events.jsonl` (slice B); sample list: `sample.json`.

Rules, identical for every row:

1. One model event per assistant message: model `gpt-4o-2024-08-06`,
   provider `openai` explicit. Passing `openai:gpt-4o-2024-08-06` as
   the model name would double-prefix to an unpriced key (the
   poc-new-24 catch); the explicit provider avoids it, and Averth
   prices it at the v6 list rate $2.50 input / $10.00 output per 1M.
2. Tokens are chars/4 ESTIMATES from real text, not recorded usage:
   the dataset records no per-call tokens, no cache counts, and no
   billed costs. input_tokens = chars of all preceding messages
   (system prompt, user issue, tool observations, assistant text,
   and serialised tool-call arguments) // 4; output_tokens =
   max(1, (assistant text chars + tool-call arguments JSON chars) // 4).
   Assistant turns in this dataset are mostly tool calls with empty
   text, so output tokens come from the tool-call arguments; counting
   only the empty text would have priced output at ~0 and understated
   spend.
3. One tool event per tool_call, named by the function name, except
   `finish`, which is a termination marker with no tool observation
   and no execution cost and is excluded. Tool counts (full run):
   str_replace_editor 12,987, execute_bash 4,263, view 1, create_script 1.
   Tool spend is Averth's built-in $0.002 default per call, flagged as
   an estimate, never a bill.
4. One retry event before the next model call when a tool observation
   contains `Traceback (most recent call last)`. This is a
   recorded-error signal, not an invented label. Two limits travel
   with it: silent failures are missed (lower bound), and
   reproduction tracebacks (the agent deliberately running a failing
   script to reproduce the bug) are also counted, so the retry count
   is not a pure redo count.
5. One end event per attempt: success = the dataset's own `resolved`
   field. No aggregate was converted into events.

## Averth run (full main run)

Command (from `~/workspace/averth`):

```
.venv/bin/python -m averth.cli trace \
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-31/events-full-main.jsonl \
  --format jsonl \
  --html ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-31/report-full-main.html \
  --agent "SWE-Gym pandas (OpenHands GPT-4o)" --anomaly
```

- CLI exit code: 0. HTML report: `report-full-main.html`
  in the same hidden_files directory. CLI output:
  `averth-output-full-main.txt`.
- Total: **$824.43, cost basis ESTIMATED** as printed by Averth.
  Priced (tokens x vendor prices, token provenance unverified):
  $789.92. Vendor-supplied (billed): $0.00. Estimated (fallback
  prices, here entirely built-in tool estimates): $34.50.
  In plain terms: $789.92 is list prices applied to chars/4
  estimated tokens, not recorded usage and not a bill. Averth's
  own COST BASIS banner says the same thing; do not quote $824.43
  as what anyone was charged.
- Independent recount from the events file: 18,895 model events,
  303,299,918 input tokens, 3,167,509 output tokens
  (303,299,918 x $2.50 + 3,167,509 x $10.00, per 1M = $789.92);
  17,252 tool events x $0.002 = $34.50; sum $824.43. Matches Averth.
- Attempts: 737. Resolved: 56 (7.6%). Failed: 681.
- Retries: 1,237, all with reason `traceback`.
- Cost per successful outcome, fully loaded: **$14.72**
  (model terminal $0.46, retry path $13.65, tool calls $0.62,
  human review $0.00 at the assumed $70.20/hr loaded rate).
- Failed runs: $785.21 (95% of spend, zero outcomes).
  Retry path (overlapping lens, not additive): $764.12.
- Yield: 3% of tokens on the terminal path
  (97% burned on retries and failed runs).
- Context compounding: 21.4x input growth first-to-last step;
  context tax $706.87 (89% of model spend).
- Heavy tail: p50 $0.72 / p95 $3.34 / max $6.03 per attempt;
  top 5% consumed 17% of budget. Costliest attempt:
  pandas-dev__pandas-52422, $6.03 (8x p50), retry path $5.93,
  8 retries, context grew 29.2x. Averth's anomaly list also flags
  pandas-51355 ($5.27), pandas-51274 ($4.99), pandas-50328 ($4.72),
  pandas-53044 ($4.25), all retry-path driven.

## 20-row slice numbers (audit only, do not quote as the diagnosis)

- Slice A (literal first 20): 20 attempts, 0 resolved, $8.67 total
  (priced $8.00 + tool estimates $0.67), 342 model / 334 tool /
  3 retry events, context 16.4x, context tax $6.90 (86% of model
  spend), yield 0%, p50 $0.49 / p95 $0.94 / max $0.97.
  CLI output: `averth-output-literal.txt`, HTML: `report-literal.html`.
- Slice B (systematic main-run, every 37th row): 20 attempts,
  0 resolved, $27.28 total (priced $26.21 + tool estimates $1.07),
  581 model / 533 tool / 42 retry events, context 22.6x,
  context tax $23.83 (91% of model spend), yield 0%,
  p50 $1.71 / p95 $2.87 / max $4.14.
  CLI output: `averth-output.txt`, HTML: `report.html`.

## Anomalies checked

- "-$0" priced-bucket artifact: NOT present in any of the three runs
  (priced buckets are $789.92, $8.00, and $26.21 respectively).
- $0 context tax on fallback pricing: NOT present; context tax is
  $706.87 (full run), $6.90 (slice A), $23.83 (slice B). The model is
  priced in v6, not fallback, so this quirk does not apply here.
- Vacuous $0 per success: PRESENT in both 0-success slices.
  Averth prints "Fully loaded: $0.00" for slices A and B because they
  have 0 successes. That is not "$0 per success"; read it as
  UNKNOWN / undefined. The full run's $14.72 per success is the
  only cost-per-success figure in this lane that means anything.
- No "Measured" label appears; the report says PRICED with the
  provenance-unverified wording, plus the ESTIMATED cost-basis banner.
- No cache data exists in this dataset, so no cache saving is
  claimed. Human review is $0.00 at an assumed rate, not measured.

## Limits: what this does not prove

- No billed cost, no recorded tokens, no tested change, no saving
  claimed. This is a clean-run diagnosis: Averth ingests 737 real
  OpenHands pandas trajectories, exit 0, and reports a complete
  ledger. It is not a value POC, not proof an operator would pay,
  and not a pandas solve-rate claim beyond this one GPT-4o sampled
  run (7.6% resolved on 737 rows, vs 6.7% across all 1,044 pandas
  rows in the dataset).
- Retry count mixes genuine redo loops with deliberate reproduction
  tracebacks; treat 1,237 as a recorded-error count, not a pure
  loop count.
- Tool spend is 100% built-in defaults ($0.002/call); the $34.50
  tool figure is an estimate, and the $824.43 total inherits it.
- The 5 Claude-3.5-Sonnet pandas rows in the dataset (1 resolved)
  are outside the main GPT-4o run and were not run here.
