# POC new-53: tarsur385 scikit-learn, Claude 4.5 Haiku — PASS

## Verdict: PASS (clean-run diagnosis only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No change was applied or measured, and no saving
is claimed.

## Label, read first

This is a tarsur385 scikit-learn result, NOT a SWE-smith scikit-learn
result. Batch-3 lane 14 proved scikit-learn/scikit-learn is absent
from SWE-smith trajectories (0 rows in 76,002 scanned), and batch-3
lane 13 ran scikit-learn-contrib/imbalanced-learn as a fallback and
stated plainly that it was not scikit-learn. This lane is the first
real scikit-learn/scikit-learn slice in the set: a different dataset
family (tarsur385 SWE-bench Verified trajectories), a different
model (Claude 4.5 Haiku), and different instance ids. Do not quote
it as filling the SWE-smith scikit-learn lane, and do not send it
to scikit-learn maintainers as a finding about their project on
this file alone (20 instances, one model, one scaffold, estimated
tokens — see Limits).

## Source and selection

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Model run: `swebench_verified_raw/claude-4.5-haiku-high`
  (500 instance dirs in this run, counted from the full paginated
  Hugging Face tree listing, saved as
  `dirs-claude-4.5-haiku-high.txt` with the work files).
- Repo counts in this run, by instance dir: astropy 22, django
  231, matplotlib 34, mwaskom/seaborn 2, pallets/flask 1,
  psf/requests 8, pydata/xarray 22, pylint-dev/pylint 10,
  pytest-dev/pytest 19, scikit-learn/scikit-learn 32,
  sphinx-doc/sphinx 44, sympy 75. (Total 500; the tree listing
  also returns each `.traj.json` file path, so raw path counts
  double-count — the 500 figure is instance dirs, not paths.)
- Selection rule, fixed before counting outcomes: first repo
  alphabetically with at least 20 files, skipping the repos
  already used in earlier lanes — django, flask, requests,
  sympy, astropy, matplotlib, xarray. That skips astropy (used,
  lane 37), django (lane 11), matplotlib (lane 42), seaborn (2,
  below threshold), flask (1, below threshold and used),
  requests (8, below threshold and used), xarray (22, skipped
  here per the brief), pylint (10, below threshold), pytest (19, below
  threshold) — leaving scikit-learn/scikit-learn (32) as the
  first qualifying repo.
- Slice: first 20 scikit-learn files in numeric instance order,
  no outcome filtering. Instances: 9288, 10297, 10844, 10908,
  11310, 11578, 12585, 12682, 12973, 13124, 13135, 13142, 13328,
  13439, 13496, 13779, 14053, 14087, 14141, 14496. The remaining
  12 scikit-learn files in this run were not used.
- Distinctness: zero instance overlap with earlier lanes. No
  earlier lane ran scikit-learn/scikit-learn trajectories:
  lane 13 ran imbalanced-learn, lane 42 only listed
  scikit-learn as a repo count in the Opus run without running
  it, and SWE-Gym's 11 repos do not include scikit-learn.
  Grep over all earlier poc/poc-new files finds no
  scikit-learn__scikit-learn trajectory id from this slice.

