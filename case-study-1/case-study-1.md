# Case study 1: one public coding-agent run, two checks verified, two unverifiable

This is one public trace, not a benchmark and not a product claim. It shows what
Averth actually does on a real agent run: the V0 verifier judges human-written
checks against recorded evidence, and the meter estimates what the run cost, with
every dollar labeled by provenance. The V0 and meter numbers below come from the
V0 ledger and the meter output saved with this case study; run counts come from
the raw trajectory, the $0.3205 recorded cost comes from the leaderboard entry's
per_instance_details.json, and the 3.84x comparison comes from the 12-run
mini-SWE-agent findings note. Nothing here is a customer, a deployment, or a
validation of Averth on a live workflow.

## The run

- Agent: mini-SWE-agent v1.0.0 (bash-only harness), model
  `claude-sonnet-4-20250514`.
- Task: SWE-bench Verified instance `django__django-15930`. Django `Case()`
  crashes with `~Q(pk__in=[])`. The generated SQL reads
  `CASE WHEN THEN true ...`, a syntax error. The fix must make an empty `When`
  condition behave as always true.
- The run: 72 messages (1 system, 35 assistant, 36 user), 35 API calls, 35
  tool calls, 0 observed tool failures (34 tool results recorded, all exit 0),
  0 retries. The agent submitted a 4-line patch
  to `django/db/models/expressions.py`: if the compiled condition is empty,
  use the SQL literal `1=1`.
- Official outcome: RESOLVED. The official evaluation record (`report.json`)
  records FAIL_TO_PASS 1/1 and PASS_TO_PASS 88/88 for this run.
- Recorded cost: $0.3205, from the leaderboard entry's per-instance record.
  The trajectory's own `model_stats` record agrees exactly
  (`instance_cost: 0.32052914999999993`, `api_calls: 35`).

## Where the trace lives

- Trajectory (raw `.traj.json`, public S3, no login):
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json
- Leaderboard entry:
  https://github.com/m0at/experiments/tree/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514
- Recorded cost, API calls, and resolved flag, direct file:
  https://raw.githubusercontent.com/m0at/experiments/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514/per_instance_details.json
- Official evaluation records for this instance:
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/report.json
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/test_output.txt
- Task definition (base commit, test patch, test lists): Hugging Face dataset
  `princeton-nlp/SWE-bench_Verified`, instance `django__django-15930`, repo
  `django/django`, base commit `63884829acd207404f2a5c3cc1d6b4cd0a822b70`.
- Subject repo: https://github.com/django/django

## What V0 verified

V0 ran in executed mode (Tier 2): it ran the checks itself in the repo and
recorded each run with command, timestamps, exit code, and output digest.
The verifier used here is the `criterion-c-checks-digest` branch
(commit 8ec848b), not master, per the operator's record in
`verifier-version.txt`; the ledger itself carries no verifier version field.
That branch freezes the checks file at load
(digest `sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`)
and refuses to run if the checks are edited mid-run. The checks and allowlist
use bare `python` as the runner, so the files are byte-identical on any
machine with the Django venv on PATH, and the digest above reproduces from
the saved checks file.

| Check | Result | Evidence |
| --- | --- | --- |
| C1: the FAIL_TO_PASS test passes with the agent patch | VERIFIED | Run exit 0, output digest `sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3`, Tier 2, after final edit |
| C2: the PASS_TO_PASS tests still pass with the agent patch | VERIFIED | Run exit 0, output digest `sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b`, Tier 2, after final edit |
| C3: an independent human reviewed and accepted this run | EXTERNAL-UNVERIFIABLE | No human reviewed this run. No confirmation record exists. |
| C4: the fix is verified on a second database backend besides SQLite | EXTERNAL-UNVERIFIABLE | The recorded runs used SQLite in memory only. No second backend was run. |

Coverage: 4 checks, 2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE. Unknown
rate 50.0%. Runs recorded: 2, of which superseded and retained, never cited: 0.

The output digests are over output that includes Django's run-time line
(`Ran 89 tests in 0.168s`), so a reproducer's digests will usually differ
for C2; compare exit codes (0), test counts (1 test OK; 89 tests OK,
skipped=1), and verdicts, not digests.

A VERIFIED row proves only what its cited observation shows. C1 proves the
one target test passes on this revision with this patch, on SQLite. C2 proves
the `expressions_case` module is green on SQLite on this revision (89 tests
ran, OK, 1 skipped). Neither proves the fix is correct in general, on other
database backends, or beyond the named assertions.

