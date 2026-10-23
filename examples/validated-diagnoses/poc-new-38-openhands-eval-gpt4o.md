# POC NEW-38: OpenHands official evaluation, GPT-4o — clean-run test, batch 4

Status: PASS (clean run). No one contacted, nothing sent, nothing posted,
no private data used. This is a clean-run diagnosis test only, not a value
pitch: does the upgraded Averth run by itself cleanly on a new public
workflow, or does it fail?

## Upgraded Averth used

- Repo: ~/workspace/averth, commit fafab07
  ("Fix Langfuse cached alias: input_cached_tokens"), price table v6
  (verified 2026-10-22).
- This lane uses the jsonl importer only. It does not exercise the
  Claude importer, Langfuse cached handling, or OTel recovered rule.

## Workflow and source — distinct from both prior OpenHands lanes

- Workflow: OpenHands CodeActAgent on real GitHub issues (SWE-bench Lite).
- Model: openai/gpt-4o-2024-05-13, maxiter 30, OpenHands v1.9,
  run starting 2024-09-29 (metadata.json). This is NOT the first batch
  (SWE-Gym/OpenHands-Sampled-Trajectories, GPT-4o-2024-08-06, train
  split, maxiter 30) and NOT poc-new-09 (nebius/SWE-rebench,
  Qwen3-Coder-480B). Different dataset, different model snapshot,
  different benchmark family (SWE-bench Lite vs SWE-Gym/SWE-rebench).
- Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  Folder: outputs/SWE-bench_Lite-test/CodeActAgent/
  gpt-4o-2024-05-13_maxiter_30_N_v1.9-no-hint-eval-24sep/
  Files used: output.jsonl (96 MB, 300 instances), report.json,
  metadata.json.
- Full-run facts from report.json: 300 instances, 300 submitted,
  269 completed, 64 resolved (21.3%), 205 unresolved, 31 empty-patch,
  0 error instances. The sample below is NOT that rate; see the
  sample warning.
- Instance overlap, verified programmatically against the saved
  sample lists: 0 of 20 with batch-1 POC 02 (SWE-Gym sample) and
  0 of 20 with poc-new-09 (SWE-rebench Qwen sample). Expected: the
  benchmarks use disjoint repo sets, and the check confirms it
  rather than assuming it.

## Sample and conversion, reproducible

- Selection rule, applied in file order, no outcome filtering:
  first 20 rows with at least 8 agent actions (model calls).
- Result: 3 resolved, 17 unresolved, 15.0% resolved in this sample.
  This is NOT claimed as representative: the full run is 21.3%
  resolved, first-20-in-file-order is reproducible, not random, and
  the sample is repo-skewed (6 astropy, 14 django, the file's
  opening order). Do not generalize the sample rate.
  Resolved in the sample: django__django-11039, django__django-11099,
  django__django-11133.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/convert.py
  (mechanical only).
- v1.9 format facts, verified by inspection before converting
  (this file differs structurally from the v2.1 Claude file in
  poc-new-16, so that converter was NOT reused blindly):
  - history is a list of [action, observation] pairs, not flat
    dicts with tool_call_metadata/model_response. There is NO
    per-call token usage anywhere in the file.
  - one agent action == one model call: on every selected row,
    len(agent actions) == len(metrics.costs) exactly (asserted
    in the converter; 485 calls total across the sample, 12-30
    per attempt, maxiter 30).
  - row-level "report" is {} for most rows, so the resolved label
    is taken from the run-level report.json resolved_ids list.
    Rows not in that list are unresolved, including empty-patch
    instances (e.g. django__django-11049 in the sample).
