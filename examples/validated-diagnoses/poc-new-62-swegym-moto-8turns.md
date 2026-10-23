# POC new-62: SWE-Gym moto slice, at least 8 assistant turns — PASS, usable diagnosis

## Verdict: PASS as a clean-run diagnosis, replacing poc-new-32

No one contacted, nothing sent, nothing posted, no private data used.
Nothing fabricated. This is a diagnosis run, not a value pitch and
not a send draft. It replaces poc-new-32, which was 20/20 empty
generations and was explicitly not counted as a usable moto
diagnosis. This lane is usable for what it is: 20 genuine, long
moto attempts under one GPT-4o run, with resolved labels. It is
not a general moto solve rate, and it adds no new moto issue
(see Overlap audit).

## Source

- Dataset: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (train.raw, 6,055 rows across 3 parquet shards, OpenHands
  CodeActAgent v2.1 trajectories).
- Moto rows in the dataset: 1,150 total (shard 0: 619, shard 1: 458,
  shard 2: 73), across 8 run_ids, per poc-new-32's scan.
- Selection rule, pre-registered, fixed before looking at
  outcomes: moto rows only (instance_id contains "moto"), shards
  in file order, first 20 rows in file order WITH at least 8
  assistant messages. This is a length filter, not an outcome
  filter: resolved labels were taken as-is after selection.
- Why the first 20 moto rows do not appear: the first 20 moto
  rows in shard 0 (the poc-new-32 sample) all have 4-6 assistant
  turns, so none qualifies. The first qualifying row is the
  21st moto row in shard 0. All 20 qualifying rows are in
  shard 0, so no shard 1/2 rows were needed.
- All 20 share run_id
  gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1,
  the same run as poc-new-32, but different rows.
- Issues (20): getmoto__moto-6470, -6114, -6387, -5835, -7111,
  -6508, -7348, -6041, -6585, -6913, -5980, -5865, -5134, -5417,
  -5899, -6408, -6308, -5960, -7273, -7484.
- Assistant turns per attempt: 10-30, mean 23.1. This is not a
  view-only sample: the shortest attempt has 10 assistant turns.

## Empty-generation rate: 1 of 20 (5%), below the 50% bias bar

- Dataset flag test_result.report.empty_generation is True for
  exactly 1 row: getmoto__moto-6470 (28 assistant turns,
  unresolved). That row is long, not a 4-turn view-only run, so
  here the flag means no patch was produced, not that the agent
  never got started. It costs $0.70 model spend in this run,
  not a driver of the totals.
- The other 19 rows are not flagged empty. The sample is
  therefore not an empty-generation block, unlike poc-new-32
  (20/20 empty, $0.38 total, no patch, no test run).

## Conversion, mechanical (same rules as poc-new-32)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-62/`
(convert.py, scan.py, scan.json, events.jsonl, sample.json,
cli-output.txt, report.html).

- One row = one attempt, case_id = run_id + "__" + instance_id.
- Model: run_id prefix gpt-4o-2024-08-06 -> Averth key
  openai:gpt-4o-2024-08-06 (price table v6, $2.50 input / $10.00
  output per 1M, the vendor list price for that snapshot).
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool-call argument chars)//4), then one tool
  event per tool call (function name).
- retry event before the next assistant turn when the preceding
  tool observation contains "Traceback", a recorded failure signal.
- end event: success = row "resolved" (matches
  test_result.report.resolved in the source).
