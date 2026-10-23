# POC new-55: tarsur385 pydata__xarray, gpt-5-mini — PASS (clean-run diagnosis only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. Averth code was not edited.

## Verdict: PASS as a clean Averth run, NOT as a value POC

Real per-step input (20 full trajectories, not aggregates), CLI exit 0,
totals reported, honest ESTIMATED cost basis. No change was applied or
measured, no saving is claimed, and no individual recipient is verified,
so this file alone does not make the lane sendable.

## Source and selection, fixed before counting outcomes

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (5,002 files: 10 model runs x 500 SWE-bench Verified instances).
- Model run: `swebench_verified_raw/gpt-5-mini/`, 500 instance
  directories. Repo counts in this run, counted from the full HF tree
  listing (500 directories): astropy__astropy 22, django__django 231,
  matplotlib__matplotlib 34, mwaskom__seaborn 2, pallets__flask 1,
  psf__requests 8, pydata__xarray 22, pylint-dev__pylint 10,
  pytest-dev__pytest 19, scikit-learn__scikit-learn 32,
  sphinx-doc__sphinx 44, sympy__sympy 75.
- Selection rule, applied in alphabetical repo order, skipping repos
  already used by earlier tarsur385 lanes: astropy (poc-new-37),
  django (poc-new-11), matplotlib (poc-new-42), flask/requests
  (poc-new-12), sympy (poc-new-36) are all skipped; seaborn (2),
  flask (1), requests (8), pylint (10), pytest (19) are below the
  20-file threshold. The first qualifying repo is therefore
  pydata__xarray (22 files). This matches the note in poc-new-42
  that xarray was the next qualifying repo after matplotlib.
- Slice: first 20 xarray files by numeric instance number, no outcome
  filtering: 2905, 3095, 3151, 3305, 3677, 3993, 4075, 4094, 4356,
  4629, 4687, 4695, 4966, 6461, 6599, 6721, 6744, 6938, 6992, 7229.
  The remaining two xarray files in this run (7233, 7393) were not
  used. All 20 files were downloaded verbatim.
- Distinctness: xarray appears in no earlier POC file. This is a
  different repo and a different model from poc-new-11 (django,
  claude-opus-4.6), poc-new-12 (flask/requests, Gemini), poc-new-36
  (sympy, gemini-3-pro), poc-new-37 (astropy, claude-opus-4.6), and
  poc-new-42 (matplotlib, claude-opus-4.6).
- Trajectories are genuine attempts, not empty generations: 13 to 49
  assistant turns per attempt, all exit_status Submitted, patches
  written via patch.txt in the tool output. This is not the moto /
  MONAI first-20 problem (poc-new-32, poc-new-33), where most rows
  were 4-to-6-turn directory listings with no patch.

## Conversion, mechanical (same rules as poc-new-36/42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-55/`
(convert.py, events.jsonl, sample.json, tree.json, averth-output.txt,
report.html, raw/ 20 traj files).

- One file = one attempt, case_id = gpt-5-mini__<instance_id>.
- Model mapping, stated: traj info.docent.model_label is "gpt-5-mini"
  in all 20 files; converter emits provider "openai", model
  "gpt-5-mini". Averth price table v6 has NO openai:gpt-5-mini entry
  (it has gpt-5.6, gpt-5.6-mini, and gpt-5-nano, but not gpt-5-mini),
  so Averth uses its documented $1.00/$3.00 per 1M fallback and flags
  it unpriced. No price was invented, and the run was NOT remapped
  to gpt-5.6-mini or any other priced key.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" in this slice).
- retry event before the next assistant turn when the preceding
  tool observation contains "Traceback", a recorded failure signal.
  Nonzero-exit tool observations (58) are reported as a check only,
  not converted to retries, to stay identical to poc-new-36/42.
- end event: success = info.resolved, the dataset's own label
  (also info.scores.resolved).
- Token counts are NOT recorded in these traj files, so tokens are
  chars//4 estimates, same limitation as poc-new-11/12/36/37/42.
  Recorded per-instance costs live in info.model_stats.instance_cost
  and are compared below, not replaced by Averth's dollars.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6.
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl
  --html report.html --agent "tarsur385 xarray gpt-5-mini" --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 946 total (444 model, 444 tool, 38 retries, 20 end).
  Model events match assistant-turn counts exactly in all 20 files;
  they are 7 below the source api_calls sum (451), because 7 files
  each carry one extra api_call with no assistant message in the
  file (3095, 3993, 4075, 4966, 6461, 6721, 7229). Same 1-call gap
  pattern as poc-new-36 sympy, negligible to totals, not hidden.
- Attempts: 20. Autonomous completions (dataset resolved labels):
  10 (50.0%). Failed: 10. All 20 exit_status Submitted.
- Total cost, metered: $5.13.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) -$0 (see
  anomaly check); vendor-supplied (billed) $0.00; estimated
  (fallback prices) $5.13, of which model $4.24 and built-in bash
  tool estimates $0.89 (444 calls x $0.002). No model dollars used a
  vendor price, because gpt-5-mini is unpriced in v6.
