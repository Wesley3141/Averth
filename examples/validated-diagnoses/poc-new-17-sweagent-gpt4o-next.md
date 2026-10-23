# POC New 17: SWE-agent, rows 100-200 of the Nebius trajectories

Lane: batch 3, agent 17 of 20. Clean run diagnosis test only.
No one was contacted, nothing was sent, nothing was posted, no private
data was used. Source is a public dataset, CC-BY-4.0 per its card.

## Correction to the lane label, read first

The lane brief described this slice as SWE-agent GPT-4o. That is
wrong for this dataset slice, and this file does not repeat it as
fact. Rows 100-200 of shard 0, row group 0, of
nebius/SWE-agent-trajectories are:

- swe-agent-llama-70b: 95 attempts
- swe-agent-llama-8b: 5 attempts
- GPT-4o: 0 attempts

A quick web search found no verified public SWE-agent GPT-4o
trajectory dataset with per step tokens to substitute, so no
fallback slice was used. Substituting a different scaffold or model
would have broken the exact rows 100-200 assignment. This is a
SWE-agent llama slice, priced at Averth fallback rates, not a
GPT-4o priced run. Any rollup that labels it GPT-4o is wrong.

## Sample, exact

Source: https://huggingface.co/datasets/nebius/SWE-agent-trajectories
File: data/train-00000-of-00012.parquet, row group 0, rows 100-200
in file order (global row indices 100-199). Not a random sample.

Issues, 7 distinct, 100 attempts, 0 resolved in every issue:

- asottile__pyupgrade-142: 31 attempts, 0 resolved
- ahawker__ulid-59: 18 attempts, 0 resolved
- airspeed-velocity__asv-702: 16 attempts, 0 resolved
- TACC__agavepy-62: 13 attempts, 0 resolved
- absent1706__sqlalchemy-mixins-108: 12 attempts, 0 resolved
- ShawHahnLab__igseq-2: 7 attempts, 0 resolved
- TheFriendlyCoder__pyjen-113: 3 attempts, 0 resolved

Distinctness vs batch 1 POC 03 (rows 0-100): 6 of the 7 issues are
new. ShawHahnLab__igseq-2 repeats, with 7 new attempts here after
5 attempts in batch 1, still 0 resolved in both slices. Do not
present this slice as 7 fully new issues.

Exit statuses in this slice: submitted 51, submitted (exit_context)
30, exit_context 9, submitted_no_patch 8, early_exit 2. Submitted
is not acceptance here: the dataset target field is false for all
100 attempts, so Averth correctly reports 0 accepted outcomes.

## Conversion, mechanical

Script:
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-17/convert.py
Input: the same local parquet file batch 1 used, at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-03-swe-agent/train-00000.parquet
Output: 6,603 events (3,064 model, 3,064 tool, 375 retry, 100 end).

Rules, identical to batch 1 POC 03, offset only:
- case_id is instance_id plus global row index, so repeated attempts
  on the same issue stay separate attempts.
- System prompt chars and user text chars count toward context.
- A user observation containing "syntax error" or starting with
  "Traceback" marks a retry before the next ai turn. These are
  recorded failure signals in the observation text, not invented
  labels.
- One ai turn becomes one model event and one tool event named
  "bash", the SWE-agent one tool action per turn construction.
- Token counts are NOT recorded in this dataset. Input tokens are
  chars of all preceding message text divided by 4, output tokens
  are chars of this ai turn divided by 4. These are estimates.
- Model names are NOT in the Averth price table, so Averth prices
  them at its documented fallback estimate ($1.00 per 1M input,
  $3.00 per 1M output) and flags them as unpriced models.
- End event success is the dataset "target" field.

## Averth run, upgraded build

Repo: ~/workspace/averth, commit 071d0e1, price table v6.
Command, from ~/workspace/averth:

.venv/bin/python -m averth.cli trace
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-17/events.jsonl
--format jsonl --html
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-17/report.html

CLI exit code: 0. Full output and HTML report are in
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-17/
(averth-output.txt, report.html, events.jsonl, convert.py).

Results, from the Averth run, independently rechecked from the
converted events:

- Attempts: 100, accepted outcomes: 0 (0.0%)
- Cost per successful outcome: undefined, not $0.00. Averth prints
  a $0.00 breakdown because there is no success to divide by. Do
  not quote $0.00 as a cost per success.
- Total cost, ESTIMATED basis only: $43.52
  - Model spend, fallback estimate: $37.39. Recheck: cumulative
    input estimate 36,335,286 tokens at $1.00 per 1M plus output
    estimate 352,386 tokens at $3.00 per 1M equals $37.39.
  - Tool spend, built-in per call estimates for bash: $6.13
    (3,064 calls). Not a measured tool bill.
  - Priced (vendor list prices): $0.00. Vendor billed: $0.00.
- Cost basis printed by Averth: ESTIMATED, with the fallback warning
  for unknown:swe-agent-llama-70b and unknown:swe-agent-llama-8b.
  No dollar figure here is a vendor bill or measured spend.
- Retries: 375 total, syntax error 208, traceback 167. These counts
  match Averth exactly when counted from the converted events.
- Context growth: 7.2x input growth first step to last step.
- Yield: 0% of tokens on the terminal path, because there is no
  accepted outcome. Failed runs: $43.52, 100% of spend.
- Heavy tail, estimated basis: p50 $0.20, p95 $1.30, max $4.53 per
  attempt, top 5% consumed 32% of budget.
- Longest attempt by ai turns: airspeed-velocity__asv-702#166,
  262 ai turns, unresolved.

## Anomalies, do not hide these

1. Model label: see the correction at the top. Not GPT-4o.
2. Priced line reads "-$0", a pre-existing floating point display
   artifact already noted in batch 1. The real priced figure is
   $0.00, because every model dollar is fallback estimated.
3. Context tax reads $0.00 despite 7.2x growth, the same fallback
   model quirk batch 1 noted. Do not quote a context tax dollar
   figure for this slice.
4. Averth reports "Autonomous completions: 0" even though 51
   attempts carry a "submitted" exit status. That is consistent
   with Averth semantics here: completion means an accepted
   outcome, and target is false for all 100. Submitted is not
   acceptance.
5. 0 of 100 resolved is a property of this file order slice, not
   a general SWE-agent solve rate. Batch 1 rows 0-100 resolved
   17 of 100, all from one issue. Combined rows 0-200: 17 of 200,
   all from Melevir__cognitive_complexity-15.

## Verdict: PASS as a clean run diagnosis, with the caveats above

PASS criteria met: real per step input (100 trajectories, 3,064
model turns), attempts 100, well above the 10 minimum, CLI exit 0
with no crash, totals produced, and an honest ESTIMATED cost basis
printed by Averth itself, not a Measured or billed claim.
This is not a value proof and not a GPT-4o run: 0 accepted
outcomes means there is no before and after, no savings figure,
and no cost per success to quote. The diagnostic signal is the
retry pattern, 375 retries, 208 after syntax errors, on a slice
where every dollar went to failed attempts.
