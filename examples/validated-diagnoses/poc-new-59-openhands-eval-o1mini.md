# POC new-59: OpenHands evaluation, o1-mini — PASS as a clean-run diagnosis

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
Nothing fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No tested change, no saving claimed, no verified
individual recipient attached.

## Source

- Dataset: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
- Run folder:
  `outputs/SWE-bench_Lite-test/CodeActAgent/o1-mini-2024-09-12_maxiter_30_N_v1.9-no-hint-eval-24sep/`
- Model: folder name `o1-mini-2024-09-12`; `metadata.json`
  `llm_config.model` is `openai/neulab/o1-mini`, run start
  2024-10-03, maxiter 30, OpenHands v1.9, CodeActAgent,
  SWE-bench Lite, temperature 0.0, `max_message_chars` 10000,
  `caching_prompt` false.
- Full run, from `report.json`: 300 instances, 57 resolved
  (19.0%), 207 unresolved, 36 empty-patch, 264 completed,
  0 error. This is a different model and a different run from
  batch-1 POC 02 (SWE-Gym sampled, GPT-4o-2024-08-06), poc-new-09
  (nebius Qwen), poc-new-16 (Claude 3.5 Sonnet v2.1), poc-new-38
  (GPT-4o-2024-05-13 v1.9), and poc-new-47 (GPT-4o-mini-2024-07-18
  v1.9).

## Selection, mechanical, no outcome filtering

First 20 rows in file order with at least 8 agent actions
(model calls). Resolved labels come from run-level
`report.json` resolved_ids, not from the row, because row-level
`report` is `{}` for most rows. Verified: row
`report.resolved` (`{}` treated as False) matches resolved_ids
membership on all 300 rows, 0 mismatches. Empty-patch instances
are therefore unresolved, not missing.

Sample (20 attempts, 6 astropy + 14 django):
astropy__astropy-12907, -14182, -14365, -14995, -7746, -6938;
django__django-11001, -11039, -11099, -11049, -11564, -10924,
-11583, -10914, -11742, -11815, -11179, -11283, -11630, -11910.
Resolved: 7 of 20 (35.0%). That is NOT representative of the
full run (19.0%) and must not be quoted as an o1-mini solve rate:
it is the first 20 file-order rows, including three 8-action
quick successes (django-11039, django-11099, django-10914).

## Conversion, mechanical

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-59/`
(`convert.py`, `events.jsonl`, `sample.json`, `averth-output.txt`,
`report.html`, plus verbatim `output.jsonl`, `report.json`,
`metadata.json`).

- One file = one attempt, case_id = instance_id (asserted
  distinct in the sample).
- History is a list of [action, observation] steps (v1.9), not
  flat dicts with model_response. There is NO per-call token
  usage anywhere, so all tokens below are chars/4 estimates.
- One model event per agent action (source == "agent", action
  not None; user message actions excluded), one tool event per
  agent action. Tool mix: run_ipython 245, run 106, finish 20,
  message 1.
- input_tokens = chars of all preceding text // 4 (user message,
  prior action messages + args, prior observation messages +
  content, accumulated in history order, UNTRUNCATED, unlike the
  run's own 10000-char message cap).
- output_tokens = chars of this action's text // 4 (message +
  JSON of args: thought, command or code).
- Retry before the next model call when an observation carries
  exit_code != 0 (`extras.exit_code`, or message "executed with
  exit code N", N != 0). A LOWER BOUND: run_ipython observations
  carry no exit code, so editor/test failures without a bash
  exit code are not counted.
- End event: success = instance_id in report.json resolved_ids.
- Model key, verbatim, no silent remapping: provider `openai`,
  model `o1-mini` (folder o1-mini-2024-09-12, metadata
  openai/neulab/o1-mini). Averth price table v6 has NO entry
  for `openai:o1-mini` or any o1 key, so Averth prices it at the
  documented fallback estimate and flags it unpriced. See the
  price-table gap below.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "OpenHands o1-mini" --anomaly`
