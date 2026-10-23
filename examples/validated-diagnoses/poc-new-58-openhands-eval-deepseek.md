# POC new-58: OpenHands evaluation, DeepSeek — PASS (clean run, fallback-priced)

## Verdict: PASS as a clean-run diagnosis only

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No change was applied or measured, and no saving
is claimed.

## Source

- Dataset: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
- Run folder: `outputs/SWE-bench_Lite-test/CodeActAgent/deepseek-chat_maxiter_100_N_v2.2-no-hint-main-non-fncall-run_1`
- Model: `deepseek/deepseek-chat` per metadata.json, CodeActAgent,
  maxiter 100, run starting 2024-11-09. This is a different run from
  poc-new-15 (nvidia Open-SWE-Traces, DeepSeek-V4-Flash-0731), from
  poc-new-16 (OpenHands Claude 3.5 Sonnet), from poc-new-38 (OpenHands
  GPT-4o-2024-05-13), and from poc-new-47 (OpenHands GPT-4o-mini).
  The other DeepSeek folder in the same dataset,
  `deepseek-v2.5_maxiter_30_N_v1.9-no-hint-eval-24sep`, was not used.
- Full run: 300 instances, 23 resolved (7.7%), 73 empty-patch
  instances, 0 error instances, per output.swebench_eval.md.
  The resolved set in that file matches the per-row `report.resolved`
  field exactly (23/23, 0 mismatches).

## Selection, mechanical, no outcome filtering

First 20 rows in file order with at least 8 unique model calls.
20 attempts, 20 distinct instance_ids:

astropy__astropy-14182, django__django-13658, django__django-11049,
django__django-13230, astropy__astropy-7746, django__django-11133,
django__django-11583, django__django-11019, django__django-10924,
django__django-11039, django__django-11001, astropy__astropy-14365,
astropy__astropy-14995, django__django-10914, django__django-11283,
django__django-11099, django__django-11179, django__django-11742,
django__django-11564, django__django-12113.

The sample is 14 django + 6 astropy in file order. It is not
representative of SWE-bench Lite generally, and 1/20 resolved below
is not a DeepSeek rate; the full run is 23/300 (7.7%).

## Conversion, mechanical (mirroring poc-new-16)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-58/`
(convert.py, events.jsonl, sample.json, averth-output.txt, report.html,
plus the source output.jsonl, metadata.json, and
output.swebench_eval.md).

- One model event per UNIQUE model_response id. Each model call
  appears twice in history (action event + observation event with
  the identical model_response id); only the action event is kept,
  so no call is double-counted.
- Recorded tokens, NOT chars/4 estimates: input_tokens =
  usage.prompt_tokens, cached_input_tokens =
  usage.prompt_tokens_details.cached_tokens (falling back to
  prompt_cache_hit_tokens), output_tokens = usage.completion_tokens.
- One tool event per model call, name = tool_call_metadata
  function_name (execute_bash 140, str_replace_editor 140, finish 6).
- Retry event before the next model call when an observation
  message matches "executed with exit code N" with N != 0. A lower
  bound: editor errors and test failures without a bash exit code
  are not counted.
- End event: success = report.resolved, the dataset's test verdict.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "OpenHands DeepSeek" --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 643 total (286 model, 286 tool, 51 retries, 20 end).
  Retries: exit code 1: 46, exit code 127: 3, exit code 123: 1,
  exit code 130: 1.
- Attempts: 20. Resolved: 1 (5.0%), django__django-13658. Failed: 19.
- Total: $1.20, cost basis ESTIMATED as printed by Averth.
  Priced (tokens x vendor prices): $0.00. Vendor-supplied (billed):
  $0.00. Estimated (fallback prices): $1.20, of which model $0.63
  and built-in tool estimates $0.57 (286 calls x $0.002).
- Cost per successful outcome, fully loaded: $1.20 (the total
  divided by 1 success; Averth's components: terminal $0.03,
  retry path $0.60, tools $0.57, human $0.00 at the assumed
  $70.20/hr rate). The resolved attempt's own metered cost,
  recomputed from the events file, is $0.06; $1.20 is not the
  cost of that one attempt, it is the whole sample's spend
  carried by one success.
- Failed runs: $1.14 (95% of spend, zero outcomes).
- Five layers: context compounding 4.0x first-to-last step,
  context tax $0.00 (see anomaly below); yield 3% of tokens on
  the terminal path (97% burned on retries and failed runs);
  heavy tail p50 $0.05 / p95 $0.13 / max $0.14 per attempt
  (costliest: django__django-11742, $0.14, flagged runaway-shaped
  by --anomaly, 6 retries, context 7.5x); top 5% consumed 11%.
- Tokens: input 3,282,517, cached 3,067,904 (93.5% of input),
  output 35,803. Cache saving printed by Averth: $2.76
  (cached tokens priced at 10% of the fallback input rate).

## Price-table gap that moves the total (read before quoting $1.20)

