# Show HN post for Averth — veteran review

## Titles, ranked by clickability

**1. Show HN: Our AI bill was 4x what the dashboard said**
Strongest. Specific number, curiosity gap, relatable pain every HN reader with an LLM bill has felt. The "our" makes it a story, not a pitch. True (0.82/0.20 ≈ 4.1x). This is the one.

**2. Show HN: Your agent cost dashboard is lying to you**
More aggressive, "you" language. Will get clicks and will get one commenter saying "it's not lying, you're reading it wrong" — which is actually fine, that argument drives the thread. Slightly riskier tone; the tool is honest, the title picks a fight.

**3. Show HN: My cost tool prints UNKNOWN instead of guessing**
The honesty-angle play. Weakest clickbait, strongest HN-culture fit. This audience viscerally respects "refuses to invent numbers." Would underperform #1 on clicks but overperform on comment quality — the people who click this one are your actual users.

Recommendation: go with #1. It earns the click honestly and the post delivers the substance.

---

## Post body (238 words)

Our token dashboard said $0.20 per successful run. The real number was $0.82. I built Averth because I wanted to know where the other $0.62 went, and no existing tool would tell me.

It reads traces you already have (Langfuse, LangSmith, OpenTelemetry) and tells you the one change worth testing first, with the arithmetic. One command, runs entirely on your machine:

```
pip install git+https://github.com/Wesley3141/Averth.git
averth trace runs.json --format langfuse
```

What it found in our test workload: retry loops burning 23% of spend, the costliest 5% of runs eating 61% of the budget, failed runs with zero outcomes. The dashboard sees none of this — it stops at the model call.

Two decisions I was stubborn about:

1. Missing usage data renders as UNKNOWN, never zero-filled. A call with no token data is not free, and I didn't want the tool to launder that.
2. Without accepted-outcome labels, cost-per-success prints UNKNOWN. An error-free trace is not an accepted outcome, and most tools conflate the two silently.

There's an optional LLM advisor (bring your own key) that writes the recommendation out in plain English, but the accounting underneath is deterministic arithmetic — 355 tests, including a chaos suite that feeds it malformed traces to make sure it degrades loudly instead of silently wrong.

Honest state: zero production users. So tell me where this breaks: is the "one change worth testing" framing actually useful, or did I build a dashboard with better copy?

---

## Veteran notes (tactical, not copy)

- **When:** Tuesday–Thursday, 8–10am US Eastern. Never weekends, never Monday morning (inbox triage) or Friday afternoon (gone).
- **Where the link goes:** the GitHub repo, not the marketing site. This crowd clicks through to read code within 30 seconds; a landing page kills momentum.
- **Comments:** be there all day. Answer every substantive question, concede fast when someone's right, never get defensive. The top comment thread matters more than the post body — that's where the stars come from.
- **Don't:** ask for upvotes (bannable, and the crowd smells it), use the word "revolutionize," or claim production users you don't have. The post already discloses zero users; that honesty is doing work.
- **Expect:** someone will say "I can do this with a spreadsheet." The correct answer is "yes, and here's why that's slow" — the pitch is faster answer + reproducible before/after, never "you can't DIY this."
- **The 4x number will get challenged.** Have the breakdown ready: $0.20 model-only vs $0.82 fully loaded (retry path + tools + human review). If someone asks for the raw ledger, consider publishing a sanitized one — nothing converts skeptics like data.
