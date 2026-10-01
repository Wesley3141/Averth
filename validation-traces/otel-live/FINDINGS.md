# OTel live-trace validation: findings

Date: 2026-09-30. Repo: github.com/Wesley3141/agentpnl, master @ 96bb241.
Branch for fixes: `validation-fixes-otel`.

## Per-trace outcome

Both trace files were generated live (real SDK spans, real timestamps,
real HTTP durations, real recorded exceptions; see SOURCES.md) and fed to
the CLI exactly as written, zero hand-fixing. Both exited 0.

**trace-a-sequential-retry.json** (13 spans, 1 trace id): sequential support
run, plan -> crm_lookup -> draft -> 3-min human escalation -> refund_api
FAILS (real ConnectionRefusedError, ERROR status, retry marker) -> re-plan
-> refund_api succeeds -> summarize. Plus malformed spans: unpriced model
with negative input tokens, a span with usage tokens but no model, a span
with no end timestamp, a tool span identified by name prefix only.

Imported as 1 attempt: failed=True (ERROR span), 1 retry, 3 escalation
minutes, business_value 12.50 from the parent span, 4 tool calls at $0.002,
total cost $3.57. Attempt boundaries correct; parent span has no model
attribute so nested spans do not double-count.

**trace-b-parallel-fanout.json** (12 spans, 1 trace id): 4 concurrent
branches (ThreadPoolExecutor), branch 2 fails twice and stays dead,
fan-in merge LLM call. Imported as 1 attempt: failed=True, 2 retries,
all 4 branches captured, merge call captured, total cost $0.05.

Post-fix, all 21 programmatic verification checks pass
(`verify_expected.py`: token math per model, attempt boundaries, retry
counts, escalation minutes, business_value override, tool latency > 0,
no negative costs, unpriced model flagged).

## Issues found, classified

### (a) Importer gaps, FIXED

1. OpenInference token dialect ignored. Spans carrying only
   `llm.token_count.prompt` / `llm.token_count.completion` imported as
   0 tokens (trace A retry_plan: 3,210 tokens vanished; trace B gemini
   branch: 2,610 tokens vanished, cost $0.00). Fix: added both keys to
   the token lookup lists in `agentpnl/importers/otel.py` and documented
   them in the module docstring. Test:
   `test_otel_openinference_token_dialect`.

2. Negative token counts produced negative cost. A span with
   `gen_ai.usage.input_tokens = -500` yielded a `$-0.00` model-mix line
   item. Fix: new `_nonneg()` clamp in `otel.py` applied to input/output
   tokens (and escalation minutes). Test:
   `test_otel_negative_tokens_clamped`.

3. `unpriced_models` lost through the ledger round-trip. The importer
   collected the flagged estimate correctly, but `ledger_from_tracker`
   dropped it, so the CLI path (`load -> ledger -> tracker -> pnl`)
   could never surface it. Fix: `ledger_from_tracker` now serializes
   `unpriced_models`; `tracker_from_ledger` restores it; same for
   `policy.export_ledger`. Test:
   `test_otel_unpriced_models_survive_ledger_roundtrip`.

4. `tool_latency_ms` computed then dropped. The importer summed real
   span durations into attempt metadata, but `LEDGER_ATTEMPT_KEYS`
   excluded it, so every ledger export silently discarded the real
   latency evidence (trace B had 5,362 ms of it). Fix: added the key to
   `LEDGER_ATTEMPT_KEYS`, to `policy.export_ledger`'s tuple (kept in
   sync per the docstring rule), and initialized it to 0.0 in
   `Tracker.start_attempt` so the key always exists. Test:
   `test_otel_tool_latency_preserved_in_ledger`.

### (b) Pricing gap

5. `deepseek-v3.2` is not in `MODEL_PRICES`. The fallback estimate
   (1.00/3.00 per 1M) applied correctly and the model is now flagged in
   `unpriced_models` end to end. NOT added to `MODEL_PRICES`: no verified
   vendor price exists and inventing one would violate the
   flagged-estimate rule. Disposition: mechanism verified working, no
   price added.

### (c) Known limitations, documented

6. Any ERROR span marks the whole attempt failed, even when a retry
   recovered it (trace A retried successfully, still failed=True).
   The escape hatch exists: set `agentpnl.success=true` on the final
   span. Documented as intended behavior, not changed.

7. Retry-path (waste) marking is attempt-global, not branch-local.
   Under parallel branches, productive later spans are counted as waste:
   in trace B the fan-in merge step ($0.019, 5,080 tokens) and in trace A
   the post-recovery summarize/audit steps land in `waste_tokens`.
   The flat event schema has no branch concept; fixing would need one.

8. A span with usage tokens but no model attribute (`llm.untracked`)
   is silently skipped: no event, no warning. Documented.

9. Missing `endTimeUnixNano` is handled (latency defaults to 0, no
   crash). Verified working, no change needed.

## Economic insight per trace

Trace A: the 3-minute human escalation ($3.51) is 98.5% of the
fully-loaded $3.57 attempt cost; the agent's own model and tool spend
($0.06) is a rounding error next to the human in the loop. The
refund_api failure's retry loop made model spend 1.39x a clean run
($0.047 vs $0.034) and put 42% of all tokens (4,770 of 11,290) on the
retry path.

Trace B: the dead payment branch burned 44% of the attempt's total cost
($0.024 of $0.055) for zero terminal value: grok-4's two failed attempts
alone were 37% of spend. Yield ratio reads 56%, but it overstates waste
under concurrency: the productive fan-in merge step is counted as
retry-path waste because the flag is attempt-global (limitation 7).
