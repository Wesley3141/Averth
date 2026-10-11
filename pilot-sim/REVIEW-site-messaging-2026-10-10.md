# Messaging audit: getaverth.com vs GitHub README

Date: 2026-10-10. Sources: live https://getaverth.com (fetched) and
Wesley3141/Averth README.md (current master).

## 1. The ONE value proposition (12 words)

**One command on your traces tells you the change worth testing first.**

Section-by-section check against the site:

| Section | Supports it? |
|---|---|
| Title tag ("lightweight meter") | Partial — names the mechanism, not the payoff |
| Announcement bar (MCP server) | No — introduces an unmentioned product surface |
| Hero ("invoice said $0.20...") | Partial — proves hidden cost, never mentions "the change" |
| Terminal (`averth trace`) | Yes — "one command" |
| Stats ($0.82 / $0.20 / 61% / 6%) | Partial — measurement only, no decision |
| Product ("Three tools. Zero dashboards.") | No — lists MCP tool names, never mentions the CLI from the hero, never says "one change" |
| Ledger ("Four times the invoice") | Partial — measurement |
| Tail ("Averages lie") | Partial — measurement |
| Layers ("Five layers") | Partial — framework, no decision |
| Method ("A diagnostic, not a dashboard") | Partial — "not a dashboard" is right, but the 3 steps end at "you get the P&L," not "you get the change" |
| "From diagnosis to control" (Govern) | No — sells a control-plane future the FAQ disclaims |
| FAQ | Partial — "What comes back?" lists outputs, never the one change |
| CTA ("Send a batch. Get the P&L.") | No — "send a batch" contradicts run-local; "P&L" is a report, not a decision |

Score: 1 of 13 sections fully supports the value prop. The site proves
"your costs are higher than you think" and never lands "here's what to do."

## 2. Distinct framing count

Framings found across site + README:

1. "Lightweight meter" (site title tag)
2. "Economic meter" (README first line — note: NOT the same words as the site)
3. "Three tools" (site product section: analyze_run_batch, simulate_policy, explain_cost_layers — MCP-server tool names)
4. "A diagnostic, not a dashboard" (site method section)
5. "P&L / the statement" (site method step 3, CTA)
6. "From diagnosis to control" / Govern (site loop section — the control-plane vision)
7. "One change worth testing" (README, outreach — ABSENT from the site entirely)
8. "Runaway detection" (--anomaly flag; README only, absent from site)
9. "LLM advisor" (averth advise; README only, absent from site)
10. "MCP server" (site announcement bar only, absent from README and product section)

That is **10 distinct framings**. A first-time visitor cannot answer
"what is this" in one sentence. Anything above 2–3 is too many; 10 is
a positioning failure. The single most important phrase in the entire
strategy — "one change worth testing" — appears zero times on the site.

## 3. Hero vs product vs FAQ: precise inconsistencies

**A. Hero shows a CLI; product section sells MCP tools.**
Hero terminal: `$ averth trace runs.json --format langfuse`. Product
section lists three tools named `analyze_run_batch`, `simulate_policy`,
`explain_cost_layers` with `in ledger_json` / `out ...` signatures.
These are two different interfaces (CLI vs MCP server). The product
section never mentions `averth trace`. A reader cannot tell which one
they're supposed to use.

**B. "Send a batch" vs "nothing leaves your machine."**
Method intro: "You run the exporter locally and send a small batch of
sanitized runs; we return the economics." CTA: "Send a batch. Get the
P&L." But method step 1, two paragraphs later: "One command on traces
you already have. Everything runs on your machine; your traces never
leave your environment." Both cannot be true. This is leftover copy
from the old send-us-your-data flow, and it directly undermines the
strongest trust claim on the page.

**C. The site promises governance and disclaims it.**
Loop section: "Govern — Identify when a run should be stopped, rerouted,
or capped." FAQ: "Production enforcement is not enabled as part of the
diagnostic." The vision section sells a control plane; the FAQ says it
doesn't exist. Pick one: either the govern section goes, or it gets an
honest "not yet" label.

**D. README says "economic meter"; site says "lightweight meter."**
Two different names for the thing in the two most-read sentences
across both properties.

**E. The MCP server announcement bar orphans.**
"New: query your agent economics from ChatGPT and Claude with the
Averth MCP server" is the FIRST content on the page. The MCP server
appears nowhere else: not in the product section, not in the README,
not in the quickstart. Leading with the least-documented surface is
backwards.

**F. Site is missing the two newest features.**
`averth advise` (LLM advisor) and `--anomaly` (runaway lens) are in the
README quickstart but absent from the site. The site is already behind
the product.

## 4. What to CUT or demote

**Cut:**
- The "From diagnosis to control" Govern section (or shrink to one
  honest "where this is going" line). It sells what the FAQ disclaims.
- The `explain_cost_layers` tool card ("in: nothing, out: the five-layer
  framework") — that is documentation, not a tool.
- "Send a batch" language everywhere (method intro, CTA). Replace with
  the run-local wording from step 1.

**Demote:**
- The MCP-server announcement bar. Move it to the open-source section
  as a bullet, or cut until it's documented.
- The three MCP tool cards. If the CLI is the hero path, the product
  section should describe user-facing capabilities (trace import →
  receipt → recommendation), not API tool names. Rewrite or cut.

**Rewrite:**
- Product section headline. "Three tools. Zero dashboards." → something
  that ends in the decision, e.g. "One command. One change worth testing."
- CTA. "Send a batch. Get the P&L." → "Run one command. Get the change
  worth testing."

**Add (one line each, not sections):**
- The phrase "one change worth testing" — currently zero occurrences.
- The advisor and anomaly flag as bullets under the hero terminal or in
  the open-source section.

## 5. The sharpest 10-word version

**One command on your traces reveals the change worth testing.**

Place it:
- **Hero subhead**, replacing "Averth measures the fully loaded cost of
  every agent run, then finds the budget and routing policies that would
  have prevented the waste."
- **Title tag**, replacing "Averth — The lightweight meter for AI agent
  costs."
- **README first line**, replacing "**The economic meter for AI agents.**"

Rationale: it contains the mechanism (one command, your traces — local,
no integration), the differentiator (reveals — the dashboard doesn't),
and the payoff (the change worth testing — a decision, not a number).
Every section on the page should be checkable against this sentence;
anything that doesn't serve it is cut.
