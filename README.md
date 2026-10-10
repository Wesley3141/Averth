# Averth

**The economic meter for AI agents.** Point it at your existing traces and get a one-page breakdown: what each workflow really costs per successful run, which step burns the most, and the one change worth testing first.

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
- **Data quality, stated honestly** — every dollar labeled by provenance: vendor-billed, measured (tokens x prices), estimated, or unknown. Missing usage data is flagged loudly, never rendered as free.
- **The five cost layers** — context compounding, tool spend, yield ratio, heavy-tail outliers, and per-model attribution, explaining *why* the number is what it is
- **One change worth testing** — top retry reasons, costliest attempts, and failed-run waste, pointing at the single highest-leverage fix

What it is not: another cost dashboard. The output of an Averth run is a concrete change to test, with before/after cost and agreed output quality compared together.

## Quickstart

**Already have traces?** This is the whole pilot:

```bash
pip install git+https://github.com/Wesley3141/Averth.git
averth trace run-2026-09.json --format langfuse --html report.html
```

Supported formats: `langfuse`, `langsmith`, `otel`, `jsonl`. The text receipt prints to stdout; `--html` writes a shareable report.

**Want to instrument a live agent?** See [docs/QUICKSTART.md](docs/QUICKSTART.md) — three minutes with the `Tracker` API, plus a LangChain callback handler for zero-code instrumentation.

**Evaluating for a pilot?** See [docs/PILOT.md](docs/PILOT.md) for the evidence standard: accepted-outcome labels and actual billing inputs. Trace completion alone is not an accepted outcome.

## Honest by design

- **No outcome labels, no cost-per-success.** Without accepted-outcome labels joined to traces, cost per successful outcome renders as UNKNOWN. An error-free trace is not an accepted outcome.
- **Missing usage is flagged, never zero-filled.** Calls with no token data are recorded at $0.00 and labeled unknown, with a loud warning — never presented as free.
- **Prices are versioned and dated.** Every report stamps the price-table vintage; a warning fires when the table is older than 90 days.
- **Read-only.** The meter makes no network calls and exfiltrates no data. The ledger contains cost/token/timing metadata only — no prompts, completions, or tool payloads.

## Repository layout

```
averth/            the package (tracker, importers, reporting, policy sim)
tests/             334 tests, including an adversarial chaos suite
pilot-sim/         clean-install prospect simulation (fake traces, all formats)
examples/          demo.py — simulated 2,000-ticket month across all five layers
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
