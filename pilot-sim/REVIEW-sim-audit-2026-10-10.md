# Hostile audit: pilot-sim prospect simulation
Date: 2026-10-10. Auditor: subagent. Standard: "do we actually know this works."

## Verdict

The core claim SURVIVES but the test setup has two real fixture bugs and
vacuous assertions. The product's accounting is correct (verified to the
cent against ground truth); the simulation does not prove as much as it
claims. Details below. Nothing here requires an LLM to verify — every
finding was reproduced locally.

## What was verified solid

- Clean venv + `pip install git+https://github.com/Wesley3141/Averth.git`
  + `averth trace` works end to end for all three formats. Exit 0, receipt
  renders. (This is the important part, and it holds.)
- Billed bucket matches ground truth exactly: sum of `calculatedTotalCost`
  in langfuse.json = $1.0406; receipt `data_quality.billed` = $1.0406.
- Unknown handling correct: 5 no-usage calls in the fixture render as
  `unknown_calls: 5`, never as free.
- Buckets partition the total: billed + measured + estimated == cost_model
  ($1.1556 == $1.1556).
- Determinism confirmed: two runs of gen_traces.py byte-identical
  (seed 20261010, single-threaded).
- `requires-python = ">=3.9"`; tested on 3.12.3.

## BUG 1 (real): OTel retries are silently dropped

The generator writes the retry marker as attribute `averth.retry_reason`:

```python
attrs.append({"key": "averth.retry_reason",
              "value": {"stringValue": "timeout"}})
```

The importer (`averth/importers/otel.py`, `_brand(attrs, "retry")`) reads
attribute `averth.retry`. Key mismatch → marker never fires.

Reproduced: `retries= 0` for the OTel ledger vs 4 for langfuse/langsmith
on the same logical data. The sim claims "~20% hit a retry" across formats
but exercises zero retries in OTel, and the runner never notices.

Fix: generator should emit `{"key": "averth.retry",
"value": {"stringValue": "timeout"}}`.

## BUG 2 (real): LangSmith failures never register

The generator marks failed tickets via `"error": "ticket reopened"` on the
ROOT chain run. But the importer's failure rule (documented in
langsmith.py, H-LS3) is: a case is failed only if the
chronologically-LAST run (by start_time) has a truthy error.

All LLM runs share `start_time: 2026-09-28T10:00:10Z`; the root chain is
`10:00:00Z`. The last run by start_time is always an LLM run with
`error: None` → `failed=False` for every ticket.

Reproduced: `failed= 0` for langsmith vs 4 for langfuse/otel, on the same
logical tickets. The "Failed-run waste" layer is untested for LangSmith.

