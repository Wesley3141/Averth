# Hostile review: Tracker.end_attempt — tracker.py lines ~293-373
Reviewer brief: C1-C3/H1-H4/M1-M3 fixes from AUDIT-2026-10-02.md were
applied; this pass reviews the FIXED code. Scope: end_attempt only
(context_growth, context_tax, yield/waste, terminal/retry split,
retry_tool_cost, budget-breach hook). __init__/logging/pnl() out of scope.

All claims below verified by running code (python3, package at
~/workspace/averth/averth/). Script: /tmp/verify_endattempt.py (ephemeral).

## Severity counts
- CRITICAL: 0
- HIGH: 1
- MEDIUM: 0
- LOW: 1

## HIGH

**H1. `budget_per_success=0` silently disables the breach hook (tracker.py:364).**
The C1 fix changed the condition to
`if self.budget_per_success and a["total_cost"] > self.budget_per_success:`
but kept the truthiness trap. A user passing `budget_per_success=0`
(the natural way to say "no spend allowed") gets a hook that can never
fire. Verified:
```
Tracker("agentW", budget_per_success=0, on_breach=cb, human_cost_per_min=0)
start_attempt; log_model_cost_estimate("custom","m", 5.00); end_attempt(success=False)
-> fired=0, no exception. A $5.00 failed runaway passes silently.
```
This is the same falsy-trap class as the audit's P1 (`--policy-cap 0`
silently ignored), which was fixed in policy.py with `is not None` but
missed here. The budget envelope is a governance control; an explicit 0
being silently swallowed is wrong behavior on an edge case.
Fix: `if self.budget_per_success is not None and a["total_cost"] >
self.budget_per_success:` (None stays the documented off-switch).
Note for the pnl() reviewer (out of my scope, handoff only): tracker.py:464-465
uses the identical `if self.budget_per_success and ...` pattern for breach
counting, so the budget=0 blind spot lives there too.

## LOW

**L1. "Identity preserved" comment overclaims by one ulp (tracker.py:346).**
The comment says `terminal + retry_path = model + retry`. It holds to the
cent, not bitwise: `terminal = model - waste_step_cost` then
`(model - w) + (w + r)` does not round-trip to `model + r` in IEEE floats.
My hand trace (scenario A: $0.0105 keep + $0.0135 waste + $0.005 extra)
failed a strict `==` on the $0.0105 terminal value while the cent-level
identity passed (`0.03 == 0.03`). Cent-level is all dollars need, and the
test suite already uses approx, but any consumer doing exact float
equality on the identity will see a mismatch. Suggest softening the
comment to "to the cent".

## Verified correct (the C1 fix holds)

1. **Hook fires on failed over-budget attempts.** All four combos run:
   success+over -> fires, no "(failed attempt)" suffix; success+under ->
   silent; fail+over -> fires WITH " (failed attempt)" suffix;
   fail+under -> silent. Exact message verified:
   `agentX: case cost $1.35 exceeded budget $1.00 (failed attempt)`.
2. **No callback -> raise.** Failed over-budget attempt with
   `on_breach=None` raises BudgetBreach (not silent). Importantly, the
   raise happens AFTER `self.attempts.append(a)` and `self._cur = None`,
   so the tracker stays usable: verified `start_attempt`/`end_attempt`
   work normally after the exception.
3. **Boundary: exactly at budget does not fire.** Strict `>` on
   tracker.py:364; matches the message's own "exceeded budget" wording
   and the audit's accepted boundary convention.
4. **Dollar identity with retries + failed attempts.** Success case:
   terminal=$0.0105 (kept step), retry_path=$0.0185 ($0.0135 waste step +
   $0.005 extra_model_cost), terminal+retry_path == model+retry_cost to
   the cent ($0.03 == $0.03). Failed case: terminal=$0.0,
   retry_path = model + retry_cost exactly ($0.031 == $0.031), and every
   token counted waste (waste_tokens == total_tokens == 4000).
5. **Additive buckets.** terminal + retry_path + tools + human == total
   to the cent ($0.05 == $0.05); retry_tool_cost ($0.01 waste tool) is
   correctly excluded from retry_path_cost per the M3 comment, and
   included in the tools total.
6. **context_tax.** Positive compounding verified by hand: (2000-1000)/1e6
   * $3.00 = $0.003 exactly. Cache-aware effective price applied;
   estimate steps (in_price=0.0) correctly contribute nothing (guard at
   line ~321); formula is visibly signed for shrinking context.
7. **Edge cases.** Single step -> context_growth 1.0, tax 0. Zero steps ->
   no crash, totals 0, identity holds. Branch retry (M1) retro-marking
   verified: past branch steps (model + estimate) both land in
   retry_path_cost ($0.0605 exact to 1e-12).
8. **Message suffix consistency.** Suffix keys off raw `success` param
   while `a["success"] = bool(success)`; truthiness always agrees, so no
   divergence possible.

## Rubric items checked, no finding
- Hardcoded/stale values: none introduced in this range (prices come from
  pricing.py, C2's vintage stamp is __init__ scope).
- NaN/inf: business_value goes through _check_finite; token counts capped
  at _check_nonneg_int; no NaN path in the arithmetic (all sums over
  validated nonneg floats).
- Security: no network, no eval, no deserialization in this range.
- Docs-vs-code: every inline comment in 293-373 matches behavior except
  the L1 ulp nuance; no docstring exists on end_attempt to contradict.
- Dead code/AI slop: none in range.

## Note
No injected-content encounters during this task (no web use).