## What failed

No V0 check failed. Three failures are on the record around this run, and
each matters for a different reason.

1. The target test fails without the patch. Before the agent patch was
   applied, the same test failed with `OperationalError: near "THEN": syntax
   error`, exactly the reported bug. That run is saved as
   `baseline-pre-patch-run.txt`. The check discriminates: it fails on the
   broken code and passes on the fixed code. A check that passes either way
   proves nothing.
2. The recorded submission fails strict `git apply`. The patch as recorded in
   the trajectory (and in the evaluation's saved `patch.diff`, byte-identical,
   747 bytes) is missing its final newline, so `git apply` rejects it as
   "corrupt patch at line 15". GNU patch applies it with fuzz 1. Appending
   one newline makes `git apply` accept it cleanly, and the applied file
   matches the submission's intended content exactly. The regenerated git diff
   differs from the recorded patch only in the abbreviated index hashes and
   the trailing newline. The code change is intact; the recorded artifact is
   one byte short. The reproduction steps below include the newline.
3. Two things were not done, and V0 says so instead of passing them. No human
   reviewed or accepted this run (C3), and no second database backend was run
   (C4). Both are EXTERNAL-UNVERIFIABLE, which is why the unknown rate is
   50%. A report that called this run "fully verified" would be overstating
   it.

## What was not observed

- No human acceptance. Recorded test verdicts are evidence, not human
  acceptance. Do not cite this case study as a human accepting the agent's
  work.
- No second database backend. The agent patch hardcodes the SQL literal
  `1=1`. It passes on SQLite. PostgreSQL, MySQL, and Oracle were not run.
- No retries. The run recorded 0 observed tool failures (34 tool results
  recorded, all exit 0) and 0 retries, so there is no retry cost to report
  and no retry loop to diagnose. The meter's retry path is $0.00 because
  nothing was retried, not because retries are free.
- No other module was run. C2 covers the `expressions_case` module only. A
  regression in another Django module would not show up here.
- No cost was measured from the provider. The trace records no token cache
  counts and no bill. See the cost section for what that means.

## What the run cost

The meter ran on the single-case trace events (71 events: 35 model, 35 tool,
1 end). The $0.98 total below is ESTIMATED overall, not measured spend and not
a bill. Within it, $0.91 is priced (vendor list prices on trace-supplied token
counts Averth does not verify) and $0.07 is estimated (built-in per-call tool
estimates). The trace's token counts are themselves estimates (characters/4),
and the trace records no prompt-cache counts.

- Attempts: 1. Autonomous completions: 1. Human escalations: 0.
  Retries: 0.
- Fully loaded cost per completed run: $0.98 ESTIMATED
  ($0.91 priced model spend + $0.07 estimated tool spend).
- Recorded cost for the same run: $0.3205, from the leaderboard entry.
  Metered estimate divided by recorded cost: 3.07x ($0.9832 unrounded /
  $0.3205).
- Context compounding: 9.9x input growth from first to last step. Context
  tax: $0.68, which is 75% of the model spend. Input token counts grow
  monotonically from first to last step, consistent with the run re-sending
  the growing history on every call, and the meter prices those resends at
  list rate.
- Yield: 100% of tokens on the terminal path. Nothing was burned on retries
  or failed runs.
- Provenance of the $0.98: $0.91 priced (vendor list prices on trace-supplied
  token counts), $0.07 estimated (built-in per-call tool estimates),
  $0.00 billed (no invoice data in the trace).

Why the meter says $0.98 and the record says $0.3205: the trace records no
prompt-cache counts, so the meter prices full-history resends at list rate.
The recorded cost is consistent with heavy prompt caching (the same gap was
3.84x across 12 runs from this leaderboard entry). The gap also includes error
from the trace's chars/4 token estimates, and the cache share cannot be
isolated from this trace. The honest statement is that the run cost $0.3205
recorded, and that a meter working from this trace alone would estimate
$0.98. Averth does not claim the $0.98 is the bill. Reconcile against the
invoice before calling any metered figure actual spend.

Cost per completed run: the run completed once with the target test and the
module green (C1 and C2 VERIFIED), so the estimated cost per completed run is
$0.98, against $0.3205 recorded. No human accepted this run (C3), so no cost
per accepted outcome is claimed. That statement holds for this one run only.
One run does not establish a rate.

## The agent patch vs the gold patch

The agent patch and the gold patch (the fix Django actually merged) differ in
implementation. The agent patch hardcodes `"1=1"`:

