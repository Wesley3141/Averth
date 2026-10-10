# Hostile docs review — HOSTILE_REVIEW.md + AUDIT-2026-10-02.md (2026-10-02)

Reviewer posture: adversarial. Assignment: verify every previously-found bug in
HOSTILE_REVIEW.md (308 lines) is STILL fixed in the current (Phase-1-edited,
uncommitted) tree, and that AUDIT-2026-10-02.md's "What the audit did NOT find"
section plus its checklist PASS items still hold after the Phase-1 edits.
P1 (policy-cap-0) and I1 (OTel string-"false") were re-verified by RUNNING
them. Rubric item 7 (docs-vs-code) applied ruthlessly throughout.

Baseline: HEAD `871c107`; Phase 1 edits present as uncommitted working-tree
changes across README.md, averth/{cli,insights,policy,pricing,report,tracker}.py,
averth/importers/common.py, sample-output.txt. Test suite: **150 passed**
(audit recorded 130; +20 from new tests/test_review_round3.py), zero
skip/xfail. All repros below were run, not eyeballed.

---

## Verdict

No CRITICAL regressions. Two HIGH findings survive:

1. **The audit's checklist claim "token counts capped at 1e12" is FALSE for
   huge ints** — `math.isfinite(10**400)` raises `OverflowError` inside
   `_check_finite` before the `_MAX_TOKENS` check ever runs, so the raw
   `OverflowError` escapes the live Tracker API instead of the documented
   `ValueError`. inf/nan are fine; the 1e12 rule works only for values
   small enough to fit in a float.
