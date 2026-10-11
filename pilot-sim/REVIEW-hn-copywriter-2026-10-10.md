# Show HN copy — Averth (copywriter pass, 2026-10-10)

## The brief
Wesley wants clickbait HN can't resist clicking, that survives HN's brutality.
Rule used throughout: every claim must be true of the test workload or the
product as it exists today. Curiosity from specificity, never from exaggeration.

---

## 5 titles, safest → most aggressive

**1. (Safest) "Show HN: Averth – open-source cost meter for AI agent runs"**
Why it works: clear, honest, zero attack surface. Why it's weak: no curiosity
gap — it asks the reader to already care about agent cost metering. Expect
modest upvotes from the niche, no front page.

**2. "Show HN: Averth – find the one change worth testing in your AI agent's costs"**
Why it works: benefit-forward, differentiates from dashboards without
attacking anyone. Risk: "one change worth testing" is a marketing-shaped
phrase; HN will demand the body prove it's real (the findings engine does).

**3. "Show HN: Our token dashboard said $0.20/success. The real number was $0.82"**
Why it works: concrete numbers, 4x gap, personal scope ("our" = honest —
it doesn't claim this is everyone's number). This is the curiosity sweet
spot: "wait, really?" is the click. Risk: low. The body must show the
waterfall breakdown in the first paragraph or it reads as bait.

**4. "Show HN: 5% of our agent's runs burned 61% of spend – open-source tool to find yours"**
Why it works: the heavy-tail stat is genuinely counterintuitive and it
generalizes better than the $0.20/$0.82 (tail concentration shows up in
almost every workload). "Find yours" is the call to action. Risk: medium —
readers will ask whether 61% is cherry-picked; the answer (seeded simulation,
reproducible) must be in the comments.

**5. (Most aggressive) "Show HN: Your token dashboard shows 25% of your agent's real cost"**
Why it works: maximum provocation — it accuses the reader's setup directly,
and "25%" is precise enough to feel factual rather than rhetorical. This is
the one people can't not click. Risk: highest. It generalizes "your" beyond
the test workload, so the body must open with the qualification ("in our
measured workload") and the full component breakdown, or the comments will
file it under hype. Survivable if the receipts are shown immediately.

## Copywriter's pick
**#3.** It threads the needle best: the 4x number gap is the most clickable
true thing we have, "our" keeps it honest, and it doesn't pick a fight with
the reader before they've clicked. #5 gets more clicks but burns goodwill
with the exact audience (infra engineers) whose trust is the whole product
thesis. If Wesley wants pure click volume and is willing to fight in the
comments, #5.

---

## Post body (~200 words)

Our token dashboard said $0.20 per successful run. The real number was $0.82 —
retries, failed runs, tool calls, and human review the dashboard never sees.

I got tired of cost tools that show a number instead of an answer, so I built
Averth: point it at traces you already have (Langfuse, LangSmith,
OpenTelemetry) and it tells you the single change worth testing first, ranked
by dollars. Not a dashboard — a decision.

```
pip install git+https://github.com/Wesley3141/Averth.git
averth trace runs.json --format langfuse
```

It runs entirely on your machine; your traces never leave. In our test
workload the top 5% of runs burned 61% of spend, and it flags runaway-shaped
attempts (anything above p95 with its dominant cost driver) — the same shape
as the $50K agent loops you've read about.

Two things I'm stubborn about: missing usage data prints as UNKNOWN, never
zero-filled — a call with no token data is not free. And without
accepted-outcome labels, cost-per-success prints UNKNOWN too, because an
error-free trace isn't an accepted outcome. I'd rather show you a gap than
invent a number.

355 tests, including a chaos suite for malformed traces. Zero production
users — that's why I'm here. Tell me where the accounting is wrong.
