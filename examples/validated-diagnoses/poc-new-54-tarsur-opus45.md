# POC new-54: tarsur385 scikit-learn, claude-4.5-opus-high — PASS

## Verdict: PASS as a clean-run diagnosis only

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft.

## Correction to the lane label, read first

This is NOT a SWE-smith scikit-learn result and NOT a SWE-Gym
scikit-learn result. Batch-3 agent 13 proved scikit-learn is absent
from the SWE-smith trajectory sets it scanned, and batch-4 lane 13's
fallback was scikit-learn-contrib/imbalanced-learn, a different
library. This lane is the first real scikit-learn slice in the set,
but from a different family: tarsur385/swebench-verified-trajectories,
model run claude-4.5-opus-high. It must never be quoted as
SWE-smith scikit-learn.

## Source and selection

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Model run: `swebench_verified_raw/claude-4.5-opus-high` (500 instance
  directories in this run).
- Repo counts in this run, counted from the full recursive tree
  listing (instance directories, not sampled):
  astropy__astropy 22, django__django 231, matplotlib__matplotlib 34,
  mwaskom__seaborn 2, pallets__flask 1, psf__requests 8,
  pydata__xarray 22, pylint-dev__pylint 10, pytest-dev__pytest 19,
  scikit-learn__scikit-learn 32, sphinx-doc__sphinx 44,
  sympy__sympy 75.
- Selection rule, fixed before counting outcomes: first repo
  alphabetically with at least 20 files, skipping repos already
  used in the tarsur385 family (astropy in poc-new-37, django in
  poc-new-11, matplotlib in poc-new-42, flask/requests in poc-new-12,
  sympy in poc-new-36, and pydata__xarray, assigned to batch-5
  lane 51). That rule lands on scikit-learn__scikit-learn (32 files).
  Sphinx (44) and sympy (75) come later alphabetically and were not
  used. Within scikit-learn, the first 20 files in numeric instance
  order, no outcome filtering.
- Slice (20): scikit-learn__scikit-learn-10297, -10844, -10908,
  -11310, -11578, -12585, -12682, -12973, -13124, -13135, -13142,
  -13328, -13439, -13496, -13779, -14053, -14087, -14141, -14496,
  -14629. The remaining 12 files in the run (14710, 14894, 14983,
  15100, 25102, 25232, 25747, 25931, 25973, 26194, 26323, 9288)
  were not in the Averth run, but were checked for the bias
  question below.
- Distinctness: scikit-learn appears in no earlier POC file (batch-1
  SWE-smith/SWE-Gym sets do not include it; batch-4 lane 13 used
  imbalanced-learn, a different repo). Zero instance overlap with
  poc-new-11 (django), poc-new-12 (flask/requests), poc-new-36
  (sympy), poc-new-37 (astropy), and poc-new-42 (matplotlib).

## Conversion, mechanical (same rules as poc-new-42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-54/`
(convert.py, events.jsonl, sample.json, convert.log,
averth-output.txt, report.html, raw/ 20 traj files).

- One file = one attempt, case_id = instance_id.
- Model: every file's info.docent.model_label is
  "claude-4.5-opus-high" (asserted in the converter). The converter
  emits that exact label with provider "anthropic".
- Model mapping, and why it is NOT remapped: Averth price table v6
  has NO entry for anthropic:claude-4.5-opus-high. It was NOT
  remapped to anthropic:claude-opus-4-6 ($15/$75 per 1M), which is
  a different model, and no Opus 4.5 vendor price was invented
  (this task forbids editing Averth code, so no price was added).
  Averth therefore applies its documented fallback $1.00 input /
  $3.00 output per 1M and flags the key unpriced. Every model
  dollar below is a fallback estimate, never a vendor-priced figure.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" in this slice).
- retry event before the next assistant turn when the preceding
  tool observation contains the literal string "Traceback", a
  genuinely recorded failure signal (same rule as POC10 /
  poc-new-42).
- end event: success = info.resolved, the dataset's own label
  (also info.scores.resolved). All 20 exit_status values are
  "Submitted".
- Tokens are NOT recorded in these traj files (assistant message
  metadata is None in all 20 files), so tokens are chars//4
  estimates, same limitation as poc-new-11/12/36/37/42.
