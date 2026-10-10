"""Experiment 1: Ahmad's Researcher shortcut.

Baseline:  known-fix lookup (deterministic) + narrative model call.
Candidate: known-fix lookup (deterministic) + compact structured explanation, no model call.

Both arms share the same lookup code path, so any behavior difference comes
only from the explanation step. Run with StubBackend today to prove the
plumbing; flip to RealBackend with approved credentials for the honest result.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from averth.lab.harness import Case, run_experiment
from averth.lab.models import ModelBackend, StubBackend, Usage
from averth.lab.pricing import cost_for
from averth.lab.quality import keyword_coverage
from averth.lab.report import render


# --- The deterministic known-fix lookup, mirroring the public Researcher ---
KNOWN_FIXES = {
    "CrashLoopBackOff": "kubectl rollout restart deployment/{deployment} -n {namespace}",
    "ImagePullBackOff": "kubectl set image deployment/{deployment} {container}={image} -n {namespace}",
    "OOMKilled": "kubectl patch deployment/{deployment} -n {namespace} --type merge -p {memory_patch}",
}


def lookup_fix(reason: str, ctx: dict) -> str:
    template = KNOWN_FIXES.get(reason, "manual triage required")
    try:
        return template.format(**ctx)
    except KeyError:
        return template


def baseline(case: Case, model: ModelBackend):
    action = lookup_fix(case.incident["reason"], case.incident["ctx"])
    prompt = (
        f"Explain this Kubernetes incident for the record. Pod {case.incident['pod']} "
        f"in {case.incident['namespace']} is {case.incident['reason']}. "
        f"Selected fix: {action}. Cover cause, impact, and why the fix is appropriate."
    )
    text, usage = model.generate(prompt, tag=case.id)
    return action, text, usage, {}


def candidate(case: Case, model: ModelBackend):
    action = lookup_fix(case.incident["reason"], case.incident["ctx"])
    expl = (
        f"Cause: {case.incident['reason']} on pod {case.incident['pod']}. "
        f"Impact: workload unavailable until replacement is healthy. "
        f"Fix appropriateness: known remediation '{action}' restarts the workload "
        f"with a clean state; verified by rollout observation, not pod disappearance."
    )
    return action, expl, Usage(0, 0), {}


def build_cases() -> list[Case]:
    ctx = {"deployment": "api", "namespace": "lab", "container": "api", "image": "api:1.2.4",
           "memory_patch": '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"1Gi"}}}]}}}}'}
    return [
        Case("crashloop-lab", {"reason": "CrashLoopBackOff", "pod": "api-7d9f", "namespace": "lab", "ctx": ctx},
             "kubectl rollout restart deployment/api -n lab",
             ("cause of the crash loop", "impact on availability", "why restart is appropriate")),
        Case("imagepull-lab", {"reason": "ImagePullBackOff", "pod": "api-3a1c", "namespace": "lab", "ctx": ctx},
             "kubectl set image deployment/api api=api:1.2.4 -n lab",
             ("cause of the pull failure", "impact on availability", "why image update is appropriate")),
        Case("oom-lab", {"reason": "OOMKilled", "pod": "worker-9e2b", "namespace": "lab", "ctx": ctx},
             "kubectl patch deployment/api -n lab --type merge -p " + ctx["memory_patch"],
             ("cause of the OOM kill", "impact on availability", "why raising the memory limit is appropriate")),
        Case("unknown-reason", {"reason": "Evicted", "pod": "api-5f77", "namespace": "lab", "ctx": ctx},
             "manual triage required",
             ("cause of the eviction", "impact on availability", "why manual triage is appropriate")),
    ]


def main() -> None:
    stub = StubBackend()
    report = run_experiment(
        name="ahmad-researcher-shortcut",
        baseline=baseline,
        candidate=candidate,
        cases=build_cases(),
        quality_fn=keyword_coverage,
        cost_fn=lambda u: cost_for(u, "sonnet-class"),
        model=stub,
    )
    print(render(report))
    print(f"\nstub model calls made: baseline={len(stub.calls)} (candidate makes none)")


if __name__ == "__main__":
    main()
