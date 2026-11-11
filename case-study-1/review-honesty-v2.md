# Adversarial honesty review, round 2: case-study-1.md (rewritten after three FAIL reviews)

Reviewer role: independent adversarial honesty reviewer. No coordination with
the case-study author. I re-checked every claim in the rewritten
`case-study-1.md` against `v0-run/evidence_ledger.json` (generated
2026-11-11T05:14:38Z, report_id `averth-case-study-1`),
`v0-run/evidence_report.md`, `case-study-1-checks.json`,
`case-study-1-allowlist.json`, `baseline-pre-patch-run.txt`,
`gold-patch-run.txt`, `verifier-version.txt`, `trace-selection.md`,
`trace-events-django-15930.jsonl`, and the Averth repo itself
(`master` vs `criterion-c-checks-digest`). I did not re-run the Django
tests or the meter; the reproduction reviewer already did that, and this
review verifies the rewritten text against the saved records.

## Verdict: FAIL

All 13 first-review findings V1-V13 are fixed in the new text, verified
word for word below. But V3 is only *mostly* fixed, and the gap is in the
same category that failed the first review: the reproduction steps as
written do not reproduce the ledger. The V0 paragraph now gives the literal
command, but it never tells the reader to check out the
`criterion-c-checks-digest` branch, and the only clone step in the section
(the meter block, line 315) is a plain `git clone`, which lands on master.
Master's verifier has no `checks_digest` at all (verified in the repo:
no `checks_digest` string in `master:evidence-v0/cli.py`,
`master:evidence-v0/requirement_spec.py`, or
`master:evidence-v0/evidence_ledger.py`; master's `cli.py` is 141 lines vs
the branch's 428). A reader following the steps literally therefore runs
master's verifier, not the branch the case study says was used ("not
master", line 52-53), and produces a ledger with no checks digest — so the
case study's own claim that "the checks digest in the ledger
(`sha256:f25cd3bc...`) reproduces from the saved checks file" cannot be
reproduced as written. The fix is one line (`git checkout
criterion-c-checks-digest` after the clone, as the reproduction review's D4
fix already specified). Until that line is in the steps, the case study
must not be published.

One new issue (N1, blocking) and two minor observations (N2, N3, not
blocking) are listed after the table.

---

## Per-finding re-check: V1-V13

### V1 (test-patch extraction) — FIXED

New wording (lines ~261-275):

