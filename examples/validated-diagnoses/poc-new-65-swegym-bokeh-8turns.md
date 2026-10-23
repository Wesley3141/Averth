# POC new-65: SWE-Gym bokeh slice, >=8 assistant turns — PASS as a clean Averth run, with bias caveats

## Verdict: PASS (clean-run diagnosis only)

No one contacted, nothing sent, nothing posted, no private data used.
Nothing fabricated. This is a diagnosis run, not a value pitch and
not a send draft. Averth code was not edited.

## Source

- Dataset: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (train.raw, 6,055 rows across 3 parquet shards, OpenHands
  CodeActAgent v2.1 trajectories).
- Bokeh rows in the dataset: 60 total (shard 0: 8, shard 1: 26,
  shard 2: 26), 3 resolved overall (5.0%), 27 flagged
  empty_generation (45%). Bokeh rows with >=8 assistant turns:
  46, of which 13 empty (28%) and 3 resolved (6.5%).
- Selection rule, pre-registered, no outcome filtering: bokeh
  rows only (instance_id starts with bokeh__bokeh), >=8 assistant
  turns, dataset file order (shard 0, then 1, then 2), first 20
  after two prior-use exclusions (below). One row = one attempt,
  case_id = run_id + "__" + instance_id, so the same issue under
  different runs is two distinct attempts.
- Sample composition, read before quoting any rate: 20 attempts,
  17 distinct issues. Four attempts are the same issue,
  bokeh__bokeh-13289, under four different temperature runs
  (t02, t03, t08, t0); 17 of 20 attempts come from a single
  run, gpt-4o-2024-08-06_maxiter_50_N_v2.1-no-hint-train-t0-run_1.
  This is a run-grouped file-order sample, not a bokeh
  population sample, and 1/20 resolved is NOT a bokeh solve
  rate, a GPT-4o rate, or an OpenHands rate. The dataset's own
  bokeh rate is 3/60 (5.0%), and even that is 60 rows across
  8 runs, not a benchmark rate.
- Issues (17): bokeh__bokeh-13289, -13370, -13636, -13608,
  -13258, -12867, -13318, -13239, -12902, -13721, -13422,
  -13147, -13328, -13198, -12779, -13757, -13443.
- The only resolved attempt is bokeh__bokeh-13289 under the
  t08 run (gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t08-run_1).

## Dedupe / overlap check

Two rows that the literal first-20 rule would have included
were excluded for prior use only, never for outcome, and the
next 2 in file order (bokeh__bokeh-13757 and -13443, both
t0-run, both unresolved, both patch-producing) were taken
instead, mirroring poc-new-34's pydantic handling:

1. bokeh__bokeh-13289 under
   gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1
   (resolved False) is batch-1 POC 2's only bokeh row.
2. bokeh__bokeh-13289 under
   claude-3-5-sonnet-20241022_maxiter_50_N_v2.1-no-hint-run_1
   (resolved True) is in batch-1 POC 10, which used that
   entire 229-row Claude run (verified: shard 0 has exactly
   229 Claude rows, and bokeh__bokeh-13289 is its only bokeh
   row).

After exclusion, exact trajectory overlap with POC 2 is 0/20
and with POC 10 is 0/20 (the sample contains no Claude rows
at all; all 20 attempts are GPT-4o-2024-08-06). Issue-level
overlap with POC 2 and POC 10 is bokeh__bokeh-13289 only,
under different runs than either prior POC used. No overlap
with poc-new-33 (MONAI) or poc-new-34 (pydantic), different
repos. Excluding one resolved and one unresolved row cannot
have manufactured the sample's low resolved rate; the
pre-exclusion literal sample was 2/20 resolved, the deduped
sample is 1/20.

## Conversion, mechanical (same rules as POC 2 / poc-new-34)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-65/`
(convert.py, events.jsonl, sample.json, raw.json, scan.py,
scan.json, scan.log, averth-output.txt, report.html).

- Model: run_id prefix gpt-4o-2024-08-06 -> Averth key
  openai:gpt-4o-2024-08-06 (price table v6, $2.50 input /
  $10.00 output per 1M, vendor list price for that snapshot).
  All 20 selected rows share it; asserted in convert.py.
- One model event per assistant turn, input = chars of all
  preceding message text (content plus tool-call arguments)
  // 4, output = chars of this assistant turn (content plus
  its tool-call arguments) // 4. One tool event per assistant
  turn, name = first tool-call function name, or "unknown".
- Retry event before the next model call when a tool
  observation matches "[Command finished with exit code N]"
  with N != 0, reason "exit code N". This is a LOWER BOUND:
  editor errors and test failures without a bash exit code
  are not counted.
- End event: success = row's resolved flag (dataset's real
  test verdict).
- Tokens are NOT recorded in this dataset, so all tokens are
  chars/4 estimates. No cache counts exist, so no cache
  discount is applied. Tool spend is Averth's built-in
  per-call estimate, not a measured tool bill.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "SWE-Gym bokeh (OpenHands, >=8 turns)" --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 694 total (329 model, 329 tool, 16 retry, 20 end).
  Tool mix: str_replace_editor 265, execute_bash 38,
  unknown 16 (turns with no tool call), finish 10.
- Attempts: 20. Autonomous completions (dataset resolved
  labels): 1 (5.0%). Failed: 19.
