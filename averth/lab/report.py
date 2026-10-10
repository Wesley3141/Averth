"""Text report for an experiment. Numbers only; no adjectives about quality."""
from __future__ import annotations

from .harness import ExperimentReport


def render(report: ExperimentReport) -> str:
    lines = [
        f"experiment: {report.experiment}",
        f"backend: {report.backend}",
        f"cases: {report.n}",
        "",
        f"{'case':<28}{'base $':>10}{'cand $':>10}{'saved $':>10}{'action':>8}{'quality':>8}",
    ]
    for c in report.comparisons:
        lines.append(
            f"{c.case_id:<28}{c.baseline.cost_usd:>10.4f}{c.candidate.cost_usd:>10.4f}"
            f"{c.cost_delta_usd:>10.4f}"
            f"{'keep' if c.action_preserved else 'CHANGED':>8}"
            f"{'keep' if c.quality_preserved else 'CHANGED':>8}"
        )
    lines += [
        "",
        f"total saved: ${report.total_saved_usd:.4f}",
        f"actions preserved: {report.actions_preserved}/{report.n}",
        f"quality preserved: {report.quality_preserved}/{report.n}",
        f"verdict: {report.verdict()}",
    ]
    if report.backend == "stub":
        lines.append("NOTE: stub backend. Cost/quality are plumbing checks, not measured results.")
    return "\n".join(lines)
