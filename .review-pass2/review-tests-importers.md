# Review: tests/test_importers.py + test_importer_hardening.py + test_policy.py
Reviewer: hostile test reviewer, pass 2 (2026-10-02)
Scope: the TESTS, not the source. 29 tests, all pass (venv pytest).
Method: read every test against the source it exercises, hand-verified the
asserted math with independent scripts, checked which Phase-1 fixes are pinned
and where, grepped the whole tests/ dir for duplicate coverage.

## Verdict

**No CRITICAL findings. 2 HIGH, 4 MEDIUM, 5 LOW.** The test files are
substantially honest: zero mocks (real temp files, real importers, real
Tracker), every asserted dollar figure I checked is independently correct,
and the branch-retry past-only semantics (the H1 fix) are genuinely pinned
by a real calculation, not a tautology. The fixtures are realistic vendor
shapes. The main weaknesses are Potemkin-style gaps: one validation test
that only executes 1 of its 6 bad inputs, and a policy-ledger round-trip
test that checks keys but never values or the documented retry-reason
survival. None of the tests encode the pre-fix buggy behavior.

Hand-verified numbers (independent recomputation, all match):
- test_otel_openinference_token_dialect: 2000/1e6*0.30 + 500/1e6*1.20 = $0.0012 ✓
- test_otel_tool_latency: 1,300,000,000 ns / 1e6 = 1300.0 ms ✓
- test_otel fixture trace-b: 8200 tokens, global retry marks post-retry 4400 waste;
  pnl() yield 0.5294 = 1 − (4400+1200 failed-trace-c)/11900 ✓ (my first hand-calc
  was wrong because I forgot pnl() aggregates all 3 attempts — not a bug)
- test_otel_branch_scoped_retry_on_span: 3300 tokens, branch retry retro-marks
  pre-retry 1100 waste, post-retry redo starts fresh → yield 1−1100/3300 ✓
  (this is the past-only semantics the H1 docstring fix requires)
- policy build_tracker: cheap $0.00525, expensive $53.70, failed $0.50;
  cap=(cheap+expensive)/2 stops only expensive; saved=0, collateral=53.70 ✓
- expensive yield = 1 − 1.0M/1.6M = 0.375 < 0.75 floor → stopped; cheap/failed
  yield 1.0 (failed is tool-only, zero tokens → the documented 1.0 default) ✓
- export_ledger key list == common.LEDGER_ATTEMPT_KEYS: both 25 keys, identical
  today ✓ (but nothing pins this — see M1)

## HIGH

### H1. test_jsonl_invalid_lines_raise executes only 1 of its 6 bad inputs
tests/test_importers.py:196-216

The test writes six invalid lines (missing field, unknown type, non-bool
success, negative cost, unknown key, malformed JSON) and asserts only
`"line 1" in str(ctx.exception)`. `load_jsonl` validates line 1 first and
raises, so entries 2–6 NEVER EXECUTE. The five remaining validators —
unknown event type (jsonl.py:88), `success`/`reopened` must-be-bool
(jsonl.py:120-124), negative cost (jsonl.py:110-114), unknown-key rejection
(jsonl.py:132-136), malformed JSON (jsonl.py:144) — are not exercised
anywhere in the assigned files. I grepped all of tests/: no other test file
covers them individually either (only NaN rejection is covered, in
test_review_round2.py:181). Consequence: a regression that deletes the
unknown-key check passes the whole suite, and a typo'd field like
`"input_token"` (missing s) would then be silently ignored → zero tokens →
wrong dollars, silently. This is exactly the silent-corruption shape the
strict schema exists to prevent, and the module docstring
(test_importers.py:1: "plus validation tests") claims this coverage exists.

### H2. Policy-ledger round-trip checks keys, never values or event survival
tests/test_policy.py:32-40 and tests/test_policy.py:43-58

