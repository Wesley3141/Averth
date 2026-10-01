# Findings: mini-SWE-agent trajectories (Claude Sonnet 4)

12 real trajectories, converted mechanically, run through the CLI with zero
hand-fixing of records. This source is special: the leaderboard entry also
publishes REAL per-instance recorded costs, so the meter can be checked
against ground truth.

## CLI outcome
`python3 -m averth.cli trace events.jsonl --format jsonl` — exit 0, clean
parse, no crashes, no unpriced models (after the pricing fix below).
`--policy-cap 1.00` replay also runs clean: would have stopped 6 of 12 runs,
exposing $14.36 (82% of metered spend).

- Attempts: 12, autonomous completions: 9 (75.0%)
- Retries: 32 (every one backed by a recorded nonzero return code),
  human escalations: 0, reopened: 0
- Total metered cost: $17.49; fully loaded per success: $1.94
- Context compounding: 9.4x input growth first to last step
- Yield ratio: 24% terminal-path tokens (76% burned on retries/dead ends)
- Heavy tail: p50 $1.22 / p95 $3.92 / max $3.92; top 5% consumed 22%

## Issues found

1. [pricing gap, FIXED] `claude-sonnet-4-20250514` was missing from
   `pricing.MODEL_PRICES` and fell back to the documented estimate.
   Disposition: added to `averth/pricing.py` at the published Anthropic
   list price ($3.00/1M input, $15.00/1M output). Tests:
   `tests/test_pricing.py`.

2. [pricing-model limitation, DOCUMENTED not fixed] Metered cost vs the
   REAL recorded per-instance costs (`compare.py`):
   metered $17.49 vs recorded $4.55, ratio 3.84x; per-instance ratios
   1.91x to 4.47x, rising with run length. Solving for an implied
   prompt-cache hit rate reproduces the recorded costs with hit rates of
   0.48-0.90 (higher on longer runs), exactly the signature of prompt
   caching on full-history resends. The library prices every input token
   at list rate and has no cache term, so it overstates model spend ~3-4x
   against a caching harness. Disposition: documented as a known
   limitation. Not fixed because the traces record no cache usage, so a
   cache-aware schema extension could not be validated against real data
   here; recommended follow-up is a `cached_input_tokens` field on the
   model event priced at the provider's cache-read rate.

3. [report clarity, NOTED not changed] "Cost per successful outcome" shows
   `Retries: $0.00` next to `Retries: 32` because retry waste is booked
   into the model line (steps flagged retry-path) rather than a separate
   retry dollar bucket; only `extra_model_cost` passed to `log_retry`
   lands in the retry line. The waste is visible in the yield ratio, but a
   reader can misread retries as free. Left as designed; noted for a
   future report pass.

4. [robustness, VERIFIED] Malformed input (non-JSON line) fails cleanly:
   exit 2 with `line 2: invalid JSON`, no traceback, no partial ledger.

## Economic insight
One failed run, django__django-11265, cost $3.92 metered ($0.92 recorded),
the single most expensive run in the set: 9 recorded tool failures across
63 turns, resolved=False. The 3 failed runs (25% of attempts) consumed
$6.36 of $17.49 metered, 36% of total spend, for zero accepted outcomes.
Against the REAL recorded costs the same shape holds at lower absolute
levels: $4.55 total across 12 runs, $0.51 per resolved instance. The P&L
story is the same either way: the tail is failed long-horizon grinds, and
a per-attempt cap is the highest-leverage control.
