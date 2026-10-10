# Review: averth/importers/common.py lines 1–140 (+ events_to_tracker body) — 2026-10-02

Reviewer scope: EVENT schema docstring (incl. H1 branch-retry fix), FALLBACK_PRICE (M1),
guess_provider (M2), _apply_model_cost, _log_model_call, events_to_tracker grouping/auto-start/auto-end.
Ledger functions below the importer body (another reviewer's) excluded. All claims below were
verified by running code in ~/workspace/averth/.venv, not by reading docs.

## Verdict
The H1/M1/M2 fixes are real and hold under test. events_to_tracker is solid on its
headline cases (duplicate ends, stray ends, post-end restarts, missing ends, empty input).
Two HIGH docs-vs-code findings remain, both fixable by changing words or one line of math.

Severity counts: CRITICAL 0 | HIGH 2 | MEDIUM 1 | LOW 3

---

## HIGH

### H-A. Schema docstring promises cache-discount pricing on the fallback path; the fallback path prices cached tokens at full rate and reports zero saving
`averth/importers/common.py:22` (EVENT schema, "model" event) claims:

    "cached_input_tokens" are priced at the Tracker's cache_read_discount
    and the saving is reported.

`_log_model_call` (`common.py:115`) catches the KeyError for unpriced models and
`_apply_model_cost` (`common.py:95`) computes

    cost = input_tokens/1e6 * FALLBACK_PRICE[0] + output_tokens/1e6 * FALLBACK_PRICE[1]

with NO discount on the cached portion and NO addition to `cache_savings`
(`cache_savings` stays 0.0). Verified live: an unpriced model with
input_tokens=10000, cached_input_tokens=10000, output_tokens=1000 costs
$0.013000 (= 10000/1e6*1.00 + 1000/1e6*3.00, full rate on the cached 10k)
with cache_savings 0.0. The priced path (`tracker.log_model_call`) would have
priced the 10k cached at 10% ($0.001) and recorded $0.009 of saving.

This is a docs-vs-code contradiction inside the reviewer's own assigned range,
and it also silently overstates fallback-path dollars on cached-heavy traces
relative to the documented behavior. Fix: either apply the discount math on the
fallback path (and record cache_savings), or scope the docstring claim to
"models present in pricing.MODEL_PRICES".

### H-B. "start" is documented as a no-op marker; a lone "start" fabricates a failed attempt
`averth/importers/common.py:10-12` (schema docstring):

    Optional explicit attempt boundary. events_to_tracker() auto-starts
    an attempt on the first event seen for a case, so "start" is a no-op
    marker kept for readability.

The code auto-starts on ANY non-"end" event (`common.py:160-163`), including
"start". Verified live:

- `[{"type":"start","case_id":"c"}]` → **1 attempt, success=False** (docs imply 0).
- `[... end ...]` followed by `{"type":"start","case_id":"c"}` with nothing after →
  **2 attempts, [True, False]** — the trailing start opens a phantom attempt that
  is auto-ended as failed.

Zero-cost (no dollar corruption), but it pollutes attempt counts and success
rates shown to users — and it directly contradicts the C6 comment two dozen
lines down, which exists precisely to avoid "fabricating a phantom zero-cost
attempt" (`common.py:156-159`). A hand-written JSONL trace with a case header
line and no other events for that case (realistic; jsonl.py accepts "start"
events per its _SPECS table) silently inflates the failure count. Fix: either
make "start" a genuine no-op (skip it when it would only create an empty
attempt), or correct the docstring ("a start with no other events for the
case produces a zero-cost failed attempt").

---

## MEDIUM

### M-A. guess_provider's "o1"/"o3" substring matches are more collision-prone than the docstring admits
The M2 docstring is honest about the heuristic class ("name-guessing, not
identification"; "gpt-custom" example; "ALWAYS pass an explicit provider";
"unknown" returns are flagged in unpriced_models — all verified true:
`guess_provider("MODEL-X")` → "unknown" → key "unknown:mystery-9k" in
unpriced_models at fallback price). But the `"o1" in name or "o3" in name`
checks (`common.py:88`) match far beyond OpenAI reasoning models:

- `guess_provider("video10-transcoder")` → "openai" (contains "o1")
- `guess_provider("nano3-turbo")` → "openai" (contains "o3")

A video-transcoding model with a price-list collision against OpenAI list prices
is a more surprising misattribution than the documented "gpt" case, and unlike
the docstring's "gpt-custom via a gateway" framing it needs no adversarial
setup — an ordinary descriptive name triggers it. The docstring's honest
warning covers the category but its only concrete example ("gpt") understates
the trigger surface. Recommend naming the o1/o3 substring behavior in the
warning (or anchoring the check to word boundaries).

---

## LOW

### L-A. _apply_model_cost duplicates log_model_cost_estimate instead of reusing it
`_apply_model_cost` (`common.py:95-110`) hand-replicates
`Tracker.log_model_cost_estimate` bookkeeping (validated-input path) with two
divergences, both benign today:
1. It does not clamp `cached_tokens > input_tokens`. `log_model_call` clamps
   before raising the KeyError, but `_log_model_call` passes the ORIGINAL
   value through, so a malformed trace with cached > input records phantom
   cached tokens on the fallback path while the estimate path clamps.
2. It records event label `("model", ...)` while `log_model_cost_estimate`
   records `("model_estimate", ...)`. Nothing in-repo branches on the label
   (only `ev[0] == "retry"` is consumed, at `tracker.py:444`), so this is
   cosmetic — but a future consumer of the events list cannot distinguish
   estimated from priced calls except via the unpriced_models list.

The duplication also skips `_check_nonneg_int`/`_check_nonneg` validation,
though the values were already validated by `log_model_call` before it raised
KeyError (except the cached clamp, per (1)). Calling
`tracker.log_model_cost_estimate(...)` from the except branch would delete this
function and remove the drift surface.

### L-B. latency_ms is accumulated without validation for direct events_to_tracker callers
`common.py:178-181`: `cur["tool_latency_ms"] += ev["latency_ms"]` after only an
`is not None` check. A string raises a cryptic TypeError; NaN passes through
into the ledger (the audit's JSON-NaN concern). The supported path (jsonl.py)
validates finiteness and nonnegativity at parse time, so this only bites
programmatic users of the public `events_to_tracker` API. Metadata only, no
dollar impact.

### L-C. The hasattr(unpriced_models) guard is unreachable defense
`common.py:142-143`: `Tracker.__init__` (`tracker.py:129`) unconditionally sets
`self.unpriced_models = set()`, and `events_to_tracker` constructs the Tracker
itself, so the hasattr branch can never fire. Harmless; reads as copy-paste
caution. Consider deleting.

---

## Verified-correct (no findings)

- **H1 fix holds exactly.** The schema docstring's branch-retry paragraph now
  says past steps retroactively marked, post-retry work "starts fresh — NOT
  pre-tainted". `Tracker.log_retry` (`tracker.py:252-293`) says the same
  ("declares that branch's work SO FAR ... discarded ... Work logged on the
  branch after this point is the redo and starts fresh — it is not
  pre-tainted"). Live run through events: branch "b" model → retry(branch="b")
  → model(branch="b") produced retry flags `[True, False]` — past-only, future
  clean. Global (branch-less) retry docstring also matches Tracker's
  forward-only documented behavior.
- **M1 fix holds.** `FALLBACK_PRICE is pricing.ESTIMATED_MODEL_PRICES` verified
  by identity (tuple alias, single source of truth). Comment at
  `common.py:73-76` is accurate.
- **M2 warning is honest.** `guess_provider` docstring: "name-guessing, not
  identification", explicit-provider guidance, "unknown" → fallback estimate +
  unpriced_models flag. Verified: unknown-provider model flagged as
  `"unknown:mystery-9k"` in `tracker.unpriced_models` and costed at exactly
  FALLBACK_PRICE rates ($0.013000 for the test case).
- **events_to_tracker edge cases** (all run and hand-checked):
  - duplicate "end": 1 attempt, no phantom (C6 fix works);
  - stray "end" with no open attempt: ignored, 0 attempts;
  - events after "end": new attempt for the same case (2 attempts, [True, False]);
  - missing "end": auto-ended success=False;
  - empty event list: 0 attempts, no crash;
  - grouping by case_id in first-seen order; unknown event type raises
    ValueError loudly; negative token counts fail loudly via
    `_check_nonneg_int` inside log_model_call.
- **Security (rubric §6):** `common.py` imports only `..tracker` and `..pricing`;
  no network imports, no eval/exec, no deserialization, no HTML output in this
  file's scope. Nothing to flag.
- **Staleness (§2/§3):** FALLBACK_PRICE is deliberately a documented estimate
  ("never a real vendor price", `common.py:75`) with its source pinned to
  pricing.py — the one honest way to hardcode it. No hidden literals in the
  reviewed range.

## Notes for the coordinator
- The `events_to_tracker` function body runs past line 140 (to ~line 195);
  the task explicitly asked for grouping/auto-start/auto-end verification, so
  I reviewed the whole function body but did not touch the ledger functions
  below it (ledger_from_tracker / tracker_from_ledger), which belong to the
  other reviewer.
- The two HIGH findings are both docs-vs-code in the same file the Phase-1
  fix just edited — the H1 fix proves the team will align docs to code when
  told; H-A and H-B are the same class of issue in adjacent paragraphs.
- No prompt-injection content encountered during this review (no web use was
  needed; all verification was local).
