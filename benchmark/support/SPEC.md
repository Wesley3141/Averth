# Support three-arm benchmark v1 — SPEC

The lead proof artifact for the Averth direction (see `../../DIRECTION.md`):
a pinned battery of real support tickets with CRM-grounded acceptance
checks, run across three arms, wired as a deployment gate.

## What "acceptable resolution" means here

A resolution is ACCEPTED iff the agent's predicted `resolution_label`
exactly matches the recorded accepted resolution for the ticket.

CRM grounding (the fields that make this more than a text-classification
task):

- `reopened`: whether the real ticket was reopened after close. Battery
  construction records it; analysis slices acceptance on reopened vs
  clean tickets. A resolution that matches a ticket which later reopened
  is still "accepted" for scoring, but the slice tells us whether the
  agent systematically misses the tickets humans got wrong.
- `time_to_close_hours` / `sla_breach`: recorded per ticket; the gate's
  threshold can include an SLA-breach-rate ceiling in v2.
- `resolution_summary`: the recorded accepted resolution, one line. The
  agent's `response_draft` is stored per run for human audit. v2 adds a
  rubric/LLM judge on drafts; v1 scores the label only, stated plainly.

Primary metric: **cost per acceptable resolution** = total arm cost /
accepted count. Same robust stats as the triage benchmark (bootstrap CI
on the C-vs-B ratio, non-inferiority on acceptance rate, trimmed
mean/median/p95/max) — reuse `../analyze.py`.

## Resolution taxonomy (fixed)

- HOWTO — usage question answered; no product change.
- CONFIG — environment/configuration issue resolved with guidance.
- BUG_FIX — confirmed defect; fixed, shipped, or workaround accepted.
- DUPLICATE — duplicate of a known issue/discussion.
- WONTFIX — by design / not planned; closed with explanation.
- ESCALATED — required human escalation beyond the agent.

Label assignment at fetch time is heuristic and deterministic (see
`fetch_tasks.py`); raw signals are preserved per task for audit. The
benchmark compares arms on the SAME battery, so label consistency matters
more than label perfection — stated, not hidden.

## Arms

- **A**: `support_agent.py` — naive v1, PINNED, do not modify. Haiku draft
  label → TF-IDF retrieval of 5 similar past tickets → Sonnet final label
  + response draft.
- **B**: one genuine Claude+LangSmith optimization pass over the same
  workflow, committed (prompts + hours) BEFORE arm C runs. Operated by a
  skeptic trying to win.
- **C**: Averth's measured experiment loop applied to the support agent.

Same spend ceiling for B and C optimization effort; same dev battery;
held-out split evaluated once per arm.

## Splits

`tasks.json`: `dev` (for iteration and arm B/C optimization) and
`heldout` (evaluation only). Pinned; fetch script records source,
fetched_at, and the exact query.

## Battery (pinned 2026-10-08)

- 640 real tickets: `microsoft/vscode` issues labeled `*question`, closed.
  384 dev / 256 heldout, with `meta` recording the exact query, fetch
  time, and sampling method.
- Sampling: random pages across the full closed set (seed 20261007) plus
  a high-comment top-up merged for underrepresented classes.
- Label composition (heuristic, spot-audited): HOWTO 246, WONTFIX 230,
  CONFIG 158, BUG_FIX 3, ESCALATED 3, DUPLICATE 0. The skew is real: this
  queue's questions are mostly usage/config/deflection. BUG_FIX and
  ESCALATED are thin here; partner Zendesk data is expected to fill them.
  Arms are compared on the SAME battery, so the skew doesn't bias the
  contrast — stated, not hidden.
- 30 tickets (4.7%) were reopened after close — the customer-side
  counter-signal. The grader reports acceptance sliced on reopened vs
  clean tickets.
- PII: email addresses scrubbed before pinning. Bodies truncated at
  6000 chars.

## The gate

`gate/` implements the deployment gate: a webhook/API interceptor (NOT
only a GitHub Action) that sits between the config surface (LaunchDarkly
flag flip, prompt-registry update, dashboard change) and production. It
runs the shadow battery against the proposed config and returns
pass/fail against the FinOps-governed Cost per Acceptable Resolution
threshold. See `gate/INTERCEPTOR_SPEC.md`.

`--mock` anywhere in this tree is plumbing validation ONLY. Mock numbers
are never benchmark results and never gate decisions.
