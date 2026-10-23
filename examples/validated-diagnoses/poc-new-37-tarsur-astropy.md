# POC new-37: tarsur385 astropy slice (SWE-bench Verified trajectories, Claude Opus 4.6)

## Verdict, in one line

- PASS as a clean Averth run (CLI exit 0), on real public astropy
  trajectories from a different dataset family than SWE-smith.
- This is NOT a SWE-smith astropy result. Batch-3 agent 14 proved
  astropy is absent from SWE-bench/SWE-smith-trajectories (0 rows in
  76,002 scanned). Do NOT count this file as filling the SWE-smith
  sympy/astropy lane. It is a tarsur385 astropy POC, labelled as such
  everywhere.

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated, no aggregates converted into events.

## Averth version used

- Repo `~/workspace/averth`, commit `fafab07`, price table v6
  (verified 2026-10-22), Langfuse cached-alias fix included.
- Command, from `~/workspace/averth`:
  `.venv/bin/python -m averth.cli trace
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-37/events.jsonl
  --format jsonl --html report.html`
- CLI exit code: 0.

## Source

- Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Slice: `swebench_verified_raw/claude-opus-4.6/astropy__astropy-*`,
  mini-swe-agent format, model run claude-opus-4.6.
- The claude-opus-4.6 run holds 22 astropy directories. Selection,
  fixed before counting outcomes, no outcome filtering: the first 20
  by numeric instance number — 7166, 7336, 7606, 7671, 8707, 8872,
  12907, 13033, 13236, 13398, 13453, 13579, 13977, 14096, 14182,
  14309, 14365, 14369, 14508, 14539. The remaining two (14598, 14995)
  are NOT used.
- Distinct from: poc-new-11 (same dataset family and model run,
  django repo, not astropy), poc-new-12 (same dataset family,
  flask/requests repos, Gemini models, not astropy), first-batch
  POC 10 (SWE-Gym Claude, different family), and batch-3 agent 14
  (SWE-smith sympy/astropy, which does not exist).
- Per-step input is real: each traj file has a `messages` list
  (system, user, assistant with bash tool_calls, tool observations)
  and `info.resolved` plus `info.scores.resolved` as the dataset's
  own solved label. All 20 exit statuses are Submitted.
- What is NOT in the source: per-call token usage. Assistant
  message metadata is None in all 20 files. So tokens are estimated,
  exactly as in poc-new-11 and POC 10, and labelled as such.

## Conversion (mechanical, converter in hidden_files)

- Converter: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-37/convert.py`
- Events: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-37/events.jsonl`
  (1,591 events: 724 model, 754 tool, 93 retry, 20 end).
