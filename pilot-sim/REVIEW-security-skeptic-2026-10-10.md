# Skeptic review: the security direction for Averth

Role: steelman the case AGAINST. Date: 2026-10-10.
Verdict up front: **kill the security direction as a direction.** Keep one narrow
version as a future finding type, and only after the Nov 1 cost bar is hit.

---

## 1. Scope creep vs. the Nov 1 bar

The Nov 1 bar is specific and demanding: **an operator who repeatedly uses
Averth, acts on a finding, and discusses paying — for cost management.**
Three weeks remain.

A security direction does not help hit this bar. It diffuses the only thing
that can hit it: obsessive focus on making one cost finding indispensable to
one operator. Every hour spent on security research is an hour not spent on:

- the follow-up messages that convert a silent prospect into a trial,
- the "one change worth testing" quality (the actual wedge),
- the prospect-sim and chaos-suite reliability work that makes the tool
  trustworthy enough to act on.

Worse, a security pivot functions as an **escape hatch from the verdict**.
The Nov 1 rule exists to force a clean kill-or-pursue decision on the cost
thesis: "if there is no repeated usage or committed pilot by November 1,
park Averth rather than extending indefinitely." A second direction lets the
founder arrive at Nov 1 with "promising security research" instead of an
answer — which is exactly the indefinite extension the rule was written to
prevent. If the cost thesis fails, the honest outcome is to park it, not to
rebrand the failure as a pivot.

A direction needs its own bar, its own validation loop, its own messaging,
its own prospect list. There is no 2x time. Pick one.

## 2. Buyer confusion: two categories, two buyers, two motions

| | Cost meter (current) | Security tool (proposed) |
|---|---|---|
| Buyer | VP Finance / Head of Finance / eng manager who owns the AI bill | CISO / security engineering / compliance |
| Budget | FinOps / engineering efficiency | Security (gated, compliance-driven) |
| Sales motion | "Run one command on traces you have, five minutes" | Audits, frameworks, risk assessments, long cycles |
| Proof required | One receipt, one change worth testing | Threat models, compliance mapping, red-team results |
| Wesley's voice | "Cut costs without giving up reliability" | Does not exist yet — new hooks, new lists, new everything |

What breaks if we chase both:

- **Messaging.** "Cost meter + security research" reads as unfocused to both
  buyers. The finance buyer wonders why a cost tool is talking about
  security; the security buyer wonders why a cost tool claims security
  authority it hasn't earned. The repo and site were *just* cleaned up for
  seed professionalism around a crisp "lightweight meter" story. Diluting it
  now undoes that work.
- **The honesty positioning.** "If there's nothing useful, we'll say so"
  works because the cost claims are grounded in measured data. Security
  claims without security depth invite exactly the invented-authority problem
  Wesley has been disciplined about avoiding.
- **Outreach.** The entire prospect engine (verified emails, LinkedIn hooks,
  the follow-up copy) is cost-led and pain-led. A security direction needs a
  parallel engine. There is no parallel team.
- **Category error.** "Cost meter" is a tool you try in an afternoon.
  "Security" is a vendor you vet for a quarter. Mixing them drags the
  try-it-now motion into enterprise-sales gravity.

## 3. "Security is where the business is" — misapplied to this product

True premise: security is a huge market with real budgets.
False application: that any of that spending attaches to *what Averth is*.

The relevant question is not "is security big" but "does anyone pay for
security **of agent cost data**, from **a cost-meter vendor**, through
**this sales motion**?" No evidence presented yet. Enumerate the actual
candidate angles:

- **(a) Prompt-injection / jailbreak detection via traces.** Crowded to the
  point of saturation: model providers ship it, plus dozens of funded
  startups. A pre-seed cost meter has no edge here.
- **(b) Data-exfiltration detection in agent tool calls.** Real problem, real
  budgets — but it is a *security product* with a *security buyer*. It shares
  nothing with Averth except the word "traces." Building it means starting a
  second company.
- **(c) Denial-of-wallet: cost anomalies as abuse signals.** The *only* angle
  adjacent to the current product: "this spend spike looks like abuse, not
  usage." Same data, same buyer, same motion. Unproven as a buyer category —
  nobody has shown a budget line for it — but it is at least coherent.
  (See "narrow version" below.)
- **(d) "Secure the meter itself."** Table stakes, not a direction. The
  run-local posture and the advisor's `[DATA]`-delimiting already cover it.
  Ship the property; don't build a product around it.

Note the asymmetry: the founder's observation ("a lot of the business is in
security") is a *general market* observation. Every crowded, well-funded
market looks like "where the business is" from the outside. The agent-security
space already has incumbents (Palo Alto, Wiz) and funded startups. Entering
it as a pre-seed cost-meter company, three weeks from a kill-or-pursue bar,
is bringing a knife to a gunfight — in a fight we were never scheduled for.

## 4. The cheapest test (build nothing)

Add **one question** to the existing prospect conversations — asked *after*
the cost conversation, so it doesn't contaminate the cost read:

> "Separate question: when you think about agent risk, is unexpected spend —
> someone misusing or attacking the agent to burn budget — something you
> budget for, or is that the security team's problem?"

And a 30-minute desk check, no researchers needed:

- Do "AI security" job posts mention cost/budget-burn as a responsibility?
- Do security RFPs or vendor evaluations mention agent spend anomalies?
- Does any buyer *language* exist for (c), or would we be inventing the
  category and the demand simultaneously?

**Kill condition, defined upfront** (a test without one is procrastination):
if fewer than 3 prospects independently raise cost-as-security-concern
(unprompted or on the question) by Nov 1, the direction is dead and is not
revisited without new evidence. Write that down before asking the question.

Do NOT spawn a research team first. Researchers without a falsifiable
hypothesis and a deadline produce reading lists, not decisions. The question
above costs zero and answers more.

## The narrow version worth keeping

**Denial-of-wallet as a finding type, not a direction.** If (c) ever shows
signal, it ships as one more insight in the existing engine — alongside the
retry finding and the tail finding — using the same ledger, the same buyer,
the same "one change worth testing" motion. Something like: "attempts from
[this pattern] cost 40x baseline and match no legitimate workflow shape;
treat as abuse until proven otherwise."

Constraints on even this:

1. It waits until the core cost bar is hit. It is a P1 feature, not a pivot.
2. It never becomes "Averth Security." No second brand, no second buyer.
3. The Nov 1 bar does not move. A security-flavored finding counts only if
   the operator acts on it the same way they'd act on a cost finding.

## What to do instead with that energy

The security-adjacent asset Averth already owns is the **privacy property**:
run-local, no exfiltration, the advisor that literally cannot see customer
data. That is a *security property of a cost product*, and it is already a
differentiator against multi-tenant cloud competitors (see the competitor
note: their platform is multi-tenant; ours never sees the traces). Sell the
property harder in cost conversations — "your CISO will like this too" is one
sentence, not a direction. Do not build the product.

---

**Bottom line:** The security direction is scope creep that dodges the Nov 1
verdict, confuses two different buyers, misapplies a general market
observation to a specific product with no buyer evidence, and can be tested
with one question instead of a research team. Kill it as a direction. Keep
denial-of-wallet as a future finding type, gated behind the cost bar. Spend
the three weeks on the bar.
