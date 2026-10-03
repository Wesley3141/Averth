"""LangChain / LangGraph callback handler for averth.

Auto-captures into a Tracker: LLM calls (model, input/output tokens), tool
calls (name, cost), chain start/end (attempt boundaries), and errors
(retries / failed attempts).

    from averth import Tracker
    from averth.integrations import AverthCallbackHandler

    tracker = Tracker("support-agent", budget_per_success=2.00)
    handler = AverthCallbackHandler(tracker)
    agent.invoke({"messages": messages}, config={"callbacks": [handler]})
    print(tracker.pnl()["per_success"]["fully_loaded"])

Works with LangGraph agents: nested chain callbacks only start an attempt
when none is active, so one graph run maps to one attempt. langchain is
optional here: the base class is imported lazily and every method can be
driven directly with stub dicts, so the handler is fully unit-testable
without langchain installed.
"""

import time
import warnings

from averth import BudgetBreach, pricing

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
    """(input_tokens, output_tokens) from response.llm_output, safely.

    Clamped at zero: a provider reporting negative counters is malformed
    data, and a callback must never inject a negative cost line (or raise
    inside the agent's own run) because of it.
    """
    llm_output = getattr(response, "llm_output", None) or {}
    if not isinstance(llm_output, dict):
        return 0, 0
    usage = llm_output.get("token_usage") or {}
    if not isinstance(usage, dict):
        return 0, 0
    in_tok = usage.get("prompt_tokens") or 0
    out_tok = usage.get("completion_tokens") or 0
    try:
        return max(0, int(in_tok)), max(0, int(out_tok))
    except (TypeError, ValueError, OverflowError):
        return 0, 0


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


class AverthCallbackHandler(BaseCallbackHandler):
    """Meters a LangChain/LangGraph agent run into an averth Tracker.

    Attach via config={"callbacks": [handler]}. The outermost chain start
    opens a Tracker attempt; chain end closes it (success), chain error
    closes it as failed. LLM and tool callbacks in between record spend.

    Budgets: if the Tracker has budget_per_success set and no on_breach
    callback, a breach at chain end cannot propagate to the host app —
    LangChain's callback dispatch swallows handler exceptions — so it is
    surfaced as a warnings.warn instead. The supported enforcement path is
    passing on_breach= to the Tracker, which fires without raising.

    Concurrency: one handler instance meters one run at a time. A second
    top-level chain start while a run is in flight raises RuntimeError
    rather than merging both runs' spend into one attempt; use one handler
    instance per concurrent run.

    Manual attempts: if you opened the attempt yourself with
    tracker.start_attempt() before the chain ran, the handler only records
    spend into it and never closes it — chain end will not end your attempt
    or set its success flag.
    """

    def __init__(self, tracker, auto_attempt=True):
        self.tracker = tracker
        self.auto_attempt = auto_attempt
        self._llm_runs = {}   # run_id -> {"model", "provider"}
        self._tool_runs = {}  # run_id -> {"name", "started"}
        # Open chain run_ids, outermost first. LangGraph reuses one run_id
        # for a whole graph run (nested callbacks share it), so the attempt
        # must close only when the outermost chain finishes, not on the
        # first nested chain end. Depth counting keeps this balanced.
        self._chain_stack = []
        # Whether THIS handler opened the tracker's current attempt. A
        # manually-opened attempt is metered but never closed by the handler.
        self._opened_attempt = False

    # ---- attempt boundaries ----
    def on_chain_start(self, serialized, inputs, run_id=None,
                       parent_run_id=None, **kwargs):
        if not self.auto_attempt:
            return
        if (self._chain_stack
                and run_id not in self._chain_stack
                and parent_run_id not in self._chain_stack):
            # A new top-level chain started while another run is in flight
            # (e.g. agent.batch with one shared handler). Its spend must
            # not be merged into the open attempt under the first run's
            # case_id — refuse loudly instead.
            raise RuntimeError(
                "AverthCallbackHandler meters one run at a time: a second "
                "top-level chain (run_id=%r) started while run %r is still "
                "open. Use one handler instance per concurrent run." %
                (run_id, self._chain_stack[0]))
        self._chain_stack.append(run_id)
        if len(self._chain_stack) == 1 and self.tracker._cur is None:
            case_id = inputs.get("case_id") if isinstance(inputs, dict) else None
            self.tracker.start_attempt(case_id=case_id)
            self._opened_attempt = True

    def _chain_done(self, run_id, success):
        if not self.auto_attempt:
            return
        if run_id in self._chain_stack:
            self._chain_stack.remove(run_id)
        # Unknown run_ids are ignored entirely: popping a real stack entry
        # here would close the attempt early and silently drop later spend.
        # Only the outermost chain end/error closes the attempt. Nested
        # chain ends (LangGraph nodes, sub-chains) must not close it early,
        # or later tool/LLM events would be dropped or split into fragments.
        if not self._chain_stack:
            opened = self._opened_attempt
            self._opened_attempt = False
            if opened and self.tracker._cur is not None:
                try:
                    self.tracker.end_attempt(success=success)
                except BudgetBreach:
                    # LangChain's callback dispatch swallows handler
                    # exceptions, so a breach raised here can never reach
                    # the host app. Surface it as a loud warning; the
                    # attempt itself is already recorded. For enforced
                    # budgets pass on_breach= to the Tracker.
                    warnings.warn(
                        "BudgetBreach swallowed by LangChain dispatch: this "
                        "run's cost exceeded the tracker's budget_per_success "
                        "($%.2f), but LangChain's callback manager catches "
                        "handler exceptions, so the breach cannot propagate "
                        "to the host app from this callback. Pass on_breach= "
                        "to the Tracker for the supported enforcement path."
                        % (self.tracker.budget_per_success,))

    def on_chain_end(self, outputs, run_id=None, parent_run_id=None, **kwargs):
        self._chain_done(run_id, True)

    def on_chain_error(self, error, run_id=None, parent_run_id=None, **kwargs):
        self._chain_done(run_id, False)

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
        info = self._tool_runs.pop(run_id, None) or {}
        name = info.get("name") or "unknown"
        if self.tracker._cur is not None:
            # The failed invocation still consumed the tool (network egress,
            # provider metering), so its cost is recorded like a success;
            # the retry marker classifies the waste separately.
            self.tracker.log_tool_call(name)
            self.tracker.log_retry(reason="tool_error: " + type(error).__name__)

    # ---- internals ----
    def _log_model(self, provider, model, in_tok, out_tok):
        try:
            self.tracker.log_model_call(provider, model, in_tok, out_tok)
        except KeyError:
            cost = pricing.estimated_model_cost(provider, model, in_tok, out_tok)
            self.tracker.log_model_cost_estimate(provider, model, cost,
                                                 in_tok, out_tok)
