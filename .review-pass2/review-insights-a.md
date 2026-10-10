# Review pass 2 — insights.py findings 1-4c (reviewer A)

Scope: `averth/insights.py` findings `failed_spend`, `tail_concentration`,
`retry_waste`, `human_dominance`, `tool_dominance`, `budget_breach`
(lines ~36-153). Reviewed against the Phase-1-fixed working tree.
Findings 5-9 and `findings_text` are another reviewer's.

## Verdict: findings 1-4c are CORRECT. No CRITICAL, no HIGH.

64 scripted checks pass, every threshold hand-verified at the exact
boundary, every dollar figure traced to `tracker.pnl()` to the cent.
The two Phase-1 fixes in my scope hold up:

- **C1 (budget-breach all-attempts counting):** the hook
  (`tracker.py:366`, `a["total_cost"] > self.budget_per_success`, no
  success gate) and `pnl()` (`tracker.py:466-469`, identical strict-`>`
  predicate) count the same set. Verified live: 2 successful + 1 failed
  over-budget attempts → hook fired 3x (the failed one tagged
  "(failed attempt)"), `pnl()` reports `budget_breaches=3`,
  `budget_breaches_failed=1`, `budget_breach_spend=8.25` exact, and the
  finding detail reads "2 accepted outcomes and 1 failed runs exceeded
  the envelope you set, burning $8.25. 1 of them failed runs (pure
  waste)." (insights.py:146-150). Title: "3 of 10 attempts blew the
  $2.00 spend envelope". Severity HIGH (3 >= 10*0.10).
- **C3 (labor-rate assumption note):** the note appears iff
  `human_rate_assumed` is true (insights.py:99). Verified: default
  tracker → note present ("Labor is costed at $70.20/hr loaded (default
  assumption — set your real rate with human_cost_per_min).");
  explicit `human_cost_per_min=0.50` → `human_rate_assumed=False`, no
  note; explicit `0.0` honored (no fallback to default), `cost_human=0`
  → no finding at all.

## What was hand-verified (all pass)

Dollar identity, to the cent:
- `failed_spend` dollars == `cost_failed` (2.75 on the test ledger).
- `tail_concentration` dollars == top-5% sum: n=20, one $41.00 run of
  $60.00 total → dollars 41.00, title "The costliest 1 runs consumed
  68% of the budget".
- `retry_waste` dollars == `cost_retry_path + cost_retry_tools` (M3):
  a $5.00 tool call on a discarded branch with zero model retry-path
  cost → dollars exactly 5.00, share 5/13=0.385 → HIGH.
- `human_dominance` dollars == `cost_human`; per-escalation figure
  `cost_human / max(escalations,1)` exact (explicit $0.50/min, 120 min
  x 4 → "$60.00 loaded each").
- `budget_breach` dollars == `budget_breach_spend` == sum of the 3
  over-envelope attempt totals, exact.

Threshold boundaries (inclusive fire / just-below silent):
- failed_spend: share exactly 0.15 fires; 0.1495 silent.
- retry_waste: 0.20 → MEDIUM; 0.35 → HIGH; 0.199 silent.
- human_dominance: share exactly 0.50 fires; 0.4995 silent.
- tool_dominance: share exactly 0.50 fires.
- tail_concentration: n=19 with share 0.695 stays SILENT (the H3
  honesty gate); n=20 fires.
- budget_breach: 1/12 attempts (8.3%) → MEDIUM; 1/9 (11.1%) → HIGH;
  attempt exactly AT the envelope is not a breach (strict `>`,
  consistent between hook and pnl).

Gaming / floor:
- total $0.99 with 100% failed share → zero findings (the $1.00
  materiality floor, insights.py:30-32).
- NaN `cost_total` → zero findings, no crash.
- total exactly $1.00 passes the floor (boundary is `< 1.0`, documented).
- Zero-attempt and all-zero-cost ledgers → `[]`, no crash (the
  early-return precedes all dict access).