- CLI exit code: 0, no crash, no error, confirmed on a separate
  direct rerun (identical totals: 20 attempts, 7 completions,
  44 retries, $4.43 total).
- Events: 808 total (372 model, 372 tool, 44 retry, 20 end).
- Attempts: 20. Autonomous completions (dataset resolved
  labels): 7 (35.0%). Failed: 13.
- Total cost: $4.43.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $0.00;
  vendor-supplied (billed) $0.00; estimated (fallback prices)
  $4.43, of which model $3.68 at fallback $1.00/$3.00 per 1M and
  tool $0.74 built-in per-call estimates (372 calls x $0.002).
  Cost per successful outcome (fully loaded): $0.63
  (terminal $0.08, retry path $0.44, tool $0.11, human $0.00 at
  the assumed $70.20/hr rate).
- Five layers: context compounding 35.4x first-to-last step,
  context tax $0.00 (see anomaly 1); yield 15% of tokens on the
  terminal path (85% burned on retries and failed runs); heavy
  tail p50 $0.15 / p95 $0.49 / max $0.97 per attempt, top 5%
  consumed 22% of budget; model mix openai:o1-mini $3.68 (100%
  of model spend).
- Failed runs: $3.37 (76% of spend, zero outcomes). Retry path
  (waste lens): $3.10 model+retry spend on discarded paths
  (overlapping lens, not additive). Retries: 44, all exit-code
  reasons: exit code 1 x32, exit code 2 x10, exit code 4 x2.
- Costliest attempt: django__django-11630, $0.97 (6x p50),
  unresolved, 3 retries, context grew 127.3x, flagged
  runaway-shaped by --anomaly.
- Independent recomputation from events.jsonl matches Averth
  exactly: input 3,499,268 + output 61,320 chars/4 tokens at
  fallback $1/$3 per 1M = $3.68 model; 372 tools x $0.002 =
  $0.74; total $4.43. Resolved-attempt spend $1.06, failed
  $3.37, matching the CLI.

## Reconciliation vs the source's own cost (read this first)

- Source `metrics.accumulated_cost` summed over exactly these
  20 attempts: $23.78. Averth's $4.43 is 81% below it.
- Manual check at the run-configured rates, NOT Averth's total:
  the same 3,499,268 input + 61,320 output tokens at
  metadata.json's $3.00 input / $12.00 output per 1M = $11.23
  model, $11.98 with the $0.74 tool defaults. That is still
  50% below the source's $23.78.
- Why both Averth figures understate the source: o1 models
  generate hidden reasoning tokens that are billed as output
  but do not appear in trajectory text. Our output count
  (61,320 tokens, visible action text only) cannot contain
  them. Per call, the source averages $23.78 / 372 = $0.064,
  while the manual $3/$12 visible-text figure averages $0.030
  — the missing ~$0.034 per call is consistent with roughly
  2,800 hidden reasoning/output tokens per call at $12/1M,
  a hypothesis, not a measured token count. The run's 10000-char
  message truncation also makes the source's own prompt
  accounting differ from our untruncated chars/4 accumulation.
- Do NOT quote $4.43, and do NOT quote $11.98, as what anyone
  was charged. The source $23.78 is itself OpenHands' own cost
  log at configured rates, not a vendor invoice. This lane's
  honest statement is: Averth ingests and reports the o1-mini
  run cleanly at exit 0, but its visible-text token estimate
  materially understates an o1 reasoning model's cost, so the
  dollar figure is a lower-bound estimate only.

## Price-table gap (wave-5 action)

- `openai:o1-mini` is absent from price table v6, so all model
  spend fell back to $1.00/$3.00 and was flagged
  `unpriced models: openai:o1-mini`. The snapshot was NOT
  remapped to another model.
