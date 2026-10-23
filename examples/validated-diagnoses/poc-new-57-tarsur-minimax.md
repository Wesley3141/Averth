# POC new-57: tarsur385 pydata__xarray, minimax-m2.5-high — PASS (clean-run diagnosis only)

## Verdict: PASS as a clean Averth run, NOT a value POC and NOT sendable

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No individual recipient is verified for this file.

## Source and selection

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (trajectory collection, not the SWE-bench task set).
- Model run: `swebench_verified_raw/minimax-m2.5-high/`, 500 instance
  directories in total. Repo counts in this run, counted from distinct
  instance directories: astropy__astropy 22, django__django 231,
  matplotlib__matplotlib 34, mwaskom__seaborn 2, pallets__flask 1,
  psf__requests 8, pydata__xarray 22, pylint-dev__pylint 10,
  pytest-dev__pytest 19, scikit-learn__scikit-learn 32,
  sphinx-doc__sphinx 44, sympy__sympy 75.
- Selection rule, fixed before counting outcomes: first repo
  alphabetically with at least 20 files, skipping repos already used
  in earlier tarsur385 slices (astropy in poc-new-37, django in
  poc-new-11, matplotlib in poc-new-42, flask/requests in poc-new-12,
  sympy in poc-new-36). That gives pydata__xarray, 22 files. The
  slice is the first 20 xarray instance ids in numeric order, no
  outcome filtering: 2905, 3095, 3151, 3305, 3677, 3993, 4075, 4094,
  4356, 4629, 4687, 4695, 4966, 6461, 6599, 6721, 6744, 6938, 6992,
  7229. The remaining two xarray files in this run (7233, 7393)
  were not used.
- Distinctness: pydata__xarray appears in no earlier POC slice.
  poc-new-42 mentioned xarray only as the next qualifying repo
  after matplotlib; it did not run it. These 20 instance ids are
  new to the POC set.
- All 20 files are mini-swe-agent format, all exit status Submitted,
  all model label `minimax-m2.5-high` (info.docent.model_label) and
  config model `minimax/minimax-m2.5` with reasoning effort high.

## Conversion, mechanical (same rules as poc-new-11/12/36/37/42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-57/`
(convert.py, events.jsonl, averth-output.txt, report.html, raw/ 20
traj files, dirs-minimax-m2.5-high.txt, minimax-dirs.txt,
minimax-scan.log).

- One file = one attempt, case_id = instance_id.
- Model mapping, stated, no price invented: traj label
  "minimax-m2.5-high" is emitted as provider "minimax", model
  "minimax-m2.5-high". That key is NOT in Averth price table v6,
  so Averth prices it at the documented fallback $1.00 input /
  $3.00 output per 1M tokens and flags
  `minimax:minimax-m2.5-high` as unpriced. The model was NOT
  remapped to a priced model.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" here: 1,353 of 1,353).
- retry event before the next assistant turn when the preceding
  tool observation contains the literal string "Traceback", a
  recorded failure signal, same rule as POC 10.
- end event: success = info.resolved, the dataset's own label
  (also info.scores.resolved).
- Tokens are NOT recorded in these traj files, so tokens are
  chars//4 estimates, same limitation as the other tarsur385
  slices. Assistant message metadata is None in all 20 files.
  No cache counts exist, so no cache discount is applied.
  Tool spend is Averth's built-in per-call estimate, not a
  measured tool bill.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified 2026-10-23 by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "tarsur385 xarray minimax-m2.5-high" --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 2,841 total (1,353 model, 1,353 tool, 115 retries, 20 end).
  Model events exactly equal the source api_calls sum (1,353),
  independently counted from the events file.
- Attempts: 20. Autonomous completions (dataset resolved labels):
  17 (85.0%). Failed: 3 (pydata__xarray-4687, -6992, -7229).