- Tokens are NOT recorded in this dataset, so all tokens are
  chars//4 estimates. No cache counts exist, so no cache discount
  is applied. Tool spend is Averth's built-in per-call estimate,
  not a measured tool bill.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6.
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "SWE-Gym moto >=8 turns"`
- CLI exit code: 0, no crash, no error.
- Events: 973 total (462 model, 449 tool, 42 retries, 20 end).
  Tool mix: str_replace_editor 313, execute_bash 124, finish 12.
  Model events exceed tool events because 13 assistant turns
  carry no tool call.
- Attempts: 20. Autonomous completions (dataset resolved labels):
  7 (35.0%). Failed: 13.
- Total cost: $13.12.
- Cost basis, as printed by Averth itself: ESTIMATED.
  Priced (tokens x vendor prices, token provenance unverified)
  $12.22; vendor-supplied (billed) $0.00; estimated
  (fallback/tool) $0.90, which is entirely built-in tool
  per-call estimates (449 x $0.002 = $0.898). Model spend
  $12.22 is openai:gpt-4o-2024-08-06 at list prices applied to
  4,647,022 input + 60,238 output chars//4 estimated tokens
  (4,647,022/1M x $2.50 + 60,238/1M x $10.00 = $12.22,
  independently recomputed). It sits in Averth's "Priced"
  bucket, but the tokens are estimates, not recorded usage,
  and Averth's own COST BASIS banner says so. Do not quote
  $13.12, or its $12.22 model part, as a bill or as measured
  spend.
- Cost per successful outcome, fully loaded: $1.87
  (terminal $0.23, retry path $1.51, tool $0.13, human $0.00
  at the assumed $70.20/hr rate, not measured).
- Five layers: context compounding 16.8x first-to-last step,
  context tax $10.34 (85% of model spend); yield 13% of tokens
  on the terminal path (87% burned on retries and failed runs);
  heavy tail p50 $0.64 / p95 $1.13 / max $1.17 per attempt;
  top 5% consumed 9% of budget.
- Failed runs: $9.68 (74% of spend, zero outcomes). Retry path:
  $10.59 model+retry spend on discarded paths (overlapping
  lens, not additive). Retries: 42, all "traceback in previous
  tool observation".
- Costliest attempt: getmoto__moto-6308, 28 model calls,
  $1.11 model spend, unresolved. No single attempt dominates:
  the max is under 9% of the total.

## Anomaly check

- No -$0 priced-bucket artifact: the priced bucket is $12.22,
  a real positive figure.
- No $0 context-tax artifact: context tax is $10.34, positive.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- One report inconsistency, flagged not hidden: the top finding
  says "Retry loops burned $10.88 (83% of spend)" while the
  waste lens says retry path $10.59. The $0.29 gap is
  unexplained in the CLI output; this file quotes the waste
  lens figure ($10.59) for retry path and treats the top
  finding as a rounded/overlapping lens, not a separate charge.
  Do not add the two lenses together.
- Retry count is a lower bound (traceback signal only); silent
  failures are missed.
- Cost per successful outcome is computable here (7 successes),
  unlike poc-new-32 where Averth printed a vacuous $0.00 with
  0 successes.

## Overlap audit, stated plainly

- poc-new-32: issue-level overlap 0 of 20, trajectory-level
  overlap 0. The samples are disjoint rows from the same run.
  This lane is a genuine replacement sample, not a re-cut of
  the same 20 rows.
- POC 10 (first batch, SWE-Gym Claude 3.5 Sonnet run, 229
  attempts): issue-level overlap 20 of 20. POC 10's moto
  subset, verified from its events file, is 59 moto issues
  and includes every issue in this sample. Trajectory-level
  overlap is 0: different model (Claude 3.5 Sonnet vs GPT-4o),
  different run_id, different messages and token counts.
  So this lane adds no new moto issue to the set; it is a
  GPT-4o re-run of POC 10's moto issues, with long genuine
  trajectories where poc-new-32 had none. Do not present it
  as a new moto issue set.
- Batch-1 POC 02 (SWE-Gym, all repos, same t04 run, first 20
  with >= 8 assistant turns): its only moto issue was
  getmoto__moto-6470, which IS in this sample (the
  empty-generation row above). That is the same issue under
  the same run, so that one attempt is a repeat of a POC 02
  attempt, not a new trajectory. The other 19 are not in
  POC 02's sample. This single repeat is disclosed, not hidden.

## Limits that must travel with this number

- 7 of 20 resolved is NOT a moto solve rate, a GPT-4o rate, or
  an OpenHands rate. It is one temperature run (t04, maxiter 30),
  one file-order block after a length filter, 20 issues.
- $13.12 is not a bill, not measured spend, and not a saving.
  It is list prices x chars//4 estimates plus tool defaults.
- No change was applied or measured, no operator was involved,
  and no individual recipient is verified. This is a
  clean-run diagnosis only, not a value POC and not sendable
  on this file alone. Any contact to the moto maintainers
  would need the issue-overlap caveat attached: these are
  GPT-4o re-runs of issues already covered by POC 10's Claude
  run, not new moto failures.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, empty rate 5% (not a biased
  empty block), no -$0/$0 anomaly.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $13.12 (priced $12.22, tool estimates $0.90), attempts
20, resolved 7/20, retries 42, context 16.8x, tax $10.34. No price was
added for this lane's model (gpt-4o-2024-08-06 was already priced in
v6). Still ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-62/averth-output-v7.txt.