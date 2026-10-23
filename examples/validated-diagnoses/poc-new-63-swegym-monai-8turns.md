# POC new-63: SWE-Gym MONAI slice, >=8 assistant turns — PASS as a clean run, with an overlap caveat

Lane: batch-5 replacement lane 63, for poc-new-33.
No one was contacted, nothing was sent, nothing was posted, no private
data was used. This is a clean-run diagnosis test only, not a value
proof and not a sendable outreach piece. No recipient was verified.

## Verdict: PASS (clean Averth run), NOT 20 new trajectories

Read the overlap section before counting this lane. The sample below
follows the brief literally, and that literal rule reuses 8 trajectories
already run in poc-new-33. This lane adds 12 new trajectories, not 20.
Count it once in the 40-POC rollup as a MONAI >=8-turn diagnosis, and
do not add 20 to any "new trajectories" total.

## Source actually run (no substitution)

- Dataset: SWE-Gym/OpenHands-Sampled-Trajectories, split train.raw.
  Source URL: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
- Repo: Project-MONAI (MONAI), the medical-imaging library.
- Selection, pre-registered in the brief, NO outcome filtering:
  the first 20 MONAI rows in dataset file order (shard 0) WITH at
  least 8 assistant turns. Rows with fewer than 8 turns were skipped
  on length only, before looking at any outcome. This is the POC 02
  length rule, applied to MONAI only.
- Model/run for every row: gpt-4o-2024-08-06. First 15 rows are run
  gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1;
  the next 5 are run
  gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t03-run_1.
  Because the same instance_id appears under both runs, case_id is
  run_id + "__" + instance_id (poc-new-33 used bare instance_id
  because all its rows were one run).

Dataset population, counted in full in poc-new-33 (scan, not a sample):
- Total rows: 6,055 across 3 shards (2,019 / 2,018 / 2,018).
- MONAI rows: 962 (shard 0: 214, shard 1: 374, shard 2: 374),
  of which 95 resolved (9.9%).

Sample (20 trajectories, 16 distinct issues, file order):
- t04: Project-MONAI__MONAI-3715 (resolved), -3403 (resolved),
  -2454, -3547, -6975, -5686 (resolved), -1121, -2061,
  -4775 (resolved), -4159, -6756, -907 (resolved),
  -5908 (resolved), -3205, -6775.
- t03: Project-MONAI__MONAI-2454, -3690, -1121,
  -4775 (resolved), -2061.
- Resolved in sample: 7 of 20 (35.0%). This is well above the
  MONAI population rate (9.9%); do not generalize it to MONAI,
  OpenHands, or GPT-4o generally. It is a first-20-with->=8-turns
  block of two temperature runs, not a representative sample.

## Empty-generation rate: 3 of 20 (15%), below the 50% bias threshold

This was the point of the lane. poc-new-33, with no turn filter,
was 12 of 20 empty generations (60%). Here, only 3 of 20 are
flagged empty_generation, all under t03:
MONAI-2454 (t03, 9 turns), MONAI-3690 (t03, 14 turns),
MONAI-1121 (t03, 11 turns). The >=8-turn filter does not remove
every empty generation, but it cuts the rate from 60% to 15%,
and the remaining empty rows cost little (see below). The
15% figure is reported, not hidden, and the lane is NOT flagged
as biased on the brief's >50% empty criterion. It is still
biased in the usual first-20 sense (see Limits).

## Overlap check: 8 trajectories reused from poc-new-33

- Against poc-new-33 (20 trajectories, all t04, bare instance_id):
  trajectory overlap 8 of 20. The shared trajectories are the
  t04 runs of MONAI-3715, -3403, -2454, -3547, -6975, -5686,
  -1121, and -2061. They are the same rows, same run, same
  messages; this lane re-runs them, it does not add them.
- Issue overlap is 9 of 16 distinct issues: the 8 above plus
  MONAI-3690, which appears in poc-new-33 as a t04 empty
  generation and here as a different, t03 trajectory.
- New trajectories in this lane: 12 of 20 (7 new t04 issues
  -4775, -4159, -6756, -907, -5908, -3205, -6775, plus the
  5 t03 trajectories).
- Against first-batch POC 02: 0 overlap. POC 02's sample contains
  no MONAI row at all (verified in poc-new-33).
- Against batch-1 files poc-01 through poc-10 and batch-2/3 files
  poc-new-01 through poc-new-30: no trajectory overlap beyond
  the poc-new-33 overlap stated above (poc-new-33 is batch-4).

## Conversion (mechanical, mirrors poc-new-33 / POC 02 exactly)

Script: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-63/convert.py
Raw rows (verbatim, one JSON per trajectory, named
<run-tag>__<instance_id>.json so t03/t04 duplicates do not
overwrite each other):
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-63/raw/
Events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-63/events.jsonl
(663 events).

Rules, identical to poc-new-33 except case_id:
- case_id = run_id + "__" + instance_id; 20 distinct case_ids
  verified in the converter (asserted, not assumed).
- Model = gpt-4o-2024-08-06, provider openai, from the run_id
  prefix (all 20 rows).
- One model event per assistant turn; input tokens = characters
  of all preceding message text (content plus tool-call
  arguments) / 4; output tokens = characters of the assistant
  turn (content plus its tool-call arguments) / 4.
- One tool event per assistant turn, name = first tool-call
  function name, or "unknown" if the turn has no tool call.
- Retry event before the next model call when a tool observation
  matches "[Command finished with exit code N]" with N != 0.
  This is a LOWER BOUND: editor errors and test failures
  without a bash exit code are not counted.
