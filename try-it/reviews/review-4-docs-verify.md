# Review 4 — Docs clarity, RE-VERIFICATION

**Verdict: FAIL**

Re-verified every first-pass defect (D1–D16) against the fixed docs by
reading `try-it/README.md` end to end as a stranger and by running its
commands literally. Fourteen of sixteen are fixed. Two are not, and
one of those is the blocking one: the install sequence still cannot
be followed literally by a stranger, because the branch is unpublished
and the feature itself is uncommitted, so a fresh clone has no `try`
command at all. The docs now *disclose* that failure honestly (new
note, lines 21–24), which is why this is PARTLY rather than the
original silent trap — but disclosure is not a working path. The
second open item is smaller: the conversion section still misstates
the bash-fence newline rule (proved live), and "byte for byte"
survives in the CHANGELOG and the importer docstring.

## Procedural note: the files changed during this verification

`try-it/README.md` and `averth/cli.py` were modified at 20:16 UTC
while this verification was running (mtimes 20:16:12–13; my first
read of the README, at task start, did **not** contain the lines
21–24 note, the "git (to obtain the checkout…)" prerequisites
wording, or the "Run this from the repository root." sentence in the
reproduce section — all three are present now). This verdict is
against the file as re-read in full after that edit. The `--help`
output was re-captured after the edit and is identical to the
earlier capture, so help-based claims below stand.

## What I checked live (commands and outputs)

All runs used `~/workspace/averth/.venv/bin/python -m averth.cli`
unless noted. Scratch evidence:
`try-it/reviews/scratch-4-verify/` (`case-study-run.log`,
`ledger-run.log`, `ledger-report.html`, `reproduce-run.log`).

1. **Fresh-clone install, literally as written** (`/tmp/try-verify-clone`):
   `git clone https://github.com/Wesley3141/Averth.git` succeeded;
   `git checkout try-it` failed:
   `error: pathspec 'try-it' did not match any file(s) known to git`,
   exit 1. Confirmed by `git ls-remote --heads origin`: no `try-it`
   ref exists (only `master`, `case-study-1`,
   `criterion-c-checks-digest`, `release/v0.3.0`, `v0-evidence-verifier`,
   `v0.2-product`, `validation-fixes*`).
2. **Local clone** (`git clone ~/workspace/averth`, `/tmp/try-clean`):
   `git checkout try-it` succeeded, but the clone has no `try-it/`
   directory, no `averth/importers/miniswe.py`, no
   `averth/try_report.py`, and `averth try` fails:
   `averth: error: argument cmd: invalid choice: 'try' (choose from
   'trace', 'simulate', 'pricing', 'advise')`. The whole feature is
   uncommitted working-tree state (`git status`: `M README.md`,
   `M averth/cli.py`, `M averth/report.py`, `M docs/CHANGELOG.md`,
   `?? averth/importers/miniswe.py`, `?? averth/try_report.py`,
   `?? try-it/`), so no clone — remote or local — reproduces it.
3. **Case-study run from a clean directory** (`/tmp/try-verify-run`,
   repo venv): `curl` downloaded 69,126 bytes; `try
   django-15930.traj.json --model claude-sonnet-4-20250514 --recorded
   0.3205` exited 0, 48 lines of stdout, `django-15930-try.html`
   written. `Retries: 0` (line 10), `  Fully loaded:         $0.98`
   (line 17, two-space indent), `Recorded cost (operator-supplied):
   $0.3205; metered estimate per completed run: $0.98 ESTIMATED
   (3.07x)` (line 48). Heading is "Cost per completed run (not per
   accepted outcome …)". Priced bucket reads "vendor list prices on
   trace-supplied token counts, not verified as provider-recorded
   usage". All published numbers reproduce.
4. **Console-script form**: `.venv/bin/averth try --help` works and
   the plain `averth try …` run produced the same recorded-cost line
   plus "Trajectory's own recorded cost $0.3205 agrees with the
   operator-supplied figure."