Fix: put the error on the last LLM run of failed tickets (matches the
importer's documented native-retry semantics), not just the root.

## Format realism (per-format notes)

Langfuse: GOOD. `{"data": [...]}` matches GET /api/public/traces;
`usageDetails.{input,output}`, `calculatedTotalCost`, `level:
ERROR/DEFAULT`, `type: GENERATION` are all real shapes. The importer
accepts all of them.

LangSmith: GOOD except Bug 2. Run-export shape (id/name/run_type/trace_id/
parent_run_ids/start_time/end_time/error/serialized/outputs/extra.metadata),
`outputs.llm_output.token_usage`, `serialized.kwargs.name`,
`extra.metadata.ls_provider` are all real. Nit: every run in the fixture
shares identical timestamps and the docstring claims "25 tickets over
~2 weeks" — timestamps are all 2026-09-28T10:00. Cosmetic; grouping is by
trace_id so no cross-contamination.

OTel: GOOD except Bug 1. OTLP JSON span shape, `gen_ai.request.model`,
`gen_ai.usage.{input,output}_tokens`, `status.code` are real semconv.
`"ERROR"` as a status code is accepted by the importer (it also accepts
`STATUS_CODE_ERROR`); real OTLP uses `STATUS_CODE_ERROR`, but the
importer's leniency makes this a non-issue for the test.

Minor: `make_call()` in gen_traces.py is dead code (defined, never called).
The TRIAGE/LOOKUP/RESPOND specs ARE used; `make_call` is leftover.

## Assertion weaknesses (run_prospect_sim.sh)

The runner's checks are mostly vacuous — they verify the receipt *renders*,
not that it is *right*:

1. `grep -q "Vendor-supplied (billed)"` passes when billed is $0.00.
   Reproduced: langsmith and otel runs show `Vendor-supplied (billed):
   $0.00` and still pass. The check proves the label exists, nothing more.

2. `grep -qi "unknown"` is vacuous. The string "unknown" appears in
   "Cost per successful outcome: UNKNOWN as an accepted-outcome metric"
   on EVERY run, even with zero unknown calls. (OTel is exempted from this
   check, but langfuse/langsmith would pass it with unknown_calls=0.)

3. No numeric assertions at all: no check that attempts == 25, no check
   that billed/measured match ground truth, no check that
   unknown_calls == 5, no check that retries > 0, no check that failures
   register. A receipt with all zeros and 25 empty attempts would pass
   every current check.

4. No cross-check against the generator's ground truth. gen_traces.py
   prints billed/measured/unknown/failed counts to stdout but the runner
   discards them.

5. `pip install git+https://...` with no `--no-cache-dir` and no commit
   pin: pip may reuse a cached wheel from a previous run, so a "clean"
   test can silently test a stale build. For a proof-grade sim, pin the
   commit or pass `--no-cache-dir`.

6. The venv is deleted (`rm -rf "$VENV"`) BEFORE the final pass/fail
   check, so on failure there is nothing left to debug.

7. `set -u` without `set -e`/`pipefail` is fine here (checks are
   explicit), not flagging it further.

### Proposed stronger assertions

Have gen_traces.py also write `sim-traces/manifest.json`:

```json
{"tickets": 25, "calls": 82, "billed": 62, "billed_total": 1.0406,
 "measured": 15, "unknown": 5, "failed": 4, "retries": <n>}
```

Then in run_case, parse the receipt with Python (not grep) and assert:

- attempts == manifest.tickets
- |data_quality.billed - manifest.billed_total| < 0.005
- data_quality.unknown_calls == manifest.unknown   (langfuse, langsmith)
- data_quality.measured > 0
- billed + measured + estimated == cost_model  (no-double-count invariant)
- retries >= 1  (after Bug 1 fix; langfuse/langsmith/otel)
- failed attempts >= 1  (after Bug 2 fix; all three formats)
- "UNKNOWN as an accepted-outcome metric" present (no outcome labels)

That turns the sim from "it renders" into "it computes correctly."

## Environment gaps (ways a real prospect differs)

1. Python version: only 3.12 tested. `requires-python >= 3.9` is
   declared but 3.9/3.10/3.11/3.13 never exercised. (Risk: low — no
   3.10+ syntax spotted — but untested is untested.)
2. `pip install git+https://...` requires git on the machine. Not every
   prospect box has it. Undocumented prerequisite.
3. No PyPI package: `pip install averth` fails. The outreach "one
   command" is really two commands (pip install, then averth trace).
   The sim tests what's documented in QUICKSTART, which is correct —
   but the outreach copy slightly oversells the simplicity.
4. Bash-only runner: no Windows coverage. A Windows prospect follows a
   different path (venv creation, activation) that is entirely untested.
5. Network: the sim assumes GitHub is reachable. A prospect behind a
   corporate proxy with no git-protocol allowance would fail at install;
   nothing in the sim covers that.
6. The sim never tests `--html` output rendering (the CLI writes an HTML
   report by default in some paths) — text receipt only.

## LLM usage

None. No model calls were made or needed at any point: generation is
seeded `random`, installation is pip, assertions are grep/Python, and
every bug above was reproduced by running the importers directly.

## Recommended actions (for parent)

1. Fix Bug 1 (otel retry key) and Bug 2 (langsmith failure marking) in
   gen_traces.py; delete dead `make_call()`.
2. Add manifest.json + numeric assertions per above; add `--no-cache-dir`
   (or commit pin) to the pip install; move venv cleanup after the verdict.
3. Optionally: test on Python 3.10/3.11 once; document the git
   prerequisite; align outreach "one command" wording with the real two
   steps.
4. Re-run the sim after fixes; all three formats should then show
   retries >= 1 and failures >= 1 with correct dollar attribution.
