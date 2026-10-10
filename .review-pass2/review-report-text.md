# Hostile review — averth/report.py `report_text()` (lines 1–130)
**Reviewer:** pass-2 hostile, report_text-only scope. `write_html` explicitly
out of scope (owned by another reviewer). Date: 2026-10-02.

Method: read `averth/report.py:1-130`, `averth/tracker.py` (pnl key
production, lines 106-126 / 525-545), `averth/pricing.py:price_vintage()`
(lines 105-121), `AUDIT-2026-10-02.md` (C2/C3/H2/H3), then ran a 14-case
verification script (`/tmp/verify_report_text.py`) building real Trackers
and hand-stripped legacy pnl dicts. Every finding below was executed, not
eyeballed.

## Verified correct (ran, hand-checked)

- **Vintage stamp matches `pricing.price_vintage()` exactly.** Fresh table
  renders `Price table: v1 (verified 2026-10-02, 1 days old)` (report.py:20).
  Backdating `PRICE_TABLE_UPDATED` 100 days renders
  `WARNING: pricing table is stale (>90 days) — vendor prices may have
  changed; verify before trusting dollar figures` (report.py:23-26).
  Threshold math is consistent: pricing uses strict `>`
  (`age_days > PRICE_TABLE_STALE_AFTER_DAYS`, pricing.py:119) and the
  message says `(>90 days)` — no off-by-one between them.
- **Labor-rate labeling works.** Default rate → `Human review: $5.85
  (at $70.20/hr loaded — ASSUMPTION, not measured;
  pass human_cost_per_min=... with your real rate)` (report.py:61-64).
  Explicit 0.5 → `$30.00/hr loaded, caller-supplied`, no ASSUMPTION
  (report.py:66-68). Explicit 0 → honored at `$0.00/hr caller-supplied`
  — the M3 `or`-bug fix holds through to the report.
- **Tool-estimate WARNING is exact.** Two default-priced calls render
  `WARNING: $0.01 of tool spend uses built-in per-call ESTIMATES (for:
  browser_action, web_search)`; spend verified $0.015 = 0.005 + 0.010
  (report.py:120-126). Explicit costs → warning correctly absent.
- **Cache line names the rate.** Default → `(priced at 10% of input rate;
  override per vendor via cache_read_discount=...)`; custom 0.25 →
  `priced at 25% of input rate` (report.py:96-103). Savings consistent
  with tracker math ($0.054 at 10% on 4000 cached tokens at $15/1M).
- **Legacy pnl (all six new keys stripped) → no KeyError, full render.**
  `price_vintage` missing → `Price table: vintage unknown (legacy ledger)`;
  `human_rate_assumed` missing → defaults to ASSUMED (conservative default
  at report.py:60, `p.get("human_rate_assumed", True)`); missing
  `cache_read_discount` → `10%` fallback; missing tool keys → warning
  correctly absent. Empty tracker (0 attempts) also renders without
  ZeroDivisionError.
- **Docs-vs-code:** inline comments at report.py:15-17, 53-55, 90-92,
  119-120, 136-138 all match actual behavior. The C3 prompt
  (`pass human_cost_per_min=... with your real rate`) is present in both
  branches' messages.

## HIGH

### H-R1. TOP FINDING still presents the assumption-driven headline dollar with no label
`averth/report.py:33-37`. The C3 fix labels the labor rate in the
"Cost per successful outcome" section, but the TOP FINDING block —
the first thing a VP Finance reads — passes `findings(p)` through
unmodified: `TOP FINDING [HIGH]: Human review is 96% of fully-loaded
cost ($5.85)`. That 96%/$5.85 is downstream of the $70.20/hr *default
assumption* (verified: 5 min × $1.17 = $5.85), and the audit's C3
explicitly named this exact line "the single most decision-relevant
number in the report is the least measured." The ASSUMPTION caveat
appears three lines later in the breakdown, but the headline number —
the one that drives the "behavior-changing insight" the module
docstring promises — carries no caveat. Fix: when
`p["human_rate_assumed"]` is true, append the assumption marker to the
finding line itself (or have `report_text` decorate human-review-driven
findings), so a skimming reader cannot take it as measured data.

## MEDIUM