- Total cost: $7.29.
- Cost basis, as printed by Averth itself: ESTIMATED.
  Priced (tokens x vendor prices, token provenance unverified)
  $6.63; vendor-supplied (billed) $0.00; estimated
  (fallback/tool) $0.66, which is entirely built-in tool
  per-call estimates (329 x $0.002). Model spend $6.63 is
  openai:gpt-4o-2024-08-06 at list prices applied to
  2,565,355 input + 22,098 output chars/4 estimated tokens —
  independently repriced at $2.50/$10.00 per 1M, it matches
  Averth's $6.63 exactly. It sits in Averth's "Priced"
  bucket, but the tokens are estimates, not recorded usage,
  and Averth's own COST BASIS banner says so. Do not quote
  $7.29, or its $6.63 model part, as a bill or as measured
  spend. The index must label this lane's dollars ESTIMATED
  (tokens estimated), not priced, regardless of Averth's
  bucket name.
- Cost per successful outcome, fully loaded: $7.29
  (terminal $0.07, retry path $6.57, tool $0.66, human $0.00
  at the assumed $70.20/hr rate). With only 1 success this
  figure is dominated by the retry path of the 19 failures;
  it is not a stable per-success price.
- Five layers: context compounding 9.0x first-to-last step,
  context tax $5.20 (78% of model spend); yield 1% of tokens
  on the terminal path (99% burned on retries and failed
  runs); heavy tail p50 $0.08 / p95 $1.03 / max $2.69 per
  attempt; top 5% consumed 37% of budget.
- Failed runs: $7.00 (96% of spend, zero outcomes). Retry
  path: $6.57 model+retry spend on discarded paths
  (overlapping lens, not additive). Retries: 16, all
  "exit code 1".
- Costliest attempt: bokeh__bokeh-13328 (t0 run), $2.69
  (34x p50), 50 assistant turns, 11 retries, context 12.5x,
  unresolved — flagged runaway-shaped by --anomaly.

## Empty-generation rate (required by the lane)

- Selected sample: 9 of 20 empty_generation (45%), all with
  git_patch length 0. This is below the lane's 50% bias
  flag threshold, but high enough that it must travel with
  every number: nearly half the sample never produced a
  patch, and the "1/20 resolved" headline is mostly "9 runs
  never started, 10 patch-producing runs failed on tests,
  1 succeeded".
- Empty vs patch-producing spend, computed from events.jsonl:
  the 9 empty attempts total $0.37 (mean $0.04 each); the
  11 patch-producing attempts total $6.92 (mean $0.63 each).
  Empty generations drive the acceptance rate, not the
  dollars — the opposite of the MONAI lane (poc-new-33),
  where 12/20 empty rows cost only $0.25 of $2.78.
- Population context: all bokeh rows 27/60 empty (45%);
  bokeh rows with >=8 turns 13/46 empty (28%). The selected
  sample's 45% is above the >=8-turn population rate because
  the shard-0 pilot rows in file order are mostly empty
  (the 4 remaining shard-0 rows in the sample are 3 empty
  of 4). A future bokeh lane that wants a cleaner sample
  should take a full run or a systematic slice, not literal
  file order.

## Anomaly check

- No "-$0" priced-bucket artifact: the priced bucket is
  $6.63, a real positive figure.
- No $0 context-tax artifact: context tax is $5.20.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Two artifacts that DO appear, both disclosed above:
  (a) chars/4 estimated tokens are bucketed as "Priced" by
  Averth, not as "Estimated" — the token-provenance gap
  flagged in batch-3 lanes 28/30; (b) Averth's top finding
  says retry loops burned $6.70 (92%) while the waste lens
  says retry path $6.57 — a $0.13 gap between two lenses
  on the same spend, unexplained in the output (same pattern
  as poc-new-38's $0.52 gap); the file quotes the waste-lens
  $6.57 figure.
- Retry cross-check: tool observations containing
  "Traceback" number 16, exactly equal to the 16 exit-code
  retries converted — unlike poc-new-34 (pydantic), where
  the two rules gave 0 vs 82. Here the two retry definitions
  agree, so the retry count is not rule-sensitive in this
  sample.
- Zero-token guard did not trigger.

## Limits that must travel with this number

- 1 of 20 resolved is NOT a bokeh, GPT-4o, or OpenHands
  solve rate. It is one file-order, run-grouped sample of
  17 issues, 17 of 20 attempts from a single t0 run, with
  45% empty generations.
- Tokens are chars/4 estimates, not recorded usage; dollars
  are list-price estimates plus tool defaults, not a bill.
- No tested change, no saving claimed, no operator, no
  value proof. This is a clean-run diagnosis only, not a
  value POC and not sendable — no individual recipient was
  verified (SWE-Gym team as a group only, no name invented).
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), attempts 20 (>= 10), CLI
  exit 0, totals reported, honest ESTIMATED cost basis,
  no -$0/$0 anomaly, zero exact overlap with POC 2 and
  POC 10. The bias caveats above are part of the pass,
  not footnotes to be dropped in a rollup.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran under wave 5 with one converter change: convert.py now emits
tokens_estimated=True on every model event (the tokens are chars/4
by construction, stated in the converter header). The regenerated
events file was verified identical to the filed one modulo the flag
(694 events, same exclusions, 1/20 resolved, 9/20 empty). Total is
unchanged at $7.29, attempts 20, resolved 1/20, retries 16, context
9.0x, tax $5.20, failed $7.00 (96%). What moved is the bucket: priced
$6.63 -> $0, and the data-quality block now reads "of which vendor
prices on estimated tokens: $6.63" inside Estimated $7.29. This is
the wave-5 provenance fix working on real lane data: the dollars
were always estimates, and now the bucket says so. The pre-flag
events file is preserved as
hidden_files/poc-new-65/events-v6-preprovenance.jsonl. New report:
hidden_files/poc-new-65/averth-output-v7.txt.