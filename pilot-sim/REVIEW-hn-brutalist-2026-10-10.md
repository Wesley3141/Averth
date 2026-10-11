# HN Brutalist Review: Averth Show HN

## Part 1: Every objection HN will raise

### 1. "Why not just use Langfuse's cost view?"
Langfuse already shows cost per trace, per model, with its own dashboard. The top comment will be someone posting a screenshot of Langfuse's cost tab asking what this adds. If the answer is "we add retries/tools/humans," the reply is "so it's a spreadsheet on top of Langfuse."

### 2. "Your $0.82 is invented."
Someone will do the arithmetic. $0.82 = $0.20 model + $0.10 tools + $0.52 human review. The $0.52 is priced at a $70.20/hr loaded rate — an assumption, stated in the fine print. HN will call the headline number fabricated: "you made up more than half of your own punchline." This is the kill shot. It will be the top comment.

### 3. "The numbers are from your own synthetic data."
Zero production users. The $0.20 vs $0.82 comes from demo.py, seed 42, a simulated 2,000-ticket month. HN will find this in under 90 seconds (it's in the README). "So you've never run this on a real workload" will get 200 upvotes.

### 4. "This is a wrapper."
It's a Python script that parses JSON, multiplies tokens by a price table, and prints a report. HN's favorite insult. The counter ("the value is the honesty, not the math") sounds defensive unless it's baked into the post.

### 5. "355 tests" is vanity.
Nobody cares about your test count. It reads as insecurity. Worse, it invites "how many lines of code?" followed by a coverage-shaming thread.

### 6. "The BYOK advisor undermines everything."
You claim deterministic accounting, then bolt on an LLM that "writes the recommendation." HN will ask: so the actual "one change worth testing" is an LLM hallucinating over aggregates? Which is it — deterministic or vibes?

### 7. "Not on PyPI."
`pip install git+https://...` signals "I haven't even packaged this properly." Five seconds of friction that costs you half the audience.

### 8. "UNKNOWN cost-per-success out of the box."
Your headline metric doesn't work without accepted-outcome labels the user has to join themselves. So a new user runs it and gets UNKNOWN. HN: "congratulations, your tool's main number is 'I don't know.'"

### 9. "Who is this for? I already see my bill."
Anyone running agents at scale sees the provider invoice. The response "but the invoice doesn't attribute to outcomes/retries" is fair — but it has to be IN the post, because the comment will come phrased as a dismissal.

### 10. "Single-author repo, 42 commits, reorganized yesterday."
Someone will click the repo, see one contributor, and call it a weekend project. The force-pushed history rewrite (if noticed) looks worse.

### 11. "The five layers are just... costs."
Context growth, tool spend, yield, tail, attribution. HN: "you discovered that costs have components and gave them names."

---

## Part 2: The post that survives

Strategy: confess everything in the post before the comments can weaponize it. Lead with the synthetic data. Decompose the $0.82. Own the wrapper accusation. Make the honesty the product, not a footnote.

**Title:**

Show HN: Averth – cost accounting for AI agent runs that admits what it can't measure

**Post:**

I built a tool that reads AI agent traces (Langfuse, LangSmith, OpenTelemetry) and tells you what each run actually cost — then ranks the fixes by dollars. It's local-only, one command, MIT licensed.

Full disclosure up front, because you'll find it anyway:

- The headline numbers ($0.20 dashboard vs $0.82 real) are from my own synthetic workload, not production. I have zero production users. The repo is single-author.
- Of that $0.82, $0.52 is human review time at an assumed loaded rate. It's labeled as an assumption in every report, and you override it with your real number. If assumed labor bothers you, the metered model/tool/retry portion was $0.30 vs the $0.20 dashboard — still 1.5x, all measured.
- Yes, the core is arithmetic: tokens × prices, grouped by attempt. The part I actually built is the part dashboards skip: every dollar labeled by provenance (vendor-billed, measured, estimated, unknown), missing usage flagged instead of zero-filled, and cost-per-success printing UNKNOWN when you haven't joined outcome labels — because an error-free trace isn't an accepted outcome and I didn't want the tool to pretend.
- The "one change" output is currently rules over the ledger (top retry reasons, tail concentration, failed-run waste). There's an optional BYOK LLM advisor that writes it up in prose, but it only reads aggregates and the numbers underneath stay deterministic.

Why not just Langfuse's cost tab? That shows what traces cost. This attributes cost to *outcomes* across retries, tool calls, and human handling, then tells you which fix to test first. Different question.

`pip install git+https://github.com/Wesley3141/Averth.git` (not on PyPI yet — fair cop)
`averth trace runs.json --format langfuse`

Genuine question for the room: for those running agents in production, what's the cost component your current tooling gets most wrong? I'm trying to find out if the honest-UNKNOWN approach is useful or just precious.
