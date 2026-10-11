# HN Positioning Review: Averth Show HN Frame

Reviewer: positioning strategist. Date: 2026-10-10.

## The pick: Frame 4 — "Your dashboard is lying to you"

Not "cost meter" (the mechanism), not "one change worth testing" (the output), not "economic control plane" (the vision). The winning frame is the **surprising insight**: every cost number you're looking at is wrong, and here's the tool that shows why.

HN upvotes findings, not tools. "I built a cost meter" is a tool announcement — it gets skimmed. "Your dashboard says $0.20 and the answer is $0.82, because dashboards silently zero-fill the data they don't have" is a finding — it gets clicked, argued with, and starred. The tool is the proof of the finding, not the subject of the post.

This frame also weaponizes Averth's actual differentiator. The honest-accounting story (UNKNOWN instead of invented numbers, missing usage flagged not free) isn't a feature list — it's an accusation against every incumbent dashboard. HN loves an accusation backed by code. And it's defensible: 355 tests, deterministic arithmetic, no LLM in the accounting path. When the comments come for you (and they will), you defend a measurement claim, not a vision.

The "one change worth testing" still appears — as the payoff paragraph, not the headline. Structure: finding → why → tool → honest limits → the decision output → "be brutal."

---

## Title

Show HN: Your AI agent doesn't cost what your dashboard says

## Post body

Our token dashboard said $0.20 per successful run. The real number was $0.82. The gap wasn't a pricing error — it was everything the dashboard silently leaves out: retry paths, failed runs, tool calls, human review time, and the 5% of runs that burned 61% of the budget.

Worse: most dashboards fill gaps with zeros. A call with no usage data renders as $0.00 — free. That's not measurement, it's fiction that happens to flatter.

So I built the opposite. Averth reads traces you already have (Langfuse, LangSmith, OpenTelemetry), runs locally, and prints a receipt where every dollar is labeled by provenance: vendor-billed, measured, estimated, or unknown. No outcome labels? Cost-per-success prints UNKNOWN — an error-free trace isn't an accepted outcome, and the tool refuses to pretend otherwise.

```
pip install git+https://github.com/Wesley3141/Averth.git
averth trace runs.json --format langfuse
```

It ranks findings by dollars and names the one change worth testing first, with the arithmetic. There's an optional LLM advisor (BYOK) that writes the recommendation out, but the accounting is deterministic — the LLM only sees aggregates, never your traces.

Honest state: 355 tests including a chaos suite for malformed traces, zero production users. The $0.20/$0.82 is from a 2,000-run synthetic workload, not a customer. If you run agents in production: does this match your spend, or am I missing a cost layer? Be brutal.

---

## Why the other three frames lose on HN (3 sentences)

"Cost meter" loses because HN has scrolled past a hundred cost dashboards and the phrase triggers "not another one" dismissal before anyone reaches the honest-accounting insight that actually differentiates it. "One change worth testing" loses because it reads as consulting-engagement copy rather than a tool — HN readers can't evaluate an output-quality promise from a post, so the frame asks for belief before showing the measurement that would earn it. "Economic control plane" loses because it's platform-vision language attached to zero production users, and HN's immune system destroys vision decks on sight while burying the concrete working thing underneath.

## Comment strategy note

The post will attract three comment types: (1) "Langfuse already shows cost" — answer with the billed/measured/unknown distinction and the zero-fill accusation, concretely; (2) "this is just a wrapper around an LLM" — point at the deterministic accounting and the BYOK-optional design; (3) demands for real customer data — concede it, don't defend. Never get defensive, never pitch. The goal of the thread is credibility and GitHub stars, not conversions — conversions come from the follow-up email to people who starred.
