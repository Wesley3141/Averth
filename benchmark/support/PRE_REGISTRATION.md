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

**Cost per acceptable resolution** = total arm cost / accepted count,
where accepted = predicted resolution label matches the recorded
accepted resolution. Computed from the Averth Tracker ledger (invoice
keys recorded per attempt for later reconciliation).

## Kill criteria (all must hold for C to win)

1. C's cost per acceptable resolution is at least 20% lower than B's
   (bootstrap 95% CI on the ratio, reuse `../analyze.py`).
2. Bootstrap p < 0.05 for the reduction.
3. C's acceptance rate is no more than 5 percentage points below B's
   (non-inferiority).
4. Payback: experiment cost / monthly savings at the partner's ticket
   volume < 6 months.

Ties, regressions, and inconclusive results are reported as such. A
failed kill criterion kills the claim, not the investigation: diagnose,
don't re-run until green.

## Commercial falsifiable claim (separate from the benchmark)

5 high-volume support-agent design partners, 30-day timebox. The
direction is dead if fewer than 2 teams block a deployment and rewrite
a prompt purely because Averth flagged a unit-economic threshold
violation.

## Amendments

(none yet)
