# Buyer audit: getaverth.com + GitHub README
Reviewer persona: VP Engineering / platform lead, runs AI agents in production, just got burned by a surprise bill. Landed from a link.
Date: 2026-10-10. Site fetched live; README fetched from GitHub (master feab3b6e, 46 commits, 0 stars).

## 1. Does it speak to my pain?

Partially — strong open, then it drifts.

The hero lands: "The invoice said $0.20. The outcome cost $0.82." I recognize that gap viscerally; my dashboard told me one number and finance told me another. The five-layers section also reads like someone who has lived it: "Every step re-reads the last, so input context compounds across long runs" and "Averages lie. The tail bills you." The 61%-of-spend-from-5%-of-runs stat is the shape of every incident I've debugged.

What loses me:
- The first thing on the page is an announcement bar: "New: query your agent economics from ChatGPT and Claude with the Averth MCP server." I came here burned by a bill. Why is a chatbot integration the first thing I see? It signals the product doesn't know what it is.
- The pain framing dissolves into framework language fast: "five cost layers," "the ledger," "fully loaded cost per accepted outcome," "Observe → Attribute → Value → Govern." I understand these words, but they read like a consulting deck, not a tool page. After the hero, nothing else on the page mentions *my* bill again.
- The FAQ's "Is this another token-cost dashboard?" is the right question, but the answer ("Averth answers what the outcome cost") is abstract. I want one sentence with a concrete example from a real incident.

Verdict: the hero recognizes my problem; the rest of the page talks about its framework.

## 2. Is "how it works" believable? What's missing?

The core claim — "One command on traces you already have. Everything runs on your machine; your traces never leave your environment" — is believable and it's the best thing on the page. `averth trace runs.json --format langfuse` is concrete. pip-installable, MIT-licensed, no account. I believe this.

But the page contradicts its own privacy story, and that's a red flag:
- The Method section intro says: "No integration, no call. You run the exporter locally and send a small batch of sanitized runs; we return the economics."
- Step 1 of the same section says: "Everything runs on your machine; your traces never leave your environment."

"Send a small batch... we return the economics" vs "traces never leave your environment" — which is it? As a buyer with a security review process, this contradiction kills the "run it this afternoon" impulse. I now have to ask which statement is true, and I won't bother.

Other believability gaps:
- What is "the exporter"? The Method section mentions running "the exporter locally" but nothing else on the page defines it. Do I export from Langfuse myself? Is there a bundled exporter? How big is "a small batch"?
- The three product cards (analyze_run_batch, simulate_policy, explain_cost_layers) are described with in/out signatures like API tools ("in ledger_json: batch of runs / out cost per outcome, tail, layers"). Are these CLI commands? MCP tools? Python functions? The page never says how I invoke them. It reads like a ChatGPT plugin listing, not a product page.
- So what IS the product? The page simultaneously presents: a CLI (`averth trace`), a Python library (Tracker API quickstart), and MCP tools for ChatGPT/Claude. No hierarchy, no "start here." A burned buyer wants one path, not three.

What I'd need before trying it: (a) a resolved privacy story in one sentence; (b) one screenshot of an actual report (the 6-line terminal snippet isn't enough to judge); (c) where the input file comes from — "export your last 2 weeks from Langfuse, it's one click" or whatever the truth is.

## 3. Do I trust $0.20 vs $0.82?

Mostly, with one reservation that matters.

What's good: the numbers are labeled "MEASURED · 2,000-RUN WORKLOAD" and there's an explicit note: "Components are rounded and measured from the test workload. Human review is priced at a loaded labor rate; your review cost per run will differ." The layers section says "In the test workload, humans were ≈63% of the fully loaded cost." That's disclosure, and it's more honest than most vendor pages.

What erodes trust: "test workload" is doing euphemistic work. Is this synthetic data or production data? The GitHub README says "simulated 2,000-ticket month" — the word "simulated" appears there but nowhere on the site. As a technical buyer I will find the repo within 90 seconds and discover the numbers come from a seeded simulation. Finding that out myself, rather than being told, converts "honest" into "sneaky" retroactively.

The deeper issue: $0.52 of the $0.82 — nearly two-thirds of the headline number — is human review at an assumed loaded rate. The metered-only comparison ($0.30 in tokens/tools vs the $0.20 dashboard, i.e. 1.5x on hard numbers) is the defensible claim, and it's buried. The hero leads with the 4x number whose majority component is modeled, not measured.

What would make me trust more: state "simulated workload" plainly on the site (one word, huge credibility difference); lead the hero with the metered-only gap and present the fully-loaded number as the modeled extension; or best of all, one anonymized real-production case, even a small one.

What makes me trust less: the current setup, where I have to cross-reference the repo to learn the numbers are synthetic.

## 4. vs Langfuse's cost view — clear differentiation?

Not clear enough. I use Langfuse. The page never names it.

