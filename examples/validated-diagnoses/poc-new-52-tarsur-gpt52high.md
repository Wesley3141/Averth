# POC new-52: tarsur385 scikit-learn, gpt-5.2-high — PASS as a clean-run diagnosis

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No individual recipient is verified for this file;
do not send it to anyone on this file alone.

## Label, read first

This is real scikit-learn, from tarsur385/swebench-verified-trajectories.
It is NOT the batch-3 lane-13 result: lane 13 searched SWE-smith,
SWE-Gym, Nebius, and nvidia Open-SWE-Traces and found 0 rows for
scikit-learn/scikit-learn, then fell back to the ecosystem library
scikit-learn-contrib/imbalanced-learn. This lane does not fill the
SWE-smith scikit-learn lane either (that lane remains unfilled: the
repo is absent from SWE-smith by construction). The repo here is
scikit-learn__scikit-learn, the model run is gpt-5.2-high, and both
are stated in the title, not hidden.

## Repo selection, fixed before counting outcomes

Source dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
(5,002 files: 10 model runs x 500 SWE-bench Verified instances).

The model run gpt-5.2-high exists (listed exhaustively by lane 48's
scan of the 10 runs in this dataset, and re-verified here via the
Hugging Face tree API, recursive listing, 500 instance dirs + 500
traj files). Instance-dir counts per repo in this run, alphabetical:

- astropy__astropy: 22 — already used (poc-new-37, Opus run), skipped
- django__django: 231 — already used (poc-new-11, Opus run), skipped
- matplotlib__matplotlib: 34 — already used (poc-new-42, Opus run), skipped
- mwaskom__seaborn: 2 — below the 20-file threshold, skipped
- pallets__flask: 1 — below threshold, skipped
- psf__requests: 8 — below threshold, skipped
- pydata__xarray: 22 — skipped per this lane's brief (reserved for
  another lane), not because it fails the threshold
- pylint-dev__pylint: 10 — below threshold, skipped
- pytest-dev__pytest: 19 — below threshold, skipped
- scikit-learn__scikit-learn: 32 — FIRST unused repo with >= 20 files
- sphinx-doc__sphinx: 44 — not reached (later alphabetically)
- sympy__sympy: 75 — already used (poc-new-36, Gemini run), skipped

The "first" claim is scoped to this model run; the other nine runs
were not enumerated for this lane. Full tree listing saved with the
work files (dirs-gpt-5.2-high.txt).

## Slice, mechanical

First 20 scikit-learn instance dirs in sorted order, no outcome
filtering, all downloaded verbatim:

scikit-learn__scikit-learn-10297, -10844, -10908, -11310, -11578,
-12585, -12682, -12973, -13124, -13135, -13142, -13328, -13439,
-13496, -13779, -14053, -14087, -14141, -14496, -14629.

The remaining 12 scikit-learn files in this run (14710, 14894, 14983,
15100, 25102, 25232, 25747, 25931, 25973, 26194, 26323, 9288) were not
used. Zero instance-id overlap with any earlier POC file, checked by
text scan of all poc-*.md and poc-new-*.md files (no hits).

## Conversion, mechanical (same rules as poc-new-42)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-52/`
(convert.py, events.jsonl, averth-output.txt, report.html, raw/ 20
traj files, dirs-gpt-5.2-high.txt, list_tree.py).

- One file = one attempt, case_id = instance_id (20 unique ids).
- Model mapping, stated, no price invented: traj
  info.docent.model_label is "gpt-5.2-high" in all 20 files. Averth
  price table v6 has NO gpt-5.2 entry (grep of pricing.py confirms:
  the GPT-5 keys in v6 are gpt-5.6, gpt-5.6-mini, and gpt-5-nano).
  The converter therefore emits provider "openai" and model
  "gpt-5.2-high" verbatim. Averth falls back to its documented
  $1.00/$3.00 per 1M estimate and flags openai:gpt-5.2-high in
  unpriced_models. No remap to gpt-5.6 was made.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" in this slice).
- retry event before the next assistant turn when the preceding
  tool observation contains the literal string "Traceback", a
  genuinely recorded failure signal (same rule as POC10 and lanes
  11/12/42). Tool observations carrying a nonzero "Exit code:"
  prefix (77 in this slice) are counted as a check only, not
  converted to retries, to stay identical to those lanes — so the
  retry count below is a lower bound.
- end event: success = info.resolved, the dataset's own label.
  info.scores.resolved agrees with info.resolved on all 20 rows
  (0 mismatches). All 20 rows have exit_status Submitted.
