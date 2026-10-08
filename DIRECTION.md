# Averth Direction — converged with Gemini Pro, 2026-10-07

## The one thesis

Averth is the CI-embedded unit-economic gate for customer-support AI
agents: it blocks agent changes (prompt, model, or config updates) that
would violate a FinOps-governed "Cost per Acceptable Resolution" threshold,
where "acceptable" is defined by CRM-grounded outcomes (resolved without
reopening, no SLA breach) and cost is attributed billing-groundedly across
total workflow compute, not just tokens.

## Why it's defensible

- **vs LangSmith / Braintrust:** their data models, product, and sales
  motion are bound to the LLM trace and the AI-engineer buyer. True Cost
  per Acceptable Resolution requires the business state machine
  (Zendesk/Salesforce ticket outcomes: reopen rates, SLA breaches, CSAT)
  fused with the invoice layer (amortized total workflow compute), sold to
  a P&L owner they don't serve. Hardcoding vertical CRM logic into a
  generic eval platform works against their platform economics.
- **vs Vantage / Finout / CloudZero:** they own the invoice but operate
  entirely post-hoc. They cannot gate a deployment.

Gemini's verbatim endorsement: "I explicitly endorse this as the ONE
direction. It is structurally sound, isolates a distinct buyer (Support
Ops / RevOps), and leverages the 'messy plumbing' of CRM integrations as
a shield against dev-tool incumbents."

## Falsifiable claim

5 high-volume support-agent design partners, 30-day timebox. Thesis is dead
if fewer than 2 teams block a deployment and rewrite a prompt purely
because Averth flagged a unit-economic threshold violation.

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
