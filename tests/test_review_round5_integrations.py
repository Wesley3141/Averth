"""Regression tests for review round 5 integration findings.

Covers averth/integrations/openai.py (streaming, async refusal, Responses
API cached tokens) and averth/integrations/langchain.py (BudgetBreach
surfacing, concurrent-run refusal, ghost run_id, foreign-attempt
protection).

Fakes/doubles only: no network, no openai package, no langchain package.
Run with: .venv/bin/python -m pytest tests/test_review_round5_integrations.py -q
"""

import warnings
from types import SimpleNamespace

import pytest

from averth import Tracker
from averth.integrations import AverthCallbackHandler, wrap_openai_client


# ---------------------------------------------------------------------------
# OpenAI fakes
# ---------------------------------------------------------------------------

class _Usage:
    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)


def _stream_chat_client(chunks):
    """Fake client whose chat.completions.create returns an iterator of chunks."""
    class _Completions:
        def create(self, **kwargs):
            return iter(chunks)

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    return SimpleNamespace(chat=_Chat())


def _async_chat_client():
    """Fake client whose chat.completions.create returns a coroutine."""
    class _Completions:
        def create(self, **kwargs):
            async def _coro():
                return SimpleNamespace(
                    model=kwargs.get("model"),
                    usage=_Usage(prompt_tokens=500, completion_tokens=100))
            return _coro()

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    return SimpleNamespace(chat=_Chat())


def _responses_client(usage):
    class _Responses:
        def create(self, **kwargs):
            return SimpleNamespace(model=kwargs.get("model"), usage=usage)

    return SimpleNamespace(responses=_Responses())


# ---------------------------------------------------------------------------
# OpenAI: streaming (C1)
# ---------------------------------------------------------------------------

def test_stream_with_usage_chunk_logs_real_tokens_not_zero():
    tracker = Tracker("stream-agent")
    chunks = [
        SimpleNamespace(delta="hello "),
        SimpleNamespace(delta="world"),
        SimpleNamespace(
            usage=_Usage(prompt_tokens=500, completion_tokens=100)),
    ]
    wrapped = wrap_openai_client(_stream_chat_client(chunks), tracker)
    tracker.start_attempt(case_id="S-1")
    stream = wrapped.chat.completions.create(
        model="gpt-5.6-mini", messages=[], stream=True,
        stream_options={"include_usage": True})
    seen = list(stream)  # consume exactly like a real user would
    assert [c.delta for c in seen[:2]] == ["hello ", "world"]  # passthrough
    tracker.end_attempt(success=True)
    # openai:gpt-5.6-mini = (0.30, 1.20) per 1M
    expected = 500 / 1e6 * 0.30 + 100 / 1e6 * 1.20
    a = tracker.attempts[0]
    assert a["model"] == pytest.approx(expected)
    assert a["model"] > 0
    assert (a["steps"][0]["in"], a["steps"][0]["out"]) == (500, 100)
    assert tracker.missing_usage == set()


def test_stream_without_usage_logs_nothing_and_flags_missing_usage():
    tracker = Tracker("stream-agent")
    chunks = [SimpleNamespace(delta="a"), SimpleNamespace(delta="b")]
    wrapped = wrap_openai_client(_stream_chat_client(chunks), tracker)
    tracker.start_attempt(case_id="S-2")
    list(wrapped.chat.completions.create(model="gpt-5.6-mini", messages=[],
                                         stream=True))
    tracker.end_attempt(success=True)
    a = tracker.attempts[0]
    # No fake $0 step: nothing was measured, so nothing is logged.
    assert a["model"] == 0
    assert a["steps"] == []
    assert "openai:gpt-5.6-mini" in tracker.missing_usage
    assert "openai:gpt-5.6-mini" in tracker.pnl()["missing_usage_models"]


# ---------------------------------------------------------------------------
# OpenAI: async refusal (H1)
# ---------------------------------------------------------------------------

