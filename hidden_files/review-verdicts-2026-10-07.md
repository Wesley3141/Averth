# 10-reviewer verdicts (arriving)

## Reviewer 10 (Operator) — NEEDS WORK
- Unanimity gate is theater, sequenced backwards: M1-M3 ungated, gate blocks M4/main. Replace with: M3 numbers are the gate; founder halt; majority rules; merge freely with normal review.
- Arm B risks strawman: "one strong pass" + $200 != real engineer. Fix: time-boxed genuine effort (2 engineer-days, skeptic operator, documented prompts/hours); report must state what B does/doesn't represent.
- Add M3b commercial gate: benchmark report to 5 target operators; gate = one signed paid pilot. Technical win alone = park.
- Service bound as contract not adjective: fixed price, one workflow, N days, walk-away clause, no custom SOWs; circuit breaker: services > X% of team time for Y weeks -> halt. Name X, Y.
- Illustrative stat will become fake stat: label/delete; rule: no number leaves repo without source experiment ID.

## Reviewer 6 (Security Pragmatist) — NEEDS WORK
- M1-M3 on own infra: zero customer-security exposure, fine to build now. All customer-facing motions die as written.
- "Redacted logs" = wish about someone else's diligence; traces contain secrets/PII you can't grep. Fix: ship redaction as code (customer-side, auditable ruleset, redaction report) or allowlist trace schema.
- "Run inside customer environment" = vendor code execution + egress + secrets in their VPC, 3-6 month review. Fix: one deployment model, signed container, no phone-home except approved results payload, egress allowlist; start SOC 2 Type I now.
- CI gates = supply-chain risk. Fix: pinned/signed releases, SBOM, least-privilege, documented fail-open/closed.
- Billing join drags finance in. Fix: reconcile customer-side, only aggregated deltas leave; or drop from pilot scope.
- No data governance: publish security page + DPA template (retention 30d, no training, subprocessor list) before outreach.
- Sequencing: build M1-M3 now; fixes 1/4/5 in parallel (days); start SOC 2 clock now; don't promise in-env runs or CI gates until survivable.

## Reviewer 4 (Experimentalist) — NEEDS WORK
- Fairness rules are promises, not protocols; every load-bearing number deferred.
- Power analysis vapor: heavy-tailed costs (CV~1.5) need ~390 held-out cases/arm to detect 30% reduction; MDE and go/no-go if N unaffordable unwritten.
- Primary metric is a ratio estimator: needs delta method/Fieller/bootstrap CIs, undefined if zero accepts; conflates cheaper-at-equal-quality vs pricier-at-higher-acceptance. Need non-inferiority margin on acceptance rate; primary contrast C vs B named explicitly.
- Arm B: spend ceiling caps API dollars but human hours unpriced/unbounded; "less work for engineers" untested without measuring engineer-hours as secondary metric.
- Arm contamination: same team runs B and C, insights leak. Fix: B artifact committed before C begins (or frozen parallel protocols), different operators.
- Grader: need 2 graders + kappa, pre-registered disagreement invalidation threshold (<90% agreement -> benchmark fails).
- Fixture/live: name live results as the decision metric, fixtures for iteration only; report p50/p95/max per arm.
- Fix: pre-registration document committed before any arm runs with all of the above.

## Reviewer 7 (Economist) — NEEDS WORK
- Hit-rate x price doesn't clear: engagement costs ~$6K (8-12 eng-days + $1K experiment spend); 40-60% hit rate needs $15-25K price, which competes with customer's own engineer + Claude and hits procurement friction.
- 10-15% savings (most likely outcome) doesn't survive payback math on $10K/mo workflow: NPV ~zero. Need 25%+ on $20K+/mo workflows = outlier hunting.
- Causal corpus needs ~100 engagements ($300-720K), depreciates in ~9 months (model pricing shifts quarterly). Flywheel is a treadmill.
- Demo de-risks wrong question; economic validation needs 5-10 paid engagements ($30-60K), unbudgeted/ungated.
- Only viable business: CI monitoring SaaS with service as CAC ($6K CAC vs $21.6K LTV = 3.6:1, needs >35% conversion). Causal graph is sales asset, not moat; CI embeddedness is the real moat.
- Fixes: engagement unit economics pre-commit (price >$18K, delivery <$6K, hit rate >60%; kill if miss by >25% after 5); "worthwhile" = >25% reduction on >$15K/mo spend, CI lower bound >10%, else walk away by rule; M3.5: $40K/8 weeks for 5 paid pilots at $8K, gate >3/5 convert to monitoring; model as SaaS-with-service-CAC; cap corpus at 15 engagements until SaaS math proven.

