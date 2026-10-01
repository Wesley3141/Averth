# Findings: SWE-smith trajectories (SWE-agent, Claude 3.7 Sonnet)

16 real trajectories, converted mechanically, run through the CLI with zero
hand-fixing of records.

## CLI outcome
`python3 -m averth.cli trace events.jsonl --format jsonl` — exit 0, clean
parse, no crashes, no unpriced models (after the pricing fix below).

- Attempts: 16, autonomous completions: 8 (50.0%)
- Retries: 36, human escalations: 0, reopened: 0
- Total cost: $24.79; fully loaded per success: $3.10
- Context compounding: 22.0x input growth first to last step
- Yield ratio: 26% terminal-path tokens (74% burned on retries/dead ends)
- Heavy tail: p50 $1.24 / p95 $5.48 / max $5.48; top 5% consumed 22%
- Model mix: claude-3-7-sonnet-20250219 $18.11 (76%),
  claude-3-5-sonnet-20241022 $5.80 (24%)

## Issues found

1. [pricing gap, FIXED] `claude-3-7-sonnet-20250219` and
   `claude-3-5-sonnet-20241022` were missing from `pricing.MODEL_PRICES`
   and fell back to the documented estimate. Disposition: added both to
   `averth/pricing.py` at their published Anthropic list prices
   ($3.00/1M input, $15.00/1M output). Tests: `tests/test_pricing.py`
   (6 tests: list-price presence and no-fallback flow for all three
   validation-surfaced models).

2. [converter heuristic, FIXED in converter] The first error heuristic
   matched the substring "error" anywhere in any user/tool message,
   including the task PR description and source-code listings containing
   identifiers like `EncodeError`. It fired 208 retry events (44% of model
   turns flagged), which drove the yield ratio to a misleading 0% because
   `log_retry` marks all following steps in the attempt as waste-path.
   Disposition: tightened to observation-only text (tool messages, or user
   messages starting with "OBSERVATION:") and real failure markers
   (Python traceback, unittest/pytest FAIL line, "command not found").
   Now 36 retry events, each spot-checked against a genuine failed tool
   call. This was converter accuracy work, not a library change: the
   library behaved exactly as documented.

3. [trace-quality, DOCUMENTED] No per-call token usage in the source;
   token counts are mechanical estimates (see SOURCES.md). Not a library
   bug; dollar figures are estimates while the retry/failure structure is
   real.

## Economic insight
The 8 failed attempts (half the runs) consumed $13.06 of the $24.79 total,
53% of all spend, while producing zero accepted outcomes. Failures are not
cheap fast exits here: the single costliest run ($5.48) was a success, and
the failed runs burned 74% of all tokens on the retry path. For this
workload the P&L lever is not cheaper models, it is earlier termination of
runs that have entered the retry tail: a $1.00 per-attempt cap replay would
have stopped the worst offenders while keeping the cheap successes.