- The run-configured $3.00/$12.00 per 1M matches o1-mini's
  launch pricing as reported by secondary sources citing
  OpenAI's pricing page, but that was NOT verified against
  OpenAI's own current page in this lane, and o1-mini pricing
  may since have changed. Before adding an alias, verify
  `openai:o1-mini` (and `openai:o1-mini-2024-09-12`) from
  OpenAI's own pages and add a regression test, per the
  pricing-table discipline. Even after an alias is added,
  rerunning this lane will still understate the source, for
  the reasoning-token reason above — the alias fixes the
  price, not the missing tokens.

## Anomaly check

1. Context tax $0.00 despite 35.4x growth — the known
   fallback-pricing quirk (fallback path records in_price 0.0,
   the context-tax loop skips it). Do not quote it as
   "context was free."
2. Report inconsistency, same pattern as poc-new-38: the top
   finding says "Retry loops burned $3.46 (78% of spend)"
   while the waste lens says retry path $3.10. The file quotes
   the waste-lens $3.10 and flags the unexplained $0.36 gap.
   Waste figures are overlapping lenses, not additive, but the
   two retry figures should agree and do not.
3. Cost-count mismatch in the sample: astropy__astropy-6938 has
   17 agent actions but 16 source costs — the extra action is
   a `message` action (the only message tool event in the
   sample), which the source cost list apparently does not
   count. Over all 300 rows, 43 rows have action count !=
   cost count (42 off by 1, 1 off by 28: django__django-12700,
   29 actions vs 1 cost, not in this sample). One agent action
   == one model call is therefore approximate for this run,
   not exact.
4. No "-$0" priced-bucket artifact (priced bucket is $0.00,
   a real zero, not a tiny negative float) and no "Measured"
   label anywhere: the report's cost basis is ESTIMATED, with
   the do-not-quote-as-a-bill warning printed.
5. Retry count is a lower bound (bash exit codes only).

## Overlap audit (do not claim instance-disjointness)

Instance-id overlap is HIGH, because every OpenHands
SWE-bench Lite lane covers the same 300-instance benchmark in
file order. Trajectories are distinct (different model, different
run folder, different histories), but the issues are not new:
- vs poc-new-16 (Claude 3.5): 10 of 20 ids overlap.
- vs poc-new-38 (GPT-4o-2024-05-13): 16 of 20 ids overlap.
- vs poc-new-47 (GPT-4o-mini-2024-07-18): 3 of 20 ids overlap.
This lane adds an o1-mini run of known issues, not a new issue
set. The rollup must count it as a model run, not as 20 new
issues.

## Limits that must travel with this number

- 7 of 20 resolved is NOT a general o1-mini solve rate: 20
  first file-order instances (6 astropy, 14 django), one model,
  one scaffold, vs 57 of 300 (19.0%) for the full run.
- Tokens are chars/4 estimates from visible text only, not
  recorded usage; reasoning tokens are missing, so model spend
  is a lower-bound estimate even at vendor list prices.
- Tool spend ($0.74) is entirely built-in per-call defaults,
  not a measured tool bill.
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), CLI exit 0, totals reported,
  honest ESTIMATED cost basis, price gap and reasoning-token
  understatement disclosed. Clean-run diagnosis only: no change
  was applied or measured, and no recipient was verified, so
  this is not ready to send to anyone.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. `openai:o1-mini`
and its snapshot `openai:o1-mini-2024-09-12` are now priced at
$1.10/$4.40 per 1M (OpenAI o1-mini page). Attempt, resolved (7/20),
and retry (44) counts are unchanged. Old total $4.43 all fallback
ESTIMATED -> new total $4.86, of which priced $4.12 and tool estimates
$0.74. Cost per success $0.63 -> $0.69. Failed $3.37 (76%) -> $3.69
(76%). Context tax $0.00 (fallback quirk) -> $3.63 (88% of model
spend). Waste-lens retry path $3.10 -> $3.46. Source recorded $23.78:
Averth is still far below it, consistent with hidden o1 reasoning
tokens billed as output but absent from trajectory text, plus the
10,000-char message truncation; pricing the key does not fix that
undercount, and the gap is still disclosed, not explained away. Still
ESTIMATED. New report: hidden_files/poc-new-59/averth-output-v7.txt.