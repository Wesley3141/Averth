# Case study: researcher narrative call vs deterministic explanation

**Source:** public code at `absence77/ai-agents-production`, pinned commit `39b3119`
(researcher: `agents/agent2_researcher.py`), plus the operator's recorded
`action_plan.json` / `incident_package.json`. Studied October 10, 2026.

## The question

The Researcher's only model call writes a prose analysis of the incident
(cause, impact, fix appropriateness). For incidents matching a known fix, does
that call add any information beyond the incident facts plus reason-code
knowledge?

## What was tested

- `researcher_shortcut_real.py` — baseline is the **actually recorded**
  `llm_analysis` from the operator's `action_plan.json` (real model output,
  not a stub). Candidate is a deterministic template parameterized by reason
  code + incident facts. Result: 10/10 substantive propositions of the
  recorded narrative reproduced; the model call adds zero incident-specific
  information. Removing it removes the step's only model call.
- `ahmad_researcher_shortcut.py` — the same comparison as a stubbed
  `averth.lab` experiment (plumbing proof).
- `judge_input_guard.py` — companion finding: the public Judge dispatched a
  model call even when all five inputs were `Unknown` (systematic key
  mismatch). Guarding malformed/contradictory inputs before dispatch drops
  those calls to zero; well-formed inputs are still judged.

## Trace compatibility note

The operator's `trace.jsonl` validates cleanly against `averth.importers.jsonl`
(zero modifications): `start`/`tool`/`end` events with `case_id`, per-step
`cost`, and `success`/`business_value` on the end event. The trace confirms
the cost attribution as data (`researcher_step_sonnet: $0.002`,
`planner_and_executor_steps: $0.002`) and records `business_value: 0.0`
(test incident). Observation: the trace contains no Judge step, so the $0.004
total may not include every model call in the pipeline — a metering gap worth
noting when scoping savings.

## Deeper file review (October 10, cross-checked against pinned source)

- **The safety Judge did not gate this execution.** `pipeline.py` wires
  Detector → Researcher → Judge → Executor, but no `judge_verdict.json` was
  shared, the trace has no Judge step, and `apply_fix` itself never calls the
  Judge — it goes rules-engine → validate → kubectl directly. The module
  whose docstring claims to prevent the expensive mistake was not in the
  loop for this incident.
- **The plan contradicts itself.** `llm_analysis` recommends "further
  investigation into the logs and container behavior **before applying this
  fix**", while the same plan sets `auto_fix_allowed: true`, `risk_level:
  "LOW"`, `confidence: 0.85` — and the executor applied it immediately.
- **The Judge is blind to the fallback.** `fallback_command` (pod deletion)
  is not among the Judge's input keys, and the fallback's own verifier is
  looser (`bad_states` excludes `CrashLoopBackOff`, no empty-string check).
- **The verifier is allowlist-by-exclusion.** `resolved = status_after not in
  ["Failed", "Unknown", "CrashLoopBackOff"] and status_after != ""` — any
  unrecognized output, including kubectl error text, counts as resolved.
- **The "test pod" ran as prod.** Operator described a test pod; records say
  `environment: "prod"`. The executor's test-environment guard (`env ==
  "test"` → report only) keys off that label, so it did not protect this run.
- **Deployment-name heuristic is workload-type-blind.**
  `"-".join(pod.split("-")[:-2])` assumes
  `{deployment}-{replicaset-hash}-{pod-hash}`; wrong for StatefulSets and
  other controllers. Correct for this incident.

## Honesty notes

- n=1 recorded incident for the narrative comparison; templates exist per
  known-fix reason and need per-reason validation.
- Whether structured text may replace prose in the operator's records is the
  operator's call.
- Per-call token counts were never recorded; cost arithmetic uses the
  operator's reported figures, not measurements.

## Reuse

Built on `averth.lab` (`run_experiment`, `StubBackend`/`RealBackend`,
`keyword_coverage`, `render`). Copy the pattern for the next workflow.
