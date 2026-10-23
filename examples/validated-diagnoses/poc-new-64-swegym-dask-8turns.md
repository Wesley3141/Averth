# POC new-64: SWE-Gym dask slice, >=8 assistant turns — PASS

## Verdict: PASS (clean-run diagnosis only)

No one contacted, nothing sent, nothing posted, no private data used.
Nothing fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No change was tested, no saving is claimed, and
no individual recipient is verified.

## Source

- Dataset: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (train.raw, 6,055 rows across 3 parquet shards, OpenHands
  CodeActAgent v2.1 trajectories).
- Dask rows in the dataset: 306 total (shard 0: 112, shard 1: 49,
  shard 2: 145), 45 resolved (14.7% across the full dask set).
- All 20 selected rows are GPT-4o-2024-08-06, maxiter 30, v2.1,
  no-hint, train: 9 from temperature run t04-run_1 and 11 from
  t03-run_1. Same model and scaffold as batch-1 POC 02, a
  different repo slice.

## Selection rule, pre-registered and outcome-blind

First 20 dask rows in dataset file order (shard 0, then shard 1,
then shard 2) WITH at least 8 assistant turns. The length filter
is a pre-registered rule, not outcome filtering: it filters out
short empty generations on length, the same rule POC 02 used,
and it is applied before looking at resolved labels.

Two corrections to the literal first 20, both by prior use only:

1. Reaching 20 qualifying rows scanned 26 dask rows; 6 were
   excluded for having fewer than 8 assistant turns.
2. The literal first 20 included 2 exact run+instance combos
   already used in batch-1 POC 02: t04 dask-9212 (resolved) and
   t04 dask-8801 (unresolved). Those 2 were excluded and
   replaced with the next 2 qualifying rows in file order:
   t03 dask-6801 (unresolved, 30 turns) and t03 dask-7305
   (unresolved, 26 turns). Excluding one resolved and one
   unresolved attempt cannot manufacture the result in either
   direction.

Final sample: 20 attempts, 12 distinct issues (the same issue
appears under both t03 and t04 runs; trajectories are distinct,
case_id is run_id + "__" + instance_id so they never collide),
4 resolved (20.0%), 16 failed. The 20% rate is this
run-grouped sample only, not a dask or GPT-4o general rate;
the full dask set resolves 45 of 306 (14.7%).

Empty-generation rate: 1 of 20 (5%). That is below the 50%
bias threshold in the lane brief, so this sample is not
flagged as an empty-generation sample. The one empty case is
not cheap, and that matters: t03 dask-7138 is flagged
empty_generation yet ran 30 turns, accumulated 537,458
estimated input tokens, and cost $1.41 (11% of the sample
total) without producing a patch. Empty here means no patch,
not no spend.

## Conversion, mechanical (same rules as POC 02 / poc-new-34)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-64/`
(scan.py, scan_all_dask.json, scan.json, resume.py, convert.py,
events.jsonl, cli_output.txt, report.html, raw/ 20 verbatim
rows saved under run-prefixed filenames).

- One row = one attempt, case_id = run_id + "__" + instance_id.
  Rows were re-fetched from the parquet by (run_id,
  instance_id) in sample order, not from instance-only
  filenames, so t03 and t04 versions of the same issue cannot
  overwrite each other.
- Model: run_id prefix gpt-4o-2024-08-06 -> Averth key
  openai:gpt-4o-2024-08-06 (price table v6, $2.50 input /
  $10.00 output per 1M, the vendor list price for that
  snapshot). No price invented, no mapping to a different key.
- Assistant: one model event per assistant turn; input =
  chars of all preceding message text (content plus tool-call
  arguments) // 4; output = chars of this turn // 4.
- Tool: one tool event per assistant turn, first tool-call
  function name, or "unknown" if none.
- Retry: before the next model call when a tool observation
  matches "[Command finished with exit code N]" with N != 0.
  LOWER BOUND: editor errors and test failures without a bash
  exit code are not counted under this rule.
- End: success = row "resolved", the dataset's own label,
  cross-checked against test_result.report.resolved for all
  20 rows (0 mismatches).