Fallbacks:
- Unnamed retry reason (`log_retry(reason="")`) → no crash, fallback
  action "Name retry reasons via log_retry(reason=...)", no
  "Top culprit" bit.
- `top_insight` returns the highest-dollar finding (verified by id;
  sort is dollars-desc, severity tiebreak).

Docs-vs-code:
- Module docstring "every dollar figure traces back to tracker.pnl()"
  holds for all six findings — every `dollars` value is a pnl field
  or an exact pnl-derived sum.
- Finding 4c comment ("breaches now count EVERY over-envelope attempt
  ... consistent with the live hook") is true: identical predicate in
  hook and pnl.

## MEDIUM

**M-A1. Mixed old/new-field indexing convention in findings().**
insights.py:37-146. The new C1/C3 fields are `.get()`-guarded with
sane defaults (`budget_breaches` → 0, `budget_breach_spend` → 0.0,
`budget_breaches_failed` → 0, `human_rate_assumed` → True, the last
deliberately conservative for old dicts). The older fields are
direct-indexed: `p["cost_failed"]` (37), `p["cost_retry_path"]` (73),
`p["cost_human"]` (94), `p["cost_tools"]` (115), `p["per_success"]`
(33), `p["tail"]` (34). A foreign or stale pnl-shaped dict that has
the new keys but lacks an old one raises KeyError instead of
degrading. The contract ("a pnl() dict") makes this defensible, but
the `.get()` usage elsewhere signals a tolerance intent that is only
half-honored. Pick one: guard all or document that a current
`pnl()` dict is required.

**M-A2. Singular/plural grammar in user-facing strings.**
insights.py:140 ("1 of them failed runs (pure waste)."),
insights.py:146 ("1 failed runs exceeded..."), insights.py:86
("Top culprit: 'x' (1 retries)."). Dollar-correct, but a VP Finance
prospect will read "1 failed runs" in the report. Pluralize at
count == 1.

## LOW

**L-A1. Dead `total > 0` guard in tail_concentration.**
insights.py:59 (`if n >= 20 and t["top5pct_share"] >= 0.40 and total > 0`).
The $1.00 materiality floor at line 30-32 guarantees `total >= 1.0`
before this line runs, so the third conjunct can never be false.
Harmless; delete or leave.

**L-A2. Tail dollars are 1-ulp off the true top-N sum.**
insights.py:65: dollars = `t["top5pct_share"] * total`, but pnl
computes `tail_share = sum(top) / total`, so the product is
`(sum/top)/total*total` — exact in real arithmetic, off by floating
point in IEEE (observed 41.00 vs 40.99999999999999-class values).
Formats correctly at `%.2f` and only matters for sort-order ties.
Consider `sum of top-N` directly if exactness is wanted.

**L-A3. Envelope boundary is strict `>` and undocumented.**
A run costing exactly the envelope is not a breach — consistent
between hook (tracker.py:366) and pnl (tracker.py:466), verified
(T3j), and defensible, but no comment or docstring states the
boundary. The audit already flagged the same for
`simulate_policy`; apply the same documentation here.

**L-A4. "1 accepted outcomes and 0 failed runs" when no failed breaches.**
insights.py:146 prints both counts unconditionally, so an
all-successful breach set reads "3 accepted outcomes and 0 failed
runs exceeded the envelope". Accurate but clunky; the `failed_bit`
is already conditional — the "0 failed runs" clause could be too.

## Notes for other reviewers (out of my scope, not findings)

- Retry reasons (user-controlled strings) flow through finding
  `detail`/`action` dicts into `report.py`'s HTML rendering. I did
  not review report.py's escaping of these specific strings; the
  reviewer owning report.py/findings 5-9 should confirm.
- No web access was used; no injected directives encountered.
  `insights.py` imports only `math` — no network surface.

## Test artifacts

Verification scripts (ephemeral, /tmp): `/tmp/verify_insights_a.py`
(45 checks), `/tmp/verify_insights_b.py` (20 checks). Both green.
