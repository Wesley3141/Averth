# SOURCES.md — provenance of the live-langgraph-agent validation traces

Generated live on 2026-09-30 by running
`validation-traces/live-langgraph-agent/live_agent.py`
(venv python at `validation-traces/live-langgraph-agent/.venv`)
against real public read-only HTTP APIs. No numbers were hand-written:
token counts, latencies, tool outcomes, retries, and failures all come
from the actual runs. Run log: `run_log.txt`.

## Agent shape

A real LangGraph `StateGraph`, instrumented with the 3-line integration:

    tracker = Tracker("live-langgraph-validation", budget_per_success=1.00)
    handler = AverthCallbackHandler(tracker)
    app.invoke(state, config={"callbacks": [handler]})

Graph: `plan` (LLM) -> fan-out via `Send` to `search_ddg` and
`github_lookup` in parallel -> `aggregate` (fan-in) -> `fetch_flaky`
-> conditional retry loop (max 3 attempts) -> `report` (LLM, streamed)
-> END. On exhausted retries the node raises, the graph errors, and the
attempt is marked failed.

## Real external tools (read-only, no keys)

- `web_search` -> `https://api.duckduckgo.com/?q=...&format=json`
  (DuckDuckGo instant-answer API)
- `github_lookup` -> `https://api.github.com/search/repositories`
  (unauthenticated public repo search)
- `flaky_fetch` -> `https://httpbin.org/status/{code}`
  (deliberate HTTP 500s for the flaky/doomed variants)

## The model situation (read this before citing token/model costs)

No model API key and no provider credentials exist in this environment,
so orchestration uses `stub_model.py`: a deterministic local
`BaseChatModel` stand-in. It makes no network calls. Token counts are
REAL measurements: tiktoken `cl100k_base` over the actual prompt strings
sent and the actual completion strings produced (verified end-to-end in
`probe_streaming.py`, including the streaming path, which delivers real
`token_usage` to the handler's `on_llm_end`).

Cost consequence: the handler sees model name `StubChatModel`, provider
`unknown`, which is absent from `pricing.MODEL_PRICES`, so every model
call flows through the documented estimate fallback
(`pricing.estimated_model_cost`, 1.00/3.00 per 1M tokens) and is flagged
in `pnl()["unpriced_models"]` as `unknown:StubChatModel`. Model spend in
these traces is therefore a labeled estimate, never a vendor price.

## Run set (16 runs, one Tracker, one attempt per run)

- 8 `clean` (RUN-01,02,03,07,10,12,14 plus RUN-04): flaky_fetch 200 first try
- 5 `flaky` (RUN-05,06,09,11,15): two genuine HTTP 500s, then 200
- 3 `doomed` (RUN-08,13,16): three genuine HTTP 500s, then the node raises

Genuine unplanned failure: RUN-04 (clean) failed for real when the
network degraded mid-batch — both parallel tools hit read timeouts
(`ReadTimeout` on web_search and github_lookup). It is kept in the
ledger as a real failed attempt, not re-run.

## Files

- `live_agent.py` — the agent and run harness
- `stub_model.py` — deterministic local model stub (see above)
- `ledger.json` — sanitized ledger via `importers.common.ledger_from_tracker`
- `events.jsonl` — EVENT-schema reconstruction of every attempt (144 lines),
  the exact input fed to `averth.cli trace --format jsonl`
- `pnl.json` — in-process `tracker.pnl()` (ground truth for validation)
- `run_log.txt` — per-run variant, wall-clock, outcome
- `cli-report.html` — HTML report produced by the CLI round-trip run
- `validate.py` — zero-hand-fixing validator (exit 0 = all views agree)
- `probe_attempt_boundaries.py`, `probe_streaming.py` — pre-fix behavior probes
- `.venv/` — throwaway environment (langchain-core, langgraph, tiktoken,
  pytest); NOT part of the committed traces
