# POC new-35: SWE-smith / sunpy slice — PASS (clean run)

Lane: batch-4 replacement lane 35 of the Averth 40-POC run. This lane
replaces batch-3 lane 14 (SWE-smith sympy/astropy, FAIL: 0 sympy and
0 astropy rows in 76,002 scanned SWE-smith rows). The sunpy slice was
suggested in that lane's own file as the closest scientific-computing
repo actually present in the dataset (291 rows in the xml split).
No one was contacted, nothing was sent, nothing was posted, no
private data was used. This is a clean-run diagnosis test only, not
a value proof and not a sendable outreach piece.

## Source actually run

- Dataset: SWE-bench/SWE-smith-trajectories, split `xml`.
  Source URL: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
- Repo: sunpy__sunpy (all rows are the single SWE-smith base commit
  f8edfd5c; task types are synthetic SWE-smith program-mutation
  tasks, not real sunpy issues — see the task-type split below).
- Selection: the first 20 sunpy rows in xml-split file order
  (shard 0 rows 2720, 2861, 2940, 2970, 3065, then shard 1 rows 28,
  60, 133, 224, 248, 1918, 1920, 1986, 1997, 2002, 2074, 2151,
  2184, 2244, 2286), with no outcome filtering. The scan that found
  them read only instance_id, traj_id, resolved, and model columns
  via HTTP range requests; message bodies were fetched only for
  these 20 rows, verbatim.
- Distinctness, verified programmatically: 0 traj_id overlap with
  first-batch POC-01 (16 SWE-smith tool-split attempts, 0 sunpy
  rows among them) and 0 overlap with batch-3 POC new-18
  (20 SWE-smith tool-split Claude attempts).
- Model for all 20 rows, from the dataset: claude-3-7-sonnet-20250219.

## Conversion (mechanical, no per-record editing)

Script: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-35/convert.py
(a copy of the POC new-18 SWE-smith converter; the xml split uses
the same layout it was written for)
Events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-35/events.jsonl
(1,102 events)
Raw rows (verbatim, one JSON per trajectory):
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-35/raw/ (20 files)

Rules, fixed before conversion:

- case_id = row traj_id; one model event per assistant turn;
  model = row model for every turn.
- One tool event per `<function=NAME>` tag in the assistant text
  (the xml layout carries tool calls as embedded tags, not as
  structured tool_calls objects). In this sample every assistant
  turn carried exactly one tag, so tool events (529) equal model
  events (529): bash 236, str_replace_editor 254, submit 39.
- Retry event before the next model call when the preceding tool
  observation (a user message starting "OBSERVATION:") matches
  the first-batch heuristic: Python traceback, FAILED/ERROR line,
  or "command not found". Observations only; the issue text is
  never scanned. This is a lower bound on failures (silent
  failures are missed).
