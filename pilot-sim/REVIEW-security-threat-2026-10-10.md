# Security research: denial-of-wallet and cost-based attacks on AI agents

Date: 2026-10-10. Researcher: subagent (web research).
Question from Wesley: is cost-anomaly detection a legitimate security direction for Averth?

## TL;DR

The threat is real but lopsided. **Documented, dollar-denominated cost attacks are overwhelmingly credential theft (LLMjacking), not adversarial prompt tricks.** The biggest single bills come from *accidents* — runaway loops under weak controls, no attacker at all. Deliberate prompt-injection-to-cost attacks on agents are mostly research papers and simulations; Forcepoint explicitly says it has not seen a real-world agent-tool fan-out attack. Meanwhile OWASP moved Unbounded Consumption from #10 (2025) to #6 (2026) on incident-weighted evidence, and agent-security vendors just raised ~$325M combined. **Nobody sells agent cost-attack detection as a product.** The honest Averth positioning: we detect *cost anomalies in minutes* (covering accidents AND attacks), not *attacks* — claiming attribution would be overreach.

## 1. Documented incidents with dollar figures

### Credential theft → inference abuse (LLMjacking) — the dominant real pattern
- **Sysdig TRT, May 2024**: attackers exploited Laravel CVE-2021-3129 to steal cloud credentials, invoked Bedrock/Azure OpenAI models, and resold access via `oai-reverse-proxy`. Estimated worst case: **>$46,000/day** (Claude), **>$100,000/day** (Claude 3 Opus, later research). Recon pattern: `InvokeModel` with `max_tokens_to_sample:-1`, plus `GetModelInvocationLoggingConfiguration` queries to dodge detection.
  - https://www.infosecurity-magazine.com/news/llmjacking-exploits-stolen-cloud/
- **Operation Bizarre Bazaar (Pillar Security, Dec 2025–Jan 2026)**: first attributed LLMjacking campaign with commercial monetization. **35,000 attack sessions (~972/day)** against exposed LLM/MCP endpoints; three-role supply chain (scanner → validator → marketplace `silver.inc` reselling 30+ LLM providers at 40–60% discount via Discord/Telegram). 60% of attack traffic was MCP-focused recon.
  - https://www.pillar.security/blog/operation-bizarre-bazaar-first-attributed-llmjacking-campaign-with-commercial-marketplace-monetization
- **Storm-2139 (Microsoft, Feb 2025)**: criminal network scraped exposed keys, abused Azure OpenAI, resold access. Microsoft sued and seized `aitism.net`. Evidence this is an organized market, not hobbyists.
- **METR API-key theft**: stolen key used for 3 weeks, ~**$600,000** in credits consumed (credits were granted free, so no cash loss — but the scale is the point).
- **fotc.com GCP incident, May 2026** (first-hand account): leaked old service-account key → privilege escalation → industrial-scale LLM inference. Bill for May 14–16: **€500,960** on an account that normally spends ~$500/month. Alerts *fired* but the amounts looked harmless in absolute terms and the team was at a conference. They built their own GCP cost-anomaly detector afterward.
  - https://fotc.com/blog/by-the-time-the-invoice-arrives-its-too-late-how-we-built-a-cost-anomaly-detector-for-google-cloud/

### Runaway loops — biggest bills, no attacker
- **Mandiant AI Risk & Resilience report, Sept 2026**: an accounting agent entered a runaway execution loop, made **>15,000 high-cost API calls in under an hour**, ~**$50,000** in charges, disrupted live transactions. No attacker involved — "a consequence of weak controls."
  - https://www.shashi.co/2026/10/mandiant-says-one-runaway-ai-agent.html
- **GetOnStack incident**: multi-agent market-research system, Agent A ↔ Agent B recursive clarification loop, ran **11 days undetected**: $127/week → **$47,000**. Then 6 weeks building circuit breakers.
- **Network-scanning agent** (documented in MCP security research): retry loop with no hard limits reached **$6,531** in days; a single runaway also 429'd every other agent sharing the pool.

### Research-stage attacks (papers/PoCs, not seen in the wild as cost attacks)
- **ReasoningBomb** (Johns Hopkins/NVIDIA/Cornell): RL-generated short stealthy prompts inducing ~19k reasoning tokens, **286.7× input-to-output amplification**, 98.4% bypass vs dual-stage detection. Economic framing: inference cost now rivals/exceeds training cost.
- **Excessive Reasoning Attack** (3–8× reasoning prolongation), **ThinkTrap** (black-box infinite thinking), **DeepSloth**, **sponge examples** — all demonstrated vs models, none tied to a real billing incident.
- **Fill-and-Squeeze** (vLLM/SGLang): drives KV-cache scheduler across saturation → 20–280× time-to-first-token slowdown. GRIEF fuzzing found 15 vulns in vLLM/SGLang (10 confirmed, 2 CVEs). Infrastructure-layer, not billing-layer.
- **Route-to-Rome (R2A, arXiv Apr 2026)**: black-box adversarial suffixes steer cost-aware LLM routers to the most expensive backend. HN framed it as denial-of-wallet. Targets the router pattern (OpenRouter/RouteLLM-style), not agents directly.

### Simulated only
- **Forcepoint X-Labs agent-tool fan-out simulation** (OWASP 2026 scenario): poisoned source → 500 tool calls / ~$10 simulated vs 1 call / $0.02 with call budget + recursion limit + circuit breaker. Forcepoint: **"has not yet seen a real-world example"** of this specific scenario. OWASP's numbers: per-turn cost climbs $0.001 → ~$0.50 by turn 100 as context grows; no single request trips rate limits.
  - https://www.scworld.com/news/simulation-highlights-owasp-llm-top-10-risk-of-unbounded-consumption

