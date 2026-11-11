# End-to-end test of the fixed reproduction steps (operator, 2026-11-11)

Tested the reproduction section of the rewritten `case-study-1.md` verbatim,
from a clean directory `/tmp/repro-cs1-fixed`, after the honesty/numbers/
reproduction reviews. All commands copied from the fixed case study text.

## Stage 1: checkout + venv (exit 0)

- Shallow checkout: `git rev-parse HEAD` =
  `63884829acd207404f2a5c3cc1d6b4cd0a822b70`. Detached HEAD note shown, as
  the case study states.
- Venv + install: Django `4.2.dev20220809040848`.

## Stage 2: patches + tests (exit 0)

- Test-patch extraction (pyarrow in venv): `FAIL_TO_PASS:
  ["test_annotate_with_full_when (expressions_case.tests.CaseExpressionTests)"]`,
  base_commit assert passed, `git apply` clean.
- Submission extraction (stdlib json): `git apply` clean after one appended
  newline. `git diff --stat`: 2 files, 14 insertions.
- C1: `Ran 1 test in 0.007s`, OK, exit 0.
- C2: `Ran 89 tests in 0.160s`, OK (skipped=1), exit 0.
- Revert (`git restore django/db/models/expressions.py`): target test FAILED
  (errors=1), `OperationalError: near "THEN": syntax error`, exit 1.
- Re-apply (`git apply /tmp/submission.diff`): 2 files, 14 insertions,
  target test OK, exit 0.

## Stage 3: meter (exit 0)

- Clone of `Wesley3141/Averth`, venv, `pip install -e .`, trace file copied
  in, meter command as written.
- Output lines as the case study quotes: `Attempts: 1`, `Autonomous
  completions: 1 (100.0%)`, `Retries: 0`, `Fully loaded: $0.98`, model $0.91,
  tools $0.07, context compounding 9.9x, context tax $0.68 (75%), yield 100%,
  p50/p95/max $0.98.
- HTML report byte-identical to the saved `trace-events-django-15930.html`
  (`diff` clean).

## Stage 4: V0 (exit 0)

- Branch `criterion-c-checks-digest`, HEAD `8ec848b`. `python` resolved to
  the Django venv python via PATH, as the case study instructs.
- Marker `2026-11-11T05:19:19Z` (after the last repo edit).
- Checks digest `sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`,
  identical to the published digest. The portable checks file reproduces.
- Counts `{'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 0.5,
  runs 2 (0 superseded).
- C1 VERIFIED, Tier 2, exit 0, digest `sha256:081dd9cc...` (matches
  published). C2 VERIFIED, Tier 2, exit 0, digest `sha256:498fa2e3...`
  (matches the FIRST run's digest, not the published second run's
  `sha256:c3c5f341...`). This is the D6 timing lottery in action: the same
  command run minutes apart lands on different C2 digests, which is why the
  case study tells reproducers to compare exit codes, test counts, and
  verdicts, not digests.

## Result

Every step in the fixed reproduction section executes as written and
produces the stated outcomes. No step failed, no command needed correction.

## Addendum: v2 review fixes re-tested (2026-11-11, after the v2 reviews)

The three v2 reviews each failed the rewritten case study on new, narrow
issues. Fixes applied to `case-study-1.md`:

- Honesty v2 N1 / reproduction v2 N2: the V0 block never told the reader to
  check out `criterion-c-checks-digest`. Added `git checkout
  criterion-c-checks-digest` before `cd evidence-v0`, with the reason
  (master's verifier has no checks digest).
- Reproduction v2 N1: the working-directory flow was broken two ways. The
  meter block now starts with `cd ..` (clone Averth next to `django-base`,
  not inside it), and the V0 block now uses `cd evidence-v0` (the reader is
  already inside `averth/` after the meter step).
- Reproduction v2 N3: marker upper bound unstated. The text now says the
  marker must be from just before the run, after the last edit; a marker in
  the future supersedes the runs, and so does one from before the last edit.
- Numbers v2 N1: the cited C2 run-time line was the first run's `0.152s`.
  Changed to the published run's `0.168s` (recomputed from the new ledger:
  `sha256(stdout+stderr)` gives exactly the cited digest `c3c5f341...`).
- Honesty v2 N3: the `--python` parenthetical claimed it was part of the
  recorded invocation, which no record supports. Reworded to state only that
  the flag is unused with an allowlist and does not affect the run.
- Honesty v2 N2: the gold-patch "target test passes" claim rested only on the
  module run. The gold target test was run separately (exit 0, `Ran 1 test
  in 0.007s`, OK, 2026-11-11T05:22:09Z) and appended to
  `gold-patch-run.txt`. The agent patch was restored after (2 files, 14
  insertions, target test OK).

Re-test of the corrected V0 block, executed literally from inside
`/tmp/repro-cs1-fixed/averth` (where the meter step leaves the reader):
`cd ..` from `django-base` lands in the parent with `averth` and
`django-base` as siblings; `git checkout criterion-c-checks-digest` gives
`8ec848b`; `cd evidence-v0` succeeds; V0 with a fresh marker
(`2026-11-11T05:23:22Z`) exits 0 with checks digest `sha256:f25cd3bc...`
(matching the published digest), counts `{'VERIFIED': 2,
'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 0.5, runs 2 (0 superseded).
