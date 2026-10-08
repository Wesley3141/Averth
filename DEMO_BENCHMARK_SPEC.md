# Averth Demo Benchmark Spec — v3

Incorporates all fixes from the 10-reviewer round (2026-10-07). Verdicts were
0 REAL / 9 NEEDS WORK / 1 NOT REAL. This revision addresses every objection.
Full verdict log: `hidden_files/review-verdicts-2026-10-07.md`.

## Goal

One convincing, reproducible benchmark answering: does Averth's measured
experiment loop beat what a competent engineer does with Claude + LangSmith?
If it can't, we learn that on a benchmark, not in front of a customer.

Scope discipline: this spec governs the **benchmark** (M0.5–M3). It does not
govern the company. Company claims (moat, flywheel, service motion) are
explicitly parked until M3 + M3b clear.

## The three arms

| Arm | What it tests |
|---|---|
| A. Original agent, unchanged | Starting performance (sanity anchor) |
| B. Agent after a genuine Claude + LangSmith optimization pass | The real alternative a competent engineer tries |
| C. Agent improved through Averth's measured experiment loop | Whether our process adds value beyond B |

Same development cases and the same dollar budget for optimization experiments
in B and C. Evaluate all arms on separate, held-out cases.

## Fairness rules (protocol, not promises)

- **Arm B is the real competitor.** Not "one strong prompt": a time-boxed
  genuine effort (2 engineer-days) by a designated skeptic trying to win, with
  Claude + LangSmith evals available, all prompts and hours committed to git.
  The report must state explicitly what arm B does and does not represent (a
  bounded pass, not weeks of production iteration).
- **Arm isolation.** Arm B's final artifact is committed before arm C begins.
  Different operators where possible. Insights must not leak between arms.
- **Pre-registration document, committed before any arm runs**, containing:
  - Minimum detectable effect and N per arm, computed from baseline-measured
    cost variance (assume heavy tails; see Statistics).
  - Primary contrast named explicitly: **C vs B** (A is a sanity anchor).
  - **Non-inferiority margin on acceptance rate** (δ): C wins only if
    cost-per-accepted-task is lower AND acceptance is not worse than B by more
    than δ, with CIs on both. Plus a latency ceiling.
  - Arm B protocol: max wall-clock hours, max API spend, prompts in git.
  - Grader-disagreement invalidation threshold (e.g., <90% human-automated
    agreement on accepts → benchmark fails, no re-interpretation).
- **Numeric kill criteria (pre-registered):** arm C beats arm B by ≥20% on cost
  per accepted task at equal-or-better quality (per the non-inferiority rule),
  p<0.05 on held-out cases, AND projected payback <6 months at realistic
  volume, net of experiment cost. Miss → kill or pivot. No re-interpretation.
- **Human labor is a measured variable.** Log engineer-hours for both
  optimization arms. The product claim is "less work for your engineers";
  unmeasured labor tests nothing.
- **Workflow selection blind to headroom.** Baseline-measure candidates, then
  pick by pre-registered criteria (representative of a customer workflow), not
  "richest cost structure." If the pick has unusual headroom, label the result
  as an upper bound, not a typical outcome.

## The gate (replaces the unanimity rule)

The 10-reviewer unanimity gate is retired: the numbers decide, not a vote.
Normal branch review governs merges to main.

- **Technical gate:** the pre-registered kill criteria above. Pass → proceed.
  Fail → kill or pivot. Inconclusive → report as inconclusive, do not ship
  "18% ± 22%" as a win.
- **Commercial gate (M3b):** take the benchmark report to five target
  operators. Gate = **one signed paid pilot** for a bounded engagement.
  Technical win without a buyer = park, not proceed.
- **Economic gate (M3.5):** after the demo, budget $40K / 8 weeks for 5 paid
  pilot engagements at a discounted $8K each. Goal is learning, not margin.
  Gate: ≥3 of 5 convert to paid monitoring pilots. Miss → kill the wedge
  before building M4/M5.

## Demo workflow selection

Baseline-measure 2–3 candidates, pick per pre-registered criteria. Candidates:

- **GitHub issue triage agent:** classify, route, draft first response.
  Acceptance: correct label/project, no hallucinated facts. Cheap runs, clean
  checks.
- **Read-only research agent:** answer technical questions with citations.
  Acceptance: correct answer, valid citations, no unsupported claims.

