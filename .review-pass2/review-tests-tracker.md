# Hostile review — the TESTS: tests/test_tracker.py, tests/test_tracker_hardening.py, tests/test_pricing.py

Reviewer posture: hostile. Method: read all three files line by line, hand-verified
the arithmetic in the key assertions, grepped for coverage of every Phase-1 fix
(C1-C3/H1-H4/M1-M3), and then ran REVERSION EXPERIMENTS: in a throwaway copy of
the repo (never touching ~/workspace/averth), I reverted each Phase-1 fix in
averth/tracker.py and re-ran the 40 tests. Results below. All 40 tests pass on
the fixed code.

## Verdict up front

The tests that exist are honest — the arithmetic assertions are hand-computed
literals (not x==x), the identity decompositions are real, and the docstrings
match the fixed code. Nothing here encodes a known bug as expected, and nothing
is tautological.

But the suite FAILS its primary job. Phase 1 fixed seven bugs; the test suite
does not lock in a single one of them. I reverted C1 (success-only breach hook),
C2 (price-vintage stamping), C3/M3 (explicit labor rate / explicit-0), and H2
(explicit_cost flagging) — five fixes — and all 40 tests still passed. A
developer can silently un-fix the flagship critical bug (C1: breach blind to
failed runaways, the entire kill-switch narrative) and CI stays green. That is
the story of this review.

## What the tests get right (no findings here, for the record)

- No tautological assertions found. Every dollar assertion is a hand-computed
  literal: test_tracker.py:34-44 (18.0/0.025/0.010/2.34), :110-116
  (1.50/0.0), :95-105 (p50=10.5, p95=19.05, share=20/210 — re-derived by hand,
  interpolation correct), test_tracker_hardening.py:24-31 (0.4455/0.0045),
  :120-128 (retry_path 0.06 vs terminal 0.05, and the additivity check
  fully_loaded == model + retry_path + tools + human, which locks the
  terminal+retry_path == model+retry identity), :141-151 (context tax 0.012).
- The legacy-ledger test (test_tracker_hardening.py:238) genuinely exercises
  the .get-default degradation path and asserts cost_model_terminal degrades
  to the raw model value — real regression coverage, correctly aimed.
- The extra_model_cost no-double-count test (:137) asserts model==0.05 while
  retry_cost carries the 0.020 — this locks the contract documented in the
  log_retry docstring against a real double-counting failure mode.
- Lifecycle error tests (:185) assert fail-loud RuntimeError for the two most
  likely misuse shapes.

## HIGH findings (missing coverage of Phase-1 fixes — the reversion experiments)

**H-T1. No test for breach-on-failed-attempt — the C1 fix is unguarded.**
tests/test_tracker.py:126-159. All three budget tests end the attempt with
success=True. C1 changed `if success and ...` to fire on ANY over-envelope
attempt. Reversion experiment: restoring the old success-only condition
passes all 40 tests. Missing: (a) failed over-budget attempt fires on_breach
callback, (b) failed over-budget attempt RAISES BudgetBreach with no
callback, (c) the "(failed attempt)" message suffix, (d)
pnl()["budget_breaches_failed"] == 1, (e) hook-vs-pnl count agreement for
the failed shape. This is the audit's flagship critical — "the seed of the
governance story" — and its test coverage is exactly zero. A one-line
regression returns the product to the exact state the audit called
embarrassing, invisibly.

**H-T2. No test for price-vintage stamping — the C2 fix is unguarded.**
Nothing in any of the three files references price_vintage, PRICE_TABLE_VERSION,
or staleness. Reversion experiment: deleting `self.price_vintage =
pricing.price_vintage()` and the pnl "price_vintage" key passes all 40 tests.
Missing: Tracker("x").price_vintage == pricing.price_vintage();
pnl()["price_vintage"] present with version/updated keys; a staleness probe
(stale flag True when the table is older than PRICE_TABLE_STALE_AFTER_DAYS).
C2's entire point is that reports must never silently misattribute dollars to
the wrong price era — the suite verifies none of it.

**H-T3. No test for the labor-rate assumption labeling — the C3/M3 fix is
unguarded.** tests/test_tracker.py:205 (test_custom_human_cost_per_min) asserts
the multiplication (2.00 * 3 = 6.00) but never touches pnl()'s
"human_rate_assumed" flag, and no test passes human_cost_per_min=0.
Reversion experiment: restoring the `or`-based default (explicit 0 silently
falls back to 1.17, the M3 bug) passes all 40 tests. Missing: (a) default
rate -> human_rate_assumed is True; (b) explicit rate -> False; (c) explicit
0 -> human_cost 0.0 AND assumed False. C3's fix exists because the headline
demo finding is "driven by an unmeasured assumption, not data" — the suite
still treats the $70/hr default as data everywhere (e.g. :33 asserts
human_cost == 2.34 derived from the silent default, with no assumed flag
assertion beside it).

