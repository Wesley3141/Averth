# POC new-60: OpenHands evaluation, Qwen 2.5 72B Instruct — PASS as a clean-run diagnosis only

## Verdict: PASS (clean Averth run, long-trajectory sample only)

No one contacted, nothing sent, nothing posted, no private data used.
Nothing fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No verified individual recipient is attached to
this file; do not send it to anyone on this file alone.

## Source

- Dataset: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
- Run folder: `outputs/SWE-bench_Lite-test/CodeActAgent/qwen-2.5-72b-instruct_maxiter_30_N_v1.9-no-hint-non-fncall-eval-24sep/`
- Model, per metadata.json: `openrouter/qwen/qwen-2.5-72b-instruct`,
  OpenHands v1.9, CodeActAgent, maxiter 30, run starting 2024-09-29,
  run id 20240930_162705, SWE-bench Lite.
- Full run, per report.json: 300 instances, 23 resolved (7.7%),
  188 unresolved, 88 empty-patch, 1 error, 0 unstopped.
- Distinct from lanes 16 (Claude 3.5 Sonnet v2.1), 38 (GPT-4o
  2024-05-13 v1.9), and 47 (GPT-4o-mini v1.9): different model,
  different run folder, different trajectories. Instance-id
  overlap is NOT zero and must not be claimed: 8 of the 20
  instance ids also appear in lane 16, 6 in lane 38, and 3 in
  lane 47, because all four runs cover the same 300-instance
  SWE-bench Lite benchmark in file order. The trajectories are
  distinct (different model, different histories); the issues
  are not new.

## Selection rule, and the bias it creates — read first

Rule, applied blindly in file order, no outcome filtering:
first 20 rows with at least 8 agent actions in
(run, run_ipython, finish, message), i.e. at least 8 model calls
by the run's own costs count. That count is verified: in the
selected sample, agent actions in that set equal
len(metrics.costs) exactly for all 20 rows.

Consequence, verified, not hidden: the sample is 0 of 20
resolved, and that is NOT a Qwen solve rate. The early resolved
rows in file order are short: file indices 4, 6, 10, and 16 are
resolved with 5, 6, 6, and 5 model calls, so the >=8 rule
excludes every early success. The first 20 rows in file order
with NO call-count filter are 4 of 20 resolved, and the full
run is 23 of 300 (7.7%). This lane is a diagnosis of 20 long
failed trajectories (8 to 30 calls each), not a measurement of
Qwen 2.5 on SWE-bench Lite. Any rollup that quotes "0%" without
this paragraph is misquoting this file.

Sample (20, all django except 3 astropy, file order):
django__django-12700, -11999, -13447, -12983, -13321, -11283,
-12708, -12113, -12747, -13265, -13660, -13768, -11179, -14155,
-13590, -11099, -11583; astropy__astropy-7746, -12907, -6938.
Five attempts have no finish action (11283, 12708, 12747, 13768,
14155); their end label is still the run's own report (False),
not an Averth inference.

## Conversion, mechanical

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-60/`
(convert.py, events.jsonl, sample.json, averth-output.txt,
report.html, output.jsonl, report.json, metadata.json,
run_id.txt).

- One row = one attempt, case_id = instance_id, asserted
  distinct in the sample.
- Model events: one per agent action in (run, run_ipython,
  finish, message). Message actions count because the run's
  costs list counts them (see above); 11 message actions in
  the sample. Message actions get a model event only, no tool
  event, because a message to the user is not a tool call.
- Tool events: one per run/run_ipython/finish action only:
  run_ipython 252, run 60, finish 9, total 321.
- input_tokens = cumulative prior flat-event text // 4, where
  text = message for user/agent events and content (full
  observation) for observation events. Same cumulative-history
  convention as lanes 38/47, UNTRUNCATED (unlike the run's own
  10000-char message cap). Output_tokens = thought + command /
  code / outputs / message content, // 4, for that action.
- Tokens are NOT recorded in this file, so all tokens are
  chars/4 estimates. No cache counts exist, so no cache
  discount is applied.
- Retry event before the next model call when an observation
  carries exit_code != 0 (extras.exit_code, or the message
  "executed with exit code N"). Lower bound: IPython
  observations carry no exit code, so editor/test failures
  without a bash exit code are not counted. Many failed
  attempts therefore show 0 retries; 0 retries does not mean
  "no failures happened".
- End event: success = row report resolved, verified exactly
  against report.json resolved_ids over all 300 rows:
  0 mismatches (row-resolved True = 23, matching
  report.json resolved_instances = 23). Empty-patch rows are
  unresolved, not missing.
- Model naming, documented: source model string
  openrouter/qwen/qwen-2.5-72b-instruct, event model
  "qwen-2.5-72b-instruct", provider omitted. Averth's
  guess_provider returns "unknown" for it, so the key is
  unknown:qwen-2.5-72b-instruct. Price table v6 has NO Qwen
  entry at all, so Averth prices it at the documented fallback
  ($1.00/$3.00 per 1M) and flags it unpriced. No price
  invented, no remap to another vendor.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "openhands-qwen25-72b" --anomaly`
- CLI exit code: 0, no crash, no error. Direct rerun not
  needed: the output below is from the run itself, and the
  per-attempt totals recomputed from events.jsonl match it
  exactly (see cross-checks).
- Events: 712 total (332 model, 321 tool, 39 retry, 20 end).
  Model calls sum to 332, matching the source costs count
  for the sample exactly.