## Reviewer 9 (Cynic) — NEEDS WORK
- Death 1 (most likely): Arm B ties arm C. Obvious levers (context trim, routing, retry limits) found by Claude pass in first hour; rigor != better answer. Fatal to company thesis. Early warning: skeptic's arm B converges on same 3 interventions as planned arm C in first session.
- Death 2: service wedge becomes permanent consulting. <20% reuse between engagements, 3-6 week security review per deal. Needs enforceable circuit breaker: don't start N+1 unless prior harness covers >60% of setup; two consecutive <40% sharing = stop selling services.
- Death 3: measurement never trustworthy enough. M1 easy on fixtures, impossible in production (multi-provider, cached tokens, tool billing, aggregates by key not trace). Fix: scope M1 brutally narrow (one provider, one workflow shape), reconciliation gap <10% before M2.
- Death 4: incumbent ships the tab. LangSmith cost-per-experiment = one quarter's work. Need named answer to "what do we do the quarter LangSmith ships cost attribution."
- Death 5: statistics eat the demo. High variance, overlapping CIs, "inconclusive." Power math before spending is the circuit breaker.
- Flip to REAL: arm C beats B by margin surviving payback math (net of experiment cost). Flip to NOT REAL: B ties C and team builds anyway.

## Reviewer 2 (Buyer) — NEEDS WORK
- Pain real, offer shape buyable, but dies 3x: inbox (no credibility), security (no sane company hands prompts/logs to unknown tiny team), procurement (no paperwork).
- Publish three-arm benchmark BEFORE any outreach. No benchmark, no meeting.
- Flip the data motion: self-serve harness customer runs in own VPC; Averth analyzes exported aggregates only. "Send us logs" = opt-in, not default.
- Replace "walk away" with written pilot agreement: fixed fee ($8-15K band), pre-registered success criteria (>20% reduction at equal/better quality), reduced fee (50%) if missed. One-page order form, W-9, DPA ready before first call.
- Name the time ask in outreach: "about 4 hours of your team's time across two weeks."
- Extend offer through deployment: pairing to land patch + install CI gate. Report alone evaporates.
- Targeting: cost optimization is important-not-urgent; trigger (bill spike, board question, re-architecture) gets the reply, not copy.

## Reviewer 8 (Moat Hunter) — NOT REAL
- Causal graph priors don't transfer: workflows are bespoke, effect sizes don't generalize across stacks; most valuable priors are customer-specific and stay with the customer.
- Corpus can't be built: traces contain prompts (IP), tool schemas, PII; no CISO approves exfil; spec has zero sharing mechanism (no anonymization, DP, federated, legal). Chicken-and-egg fatal while LangSmith/providers sit on population-scale data.
- Causal purity loses to 1000x observational scale + structural position (providers own pricing lever and can A/B at platform level).
- CI embeddedness is a feature not moat: noisy gates get disabled after first false block; migration = deleting one YAML file once LangSmith ships it.
- Service-to-software flywheel asserted never evidenced; devtools precedent is Palantir (services wearing software costume). "Better priors -> more engagements" wished into existence.
- Real moat would require: data gravity (be system of record / execution layer, not observer), sharing mechanism designed day one, or honest distribution/DX moat, or admit service IS the business (high-margin consultancy, not venture software).

