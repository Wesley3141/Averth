"""Core experiment runner: baseline vs candidate on the same cases.

An experiment is:
  - a set of cases (incident inputs + expected action + required explanation points)
  - a baseline workflow function and a candidate workflow function
  - a quality function scoring each run's output
  - a cost function turning usage into dollars

The runner executes both arms on every case and produces a comparison report.
Nothing here invents model behavior: both arms run against the same backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from .models import ModelBackend, Usage


@dataclass(frozen=True)
class Case:
    id: str
    incident: dict
    expected_action: str
    required_points: Tuple[str, ...]  # explanation must address each of these


@dataclass
class ArmResult:
    case_id: str
    action: str
    explanation: str
    usage: Usage
    cost_usd: float
    quality: Dict[str, bool]
    notes: str = ""


@dataclass
class Comparison:
    case_id: str
    baseline: ArmResult
    candidate: ArmResult

    @property
    def cost_delta_usd(self) -> float:
        return self.baseline.cost_usd - self.candidate.cost_usd

    @property
    def action_preserved(self) -> bool:
        return self.candidate.action == self.baseline.action

    @property
    def quality_preserved(self) -> bool:
        b, c = self.baseline.quality, self.candidate.quality
        return all(c.get(k, False) for k in b if b.get(k))


@dataclass
class ExperimentReport:
    experiment: str
    backend: str
    comparisons: List[Comparison] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.comparisons)

    @property
    def total_saved_usd(self) -> float:
        return sum(c.cost_delta_usd for c in self.comparisons)

    @property
    def actions_preserved(self) -> int:
        return sum(1 for c in self.comparisons if c.action_preserved)

    @property
    def quality_preserved(self) -> int:
        return sum(1 for c in self.comparisons if c.quality_preserved)

    def verdict(self) -> str:
        if self.n == 0:
            return "no cases ran"
        if self.actions_preserved == self.n and self.quality_preserved == self.n:
            if self.total_saved_usd > 0:
                return "candidate preserves behavior and saves money"
            return "candidate preserves behavior; no savings measured"
        return "candidate changes behavior: do not ship"


WorkflowFn = Callable[[Case, ModelBackend], Tuple[str, str, Usage, dict]]
# returns (action, explanation, usage, extra_quality_hints)


def run_experiment(name: str, baseline: WorkflowFn, candidate: WorkflowFn,
                   cases: List[Case], quality_fn: Callable[[Case, str, str, dict], Dict[str, bool]],
                   cost_fn: Callable[[Usage], float],
                   model: ModelBackend) -> ExperimentReport:
    report = ExperimentReport(experiment=name, backend=model.name)
    for case in cases:
        b_action, b_expl, b_usage, b_extra = baseline(case, model)
        c_action, c_expl, c_usage, c_extra = candidate(case, model)
        report.comparisons.append(Comparison(
            case_id=case.id,
            baseline=ArmResult(case.id, b_action, b_expl, b_usage,
                               cost_fn(b_usage), quality_fn(case, b_action, b_expl, b_extra)),
            candidate=ArmResult(case.id, c_action, c_expl, c_usage,
                                cost_fn(c_usage), quality_fn(case, c_action, c_expl, c_extra)),
        ))
    return report
