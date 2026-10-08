# Pre-registration: Three-Arm Triage Benchmark

Committed before any arm runs. Amending after results are known is forbidden;
amendments before unblinding require a dated addendum stating the reason.

## Workflow

GitHub issue triage (bug vs feature_request), repo pinned in `tasks.json`.
Agent v1 pinned at git commit `[TBD]`.

## Arms

- **A:** agent v1, unchanged (sanity anchor).
- **B:** agent v1 + one genuine Claude + eval-harness optimization pass.
  Operator: [skeptic name]. Time-box: 2 engineer-days. All prompts and hours
  committed to git before arm C begins. Spend ceiling: $[X] API.
  Represents: a bounded competent-engineer pass, NOT weeks of iteration.
- **C:** Averth measured experiment loop. Interventions tested individually
  before combining: (1) context reduction, (2) step-specific model routing,
  (3) retry/fallback policy.

Arm B artifact committed before arm C begins. Single-team operation is a
disclosed limitation; the commit barrier is the enforced isolation.

## Primary contrast

**C vs B** on cost per accepted task. A is a sanity anchor only.

## Metrics

- Primary: cost per accepted task (ratio estimator; bootstrap 95% CI).
- Quality gate: acceptance rate, non-inferiority margin δ = 0.05
  (C wins only if accept_C ≥ accept_B − 0.05, CIs on both).
- Latency ceiling: p95 per-task latency may not regress >20% vs B.
- Robustness: report trimmed mean, median, p50/p95/max per arm.
- Human labor: engineer-hours logged for B and C as a secondary metric.

## Sample size

Computed from baseline-measured cost variance (heavy-tail assumption):

- Baseline CV (arm A pilot, n=[TBD]): [TBD]
- Minimum detectable effect: 20% reduction
- α = 0.05, power = 0.80
- Held-out N per arm: [TBD — computed, not chosen]
- If required N exceeds budget: accept a directional result explicitly
  BEFORE spending, or do not run.

## Grader

Automated checks primary (exact label match). Two human graders + kappa on a
calibration subset of [TBD] held-out cases.

**Invalidation rule:** if human-automated agreement on accepts < 90%, the
benchmark is invalid. Relabel nothing, rerun nothing, report the failure.

## Kill criteria (all must hold)

1. C beats B by ≥20% on cost per accepted task (bootstrap p < 0.05).
2. Non-inferiority on acceptance rate holds (δ = 0.05).
3. Projected payback < 6 months at 10K tasks/month, net of experiment cost.

Miss → kill or pivot. Inconclusive → reported as inconclusive.
"18% ± 22%" is not a win.

## Budget

Demo cap: $[1,500]. All spend disclosed, including optimization-experiment
cost and human-hours costed at $[rate]/day.

## Deliverables

Proposed patch (diff), reproducible commands, comparison report with
improvements AND regressions, full experiment economics with payback math.
If arm B ties arm C, that is the headline.

## Amendments

- 2026-10-08: retrieval corpus is dev-only (was dev+heldout). Heldout
  labels must not leak through the similar-issue tool at evaluation time.
  No real-model runs had occurred before this change (mock only), so no
  results are invalidated.