- Raw files: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-37/raw/`
  (20 `.traj.json` files, downloaded verbatim).
- Rules, fixed, mirroring the poc-new-11 django converter:
  system/user/tool content lengths accumulate into context_chars;
  one model event per assistant turn, input = context_chars // 4,
  output = (assistant content chars + tool argument chars) // 4;
  one tool event per tool_call (function name, always "bash" in
  this slice); retry event before the next assistant turn when the
  preceding tool observation contains the literal string
  "Traceback", a genuinely recorded failure signal; end event
  success = info.resolved (dataset's own label).
- Model-name mapping, documented, no price invented: traj
  info.docent.model_label is "claude-opus-4.6"; Averth's price
  table key is "anthropic:claude-opus-4-6" ($15/$75 per 1M, table
  v6), so the converter emits model "claude-opus-4-6" with no
  provider override (Averth guesses anthropic from the claude-
  prefix). Same model, hyphenated key.
- Cross-check: model events (724) exactly equal the source's
  `info.model_stats.api_calls` sum (724). Tool events (754) are
  the tool_calls in the files.

## Averth result

- Attempts: 20
- Resolved (dataset's own label): 11 (55.0%); failed: 9
- Retries: 93, all "traceback in previous tool observation"
- Total: $92.90
- Cost basis: ESTIMATED, as printed by Averth ("Do not quote this
  report as measured spend or as a bill"). Priced (tokens x vendor
  prices, token provenance unverified): $91.39, all
  anthropic:claude-opus-4-6. Estimated (built-in bash tool
  defaults): $1.51. Billed: $0.00. No model fallback was used.
- Tokens, chars/4 estimates, not recorded usage: 5,742,473 input,
  70,077 output. Independent check: 5,742,473 / 1M x $15 +
  70,077 / 1M x $75 = $91.39, matching Averth's priced bucket.
- Cost per successful outcome, fully loaded: $8.45 (model
  terminal $0.22, retry path $8.09, tool $0.14, human $0.00).
  The retry path dominates the per-success cost, not the
  terminal path.
- Failed runs: $56.21 (61% of spend, zero outcomes).
- Retry path (overlapping lens, not additive with failed runs):
  $88.97 model+retry spend on discarded paths. Averth's top
  finding prints retry loops at $90.21 (97% of spend); the two
  figures are different lenses on the same discarded paths,
  not two separate charges.
- Context compounding: 6.4x input growth first-to-last step;
  context tax $66.19 (72% of model spend).
- Yield: 2%. This is Averth's terminal-path token share, NOT the
  resolved rate. The resolved rate is 55%. Do not conflate them:
  55% of attempts resolved, but only 2% of tokens sat on a
  terminal path, because resolved runs still carry long retry
  histories.
- Heavy tail: p50 $3.65 / p95 $10.17 / max $21.00 per attempt;
  top 5% consumed 23% of budget. Costliest attempt by model
  tokens: astropy__astropy-13398 ($20.85 model, failed, 70
  assistant turns, the longest run in the slice).

## Material discrepancy, not hidden

- The source's own `info.model_stats.instance_cost` sums to
  $12.46 for exactly these 20 attempts. Averth's $92.90 is about
  7.5x that figure, the same direction and magnitude as
  poc-new-11 django (Averth $873.38 vs source $116.05, also
  about 7.5x).
- Likely cause (hypothesis, not verified): Averth accumulates
  full history with no truncation and no cache discount, at
  list prices, on chars/4 token estimates, while the source
  cost field presumably reflects actual API usage. The
  hypothesis is NOT proven from these files alone.
- Consequence: quote $92.90 only as an Averth chars/4 list-price
  estimate, never as what anyone was charged. The $12.46 source
  figure is likewise not independently verified as a bill; it
  is the dataset's own field, reported for comparison only.

## Anomaly check

- No "-$0" priced-bucket artifact in this run's CLI output
  (priced bucket is $91.39).
- No $0 context-tax anomaly (context tax is $66.19).
- No "Measured" label appears; the report carries the COST
  BASIS: ESTIMATED banner and the do-not-quote-as-a-bill warning.
- Zero-token guard did not trigger (tokens present).
- Retry count is a lower bound in the same sense as prior
  lanes: it counts only the recorded "Traceback" signal, so
  silent failures are missed. It is not a claim that only 93
  things went wrong.

## Limits

- Clean-run diagnosis only, not a value POC: no change was
  applied or measured, no saving is claimed, and cost per
  success rests on estimated tokens, not a bill.
- 11/20 resolved is not a general astropy solve rate: 20
  instances, one model run, one scaffold (mini-swe-agent).
- Tokens are chars/4 estimates, so every model dollar inherits
  that estimation error, compounded by full-history accumulation
  (see the 7.5x discrepancy above).
- Not ready to send to anyone: no verified individual recipient
  is attached to this slice, and the dataset authors are not
  identified here as outreach targets.

## Wave-5b addendum (price-table v8, 2026-10-23) — supersedes the totals above

Correction: Anthropic's own pricing page (docs.anthropic.com/en/docs/
about-claude/pricing) lists Claude Opus 4.6 at $5.00 input / $0.50
cached / $25.00 output per 1M tokens. The v6/v7 table carried Opus
4.1's $15/$75 rates onto Opus 4.6, so every dollar above was
overstated 3x on the model side. Opus 4.1 is a distinct model at
$15/$75 and keeps its own entry. The v8 rerun below uses the
corrected price and flags the chars/4 tokens as estimated, so model
spend now lands in the Estimated bucket, not Priced. Attempts 20,
resolved 11, retries 93 are unchanged; only dollars move.
Fresh report: hidden_files/poc-new-37/averth-output-v8.txt and
report-v8.html; pre-correction events preserved as events-v7.jsonl.
- Total $31.97 (was $92.90), all Estimated: model $30.46
  (exactly $91.39 / 3) plus $1.51 tool estimates.
- Cost per successful outcome $2.91 fully loaded (was $8.45).
- Failed runs $19.27 (60% of spend; was $56.21 at 61% — the one-point
  share shift is because tool estimates do not scale with the price
  correction, not a change in outcomes).
- Context tax $22.06 (was $66.19; 72% of model spend, unchanged
  share). Yield 2%, context 6.4x unchanged.
- Metered vs recorded: source instance_cost sums to $12.46, so
  Averth v8 is 2.57x the source field (was 7.46x). Still not a bill:
  dollars are list prices on chars/4 estimated tokens with full-
  history accumulation and no cache discount. Never quote $31.97
  as what anyone was charged, and never quote the old $92.90.
