# Hostile review, pass 2 — `averth/importers/otel.py` (224 lines)

Reviewer posture: adversarial. Scope is ONLY the OTel span importer, reviewed
against the FIXED tree (AUDIT-2026-10-02.md Phase 1 applied). Every finding
below was verified by executing code (batteries:
`.review-pass2/battery-otel.py`, `.review-pass2/battery-otel2.py`), not by
reading. File:line refs are `averth/importers/otel.py` unless noted.

## Verdict

The assigned headline bug class is **half-fixed**. The I1 fix (`_parse_bool`
for `averth.success`, otel.py:101-113) holds under a 21-value probe matrix.
But the *same truthiness trap* the fix was written for is alive in the three
sibling gates on the same page: `averth.retry="false"` (the literal string)
creates a retry event, `averth.escalation_minutes="false"` fabricates a
human-escalation event, and `averth.branch=False` becomes the branch name
`"False"`. A global retry marks every following step as retry-path waste, so
an explicit "not a retry" marker silently voids an attempt's terminal spend —
wrong dollar figures from the exact bug class the audit declared fixed.

Secondary: garbage `averth.success`/`averth.business_value` values clobber
earlier explicit values (success flipped False→True, $5.00→$0.00), and
wrong-typed token attributes (`[1000000]`) are silently zeroed — $1.00 of
spend evaporates with no error.

**Counts: CRITICAL 0 · HIGH 4 · MEDIUM 6 · LOW 7.**

---

## What I verified as CORRECT (the assigned focus areas)

**I1 fix holds for `averth.success`.** Probed `_parse_bool` directly with 21
inputs: `"false"`, `"False"`, `"FALSE"`, `" false "`, `"0"`, `"no"`, `"N"`,
`"f"` → `False`; `"true"`, `"True"`, `"1"`, `"yes"`, `"y"`, `"Y"`, `"t"` →
`True`; `"maybe"`, `""`, `"2"`, `"00"`, `"off"`, `"on"` → `None`
(falls back to status-code logic). OTLP `{"boolValue": false}` → `False`;
`{"stringValue": "false"}` → `False`. End-to-end: a span with
`averth.success="false"` yields `success=False` in the ledger. The original
`bool("false") is True` bug is dead on this attribute.

**M2b span→event ordering holds.** On a dual model+retry span the model event
is emitted before the retry event (otel.py:171-199), and the Tracker's
global-retry forward-only semantics leave the span's own call terminal:
verified `terminal_model_cost=0.000250, retry_path_cost=0` — identical to
logging `log_model_call` then `log_retry()` via the Tracker API. The old
cross-path inconsistency (HOSTILE_REVIEW.md M2) is fixed. Branch-scoped dual
spans taint the span's own call via the retroactive branch rule
(`retry_path=0.000250`), which matches `Tracker.log_retry` documented
semantics exactly — consistent, not a bug (the docstring's wording is
confusing; see L5).

**Token extraction dialects work.** OTLP `intValue`-as-string (`"1500"`) →
1500 tokens; first-non-empty-wins across the five input / five output
dialects (gen_ai.prompt_tokens=200 beats llm.prompt_tokens=999 → 200);
negative counts clamped to 0 (`-50` → 0); explicit `0` honored (cost $0.00);
cache_read tokens flow through (`cached=900, savings=0.002430`).
End-to-end math on fallback pricing verified to the microcent
(1000 in/500 out → $0.002500 = 1000/1e6·1.00 + 500/1e6·3.00).

**Malformed numerics mostly fail loud.** `"1e999"` tokens → `ValueError:
input_tokens must be finite`; `10**13` → `ValueError: implausibly large`;
`"1e999"` business_value → `ValueError: business_value must be finite`.
`status.code` in `("ERROR", "STATUS_CODE_ERROR")` marks the case failed;
explicit `averth.success="true"` correctly overrides a status ERROR
(documented override precedence). Tool latency from span duration correct
(2.5 s → 2500.0 ms); negative duration (clock skew) omits latency rather
than recording negative. `tool.` name-prefix detection works. Empty span
list → empty ledger, no crash. `price_vintage` stamped on the ledger (C2
fix present).

---

## HIGH findings

### H1. `averth.retry="false"` (string) creates a retry event — the I1 bug class survives in the sibling gate
**otel.py:195** — `if _brand(attrs, "retry") not in (None, ""):`