2. **HOSTILE_REVIEW H2's zero-base guard was never built** — round 2 fixed
   only the cache-discount half ("context tax cache-discounted (H2)" in
   c718dac's message). A zero-token first step — exactly what the OpenAI
   wrapper logs for streaming calls with no usage — still makes
   `context_tax` equal 100% of subsequent input-token spend, while the
   guarded `context_growth` ratio simultaneously reports 1.0.

Everything else claimed fixed checks out (see §4).

---

## HIGH findings

### H-1. Huge token counts escape the documented numeric contract as `OverflowError` (audit checklist item 2 contradicted)

`averth/tracker.py:53-76`:

```python
def _check_finite(name, value):
    ...
    if not math.isfinite(value):      # line 59 — OverflowError on huge ints
        raise ValueError(...)

def _check_nonneg_int(name, value):
    _check_finite(name, value)          # line 71 — blows up before the cap
    ...
    if value > _MAX_TOKENS:            # line 74 — never reached for 10**400
        raise ValueError("%s implausibly large: %r" % (name, value))
```

Verified by running:

```
log_model_call("openai", "gpt-5.6-mini", 10**400, 10)
  -> OverflowError: int too large to convert to float   (WRONG EXCEPTION)
log_model_call(..., float("inf"), ...) -> ValueError    (good)
log_model_call(..., float("nan"), ...) -> ValueError    (good)
```

The module docstring (`tracker.py:30-33`) states the numeric contract:
"every numeric input must be finite (NaN/inf rejected with ValueError) and
token counts are capped at 1e12." A caller catching the documented
`ValueError` crashes on the malformed-provider-counter case the cap was
written for — the identical failure shape the round-2 fix eliminated for
inf/nan (`math.isfinite` works on floats, but on a Python int larger than
~1.8e308 it raises before returning False). This directly contradicts the
audit's checklist item 2 ("NaN/inf rejected loudly; token counts capped at
1e12; no silent poisoning") and the audit's ranked-list claim that all of
HOSTILE_REVIEW C1–C4 was fixed. It fails loud, not silent — hence HIGH, not
CRITICAL — but it is a wrong-exception escape from the live API on the exact
adversarial input the fix was named for. The fix is trivial: move the
`> _MAX_TOKENS` check before `math.isfinite`, or special-case ints.

Docs-vs-code coda (same file): the docstring says counts are "capped" at
1e12; the code REJECTS them (ValueError). "Capped" vs "rejected" is loose
wording on its own, but combined with the above, the contract paragraph is
inaccurate in two ways.

### H-2. `context_tax` still has no zero-base guard (HOSTILE_REVIEW H2, half-unfixed)

HOSTILE_REVIEW §4 H2 said: "`context_tax` ignores the cache discount, and has
no zero-base guard. … `base_in = steps[0]["in"]` with no guard: a zero-token
first step — exactly what the OpenAI wrapper logs for streaming calls with no
usage — makes `context_tax` equal 100% of input-token spend."

Round 2's commit message claims "(H2)" via "context tax cache-discounted" —
only the FIRST half was fixed (the code now prices at the cache-discounted
effective input rate, `tracker.py:324-327`, verified). The zero-base guard
was never built. Verified by running:

```
t.log_model_call("openai", "gpt-5.6-mini", 0, 10)      # zero-token first step
t.log_model_call("openai", "gpt-5.6-mini", 1000, 10)
t.end_attempt(success=True)
  -> context_growth: 1.0        (guarded — reports "no compounding")
  -> context_tax:    $0.0003    (= 1000/1e6 × $0.30, i.e. 100% of the second
                                 step's input spend, booked as "tax")
```

The ratio lens says "no compounding" while the dollar lens — the one a VP
Finance reads — books the entire step's input cost as compounding waste.
The two lenses contradict each other on the exact streaming-with-no-usage
shape the OpenAI wrapper produces. A `base_in == 0` guard (skip the tax, or
fall back to a later non-zero base) is the missing half of the documented fix.

---

## MEDIUM findings

### M-1. The $1.00 materiality floor silently suppresses ALL findings (`insights.py:28`)

```python
if not math.isfinite(total) or total < 1.0:
    return out   # zero findings, however pathological the shares
```

Verified: a $0.00002 ledger and an n=1 ledger now emit zero findings (the
hostile-review hair-trigger case is fixed). But the floor is $1.00 of TOTAL
spend — a $0.50 evaluation run or a small pilot reports "No material
findings: spend is clean across all five layers," which reads as a clean
bill of health, not "below the noise floor." The floor exists only as a code
comment; the "spend is clean" copy does not mention it. A one-line honesty
fix: change the clean verdict to "spend below the $1 materiality floor" when
`0 < total < 1.0`. (Judgment call acknowledged; the current wording
overclaims.)

---

## LOW findings

### L-1. "1 days old" pluralization in the price-vintage line
`report_text` renders `"Price table: v2 (verified 2026-10-02, 1 days old)"`
(`report.py:20-23`) — cosmetic, but this is the headline line of every
report a prospect reads. (Also note: age is computed from the system clock;
"1 days old" on the day it was written suggests the box is a day ahead of
CDT — harmless, but a sharp reader comparing the verified date to the age
will notice.)

### L-2. Untracked `simulate.html` in the repo root
Present since before this review (`git status` shows `?? simulate.html`);
it is a generated CLI artifact, not source. Should be gitignored or removed
so a stray artifact never ships in a source tarball.

---

## §4. Verified still fixed / still holding (ran, not read)

### HOSTILE_REVIEW.md items
- **P1 (policy-cap-0)** — FIXED, still holds. Library: `simulate_policy(ledger,
  max_cost_per_attempt=0)` stops 2/2 runs, reports collateral honestly;
  `cap=None` still means no cap. End-to-end via CLI (`trace --format jsonl
  --policy-cap 0`): "Would have stopped 1 of 1 runs … cost $0.90 > cap $0.00."
  `policy.py:69` uses `is not None`.
- **I1 (OTel string-"false")** — FIXED, still holds. `load_otel` on a span with
  `averth.success: "false"` (string) imports as `success: False`.
  `_parse_bool` (`otel.py:101-113`) is actually wired in at `otel.py:154,218`.
- **M1 (dead-branch retroactive waste)** — FIXED, still holds. Branch-scoped
  `log_retry(branch="dead")` now marks the dead branch's past model AND tool
  steps as retry-path: per_success model=$0.00042, retry_path=$0.00042,
  fully_loaded=$0.00084 — the dead branch's call is fully in retry_path.
  Tracker module docstring documents the semantics.
- **M2b (OTel dual-attribute span ordering)** — FIXED, still holds. Span with
  both model attrs and `averth.retry`: model event emitted first, retry after;
  the span's own call stays terminal (`terminal_model_cost > 0`,
  `retry_path_cost == 0`).
