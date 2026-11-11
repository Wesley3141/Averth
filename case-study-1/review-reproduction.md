# Review: reproduction of case study 1 (adversarial, from scratch)

Reviewer: independent reproduction reviewer (subagent, no coordination with authors)
Date: 2026-11-11 (runs 04:54–05:15 UTC; all times UTC unless noted)
Case study reviewed: `case-study-1.md` (reproduction section only, plus the URLs it cites)
Fresh work directory: `/tmp/repro-cs1/` (new `django-base`, new `django-venv`; the
existing `~/workspace/averth/case-study-1/django-base` checkout was not touched)
Environment: Python 3.12.3, git 2.43.0, curl, GNU patch, `/tmp` is a 512 MB tmpfs,
network to GitHub measured very slow this session (~250 KB/s effective on the full clone).

## Verdict: FAIL

The reproduction steps **as written do not reproduce**. Three of the steps fail outright
when executed literally (D1, D2, D3), a fourth gives no executable command at all (D4),
and the first step (full `git clone`) could not complete inside the task's `/tmp`
budget (D7). A reader following the case study verbatim gets stuck at the test patch,
gets stuck again at the submission, gets a `ModuleNotFoundError` from the meter
command, and has no V0 command to run.

This is a FAIL **of the reproduction section, not of the case study's findings**.
Once the missing/corrected commands in this review are substituted, everything the
case study claims reproduces: the target test fails without the patch and passes with
it, the module passes 89 tests (1 skipped), the meter prints $0.98 with HTML
byte-identical to the saved report, and the V0 verifier returns the same verdicts
(2 VERIFIED / 2 EXTERNAL-UNVERIFIABLE, unknown rate 50%). The underlying evidence is
sound; the instructions for re-deriving it are not. No finding in the case study
needed correction — only the steps.

## 1. Per-URL fetch table

Every URL printed in the case study (plus the two it implies) was fetched with `curl -sL`.
All return HTTP 200. Content was verified, not just status.

