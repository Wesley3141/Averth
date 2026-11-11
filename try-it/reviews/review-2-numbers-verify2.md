# Review 2 (verify 2) — Correctness of the numbers, second re-verification

**Verdict: FAIL** — narrowly, and certification-only again. N1 is fully
fixed and sensitivity-proven in both stdout and HTML. N2 is fixed: the
CHANGELOG now carries the adopted wording. D6(b) is half fixed: the
converter count on the trajectory is real and sensitive (35, and 34 on
a minus-one-assistant trajectory, which would FAIL). But the
fixture-side half is not: re-running my deletion proof on a
fixture-JSONL copy, dropping the *smallest* model event (1,460 in /
58 out tokens, ≈ $0.0053) still leaves the meter at Model/API $0.91 /
Fully loaded $0.98, and no script check counts model events in the
fixture JSONL — so that drop is still invisible to the script. The
comment at `try-it/reproduce-case-study.py:415-417` claims "the
converter's events must meter identically to the trajectory run", but
the check verifies only rounded-total equality, which is weaker than
identity. One line (count `"type": "model"` lines in the fixture and
assert 35) closes it. Everything else I checked passes, including the
full 50/50 reproduce run.

Scope: numbers only, narrowly the three defects from my first
re-verification. I edited no source file. Scratch evidence is in
`try-it/reviews/scratch-2-verify2/` (`sensitivity2.py`,
`sensitivity2.log`, `reproduce.log`, `repro-work/`, fresh live
`traj-stdout.txt` / `traj-try.html`, `jsonl-stdout.txt` /
`jsonl-try.html`, `traj-minus-one-assistant.json`, and the two mutated
fixture copies `jsonl-drop-first-model.jsonl` /
`jsonl-drop-last-model.jsonl` with their meter outputs).

## What I checked live

1. **Reproduce script end to end** (this pass, fresh work dir):
   `python3 try-it/reproduce-case-study.py --work-dir
   try-it/reviews/scratch-2-verify2/repro-work --force` — exit 0,
   **all 50 checks PASSED** (was 47; the new checks are "JSONL meter
   fully loaded" and "combined report yield ratio", plus the renamed /
   re-sourced checks below). Log: `reproduce.log` (50 `PASS` lines,
   counted). This includes "trajectory assistant messages (35)",
   "meter model events (35)", "JSONL meter fully loaded (0.98)",
   "yield rate (100.0)", and "combined report yield ratio (100.0)".
2. **Fresh live `averth try` runs** (`.venv/bin/python -m averth.cli`,
   exit 0 each): trajectory and fixture JSONL, using the previously
   downloaded trajectory and `try-it/fixtures/trace-events-django-15930.jsonl`.
   Confirmed in fresh stdout AND HTML for both input paths: Priced
   $0.91, Estimated $0.07, Billed $0.00, Fully loaded $0.98, ratio
   3.07x, Retries 0, Yield ratio 100%, and **zero occurrences of
   "recorded tokens"** in all four fresh outputs. The HTML yield card
   reads `<div class="k">Yield ratio</div><div class="v">100%</div>`,
   matching the script's combined-report regex exactly. (One of my
   own runs failed first with exit 2 on a wrong model name,
   `claude-sonnet-4-5-20250929`; the correct model is
   `claude-sonnet-4-20250514` per `reproduce-case-study.py:68`, and
   the unknown-model rejection worked as designed.)
3. **Sensitivity proofs** (`sensitivity2.py`, exact regexes/snippets
   copied from the reproduce script, run against copies of live
   output): see N1 and D6(b) below.
4. **Test suite:** `pytest tests/test_try_it.py -q` → **53 passed**
   (52 in the first re-verification).
5. **Independent read of the reproduce script's own fresh outputs:**
   `repro-work/report.html` has the new Priced label, the yield card
   at 100%, and zero "recorded tokens"; `repro-work/jsonl-report.html`
   shows Fully loaded $0.98 and zero "recorded tokens".

## Item 1 — D6(b), meter model events: PARTLY FIXED (converter half fixed, fixture half not)

What is in place (`try-it/reproduce-case-study.py`):

- Step 1 check renamed to what it measures: `:206-209`
  `check_int("trajectory assistant messages", …, 35)` — passed in
  the live 50/50 run; I independently counted 35 assistant messages
  out of 72 trajectory messages.
- Converter count, step 7 (`:398-413`): runs
  `miniswe.miniswe_events(traj_path, model=MODEL)` via the Averth
  venv and `check_int("meter model events", <count of
  e['type'] == 'model'>, 35)`. Passed at 35 in the live run.
- Second meter run on the fixture JSONL (`:415-426`):
  `check("JSONL meter fully loaded", <Fully loaded from the JSONL
  run>, 0.98)`. Passed at $0.98 in the live run, and my fresh live
  JSONL run independently agrees at $0.98.

Sensitivity proof — converter side (FIXED):

- Converter count on the downloaded trajectory: **35**.
- Same count on a trajectory copy with one assistant message removed
  (`traj-minus-one-assistant.json`): **34** → the check would FAIL.
  The count moves with the event count; a converter drop of any size
  is caught, including a small one. This is the half D6(b) named
  ("the meter's own model-event count is 35"), and it is now real.

Deletion proof — fixture side (NOT FIXED):

- Fixture JSONL: 71 lines, 35 `"type": "model"` events, model token
  sums 279,017 in / 5,077 out (verified independently).