- Independent check: 4,153,108 input tokens x $1.00/1M +
  28,997 output tokens x $3.00/1M = $4.2401, matching Averth's
  $4.24 model spend; 444 tool events x $0.002 = $0.888, matching
  $0.89; sum $5.13.
- Cost per successful outcome (fully loaded): $0.51 (terminal $0.09,
  retry path $0.34, tool $0.09, human $0.00 at the assumed
  $70.20/hr rate).
- Five layers: context compounding 7.2x first-to-last step,
  context tax $0.00 (see anomaly check); yield 20% of tokens on
  the terminal path (80% burned on retries and failed runs);
  heavy tail p50 $0.20 / p95 $0.67 / max $0.86 per attempt;
  top 5% consumed 17% of budget. Costliest: pydata__xarray-6938,
  $0.86, failed, 48 turns, flagged runaway-shaped by --anomaly
  (retry path $0.76, context 13.1x).
- Failed runs: $3.26 (64% of spend, zero outcomes). Retry path:
  $3.38 model+retry spend on discarded paths (overlapping lens,
  not additive). Retries: 38, all "traceback in previous tool
  observation" (lower bound; silent failures missed).

## Anomaly check required by the lane

- "-$0" priced bucket: REPRODUCED. The priced bucket prints "-$0"
  even though all model spend is fallback-estimated. This is the
  pre-existing display artifact seen in poc-new-03, poc-new-17,
  poc-new-27, and poc-new-50, still unfixed. Do not quote "-$0" as
  a dollar figure; the priced bucket here is effectively $0.
- $0 context tax: REPRODUCED, and it is the known fallback-pricing
  quirk, not "context was free". The fallback cost path records
  in_price 0.0, and the context-tax loop skips steps with no input
  price, so a run priced entirely at fallback shows 7.2x context
  growth with $0.00 context tax (same as poc-new-09, poc-new-15,
  poc-new-17, poc-new-27, poc-new-40, poc-new-41). Do not quote
  $0.00 context tax as a finding.
- Top-finding vs waste-lens gap: the text output's top finding
  says "Retry loops burned $3.66 (71% of spend)" while waste
  accounting says retry path $3.38. The $0.28 gap is unexplained
  in the output; this file quotes the waste-lens $3.38. Same
  inconsistency pattern as poc-new-38 ($0.52 gap) and poc-new-35
  (overlapping lenses, not additive).
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Zero-token guard did not trigger.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $1.0611 total
  (per file $0.0252 to $0.1528).
- Averth metered $5.13 vs recorded $1.0611: +$4.07 (+384%, about
  4.8x). Decomposition: metered model spend $4.24 is $3.18 above
  recorded model spend (recorded costs include no tool defaults,
  so the $0.89 tool estimate is additional). Likely causes,
  stated as hypotheses only, not verified: (1) Averth applies the
  $1.00/$3.00 fallback because gpt-5-mini has no v6 price, and the
  real gpt-5-mini price is almost certainly below fallback input
  price; (2) Averth accumulates full history with no truncation
  and no cache discount on chars//4 estimates, while the source
  field presumably reflects actual API usage. Do not quote $5.13
  as what anyone was charged, and do not back out a gpt-5-mini
  price from this ratio — that would be inventing a price.
  The honest next step is verifying gpt-5-mini list prices from
  OpenAI's own pages, adding the key with a regression test, and
  rerunning this exact events file; the totals will move, the
  attempt/resolved/retry counts will not.

## Limits that must travel with this number

- 10 of 20 resolved is NOT a general solve rate. It is 20 xarray
  Verified issues under one model (gpt-5-mini) in one scaffold
  (mini-swe-agent 1.1). Do not present 50% as gpt-5-mini's or
  xarray's general SWE-bench rate.
- Tokens are chars//4 estimates, not recorded usage; dollars are
  fallback estimates plus tool defaults, not a bill. The $5.13
  total is the least price-anchored total in this batch's tarsur
  lanes precisely because the model is unpriced; compare it only
  to other fallback lanes, never to priced lanes like poc-new-42
  ($78.75, Opus list prices) as if they were on the same basis.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, anomalies disclosed. Clean-run
  diagnosis only: no change applied or measured, no saving
  claimed, no operator, no value proof.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. `openai:gpt-5-mini`
is now priced at $0.25/$2.00 per 1M (OpenAI GPT-5-mini page). Attempt,
resolved (10/20), and retry (38) counts are unchanged. Old total $5.13
all fallback ESTIMATED -> new total $1.98, of which priced $1.10 and
tool estimates $0.89. Cost per success $0.51 -> $0.20. Failed $3.26
(64%) -> $1.22 (62%). Context tax $0.00 (fallback quirk) -> $0.84
(76% of model spend). Waste-lens retry path $3.38 -> $0.87; the top
finding now decomposes it. Source recorded $1.06: Averth is now 1.87x
the source (was 4.8x at fallback rates). The v6 $5.13 must no longer
be quoted. Still ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-55/averth-output-v7.txt.