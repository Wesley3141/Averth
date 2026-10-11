# Skeptic review: Show HN for Averth right now

Reviewer: skeptic audit, 2026-10-10.
Scope: whether to post Show HN for Averth before the Nov 1 bar.
Verdict: **DON'T. Not now.**

---

## The one-sentence case

Show HN is a one-shot broadcast channel; the Nov 1 bar needs a sniper rifle, and the ammo we'd fire is synthetic numbers with zero users behind them.

## 1. HN traffic does not serve the Nov 1 bar

The bar: *one operator* who runs it repeatedly on a real workflow, acts on a finding, discusses paying. That's a specific human with production traces and budget pain.

HN delivers: developers, tinkerers, students, and engineers browsing on work time. They star repos. They do not pilot enterprise tooling. The conversion path from "HN front page" to "operator running your meter on production traces weekly" is a lottery ticket, not a channel.

Wesley named the failure mode himself: "a thousand stars and zero pilots is worse than ten pilots and fifty stars." A Show HN that pops would produce exactly that — vanity metrics that feel like progress while the Nov 1 clock runs out.

## 2. The failure modes, ranked by likelihood

**Most likely bad outcome: the synthetic-numbers thread.** The entire hook — "$0.20 dashboard, really $0.82" — comes from `demo.py`, a seeded simulation of a fictional 2,000-ticket month. The site labels it "2,000-RUN WORKLOAD" and the drafted post says "in our test workload," but HN does not read footnotes. The first comment will be "is this real data?" and the honest answer — "no, it's synthetic" — will become the thread. Once HN decides you're presenting simulated numbers as findings, the discussion is over. You don't recover from that in the same thread.

**Second most likely: silence.** 8 upvotes, two comments, one saying "yet another LLM cost tracker." This burns the one shot — reposts are frowned upon and get flagged. A failed launch now poisons a real launch later.

**Active danger: the founder's instinct.** Wesley asked for "something people will click even if clickbait." HN *punishes* clickbait. Flagging is community-driven, and nothing gets flagged faster than a title that overpromises. The current instinct is misaligned with the channel's immune system. A clickbait Show HN doesn't just fail — it fails publicly, in front of the exact technical audience whose trust the product's "honest accounting" positioning needs.

**Best case (unlikely):** front page, thoughtful discussion, one operator emails. Possible. Not plannable.

## 3. Is the product ready for HN scrutiny?

Engineering: yes. 355 tests, chaos suite, verified clean install — genuinely solid, and HN respects that.

What HN would find embarrassing:

1. **The headline number is synthetic.** See above. This is the thread-killer.
2. **Not on PyPI.** Install is `pip install git+https://github.com/...`. For HN, that's a smell — it reads "not finished enough to publish."
3. **The advisor is BYOK vaporware to a reader.** No demo without their own key. HN will ask "show me the recommendation output" and there will be nothing to show.
4. **"One change worth testing" is rule-based heuristics.** The findings engine ranks by dollars with hand-written rules. That's fine as v1, but HN will probe whether the recommendations are actually good or just plausible-sounding. With zero production users, there's no evidence either way.

None of these are fatal individually. Together, under HN's microscope, with a clickbait title, they're a bad day.

## 4. Timing

Three weeks to Nov 1. Every hour spent drafting the post, writing the writeup, and wrangling 200 comments is an hour not spent on the six unsent follow-ups and Noah — the actual revenue pipeline.

More importantly: the post is 10x stronger *after* Nov 1. Compare:

- Now: "Show HN: I built a cost meter (numbers are simulated, zero users, be brutal)"
- After a pilot: "Show HN: we metered a real production agent and found $X — here's the trace-shaped receipt"

The second post writes itself and HN rewards it. The first post spends the one shot to learn things the reviewer pipeline already teaches for free.

## What has to be true first

1. **One real production trace analyzed.** Even anonymized, even a friendly operator's redacted export. Real numbers replace the demo.py hook. This is non-negotiable — it's the difference between a finding and a fiction.
2. **On PyPI.** `pip install averth`. Thirty minutes of work, removes the "unfinished" smell.
3. **Nov 1 resolved.** If the bar is hit, the post has a user story. If the thesis is parked, the post is moot. Either way, launching before the verdict is premature.
4. **Founder commits to honest framing.** No clickbait. HN's immune system will do what it does otherwise, and the "honest accounting" brand can't survive its own launch being dishonest.

## The narrow exception

If Wesley wants HN-adjacent value now without the one-shot risk: participate in *existing* relevant threads (someone complaining about agent costs, a Langfuse discussion) with a genuinely useful comment and a link. Low stakes, no launch burned, real feedback. That's the move for October. The Show HN is the move for after Nov 1 — with a real story or not at all.
