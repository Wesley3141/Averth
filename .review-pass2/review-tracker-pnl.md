# Hostile review — Tracker.pnl() (tracker.py:360-542)
**Reviewer:** pnl-lane reviewer · **Date:** 2026-10-02 · **Scope:** `averth/tracker.py`
lines 360–542 only (the `pnl()` aggregation). `end_attempt` and logging
methods explicitly out of scope (other reviewers). Code reviewed is the
Phase-1-fixed tree (C1–C3/H1–H4/M1–M3 per AUDIT-2026-10-02.md).

## Method
Built a 4-attempt Tracker by hand with independently precomputed figures
(success with retry + cached escalation + explicit/default tools; failed
attempt with cached tokens; failed runaway over budget with unpriced model;
reopened success) and asserted every `pnl()` key against the hand math.
Separately exercised: empty tracker, all-failed tracker, tool-only
(zero-token) attempt, tail-label boundaries n=1/19/20/21/40, exactly-at-cap
boundary, no-callback failed breach, `budget_per_success=0`, legacy attempt
dicts missing every new key, explicit `human_cost_per_min=0`, and
`price_vintage` object identity. Full suite: **150 passed**.

## Verdict
The aggregation math is correct — every figure hand-verified to the cent,
all identities hold, breach counting agrees with the hook, and the new
transparency keys report the right values. One HIGH (frozen price-vintage
stamp undermines the C2 staleness guarantee for long-lived trackers), two
MEDIUMs, four LOWs. No criticals.

## What verified clean (evidence)
- **Five-layer aggregation** — all sums match independent recomputation:
  `cost_model` 2.628, `cost_model_terminal` 0.315, `cost_retry_path` 2.363,
  `cost_tools` 0.022, `cost_retry` 0.05, `cost_retry_tools` 0.012,
  `cost_human` 5.0, `cost_total` 7.70, `cost_failed` 2.023.
- **Identity** `terminal + retry_path == model + retry` holds in aggregate
  (0.315 + 2.363 == 2.628 + 0.05), and `per_success` buckets are additive
  (terminal + retry_path + tools + human == fully_loaded per success).
- **Yield** 1 − 4.45M/6.55M ≈ 0.3206 ✓; **avg_context_growth** 1.5 ✓;
  **context_tax** $0.094 with cache-discounted effective pricing ✓.
- **Tail** — p50 = 1.0115, p95 = 4.9967 (linear interpolation, hand-checked),
  max = 5.612, n=4 → label `"costliest run"`, share = 5.612/7.70.
  Boundaries: n=19 → costliest run; n=20 → "top 5%" with tail_n=1 = exactly
  5%; n=40 → tail_n=2. n=1 → p50 == max (no crash).
- **Breach counting (C1)** — counts ALL over-envelope attempts: 2 breaches,
  `budget_breach_spend` 7.122, `budget_breaches_failed` 1. Hook condition
  and count condition are textually identical (`budget_per_success and
  total_cost > budget_per_success`, strict `>` both sides); failed
  over-budget attempt with no callback raises `BudgetBreach` containing
  "(failed attempt)", and the attempt is still in the ledger so the count
  includes it. Exactly-at-cap does not breach — consistent with the
  "exceeded" wording in the breach message.
- **New keys** — `price_vintage` carries version/updated/stale from
  `pricing.price_vintage()`; `human_cost_per_min` 0.5 with
  `human_rate_assumed=False` (explicit), default tracker reports
  `human_rate_assumed=True`; explicit `0` honored (M3 fix confirmed);
  `tools_default_priced_spend` 0.012 / names `["browser_action",
  "crm_lookup"]` (explicit-cost calls correctly excluded);
  `cache_read_discount` 0.10 passthrough.
- **Zero guards** — empty tracker: success_rate 0.0, all per_success 0.0,
  yield 1.0, growth 1.0, tail all 0.0, shares 0.0, no crash. All-failed
  tracker: per-buckets 0.0. Zero-token attempt: yield 1.0 (documented).
- **Legacy ledgers** — attempt dict missing `terminal_model_cost`,
  `retry_path_cost`, `retry_tool_cost`, `context_tax`, `cache_savings`,
  `cached_tokens`, `context_growth`, `reopened`, `events`, `tool_steps`
  does not crash; terminal falls back to `model` spend (documented
  degradation).
