"""OpenAI SDK wrapper for agentpnl.

Wraps an OpenAI client instance (duck-typed, no openai import at module
level) so chat.completions.create and responses.create calls capture model
and token usage into a Tracker:

    from agentpnl import Tracker
    from agentpnl.integrations import wrap_openai_client

    tracker = Tracker("support-agent")
    client = wrap_openai_client(openai.OpenAI(), tracker)
    tracker.start_attempt(case_id="C-1042")
    client.chat.completions.create(model="gpt-5.6-mini", messages=[...])
    tracker.end_attempt(success=True)

The original client is never mutated: the wrapper is a lightweight proxy
that delegates everything except the two metered create() methods. Calls
are timed around the SDK invocation. Models missing from the pricing table
fall back to an estimated price and are flagged in
pnl()["unpriced_models"], so estimated spend is visible, never hidden.
"""

import time

from agentpnl import pricing


def _int_or_zero(value):
    # C10: int(float("inf")) raises OverflowError, not ValueError
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError, OverflowError):
        return 0


def _usage_field(usage, *names):
    """First non-None usage field, supporting dicts and attribute objects."""
    if usage is None:
        return 0
    for name in names:
        if isinstance(usage, dict):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        if value is not None:
            return _int_or_zero(value)
    return 0


def _usage_tokens(usage):
    in_tok = _usage_field(usage, "prompt_tokens", "input_tokens")
    out_tok = _usage_field(usage, "completion_tokens", "output_tokens")
    return in_tok, out_tok


def _usage_cached_tokens(usage):
    """Cached input tokens from usage.prompt_tokens_details (dict or object).

    OpenAI's API reports these as measured data; when absent this returns 0
    and pricing proceeds without a cache term.
    """
    if usage is None:
        return 0
    if isinstance(usage, dict):
        details = usage.get("prompt_tokens_details")
    else:
        details = getattr(usage, "prompt_tokens_details", None)
    if details is None:
        return 0
    if isinstance(details, dict):
        return _int_or_zero(details.get("cached_tokens"))
    return _int_or_zero(getattr(details, "cached_tokens", None))


def _capture(tracker, provider, model, resp):
    model = model or getattr(resp, "model", None) or "unknown"
    usage = getattr(resp, "usage", None)
    in_tok, out_tok = _usage_tokens(usage)
    cached_tok = _usage_cached_tokens(usage)
    try:
        tracker.log_model_call(provider, model, in_tok, out_tok,
                               cached_input_tokens=cached_tok)
    except KeyError:
        cost = pricing.estimated_model_cost(provider, model, in_tok, out_tok)
        tracker.log_model_cost_estimate(provider, model, cost, in_tok, out_tok,
                                        cached_input_tokens=cached_tok)


class _CreateMethod:
    """Wraps one create() method: times the call, captures model + usage."""

    def __init__(self, create_fn, tracker, provider):
        self._create_fn = create_fn
        self._tracker = tracker
        self._provider = provider

    def __call__(self, *args, **kwargs):
        started = time.time()
        resp = self._create_fn(*args, **kwargs)
        _ = time.time() - started  # latency observed; spend is the Phase-0 record
        _capture(self._tracker, self._provider, kwargs.get("model"), resp)
        return resp


class _CompletionsProxy:
    def __init__(self, completions, tracker, provider):
        self._completions = completions
        self._tracker = tracker
        self._provider = provider

    @property
    def create(self):
        return _CreateMethod(self._completions.create, self._tracker,
                             self._provider)

    def __getattr__(self, name):
        return getattr(self._completions, name)


class _ChatProxy:
    def __init__(self, chat, tracker, provider):
        self._chat = chat
        self._tracker = tracker
        self._provider = provider

    @property
    def completions(self):
        return _CompletionsProxy(self._chat.completions, self._tracker,
                                 self._provider)

    def __getattr__(self, name):
        return getattr(self._chat, name)


class _ResponsesProxy:
    def __init__(self, responses, tracker, provider):
        self._responses = responses
        self._tracker = tracker
        self._provider = provider

    @property
    def create(self):
        return _CreateMethod(self._responses.create, self._tracker,
                             self._provider)

    def __getattr__(self, name):
        return getattr(self._responses, name)


class _ClientProxy:
    def __init__(self, client, tracker, provider):
        self._client = client
        self._tracker = tracker
        self._provider = provider

    @property
    def chat(self):
        return _ChatProxy(self._client.chat, self._tracker, self._provider)

    @property
    def responses(self):
        return _ResponsesProxy(self._client.responses, self._tracker,
                               self._provider)

    def __getattr__(self, name):
        return getattr(self._client, name)


def wrap_openai_client(client, tracker, provider="openai"):
    """Return a proxy around an OpenAI SDK client that meters usage.

    chat.completions.create and responses.create are timed and their model
    plus token usage is captured into tracker. The original client object
    is not mutated. No import of openai; the client is duck-typed.
    """
    return _ClientProxy(client, tracker, provider)