def test_async_client_raises_loudly_with_zero_steps_logged():
    tracker = Tracker("async-agent")
    wrapped = wrap_openai_client(_async_chat_client(), tracker)
    tracker.start_attempt()
    with pytest.raises(TypeError, match="async"):
        wrapped.chat.completions.create(model="gpt-5.6-mini", messages=[])
    # Refused before logging anything: no phantom $0 step.
    assert tracker._cur["steps"] == []
    assert tracker._cur["model"] == 0.0
    tracker.end_attempt(success=True)
    assert tracker.pnl()["attempts"] == 1


# ---------------------------------------------------------------------------
# OpenAI: Responses API cached tokens (H2)
# ---------------------------------------------------------------------------

def test_responses_cached_tokens_priced_at_cache_rate():
    tracker = Tracker("responses-agent")
    usage = _Usage(input_tokens=1000, output_tokens=150,
                   input_tokens_details=_Usage(cached_tokens=400))
    wrapped = wrap_openai_client(_responses_client(usage), tracker)
    tracker.start_attempt()
    wrapped.responses.create(model="gpt-5-nano", input="hi")
    tracker.end_attempt(success=True)
    a = tracker.attempts[0]
    assert a["cached_tokens"] == 400
    assert a["cache_savings"] > 0
    # openai:gpt-5-nano = (0.05, 0.40) per 1M; cached input at 10% rate
    expected = (600 / 1e6 * 0.05) + (400 / 1e6 * 0.05 * 0.10) \
        + (150 / 1e6 * 0.40)
    assert a["model"] == pytest.approx(expected)
    assert a["cache_savings"] == pytest.approx(400 / 1e6 * 0.05 * 0.90)


# ---------------------------------------------------------------------------
# LangChain doubles
# ---------------------------------------------------------------------------

def _llm_response(in_tok, out_tok):
    return SimpleNamespace(
        llm_output={"token_usage": {"prompt_tokens": in_tok,
                                    "completion_tokens": out_tok}})


def _run_chain_with_llm(handler, tracker, model="gpt-5.6-mini",
                        in_tok=1000, out_tok=200, case_id="C-1",
                        run_id="r-chain"):
    handler.on_chain_start({}, {"case_id": case_id}, run_id=run_id)
    handler.on_llm_start({"kwargs": {"model_name": model}}, ["q"],
                         run_id="r-llm")
    handler.on_llm_end(_llm_response(in_tok, out_tok), run_id="r-llm")


# ---------------------------------------------------------------------------
# LangChain: BudgetBreach surfacing (H1)
# ---------------------------------------------------------------------------

def test_budget_breach_without_on_breach_warns_and_records_attempt():
    tracker = Tracker("budget-agent", budget_per_success=0.0)
    h = AverthCallbackHandler(tracker)
    _run_chain_with_llm(h, tracker)
    with pytest.warns(UserWarning, match="BudgetBreach"):
        h.on_chain_end({}, run_id="r-chain")
    # The breach cannot propagate (LangChain swallows handler exceptions),
    # but the attempt itself is recorded and tracker state is clean.
    assert tracker.pnl()["attempts"] == 1
    assert tracker._cur is None


def test_budget_breach_with_on_breach_callback_fires_without_warning():
    fired = []
    tracker = Tracker("budget-agent", budget_per_success=0.0,
                      on_breach=lambda attempt, breach: fired.append(breach))
    h = AverthCallbackHandler(tracker)
    _run_chain_with_llm(h, tracker)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning becomes a test failure
        h.on_chain_end({}, run_id="r-chain")
    assert len(fired) == 1
    assert tracker.pnl()["attempts"] == 1


# ---------------------------------------------------------------------------
# LangChain: concurrent top-level runs (H2)
# ---------------------------------------------------------------------------