| # | URL | HTTP | Size | Content check |
| --- | --- | --- | --- | --- |
| 1 | `https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json` | 200 | 69,126 B | Valid JSON; `info.model_stats` = `{instance_cost: 0.32052914999999993, api_calls: 35}`; `info.submission` 747 bytes, no trailing newline; byte-identical to the local `validation-traces/mini-swe-agent-s3/raw/django__django-15930.traj.json`; 72 messages (1 system, 35 assistant, 36 user) |
| 2 | `https://github.com/m0at/experiments/tree/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514` | 200 | 196,610 B | GitHub tree HTML; lists `per_instance_details.json`, `metadata.yaml`, `logo.jpg`. It is a directory page, not the data file (see D10) |
| 3 | `https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/report.json` | 200 | 9,284 B | Valid JSON; `resolved: true`; FAIL_TO_PASS success 1/1, failure 0; PASS_TO_PASS success 88/88, failure 0 |
| 4 | `https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/test_output.txt` | 200 | 26,276 B | Ends `OK`, in-memory SQLite DB destroyed; confirms the official run passed |
| 5 | `https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/patch.diff` (cited in `trace-selection.md`, not in the case study) | 200 | 747 B | Byte-identical to `info.submission` from URL 1; also missing its trailing newline. Confirms the missing newline is a property of the recorded artifact, not a transcription error |
| 6 | `https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet` | 200 | 2,096,679 B | Valid Parquet, 500 rows; instance `django__django-15930`, repo `django/django`, base commit `63884829acd207404f2a5c3cc1d6b4cd0a822b70`; extracted `test_patch` byte-identical to the saved `swebench-test-patch-django-15930.diff`; extracted `patch` byte-identical to the saved gold patch. Byte-identical to the local `swebench-verified.parquet` |
| 7 | `https://github.com/django/django` | 200 | 280,293 B | GitHub repo HTML page |
| 8 | `https://github.com/Wesley3141/Averth` | 200 | 253,564 B | GitHub repo HTML page; branch `criterion-c-checks-digest` exists, HEAD `8ec848b7d3085c752f340ffe2754d90ada432edd`, matching the case study |
| 9 | `https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified` (dataset page, implied by the case study's dataset citation) | 200 | 519,181 B | Dataset page HTML |
| 10 | `https://raw.githubusercontent.com/m0at/experiments/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514/per_instance_details.json` (NOT printed anywhere in the case study; the actual source of the $0.3205) | 200 | 53,074 B | `django__django-15930`: `{cost: 0.32052914999999993, api_calls: 35, resolved: true}` — agrees with the trajectory's `model_stats` exactly |

No URL is dead, wrong, or login-gated. The URL layer passes. Every failure below is
in the commands, not the links.

## 2. From-scratch run log

What I ran, in order, and what happened. "As written" means the literal case-study
text; "corrected" means the command this review supplies in §3.

### 2.1 Clone as written — FAILED (killed after 13 min 20 s, incomplete)

```
cd /tmp/repro-cs1
git clone https://github.com/django/django.git django-base
```

Still downloading after 13 min 20 s at 225 MB (`.git` only, no checkout yet);
`/tmp` (512 MB tmpfs) was 89% full with 58 MB free — before any venv existed.
Killed with SIGTERM. The full clone is what the case study's next line makes
unnecessary: it immediately shallow-fetches the one commit it needs. See D7.

### 2.2 Shallow checkout (corrected) — OK, 59 s, 68 MB

```
mkdir -p /tmp/repro-cs1/django-base && cd /tmp/repro-cs1/django-base
git init -q . && git remote add origin https://github.com/django/django.git
git fetch --depth 1 origin 63884829acd207404f2a5c3cc1d6b4cd0a822b70   # exit 0, 59 s
git checkout -q FETCH_HEAD                                          # exit 0
git rev-parse HEAD  # 63884829acd207404f2a5c3cc1d6b4cd0a822b70
git log --oneline -1  # 6388482 Fixed #33902 -- Fixed Meta.constraints validation crash with F() expressions.
```

This proves GitHub allows fetching this exact SHA with `--depth 1`. The case
study's `git fetch --depth 1 origin <sha>` / `git checkout FETCH_HEAD` lines are
themselves correct — only the preceding full `git clone` is the problem.

### 2.3 Venv and install as written — OK

```
python3 -m venv ../django-venv
../django-venv/bin/pip install asgiref sqlparse pytest
../django-venv/bin/pip install -e .
../django-venv/bin/python -c "import django; print(django.__version__)"  # Django 4.2.dev20220809040848
```

No issues. (Note: `pip install -e .` must run from inside `django-base`; the
case study implies this via the earlier `cd` but never states it for this block.)

### 2.4 Test patch as written — FAILED (exit 128)

The case study's curl saves the Parquet file under the name `/tmp/test-patch.diff`,
then says "Extract it with Python (`pyarrow` reads the file) and apply it:"
`git apply /tmp/test-patch.diff`. There is no extraction command, so the literal
next step is:

```
git apply --check /tmp/test-patch.diff   # the downloaded parquet file
# error: git diff header lacks filename information when removing 1 leading pathname component (line 1440)
# exit 128
```

`file` confirms the download is `Apache Parquet`, not a diff. A reader cannot do
this step as written. See D1. Also `pyarrow` is not installed anywhere on this
machine (see D8).

### 2.5 Test patch extraction (corrected) — OK

Installed `pyarrow` into a throwaway venv and extracted with the command in §3
(D1 fix). Result: 500 rows, exactly 1 matching `django__django-15930`,
`base_commit` matches, `FAIL_TO_PASS` = 1 test
(`test_annotate_with_full_when (expressions_case.tests.CaseExpressionTests)`),
`test_patch` 902 chars, byte-identical to the case-study dir's saved
`swebench-test-patch-django-15930.diff`; `patch` (gold) byte-identical to the
saved gold patch. Applied cleanly:

```
git apply /tmp/test-patch.diff   # TEST PATCH APPLIED OK
git status --porcelain           # M tests/expressions_case/tests.py (10 insertions)
```

### 2.6 Target test WITHOUT agent patch — FAILS exactly as claimed

```
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
# django.db.utils.OperationalError: near "THEN": syntax error
# Ran 1 test in 0.008s / FAILED (errors=1) / exit 1
```

Discrimination confirmed: the check fails on the broken code.

### 2.7 Submission as written — FAILED (exit 128)

The case study curls the trajectory JSON to `/tmp/submission.diff`, says "The
submission is the `info.submission` field of that JSON file. Extract it and add
one trailing newline, then apply it:", and gives only:

```
printf '\n' >> /tmp/submission.diff
git apply /tmp/submission.diff
```

There is no extraction command, so literally the `printf` appends a newline to
the **JSON file**, and `git apply` is run against JSON:

```
git apply --check /tmp/submission-as-written.diff
# error: No valid patches in input (allow with "--allow-empty")
# exit 128
```

A reader cannot do this step as written. See D2.

### 2.8 Submission extraction (corrected) — OK

Extraction with the §3 (D2 fix) command: `info.submission` written out (747
chars), one newline appended → 748 bytes, equal to the evaluation's `patch.diff`
+ `"\n"`. Applied cleanly:

```
git apply /tmp/submission.diff   # SUBMISSION APPLIED OK
git status --porcelain           # M django/db/models/expressions.py, M tests/expressions_case/tests.py
git diff --stat                  # 2 files changed, 14 insertions(+) — matches trace-selection.md exactly
```

The applied diff is the 4-line `1=1` patch in `When.as_sql()` plus the test patch.
Also verified the case study's quirk claim directly:

```
git apply --check /tmp/submission-raw.diff   # raw 747-byte submission, no newline
# error: corrupt patch at line 15 / exit 128
patch --dry-run -p1 < /tmp/submission-raw.diff
# patch unexpectedly ends in middle of line / Hunk #1 succeeded at 1299 with fuzz 1. / exit 0
```

### 2.9 Both runtests commands WITH agent patch — PASS, exactly as claimed

```
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
# Ran 1 test in 0.007s / OK / exit 0

../django-venv/bin/python tests/runtests.py expressions_case -v 0
# Ran 89 tests in 0.156s / OK (skipped=1) / exit 0
```

### 2.10 Revert and re-run — FAILS again, exactly as claimed

```
git checkout django/db/models/expressions.py   # AGENT PATCH REVERTED
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
# Ran 1 test in 0.008s / FAILED (errors=1) / exit 1
```

(The revert command works on git 2.43.0, though `git checkout <path>` for
reverting is deprecated syntax; see D11.)

### 2.11 Meter command as written — FAILED (`ModuleNotFoundError`)

```
python3 -m averth.cli trace trace-events-django-15930.jsonl --format jsonl
# /usr/bin/python3: Error while finding module specification for 'averth.cli'
# (ModuleNotFoundError: No module named 'averth')
```

No install step, no working directory, and no pointer to where
`trace-events-django-15930.jsonl` comes from (it lives in the case-study
directory, not in the Averth repo). See D3.

### 2.12 Meter command (corrected) — OK, reproduces exactly

After `pip install -e` of the Averth checkout into a venv and copying the trace
file into the working directory, the same command prints: Attempts 1, Autonomous
completions 1 (100.0%), Reopened 0, Human escalations 0, Retries 0, Model/API
$0.91, Retry path $0.00, Tool calls $0.07, Fully loaded $0.98, context
compounding 9.9x / context tax $0.68 (75% of model spend), yield 100%, p50/p95/max
$0.98. The HTML report it writes is **byte-identical** to the saved
`trace-events-django-15930.html` (8,720 bytes, `diff` clean).

### 2.13 V0 run as written — NOT RUNNABLE (no command given)

The paragraph says "run the verifier with the checks file, allowlist, and trace
events saved with this case study" but names no program, no flags, no working
directory, no install step, and no `--final-edit-marker` value. There is nothing
to execute. See D4. The actual CLI (found by reading the cloned repo) is
`evidence-v0/cli.py` with `--repo --checks --allowlist --execute --python
--trace --final-edit-marker --out --report-id`.

### 2.14 V0 run (corrected) — verdicts reproduce; digests do not

Re-applied the agent patch, rewrote the checks/allowlist with `/tmp` paths
(the originals embed absolute `/home/hatch/...` paths — see D5), and ran:

```
cd /tmp/repro-cs1/averth/evidence-v0
python3 cli.py --repo /tmp/repro-cs1/django-base \
  --checks /tmp/repro-cs1/checks-repro.json \
  --allowlist /tmp/repro-cs1/allowlist-repro.json --execute \
  --python /tmp/repro-cs1/django-venv/bin/python \
  --trace /tmp/repro-cs1/meter/trace-events-django-15930.jsonl \
  --final-edit-marker 2026-11-11T05:09:49+00:00 \
  --out /tmp/repro-cs1/v0-run --report-id v0-case-study-1-repro
# counts: {'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}, unknown rate: 0.5, runs: 2 (0 superseded)
```

Verdicts match the published report exactly (C1, C2 VERIFIED, Tier 2,
`after_final_edit: True`, exit 0; C3, C4 EXTERNAL-UNVERIFIABLE). But:

- Checks digest: mine `sha256:8ff99a73…` vs published `sha256:6dde8826…` —
  differs because the checks file's `required_command` paths had to change.
- Run output digests: mine C1 `sha256:058a8cb8…`, C2 `sha256:f113b634…` vs
  published C1 `sha256:081dd9cc…`, C2 `sha256:498fa2e3…` — differ because the
  hashed output embeds the wall-clock line `Ran N tests in Xs`. See D6.

### 2.15 Digest lottery (quantified)

Ran each runtests command 8 times, hashing `stdout + stderr` exactly as V0 does:

- C1: timing was `0.007s` in 7/8 runs (once `0.006s`). Digest matched the
  published `081dd9cc…` in **7/8** runs. (My V0 run's C1 happened to land on a
  non-`0.007s` timing, hence its different digest — while a manual run seconds
  later hashed exactly to the published digest.)
- C2: timings `0.146s`–`0.158s` across the 8 runs, 7 distinct digests. Digest
  matched the published `498fa2e3…` in **1/8** runs (the run that happened to
  take `0.152s`).

So the C2 cited digest is a timing lottery a reproducer will usually lose, and
even the C1 digest is not guaranteed. The verdicts and test counts reproduce;
the digests usually do not.

## 3. Defects and exact fixes

Severity: BLOCKER = the step cannot be completed as written; MAJOR = it
completes but the result cannot be checked as stated, or it wastes an
unreasonable amount of time/disk; MINOR = wording, missing context, or a
paper cut a careful reader can work around.

### D1 — BLOCKER: test-patch extraction command is missing; `git apply` is aimed at a Parquet file

- File: `case-study-1.md`, section "Reproduction steps".
- Wrong text: the curl saves the Parquet download as `/tmp/test-patch.diff`,
  followed by "The test patch is inside that parquet file, instance
  `django__django-15930`, field `test_patch`. Extract it with Python
  (`pyarrow` reads the file) and apply it:" and then
  `git apply /tmp/test-patch.diff`.
- What happens: `git apply` on the Parquet file fails, exit 128
  ("git diff header lacks filename information… (line 1440)"). No extraction
  command exists anywhere in the section.
- Fix: name the download for what it is, add the install step, and give the
  extraction command. Replace the block with:

```bash
curl -sL -o /tmp/swebench-verified.parquet \
  "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet"
../django-venv/bin/pip install pyarrow
../django-venv/bin/python - <<'EOF'
import pyarrow.parquet as pq
t = pq.read_table('/tmp/swebench-verified.parquet')
row = [r for r in t.to_pylist() if r['instance_id'] == 'django__django-15930'][0]
assert row['base_commit'] == '63884829acd207404f2a5c3cc1d6b4cd0a822b70'
open('/tmp/test-patch.diff', 'w').write(row['test_patch'])
print('FAIL_TO_PASS:', row['FAIL_TO_PASS'])
EOF
git apply /tmp/test-patch.diff
```

  Notes for the fix text: (a) install `pyarrow` inside the venv, not system
  Python (see D8); (b) `pyarrow` returns `FAIL_TO_PASS`/`PASS_TO_PASS` as
  stringified lists, so a reader who prints them sees one long string — the
  minimal extraction above only needs `test_patch`, which is a plain string.

### D2 — BLOCKER: submission extraction command is missing; the newline is appended to the JSON file

- File: `case-study-1.md`, section "Reproduction steps".
- Wrong text: the curl saves the trajectory JSON as `/tmp/submission.diff`,
  followed by "The submission is the `info.submission` field of that JSON
  file. Extract it and add one trailing newline, then apply it:" and then
  `printf '\n' >> /tmp/submission.diff` / `git apply /tmp/submission.diff`.
- What happens: the `printf` appends a newline to the **JSON file** (which
  already ends in a newline anyway), and `git apply` on JSON fails, exit 128
  ("error: No valid patches in input"). No extraction command exists.
- Fix: name the download for what it is and give the extraction command.
  Replace the block with:

```bash
curl -sL -o /tmp/django-15930.traj.json \
  "https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json"
python3 - <<'EOF'
import json
traj = json.load(open('/tmp/django-15930.traj.json'))
open('/tmp/submission.diff', 'w').write(traj['info']['submission'])
EOF
printf '\n' >> /tmp/submission.diff
git apply /tmp/submission.diff
```

  (Stdlib `json` only — no new dependency. The `printf` line is then correct
  because it now targets the extracted patch, not the JSON.)

### D3 — BLOCKER: meter command fails as written (`ModuleNotFoundError`); install, cwd, and trace-file provenance all missing

- File: `case-study-1.md`, section "Reproduction steps" (meter paragraph).
- Wrong text: `python -m averth.cli trace trace-events-django-15930.jsonl --format jsonl`
  with no preceding install step, no working directory, and no statement of
  where `trace-events-django-15930.jsonl` comes from.
- What happens: `ModuleNotFoundError: No module named 'averth'` (verified
  §2.11). The trace file is in the case-study directory, not in the Averth
  repo, so even an installed Averth cannot find it from an arbitrary cwd.
- Fix: add the setup before the command (after the V0 clone step, or as its own
  block):

```bash
git clone https://github.com/Wesley3141/Averth.git averth
cd averth
python3 -m venv ../averth-venv
../averth-venv/bin/pip install -e .
cp /path/to/case-study-1/trace-events-django-15930.jsonl .
../averth-venv/bin/python -m averth.cli trace trace-events-django-15930.jsonl --format jsonl
```

  And state that the command writes `trace-events-django-15930.html` next to
  the input file (it does; the saved HTML in the case-study dir is byte-identical
  to a fresh run's output, verified by `diff`).

### D4 — BLOCKER: the V0 paragraph gives no executable command

- File: `case-study-1.md`, section "Reproduction steps" (V0 paragraph).
- Wrong text: "To reproduce the V0 run itself, clone
  https://github.com/Wesley3141/Averth, check out branch
  `criterion-c-checks-digest`, and run the verifier with the checks file,
  allowlist, and trace events saved with this case study."
- What happens: there is no program name, no flags, no working directory, no
  install step, and no `--final-edit-marker` value. Nothing in the case study
  (or in the linked `v0-run/evidence_report.md`, which does not record the
  invocation) tells the reader how the run was produced. I had to read
  `evidence-v0/cli.py` in the cloned repo to reconstruct it.
- Fix: give the full command that reproduces the published verdicts (verified
  §2.14), with the repo-state precondition stated:

```bash
git clone https://github.com/Wesley3141/Averth.git averth
cd averth && git checkout criterion-c-checks-digest   # HEAD 8ec848b
# From the averth checkout, with the Django repo at the base commit + test
# patch + agent patch applied, and the checks/allowlist files rewritten to
# your venv path (see D5). --final-edit-marker must be a timestamp AFTER
# the last edit to the Django checkout, or the runs are recorded superseded.
cd averth/evidence-v0
python3 cli.py --repo /path/to/django-base \
  --checks /path/to/case-study-1-checks.json \
  --allowlist /path/to/case-study-1-allowlist.json --execute \
  --python /path/to/django-venv/bin/python \
  --trace /path/to/trace-events-django-15930.jsonl \
  --final-edit-marker <ISO-8601 timestamp after your last repo edit> \
  --out ./v0-run-repro --report-id v0-case-study-1-repro
```

  Note: `cli.py` runs from the `evidence-v0` directory (it inserts its own
  directory on `sys.path`); there is no install step strictly required for
  this path, but the `INSTALL.md` `pip install ./evidence-v0` /
  `averth-evidence` console-script path exists and was not tested in this
  review.

### D5 — MAJOR: checks and allowlist files embed absolute `/home/hatch/...` paths; any reproducer must rewrite them, which changes the checks digest

- Files: `case-study-1-checks.json`, `case-study-1-allowlist.json`
  (referenced by `case-study-1.md`, "Files" section).
- Wrong text: `required_command` /
  `command` / `runner` values are absolute paths under
  `/home/hatch/workspace/averth/case-study-1/django-venv/bin/python`.
  Those paths do not exist on any other machine (or in any other checkout
  directory on this machine).
- What happens: the files are unusable as-is; the reader must rewrite every
  command to their own venv path. Doing so changes the checks digest: my run's
  digest was `sha256:8ff99a73ec800a53f2b0e71fc0fb1ca4622f7e18a720ff985dadd8adbbf51571`
  vs the published `sha256:6dde8826cdd36df16d9a33464d847b2bd3da47e16055ed809a52202011d79739`
  — the only difference between the two files was the venv path.
- Fix: either (a) make the checks/allowlist paths relative or templated
  (e.g. a `{VENV}` placeholder the reader substitutes, with the substitution
  documented), or (b) keep the files as-is and state in the case study that
  the checks digest is path-bound and a reproducer's digest will differ, and
  that the comparable outputs are the verdicts, coverage, and exit codes —
  not the digest. Option (b) is the smaller fix; option (a) is the better one.

### D6 — MAJOR: the cited run output digests embed wall-clock timing and usually do not reproduce

- File: `case-study-1.md`, "What V0 verified" table (C1, C2 rows).
- Wrong text (by omission): the table cites `output_digest
  sha256:081dd9cc…` (C1) and `sha256:498fa2e3…` (C2) as the evidence for the
  VERIFIED rows, with no warning that the digest is over output containing
  Django's `Ran N tests in Xs` timing line.
- What happens: V0 hashes `stdout + stderr` verbatim, and the timing varies
  run to run. Measured over 8 runs each: C1's digest matched the published
  value in 7/8 runs (timing usually `0.007s`, once `0.006s`); C2's matched in
  **1/8** runs (timings `0.146s`–`0.158s`, 7 distinct digests). My own V0
  run's digests (`058a8cb8…` / `f113b634…`) matched neither published value,
  even though both runs exited 0 with identical test outcomes — and a manual
  run minutes later hashed exactly to the published C1 digest.
- Fix: add one sentence to the "What V0 verified" section and to the
  reproduction steps: "The output digests embed Django's run-time line
  (`Ran 89 tests in 0.152s`), so a reproducer's digests will usually differ
  for C2; compare exit codes (0), test counts (1 test OK; 89 tests OK,
  skipped=1), and verdicts, not digests." Longer-term fix (for the tool, not
  this case study): normalize or strip the timing line before hashing.

### D7 — MAJOR: the full `git clone` is needlessly slow and large, and does not fit the task's `/tmp` budget

- File: `case-study-1.md`, section "Reproduction steps".
- Wrong text: `git clone https://github.com/django/django.git django-base`
  followed by `git fetch --depth 1 origin <sha>` / `git checkout FETCH_HEAD`.
- What happens: the full clone downloads the entire Django history. On this
  machine it ran 13 min 20 s, reached 225 MB (`.git` only, no checkout yet),
  and filled the 512 MB `/tmp` tmpfs to 89% (58 MB free) before any venv
  existed — I killed it incomplete. The very next line shallow-fetches the
  single commit the run needs, so the full history is pure waste.
- Fix: replace the three lines with the shallow-only checkout (verified §2.2:
  59 s, 68 MB total, correct HEAD):

```bash
mkdir django-base && cd django-base
git init -q . && git remote add origin https://github.com/django/django.git
git fetch --depth 1 origin 63884829acd207404f2a5c3cc1d6b4cd0a822b70
git checkout FETCH_HEAD
```

  (On a machine with a large disk and fast network the full clone works, but
  it is still ~4x the download and ~13x the time for zero benefit. The shallow
  form is strictly better and is what the steps already imply.)

### D8 — MINOR: `pyarrow` is not installed, and installing it into system Python breaks pandas

- File: `case-study-1.md`, section "Reproduction steps" ("Extract it with
  Python (`pyarrow` reads the file)").
- What happens: this machine has no `pyarrow` (system Python 3.12.3 has pandas
  2.1.4 but no pyarrow). `pip install pyarrow` today installs pyarrow 26.0.1,
  which requires NumPy ≥ 2.0; installing that into system Python shadows the
  system NumPy 1.26.4 and breaks the system pandas with
  `ValueError: numpy.dtype size changed, may indicate binary incompatibility`
  (reproduced). In a clean venv `pip install pyarrow` pulls a matching NumPy
  and works — which is why the D1 fix installs it into `django-venv`.
- Fix: fold into the D1 fix — install `pyarrow` inside the venv, never system
  Python. One line: `../django-venv/bin/pip install pyarrow`.

### D9 — MINOR: misleading filenames and unstated working directory

- File: `case-study-1.md`, section "Reproduction steps".
- Wrong text: (a) the Parquet download is saved as `/tmp/test-patch.diff` and
  the trajectory JSON as `/tmp/submission.diff` — both names lie about the
  file contents, which is part of why D1/D2 fail silently confusingly;
  (b) `git apply …` must run inside `django-base`, but the section states the
  working directory only for the `runtests.py` commands ("from the
  `django-base` directory"), several commands after the `cd django-base`.
  A reader running the curl/apply block in a second shell fails.
- Fix: use the D1/D2 filenames (`/tmp/swebench-verified.parquet`,
  `/tmp/django-15930.traj.json`, `/tmp/test-patch.diff`,
  `/tmp/submission.diff` for the real diffs) and add "run all `git apply` and
  `runtests.py` commands from inside `django-base`" at the top of the section.

### D10 — MINOR: the recorded $0.3205 has no direct URL in the case study

- File: `case-study-1.md`, sections "The run" / "What the run cost" and
  "Reproduction steps" (meter paragraph).
- Wrong text (by omission): the $0.3205 is attributed to "the leaderboard
  entry's `per_instance_details.json`", but the only leaderboard URL given is
  a GitHub tree page (HTML directory listing). A reader must click through
  the tree to find the file.
- Fix: add the direct raw URL next to the leaderboard link:
  `https://raw.githubusercontent.com/m0at/experiments/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514/per_instance_details.json`
  (verified HTTP 200; the instance row is `{cost: 0.32052914999999993,
  api_calls: 35, resolved: true}`).

### D11 — MINOR: prerequisites and revert-command wording

- File: `case-study-1.md`, section "Reproduction steps".
- Wrong text: "You need Python 3.12, git, and internet access" — the steps
  also need `python3-venv`/`pip` (for `python3 -m venv`), `curl`, and GNU
  `patch` if the reader takes the fuzz route. On this machine all were
  present; on a bare Python install `python3 -m venv` fails without the
  venv package. Also "revert the agent patch first (`git checkout
  django/db/models/expressions.py`)" works (git 2.43.0, verified) but
  `git checkout <path>` for reverting is deprecated syntax and silently
  discards *any* uncommitted change to that file, not just the agent patch.
- Fix: extend the prerequisites line to "Python 3.12 (with `venv` and `pip`),
  git, curl, and internet access", and prefer
  `git restore django/db/models/expressions.py` (or note that the checkout
  form reverts all uncommitted changes to that file). Also state that
  `git checkout FETCH_HEAD` leaves a detached HEAD — expected, not an error.

### D12 — MINOR: the meter's "expected output" does not match the tool's actual wording

- File: `case-study-1.md`, section "Reproduction steps" (meter paragraph).
- Wrong text: "Expected meter output: 1 attempt, 1 trace-labelled completion,
  0 retries, fully loaded $0.98 ESTIMATED."
- What happens: the actual stdout (verified §2.12) says "Autonomous
  completions: 1 (100.0%)" (not "trace-labelled completion"), prints
  "Fully loaded: $0.98" with no "ESTIMATED" label anywhere, and labels the
  $0.91 "Priced (vendor prices on recorded tokens…)" even though the case
  study's own cost section says the trace's token counts are estimates
  (characters/4). The ESTIMATED framing exists only in the case study's
  prose, not in the tool output a reader will see.
- Fix: quote the tool's actual lines ("Attempts: 1", "Autonomous completions:
  1", "Retries: 0", "Fully loaded: $0.98") and add: "the tool labels the
  $0.91 'Priced' because it applies vendor list prices; the underlying token
  counts are trace estimates (characters/4), so treat the $0.98 as an
  estimate, as the cost section states."

### D13 — MINOR (V0): the `--final-edit-marker` value and required repo state are unstated

- File: `case-study-1.md`, section "Reproduction steps" (V0 paragraph).
- Wrong text (by omission): nothing says the V0 run must execute with the
  agent patch applied, nor what final-edit marker to pass. The original
  marker (`2026-11-11T04:50:39+00:00`, from the saved report) is not printed
  in the case study.
- What happens: a reader who runs V0 before applying the patch, or with a
  marker predating their last edit, gets superseded runs / FAILED checks
  instead of the published VERIFIED rows, with no explanation in the case
  study of why.
- Fix: fold into the D4 fix — state the precondition ("Django checkout with
  test patch and agent patch applied; run V0 last") and that the marker must
  be an ISO-8601 timestamp after the last edit to the checkout.

### D14 — NOTE (not a defect): pyarrow returns the test lists as strings

- For the record: `pyarrow` reads `FAIL_TO_PASS`/`PASS_TO_PASS` as one long
  string each (the stringified list; `PASS_TO_PASS` is 6,765 chars), not as
  lists — the saved `swebench-row-django-15930.json` has them as real lists
  (88 entries, matching `report.json`). The minimal extraction in D1 is
  unaffected (`test_patch` is a plain string), but any reader code that does
  `len(row['PASS_TO_PASS'])` gets 6765, not 88. Use `ast.literal_eval` if the
  lists are needed.

## 4. What verified cleanly (no fix needed)

- All 9 case-study URLs return HTTP 200 with the claimed content; the
  trajectory, parquet, `report.json`, `test_output.txt`, and `patch.diff`
  are byte-identical to the copies saved with the case study.
- `report.json`: resolved true, FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88.
- `per_instance_details.json` cost `0.32052914999999993` agrees exactly with
  the trajectory's `model_stats.instance_cost`; `api_calls` 35 agrees.
- Trajectory: 72 messages (1 system, 35 assistant, 36 user).
- Base commit `63884829…` fetches by SHA and checks out correctly.
- Venv + `asgiref`/`sqlparse`/`pytest` + `pip install -e .` works as written;
  Django `4.2.dev20220809040848`.
- Test patch applies cleanly; working tree after both patches is exactly
  2 files, 14 insertions.
- Target test fails without the patch (`OperationalError: near "THEN": syntax
  error`, exit 1), passes with it (exit 0), fails again after revert.
- Module run: `Ran 89 tests … OK (skipped=1)`, exit 0.
- Raw submission rejected by strict `git apply` ("corrupt patch at line 15",
  exit 128); GNU patch applies it with fuzz 1; `+ "\n"` makes `git apply`
  accept it; applied diff is byte-identical to the recorded submission apart
  from that newline.
- Meter (once installed): every figure in the case study reproduces
  ($0.98 fully loaded, $0.91 model, $0.07 tool, 9.9x context growth,
  $0.68 context tax, 100% yield, 0 retries); the HTML report is byte-identical
  to the saved one.
- V0 (once the real command is reconstructed): verdicts, coverage (2 VERIFIED,
  2 EXTERNAL-UNVERIFIABLE, unknown rate 50%), run count (2), Tier 2, and
  `after_final_edit` all reproduce.
- Averth branch `criterion-c-checks-digest` exists at the stated commit
  `8ec848b`.

## 5. What was not tested

- No second database backend (out of scope; C4 is already
  EXTERNAL-UNVERIFIABLE and the case study states this).
- No human review (out of scope; C3 is already EXTERNAL-UNVERIFIABLE).
- The `pip install ./evidence-v0` / `averth-evidence` console-script install
  path from `INSTALL.md` (I ran `evidence-v0/cli.py` directly).
- The full `git clone` to completion (killed at 13 min 20 s / 225 MB; on a
  large disk with fast network it would presumably finish, but the shallow
  form makes the question moot).

## 6. Suggested corrected reproduction section (summary)

Replace the current "Reproduction steps" with the D7 shallow checkout, the D1
extraction block, the D2 extraction block, the two `runtests.py` commands
unchanged, the revert check unchanged, and the D4 V0 command plus the D3 meter
setup. Add the D5/D6/D13 caveats (path-bound checks digest; timing-fragile
output digests; marker must postdate the last edit) and the D10 raw URL for
`per_instance_details.json`. With those changes, a reader can reproduce every
number in the case study from the URLs alone; as written, they cannot get past
the test patch.

## Appendix: corrected full run (condensed, as executed)

```bash
mkdir -p /tmp/repro && cd /tmp/repro
git init -q django-base && cd django-base
git remote add origin https://github.com/django/django.git
git fetch --depth 1 origin 63884829acd207404f2a5c3cc1d6b4cd0a822b70
git checkout FETCH_HEAD
python3 -m venv ../django-venv
../django-venv/bin/pip install asgiref sqlparse pytest
../django-venv/bin/pip install -e .
curl -sL -o /tmp/swebench-verified.parquet \
  "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet"
../django-venv/bin/pip install pyarrow
../django-venv/bin/python -c "
import pyarrow.parquet as pq
t = pq.read_table('/tmp/swebench-verified.parquet')
row = [r for r in t.to_pylist() if r['instance_id'] == 'django__django-15930'][0]
open('/tmp/test-patch.diff', 'w').write(row['test_patch'])"
git apply /tmp/test-patch.diff
curl -sL -o /tmp/django-15930.traj.json \
  "https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json"
python3 -c "
import json
open('/tmp/submission.diff', 'w').write(json.load(open('/tmp/django-15930.traj.json'))['info']['submission'])"
printf '\n' >> /tmp/submission.diff
git apply /tmp/submission.diff
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0  # expect OK
../django-venv/bin/python tests/runtests.py expressions_case -v 0               # expect 89 tests OK (skipped=1)
git checkout django/db/models/expressions.py
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0  # expect FAILED, near "THEN"
```
