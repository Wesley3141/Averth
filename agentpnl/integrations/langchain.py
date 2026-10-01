"""LangChain / LangGraph callback handler for agentpnl.

Auto-captures into a Tracker: LLM calls (model, input/output tokens), tool
calls (name, cost), chain start/end (attempt boundaries), and errors
(retries / failed attempts).

    from agentpnl import Tracker
    from agentpnl.integrations import AgentPNLCallbackHandler

    tracker = Tracker("support-agent", budget_per_success=2.00)
    handler = AgentPNLCallbackHandler(tracker)
    agent.invoke({"messages": messages}, config={"callbacks": [handler]})
    print(tracker.pnl()["per_success"]["fully_loaded"])

Works with LangGraph agents: nested chain callbacks only start an attempt
when none is active, so one graph run maps to one attempt. langchain is
optional here: the base class is imported lazily and every method can be
driven directly with stub dicts, so the handler is fully unit-testable
without langchain installed.
"""

import time

from agentpnl import pricing

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
    except ImportError:
        BaseCallbackHandler = object


def _model_from_serialized(serialized):
    """Best-effort model name from a langchain serialized-LLM dict."""
    if not isinstance(serialized, dict):
        return None
    kwargs = serialized.get("kwargs") or {}
    for key in ("model_name", "model", "model_id"):
        value = kwargs.get(key)
        if value:
            return str(value)
    name = serialized.get("name")
    if name:
        return str(name)
    ids = serialized.get("id") or []
    if ids:
        return str(ids[-1])
    return None


def _guess_provider(model):
    """Guess the provider from the model name."""
    m = (model or "").lower()
    if "gpt" in m:
        return "openai"
    if "claude" in m:
        return "anthropic"
    if "gemini" in m:
        return "google"
    if "grok" in m:
        return "xai"
    return "unknown"


def _token_usage(response):
    """(input_tokens, output_tokens) from response.llm_output, safely."""
    llm_output = getattr(response, "llm_output", None) or {}
    if not isinstance(llm_output, dict):
        return 0, 0
    usage = llm_output.get("token_usage") or {}
    if not isinstance(usage, dict):
        return 0, 0
    in_tok = usage.get("prompt_tokens") or 0
    out_tok = usage.get("completion_tokens") or 0
    return int(in_tok), int(out_tok)


def _tool_name(serialized):
    if not isinstance(serialized, dict):
        return "unknown"
    name = serialized.get("name")
    if name:
        return str(name)
    ids = serialized.get("id") or []
    if ids:
        return str(ids[-1])
    return "unknown"


class AgentPNLCallbackHandler(BaseCallbackHandler):
    """Meters a LangChain/LangGraph agent run into an agentpnl Tracker.

    Attach via config={"callbacks": [handler]}. The outermost chain start
    opens a Tracker attempt; chain end closes it (success), chain error
    closes it as failed. LLM and tool callbacks in between record spend.
    """

    def __init__(self, tracker, auto_attempt=True):
        self.tracker = tracker
        self.auto_attempt = auto_attempt
        self._llm_runs = {}   # run_id -> {"model", "provider"}
        self._tool_runs = {}  # run_id -> {"name", "started"}

    # ---- attempt boundaries ----
    def on_chain_start(self, serialized, inputs, run_id=None,
                       parent_run_id=None, **kwargs):
        if self.auto_attempt and self.tracker._cur is None:
            case_id = inputs.get("case_id") if isinstance(inputs, dict) else None
            self.tracker.start_attempt(case_id=case_id)

    def on_chain_end(self, outputs, run_id=None, parent_run_id=None, **kwargs):
        if self.tracker._cur is not None:
            self.tracker.end_attempt(success=True)

    def on_chain_error(self, error, run_id=None, parent_run_id=None, **kwargs):
        if self.tracker._cur is not None:
            self.tracker.end_attempt(success=False)

    # ---- LLM calls ----
    def on_llm_start(self, serialized, prompts, run_id=None,
                     parent_run_id=None, **kwargs):
        model = _model_from_serialized(serialized)
        self._llm_runs[run_id] = {"model": model,
                                  "provider": _guess_provider(model)}

    def on_llm_end(self, response, run_id=None, parent_run_id=None, **kwargs):
        info = self._llm_runs.pop(run_id, None) or {}
        model = info.get("model") or "unknown"
        provider = info.get("provider") or "unknown"
        in_tok, out_tok = _token_usage(response)
        if self.tracker._cur is not None:
            self._log_model(provider, model, in_tok, out_tok)

    def on_llm_error(self, error, run_id=None, parent_run_id=None, **kwargs):
        self._llm_runs.pop(run_id, None)
        if self.tracker._cur is not None:
            self.tracker.log_retry(reason="llm_error: " + type(error).__name__)

    # ---- tool calls ----
    def on_tool_start(self, serialized, input_str, run_id=None,
                      parent_run_id=None, **kwargs):
        self._tool_runs[run_id] = {"name": _tool_name(serialized),
                                   "started": time.time()}

    def on_tool_end(self, output, run_id=None, parent_run_id=None, **kwargs):
        info = self._tool_runs.pop(run_id, None) or {}
        name = info.get("name") or "unknown"
        if self.tracker._cur is not None:
            self.tracker.log_tool_call(name)

    def on_tool_error(self, error, run_id=None, parent_run_id=None, **kwargs):
        self._tool_runs.pop(run_id, None)
        if self.tracker._cur is not None:
            self.tracker.log_retry(reason="tool_error: " + type(error).__name__)

    # ---- internals ----
    def _log_model(self, provider, model, in_tok, out_tok):
        try:
            self.tracker.log_model_call(provider, model, in_tok, out_tok)
        except KeyError:
            cost = pricing.estimated_model_cost(provider, model, in_tok, out_tok)
            self.tracker.log_model_cost_estimate(provider, model, cost,
                                                 in_tok, out_tok)
