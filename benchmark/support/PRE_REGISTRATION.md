# Pre-registration — support three-arm benchmark v1

Registered before any real-model arm runs. Amendments require a dated
entry below; silent changes invalidate the comparison.

## Battery

- Source: real support tickets (see `fetch_tasks.py` header + pinned
  `tasks.json` for exact query, fetched_at, repo/dataset).
- Splits: `dev` (arm iteration + arm B/C optimization) and `heldout`
  (evaluation; each arm evaluated once).
- Labels: fixed taxonomy (HOWTO, CONFIG, BUG_FIX, DUPLICATE, WONTFIX,
  ESCALATED), assigned by documented deterministic heuristics; raw
  signals preserved per task for audit.

## Arms

- **A** (sanity anchor): `support_agent.py` v1, pinned. Run first on
  heldout.
- **B** (the skeptic): one genuine Claude+LangSmith optimization pass
  over the support workflow. The operator commits prompts and hours
  BEFORE arm C begins, and tries to win. Same optimization-spend ceiling
  as C.
- **C** (Averth): the measured experiment loop applied to the same
  workflow.

Arm B's prompts, hours, and spend are committed before arm C starts.
Human hours are logged for B and C.

## Primary metric

**Cost per correctly classified ticket** = total arm cost / accepted
count, where accepted = predicted resolution label matches the recorded
accepted resolution. The name is honest about v1: acceptance is label
accuracy, not resolved work. Computed from the Averth Tracker ledger
(invoice keys recorded per attempt for later reconciliation).

## Kill criteria (all must hold for C to win)

1. C's cost per correctly classified ticket is at least 20% lower than
   B's (bootstrap 95% CI on the ratio, reuse `../analyze.py`).
2. Bootstrap p < 0.05 for the reduction.
3. C's acceptance rate is no more than 5 percentage points below B's
   (non-inferiority).
4. Payback: experiment cost / monthly savings at the partner's ticket
   volume < 6 months.

## False-alarm quantification (before any enforcement)

Before the gate blocks anything, run the same unchanged configuration
through the gate N≥10 times and measure how often it fails. A gate
whose no-change failure rate exceeds 5% is too noisy to enforce —
diagnose the variance (model nondeterminism, battery sampling) before
trusting its decisions.

Ties, regressions, and inconclusive results are reported as such. A
failed kill criterion kills the claim, not the investigation: diagnose,
don't re-run until green.

## Commercial falsifiable claim (separate from the benchmark,
revised 2026-10-08)

One team operating a custom support workflow, in shadow mode. The
signal is repeated use on real release decisions and willingness to pay
— not blocked-deployment counts (withdrawn: rewards noisy blocking,
punishes a useful product when no harmful change occurs). Blocking is
enabled only after the metric and repeated decisions are trusted.

## Amendments

(none yet)