- `test_export_load_roundtrip_preserves_schema` asserts only
  `SCHEMA_KEYS.issubset(set(a.keys()))`. The hand-maintained SCHEMA_KEYS
  (test_policy.py:9-16) omits 4 of the 25 real export keys
  (`retry_tool_cost`, `tool_latency_ms`, `events`, `tool_steps`). If
  `export_ledger` silently dropped `"events"`, this test still passes.
- `test_ledger_contains_no_payload_data` iterates `a.get("events", [])` —
  a missing events key makes the loop a no-op and the test still passes.
- The comment at test_policy.py:54-55 states "events ARE exported (retry
  reasons must survive reimport)", but NO test asserts a retry reason (or
  any event) actually survives export → import. The documented H5 behavior
  is verified by comment only.
- No test runs `tracker_from_ledger` on a `policy.export_ledger` output and
  checks `pnl()` matches the source tracker. A value-level regression
  (rounding, a dropped field, a renamed key) that preserves key presence
  passes every policy test. (The importer-side round trip is better covered:
  test_importers.py:245 asserts cost_total/business_value, but the
  policy-export path is a different writer and is unpinned.)

## MEDIUM

### M1. No parity test between policy.export_ledger and common.LEDGER_ATTEMPT_KEYS
averth/policy.py:30-53 vs averth/importers/common.py:201-228

common.py:201 carries the comment "Must match the key list in
policy.export_ledger". Today they do (verified: 25 keys, set-identical).
But no test asserts `set(LEDGER_ATTEMPT_KEYS) == set(<export keys>)`, and
the test_policy.py SCHEMA_KEYS is a third hand-maintained copy that is only
subset-checked. A one-sided future edit (e.g. adding a per-attempt metric
to export_ledger but not LEDGER_ATTEMPT_KEYS, or vice versa) diverges the
two ledger paths silently — the importer reimport path (`tracker_from_ledger`
→ `pnl()`, which does `a["total_cost"]` etc. without .get) would KeyError
or misreport. A three-line parity test would pin the documented invariant.

### M2. test_ledger_roundtrip_preserves_pnl checks only 4 of ~25 fields
tests/test_importers.py:245-261

Asserts attempts, successes, cost_total, business_value survive
`events_to_tracker → ledger_from_tracker → tracker_from_ledger`. Unasserted:
waste_tokens / yield, cached_tokens / cache_savings, retry_path_cost,
terminal_model_cost, tool_latency_ms, per_model, events, tool_steps. A
regression that dropped `waste_tokens` from the rehydrated attempt would
pass while the yield story silently changed. (unpriced_models is covered by
test_importers.py:231; price_vintage by test_review_round3.py:113 — those two
are fine.)

### M3. policy_text is only tested on a hand-built dict, never on real output
tests/test_policy.py:121-140

`test_policy_text_renders` constructs the `sim` dict by hand. If
`simulate_policy`'s return dict gains/renames a key (e.g. the saved/collateral
split fields), `policy_text` can KeyError on the real CLI path while this
test passes. One integration test — `policy_text(simulate_policy(ledger, …))`
on the build_tracker fixture — would close it. (Checked: test_cli.py:114
exercises simulate_policy via --policy-cap but never calls policy_text.)

### M4. simulate_policy edge inputs untested in assigned files
averth/policy.py:60-100

- Empty ledger (`{"attempts": []}`): the `exposed / total if total else 0.0`
  guard and the `sorted(...)[:10]` on empty are never exercised. (The only
  empty-attempts test, test_importers.py:243, covers tracker_from_ledger,
  not simulate_policy.)
- Exact-at-cap boundary: `>` is strict, so a run at exactly the cap is NOT
  stopped. The audit noted this as "defensible, but document the boundary"
  (LOW). No test pins the boundary either way, so a future `>=` change
  (or an accidental one) is invisible.

## LOW

### L1. Negative-token test asserts >= 0 where the truth is exactly 0
tests/test_importers.py:111-121

