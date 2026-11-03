# V0 evidence verifier — README

A small, local-first, read-only retrospective evidence verifier. It is
NOT a platform, NOT fleet analytics, NOT always-on monitoring, NOT a
SaaS dashboard, NOT automatic guard generation, and NOT a repair
actuator. It produces one machine-readable JSON ledger plus one
concise Markdown report from the same judgments.

## What it does

- Takes a human-written acceptance-check file (3–5 checks, manually
  seeded, NOT auto-extracted), a repo directory, and optionally a
  recorded-run ledger and/or a JSONL trace file.
- Judges each check as VERIFIED, FAILED, NOT OBSERVED,
  EXTERNAL-UNVERIFIABLE, or NOT APPLICABLE, with evidence ID, source,
  trust tier (0–4), command, working directory, timestamps, exit code,
  output digest, artifact digest, and after-final-edit status.
- Retains superseded runs (started before the final edit marker) in
  history and never cites them.
- Keeps NOT OBSERVED distinct from NOT EXECUTED, and never turns a
  successful shell command into proof of correctness.
- Summarises a trace file only. A trace summary is never a verdict,
  and no cost-per-accepted-outcome figure is computed from a trace
  with no acceptance join.

## Modules

- `trace_adapter.py` — recorded-run ledger import (Tier 1) and JSONL
  trace summarisation (no judgments).
- `requirement_spec.py` — human-written check file parsing and
  validation.
- `evidence_ledger.py` — repo snapshot (SHA-256 digests), git state
  (read-only), append-only ledger, coverage counts, unknown rate.
- `verifier.py` — judging rules and the execution allowlist.
- `reporter.py` — JSON ledger + Markdown report from the same rows,
  with a mandatory LIMITATIONS section.
- `cli.py` — command-line entry point.

## Safety

- Read-only by default, explicit user-triggered run. The target repo
  is never modified, except an operator-chosen `--out` directory if
  the operator explicitly puts it there. No `.claude/settings.json`,
  git hook, CI, PR, or production service is ever touched.
- Only explicitly allowlisted pytest commands are ever executed, and
  only with `--execute`. The allowlist is: `python -m pytest` with
  `-q`/`-v` flags and relative test paths/nodes inside the repo.
  No shell, no arbitrary command from a README, PR, issue, or
  transcript is ever executed. A non-allowlisted check is skipped
  with a printed note, and its check stays NOT OBSERVED; refusal
  never aborts the report.
- No network, no model calls, no credentials, no uploads. The
  default upload set is empty; this tool has no upload path.
- Tier 2 (this tool's own local recorder) is stronger observation,
  NOT tamper-proof provenance. No Tier 3 is wired in, so no Tier 3
  row is ever produced. Tier 4 only with a named tester and named
  procedure supplied in the check file.

## How to run it

```bash
cd ~/workspace/research/averth-pivot-2026-11-02/experiment-14day/v0-verifier

# Unit tests (system python3 has no pytest; use the Averth venv):
~/workspace/averth/.venv/bin/python -m pytest -q tests/
# Result, 2026-11-03: 9 passed.

# (a) Fixture, imported recorded runs (Tier 1):
python3 cli.py --repo ../evidence-fixture \
  --checks examples/fixture-checks.json \
  --runs ../evidence-fixture/evidence_ledger.json \
  --out runs/imported --report-id v0-fixture-imported
# Result: VERIFIED 2, FAILED 2, NOT OBSERVED 2,
#   EXTERNAL-UNVERIFIABLE 1, NOT APPLICABLE 1, unknown rate 37.5%,
#   5 runs, 1 superseded and retained, never cited.

# (a2) Fixture, live-recorded runs (Tier 2; --python must have pytest):
python3 cli.py --repo ../evidence-fixture \
  --checks examples/fixture-checks.json --execute \
  --python ~/workspace/averth/.venv/bin/python \
  --out runs/executed --report-id v0-fixture-executed
# Result: VERIFIED 3 (add, subtract, and edge tests, which are
#   actually run in this mode), FAILED 2 (multiply, full suite),
#   EXTERNAL-UNVERIFIABLE 1, NOT OBSERVED 1 (build, never run),
#   NOT APPLICABLE 1, unknown rate 25.0%.
# Note the honest difference between (a) and (a2): in (a) the edge
# tests were never run in any recorded run, so C5 is NOT OBSERVED;
# in (a2) the tool runs them and they pass, so C5 becomes VERIFIED.
# Running the check is what moves the row, not relabelling it.

# (b) Public benchmark trace, Averth meter read-only (from ~/workspace/averth):
.venv/bin/python -m averth.cli trace validation-traces/mini-swe-agent-s3/events.jsonl --format jsonl
# Reproduced 2026-11-03: 12 attempts, 9 trace-labelled completions,
# 32 retries, fully loaded $1.94 per trace-labelled success,
# context compounding 9.4x, yield 21%, retry loops $13.60 (78%).
# Cost basis is ESTIMATED per the CLI itself; do not quote it as
# measured spend or as a bill. Completions are trace labels, not
# accepted outcomes.

# (b2) Same trace summarised by the V0 tool (summary only, no verdict):
python3 cli.py --repo ../evidence-fixture \
  --checks examples/fixture-checks.json \
  --runs ../evidence-fixture/evidence_ledger.json \
  --trace ~/workspace/averth/validation-traces/mini-swe-agent-s3/events.jsonl \
  --out runs/imported-with-trace --report-id v0-fixture-imported-with-trace
# Trace summary: 938 lines, 12 cases, 447 model events, 447 tool
# events, 32 retry events, 12 end events, 5,182,465 input tokens,
# 69,883 output tokens. No cost-per-accepted-outcome is computed.
```

## What it provably does and does not do

Does: record what was actually tested, with command, timestamps, exit
code, digests, and after-final-edit status; distinguish NOT OBSERVED
from NOT EXECUTED; retain superseded runs instead of citing them;
refuse non-allowlisted commands; state its unknown rate up front.

Does not do: prove test quality, correctness beyond the named
assertions, acceptance by any human or operator, value, time saved,
willingness to pay, or boot on untested hardware. It does not repair
anything, does not guard anything, and is not validated on a real
workflow. The next V0 step is one controlled repair experiment,
still blocked on model access unless Wesley authorises a new model
evaluation environment.
