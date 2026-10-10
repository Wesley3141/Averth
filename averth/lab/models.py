"""Model backends for workflow experiments.

The harness never cares which backend is plugged in. StubBackend proves the
plumbing with zero spend; flipping to a real backend needs approved
credentials and is the only step that can produce an honest quality result.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class ModelBackend(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(self, prompt: str, *, tag: str = "") -> Tuple[str, Usage]:
        """Return (text, usage). Must never raise on stubbed paths."""


class StubBackend(ModelBackend):
    """Deterministic canned responses. Zero spend, zero network.

    responses: mapping from a case tag to (text, Usage). Unknown tags get
    the default response. This proves experiment plumbing only; it says
    nothing about real model quality.
    """

    name = "stub"

    def __init__(self, responses: Optional[Dict[str, Tuple[str, Usage]]] = None,
                 default: Optional[Tuple[str, Usage]] = None):
        self._responses = responses or {}
        self._default = default or (
            "Canned analysis: cause, impact and fix appropriateness noted.",
            Usage(input_tokens=400, output_tokens=120),
        )
        self.calls: List[dict] = []

    def generate(self, prompt: str, *, tag: str = "") -> Tuple[str, Usage]:
        self.calls.append({"tag": tag, "prompt_chars": len(prompt)})
        return self._responses.get(tag, self._default)


class RealBackend(ModelBackend):
    """Real provider backend. Refuses to exist without approved credentials.

    Constructing this without an explicit api_key raises: the harness must
    never silently fall back to a stub and present the result as measured.
    """

    def __init__(self, provider: str, model: str, api_key: Optional[str] = None):
        if not api_key:
            raise RuntimeError(
                "RealBackend needs approved credentials (api_key). "
                "Refusing to construct; use StubBackend for dry runs."
            )
        self.name = f"{provider}/{model}"
        self._provider = provider
        self._model = model
        self._api_key = api_key

    def generate(self, prompt: str, *, tag: str = "") -> Tuple[str, Usage]:
        raise NotImplementedError(
            "Wire this to the approved provider client. The harness records "
            "real Usage from the provider response; do not estimate tokens."
        )
