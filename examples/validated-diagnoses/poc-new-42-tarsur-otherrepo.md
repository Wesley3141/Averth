# POC new-42: tarsur385 SWE-bench Verified, matplotlib slice — PASS

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch,
not a billed-cost receipt, and not a send draft.

## Repo and model chosen, and why

- Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Model run used: `claude-opus-4.6` under
  `swebench_verified_raw/claude-opus-4.6/`. This is the same model
  run as poc-new-11 (django), so the file format was already
  verified; the repo is different, so there is zero attempt overlap
  with poc-new-11.
- Selection rule, applied to that single model run, in
  alphabetical repo order, skipping the repos the task excludes:
  astropy__astropy, 22 files, excluded (lane 37); django__django,
  231 files, excluded (poc-new-11); matplotlib__matplotlib, 34
  files, meets the at-least-20 threshold, so it is the pick.
  For transparency, the next repos in that run are
  mwaskom__seaborn (2, below threshold), pallets__flask (1,
  excluded, poc-new-12), psf__requests (8, excluded, poc-new-12),
  pydata__xarray (22, would be the next qualifying repo, not
  used), pylint-dev__pylint (10), pytest-dev__pytest (19),
  scikit-learn__scikit-learn (32), sphinx-doc__sphinx (44),
  sympy__sympy (75, excluded, lane 36). Repo counts were read
  from the full paginated HF tree listing for this model run
  (500 instance dirs), saved as `dirs-claude-opus-4.6.txt`.
  The claim "first" is scoped to this model run; the other nine
  model runs were not enumerated for this lane.
- Slice, mechanical, no outcome filtering: the first 20
  matplotlib instance dirs in sorted order:
  matplotlib__matplotlib-13989, -14623, -20488, -20676, -20826,
  -20859, -21568, -22719, -22865, -22871, -23299, -23314,
  -23412, -23476, -24026, -24149, -24177, -24570, -24627, -24637.
  All 20 files were downloaded verbatim and are kept under
  `hidden_files/poc-new-42/raw/`. The remaining 14 matplotlib
  files in this run were not used.
- Distinctness: matplotlib appears in no earlier batch (batch 1,
  batch 2, or batch 3 lanes 11-30). Zero instance overlap with
  poc-new-11 (django) and poc-new-12 (flask/requests) by repo,
  and zero overlap with lanes 36/37 (sympy/astropy) by repo.

## Conversion, mechanical (same rules as poc-new-11)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-42/`
(convert.py, events.jsonl, averth-output.txt, report.html,
raw/ 20 files, dirs-claude-opus-4.6.txt, list_tree.py).

- One file = one attempt, case_id = instance_id.
- Model mapping, stated: traj `info.docent.model_label` is
  "claude-opus-4.6" in all 20 files (assistant message model
  fields are None). Averth's price table v6 key is
  "anthropic:claude-opus-4-6" at $15 input / $75 output per 1M
  tokens (averth/pricing.py), so the converter emits model
  "claude-opus-4-6". Same model, hyphenated key; no price
  invented, and the model is priced, not fallback.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars // 4,
  output = (content chars + tool argument chars) // 4), then one
  tool event per tool_call (function name, always "bash" here).
- retry event before the next assistant turn when the preceding
  tool observation contains the literal string "Traceback", a
  recorded failure signal, the same rule as poc-new-11.
- end event: success = `info.resolved`, the dataset's own label
  (also `info.scores.resolved`). All 20 files have exit_status
  "Submitted".
- Tokens are NOT recorded in these traj files, so tokens are
  chars // 4 estimates, same limitation as poc-new-11 and
  poc-new-12. Recorded per-instance costs live in
  `info.model_stats.instance_cost` and are compared below, not
  replaced by Averth's dollars.
