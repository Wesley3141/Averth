"""OpenAI SDK wrapper for averth.

Wraps an OpenAI client instance (duck-typed, no openai import at module
level) so chat.completions.create and responses.create calls capture model
and token usage into a Tracker:

    from averth import Tracker
    from averth.integrations import wrap_openai_client

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

Streaming: with stream=True the SDK returns an iterator immediately, so no
usage exists at call time. The wrapper returns a lightweight iterator proxy:
chunks pass through to the caller unchanged, and when the stream is fully
consumed the usage reported on the final chunk
(stream_options={"include_usage": True}) is logged through the normal
path. If the stream is exhausted without ever reporting usage, NO
zero-cost step is logged; instead the "provider:model" key is added to
tracker.missing_usage so the gap is visible in
pnl()["missing_usage_models"]. A stream that is abandoned before
exhaustion records nothing. Async clients are not supported: create()
returning an awaitable raises TypeError immediately, before anything is
logged.
"""

import inspect
import time
from types import SimpleNamespace

from averth import pricing


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
    """Cached input tokens from usage details (dict or object).

    Chat Completions reports them at usage.prompt_tokens_details; the
    Responses API reports them at usage.input_tokens_details. Both shapes
    are read (first non-None wins). OpenAI's API reports these as measured
    data; when absent this returns 0 and pricing proceeds without a cache
    term.
    """
    if usage is None:
        return 0
    for attr in ("prompt_tokens_details", "input_tokens_details"):
        if isinstance(usage, dict):
            details = usage.get(attr)
        else:
            details = getattr(usage, attr, None)
        if details is None:
            continue
        if isinstance(details, dict):
            value = details.get("cached_tokens")
        else:
            value = getattr(details, "cached_tokens", None)
        if value is not None:
            return _int_or_zero(value)
    return 0


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


class _StreamWrapper:
    """Iterator proxy for stream=True responses.

    Chunks pass through to the caller unchanged. Usage arrives, if at all,
    on the final chunk (stream_options={"include_usage": True}); when the
    stream is exhausted the real token counts are logged through the normal
    path. If the stream ends without ever reporting usage, no zero-cost
    step is logged — the "provider:model" key goes to
    tracker.missing_usage instead, so the gap is visible rather than
    presented as $0.00 of measured spend.
    """

    def __init__(self, stream, tracker, provider, model):
        self._stream = iter(stream)
        self._tracker = tracker
        self._provider = provider
        self._model = model
        self._usage = None
        self._finished = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self._stream)
        except StopIteration:
            self._finish()
            raise
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            self._usage = usage
        return chunk

    def _finish(self):
        if self._finished:
            return
        self._finished = True
        if self._usage is not None:
            _capture(self._tracker, self._provider, self._model,
                     SimpleNamespace(model=self._model, usage=self._usage))
        else:
            self._tracker.missing_usage.add(
                "%s:%s" % (self._provider, self._model or "unknown"))

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _is_stream_response(resp, kwargs):
    """True when create() returned a streaming iterator rather than a response.

    The explicit stream=True kwarg is the primary signal; a duck-typed
    fallback catches iterators with no .usage attribute.
    """
    if kwargs.get("stream"):
        return True
    return (getattr(resp, "usage", None) is None
            and hasattr(resp, "__next__"))


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
        if inspect.isawaitable(resp):
            # Async clients are not supported: the coroutine carries no
            # usage, so capturing here would log a phantom $0.00 step while
            # the real spend (visible only after await) went unrecorded.
            # Refuse loudly before logging anything.
            close = getattr(resp, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            raise TypeError(
                "averth's OpenAI wrapper does not support async clients: "
                "create() returned an awaitable, which carries no usage to "
                "capture. Use the synchronous openai.OpenAI client instead. "
                "Nothing was logged.")
        if _is_stream_response(resp, kwargs):
            return _StreamWrapper(resp, self._tracker, self._provider,
                                  kwargs.get("model"))
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
    stream=True calls return a metering iterator proxy (usage is logged when
    the stream is fully consumed; see the module docstring). Async clients
    are not supported and raise TypeError.
    """
    return _ClientProxy(client, tracker, provider)
