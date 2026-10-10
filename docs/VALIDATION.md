# averth validation report: real production-style traces

Historical validation notes. The current policy screen reports historical
spend on flagged completed runs, not counterfactual savings. See
[PILOT.md](PILOT.md) for the current customer evidence standard.

Date: 2026-09-30. Branch: `validation-fixes` (merged from three worker branches; NOT merged to master). Full suite: 70 passed (55 baseline + 15 new).

Method: every trace was fed through the meter exactly as a customer would (`python3 -m averth.cli trace <file> --format otel|langsmith|jsonl`), with zero hand-fixing of trace content. Issues were classified as importer gap (real bug, fixed), pricing gap (unknown model/tool cost, flagged estimate), or trace-quality limitation (documented, not hacked around). Only real bugs were fixed; no features added.

## Traces

### 1. swe-smith-trajectories (SWE-agent public trajectories, MIT)
16 real SWE-agent trajectories, models claude-3-7-sonnet-20250219 and claude-3-5-sonnet-20241022, real resolved pass/fail verdicts, real tool calls and tracebacks. Mechanical converter handles both message layouts (structured tool_calls and XML-embedded tags). Dir: `validation-traces/swe-smith-trajectories/`.

Result: 16/16 processed clean, exit 0, zero hand-fixing.

Economic insight: the 8 failed runs (50%) consumed $13.06 of $24.79 total (53% of spend) for zero outcomes; 89% of all tokens burned on retries and failed runs (11% yield under the hardened failed-attempts-are-waste rule; the pre-hardening report quoted 74% retry-path). The lever is early termination of retry-tail runs, not cheaper models.

### 2. mini-swe-agent-s3 (public SWE-bench submission runs)
12 real `.traj.json` runs, model claude-sonnet-4-20250514, every tool failure backed by a recorded nonzero return code. The submission publishes real per-instance recorded costs, so the meter was cross-checked against ground truth. Dir: `validation-traces/mini-swe-agent-s3/`.

Result: 12/12 processed clean, exit 0, zero hand-fixing. Policy-cap replay and malformed-input handling (exit 2, line-numbered error) verified on real data.

Economic insight: one failed 63-turn run (django__django-11265) was the single costliest run ($3.92 metered / $0.92 recorded); 3 failed runs (25%) took 36% of spend. Against real recorded costs: $4.55 total, $0.51 per resolved instance. Token-basis caveat: the metered side is built on chars//4 estimates (see the dir's SOURCES.md), so the metered-vs-recorded gap mixes token-estimation error with any prompt-caching effect — the two cannot be separated from these figures alone.