- **C1 (inf/nan tokens)** — rejected with `ValueError` (see H-1 for the
  huge-int hole). **C2** — NaN rejected with `ValueError` on all four paths
  (`log_tool_call`, `log_escalation`, `log_retry`, `log_model_cost_estimate`)
  plus `end_attempt(business_value=nan)`; `export_ledger` writes with
  `allow_nan=False` (belt-and-suspenders); exported JSON verified free of
  NaN/Infinity literals. **C3** — inf costs rejected. **C4** — JSONL importer
  rejects `1e400`/NaN numerics with a line-numbered `ValueError`. **C5** —
  LangSmith clamps tokens via `max(0.0, …)` (`langsmith.py:79,141`). **C6** —
  duplicate `end` events produce no phantom attempt. **C7** — `pnl()` uses
  `.get("context_growth", 1.0)` / `.get("tool_steps", [])` throughout.
  **C8** — `business_value="abc"` rejected at `end_attempt`. **C10** —
  `integrations/openai.py:28-33` `_int_or_zero` catches `OverflowError`.
- **H1** — `low_yield` dollars now exact: `cost_model − cost_model_terminal`
  (`insights.py:190`), not the ratio approximation. **H4** — "lenses, not
  additive" disclaimer now in `findings_text` (`insights.py:254-257`) and the
  HTML cards (`report.py:269`). **H5** — export preserves `events`
  (`policy.py` export list, `common.py` ledger keys); export→reimport round
  trip verified: `top_retry_reasons` survives ("judge rejected draft", 1).
  **H7** — reopened finding counts successful-only via `reopened_successful`
  (`insights.py:171-172`); detail text now reads "accepted outcomes."
  **H8 / §6 hair triggers** — `findings()` returns nothing for
  `total < $1.00`; tail rule gated to `n >= 20` with honest "costliest run"
  labeling below that (`tracker.py:442-449`); n=1 and $0.00002 ledgers
  verified to emit zero findings. **§6 blind spots** — `tool_dominance` and
  `budget_breach` finding rules now exist (`insights.py:115-147`).
- **M3 (retry-path tool lens)** — verified via `retry_tool_cost` plumbing and
  the M1 test above. M2/M4/M5 (global-retry smearing) remain documented
  limitations per round-2's "4 documented limitations" — consistent with the
  docstring; no claim of fix was made, so no regression.

### AUDIT-2026-10-02.md items
- **Checklist 1 (tests)** — 150 passed, zero skips/xfairs; no
  TODO/FIXME/placeholder in `averth/` or `demo.py` (re-grepped).
- **Checklist 2 (core math)** — identity `terminal + retry_path ==
  model + retry_cost` verified numerically to 1e-9; percentiles still
  linear-interpolation (`tracker.py:86-101`); context-tax hand figures sane
  on normal inputs. (H-1 is the exception.)
- **Checklist 3 (five layers)** — all computed: context growth+tax, tool
  spend with explicit/estimate split, yield, interpolated p50/p95/max +
  honest tail labels, per-model attribution + labor.
- **Checklist 4 (demo)** — fresh `demo.py` run is **byte-identical** to
  `sample-output.txt`; dashboard $0.20 vs fully-loaded $0.82 (4.1x) per the
  audit; 61% tail claim untouched. README.md:42's `$0.03` is now explicitly
  labeled "an illustrative placeholder … (Current demo.py output: dashboard
  $0.20 vs fully-loaded $0.82)" — H4's external-circulation concern addressed
  in-repo.
