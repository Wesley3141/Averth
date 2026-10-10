"""Experiment 2: judge-input guard.

Baseline: the public Judge extracts five fixed keys (incident_type, pod,
namespace, fix_action, reasoning). On the recorded plan every one of them is
missing, so the Judge dispatches a model call on five Unknowns.

Candidate: fix the key mapping AND validate before dispatch. Malformed or
contradictory inputs escalate with zero model calls; well-formed inputs are
still judged exactly as before.

What is measured (deterministic, no model needed):
  - judge model calls dispatched per case, baseline vs candidate.
What is estimated (labeled):
  - dollars per avoided call, from prompt size at Sonnet-class rates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.models import StubBackend, Usage
from lab.pricing import cost_for

INCIDENT_DIR = Path.home() / "workspace/outreach/ahmad-gayibov-incident"

BASELINE_KEYS = ["incident_type", "pod", "namespace", "fix_action", "reasoning"]

# alias map mirrors the tested candidate patch
ALIASES = {
    "incident": ("root_cause", "incident_type"),
    "pod": ("incident_pod", "pod"),
    "namespace": ("incident_namespace", "namespace"),
    "action": ("fix_description", "fix_action"),
    "reasoning": ("llm_analysis", "reasoning"),
    "command": ("fix_command",),
}

# incident reason -> substrings a compatible fix must contain
COMPATIBLE = {
    "crashloopbackoff": ("rollout restart", "delete pod"),
    "imagepullbackoff": ("set image",),
    "oomkilled": ("memory", "patch deployment"),
}


def baseline_extract(plan: dict) -> dict:
    return {k: plan.get(k, "Unknown") for k in BASELINE_KEYS}


def candidate_extract(plan: dict) -> dict:
    fields = {}
    for label, aliases in ALIASES.items():
        values = [plan[k] for k in aliases if k in plan]
        if not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f"missing Judge field: {label}")
        if len(set(values)) != 1:
            raise ValueError(f"conflicting Judge aliases: {label}")
        fields[label] = values[0]
    return fields


def judge_prompt(f: dict) -> str:
    get = f.get
    return (
        "You are the safety Judge for an automated Kubernetes incident responder.\n"
        f"Incident type: {get('incident', get('incident_type'))}\n"
        f"Pod: {get('pod')}\n"
        f"Namespace: {get('namespace')}\n"
        f"Proposed action: {get('action', get('fix_action'))}\n"
        f"Command: {get('command', 'n/a')}\n"
        f"Researcher reasoning: {get('reasoning')}\n"
        "Decide: approve or escalate. A wrong auto-fix can take down a workload."
    )


def compatible(incident: str, command: str) -> bool:
    subs = COMPATIBLE.get(incident.lower().replace(" ", ""))
    if subs is None:
        return True  # unknown incident class: judge it, don't block it
    cmd = command.lower()
    return any(s in cmd for s in subs)


def run_case(name: str, plan: dict, model: StubBackend) -> dict:
    # baseline: always dispatches
    b_inputs = baseline_extract(plan)
    b_prompt = judge_prompt(b_inputs)
    _, b_usage = model.generate(b_prompt, tag=f"baseline-{name}")
    b_unknowns = sum(1 for v in b_inputs.values() if v == "Unknown")

    # candidate: map, validate, consistency-check, then dispatch or escalate
    try:
        c_inputs = candidate_extract(plan)
    except ValueError as e:
        return {"case": name, "baseline_calls": 1, "candidate_calls": 0,
                "baseline_unknowns": b_unknowns, "outcome": f"escalated: {e}",
                "prompt_chars": len(b_prompt)}
    if not compatible(c_inputs["incident"], c_inputs.get("command", "")):
        return {"case": name, "baseline_calls": 1, "candidate_calls": 0,
                "baseline_unknowns": b_unknowns,
                "outcome": "escalated: fix incompatible with incident type",
                "prompt_chars": len(b_prompt)}
    c_prompt = judge_prompt(c_inputs)
    _, c_usage = model.generate(c_prompt, tag=f"candidate-{name}")
    return {"case": name, "baseline_calls": 1, "candidate_calls": 1,
            "baseline_unknowns": b_unknowns, "outcome": "judged (behavior preserved)",
            "prompt_chars": len(b_prompt), "usage": c_usage}


def main() -> None:
    recorded = json.loads((INCIDENT_DIR / "action_plan.json").read_text())
    cases = {
        "recorded-plan": recorded,
        "well-formed": {
            "incident_type": "CrashLoopBackOff",
            "pod": "crash-deploy-5fcdc87555-tjhgc",
            "namespace": "default",
            "fix_action": "Restart the workload to clear transient crash state",
            "reasoning": "Container exiting with code 1; restart is the known remediation.",
            "fix_command": "kubectl rollout restart deployment/crash-deploy -n default",
        },
        "missing-action": {
            "incident_type": "CrashLoopBackOff",
            "pod": "api-xyz",
            "namespace": "default",
            "reasoning": "Some analysis.",
        },
        "contradictory": {
            "incident_type": "CrashLoopBackOff",
            "pod": "api-xyz",
            "namespace": "default",
            "fix_action": "Update the container image",
            "reasoning": "Image pull failing.",
            "fix_command": "kubectl set image deployment/api api=api:9.9.9 -n default",
        },
    }
    model = StubBackend()
    rows = [run_case(n, p, model) for n, p in cases.items()]

    print(f"{'case':<16}{'base calls':>11}{'cand calls':>11}  outcome")
    for r in rows:
        print(f"{r['case']:<16}{r['baseline_calls']:>11}{r['candidate_calls']:>11}  {r['outcome']}")
    avoided = sum(r["baseline_calls"] - r["candidate_calls"] for r in rows)
    print(f"\njudge calls avoided: {avoided}")
    # estimated cost per call from prompt size (labeled estimate, not measured)
    chars = rows[0]["prompt_chars"]
    est_tokens_in = chars / 4
    est = cost_for(Usage(int(est_tokens_in), 150), "sonnet-class")
    print(f"prompt size: ~{chars} chars -> ~{est_tokens_in:.0f} input tokens (estimate)")
    print(f"estimated cost per judge call: ~${est:.4f} (Sonnet-class rates, labeled estimate)")
    print(f"estimated spend avoided on malformed inputs: ~${avoided * est:.4f} (illustrative)")
    print("NOTE: call counts are deterministic. Dollar figures are illustrative estimates, not measured.")


if __name__ == "__main__":
    main()