The FAQ draws the line as "Token dashboards answer what the model cost. Averth answers what the outcome cost: retries, failed runs, tool and API spend, context growth, escalation, and human review at a loaded rate." That's directionally right, but as a Langfuse user my actual question is narrower: "I already have Langfuse's cost tab — what specifically does it miss?" The page never answers that concretely. The honest answer exists in the product (retry-path attribution, failed-run waste lens, yield ratio, p50/p95/max heavy-tail reporting, unknown-usage flagging instead of silent zero-fill, per-model attribution with human labor) — but it's scattered across the five-layers section rather than stated as "here's what your Langfuse cost view doesn't show you."

Worse, the page muddies the relationship: the trace importers take Langfuse exports as *input* ("trace importers for Langfuse, LangSmith, and OpenTelemetry"), which means Averth complements Langfuse rather than replacing it. That's actually a good story — "keep Langfuse, add the economics layer" — but the page never tells it. Instead the MCP-tool framing makes it look like a competing interface.

One more gap: nothing addresses the obvious objection "can't I just do this in a spreadsheet from the Langfuse export?" The honest answer (faster, reproducible, before/after comparison, honest unknowns) never appears.

## 5. Do I know what to do next? Would I run the command?

No — the page gives me two competing next steps and I would do neither.

Path A (self-serve): the terminal snippet shows `averth trace runs.json --format langfuse`, and the OSS section shows `pip install git+https://github.com/Wesley3141/Averth.git`. This is the path I'd take.

Path B (contact): the closing CTA is "Send a batch. Get the P&L." with a "Get the free diagnostic" mailto button and "NO INTEGRATION, RAW CUSTOMER CONTENT, OR CALL NEEDED FIRST."

These conflict. If it's truly one command and runs locally, why am I emailing someone? If the diagnostic is the product, why show me the pip install? A burned, busy buyer doesn't resolve ambiguity — they bounce. The mailto CTA actively undermines the self-serve story: it signals "this isn't really self-serve, you'll end up on a call."

Friction notes on Path A: `pip install git+https://...` instead of `pip install averth` (not on PyPI) reads unfinished and adds a beat of hesitation. And per section 2, I still don't know where `runs.json` comes from.

Would I run the command? Not from this page. I'd need: one unambiguous primary CTA ("run this now"), the privacy contradiction resolved, and a real report screenshot. As it stands I'd more likely star the repo and forget it.

## 6. README vs site: do they match?

No. They tell different stories with direct contradictions:

- **Positioning.** Site title: "The lightweight meter for AI agent costs." GitHub repo header: "The economic control plane for enterprise agents." These are different products in a buyer's mind — a humble tool vs. a platform. Pick one.
- **The promised outcome.** README: "What it is not: another cost dashboard. The output of an Averth run is a concrete change to test." The phrase "one change worth testing" never appears on the site. The site's payoff is "the P&L" and "policies that would have prevented the waste." A buyer reading both gets two different value props.
- **The primary path.** README quickstart leads with `averth trace` on existing traces ("This is the whole pilot"). The site's OSS section leads with instrumenting via the Tracker API ("Wrap your agent loop"). Different "start here."
- **Data flow contradiction (the serious one).** README: "Runs locally. Your traces never leave your machine." Site Method section: "You run the exporter locally and send a small batch of sanitized runs; we return the economics." One of these is wrong, and a security-conscious buyer will assume the worse one.
- **Feature drift.** README documents `averth advise` (BYOK LLM advisor, three modes, --show-prompt). The site never mentions it. Site announces the MCP server for ChatGPT/Claude; the README never mentions it. Each surface is missing the other's newest feature, which reads as "neither is maintained."
- **Stale details.** README's repo layout says "334 tests" — the suite has grown since. Minor, but it's exactly the kind of drift that makes a buyer wonder what else is stale.

## Bottom line for the parent

As the burned buyer, my 30-second read: interesting hero, credible pain, then confusion. Three products presented as one (CLI, library, MCP tools), a privacy story that contradicts itself in adjacent paragraphs, numbers I trust until I discover they're simulated, and two competing calls to action. I would not run the command and I would not send the email. I'd star the repo and move on.

The fix list, in priority order:
1. Resolve the privacy contradiction — one sentence, one story, everywhere. (Highest leverage; it's currently a trust-killer.)
2. One primary CTA. If self-serve is real, make "run this now" the only path and demote the mailto. If the diagnostic is the product, stop showing the pip install so prominently.
3. Say "simulated" on the site, and lead with the metered-only gap ($0.30 vs $0.20) with the fully-loaded number as the modeled extension.
4. Align site and README on positioning ("lightweight meter" vs "control plane"), the promised outcome ("one change worth testing" appears in neither or both), and feature parity (advise, MCP server).
5. Answer "what does Langfuse's cost view miss?" directly, by name. That's the comparison every buyer in this market is actually making.
6. Get on PyPI. `pip install git+https` is a papercut that signals unfinished.
7. One real report screenshot. The terminal snippet is too small to evaluate.