- Mapping:
  - case_id = instance_id (asserted distinct in the sample).
  - model = gpt-4o-2024-05-13, provider = openai, exactly as in
    metadata.json's llm_config ("openai/gpt-4o-2024-05-13" with
    the provider prefix stripped, not double-prefixed).
  - one "model" event and one "tool" event per agent action;
    tool name = action (run 153, run_ipython 325, finish 7).
  - tokens are chars/4 ESTIMATES, not recorded usage: input =
    chars of all preceding text (user message, prior action
    messages + args, prior observation messages + content) // 4,
    accumulated in history order and UNTRUNCATED; output = chars
    of this action's message + args JSON // 4. Totals: input
    8,625,870 tokens, output 122,303 tokens.
  - "retry" event before the next model call when an observation
    message matches "executed with exit code N" with N != 0,
    reason "exit code N". A LOWER BOUND: run_ipython observations
    carry no exit code, and editor/test failures without a bash
    exit code are not counted.
  - "end" event success = instance_id in report.json resolved_ids
    (the dataset's test verdict for the run).
- Converted events: 1,080 lines — 485 model, 485 tool, 90 retry,
  20 end. Counts match an independent recount of the events file
  exactly.

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/averth trace
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/events.jsonl
  --format jsonl
  --html ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/report.html
  --agent openhands-eval-gpt4o

- CLI exit code: 0, verified on a separate rerun (identical output
  except the HTML path). No error, no traceback, no unknown-event
  rejection.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run

- Attempts: 20
- Autonomous completions (resolved): 3 (15.0%)
- Failed attempts: 17 (85.0%)
- Retries: 90 — exit code 1: 73, exit code 2: 9, exit code 4: 5,
  exit code 127: 3. These match an independent recount exactly.
- Total cost: $9.96
  - Priced (tokens x vendor prices): $0.00
  - Vendor-supplied (billed): $0.00. No billed cost is claimed.
  - Estimated: $9.96 — model $8.99 at fallback prices plus
    $0.97 built-in per-call tool estimates (485 calls x $0.002).
    The report header therefore reads COST BASIS: ESTIMATED,
    with the do-not-quote-as-a-bill warning.
  - Manual check of the model figure: 8,625,870 x $1.00 +
    122,303 x $3.00, per 1M = $8.9928, matching Averth's $8.99.
- Fully loaded cost per successful outcome (estimated basis):
  $3.32 (model terminal $0.04, retry path $2.95, tool calls
  $0.32, human review $0.00 at the $70.20/hr assumption, not
  measured).
- Failed runs: $9.29 (93% of spend, zero outcomes).
- Retry path: $8.86 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 1% of tokens on the terminal path.
- Context compounding: 103.7x input growth first-to-last step;
  context tax $0.00 (see anomaly 2 — do not quote this as
  "context was free").
- Heavy tail per attempt: p50 $0.40 / p95 $0.98 / max $2.60;
  top 5% consumed 26% of budget. Costliest attempt on model
  spend alone: django__django-11630 at $2.54 (fallback basis).
- Human escalations: 0. Reopened: 0.

## Anomalies noted (do not hide them; none blocked the run)

1. Price-table gap, and it moves the total a lot. Price table v6
   has NO entry for openai:gpt-4o-2024-05-13 (only openai:gpt-4o
   and openai:gpt-4o-2024-08-06), so Averth priced all model spend
   at the documented fallback ($1.00/$3.00 per 1M) and flagged
   openai:gpt-4o-2024-05-13 as unpriced. The snapshot was NOT
   silently remapped to generic gpt-4o: that would have hidden
   the gap. This is the same gap batch-3 agent 20 flagged.
   Consequence: $9.96 UNDERSTATES the run's own cost basis.
   The run's metadata configures $3.00 input / $15.00 output per
   1M; at those rates, the same estimated tokens cost $27.71
   model spend (manual check: 8,625,870 x $3.00 + 122,303 x
   $15.00, per 1M), for a manual total of $28.68 with tools.
   That $28.68 is a manual check, NOT Averth's total and NOT a
   bill: the tokens underneath it are still chars/4 estimates.
2. Context tax $0.00 despite 103.7x growth — the known fallback
   quirk, seen in batch-2/3 lanes: the fallback cost path records
   in_price 0.0, and the context-tax loop skips steps with no
   input price. With a real price entry, context tax would be
   large (at source rates, most of the $27.71 model spend sits
   on repeated context). Do not quote $0.00 as a finding.
3. Reconciliation vs the source's own cost log. Sample sum of
   metrics.accumulated_cost: $22.43, versus Averth's $9.96
   (fallback) and $28.68 (manual, source rates). The manual
   figure exceeds the source log by 28%, as expected: Averth's
   token estimate accumulates observation content UNTRUNCATED,
   while the run configured max_message_chars 10000, so the
   source's API calls saw truncated history. The source figure
   is OpenHands' own cost log, not a vendor bill, and Averth
   does not use it. Neither $9.96 nor $28.68 is what anyone
   was charged.
4. Sample resolved rate (15.0%) is below the full-run rate
   (21.3%), and the sample is repo-skewed (astropy + django
   only). First-20-in-file-order is reproducible but not a
   representative sample, and no claim is made that it is.
5. Retry count is a lower bound (exit-code rule only; see above).
   In particular, run_ipython failures that surface as test
   output rather than a bash exit code are missed.
6. Minor report inconsistency, flagged not smoothed over: the
   text output's top finding says "Retry loops burned $9.38
   (94% of spend)" while the waste-accounting lens says retry
   path $8.86. The file does not explain the $0.52 difference,
   so this file quotes the waste-lens figure ($8.86) for retry
   path and treats $9.38 as a separate insight headline.
7. No "-$0" priced-bucket artifact in this run (priced bucket
   is a clean $0.00), and no "Measured" label appears.

## What this does NOT prove

- No billed cost, no vendor invoice, no recorded tokens: every
  model dollar is a fallback price applied to chars/4 estimated
  tokens, tool dollars are defaults. This run proves Averth can
  ingest and report a new OpenHands/GPT-4o evaluation trajectory
  set by itself, with exit 0, a complete report, and arithmetic
  that checks out against independent recounts. It does not
  prove an operator would use it repeatedly, act on a finding,
  or pay for it.
- No change was tested here. The retry finding (exit code 1,
  73 of 90) is a report output, not a tested fix, and no saving
  is claimed. The honest next step for this lane is a price-table
  fix (verify the gpt-4o-2024-05-13 snapshot price from OpenAI's
  own pages, then add it) and a rerun — at source rates the
  total would roughly triple, which is exactly why the fallback
  total must never be quoted without its basis.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/events.jsonl (1,080 lines)
- Sample list: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/sample.json
- Source files (local copies): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/output.jsonl, report.json, metadata.json
- Averth text output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/averth-output.txt
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-38/report.html

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. The only change is
pricing: `openai:gpt-4o-2024-05-13` is now priced at $2.50/$10.00 per 1M
(OpenAI GPT-4o page, snapshot listed there), where v6 fell back to
$1.00/$3.00. Attempt, resolved (3/20), and retry (90) counts are
unchanged. Old total $9.96 all fallback ESTIMATED -> new total $23.76,
of which priced $22.79 and tool estimates $0.97. Cost per success
$3.32 -> $7.92. Failed $9.29 (93%) -> $22.21 (93%). Context tax $0.00
(fallback quirk) -> $21.02 (92% of model spend). Waste-lens retry path
$8.86 -> $22.45; the top finding now prints $22.97 and decomposes it as
$22.45 model/retry spend plus $0.52 retry-path tool spend, so the old
$9.38-vs-$8.86 gap class is explained, not hidden. The source's own
$22.43 accumulated cost is now close to Averth's $23.76 (the v6 $9.96
was the fallback artifact, not a source disagreement). Still
ESTIMATED (v1.9 format, no per-call usage, output undercounted).
New report: hidden_files/poc-new-38/averth-output-v7.txt.