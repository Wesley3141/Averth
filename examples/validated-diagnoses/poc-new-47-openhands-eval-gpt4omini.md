# POC new-47: OpenHands evaluation, GPT-4o-mini — clean run PASS (not a value POC, not a bill)

**Verdict: PASS as a clean Averth run.** Averth ingests a real public
OpenHands evaluation trajectory set and produces a complete report,
CLI exit 0, with no crash and no fabricated input. This is a
diagnosis test only: no change was applied or measured, no saving is
claimed, and no dollar figure below is a bill.

## Source

- Dataset: OpenHands/openhands-evaluation-outputs,
  https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
- Run folder:
  `outputs/SWE-bench_Lite-test/CodeActAgent/gpt-4o-mini-2024-07-18_maxiter_30_N_v1.9-no-hint-eval-24sep/`
- Model per metadata.json: `openai/gpt-4o-mini-2024-07-18`, run
  2024-10-02, maxiter 30, CodeActAgent, SWE-bench Lite.
- Full run (run report.json): 300 instances, 263 completed,
  23 resolved (7.7%), 240 unresolved, 37 empty-patch. The OpenHands
  paper's earlier 7.0% figure for gpt-4o-mini is close but not
  identical to this run's 7.7%; quote this run's 7.7%, not the paper's.
- Distinct from poc-new-16 (Claude 3.5 Sonnet, v2.1 run) and from
  any GPT-4o run: different model, different run folder, different
  trajectories. Instance-id overlap is NOT zero: 4 of the 20 sampled
  instance_ids also appear in poc-new-16's sample
  (django__django-11099, django__django-11999, django__django-12125,
  django__django-12908), because both runs cover the same 300-instance
  SWE-bench Lite benchmark in file order. The trajectories are
  distinct (different model, different histories); do not claim
  instance-disjointness in the rollup.

## Selection (file order, no outcome filtering)

First 20 rows in file order with at least 8 agent actions
(run / run_ipython / finish). 20 attempts, 457 model calls, 1,012
Averth events (457 model, 457 tool, 78 retry, 20 end).

Sample: django__django-11099, django__django-12125,
sympy__sympy-20212, django__django-14155, django__django-13028,
django__django-11999, django__django-13401, django__django-11848,
sympy__sympy-22005, sympy__sympy-18057, matplotlib__matplotlib-26011,
django__django-10924, django__django-11049, django__django-14752,
matplotlib__matplotlib-23299, pydata__xarray-4248,
sympy__sympy-24152, django__django-12908, django__django-16255,
sphinx-doc__sphinx-8627.

Outcome label: row `report.resolved` when present; rows with
`report == {}` are unresolved. Verified exactly against the run's
report.json (`resolved_ids`, 23 ids): 0 mismatches over all 300 rows
(row-resolved True = 23, empty report = 240, resolved False = 37).

## Conversion (mechanical, in hidden_files/poc-new-47/convert.py)

This v1.9 file differs from poc-new-16's v2.1 file: history is a
list of steps, each step a list of events, and it records NO
per-call token usage. `metrics.costs` holds one dollar figure per
agent action, at the run's proxy rates ($0.17 input / $0.66 output
per 1M per metadata.json llm_config), but no token counts.

- Flatten history steps in order. One model event and one tool
  event (name = action) per agent action.
- input_tokens = (cumulative characters of all prior flat-event
  text) // 4, where text = message for user/agent events and
  content (full observation) for observation events. Cumulative
  history convention, same as the first-batch SWE converters.
- output_tokens = (thought + command/code/outputs text) // 4 for
  that action. This is a severe undercount of real model output:
  the trajectory stores actions, not full model responses (see
  Anomalies).
- Retry before the next model call when an observation carries
  exit_code != 0 (extras.exit_code, or "executed with exit code N").
  Lower bound: IPython observations carry no exit code.
- End success = resolved label above.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6.
- Command: `averth trace events.jsonl --format jsonl
  --agent openhands-gpt-4o-mini --html report.html`
- CLI exit code: 0. No crash, no rejected events, no "Measured"
  label, no "-$0" priced-bucket artifact in this output.

## Results (primary run, base-key alias — read the price-gap note)

- Attempts: 20. Resolved (accepted): 3 (15.0%). Failed: 17.
  The sample's 15% is NOT representative of the full run's 7.7%.
- Total: **$1.71, cost basis ESTIMATED** as printed by Averth.
  Priced (tokens x vendor prices, token provenance unverified):
  $0.80. Vendor-supplied (billed): $0.00. Estimated (built-in tool
  defaults): $0.91. Do not quote $1.71 as a bill.
- Model spend: $0.80, all openai:gpt-4o-mini at $0.15 input /
  $0.60 output per 1M. Tokens: 5,132,358 input, 48,326 output
  (chars/4 estimates, not recorded usage; caching_prompt is false,
  cached tokens 0).
