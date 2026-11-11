# Review: reproduction of case study 1, round 2 (adversarial, fixed steps re-executed)

Reviewer: independent adversarial reproduction reviewer (subagent, no coordination with authors or operator)
Date: 2026-11-11 (runs 05:20–05:22 UTC; all times UTC unless noted)
Case study reviewed: `case-study-1.md` as rewritten after the first FAIL review
  (`review-reproduction.md`, defects D1–D14), plus the operator's own test
  (`repro-test-fixed-steps.md`, which reported a pass).
Fresh work: no new clone. The operator's existing from-scratch run at
  `/tmp/repro-cs1-fixed` was reused as instructed (Django checkout at base
  commit + test patch + agent patch, `django-venv`, Averth clone with
  `averth-venv`, operator V0 output at
  `averth/evidence-v0/v0-run-repro`). The operator's V0 output was backed up
  before my re-runs and restored afterwards; the Django checkout was left in
  the state found (base commit + both patches, 2 files, 14 insertions).
Environment: Python 3.12, git, curl. No full Django clone was run.

## Verdict: FAIL

The fixed steps are a large improvement — D1, D2, D3, D5, D6, D7, D8, D10,
D11, D12, D14 are genuinely fixed, and when the commands are reached they
reproduce exactly (meter figures, HTML byte-identical, V0 counts
2 VERIFIED / 2 EXTERNAL-UNVERIFIABLE, unknown rate 0.5, checks digest
`sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`).
But the section still does not execute as written, in one shell, top to
bottom, for two independent reasons:

- **N1 (BLOCKER): the working-directory flow between the meter block and the
  V0 block is broken.** After the meter block the shell is inside `averth`,
  and the V0 block's first line, `cd averth/evidence-v0`, fails there
  (`No such file or directory`, exit 1, verified in a subshell). The meter
  block itself has the same class of problem one step earlier: at that point
  the shell is inside `django-base` and the text never says to leave it, so
  `git clone … averth` as written nests Averth inside the Django repo under
  test — and V0 snapshots the repo with `repo.rglob("*")`, so a nested
  checkout would be hashed into the ledger. The operator's own passing run
  proves the deviation: their layout has `averth` as a *sibling* of
  `django-base`, which requires an unstated `cd ..` before the clone.
- **N2 (MAJOR): no `git checkout criterion-c-checks-digest` anywhere in the
  reproduction steps.** A plain `git clone` lands on master (`1431bef`).
  Master V0 reproduces the verdict *counts*, but its ledger has no
  `checks_digest` field at all, so the text's promise — "the checks digest
  in the ledger … reproduces from the saved checks file" — is unverifiable
  on master, and the checks-freeze protection the case study describes is
  branch-only. The first review's D4 fix explicitly included the checkout
  line; the rewrite dropped it.

This is a FAIL of the reproduction section, not of the case study's
findings. Nothing else in the case study needed correction: every number I
reached reproduced. The fix is small (a `cd ..` before the clone, `cd
evidence-v0` instead of `cd averth/evidence-v0`, one checkout line), but as
written a reader following the section sequentially in one shell is stuck
at the V0 `cd`, and a reader who gets past it by other means is on the
wrong verifier version.

## 1. What I executed (run log)

All commands below were run against `/tmp/repro-cs1-fixed` unless noted.
State on arrival, verified first: `git rev-parse HEAD` in `django-base` =
`63884829acd207404f2a5c3cc1d6b4cd0a822b70`; `git status --porcelain` = `M
django/db/models/expressions.py`, `M tests/expressions_case/tests.py`;
`git diff --stat` = 2 files, 14 insertions. Averth checkout: branch
`criterion-c-checks-digest`, HEAD `8ec848b7d3085c752f340ffe2754d90ada432edd`.

### 1.1 Meter command, as written — PASS, exact

```
cd /tmp/repro-cs1-fixed/averth
/tmp/repro-cs1-fixed/averth-venv/bin/python -m averth.cli trace trace-events-django-15930.jsonl --format jsonl
# exit 0
```

