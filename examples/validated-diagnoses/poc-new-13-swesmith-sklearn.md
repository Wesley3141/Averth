# POC new-13: SWE-smith / scikit-learn lane — FALLBACK USED, read this first

Lane: SWE-smith, scikit-learn repo slice, batch-3 agent 13 of 20.
No one was contacted, nothing was sent, nothing was posted, no private
data was used. This is a clean-run diagnosis test only, not a value
proof and not a sendable outreach piece.

## Fallback disclosure (do not strip this when quoting)

This is NOT scikit-learn/scikit-learn. A real scikit-learn/scikit-learn
trajectory slice does not exist in any public trajectory corpus I
checked, so the lane as originally specified cannot be run as written.
The slice actually run is scikit-learn-contrib/imbalanced-learn, a
scikit-learn ecosystem library (it extends the scikit-learn API), from
a sibling trajectory dataset. Do not present any number below as a
scikit-learn result, and do not send it to scikit-learn maintainers.

## Why the exact lane failed: exact scikit-learn = 0 everywhere checked

I scanned the instance/repo column of every shard, not just a sample,
using a column-pruned parquet reader (only instance_id/repo/resolved
columns fetched, no full downloads):

- SWE-bench/SWE-smith-trajectories, splits tool, ticks, and xml:
  0 rows with repo scikit-learn/scikit-learn in any split. Tool split
  total 24,100 rows. This is the dataset the first-batch POC 01 used
  (16 broad attempts, no sklearn row among them either). The pattern
  is systematic: SWE-smith and the other training corpora exclude
  SWE-bench repos, and scikit-learn is a SWE-bench repo.
- SWE-Gym/OpenHands-Sampled-Trajectories, train.raw: 0 in 6,055 rows.
- nebius/SWE-agent-trajectories, train: 0 in 80,040 rows (12 shards).
- nvidia/Open-SWE-Traces, v1.0 openhands + sweagent, v1.1
  minisweagent + openhands: 0 exact sklearn in every shard scanned.
- nvidia/Open-SWE-Traces, v2.0, all three splits scanned in full:
  sweagent 0 exact, openhands 0 exact, minisweagent 0 exact.
  The only "scikit" hits in v2.0 are sibling repos (scikit-rf,
  scikit-hep, scikit-build, scikit-learn-contrib), not
  scikit-learn/scikit-learn.

Substring searches for "scikit" that return scikit-rf or scikit-hep
rows are false positives for this lane and were rejected.

## Fallback source actually run

- Dataset: nvidia/Open-SWE-Traces, config v2.0, split sweagent.
  Source URL: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
- Underlying task set in the rows' metadata:
  hf_dataset_name AweAI-Team/Scale-SWE.
- Repo: scikit-learn-contrib/imbalanced-learn (21 rows in the sweagent
  split, 13 in openhands, 21 in minisweagent, all resolved 0; see below).
- Selection: the first 14 imbalanced-learn rows in shard order
  (sweagent shards 0-4), fetched verbatim. I stopped at 14 because
  the task threshold is 10 and full-message fetching runs about
  2 minutes per shard; this is a mechanical shard-order cut, not a
  cherry-pick by outcome. Outcome selection bias is in any case
  impossible here: every imbalanced-learn row in all three v2.0
  splits is resolved 0 (55 of 55).
- Teacher model for all 14 rows, from each row's metadata:
  Qwen3.8-Flash-Next, reasoning effort xhigh.
- Raw rows (verbatim, one JSON per trajectory):
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-13/raw/
  (14 files, named by trajectory_id).

## Conversion (mechanical, no per-record editing)

Script: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-13/convert.py
Events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-13/events.jsonl
(2,122 events). Rules, mirroring the first-batch SWE-smith converter:

- case_id = trajectory_id; one model event per assistant turn;
  model = Qwen3.8-Flash-Next for every turn.
- One tool event per tool_call in the assistant message, name =
  function name (bash, str_replace_editor, submit).
- Retry event before the next model call when the preceding tool
  observation matches the first-batch heuristic: Python traceback,
  FAILED/ERROR line, or "command not found". Observations only; the
  issue text is never scanned.
