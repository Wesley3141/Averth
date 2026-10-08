# Averth Pilot Agreement (Template)

> DRAFT — have counsel review before use. This is a starting template, not
> legal advice.

## 1. Scope

Averth will perform **one** bounded workflow review:

- **Workflow:** [name / entry point — one workflow only]
- **Duration:** [N] business days from kickoff ("[date]")
- **Customer time commitment:** ~4 hours total across the engagement
  (1h workflow walkthrough, 1h acceptance-criteria definition,
  2h patch review and landing)

No additional workflows, no custom statements of work. Additional work
requires a separate agreement.

## 2. What Averth delivers

1. Baseline measurement: cost per accepted task and quality metrics on
   representative tasks, using customer-approved acceptance criteria.
2. Controlled experiments: [2–4] targeted changes tested against the baseline.
3. A proposed patch (config or code diff) with supporting evidence.
4. Pairing support to land the patch in the customer's repository.
5. A comparison report showing improvements **and** regressions, with full
   experiment economics (including what the experiments themselves cost).

## 3. Success criteria (pre-registered)

The engagement succeeds if, on held-out cases agreed before experiments begin:

- Cost per accepted task is reduced by **≥20%**, and
- Acceptance rate is not worse than baseline by more than **[δ]**,
  measured with 95% confidence intervals.

If criteria are missed, the customer owes **50%** of the fee (Section 4).
Averth will report the miss plainly, including what was tried.

## 4. Fee

**$[8,000–15,000]** fixed fee, invoiced [50% at kickoff / 50% at delivery].
No hourly billing, no overages. If success criteria (Section 3) are missed,
the second invoice is reduced to 50%.

## 5. Walk-away

Either party may terminate with written notice. On termination, the customer
owes only for completed milestones. Averth delivers all work product produced
to date.

## 6. Data

- Default: Averth's harness runs **inside the customer's environment**.
  Only aggregated, customer-approved results leave the customer's systems.
- If the customer opts into sharing redacted traces: redaction is performed
  by Averth's customer-side redactor with an auditable report; the customer
  reviews the redaction report before any data is shared.
- Retention: 30 days after engagement end, then deleted.
- Averth does not train models on customer data.

## 7. Experiment data rights

Anonymized experiment metadata (workflow pattern, intervention type, measured
effect size — **no prompts, no traces, no customer data**) may be retained by
Averth for cross-customer research. The customer may opt out in writing;
opt-out does not affect the fee.

## 8. Confidentiality

Each party's non-public information stays confidential. Standard mutual NDA
terms apply for [2] years.