- Tokens are NOT recorded in this dataset, so all tokens are
  chars/4 estimates. No cache counts exist, so no cache
  discount is applied. Tool spend is Averth's built-in
  per-call estimate, not a measured tool bill.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "SWE-Gym dask (OpenHands GPT-4o)" --anomaly`
- CLI exit code: 0, no crash, no error. A direct rerun gives
  identical totals (20 attempts, 4 resolved, 29 retries,
  $11.64 priced, $12.48 total).
- Events: 889 total (420 model, 420 tool, 29 retry, 20 end).
  Tool mix is counted in the events file; tool spend is
  420 calls at the built-in $0.002 default = $0.84.
- Attempts: 20. Autonomous completions (dataset resolved
  labels): 4 (20.0%). Failed: 16.
- Total cost: $12.48.
- Cost basis, as printed by Averth itself: ESTIMATED.
  Priced (tokens x vendor prices, token provenance
  unverified) $11.64; vendor-supplied (billed) $0.00;
  estimated (fallback/tool) $0.84, entirely built-in tool
  per-call estimates; no model dollars used fallback pricing.
  The $11.64 sits in Averth's "Priced" bucket, but the tokens
  are chars/4 estimates, not recorded usage, and Averth's own
  COST BASIS banner says so. Do not quote $12.48, or its
  $11.64 model part, as a bill or as measured spend. In index
  terms this lane's dollars are ESTIMATED (tokens estimated).
- Cost per successful outcome, fully loaded: $3.12
  (terminal $0.23, retry path $2.68, tool $0.21, human $0.00
  at the assumed $70.20/hr rate, not measured).
- Failed runs: $11.13 (89% of spend, zero outcomes).
  Resolved runs: $1.35 (11%).
- Retry path: $10.71 model+retry spend on discarded paths
  (overlapping lens, not additive with failed runs).
- Five layers: context compounding 20.5x first-to-last step,
  context tax $10.24 (88% of model spend); yield 8% of tokens
  on the terminal path (92% burned on retries and failed
  runs; yield is a token-share definition, not the 20%
  success rate); heavy tail p50 $0.52 / p95 $1.41 /
  max $1.43 per attempt; top 5% consumed 11% of budget.
  Costliest attempt: t04 dask-7305, $1.43, unresolved,
  30 turns, 1 retry, context grew 28.1x.
- Retries: 29, all exit code 1 under the POC 02 bash-exit
  rule. As a check only, tool observations containing
  "Traceback" number 30, so here the two retry rules nearly
  agree (29 vs 30) — unlike poc-new-34 pydantic, where the
  bash-exit rule gave 0 and the traceback rule gave 82.
  Retry counts across lanes with different rules are not
  directly comparable; the rule used is stated above.

## Anomaly check required by the lane

- No "-$0" priced-bucket artifact: the priced bucket is
  $11.64, a real positive figure.
- No $0 context-tax artifact: context tax is $10.24.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Two artifacts that DO appear, both disclosed:
  (a) chars/4 estimated tokens are bucketed as "Priced" by
  Averth, not as "Estimated" — the token-provenance gap
  flagged in poc-new-28/30/32/35; the index must label this
  lane's dollars ESTIMATED (tokens estimated), not priced,
  regardless of Averth's bucket name.
  (b) The text output's top finding says retry loops burned
  $10.94 while the waste lens says retry path $10.71, an
  unexplained $0.23 gap between overlapping lenses. This
  file quotes the waste-lens figure ($10.71) and flags the
  gap; it is the same top-finding vs waste-lens
  inconsistency poc-new-38 flagged ($9.38 vs $8.86).

## Overlap audit

- Trajectory-level (run_id + instance_id): zero overlap
  with every earlier lane after the 2 POC 02 exclusions
  above, verified against prior sample.json files and
  against ~/workspace/poc-02-openhands/sample.json.
- Issue-level: 2 of the 12 distinct dask issues in this
  sample (dask-9212, dask-8801) also appear in POC 02, but
  under different trajectories (t03 runs here, t04 runs
  there for those two issues after exclusion; the excluded
  t04 versions are the POC 02 ones). The other 10 issues
  are new to this lane.
- Distinct from poc-new-31 (pandas), poc-new-32 (moto),
  poc-new-33 (MONAI), and poc-new-34 (pydantic) by repo.

## Limits that must travel with this number

- 4 of 20 resolved is NOT a dask solve rate, a GPT-4o
  rate, or an OpenHands rate. It is 12 issues under two
  temperature runs of one model, in file order with a
  length filter. Do not present 20% as any general rate.
- Tokens are chars/4 estimates, not recorded usage;
  dollars are list-price estimates plus tool defaults,
  not a bill. The empty-generation case (t03 dask-7138,
  $1.41) shows that a no-patch run can still be one of
  the costliest runs in the sample.
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), attempts 20, CLI exit 0,
  totals reported, honest ESTIMATED cost basis, empty
  rate 5% (not biased), no -$0/$0-tax anomaly.
  Clean-run diagnosis only: no change was applied or
  measured, no saving is claimed, and no recipient was
  verified, so this file alone does not make the lane
  sendable.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $12.48 (priced $11.64, tool estimates $0.84), attempts
20, resolved 4/20, retries 29, context 20.5x, tax $10.24. No price was
added for this lane's model (gpt-4o-2024-08-06 was already priced in
v6). Still ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-64/averth-output-v7.txt.