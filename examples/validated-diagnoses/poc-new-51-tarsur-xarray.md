# POC new-51: tarsur385 SWE-bench Verified, pydata__xarray slice — PASS

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch,
not a billed-cost receipt, and not a send draft.

## Repo and model chosen, and why

- Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Model run used: `claude-opus-4.6` under
  `swebench_verified_raw/claude-opus-4.6/`. This is the same model
  run as poc-new-11 (django), poc-new-37 (astropy), and
  poc-new-42 (matplotlib), so the file format was already
  verified; the repo is different, so there is zero attempt
  overlap with those lanes.
- Selection rule, applied to that single model run: pydata__xarray
  is the next qualifying repo after matplotlib in lane 42's scan
  (lane 42 listed pydata__xarray at 22 files, "would be the next
  qualifying repo, not used"). Verified here from the full
  paginated HF tree listing for this model run (500 instance
  dirs): pydata__xarray has exactly 22 dirs.
- Slice, mechanical, no outcome filtering: the first 20 xarray
  instance dirs in sorted order:
  pydata__xarray-2905, -3095, -3151, -3305, -3677, -3993,
  -4075, -4094, -4356, -4629, -4687, -4695, -4966, -6461,
  -6599, -6721, -6744, -6938, -6992, -7229.
  All 20 files were downloaded verbatim and are kept under
  `hidden_files/poc-new-51/raw/`. The remaining 2 xarray files
  in this run (-7233, -7393) were not used.
- Distinctness: pydata__xarray appears in no earlier batch
  (batch 1, batch 2, or batch 3 lanes 11-30, or batch-4 lanes
  31-50). Zero instance overlap with poc-new-11 (django),
  poc-new-12 (flask/requests), poc-new-36 (sympy),
  poc-new-37 (astropy), and poc-new-42 (matplotlib) by repo.

## Conversion, mechanical (same rules as poc-new-42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-51/`
(convert.py, events.jsonl, averth-output.txt, report.html,
raw/ 20 files).

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
  recorded failure signal, the same rule as poc-new-42.
- end event: success = `info.resolved`, the dataset's own label
  (also `info.scores.resolved`). All 20 files have exit_status
  "Submitted".
- Tokens are NOT recorded in these traj files, so tokens are
  chars // 4 estimates, same limitation as poc-new-42.
  Recorded per-instance costs live in
  `info.model_stats.instance_cost` and are compared below, not
  replaced by Averth's dollars.
- Cross-check: model events 504 exactly equal the source's
  `model_stats.api_calls` sum 504 across these 20 files. Tool
  events 544, retries 62, end events 20, total events 1,130.
- Empty-generation check: this traj format carries no
  empty_generation flag, and its `info.submission` field is an
  empty string in all 20 files (including all 16 resolved ones),
  so submission emptiness is NOT an empty-generation signal
  here. The genuine-attempt check is turn count: assistant turns
  per attempt range from 10 to 56, with no 4-6 turn view-only
  run of the kind that disqualified the SWE-Gym moto slice
  (poc-new-32). Empty-generation rate on that basis: 0 of 20.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --anomaly`
- CLI exit code: 0, confirmed on a direct run (not only through
  a pipe). No crash, no error, no unpriced model.
- Attempts: 20. Autonomous completions (dataset resolved labels):
  16 (80.0%). Failed: 4 (20.0%): -6599, -6938, -6992, -7229.
- Retries: 62, all "traceback in previous tool observation".
- Total cost: $57.36.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $56.27,
  all anthropic:claude-opus-4-6 (100% of model spend);
  vendor-supplied (billed) $0.00; estimated (fallback/tool)
  $1.09, entirely built-in bash per-call estimates, flagged as
  estimates in the report. No model dollars used fallback pricing.
- Independent check: events tokens 3,453,367 input x $15/1M +
  59,623 output x $75/1M = $56.27, matching Averth.
- Cost per successful outcome, fully loaded: $3.59
  (model terminal $0.31, retry path $3.20, tool $0.07,
  human $0.00, human rate $70.20/hr is an assumption, not
  measured).
- Failed runs: $18.53 (32% of spend, zero outcomes).
- Retry path: $51.24 model+retry spend on discarded paths
  (overlapping lens, not additive; the top finding line quotes
  $52.03 including tool spend on retry loops, 91% of spend).
- Five layers: context compounding 5.1x input growth
  first-to-last step, context tax $37.50 (67% of model spend);
  yield 8% of tokens on the terminal path (92% burned on retries
  and failed runs); heavy tail p50 $1.99 / p95 $5.35 /
  max $12.95 per attempt, top 5% consumed 23% of budget.
- Costliest attempt: pydata__xarray-6599, $12.95, failed, 56
  turns, 6 retries, context 12.8x, flagged runaway-shaped by
  --anomaly. It is 7x the p50 and 23% of the slice total on its
  own; it is a failed run, not a success story.

## Anomaly check

- No "-$0" priced bucket: priced bucket is $56.27.
- No $0 context tax: context tax is $37.50.
- No "Measured" label: the report's cost basis is ESTIMATED,
  with the do-not-quote-as-a-bill warning printed.
- Zero-token guard did not trigger: the trace has tokens
  throughout.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from `info.model_stats.instance_cost`,
  summed over exactly these 20 files: $8.4055.
- Averth metered $57.36 vs recorded $8.4055: about 6.8x higher.
  This is the same direction as poc-new-11 (django, about 7.5x),
  poc-new-37 (astropy, about 7.5x), and poc-new-42 (matplotlib,
  about 8.25x), and unlike poc-new-12 (flask/requests, +8.9%)
  and poc-new-36 (sympy, -8.3%), so the size of the gap is
  slice-dependent and must not be averaged away.
- Likely causes, stated as hypotheses, not verified: Averth
  accumulates full history into context with no truncation and
  applies no cache discount, while the source's cost field
  presumably reflects actual API usage (with whatever caching
  and truncation the real run used), and chars // 4 token
  estimates are not recorded usage. The Averth figure therefore
  overstates what the source says the run cost.
- Consequence: quote $57.36 only as "Averth chars/4 list-price
  estimate", never as what anyone was charged, and never
  alongside the source's $8.4055 as if they were the same thing.
  A real billed-cost POC would need recorded token usage, which
  this source does not publish in its messages.

## Limits that must travel with this number

- 16 of 20 resolved is NOT a general solve rate. It is the first
  20 xarray instances in sorted order under one model
  (claude-opus-4.6), out of 22 xarray files in this run.
  Do not present 80.0% as Claude's or any scaffold's general
  SWE-bench rate.
- Tokens are chars // 4 estimates, not recorded usage; dollars
  are list-price estimates plus tool defaults, not a bill.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20 (>= 10), CLI exit 0, totals
  reported, honest ESTIMATED cost basis, no -$0 / $0-tax /
  "Measured" anomaly, no empty-generation bias (turns 10-56).
  This is a clean-run diagnosis test, not a value POC: no change
  was applied or measured, and cost per success here is an
  estimate built on estimated tokens, not a billed saving.

## Wave-5b addendum (price-table v8, 2026-10-23) — supersedes the totals above

Correction: Anthropic's own pricing page (docs.anthropic.com/en/docs/
about-claude/pricing) lists Claude Opus 4.6 at $5.00 input / $0.50
cached / $25.00 output per 1M tokens. The v6/v7 table carried Opus
4.1's $15/$75 rates onto Opus 4.6, so every dollar above was
overstated 3x on the model side. Opus 4.1 is a distinct model at
$15/$75 and keeps its own entry. The v8 rerun below uses the
corrected price and flags the chars/4 tokens as estimated, so model
spend now lands in the Estimated bucket, not Priced. Attempts 20,
resolved 16, retries 62 are unchanged; only dollars move.
Fresh report: hidden_files/poc-new-51/averth-output-v8.txt and
report-v8.html; pre-correction events preserved as events-v7.jsonl.
- Total $19.85 (was $57.36), all Estimated: model $18.76
  (exactly $56.27 / 3) plus $1.09 tool estimates.
- Cost per successful outcome $1.24 fully loaded (was $3.59).
- Failed runs $6.35 (32% of spend, share unchanged; was $18.53).
- Context tax $12.50 (was $37.50; 67% of model spend, unchanged
  share). Yield 8%, context 5.1x unchanged.
- Metered vs recorded: source instance_cost sums to $8.4055, so
  Averth v8 is 2.36x the source field (was 6.82x). Still not a bill:
  dollars are list prices on chars/4 estimated tokens with full-
  history accumulation and no cache discount. Never quote $19.85
  as what anyone was charged, and never quote the old $57.36.