Requirements: multiple tool calls per run, explicit checkable outputs, public
inputs, pinned revision, cheap enough for hundreds of runs. Constrain the
integration to **one framework** (pick one; depth beats universality — a
universal adapter is a graveyard).

## Control-plane decision (M2 dependency — decide before building M2)

M1 is a passive meter; M2 must actively vary the workflow. Two architectures:

- **(a) Per-agent fork:** modify the chosen agent to expose knobs
  (model-per-step, context trim, retry policy). Fast, demo-suitable, does not
  generalize. Validates the demo, not the product.
- **(b) Proxy/gateway layer:** all model calls flow through an
  Averth-controlled client wrapper (LiteLLM-style) that logs, prices, and
  enforces per-step routing and context policies. Real product architecture,
  ~3–4 weeks, different adoption motion (infrastructure traffic flows through).

Demo may use (a). The product path is (b). Do not let M2 proceed without naming
which is being built.

## M0.5: task set + grader + fixture strategy (explicit milestone)

Nobody starts M2 until this is done:

- Task set constructed from public inputs, pinned.
- **Grader implemented and validated:** automated checks primary (exact labels,
  citation validity, tool-error absence). Two human graders + kappa on a
  calibration subset. **Disagreement procedure written down before grading:**
  if human-automated agreement on accepts falls below the pre-registered
  threshold, the benchmark is invalid — relabel nothing, rerun nothing,
  report the failure.
- **Fixture strategy decided up front:** fixed tool-response fixtures for
  iteration; **live-integration results are the decision metric.** Fixture-miss
  policy specified (fail the run? fall back to live and record?). Fixtures
  mute the heavy-tail surprises the product claims to fix — never let the
  decision rest on fixtures alone.

## Statistics (fixed for heavy tails)

- Primary metric: cost per accepted task is a **ratio estimator** — use the
  delta method, Fieller, or bootstrap for CIs, not mean ± 1.96·SE. Undefined
  if an arm accepts zero tasks; pre-register the fallback.
- Use a **robust estimator** (trimmed mean, or median + separately reported
  tail share). Report p50/p95/max per arm, not just means — the tail is the
  thesis.
- Power analysis assumes heavy-tailed costs calibrated on baseline
  measurements. Set minimum held-out N from that math, or explicitly accept a
  directional (non-definitive) result **before** spending.
- Budget cap for the demo (propose $1,500) set up front. Disclose everything,
  including optimization-experiment spend.

## M1: measurement hardening

Much exists (`tracker.py`: per-run cost, retry-branch waste, price-vintage
stamping, estimate flags). Remaining work is plumbing:

- **Enumerate per-provider usage fields:** Anthropic
  `cache_creation_input_tokens` / `cache_read_input_tokens`, OpenAI
  `prompt_tokens_details.cached_tokens`, Gemini thought tokens, Bedrock usage
  gaps. Per-provider validation test in CI: a known prompt must produce
  expected dollars. Silent mispricing gets caught by CI, not by a customer.
- **"Reconciled" = explained-delta report**, not exact match: estimated vs.
  billed with every delta component labeled (cache discount, tier, credits,
  unexplained residual). Estimated cost will never equal a real enterprise
  bill — produce the explained delta, not a false exactness.
- **Defer all provider billing-API integrations until after M3.**
- Keep estimated charges explicitly labeled as estimates. No number leaves the
  repo without a source experiment ID (rule: fixes the illustrative-stat
  problem permanently).

## Sequencing

- **M0.5:** task set + grader + fixture strategy (2–3 weeks; fixture pain
  lives here).
- **M1:** measurement hardening (1–2 weeks; much exists).
- **M2:** experiment runner + intervention knobs + holdback splits + repeat
  orchestration + robust stats (3–4 weeks). Control-plane decision first.
- **M3:** three-arm benchmark per this spec (1–2 weeks elapsed).
- **M3b:** commercial gate — five operators, one signed paid pilot.
- **M3.5:** economic validation — 5 paid pilots, conversion gate.
- **M4:** patch generation (diff + evidence + uncertainty). **Not before M3.**
- **M5:** CI regression check. **Not before M3b.**

Estimated M0.5–M3 for 2–3 engineers: ~8–11 weeks.

## Security and data motion (before any customer contact)

The "send us redacted logs" motion is retired as the default:

- **Default: customer-side harness.** Ship a self-serve runner the customer
  operates in their own VPC; Averth analyzes exported aggregates only. "Send
  us logs" becomes opt-in, not the default.