Output lines match the case study verbatim: `Attempts: 1`,
`Autonomous completions:1 (100.0%)`, `Retries: 0`, `Model/API (terminal):
$0.91`, `Tool calls: $0.07`, `Fully loaded: $0.98`, context compounding
`9.9x`, context tax `$0.68 (75% of model spend)`, yield `100%`,
p50/p95/max `$0.98`. (The case study writes `Autonomous completions: 1`;
the tool prints `Autonomous completions:1` — same words, column-aligned
spacing; not a defect.) The rewritten HTML is byte-identical to the saved
`trace-events-django-15930.html` (`diff` clean) and identical to the
operator's run. The `Priced` / estimate caveat in the text matches the
tool's own `COST BASIS: ESTIMATED` header.

### 1.2 Runtests commands, as written — PASS, exact

From `django-base`, with the agent patch applied:

```
../django-venv/bin/python tests/runtests.py expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
# Ran 1 test in 0.007s / OK / exit 0
../django-venv/bin/python tests/runtests.py expressions_case -v 0
# Ran 89 tests in 0.170s / OK (skipped=1) / exit 0
```

Revert check, as written: `git restore django/db/models/expressions.py`,
then the target test `FAILED (errors=1)`, exit 1 (the `OperationalError:
near "THEN"` failure; tail output confirmed `FAILED (errors=1)`).
Re-apply, as written: `git apply /tmp/submission.diff` → 2 files,
14 insertions; target test OK, exit 0. (Note: `/tmp/submission.diff`
(748 bytes) and `/tmp/test-patch.diff` still existed from the operator's
run; a fresh reader creates them via the D1/D2 blocks in the same session.)

### 1.3 V0 command, as written except the `cd` — PASS, exact (correct marker)

The V0 `cd` as written fails (see N1), so the command itself was run from
`evidence-v0` reached by the corrected `cd evidence-v0`. Everything else
is literal from the text, with the `/path/to/…` placeholders substituted
and the marker set to the current UTC time (see N3 for why the marker
matters):

```
cd /tmp/repro-cs1-fixed/averth/evidence-v0
export PATH=/tmp/repro-cs1-fixed/django-venv/bin:$PATH   # `which python` = django-venv python
python3 cli.py --repo /tmp/repro-cs1-fixed/django-base \
  --checks /home/hatch/workspace/averth/case-study-1/case-study-1-checks.json \
  --allowlist /home/hatch/workspace/averth/case-study-1/case-study-1-allowlist.json --execute \
  --python /tmp/repro-cs1-fixed/django-venv/bin/python \
  --trace /tmp/repro-cs1-fixed/averth/trace-events-django-15930.jsonl \
  --final-edit-marker 2026-11-11T05:21:07Z \
  --out ./v0-run-repro --report-id v0-case-study-1-repro
# exit 0
# checks digest: sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a
# counts: {'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}
# unknown rate: 0.5
# runs: 2 (0 superseded, retained, never cited)
```

Ledger judgments confirm the published rows: C1 VERIFIED, Tier 2, exit 0,
`after_final_edit: true`, output digest
`sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3`
(identical to the published C1 digest); C2 VERIFIED, Tier 2, exit 0,
`after_final_edit: true`, output digest
`sha256:ac2e0f52e63b5446081ef514c7c57293eb342349e7251e120d479698ac26c013`
(differs from the published C2 digest — see D6); C3, C4
EXTERNAL-UNVERIFIABLE. My branch-run ledger was saved to
`/tmp/v2-my-branch-v0-ledger.json` before the operator's output was
restored.

### 1.4 V0 with a future marker — the N3 trap, demonstrated

My first V0 attempt used a marker 2 minutes in the *future*
(`2026-11-11T05:22:51Z`, generated `date -u -d "+2 minutes"` while the run
executed at 05:20:53Z). Result, exit 0 but wrong verdicts:

