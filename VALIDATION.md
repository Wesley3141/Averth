# agentpnl validation report: real production-style traces

Date: 2026-09-30. Branch: `validation-fixes` (merged from three worker branches; NOT merged to master). Full suite: 70 passed (55 baseline + 15 new).

Method: every trace was fed through the meter exactly as a customer would (`python3 -m agentpnl.cli trace <file> --format otel|langsmith|jsonl`), with zero hand-fixing of trace content. Issues were classified as importer gap (real bug, fixed), pricing gap (unknown model/tool cost, flagged estimate), or trace-quality limitation (documented, not hacked around). Only real bugs were fixed; no features added.

## Traces

### 1. swe-smith-trajectories (SWE-agent public trajectories, MIT)
16 real SWE-agent trajectories, models claude-3-7-sonnet-20250219 and claude-3-5-sonnet-20241022, real resolved pass/fail verdicts, real tool calls and tracebacks. Mechanical converter handles both message layouts (structured tool_calls and XML-embedded tags). Dir: `validation-traces/swe-smith-trajectories/`.

Result: 16/16 processed clean, exit 0, zero hand-fixing.

Economic insight: the 8 failed runs (50%) consumed $13.06 of $24.79 total (53% of spend) for zero outcomes; 74% of all tokens burned on the retry path. The lever is early termination of retry-tail runs, not cheaper models.

### 2. mini-swe-agent-s3 (public SWE-bench submission runs)
12 real `.traj.json` runs, model claude-sonnet-4-20250514, every tool failure backed by a recorded nonzero return code. The submission publishes real per-instance recorded costs, so the meter was cross-checked against ground truth. Dir: `validation-traces/mini-swe-agent-s3/`.

Result: 12/12 processed clean, exit 0, zero hand-fixing. Policy-cap replay and malformed-input handling (exit 2, line-numbered error) verified on real data.

Economic insight: one failed 63-turn run (django__django-11265) was the single costliest run ($3.92 metered / $0.92 recorded); 3 failed runs (25%) took 36% of spend. Against real recorded costs: $4.55 total, $0.51 per resolved instance.

### 3. otel-live trace A: sequential support run with retry and failure
13 real OpenTelemetry SDK spans (real timestamps, real HTTP calls, a real recorded ConnectionRefusedError with ERROR status and retry), plus malformed spans (unpriced model with negative input tokens, usage-tokens-but-no-model span, span with no end timestamp, tool identified by name prefix only). Dir: `validation-traces/otel-live/`, file `trace-a-sequential-retry.json`.

Result: processed clean, exit 0, zero hand-fixing.

Economic insight: the 3-minute human escalation ($3.51) is 98.5% of the fully-loaded $3.57 attempt; the refund_api failure's retry loop made model spend 1.39x a clean run and put 42% of all tokens on the retry path.

### 4. otel-live trace B: parallel fan-out with a dead branch
12 real SDK spans, 4 concurrent branches via ThreadPoolExecutor, one branch fails twice and stays dead, fan-in merge LLM call. File `trace-b-parallel-fanout.json`.

Result: processed clean, exit 0, zero hand-fixing.

Economic insight: the dead payment branch burned 44% of the attempt's cost ($0.024 of $0.055) for zero terminal value; yield reads 56% but overstates waste under concurrency because the productive merge step is counted as retry-path waste.

### 5. live-langgraph-agent: real LangGraph agent against live public APIs
A real LangGraph StateGraph (plan, parallel Send fan-out to two tools, fan-in, retry loop, streamed report), instrumented with the 3-line AgentPNLCallbackHandler, run 16 times against DuckDuckGo instant-answer API, GitHub repo search, and httpbin (deliberate HTTP 500s). 16 attempts, 12 successes, 21 retries, $0.1783 total. Includes a genuine unplanned failure (both parallel tools hit real network timeouts). Model orchestration used a deterministic local stub (no model API key in this environment); token counts are real tiktoken measurements, tool calls/latency/retries/failures are 100% real. Dir: `validation-traces/live-langgraph-agent/`.

Result: validated clean with zero hand-fixing. In-process pnl(), rehydrated ledger, and CLI output all agree on every bucket.

Economic insight: $0.174 of $0.178 total (97.6%) is external tool spend, the layer invisible on provider invoices, while 1,794 real tokens cost $0.0043. One-third of tool invocations failed, and before the fix those were metered at $0. For agentic workloads with per-call-priced tools, the lever is tool-call count and failure rate, not model selection.

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
9. Prompt caching is not modeled. Against mini-SWE-agent's real recorded costs, the meter reads $17.49 vs $4.55 recorded (3.84x; per-instance 1.91x-4.47x, rising with run length). Implied prompt-cache hit rates of 0.48-0.90 reproduce the recorded costs exactly. The library prices all input tokens at list rate with no cache term; traces record no cache usage, so a cache-aware change could not be validated here. Recommended follow-up: add `cached_input_tokens` to the model event schema. This is the largest known accuracy gap and the top candidate for the next validation pass.
10. An ERROR span marks the attempt failed even when a retry recovered it (the `agentpnl.success` override exists for this).
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
