# Review 5 of 5 — Engineering Quality: `averth try` (branch `try-it`)

**Verdict: FAIL**

**Reviewer:** adversarial reviewer 5/5, angle engineering quality.
**Scope read:** `averth/importers/miniswe.py`, `averth/try_report.py`,
`averth/cli.py` (`try` subcommand, `_detect_try_format`, `_report_and_html`),
`averth/report.py` (`try_extras` change), `try-it/reproduce-case-study.py`,
`tests/test_try_it.py`. No source file was edited. No merge, push, deploy,
or contact. Scratch probes:
`~/workspace/averth/try-it/reviews/scratch-5/probe.py`,
`probe2.py`, `probe3.py`, `probe4.py`, `probe5.py`, `bytecheck.py`
(+ `.log` files).

**Test suite:** `~/workspace/averth/.venv/bin/python -m pytest tests/ -q`
→ **446 passed, 1 skipped.** Green, but green here is weak evidence for
this feature (see §8): the try-it tests exercise almost only the happy
path, and several defects below are in code paths with zero test coverage.

**What held up under attack (credit where due):**
- Unknown `--model` does not crash the meter: it prices at the documented
  $1.00/$3.00 fallback and flags `unpriced_models` (verified live).
- V0 judgment/criterion/report-id fields *are* escaped (verified with an
  isolated hostile ledger, `source_note=None`: no literal `<script>` or
  `<img` in the output). `case_id` is escaped in `report.py` costliest rows.
- Zero-success traces are handled: `per_success` is all zeros, the
  recorded comparison prints "No completed runs…", summary lines are empty.
- Digest mismatch refuses before any report is written; `--checks` without
  `--ledger`, missing file, missing model, and bad `--recorded 0` all exit 2
  with a clean `averth: error:` line.
- Zero new dependencies: new code imports stdlib only (`json`, `re`,
  `hashlib`, `html`, `argparse`, `os`, `shutil`, `subprocess`, `sys`,
  `datetime`). CHANGELOG `## Unreleased` entry exists and describes the
  feature. No em-dash violation: the repo's no-em-dash rule is scoped to
  outreach/contact copy (POC drafts, case-study review); `try-it/README.md`
  uses em dashes in option descriptions, consistent with pre-existing CLI
  help text (`cli.py:79,357`). Nothing in the new user-facing copy breaks
  a repo-wide rule, because there is not one.

The FAIL rests on D1–D3 (each independently blocking) plus D4–D7.

---

## D1 (HIGH, security) — Unescaped `source_note` is an HTML injection via the trace filename

**Files:** `averth/try_report.py:189-195` (sink),
`averth/cli.py:282-300` (source).

`build_try_extras` interpolates `source_note` raw into the HTML:

```python
"<h2>How this report was made</h2><p>%s</p>" % (source_note, ...)
```

and `_cmd_try` builds `source_note` from the input file's basename with no
escaping (`"Trace: %s (mini-SWE-agent trajectory). …" % base`).
The docstring at `try_report.py:100-105` claims the return is "(already
escaped)". It is not: every other interpolated value in this function is
`_html.escape(...)`d, this one is not.

**Reproduction (verified live, `scratch-5/probe2.py`):**

```bash
# file named: <img src=x onerror=alert(1)>.traj.json
averth try '<img src=x onerror=alert(1)>.traj.json' --model claude-sonnet-4-20250514 --out evil.html
grep -c '<img src=x onerror=alert(1)>' evil.html   # -> 1, literal raw tag
```

The whole point of this feature is a *shareable* HTML report. Anyone who
receives a trace with a hostile filename (or any future caller passing an
unescaped note) gets a report that runs attacker markup when opened.
Note the existing test `test_try_traj_end_to_end` asserts `"http" not in
html` for self-containment — a hostile filename also defeats that spirit,
but no test checks escaping at all.