```
counts: {'NOT OBSERVED': 2, 'EXTERNAL-UNVERIFIABLE': 2}
unknown rate: 1.0
runs: 2 (2 superseded, retained, never cited)
```

The verifier supersedes any run started before the marker (`verifier.py`:
"A run before the marker is superseded"). A future marker therefore
silently voids both runs. The text states only the lower bound (marker
after the last edit); the upper bound (marker before the run starts) is
unstated. A reader using the current time is fine; a reader who pads into
the future gets silently superseded runs with no error. Minor, but real —
and it is the only respect in which D13 is incomplete.

### 1.5 V0 on master (plain clone, no branch checkout) — N2, demonstrated

To test what a reader gets from the steps as written (plain `git clone`,
no checkout line), I added a worktree at `origin/master` (`1431bef`,
detached HEAD) at `/tmp/v2-master-averth` — no new clone — and ran the
identical V0 command from its `evidence-v0`:

```
counts: {'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}
unknown rate: 0.5
runs: 2 (0 superseded, retained, never cited)
```

Counts reproduce on master. But the master ledger has **no `checks_digest`
key at all** (key list: `schema_version, report_id, generated_at,
task_intent, task_intent_source, target_repo, target_commit, commit_note,
workspace_dirty, final_edit_marker, files, runs, judgments, coverage,
trace_summary`), and its report contains no "checks digest" line, while
the branch ledger/report carry
`sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`.
Master's `requirement_spec.py` has no `checks_digest` function and its
`cli.py` never prints one; the branch diff vs master for `evidence-v0/` is
5,385 insertions / 93 deletions across 10 files, including the freeze
logic. So on master the case study's sentence "the checks digest in the
ledger … reproduces from the saved checks file" cannot be checked at all,
and the reader is running a verifier without the mid-run-edit freeze the
case study describes. Master-run ledger saved to
`/tmp/v2-master-v0-ledger.json`; the worktree was removed afterwards.
(`git ls-remote` confirms remote HEAD = `1431befa1168e432de59d4ca3220b992a888d90f`
= master, and `refs/heads/criterion-c-checks-digest` =
`8ec848b7d3085c752f340ffe2754d90ada432edd`.)

### 1.6 C2 digest lottery (D6) — re-quantified in this session

Eight consecutive C2 runs: `0.154s, 0.185s, 0.167s, 0.164s, 0.147s,
0.203s, 0.188s, 0.149s` — 8 distinct timings (plus 0.152s, 0.156s,
0.160s, 0.170s seen in earlier runs this session). C1 was `0.007s` in
4/4 runs here. Distinct C2 output digests now observed across runs:
published `c3c5f341…`, operator's `498fa2e3…` (which matched the *previous*
published digest, not the current one), my future-marker run `3076f792…`,
my branch run `ac2e0f52…`, my master run `496f1474…` — none of the four
new ones equals the published `c3c5f341…`. C1's digest
`081dd9cc…` matched the published value in all three of my V0 runs.
The D6 caveat is accurate and, if anything, understated for C2.

### 1.7 Checks digest from the published file — verified independently

