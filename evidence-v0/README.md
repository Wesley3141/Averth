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
- `recorded_run_converter.py`, adapter 1, wave 1: convert a raw
  harness, CI, or log record to ledger JSON. Never executes
  anything. A command string in the input is data only.
- `runner_allowlist.py` and `allowlist_runner.py`, adapter 3,
  wave 1: an explicit per-workflow allowlist. Only a command
  listed exactly, token for token, in an operator-written
  allowlist file may run, and only with an explicit
  confirmation flag. cli.py --execute stays pytest-only.
- `check_interview.md`, adapter 6, wave 1: intent to 3 to 5
  human-written checks before judging, with a worked example
  for a no-test workflow.
- `pr_evidence_converter.py`, adapter 7, wave 1, fixture-based:
  convert CI runs to ledger runs and list every other PR or
  review claim as Tier 0. No live GitHub fetch in this wave.

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

## Wave 1 build status, 2026-11-04, branch checkout, uncommitted

Built in this wave, in the branch checkout only, not merged to
master, not pushed, not deployed:

- Gap 0 matcher fix, synced from the experiment copy into
  evidence-v0/trace_adapter.py. Only a Python interpreter token
  may now be dropped. npm, cargo, make, and go are kept.
  Multi-runner probe, branch cli.py on the generality probe:
  P2 VERIFIED citing npm run, P3 VERIFIED citing cargo run,
  P5 VERIFIED citing make run, P4 VERIFIED citing go run.
  Full probe counts: VERIFIED 6, NOT OBSERVED 3,
  EXTERNAL-UNVERIFIABLE 1, unknown rate 40.0 percent, 6 runs,
  1 superseded and retained, never cited. Before this fix,
  P3 and P5 cited the npm run in status only.
- Adapter 1, recorded_run_converter.py, with JSON and log
  input formats and example files in examples/. It never
  executes a command string. A converted run is Tier 1, the
  same as any imported run, and conversion does not make a
  log trustworthy.
- Adapter 3, runner_allowlist.py and allowlist_runner.py,
  with an example npm allowlist in examples/. Only an exact
  listed command may run, only with a confirmation flag.
  cli.py --execute remains pytest-only; adapter 3 is a
  separate, operator-approved path, never automatic, never
  from a transcript.
- Adapter 6, check_interview.md, with examples/no-test-checks.json.
  Smoke run on that template, with no recorded runs and no
  supplied human confirmation: NOT OBSERVED 2, FAILED 2,
  EXTERNAL-UNVERIFIABLE 1, unknown rate 60.0 percent, 0
  VERIFIED. That is the honest template result, not a pass.
- Adapter 7, pr_evidence_converter.py, fixture-based only,
  with examples/pr-fixture.json. CI runs become Tier 1
  ledger runs; every other PR or review claim stays Tier 0
  and is never turned into a run. No live GitHub fetch was
  made in this wave, and no report from this converter may
  be cited as live-verified or as a merge certifier.
- Tests: 19 passed with the Averth repo venv python
  (9 original plus 10 new adapter tests), 0 failed.

Still true after wave 1, and still a limit on any prod claim:
V0 has only run on a local fixture and public traces, not on
a real developer workflow. Zero live benchmarks, zero paying
customers, no validated repair, no measured improvement, no
measured saving. Executed mode in cli.py is pytest-only.
Trace mode is summary only, never a verdict. The live repair
benchmark stays blocked pending a newly authorised model
evaluation environment, never local credentials.

## Wave 2 build status, 2026-11-05, branch checkout, uncommitted

Built in this wave, in the branch checkout only, not merged
to master, not pushed, not deployed, not published to PyPI:

- Install packaging: evidence-v0/pyproject.toml, package
  averth-evidence, version 0.2.0, console script
  averth-evidence, with INSTALL.md and CHANGELOG.md.
  Clean-install smoke run from a fresh directory, using
  only the installed tool, not the workspace copy:
  VERIFIED 1, unknown rate 0.0, 1 run, 0 superseded.
  PyPI publication is prepared, not done.
- JSONL trace normaliser: trace_normaliser.py, one JSON
  object per line, summary only, never a verdict. It
  accepts a JSON array, pretty-printed objects, or one
  object per line, preserves type and case_id where
  present, invents neither, and counts unparseable input
  instead of guessing.
- Timestamp and final-edit capture: timestamp_capture.py,
  ISO validation, marker derivation from a directory,
  and the exact V0 outcome for a missing fact. A run
  with no parseable start timestamp is NOT OBSERVED,
  never a pass. A run before the final-edit marker is
  superseded, retained, never cited. A missing marker
  falls back to the repo snapshot latest modification
  time, documented as a limitation, not a proof of edit
  order.
- Artifact digest capture for non-Python repos:
  artifact_snapshot.py, copy a file into a local
  snapshot directory with a SHA-256 digest recorded.
  A remote URL is never accepted as a digest or as a
  source file. A named human confirmation is recorded
  separately, scoped to that tester and procedure,
  never as a digest.
- Live PR evidence converter: pr_live_fetch.py,
  credential-free public GitHub API fetch of a pull
  request, files, reviews, comments, and check runs,
  converted to ledger runs plus Tier 0 claims. Check
  runs map to ci-check labels, success to exit 0,
  anything else to exit 1. Status: implemented with
  mocked tests, NOT live-verified in this wave, because
  no live GitHub API run was verified with the tools
  available to this wave. Do not cite it as
  live-verified, and do not cite it as a merge
  certifier.
- Tests: 32 passed, 0 failed, with the Averth repo venv
  python, 9 original plus 10 wave 1 plus 13 wave 2 tests.
  Fixture counts re-run with the branch tool are
  unchanged: imported 2, 2, 2, 1, 1 at 37.5 percent
  unknown, executed 3, 2, 1, 1, 1 at 25.0 percent unknown.

Still true after wave 2, and still a limit on any prod
claim: V0 has only run on a local fixture and public
traces, not on a real developer workflow. Zero live
benchmarks, zero paying customers, no validated repair,
no measured improvement, no measured saving. The live
PR fetch is not live-verified. The demo package formal
second-pass sign-off is recorded in the wave 2 report,
and is not a customer install, a pilot, or a validation
on a real workflow. This wave is closer to installable,
with a tested install path, but it is not, by itself,
a prod-ready product, and no customer install should be
promised on the basis of it until reviewers verify wave
2 and a real workflow is run.
