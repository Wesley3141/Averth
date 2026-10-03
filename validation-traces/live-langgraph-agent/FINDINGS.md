# FINDINGS.md — live LangGraph validation, 2026-09-30

## Per-run-set outcome

16 runs through a real LangGraph graph (plan -> parallel fan-out to
DuckDuckGo + GitHub -> fan-in -> flaky HTTP fetch with graph-level retry
loop -> streamed report), metered by `AverthCallbackHandler` into one
Tracker. Result: **16 attempts, 12 successes, 21 retries, $0.1783 total**,
all from real network calls with real latency, real failures, and real
tiktoken-measured token counts. One run (RUN-04) failed for real on a
network degradation (both parallel tools timed out); it stays in the
ledger as a genuine failed attempt.

`validate.py` passes clean against the archived `events.jsonl` input and
the current `ledger.json`/`pnl.json` snapshots. The snapshots were
regenerated from the archived events after the failed-attempt waste rule
changed. This now checks reproducibility and serialization; it is no longer
an independent in-process comparison. The event stream retains real tool
calls, measured token counts, and recorded outcomes, while model calls use
a deterministic local stub and tool dollars are built-in estimates.

## Issues found

### (a) Integration gap, FIXED — nested chain ends closed the attempt early

`AverthCallbackHandler.on_chain_end` closed the Tracker attempt on ANY
chain end. LangGraph reuses one run_id for a whole graph run and emits a
chain end per node, so the first node end closed the attempt as
"success"; later tool/LLM events were silently dropped or splintered
into extra empty attempts. A 2-node probe produced **2 attempts, 0
events, both "success"** before the fix, 1 attempt after.

Fix (`averth/integrations/langchain.py`): depth-count open chains in
`_chain_stack`; only the outermost chain end/error closes the attempt.
Nested errors no longer fail the attempt either — only the outermost
chain error marks the run failed, so graph-recovered node errors do not
kill the attempt. Verified against the real LangGraph event stream and
kept backward compatible with the stub-driven unit tests.

Tests: `test_nested_chain_end_does_not_close_attempt_early`,
`test_nested_chain_error_does_not_fail_attempt_early`
(`tests/test_integrations.py`).

### (a) Integration gap, FIXED — failed tool calls were metered at $0

`on_tool_error` logged a retry but never recorded the tool call, so a
failed invocation (real network egress, real provider metering)
contributed $0. In this batch 21 of 63 tool invocations failed; the fix
recovered **$0.045 of $0.174 tool spend (26%)** that was previously
invisible. Failed calls are now costed like successes and the retry
marker separately classifies the waste — no double counting, since
`on_tool_end` and `on_tool_error` are mutually exclusive per invocation.

Tests: `test_tool_error_records_tool_cost_and_retry`
(`tests/test_integrations.py`).

### (a) Integration gap, FIXED — ledger export/import dropped the unpriced-models flag

`importers.common.ledger_from_tracker` did not export
`tracker.unpriced_models`, and `tracker_from_ledger` did not restore it,
so a reimported ledger presented estimated model spend as exact vendor
pricing — defeating the "flagged, never hidden" purpose of the estimate
path. Fix: both `ledger_from_tracker` and `policy.export_ledger` now
include `unpriced_models`; `tracker_from_ledger` restores it (`.get`
with default for backward compatibility with older ledgers).

Tests: `test_ledger_roundtrip_preserves_unpriced_models`,
`test_tracker_from_ledger_accepts_legacy_ledger_without_flags`
(`tests/test_importers.py`).

### (c) Environment artifact — no model API available

Token counts are real tiktoken measurements of real strings, but the
"model" is a deterministic local stub, so model spend ($0.0043) flows
through the estimate fallback and is flagged `unknown:StubChatModel`.
Re-run against a real provider to validate vendor-price paths; the
handler's model-name extraction for real providers is covered by unit
tests, not by this live batch.

### (c) Known limitation — parallel-branch thread safety

The two `Send` branches record into one shared attempt from two
threads. CPython's GIL made this safe in practice here (event counts
reconcile exactly: 63 tool events == ledger tool spend / prices), but
`Tracker` has no lock; a lost `+=` update under heavier parallelism
would show up as exactly this kind of event-count vs cost-sum mismatch,
which `validate.py` checks.

### (c) Known limitation — handler sees the stub's class name, not its model field

`_model_from_serialized` falls back to the serialized `name`
(`StubChatModel`) because a custom chat model carries no `model_name`
in kwargs. Correct best-effort behavior for real providers (kwargs
carry the model); custom models get class-name attribution, still
flagged as estimated.

## The economic insight

For this agent shape, **the model is nearly free and the tools are the
entire economy**: $0.174 of $0.178 total cost (97.6%) is external tool
spend — the layer invisible on provider invoices — while 1,794 real
tokens cost $0.0043. Even repriced at frontier vendor rates, the token
bill would stay a fraction of the per-call tool prices, so the economic
lever here is tool-call count and failure rate, not model selection.
The failure rate is the hidden multiplier: one-third of tool
invocations failed (21/63), and before the costing fix those failures
were metered at $0, understating true cost by 26%. Retried runs also
show the yield effect the meter is built to catch: 494 of 1,794 tokens
(27.5%) burned on retry paths, and the streamed report call in every
flaky run landed on the waste path exactly as designed. Wall-clock tells
the same story from the other side: clean runs finished in ~2.2s while
flaky runs stretched to 3.4–35.7s — retries, not tokens, dominate both
cost and latency.

## Full suite

66 passed (`pytest tests/`), up from a 61-test baseline; the 5 new
tests are the ones listed above.