`_parse_bool` was added for `averth.success` but the retry gate still uses
naive truthiness. Verified end-to-end: a span with `"averth.retry": "false"`
→ `retries=1`; `"False"` → 1; `"no"` → 1; bool `False` → 1; int `0` → 1
(reason recorded as `"false"`/`"False"`/`"no"`/`"False"`/`"0"`). A global
retry marks **every following step** as retry-path waste, so an explicit
"not a retry" marker silently moves real terminal spend into the waste
lens: two-span probe gave `terminal=0.002500, retry_path=0.002500`
(want: `retries=0, terminal=0.005000, retry_path=0`). The audit declared
this bug class fixed; it is fixed on exactly one of four attributes.
Fix: run the retry marker through `_parse_bool`-style tri-state logic —
only truthy markers (`"true"/"1"/"yes"`/non-empty reason strings?) create
the event; explicit falsy values must be ignored, not recorded as reason
`"False"`.

### H2. Unparseable `averth.success` clobbers an earlier explicit override (False → True)
**otel.py:153-154** —
```python
if _brand(attrs, "success") is not None:
    case["success_override"] = _parse_bool(_brand(attrs, "success"))
```
`_parse_bool("maybe")` → `None`, and the code writes `None` over whatever a
previous span set. Verified: span1 `averth.success="false"` + span2
`averth.success="maybe"` (ordered by start time) → ledger `success=True`.
Success drives the waste lens (a failed attempt's tokens are 100% waste), so
this silently reclassifies a failed attempt as successful and misstates
terminal vs waste dollars. Fix: only overwrite when `_parse_bool(...) is
not None`.

### H3. Garbage `averth.business_value` resets an explicit value to $0.00
**otel.py:151-152** — `case["business_value"] = _num(_brand(attrs,
"business_value"))`. `_num` swallows `ValueError` → default `0.0`, and the
assignment is unconditional. Verified: span1 `averth.business_value=5.0` +
span2 `averth.business_value="abc"` → ledger `business_value=0.0` (want
5.0). Silent corruption of a dollar field that feeds ROI math. Fix: ignore
the attribute when it does not parse (keep the earlier value), or fail
loud.

### H4. Wrong-typed token attributes are silently zeroed — spend evaporates
**otel.py:82-84** (`_num` swallowing `TypeError`):
```python
try: return float(value)
except (TypeError, ValueError): return default
```
Verified: `gen_ai.usage.input_tokens=[1000000]` (array where a scalar
belongs) → `total_tokens=50.0, model_cost=0.000150` — the 1,000,000 input
tokens ($1.00 at fallback prices) vanish without any error. Rubric item 5
is explicit: "NaN/inf/None/**type errors** must never become silent
corruption." Fix: raise a clear `ValueError` naming the span/attribute when
a token attribute is a non-scalar type, instead of defaulting to 0.

## MEDIUM findings

### M1. Falsy `averth.escalation_minutes` fabricates a human-escalation event
**otel.py:201** — same truthiness gate as H1. Verified:
`"averth.escalation_minutes": "false"` → ledger contains
`('escalation', '', 0.0)`; bool `False` → same. No dollar impact (0
minutes), but the exported ledger asserts a human escalation happened that
didn't. Same fix as H1.

### M2. Override-only cases are silently dropped — explicit failure signal lost
**otel.py:209-211** + `common.py` C6 rule. A case whose spans carry only
`averth.*` annotations (e.g. `averth.success="false"` on an outcome span,
no model/tool/retry/escalation events) produces **zero attempts**: the
importer always appends an `end` event, but `events_to_tracker` skips a
lone `end` as stray (the C6 phantom-attempt fix). Verified: `attempts=0`
for a case explicitly marked failed. The failure signal evaporates with no
warning. Fix: when a case has override attributes but no cost events, still
emit the attempt (zero-cost, with the recorded success/business_value), or
log a warning naming the dropped case.

### M3. The "unknown" trace bucket silently merges spans — docstring guarantee violated
**otel.py:140-142.** The module docstring promises: "spans missing trace_id
are grouped under their own span_id so nothing is silently merged." But the
fallback chain ends in the literal `"unknown"`, so spans missing **both**
trace_id and span_id merge into one case. Verified: two unrelated spans
with no IDs → 1 attempt, their costs summed. Docs-vs-code plus silent merge
— the exact thing the docstring says cannot happen. Fix: generate a unique
case id per span (e.g. `"unknown-<index>"`) when no id is present, or drop
the guarantee from the docstring.

### M4. Malformed spans abort the whole import with raw, unlocated errors
One bad span kills every good span in the file, and the error names no
span:
- **otel.py:210** `name.startswith` — `"name": null` →
  `AttributeError: 'NoneType' object has no attribute 'startswith'`
- **otel.py:147** `status.get` — `"status": "ERROR"` (string) →
  `AttributeError: 'str' object has no attribute 'get'`
- **otel.py:135** `data["spans"]` — dict without `"spans"` → bare
  `KeyError: 'spans'`
- non-dict item in the span list → `AttributeError: 'str' object has no
  attribute 'get'`
- **otel.py:84** — `float()` on a >1e308 int raises `OverflowError`, which
  `_num` does not catch (only `TypeError`/`ValueError`) → raw
  `OverflowError: int too large to convert to float` escapes.

Fail-loud in the crash sense, but this is the same "one malformed span
kills the entire import" shape as HOSTILE_REVIEW.md C5 (LangSmith). Fix:
wrap per-span processing to raise a single `ValueError` naming the file,
span index, and field — and decide explicitly whether one bad span should
abort the file or be skipped with a warning.

### M5. A span carrying both a model call and a tool call silently drops the tool event
**otel.py:206** — `if model: continue`. Verified: span with
`gen_ai.request.model` + `tool.name="web_search"` (and `name="tool.search"`)
→ ledger `tools=0.0`, events contain only the model event. The tool call,
its latency, and its (default) cost vanish with no warning, and the
precedence is undocumented (the docstring documents model-first ordering
only for the retry case). Fix: document the precedence, or emit both
events.

### M6. `averth.branch=False` becomes the literal branch name `"False"`
**otel.py:191-192, 198-199** — `ev["branch"] = str(_brand(attrs, "branch"))`.
Verified: `"averth.branch": False` → retry event
`('retry', 'False', 0.0, 'False')` — reason and branch both the string
`"False"`. Internally consistent (model and retry gates stringify the same
way, so they still match each other), but a bool `False` was clearly meant
as "no branch". Combined with H1 this is how a stray `retry=false` +
`branch=false` pair fabricates a branch-scoped retry. Same tri-state fix
as H1.

## LOW findings

- **L1.** Fractional tokens stored raw on the unpriced fallback path:
  `total_tokens=200.9` for 150.9 input tokens. Root cause is
  `common.py:_apply_model_cost` not int-normalizing like
  `Tracker.log_model_call` does (otel.py always emits floats via `_nonneg`);
  out of this file's scope — flagged for the common.py reviewer. Dollar
  impact is sub-microcent.
- **L2.** `_parse_bool` int/str inconsistency (otel.py:101-113): int `2` →
  `True` via `bool(2)`, but string `"2"` → `None`; `float("nan")` → `True`
  via `bool(nan)`. Edge-of-edge, but the two code paths disagree on what
  counts as true.
- **L3.** Escalation reason dict → `str()` repr in the ledger (otel.py:204):
  `{'a': 1}` stored as the reason string. Cosmetic.
- **L4.** The M2b docstring sentence (otel.py:155-165) is confusingly
  worded: "it does not retroactively taint the call on its own span (for
  branch-scoped retries the branch work is still caught by the retroactive
  branch rule)". Behavior verified correct per `Tracker.log_retry`
  semantics (p14/p15), but a reader will misparse the main clause.
