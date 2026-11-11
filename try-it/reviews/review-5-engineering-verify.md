# Review 5 of 5 — Engineering Quality RE-VERIFICATION: `averth try` (branch `try-it`)

**Verdict: FAIL** (narrow: one new live defect, N1, in the D3 fix area; D5 partly fixed)

**Reviewer:** adversarial reviewer 5/5, angle engineering quality (re-verification pass).
**First-pass review:** `try-it/reviews/review-5-engineering.md` (FAIL, D1–D11).
**Adjudication:** `try-it/reviews/adjudication.md` (read in full first, as instructed).
**Scope re-read:** `averth/importers/miniswe.py`, `averth/try_report.py`,
`averth/cli.py` (`try` subcommand, `_detect_try_format`, `_report_and_html`),
`averth/report.py` (`try_extras` change), `try-it/reproduce-case-study.py`,
`tests/test_try_it.py`. No source file was edited. No merge, push, deploy,
or contact. All commands run with `~/workspace/averth/.venv/bin/python -m averth.cli`
unless noted. Scratch probes: `try-it/reviews/scratch-5-verify/probe_verify.py`
(+ `probe_verify.log`), `repro-full.log`, `repro-midfail.log`, `head-report.html`,
`new-report.html`, plus per-case HTML/JSON artifacts in the same directory.

**Test suite:** `.venv/bin/python -m pytest tests/ -q` →
**476 passed, 1 skipped** (first pass: 446 passed, 1 skipped).
`tests/test_try_it.py`: **52 passed** (first pass: 22).

**Published numbers re-verified live:** `averth try` on
`try-it/fixtures/django-15930.traj.json --model claude-sonnet-4-20250514
--recorded 0.3205` → rc 0, stdout `$0.98`, `3.07x`, `Retries:               0`
(padded columns; my probe's literal `"Retries: 0"` match was a probe bug, not
a product bug), HTML contains no `http`. The full reproduce script ran end to
end: **47/47 checks PASSED** (`scratch-5-verify/repro-full.log`).

---

## Per-defect re-verification

### D1 (HIGH, HTML injection via `source_note`) — FIXED

Probe (live, `probe_verify.py`): copied the fixture traj to
`<img src=x onerror=alert(1)>.traj.json` and metered it.

- CLI rc 0; HTML contains **no literal** `<img src=x onerror=alert(1)>`,
  no literal `<script>`; escaped form `&lt;img src=x onerror=alert(1)&gt;`
  present. Fix confirmed at the sink: `try_report.py` escapes
  `source_note` with `_html.escape` in `build_try_extras`.
- Test pins it: `test_try_hostile_filename_is_escaped` and
  `test_try_extras_escape_source_note` (both assert `"<img src=x" not in html`
  and `"&lt;img" in html`).

### D2 (HIGH, `--recorded nan`/`inf` accepted) — FIXED

Probe (live): `--recorded nan`, `inf`, `-1`, `0` → all rc 2,
`averth: error: --recorded must be a positive dollar figure`, no traceback,
no `$nan`/`$inf` in stdout, no report written. Library level:
`build_try_extras` and `try_summary_lines` with `nan`/`inf`/`0`/`-1`/`"x"`
all raise `ValueError` — `try_summary_lines(recorded=0)` raises
`ValueError`, **not** `ZeroDivisionError` (the adjacent from the first pass).
`_check_recorded` (`try_report.py`) now rejects non-`int`/`float`,
non-finite, and non-positive values; `cli.py` checks `math.isfinite`
before any work.

Note (not a defect): `--recorded -inf` in space form is rejected by argparse
itself (usage error, exit 2, no report) because `-inf` looks like an option
token; `--recorded=-inf` yields the clean `averth: error:` line. Same
outcome class, no report, no traceback.

### D3 (HIGH, malformed V0 ledgers crash with traceback) — FIXED, with one residual gap (see N1)

Probe (live, 14 ledger shapes + missing files, all through the CLI):
`judgments` as string / dict / `None` / int / list-of-string; `counts`
values as string / bool; `counts` as string; `unknown_rate` as string;
`runs_total` as string / bool; `coverage` as string; bad JSON; missing
ledger file; missing checks file. **Every case: rc 2, `averth: error:`,
no `Traceback`, no report written.** Library level: `load_v0_ledger`
raises `ValueError` (not `FileNotFoundError`/`JSONDecodeError`) for a
missing file and for bad JSON. The `build_try_extras` /
`try_summary_lines` calls in `_cmd_try` are now wrapped in the CLI error
contract (`cli.py`, `try/except → averth: error:, return 2`).

