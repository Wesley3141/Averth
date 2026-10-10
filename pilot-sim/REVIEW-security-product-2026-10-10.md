# Security-flavored Averth: product design (not hype)

Date: 2026-10-10. Author: research subagent.
Question: what would a security feature be, given what Averth already measures?

## 0. The one-sentence honest framing

Averth sees **economics, never content**. It cannot confirm an attack. It can
detect the **cost-shaped shadow** of one: which attempts were economically
anomalous, what drove the spend, and whether they share a pattern. That is a
real signal, and it is strictly complementary to — not competitive with —
content inspection.

## 1. Signals that fall out of existing metrics

Every mapping below uses fields already in `tracker.pnl()`. No new
instrumentation required.

| Existing metric | Security-relevant signal | Threat it shadows |
|---|---|---|
| `tail` (p50/p95/max, top5pct_share) + per-attempt costs | Attempts costing far above baseline, clustered by shared attributes | **Denial-of-wallet / resource abuse** — the established OWASP-adjacent category; AI security checklists list cost/abuse controls alongside DLP and injection detection |
| `cost_retry_path` + `top_retry_reasons` | Retry-count spikes sharing one reason string across attempts | **Prompt-injection exploitation** — injected agents often loop (confused retries) or fan out tool calls; Averth flags the economic shape, the firewall confirms the content |
| Per-attempt output/input token ratio vs baseline | Output-token inflation 3-sigma above the agent's own norm | **Data exfiltration** — exfil reads as abnormal output volume; the dev.to token-accounting literature treats output inflation as the jailbreak/exfil signature |
| `avg_context_growth`, `context_tax` | Context exploding relative to baseline on specific attempts | **Context poisoning / retrieval overfetch** — poisoned history or injected documents bloat context before anything else |
| `cost_tools` + per-tool attribution | Tool-spend concentration: one tool suddenly dominating | **Compromised-agent API abuse** — an agent hammering a paid external API it barely used before |
| `per_model` + `unpriced_models` | New/expensive models appearing in the ledger | **Model-routing hijack or shadow usage** — spend migrating to models nobody approved |
| `escalations` + `cost_human` | Escalation-rate spikes | **Social-engineering-via-agent** — attacks that push the agent to punt to humans at scale |

What Averth can **never** do: confirm injection (no prompt inspection),
confirm exfil (no output inspection), block anything inline (read-only by
design). Every signal above is an anomaly with an economic fingerprint, and
the output must say "inspect these attempts," never "you were attacked."

## 2. Who buys — and the GTM problem

- **Cost buyer (today):** VP Finance / platform lead / head of engineering.
  Buys on unit economics.
- **Security buyer:** CISO / SecOps / AppSec. Buys on risk and compliance.
  **Different person, different budget, different sales motion.** A CISO
  evaluates you against Check Point, OrcaRouter, and the YC agent-security
  cohort. That is a fight Averth cannot win and should not pick: those
  vendors sell *prevention* (inline firewalls, guardrails — OrcaRouter made
  theirs free); Averth is *retrospective detection*.

**The way through:** do not sell to the CISO. Sell **abuse monitoring** to
the buyer you already have. Denial-of-wallet already sits on the AI security
checklists that platform teams own, and "which attempts burned anomalous
money and why" is a platform/SRE problem before it is a CISO problem. One
GTM motion, one champion, no repositioning as a security company. If a
prospect's CISO gets involved, the pitch is "we feed your SIEM," not
"we replace your firewall."

## 3. Competitive map — where the angle does NOT overlap

- **Prompt-injection firewalls:** OrcaRouter (free tier), Check Point AI
  Firewall (inline enforcement), Silmaril (YC, self-immunizing). They inspect
  content and block. Averth does neither. No overlap.
- **Agent auth/audit/credentials:** Multifactor (YC, permissions + audit),
  OneCLI (credential isolation). Control-plane plays. Averth is post-hoc
  forensics. No overlap.
- **Red-teaming:** Fabraix (YC, continuous vuln hunting). Proactive attack
  simulation. Averth watches production economics. No overlap.
- **Closest direct overlap:** at least one observability platform
  (agents.opsveritas.com, per recent token-accounting literature) already
  does baseline-aware (3-sigma) token anomaly detection with auto-pause.
  That is the same *shape* of signal. Averth's differentiation there: it
  works on the prospect's existing traces (Langfuse/LangSmith/OTel, local,
  no re-instrumentation), attributes across all five cost layers (not just
  tokens), and carries the honest data-quality story (billed/measured/
  estimated/unknown) that a pure token monitor lacks.

The non-overlap is real but narrow: nobody sells **post-hoc economic
forensics of agent abuse** as the product. It is an adjacency to the
security market, not a position inside it. Treat it as a feature that
deepens the platform/finance sale, not as a second company.

## 4. Smallest shippable security feature

**Anomaly lens on the existing receipt** (read-only, no blocking, no new
instrumentation). From the ledger's own per-attempt cost distribution
(p50/p95 already computed), flag attempts above p95, cluster them by shared
pattern (same retry reason, same dominant tool, same model), and append a
"Suspicious attempts" section to the report: case ID, cost vs baseline,
largest-first cost driver (retries? tool fan-out? output tokens? context
growth?), and one suggested next step ("inspect tool calls in case X —
40x normal tool spend; feed the case ID to your SIEM or firewall vendor").
The user investigates; Averth never declares an attack. Ship it as
`averth trace ... --anomaly` reusing the findings pipeline. If no attempt
clears the bar, the section says so — the honest-out carries over.

## 5. Verdict

Build the anomaly lens as a **feature for the existing buyer**, not a pivot
to security. The security buyer is a different person with a different
budget and entrenched incumbents; chasing them splits focus six weeks
before the November 1 bar. The economics-anomaly angle is genuinely
differentiated (post-hoc, trace-native, honest about what it can't prove),
but its commercial value is making the platform/finance sale stickier —
"we also catch the abuse your firewall can't see because we watch the
money" — not opening a second front.