## Conversion, mechanical

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-53/`
(convert.py, events.jsonl, sample.json, averth-output.txt,
report.html, raw/ 20 traj files, list_tree.py,
dirs-claude-4.5-haiku-high.txt, scan.log).

- One file = one attempt, case_id = instance_id.
- Model mapping, documented, no price invented: every traj file
  carries `info.docent.model_label = "claude-4.5-haiku-high"`.
  Averth price table v6 prices `anthropic:claude-haiku-4-5` at
  $1.00 input / $5.00 output per 1M tokens (verified 2026-10-02,
  and the dated `claude-haiku-4-5-20251001` key at the same
  $1/$5). The converter emits model `claude-haiku-4-5`
  (Averth resolves the claude- prefix to anthropic), i.e. the
  Haiku 4.5 model at its v6 list price; "high" is an effort
  variant of that run, not a distinct vendor-priced model —
  the same treatment lane 12 gave gemini-3-flash-high, mapping
  it to the v6 gemini-3-flash key. If the label had been a
  different model, the converter would have emitted it raw and
  let Averth flag it unpriced at fallback; that did not happen
  here, and no fallback model dollars appear in this run.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" in this slice).
- retry event before the next assistant turn when the preceding
  tool observation contains the literal string "Traceback", a
  genuinely recorded failure signal (same rule as POC 10 and
  lanes 11/12/36/37/42).
- end event: success = info.resolved, the dataset's own label
  (also info.scores.resolved). All 20 exit statuses are
  Submitted; there are no LimitsExceeded, ServiceUnavailable,
  or other label anomalies in this slice (unlike lane 36's
  sympy slice, which had three).
- Token counts are NOT recorded in these traj files (assistant
  message model and metadata fields are None in all 20), so all
  tokens are chars/4 estimates, not recorded usage.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified by `averth pricing`: v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 1,879 total (880 model, 880 tool, 99 retries, 20 end).
  Cross-check: 880 model events exactly equal the source
  `api_calls` sum (880), and every per-case model-event count
  matches that case's api_calls (20/20, verified
  programmatically). Tool mix: bash 880.
- Attempts: 20. Resolved (dataset labels): 18 (90.0%).
  Failed: 2 (scikit-learn__scikit-learn-12682,
  scikit-learn__scikit-learn-14087).
- Retries: 99, all "traceback in previous tool observation"
  (a lower bound — silent failures without a traceback are
  missed by this rule).
- Total cost: $13.78.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified)
  $12.02; vendor-supplied (billed) $0.00; estimated
  (fallback/tool) $1.76, which is entirely built-in bash
  per-call estimates (880 x $0.002). No model dollars used
  fallback pricing.
- Independent model math: 11,282,623 input tokens x $1.00/1M
  = $11.28 plus 146,792 output tokens x $5.00/1M = $0.73,
  total $12.02, matching Averth exactly.
- Cost per successful outcome, fully loaded: $0.77 (terminal
  $0.03, retry path $0.64, tool $0.10, human $0.00 at the
  assumed $70.20/hr rate, not measured).
- Five layers: context compounding 12.4x first-to-last step,
  context tax $9.74 (81% of model spend); yield 4% of tokens
  on the terminal path; heavy tail p50 $0.57 / p95 $1.45 /
  max $1.85 per attempt; top 5% consumed 13% of budget.
  Model mix: anthropic:claude-haiku-4-5 $12.02 (100%).
- Failed runs: $2.50 (18% of spend, zero outcomes). Retry
  path: $11.51 model+retry spend on discarded paths
  (overlapping lens, not additive).

## Anomaly check

- No "-$0" priced-bucket artifact: the priced bucket is $12.02,
  a real positive figure.
- No $0 context-tax artifact: context tax is $9.74.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.
- Yield 4% with 18/20 resolved is definitional (tokens on the
  terminal path only), not a contradiction — resolution here
  was retry-expensive, the same pattern lane 36 flagged for
  its 20/20 sympy slice (yield 1%). Do not quote "4% yield"
  as a success rate; the resolved rate is 90.0%.
- Top-finding vs waste-lens gap, flagged not hidden: the
  report's top finding says "Retry loops burned $13.00
  (94% of spend)" while waste accounting says retry path
  $11.51 model+retry spend. The file quotes the waste-lens
  $11.51 figure; the $1.49 gap between the two lenses is
  unexplained in Averth's output (same class of gap lanes 38
  and 34 flagged: $0.52 and a retry-loops label on 0 retries).
- Costliest attempt, flagged by Averth's anomaly check:
  scikit-learn__scikit-learn-12682, $1.85 (3x p50), failed,
  4 retries, context grew 32.7x.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $3.67 total.
- Averth metered $13.78 vs recorded $3.67: about 3.75x higher.
  Decomposition: metered model spend $12.02 vs recorded $3.67
  (the gap is the model side; tool defaults add $1.76 on top).
- Likely causes, stated as hypotheses only, not verified:
  Averth accumulates full history with no truncation and no
  cache discount, at list prices on chars/4 estimated tokens,
  while the source field presumably reflects actual API usage
  (with caching and/or truncation). The ratio is smaller than
  the Opus 4.6 slices in this dataset (django ~7.5x, astropy
  ~7.5x, matplotlib ~8.25x) and far closer than those, but
  $13.78 is still not a bill. Do not quote it as what anyone
  was charged.
- Recorded costs are per-instance API costs from the run
  metadata, not Averth-measured bills; the comparison is a
  sanity check on the meter, not a reconciliation to an invoice.

## Limits that must travel with this number

- 18/20 resolved is NOT a general solve rate. It is 20
  scikit-learn Verified issues under one model (Claude 4.5
  Haiku, high-effort run) and one scaffold (mini-swe-agent
  format). Do not present 90.0% as Haiku's or any scaffold's
  general SWE-bench rate.
- Tokens are chars/4 estimates, not recorded usage; dollars are
  list-price estimates plus tool defaults, not a bill.
  Averth's "Priced" bucket means vendor list prices applied to
  estimated tokens here, and the index must label this lane's
  dollars ESTIMATED (tokens estimated), not priced, regardless
  of Averth's bucket name.
- The native SWE-smith scikit-learn lane remains unfilled:
  scikit-learn does not exist in SWE-smith trajectories.
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), attempts 20, CLI exit 0,
  totals reported, honest ESTIMATED cost basis, no -$0/$0
  anomaly, model-event count reconciled exactly to the
  source api_calls sum.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $13.78 (priced $12.02, tool estimates $1.76), attempts
20, resolved 18/20, retries 99, context 12.4x, tax $9.74. No price was
added for this lane's model (the converter already maps
claude-4.5-haiku-high to priced claude-haiku-4-5 at the same $1/$5
rates; the new anthropic:claude-4.5-haiku-high key carries identical
rates, so a verbatim rerun would not move the total). Still ESTIMATED
(chars/4 tokens). New report:
hidden_files/poc-new-53/averth-output-v7.txt.