Residual: the shape validation accepts **bool and non-finite numbers**
for `unknown_rate` (and non-finite numbers for `counts`) — recorded as
new defect N1 below. Everything D3 originally listed is fixed; N1 is a
narrower hole in the same validation function.

### D4 (MEDIUM, malformed trajectories crash) — FIXED

Probe (live): non-string `text` parts (`123`, `True`) → rc 0, converted
cleanly, int part contributes nothing (event count identical to fixture:
71 vs 71). Non-dict messages (string / int / `None`) → rc 2, clean
`averth: error: … message 1 is not an object …`, no traceback. Non-dict
`info` (`"Submitted"`, `5`) → rc 0, tolerated, no end event invented.
Non-UTF-8 file → rc 2, clean `… is not readable text (binary or
non-UTF-8) …`, no `UnicodeDecodeError` on stderr. Files open with
`encoding="utf-8"` (`miniswe.py`), `_message_text` skips non-str parts,
message loop raises `ValueError` naming the index, `info` guarded with
`isinstance(info, dict)`.

### D5 (MEDIUM, format detection) — PARTLY FIXED

Fixed and verified live:

- Single-line JSONL detects and meters (rc 0).
- Empty file → rc 2, `… is empty`; `[]` and `{"data": []}` → rc 2,
  `… contains no traces (empty export); nothing to meter`, no report;
  whitespace-only JSONL → rc 2, empty; bare JSON object with neither key
  → rc 2, no `--format` suggestion in the message.
- Typeless first line: `_detect_try_format` returns `"jsonl"` for
  `{"note": "header"}` + model lines (verified live via direct call and
  by the test `test_detect_try_format_skips_typeless_first_line`).