> `curl -sL -o /tmp/swebench-verified.parquet \`
> `  "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet"`
> `../django-venv/bin/pip install pyarrow`
> `../django-venv/bin/python - <<'EOF'`
> `import pyarrow.parquet as pq`
> `t = pq.read_table('/tmp/swebench-verified.parquet')`
> `row = [r for r in t.to_pylist() if r['instance_id'] == 'django__django-15930'][0]`
> `assert row['base_commit'] == '63884829acd207404f2a5c3cc1d6b4cd0a822b70'`
> `open('/tmp/test-patch.diff', 'w').write(row['test_patch'])`
> `print('FAIL_TO_PASS:', row['FAIL_TO_PASS'])`
> `EOF`
> `git apply /tmp/test-patch.diff`

The download is now named for what it is, the extraction is a pasted
executable command, and `git apply` runs on the extracted diff. This
matches the reproduction review's D1 fix verbatim (plus the base-commit
assert and the `FAIL_TO_PASS` print, which are harmless: `test_patch` is a
plain string, so the stringified-list quirk in D14 does not affect the
extraction). The `pyarrow` install is inside the venv, never system
Python (reproduction review D8).

### V2 (submission extraction) — FIXED

New wording (lines ~277-290):

> `curl -sL -o /tmp/django-15930.traj.json \`
> `  "https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json"`
> `python3 - <<'EOF'`
> `import json`
> `traj = json.load(open('/tmp/django-15930.traj.json'))`
> `open('/tmp/submission.diff', 'w').write(traj['info']['submission'])`
> `EOF`
> `printf '\n' >> /tmp/submission.diff`
> `git apply /tmp/submission.diff`

The download is now named for what it is, the extraction is a pasted
executable command using stdlib `json` only, and the `printf` now appends
the newline to the extracted patch, not to the JSON. Matches the
reproduction review's D2 fix.

### V3 (literal V0 command) — PARTIALLY FIXED (see N1)

The literal command is now present (lines ~340-348):

> `cd averth/evidence-v0`
> `export PATH=/path/to/django-venv/bin:$PATH`
> `python3 cli.py --repo /path/to/django-base \`
> `  --checks /path/to/case-study-1-checks.json \`
> `  --allowlist /path/to/case-study-1-allowlist.json --execute \`
> `  --python /path/to/django-venv/bin/python \`
> `  --trace /path/to/trace-events-django-15930.jsonl \`
> `  --final-edit-marker <ISO-8601 timestamp after your last repo edit> \`
> `  --out ./v0-run-repro --report-id v0-case-study-1-repro`

Module, flags, working directory, marker rule, and expected output are
all stated, and the expected output matches the new ledger exactly:
"counts `{'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 0.5,
runs 2 (0 superseded)" vs ledger coverage
`{'criteria_total': 4, 'counts': {'VERIFIED': 2, 'EXTERNAL-UNVERIFIABLE': 2},
'unknown': 2, 'unknown_rate': 0.5, 'decided': 2,
'superseded_runs_retained': 0, 'runs_total': 2}`. The stated marker
("Our run used marker `2026-11-11T05:14:32Z`") matches the ledger's
`final_edit_marker` `2026-11-11T05:14:32+00:00`, and the runs start after
it (05:14:36.75, 05:14:37.61). BUT: the paragraph says "use the same
Averth checkout" and never checks out the branch, and the only clone in
the section (line 315, meter block) is a plain `git clone` onto master.
See N1. V3 is fixed as a command and broken as a version pin.

### V4 ("cost per completed run", no acceptance) — FIXED

New wording (lines 162-165):

> `Cost per completed run: the run completed once with the target test and the`
> `module green (C1 and C2 VERIFIED), so the estimated cost per completed run is`
> `$0.98, against $0.3205 recorded. No human accepted this run (C3), so no cost`
> `per accepted outcome is claimed. That statement holds for this one run only.`
> `One run does not establish a rate.`

"Cost per accepted outcome" appears nowhere else except inside this
disclaimer. The completions line now uses the meter's own term (line 134):
"Attempts: 1. Autonomous completions: 1. Human escalations: 0." Both
match the meter and are consistent with the ledger's trace-summary note
("This trace carries no acceptance join, so no cost-per-accepted-outcome
figure is computed from it, and no judgment in any report may cite this
summary as a verdict"), which I re-read in the new ledger.

### V5 (title) — FIXED

New title (line 1):

> `# Case study 1: one public coding-agent run, two checks verified, two unverifiable`

No "verified end to end" anywhere in the file (grep: zero hits).

### V6 (intro provenance) — FIXED

New wording (lines 3-11):

> `This is one public trace, not a benchmark and not a product claim. It shows what`
> `Averth actually does on a real agent run: the V0 verifier judges human-written`
> `checks against recorded evidence, and the meter estimates what the run cost, with`
> `every dollar labeled by provenance. The V0 and meter numbers below come from the`
> `V0 ledger and the meter output saved with this case study; run counts come from`
> `the raw trajectory, the $0.3205 recorded cost comes from the leaderboard entry's`
> `per_instance_details.json, and the 3.84x comparison comes from the 12-run`
> `mini-SWE-agent findings note. Nothing here is a customer, a deployment, or a`
> `validation of Averth on a live workflow.`

"All numbers below come from the V0 ledger and the meter output" is gone;
each source is now named. "The meter reports what the run cost" is now
"the meter estimates what the run cost". The 3.84x figure was verified by
the numbers review (metered $17.49 vs recorded $4.55 across 12 runs);
I did not re-verify that aggregate here.

### V7 (metered-dollars wording) — FIXED

New wording (lines 127-133):

> `The meter ran on the single-case trace events (71 events: 35 model, 35 tool,`
> `1 end). The $0.98 total below is ESTIMATED overall, not measured spend and not`
> `a bill. Within it, $0.91 is priced (vendor list prices on trace-supplied token`
> `counts Averth does not verify) and $0.07 is estimated (built-in per-call tool`
> `estimates).`

The blanket "all metered dollars are ESTIMATED" is gone; the split is
$0.91 priced / $0.07 estimated / $0.00 billed, matching the meter. I
recomputed the event counts from `trace-events-django-15930.jsonl`: 71
lines, 35 model, 35 tool, 1 end. Correct.

### V8 (caching caveat) — FIXED

New wording (lines 147-155):

> `Why the meter says $0.98 and the record says $0.3205: the trace records no`
> `prompt-cache counts, so the meter prices full-history resends at list rate.`
> `The recorded cost is consistent with heavy prompt caching (the same gap was`
> `3.84x across 12 runs from this leaderboard entry). The gap also includes error`
> `from the trace's chars/4 token estimates, and the cache share cannot be`
> `isolated from this trace.`

Both halves of the source caveat are now present: estimation error and
"the cache share cannot be isolated". Caching is no longer presented as
the sole explanation.

### V9 (1/1 and 88/88 attributed to report.json) — FIXED

New wording (lines 25-27):

> `Official outcome: RESOLVED. The official evaluation record (`report.json`)`
> `records FAIL_TO_PASS 1/1 and PASS_TO_PASS 88/88 for this run.`

"The leaderboard entry records" is gone. The `report.json` URL is printed
directly below (line 41), and the numbers were confirmed in the live
`report.json` by both prior reviews.

### V10 (pre-patch and gold-patch runs cited as saved files) — FIXED

Pre-patch, "What failed" item 1 (lines ~88-92):

> `The target test fails without the patch. Before the agent patch was`
> `applied, the same test failed with `OperationalError: near "THEN": syntax`
> `error`, exactly the reported bug. That run is saved as`
> ``baseline-pre-patch-run.txt`.`

Verified: `baseline-pre-patch-run.txt` exists, states
`STATE: test patch applied, agent patch NOT applied (reverted to base
commit)`, timestamp `2026-11-11T04:57:12Z`, `EXIT CODE: 1`, and the
traceback ends in `django.db.utils.OperationalError: near "THEN": syntax
error` with `FAILED (errors=1)`. The command in the file matches the C1
command.

Gold patch (lines ~186-189):

> `Both pass the recorded tests: the agent patch under V0 (C1, C2), and the gold`
> `patch in a separate rerun during trace selection (target test passes, module`
> `89 tests OK, 1 skipped, saved as `gold-patch-run.txt`); no V0 run of the gold`
> `patch is recorded in the ledger.`

Verified: `gold-patch-run.txt` exists, states `STATE: test patch applied,
GOLD patch applied (not the agent patch)`, timestamp
`2026-11-11T04:57:17Z`, `EXIT CODE: 0`, `Ran 89 tests in 0.171s`, `OK
(skipped=1)`. The "no V0 run of the gold patch is recorded in the ledger"
disclaimer is true: the new ledger contains exactly 2 runs, both
post-agent-patch, both exit 0. See N2 for a minor scoping note on the
"target test passes" clause.

### V11 (byte-identical claim corrected) — FIXED

New wording (lines ~96-100):

> `Appending one newline makes `git apply` accept it cleanly, and the applied file`
> `matches the submission's intended content exactly. The regenerated git diff`
> `differs from the recorded patch only in the abbreviated index hashes and`
> `the trailing newline.`

This states exactly what the numbers review proved (regenerated diff 742
bytes vs recorded 747; index line `822968ef56..02a49836d7` vs
`822968e..02a4983`; hunk content identical; patched file bytes identical).
The literal "byte-identical apart from that newline" claim about the diff
is gone. (The remaining "byte-identical" uses in the file are the
trajectory-vs-`patch.diff` identity at line 95 and the HTML identity at
line 328, both verified by the prior reviews, not the false claim.)

### V12 ("0 observed tool failures (34 tool results recorded, all exit 0)") — FIXED

"The run" (lines 21-23):

> `35 tool calls, 0 observed tool failures (34 tool results recorded, all exit 0),`
> `0 retries.`

"What was not observed" (lines 116-118):

> `No retries. The run recorded 0 observed tool failures (34 tool results recorded, all exit 0)`
> `and 0 retries, so there is no retry cost to report`

The unqualified "0 tool failures" is gone in both places; the evidence
base (34 recorded results) is now stated. The numbers review confirmed
34 returncodes, all `0`.

### V13 (re-sending stated as inference) — FIXED

New wording (lines 141-145):

> `Context tax: $0.68, which is 75% of the model spend. Input token counts grow`
> `monotonically from first to last step, consistent with the run re-sending`
> `the growing history on every call, and the meter prices those resends at`
> `list rate.`

"Consistent with" now marks the inference. I recomputed from the trace
events: first input 1460, last input 14465, ratio 9.9075x (9.9x as
stated), inputs monotonic non-decreasing across all 35 model events,
totals 279,017 in / 5,077 out, matching the ledger's trace summary.
The ratio line is also now correct (numbers review D1): "Metered estimate
divided by recorded cost: 3.07x ($0.9832 unrounded / $0.3205)" —
0.9832 / 0.3205 = 3.0677, which rounds to 3.07x.

---

## New issues found in the rewritten text

### N1 (BLOCKING). V0 reproduction steps never check out the verifier branch; a literal reader runs master, whose ledger has no checks digest

- The V0 paragraph (lines ~330-348) says "use the same Averth checkout"
  and gives the literal `cli.py` command, but contains no branch checkout.
  The only clone in the section is the meter block (line 315):
  `git clone https://github.com/Wesley3141/Averth.git averth` — a plain
  clone onto the default branch (master, `1431befa...`).
- The case study itself states the verifier is "the
  `criterion-c-checks-digest` branch (commit 8ec848b), not master"
  (lines 52-53). A literal reader therefore runs the verifier the case
  study says was *not* used.
- I verified in the Averth repo that this is not a cosmetic difference.
  Master's verifier predates the digest machinery entirely:
  `master:evidence-v0/cli.py` (141 lines) contains no `digest` reference;
  `master:evidence-v0/requirement_spec.py` has `load_checks` but no
  `checks_digest`; `master:evidence-v0/evidence_ledger.py` has no
  `checks_digest` field. The branch (`criterion-c-checks-digest`,
  `8ec848b7d3085c752f340ffe2754d90ada432edd`) adds the freeze/digest code
  (`cli.py` 428 lines, `requirement_spec.py` `checks_digest()` hashing
  raw file bytes, ledger `checks_digest` field).
- Consequence: a master run accepts the same flags, so it would not
  crash — it would silently produce a *different* ledger with no
  `checks_digest` key. The case study's claim (lines 58-61) that "the
  checks digest in the ledger
  (`sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`)
  reproduces from the saved checks file" is then unreproducible as
  written, and the freeze/refuse-mid-run-edit behavior described in
  "What V0 verified" would not be exercised. (I verified the digest
  itself does reproduce from the saved portable checks file:
  `sha256sum case-study-1-checks.json` =
  `f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`,
  matching the new ledger — but only under the branch verifier.)
- Fix: one line, as the reproduction review's D4 fix already specified —
  after the clone, `git checkout criterion-c-checks-digest` (HEAD
  `8ec848b`), before the V0 command. The meter block clones without a
  branch, so the checkout must be explicit in the V0 paragraph, not
  assumed.

### N2 (MINOR, not blocking). Gold-patch "target test passes" rests on the module run, not a separate target-test run

- `gold-patch-run.txt` records exactly one command: the module run
  (`tests/runtests.py expressions_case -v 0`, 89 tests OK, skipped=1).
  There is no separate target-test-only run for the gold patch in the
  file. The case study's "(target test passes, module 89 tests OK, 1
  skipped)" is still sound — the target test is one of the 89 and the
  module run has 0 failures — but a strict reader checking the file for
  a target-test line will not find one. Optional one-line softening
  ("the module run, which includes the target test, passes 89 tests OK")
  would close it. Not a FAIL by itself.

### N3 (MINOR, not blocking). "--python flag ... was part of the recorded invocation" is unverifiable from the artifacts

- Line ~350: "The `--python` flag is unused when an allowlist is given;
  it is shown because it was part of the recorded invocation." No
  invocation command is recorded in the ledger or the report (the ledger
  carries no invocation field), so this cannot be checked against any
  record; it rests on the operator's word, like the branch/commit claim.
  Harmless — the flag is accepted by the branch CLI and the reproduction
  reviewer used it — but it is a second operator-record claim sitting
  next to a sentence that is careful to flag the branch claim as the
  operator's record. Optional: qualify it the same way. Not a FAIL.

---

## Rule-by-rule re-check (rewritten text)

1. **Em dashes / en dashes.** PASS. Raw-byte count: 0 U+2014, 0 U+2013
   in `case-study-1.md`.
2. **No invented customers, deployments, fundraise, validation claims.**
   PASS. Intro: "Nothing here is a customer, a deployment, or a
   validation of Averth on a live workflow." "What this does and does not
   show" repeats it. No demand, fundraise, or deployment claim anywhere.
3. **D5/D6 reproducibility caveats (numbers review).** PASS. D5: the
   pre-patch run is saved and cited (V10 above); the gold run is saved
   and cited. D6: the verifier claim is qualified — "per the operator's
   record in `verifier-version.txt`; the ledger itself carries no
   verifier version field" (lines 52-55). I confirmed the ledger has no
   verifier/branch/version key (only `schema_version` matched a keyword
   scan), and `verifier-version.txt` records branch
   `criterion-c-checks-digest`, commit `8ec848b`, full hash
   `8ec848b7d3085c752f340ffe2754d90ada432edd`, recorded
   `2026-11-11T04:58:01Z`. The commit exists at that hash on that branch
   (verified via `git rev-parse`).
4. **Reproduction-review caveats carried over.** PASS, except N1. The
   shallow checkout, venv warning, detached-HEAD note, prerequisites
   (Python 3.12 with venv/pip, git, curl), `git restore` revert, direct
   raw URL for `per_instance_details.json`, meter install/cwd/trace-file
   steps, digest-timing caveat ("compare exit codes (0), test counts (1
   test OK; 89 tests OK, skipped=1), and verdicts, not digests"), and the
   meter's actual output wording ("Autonomous completions: 1 (100.0%)",
   "Fully loaded: $0.98", with the "Priced" label explained) are all
   present. The portable checks/allowlist files use bare `python`
   (verified by reading both files), and the checks digest reproduces
   from the saved file (verified by `sha256sum`).
