# Hostile review — averth/integrations/langchain.py (201 lines)
Reviewer: subagent (pass 2). Date: 2026-10-02. Scope: `averth/averth/integrations/langchain.py` ONLY
(the package is nested: `~/workspace/averth/averth/`, not `~/workspace/averth/integrations/`).

Method: every finding below was verified by running code, not by reading.
Simulations ran against the REAL `langchain_core` 1.6.6 base class
(`validation-traces/live-langgraph-agent/.venv`) and against a langchain-free
interpreter. Key ground truths established from the installed langchain-core
source (`callbacks/manager.py::handle_event`, `callbacks/base.py`):

- Chat models: `on_chat_model_start` default raises `NotImplementedError` and the
  manager falls back to `on_llm_start`. The handler's model-capture path works
  for chat models. NOT a finding.
- `handle_event` wraps EVERY handler call in try/except: handler exceptions are
  swallowed into `logger.warning("Error in %s.%s callback ...")` UNLESS
  `handler.raise_error` is True. `AverthCallbackHandler` leaves the default
  (`raise_error=False`; verified on a live instance). So the host app can never
  crash from these callbacks — good — but see H1.

## Severity counts
- CRITICAL: 0
- HIGH: 4
- MEDIUM: 5
- LOW: 3

---

## HIGH findings

### H1 — BudgetBreach is silently swallowed by LangChain's dispatch; the kill-switch story dies in this integration (langchain.py: `_chain_done` → `tracker.end_attempt`)
`Tracker.end_attempt` raises `BudgetBreach` when `total_cost > budget_per_success`
and no `on_breach` callback is set (tracker.py). `_chain_done`
(langchain.py:120-133) calls `end_attempt` with no try/except. Verified live
through langchain-core's real `handle_event` dispatch:

```
"Error in AverthCallbackHandler.on_chain_end callback:
 BudgetBreach('sim3: case cost $0.00 exceeded budget $0.00')"
```

