# Review 4 — Docs clarity, SECOND RE-VERIFICATION

**Verdict: FAIL**

Five of the six scoped items are fixed, verified live. One is not:
N1 — the no-model error the user actually sees still says "file
path". The fix landed in the docstring only (`miniswe.py:154`) and
missed the `ValueError` itself (`miniswe.py:172–173`), which is the
string the CLI surfaces. That is the single open item, and it is the
same class of defect as before (error text contradicting the docs),
so this stays FAIL. Everything else in scope — including the
blocking D1, now resolved except for the push that needs the user's
tap — checks out.

## What I checked live (commands and outputs)

All runs used `~/workspace/averth/.venv/bin/python -m averth.cli`
unless noted. Scratch evidence:
`try-it/reviews/scratch-4-verify2/` (`case-study-run.log`,
`reproduce-run.log`). The 290 MB reproduce work dir and the
`/tmp` clones/venv were deleted after the runs; the logs are
retained.

1. **Fresh GitHub clone** (`/tmp/try-verify2-clone`, since deleted):
   `git clone https://github.com/Wesley3141/Averth.git` succeeded;
   `git checkout try-it` failed: `error: pathspec 'try-it' did
   not match any file(s) known to git`, exit 1. `git ls-remote
   --heads origin` shows **0** `try-it` refs. Expected: the
   branch is committed but not pushed, and pushing is forbidden
   to me. The README note (lines 21–24) discloses this honestly
   (see D1).
2. **Local clone, end to end** (`git clone ~/workspace/averth`,
   `/tmp/try-verify2-local`, since deleted): `git checkout try-it`
   succeeded, HEAD is `0750720 One-command try-it (averth try)
   and case-study reproduction script`. `try-it/` present
   (`README.md`, `fixtures`, `reproduce-case-study.py`,
   `reviews`); `averth/importers/miniswe.py` and
   `averth/try_report.py` present. A fresh venv in `/tmp` with
   `pip install -e .` from the clone gives `averth try` as a
   valid choice (`try --help` prints the full usage). The
   case-study run from a clean directory, using the README's
   exact `curl` URL (69,126 bytes) and exact `try` command,
   exited 0: `Retries: 0` (log line 10), `  Fully loaded:
   $0.98` (line 17), `Recorded cost (operator-supplied):
   $0.3205; metered estimate per completed run: $0.98 ESTIMATED
   (3.07x)` (line 48), `django-15930-try.html` written. All
   published numbers reproduce from the clone.
3. **No-model error, live** (repo venv, trajectory copied to
   `/tmp/noname-traj.json`): `averth try /tmp/noname-traj.json`
   exited **2** with: `averth: error: failed to parse
   /tmp/noname-traj.json (traj): no model named for
   /tmp/noname-traj.json: pass --model (e.g. --model
   claude-sonnet-4-20250514) or put the model name in the file
   path`. (See N1.)
4. **Fence probe, live** (`miniswe.miniswe_events` on synthetic
   trajectories, model passed explicitly): a ```` ```bash ````
   fence with **no newline** after `bash` yields 2 events
   (`model`, `tool`); uppercase ```` ```BASH ```` with a trailing
   space also yields 2 events; a plain ```` ```bash\n ```` fence
   yields 2 events. The README sentence matches this behaviour
   (see D13).
5. **Reproduce script end to end**: `python3
   try-it/reproduce-case-study.py --work-dir
   try-it/reviews/scratch-4-verify2/repro-work` from the repo
   root exited 0 in **97 s** wall time: "reproduce: all **51**
   checks PASSED" (51 `PASS` lines in `reproduce-run.log`; the
   two `FAIL` substring matches are check names —
   `FAIL_TO_PASS is 1 test` and `V0 FAILED (actual 0…)` — both
   PASS). No tracked file was modified by the run (`git status`
   clean for `try-it/`, `averth/`, `docs/`, `tests/`,
   `README.md`).

## Item-by-item verdicts

- **D1 — FIXED, except push.** (a) Fresh GitHub clone: `git
  checkout try-it` still fails, as expected — the branch is
  committed locally but not pushed to origin (0 remote refs),
  and pushing needs the user's tap. This is **not** a docs
  defect: the README note (lines 21–24) still accurately
  describes the state — "an unmerged branch and is not
  published yet. Until it is pushed, `git checkout try-it`
  fails on a fresh clone; run the commands from a checkout
  that already has the branch instead. Once the branch is
  published, the commands above work literally." (b) Local
  clone now works end to end (see live check 2): `try-it/`
  present, `miniswe.py` present, `averth try` a valid choice,
  case-study run reproduces $0.98 / 3.07x. The "invalid choice"
  hint (README lines 28–30) now reads "your checkout does not
  have the `try-it` branch checked out", which correctly
  diagnoses the remaining failure mode (wrong branch checked
  out) rather than the old committed-state case. Fully fixed
  for a stranger once the branch is pushed; nothing further
  for the docs to do.
- **D13 — FIXED.** README lines 211–219 now read: the fence is
  "exactly ```` ```bash ````, case-insensitive, optionally
  followed by trailing spaces and optionally by a newline",
  and output tokens are "the characters of the assistant
  message integer-divided by 4". Both match the regex
  (`` ```bash[ \t]*\n?(.*?)``` ``) and the `// 4` code, and the
  live fence probe (check 4) confirms the no-newline and
  uppercase-with-trailing-space cases emit tool events.
