# Hostile review — averth/integrations/openai.py (pass 2)

Reviewer posture: brutal. Every finding below was verified by running code
against fake duck-typed clients in `~/workspace/averth` (package import,
no `openai` package installed — `openai` not in `sys.modules` after import).
OpenAI SDK type shapes cross-checked against openai 3.22.1 vendored in
`validation-traces/live-langgraph-agent/.venv`. File:line refs are to
`averth/integrations/openai.py` (176 lines) unless noted.

Existing tests (`tests/test_integrations.py`, `OpenAIWrapperTest`) cover:
priced-model capture, responses-API field names, unknown-model estimate
fallback, client non-mutation. They do NOT cover streaming, async,
cached tokens on the Responses API, error paths, or retries — which is
where the bugs below live.

## What holds up (verified, not just read)

- **No double-counting on retries.** SDK-internal retries happen inside one
  `create()` invocation → one `_capture`. User-level retry-after-failure:
  the failed call raises *before* `_capture` runs (zero steps logged), the
  successful retry logs exactly one step. Verified: 2 `create` calls →
  1 step, cost exactly one success ($0.00027 for 500/100 on gpt-5.6-mini).
- **Degrades gracefully without the OpenAI package.** No module-level
  `import openai` (verified in source and via `sys.modules`); the client
  is purely duck-typed and attribute access is lazy (properties only touch
  `client.chat` / `client.responses` on access). Works with hand-rolled
  fakes. A client lacking `.chat` raises `AttributeError` on access —
  loud, not silent.
- **Error paths fail loud.** `create()` raising (API 500, timeout) propagates
  to the caller unchanged and logs zero steps — correct, since a failed
  call has no usage to record. `_capture` failures (e.g. tracker used
  without `start_attempt()`) raise `RuntimeError` from `tracker._req()`
  (`tracker.py:375`) — loud. The `except KeyError` in `_capture` only
  catches the pricing-table miss (raised as `KeyError` by
  `log_model_call`, `tracker.py:183-185`); `_check_nonneg_int` raises
  `ValueError`/`TypeError`, which propagate. No silent misrouting found.
- **Happy-path math is exact.** Chat completion 500 in / 100 out /
  200 cached on `openai:gpt-5.6-mini` (0.30, 1.20) → $0.000216, matching
  hand calc `(500-200)/1e6*0.30 + 200/1e6*0.30*0.10 + 100/1e6*1.20`;
  `cache_savings` correct. Unknown model → `estimated_model_cost`
  (1.00, 3.00) → flagged in `pnl()["unpriced_models"]`, exactly as the
  module docstring promises. Dict-style usage objects work; positional
  `model=` falls back to `resp.model` correctly; `usage=None` logs an
  honest 0/0 step.
- **Security:** `time` + `averth.pricing` imports only — zero network
  surface, no secrets, nothing user-controlled rendered anywhere.
- **Hardcoded values:** none in this file (all pricing via `pricing.py`).

---

## CRITICAL

### C1. `stream=True` calls silently record $0.00 spend
`openai.py:98-104` (`_CreateMethod.__call__` → `_capture`, `openai.py:76-89`).

With `stream=True` the SDK returns a `Stream` iterator *immediately*;
per-chunk usage does not exist on it (usage arrives, if at all, in the
final chunk and only when `stream_options={"include_usage": True}` is set).
`_capture` does `getattr(resp, "usage", None)` → `None` →
`_usage_tokens(None)` → `(0, 0)` → `log_model_call(provider, model, 0, 0)`.

