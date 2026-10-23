# POC NEW 40: OpenHands, Qwen3.6-27B — clean-run test, batch 4

Verdict: PASS for a clean Averth run. This is a diagnosis, not a value
POC: no change was applied or measured, no one was contacted, nothing
was sent or posted, no private data was used.

## Source

- Dataset: nvidia/Open-SWE-Traces,
  https://huggingface.co/datasets/nvidia/Open-SWE-Traces
- File: data/openhands/qwen36_27b/scale-swe/train-00000-of-00009.parquet
  (shard 0, 2,500 rows; this lane uses only the first 20 rows in file
  order that meet the turn floor, below).
- Scaffold: OpenHands. Teacher model, from each row's metadata:
  Qwen3.6-27B, enable_thinking false.
- Distinct from earlier lanes: not poc-new-15 (OpenHands
  DeepSeek-V4-Flash-0731, scale-swe) and not poc-new-13 (nvidia v2.0
  sweagent imbalanced-learn, Qwen3.8-Flash-Next), and not poc-new-09
  (nebius SWE-rebench OpenHands Qwen3-Coder-480B). Zero instance_id
  overlap with the poc-new-15 sample and zero overlap with the
  poc-new-09 sample, both verified programmatically.

## Selection and conversion (mechanical, no outcome filtering)

- Selection: first 20 rows in file order with at least 8 assistant
  turns. All 20 qualify (72 to 109 assistant turns each); all 20
  instance_ids distinct. Resolved labels were not used to select.
- One model event per assistant turn, one tool event per assistant
  turn (name = first tool-call name), a retry event before the next
  model call when a tool observation matches
  "[Command finished with exit code N]" with N != 0, and an end event
  with success = the dataset's own resolved verdict.
- Input tokens = characters of all preceding message text (content
  plus reasoning_content plus tool-call arguments) divided by 4.
  Output tokens = characters of this assistant turn, same fields,
  divided by 4. These are chars/4 ESTIMATES, not recorded usage: the
  dataset records no per-call token counts, no cache counts, and no
  billed dollar costs.
- Independent recount: sample assistant turns sum to 1,734, exactly
  equal to the 1,734 model events in the converted file.
- Converted events: 3,627 lines — 1,734 model, 1,734 tool, 139 retry,
  20 end. Tool names: execute_bash 977, str_replace_editor 679,
  think 58, finish 20.
- Model tokens (estimated): input 59,925,986, output 421,676.

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl \
  --html <report.html> --agent openhands-qwen36-27b

- Repo: ~/workspace/averth, commit fafab07 ("Fix Langfuse cached
  alias: input_cached_tokens").
- Price table v6, verified 2026-10-22. `averth pricing` exits 0, 18
  models, 8 tools.
- CLI exit code: 0. No error, no traceback, no unknown-event
  rejection. HTML report written.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run, all estimated

- Attempts: 20
- Autonomous completions (resolved): 11 (55.0 percent)
- Failed attempts: 9 (45.0 percent)
- Retries: 139 — exit code 1: 128, exit code 2: 4, exit code 4: 2,
  exit code 130: 2, exit code 6: 1, exit code 127: 1, exit code 128: 1.
- Total: $64.66, cost basis ESTIMATED as printed by Averth.
  Priced $0, billed $0.00, estimated (fallback prices) $64.66.
- Model spend: $61.19, all at the documented fallback $1.00 input /
  $3.00 output per 1M tokens, because Qwen3.6-27B has no price-table
  entry in v6 and Averth flags unknown:Qwen3.6-27B. Independently
  rechecked: 59,925,986 input x $1.00/1M = $59.93, plus 421,676
  output x $3.00/1M = $1.27, sum $61.19.
- Tool spend: $3.47, entirely built-in per-call estimates
  (1,734 calls x $0.002 = $3.47), flagged estimated in the report.
- Cost per successful outcome: $5.88 fully loaded (model terminal
  $0.41, retry path $5.15, tool calls $0.32, human $0.00).
- Failed runs: $30.91 (48 percent of spend, zero outcomes).
- Retry path: $56.67 model plus retry spend on discarded paths
  (overlaps failed runs; do not add the two lenses).
- Context compounding: 21.6x input growth first-to-last step;
  context tax $0.00 (0 percent of model spend) — see anomaly note.
- Yield: 7 percent of tokens on the terminal path (93 percent burned
  on retries and failed runs).
- Heavy tail: p50 $3.07 / p95 $4.62 / max $5.26 per attempt; top 5
  percent consumed 8 percent of budget.

## Anomalies and limits, not hidden

- Context tax $0.00 despite 21.6x growth is the known fallback-pricing
  quirk, seen in batch 2 and in poc-new-15: the fallback cost path
  records in_price 0.0, and the context-tax loop skips steps with no
  input price. Do not quote this as "context was free."
- The "-$0" priced-bucket artifact did NOT reproduce here (priced
  bucket is $0, printed as $0), and no "Measured" label appears.
- Retry count is a lower bound: only bash exit codes are counted.
  Editor errors and test failures without a bash exit code are not
  counted as retries.
- Input tokens are cumulative full-history context per turn, with no
  truncation and no cache discount, at chars/4 estimates. A real API
  bill for these runs would almost certainly be lower. $64.66 is an
  Averth estimate, never a bill, and must not be quoted as what
  anyone was charged.
- The 55.0 percent resolved rate is this first-20 sample only, not a
  rate for the shard, the dataset, or Qwen3.6-27B generally.
- Cost per successful outcome rests entirely on estimated tokens at
  fallback prices. A vendor price for Qwen3.6-27B, recorded tokens,
  or a bill would move every model dollar; do not compare $5.88 per
  success against priced-model lanes without that caveat.
- No tested change, no saving claimed, no operator, no recipient.
  This file is a clean-run diagnosis only and is not sendable as a
  value POC on its own.

## Files

- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/convert.py
- Events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/events.jsonl (3,627 lines)
- Sample: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/sample.json
- Averth text output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/averth-output.txt
- HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/report.html
- Source shard (206 MB, local copy only): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-40/shard0.parquet