```
if not condition_sql:
    condition_sql = "1=1"
    condition_params = []
```

The gold patch compiles `Value(True)` instead:

```
if condition_sql == "":
    condition_sql, condition_params = compiler.compile(Value(True))
```

Both pass the recorded tests: the agent patch under V0 (C1, C2), and the gold
patch in a separate rerun during trace selection (target test passes, module
89 tests OK, 1 skipped, saved as `gold-patch-run.txt`); no V0 run of the gold
patch is recorded in the ledger. The case study does not claim the agent patch
equals the gold patch. The hardcoded literal is a portability question the
recorded tests do not answer, which is the same point as C4.

## How the evidence was collected

1. The trajectory was fetched from the public S3 bucket named above, no
   login. The leaderboard entry's `per_instance_details.json` supplied the
   recorded cost, API calls, and resolved flag. The SWE-bench Verified
   dataset supplied the base commit, the test patch, and the FAIL_TO_PASS and
   PASS_TO_PASS lists.
2. Django was checked out at the base commit. The test patch was applied.
   The target test was run without the agent patch and failed with the
   reported syntax error (saved as `baseline-pre-patch-run.txt`). The agent
   submission was applied (plus one trailing newline, see above). The target
   test was run again and passed. The gold patch was also run in place of the
   agent patch as a cross-check (saved as `gold-patch-run.txt`).
3. V0 ran in executed mode with an operator-written allowlist containing
   exactly the two runtests commands, using bare `python` as the runner so
   the checks file is portable across machines. It recorded both runs itself
   (Tier 2) and judged the four human-written checks. No check was edited
   after the run started; the checks digest is in the ledger. Final-edit
   marker 2026-11-11T05:14:32Z, after the last edit to the checkout. The first
   V0 run used absolute venv paths in the checks file; those files are kept
   as `case-study-1-checks-v1-absolute-paths.json` and
   `case-study-1-allowlist-v1-absolute-paths.json`, and the published run
   uses the portable files.
4. The meter ran read-only on the single-case trace events. No live model
   calls, no credentials, no uploads were involved at any step.

## Reproduction steps

You need Python 3.12 (with `venv` and `pip`), git, curl, and internet access
to the public URLs below. No account, key, or signup is needed anywhere.
Work from an empty directory. Run all `git apply` and `runtests.py` commands
from inside `django-base`.

Check out Django at the base commit. A shallow fetch of the one commit is
all the steps need; a full clone downloads the whole history for no benefit.

```
mkdir django-base && cd django-base
git init -q . && git remote add origin https://github.com/django/django.git
git fetch --depth 1 origin 63884829acd207404f2a5c3cc1d6b4cd0a822b70
git checkout FETCH_HEAD
```

`git checkout FETCH_HEAD` leaves a detached HEAD. That is expected, not an
error. Confirm the checkout with `git rev-parse HEAD`, which must print
`63884829acd207404f2a5c3cc1d6b4cd0a822b70`.

Build the venv and install Django editable from this checkout (from inside
`django-base`):

```
python3 -m venv ../django-venv
../django-venv/bin/pip install asgiref sqlparse pytest
../django-venv/bin/pip install -e .
```

Warning: the venv's editable Django install points at the checkout under
test. If you check out a second copy of Django elsewhere and run it with
this venv, it silently imports the patched Django from this checkout and
gives a false pass. Always run these commands from the `django-base`
directory the venv was installed against, or install a fresh venv per
checkout.

Fetch the task definition and extract the test patch. The download is a
Parquet file, so save it under its real name and extract with Python
(`pyarrow` reads the file; install it inside the venv, never system Python):

```
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

Note: `pyarrow` returns `FAIL_TO_PASS` and `PASS_TO_PASS` as stringified
lists, not lists. The extraction above only needs `test_patch`, which is a
plain string. Use `ast.literal_eval` if the test lists are needed.

Fetch the agent submission and append the missing trailing newline. The
download is a JSON file, so save it under its real name and extract the
`info.submission` field (stdlib `json` only, no new dependency):

```
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

Run the checks (from the `django-base` directory, with the venv Python):

```
../django-venv/bin/python tests/runtests.py \
  expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
../django-venv/bin/python tests/runtests.py expressions_case -v 0
```

Expected: the first command passes (the target test), the second passes (89
tests, 1 skipped). To confirm the check discriminates, revert the agent
patch first (`git restore django/db/models/expressions.py`) and run the
first command again: it fails with `OperationalError: near "THEN": syntax
error`. Re-apply the agent patch before the V0 step below:
`git apply /tmp/submission.diff`.