- End event: success = row resolved (the dataset's real verdict).
  Independent recount: all 20 end labels match the scan's
  resolved column exactly, 0 mismatches.

Token disclosure, stated plainly: the dataset records no per-call
token usage. Input tokens = characters of all preceding message
text / 4; output tokens = characters of the assistant turn / 4,
where assistant turn text = content plus tool-call names and
arguments. These are mechanical estimates in the same style as
first-batch POC 01, never recorded usage, and every dollar below
inherits that status. No cache tokens are recorded.

## Averth run

- Averth: ~/workspace/averth at commit fafab07 (price table v6,
  verified: `averth pricing` exits 0, 18 models, 8 tools, fresh).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace
  <hidden_files/poc-new-35/events.jsonl> --format jsonl
  --html <hidden_files/poc-new-35/report.html>`
- CLI exit code: 0, no crash, no dropped-case error.
- Full CLI output:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-35/cli_output.txt
- HTML report:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-35/report.html

## Numbers, fresh run

- Attempts: 20. Accepted outcomes (resolved): 10 (50.0%).
  Failed: 10.
- Model events: 529. Tool events: 529. Retries: 24, every one
  reason "tool error". Per-case assistant turns range 11 to 76.
- Total cost: $26.82. Model spend $25.77, tool spend $1.06
  (sum $26.83 before rounding; CLI total $26.82).
- Cost basis, exactly as Averth printed it: COST BASIS ESTIMATED.
  Priced (tokens x vendor prices; token provenance unverified):
  $25.77. Vendor-supplied (billed): $0.00. Estimated (fallback
  prices): $1.06, entirely built-in tool per-call estimates.
  Model price status: anthropic:claude-3-7-sonnet-20250219 is in
  price table v6 at $3.00 input / $15.00 output per 1M, so no
  model fallback was used. Estimated token totals: 8,126,552
  input tokens, 92,486 output tokens. Independent recomputation
  at $3/$15 gives $25.767, matching Averth's $25.77 exactly.
- Cost per successful outcome, fully loaded: $2.68
  (model terminal $0.32, retry path $2.26, tools $0.11, human
  $0.00 at the $70.20/hr loaded assumption, which is not
  measured). With 10 successes this figure is defined, unlike
  the 0-success lanes; it still rests on estimated tokens, not
  a bill.
- Failed runs: $19.38 (72% of spend, zero outcomes).
- Retry path: $22.62 model+retry spend on discarded paths
  (overlaps failed runs; do not sum lenses).
- Context compounding: 13.1x input growth first-to-last step;
  context tax $21.80 (85% of model spend).
- Yield: 12% of tokens on a terminal path (88% burned on
  retries and failed runs). Yield here is definitional
  (terminal path only), as in earlier SWE-smith lanes.
- Heavy tail: p50 $0.90 / p95 $3.48 / max $5.96 per attempt;
  top 5% consumed 22% of budget.

## The finding that must travel with the headline rate

The 50% resolved rate is not a general sunpy rate. It splits
cleanly by SWE-smith task type, and the split is in the file
order itself, not a post-hoc cherry-pick:

- Program-mutation tasks (func_pm_*): 9 of 10 resolved
  (the first 10 rows in file order).
- LM-rewrite tasks (lm_rewrite_*): 1 of 10 resolved
  (the last 10 rows in file order; the single success is
  lm_rewrite__a7wzfpt8).

Quoting "50% on sunpy" without that split would hide the real
diagnosis: these Claude 3.7 runs handle the mutation tasks and
almost uniformly fail the rewrite tasks. No cause is proven by
this meter run (no change was tested), and the tasks are
synthetic SWE-smith mutations of one sunpy commit, not real
sunpy issues, so nothing here should be sent to sunpy
maintainers as a finding about their project.

## Anomalies noted, as the task requires

1. The $25.77 "Priced" bucket rests on chars/4 estimated tokens,
   not recorded usage. Averth's own banner says exactly that
   ("token provenance unverified") and the overall basis is
   ESTIMATED, but the bucket name alone would mislead a reader
   into treating it as recorded-token spend. Quote $26.82 only
   as an Averth list-price estimate, never as what anyone was
   charged. This is the same token-provenance gap flagged in
   batch-3 lanes 28 and 30: Averth's Priced bucket does not
   distinguish recorded tokens from estimated tokens.
2. No "-$0" display artifact appeared in this run's CLI output
   (searched, zero occurrences), and no "Measured" label
   appears.
3. No $0 context-tax artifact: context tax is $21.80, because
   the model is priced (not fallback) and successes exist.
   Contrast batch-3 lane 13, where $0 tax was vacuous with
   zero successes.
4. Top-finding vs waste-accounting retry figures differ
   slightly: the headline finding says retry loops burned
   $23.06 (86% of spend) while waste accounting says retry
   path $22.62. These are two overlapping lenses on the same
   spend, not additive partitions; neither is quoted here as
   a separate charge.
5. Retry count (24) is a lower bound under the error heuristic;
   silent failures are not counted as retries.
6. Tool spend $1.06 uses Averth's built-in per-call defaults
   for bash, str_replace_editor, and submit. It is not measured
   tool cost; Averth prints that warning itself.
7. Human review is $0.00 because no human time was recorded;
   the $70.20/hr rate in the report is an assumption, not a
   measurement.

## Independent cross-check

Direct count of events.jsonl (not the CLI's own summary):
model 529, tool 529, retry 24, end 20, every end label matching
the dataset scan. Matches the CLI's attempts, retries, and
50% acceptance exactly. Manual model-cost recomputation
($25.767) matches Averth's $25.77.

## Verdict: PASS as a clean-run diagnosis, with the split stated

PASS criteria from the task, checked:

- Real per-step input: yes, 20 verbatim trajectories, 23 to
  153 messages each, assistant turns with embedded tool calls
  and observations.
- Attempts >= 10: yes, 20.
- Totals and honest cost basis: yes, exit 0, $26.82
  ESTIMATED, $25.77 priced-on-estimated-tokens, $0 billed,
  $1.06 tool estimates, anomalies above noted.
- Aggregates alone: no, this is not an aggregate conversion;
  no paper total or blog total was turned into a single event.
- Resolved labels present: yes, dataset resolved for all 20
  rows; no auto-end-as-failed artifact is quoted.

What this is not:

- Not a value POC: no change was applied or measured, and
  cost per success rests on estimated tokens, not a bill.
- Not a finding about real sunpy work: the tasks are synthetic
  SWE-smith mutations of one commit, and the resolved rate
  splits 9/10 vs 1/10 by task type.
- Not ready to send to anyone. No recipient was verified.
  No contact was made.
