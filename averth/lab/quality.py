"""Quality rubrics. Stub-phase proxies are labeled as such.

Rule-based checks (keyword coverage, action equality) are cheap proxies, not
quality judgments. A real verdict needs a human or an LLM judge reading the
explanations; the harness accepts either through the same interface.
"""
from __future__ import annotations

from typing import Callable, Dict

from .harness import Case


def keyword_coverage(case: Case, action: str, explanation: str, extra: dict) -> Dict[str, bool]:
    """Proxy: does the explanation mention each required point?

    PROXY, not a judgment. A real judge reads for correctness, not keyword
    presence. Labeled everywhere it is used.
    """
    lowered = explanation.lower()
    checks = {
        "action_correct": action == case.expected_action,
        "explanation_present": len(explanation.strip()) > 20,
    }
    for i, point in enumerate(case.required_points):
        key_terms = [t for t in point.lower().split() if len(t) > 4]
        checks[f"covers_point_{i+1}"] = any(t in lowered for t in key_terms) if key_terms else True
    checks["_proxy"] = True
    return checks


def human_judged(judgments: Dict[str, Dict[str, bool]]) -> Callable[[Case, str, str, dict], Dict[str, bool]]:
    """Build a quality fn from a human's per-case judgments.

    judgments: {case_id: {"action_correct": bool, "explanation_adequate": bool, ...}}
    Missing cases fail closed.
    """
    def fn(case: Case, action: str, explanation: str, extra: dict) -> Dict[str, bool]:
        j = judgments.get(case.id)
        if j is None:
            return {"judged": False, "action_correct": False, "explanation_adequate": False}
        out = {"judged": True, **j}
        out["_proxy"] = False
        return out
    return fn