`test_otel_negative_tokens_clamped` asserts
`assertGreaterEqual(a["per_model"][...], 0)` and
`assertGreaterEqual(a["total_cost"], 0)`. The importer's `_nonneg` clamp
guarantees exactly 0 here (no tools on the span). The weaker assertion
would also pass if clamping regressed to, say, a small positive epsilon.
Harmless, but the test undersells the guarantee it means to pin.

### L2. Fixtures exercise only the legacy agentpnl.* marker names
tests/fixtures/otel_spans.json, tests/fixtures/langsmith_runs.json

The OTel fixture's retry marker is `agentpnl.retry`; the LangSmith fixture's
are `agentpnl_retry` / `agentpnl_escalation_minutes`. The NEW `averth.*`
names are covered only by synthetic hardening-test spans/runs
(test_importer_hardening.py), never by a realistic full-trace fixture. Not a
correctness gap, but the fixtures under-represent the current contract.

### L3. Fixture tests lean on assertGreater(cost_total, 0) smoke assertions
tests/test_importers.py:35, 141, 163

Each fixture test asserts `cost_total > 0` alongside specific assertions
(case_ids, retries, human_min, per_model keys). The smoke part is fine as a
canary; the specific assertions carry the weight. Not tautological, just
noted.

### L4. Hardcoded price literals in dialect test are fail-loud, acceptable
tests/test_importers.py:105-109 and tests/test_importers.py:271-278

`2000/1e6*0.30 + 500/1e6*1.20` and the `(1.00, 3.00) → $4.00` fallback
expectation duplicate price-table values as literals. If MODEL_PRICES
changes, these fail LOUDLY and force a conscious update — the right failure
mode for a pricing pin. No action; recorded so a future reader doesn't
"fix" them into tautologies.

### L5. Mixed test frameworks
tests/test_importers.py uses unittest + sys.path hack; test_importer_hardening.py
and test_policy.py use pytest. Cosmetic; the suite runs green under both
runners.

## Coverage map for the brief's three named gaps

- **Ledger round-trip vintage (C2 fix):** NOT in assigned files — covered by
  test_review_round3.py:113 (`test_ledger_roundtrip_preserves_vintage`) and
  :101/:122. No gap repo-wide, but the importer/policy test files I reviewed
  don't touch it.
- **FALLBACK_PRICE dedupe (M1 fix):** NOT in assigned files — covered by
  test_review_round3.py:249 (`test_fallback_price_matches_pricing_estimate`,
  asserts `common.FALLBACK_PRICE == pricing.ESTIMATED_MODEL_PRICES`). The
  assigned files do exercise the fallback VALUE ($4.00 at test_importers.py:271)
  but not the single-source-of-truth identity.
- **Branch-retry past-only semantics (H1 fix):** COVERED in assigned files —
  test_importer_hardening.py:59-92 (`test_otel_branch_scoped_retry_on_span`)
  asserts yield == 1−1100/3300, i.e. the pre-retry branch step is waste and
  the post-retry redo starts fresh. This genuinely pins the fixed behavior
  (the old docstring's "past and future" reading would give a different
  number). Complemented by test_review_round3.py:228 (docstring-vs-code).

## Other Phase-1 fixes and where they are pinned (for the coordinator)

All verified present in the suite, none in my three files: C1 budget hook on
failed attempts (test_review_round3.py:21,35,43,60), C4 NaN/inf JSONL
rejection (test_review_round2.py:181), C6 duplicate-end (test_review_round2.py:122),
cap=0 (test_review_round2.py:116), I1 OTel string-"false" (test_review_round2.py,
per its header), M3 explicit-zero labor rate (test_review_round3.py:143).

## Notes

- No mocks, stubs, or monkeypatching anywhere in the three files. Inputs are
  built as real files (tempfile) or realistic vendor-shaped dicts; the OTel
  tests cover both the OTLP attribute-list dialect (fixtures) and the
  flat-dict dialect (hardening `_span` helper). This is the strongest part of
  the test design.
- No test encodes pre-fix buggy behavior; all 29 pass against the fixed code.
- No prompt-injection content encountered (no web use in this review).