- **Retry reasons** — `[("timeout", 1)]` from events; empty-string reasons
  skipped. **per_model** sums exactly to `cost_model`; `unpriced_spend`
  1.50; **costliest_attempts** correctly ordered desc, top-10 cap fine.
- **Security** — no network, no new imports beyond function-local
  `collections.Counter` (stdlib); output is JSON-safe (inputs validated
  finite upstream; tuples in `top_retry_reasons` serialize as lists).

## Findings

### HIGH
**H-PNL1. `price_vintage` is frozen at `__init__`; long-lived trackers stamp
reports with a false freshness claim.**
`tracker.py:121`: `self.price_vintage = pricing.price_vintage()` —
`age_days`/`stale` computed once at construction. `tracker.py:523` returns
that same object from `pnl()` (verified: `t.pnl()["price_vintage"] is
t.price_vintage` → True). A tracker constructed today and used for a
month-long pilot stamps every report `stale: False` with `age_days: 0`
even after the table passes `PRICE_TABLE_STALE_AFTER_DAYS`. This directly
undermines the C2 fix's guarantee ("reports stamp the vintage so a reader
can tell whether the dollars assume this month's or last year's prices").
Fix: compute `pricing.price_vintage()` inside `pnl()` (or make it a
property); the stamp should reflect call time, not construction time.

### MEDIUM
**M-PNL1. `budget_per_success=0` silently disables the breach machinery.**
`tracker.py:460-462` (count) and the hook (~`tracker.py:363`) both gate on
`if self.budget_per_success` — falsy for 0. A $0 per-attempt budget (every
non-free attempt breaches) can never fire and is never counted. The
codebase already fixed this exact pattern for the sibling feature
(`policy.py:64` uses `is not None` after the `--policy-cap 0` bug); the
breach path was not given the same treatment. Edge-casey, but this is the
governance hook the pitch is built on — use `is not None`.

**M-PNL2. `tail["top5pct_share"]` holds costliest-run share when n < 20.**
`tracker.py:520-524`: the key name promises a top-5% share while the value
is the single costliest run's share for n<20. Mitigating facts: `tail_label`
sits adjacent and is honest, `report.py:82-83,416,444-445` always renders
the label with the share, and `insights.py:54` gates its 40% finding on
`n >= 20`. But any direct API consumer reading the dict will misread it.
Suggest renaming to `tail_share` (label disambiguates) or emitting both keys.

### LOW
**L-PNL1. Stale bug-reference comment.** `tracker.py:415`: "minimal
hand-built ledgers may lack the key (C7)" — there is no C7 in
AUDIT-2026-10-02.md (bugs are C1–C3/H1–H4/M1–M3); the string "C7" appears
nowhere else in the repo. Copy-paste slop; harmless but exactly the kind of
thing that erodes trust in comments.

**L-PNL2. `avg_context_growth` is an arithmetic mean of per-attempt ratios**
(`tracker.py:418-419`). Labeled "kept for continuity" — a documented
choice, but arithmetic mean of growth ratios overstates compounding vs the
geometric mean (4.0× and 1.0× average to 2.5×, not 2.0×). Fine for a
continuity metric; do not present it as the compounding rate.

**L-PNL3. `budget_breach_spend` is the FULL cost of over-budget attempts,
not the overage** (`tracker.py:464`). The name invites misreading ("breach
spend $7,122" sounds like excess spend; the excess here is $5,122). The
value is arguably the right reporting choice (total waste exposure), but
the label should say so — e.g. `budget_breach_attempt_spend` or a doc line.

**L-PNL4. Empty retry reasons are silently dropped** (`tracker.py:435`:
`ev[1]` falsy check). `log_retry()` with no reason still increments the
retry counter but contributes nothing to `top_retry_reasons`, so the
"operational lever" view undercounts precisely the least-instrumented
retries. Minor; consider counting them under `"(unspecified)"`.

## Non-findings (checked, clean)
- Strict `>` (not `>=`) on the breach boundary is consistent between hook
  and count and matches the "exceeded budget" message wording.
- Legacy tool steps without `explicit_cost` default to treated-as-explicit
  (`ts.get("explicit_cost", True)`, `tracker.py:470-476`) — documented
  tradeoff to avoid false warnings; direction is stated in the comment.
- `yield_ratio == 1.0` for zero-token (tool-only) attempts — noted in the
  audit as known behavior, not a bug.
- No thread-safety, no network, no `eval` — unchanged, out of scope.

## Injection note
Per rubric: no web content was consulted; no injected directives
encountered.
