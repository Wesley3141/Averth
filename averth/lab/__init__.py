"""Averth lab: verify a workflow change before claiming it.

An experiment pits a baseline workflow against a candidate on the same cases
and reports cost delta, action preservation, and quality preservation with a
fail-closed verdict. Backends are swappable: StubBackend proves plumbing with
zero spend; RealBackend refuses to exist without approved credentials, so
stubbed results can never be presented as measured.
"""

from .harness import (
    ArmResult,
    Case,
    Comparison,
    ExperimentReport,
    WorkflowFn,
    run_experiment,
)
from .models import ModelBackend, RealBackend, StubBackend, Usage
from .pricing import PRICE_TABLE, cost_for
from .quality import human_judged, keyword_coverage
from .report import render

__all__ = [
    "ArmResult",
    "Case",
    "Comparison",
    "ExperimentReport",
    "WorkflowFn",
    "run_experiment",
    "ModelBackend",
    "RealBackend",
    "StubBackend",
    "Usage",
    "PRICE_TABLE",
    "cost_for",
    "human_judged",
    "keyword_coverage",
    "render",
]
