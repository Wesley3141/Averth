# POC new-56: tarsur385 SWE-bench Verified, pydata__xarray under glm-5-high — PASS

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft.

## Overlap disclosure, read first

This lane uses exactly the same 20 xarray instance ids as
poc-new-51-tarsur-xarray, in the same sorted order: pydata__xarray-2905,
-3095, -3151, -3305, -3677, -3993, -4075, -4094, -4356, -4629, -4687,
-4695, -4966, -6461, -6599, -6721, -6744, -6938, -6992, -7229.
Instance-id overlap with poc-new-51 is therefore 20 of 20, not zero.
What is different is the model run: poc-new-51 is claude-opus-4.6,
this lane is glm-5-high. The trajectories are different runs
(Opus: 504 model events for these 20 files; GLM: 1,745 model events),
so trajectory-level overlap is zero, but issue-level overlap is total.
Do not count this lane as 20 new issues, and do not quote it as
independent of poc-new-51. The repo-level selection rule (first repo
alphabetically with at least 20 files, skipping astropy, django,
flask, requests, sympy, matplotlib) was applied to the glm-5-high run
before this overlap was found; lane 51 was running in parallel in the
same batch, so the repo had not been "used" when this lane was briefed.
The honest label is: same 20 xarray issues, second model run.

## Source

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Slice: `swebench_verified_raw/glm-5-high/`, repo pydata__xarray.
  The full glm-5-high run has 500 instance dirs. Repo counts in that
  run: astropy 22, django 231, matplotlib 34, mwaskom/seaborn 2,
  pallets/flask 1, psf/requests 8, pydata__xarray 22, pylint-dev/pylint
  10, pytest-dev/pytest 19, scikit-learn 32, sphinx-doc/sphinx 44,
  sympy 75. Skipping the already-used repos (astropy, django, flask,
  requests, sympy, matplotlib), pydata__xarray is the first repo
  alphabetically with at least 20 files. The remaining 2 xarray files
  in this run (-7233, -7393) were not used.
- Slice rule, mechanical, no outcome filtering: first 20 xarray
  instance dirs in sorted order, listed above, downloaded verbatim.
- Format: mini-swe-agent 1.1 trajectories (trajectory_format
  mini-swe-agent-1.1, mini_version 2.1.0). Every file's
  `info.docent.model_label` is "glm-5-high", confirming the run.
  Assistant message `model` fields are empty in these files, so the
  run label, not a per-message model field, is the model evidence.

## Conversion, mechanical (same rules as batch-3 agents 11/12 and batch-4 agents 36/37/42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-56/`
(convert.py, events.jsonl, sample.json, tree.json, averth-output.txt,
report.html, raw/ 20 traj files).

- One file = one attempt, case_id = glm-5-high__<instance_id>.
- Model mapping, stated, no price invented: traj label "glm-5-high"
  -> Averth key "unknown:glm-5-high". Price table v6 prices only
  unknown:glm-5.3 and zai:glm-5.3 ($1.40 input / $4.40 output per 1M,
  cached $0.26). glm-5-high is a different model; it was NOT mapped
  to glm-5.3. Averth therefore applies its documented fallback
  $1.00 input / $3.00 output per 1M and flags unknown:glm-5-high as
  unpriced. Every model dollar below is fallback-estimated, not a
  vendor list price for glm-5-high.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" here).
- retry event before the next assistant turn when the preceding
  tool observation contains "Traceback", a recorded failure signal.
  Tool observations here start "Exit code: N"; the nonzero-exit
  count (594) is reported as a check only, NOT converted to retries,
  to stay identical to agents 11/12/36. Retry count 110 is therefore
  a lower bound, not a count of all failed tool calls.
- end event: success = info.resolved, the dataset's own label, kept
  mechanically even where exit_status is odd (see below).
- Token counts are NOT recorded in these traj files, so tokens are
  chars//4 estimates, same limitation as batch 1 and agents 11/12.
  Recorded per-instance costs live in info.model_stats.instance_cost
  and are compared below, not replaced by Averth's dollars.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --anomaly`
- CLI exit code: 0, confirmed on a direct rerun (not only through
  a pipe). No crash, no error.
- Events: 3,663 total (1,745 model, 1,788 tool, 110 retry, 20 end).
- Attempts: 20. Autonomous completions (dataset resolved labels):
  15 (75.0%). Failed: 5 (pydata__xarray-4687, -6599, -6938, -6992,
  -7229). Exit statuses: 19 Submitted, 1 LimitsExceeded (-6599,
  failed, the costliest attempt).
- Total cost, metered: $33.14.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $0.00;
  vendor-supplied (billed) $0.00; estimated (fallback) $33.14, of
  which model $29.57 at fallback prices and tool $3.58 in built-in
  bash per-call estimates (1,788 calls x $0.002, flagged as
  estimates in the report). No model dollar used a vendor price.
- Independent check: 29,134,100 input tokens x $1.00/1M +
  144,650 output tokens x $3.00/1M = $29.568, matching Averth's
  $29.57; plus $3.58 tool = $33.14. Per-attempt recomputation from
  events.jsonl also totals $33.1441.
- Cost per successful outcome (fully loaded): $2.21
  (terminal $0.20, retry path $1.77, tool $0.24, human $0.00 at
  the assumed $70.20/hr rate, an assumption, not measured).