### M-R1. Nested vintage keys are direct-indexed: partial `price_vintage` dict → KeyError
`averth/report.py:20-25`. The top-level `p.get("price_vintage")` is
graceful, but `vint["version"]`, `vint["updated"]`, `vint["age_days"]`,
`vint["stale"]`, and `vint["stale_after_days"]` are all direct indexes.
A pnl dict carrying a partial vintage (e.g. `stale=True` but missing
`stale_after_days`) crashes: verified `KeyError: 'stale_after_days'`
instead of the graceful fallback the surrounding code promises.
Unreachable from `tracker.pnl()` today (it always emits the full dict
from `pricing.price_vintage()`), but `report_text` accepts any pnl
dict and the nested keys should use the same `.get` posture as the
top level — e.g. `vint.get("stale_after_days")`.

### M-R2. None values for the new keys crash loudly instead of degrading
`averth/report.py:63-64, 98-103, 122`. `human_cost_per_min=None` →
`TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'`;
`tools_default_priced_spend=None` → `TypeError: '>' not supported`;
`cache_read_discount=None` → `TypeError` on `* 100`. All three are
`.get(key, default)` lookups whose defaults are defeated by an
explicit `None` — reachable in any pnl dict deserialized from JSON
with `null` values. Loud, not silent, so not critical — but a
one-line `or <default>` normalization would make the report robust.

### M-R3. Future-dated `PRICE_TABLE_UPDATED` permanently defeats the staleness guard
`averth/pricing.py:113-119` (feeds report.py:20-26). `age_days` can go
negative if the verification date is ever set ahead of the system
clock (fat-fingered bump, or clock skew on the metering host): the
report would print e.g. `-3 days old` and `stale` would be `False`
forever, so the warning the C2 fix added can never fire. The
staleness invariant deserves a floor: `age_days = max(0, ...)` or an
explicit sanity check that the table date is not in the future.

## LOW

- **L-R1.** `report.py:21`: `"1 days old"` — no singular/plural handling
  (`%d days old`). Cosmetic, but this line is the trust stamp on every
  report.
- **L-R2.** Indentation inconsistency between warnings: the stale warning
  (report.py:24) has no indent while the unpriced-spend (report.py:111)
  and tool-estimate (report.py:122) warnings are indented two spaces.
  All three are report-level, none are nested under the waste-accounting
  header they visually sit near.
- **L-R3.** Empty `price_vintage` dict `{}` renders `Price table: vintage
  unknown (legacy ledger)` (report.py:19 falsy check). Misleading label
  for a present-but-empty dict; harmless.
- **L-R4.** Hardcoded `0.10` fallback in `report.py:102`
  (`p.get("cache_read_discount", 0.10)`) duplicates
  `pricing.CACHE_READ_DISCOUNT`. Only reachable on legacy pnls, but the
  literal will silently diverge if the pricing constant ever changes —
  import the constant instead.
- **L-R5.** Hand-built pnl with `tools_default_priced_spend > 0` but
  missing/empty `tools_default_priced_names` renders `ESTIMATES (for: )`
  with an empty parenthetical.
- **L-R6.** Legacy pnl shows `(at $0.00/hr loaded — ASSUMPTION, not
  measured; ...)` — honest and loud, but `$0.00/hr` reads as a claim
  about the rate rather than "unknown." Acceptable as-is.

## Security (rubric item 6, text renderer)

- `report_text` builds plain strings; no HTML, no network, no eval.
  Model names, retry reasons, and agent names flow into `%`-format
  strings only — no injection surface in the text path. `json.load` of
  ledgers is not in this file's scope (importers reviewed separately).
  Clean.

## Notes for the coordinator

- `report_text` in production is only ever fed `tracker.pnl()`
  (`cli.py:76`, `demo.py:81`), so M-R1/M-R2/L-R5 are hand-built-pnl-only
  paths; H-R1 fires on every default-rate report and is the one that
  matters for the VP Finance reader.
- No CRITICAL findings. The C2/C3/H2/H3 Phase-1 fixes all verified
  working on real Tracker output; the residual gap is H-R1 (headline
  finding unlabeled) plus defensive-coding gaps around the new keys.
- Test script kept at `/tmp/verify_report_text.py` (ephemeral scratch);
  all assertions above were executed green except the four intentional
  crash probes (tests 10–12, 14), which produced the documented
  KeyError/TypeError.