## Reviewer 3 (Incumbent / LangSmith PM) — NEEDS WORK
- Copy timelines: experiment runner = already shipped. Cost per accepted task = 4-8 weeks. Patch generation = would not ship (liability). CI regression gates = 2-6 weeks. Billing reconciliation = 1-2 quarters, likely never (buyer doesn't own invoice).
- "Complete path" = bundle of commodities; only novel leg is patch diff, and it's a services artifact.
- Causal graph: incumbents run orders of magnitude more experiments; data moats don't hold at 100x disadvantage.
- CI embeddedness not exclusive; LangSmith SDK already in their CI. Stickiness accrues to whoever lands first per repo.
- Service flywheel asserted not designed; spec never defines what "software-izable" looks like.
- Buyer straddle: cost owner (FinOps) is the real opening (LangSmith doesn't sell there) but spec targets operators. Pick one.
- Harder to copy: verticalize priors (one harness class); public repeating benchmark leaderboard; own the invoice join (boring = moat); sell to budget owner not builder.
- Hardest to replicate: the service motion aimed at cost owner — defensible by neglect only, until cost-per-task becomes top-3 buyer priority.

## Reviewer 1 (Adversary) — NEEDS WORK
- Steelman: good engineer with Claude + LangSmith free tier reproduces M1-M5 in ~5 days, ~$50 API. "Complete path" = doing all steps in order, which any motivated engineer does. "For them" is a feature, not a company.
- Entry-point abstraction is the hard problem, hand-waved as input assumption. Universal adapter = graveyard; wedge to ONE framework (e.g., LangGraph).
- All three moats are post-victory moats (need dozens of engagements; cold start zero; transferability asserted; CI stickiness = sales not moat; flywheel circular).
- Arm B strawman: real competitor = Claude + LangSmith + 2 weeks of engineer iteration. Put LangSmith in arm B.
- Benchmark tests technical superiority not WTP; payback disclosure may compute "never pays back."
- "Meaningful savings" is a vibe; workflow selection = selection bias toward headroom. Fix: pre-register numeric kill criteria (C beats B by >20%, p<0.05, payback <6 months at partner volume; miss -> kill/pivot, no re-interpretation).
- Fixes: wedge to one framework; signed design-partner LOI before M2 ("cut by X% we pay $Y"); arm B = Claude+LangSmith with skeptic; numeric kill criteria; resolve cross-customer data rights NOW (write clause into pilot template); select workflow blind to headroom or label as upper bound.

## Reviewer 5 (Engineer) — NEEDS WORK
- M1 60% built (tracker.py already does per-run cost, retry-branch waste, price-vintage, estimate flags). Remaining M1 = plumbing.
- Missing architecture between M1 and M2: the control plane. Passive meter vs actively varying workflow needs interception. Two options: (a) per-agent fork (demo-fast, non-general), (b) proxy/gateway layer like LiteLLM (real product, 3-4 weeks, different adoption story). Spec picks neither. Name it as milestone dependency.
- "Billing reconciliation" undefined = rabbit hole. Define as explained-delta report (estimated vs billed, every component labeled, residual shown); defer provider billing-API integrations until after M3.
- Statistics break on heavy tails: mean CIs dominated by outliers -> inconclusive. Fix: robust estimator (trimmed mean / median + tail share), power analysis with heavy-tail assumption, minimum held-out N from that math.
- Fixture fidelity breaks first: unbounded tool-call space, temperature divergence. Spec lists as risk but needs milestone + fixture-miss policy decided up front.
- No milestone owns the grader; grader is the whole game (Goodhart). Need M0.5: task set + grader + fixture strategy as explicit milestone, disagreement procedure written down.
- Per-provider usage fields must be enumerated (Anthropic cache tokens, OpenAI cached_tokens, Gemini thought tokens, Bedrock gaps) with per-provider validation test in CI.
- Research-disguised-as-engineering: causal graph transport, general enterprise billing reconciliation. Label as vision, not milestones.
- Timeline 2-3 engineers: M1 1-2wk, M0.5 2-3wk, M2 3-4wk, M3 1-2wk = ~8-11 weeks to demo.
