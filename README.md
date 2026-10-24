# Averth

**One command on your traces reveals the change worth testing.** Averth measures the fully-loaded cost of every AI agent run — model spend, retries, tool calls, human review — and names the single fix worth trying first.

```bash
pip install git+https://github.com/Wesley3141/Averth.git
averth trace traces.json --format langfuse
```

Runs locally. Your traces never leave your machine.

## The problem

Token dashboards tell you what the model cost. They don't tell you what the workflow cost. In practice:

- **Retries and failed runs** burn tokens that never produce an outcome
- **Context growth** compounds cost across steps (4.7x in our simulations)
- **Human review time** is real spend that never appears on the model bill
- **Averages lie** — the top 5% of attempts often consume the majority of budget

Teams discover this when the invoice arrives, not when the workflow ships.

## What Averth does

Averth reads the traces you already have (Langfuse, LangSmith, OpenTelemetry, or JSONL) and produces a trustworthy cost receipt:

- **Fully-loaded cost per attempt** — model spend, retry paths, tool calls, and human review time, shown as separate lines
- **Data quality, stated honestly** — every dollar labeled by provenance: vendor-billed, priced on recorded tokens, estimated (fallback prices, tokens estimated from text, or tool estimates), or unknown. Spend from estimated tokens lands in Estimated, never Priced. Missing usage data is flagged loudly, never rendered as free; context tax on fallback-priced runs prints n/a, not $0.00.
- **The five cost layers** — context compounding, tool spend, yield ratio, heavy-tail outliers, and per-model attribution, explaining *why* the number is what it is
- **One change worth testing** — top retry reasons, costliest attempts, and failed-run waste, pointing at the single highest-leverage fix

What it is not: another cost dashboard. The output of an Averth run is a concrete change to test, with before/after cost and agreed output quality compared together.

## Quickstart

**Already have traces?** This is the whole pilot:

```bash
pip install git+https://github.com/Wesley3141/Averth.git
averth trace run-2026-09.json --format langfuse --html report.html
```

Supported formats: `langfuse`, `langsmith`, `otel`, `jsonl`, `claude` (Claude Code session JSONL, one session file at a time; see the importer docstring for its cache and sidechain limits), `codex` (Codex CLI rollout JSONL, one rollout file at a time; token_count snapshots are cumulative, so the importer counts deltas, and the model comes from turn_context; see the importer docstring for its compaction, subagent, and pricing limits). The text receipt prints to stdout; `--html` writes a shareable report.

**Want the AI read on it?** Bring your own key, get the recommendation:

```bash
export AVERTH_ANTHROPIC_KEY=...   # or AVERTH_OPENAI_KEY; used once, never stored
averth advise run-2026-09.json --format langfuse --mode recommend
```

Three modes: `recommend` (the one change worth testing), `explain` (plain English for the budget owner), `investigate` (why an attempt cost what it did). `--show-prompt` prints exactly what the LLM would see, no call spent. The advisor only reads sanitized cost aggregates, never your prompts or data.

**Want to catch runaways?** Flag the cost outliers before finance does:

```bash
averth trace run-2026-09.json --format langfuse --anomaly
```

Attempts above p95 with their dominant driver, ranked by dollars. Cost anomalies only, never attack attribution ("inspect, not accusations").

**Want to instrument a live agent?** See [docs/QUICKSTART.md](docs/QUICKSTART.md) — three minutes with the `Tracker` API, plus a LangChain callback handler for zero-code instrumentation.

**Evaluating for a pilot?** See [docs/PILOT.md](docs/PILOT.md) for the evidence standard: accepted-outcome labels and actual billing inputs. Trace completion alone is not an accepted outcome.

## Honest by design

- **No outcome labels, no cost-per-success.** Without accepted-outcome labels joined to traces, cost per successful outcome renders as UNKNOWN. An error-free trace is not an accepted outcome.
- **Missing usage is flagged, never zero-filled.** Calls with no token data are recorded at $0.00 and labeled unknown, with a loud warning — never presented as free.
- **Prices are versioned and dated.** Every report stamps the price-table vintage (currently v8, dated 2026-10-23); a warning fires when the table is older than 90 days.
- **Read-only.** The meter makes no network calls and exfiltrates no data. The ledger contains cost/token/timing metadata only — no prompts, completions, or tool payloads.

## Repository layout

```
averth/            the package (tracker, importers, reporting, policy sim)
tests/             412 passing, 1 skipped, including an adversarial chaos suite
pilot-sim/         clean-install prospect simulation (fake traces, all formats)
examples/          demo.py — simulated 2,000-ticket month across all five layers; validated-diagnoses/ — the 40-POC outreach-ready index plus all 43 counted A-lane POC files (see examples/validated-diagnoses/README.md for what the dollars are not)
docs/              QUICKSTART, PILOT, VALIDATION, and design docs
benchmark/         pinned-ticket benchmark + deployment-gate shadow harness
validation-traces/ saved trace fixtures with expected outputs
```

## Local verification

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,langchain,openai]'
.venv/bin/python -m pytest -q
```

Or prove the prospect path end to end (fresh venv, install from GitHub, fake production traces in all three formats, numeric receipt assertions):

```bash
./pilot-sim/run_prospect_sim.sh
```

## License

MIT. See `LICENSE`.