- Dropping the **last** model event (14,465 in / 123 out) from a
  fixture copy: meter moves to Model/API **$0.87** / Fully loaded
  **$0.94** → the "JSONL meter fully loaded" check would FAIL.
  Caught.
- Dropping the **first** model event (1,460 in / 58 out, ≈ $0.0053)
  from a fixture copy: meter stays at Model/API **$0.91** / Fully
  loaded **$0.98** → the "JSONL meter fully loaded" check would
  still PASS, and **no other script check counts model events in
  the fixture JSONL** (the only fixture event-count in the script
  is the converter count, which reads the trajectory, not the
  fixture). A dropped small event in the fixture is still
  undetectable by the script — the exact hole from my first
  re-verification, now narrowed to the fixture side.
- The step-7 comment (`:415-417`) says "the converter's events must
  meter identically to the trajectory run", but the check asserts
  only rounded-total equality ($0.98 == $0.98), not identity. The
  comment overclaims what the check certifies.
- **Exact fix (one line, my first review's option (a), still
  unimplemented):** in step 7, count model events in the fixture
  JSONL itself and assert 35, e.g.
  `check_int("fixture JSONL model events", sum(1 for ln in
  open(os.path.join(fixtures, "trace-events-django-15930.jsonl"))
  if json.loads(ln).get("type") == "model"), 35)` — or compare the
  converter's event list against the fixture events directly. Either
  makes the first-event fixture drop FAIL (34 != 35).

## Item 2 — N1, yield rate: FIXED

- `try-it/reproduce-case-study.py:389-393`: the "yield rate" check
  now parses the yield line itself —
  `re.search(r"Yield ratio: ([0-9.]+)% of tokens on the terminal
  path", out)` — and `:524-528` adds a "combined report yield
  ratio" check parsing the HTML yield card
  (`<div class="k">Yield ratio</div><div class="v">([0-9.]+)%</div>`).
  Both passed at 100.0 in the live 50/50 run.
- **Proof by mutation** (`sensitivity2.py`, copy of fresh live
  stdout, only the yield line changed 100% → 42%): the new stdout
  regex returns **42** → the check FAILs. The same mutation applied
  to a copy of the fresh HTML yield card returns **42** → the
  combined-report check FAILs. The old regex
  (`Autonomous completions: … (100.0%)`) still returns 100.0 on the
  mutated stdout, confirming the flaw that was fixed. The check now
  reads the yield ratio, not the success rate, in both render paths.

## Item 3 — N2, CHANGELOG token-provenance bullet: FIXED

- `docs/CHANGELOG.md:205-210`, under `## Unreleased`, now reads:
  `Reports label the Priced bucket "vendor list prices on
  trace-supplied token counts, not verified as provider-recorded
  usage"), name fallback-price, …` — the adopted wording, confirmed
  by reading. The pre-fix sentence ("vendor prices on recorded
  tokens") is gone from the bullet.
- Repo grep for "recorded tokens" over `averth/`, `docs/`,
  `try-it/`, `tests/`, and `README.md`: the only current
  source/docs hit is the code comment at `averth/report.py:204`
  ("The parenthetical no longer says \"recorded tokens\"…"), which
  is explicitly a note about the old wording and is acceptable per
  the task. All other hits are (a) first-pass review files quoting
  the old label as evidence, (b) historical scratch artifacts, or
  (c) stale generated HTML from pre-relabel code — see the note
  below. No current source file, doc, or fresh output asserts the
  Priced bucket is priced on recorded tokens.

## New defects

### N3 (trivial, docs typo) — stray close-paren in the fixed CHANGELOG bullet

- **File/lines:** `docs/CHANGELOG.md:207-208`: `… not verified as
  provider-recorded usage"), name fallback-price, …` — the `)`
  after the closing quote has no matching `(`. The wording is
  correct; the punctuation is not.
- **Exact fix:** delete that `)` so the clause reads `… usage",
  name fallback-price, …`. Not a FAIL driver.

### Note (not a defect) — stale generated artifacts still carry the old label

- Pre-relabel generated HTML still in the tree shows the old label:
  `case-study-1/trace-events-django-15930.html` (2026-11-11 04:53,
  before `averth/report.py` was relabelled at 20:15),
  `trace-a-sequential-retry.html` (2026-11-03),
  `try-it/repro-work/report.html` (19:51) and
  `try-it/.test-out/report.html` (19:14), plus first-pass scratch
  outputs. These are outputs of old code, not claims in any source
  file — the current generator is proven clean by four fresh outputs
  with zero "recorded tokens" plus the reproduce script's fresh
  reports. Follow-up: regenerate or delete the stale artifacts so
  nobody opens one and reads the superseded label as current. Not a
  FAIL driver: the fix lives in the generator, and re-running the
  reproduce script already produces clean reports.

## What I did not verify

- The $3/$15 list prices against Anthropic's live pricing page (no
  live-browser access in this role; values taken as text literals
  from `averth/pricing.py`, as in the first pass).
- The gold-patch / baseline Django claims beyond the reproduce
  script's own live runs (baseline failure, target pass, module 89
  tests / skipped=1, gold pass — all executed and passing in the
  50/50 run I watched).

## Bottom line

N1 is fixed in both render paths and mutation-proven. N2 is fixed;
the CHANGELOG carries the adopted wording (modulo a stray paren, N3).
D6(b) is fixed on the converter side — the meter's own model-event
count is now 35 by direct count, sensitive to a drop — but the
fixture side still relies on a cent-rounded total, and I proved by
deletion that dropping the smallest model event from the fixture
leaves every script check passing. Add the one-line fixture
event-count check, re-run, and this passes.
