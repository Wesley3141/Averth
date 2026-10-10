# Averth Demo Benchmark Spec — v2 (hardened, 2026-10-07)
**Status: DRAFT, local only.** The 10-reviewer gate failed (0/10 REAL), so nothing in this spec pushes to main until the gate is re-run and passes. This draft folds in every fix from `REVIEW_SYNTHESIS_2026-10-07.md`.

## Goal (unchanged)

One convincing, reproducible demo answering a single question: does Averth's measured experiment loop beat what a competent engineer does with Claude/Cursor + LangSmith? If it can't, we learn that on a benchmark, not in front of a customer.

## The three arms

| Arm | What it tests |
|---|---|
| A. Original open-source agent, unchanged | Starting performance |
| B. Agent after a **time-boxed genuine engineering effort** (2 engineer-days): Claude/Cursor + LangSmith, run by the most skeptical operator, documented prompts and hours | The real alternative — a competent engineer with the actual incumbent tooling |
| C. Agent improved through Averth's measured experiment loop | Whether our process adds value beyond B |

Same development cases, same API-spend ceiling, plus a **time box on B**. Arm B's artifact is **committed before arm C begins** (different operators or frozen parallel protocols) — no insight leakage. Engineer-hours on B is a secondary metric: "less work for your engineers" is otherwise never tested. The final report states plainly what B does and does not represent.

## Fairness rules

- **Pre-registration document committed before any arm runs.** It covers: quality thresholds, the non-inferiority margin on acceptance rate, the explicit primary contrast (C vs B), the statistical plan below, grader design, and kill criteria. No moving goalposts after results.
- Same spend ceiling AND time box for B and C.
- **Test changes individually before combining:** context reduction, step-specific model routing, retry/fallback policy.
- Repeat runs to expose variability.
- **Numeric kill criteria, pre-registered:** C beats B by >20%, p<0.05, payback <6 months at partner volume → miss = kill/pivot, no re-interpretation. If B matches C, report that. That outcome is fatal to the thesis and is a useful answer.

## Scope

- **One workflow:** a read-only research or issue-triage agent with multiple tool calls and explicit, checkable outputs. **Selected blind to headroom**, or labeled as an upper bound. Baseline-measure 2-3 candidates first, pick the richest cost structure (visible retries, context growth, model-choice sensitivity).
- **Our infrastructure.** Public inputs, pinned source revision, fixed tool-response fixtures **for iteration only**; **live results are the decision metric**. Distinguish fixture-based from live-integration numbers in every table. Do not run the first demo inside a customer environment (security review kills momentum); port it later.
- **One framework wedge** for the entry-point abstraction (e.g., LangGraph). A universal adapter is the graveyard; name the wedge.

## Measurement protocol

Per run record: model/version, input/output tokens, per-provider usage fields (Anthropic cache tokens, OpenAI cached_tokens, Gemini thought tokens, Bedrock gaps — enumerated, with per-provider validation tests in CI), cache usage, retries, tool charges, pricing date, missing data. **Estimated charges labeled as estimates, always.**

- **"Billing reconciliation" is defined as an explained-delta report**: estimated vs billed, every component labeled, residual shown. Provider billing-API integrations deferred until after M3. Reconcile against provider billing where available.
- **Failure language**: a failed attempt incurred cost, but that does not automatically mean its entire cost was avoidable. The experiment establishes what can actually be reduced.
- **Provenance rule**: no number leaves the repo without a source experiment ID.

## Statistics and grading (M0.5: task set + grader + fixture strategy is an explicit milestone)

- **Primary metric (pre-registered):** cost per accepted task — a **ratio estimator**. Use bootstrap CIs or delta method; define behavior when zero accepts; it conflates cheaper-at-equal-quality vs pricier-at-higher-acceptance → **non-inferiority margin on acceptance rate**, primary contrast C vs B named explicitly.
- **Robust estimators**: trimmed mean / median + tail share instead of raw means (heavy tails make means meaningless). Report p50/p95/max per arm.
- **Power analysis under heavy tails** (CV~1.5): ~390 held-out cases/arm to detect a 30% reduction. Size the held-out set from the math; **go/no-go if N is unaffordable** — don't spend, don't spin.
- **Grading:** automated checks primary (exact labels, citation validity, tool-error absence). **2 human graders + kappa agreement; pre-registered invalidation** (<90% agreement → benchmark fails). Human validation sample of at least 20% to validate the automated grader itself.
- **Budget:** cap total demo spend up front (propose $1,500). **Disclose everything**, including optimization-experiment cost. Payback disclosure: how many future tasks recover the experiment expense, under stated assumptions. If payback computes "never," publish that.

## Acceptance checks

Task correctness, required evidence, tool errors, completion rate, latency, cost per accepted task — all pre-registered, all reported, improvements AND regressions.

## Deliverables

- A proposed patch (config or code diff) an engineer can actually apply — affected step, supporting evidence, implementation, remaining uncertainty.
- Reproducible commands.
- A comparison report showing improvements and regressions.
- Full economics, including the payback computation.

## Build order

