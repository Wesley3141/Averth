# POC new-36: tarsur385 sympy slice — PASS (clean-run diagnosis test only)

## Verdict: PASS

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft.

## Label correction, read first

This is NOT a SWE-smith sympy result. Batch-3 agent 14 proved
sympy (and astropy) do not exist in SWE-bench/SWE-smith-trajectories
(76,002 rows scanned across the tool, xml, and ticks splits, 0 hits),
so the lane as originally named cannot be run. This file is the
replacement lane the parent assigned: sympy trajectories from a
different, real public trajectory collection, labelled as such
throughout. It must never be quoted as SWE-smith sympy.

## Source used

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (SWE-bench Verified trajectories in mini-swe-agent format, 10 model
  runs x 500 instances; this dataset is a trajectory collection, not
  the SWE-bench task set).
- Slice rule, mechanical: the first 20 sympy files in numeric order
  under `swebench_verified_raw/gemini-3-pro/`, i.e. instance ids
  sympy__sympy-11618 through sympy__sympy-14531 (see list below).
  One model run only, no outcome filtering: all 20 files in that
  range are included, whatever their label.
- Issues (20): sympy__sympy-11618, -12096, -12419, -12481, -12489,
  -13031, -13091, -13372, -13480, -13551, -13615, -13647, -13757,
  -13798, -13852, -13877, -13878, -13974, -14248, -14531.
- Distinctness: zero overlap with batch-3 agent 11 (django,
  claude-opus-4.6) and agent 12 (flask/requests, Gemini), different
  repo and, for agent 11, different model; zero overlap with
  first-batch POC 10 (SWE-Gym, which does not contain sympy) and
  POC 01 (SWE-smith, which does not contain sympy either). This is
  the first sympy slice in the set.

## Conversion, mechanical (same rules as batch-3 agents 11/12)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-36/`
(convert.py, events.jsonl, averth-output.txt, report.html, raw/ 20 files).

- One file = one attempt, case_id = gemini-3-pro__<instance_id>.
- Model: "gemini-3-pro", provider "google" — the exact Averth price
  table v6 key google:gemini-3-pro at $2.00 input / $12.00 output per
  1M tokens. No mapping and no invented price: the run's docent
  model_label is gemini-3-pro and its config model_name is
  gemini/gemini-3-pro-preview; Averth prices it at the v6
  gemini-3-pro list price (see the recorded-cost comparison below
  for how close that lands).
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" here).
- retry event before the next assistant turn when the preceding
  tool observation contains "Traceback", a recorded failure signal.
  Tool observations also carry a <returncode> tag; the
  nonzero-returncode count (155) is reported as a check only, NOT
  converted to retries, to stay identical to agents 11/12.
- end event: success = info.resolved, the dataset's own label, kept
  mechanically even where exit_status is odd (see anomalies).
- Token counts are NOT recorded per call in these traj files, so
  tokens are chars//4 estimates, same limitation as agents 11/12.
  Recorded per-instance costs live in info.model_stats.instance_cost
  and are compared below, not replaced by Averth's dollars.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified 2026-10-22/23).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 2,681 total (1,282 model, 1,282 tool, 97 retries, 20 end).
  Model-event count vs the source's api_calls sum: 1,282 vs 1,283,
  off by exactly 1 (see anomalies).
- Attempts: 20. Autonomous completions (dataset resolved labels):
  20 (100.0%). Failed: 0.
- Retries: 97, all "traceback in previous tool observation".
- Total cost, metered: $23.48.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $20.91;
  vendor-supplied (billed) $0.00; estimated (fallback/tool) $2.56,
  which is entirely built-in bash per-call estimates. No model
  dollars used fallback pricing.
- Cost per successful outcome (fully loaded): $1.17
  (model terminal $0.01, retry path $1.03, tool $0.13, human $0.00).
- Five layers: context compounding 8.8x first-to-last step,
  context tax $16.52 (79% of model spend); yield 1% of tokens on
  the terminal path (see below); heavy tail p50 $0.99 / p95 $2.20 /
  max $3.75 per attempt, top 5% consumed 16% of budget; model mix
  google:gemini-3-pro $20.91 (100% of model spend).