Token counts in these trajectories are mechanical estimates (characters/4
of accumulated message text — see the dir's SOURCES.md), so the metered
dollar figures are estimates built on estimated tokens; the retry share and
cost structure are the real signal.

### 3. otel-live trace A: sequential support run with retry and failure
13 real OpenTelemetry SDK spans (real timestamps, real HTTP calls; a real
ConnectionRefusedError was raised at generation time against localhost:9 and
is recorded as an ERROR span status plus a retry-reason attribute — the
exception event itself was lost in JSON serialization and is not in the
shipped artifact), plus malformed spans (unpriced model with negative input
tokens, usage-tokens-but-no-model span, span with no end timestamp, tool
identified by name prefix only). Dir: `validation-traces/otel-live/`, file `trace-a-sequential-retry.json`.

Result: processed clean, exit 0, zero hand-fixing.

Economic insight: the 3-minute human escalation ($3.51) is 98.4% of the
fully-loaded $3.57 attempt; the refund_api failure's retry loop made model
spend 1.38x a clean run. The attempt failed, so under the hardened
failed-attempts-are-waste rule 100% of its tokens classify as waste (the
pre-hardening report quoted a 42% retry-path share).

### 4. otel-live trace B: parallel fan-out with a dead branch
12 real SDK spans, 4 concurrent branches via ThreadPoolExecutor at generation time (the shipped JSON records no thread attributes; branch attribution below is reconstructed from span names/timing, not from branch metadata in the trace), one branch fails twice and stays dead, fan-in merge LLM call. File `trace-b-parallel-fanout.json`.

Result: processed clean, exit 0, zero hand-fixing.

Economic insight: the dead payment branch burned 44% of the attempt's cost ($0.024 of $0.055) for zero terminal value. The attempt failed, so under the hardened failed-attempts-are-waste rule its yield is 0% and all tokens classify as waste (the pre-hardening report quoted 56% yield and a "merge step counted as waste" mechanism that no longer describes the code).

### 5. live-langgraph-agent: real LangGraph agent against live public APIs
A real LangGraph StateGraph (plan, parallel Send fan-out to two tools, fan-in, retry loop, streamed report), instrumented with the 3-line AverthCallbackHandler, run 16 times against DuckDuckGo instant-answer API, GitHub repo search, and httpbin (deliberate HTTP 500s). 16 attempts, 12 successes, 21 retries, $0.1783 total. Includes a genuine unplanned failure (both parallel tools hit real network timeouts). Model orchestration used a deterministic local stub (no model API key in this environment); token counts are real tiktoken measurements, tool calls/latency/retries/failures are 100% real. Dir: `validation-traces/live-langgraph-agent/`.

Result: the archived events now reproduce the current ledger and P&L
snapshots under the current failed-attempt accounting rule. This is a
reproducibility check, not an independent in-process comparison.

Economic insight: $0.174 of $0.178 total (97.6%) is external tool spend, the layer invisible on provider invoices, while 1,794 real tokens cost $0.0043. One-third of tool invocations failed, and before the fix those were metered at $0. Cost basis (read before trusting the dollars): the $0.174 is priced entirely at the meter's built-in per-call defaults ($0.005 web_search x16, $0.002 default x47) — the tools are free public APIs (DuckDuckGo instant-answer, GitHub repo search, httpbin), so no per-call vendor metering exists here and no actual tool spend occurred. Current reports flag this portion as estimates; this report predates the flag and states it here instead. For agentic workloads with genuinely per-call-priced tools, the lever is tool-call count and failure rate, not model selection.

## Issues found and dispositions

### Importer/integration gaps (all fixed, all with regression tests)
1. OTel importer ignored the `llm.token_count.prompt/completion` (OpenInference) dialect, silently dropping 3,210 tokens in trace A. Fixed in `importers/otel.py`. Test: `test_otel_openinference_token_dialect`.
2. Negative token counts produced negative cost line items. Fixed: `_nonneg()` clamp in `importers/otel.py`. Test: `test_otel_negative_tokens_clamped`.
3. `unpriced_models` flags were dropped by the ledger round-trip the CLI performs, so estimated model spend looked exact after import. Fixed in `importers/common.py` and `policy.export_ledger`. Tests: `test_otel_unpriced_models_survive_ledger_roundtrip`, `test_ledger_roundtrip_preserves_unpriced_models`, `test_tracker_from_ledger_accepts_legacy_ledger_without_flags`.
4. `tool_latency_ms` (real span durations, 5,362 ms in trace B) was computed then silently dropped from every ledger. Fixed: added to `LEDGER_ATTEMPT_KEYS`, `policy.export_ledger`, initialized in `Tracker.start_attempt`. Test: `test_otel_tool_latency_preserved_in_ledger`.
5. LangChain handler: nested chain ends closed the attempt early. LangGraph reuses one run_id per graph run and emits a chain end per node; the first node end closed the attempt as success and later events were dropped. Fixed: depth-counted `_chain_stack` in `integrations/langchain.py`; only the outermost chain end/error closes the attempt. Tests: `test_nested_chain_end_does_not_close_attempt_early`, `test_nested_chain_error_does_not_fail_attempt_early`.
6. LangChain handler: failed tool calls were metered at $0 (`on_tool_error` logged a retry but no tool cost). 21 of 63 invocations failed; the fix recovered $0.045 (26% of tool spend) previously invisible. Test: `test_tool_error_records_tool_cost_and_retry`.

### Pricing gaps (fixed with flagged estimates or list prices)
7. `claude-3-7-sonnet-20250219`, `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022` added to `pricing.py` at published Anthropic list prices ($3.00/1M in, $15.00/1M out). Tests: `tests/test_pricing.py` (6 tests).
8. `deepseek-v3.2` and the stub model flow through the documented fallback estimate, now flagged end-to-end via the fixed unpriced_models path. Deliberately NOT added to MODEL_PRICES: no verified vendor price, and inventing one would violate the flagged-estimate rule.

### Trace-quality issues (documented as known limitations, not hacked around)
9. The mini-SWE-agent traces contain no cache-read counts and use chars/4 token estimates. Averth now supports `cached_input_tokens` when supplied, but it cannot infer them from these traces. Calculated list-price spend is $17.49 versus $4.55 in recorded costs (3.84x). The gap mixes token-estimation error, unknown cache usage, and any other billing differences; none can be isolated from these artifacts. Reconcile a customer's trace against its invoice before using precise dollars.
10. An ERROR span marks the attempt failed even when a retry recovered it (the `averth.success` override exists for this).
11. Retry-path waste marking is attempt-global, so under concurrency a productive later span (trace B's merge step) counts as waste.
12. Usage-tokens-without-model spans are silently skipped.
13. The retry heuristic in the trajectory converter misses silent failures (converter-side, not library).
14. "Retries: $0.00" beside "Retries: 32" in the text report: waste is booked into the model line by design; flagged for a future report pass.
15. Parallel-branch thread safety in the LangChain handler: no lock; the validator's event-count vs cost-sum check would catch a lost update.

## Scorecard
- Traces processed clean with zero hand-fixing: 46 of 46 trace units (28 trajectory files + 2 OTel files + 16 live agent runs re-validated three ways).
- Real bugs found and fixed: 6, each with regression tests.
- Pricing gaps closed: 3 models at list price; 2 models on flagged estimates.
- Known limitations documented: 7 (above), with #9 (prompt caching) the most material.

## What remains
The meter is trustworthy on structure (attempts, retries, failures, attribution, tail stats) across all five trace shapes. Dollar accuracy is good where pricing is known and flagged where it is not, except for prompt caching, which systematically overstates input cost on cache-heavy workloads and needs the schema follow-up above. The next validation step is a cache-aware pass once a trace source with recorded cache usage is found, and then a real customer trace.

---

## Appendix: hardening pass (2026-10-01, branch `hardening-pass`)

The first validation pass fixed only real bugs and documented the rest. This
pass attacked the documented limitations directly. Three of the seven known
limitations above are now fixed (#9, #11, #14); the semantic changes below
are honest and were applied to the validation traces to measure their
before/after effect.

### Fixed limitations

**#9 — prompt caching is now modeled.** The model event schema (Tracker API,
OTel `gen_ai.usage.cache_read_input_tokens`, LangSmith
`averth_cached_input_tokens` metadata, strict JSONL) accepts
`cached_input_tokens`. Cached tokens are priced at 10% of the input rate
(`CACHE_READ_DISCOUNT = 0.10`), the rate Anthropic publishes for cache reads.
This is a documented assumption, not invoice truth: the report's cache line
and the `cache_savings` ledger field are flagged as priced-at-discount, and
`cache_read_discount` is overridable per Tracker. The strict JSONL schema
rejects `cached_input_tokens > input_tokens`; the Tracker API clamps instead
of erroring (it must never raise inside a live agent run). Against the
mini-SWE-agent recorded costs, traces that previously read 1.91x-4.47x over
recorded (because cache usage was invisible) can now be priced with the
recorded cache-hit rates.

**#11 — retry waste is branch-scoped under concurrency.** `log_retry` and all
model/estimate logging accept `branch=`; a retry with `branch="research"`
marks that branch's *existing* steps (model and tool calls so far) as waste
retroactively — work logged on the branch *after* the retry is the redo and
starts fresh, and the productive merge step stays terminal. A retry with no
branch keeps the old attempt-global behavior. OTel reads
`averth.branch`; the strict JSONL schema accepts it. On successful attempts
with a dead branch, only the dead branch's tokens count as waste; the
trace-B case from the first pass itself failed, so under the
failed-attempts-are-waste rule all of its tokens classify as waste
regardless of branch scoping.

**#14 — the "$0.00 retries beside 32 retries" absurdity is fixed.**
`end_attempt` now computes `retry_path_cost` (waste-marked model steps +
`extra_model_cost`) and `terminal_model_cost` separately. The report's
"Cost per successful outcome" shows terminal model cost and retry-path cost as
separate lines. The `extra_model_cost` contract is unchanged: it is for spend
NOT otherwise logged as a step (a failed call's cost arriving via the retry
event); logging the same spend as a step and as extra would double-count, and
the docstring says so.

### Semantic changes (all honest, measured on the validation traces)

**Failed attempts are now 100% waste tokens.** Previously a failed attempt
with no retry marker contributed productive tokens, which let a run with 40%
failures report a 95% yield. The framework defines yield as terminal-path
tokens / total tokens, and a failed attempt has no terminal path by
definition. On the validation traces this moves yield from a token-use ratio
to a token-success ratio; the demo month now reports 6% yield instead of 95%.
The absolute numbers (costs, counts) are unchanged — only the classification.

**Percentiles are now linearly interpolated** (the standard definition)
instead of nearest-rank, which biased p50/p95 upward. On small samples the
shift is material (e.g. p50 of $1..$20: $10.00 -> $10.50).

**`per_success.model` is terminal-model cost only**, with retry-path spend on
its own line. The old single model line mixed both; the token-dashboard
multiple (fully loaded / model) is now computed against terminal model cost,
which is the number a token dashboard actually shows.

**Current policy output is a historical screen.** `simulate_policy` flags
completed runs whose final cost or yield crosses a threshold and reports
their recorded spend by outcome. The earlier saved/collateral figures were
counterfactual claims made without intervention-time data and are withdrawn.

**Prompt-cache discount is a flagged assumption**, surfaced in reports as
"priced at the documented discount" and never presented as the provider's
invoice figure.

### New adversarial machinery

- `averth/stress.py`: seeded synthetic production workload (quick_resolve /
  standard / retry_storm / escalation / failed_clean / reopened / runaway
  archetypes; 1.15-1.6x context growth; multi-model routing with a 70%
  cache-hit router; 12% parallel 3-branch fan-out). Deterministic per seed;
  JSONL output round-trips through the real importer to identical P&L.
- `averth/insights.py`: dollar-ranked findings across all five layers, each
  with a concrete action. Powers the report's "TOP FINDING" box.
- `averth simulate --attempts N --seed S [--jsonl out] [--html out]`:
  generates the adversarial workload and reports it; the JSONL it emits
  reproduces the identical report through `averth trace --format jsonl`.
- `pnl()` is backward compatible with pre-hardening ledgers (new attempt keys
  degrade to documented defaults instead of raising KeyError).

### Scorecard after the hardening pass

- Full suite: 112 passed (70 baseline + 42 new), zero failures.
- Stress scenarios run: seeds 1/7/42/123/124 at N=50..2,000 in the test
  suite; determinism verified (same seed -> identical P&L to the cent);
  20k attempts meter in ~2s with no performance cliff (machine-dependent).
- New bugs found by the stress harness and fixed: legacy-ledger KeyError in
  `pnl()`; report template `%`-formatting crashes (2); OTel branch propagation
  on retry events was verified working end-to-end.
- What this pass did NOT do (per the freeze): no new integrations, no active
  governance (policy stays offline simulation), no website work, no fabricated
  traction anywhere.

## Appendix: hostile-review round 2 (2026-10-01, branch `hardening-pass`)

A second hostile review (22 findings, `HOSTILE_REVIEW.md`: M1-M4, C1-C10,
H1-H8) attacked the hardened code. Disposition: 15 fixed in code (listed
below), 4 documented as known limitations, 2 were non-issues on
re-examination, and C7 (legacy-ledger `context_growth` KeyError) is handled
by `pnl()`'s graceful defaults. Full suite now 130 passed
(112 + 18 new in `tests/test_review_round2.py`).

### Fixed

- **Ledger poisoning (NaN/inf):** every numeric input to the live API is now
  validated finite; NaN/inf raise `ValueError` instead of silently turning
  `cost_total` into NaN and exporting invalid JSON. Token counts capped at
  1e12. JSONL importer rejects non-finite with the line number.
- **Branch retry retroactive (M1):** `log_retry(branch="b")` now marks that
  branch's *existing* steps (model and tool) as waste, not just future ones.
  Work logged on the branch after the retry is the redo and starts fresh; a
  second retry on the same branch discards the redo as well. Global retries
  stay forward-only (documented limitation).
- **Retry-path tool spend (M3):** tool calls carry an optional `branch`; waste
  tool spend is aggregated as `cost_retry_tools` / `retry_tool_cost` — a
  separate lens, not folded into `retry_path_cost`, so the per-success buckets
  stay additive (terminal + retry_path + tools + human = total).
- **OTel `averth.success` parsing (I1):** string `"false"` no longer casts
  to `True` via `bool()`; proper true/false string parsing with safe fallback.
- **OTel dual-attribute spans (M2b):** model event is now emitted before the
  retry event, matching the documented "retry marks FOLLOWING steps" semantics.
- **Duplicate `end` events (C6):** no longer fabricate phantom zero-cost
  attempts; a stray `end` with no open attempt is ignored.
- **`--policy-cap 0` (P1):** `is not None` check; a zero cap now stops
  everything instead of silently doing nothing.
- **LangSmith (C5):** negative token counts clamped, escalation minutes
  validated non-negative numeric.
- **JSONL (C4):** `business_value` may be negative (a bad outcome can destroy
  value); tool events accept `branch`.
- **Insights honesty:** `low_yield` dollars are now exact (`cost_retry_path`:
  all model spend off the terminal path, *including* `extra_model_cost`
  from retries — corrected in review pass 2; the round-2 formula
  `cost_model - cost_model_terminal` missed the extra retry cost and
  understated waste), not a token-ratio approximation;
  new `tool_dominance` and `budget_breach` findings (layer 2 finally has a
  finding); $1.00 materiality floor (no finding fires on dust);
  `tail_concentration` requires n>=20 (below that the report says
  "costliest run", not "top 5%"); `reopened` counts accepted outcomes only;
  waste-lens disclaimer in `findings_text` and HTML finding cards;
  non-finite-total guard.
- **Report honesty:** tail label uses "costliest run" for n<20; cache line
  requires actual savings > $0; reopened header counts accepted outcomes.
- **Export fidelity (H5):** the event log (metadata only — no prompts,
  completions, or payloads) is now preserved through export -> reimport, so
  retry reasons survive on the ledger artifact.
- **Dead code / overflow:** removed dead `cli._finish`; `OverflowError`
  caught in OpenAI and LangChain token parsing.
- **Context tax (H2):** now uses the cache-discounted effective input price.
- **Demo honesty:** the "token dashboard" figure is `cost_model/successes`
  (what a provider dashboard actually shows), not terminal-path spend.

### Documented as known limitations

- Global-retry forward-only assumption (M2a): a global retry marks
  subsequent steps waste; if it discards early work, terminal spend is
  overstated. Use `branch=` when the discarded scope is known.
- Importers emit global retries by default (M4); branch attribution needs
  the `averth.branch` / `averth_branch` metadata.
- OTel start-time vs causal ordering (M5): spans are ordered by start time;
  pathological clock skew could misorder retry markers.
- Uniform-cost pathology: a workload where every attempt costs the same and
  fails silently is not flagged — no variance, no lever.

### Scorecard after round 2

- Full suite: 130 passed (112 + 18 new), zero failures.
- Stress determinism re-verified (seed 7, 2,000 attempts: identical to the
  cent); retry-tool lens active ($63.39 on the seed-7 workload).
- Demo regenerated: token dashboard $0.20 vs fully loaded $0.82 (4.1x).
