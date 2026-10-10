# Hostile review — averth/pricing.py (review pass 2)
Reviewer: pricing-reviewer (subagent). File reviewed: `averth/pricing.py` (137 lines).
Audit context read: AUDIT-2026-10-02.md; rubric followed item by item.
Math was hand-verified with executed scripts (see "Verification log" below).
No prompt-injection attempts encountered during this review.

## Verdict
The versioning scheme is a convention, not a mechanism: bumping works only if
a human remembers, the date is validated lazily (not at import), a future
date defeats the staleness alarm silently, and one of the 12 model prices is
wrong at the table's own claimed verification date. Math is correct; the
failure modes are all staleness/validation, which is exactly the rubric's
priority-2 item.

Counts: CRITICAL 1 | HIGH 2 | MEDIUM 6 | LOW 4

---

## CRITICAL

### C1. Haiku-4-5 price is wrong on the table's own verification date
`averth/pricing.py:47` — `"anthropic:claude-haiku-4-5": (0.80, 4.00)`.

Three independent sources, including one verified 2026-10-02 (today), agree
Haiku 4.5 is $1.00 input / $5.00 output per 1M tokens:
- economize.cloud (source: Anthropic official pricing page, verified
  2026-10-02): input $1.00, cache $0.10, output $5.00
  (https://www.economize.cloud/resources/anthropic/pricing/haiku-4.5/)
- datacamp.com model-comparison table: "Claude Haiku 4.5 | $1 / $5"
  (https://www.datacamp.com/blog/claude-sonnet-5-5)
- observervoice.com: "Haiku 4.5 runs $1 per million input tokens and
  $5 per million output"
  (https://observervoice.com/claude-chatgpt-pricing-business-218271/)

The table underprices Haiku 4.5 input by 20% and output by 20%. Every cost
report metering Haiku 4.5 shows wrong dollar figures. This also falsifies the
module docstring's claim (`averth/pricing.py:20`) that the table was "last
verified against vendor list-price pages" as of 2026-10-02 — on that very
date this entry contradicts the vendor list price.

Verification for the other two spot-checks (same method, control cases):
- `anthropic:claude-sonnet-4-5` (3.00, 15.00) — MATCHES published rate
  ("Sonnet 4.5 costs $3 and $15", digitalmatters.me, updated 2 days ago).
- `xai:grok-4` (3.00, 15.00) — MATCHES upstream provider rate via Requesty
  catalog (https://www.requesty.ai/models/xai/grok-4).

Recommended fix: correct to (1.00, 5.00), add a regression test pinning it
(like tests/test_pricing.py pins the validation models), and treat every
price edit as requiring the docstring's own "regression test pinning the
changed price" — which the codebase currently does not enforce for 9 of 12
entries (see H2).

---

## HIGH

### H1. A future-dated PRICE_TABLE_UPDATED silently disables the staleness alarm
`averth/pricing.py:21` (constant), `:111-:124` (price_vintage).

```python
p.PRICE_TABLE_UPDATED = "2027-10-02"
p.price_vintage()   # -> {'version': 1, 'updated': '2027-10-02', 'age_days': -364, 'stale': False, ...}
p.staleness_warning()  # -> None
```

Observed behavior: a one-keystroke slip (e.g. `2026-12-02` typed on 2026-10-02)
yields `age_days = -61`, `stale = False`, no warning — and the alarm stays
silent until 90 days after the WRONG date, i.e. up to ~5 months late. Reports
stamp a nonsense negative age ("price table v1 is -364 days old") into every
ledger, CLI status screen, and HTML report. There is no validation at import
and no clamp in price_vintage(); the negative age is passed straight through
to users.

Recommended fix: at minimum `if updated > date.today(): raise ValueError(...)`
in price_vintage(), or validate once at import so a bad constant fails fast.
A test pinning `age_days >= 0` costs one line.

### H2. The version-bump scheme is convention-only; nothing ties table edits to the version
`averth/pricing.py:19` ("Bump on ANY price change") vs reality.

- No test fails if someone edits a price and forgets to bump
  PRICE_TABLE_VERSION or PRICE_TABLE_UPDATED. The docstring prescribes a
  process ("add a regression test pinning the changed price") that exists for
  exactly 3 of 12 model prices (tests/test_pricing.py pins the three
  validation models only). The other 9 entries — including all three OpenAI
  models, opus-4-6, sonnet-4-5, haiku-4-5, both Geminis, and grok-4 — can be
  silently edited with zero test failure.
- Result: two failure modes the scheme exists to prevent are both live.
  (a) Price changed, version not bumped → reports stamp the OLD version
  against NEW prices; the "vintage" is a lie and no check catches it.
  (b) Version bumped, date not moved → `staleness_warning()` sleeps 90 more
  days on a fresh version number.
- The staleness system treats the whole table as one unit, so it cannot detect
  a partial refresh either.

Recommended fix: extend test_pricing.py to pin ALL 12 (input, output) pairs —
then any price change without a corresponding test+version update breaks CI,
which is the only enforcement that actually works. Even better: a test that
parses PRICE_TABLE_UPDATED and asserts it is a valid, non-future ISO date.

---

## MEDIUM

### M1. Malformed PRICE_TABLE_UPDATED raises lazily, not at import
`averth/pricing.py:115` — `updated = date.fromisoformat(PRICE_TABLE_UPDATED)`.

Confirmed: setting `PRICE_TABLE_UPDATED = "not-a-date"` imports cleanly; the
`ValueError: Invalid isoformat string: 'not-a-date'` surfaces only when
price_vintage() is called. On the loudness question in the brief: it IS an
exception (loud, not silent corruption) on that path, and Tracker.__init__
calls price_vintage() (`averth/tracker.py:126`), so the main flow fails fast.
But pricing-only consumers (`model_call_cost`, `tool_call_cost`) never touch
the date, so a corrupt constant ships through those flows unnoticed. One
import-time validation would close this for every consumer at once.

### M2. The 90-day threshold is slower than observed price velocity
`averth/pricing.py:23` — `PRICE_TABLE_STALE_AFTER_DAYS = 90`.

Observed within the last ~2 months (search results above):
- xAI flagship: grok-4 $3/$15 → grok-4.6 $2/$6 (50% cut, ~2 months).
- Anthropic Sonnet 5.5 launched 2026-09-28 at $2/$10, 33% below Sonnet 4.5's
  $3/$15 — one month before this table's verification date.

A 90-day window can straddle a 50% vendor price cut without firing the alarm.
For a metering library whose output is dollar figures, the "how stale is too
stale" number should be justified against how fast vendor prices actually move;
as written it is an unexamined round number. Additionally, the single global
vintage means refreshing one entry resets the staleness clock for all twelve.

### M3. PRICE_TABLE_SOURCE names vendors but gives no URLs
`averth/pricing.py:25-27`. The docstring promises the source is recorded "so
a reviewer can re-verify them" — but lists four vendor names, not four
list-price URLs (which drift: Anthropic alone has claude.com/pricing,
docs.anthropic.com, AWS Bedrock pages, etc.). A reviewer re-verifying the
table today has to go hunt. Cheap fix, real payoff for the stated purpose.

### M4. tool_call_cost() silently conflates "unknown tool" with "default"
`averth/pricing.py:128-129` — `TOOL_PRICES.get(name, TOOL_PRICES["default"])`.

The pure function returns 0.002 for ANY unknown name with no signal that the
fallback fired: `tool_call_cost("web_serach")` → 0.002 instead of web_search's
0.005 (a 60% underprice on a typo). End-to-end the damage is contained —
Tracker.log_tool_call marks explicit_cost=False and pnl()/reports surface
`tools_default_priced_spend` loudly (verified: tracker.py:229-241, 538-539;
report.py:124-129, 228-233) — but the function itself gives callers no way to
distinguish a hit from a miss without re-checking the table. A sentinel return
or a `used_default` flag would keep the H2 discipline inside the function, not
just in its heaviest consumer.

### M5. The (1.00, 3.00) model fallback is a single point far from the high tail
`averth/pricing.py:80` — `ESTIMATED_MODEL_PRICES = (1.00, 3.00)`.

The table spans (0.05, 0.40) at nano to (15.00, 75.00) at Opus-4-6. The flat
fallback underprices an unknown Opus-class model by ~25x on output. It is
flagged downstream (unpriced_models, verified in tracker.py:195-227 and
report.py:121, 224), so it is not silent — but the fallback will most often be
reached for NEW expensive models (flagships), exactly the cases where a single
mid-table point is the worst choice. A documented rationale for the point (or
a wider pair of bounds) would make the "estimate" claim honest about its
expected error.

### M6. CACHE_READ_DISCOUNT 0.10x is wrong for OpenAI models by 25%
`averth/pricing.py:71-77`. The comment correctly documents Anthropic's 0.10x
and discloses that "other vendors differ," and Tracker accepts an override
(verified tracker.py:106, 121-122). But OpenAI publishes 0.125x (GPT-5-Codex:
$1.25 in / $0.125 cache-read per the migration_cost.py gist, verified
2026-05-14), so the universal 0.10 systematically overstates OpenAI cache
savings by 25%. The disclosure is honest and the saving is labeled as an
assumption — so this stays MEDIUM — but a per-provider discount table would
remove a known-quantified error.

---

## LOW

### L1. estimated_model_cost docstring hardcodes the constant's value
`averth/pricing.py:136-138` — "Uses ESTIMATED_MODEL_PRICES (1.00/3.00 per 1M
tokens)." If the constant changes, the docstring lies. Cite the name, not the
numbers.

### L2. price_vintage() uses naive date.today()
`averth/pricing.py:116`. Age flips at server-local midnight; deployments in a
different tz than the person who set PRICE_TABLE_UPDATED can be off by a day
at the boundary. No test pins age (only version), so nothing is flaky today —
but the boundary test at exactly 90 days (`stale` False at day 90, True at
day 91, verified by execution) is tz-sensitive.

### L3. No model-retirement awareness
Sonnet 4.5's deprecation was announced 2026-09-30 with retirement 2026-11-30
(digitalmatters.me). The table will keep pricing it after death, and
KeyError-fallback will route any 2026-12 replacement model (Sonnet 5.5,
$2/$10) through the (1.00, 3.00) estimate — a 2x underprice on the CURRENT
default model. The vintage mechanism is the only backstop; nothing flags "this
model no longer exists." (Out of scope for this file's contract, but the
versioning scheme claims to keep dollars honest across price eras.)

### L4. Three sonnet-version aliases pinned to identical prices
`averth/pricing.py:43-45` — sonnet-4-20250514, claude-3-7-sonnet-20250219,
claude-3-5-sonnet-20241022 all (3.00, 15.00). Correct per Anthropic's ladder
today, but it is three maintenance obligations that move together; fine as-is,
noted only so a future editor doesn't update one and miss the others.

---

## Explicitly checked, no finding

- **Math**: model_call_cost (22.50 for 1M/2M gpt-5.6; 0.80 for 0.5M/0.1M
  haiku-4-5), estimated_model_cost (4.00 for 1M/1M), tool_call_cost defaults
  (0.005 web_search; 0.002 unknown) — all correct to the cent, verified by
  execution.
- **Edge cases run**: zero tokens → 0.0; unknown tool / empty-string tool name
  → 0.002 default; None provider/model → loud KeyError
  ("no price for None:None; add it to MODEL_PRICES"); negative tokens → -0.0025
  (caller-validation is Tracker's job, out of scope).
- **Docs-vs-code**: "Reports stamp the vintage" ✓ (report.py:19, 237 use
  price_vintage); "`averth pricing` shows the current status" ✓ (cli.py:113-114
  calls price_vintage + staleness_warning); cache-override claim ✓
  (tracker.py:106, 121-122); "meter tracks which tool calls used defaults" ✓
  (tracker.py:229-241, 538-539; report.py:124-129). No docstring in this file
  contradicts its own code.
- **Security**: zero network imports in this module; staleness_warning()
  interpolates only internal constants (no injection surface); no secrets;
  KeyError message interpolates caller-supplied provider/model but is raised,
  not rendered into HTML.
- **AI slop**: none found — comments are substantive (H2 warning is genuinely
  useful), no TODOs, no dead branches.

---

## Verification log

Executed scripts against `averth/pricing.py` (Python 3.12), today 2026-10-02:
1. Math: gpt-5.6 1M/2M = 22.50 (expected 22.50); haiku-4-5 0.5M/0.1M = 0.80
   (expected 0.80); estimate 1M/1M = 4.00; tool web_search 0.005, unknown 0.002.
2. KeyError path: `model_call_cost("openai","nonexistent-model",100,100)` →
   KeyError 'no price for openai:nonexistent-model; add it to MODEL_PRICES'.
3. price_vintage() normal: version 1, updated 2026-10-02, age_days 1, stale
   False; staleness_warning() → None.
4. Malformed date: import succeeds; price_vintage() raises
   ValueError "Invalid isoformat string: 'not-a-date'".
5. Future date "2027-10-02": age_days -364, stale False, warning None.
6. Boundary: 90-day-old table → stale False, warning None; 91-day-old → stale
   True.
7. Zero tokens → 0.0; tool_call_cost("") and tool_call_cost(None) → 0.002;
   negative tokens → -0.0025; fromisoformat accepts "20261002" (basic format)
   and rejects "2026-10-2" / trailing space.

Spot-price verification: browser.search results above (3 entries checked,
1 wrong, 2 matching).
