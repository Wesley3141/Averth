# Review 5 of 5 — Engineering Quality SECOND RE-VERIFICATION: `averth try` (branch `try-it`)

**Verdict: PASS**

**Reviewer:** adversarial reviewer 5/5, angle engineering quality (second re-verification).
**First re-verification:** `try-it/reviews/review-5-engineering-verify.md` (FAIL — N1, N2, D5 PARTLY).
**Adjudication:** `try-it/reviews/adjudication.md` (read in full first, as instructed).
**Scope re-read:** `averth/try_report.py` (`load_v0_ledger`), `averth/importers/jsonl.py`
(`_validate`, read-only check), `try-it/reproduce-case-study.py` (docstring),
`try-it/README.md` (JSONL section), `tests/test_try_it.py`
(`test_v0_ledger_rejects_malformed_shapes`). No source file was edited. No merge,
push, deploy, or contact. All commands run with
`~/workspace/averth/.venv/bin/python -m averth.cli` unless noted. Scratch probes:
`try-it/reviews/scratch-5-verify2/probe_verify2.py` (+ `probe_verify2.log`),
`repro-full.log`, plus per-case ledger artifacts under `v5v2-*/`.

**Commit verified:** `0750720` ("One-command try-it (averth try) and case-study
reproduction script"), branch `try-it`, clean tree apart from untracked review
scratch (pre-existing untracked files untouched).

**Test suite:** `.venv/bin/python -m pytest tests/ -q` →
**477 passed, 1 skipped** (first re-verification: 476 passed, 1 skipped).
`tests/test_try_it.py`: **53 passed** (was 52).

**Reproduce script:** `python3 try-it/reproduce-case-study.py --work-dir
try-it/reviews/scratch-5-verify2/repro-work --force` → **51/51 checks PASSED**
(`scratch-5-verify2/repro-full.log`, `reproduce: all 51 checks PASSED`), including
the new fixture model-event count check ("fixture JSONL model events (actual 35,
published 35)").

---

## Per-item verification

### N1 (drove the FAIL: bool / non-finite `unknown_rate`, non-finite `counts`) — FIXED

Code (read): `averth/try_report.py:102-120`.

- `counts` values (`:102-111`): `isinstance(v, (int, float)) and not
  isinstance(v, bool) and math.isfinite(v)`, error names `coverage.counts`.
- `unknown_rate` (`:112-120`): same triple condition (`(int, float)`,
  non-bool, `math.isfinite`), error names `coverage.unknown_rate`.
- Adjacent fields, same shape (`:121-133`): `coverage.unknown` and
  `coverage.superseded_runs_retained` must be non-bool integers
  (`isinstance(..., int) and not isinstance(..., bool)`); `runs_total`
  likewise.

Live CLI probes (12 ledger shapes, all through `averth try` on
`try-it/fixtures/django-15930.traj.json --model claude-sonnet-4-20250514
--ledger <probe> --out <fresh path>`; `probe_verify2.py`, 18/18 checks PASS):

| Ledger shape | rc | stderr | report written |
|---|---|---|---|
| `unknown_rate: true` | 2 | `averth: error: … ('coverage.unknown_rate' must be a number)` | no |
| `unknown_rate: NaN` (raw literal) | 2 | same, names `unknown_rate` | no |
| `unknown_rate: Infinity` (raw literal) | 2 | same, names `unknown_rate` | no |
| `unknown_rate: -Infinity` (raw literal) | 2 | same, names `unknown_rate` | no |
| `counts: {"VERIFIED": NaN}` | 2 | `… ('coverage.counts' must map verdict names to numbers)` | no |
| `counts: {"VERIFIED": Infinity}` | 2 | same, names `counts` | no |
| `counts: {"VERIFIED": true}` | 2 | same, names `counts` | no |
| `unknown: true` | 2 | `… ('coverage.unknown' must be an integer)` | no |
| `unknown: 1.5` | 2 | same, names `unknown` | no |
| `superseded_runs_retained: true` | 2 | `… ('coverage.superseded_runs_retained' must be an integer)` | no |
| `superseded_runs_retained: 1.5` | 2 | same, names `superseded_runs_retained` | no |
| `runs_total: true` | 2 | `… ('coverage.runs_total' must be an integer)` | no |

Every case: no `Traceback` on stderr. Control: a valid ledger
(`unknown_rate: 0.5`, `counts: {"VERIFIED": 2}`) → rc 0, report written,
report prints `Unknown rate 50.0%` — the fix did not break the valid path,
and no `nan%`/`inf%`/`100.0%`-from-bool output is reachable through any
probed shape.

Tests (read, `tests/test_try_it.py:159-199`,
`test_v0_ledger_rejects_malformed_shapes`): the same function now asserts
`unknown_rate: True`, `float("nan")`, `float("inf")` and
`counts: {"VERIFIED": float("nan")}` / `{"VERIFIED": True}` all raise
`ValueError` matching the field name. These assertions fail on the old
code, by reasoning (no revert performed, as instructed): the test helper
writes with `json.dumps`, which emits the raw literals `true` / `NaN` /
`Infinity`, and `json.load` reads them back as `True` / `nan` / `inf`
(Python's `json` accepts the non-standard literals by default). The old
validation was `isinstance(v, (int, float))` only for `unknown_rate`
(`isinstance(True, (int, float))` is `True`; `nan`/`inf` are floats), and
`isinstance` + non-bool only for `counts` — so every one of those
`pytest.raises` blocks would fail to raise. The tests pin the fix, not
just rc 0.

### N2 (reproduce docstring promises NOT RUN rows) — FIXED

- `grep "NOT RUN" try-it/reproduce-case-study.py` → zero hits anywhere
  in the file (docstring, code, comments).
- Docstring (`reproduce-case-study.py:21-23`) now reads: "If the run fails
  midway, the checks recorded so far print first." — exactly the narrowed
  wording the first re-verification proposed (the docstring-only branch of
  the either/or; no NOT RUN listing was implemented, and none is claimed).

### D5 (was PARTLY: header/comment first line in JSONL) — FIXED (docs branch, as adjudicated)

- README (`try-it/README.md:178-180`, JSONL section): "Every line must be
  an event object with a `type` key; a file whose first line is a header or
  comment with no `type` is not supported." The sentence is present and
  states the rule in plain terms.
- Live end-to-end check (probe): a JSONL file whose first line is
  `{"note": "header, no type"}` followed by real model events → rc 2,
  `averth: error: failed to parse … (jsonl): line 1: unknown event type
  None (expected one of end, escalation, model, …)`, no `Traceback`, no
  report written. The shared importer contract is deliberately unchanged
  (see below); the docs branch of the either/or is the adopted resolution,
  and the pair — README sentence plus an importer error that names line 1,
  the offending (missing) type, and the expected types — tells a stranger
  with a header-line JSONL exactly why `averth try` refuses it.
- Importer unchanged, confirmed: `averth/importers/jsonl.py` is not in
  commit `0750720`'s stat, and `_validate` (`jsonl.py:115-122`) predates
  the branch.

Correction to my own first re-verification: the live error renders
`unknown event type None`, not `unknown event type ''` as I quoted there.
`_validate` does `etype = ev.get("type")` (→ `None` when absent) and
formats it with `%r`. Same code path then and now; the `''` in my earlier
file was my transcription error, not a behavior change. `None` is slightly
less self-explanatory than `''` would be, but the message still names the
line, the missing type, and the full expected-type list, so it is not a
defect.

---

## What was checked live (probe index)

- `probe_verify2.py`: 18 checks, **0 FAIL** on the final run
  (`probe_verify2.log`). Two checks initially failed and were re-run after
  correcting probe bugs, not product behavior: the D5 expectation copied
  my first review's `''` wording (actual: `None`, see correction above),
  and the N2 check used a single-line substring against a docstring
  sentence that wraps across two lines ("print\n   first"). Both
  corrected expectations pass; the underlying product behavior was
  verified in both runs.
- Full suite: 477 passed, 1 skipped. `tests/test_try_it.py`: 53 passed.
- Reproduce script end to end: 51/51 PASS (84 s wall clock).

## New defects found on this pass

None.

## Non-blocking observations (not verdict-driving)

1. **Test-coverage gap, adjacent fields only:** `test_v0_ledger_rejects_malformed_shapes`
   pins the string case (`"two"`) for `coverage.unknown` and
   `coverage.superseded_runs_retained` (`test_try_it.py:190-197`) but has
   no bool / non-integer case for either field. The behavior itself is
   verified live above (both `true` and `1.5` rejected, rc 2, field named),
   so this is coverage only. If the suite is touched again, two lines
   (`"unknown": True`, `"superseded_runs_retained": 1.5`) would close it.
   It does not block this verdict: the task's N1 test requirement covers
   `unknown_rate`/`counts`, which are tested, and the adjacent-field
   requirement was a code + live check, which passed.

## Required fixes before this ships

None. N1, N2, and D5 (docs branch) are all verified fixed live, with tests
pinning N1; the regression sweep passes (477 passed, 1 skipped; reproduce
51/51).
