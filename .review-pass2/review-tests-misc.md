# Review pass 2 — tests: test_report, test_insights, test_cli, test_stress, test_integrations, test_review_round2, test_review_round3

Reviewer posture: hostile. All 81 tests in these files pass (verified in
`~/workspace/averth/.venv`, 1.94s). Passing is not the bar — the questions
are: do the assertions prove anything, do they encode buggy behavior, and
what is not covered.

## Severity counts
- CRITICAL: 0
- HIGH: 4
- MEDIUM: 10
- LOW: 4

---

## HIGH

### H1. `averth pricing` (the C2 user-facing fix) has zero test coverage
- `tests/test_cli.py` — no test invokes `main(["pricing"])` or
  `build_parser()`'s pricing subcommand. Nothing asserts exit 0, the
  version/date/staleness lines, or the "how to update" instructions.
- The audit's C2 fix had four parts (dated/versioned table, staleness
  warning, one-command visibility, vintage stamped on reports). The first
  two and the fourth are pinned in `test_review_round3.py`; the third —
  the actual `averth pricing` command Wesley would run — is tested by
  nobody. A regression that deletes the subparser or breaks
  `_cmd_pricing` would sail through the suite.
- Verified the command works today (prints "Averth price table v2 ...",
  rc 0), so this is purely a coverage gap, not a code bug.

### H2. New HTML report banners/labels are unasserted; XSS-escaping claim has no test
- `tests/test_report.py` (65 lines) asserts: return path, file exists,
  agent name in body, "Fully loaded" in body, per-success figure rendered,
  `<svg` present, footer string, policy-section strings. That is all.
- The Phase-1 fixes added these HTML elements in `averth/report.py`,
  none of which any test asserts:
  - `unpriced_banner` ("Estimated spend") — `report.py:write_html`
  - `tool_est_banner` ("Estimated tool spend") — H2 flag
  - `stale_banner` ("Stale pricing")
  - `human_note` ("default assumption", C3)
  - `vintage_line` ("Price table v…")
  - token-dashboard `mult_card` (`token_dashboard_per_success` param is
    never passed by any test)
- Worse: the test's own fixture *triggers* three of these. I verified:
  `_build_tracker` logs `crm_lookup` with no explicit cost (default
  $0.002 estimate) and uses the default labor rate, so the rendered HTML
  contains the tool-estimate banner, the vintage line, and the human
  assumption note — and the test walks right past them asserting none.
- Security gap: the audit's security checklist item 10 claims "HTML
  report escapes all user-controlled strings" — I confirmed escaping
  works (malicious `<script>` agent name and `<img onerror>` case_id
  render escaped in `/tmp/probe_xss.html`), but **no test pins it**.
  An escaping regression is a stored-XSS vector in a shareable HTML
  report and the suite would not catch it.

### H3. Fake-importer fallback in test_cli.py is dead code; module docstring is stale; uses deprecated `tempfile.mktemp`
- `tests/test_cli.py:9-16` module docstring: "If averth.importers is not
  ready yet, the fixture path is exercised via monkeypatched stand-ins
  rather than failing the suite."
- `averth/importers/` exists with `jsonl.py` (imported successfully by
  `test_stress.py`), so `_try_real_importer()` always returns True and
  `_install_fake_importer` never runs in this repo.
- Consequences: (a) the docstring describes a situation that cannot
  occur — docs-vs-code; (b) `_install_fake_importer` (~35 lines) is
  untested dead code containing `tempfile.mktemp` (deprecated, insecure
  tempfile creation) — anyone "fixing" the docstring's scenario would
  inherit that; (c) the fallback's `fake_load_jsonl` ignores the fixture
  file entirely and returns a hardcoded tracker, so even if it did run
  it would not test parsing.

### H4. test_cli_simulate_exit0 contains two vacuous/tautological assertions
`tests/test_stress.py:95-103`:
```python
assert "TOP FINDING" in out or "No material findings" in out
...
assert "What to do Monday morning" in body or "Averth" in body
```
- First: `report_text()` prints `"TOP FINDING [...]"` iff `findings(p)`
  is non-empty, and `findings_text()` prints `"No material findings..."`
  iff it is empty. The `or` is exhaustive over program state — it asserts
  nothing about the CLI, the simulation, or the report. A test that
  cannot fail is not a test.
- Second: `write_html` always emits `<footer>Generated locally by
  averth...` and `<title>Averth report:` — `"Averth" in body` is
  unconditionally true, so the disjunct makes the "What to do Monday
  morning" check (the only meaningful half) optional. The test would pass
  even if insight cards silently stopped rendering.