- End event: success = row's resolved flag, the dataset's real
  test verdict. Verified equal to test_result.report.resolved
  for all 20 rows, and assistant-turn counts verified against
  sample.json in the converter.

Token disclosure, stated plainly: the dataset records no per-call
token usage, no cache counts, and no billed dollar costs. Every
token below is a chars/4 estimate, never recorded usage. The
"Priced" bucket below therefore means "vendor list prices
applied to estimated tokens", not "recorded tokens priced" —
Averth's own banner says the same (token provenance unverified).

## Averth run

- Averth: ~/workspace/averth at commit fafab07, price table v6
  (verified 2026-10-23). No Averth code was edited in this lane.
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace
  <hidden_files/poc-new-63/events.jsonl> --format jsonl
  --html <hidden_files/poc-new-63/report.html>
  --agent "SWE-Gym MONAI >=8 turns"`
- CLI exit code: 0, no crash, no dropped-case error.
- Full CLI output:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-63/cli_output.txt
- HTML report:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-63/report.html

## Numbers, fresh run

- Attempts: 20. Accepted outcomes (resolved): 7 (35.0%).
  Failed attempts: 13 (65.0%).
- Model events: 313. Tool events: 313. Retries: 17, all
  "exit code 1" (14) or "exit code 123" (3). End events: 20.
- Tool mix: str_replace_editor 197, execute_bash 55,
  unknown 46 (turns with no tool call), finish 15.
- Total cost: $5.87.
- Cost basis, exactly as Averth printed it: COST BASIS ESTIMATED.
  Priced (tokens x vendor prices, token provenance unverified)
  $5.24; vendor-supplied (billed) $0.00; estimated
  (fallback/tool) $0.63, which is entirely built-in tool
  per-call estimates (313 x $0.002 = $0.626, matching $0.63).
  Model spend $5.24 is openai:gpt-4o-2024-08-06 at v6 list
  prices $2.50 input / $10.00 output per 1M applied to
  1,917,116 input + 45,170 output chars/4 estimated tokens:
  1,917,116/1e6 x $2.50 + 45,170/1e6 x $10.00 = $5.2445,
  matching Averth's $5.24. Do not quote $5.87 as a bill or as
  measured spend.
- Cost per successful outcome, fully loaded: $0.84
  (terminal $0.17, retry path $0.57, tool $0.09, human $0.00
  at the assumed $70.20/hr rate, not measured).
- Failed runs: $4.29 (73% of spend) for zero accepted outcomes.
- Retry path: $4.02 model+retry spend on discarded paths
  (overlapping lens, not additive with failed runs).
- Five layers: context compounding 19.4x first-to-last step,
  context tax $4.36 (83% of model spend); yield 23% of tokens
  on the terminal path (77% burned on retries and failed runs);
  heavy tail p50 $0.19 / p95 $0.81 / max $0.84 per attempt;
  top 5% consumed 14% of budget.
- Comparison with poc-new-33 (same dataset, no turn filter):
  attempts 20 in both; resolved 7 vs 3; total $5.87 vs $2.78;
  context tax $4.36 vs $1.98; yield 23% vs 20%; cost per
  success $0.84 vs $0.93. The >=8-turn sample costs more and
  resolves more because it actually runs the agent instead of
  stopping after 4 directory-listing calls. That comparison is
  a sampling-rule effect, not a model improvement.

## Anomaly check required by the lane

- No "-$0" priced-bucket artifact: the priced bucket is $5.24,
  a real positive figure.
- No $0 context-tax artifact: context tax is $4.36, positive.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Two artifacts that DO appear, both disclosed:
  (a) chars/4 estimated tokens are bucketed as "Priced" by
  Averth, not as "Estimated" — the index must label this
  lane's dollars ESTIMATED (tokens estimated), not priced,
  regardless of Averth's bucket name (same token-provenance
  gap flagged in batch-3 lanes 28/30 and batch-4 lane 33).
  (b) Minor report inconsistency, same shape as batch-4
  lane 38: the findings list says "Retry loops burned $4.20"
  while the waste lens says retry path $4.02, an unexplained
  $0.18 gap. This file quotes the waste-lens $4.02.
- Tool "unknown" (46 events) is an artifact of the
  one-tool-event-per-turn rule: turns with no tool call still
  emit a tool event at the $0.002 built-in default. Tool
  spend is therefore a rule artifact, not a measured tool log.

## Limits that must travel with this number

- 7 of 20 resolved is NOT a MONAI solve rate, a GPT-4o rate,
  or an OpenHands rate. It is a first-20-with->=8-turns block
  of two temperature runs (t04 + t03), against a MONAI
  population rate of 9.9% in this dataset.
- Tokens are chars/4 estimates, not recorded usage; dollars are
  list-price estimates plus tool defaults, not a bill.
- 8 of these 20 trajectories were already run in poc-new-33.
  Any aggregate over poc-new-33 + this lane must deduplicate
  those 8, or it double-counts them.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, empty rate 15% (below the
  brief's 50% bias threshold), no -$0/$0 anomaly. This is a
  clean-run diagnosis only: no change was applied or measured,
  no saving is claimed, and no recipient was verified.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $5.87 (priced $5.24, tool estimates $0.63), attempts 20,
resolved 7/20, retries 17, context 19.4x, tax $4.36. No price was
added for this lane's model (gpt-4o-2024-08-06 was already priced in
v6). Still ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-63/averth-output-v7.txt.