- **N1 — NOT FIXED.** The docstring was fixed
  (`averth/importers/miniswe.py:154`: "put the model name in
  the file name"), but the `ValueError` the CLI actually
  surfaces was not (`averth/importers/miniswe.py:172–173`):
  `"or put the model name in the file path"`. Verified live
  (check 3, exit 2): the user-facing error still says "file
  path", which under the basename-only rule is wrong — a model
  name in the directory part of the path does not work, and
  "file path" invites exactly that mistake. Fix: change
  `miniswe.py:172–173` to "the file name", same wording as the
  docstring. One-word fix; nothing else in scope depends on
  it.
- **N2 — FIXED.** `grep -rn "byte for byte\|byte_for_byte"`
  over `docs/CHANGELOG.md`, `averth/importers/miniswe.py`,
  `tests/test_try_it.py`, `try-it/README.md` returns nothing.
  The importer claim now reads "reproduces the published
  case-study events, as parsed event records" (CHANGELOG
  lines 9–10; `miniswe.py:8–10` docstring likewise), and the
  test is renamed `test_converter_reproduces_published_events`
  (`tests/test_try_it.py:43`). Observation, not a defect: the
  hyphenated form "byte-for-byte" survives once, at
  `docs/CHANGELOG.md:44`, in the unrelated V0 criterion-c
  entry ("an edit reverted byte-for-byte before the re-hash
  escapes detection"), where it describes a literal raw-bytes
  hash comparison and is accurate. It is not the N2 claim and
  needs no change.
- **N3 — FIXED.** The timing band now reads "47 to 86 seconds"
  in both `try-it/README.md:202` and the reproduce script
  docstring (`try-it/reproduce-case-study.py:34`). Observation:
  this run's total wall time was **97 s** (first verification:
  86 s). The sentence scopes the band to the Django-install
  portion ("about a minute for the Django install (47 to 86
  seconds measured; allow more on a slow connection)"), and
  neither the script nor its log prints a per-step breakdown,
  so I cannot decompose total vs install time. Not marked a
  defect; if a future run shows the install portion itself
  exceeding 86 s, widen the band then.
- **New (JSONL header/comment) — FIXED.** `try-it/README.md`
  lines 179–180: "Every line must be an event object with a
  `type` key; a file whose first line is a header or comment
  with no `type` is not supported." The sentence exists and
  states the limitation plainly.
- **README note spot-check (lines 21–24) — ACCURATE.** Branch
  committed locally as `0750720` (verified: `git log -1`,
  clean working tree for the try-it paths); unpushed to
  GitHub (verified: 0 `try-it` refs in `ls-remote --heads
  origin`); fresh-clone checkout fails (verified live,
  exit 1). The note describes exactly this state.

## New defects found

None, apart from the N1 miss itself (the docstring/error
split), which is an open item from the previous round, not a
new defect. No source file was edited. Nothing was merged,
pushed, deployed, or sent to anyone.

## Not checked / not signed off

- Python 3.9 specifically was not tested (same gap as the
  first verification).
- The `--recorded 0.3205` source value was not independently
  fetched from `per_instance_details.json`; the reproduce
  script checks it against the live leaderboard record and
  passed (51/51).
- The zero-success `--recorded` case and a live Langfuse
  export run were not executed (code-checked only, as before).

## Files

- Review: `try-it/reviews/review-4-docs-verify2.md` (this file)
- Scratch: `try-it/reviews/scratch-4-verify2/case-study-run.log`
  (48-line live stdout from the local clone),
  `reproduce-run.log` (51/51 PASS, 97 s)