Verified with a fake Stream (no `.usage`, consumed via `list()` like a
real user would):
```
STREAMED call logged tokens in/out: 0 0 cost: 0.0
```
The attempt really burned tokens; the ledger says $0.00. This is wrong
dollar figures shown to users via silent undercounting, on a *realistic*
input — streaming is the default UX in agentic workloads, exactly the
workloads Averth meters. It also contradicts the module docstring
("chat.completions.create and responses.create calls capture model and
token usage into a Tracker", `openai.py:1-17`): for streamed calls the
wrapper captures the model and *zero* usage, with no warning.

Fix direction: detect a stream/async-iterator return and either wrap it to
accumulate usage from the terminal chunk (when `include_usage` is on) or
raise/log loudly that streamed calls are not metered. Silently writing
$0.00 is the one unacceptable option.

## HIGH

### H1. Async clients get a phantom $0 entry; real usage is never recorded
`openai.py:98-104`.

`_CreateMethod.__call__` is synchronous. Wrapping `AsyncOpenAI`, the call
`self._create_fn(*args, **kwargs)` returns a *coroutine*; `_capture` runs
immediately on the coroutine object (`getattr(coro, "usage", None)` →
`None`) and logs `(model, 0, 0)` → $0.00. The caller then awaits the
coroutine and gets the real response — whose usage the wrapper never sees.

Verified:
```
ASYNC logged in/out/cost: 0 0 0.0   (real response carried 500/100)
```
Net effect per async call: one phantom zero-cost step in the ledger *and*
the actual spend invisible. The docstring promises "Wraps an OpenAI
client instance (duck-typed, no openai import at module level)" with no
async exclusion (`openai.py:173-180`), so an `AsyncOpenAI` user following
the docs gets silently corrupt ledgers. Fix: detect coroutine returns and
either await-chain properly (return an async wrapper) or raise a loud
`TypeError` refusing async clients.

### H2. Responses API cached tokens silently dropped → cost overstated
`openai.py:55-69` (`_usage_cached_tokens`).

The helper only reads `usage.prompt_tokens_details.cached_tokens` — the
Chat Completions shape. The Responses API reports prompt-cache reads at
`usage.input_tokens_details.cached_tokens` (verified in openai 3.22.1
`types/responses/response_usage.py:14,37`: `InputTokensDetails.cached_tokens`).
Cached input tokens are therefore priced at the *full* input rate instead
of the 10% cache-read rate, and `cache_savings` is understated.

Verified with a Responses-shaped fake (`input_tokens=1000`,
`input_tokens_details.cached_tokens=400`):
```
responses cached recorded: 0 (API reported 400)
```
For a responses-API agent with heavy prompt caching this overstates model
spend by up to ~9% of cached input cost — wrong dollar figures, silent.
Fix: read `input_tokens_details` as a fallback (same `_usage_field`
first-non-None pattern already used for the token counts).

## MEDIUM

### M1. `total_tokens`-only usage shapes silently log $0.00
`openai.py:46-49` (`_usage_tokens`).

`_usage_field` only looks for `prompt_tokens`/`input_tokens` and
`completion_tokens`/`output_tokens`. Some OpenAI-compatible endpoints and
proxies return only `total_tokens`. Verified: `usage.total_tokens=600` →
logged `in=0, out=0, cost=$0.00`, no flag. The real OpenAI API always
returns the split, so this bites exactly the duck-typed non-OpenAI
backends the duck-typed design invites. At minimum flag the step
(`unpriced`-style marker) instead of writing a confident $0.00.

## LOW

### L1. Latency timed then discarded
`openai.py:101-102`: `_ = time.time() - started  # latency observed;
spend is the Phase-0 record`. The measurement is dead code with an
explanatory comment, and the module docstring ("Calls are timed around
the SDK invocation", `openai.py:13`) overpromises to a reader who expects
latency to be recorded. Either record it on the step or stop timing.

### L2. Double-wrapping double-counts
Wrapping an already-wrapped client (`wrap_openai_client(wrapped, t)`)
logs 2 steps for 1 API call (verified). Pure user error, but a cheap
marker attribute (e.g. `_averth_wrapped`) with a loud refusal would make
it impossible.

### L3. `_int_or_zero` silently coerces garbage to 0
`openai.py:23-28`: `int("abc")` → `ValueError` → 0; a dict → `TypeError`
→ 0. Malformed upstream usage data becomes a confident 0 instead of a
loud error. Downstream `_check_nonneg_int` can't see the difference.
Unlikely with the real SDK; still a silent-corruption shape.

---

## Rubric sweep (no finding)

- **Staleness:** no frozen prices, thresholds, or date logic in this file.
- **Boundary edges:** `cached > in_tok` clamped in tracker; zero-token
  steps price honestly at $0.00; single-attempt ledgers fine.
- **Injection/HTML:** N/A — no rendering in this module.
- **Dead code:** none besides L1.

## Injection note (per rubric security note)

No web use in this review; no injected directives encountered.