- `"Fully loaded" in out` is the only load-bearing assertion in the test.

---

## MEDIUM

### M1. Hardcoded `/tmp` path in test_review_round2.py (parallel-run collision, /tmp volatility)
- `tests/test_review_round2.py::test_export_is_valid_json_after_rejection`
  writes to the fixed path `"/tmp/review2-ledger.json"`.
- Two concurrent pytest runs (or a reviewer and CI on the same box)
  write the same file; a sibling process can read a half-written ledger
  or delete it. `tmp_path` exists in the same file's other tests — this
  one just didn't use it.
- AGENTS.md notes /tmp can be wiped mid-task; the ledger here is small,
  but the collision hazard is real.

### M2. test_price_vintage_shape is a scheduled time bomb
- `tests/test_review_round3.py::test_price_vintage_shape` asserts
  `v["stale"] is False  # table was just verified`.
- `PRICE_TABLE_UPDATED = "2026-10-02"`, `PRICE_TABLE_STALE_AFTER_DAYS =
  90` → this test starts failing on ~2026-12-31 with zero code changes.
- Arguably intentional (forces the operator to re-verify prices), and the
  CLI's own copy tells you how. But it is a date-dependent suite
  failure, and the comment "table was just verified" will be false for
  anyone reading the test after the bomb goes off. At minimum the
  assertion should be `v["stale"] is False or <explicit skip reason>`,
  or the bomb should be documented in the test as deliberate.

### M3. Dead helper `_pnl_with` in test_insights.py
- `tests/test_insights.py:9-16` defines `_pnl_with(**kw)` — "Build a pnl
  dict from a driven tracker, then override keys." It is never called by
  any test in the file. Dead test code / AI slop; delete it.

### M4. Tautological assertion in test_integrations.py
- `tests/test_integrations.py::test_original_client_not_mutated`:
  ```python
  self.assertIs(self.client.chat, self.client.chat)  # untouched
  ```
  An object is always identical to itself. This line proves nothing; the
  real checks are the adjacent `assertIsNot` lines. The comment
  "untouched" claims a property the line does not verify.

### M5. test_integrations.py hardcodes price tuples instead of referencing pricing constants
- `(3.00, 15.00)` for `anthropic:claude-sonnet-4-5`,
  `(0.30, 1.20)` for `openai:gpt-5.6-mini`, `(0.05, 0.40)` for
  `openai:gpt-5-nano`, and the fallback `(1.00, 3.00)` appear as literals
  in `test_llm_cost_captured_with_priced_model`,
  `test_unknown_model_falls_back_to_estimate`,
  `test_chat_completions_captures_priced_model`,
  `test_responses_api_uses_output_token_fields`,
  `test_unknown_model_estimate_fallback`.
- Wesley's hardcoded-values priority applies to the test suite too: when
  a vendor price is updated per the new C2 discipline, these literals
  must be found and edited by hand in a second file. The fallback
  literal `(1.00, 3.00)` is especially bad — `pricing.ESTIMATED_MODEL_PRICES`
  exists precisely for this (and `test_fallback_price_matches_pricing_estimate`
  in round3 pins the constant, not the uses).
- Counterpoint: pinning exact dollars is the point of regression tests.
  The fix is not to remove the pins but to derive them from the table
  (e.g. `pricing.MODEL_PRICES["openai:gpt-5.6-mini"]`) so a legitimate
  price update touches one file.

### M6. test_branch_fanout_keeps_honest_yield asserts tags, not yield honesty
- `tests/test_stress.py:79-85` is titled "A dead branch's retry must not
  smear the productive merge step" but asserts only:
  - some events carry a `branch` tag,
  - at least one branch-scoped retry event exists.
- It never compares a yield/waste number against a hand-computed
  expectation. The actual yield-honesty behavior is pinned by
  `test_review_round2.py`'s branch tests; this stress test's title
  promises a property its body does not check.

