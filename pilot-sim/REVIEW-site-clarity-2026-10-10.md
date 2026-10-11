# Site clarity audit: getaverth.com (first-time visitor, 2026-10-10)

Method: fetched the live page with curl, read it top to bottom as someone
who has never heard of Averth.

## 1. In 10 seconds, what does this company do?

"A tool that shows your AI agents cost more than your dashboard says ($0.82
vs $0.20), and finds policies to cut the waste."

The hero earns this: "The invoice said $0.20. The outcome cost $0.82"
plus "Averth measures the fully loaded cost of every agent run, then finds
the budget and routing policies that would have prevented the waste."
That is a decent 10-second read. The problem is everything after it.

## 2. Who is it for?

Unknowable from the page. No persona is ever named — not VP Finance, not
platform team, not "teams running support agents." The FAQ answers "What do
you need from us?" with a data spec, not a buyer. A visitor cannot tell
whether this is for them unless they arrived already convinced they have an
agent-cost problem. There is no "built for teams who..." sentence anywhere.

## 3. What is the visitor supposed to DO?

There are six competing actions and no single path:

1. "Get the free diagnostic" (mailto link, hero)
2. "Read the docs" (GitHub, hero)
3. `pip install git+https://...` (self-serve, OSS section)
4. "Start the diagnostic" (CTA section)
5. "Star on GitHub" (CTA section)
6. Announcement bar: "query your agent economics from ChatGPT and Claude
   with the Averth MCP server"

Is it self-serve or sales-led? The pip install says self-serve. The mailto
CTA says talk to us. "NO INTEGRATION, RAW CUSTOMER CONTENT, OR CALL NEEDED
FIRST" says self-serve. A visitor who wants the one obvious next step will
not find it.

## 4. Everything that confused me

**a) The core contradiction — send data vs. nothing leaves your machine.**
The method section, within ~200px of each other:
- "You run the exporter locally and **send a small batch of sanitized runs;
  we return the economics**."
- Step 1: "One command on traces you already have. **Everything runs on
  your machine; your traces never leave your environment**."
The CTA section says "Send a batch. Get the P&L." So which is it — do I send
you my runs, or does nothing leave my machine? Both statements are on the
same page. A privacy-conscious buyer (the exact buyer this product needs)
hits this contradiction and leaves.

**b) The announcement bar contradicts the privacy story again.**
"New: query your agent economics from ChatGPT and Claude with the Averth
MCP server." An MCP server wired into ChatGPT/Claude implies data flowing
to those services — immediately after the page promised nothing leaves the
machine. Even if the architecture is sound, the juxtaposition reads as
dishonest to a skimmer.

**c) "Cost per accepted outcome" is never defined.**
It appears in the terminal, the FAQ, and three sections — but nowhere does
the page say what makes an outcome "accepted." This is the product's core
unit and a first-time visitor has to guess. (The README's honest
UNKNOWN-without-labels story — the single best differentiator — is nowhere
on the page at all.)

**d) The hero numbers have no anchor.**
"The invoice said $0.20. The outcome cost $0.82." Per what? Per run? Per
month? Per thousand runs? A visitor spends their first 10 seconds doing
unit-guessing instead of understanding.

**e) "Fully loaded cost" is unexplained jargon on first view.**
The terminal breaks it down (retry path $0.19, tools $0.10, human review
$0.52) but the hero uses the term without the decomposition. "Loaded with
what?" is the natural question and the hero doesn't answer it.

**f) "The five cost layers" is used 4+ times before being defined.**
The layers section eventually defines them, but the product cards and hero
reference "five layers" / "five cost layers" long before. First mention
should carry the definition or link to it.

**g) "Offline policy replay" is the most confusing product description.**
"Replay a budget or routing policy against historical runs: which runs would
have been stopped, the waste saved, and the collateral damage to successful
runs." — "Collateral damage to successful runs" is opaque. A visitor cannot
picture what this feature does or why they'd want it.

**h) The page sells a future as the present.**
"From diagnosis to control" / "The same policy layer can then continuously
identify when a run should be stopped, rerouted, or escalated." Then the
FAQ admits: "Production enforcement is not enabled as part of the
diagnostic." So the "control" half of the page's arc doesn't exist yet. A
technical buyer who reads the FAQ after the loop section will feel misled.

**i) Unexplained statistics jargon.**
"p50 / p95 / max per attempt: $0.02 / $5.68 / $9.78" and "Test workload
yield: 6%" and "Terminal-path yield." None of these terms are defined for a
non-technical visitor. The finance buyer the product wants will bounce off
"terminal-path."

**j) The CTA fine print is grammatically ambiguous.**
"NO INTEGRATION, RAW CUSTOMER CONTENT, OR CALL NEEDED FIRST" — reads as a
list of things that are... needed? not needed? It means "you don't need any
of these," but it parses as the opposite on first read.

**k) Who is "we"?**
"We return the economics" (method section) implies a service company. The
pip install and MIT license imply open source you run yourself. The mailto
CTA implies a founder doing diagnostics by hand. All three are probably
true, but a visitor can't tell what the business is: product, service, or
repo.

**l) "Accepted outcome" vs "successful run" vs "outcome."**
Used interchangeably across sections with no definitions. If "accepted" is
doing load-bearing work in the product's honesty story, it needs one
definition, early, used consistently.

## 5. Does the page say what it is NOT?

Once, buried in the FAQ: "Is this another token-cost dashboard?" → "No.
Token dashboards answer what the model cost. Averth answers what the
outcome cost."

That is the entire negation on the page, and a skimmer never reaches it.
Wesley's positioning — "not another cost dashboard; it tells you the one
change worth testing" — never appears above the fold. A visitor skimming
the hero and product cards could reasonably conclude "oh, a cost dashboard
with extra charts," which is exactly the dismissal the product needs to
preempt.

## Verdict

Wesley's worry is **proven, with one qualification**: the hero's first 10
seconds are actually fine. The damage happens in seconds 10–60, where the
page (1) contradicts itself on whether data leaves the visitor's machine,
(2) offers six competing actions with no single path, (3) never names who
it's for, (4) buries its best differentiator (honest UNKNOWN accounting —
absent entirely), and (5) sells a "control" future the FAQ admits doesn't
exist. A confused buyer doesn't convert; a buyer who spots the
send-vs-local contradiction actively distrusts.

Highest-leverage fixes, in order:
1. Resolve the send-vs-local contradiction into one coherent story.
2. One primary CTA (pick: self-serve install OR diagnostic email).
3. Name the buyer in one sentence ("Built for teams running customer-facing
   agents who need to answer: what does each resolved ticket actually cost?").
4. Put the "not a dashboard" negation and the UNKNOWN honesty story above
   the fold — they are the differentiators.
5. Demote "control"/enforcement language to clearly-labeled future, or cut it.