**Fix:** escape at the sink, not the call site:
`_html.escape(source_note)` in `build_try_extras` (or escape `base` in
`_cmd_try` *and* escape at the sink — defense in depth; the sink fix is
the one that matters). Add a test metering a traj whose basename contains
`<img src=x onerror=…>` and asserting no literal `<img` in the output.

## D2 (HIGH) — `--recorded nan` / `inf` are accepted and produce a "successful" report reading `$nan` / `$inf`

**Files:** `averth/cli.py:236`, `averth/try_report.py:110-111,204-209`.

The only guard is `recorded <= 0`. For NaN every comparison is False, so
`nan <= 0` is False and it sails through; `inf <= 0` is False too.
`argparse type=float` accepts both spellings.

**Reproduction (verified live, `scratch-5/probe2.py`):**

```bash
averth try django-15930.traj.json --model claude-sonnet-4-20250514 --recorded nan
# rc=0, stdout: "Recorded cost: $nan; metered estimate per completed run: $0.00 ESTIMATED (nanx)"
# HTML contains literal "nan"
averth try … --recorded inf
# rc=0, stdout: "Recorded cost: $inf; … (0.00x)"
```

A report that prints `$nan` with exit code 0 is worse than an error: it
looks like a completed run. Same flaw in `build_try_extras`'s own guard
(`try_report.py:111`), so the library API is equally broken.

**Fix:** reject non-finite values in both places:
`if recorded is None or not math.isfinite(recorded) or recorded <= 0:
raise ValueError(...)`, and the same in `_cmd_try` before any work.
Add tests for `--recorded nan`, `--recorded inf`, `--recorded -1`.

**Adjacent (same function):** `try_summary_lines` (`try_report.py:204-209`)
divides by `recorded` with no guard of its own. Called directly with
`recorded=0` it raises `ZeroDivisionError`, while `build_try_extras`
raises the intended `ValueError` for the same input (verified live).
Give `try_summary_lines` the same finite-positive guard.

## D3 (HIGH) — Malformed-but-accepted V0 ledgers crash `_cmd_try` with an uncaught traceback

**Files:** `averth/try_report.py:43-96` (validation gap),
`averth/cli.py:303-308` (unguarded call).

`load_v0_ledger` validates only that the top level is a dict with a
`judgments` key. It never validates the *shape* of what it keeps:
`judgments` may be a string, dict, int, or `None`; `coverage.counts`
values may be strings; `unknown_rate` may be a string. `build_try_extras`
then dies with `%d` / `*` `TypeError`s — and the `build_try_extras` /
`try_summary_lines` calls in `_cmd_try` (`cli.py:303-308`) sit **outside**
any `try/except`, unlike the `load_v0_ledger` call just above them.
Result: a raw traceback on stderr and exit code 1, breaking the CLI's
`averth: error:` / exit-2 contract that the rest of `try` honors.

**Reproduction (verified live, `scratch-5/probe2.py`, `probe3.py`):**

```python
# ledger {"judgments": [], "coverage": {"counts": {"VERIFIED": "two"}}}
averth try <traj> --model … --ledger led-badcounts.json
# Traceback (most recent call last): … cli.py:303, in _cmd_try …
#   try_report.py:144, in <genexpr>  TypeError: %d format: a real number
#   is required, not str
```