Averth price table v6 has NO DeepSeek entry (verified by grep of
averth/pricing.py). The model key deepseek:deepseek-chat is
therefore unpriced and falls back to the documented $1.00/$3.00
per 1M, with cached tokens at the tracker's 10% cache-read
discount. Independent check of the fallback math:
(3,282,517 - 3,067,904)/1M x $1.00 + 3,067,904/1M x $0.10 +
35,803/1M x $3.00 = $0.63, matching Averth's model spend.
No DeepSeek price was invented and no snapshot was remapped to
another vendor's model. $1.20 must never be quoted without its
fallback basis: DeepSeek's actual list prices are far below the
generic $1.00/$3.00 fallback, so a verified DeepSeek price-table
entry (from DeepSeek's own pricing page, not from search snippets)
would lower the model figure substantially. That is a wave-5
price-table action, not a number in this file.

## Reconciliation vs the source's own cost log

- The source's metrics.costs list double-counts every cost: each
  cost appears twice in adjacent pairs, and accumulated_cost
  equals the sum of the duplicated list (verified on the sample
  rows: every costs list has even length with equal pairs).
  Summed over exactly these 20 attempts, accumulated_cost is
  $0.1713; deduped (halved) it is $0.0856.
- Averth's fallback model spend ($0.63) is about 7.4x the deduped
  source log ($0.0856). That gap is the fallback-rate gap above,
  not an Averth arithmetic error: Averth's fallback math checks
  out exactly, and its tool defaults ($0.57, 48% of the total)
  are built-in estimates on top of it. Neither $1.20 nor $0.0856
  is a vendor bill; the source figure is OpenHands' own cost log
  at rates it does not state in metadata.json (input_cost_per_token
  and output_cost_per_token are both null there).
- One source-cost artifact: django__django-11049 is flagged
  empty_generation and its source accumulated_cost is $0.00,
  yet it has 14 recorded model calls with 131,138 prompt tokens.
  Averth prices those tokens at fallback like any other call;
  the $0.00 source figure for that row is not a real $0 bill.

## Anomalies, not hidden

- No "-$0" priced-bucket artifact: the priced bucket is $0.00,
  a real zero because nothing was priced.
- Context tax $0.00 despite 4.0x growth: the known fallback-pricing
  quirk (the fallback path records in_price 0.0, so the
  context-tax loop skips it). Do not quote it as "context was free."
- Report inconsistency, same pattern as poc-new-38: the text
  output's top finding says "Retry loops burned $0.95 (79% of
  spend)" while the waste-accounting lens says retry path $0.60.
  This file quotes the waste-lens $0.60; the $0.35 gap between
  the two lenses is unexplained in the output and is flagged
  for a report-wording fix, not resolved here.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- 7 of 20 sample rows are flagged empty_generation
  (django__django-11049, -13230, -11133, -11019, -11039,
  astropy__astropy-14995, django__django-11179): runs that
  produced no patch. They drive the 1/20 rate as much as test
  failures do, and 19/20 failed must not be read as "19 tasks
  tried and failed on tests."

## Overlap audit

- Trajectory overlap with earlier lanes: zero. This is a new
  DeepSeek run with its own histories and model_response ids.
- Instance-id overlap is NOT zero, because all OpenHands Lite
  runs cover the same 300-instance benchmark in file order:
  9 of 20 ids also appear in poc-new-16's Claude sample
  (astropy__astropy-14182, -14365, django__django-10914,
  -11001, -11039, -11099, -11133, -11283, -11742) and 3 of 20
  in poc-new-47's GPT-4o-mini sample (django__django-10924,
  -11049, -11099). Do not claim instance-disjointness for this
  lane; the trajectories are distinct, the benchmark issues are
  shared.

## Limits that must travel with this number

- 1/20 resolved is NOT a DeepSeek, OpenHands, or SWE-bench rate.
  It is this file-order sample (14 django + 6 astropy, 7 empty
  generations) under one model run. The full run is 23/300.
- $1.20 is not a bill, not measured spend, and not a saving.
  It is fallback prices on recorded tokens plus tool defaults.
  At a verified DeepSeek price the model part would be lower.
- Tool spend ($0.57, 48% of the total) is entirely built-in
  per-call estimates, not a measured tool bill.
- PASS criteria met: real per-step input (20 full trajectories
  with recorded usage, not aggregates), CLI exit 0, totals
  reported, honest ESTIMATED cost basis, anomalies disclosed.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $1.20, all ESTIMATED at fallback, because
deepseek:deepseek-chat could NOT be verified from DeepSeek's own
pricing page and was deliberately left unpriced (the alias was
retired July 2026 and current DeepSeek pricing is peak/off-peak
dual, so no single standard rate exists to pin). Attempts 20,
resolved 1/20, retries 51, context 4.0x, context tax now n/a (input
prices missing for fallback calls) instead of the old $0.00. Still
ESTIMATED (recorded tokens, fallback rates). New report:
hidden_files/poc-new-58/averth-output-v7.txt.