- Cross-check: model events per case exactly equal the source's
  api_calls per case for all 20 cases (573 model events total,
  matching the api_calls sum 573).

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html`
- CLI exit code: 0, no crash, no error.
- Events: 1,306 total (573 model, 647 tool, 66 retries, 20 end).
- Attempts: 20. Autonomous completions (dataset resolved labels):
  20 (100.0%). Failed: 0.
- Total cost: $6.62.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $0.00;
  vendor-supplied (billed) $0.00; estimated (fallback prices)
  $6.62, of which model $5.33 at fallback and built-in bash tool
  estimates $1.29 (647 calls x $0.002). Averth's own warning line
  says so, and the report flags
  "unpriced models: anthropic:claude-4.5-opus-high".
- Independent check: 5,087,135 input tokens x $1.00/1M +
  80,515 output tokens x $3.00/1M = $5.3287, matching Averth's
  $5.33; plus $1.294 tool estimates = $6.6227, matching $6.62.
- Cost per successful outcome (fully loaded): $0.33
  (terminal $0.03, retry path $0.23, tool $0.06, human $0.00 at
  the assumed $70.20/hr rate, not measured).
- Five layers: context compounding 7.8x first-to-last step,
  context tax $0.00 (see anomaly 2); yield 12% of tokens on the
  terminal path; heavy tail p50 $0.28 / p95 $0.71 / max $0.80
  per attempt; top 5% consumed 12% of budget.
- Failed runs: $0.00 (0% of spend, zero outcomes). Retry path:
  $4.68 model+retry spend on discarded paths (overlapping lens,
  not additive). Retries: 66, all "traceback in previous tool
  observation" (a lower bound: silent failures are missed).

## The 20/20 question, checked, not assumed

20/20 resolved looks like a slice artifact, so the remaining 12
scikit-learn files in the same run were fetched and their labels
read (they were not run through Averth): 11 resolved, 1 failed
(scikit-learn__scikit-learn-25747). The full scikit-learn run is
therefore 31/32 resolved (96.9%). The 20/20 slice is consistent
with the full run, not a file-order block of successes hiding
failures later in the repo. That does NOT make 100% a general
scikit-learn solve rate: it is 20 instances of one repo under one
model run at high effort, and the full-run 31/32 rate is itself
far above published SWE-bench rates for any model, which is a
reason to treat the dataset's resolved labels as run-specific,
not as a benchmark claim. Do not quote 20/20 or 31/32 as
"Claude solves scikit-learn" or as a scikit-learn project finding.

## Anomaly check

- No "-$0" priced-bucket artifact: the priced bucket is $0.00,
  a real figure (all model spend is fallback).
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Context tax $0.00 despite 7.8x growth: the known fallback-pricing
  quirk (the fallback cost path records in_price 0.0, and the
  context-tax loop skips steps with no input price). Do NOT quote
  it as "context was free".
- Top-finding vs waste-lens gap: the text output's top finding
  says retry loops burned $5.64 (85% of spend) while the waste
  lens says retry path $4.68. The file quotes the waste-lens
  figure; the $0.96 gap is unexplained in Averth's output and
  the two figures are overlapping lenses, not additive. The
  "88% burned on retries and failed runs" wording is also
  misleading here: there are 0 failed runs, so that 88% is retry
  path only.
- Yield 12% with 20/20 resolved is definitional (tokens on the
  terminal path only), not a contradiction: resolution here was
  retry-expensive, with 66 retries across 20 attempts.
- Cost per success components as printed sum to $0.32 vs the
  $0.33 fully loaded figure: a rounding difference.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $10.72.
- Averth metered $6.62 vs recorded $10.72: -$4.10 (-38%).
  Decomposition: metered model spend $5.33 is $5.39 below
  recorded, and $1.29 of built-in bash tool estimates closes
  part of the gap. This is the opposite direction from the
  claude-opus-4.6 slices (poc-new-11 django ~7.5x above recorded,
  poc-new-37 astropy ~7.5x above, poc-new-42 matplotlib ~8.25x
  above), and the reason is visible: those slices used a real
  $15/$75 list price on untruncated chars//4 history, while this
  slice uses a $1/$3 fallback on the same kind of history.
  Neither direction is a bill. Do not quote $6.62 as what anyone
  was charged, and do not use the recorded $10.72 to infer an
  Opus 4.5 vendor price: recorded costs presumably reflect
  cache discounts and truncated context that Averth does not
  model, so back-solving a price from them would be fabrication.
- Until a verified Opus 4.5 price is added to Averth's table and
  this events file is rerun, $6.62 must always travel with its
  fallback basis.

## Limits that must travel with this number

- 20/20 resolved is NOT a general solve rate (see the 20/20
  question above). One repo, one model run, 20 instances.
- Tokens are chars//4 estimates, not recorded usage; dollars are
  fallback estimates plus tool defaults, not a bill.
- No change was applied or measured, no saving is claimed, and
  no tested fix follows from this run: the retry finding (66
  tracebacks) is a report output, not a tested intervention.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, no -$0/$0-tax hidden (both are
  disclosed above, the tax one as a known quirk).
- Not sendable on this file alone: no verified individual
  recipient is attached to this workflow, and the fallback
  pricing means the dollar figure would mislead a recipient
  without the basis attached.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5.
`anthropic:claude-4.5-opus-high` is now priced at the Opus 4.5 rate
$5.00/$25.00 per 1M (Anthropic pricing page; the dataset label is Opus
4.5 at high effort, never a remap to Opus 4.6). Attempt, resolved
(20/20), and retry (66) counts are unchanged. Old total $6.62 all
fallback ESTIMATED -> new total $28.74, of which priced $27.45 and
tool estimates $1.29. Cost per success $0.33 -> $1.44. Context tax
$0.00 (fallback quirk) -> $20.40 (74% of model spend). Waste-lens
retry path $4.68 -> $24.00; the top finding now decomposes it ($24.00
model plus $0.96 retry-path tools = $24.96 headline). Source recorded
$10.72: Averth is now 2.68x the source (was 0.62x at fallback rates,
the opposite direction from the Opus 4.6 slices, which used real
$15/$75 prices). The v6 $6.62 must no longer be quoted. Still
ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-54/averth-output-v7.txt.