Also verified: `judgments: "oops"` → `AttributeError: 'str' object has no
attribute 'get'` (this one *is* caught, but surfaces as a raw Python
message, rc=2); `judgments: None` / `5` → `TypeError: 'NoneType' object
is not iterable`; `coverage.counts: "x"` with `unknown_rate: "high"` →
`TypeError: must be real number, not str`. A ledger whose `checks` file
is missing raises `FileNotFoundError`, and a ledger with bad JSON raises
`json.JSONDecodeError` — both contradict the docstring
(`try_report.py:52-53`, "Raises ValueError when … the checks file cannot
be read"), even though the CLI still maps them to exit 2.

**Fix:** (a) validate in `load_v0_ledger`: `judgments` must be a list of
dicts; `counts` must be a dict of numbers; `unknown_rate`, if present,
must be a number (or None); `runs_total`, if present, must be an int;
raise `ValueError` naming the field otherwise. Wrap the `open`/`json.load`
calls and the checks-file read so all failures raise `ValueError`.
(b) Belt and braces: wrap the `build_try_extras` / `try_summary_lines`
calls in `_cmd_try` in the same `try/except → averth: error:, return 2`
pattern used for the ledger load. Add tests for each malformed shape
through the CLI asserting rc=2 and no `Traceback` on stderr.

## D4 (MEDIUM) — `miniswe` crashes with raw `TypeError`/`AttributeError` on malformed-but-plausible trajectories

**Files:** `averth/importers/miniswe.py:47-64, 108-131`.

The docstring on `_message_text` promises: "Anything else contributes
nothing rather than crashing the conversion." False in three places:

1. **Non-string `text` part** (`miniswe.py:57-61`): `"".join(...)` over
   `part.get("text", "")` where the value is an `int`/`bool` raises
   `TypeError: sequence item 1: expected str instance, int found`
   (verified: user content `[{"type": "text", "text": 123}]`, and
   `text: True` likewise).
2. **Non-dict message in `messages`** (`miniswe.py:108+`): the loop calls
   `message.get(...)` unguarded. A list containing a string, int, or
   `None` raises `AttributeError: 'str' object has no attribute 'get'`
   (verified for all three).
3. **Non-dict `info`** (`miniswe.py:131`):
   `(traj.get("info") or {}).get("exit_status")` — a truthy non-dict
   `info` (e.g. `"Submitted"`) raises
   `AttributeError: 'str' object has no attribute 'get'` (verified).
   (`info: None` is fine; only truthy non-dicts crash.)

The CLI maps these to exit 2 via the generic parse `except`, but the
message is Python-internals text (`sequence item 1: expected str
instance, int found`), not a user-facing diagnosis naming the offending
field. Compare the clean `ValueError`s the same module raises for
missing `messages` / empty messages.

**Fix:** in `_message_text`, coerce with `str(...)` only for str values
and skip non-str (`text if isinstance(text, str) else ""`); in
`miniswe_events`, skip-or-reject non-dict messages with a `ValueError`
naming the index, and guard `info` with
`info = traj.get("info"); status = info.get("exit_status") if
isinstance(info, dict) else None`. Also open with `encoding="utf-8"`:
a non-UTF-8 file currently raises a raw `UnicodeDecodeError` (verified).
Add tests for each shape.

## D5 (MEDIUM) — `_detect_try_format` rejects valid JSONL and misroutes empty inputs

**File:** `averth/cli.py:182-226`.

1. **Single-line JSONL is rejected.** The detector runs `json.load` on
   the whole file first. A one-event JSONL file *is* valid JSON, parses
   as a dict without `messages`/`data`, and is rejected with "JSON object
   with neither 'messages' … nor 'data' …" (verified live, rc=2).
   The line-scan fallback is never reached. Any JSONL file whose first
   event is the only event breaks under `--format auto` while working
   under `--format jsonl`.
2. **Only the first non-blank line is inspected.** A JSONL file whose
   first event lacks `"type"` (e.g. a header/metadata event) is rejected
   even though later lines are valid model events (verified live) — and
   the error message does not say "first line has no `type`", so the
   operator cannot tell why.
3. **Empty shapes route to a "successful" empty report.** `[]` and
   `{"data": []}` detect as `langfuse`; `load_langfuse` returns zero
   events and the CLI exits 0 with a 0-attempt report (verified live).
   An empty export is not a successful meter run; it should be an
   error, or at minimum the detector should not claim it.

**Fix:** try the line-scan *before* (or as well as) whole-file
`json.load` when the file is not a dict-with-`messages`/`data` shape;
scan more than the first line for a `"type"` key (bounded, e.g. first
10 non-blank lines); reject empty inputs explicitly in `_cmd_try`
(zero events → `averth: error: no events …`, exit 2). Add direct tests
for `_detect_try_format` — there are currently **zero** (see §8).

## D6 (LOW-MEDIUM) — `try_extras=None` is NOT byte-identical to the old output

**Files:** `averth/report.py:748,851`, docstring at `389-396`.

The claim: "`None` keeps the report exactly as before." Verified false
by a byte comparison: HEAD's `write_html` vs the new one, same tracker,
same fixture events (`scratch-5/bytecheck.py`, `git worktree` of HEAD):

```
110a111
>
```

The template gained a `%(try_extras)s` line (`report.py:748`) that
renders as a stray blank line before `</main>` when extras are `""`.
One blank line is cosmetic, but the docstring's exactness claim is
what the task asked me to prove, and it is false — and no test pins it,
so it will drift silently.

**Fix:** either make the insertion conditional (build the template with
the extras block only when non-empty) or correct the docstring to
"identical except for one blank line". Prefer the conditional insertion;
add a regression test comparing `write_html(..., try_extras=None)` output
against the pre-change output (or at least asserting no stray blank line
before `</main>`).

## D7 (MEDIUM, reproduce script) — `--force` is an unguarded `shutil.rmtree`; downloads are unchecked; mid-run failure prints no table

**File:** `try-it/reproduce-case-study.py`.

1. **`--force` wipes whatever `--work-dir` names** (`:126-134`):
   `work = os.path.abspath(args.work_dir)` then, with no guard at all,
   `shutil.rmtree(work)`. `--work-dir . --force` from the repo root
   deletes the checkout; `--work-dir ~ --force` deletes the home
   directory; `--work-dir / --force` attempts the filesystem. There is
   no check that `work` is inside an expected parent, no confirmation,
   no basename allowlist. **Fix:** refuse when `work` is `/`, the cwd,
   the repo root, `$HOME`, or any ancestor of the repo; or require the
   directory to look like a previous run (contain a marker file the
   script itself wrote).
2. **`--force` on an existing *file* traceback-crashes** (verified live):
   `shutil.rmtree` on a file raises `NotADirectoryError`, uncaught
   (the `rmtree` is outside the `try:` block), rc=1 with a traceback.
   **Fix:** handle `os.path.isfile(work)` (refuse, or unlink with an
   explicit message) and wrap in the script's error reporting.
3. **`download()` (`:102-107`) has no `--fail` and no checksum.**
   `curl -sL --retry 3 -o dest url` with no `-f` saves a 404 HTML error
   page; the only check is non-empty size, which an error page passes.
   The failure then surfaces minutes later as a `JSONDecodeError` /
   `KeyError` deep in the run. **Fix:** add `--fail` (and ideally verify
   the trajectory parses as JSON immediately after download, before the
   multi-minute Django install).
4. **Mid-run failure prints no PASS/FAIL table**, contradicting the
   module docstring ("Prints one PASS/FAIL line per published number").
   Any exception in steps 1–8 (e.g. `money()`'s `re.search(...).group(1)`
   at `:273-292` raising `AttributeError` if meter output wording ever
   changes) jumps to the `except` at `:395+`, prints one
   `reproduce: FAILED: …` line, and returns 1 with zero per-number lines.
   **Fix:** on exception, print the checks table so far with the
   un-run checks marked NOT RUN, then the failure.
5. **"The repository checkout itself is never modified" (docstring) is
   false in the letter:** step 7 runs `pip install -q -e repo_root`
   (`:263-264`), and an editable install writes `averth.egg-info/` into
   the source tree. An `averth.egg-info/` directory is in fact present
   in the checkout now (git-ignored, so no tracked change — but the
   docstring's claim is still wrong, and a stale egg-info can confuse
   later installs). **Fix:** correct the docstring, or install with
   `--no-build-isolation` into a temp dir / use `pip install --target`
   instead of `-e` against the live checkout.

Also noted (lower): the baseline check `"THEN" in baseline.stdout`
(`:224-225`) and `"Ran 89 tests"` / `"skipped=1"` (`:240-243`) are
string matches against Django's output wording — pinned to one base
commit, so acceptable, but brittle if Django ever rewords; `record` key
access (`record["cost"]`, `record["api_calls"]`, `:166-168`) has no
schema guard, so a leaderboard-format change fails as a bare `KeyError`.

## D8 (LOW) — Model inference and exit-status corners

**File:** `averth/importers/miniswe.py:66-85, 125, 131-136`.

- `_infer_model` is pure substring matching with no word boundaries:
  `mygpt-4o-model.traj.json` infers `gpt-4o` (verified). Longest-match
  wins, so the two-priced-names case works (`gpt-4o` +
  `claude-sonnet-4-20250514` → the Claude model, verified both orders;
  `gpt-4o-mini-2024-07-18` beats its `gpt-4o` prefix, verified).
  But a directory or filename that merely *mentions* a model name
  (e.g. `notes-about-gpt-4o/traj.json`) silently meters at that model's
  price. **Fix:** prefer matching on the basename and require a
  non-alphanumeric boundary (or at least document that any substring
  anywhere in the path counts).
- An explicit `--model` that is not in the price table produces **no
  error at all**: the meter silently prices at the $1.00/$3.00 fallback
  (verified: `--model gpt-9-unknown` → `cost_total=1.2e-05`,
  `unpriced=['openai:gpt-9-unknown']`). That is the meter's standing
  fallback convention and the report does flag it, so this is a
  wart, not a crash — but a typo'd `--model` is the most likely user
  error here and deserves a stderr warning naming the fallback.
- `exit_status` comparison is case-sensitive: `"submitted"` /
  `"SUBMITTED"` → failure (verified). That matches the written spec
  ("`Submitted` means success; any other recorded status means False"),
  so it is not a bug — but the spec sentence should say the match is
  exact/case-sensitive, since leaderboard data is the only source and a
  future variant would silently flip outcomes.
- `_BASH_FENCE` (`miniswe.py:44`, `r"```bash\n(.*?)```"`) misses real
  bash blocks: single-line ```` ```bash echo hi``` ````, ```` ```bash `` ``
  with a trailing space, and ```` ```BASH `` `` (verified: 0 tool events
  for all three). Real mini-SWE-agent output uses ` ```bash\n`, so the
  published numbers are unaffected — but the docstring's "per ```bash
  code block" promise overclaims. **Fix:** `r"```bash[ \t]*\n?(.*?)```"`
  with `re.IGNORECASE`, or document the exact fence shape accepted.

## D9 (LOW) — `_detect_try_format` reads the file twice; huge trajectories pay double parse

**File:** `averth/cli.py:182-226`. Whole-file `json.load`, then (on
failure) a second open and line scan; then the importer parses the file
a third time. For a multi-hundred-MB trajectory this is 2–3× memory
churn for no benefit. 20k-message trajectories convert in 0.08s
(verified), so this is not a performance failure today — just note it
if the try-it is ever pointed at production-scale traces: detect from a
bounded prefix read instead of `json.load` on the whole file.

## D10 — What the tests do not cover (test quality)

The suite is green, but the try-it tests (`tests/test_try_it.py`, 22
tests) are overwhelmingly happy-path:

- **Zero tests for `_detect_try_format`** — the whole auto-detect
  surface (single-line JSONL, first-line-without-`type`, empty file,
  bare list, JSON object with neither key) is untested. D5 would have
  been caught by a 10-line parametrized test.
- **Zero tests for HTML escaping** — no test meters a hostile filename
  or hostile ledger field. D1 would have been caught by one test.
- **Zero tests for `recorded` validation beyond `0`** — `nan`/`inf`/
  negative-via-API are untested. D2 would have been caught.
- **Zero tests for malformed ledgers** — `judgments` as string/dict/
  `None`, non-numeric counts, non-numeric `unknown_rate`. D3 would have
  been caught.
- **Zero tests for malformed trajectories** — non-dict messages,
  non-dict `info`, non-string `text` parts, fence variants. D4/D8 would
  have been caught. (The existing converter tests cover only missing
  model, non-trajectory, and empty messages.)
- **Zero tests for `write_html` backward compatibility** — no test
  asserts `try_extras=None` output matches the pre-change output. D6
  would have been caught.
- **Zero tests for the reproduce script** — no test for `--force` on a
  file, no test for `download()` with a 404, no test for the failure
  table. D7 is entirely untested.
- **Tests that would pass if the code were broken:**
  - `test_try_auto_detects_traj_without_format_flag` asserts only
    rc==0 and the HTML file exists — it would pass if detection
    silently picked any format that still meters.
  - `test_try_jsonl_format` asserts stdout numbers and file existence,
    never the HTML content — the extras sections could be missing and
    it would pass.
  - `test_converter_model_inferred_from_path` uses a path with exactly
    one model name — it would pass if `_infer_model` took the *first*
    instead of the longest match, or matched anywhere without
    boundaries (D8).
  - `test_v0_ledger_without_checks_is_labelled_unverified` checks only
    `counts["VERIFIED"] == 2`, not the `digest_verified is None`
    labelling in the rendered HTML.
  - `test_try_extras_carry_the_published_comparison` asserts substrings
    (`"3.07x"`, `"$0.3205"`) but nothing about escaping, the
    recorded-guard, or zero-success rendering.

## D11 (LOW) — Conventions check

- CHANGELOG: updated (`docs/CHANGELOG.md`, `## Unreleased` → Added).
- Dependencies: none added (stdlib only, verified by import audit).
- Em dashes: no repo-wide ban found; the ban is scoped to outreach
  copy. New CLI/README copy is consistent with existing style.
- One correction to a docstring: `report.py:392-396` says `try_extras`
  "is pre-rendered HTML … inserted before `</main>`" — true — but
  also says "`None` keeps the report exactly as before", which D6
  disproves by one blank line.

---

## Not tested (stated, not signed off)

- The full `reproduce-case-study.py` end-to-end run (needs network,
  a Django checkout + install, several minutes): **not executed**.
  D7 findings are from code reading plus the two cheap live checks
  (`--force` on a file, `shutil.rmtree` guard inspection) and the
  observed `averth.egg-info/` in the checkout. The download-failure,
  mid-run-table, and egg-info claims are therefore code-level, not
  run-level, findings.
- Multi-hundred-MB / multi-million-message trajectories (D9 is an
  inference from the code path, not a measurement).
- Langfuse exports with real observations (only the empty-list shape
  was exercised live); the Langfuse importer itself is pre-existing
  code, not this branch's, and was not audited beyond the empty case.
- The `try-it/README.md` claims beyond the em-dash scan were not
  line-by-line verified against behavior.

## Required fixes before this ships (in priority order)

1. D1: escape `source_note` at the sink in `try_report.py:189-195`
   (+ regression test with a hostile filename).
2. D2: reject non-finite `--recorded` in `cli.py:236` and
   `try_report.py:111`; give `try_summary_lines` the same guard.
3. D3: validate ledger shapes in `load_v0_ledger` (raise `ValueError`)
   and wrap the `build_try_extras`/`try_summary_lines` calls in
   `_cmd_try` with the CLI error contract.
4. D4: harden `_message_text` / message loop / `info` handling in
   `miniswe.py` per the docstring's own promise.
5. D5: fix single-line-JSONL detection, scan past a typeless first
   line, reject empty inputs.
6. D6: remove the stray blank line (or correct the docstring) + pin
   with a regression test.
7. D7: guard `--force` against `/`, cwd, repo root, `$HOME`; handle
   work-dir-is-a-file; add `curl --fail` + early JSON validation;
   print the checks table on mid-run failure; correct the
   "never modified" docstring.
8. D8/D9: fence regex, inference boundaries, typo'd-model warning,
   case-sensitivity note.
9. §8 test gaps: direct `_detect_try_format` tests, escaping tests,
   malformed-ledger/trajectory tests, `nan`/`inf` tests, byte-identity
   regression test.
