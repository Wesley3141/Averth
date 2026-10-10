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