The exception never reaches the host app (langchain swallows it) and never
reaches the averth user either — it becomes one `logger.warning` line. The
attempt itself IS recorded correctly (`_cur` is cleared before the raise in
`end_attempt`, verified: attempts==1 after the swallow), so no dollar
corruption; but the entire governance contract ("exceed per-outcome budget
and the callback fires — downgrade the model, require approval, or kill the
run", `averth/__init__.py` docstring) silently degrades to a log line when the
Tracker is wired through this handler. Neither the module docstring, the class
docstring, nor any comment mentions budgets at all. A buyer running the
diagnostic with a budget set would believe enforcement is live when it is not.
Fix options: catch `BudgetBreach` in `_chain_done` and re-surface it (e.g.
stash on the handler / call `tracker.on_breach` if set), or document loudly
that budget enforcement does not propagate through LangChain callbacks.

### H2 — One shared handler + concurrent runs = spend merged into one attempt, one case_id silently lost (langchain.py:103-119, `self._chain_stack`)
`_chain_stack`, `_llm_runs`, `_tool_runs` are per-handler-instance state with no
isolation per run. Simulated two interleaved chains on one handler (the natural
`agent.batch(inputs, config={"callbacks": [handler]})` pattern):

```
on_chain_start(case A, run cA) -> attempt 1 opens (case_id "A")
on_chain_start(case B, run cB) -> stack [cA, cB], no new attempt
... B's LLM events logged into attempt 1 ...
on_chain_end(cA) -> removes cA, stack [cB] non-empty: attempt NOT closed
on_chain_end(cB) -> stack empty: attempt 1 closed
```

Result: `attempts == 1`, `case_ids == ["A"]`. Run B's model/tool spend is
attributed to run A's attempt; B's case_id vanishes. Silent misattribution of
dollars across business cases — the exact thing the meter exists to prevent.
The module docstring claims "one graph run maps to one attempt", which is
false under concurrency. No docstring, comment, or README line warns that a
handler instance is single-run/concurrency-unsafe. Fix: key in-flight state by
outermost run_id (dict of per-run stacks) or document "one handler instance
per concurrent run; do not share across batch".

### H3 — A chain end/error for an UNKNOWN run_id pops a real stack entry, closes the attempt early, and silently drops all later spend (langchain.py:124-129)
```python
if run_id in self._chain_stack:
    self._chain_stack.remove(run_id)
elif self._chain_stack:
    self._chain_stack.pop()          # <-- hazard
```
The `elif` branch fires only when `run_id` was never started under this
handler — there is no legitimate case (LangGraph's reused run_id IS in the
stack, so the depth-counting comment does not justify this branch). Verified
trace: stack `[cX]` (attempt open, LLM logged), then `on_chain_end(run_id="ghost")`
→ pops `cX` → stack empty → `end_attempt` runs early. Subsequent
`on_tool_start/on_tool_end` find `_cur is None` and are dropped silently
(`tools == 0.0`), and the real `on_chain_end(cX)` becomes a no-op. Triggers in
reality: handler attached mid-run, LangChain emitting ends for runs whose
starts were filtered/ignored, or any run_id mismatch. One stray event
fractures the whole attempt's economics with zero signal. Fix: delete the
`elif` branch — ignore unknown run_ids entirely.

### H4 — The handler closes an attempt it did not open (langchain.py:114-119, 133)
`on_chain_start` skips `start_attempt` when `tracker._cur` is not None (avoids
the RuntimeError), but still pushes onto `_chain_stack`. On `on_chain_end` the
stack empties and `_chain_done` calls `tracker.end_attempt(...)` — closing the
user's manually-managed attempt. Verified: user opens `start_attempt(case_id="manual")`,
attaches handler with `auto_attempt=True`; the chain's LLM cost lands in the
manual attempt and the chain end closes it (`tracker._cur` → None). Mixed
manual + callback usage is plausible (user opens the attempt, uses callbacks
only for LLM/tool metering). The outcome (whose attempt got closed, and its
`success` flag — set from the chain's outcome, not the user's) is surprising
and undocumented. Fix: track whether THIS handler opened the attempt
(e.g. a flag set in `on_chain_start`) and only close what it opened; document
the interaction.

---

## MEDIUM findings

### M1 — Spend outside any attempt is dropped with zero signal (langchain.py:140-148, 160-164)
`on_llm_end` / `on_tool_end` / `on_llm_error` / `on_tool_error` all no-op when
`tracker._cur is None`. The module docstring says "LLM and tool callbacks in
between record spend" without qualification. Realistic trigger: direct
`llm.invoke(..., config={"callbacks": [handler]})` with no chain wrapper, or
attaching callbacks but forgetting `auto_attempt`. Every token then vanishes
silently — the worst failure mode for a meter is to under-report with no
warning. At minimum log a warning (or count dropped events on the handler).

### M2 — Docstring says the base class is "imported lazily"; it is imported at module load (langchain.py:15-18)
"The base class is imported lazily" — false. The import happens at module
import time inside try/except (an *optional* import, not a lazy one).
Docs-vs-code; the claim matters because "lazy" implies importing
`averth.integrations.langchain` has no import-time cost/failure modes, which
is not what the code does.

### M3 — Class docstring overclaims: "chain error closes it as failed" (langchain.py:92-97)
Only the OUTERMOST chain error fails the attempt; nested chain errors are
absorbed (verified by `test_nested_chain_error_does_not_fail_attempt_early`).
The class docstring states the unqualified version; only the module docstring's
LangGraph paragraph hints at the real rule. A reader wiring error alerts off
"chain error closes it as failed" will mispredict behavior for nested chains.

### M4 — Dead data: `time.time()` recorded per tool run, never read (langchain.py:158-159)
`self._tool_runs[run_id] = {"name": ..., "started": time.time()}` — `started`
is never consumed by `on_tool_end`/`on_tool_error` (no latency is logged to
the tracker; `tool_latency_ms` stays 0.0). Dead field, misleading to the next
reader (implies latency tracking exists). Either wire it up or delete it.

### M5 — Unmatched/duplicate `on_llm_end` books a spurious "unknown:unknown" estimate line (langchain.py:140-148)
`on_llm_end` with no matching `on_llm_start` (handler attached mid-run, or a
duplicate end event) pops `None`, defaults model/provider to `"unknown"`, and
— since `"unknown:unknown"` is not in `MODEL_PRICES` — records an ESTIMATE
cost line via `log_model_cost_estimate` and adds `"unknown:unknown"` to
`unpriced_models`. Verified: a duplicate end for a priced model produced
$0.000172 instead of $0.000042 (priced line + spurious estimate line). The
spend is at least flagged, but an event the handler cannot attribute should
not invent a cost line; warn-and-skip is safer.

---

## LOW findings

### L1 — `_guess_provider` is a frozen substring heuristic (langchain.py:59-71)
`"gpt" in m` misfires on adversarial names (`"gpt-claude-bridge"` →
"openai"); current non-gpt OpenAI models (`o3`, `o4-mini`) → `"unknown"` →
estimate fallback. The fallback is flagged in `unpriced_models`, so dollars
stay honest, but provider attribution silently degrades as vendors rename
models. Consider matching on known prefixes or documenting the heuristic's
limits.

### L2 — `run_id=None` collisions in `_llm_runs`/`_tool_runs` (langchain.py:136-138, 157-159)
Two starts with `run_id=None` overwrite each other under the `None` key; the
first entry's model info is lost. Pathological (LangChain always passes UUIDs),
but the dict silently accepts it.

### L3 — `on_tool_error` without a prior start books `TOOL_PRICES["default"]` ($0.002) under name `"unknown"` (langchain.py:166-174)
Defensible (the comment explains the metering rationale), but an error event
with no matching start still creates spend out of thin air. Consistent with
M5's warn-and-skip suggestion.

---

## What verified CLEAN (do not "fix")
- Callback → Tracker mapping for the success path, LLM retry path, and tool
  error path: hand-computed dollar figures match to the cent (retry-path test:
  model $0.00081 = terminal $0.00054 + retry-path $0.00027; retry tool $0.005;
  yield 2/3; `top_retry_reasons == [("llm_error: RuntimeError", 1)]`).
- Chat-model support: `on_chat_model_start` → `NotImplementedError` → manager
  falls back to `on_llm_start`; verified in langchain-core 1.6.6 source.
- Host-app safety: langchain-core's `handle_event` swallows ALL handler
  exceptions (`raise_error` defaults False, verified on live instance) — the
  handler needs no try/except of its own, and no callback path can crash the
  host app. (This is also the mechanism behind H1.)
- Lazy/optional import: on a langchain-free interpreter `BaseCallbackHandler`
  falls back to `object`, handler instantiates and functions fully; all 20
  tests in `tests/test_integrations.py` pass.
- Retry reasons use `type(error).__name__` only — no prompt/response content
  reaches the ledger. No network imports (`time`, `averth.pricing`, optional
  langchain only). `AgentPNLCallbackHandler` alias works.
- `_token_usage` clamps negatives/non-numerics; `_model_from_serialized` and
  `_tool_name` degrade to `"unknown"` instead of raising; `BudgetBreach` does
  not corrupt tracker state when swallowed (attempt recorded, `_cur` cleared).
- Nested-chain depth counting for LangGraph's reused run_id is balanced
  (verified by existing tests + simulation); `auto_attempt=False` fully
  disables attempt management (verified).

## Suggested fix priority
1. Delete the `elif self._chain_stack: self._chain_stack.pop()` branch (H3) —
   one-line, pure hazard.
2. Decide the BudgetBreach story for this integration (H1) — document or
   re-surface; do not leave it as a swallowed warning.
3. Per-run state isolation or a loud single-run-only contract (H2).
4. Track handler-opened attempts; don't close foreign ones (H4).
5. Warn (not silent drop) when events arrive with no active attempt (M1, M5);
   fix the "imported lazily" wording (M2); drop or use `started` (M4).