- Tokens are NOT recorded in these traj files (assistant message
  metadata is None in all 20 files), so tokens are chars//4
  estimates, same limitation as lanes 11/12/36/37/42.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified: `git log` shows fafab07 as HEAD; `averth pricing`
  reports v6, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --anomaly`
- CLI exit code: 0, no crash, no error.
- Events: 1,167 total (542 model, 562 tool, 43 retries, 20 end).
  Model events exactly equal the source api_calls sum (542),
  independently counted. Tool mix: bash 562.
- Attempts: 20. Resolved (dataset labels): 17 (85.0%). Failed: 3
  (scikit-learn__scikit-learn-10908, -13142, -14087).
- Total cost: $6.34.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $0.00;
  vendor-supplied (billed) $0.00; estimated (fallback prices)
  $6.34, of which model $5.21 at fallback prices and $1.12 of
  built-in bash per-call estimates (562 x $0.002). Cost per
  successful outcome (fully loaded): $0.37 (terminal $0.07, retry
  path $0.23, tool $0.07, human $0.00 at the assumed $70.20/hr
  loaded rate, which is an assumption, not measured).
- Five layers: context compounding 8.0x first-to-last step,
  context tax $0.00 (see anomaly 1); yield 24% of tokens on the
  terminal path (76% burned on retries and failed runs); heavy
  tail p50 $0.22 / p95 $0.61 / max $1.31 per attempt, top 5%
  consumed 21% of budget; model mix 100% openai:gpt-5.2-high.
- Failed runs: $0.59 (9% of spend, zero outcomes). Retry path:
  $3.96 model+retry spend on discarded paths (overlapping lens,
  not additive). Costliest attempt: scikit-learn__scikit-learn-12682
  at $1.31 (6x p50), 1 retry, context grew 28.3x, flagged
  runaway-shaped by --anomaly.

## Independent checks (not the CLI's summary)

- Token math: 5,093,135 input tokens x $1.00/1M + 39,675 output
  tokens x $3.00/1M = $5.212, matching Averth's $5.21 model spend.
  Tools: 562 x $0.002 = $1.124. Sum $6.336, matching the $6.34
  total within rounding.
- Output-token caveat, material: only 35 of 542 assistant messages
  carry any prose content (9,122 chars total); the rest are
  tool-call-only turns. Output tokens here are therefore mostly
  tool-argument characters, not full model response text, and
  any reasoning tokens are absent from the message text. Output
  spend is understated versus a real bill by an unknown amount,
  in the same direction as the sympy lane (poc-new-36).
- Recorded-cost comparison: the 20 traj files' own
  info.model_stats.instance_cost values sum to $5.74. Averth's
  $6.34 is +10.5% above it. Decomposition: Averth model spend
  $5.21 is 9.2% BELOW recorded, and the $1.12 of built-in tool
  defaults more than accounts for the net excess. Do not quote
  $6.34 as what anyone was charged; it is a fallback-price
  estimate plus tool defaults, not a bill.

## Anomaly check required by the lane

1. Context tax $0.00 despite 8.0x growth: the known
   fallback-pricing quirk (the fallback path records in_price
   0.0, and the context-tax loop skips steps with no input
   price). Do not quote it as "context was free."
2. Top-finding vs waste-lens gap: the report's finding 2 says
   "Retry loops burned $4.72 (75% of spend)" while the waste
   lens says retry path $3.96. The $0.76 gap is unexplained in
   the report. This file quotes the waste-lens figure ($3.96)
   and flags the gap, the same pattern lane 38 flagged ($0.52
   gap there). Do not quote $4.72 without the gap note.
3. No "-$0" priced-bucket artifact: the priced bucket is $0.00,
   a real zero (nothing priced), not a tiny negative float.
4. No "Measured" label anywhere: the report's cost basis is
   ESTIMATED, with the do-not-quote-as-a-bill warning printed.
5. Zero-token guard did not trigger (542 model events, nonzero
   tokens throughout).

## Limits that must travel with this number

- 17 of 20 resolved is NOT a general solve rate. It is 20
  scikit-learn Verified issues under one model (gpt-5.2-high),
  one scaffold (mini-swe-agent format), in sorted instance
  order. Do not present 85% as GPT-5.2's or any scaffold's
  general SWE-bench rate.
- Dollars are fallback-price estimates plus tool defaults, not
  a bill, and the model has no verified vendor price in v6:
  if OpenAI's gpt-5.2 price differs from the $1/$3 fallback,
  the model spend moves with it. Never quote $6.34 without its
  fallback basis and the unpriced-model flag.
- Tokens are chars//4 estimates, not recorded usage, and output
  tokens understate full model responses (see independent checks).
- Retry count (43) is a lower bound under the Traceback rule;
  77 tool observations carry nonzero exit codes that were not
  converted to retries.
- PASS criteria met: real per-step input (20 full trajectories,
  not aggregates), attempts 20, CLI exit 0, totals reported,
  honest ESTIMATED cost basis, no hidden substitution. Clean-run
  diagnosis only: no change was applied or measured, no saving
  is claimed, and this file alone does not make the lane
  outreach-ready (no verified individual recipient).

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. `openai:gpt-5.2-high`
is now priced at the GPT-5.2 rate $1.75/$14.00 per 1M (OpenAI GPT-5.2
page lists high as a reasoning-effort level of the same model; this is
not a remap to gpt-5.6). Attempt, resolved (17/20), and retry (43)
counts are unchanged. Old total $6.34 all fallback ESTIMATED -> new
total $10.59, of which priced $9.47 and tool estimates $1.12. Cost per
success $0.37 -> $0.62. Failed $0.59 (9%) -> $0.98 (9%). Context tax
$0.00 (fallback quirk) -> $7.23 (76% of model spend). Waste-lens retry
path $3.96 -> $7.13; the top finding now decomposes it ($7.13 model
plus $0.77 retry-path tools = $7.90 headline). Source recorded $5.74:
Averth is now 1.84x the source (was 1.10x at fallback rates). Still
ESTIMATED (chars/4 tokens). New report:
hidden_files/poc-new-52/averth-output-v7.txt.