**H-T4. No test for explicit_cost / default-priced tool flagging — the H2 fix
is unguarded.** log_tool_call(name) without cost uses the TOOL_PRICES
estimates; Phase 1 added explicit_cost=False and pnl()'s
tools_default_priced_spend / tools_default_priced_names. No test in any file
mentions explicit_cost, tools_default_priced_spend, or
tools_default_priced_names. Reversion experiment: removing the flag from
tool_steps passes all 40 tests. Missing: (a) default-priced call lands in
tools_default_priced_spend with its name in tools_default_priced_names;
(b) explicit cost= does NOT; (c) the two spends are disjoint
(tools_default_priced_spend <= cost_tools). H2 is the audit's "wrong default
does the most damage" finding — uncovered.

## MEDIUM findings (gaps in fail-loud and boundary coverage)

**M-T1. No tests for the numeric loud-failure contract.** tracker.py rejects
NaN/inf/non-numeric/bool and caps tokens at 1e12 (_check_finite,
_check_nonneg_int); the audit verified this by hand. The suite tests only
negative tokens (test_tracker_hardening.py:46-53). Missing: NaN tokens raise
ValueError, inf cost raises ValueError, None/bool raise ValueError, tokens >
1e12 raise ValueError, negative tool cost raises ValueError, negative
human_cost_per_min in the constructor raises ValueError. Silent-NaN
corruption is the failure mode the validation guards exist for; the guards
have no tests.

**M-T2. No boundary test for the breach threshold.** end_attempt uses strict
`>` (a run exactly at budget does not breach). No test asserts the
exactly-at-cap case. If someone "fixes" this to `>=`, or the audit's LOW
note ("document the boundary") is never honored, nothing notices. One-line
test, missing.

**M-T3. cache_read_discount is set but never asserted as surfaced.** 
test_tracker_hardening.py:55 passes cache_read_discount=0.50 and asserts the
resulting dollars — good math coverage — but pnl()["cache_read_discount"]
(the H3 surfacing) is never read by any test. The fix's visibility half is
untested.

**M-T4. No failed-attempt breach message or ordering assertions.** Even for
the success path, no test checks the BudgetBreach message contents, and no
test checks whether the attempt is still recorded in t.attempts after the
raise path (the code appends before raising — intended or not, it is
untested either way).

**M-T5. Empty-tracker pnl() is untested.** pnl() with zero attempts exercises
the tot_tok==0 -> yield 1.0 branch, the empty-costs percentile branch, and
success_rate 0.0. A fresh Tracker().pnl() is a realistic first call (CLI
report path); no test calls it.

## LOW findings

**L-T1. Dead imports in tests/test_tracker.py.** Line 3 `import math` and
line 9 `from averth import pricing` are both unused (verified by grep —
zero `math.` / `pricing.` references in the file). AI slop; harmless, but
exactly the kind of thing a "production ready, series A" bar should not
ship in the test suite.

**L-T2. No double-end_attempt test.** tests/test_tracker.py:185 covers
start-before-log and double-start, but not end_attempt() twice (second call
should RuntimeError via _req). Trivial gap.

**L-T3. Branch-retry edge shapes untested.** No test for a second retry on
the same branch (documented: "discards the redo as well"), no test for
log_retry(branch=...) on an estimate step plus a priced step mixing, no
test that tool_steps on a retried branch feed retry_tool_cost. The single
branch test (:72) covers the happy path only.

## Reversion-experiment log (method evidence)

All experiments ran in /tmp/averth-revert-test, a throwaway copy; the real
repo was never modified.
1. Restored `if success and self.budget_per_success ...` (C1 revert) -> 40 passed.
2. Deleted price_vintage stamping (C2 revert) -> 40 passed.
3. Restored `human_cost_per_min or pricing.HUMAN_COST_PER_MIN` and neutralized
   the assumed flag (C3/M3 revert) -> 40 passed.
4. Removed explicit_cost from tool_steps (H2 revert) -> 40 passed.
Combined C1+C2+C3+M3+H2 revert -> 40 passed. The suite cannot distinguish the
fixed tracker from the audited-buggy tracker on any of these five fixes.

## Recommended test additions (priority order)

1. test_budget_breach_fires_on_failed_attempt (hook) + raises variant; assert
   "(failed attempt)" in the message and budget_breaches_failed == 1.
2. test_price_vintage_stamped: Tracker.price_vintage == pricing.price_vintage();
   pnl()["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION.
3. test_human_rate_assumed_flag: default True / explicit False / explicit 0
   honored with human_cost 0.0.
4. test_default_priced_tool_spend_flagged: default call -> spend+names;
   explicit cost -> absent; disjointness check.
5. test_breach_at_exact_budget_does_not_fire.
6. Loud-failure parametrized test: NaN/inf/None/True/1e13 tokens, negative
   tool cost, negative constructor rate -> ValueError.

## Counts

- CRITICAL: 0 (no test produces wrong dollars, corrupts data, or crashes —
  the damage here is missing coverage, not wrong coverage)
- HIGH: 4 (H-T1 breach-on-failed unguarded; H-T2 vintage unguarded; H-T3
  labor-rate labeling unguarded; H-T4 explicit_cost flagging unguarded)
- MEDIUM: 5 (M-T1 numeric loud-failure; M-T2 breach boundary; M-T3
  cache_read_discount surfacing; M-T4 breach message/ordering; M-T5
  empty-tracker pnl)
- LOW: 3 (L-T1 dead imports; L-T2 double-end; L-T3 branch-retry edges)

No prompt-injection content encountered during this review (no web use).