- **Checklist 5 (policy sim)** — saved-vs-collateral split logic untouched
  by Phase 1 (diff was 3 lines: export keys + `allow_nan=False`); P1 re-verified
  above, including the CLI surface.
- **Checklist 7 (deps)** — `pyproject.toml`: `dependencies = []`; langchain/
  openai remain optional extras, lazily imported. CLI entry works;
  new `averth pricing` command verified working (v2, 2026-10-02, 12 models,
  8 tools, "fresh (warns after 90 days)").
- **Checklist 9 (dead code)** — none; audit's P1/I1 re-verification confirmed
  again today.
- **Checklist 10 (security)** — re-grepped: zero network imports
  (`requests`/`urllib`/`socket`/`http`), zero `eval`/`exec`/`subprocess`/
  `os.system`; new report banners escape user-controlled strings via
  `_html.escape`; ledger export docstring now honestly notes free-text fields
  (case_id, tool names, reasons) are caller-provided and may carry customer
  data — an improvement over the audit's flat "metadata-only" phrasing.
- **Audit C1** — hook now fires on failed over-envelope attempts: callback
  receives `"(failed attempt)"` suffix; no-callback raises `BudgetBreach`;
  `pnl()` counts agree (`budget_breaches`, `budget_breaches_failed`,
  `budget_breach_spend`); insights `budget_breach` rule consumes the new
  counts. **C2** — dated/versioned table (`PRICE_TABLE_VERSION=2`,
  `PRICE_TABLE_UPDATED=2026-10-02`, 90-day staleness alarm), `price_vintage()`
  / `staleness_warning()` API, vintage stamped on `report_text`, HTML, and
  exported ledgers (round-trips through `tracker_from_ledger` so old reports
  stamp the old vintage). **C3** — "ASSUMPTION, not measured" labeling in
  `report_text`, the human_dominance finding, and the HTML report; explicit
  `human_cost_per_min=0.0` honored (M3 fixed: `is None` check, not `or`).
  **H1** — importer EVENT docstring corrected to past-only semantics.
  **H2** — built-in tool-estimate spend flagged in reports + HTML with dollar
  amounts and tool names. **H3** — cache-discount rate named in the cache line
  ("priced at 10% of input rate; override per vendor"). **M1** —
  `FALLBACK_PRICE` deduped to `pricing.ESTIMATED_MODEL_PRICES`. **M2** —
  `guess_provider` carries an explicit heuristic warning in its docstring.
- **"What the audit did NOT find"** — still holds: meter math verified
  independently; demo not rigged (seeded, byte-identical); policy sim not
  theater (collateral accounting intact); no TODOs (re-grep clean); zero
  network imports (re-grep clean); no active-enforcement claims
  (TERMS.md/README untouched by Phase 1).

### Out of scope / not re-verified
- MCP live probe (`mcp.getaverth.com`) — separate Vercel deploy, untouched by
  Phase 1; not probed (no live-browser surface in this review).
- The 46-trace validation corpus — VALIDATION.md and trace dirs untouched by
  Phase 1; not re-run.
- `simulate.html` diff was not reviewed (untracked artifact, see L-2).

---

## Injection note
Per rubric: no injected developer-style messages encountered during this
review. No web fetches were needed; nothing was read or computed beyond the
assignment.

## Severity counts
- CRITICAL: 0
- HIGH: 2 (H-1: OverflowError escapes the 1e12 token cap — audit checklist
  claim false; H-2: context_tax zero-base guard never built — half of
  HOSTILE_REVIEW H2 remains)
- MEDIUM: 1 (M-1: $1.00 materiality floor overclaims "spend is clean")
- LOW: 2 (L-1: "1 days old" pluralization; L-2: untracked simulate.html)
