# Averth Direction — converged with Gemini Pro, 2026-10-07

## The one thesis

Averth is the CI-embedded unit-economic gate for customer-support AI
agents: it blocks agent changes (prompt, model, or config updates) that
would violate a FinOps-governed "Cost per Acceptable Resolution" threshold,
where "acceptable" is defined by CRM-grounded outcomes (resolved without
reopening, no SLA breach) and cost is attributed billing-groundedly across
total workflow compute, not just tokens.

## Why it's defensible (hypothesis, not proven)

- **vs LangSmith / Braintrust:** Braintrust already markets CI
  evaluation, regression blocking, and cost comparison across
  prompt/model experiments; LangSmith documents offline evaluation and
  business-rule evaluators. They are trace-bound and sell to the AI
  engineer, which leaves room — but the claim that they *structurally
  cannot* approach this is withdrawn. The hypothesis is narrower: that
  support-specific outcome/cost evaluation, fused with the business
  state machine (Zendesk/Salesforce outcomes) and sold to the P&L owner,
  is easier and useful enough to adopt that the integration depth
  becomes the moat. Unproven until a partner proves it.
- **vs Vantage / Finout / CloudZero:** Finout exposes cost data for
  deploys, PRs, and internal tools — FinOps tooling *can* participate in
  deployments. None of them gates a deployment on support-outcome
  quality today, but the categorical "cannot" is withdrawn for the
  same reason.

Buyer segmentation and messy integrations can help; they do not
establish an architectural moat on their own.

Gemini's verbatim endorsement: "I explicitly endorse this as the ONE
direction. It is structurally sound, isolates a distinct buyer (Support
Ops / RevOps), and leverages the 'messy plumbing' of CRM integrations as
a shield against dev-tool incumbents."

## Falsifiable claim (revised 2026-10-08)

One team operating a custom support workflow, in shadow mode: reviewed
historical cases graded offline, one targeted change tested, measured
cost and answer/action quality before and after, with uncertainty and
limitations stated. The team decides whether the result warrants
deployment.

The commercial signal is **repeated use on real release decisions and
willingness to pay** — not blocked-deployment counts. (The earlier
"2 blocked deploys in 30 days" criterion is withdrawn: it rewards noisy
blocking and punishes a useful product when no harmful change occurs.)
Blocking is enabled only after the metric and repeated decisions are
trusted; reopen/SLA behavior is validated prospectively after
deployment.

## First build

"Support three-arm benchmark v1" (`benchmark/support/`): a pinned battery
of real support tickets with CRM-grounded acceptance checks
(resolved-without-reopen, SLA compliance), run across three arms
(unchanged open-source agent, one genuine Claude+LangSmith optimization
pass, Averth's measured experiment loop), with bootstrap confidence
intervals and pre-registered kill criteria, wired as a deployment gate on
one design partner's agent pipeline.

Scoping correction (accepted during iteration): the gate is NOT only a
GitHub Action. The "merge" for support agents is usually a LaunchDarkly
tweak, prompt-registry update, or dashboard config change — so the gate is
packaged as a deployment webhook/API interceptor between the config
dashboard and production that runs the shadow battery and returns
pass/fail before the new config goes live.

## What this supersedes

- Moat plan v2's generic "workflow improvement with billing-grounded
  measurement" is now narrowed: customer-support agents, Cost per
  Acceptable Resolution, deployment gate, FinOps-governed threshold.
- The issue-triage benchmark remains a valid proof-of-harness but is no
  longer the lead artifact; the support battery is.

## Status

- [x] Thesis converged (Gemini Pro, 5 exchanges, 2026-10-07)
- [x] Support benchmark v1 built (spec, arm-A agent, grader, runner,
      gate service + interceptor spec, pre-registration, 16 unit tests)
- [ ] Ticket battery fetched (blocked: source research in progress)
- [ ] Pushed to master
- [ ] Reviewed by Gemini + Hatch
- [ ] Real model runs (blocked: no API key)
- [ ] Design partner #1 (not started)