- Five layers: context compounding 15.0x first-to-last step,
  context tax $0.00 (see anomaly 1); yield 10% of tokens on the
  terminal path (90% burned on retries and failed runs; yield is
  a token-share definition, NOT the 75% resolved rate);
  heavy tail p50 $0.93 / p95 $5.05 / max $5.59 per attempt,
  top 5% consumed 17% of budget.
- Failed runs: $13.15 (40% of spend, zero outcomes). Retry path:
  $26.54 model+retry spend on discarded paths (overlapping lens,
  not additive).
- Retries: 110, all "traceback in previous tool observation".
  Nonzero-exit tool observations: 594 (check only, see above).

## Anomaly check required by the lane

- No "-$0" priced-bucket artifact: the priced bucket is $0.00,
  a real zero because no model dollar was priced.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- $0 context tax despite 15.0x growth: the known fallback-pricing
  quirk. The fallback path records in_price 0.0, and the
  context-tax loop skips steps with no input price. Do not quote
  it as "context was free."
- Top-finding vs waste-lens gap, flagged not hidden: the text
  output's top finding says retry loops burned $29.42 (89% of
  spend) while the waste lens says retry path $26.54. The file
  quotes the waste-lens figure; the $2.88 gap is unexplained in
  Averth's output (same pattern as earlier lanes) and is a report
  wording inconsistency to fix, not a number to average away.
- Cost per successful outcome is defined with 15 successes, so
  it is not vacuous here (contrast lanes with 0 successes, where
  Averth prints $0.00 and it must be read as UNKNOWN).
- Model-event vs source-api_calls gap, explained: model events
  1,745 vs source info.model_stats.api_calls sum 1,753, a gap of
  8. The converter emits exactly one model event per assistant
  message, and in the 8 affected files the assistant-message count
  itself is api_calls minus 1 (e.g. -2905: 236 messages vs 237
  api_calls). The gap is in the source's counts, not a converter
  drop; the extra call is presumably a final/submission call not
  stored as an assistant message. It is negligible to totals
  (8 calls out of 1,753) and is disclosed, not adjusted for.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $13.1481.
- Averth metered $33.14 vs recorded $13.15: about 2.5x higher.
  This is the same direction as the Opus tarsur lanes (about
  6.8x-8.25x) but smaller, and unlike poc-new-12 (+8.9%) and
  poc-new-36 (-8.3%), so the gap is slice- and model-dependent
  and must not be averaged away.
- Likely causes, stated as hypotheses only, not verified: Averth
  accumulates full history into context with no truncation and
  applies no cache discount, chars//4 estimates are not recorded
  usage, and the fallback $1/$3 price is not glm-5-high's vendor
  price. The Averth figure therefore does not reconcile to the
  source's cost field. Quote $33.14 only as "Averth chars/4
  fallback-price estimate", never as what anyone was charged.
- Do NOT compare $33.14 against poc-new-51's $57.36 as model
  efficiency: poc-new-51 prices Opus at $15/$75 per 1M, this lane
  prices GLM at fallback $1/$3. The price bases are different,
  so the totals are not comparable as model costs.

## Cross-model note, same 20 issues (post-hoc, not a controlled experiment)

- poc-new-51 (Opus 4.6): 16 of 20 resolved, $57.36 estimated
  (priced), 504 model events, context 5.1x, tax $37.50, source
  cost $8.41.
- This lane (glm-5-high): 15 of 20 resolved, $33.14 estimated
  (fallback), 1,745 model events, context 15.0x, tax $0.00
  (fallback quirk), source cost $13.15.
- Failed sets overlap almost entirely: Opus failed -6599, -6938,
  -6992, -7229; GLM failed those four plus -4687. The one
  difference is -4687 (Opus resolved, GLM failed). GLM took about
  3.5x as many model turns on the same issues, but turn count
  and resolved rate are not comparable as efficiency without a
  common price and recorded tokens.

## Limits that must travel with this number

- 15 of 20 resolved is NOT a general solve rate. It is the first
  20 xarray instances in sorted order under one model, out of 22
  xarray files in this run, and the same 20 issues as poc-new-51.
  Do not present 75.0% as GLM's or any scaffold's general
  SWE-bench rate.
- Tokens are chars//4 estimates, not recorded usage; dollars are
  fallback-price estimates plus tool defaults, not a bill, and
  not glm-5-high's vendor price.
- The native question "what does glm-5-high actually cost?" is
  unanswered by this lane: v6 has no glm-5-high price, and adding
  one requires verifying it from the vendor's own pricing page,
  then rerunning these exact events.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, anomalies disclosed. Clean-run
  diagnosis only: no change applied or measured, no saving
  claimed, no individual recipient verified, not ready to send
  to anyone on this file alone.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. `unknown:glm-5-high`
is now priced at the GLM-5 rate $1.00/$3.20 per 1M (Z.ai pricing page;
high effort is the same model). Attempt, resolved (15/20), and retry
(110) counts are unchanged. Old total $33.14 all fallback ESTIMATED ->
new total $33.17, of which priced $29.60 and tool estimates $3.58.
The move is only $0.03: input was already $1.00 under fallback, and
output moves $3.00 -> $3.20 on 144,650 output tokens. Cost per success
$2.21 unchanged (rounded). Failed $13.15 (40%) unchanged. Context tax
$0.00 (fallback quirk) -> $25.83 (87% of model spend). Waste-lens
retry path $26.54 -> $26.57. Source recorded $13.15: Averth is now
2.52x the source. Still ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-56/averth-output-v7.txt.