- Failed runs: $0.00 (0% of spend, zero outcomes). Retry path:
  $20.63 model+retry spend on discarded paths (overlapping lens,
  not additive). Top finding: retry loops burned $23.05 (98% of
  spend).

## Arithmetic check (independent)

- Cumulative-context input tokens summed over model events:
  10,133,820 (each turn re-counts the full accumulated context, so
  this is a cumulative sum, not distinct tokens). At $2.00/1M:
  $20.27. Output tokens: 53,921, at $12.00/1M: $0.65. Sum $20.92,
  matching Averth's $20.91 model spend within rounding.
- Output tokens are small because most assistant messages carry no
  prose content (only tool calls) and the run used high reasoning
  effort, whose reasoning tokens are not present in the message
  text. Model spend here is therefore input-dominated and, if
  anything, understates a real bill that would also charge
  reasoning tokens.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 20 files: $25.61.
- Averth metered $23.48 vs recorded $25.61: -$2.13 (-8.3%).
  Decomposition: metered model spend $20.91 is $4.70 BELOW
  recorded, and the $2.56 of built-in bash tool estimates closes
  part of the gap. Do not quote $23.48 as what anyone was charged.
- This is far closer than batch-3 agent 11's django slice, where
  Averth's $873.38 was ~7.5x the source's $116.05 (full-history,
  no-cache chars//4 estimates vs the run's own metering). The
  sympy slice lands within 9% of recorded, which is a sanity
  check on the meter for this model and format, not a
  reconciliation to an invoice.

## Anomaly check

- No "-$0" priced-bucket artifact: the priced bucket is $20.91,
  a real positive figure. No $0 context-tax artifact: context
  tax is $16.52. No "Measured" label anywhere: the report's cost
  basis is ESTIMATED, with the do-not-quote-as-a-bill warning.
- Yield 1% alongside 20 of 20 resolved is NOT a contradiction:
  yield, as Averth defines it, is the share of tokens on the
  terminal path. With 97 retries across 20 attempts, 99% of
  tokens sit on discarded paths even though every attempt
  eventually resolved. The finding is "resolution was
  retry-expensive", not "resolution failed".
- Label anomalies, kept mechanically, not corrected or dropped:
  (a) sympy__sympy-13031 has exit_status ServiceUnavailableError,
  only 1 assistant turn (2 api_calls), recorded cost $0.0043, yet
  info.resolved is True. It is counted resolved because the
  label says so; its recorded cost is $0.0043, so including or
  excluding it moves totals negligibly, but a 1-turn "resolved"
  run is not evidence of a solved task. (b) Two attempts have
  exit_status LimitsExceeded yet are labelled resolved
  (sympy__sympy-12489, recorded $3.00; sympy__sympy-13615,
  recorded $3.18, both at/over the run's $3.00 cost_limit in
  config). Labels were not overridden.
  (c) Model events (1,282) vs source api_calls (1,283): the
  1-call gap is the 13031 file (1 assistant message, 2 api_calls),
  consistent with one unrecorded/failed call.
- Cost anomaly flagged by Averth (--anomaly): sympy__sympy-12489
  at $3.75 (4x p50), largest driver retry path ($3.49), 10
  retries, context grew 20.2x.

## Limits that must travel with this number

- 20 of 20 resolved is NOT a general solve rate. It is 20 sympy
  Verified issues under one strong Gemini model, with two label
  anomalies above (a 1-turn run and two cost-limit runs counted
  resolved). Do not present 100% as Gemini's or any scaffold's
  general SWE-bench rate.
- Tokens are chars//4 estimates, not recorded usage; reasoning
  tokens are absent from the message text, so output spend is
  understated; dollars are list-price estimates plus tool
  defaults, not a bill.
- The native SWE-smith sympy lane remains unfilled: no public
  SWE-smith trajectory set contains sympy, as agent 14 showed.
  A future SWE-smith-only claim for sympy would still be false.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, no -$0/$0 anomaly, recorded-cost
  comparison included. This is a clean-run diagnosis, not a
  value POC: no change was applied or measured, and no saving
  is claimed.
