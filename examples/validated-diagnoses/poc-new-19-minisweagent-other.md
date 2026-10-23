# POC new-19: mini-SWE-agent, disjoint slice (batch-3 agent 19 of 20)

## Verdict: PASS (clean-run diagnosis test only, with the anomalies stated below)

No one contacted, nothing sent, nothing posted, no private data used.

## What is different from the first batch

- First batch: mini-SWE-agent-s3, 12 attempts, 9 completions, model
  `claude-sonnet-4-20250514`, SWE-bench Verified entry
  `20250726_mini-v1.0.0_claude-sonnet-4-20250514` in m0at/experiments,
  trajectories from the public `swe-bench-submissions` S3 bucket.
- This lane: the SAME leaderboard entry, but a DISJOINT slice of it.
  A different-model m0at mini entry could not be enumerated: the
  GitHub `evaluation/verified` tree page renders only the first 100
  entries (chronologically up to 20250629), and web search surfaced no
  second `mini-v1.0.0` entry name. Per the task's fallback clause, this
  lane therefore uses another mechanical mini-SWE-agent slice, and
  that fallback is stated here rather than hidden.
- Slice rule (mechanical, no cherry-picking): from
  `per_instance_details.json` (500 instances, saved verbatim in the
  first-batch trace directory), take every 42nd instance starting at
  index 21, excluding the first batch's 12. That yields 11 instances,
  none overlapping the first batch. Same model, same entry, different
  instances.

## Source

- Leaderboard entry: https://github.com/m0at/experiments/tree/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514
- Trajectories: public S3 bucket `swe-bench-submissions`, prefix
  `bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/`
  (anonymous read; files saved verbatim, one per instance).
- Per-instance resolved flags and recorded costs: the same entry's
  `per_instance_details.json` (saved verbatim in the first batch).
- Work files (raw trajectories, converted events, HTML report):
  `~/workspace/goals/agent-p-l-validation/files/poc-new-19-work/`

## Conversion (mechanical, same rules as the first batch)

- One model event per assistant turn, model `claude-sonnet-4-20250514`,
  one `bash` tool event per turn (mini-SWE-agent issues exactly one
  bash command per turn by construction).
- A `retry` event before the next model call when the tool-result
  message carries `<returncode>` != 0 (a real recorded failure signal).
- End event success = the leaderboard's real `resolved` verdict for
  that instance, not an inferred completion.
- Token counts are mechanical chars/4 estimates (accumulated context
  chars for input, turn chars for output). The trajectories record no
  per-call usage. This is the same limitation as the first batch and
  it drives the anomaly below; it is not hidden.

## Averth run (upgraded build)

- Repo: `~/workspace/averth` at commit `071d0e1`, price table v6
  (verified 2026-10-22).
- Command: `averth trace events.jsonl --format jsonl` (from the repo
  venv).
- CLI exit code: 0, no crash, no error.
- Attempts: 11 (all 11 trajectories converted and run).
- Autonomous completions: 8 of 11 (72.7%), resolved verdicts from the
  leaderboard, not inferred.
- Retries: 31 (25x returncode 1, 4x returncode 2, 1x returncode 4,
  1x returncode 5).
- Total cost: $12.58.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $11.86,
  vendor-supplied (billed) $0.00, estimated (fallback/tool) $0.72
  (all of it built-in bash per-call estimates, with Averth's warning).
  Cost per successful outcome (fully loaded): $1.57.
- Five layers: context compounding 8.7x first-to-last step, context
  tax $9.15 (77% of model spend); yield 22% of tokens on the terminal
  path; heavy tail p50 $0.75 / p95 $2.66 / max $3.35 per attempt;
  model mix 100% `anthropic:claude-sonnet-4-20250514` at $3.00/$15.00
  per 1M tokens.
- Failed runs: $6.07 (48% of spend, zero outcomes). Retry path:
  $9.25 model+retry spend on discarded paths.

## Anomaly that must travel with this number

- The leaderboard's RECORDED cost for exactly these 11 instances sums
  to $3.50. Averth's metered total is $12.58, about 3.6x the recorded
  figure. This is the same direction and size as the first batch
  ($17.49 metered vs $4.55 recorded, about 3.8x).
- Cause, stated not excused: token counts here are chars/4 estimates
  of full accumulated context, priced at list rates, with no prompt
  cache recorded. The recorded costs reflect the provider's actual
  billing (including caching). So $12.58 is a list-price, estimated
  token view, NOT a bill, and Averth's own COST BASIS banner says so.
  Quoting $12.58 without that sentence would be misleading.
- Per-instance recorded costs (for audit): django-12193 $0.308,
  django-12708 $0.178, django-12713 $0.197, django-13810 $0.252,
  django-15268 $0.716, django-15629 $0.538, django-16255 $0.095,
  scikit-learn-12585 $0.178, scikit-learn-15100 $0.230,
  sphinx-9230 $0.359, sphinx-9673 $0.450. Resolved: 8 of 11.
- No other anomaly: no dropped tokens (every assistant turn became a
  model event), no misleading "Measured" label (the report says
  ESTIMATED and PRICED), no invented outcomes, no invented tokens.

## Why this passes, and what it does not prove

- PASS criteria met: real per-step input (11 full trajectories, not
  aggregates), attempts >= 10, exit 0, totals produced, honest cost
  basis printed, anomalies noted.
- This does NOT prove Averth matches billed cost: it overstates this
  slice by ~3.6x for the reason above. It does NOT prove value to a
  live operator: no one acted on a finding here, and the "one change
  worth testing" (fix returncode-1 validation failures, compact
  context) is a hypothesis from the report, not a tested change.
- What would strengthen it: a mini-SWE-agent entry with recorded
  per-call usage (not chars/4), or a different-model entry once one
  is enumerated, run through the same mechanical conversion.