- Total cost, metered: $21.29.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $0.00;
  vendor-supplied (billed) $0.00; estimated (fallback prices)
  $21.29, of which model $18.59 at fallback and tool $2.71
  (1,353 bash calls at Averth's $0.002 built-in default).
  Independent check: 18,220,235 input tokens x $1.00/1M +
  122,713 output tokens x $3.00/1M = $18.59, matching Averth.
- Cost per successful outcome (fully loaded): $1.25
  (terminal $0.04, retry path $1.06, tool $0.16; components sum
  to $1.26 before rounding).
- Five layers: context compounding 11.8x first-to-last step,
  context tax $0.00 (see anomaly 1); yield 3% of tokens on the
  terminal path (97% burned on retries and failed runs — this
  is Averth's terminal-path token definition, NOT the resolved
  rate of 85%, do not conflate them); heavy tail p50 $0.63 /
  p95 $2.65 / max $3.63 per attempt, top 5% consumed 17%.
- Failed runs: $5.81 (27% of spend, zero outcomes). Retry path:
  $17.98 model+retry spend on discarded paths (overlapping lens,
  not additive). Retries: 115, all "traceback in previous tool
  observation" (lower bound: silent failures missed).
- Costliest attempt: pydata__xarray-4687, $3.63 total, $3.33
  model, 147 model calls, 7 retries, context 18.8x, failed.
  Averth flags it runaway-shaped. By contrast the source's
  costliest file by recorded cost is pydata__xarray-6599
  ($0.2245 recorded, $1.36 Averth model) — the two rankings
  differ, because Averth's dollars are fallback prices on
  untruncated chars//4 history, not the source's cost field.

## Anomaly check

- No "-$0" priced-bucket artifact: the priced bucket is $0.00,
  a real figure, because every model dollar is fallback.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Context tax $0.00 despite 11.8x growth: the known
  fallback-pricing quirk (fallback path records in_price 0.0,
  so the context-tax loop skips it). Do not quote it as
  "context was free."
- Top-finding vs waste-lens gap, same pattern as earlier lanes:
  the top finding says retry loops burned $20.35 (96% of spend)
  while waste accounting says retry path $17.98. The file
  quotes the waste-lens figure for retry path and flags the
  $2.37 unexplained gap; the two lenses are not additive and
  neither should be summed with failed-run spend.
- Cost per success components sum to $1.26 vs the $1.25 fully
  loaded figure: rounding, noted here, not hidden.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $1.60 total
  (17 resolved, 3 failed; per-file $0.0201 to $0.2245).
- Averth metered $21.29 vs recorded $1.60: about 13.3x higher.
  Direction is expected (fallback $1/$3 list prices on
  untruncated chars//4 history with no cache discount, vs the
  source's own cost field for a low-priced model), but the
  magnitude means $21.29 must never be quoted as what anyone
  was charged, and must never be compared against priced-model
  lanes as if it were on the same price basis. It is a fallback
  estimate, full stop.
- Recorded costs are per-instance API costs from the run
  metadata, not Averth-measured bills; the comparison is a
  sanity check on the meter, not a reconciliation to an invoice.
  Why the source field is so low (real MiniMax pricing,
  truncation, caching, or reasoning-token accounting) is NOT
  established from these files and is not claimed here.

## Limits that must travel with this number

- 17 of 20 resolved is NOT a general solve rate. It is 20
  xarray Verified issues under one model (minimax-m2.5-high)
  in one scaffold. Do not present 85% as MiniMax's or any
  scaffold's general SWE-bench rate.
- Tokens are chars//4 estimates, not recorded usage; dollars
  are fallback prices plus tool defaults, not a bill, and
  not comparable to priced-model lanes without that basis.
- Yield 3% is definitional (tokens on the terminal path only);
  resolution was retry-expensive, which is the finding, not
  a contradiction with 85% resolved.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, no -$0/$0 anomaly hidden.
  This is a clean-run diagnosis only: no change was applied
  or measured, no saving is claimed, and no operator or
  recipient is attached to it.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $21.29, all ESTIMATED at fallback, because
minimax:minimax-m2.5-high could NOT be verified from MiniMax's own
pricing page and was deliberately left unpriced (third-party
consensus $0.30/$1.20 was not fetched from the vendor page and was
not used). Attempts 20, resolved 17/20, retries 115, context 11.8x,
context tax now n/a (input prices missing for fallback calls) instead
of the old $0.00, which must not be quoted as "context was free".
Still ESTIMATED, compare only to other fallback lanes. New report:
hidden_files/poc-new-57/averth-output-v7.txt.