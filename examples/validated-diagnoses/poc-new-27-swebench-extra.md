# POC NEW-27: SWE-bench Extra trajectories, SWE-agent (fallback slice)

Lane: SWE-bench Extra, SWE-agent trajectories, distinct dataset from
SWE-bench, SWE-Gym, and SWE-smith.
Status: PASS as a clean-run diagnosis on the fallback slice below.
This is NOT a GPT-4o run, and it must never be quoted as one.

## Headline correction: the lane's GPT-4o slice does not exist here

The assignment asked for SWE-bench Extra, GPT-4o trajectories. That
slice does not exist in the dataset that actually holds SWE-bench
Extra trajectories, and this file does not pretend otherwise.

Evidence, checked, not assumed:

- Source dataset: https://huggingface.co/datasets/nebius/SWE-agent-trajectories
  (Nebius, "SWE-agent-trajectories", trajectories on SWE-bench Extra
  instances, per the Nebius blog "Scaling data collection for training
  software engineering agents", http://nebius.com/blog/posts/scaling-data-collection-for-training-swe-agents).
- The blog says the trajectories were generated with open-weight
  models, later iterations predominantly Llama-3.1-70b and Qwen-2.5-72b
  fine-tuned on earlier versions. GPT-4o appears in the blog only as
  the reference for the "easy-lite 50" evaluation subset and for
  validating the "verified-50" subset, not as a trajectory generator.
- Full scan performed for this POC: all 12 parquet shards of
  nebius/SWE-agent-trajectories were downloaded and their model_name
  column counted, 80,036 rows in total, 13,389 resolved, matching the
  blog's published totals exactly. Every row's model_name is one of:
  swe-agent-llama-70b, swe-agent-llama-8b, swe-agent-llama-405b.
  GPT-4o count: 0. Qwen count: 0. No GPT-4o slice exists to run.
  Full scan log:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/shard-scan.log
- Shard 0 alone (6,670 rows) is also GPT-4o-free: llama-70b 6,018,
  llama-8b 511, llama-405b 141.

Fallback used, as the task allows ("fallback to another SWE-bench-extra
slice if needed, report it"): a llama slice of the same SWE-bench
Extra dataset, defined exactly below. Do NOT relabel it GPT-4o in
outreach, in a subject line, or in a summary table. If a GPT-4o
trajectory set on SWE-bench Extra instances is ever found elsewhere,
it is a different dataset and needs its own POC file.

## Sample definition, exact

- Dataset: nebius/SWE-agent-trajectories, shard 0,
  data/train-00000-of-00012.parquet.
- Sample: rows 400-499 in global file order (100 trajectories).
  This is NOT a random sample of the 80,036 rows.
- Zero row overlap with POC 03, which used rows 0-99 of the same
  shard. Zero issue overlap with POC 03's 7 issues: none of the 6
  issues below appears in POC 03.
- Issues in this sample, attempts and resolved (dataset target):
  - delph-in__pydelphin-362: 6 attempts, 0 resolved
  - fairlearn__fairlearn-896: 11 attempts, 0 resolved
  - geopandas__geopandas-3240: 16 attempts, 10 resolved
  - google__latexify_py-67: 10 attempts, 0 resolved
  - google__mobly-472: 17 attempts, 0 resolved
  - hugovk__pypistats-41: 40 attempts, 17 resolved
- Models in sample: swe-agent-llama-70b 94 attempts (all 27 resolved),
  swe-agent-llama-8b 6 attempts (0 resolved). The 8b result is n=6;
  do not quote it as an 8b failure rate.
- Exit statuses in sample: submitted 83, submitted (exit_context) 16,
  exit_context 1. So 17 of 100 attempts ended in a context exit of
  some form.
- Skew warning, read before quoting 27%: resolved attempts come from
  only 2 of 6 issues (geopandas 10, hugovk 17). The other 4 issues
  resolved 0 of 44 attempts. 27% is this file-order block's rate, not
  SWE-agent's general solve rate, not a llama-70b rate, and not a
  GPT-4o rate.

## Conversion, mechanical and documented

Script: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/convert.py
Input: shard 0 parquet, rows 400-499.
Output: events.jsonl, 3,539 events (100 start, 1,550 model, 1,550 tool,
239 retry, 100 end).

Rules, same as POC 03's converter except for the slice and explicit
start events:
- case_id is instance_id plus global row index, so repeated attempts
  on the same issue stay separate attempts instead of merging.
- System entry: system_prompt length counts toward context chars.
- User entry: text length counts toward context chars. If the text
  contains "syntax error" or starts with "Traceback", the next ai turn
  is preceded by a retry event with that reason. These are recorded
  failure signals in the observation text, not invented labels.
- Ai entry: one model event and one tool event named "bash" per turn.
  SWE-agent turns in these traces carry one tool action per turn by
  construction; the tool cost is Averth's default estimate and is
  flagged as such in the report, not a measured tool bill.
- Token counts are NOT recorded in this dataset. input_tokens is
  chars of all preceding message text divided by 4, output_tokens is
  chars of this ai turn divided by 4, the same mechanical estimate
  POC 03 used. These are estimates. Totals on this basis: 13,610,821
  estimated input tokens, 173,059 estimated output tokens.
- Model names swe-agent-llama-70b and swe-agent-llama-8b are NOT in
  Averth's price table v6, so Averth prices them at its documented
  fallback estimate ($1.00 per 1M input tokens, $3.00 per 1M output
  tokens) and flags them as unpriced models. Dollar totals below are
  ESTIMATES, never a vendor bill.
- End event: success is the dataset "target" field, the dataset's own
  solved or unsolved label for that trajectory. Acceptance labels
  therefore exist for this sample, so cost per successful outcome can
  be computed, but only on the estimated dollar basis above.

## Averth run

Tool: Averth in ~/workspace/averth at commit 071d0e1, price table v6
(verified 2026-10-22).

Reproduction command, from ~/workspace/averth:

    .venv/bin/python -m averth.cli trace \
      ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/events.jsonl \
      --format jsonl \
      --html ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/report.html \
      --anomaly

CLI exit code: 0. Full output saved at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/averth-output.txt
and the HTML report at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-27/report.html

## Results, from the Averth run

- Attempts: 100
- Accepted outcomes (dataset target true): 27, or 27.0%
- Failed attempts: 73, or 73.0%
- Retries: 239 total. Top reasons: syntax error 151 times,
  traceback 88 times.
- Yield: 6% of tokens on the terminal path, 94% burned on retries
  and failed runs, per Averth.
- Context growth: 5.1x input growth first step to last step, per
  Averth.
- Heavy tail, estimated basis: p50 $0.08, p95 $0.70, max $0.89 per
  attempt, top 5% of attempts consumed 23% of estimated budget.
- Cost per successful outcome, estimated basis, fully loaded: $0.64
  (model terminal $0.03, retry path $0.49, tool calls $0.11, human
  review $0.00).
- Costliest attempts (anomaly flag, inspect not accuse):
  delph-in__pydelphin-362#402 $0.89 (retry path $0.77, context 12.1x),
  fairlearn__fairlearn-896#416 $0.84 (retry path $0.76, context 12.3x),
  delph-in__pydelphin-362#405 $0.81 (14 retries, context 12.4x),
  google__mobly-472#450 $0.72 (36 retries, context 14.5x),
  google__latexify_py-67#434 $0.70 (29 retries, context 14.5x).
  The pattern is retry loops, not model choice: the top attempts are
  expensive because their discarded paths are long.

## Costs, recorded first, metered second

- Recorded costs in this dataset: NONE. This dataset publishes no
  per-instance dollar cost, so there is no recorded bill to reconcile
  against. Any dollar figure below is an Averth estimate, not a bill.
- Metered total, Averth estimated fallback basis: $17.23
  - Model spend, estimated: $14.13, all flagged as estimated.
    Arithmetic check: 13,610,821 input tokens at $1.00/1M = $13.61,
    plus 173,059 output tokens at $3.00/1M = $0.52, total $14.13.
    Model mix: llama-70b $12.52 (89% of model spend), llama-8b $1.61
    (11% of model spend).
  - Tool spend, built-in per-call estimate: $3.10 (1,550 bash events
    at $0.002 each), flagged as estimated, not a measured tool bill.
  - Failed runs: $15.56, or 90% of estimated spend, for zero outcomes.
  - Retry path: $13.31 model plus retry spend on discarded paths.
    Waste figures are overlapping lenses on the same spend, not
    additive partitions; do not sum them.
- Cost basis printed by Averth: "COST BASIS: ESTIMATED". Priced
  (tokens x vendor prices): $0.00. Vendor-supplied (billed): $0.00.

## Anomalies and limits, do not hide these

1. No GPT-4o. See the headline section. Any outreach copy that says
   GPT-4o for this POC is wrong.
2. All dollars estimated. No recorded tokens, no recorded prices for
   these model names, no bill. The value here is the shape of the
   diagnosis (failed share, retry reasons, tail), not the dollar
   total.
3. Priced bucket displays "-$0" in the Averth output. This is a
   pre-existing floating-point display artifact already noted for
   POC 03, not a negative charge. The total $17.23 is unaffected.
4. Context tax prints $0.00 despite 5.1x context growth. Same quirk
   POC 03 noted for unpriced-model fallback runs. Do NOT quote a
   context tax dollar figure from this run; quote only the 5.1x
   growth multiple.
5. One tool event per ai turn is a scaffold assumption, documented
   above, not a count read from a tool log. If a turn in fact made
   zero or several tool calls, the $3.10 tool figure moves.
6. Sample is one file-order block of 100, skewed to 2 resolving
   issues. Do not generalize the 27% rate, the $0.64 per success, or
   the $17.23 total beyond this block.
7. This is a clean-run diagnosis test, not a value proof. Averth ran
   by itself, exit 0, and measured the shape of waste; it did not
   fix anything, and no before/after change was tested here.

## Verdict

PASS, fallback slice only: real per-step input (1,550 ai turns with
recorded text, converted mechanically), 100 attempts (above the
10-attempt bar), CLI exit 0, totals with an honest ESTIMATED cost
basis, anomalies noted above. The original GPT-4o lane is FAIL for
input availability: no GPT-4o trajectories exist in this dataset.

## Outreach-safe summary (if this POC is ever used)

"Ran Averth on 100 public SWE-agent trajectories on SWE-bench Extra
instances (Nebius collection, llama models, not GPT-4o). 27 of 100
resolved, all from 2 of 6 issues. Failed runs took 90% of estimated
spend. Top retry reason was syntax error, 151 times. Estimated total
$17.23 on a fallback-price basis, not a bill. One change worth testing:
validate edit syntax before the next turn and stop after repeated
syntax retries, then compare cost per resolved issue before and
after."

No one was contacted, nothing was sent, nothing was posted, no
private data was used.