def test_second_top_level_chain_start_raises_refusing_to_merge():
    tracker = Tracker("concurrent-agent")
    h = AverthCallbackHandler(tracker)
    h.on_chain_start({}, {"case_id": "A"}, run_id="cA")
    with pytest.raises(RuntimeError, match="one run at a time"):
        h.on_chain_start({}, {"case_id": "B"}, run_id="cB")
    # First run's state is untouched: still open under its own case_id.
    assert h._chain_stack == ["cA"]
    assert tracker._cur is not None
    assert tracker._cur["case_id"] == "A"
    h.on_chain_end({}, run_id="cA")
    assert tracker.pnl()["attempts"] == 1
    assert tracker.attempts[0]["case_id"] == "A"


def test_nested_chain_with_parent_run_id_does_not_raise():
    tracker = Tracker("nested-agent")
    h = AverthCallbackHandler(tracker)
    h.on_chain_start({}, {"case_id": "N-1"}, run_id="cA")
    # A legitimate nested sub-chain carries its parent's run_id: allowed.
    h.on_chain_start({}, {}, run_id="cB", parent_run_id="cA")
    h.on_chain_end({}, run_id="cB")
    h.on_chain_end({}, run_id="cA")
    assert tracker.pnl()["attempts"] == 1


def test_langgraph_reused_run_id_does_not_raise():
    tracker = Tracker("langgraph-agent")
    h = AverthCallbackHandler(tracker)
    h.on_chain_start({}, {"case_id": "LG-1"}, run_id="r-root")
    h.on_chain_start({}, {}, run_id="r-root", parent_run_id="r-root")
    h.on_chain_end({}, run_id="r-root", parent_run_id="r-root")
    h.on_chain_end({}, run_id="r-root")
    assert tracker.pnl()["attempts"] == 1


# ---------------------------------------------------------------------------
# LangChain: ghost run_id (H3)
# ---------------------------------------------------------------------------

def test_ghost_chain_end_does_not_close_attempt_early():
    tracker = Tracker("ghost-agent")
    h = AverthCallbackHandler(tracker)
    h.on_chain_start({}, {"case_id": "X"}, run_id="cX")
    h.on_llm_start({"kwargs": {"model_name": "gpt-5.6-mini"}}, ["q"],
                   run_id="r-llm")
    h.on_llm_end(_llm_response(1000, 200), run_id="r-llm")
    h.on_chain_end({}, run_id="ghost")  # unknown run_id: must be ignored
    assert tracker._cur is not None
    assert h._chain_stack == ["cX"]
    # Later spend still lands in the still-open attempt.
    h.on_tool_start({"name": "web_search"}, "{}", run_id="r-tool")
    h.on_tool_end("results", run_id="r-tool")
    h.on_chain_end({}, run_id="cX")
    assert tracker.pnl()["attempts"] == 1
    a = tracker.attempts[0]
    assert a["model"] > 0
    assert a["tools"] == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# LangChain: handler must not close a foreign attempt (H4)
# ---------------------------------------------------------------------------

def test_handler_does_not_close_manually_opened_attempt():
    tracker = Tracker("manual-agent")
    h = AverthCallbackHandler(tracker)
    tracker.start_attempt(case_id="manual")
    h.on_chain_start({}, {}, run_id="c1")  # handler must not open/close
    h.on_llm_start({"kwargs": {"model_name": "gpt-5.6-mini"}}, ["q"],
                   run_id="r-llm")
    h.on_llm_end(_llm_response(1000, 200), run_id="r-llm")
    h.on_chain_end({}, run_id="c1")
    # Still open, under the user's case_id, with the chain's spend metered.
    assert tracker._cur is not None
    assert tracker._cur["case_id"] == "manual"
    assert tracker._cur["model"] > 0
    tracker.end_attempt(success=True)
    assert tracker.pnl()["attempts"] == 1
    assert tracker.attempts[0]["case_id"] == "manual"


def test_handler_opened_attempt_still_closes_normally():
    tracker = Tracker("auto-agent")
    h = AverthCallbackHandler(tracker)
    _run_chain_with_llm(h, tracker)
    h.on_chain_end({}, run_id="r-chain")
    assert tracker._cur is None
    assert tracker.pnl()["attempts"] == 1
    assert tracker.pnl()["successes"] == 1