### Adjacent context
- IBM 2026 Cost of a Data Breach: prompt-injection incidents averaged **$5.89M** in *breach* costs (not wallet costs — different thing, don't conflate).
- Gartner (via industry reporting): >40% of agentic AI projects will be canceled by end of 2027 over escalating costs, unclear value, inadequate risk controls.

## 2. Who talks about this

- **Cloud vendors (origin)**: "Denial of wallet" traces to 2008 ("Economic Denial of Sustainability") / 2013 coinage. OWASP Serverless Top 10 lists it (SAS-07). Vendor guidance is primitive: billing alerts, concurrency caps, budgets. No agent awareness.
- **OWASP LLM Top 10 2026**: **LLM06 Unbounded Consumption** — "uncontrolled inference load causes cost blowout" — rose **#10 → #6** on incident-weighted evidence (2026 is the first edition weighted against real incidents, not just expert opinion). Five catalogued patterns: denial of wallet, agent-tool fan-out, reasoning-loop exhaustion (+ two more). Explicitly separates this from prompt injection (LLM01): *"injection works on instructions; unbounded consumption works on resource limits. Solving one doesn't touch the other."*
  - https://xygeni.io/sscs-glossary/what-is-llm-security/
- **MITRE ATLAS**: AML.T0034 (Cost Harvesting, with resource-intensive-queries sub-technique) and AML.T0029 (Denial of AI Service); OWASP LLM10 maps onto both. NIST's adversarial-ML taxonomy (Mar 2025) added energy-latency attacks.
- **Forcepoint X-Labs** (Jyotika Singh): leading public research voice on the agent-specific patterns.
- **Incident-severity thinking**: the AI-governance curriculum's severity ladder lists "a runaway agent loop that cost the org $47,000 overnight" as an incident class where **"the finance team notices, not security"** — that line is the wedge.

## 3. Who sells detection today

**Nobody sells agent cost-attack detection as a product.** The market splits three ways, and the middle is empty:

| Layer | Who | What they actually detect |
|---|---|---|
| Cloud cost anomaly | AWS Budgets/CloudWatch, GCP budget alerts, Azure Cost Management | Generic spend spikes; slow (billing-cycle latency); the fotc.com story shows alerts firing but being unactionable |
| Agent observability | AgentOps (recursive loop detection, cost monitoring), Langfuse, LangSmith, Helicone, Arize Phoenix, Datadog, Galileo | Cost *tracking* and some loop detection; not attack detection |
| AI agent security (well funded) | **Zenity** ($125M Series C, Aug 2026), **Noma** ($100M Series B), **HiddenLayer** ($100M Series B), **Straiker** ($64M Series A) | Runtime action governance, intent-based allow/block, prompt-injection/DLP/agency — **cost is not their detection surface** |
| Research/consulting | Pillar Security (platform + research), fotc.com (built their own) | LLMjacking research; bespoke detectors |

The gap is precise: **no vendor detects cost-shaped anomalies at the agent layer in anything near real time.** Cloud tools see the bill days later. Security vendors watch actions and data, not spend. Observability vendors track cost but don't treat spikes as security signals.

## 4. Honest assessment: real vs theoretical

- **Real, documented, dollar-denominated**: stolen-credential inference abuse (LLMjacking as an organized criminal market). This is the attack that actually moves money today.
- **Real, documented, but accidental**: runaway loops ($50K/hr, $47K, $6.5K). The Mandiant case is the single most important data point: the largest agent cost incident on record had *no attacker*. Weak controls are the common cause.
- **Research-demonstrated, not observed in the wild**: reasoning-bomb / sponge / router-steering attacks. They prove the asymmetry (pennies in, dollars out) but nobody has tied one to a real bill.
- **Simulated only**: agent-tool fan-out via poisoned sources. Plausible, unobserved.
- **Structural fact that favors the threat growing**: agent token multipliers are large (Anthropic: multi-agent ~15× chat tokens; Manus: 100:1 input-to-output ratio), context makes per-turn cost climb superlinearly, and individual requests stay under every rate limit while the aggregate bleeds.

## 5. What this means for Averth

1. **The security framing is legitimate but must be scoped honestly.** "Detect cost anomalies in minutes" is defensible and differentiated. "Detect cost *attacks*" / attribution is overreach — Averth sees spend shape, not intent. The Mandiant lesson cuts both ways: it proves the pain is real and urgent, but also that the buyer doesn't need an adversary to need us.
2. **The wedge line already exists in the wild**: "the finance team notices, not security." Averth sits exactly there — the meter that notices before finance does.
3. **Competitive whitespace is real**: the $325M+ funded agent-security vendors don't do cost; the observability vendors don't do security; the cloud vendors are too slow. An agent-layer cost-anomaly signal (retry storms, tail explosions, per-turn cost acceleration, unknown-spend spikes) has no direct incumbent.
4. **Don't chase the adversarial framing first.** The near-term buyer pain is accidental runaways and missing budgets (Nov 1 bar: operators who act on findings). The attack-detection story is a second act that the same machinery enables — and OWASP LLM06's rise gives it institutional backing when we're ready.
5. **One concrete product implication**: per-turn cost acceleration (OWASP's $0.001 → $0.50/turn-100 curve) and tail-share explosion are detectable from the ledger *today*. Those two signals alone would have caught the GetOnStack and Mandiant incidents. That's the security-flavored finding to lead with, without claiming to detect attackers.