To reproduce the meter output, clone Averth once, install it in its own
venv, and copy the trace events file saved with this case study
(`trace-events-django-15930.jsonl`) into the checkout. Clone it next to
`django-base`, not inside it: you are still in `django-base` from the test
commands above, so go up one directory first, or V0 will hash the Averth
checkout into the Django repo snapshot.

```
cd ..
git clone https://github.com/Wesley3141/Averth.git averth
cd averth
python3 -m venv ../averth-venv
../averth-venv/bin/pip install -e .
cp /path/to/trace-events-django-15930.jsonl .
../averth-venv/bin/python -m averth.cli trace trace-events-django-15930.jsonl --format jsonl
```

Expected meter output lines: `Attempts: 1`, `Autonomous completions: 1
(100.0%)`, `Retries: 0`, `Fully loaded: $0.98`. The tool labels the $0.91
"Priced" because it applies vendor list prices; the underlying token counts
are trace estimates (characters/4), so treat the $0.98 as an estimate, as the
cost section states. The command writes `trace-events-django-15930.html`
next to the input file; the saved HTML is byte-identical to a fresh run's
output. The recorded $0.3205 comes from the leaderboard entry's
`per_instance_details.json`, not from the meter.

To reproduce the V0 run itself, use the same Averth checkout. You are still
in it from the meter step above. Check out the branch first: master's
verifier has no checks digest, so a run on master cannot reproduce the
ledger. Run V0 last, with the Django checkout at base commit plus test patch
plus agent patch applied. The `--final-edit-marker` must be an ISO-8601
timestamp from just before you run the command, after your last edit to the
checkout. A marker in the future supersedes the runs, and so does a marker
from before your last edit. Our run used marker `2026-11-11T05:14:32Z`. Run
with the Django venv first on PATH, so the bare `python` in the checks
resolves to the venv python:

```
git checkout criterion-c-checks-digest
cd evidence-v0
export PATH=/path/to/django-venv/bin:$PATH
python3 cli.py --repo /path/to/django-base \
  --checks /path/to/case-study-1-checks.json \
  --allowlist /path/to/case-study-1-allowlist.json --execute \
  --python /path/to/django-venv/bin/python \
  --trace /path/to/trace-events-django-15930.jsonl \
  --final-edit-marker <ISO-8601 timestamp from just before the run, after your last repo edit> \
  --out ./v0-run-repro --report-id v0-case-study-1-repro
```

The `--python` flag is unused when an allowlist is given, so it does not
affect the run. The checks and allowlist use
bare `python` as the runner, so the published files work byte-for-byte on any
machine, and the checks digest in the ledger
(`sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`)
reproduces from the saved checks file. Expected V0 output: counts
`{'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 0.5, runs 2
(0 superseded). The run output digests embed Django's run-time line, so a
reproducer's digests will usually differ for C2; compare exit codes (0),
test counts (1 test OK; 89 tests OK, skipped=1), and verdicts, not digests.

## What this does and does not show

V0 does what it says: it judges human-written checks against recorded runs,
freezes the checks so they cannot be edited mid-run, keeps NOT OBSERVED
distinct from a pass, and states its unknown rate up front. On this run it
verified the target test and the module, and it refused to verify the two
things with no evidence behind them.

It does not show that Averth works on a live customer workflow, that the
agent's fix is correct in general, that the meter's estimate equals a bill,
or that one verified run predicts the next. One public trace is one public
trace. The value here is that every number traces to a record you can fetch
yourself, and every gap is stated where it is.

## Files

- V0 ledger (JSON): `v0-run/evidence_ledger.json`
- V0 report (Markdown): `v0-run/evidence_report.md`
- Checks file: `case-study-1-checks.json`
- Allowlist: `case-study-1-allowlist.json`
- Single-case trace events: `trace-events-django-15930.jsonl`
- Meter HTML report: `trace-events-django-15930.html`
- Pre-patch baseline run (target test fails without the agent patch):
  `baseline-pre-patch-run.txt`
- Gold-patch cross-check run: `gold-patch-run.txt`
- Verifier version record (branch and commit, operator's record):
  `verifier-version.txt`
- First V0 run's checks/allowlist (absolute venv paths, superseded by the
  portable files): `case-study-1-checks-v1-absolute-paths.json`,
  `case-study-1-allowlist-v1-absolute-paths.json`
- Trace selection notes (why this trace, why not the others):
  `trace-selection.md`