5. **`--ledger`/`--checks` example, literally from the repo root**:
   after `curl` into the repo root, the exact README command exited
   0; stdout V0 line: "VERIFIED 2, FAILED 0, NOT OBSERVED 0,
   EXTERNAL-UNVERIFIABLE 2, NOT APPLICABLE 0; unknown rate 50.0%;
   checks digest verified against the checks file". (Generated
   `django-15930.traj.json` / `django-15930-try.html` in the repo
   root were removed afterwards; report copy kept as
   `ledger-report.html`.)
6. **`--ledger` alone**: summary included, "checks digest NOT
   verified (no --checks given …)". **`--checks` alone**: exit 2,
   "`--checks` needs `--ledger`". **Tampered checks file**: exit 2,
   digest-mismatch refusal, and no `mismatch.html` was written.
7. **Model inference**: a trajectory in a directory literally named
   `claude-sonnet-4-20250514` with a plain filename was **refused**
   (exit 2, no model named) — directory does not count. A file named
   `my-claude-sonnet-4-20250514-run.traj.json` inferred the model and
   ran to `$0.98`. `--recorded 0` refused, exit 2 ("must be a
   positive dollar figure"). No-model error is the documented
   exit-2 ask for `--model`.
8. **JSONL**: `try` on `try-it/fixtures/trace-events-django-15930.jsonl`
   exited 0, report header "Averth: jsonl-import"; default `--out`
   produced `trace-events-django-15930-try.html` in cwd. The
   README's two example JSONL lines are byte-identical to fixture
   lines 1–2 (verified by `head`).
9. **Detection failure**: a garbage file exited 2 naming all three
   shapes ("not a mini-SWE-agent trajectory …, a Langfuse export …,
   or a JSONL events file …").
10. **Fence rule, live probe** (`miniswe.miniswe_events` on synthetic
    trajectories): a ```` ```bash ```` fence with **no newline** after
    `bash` still yields 1 tool event; uppercase `BASH` with a
    trailing space also yields 1. (See D13.)
11. **Reproduce script end to end**: `python3
    try-it/reproduce-case-study.py --work-dir
    try-it/reviews/scratch-4-verify/repro-work` from the repo root
    exited 0 in **86 s** wall time: "reproduce: all 47 checks
    PASSED" (full table in `reproduce-run.log`). A second run
    without `--force` refused, exit 2 ("already exists; pass
    --force to wipe it and redo the run"). The 290 MB `repro-work`
    directory was deleted after the run; the log is retained.

## Defect-by-defect verdicts

- **D1 — PARTLY (blocking in substance).** The clone/checkout/cd
  sequence is now present (`try-it/README.md` lines 14–18) and the
  "run every command from the repository root" instruction is
  explicit (lines 10–11). But the sequence does not work literally
  for a stranger, proved twice live: (a) the branch is not on
  origin, so `git checkout try-it` fails on a fresh GitHub clone;
  (b) even a local clone loses the feature entirely because it is
  uncommitted, so `averth try` is an invalid choice. What changed
  for the better: the new note (lines 21–24) discloses this
  honestly — "not published yet… `git checkout try-it` fails on a
  fresh clone; run the commands from a checkout that already has
  the branch instead" — so the stranger is no longer silently
  misled. What is still missing: a stranger has no way to obtain
  "a checkout that already has the branch" from these
  instructions. Fully fixed only when the branch is committed and
  pushed (or the note names a concrete obtainable snapshot).
  Related: the "invalid choice" hint (lines 28–30, "you are not on
  the `try-it` branch") misdiagnoses case (b), where the reader
  *is* on `try-it` and the command still does not exist.
- **D2 — FIXED, conditional on D1.** From a checkout that has the
  branch, every command works literally as written: the venv
  sequence, the curl, the `try` command, and the plain `averth
  try …` form (all run live above). The failure a stranger hits is
  D1's obtainability, not D2's commands.
- **D3 — FIXED.** Root `README.md` lines 47–53: "On the unmerged
  `try-it` branch only: `git checkout try-it`, then `averth try
  <trace>` … (On `master` the `try` subcommand does not exist
  yet.)" The pointer is scoped and separated from the master
  install. (Same obtainability caveat as D1: the root README's
  `git checkout try-it` also fails on a fresh clone until push.)
- **D4 — FIXED.** "Look for these lines … in this order"
  (lines 102–107) matches real output exactly: order, two-space
  indent on `Fully loaded:`, and the operator-supplied recorded
  line, all verified against the 48-line live stdout ("about 50
  lines" is a fair approximation).
- **D5 — FIXED.** README lines 87–91 and `try --help` now agree:
  "Default: `<stem>-try.html` in the current directory, where
  `<stem>` is the trace filename without `.traj.json` (or `.json`)",
  `django-15930.traj.json` → `django-15930-try.html`. Verified
  live for both a `.traj.json` and a plain `.json` input.
- **D6 — FIXED.** `--format auto` is named as the default
  (line 47) and the three detection rules are stated (lines
  47–52); detection failure exits 2 naming the shapes, verified
  live. (Undocumented nuances remain — single-line JSONL counts,
  the scan looks at the first 10 non-blank lines — but the
  first-pass fix asked for the rules, and they are there.)
- **D7 — FIXED, with new defect N1 noted below.** README lines
  57–69 now document the new behaviour exactly as adjudicated:
  basename-only with non-alphanumeric boundaries, longest match
  wins, directory does not count, explicit `--model` overrides
  inference, unpriced models refused with `averth pricing` as the
  remedy, ignored for JSONL/Langfuse. Both boundary behaviours
  were verified live. The failure text is paraphrased rather than
  quoted, which is acceptable — but see N1.
- **D8 — FIXED.** Positivity (`--recorded 0` refused, verified
  live, exit 2), the `cost` field of `per_instance_details.json`
  (lines 71–75), and the zero-success case ("If the run completed
  zero runs, no comparison is shown") are all documented. The
  zero-success sentence itself was **not** live-run by me; it is
  confirmed only by code (`averth/try_report.py:231`, "No completed
  runs, so there is no per-run figure…") — not signed off as a
  live behaviour.
- **D9 — FIXED.** The runnable `--ledger`/`--checks` pair is given
  (lines 124–129) and ran literally from the repo root with the
  expected V0 line and digest-verified state. Ledger-alone
  (unverified), checks-alone (exit 2), and digest-mismatch
  (exit 2, no HTML) all verified live as documented.
- **D10 — FIXED.** README lines 93–95 state all three defaults
  (`miniswe-import`, `jsonl-import`, `langfuse-import`); all three
  match the importer signatures (`averth/importers/miniswe.py:210`,
  `jsonl.py:166`, `langfuse.py:190`, each `agent_name=…`), and the
  JSONL default was confirmed live in the generated HTML header.
  (Langfuse default is code-verified only; no Langfuse export was
  run live.)
- **D11 — FIXED.** `--force` and the re-run refusal are documented
  (lines 204–206) and the refusal was verified live (exit 2);
  the work dir is stated relative to the caller's cwd and the
  section now adds "Run this from the repository root."
  (lines 199–203).
- **D12 — FIXED.** The README (lines 188–197) now names the
  gold-patch cross-check and the non-published consistency checks
  (`api_calls`, baseline failure mode), lists PyPI among the
  prerequisites, and the script docstring corrects the
  "checkout never modified" claim (work dir + `averth.egg-info`,
  no tracked file modified). The reproduce run passed 47/47
  live. Timing caveat: see N3.
- **D13 — PARTLY.** Fixed: no-end-event-without-exit-status
  (lines 218–221), parsed-events regression test (line 224),
  integer division for input tokens (line 209–210), exact
  case-sensitive `Submitted` match. **Not fixed:** the fence rule
  (lines 211–213) says the fence must be "exactly ```` ```bash ````
  followed by a newline, optionally with trailing spaces" — but
  the code (`averth/importers/miniswe.py`, `_BASH_FENCE =
  re.compile(r"```bash[ \t]*\n?(.*?)```", …)`) makes the newline
  **optional**, and my live probe proves a no-newline fence still
  emits a tool event. The sentence also garbles the order (trailing
  spaces come *before* the optional newline in the regex).
  Also, "output tokens equal to the characters … divided by 4"
  (line 210) omits "integer-" although the code is `// 4` for
  output too. And "byte for byte" survives outside the README —
  see N2.
- **D14 — FIXED.** A "Trace formats" section exists (lines
  158–184) with a per-format shape, the trajectory fixture and
  S3 URL shape, and a JSONL example whose two lines are
  byte-identical to the fixture. Langfuse gets a shape
  description rather than literal example lines; that matches
  what the first-pass fix asked for.
- **D15 — FIXED.** "Retries: 0" (line 117, not "retry share");
  the lede is scoped to the `try` command itself (lines 3–6);
  "Cost per completed run" heading and the "completed means
  finished and submitted" gloss (lines 150–153) match the live
  stdout; the $0.91 bucket label is quoted exactly as the live
  report prints it (lines 119–122).
- **D16 — FIXED.** `curl` is in the prerequisites (line 26);
  the CHANGELOG reproduce claim is qualified
  (`docs/CHANGELOG.md` lines 15–18: "checks the published
  numbers listed in its PUBLISHED table, plus a gold-patch
  cross-check and consistency checks that are not published
  numbers", plus the explicit exclusions); help and README agree
  on `--model`. (The CHANGELOG still says "byte for byte" —
  see N2, which is a D13 remnant rather than a D16 item.)

## New defects found

- **N1 (minor, error text contradicts the docs).**
  `averth/importers/miniswe.py:154` (the no-model ValueError,
  surfaced by the CLI): "…or put the model name in the file
  path". Under the new basename-only rule that is wrong twice
  over: a model name in the *directory* part of the path does
  not work (verified live), and "file path" invites exactly
  that mistake. Fix: "…or put the model name in the file
  name". The `--help` text is fine; only this error string is
  stale.
- **N2 (minor, "byte for byte" survives in two places).**
  `docs/CHANGELOG.md:10` still says the importer "reproduces
  the published case-study events byte for byte", and
  `averth/importers/miniswe.py:8` (module docstring) says the
  same. The test (`tests/test_try_it.py:43–45`,
  `test_converter_reproduces_published_events_byte_for_byte`)
  compares parsed event dicts, not bytes — the first-pass
  finding stands for these three locations even though the
  README itself was fixed. Fix: "reproduces the published
  case-study events" / rename the test, in all three places.
- **N3 (minor, timing band).** The README (line 200) and the
  script docstring say the Django install takes "47 to 74
  seconds measured". My full reproduce run took **86 s** wall
  time (single run, this machine/network). If 47–74 s is the
  Django-install portion only, say so; if it is the total
  runtime, the band is already exceeded by one measurement.
  The "allow more on a slow connection" hedge softens this;
  widen the band or scope it before it reads as a promise.

## Not checked / not signed off

- Python 3.9 specifically was not tested (same gap as
  first-pass).
- The `--recorded 0.3205` source value was not independently
  fetched from `per_instance_details.json` (same gap as
  first-pass); the reproduce script does check it against the
  live leaderboard record and passed.
- The zero-success `--recorded` case and a live Langfuse export
  run were not executed (code-checked only, as noted above).
- No source file was edited. Nothing was merged, pushed,
  deployed, or sent to anyone.

## Files

- Review: `try-it/reviews/review-4-docs-verify.md` (this file)
- Scratch: `try-it/reviews/scratch-4-verify/case-study-run.log`
  (48-line live stdout), `ledger-run.log`,
  `ledger-report.html`, `reproduce-run.log` (47/47 PASS, 86 s)
