# 10-Reviewer Verdict Synthesis — Demo Benchmark Plan
**Date:** 2026-10-07 (evening CDT) · **Verdict file:** `hidden_files/review-verdicts-2026-10-07.md`

## Tally

- **REAL: 0 / 10**
- **NEEDS WORK: 9** (Adversary, Buyer, Incumbent/LangSmith, Experimentalist, Engineer, Security, Economist, Cynic, Operator)
- **NOT REAL: 1** (Moat Hunter)

**The unanimous gate failed.** No M4 build work, no push to main. That is the honest result, and it is the correct one: every reviewer found the same class of problem — the v1 spec was a set of promises, not a protocol.

## What the reviewers converged on (grouped fixes)

### 1. Arm B is a strawman (1, 4, 5, 9, 10)
"One strong Claude/Cursor pass + $200" is not what a real engineer would do. Fix: arm B = **time-boxed genuine effort (2 engineer-days)**, run by the most skeptical operator, **Claude + LangSmith** (LangSmith is the real incumbent and the free tier exists — it must be in arm B), documented prompts and hours, **engineer-hours as a secondary metric** (otherwise "less work for your engineers" is never tested). Arm B's artifact is **committed before arm C begins** (different operators or frozen parallel protocols) to prevent insight leakage. The report must state plainly what B does and does not represent.

### 2. Statistics: promises, not a protocol (4, 5, 9, 1)
A **pre-registration document is committed before any arm runs** covering:
- Primary metric is a **ratio estimator** (cost per accepted task): use bootstrap CIs / delta method; define behavior when zero accepts; it conflates cheaper-at-equal-quality vs pricier-at-higher-acceptance → add a **non-inferiority margin on acceptance rate**; name the **primary contrast C vs B** explicitly.
- **Power analysis under heavy tails**: costs have CV~1.5; ~390 held-out cases/arm needed to detect a 30% reduction. Size held-out from the math, and **go/no-go if N is unaffordable**.
- **Robust estimators**: means die on outliers → trimmed mean / median + tail share. Report p50/p95/max per arm.
- **Grader**: 2 graders + kappa; **pre-registered disagreement invalidation** (<90% agreement → benchmark fails). Grader is the whole game — it becomes **M0.5**: task set + grader + fixture strategy as an explicit milestone.
- **Fixture vs live**: fixtures for iteration only; **live results are the decision metric**. Report both separately.
- Workflow selected **blind to headroom** or labeled as an upper bound.

### 3. Numeric kill criteria (1, 7, 9, 10)
Pre-register: **C beats B by >20%, p<0.05, payback <6 months at partner volume**; miss → kill/pivot, no re-interpretation. Service line: price >$18K, delivery <$6K, hit rate >60%; kill if miss by >25% after 5 engagements. "Worthwhile" = **>25% reduction on >$15K/mo spend, CI lower bound >10%**, else walk away by rule. If arm B matches C, report that too — and that is fatal to the thesis.

### 4. Economics: the demo de-risks the wrong question (7)
Engagement costs ~$6K (8-12 eng-days + $1K experiment spend); 40-60% hit rate needs $15-25K price — which competes with the customer's own engineer + Claude and hits procurement. 10-15% savings on a $10K/mo workflow has ~zero NPV after payback. **Only outlier hunting clears**: 25%+ on $20K+/mo workflows. The causal corpus needs ~100 engagements ($300-720K), depreciates in ~9 months as model pricing shifts quarterly — **the flywheel is a treadmill**; cap the corpus at 15 engagements until the SaaS math is proven. Only viable shape identified: **CI monitoring SaaS with the service as CAC** ($6K CAC vs $21.6K LTV, needs >35% conversion). Add **M3b commercial gate**: take the benchmark report to 5 target operators; gate = **one signed paid pilot**. Technical win alone = park. M3.5: $40K/8 weeks for 5 paid pilots at $8K; gate = >3/5 convert to monitoring.

