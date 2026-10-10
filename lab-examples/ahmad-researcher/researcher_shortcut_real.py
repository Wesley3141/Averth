"""Experiment 1b: researcher shortcut against the REAL recorded narrative.

Baseline explanation = action_plan.json['llm_analysis'], the actual recorded
model output from the April 30 incident. Not a stub, not a guess.
Candidate = deterministic template parameterized by reason code + incident facts.

Question: does the recorded narrative contain any substantive proposition the
template cannot reproduce from (incident_package + known-fix table)?

Model calls are counted, not simulated: the baseline's call is a recorded fact
(the llm_analysis exists); the candidate makes none.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from averth.lab.harness import Case, run_experiment
from averth.lab.models import Usage
from averth.lab.report import render

INCIDENT_DIR = Path.home() / "workspace/outreach/ahmad-gayibov-incident"

TEMPLATES = {
    "CrashLoopBackOff": (
        "Cause: pod {pod} in namespace {namespace} is in CrashLoopBackOff; the container "
        "is exiting with code {exit_code} after {restart_count} restarts, even though image "
        "{image} pulled successfully. "
        "Impact: the deployment cannot reach a stable state; availability and reliability are "
        "degraded until a healthy replacement serves traffic. "
        "Fix: {fix}. This is appropriate if the crash is transient or environment-related; it does "
        "not address underlying configuration errors or resource constraints. If the cause is not "
        "clearly transient, investigate container logs and resource limits before applying the fix; "
        "if crashes persist after the restart, do not repeat it blindly."
    ),
    "ImagePullBackOff": (
        "Cause: pod {pod} in namespace {namespace} is in ImagePullBackOff; image {image} could not "
        "be pulled. "
        "Impact: the deployment cannot start; availability is degraded until a valid image is set. "
        "Fix: {fix}. This is appropriate if the tag or registry reference is wrong; it does not "
        "address underlying registry authentication or network issues. If pulls keep failing, check "
        "image pull secrets and registry access before further action."
    ),
    "OOMKilled": (
        "Cause: pod {pod} in namespace {namespace} was OOMKilled; the container exceeded its memory "
        "limit. "
        "Impact: the workload is terminated and will be restarted; repeated kills degrade availability. "
        "Fix: {fix}. This is appropriate if the limit was simply too low; it does not address an "
        "underlying memory leak. If kills persist after raising the limit, investigate the application's "
        "memory profile before further action."
    ),
}

# substantive propositions in the recorded Sonnet narrative, as checkable predicates.
# Pod/fix identifiers are read from the recorded plan at runtime, never hardcoded,
# so the case study carries no operator-specific identifiers.
def get_propositions():
    plan = json.loads((INCIDENT_DIR / "action_plan.json").read_text())
    pod = plan["incident_pod"]
    fix = plan["fix_command"]
    return [
        ("pod_identity", lambda c, _p=pod: _p in c),
        ("namespace", lambda c: "namespace default" in c),
        ("reason", lambda c: "crashloopbackoff" in c.lower()),
        ("exit_code", lambda c: "code 1" in c),
        ("image_pulled_ok", lambda c: "busybox" in c.lower()),
        ("impact_availability", lambda c: "availability" in c.lower()),
        ("fix_command", lambda c, _f=fix: _f in c),
        ("hedge_transient", lambda c: "transient" in c.lower()),
        ("hedge_underlying", lambda c: "underlying" in c.lower()),
        ("hedge_investigate", lambda c: "investigat" in c.lower()),
    ]


def incident_facts(pkg: dict) -> dict:
    events = pkg.get("events", "")
    m = re.search(r'Successfully pulled image "([^"]+)"', events)
    return {
        "pod": pkg.get("pod", "unknown"),
        "namespace": pkg.get("namespace", "unknown"),
        "exit_code": str(pkg.get("exit_code", "unknown")),
        "restart_count": str(pkg.get("restart_count", "unknown")),
        "image": m.group(1) if m else "unknown",
    }


def baseline(case: Case, model):
    plan = json.loads((INCIDENT_DIR / "action_plan.json").read_text())
    return plan["fix_command"], plan["llm_analysis"], Usage(0, 0), {"recorded": True, "model_calls": 1}


def candidate(case: Case, model):
    pkg = json.loads((INCIDENT_DIR / "incident_package.json").read_text())
    plan = json.loads((INCIDENT_DIR / "action_plan.json").read_text())
    facts = incident_facts(pkg)
    facts["fix"] = plan["fix_command"]
    reason = pkg.get("reason", "")
    template = TEMPLATES.get(reason, "Manual triage required for pod {pod}: reason {reason}.")
    facts.setdefault("reason", reason)
    return plan["fix_command"], template.format(**facts), Usage(0, 0), {"model_calls": 0}


def quality_fn(case: Case, action: str, explanation: str, extra: dict) -> dict:
    checks = {"action_correct": action == case.expected_action}
    for name, pred in get_propositions():
        try:
            checks[name] = bool(pred(explanation))
        except Exception:
            checks[name] = False
    checks["_proxy"] = True  # keyword predicates, not a reading
    return checks


def main() -> None:
    plan = json.loads((INCIDENT_DIR / "action_plan.json").read_text())
    case = Case("recorded-incident", {}, plan["fix_command"], ())
    report = run_experiment(
        name="ahmad-researcher-shortcut-real-baseline",
        baseline=baseline,
        candidate=candidate,
        cases=[case],
        quality_fn=quality_fn,
        cost_fn=lambda u: 0.0,  # real per-call tokens were not recorded; see summary
        model=_NoModel(),
    )
    print(render(report))
    c = report.comparisons[0]
    missing = [k for k, v in c.candidate.quality.items() if not v and not k.startswith("_")]
    kept = [k for k, v in c.candidate.quality.items()
            if v and k != "action_correct" and not k.startswith("_")]
    print(f"\npropositions preserved: {len(kept)}/{len(get_propositions())}")
    if missing:
        print(f"dropped propositions: {missing}")
    else:
        print("dropped propositions: none")
    print("\nRecorded baseline calls: 1 (fact: llm_analysis exists in action_plan.json).")
    print("Candidate calls: 0.")
    print("Owner-reported Researcher step cost: ~$0.002; the narrative call is the step's")
    print("only model call (code structure), so skipping it removes ~$0.002/incident")
    print("at the reported rate. Per-call tokens were not recorded; this is arithmetic")
    print("on the reported figure, not a measurement.")
    print("NOTE: proposition checks are keyword predicates (proxy). n=1 recorded incident.")


class _NoModel:
    name = "recorded-data (no live model)"
    def generate(self, prompt: str, *, tag: str = ""):
        raise RuntimeError("this experiment uses recorded data, not a model")


if __name__ == "__main__":
    main()
