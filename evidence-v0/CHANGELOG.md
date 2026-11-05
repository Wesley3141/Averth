# Averth V0 evidence verifier, changelog

This changelog covers evidence-v0/ on branch v0-evidence-verifier
only. It is not the main Averth meter changelog. Nothing here
is published to PyPI yet. A version number here means the
branch checkout carries that code, not that a release was
shipped, installed by a customer, or validated on a real
workflow.

## 0.3.0, wave 3, branch checkout only, not published

- Universal ingestion: universal_ingest.py accepts JSON,
  JSON array, JSONL, pretty printed JSON, plain text logs,
  OpenTelemetry style spans, and meter style events,
  detected from content, preserving original IDs, verbatim
  commands, and unknown fields. A new format is a new
  adapter, not a verifier rewrite.
- Runner detection across languages, plus a generic path
  for any other command. A check is judged only from its
  own exact command run, never from another runner's run.
  Missing exit codes are NOT OBSERVED, never FAILED.
- Generic executed mode: cli.py --execute with an
  operator written --allowlist runs any exactly listed
  command, any runner (one runner per allowlist file).
  Without an allowlist, execute
  stays pytest only. Destructive command review warning
  and quoting limit are kept.
- No test workflows: observe only mode with no --checks,
  and INFERRED rows with --infer-checks, always NOT
  OBSERVED, never human acceptance, never a pass.
- Timestamps: ISO, common date forms, and epoch seconds,
  milliseconds, microseconds, and nanoseconds. Unparseable
  timestamps are never invented.
- Failure tolerance: malformed lines, unknown fields,
  unknown runners, missing exit codes, and mixed language
  runs produce a ledger, not a crash, with counts reported.
- Tests: 53 passed, 0 failed, 32 before wave 3 plus 21 new,
  covering Python, Node, Rust, Go, shell, multi language,
  frontend build and lint, no tests, no exit code,
  malformed JSONL, and OpenTelemetry spans.
- Remaining honest limits, unchanged in kind: unknown
  inputs are reported as unknown, not judged. A ledger is
  not proof of correctness, acceptance, value, time saved,
  or willingness to pay. No real workflow validation, no
  live benchmarks, no paying customers, no validated
  repair, no measured saving, live PR fetch mocked only.

## 0.2.0, wave 2, branch checkout only, not published

- Install packaging: evidence-v0/pyproject.toml installs the
  tool as averth-evidence from the branch checkout, with a
  tested clean-install smoke run from a fresh directory.
  PyPI publication is prepared, not done.
- JSONL trace normaliser: trace_normaliser.py, summary only,
  never a verdict. It converts a JSON array, pretty-printed
  JSON objects, or one JSON object per line into one JSON
  object per line with type and case_id preserved, counting
  unparseable input instead of guessing.
- Timestamp and final-edit capture: timestamp_capture.py,
  validation of ISO timestamps, derivation of a final-edit
  marker from a directory, and the exact V0 outcome when a
  timestamp or marker is missing. Missing start timestamp
  means NOT OBSERVED, never a pass. Missing marker falls
  back to the repo snapshot latest modification time, which
  is documented as a limitation, not a proof of edit order.
- Artifact digest capture for non-Python repos:
  artifact_snapshot.py, copy an artifact file into a local
  snapshot directory with a SHA-256 digest recorded. A
  remote URL is never accepted as a digest. A named human
  confirmation is recorded separately, scoped to that tester
  and procedure, never as a digest.
- Live PR evidence converter: pr_live_fetch.py, a
  credential-free public GitHub API fetch of a pull request,
  its files, reviews, comments, and check runs, converted
  to the same ledger shape as the fixture converter. Live
  fetch is implemented with mocked tests, and is labelled
  not live-verified in this wave, because no live GitHub
  API run was verified with the tools available to this
  wave. Do not cite it as live-verified until a real PR
  fetch is run and recorded.
- Demo package formal second-pass sign-off: see the wave 2
  report. The demo package was re-run against the current
  branch tool, and its guide counts were checked against
  the new 19 plus wave 2 test total, not the old 9.
- Investor brief v2 qualification pass: see
  v0-demo-package/08-INVESTOR-BRIEF-V2.md as updated in
  this wave, with demo status, exact check counts,
  ESTIMATED labels, LangGraph and OpenTelemetry exclusions,
  datasets identified but not evaluated, GitHub tier
  distinctions, no superiority claim, explicit zero live
  improvement results, zero paying customers, and future
  goal distinguished from current capability.

## 0.1.0, wave 1, branch checkout only, not published

- Gap 0 matcher fix: only a Python interpreter token is
  dropped in normalize_command. npm, cargo, make, and go
  are kept, so distinct runners no longer cite one run.
- Adapter 1: recorded_run_converter.py, JSON and log
  inputs, never executes a command string.
- Adapter 3: runner_allowlist.py and allowlist_runner.py,
  exact listed command only, confirmation flag required.
  cli.py --execute stays pytest-only.
- Adapter 6: check_interview.md, intent to 3 to 5
  human-written checks, no auto-extraction.
- Adapter 7, fixture-based: pr_evidence_converter.py, CI
  runs to Tier 1, every other PR claim stays Tier 0.
- Tests: 19 passed, 0 failed, with the Averth repo venv
  python, 9 original plus 10 new adapter tests.

## 0.0.0, initial V0, branch commit 40f12e2

- Local-first, read-only retrospective verifier, standard
  library only, no model calls, no network, no credentials.
- Five modules plus a CLI, one JSON ledger plus one
  Markdown report, 9 unit tests passing.
- Tested only on a local fixture and public traces, not
  on a real developer workflow. Zero live benchmarks,
  zero paying customers, no validated repair.