### 5. The moat thesis is dead as stated (8) — NOT REAL
Causal graph priors don't transfer: workflows are bespoke, effect sizes don't generalize across stacks, most valuable priors are customer-specific. No sharing mechanism exists in the spec (traces contain prompts/IP, tool schemas, PII; no CISO approves exfil; no anonymization, DP, federated, or legal design). LangSmith/providers sit on population-scale data; causal purity loses to 1000x observational scale + structural position. CI embeddedness is a feature, not a moat: noisy gates get disabled after the first false block. Surviving moat candidates: **(a)** verticalized priors (one harness class), **(b)** the boring moat — **own the invoice join** (customer-side reconciliation), **(c)** honest distribution/DX moat, or **(d)** admit the service IS the business (high-margin consultancy, not venture software). **This needs Wesley's explicit pick.**

### 6. Security sequencing (6)
M1-M3 on our own infra: zero customer-security exposure, fine to build now. All customer-facing motions die as written: "redacted logs" is wishful (traces contain secrets/PII you can't grep) → **redaction as code** (customer-side, auditable ruleset, redaction report) or an allowlist trace schema. "Run inside customer environment" = 3-6 month security review → **one deployment model: signed container, no phone-home except approved results payload, egress allowlist**; start the **SOC 2 Type I clock now**. CI gates = supply-chain risk → pinned/signed releases, SBOM, least-privilege, documented fail-open/closed. Billing join drags finance in → **reconcile customer-side, only aggregated deltas leave** the VPC; or drop from pilot scope. Publish security page + DPA template (30d retention, no training, subprocessor list) **before** outreach. Data rights clause written into the pilot template NOW.

### 7. Service as a contract, not an adjective (2, 9, 10)
Replace "walk away" with a **written pilot agreement**: fixed fee ($8-15K band), pre-registered success criteria (>20% reduction at equal/better quality), **reduced fee (50%) if missed**, one-page order form, W-9, DPA ready before the first call. Time ask named in outreach: **"about 4 hours of your team's time across two weeks."** Extend the offer through deployment: pair to land the patch + install the CI gate; a report alone evaporates. **Circuit breaker**: services >X% of team time for Y weeks → halt (name X, Y); don't start N+1 unless the prior harness covers >60% of setup; two consecutive <40% sharing → stop selling services. Rule: **no number leaves the repo without a source experiment ID.**

### 8. Gate redesign (10)
The unanimity gate is theater and sequenced backwards. Replace with: **M3 numbers are the gate; founder halt reserved; majority rules; merge freely with normal review.** M1-M3 buildable now (they need the rigor most); the gate blocks M4 (patch gen) and pilot motions.

### 9. Architecture: the control plane is missing (5)
Passive metering vs actively varying a workflow needs interception. Two options: **(a)** per-agent fork (demo-fast, non-general) or **(b)** proxy/gateway layer (e.g., LiteLLM-style; 3-4 weeks, real product, different adoption story). Name it as an M2 dependency — the spec currently picks neither. "Billing reconciliation" = **explained-delta report** (estimated vs billed, every component labeled, residual shown); defer provider billing-API integrations until after M3. Per-provider usage fields enumerated (Anthropic cache tokens, OpenAI cached_tokens, Gemini thought tokens, Bedrock gaps) with per-provider validation tests in CI. Research-disguised-as-engineering (causal graph transport, general enterprise billing reconciliation) labeled as vision, not milestones. Estimated timeline, 2-3 engineers: M1 1-2wk, M0.5 2-3wk, M2 3-4wk, M3 1-2wk = **~8-11 weeks to demo**.

### 10. Buyer straddle (2, 3)
Publish the benchmark BEFORE any outreach. The cost owner (FinOps) is the real opening — **LangSmith doesn't sell there, but the spec targets operators. Pick one.** Cost optimization is important-not-urgent; **trigger events (bill spike, board question, re-architecture)** get the reply, not copy. Flip the data motion: self-serve harness customer runs in own VPC; Averth analyzes exported aggregates only.

## Recommendation

1. **Accept the failure**: the gate did its job. No build, no push.
2. **Adopt the v2 spec** (drafted at `hidden_files/DEMO_BENCHMARK_SPEC_v2_draft.md`), which folds in every fix above.
3. **Two decisions that can't be delegated to a document:**
   - **Moat**: verticalize, invoice-join, CI-embeddedness + DX, or admit services. The Moat Hunter's verdict stands until one is chosen and designed.
   - **Gate**: replace unanimity with M3-numbers + founder-halt + majority.
4. Re-run the review on the v2 spec with a **narrowed question** ("does the revised plan survive?"), then build M0.5-M3.
