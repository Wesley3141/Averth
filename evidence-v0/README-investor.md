# Averth V0 — investor brief (one page, honest version)

**What Averth is, today:** a local meter for AI agent work, plus a
new, small, working V0 evidence verifier built locally on 2026-11-03.
The meter tells you what an agent run actually cost, where retries
and context burned it, and cost per usable result on traces it can
join to an outcome. The V0 verifier answers a narrower, adjacent
question: for a small set of human-written acceptance checks, what
does the record actually show — VERIFIED, FAILED, NOT OBSERVED,
EXTERNAL-UNVERIFIABLE, or NOT APPLICABLE — with command, timestamps,
exit code, digests, and after-final-edit status for every judgment.

**What is built and runnable:** a Python tool (standard library
only, no model calls, no network, no credentials) in
`evidence-v0/` on branch `v0-evidence-verifier` (the earlier
prototype copy lived in `experiment-14day/v0-verifier/`), with
five core modules (trace_adapter, requirement_spec,
evidence_ledger, verifier, reporter) plus a CLI. It is read-only
by default, executes only allowlisted pytest commands and only
on an explicit `--execute` flag, and outputs one JSON ledger
plus one Markdown report from the same judgments. It has 19
unit tests after wave 1, all passing, run with the Averth repo
venv python because system python3 has no pytest.

**What is proven, on the local fixture only:** on a toy widget
fixture (add correct, subtract correct, multiply intentionally
buggy, returning a sum instead of a product), the imported-run mode
produces VERIFIED 2 (add, subtract), FAILED 2 (multiply, full
suite), NOT OBSERVED 2 (edge tests never run in any recorded run;
build never run), EXTERNAL-UNVERIFIABLE 1 (real-hardware claim),
NOT APPLICABLE 1 (database migration, no database in the fixture),
unknown rate 37.5%, with 1 superseded run retained and never cited.
In live-recorded mode the tool runs the edge tests and they pass,
so C5 becomes VERIFIED and the unknown rate falls to 25.0% — the
row moves because the check was actually run, not because it was
relabeled. On a public benchmark trace, the existing Averth meter
reproduces 12 attempts, 9 trace-labelled completions, 32 retries,
$1.94 fully loaded per trace-labelled success, 9.4x context
compounding, and 21% yield, on an ESTIMATED cost basis that must
not be quoted as measured spend or as a bill.

**What is unproven, stated plainly:** there is no independently
validated repair. Zero live improvement benchmarks have been run.
Zero paying customers exist for the new direction. The V0 is NOT
validated on a real workflow: the fixture is toy code, the trace
is a public benchmark, and neither is a customer's work. There is
no Tier 2/3 evidence in the imported-run mode (Tier 1 only); in
live-recorded mode Tier 2 means this tool's own local recorder,
which is stronger observation, never tamper-proof provenance, and
no independent CI attestation (Tier 3) is wired in. The V0 does
not prove test quality, correctness beyond the named assertions,
acceptance by any human or operator, value, time saved,
willingness to pay, or boot on untested hardware. It does not
repair, guard, monitor, or orchestrate anything.

**What would change the story:** one independently validated
improvement on a real coding-agent workflow (unmodified vs simple
truncation vs structured compaction, on matched tasks, measuring
success, cost, time, and quality), followed by a developer
voluntarily trying the analysis on their own work. That experiment
is blocked on model access until a newly authorised model
evaluation environment is provided; local credentials are not
used to unblock it. Until then, the honest pitch is a credible
local report and a defined experiment, not a proven product.

**Wave 1, 2026-11-04, branch checkout, uncommitted, not merged,
not pushed, not deployed:** a multi-runner matcher fix, so npm,
cargo, make, and go runs are now cited separately instead of
collapsing onto one run; a generic recorded-run converter that
never executes a command string; an explicit per-workflow
runner allowlist, separate from the pytest-only cli.py execute
mode; a check-writing interview with a no-test worked example;
and a fixture-based PR evidence converter that keeps CI runs
as Tier 1 and every other PR or review claim as Tier 0. The
PR converter made no live GitHub fetch in this wave. After
wave 1, the limits in the paragraph above are unchanged: no
real workflow validation, zero live benchmarks, zero paying
customers, no validated repair, no measured improvement or
saving. Wave 1 is progress toward an installable tool, not a
prod-ready product, and no customer install is promised on
the basis of this brief.

**Wave 2, 2026-11-05, branch checkout, uncommitted, not merged,
not pushed, not deployed, not published to PyPI:** install
packaging as averth-evidence version 0.2.0, with a tested
clean-install smoke run from a fresh directory, VERIFIED 1,
unknown rate 0.0, 1 run, 0 superseded; a JSONL trace
normaliser, summary only, never a verdict; timestamp and
final-edit capture, with missing start timestamp returning
NOT OBSERVED, never a pass; artifact digest capture for
non-Python repos, with a remote URL never accepted as a
digest; and a live PR fetch path, implemented with mocked
tests, labelled not live-verified, never cited as
live-verified or as a merge certifier. Tests are now 32
passed, 0 failed. After wave 2, the limits above are
unchanged: no real workflow validation, zero live
benchmarks, zero paying customers, no validated repair,
no measured improvement or saving. Wave 2 is closer to
installable, with a tested install path, but it is not a
prod-ready product, and no customer install is promised
on the basis of this brief until reviewers verify wave 2
and a real workflow is run.

**Ask, if any:** nothing is being sold on the basis of this brief.
No subscription, price, or saving is claimed. Any conversation
that follows is discovery (does this report save review time?),
not an invitation to test an unproven repair.

**Wave 3, 2026-11-05, branch checkout, uncommitted, not merged,
not pushed, not deployed, not published to PyPI:** universal
ingestion for any supported input shape, in universal_ingest.py:
JSON, JSON array, JSONL, pretty printed JSON, plain text
logs, OpenTelemetry style spans, and meter style events,
detected from content, with original IDs, verbatim commands,
and unknown fields preserved. Runner detection across
pytest, npm, yarn, pnpm, cargo, go, make, gradle, maven,
dotnet, phpunit, rspec, jest, vitest, shell, docker, and a
generic path for anything else. A check is judged only from
its own exact command run. Generic executed mode with an
operator written allowlist runs any exactly listed command,
any runner (one runner per allowlist file); without an
allowlist, execute stays pytest only.
Observe only mode and inferred rows mean a workflow with no
human checks never passes: inferred rows are always NOT
OBSERVED and labelled not human acceptance. Timestamps in
ISO, common date forms, and epoch seconds through nanos;
unparseable timestamps are never invented. Malformed input,
unknown runners, missing exit codes, and mixed language runs
produce a ledger, not a crash. Tests are now 53 passed, 0
failed, 32 before wave 3 plus 21 new, covering Python, Node,
Rust, Go, shell, multi language, frontend build and lint,
no tests, no exit code, malformed JSONL, and OpenTelemetry
spans. After wave 3, the limits above are still true, in
plain language: unknown inputs are reported as unknown, not
judged, and a ledger is not proof of correctness, acceptance,
value, time saved, or willingness to pay. No real workflow
validation, zero live benchmarks, zero paying customers, no
validated repair, no measured improvement or saving, and the
live PR fetch is still mocked only, not live verified. Wave 3
does not prove the tool on a completely different workflow:
it proves the tool can ingest that workflow without crashing
and can report honestly what is unknown, provided human
checks, a snapshot, timestamps, and permission are supplied.
No customer install is promised on the basis of this brief
until reviewers verify wave 3 and a real workflow is run.