- Cross-check: model events 558 exactly equal the source's
  api_calls sum 558 across these 20 files. Tool events 592,
  retries 58, end events 20, total events 1,228.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html`
- CLI exit code: 0, confirmed on a direct rerun (not only through
  a pipe). No crash, no error, no unpriced model.
- Attempts: 20. Autonomous completions (dataset resolved labels):
  15 (75.0%). Failed: 5 (25.0%): -20676, -20826, -21568, -23299,
  -23476.
- Retries: 58, all "traceback in previous tool observation".
- Total cost: $78.75.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $77.57,
  all anthropic:claude-opus-4-6 (100% of model spend);
  vendor-supplied (billed) $0.00; estimated (fallback/tool)
  $1.18, entirely built-in bash per-call estimates, flagged as
  estimates in the report. No model dollars used fallback pricing.
- Cost per successful outcome, fully loaded: $5.25
  (model terminal $0.50, retry path $4.67, tool $0.08,
  human $0.00, human rate $70.20/hr is an assumption, not
  measured).
- Failed runs: $25.52 (32% of spend, zero outcomes).
- Retry path: $70.02 model+retry spend on discarded paths
  (overlapping lens, not additive; the top finding line quotes
  $70.80 including tool spend on retry loops, 90% of spend).
- Five layers: context compounding 6.6x input growth
  first-to-last step, context tax $59.30 (76% of model spend);
  yield 9% of tokens on the terminal path (91% burned on retries
  and failed runs); heavy tail p50 $2.04 / p95 $14.00 /
  max $15.71 per attempt, top 5% consumed 20% of budget.

## Anomaly check

- No "-$0" priced bucket: priced bucket is $77.57.
- No $0 context tax: context tax is $59.30.
- No "Measured" label: the report's cost basis is ESTIMATED,
  with the do-not-quote-as-a-bill warning printed.
- Zero-token guard did not trigger: the trace has tokens
  throughout.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from `info.model_stats.instance_cost`,
  summed over exactly these 20 files: $9.541.
- Averth metered $78.75 vs recorded $9.541: about 8.25x higher.
  This is the same direction as poc-new-11 (django, about 7.5x),
  and unlike poc-new-12 (flask/requests, +8.9%), so the size of
  the gap is slice-dependent and must not be averaged away.
- Likely causes, stated as hypotheses, not verified: Averth
  accumulates full history into context with no truncation and
  applies no cache discount, while the source's cost field
  presumably reflects actual API usage (with whatever caching
  and truncation the real run used), and chars // 4 token
  estimates are not recorded usage. The Averth figure therefore
  overstates what the source says the run cost.
- Consequence: quote $78.75 only as "Averth chars/4 list-price
  estimate", never as what anyone was charged, and never
  alongside the source's $9.541 as if they were the same thing.
  A real billed-cost POC would need recorded token usage, which
  this source does not publish in its messages.

## Limits that must travel with this number

- 15 of 20 resolved is NOT a general solve rate. It is the first
  20 matplotlib instances in sorted order under one model
  (claude-opus-4.6), out of 34 matplotlib files in this run.
  Do not present 75.0% as Claude's or any scaffold's general
  SWE-bench rate.
- Tokens are chars // 4 estimates, not recorded usage; dollars
  are list-price estimates plus tool defaults, not a bill.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20 (>= 10), CLI exit 0, totals
  reported, honest ESTIMATED cost basis, no -$0 / $0-tax /
  "Measured" anomaly. This is a clean-run diagnosis test, not a
  value POC: no change was applied or measured, and cost per
  success here is an estimate built on estimated tokens, not a
  billed saving.

## Wave-5b addendum (price-table v8, 2026-10-23) — supersedes the totals above

Correction: Anthropic's own pricing page (docs.anthropic.com/en/docs/
about-claude/pricing) lists Claude Opus 4.6 at $5.00 input / $0.50
cached / $25.00 output per 1M tokens. The v6/v7 table carried Opus
4.1's $15/$75 rates onto Opus 4.6, so every dollar above was
overstated 3x on the model side. Opus 4.1 is a distinct model at
$15/$75 and keeps its own entry. The v8 rerun below uses the
corrected price and flags the chars/4 tokens as estimated, so model
spend now lands in the Estimated bucket, not Priced. Attempts 20,
resolved 15, retries 58 are unchanged; only dollars move.
Fresh report: hidden_files/poc-new-42/averth-output-v8.txt and
report-v8.html; pre-correction events preserved as events-v7.jsonl.
- Total $27.04 (was $78.75), all Estimated: model $25.86
  (exactly $77.57 / 3) plus $1.18 tool estimates.
- Cost per successful outcome $1.80 fully loaded (was $5.25).
- Failed runs $8.74 (32% of spend, share unchanged; was $25.52).
- Context tax $19.77 (was $59.30; 76% of model spend, unchanged
  share). Yield 9%, context 6.6x unchanged.
- Metered vs recorded: source instance_cost sums to $9.541, so
  Averth v8 is 2.83x the source field (was 8.25x). Still not a bill:
  dollars are list prices on chars/4 estimated tokens with full-
  history accumulation and no cache discount. Never quote $27.04
  as what anyone was charged, and never quote the old $78.75.