### M7. No exact-boundary tests for any materiality threshold
- Insights thresholds are all boundary-sensitive (`>= 0.15` failed
  share, `>= 0.40` tail share with `n >= 20`, `>= 0.20`/`0.35` retry
  share, `>= 0.50` human/tool share, `< 0.60` yield, `$1.00` floor) and
  the policy sim uses strict `>` (a run exactly at the cap is NOT
  stopped — the audit's noted-but-undocumented boundary).
- Existing tests probe 10%-vs-20% (failed share) and n=10-vs-n≥20
  (tail), but no test sits exactly ON any threshold. An off-by-one or
  `>`/`>=` flip on any rule would pass the suite.

### M8. CLI surface gaps: --policy-yield, --jsonl, --agent, attempts<1, default html path
- `tests/test_cli.py` covers `--policy-cap` but never `--policy-yield`
  (the second policy knob); never `--jsonl` on `simulate` (verified the
  flag works manually — no test); never `--agent` override on `trace`;
  never `simulate --attempts 0` (I verified it returns 2 with a clean
  stderr message — unpinned); never the default HTML path
  (`<inputfile>.html` in cwd).
- `test_missing_file_exit2` and `test_bad_format_flag_exit2` are good;
  the gaps above are the untested half of the same surface.

### M9. test_tool_cost_captured pins the arbitrary H2 default without asserting its flag
- `tests/test_integrations.py::test_tool_cost_captured` asserts
  `web_search` costs exactly `0.005` — the audit-flagged arbitrary
  built-in estimate — with no assertion that the spend is flagged as an
  estimate (`tools_default_priced_names`). A reader sees the number
  pinned as "correct" and the H2 warning invisible. The round3 tests pin
  the flag via `Tracker` directly, but the integration path (the one a
  LangChain user actually hits) does not.

### M10. test_insights rank comment overstates the sort ("strictly by dollars")
- `tests/test_insights.py::test_findings_rank_by_dollars` comment:
  "ranking is strictly by dollars". `averth/insights.py` sorts by
  `(-dollars, severity-rank)` — severity breaks dollar ties. Moot in this
  test (both HIGH), and I verified by running that exactly the two
  claimed findings fire (top-5% of $208 is $50 = 24% < 40% tail
  threshold, so no third finding — the comment's "$200 failed of $208"
  arithmetic checks out). Docs-vs-code nit only.

---

## LOW

### L1. Trivial `"Averth" in out` assertions
- `tests/test_cli.py::test_trace_jsonl_exit0` asserts `"Averth" in out`
  — the CLI prints the full text report, so this is near-vacuous.
  Harmless, but it is the weakest possible content check alongside a
  decent structural one (html file exists, agent name in it).

### L2. write_jsonl == generate event identity is unpinned
- `test_jsonl_roundtrip_identical` round-trips through the importer
  (strong), and I verified `stress.write_jsonl(seed, attempts)` produces
  byte-identical events to `generate(seed, attempts, record_events=True)`.
  No test pins that identity directly; a future `write_jsonl` that
  regenerated differently would still pass roundtrip but break the
  "simulate --jsonl feeds averth trace" contract.

### L3. test_report never passes token_dashboard_per_success
- `write_html(..., token_dashboard_per_success=...)` renders the
  "Token-dashboard multiple" card and `report_text` the "Token dashboard"
  line — the demo's headline comparison. Untested in both renderers.

### L4. Insights findings with no test in the assigned files
- `low_yield` and `reopened` findings have no test among these files
  (may be covered elsewhere — not verified), and the `budget_breach`
  MEDIUM-severity branch (breaches < 10% of attempts) is untested; only
  the HIGH branch is pinned in round3.

---

## What the tests do well (hostile reviewer must concede)
- `test_review_round2.py` and `test_review_round3.py` are genuinely
  good regression pins: each audit fix (C1–C3, H1–H4, M1, M3) has a test
  that fails if the fix is reverted in the obvious way. I spot-checked
  the branch-waste arithmetic (`waste_tokens == 1100` / `2200`) against
  `tracker.py` semantics — consistent.
- `test_stress.py::test_deterministic_for_fixed_seed` and
  `test_jsonl_roundtrip_identical` (14 pnl keys, `pytest.approx`) are
  the strongest determinism/serialization pins in the suite.
- `stress.generate` uses a dedicated `random.Random(seed)` (not the
  global RNG) — determinism is structural, not accidental.
- The OTel string-"false"/"True" tests and the NaN/inf rejection tests
  target real past bugs, not happy paths.

## Notes / non-findings
- No prompt-injection content encountered (no web use in this review).
- `test_price_vintage_shape` asserting the exact key set
  `{"version","updated","age_days","stale","stale_after_days"}` is
  intentionally brittle — acceptable for a pin, not flagged.
- `test_deterministic_for_fixed_seed` uses exact float `==` on
  `cost_total`/`yield_ratio`; safe here because both sides derive from
  the same seeded RNG, not from two independent computations.