5. **V0 table vs new ledger.** PASS. C1 digest
   `sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3`
   and C2 digest
   `sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b`
   in the case-study table match the new ledger runs and the new report
   exactly; both exit 0, Tier 2, `after_final_edit: true`; C3/C4
   EXTERNAL-UNVERIFIABLE with the scope limitations quoted verbatim.
   Coverage line matches the ledger coverage block exactly.
6. **One public trace, no generalization.** PASS. "One run does not
   establish a rate", "One public trace is one public trace", and the
   12-run 3.84x comparison is sourced, not generalized from this run.
7. **"What failed" / "What was not observed" vs the records.** PASS.
   The `git apply` / GNU-patch / newline account matches the numbers
   review's verified behavior; SQLite-only scope is stated; the
   `1=1` vs `Value(True)` quotes match the submission and gold diffs as
   verified in the first review.

## What must change before publication

1. **N1 (blocking):** add `git checkout criterion-c-checks-digest` to
   the reproduction steps (after the Averth clone, before the V0
   command), so a literal reader runs the branch verifier the ledger
   came from and can reproduce the `checks_digest` field. Then re-verify
   by running the printed V0 command verbatim from a fresh clone.
2. N2, N3 (optional, one line each): soften the gold-patch "target test
   passes" clause to point at the module run, and qualify the
   `--python`-was-in-the-invocation sentence as the operator's record.
