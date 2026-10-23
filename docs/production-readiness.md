# Production readiness (honest checklist, 2026-10-23)

This page states what this repo is and is not, as of the commit that
added it. It is not a funding claim and not a customer claim.

## What IS ready

- **Test suite green.** Full suite measured 2026-10-23: 412 passed,
  1 skipped, 0 failed (`python -m pytest -q`, 1.97s). The suite
  includes an adversarial chaos suite and importer-hardening tests.
- **Price table v8, vendor-page prices.** `PRICE_TABLE_VERSION = 8`,
  `PRICE_TABLE_UPDATED = "2026-10-23"`, verified against vendors'
  own pricing pages. Every report stamps the price-table vintage
  and warns when the table is older than 90 days.
- **Changelog discipline.** Every feature/fix commit updates
  `docs/CHANGELOG.md` under `## Unreleased` in the same commit,
  including the wave-5/5b corrections (Opus 4.6 repricing, token
  provenance, outcome-unknown handling).
- **Validated diagnoses, inspectable.** `examples/validated-diagnoses/`
  holds the 40-POC outreach-ready index plus all 43 counted A-lane
  POC files, copied verbatim with their wave-5/5b addenda, and a
  README stating exactly what the dollars are not.
- **Clean and inspectable repo.** No secrets, API keys, or private
  material in the tracked tree; scratch outputs (`.venv`,
  `__pycache__`, `*.html` reports) are git-ignored, not tracked.

## What is NOT ready

- **No live-operator production proof.** The 43 diagnoses are
  clean runs over public traces and datasets. No operator has used
  Averth repeatedly on a live workflow, acted on a finding, and
  talked about paying.
- **No paying customer, and no verified outreach recipient.** No
  lane in `examples/validated-diagnoses/` has a verified individual
  recipient, and nothing in this repo is a send draft.
- **The Nov 1 bar is unmet.** One operator using Averth repeatedly
  and talking about paying has not happened yet.
- **New trace formats still need an importer.** Formats outside
  Langfuse, LangSmith, OpenTelemetry, JSONL, and Claude Code
  session JSONL are not covered.
- **Unpriced models fall back to estimated rates.** Dollars for
  unpriced models, and spend computed from chars/4-estimated
  tokens, land in the Estimated bucket, never Priced — and are
  never a bill.

## Bottom line

The repo is clean and inspectable: the meter runs, the suite is
green, the prices are versioned and dated, and the diagnoses are
published with their limits stated. What it does not yet have is
production proof from a live operator. That is the next milestone,
not a claim this repo makes.