**Not fixed end to end:** the same typeless-first-line file still fails
under `averth try` with rc 2:
`averth: error: failed to parse … (jsonl): line 1: unknown event type ''`.
Detection now passes, but the shared JSONL importer (`averth/importers/jsonl.py`)
is strict by documented design ("every line must be a JSON object with a
known 'type'") and rejects the header line. So the user-visible outcome
for a header-line JSONL is unchanged from the first pass. The adjudication
adopted only the detection fix ("the line scan looks past a typeless first
line"), so this is a scope decision for the parent, not a missed line of
the adopted fix: either the importer must skip non-event lines (shared
with `averth trace`, so a deliberate contract change), or the docs must
state header lines are unsupported. I mark D5 PARTLY and do not rest the
verdict on it.

### D6 (LOW-MEDIUM, `try_extras=None` byte-identity) — FIXED

Verified against a git worktree of HEAD (`8ec848b`): rendered HEAD's
`write_html` (no `try_extras` parameter) and the branch's `write_html
(try_extras=None)` on the same tracker built from
`try-it/fixtures/trace-events-django-15930.jsonl`. `diff` output is
**exactly one line** (line 76): the deliberate Priced-bucket relabel —
HEAD: `Priced (vendor prices on recorded tokens; legacy traces without a
provenance flag still land here)` → branch: `Priced (vendor list prices on
trace-supplied token counts, not verified as provider-recorded usage)`.
No stray blank line, no other difference. The conditional insertion
(`report.py:893`, `"try_extras_block": ("\n" + try_extras) if try_extras
else ""`) is the fix, and the docstring now says `None` "adds nothing:
the block is omitted, not rendered as a blank line" (`report.py:418-421`).
Test `test_write_html_without_try_extras_is_unchanged` pins `None` ==
`""` byte-for-byte within the new code; my worktree diff pins it against
HEAD.

### D7 (MEDIUM, reproduce script) — FIXED, except a docstring nit (see N2)

Probes (live):

- `--force` guards, all refused with rc 2 and a clean
  `reproduce: error:` line: `--work-dir /`, repo root, `$HOME`, cwd
  (`.` from a temp dir), and repo ancestor (`~/workspace`). Sentinel
  files placed in `$HOME` and in the cwd survived untouched.
- Work-dir-is-a-file: refused rc 2, `… is a file, not a directory`,
  with and without `--force`.
- `curl --fail`: present (`reproduce-case-study.py:124`,
  `curl -sL -f --retry 3 …`); trajectory JSON-parsed immediately after
  download (`:203`).
- Mid-run failure table: verified live with a stub `curl` that exits 22
  (simulated 404) on PATH — rc 1, `Published-number checks:` table
  header printed, then `reproduce: FAILED: command failed (exit 22):
  curl -sL -f …` (`scratch-5-verify/repro-midfail.log`). The table prints
  on failure as adjudicated.
- Docstring corrected: "about a minute … (47 to 74 seconds measured)",
  "writes a git-ignored `averth.egg-info/` directory into the source
  tree. No tracked file is modified", and the "What it checks / what it
  does NOT check" scoping.
- Full run end to end: **47/47 checks PASSED**
  (`scratch-5-verify/repro-full.log`, `reproduce: all 47 checks PASSED`).

### D8 (LOW, inference / fences / exit status) — FIXED

Probe (live): fence regex accepts single-line ```` ```bash echo hi``` ````,
trailing space ```` ```bash `` ````, and ```` ```BASH `` ```` (1 tool event
each; test `test_converter_bash_fence_variants` asserts 3 tool events).
`_infer_model("mygpt-4o-model.traj.json")` → `None`;
`_infer_model("notes-about-gpt-4o/traj.json")` → `None` (directory ignored);
basename inference and longest-match still work
(`gpt-4o-mini-2024-07-18` beats `gpt-4o`). Exit status: `"Submitted"` →
success True; `"submitted"` / `"SUBMITTED"` → False; documented as
"exact match, case-sensitive" in `miniswe.py:29` and `try-it/README.md:220`.
Unknown `--model gpt-9-unknown` → rc 2, `unknown model … not in the
Averth price table; run 'averth pricing' to list priced models`.

### D9 (LOW, double parse) — DEFERRED per adjudication, not re-checked as a fix

Adjudication: "noted, not fixed." The detector now reads the file once
(single `f.read()` in `_detect_try_format`). No performance failure was
measured in either pass. No verdict weight.

### D10 (test coverage) — FIXED

`tests/test_try_it.py` grew 22 → **52 tests**, all passing; full suite
476 passed, 1 skipped. The new tests assert the fixed behavior, not just
rc 0 (verified by reading, no source edited, as instructed):

- `test_try_extras_escape_source_note`, `test_try_hostile_filename_is_escaped`
  — assert `"&lt;img" in html` and `"<img src=x" not in html`; fail on the
  old unescaped code.
- `test_try_extras_reject_nonfinite_recorded` — `nan`/`inf` raise
  `ValueError`; fails without `_check_recorded`'s finiteness check.
- `test_v0_ledger_rejects_malformed_shapes` — judgments string /
  non-dict item, counts string value, `unknown_rate` string,
  `runs_total` string, missing ledger (`--ledger`), bad JSON, missing
  checks (`--checks`).
- `test_converter_skips_non_string_text_parts` (input_tokens == 1 for
  `"hello"` only), `test_converter_rejects_non_dict_message`
  (`match="message 0"`), `test_converter_tolerates_non_dict_info`,
  `test_converter_bash_fence_variants` (3 tool events),
  `test_infer_model_matches_basename_only`.
- `test_detect_try_format_single_line_jsonl`,
  `test_detect_try_format_skips_typeless_first_line`,
  `test_try_recorded_nan_inf_are_errors`,
  `test_write_html_without_try_extras_is_unchanged`.

Coverage gap that remains (noted, not verdict-driving): no test for the
reproduce script's `--force` guards or its mid-run failure table (D7 is
still entirely test-uncovered); and no test pins `unknown_rate` bool /
non-finite rejection (see N1).

### D11 (conventions) — FIXED / no violation found

CHANGELOG `## Unreleased` entry exists (`docs/CHANGELOG.md:7`, one-command
try-it). Zero new dependencies: new code imports stdlib only
(`try_report.py`: `datetime`, `hashlib`, `html`, `json`, `math`;
`miniswe.py`: `json`, `os`, `re`). The `report.py:392-396` docstring claim
D6 disproved is corrected (see D6).

---

## NEW defects found on re-verification

### N1 (MEDIUM — drives this FAIL) — `load_v0_ledger` accepts bool / non-finite `unknown_rate`, and non-finite `counts`; a successful report then prints nonsense

**File:** `averth/try_report.py:107-112` (`unknown_rate` check) and
`:99-105` (`counts` check).

The validation excludes bools for `counts` values and for `runs_total`
(`not isinstance(v, bool)` / `isinstance(..., bool)` checks are present
there) but **not** for `unknown_rate`:

```python
unknown_rate = coverage.get("unknown_rate")
if unknown_rate is not None and not isinstance(
        unknown_rate, (int, float)):
    raise ValueError(...)
```

In Python `isinstance(True, (int, float))` is True, and `float("nan")` /
`float("inf")` are floats, so all three pass. And `json.load` accepts
the non-standard literals `NaN` / `Infinity` by default, so they arrive
from a real file. Verified live through the CLI (rc 0, report written):

| Ledger `unknown_rate` | CLI rc | Report prints |
|---|---|---|
| `true` | 0 | `Unknown rate 100.0%.` (HTML and stdout) |
| `NaN` (raw JSON literal) | 0 | `Unknown rate nan%.` |
| `Infinity` (raw JSON literal) | 0 | `Unknown rate inf%.` |

Evidence: `scratch-5-verify/bool-unknown.json(.html)`,
`nan-unknown.json(.html)`, `inf-unknown.json(.html)`; e.g.
`grep -o "Unknown rate [^<.]*" nan-unknown.json.html` →
`Unknown rate nan%`. Library level confirmed too:
`try_summary_lines(pnl, v0={…, "unknown_rate": True})` →
`"unknown rate 100.0%"`; with `float("nan")` → `"unknown rate nan%"`.

This is the same failure mode D2 was HIGH for (a successful-looking
report printing `$nan`), now in the V0 section the D3 fix was supposed
to harden, and it is inconsistent inside the same function (counts and
runs_total reject bools; unknown_rate does not). Non-finite `counts`
values slip through the same way and fail one step later with a
Python-internals message instead of a validation error:
`counts: {"VERIFIED": NaN}` → rc 2, but
`averth: error: cannot convert float NaN to integer` (caught by the
`_cmd_try` wrapper, so the exit contract holds; the message does not
name the field).

**Fix:** in `load_v0_ledger`, require `unknown_rate` to be a real finite
non-bool number (`isinstance(v, (int, float)) and not isinstance(v, bool)
and math.isfinite(v)`) and require `counts` values to be finite as well
(`math` is already imported in `try_report.py`); add tests for
`unknown_rate: true`, `NaN`, `Infinity` and `counts: {"VERIFIED": NaN}`.
One-line-class fix; no other file needs to change.

### N2 (LOW, docstring) — reproduce script promises NOT RUN rows it never prints

**File:** `try-it/reproduce-case-study.py:22` (docstring) vs `:184-194`
(`print_table`).

Docstring: "If the run fails midway, the checks recorded so far print
first, with the rest marked NOT RUN." `print_table()` only iterates the
recorded `checks` dict; there is no NOT RUN marking anywhere in the file
(`grep NOT RUN` hits only the docstring). Verified live with the stub-curl
failure: the table header printed with zero rows and no NOT RUN lines
(`repro-midfail.log`). The adjudicated fix ("the checks table prints on
mid-run failure") is true; the NOT RUN half of the sentence is not.
**Fix:** either implement the NOT RUN listing (iterate the expected check
names) or narrow the docstring to "the checks recorded so far print".

---

## What was checked live (probe index)

- `probe_verify.py` (89 checks; the 5 apparent failures were 3 probe
  artifacts — `"Retries: 0"` vs padded `"Retries:               0"`,
  `--recorded -inf` space form hitting argparse — plus the 2 real
  findings N1/D5-end-to-end, all re-probed individually above).
- HEAD-worktree byte comparison for D6 (single-line diff, Priced relabel).
- All six `--force` guard targets for D7, sentinel files surviving;
  stub-curl mid-run failure; full reproduce run, 47/47 PASS.
- Full suite: 476 passed, 1 skipped; try-it file: 52 passed.

## Required fixes before this ships

1. **N1:** reject bool / non-finite `unknown_rate` and non-finite `counts`
   values in `load_v0_ledger`, with tests. (One-line-class fix.)
2. **N2:** correct the NOT RUN docstring sentence in
   `reproduce-case-study.py` (or implement the listing).
3. **D5 (parent ruling needed):** decide whether a typeless/header first
   line in a JSONL file should meter end to end. If yes, the shared
   `jsonl` importer contract must change deliberately (it is strict by
   design and shared with `averth trace`); if no, document that header
   lines are unsupported. Detection alone is verified fixed.