`sha256sum` of `case-study-1-checks.json` =
`f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`,
identical to the published digest and to both branch-ledger digests
(operator's and mine). The v1 absolute-paths file still hashes to the old
`6dde8826…`, as expected. The digest is a plain file-bytes SHA-256
(`requirement_spec.py: checks_digest` = `sha256_bytes(raw)`), so it
reproduces on any machine from the published file with no path
substitution — D5 is fully fixed.

## 2. Per-defect re-check: D1–D14

Severity scale as in the first review: BLOCKER = the step cannot be
completed as written; MAJOR = it completes but the result cannot be
checked as stated, or it wastes unreasonable time/disk; MINOR = wording
or a paper cut a careful reader can work around.

| Defect | Verdict | Evidence |
| --- | --- | --- |
| D1 test-patch extraction missing; `git apply` aimed at a Parquet file | FIXED | Text now saves the download as `/tmp/swebench-verified.parquet`, installs `pyarrow` in the venv, gives the full heredoc extraction with `base_commit` assert, writes `/tmp/test-patch.diff`, then `git apply /tmp/test-patch.diff`. Operator ran it clean (§2 stage 2); the file exists (902 bytes) and the patch is applied in the checkout. |
| D2 submission extraction missing; newline appended to the JSON file | FIXED | Text now saves the trajectory as `/tmp/django-15930.traj.json`, gives the stdlib-`json` heredoc writing `traj['info']['submission']` to `/tmp/submission.diff`, then `printf '\n' >> /tmp/submission.diff` (now correctly targeting the extracted patch), then `git apply`. Operator ran it clean; `/tmp/submission.diff` is 748 bytes; re-apply in §1.2 worked. |
| D3 meter command `ModuleNotFoundError`; install, cwd, trace provenance missing | FIXED (command level) | Text now gives clone + `cd averth` + `../averth-venv` + `pip install -e .` + `cp /path/to/trace-events-django-15930.jsonl .` + the meter command, and states the HTML output. §1.1 reproduces every figure exactly and the HTML is byte-identical. Residual cwd issue is N1, not D3's install/provenance complaint. |
| D4 V0 paragraph gives no executable command | PARTIALLY FIXED | The full command now exists with every flag (`--repo --checks --allowlist --execute --python --trace --final-edit-marker --out --report-id`) and §1.3 reproduces the published counts with it. But two pieces the first review's D4 fix prescribed are missing: the `git checkout criterion-c-checks-digest` line (→ N2) and a working `cd` (→ N1). The core complaint (no command) is fixed; the command as placed in the section is not yet runnable as written. |
| D5 checks/allowlist embed absolute `/home/hatch/…` paths; digest path-bound | FIXED | Both files now use bare `python` as runner. §1.7: file-bytes SHA-256 of the published checks file equals the published digest exactly, with no substitution; my branch V0 run's ledger digest matches too. |
| D6 cited run digests embed wall-clock timing, usually do not reproduce | FIXED | Caveat now appears twice: in "What V0 verified" ("a reproducer's digests will usually differ for C2; compare exit codes (0), test counts (1 test OK; 89 tests OK, skipped=1), and verdicts, not digests") and in the V0 reproduction paragraph. §1.6 re-quantifies it: 8 distinct C2 timings in 8 runs, 5 distinct C2 digests observed, none matching the published `c3c5f341…`; C1 stable and matching. The caveat is accurate. |
| D7 full `git clone` needlessly slow/large, exceeds /tmp budget | FIXED | Text now has only the shallow form (`mkdir django-base && cd django-base`, `git init`, `git fetch --depth 1 origin <sha>`, `git checkout FETCH_HEAD`). No full clone anywhere in the section. Operator stage 1 verified it; `rev-parse HEAD` confirms the SHA. |
| D8 `pyarrow` not installed; system-Python install breaks pandas | FIXED | Text installs it inside the venv only: `../django-venv/bin/pip install pyarrow`. No system-Python install is suggested anywhere. |
| D9 misleading filenames; unstated working directory | FIXED for the Django part; residual in N1 | Filenames are now truthful (`/tmp/swebench-verified.parquet`, `/tmp/django-15930.traj.json`, real `.diff` names for real diffs), and the section states "Run all `git apply` and `runtests.py` commands from inside `django-base`". But no equivalent cwd statement exists for the Averth blocks — the meter clone and V0 `cd` assume a return to the work directory that is never stated (N1). |
| D10 recorded $0.3205 has no direct URL | FIXED | "Where the trace lives" now lists the direct raw file: `https://raw.githubusercontent.com/m0at/experiments/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514/per_instance_details.json`, alongside the tree link. |
| D11 prerequisites and revert-command wording | FIXED | Prerequisites now read "Python 3.12 (with `venv` and `pip`), git, curl, and internet access"; revert uses `git restore django/db/models/expressions.py` (verified in §1.2); detached-HEAD note present ("That is expected, not an error"). |
| D12 meter "expected output" does not match tool wording | FIXED | Text now quotes the actual lines (`Attempts: 1`, `Autonomous completions: 1 (100.0%)`, `Retries: 0`, `Fully loaded: $0.98`) and adds the `Priced`-label caveat with the characters/4 token-estimate explanation. §1.1 matches verbatim (modulo column spacing). |
| D13 `--final-edit-marker` value and required repo state unstated | FIXED in substance; see N3 | Text now states the precondition (Django checkout at base + test patch + agent patch, run V0 last), the marker rule (ISO-8601 after the last edit), and the operator's marker (`2026-11-11T05:14:32Z`). §1.3 with a current-time marker reproduces. Only the upper bound is missing (N3, minor). |
| D14 pyarrow returns test lists as strings | FIXED | Note present verbatim in substance: "`pyarrow` returns `FAIL_TO_PASS` and `PASS_TO_PASS` as stringified lists, not lists… Use `ast.literal_eval` if the test lists are needed." The extraction only needs `test_patch`, a plain string. |

## 3. New defects found

### N1 — BLOCKER: working-directory flow breaks between the meter block and the V0 block (and at the meter clone)

- The section establishes a sequential single-shell flow: `mkdir
  django-base && cd django-base`, then "Run all `git apply` and
  `runtests.py` commands from inside `django-base`". No instruction ever
  returns the reader to the work directory.
- Meter block, as written from `django-base`: `git clone
  https://github.com/Wesley3141/Averth.git averth` creates
  `django-base/averth` (verified: no such directory exists in the
  operator's checkout because the operator did not follow this; their
  `averth` is a sibling of `django-base`, which requires an unstated `cd
  ..`). A nested clone would also pollute the repo V0 snapshots: the
  ledger's file list is built with `repo.rglob("*")`
  (`evidence_ledger.py:96`), i.e. every file under `django-base`
  including untracked directories, so a nested Averth checkout (plus its
  venv) would be hashed into the ledger.
- V0 block, as written from the post-meter cwd (`averth` in the sibling
  reading, `django-base/averth` in the nested reading): `cd
  averth/evidence-v0` fails in **both** readings. Verified in a subshell:
  `(cd /tmp/repro-cs1-fixed/averth && cd averth/evidence-v0)` →
  `No such file or directory`, exit 1. The only reading under which it
  works is "start each code block from the work directory in a fresh
  shell", which the text never states.
- Fix: add `cd ..` (return to the work directory) before the meter
  clone, and change the V0 block's first line to `cd evidence-v0`
  (correct from inside `averth` under either the sibling or the nested
  layout). The operator's passing test does not cover this: their layout
  and their V0 run both required deviations from the text that are not
  recorded in `repro-test-fixed-steps.md`.

### N2 — MAJOR: reproduction steps never check out `criterion-c-checks-digest`; plain clone is master, whose ledger has no checks digest

- The string `criterion-c-checks-digest` appears in the case study only
  in the "What V0 verified" prose, never as a command. The meter block
  is a plain `git clone https://github.com/Wesley3141/Averth.git averth`
  with no checkout, and the V0 block says only "use the same Averth
  checkout".
- Remote HEAD is master `1431bef` (`git ls-remote`); the branch is
  `8ec848b`. The branch is 5,385 insertions ahead of master in
  `evidence-v0/` alone, including the checks-freeze logic.
- Demonstrated (§1.5): master V0 gives the same verdict counts
  (2 VERIFIED / 2 EXTERNAL-UNVERIFIABLE, 0.5, 2 runs), so the headline
  numbers survive — but the master ledger contains no `checks_digest`
  field and no "checks digest" report line, so the text's claim that
  "the checks digest in the ledger
  (`sha256:f25cd3bc…`) reproduces from the saved checks file" cannot be
  verified on master, and the reader runs a verifier without the
  freeze protection the case study describes as part of the run.
- Fix: restore the line from the first review's D4 fix, in the meter
  block right after the clone: `cd averth && git checkout
  criterion-c-checks-digest   # HEAD 8ec848b` (adjusting for the N1
  `cd` fix so the sequencing is unambiguous). The operator's checkout
  is on the branch, so again their passing test required an unrecorded
  deviation from the text.

### N3 — MINOR: `--final-edit-marker` upper bound unstated; a future marker silently supersedes every run

- Text: "The `--final-edit-marker` must be an ISO-8601 timestamp after
  your last edit to the checkout, or the runs are recorded superseded."
  That states only the lower bound. Demonstrated (§1.4): a marker 2
  minutes in the future produced exit 0 with counts `{'NOT OBSERVED':
  2, 'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 1.0, 2 superseded runs —
  no error, just silently voided verdicts.
- Fix: "a timestamp after your last edit to the checkout **and just
  before you run the command** (use the current UTC time, e.g. `date -u
  +%Y-%m-%dT%H:%M:%SZ` immediately before invoking V0)".

## 4. What verified cleanly (no fix needed)

- Meter: every figure in the case study reproduces; HTML byte-identical
  to the saved report.
- V0 on the branch with a current-time marker: counts, unknown rate, run
  count, Tier 2, `after_final_edit`, checks digest, and the C1 output
  digest all reproduce exactly.
- Checks digest reproduces from the published file by plain SHA-256 with
  no path substitution (D5 fully closed).
- D6 caveat re-quantified and accurate; C2 digests vary run to run,
  C1's is stable in this session.
- Revert/re-apply discrimination: target test fails without the patch,
  passes with it, exactly as claimed.
- Shallow checkout, both extractions, prerequisites, revert wording,
  meter wording, direct `per_instance_details.json` URL, stringified-list
  note: all as fixed.

## 5. What was not tested

- The shallow Django fetch was not re-run (already verified by the first
  review §2.2 and the operator stage 1; the existing checkout's HEAD was
  confirmed instead). No full `git clone` was run, per instructions.
- No second database backend, no human review (out of scope; C3/C4 are
  already EXTERNAL-UNVERIFIABLE).
- The `pip install ./evidence-v0` / `averth-evidence` console-script path
  (ran `evidence-v0/cli.py` directly, as the text does).
- The `/path/to/…` placeholders in the meter and V0 blocks require
  substitution with the reader's real paths; they are visibly placeholders
  (and match the first review's own suggested fix text), so they are noted
  here, not counted as defects — unlike N1/N2, which are literal commands
  that fail or silently change the result.

## 6. Suggested fix (exact, minimal)

In the meter block, before the clone:

```bash
cd ..   # back to the work directory; the Averth checkout is a sibling of django-base, not inside it
git clone https://github.com/Wesley3141/Averth.git averth
cd averth && git checkout criterion-c-checks-digest   # HEAD 8ec848b, the verifier version used here
```

In the V0 block, replace the first line:

```bash
cd evidence-v0   # you are already inside averth after the meter block
```

And in the marker sentence, add: "…after your last edit to the checkout
and just before you run the command (use the current UTC time)". With
those three changes, the section executes as written in one shell; as
written now, it does not.

## Appendix: artifacts from this review

- My branch V0 ledger (correct marker): `/tmp/v2-my-branch-v0-ledger.json`
  (counts 2/2, unknown 0.5, checks digest `f25cd3bc…`, C1 digest
  `081dd9cc…`, C2 digest `ac2e0f52…`).
- Master V0 ledger (plain clone, no checkout):
  `/tmp/v2-master-v0-ledger.json` (counts 2/2, unknown 0.5, **no
  `checks_digest` key**).
- Operator's V0 output was backed up to `/tmp/v2-operator-v0-backup`
  before my re-runs and restored afterwards; the master worktree was
  removed. Final checkout state verified after cleanup: `django-base`
  at `63884829acd207404f2a5c3cc1d6b4cd0a822b70`, 2 files modified,
  14 insertions; Averth on `criterion-c-checks-digest` at `8ec848b`.
- No file in `~/workspace/averth/case-study-1/` was edited by this review.
