# Hostile review — pass 2: averth/policy.py simulate_policy() + policy_text()
Reviewer: policy-sim subagent | Date: 2026-10-02
Scope: `averth/averth/policy.py` lines 57–115 ONLY (`simulate_policy`, `policy_text`).
NOT reviewed (other reviewer's): `export_ledger`, `load_ledger`.
Context: Phase 1 fixed C1–C3 / H1–H4 / M1–M3 from AUDIT-2026-10-02.md.

Method: built a 5-attempt ledger by hand with known costs/yields, computed
every expected value on paper, then ran a verification script
(/tmp/verify_sim.py, all asserts green). Edge cases actually executed:
cap exactly equal, cap=0, yield exactly at floor, floor=1.0, floor=0,
zero-token attempts, empty ledger, both-policies-None, CLI real path
(cap-only), NaN cost, missing keys.

## Findings

### MEDIUM

**M1. Strict-`>` stop boundary is still undocumented (audit's LOW note, never fixed).**
`averth/policy.py:70`: `a["total_cost"] > max_cost_per_attempt` — a run
costing EXACTLY the cap is NOT stopped. Same for the yield floor
(`policy.py:74`): yield exactly at the floor is not stopped. Verified by
hand and by execution: cap=6.00, run a2 at $6.00 → reasons `['yield 50% <
floor 75%']` only, no cap reason; yield exactly 0.75 with floor=0.75 →
would_stop=0.
The behavior is defensible (a cap permits spending up to the cap), but it is
documented NOWHERE: not in the `simulate_policy` docstring, not in a code
comment, not in README's `--policy-cap` section (README.md:165-169).
The Phase-1 audit explicitly said "Defensible, but document the boundary"
and Phase 1 did not do it. A prospect A/B-testing the boundary against the
natural reading of "cap" will find behavior that contradicts their mental
model with no documentation to settle it. Fix: one docstring line, e.g.
"Both thresholds are strict: a run at exactly the cap (or yield) is not
stopped."

**M2. `policy_text` prints `$None` / `None` and inconsistent precision in the header.**
`averth/policy.py:102-104`:
`f"Policy replay: max_cost_per_attempt=${p['max_cost_per_attempt']}, yield_floor={p['yield_floor']}"`
- Both policies unset (direct API call): prints `max_cost_per_attempt=$None,
  yield_floor=None`. Verified by execution.
- The REAL CLI path hits this: `averth/cli.py:175-179` calls
  `simulate_policy` when *either* arg is set, so `averth trace x --policy-cap
  5` (no `--policy-yield`) prints `max_cost_per_attempt=$5, yield_floor=None`
  — verified by execution.
- Precision is inconsistent in the same output: header uses `str()` (`$6.0`)
  while the reason lines two lines below use `$%.2f` (`$6.00`). Verified in
  actual `policy_text` output.
No dollar figure is wrong — the aggregates all check out — but this is
prospect-facing output (`cli.py:84` stdout, `demo.py:98`). A report header
with `$None` in it reads as a bug in the product. Fix: format None as
"none"/"—" and use `:,.2f` in the header like every other dollar figure.

### LOW

**L1. Docstring overclaims what is returned.**
`averth/policy.py:57-62`: "Returns the runs that would have been stopped and
the exposed spend." It does not return the runs — it returns a dict of
aggregates plus `worst` (top-10 stopped). And `policy_text` never prints
`exposed_spend`/`exposed_share` at all, even though the docstring's headline
is "the exposed spend." The text shows saved + collateral but omits the
exposed total the docstring promises. Cosmetic, but docs-vs-code (rubric #7).

**L2. NaN `total_cost` is silently skipped and poisons the aggregate.**
Verified: `total_cost=NaN` with a cap → `NaN > cap` is False, so the run is
silently NOT stopped; `sum()` then makes `total` NaN and `exposed_share`
NaN. The tracker's NaN rejection (audit checklist 2) means exporter-produced
ledgers can't contain NaN — only hand-crafted JSON can — so this is LOW.
Missing keys fail LOUD (`KeyError: 'total_cost'`, verified), which is the
correct behavior and is kept.

## Verified-correct (rubric #1, hand-traced to the cent)

All of the following matched hand computation exactly (script asserts all
green, exposed_share to 1e-9):

- 5-attempt hand ledger, cap=6.00 / floor=0.75: would_stop=3,
  would_stop_failed=1, would_stop_success=2, saved_spend=6.00,
  collateral_spend=17.50, exposed_spend=23.50, exposed_share=23.5/25.5.
- Failed-vs-collateral split is the honest one: a stopped SUCCESS run's cost
  goes to `collateral_spend`, never `saved_spend`.
- Both-reasons case: a run breaching cap AND floor gets one entry with both
  reasons (`['cost $7.50 > cap $6.00', 'yield 20% < floor 75%']`), counted once
  in would_stop. `worst` sorted cost-desc, top 10.
- `policy_text` numbers match the sim dict exactly (stop counts, saved,
  collateral, per-run lines, SUCCESS/FAILED labels).
- cap=0 (prior P1 fix): uses `is not None`; stops all runs with cost > 0;
  a $0.00 run is correctly NOT stopped by cap=0. Regression test
  `tests/test_review_round2.py:111` covers this.
- yield_floor=1.0 stops every run with any waste (y<1); floor=0.0 stops
  nothing; zero-token attempts get y=1.0 and pass yield floors (matches the
  tracker's convention noted in the audit).
- Empty ledger: all counts 0, exposed_share 0.0 (no ZeroDivisionError), worst=[].
- Single combined reason rendering: `a4: $7.50 (success) — cost $7.50 > cap
  $6.00; yield 20% < floor 75%` — matches sim reasons verbatim.

## Rubric items with nothing to flag

- #2/#3 hardcoded/staleness: no prices, rates, or thresholds in these two
  functions — all policy parameters are caller-supplied. Clean.
- #6 security: zero network imports in `averth/policy.py` (grep-verified);
  `policy_text` is plain text for stdout, not HTML — no injection vector in
  scope; this module does no deserialization (that's `load_ledger`, another
  reviewer's scope). Clean.
- #8 dead code: none; no TODOs/placeholders in the two functions.
- Error handling beyond L2: type errors (e.g. string cost) raise loudly
  rather than corrupting; missing keys → KeyError. Acceptable.

## Prompt-injection note (per rubric security note)

No web access was used in this review; all verification ran locally against
the repo. No injected directives encountered.

## Verdict

The replay math is trustworthy — hand-verified to the cent, the
saved/collateral split is honest, and the prior cap=0 bug is genuinely
fixed. The code is NOT wrong; it is under-documented at the threshold
boundary (M1, a carry-over from the first audit that Phase 1 ignored) and
sloppy in its user-facing header formatting (M2). Neither blocks a pilot,
both should be fixed before a VP Finance reads the output.
