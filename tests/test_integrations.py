"""Integration tests: run with `python3 -m unittest discover -s tests`.

No langchain, no openai, no network. The LangChain handler is driven
directly with stub dicts/objects; the OpenAI wrapper is exercised against
a fake duck-typed client.
"""

import unittest
from types import SimpleNamespace

from averth import Tracker, pricing
from averth.integrations import AverthCallbackHandler, wrap_openai_client


def llm_response(prompt_tokens, completion_tokens):
    return SimpleNamespace(
        llm_output={"token_usage": {"prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens}})


class LangChainHandlerTest(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker("test-agent")
        self.h = AverthCallbackHandler(self.tracker)

    def run_success_flow(self):
        h = self.h
        h.on_chain_start({}, {"case_id": "C-1"}, run_id="r-chain")
        h.on_llm_start({"kwargs": {"model_name": "claude-sonnet-4-5"}},
                       ["answer this"], run_id="r-llm")
        h.on_llm_end(llm_response(1000, 200), run_id="r-llm")
        h.on_tool_start({"name": "web_search"}, "{}", run_id="r-tool")
        h.on_tool_end("results", run_id="r-tool")
        h.on_chain_end({}, run_id="r-chain")

    def test_successful_chain_records_attempt(self):
        self.run_success_flow()
        self.assertEqual(self.tracker.pnl()["attempts"], 1)
        self.assertEqual(self.tracker.pnl()["successes"], 1)
        self.assertEqual(self.tracker.attempts[0]["case_id"], "C-1")

    def test_llm_cost_captured_with_priced_model(self):
        self.run_success_flow()
        # anthropic:claude-sonnet-4-5 = (3.00, 15.00) per 1M
        expected = 1000 / 1e6 * 3.00 + 200 / 1e6 * 15.00
        self.assertAlmostEqual(self.tracker.attempts[0]["model"], expected)
        self.assertAlmostEqual(
            self.tracker.pnl()["per_model"]["anthropic:claude-sonnet-4-5"],
            expected)

    def test_tool_cost_captured(self):
        self.run_success_flow()
        self.assertAlmostEqual(self.tracker.attempts[0]["tools"], 0.005)

    def test_nested_chain_start_does_not_double_open(self):
        h = self.h
        h.on_chain_start({}, {}, run_id="r-outer")
        # A legitimate nested sub-chain carries its parent's run_id (this is
        # what real LangChain emits); a new run_id with no parent in the
        # stack is treated as a concurrent top-level run and now raises
        # RuntimeError instead of merging spend (see review round 5, H2).
        h.on_chain_start({}, {}, run_id="r-inner", parent_run_id="r-outer")
        h.on_chain_end({}, run_id="r-inner")
        h.on_chain_end({}, run_id="r-outer")
        self.assertEqual(self.tracker.pnl()["attempts"], 1)

    def test_chain_error_fails_attempt(self):
        h = self.h
        h.on_chain_start({}, {}, run_id="r-chain")
        h.on_chain_error(ValueError("boom"), run_id="r-chain")
        p = self.tracker.pnl()
        self.assertEqual(p["attempts"], 1)
        self.assertEqual(p["successes"], 0)

    def test_llm_error_logs_retry(self):
        h = self.h
        h.on_chain_start({}, {}, run_id="r-chain")
        h.on_llm_start({"kwargs": {"model_name": "gpt-5.6-mini"}},
                       ["q"], run_id="r-llm")
        h.on_llm_error(RuntimeError("timeout"), run_id="r-llm")
        h.on_chain_end({}, run_id="r-chain")
        self.assertEqual(self.tracker.pnl()["retries"], 1)

    def test_unknown_model_falls_back_to_estimate(self):
        h = self.h
        h.on_chain_start({}, {}, run_id="r-chain")
        h.on_llm_start({"kwargs": {"model_name": "gpt-9-ultra"}},
                       ["q"], run_id="r-llm")
        h.on_llm_end(llm_response(1000, 200), run_id="r-llm")
        h.on_chain_end({}, run_id="r-chain")
        # fallback prices (1.00, 3.00) per 1M
        expected = 1000 / 1e6 * 1.00 + 200 / 1e6 * 3.00
        self.assertAlmostEqual(self.tracker.attempts[0]["model"], expected)
        p = self.tracker.pnl()
        self.assertEqual(p["unpriced_models"], ["openai:gpt-9-ultra"])

    def test_provider_guessing(self):
        from averth.integrations.langchain import _guess_provider
        self.assertEqual(_guess_provider("gpt-5.6-mini"), "openai")
        self.assertEqual(_guess_provider("claude-opus-4-6"), "anthropic")
        self.assertEqual(_guess_provider("gemini-3-pro"), "google")
        self.assertEqual(_guess_provider("grok-4"), "xai")
        self.assertEqual(_guess_provider("mystery-7b"), "unknown")

    def test_nested_chain_end_does_not_close_attempt_early(self):
        # Real LangGraph reuses one run_id for the whole graph run; a nested
        # node end must not close the attempt, or later tool/LLM events are
        # dropped and the run fragments into several empty attempts.
        h = self.h
        h.on_chain_start({}, {"case_id": "LG-1"}, run_id="r-root")
        h.on_chain_start({}, {}, run_id="r-root", parent_run_id="r-root")
        h.on_llm_start({"kwargs": {"model_name": "gpt-5.6-mini"}},
                       ["q"], run_id="r-llm")
        h.on_llm_end(llm_response(1000, 200), run_id="r-llm")
        h.on_chain_end({}, run_id="r-root", parent_run_id="r-root")  # node done
        # events after the nested end must still land in the same attempt
        h.on_tool_start({"name": "web_search"}, "{}", run_id="r-tool")
        h.on_tool_end("results", run_id="r-tool")
        h.on_chain_end({}, run_id="r-root")  # graph done
        p = self.tracker.pnl()
        self.assertEqual(p["attempts"], 1)
        self.assertEqual(p["successes"], 1)
        a = self.tracker.attempts[0]
        self.assertEqual(a["case_id"], "LG-1")
        self.assertGreater(a["model"], 0)
        self.assertAlmostEqual(a["tools"], 0.005)

    def test_nested_chain_error_does_not_fail_attempt_early(self):
        # A node error the graph recovers from must not fail the attempt;
        # only the outermost chain error marks the run failed.
        h = self.h
        h.on_chain_start({}, {}, run_id="r-root")
        h.on_chain_start({}, {}, run_id="r-node", parent_run_id="r-root")
        h.on_chain_error(ValueError("node blew up"), run_id="r-node",
                         parent_run_id="r-root")
        h.on_chain_end({}, run_id="r-root")
        p = self.tracker.pnl()
        self.assertEqual(p["attempts"], 1)
        self.assertEqual(p["successes"], 1)

    def test_tool_error_records_tool_cost_and_retry(self):
        # A failed tool invocation still consumed the tool (network egress,
        # provider metering): its cost is recorded and the retry classified.
        h = self.h
        h.on_chain_start({}, {}, run_id="r-chain")
        h.on_tool_start({"name": "web_search"}, "{}", run_id="r-tool")
        h.on_tool_error(RuntimeError("upstream 500"), run_id="r-tool")
        h.on_tool_start({"name": "web_search"}, "{}", run_id="r-tool2")
        h.on_tool_end("results", run_id="r-tool2")
        h.on_chain_end({}, run_id="r-chain")
        a = self.tracker.attempts[0]
        self.assertEqual(a["retries"], 1)
        # two real invocations happened: failed + retried
        self.assertAlmostEqual(a["tools"], 0.005 * 2)

    def test_callbacks_without_attempt_do_not_crash(self):
        h = AverthCallbackHandler(Tracker("idle"))
        h.on_llm_end(llm_response(10, 10), run_id="r-x")
        h.on_tool_end("out", run_id="r-x")
        h.on_chain_end({}, run_id="r-x")
        h.on_llm_error(ValueError("x"), run_id="r-x")
        self.assertEqual(h.tracker.pnl()["attempts"], 0)


class PricingEstimateTest(unittest.TestCase):
    def test_estimated_model_cost_math(self):
        self.assertAlmostEqual(
            pricing.estimated_model_cost("openai", "gpt-9-ultra", 1_000_000, 1_000_000),
            4.00)

    def test_log_model_cost_estimate_flags_model(self):
        t = Tracker("t")
        t.start_attempt()
        t.log_model_cost_estimate("openai", "gpt-9-ultra", 0.0016, 1000, 200)
        t.end_attempt(success=True)
        p = t.pnl()
        self.assertAlmostEqual(p["cost_model"], 0.0016)
        self.assertEqual(p["unpriced_models"], ["openai:gpt-9-ultra"])
        self.assertAlmostEqual(p["per_model"]["openai:gpt-9-ultra"], 0.0016)

    def test_pnl_unpriced_models_empty_by_default(self):
        t = Tracker("t")
        t.start_attempt()
        t.log_model_call("openai", "gpt-5.6-mini", 100, 50)
        t.end_attempt(success=True)
        self.assertEqual(t.pnl()["unpriced_models"], [])


# ---- fake OpenAI SDK client (duck-typed) ----
class _FakeUsage:
    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)


class _FakeChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(model=kwargs.get("model"),
                               usage=_FakeUsage(prompt_tokens=500,
                                                completion_tokens=100))


class _FakeChat:
    def __init__(self):
        self.completions = _FakeChatCompletions()


class _FakeResponses:
    def create(self, **kwargs):
        return SimpleNamespace(model=kwargs.get("model"),
                               usage=_FakeUsage(input_tokens=800,
                                                output_tokens=150))


class _FakeClient:
    def __init__(self):
        self.chat = _FakeChat()
        self.responses = _FakeResponses()
        self.api_key = "sk-test"


class OpenAIWrapperTest(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        self.tracker = Tracker("test-agent")
        self.wrapped = wrap_openai_client(self.client, self.tracker)

    def test_chat_completions_captures_priced_model(self):
        self.tracker.start_attempt(case_id="C-7")
        resp = self.wrapped.chat.completions.create(model="gpt-5.6-mini",
                                                    messages=[{"role": "user",
                                                               "content": "hi"}])
        self.assertIsNotNone(resp)
        self.tracker.end_attempt(success=True)
        # openai:gpt-5.6-mini = (0.30, 1.20) per 1M
        expected = 500 / 1e6 * 0.30 + 100 / 1e6 * 1.20
        self.assertAlmostEqual(self.tracker.attempts[0]["model"], expected)
        self.assertEqual(self.tracker.pnl()["unpriced_models"], [])

    def test_responses_api_uses_output_token_fields(self):
        self.tracker.start_attempt()
        self.wrapped.responses.create(model="gpt-5-nano", input="hi")
        self.tracker.end_attempt(success=True)
        # openai:gpt-5-nano = (0.05, 0.40) per 1M; usage.input_tokens/output_tokens
        expected = 800 / 1e6 * 0.05 + 150 / 1e6 * 0.40
        self.assertAlmostEqual(self.tracker.attempts[0]["model"], expected)

    def test_unknown_model_estimate_fallback(self):
        self.tracker.start_attempt()
        self.wrapped.chat.completions.create(model="gpt-9-ultra", messages=[])
        self.tracker.end_attempt(success=True)
        expected = 500 / 1e6 * 1.00 + 100 / 1e6 * 3.00
        self.assertAlmostEqual(self.tracker.attempts[0]["model"], expected)
        self.assertEqual(self.tracker.pnl()["unpriced_models"],
                         ["openai:gpt-9-ultra"])

    def test_original_client_not_mutated(self):
        self.assertIsNot(self.wrapped, self.client)
        self.assertIs(self.client.chat, self.client.chat)  # untouched
        self.assertIsNot(self.wrapped.chat, self.client.chat)
        self.assertIsNot(self.wrapped.responses, self.client.responses)
        self.assertEqual(self.wrapped.api_key, "sk-test")  # passthrough
        self.assertEqual(len(self.client.chat.completions.calls), 0)

    def test_call_still_reaches_underlying_client(self):
        self.tracker.start_attempt()
        self.wrapped.chat.completions.create(model="gpt-5.6-mini", messages=[])
        self.tracker.end_attempt(success=True)
        self.assertEqual(len(self.client.chat.completions.calls), 1)
        self.assertEqual(self.client.chat.completions.calls[0]["model"],
                         "gpt-5.6-mini")


if __name__ == "__main__":
    unittest.main()