- Attempts: 20. Autonomous completions (run's own labels):
  0 (0.0%). Failed: 20.
- Total cost: $2.91.
- Cost basis, as printed by Averth itself: ESTIMATED.
  Priced (tokens x vendor prices, token provenance
  unverified) -$0 (see anomaly 1); vendor-supplied (billed)
  $0.00; estimated (fallback prices) $2.91, of which model
  $2.26 at fallback and tool $0.64 in built-in per-call
  estimates (321 calls x $0.002). Model spend is 100%
  unknown:qwen-2.5-72b-instruct.
- Cost per successful outcome: Averth prints $0.00 on every
  line (terminal, retry path, tool, fully loaded). That is
  VACUOUS with 0 successes: read it as UNKNOWN, never as
  "$0 per success" (same artifact lanes 13 and 32 flagged).
- Five layers: context compounding 29.6x first-to-last step,
  context tax $0.00 (see anomaly 2); tool spend $0.64;
  yield 0% of tokens on the terminal path (definitional with
  0 successes, not a success rate); heavy tail p50 $0.11 /
  p95 $0.28 / max $0.38 per attempt, top 5% consumed 13%.
- Failed runs: $2.91 (100% of spend, zero outcomes). Retry
  path: $2.26 model+retry spend on discarded paths
  (overlapping lens, not additive). Retries: 39, all exit
  code: 1 x29, 2 x7, 123 x3.
- Costliest attempt: django__django-11999, $0.38 (3x p50),
  30 model calls, 7 retries, context grew 67.4x, flagged
  runaway-shaped by --anomaly. Next: astropy__astropy-7746,
  $0.27, 22 calls, 0 retries; django__django-11179, $0.25,
  30 calls, 15 retries (most retries in the sample).

## Anomaly check

1. "-$0" priced bucket: PRESENT. The priced bucket prints
   -$0, a tiny negative float, not $0. Pre-existing display
   artifact, repeatedly noted in earlier lanes, still
   unfixed. Do not quote -$0 as a cost.
2. Context tax $0.00 despite 29.6x growth: the known
   fallback-pricing quirk. The fallback cost path records
   in_price 0.0, and the context-tax loop skips steps with
   no input price, so a fallback-priced run shows large
   context growth with $0.00 context tax. Do not quote it
   as "context was free".
3. Top-finding vs waste-lens gap: the text output's top
   finding says "Retry loops burned $2.44 (84% of spend)"
   while the waste lens says retry path $2.26. The $0.18
   gap is unexplained in the output; this file quotes the
   waste-lens $2.26 figure and flags the gap, as lane 38
   did for its $0.52 gap. Same report inconsistency, still
   unfixed.
4. No "Measured" label anywhere: the report's cost basis
   is ESTIMATED, with the do-not-quote-as-a-bill warning
   printed.
5. Yield 0% and "failed runs burned 100%" are definitional
   with 0 successes in a >=8-call sample, not evidence
   that Qwen never solves anything (full run: 7.7%).

## Reconciliation vs the source's own cost (the honest comparison)

- Source accumulated_cost, summed over exactly these 20
  rows: $1.3719. Averth $2.91 is 2.12x that.
- Decomposition: Averth model $2.26 is at fallback rates
  ($1.00/$3.00), not the run's rates. Independent check
  from events.jsonl: 2,179,146 input + 28,282 output tokens
  (chars/4 estimates); at fallback, 2.179146 x $1.00 +
  0.028282 x $3.00 = $2.2640, matching Averth's $2.26.
- Manual check at the run's own proxy rates ($0.35 input /
  $0.40 output per 1M, from metadata.json llm_config):
  2.179146 x $0.35 + 0.028282 x $0.40 = $0.7741 model.
  With the $0.64 tool defaults, that is $1.42 total, close
  to the source $1.37 (+3.2%) only because the tool
  defaults fill the gap: the model part alone is 44% below
  the source ($0.77 vs $1.37). The chars/4 convention used
  here (message text only for agent actions, not full args)
  undercounts the prompt the run actually sent, and output
  tokens (28,282 total, ~85 per call) are far below what a
  real 72B call would emit. Do not quote $2.91, $1.42, or
  $1.37 as a bill; $1.37 is OpenHands' own proxy-rate cost
  log, not a vendor invoice, and $2.91 is Averth's fallback
  estimate on estimated tokens.

## Limits that must travel with this number

- 0 of 20 resolved is NOT a Qwen rate, an OpenHands rate,
  or a SWE-bench Lite rate. It is the outcome of 20 long
  trajectories (8-30 calls) selected by a call-count rule
  that excludes the run's short successes. Full run:
  23/300 (7.7%).
- Sample is django-heavy (17 django, 3 astropy) by file
  order, not by design.
- Tokens are chars/4 estimates, not recorded usage;
  dollars are fallback estimates plus tool defaults, not
  a bill. The Qwen price gap is a price-table gap, not a
  model finding: until a verified Qwen 2.5 72B price is
  added with a regression test, never quote $2.91 without
  its fallback basis, and never quote the proxy-rate $1.42
  as Averth's total.
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), CLI exit 0, totals
  reported, honest ESTIMATED cost basis, anomalies
  disclosed. Not a value POC: no change was applied or
  measured, no saving claimed, no operator, no billed cost.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $2.91, all ESTIMATED at fallback, because
unknown:qwen-2.5-72b-instruct could NOT be verified from a vendor
page (open-weight, provider-varying proxy prices) and was left
unpriced. Attempts 20, resolved 0/20, retries 39, context 29.6x,
context tax now n/a instead of $0.00. Two display fixes verified on
this lane: the priced bucket now renders "$0", not the old "-$0"
artifact, and cost per success is still vacuous with 0 successes
(read as UNKNOWN, never "$0 per success"). The 0/20 bias note is
unchanged: the >= 8-call rule excludes every early success. New
report: hidden_files/poc-new-60/averth-output-v7.txt.