- **M0.5: task set + grader + fixture strategy.** The grader is the whole game (Goodhart); it gets its own milestone with a disagreement procedure written down before any arm runs.
- **M1: measurement harness.** Per-run cost recording, labeled estimates, explained-delta reconciliation. ~60% exists (tracker.py); remaining is plumbing. Narrow: one provider, one workflow shape; reconciliation gap <10% before M2.
- **M2: experiment runner.** Baseline vs controlled alternatives, holdback cases, repeat runs. **Control-plane decision first**: (a) per-agent fork (demo-fast, non-general) or (b) proxy/gateway layer (3-4 weeks, real product, different adoption story). The spec picks one before building.
- **M3: three-arm benchmark.** The demo in this spec. **Gate: M3 numbers.** If they pass kill criteria → M4. Technical win alone = park (see M3b).
- **M3b: commercial gate.** Take the benchmark report to 5 target operators; **gate = one signed paid pilot**. Skip = park the technical demo.
- **M3.5: paid pilots.** ~$40K/8 weeks for 5 paid pilots at $8K; gate = >3/5 convert to monitoring. Engagement unit economics pre-committed: price >$18K, delivery <$6K, hit rate >60%; kill the service line if miss by >25% after 5.
- **M4: patch generation.** Diff + evidence + uncertainty.
- **M5: CI regression check.** Saved benchmark, re-run on prompt/model/workflow changes.

**Estimated timeline (2-3 engineers):** M1 1-2wk, M0.5 2-3wk, M2 3-4wk, M3 1-2wk = **~8-11 weeks to the demo.**

## Gate (redesigned per reviewer 10)

The unanimity gate was theater. New gate: **M3 numbers are the gate; founder halt reserved; majority rules; merge freely with normal review.** The gate blocks M4 and customer pilot motions, not M0.5-M3.

## The pilot offer (when M3b arrives)

Written pilot agreement, not "walk away": fixed fee ($8-15K band), pre-registered success criteria (>20% reduction at equal/better quality), **reduced fee (50%) if missed**, one-page order form, W-9, DPA ready before the first call. Time ask named in outreach: **"about 4 hours of your team's time across two weeks."** Extend through deployment: pair to land the patch + install the CI gate — a report alone evaporates. **Publish the benchmark before any outreach.** Flip the data motion: customer runs the self-serve harness in their own VPC; Averth analyzes exported aggregates only. **Circuit breaker**: services >X% of team time for Y weeks → halt (X, Y named); don't start N+1 unless the prior harness covers >60% of setup; two consecutive <40% sharing → stop selling services.

## Security (parallel track, starts now)

- SOC 2 Type I clock starts now.
- Security page + DPA template (30d retention, no training, subprocessor list) published before any outreach.
- **Redaction as code**: customer-side, auditable ruleset, redaction report — or an allowlist trace schema. "Redacted logs" as a phrase dies.
- One deployment model: signed container, no phone-home except an approved results payload, egress allowlist. No customer-environment runs promised until this is survivable.
- CI gates: pinned/signed releases, SBOM, least-privilege, documented fail-open/closed.
- Data rights clause written into the pilot template now. Cross-customer data rights resolved before M2.

## Moat: what compounds (and what doesn't) — rewritten

Blunt: today there is no moat, and the v1 moat section was wrong. The causal experiment graph **does not transfer**: workflows are bespoke, effect sizes don't generalize across stacks, the valuable priors are customer-specific and stay with the customer, there is no sharing mechanism (traces carry IP and PII; no CISO approves exfil), and LangSmith/providers own population-scale data plus the pricing lever. The service-to-software flywheel is asserted, never evidenced — name the evidence or stop saying it.

What could compound (pick one before M4):

1. **Verticalized priors.** Causal priors within one harness class (e.g., LangGraph triage agents), where stack similarity is high enough that transfer is real. Narrow, testable, evidence-first.
2. **The boring moat: own the invoice join.** Reconcile customer-side; aggregated deltas are the product surface. Boring = defensible.
3. **CI embeddedness + DX.** Stickiness one repo at a time — but only if gates are trustworthy enough that nobody disables them. Noisy gates get deleted; this moat is earned by the benchmark quality.
4. **Admit the service is the business.** High-margin consultancy with excellent tooling is an honest company; it is not venture software.

**Wesley's explicit pick required.** Until then: cap the experiment corpus at 15 engagements, label causal-graph transport as vision, not a milestone.

## Risks (updated)

1. **B ties C.** The most likely death (context trim, routing, retry limits found by a real Claude+LangSmith pass in the first hour). Mitigate: genuine B, and treat the tie as the answer it is.
2. **Statistics eat the demo.** High variance, overlapping CIs, "inconclusive." Mitigate: power math before spending, robust estimators, pre-registered go/no-go.
3. **Measurement never trustworthy enough.** M1 easy on fixtures, hard in production. Mitigate: brutal M1 scoping (one provider, one workflow shape, gap <10%).
4. **Incumbent ships the tab.** LangSmith cost-per-experiment = one quarter's work. Named answer required: what we do the quarter LangSmith ships cost attribution.
5. **Service wedge becomes permanent consulting.** Mitigate: the circuit breaker above, hard numbers.
6. **Fixture overfit.** Mitigate: fixtures for iteration, live for decisions, fixture-miss policy decided up front.

## Positioning notes (unchanged)

- Sell the bounded outcome first ("one workflow to a measured improvement"), Averth as the instrument. Brutally bounded: fixed scope, walk away if no improvement.
- Never claim customers can't DIY with bills, traces, and spreadsheets. Claim: a faster answer and a reproducible before/after.
- LangSmith does experiment comparisons and evals. The bet is the complete path: expensive workflow → tested change → implementation → continuing cost and quality checks. Whether customers value that enough is what this benchmark starts to test.
- Pick the buyer: cost owner (FinOps) is the opening LangSmith doesn't sell into — but the spec currently targets operators. **Pick one.**
- Target **trigger events** (bill spike, board question, re-architecture), not personas. Cost optimization is important-not-urgent; the trigger gets the reply.