- **L5.** OTel never reads a tool-cost attribute — every tool call is priced
  at the arbitrary `TOOL_PRICES` default (verified: `web_search` →
  `$0.005000`; audit H2 is pricing-scope, noting the otel surface here).
- **L6.** Duplicate model-attribute dialects where the first is `0`:
  `gen_ai.usage.input_tokens=0` + `llm.usage.prompt_tokens=999` → 0 wins
  ("first non-empty wins" per docstring; `0` is not empty). Documented
  behavior, verified — noting because a reader may expect "first nonzero".
- **L7 (checked, not a bug).** `averth.success="true"` beats
  `status.code=STATUS_CODE_ERROR` → `success=True`. Matches the documented
  "overrides set the end event fields explicitly" precedence.

## Checked and clean

Zero network imports (`json` + `.common` only); `json.load` of untrusted
input is safe (no eval/exec); no secrets; no HTML output in this module;
empty input → empty ledger; `{"spans": [...]}` and bare-list forms both
parse; OTLP attribute-list and flat-dict forms both parse; case grouping
preserves first-seen order; spans sort stably by start time; unpriced
models land in `unpriced_models` with fallback pricing applied correctly.

## Fix priority (my recommendation)

1. H1 (+M1, M6): one tri-state helper for all `averth.*` marker gates —
   explicit falsy (`"false"`, `False`, `0`, `"no"`) must mean "absent".
2. H2/H3: never let an unparseable override clobber a parsed one.
3. H4: reject non-scalar token attributes loudly instead of zeroing.
4. M2/M3/M4: decide the malformed-input contract (per-span error with
   location; no silent merges; no silent drops) and implement it once.