- **Redaction as code, not advice:** customer-side redactor with auditable
  ruleset and a redaction report (what was stripped, counts by category).
  Allowlist trace schema preferred: only approved fields leave the building.
- **One deployment model with a crisp trust boundary** (for any in-env
  execution): signed container the customer pulls, no phone-home except a
  customer-approved results payload, documented egress allowlist. Start the
  SOC 2 Type I clock now — "runs in your environment" cannot be sold without
  it.
- **CI gate spec:** pinned signed releases, SBOM, least-privilege (model API
  key scope documented, status checks only, no write), explicit fail-open /
  fail-closed behavior.
- **Billing reconciliation happens customer-side;** only aggregated deltas
  leave. Or drop it from pilot scope — labeled estimates suffice for a pilot.
- **Publish before outreach:** security page + DPA template (what data, where
  it lives, 30-day retention then delete, no training on customer data,
  subprocessor list, region).

## Buyer motion (commercial gate support)

- **Publish the three-arm benchmark before any outreach.** Public,
  reproducible, regressions disclosed, full experiment economics with payback
  math. No benchmark, no meeting.
- **Written pilot agreement**, not "we'll walk away": fixed fee ($8–15K band),
  pre-registered success criteria (≥20% cost-per-accepted-task reduction at
  equal-or-better quality on held-out cases), reduced fee (50%) if criteria
  are missed. One-page order form, W-9, standard DPA ready before the first
  call; willing to work under customer paper.
- **Name the time ask in outreach:** "about 4 hours of your team's time across
  two weeks."
- **Extend through deployment:** pairing to land the patch + installing the CI
  gate. A report alone evaporates at handoff.
- **Target the trigger:** cost optimization is important-not-urgent; the reply
  comes from a bill spike, a board question, or an active re-architecture —
  pain-led prospecting already aims there.

## Service circuit breaker (in writing, not a vibe)

- Fixed price, one workflow, N days, walk-away clause, no custom SOWs.
- **Reuse rule:** do not start engagement N+1 unless the prior harness covers
  >60% of setup. Two consecutive engagements sharing <40% → stop selling
  services, reassess.
- **Time-box rule:** if services exceed X% of team time for more than Y weeks
  (set X, Y before the first engagement) → halt and reassess.
- **"Worthwhile improvement" defined numerically:** ≥25% reduction in cost per
  accepted task on ≥$15K/month workflow spend, 95% CI lower bound above 10%.
  Anything smaller is a walk-away **by rule**, protecting margins and honesty
  simultaneously.
- **Cap corpus investment:** ≤15 engagements of causal-graph building until
  SaaS conversion math is proven. Treat priors as depreciating assets
  (~9-month half-life), not a compounding moat.

## Moat (demoted to hypotheses)

The v2 moat section is retracted as stated. What survives as testable
hypotheses, ranked:

1. **CI embeddedness** — stickiest candidate, but only if we land first per
   repo and gates are quiet (noisy gates get disabled). Test in M3b/M3.5.
2. **Invoice join** — boring, fiddly, incumbents will never prioritize it.
   "Boring" is the most defensible moat on this list.
3. **Verticalized priors** — transferable causal claims within one harness
   class (e.g., LangGraph support agents). Generic priors are trivia.
4. **Causal experiment graph** — demoted to sales asset until cross-customer
   data rights exist in writing. Do not build the corpus on hope.

**Buyer hypothesis to test:** the FinOps / budget owner is the real opening
(LangSmith doesn't sell there). If outreach targets operators, the product
must answer the operator's questions; if it targets the budget owner, it must
answer forecast/variance/chargeback. Pick one per motion — the current straddle
serves neither.

## Death-4 answer (named in advance)

The quarter LangSmith ships cost-per-experiment + regression alerts: we do not
compete on the runner. We compete on (a) the invoice join they won't build,
(b) the FinOps buyer they don't sell to, (c) vertical depth in one harness
class. If none of those hold by then, the honest fallback is a feature
acquisition — named now, not discovered in panic.

## Risks (kept from v2, still live)

1. Chosen agent already efficient → arms tie → benchmark proves nothing
   (early warning: arm B converges on arm C's planned levers in session one).
2. Fixture overfit → live divergence (mitigated: live decides, fixtures
   iterate).
3. Measurement never trustworthy enough (mitigated: brutal M1 scoping, <10%
   reconciliation gap before M2).
4. Statistics eat the demo (mitigated: power math before spending; inconclusive
   is an acceptable honest output).
5. Service wedge becomes consulting (mitigated: circuit breaker above).