- Cost per successful outcome: $0.57 fully loaded (total / 3).
  Averth's printed split — model terminal $0.0017, retry path
  $0.26, tool calls $0.30 — uses its terminal-path definition for
  the model line; quote the $0.57 fully loaded figure, never the
  $0.0017 terminal line alone.
- Failed runs: $1.58 (92% of spend, zero outcomes).
- Retries: 78 (exit code 1: 43, exit code 2: 28, exit code 127: 7).
  Lower bound; see conversion notes.
- Context compounding: 39.7x input growth first-to-last step;
  context tax $0.74 (92% of model spend).
- Yield: 1% of tokens on the terminal path (Averth's
  terminal-path definition, not the 15% success rate).
- Heavy tail: p50 $0.07 / p95 $0.15 / max $0.27 per attempt;
  top 5% consumed 16% of budget.
- 9 of 20 attempts hit the 30-action maxiter cap; those runs are
  truncated, not completed.

## Reconciliation against the source's own costs

- Source `metrics.accumulated_cost` for exactly these 20
  attempts sums to **$1.09** (resolved attempts: $0.015, $0.034,
  $0.033).
- Averth primary total $1.71 is 57% above the source figure, but
  the two totals are not comparable line by line:
  - Averth model spend $0.80 is 27% BELOW the source's $1.09,
    because output tokens are undercounted (48,326 chars/4 tokens
    from thought + command/code only; real model responses are not
    stored in this v1.9 trajectory) and because Averth uses list
    prices ($0.15/$0.60) while the source used proxy rates
    ($0.17/$0.66).
  - Averth tool defaults $0.91 (457 calls at the built-in $0.002)
    push the total above the source figure. Tool spend is 53% of
    Averth's total and is entirely an estimate, not a measured
    tool cost.
- Conclusion: $1.71 is an Averth estimate with a dominant invented
  tool component and an undercounted output component. It proves
  ingestion and reporting, not what anyone was charged.

## Price-table gap found (diagnostic run, not the primary total)

The source model key `openai:gpt-4o-mini-2024-07-18` is NOT in
price table v6 (only the base `openai:gpt-4o-mini`). A verbatim-key
run of the identical events (events_exact.jsonl, same 457 calls)
exits 0 but totals **$6.19, all fallback**: model $5.28 at the
$1.00/$3.00 fallback plus the same $0.91 tool defaults, with
Averth flagging `unpriced models: openai:gpt-4o-mini-2024-07-18`.
That is 6.6x the priced model spend ($5.28 vs $0.80) and 3.6x the
primary total ($6.19 vs $1.71), purely from the missing dated alias.

The primary run maps the snapshot to the base key because the
snapshot's launch price was the same $0.15 input / $0.60 output
per 1M (OpenAI launch pricing, July 18, 2024; Averth v6 base entry
matches, cached $0.075 unused here). The mapping is documented in
convert.py, not hidden. Parent action for wave 5: add
`openai:gpt-4o-mini-2024-07-18` at $0.15/$0.60, cached $0.075, with a
regression test, then this lane reruns verbatim with no alias.
Until then, never quote the $6.19 fallback total as the lane's
result, and never quote the $1.71 total without the alias note.

## Anomalies and limits (all travel with the number)

1. Tool estimates dominate: $0.91 of $1.71 (53%) is built-in
   per-call defaults, flagged as estimates in the report itself.
2. Output tokens are undercounted by construction (thought +
   command/code only; full model responses are absent from v1.9
   trajectories), so model spend $0.80 is a lower-bound estimate,
   not a reconciled bill.
3. Retry count is a lower bound (bash exit codes only).
4. Yield 1% is Averth's terminal-path token definition, not a
   success rate; the success rate is 15% in-sample, 7.7% full-run.
5. 9 of 20 attempts are maxiter-truncated at 30 actions.
6. No tested change, no saving, no operator, no recipient. This
   lane is a clean-run diagnosis, not a value POC and not
   outreach-ready on its own.

## Files

- This file.
- Converter, events, sample list, CLI outputs, HTML reports:
  `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-47/`
  (convert.py, events.jsonl, events_exact.jsonl, sample.json,
  averth-output.txt, averth-output-exact.txt, report.html,
  report_exact.html, output.jsonl, metadata.json, report.json).
- No one contacted, nothing sent, nothing posted, no private data
  used, nothing fabricated. Aggregates were not converted into
  events; every event comes from a real trajectory step.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $1.71 (priced $0.80, tool estimates $0.91), attempts 20,
resolved 3/20, retries 78, context 39.7x, tax $0.74. Additionally
verified: replacing the converter's mapped model with the verbatim
snapshot key `openai:gpt-4o-mini-2024-07-18` (now priced at
$0.15/$0.60, same rates as the base mini) reproduces $1.71 exactly,
so the base-model mapping is no longer needed. The old "$6.19 if
verbatim" fallback warning is retired. Still ESTIMATED (v1.9 format,
output undercounted). New report:
hidden_files/poc-new-47/averth-output-v7.txt.