- End event: success = row resolved (the dataset's real verdict).

Token disclosure, stated plainly: the dataset records no per-call
token usage. Input tokens = characters of all preceding message
text / 4; output tokens = characters of the assistant turn / 4,
where assistant turn text = content + reasoning_content + tool-call
names and arguments. These are mechanical estimates in the same
style as first-batch POC 01, never recorded usage, and every dollar
below inherits that status.

## Averth run

- Averth: ~/workspace/averth at commit 071d0e1, price table v6
  (verified 2026-10-22).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace
  <hidden_files/poc-new-13/events.jsonl> --format jsonl
  --html <hidden_files/poc-new-13/report.html>`
- CLI exit code: 0, no crash, no dropped-case error.
- Full CLI output:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-13/cli_output.txt
- HTML report:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-13/report.html

## Numbers, fresh run

- Attempts: 14. Accepted outcomes: 0 (0.0%). All 14 end events are
  success False, matching the dataset resolved labels exactly.
- Model events: 1,017. Tool events: 1,017. Retries: 74, every one
  reason "tool error". Per-case assistant turns range 28 to 170;
  the longest case (170 turns) ends with 214,523 estimated input
  tokens on its last turn.
- Total cost: $60.99. Model spend $58.95, tool spend $2.03
  (sum $60.98 before rounding; CLI total $60.99).
- Cost basis, exactly as Averth printed it: COST BASIS ESTIMATED.
  Priced (tokens x vendor prices): $0.00. Vendor-supplied (billed):
  $0.00. Estimated (fallback prices): $60.99.
- Model price status: Qwen3.8-Flash-Next is NOT in price table v6,
  so Averth used its documented fallback $1.00 input / $3.00 output
  per 1M tokens and flagged it as unpriced model
  unknown:Qwen3.8-Flash-Next. No Qwen list price was invented.
- Context compounding: 99.5x input growth first to last step.
- Yield: 0% of tokens on a terminal path (100% burned on retries
  and failed runs, because there is no successful terminal path).
- Heavy tail: p50 $1.87, p95 $16.22, max $21.52 per attempt;
  costliest run consumed 35% of budget.
- Cost per successful outcome: undefined in reality (0 successes).
  See anomaly 2 below about what the CLI prints.

## Anomalies noted, as the task requires

1. Context tax $0.00 despite 99.5x compounding. This is vacuous,
   not a finding that context was free. With zero accepted
   outcomes there is no terminal path for the tax to be computed
   against, so it prints $0.00 (0% of model spend). Do not quote
   "$0 context tax" as a result.
2. Cost per successful outcome prints $0.00 in the CLI (all four
   components $0.00) despite 0 successes. That is also vacuous:
   there is no successful outcome to divide by. Read it as
   UNKNOWN / not applicable, never as "$0 per success".
3. No "-$0" display artifact appeared in this run's CLI output
   (searched, zero occurrences).
4. Tool spend $2.03 uses Averth's built-in per-call defaults for
   bash, str_replace_editor, and submit. It is not measured tool
   cost; Averth prints that warning itself.
5. The 0/14 acceptance rate is the dataset's own verdict, not an
   Averth judgement, but it is suspiciously uniform: all 55
   imbalanced-learn rows across all three v2.0 splits are
   resolved 0, all from the same teacher model family. Treat
   "imbalanced-learn tasks are unresolvable" as unproven; what is
   proven is only that these 14 Qwen3.8-Flash-Next runs did not
   resolve their tasks under this dataset's evaluation.

## Independent cross-check

Direct count of events.jsonl (not the CLI's own summary):
model 1,017, tool 1,017, retry 74, end 14, every end success False.
Matches the CLI's attempts, retries, and 0% acceptance exactly.

## Verdict: PASS as a clean-run diagnosis, with the fallback stated

PASS criteria from the task, checked:
- Real per-step input: yes, 14 verbatim trajectories, 57 to 341
  messages each, assistant turns with tool calls and observations.
- Attempts >= 10: yes, 14.
- Totals and honest cost basis: yes, exit 0, $60.99 ESTIMATED,
  $0 priced, $0 billed, fallback model price flagged, anomalies
  above noted, no -$0 artifact.
- Aggregates alone: no, this is not an aggregate conversion; no
  paper total or blog total was turned into a single event.

What this is not:
- Not a scikit-learn result. Do not count it as sklearn in the
  40-POC rollup without the fallback label.
- Not a value POC: 0 successes means there is no before/after
  lever, no cost per accepted outcome, and no finding a prospect
  can act on beyond "these 14 runs failed".
- Not ready to send to anyone. No recipient was verified, and
  with fallback prices plus a uniform 0/14 label, this would need
  verification before any contact. No contact was made.
