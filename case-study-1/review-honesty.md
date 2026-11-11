# Adversarial honesty and wording review: case-study-1.md

Reviewer role: adversarial honesty and wording reviewer. Independent review;
no coordination with the case-study author. I re-checked claims against
`v0-run/evidence_ledger.json`, `v0-run/evidence_report.md`,
`case-study-1-checks.json`, `case-study-1-allowlist.json`, `trace-selection.md`,
the raw trajectory
`validation-traces/mini-swe-agent-s3/raw/django__django-15930.traj.json`,
the saved diffs, the meter HTML, the SWE-bench row file, the leaderboard
`per_instance_details.json`, and the live S3 `report.json` (fetched
2026-11-11). I also re-ran the disputed test behavior myself in a clean
git worktree (see finding V10): pre-patch failure and gold-patch pass are
substantively true, but neither is recorded anywhere in the case-study files.

## Verdict: FAIL

The text is careful in most places and no number I checked was fabricated,
but it fails on four counts that matter for a case study whose stated value
is exact reproducibility and honest scoping:

1. The reproduction steps are not executable as written (two broken
   extract-then-apply sequences; no V0 command at all).
2. "Cost per accepted outcome" contradicts the ledger's own no-acceptance-join
   note and C3's scope limitation (test verdicts are not acceptance).
3. The title claims the run is "verified end to end" when 2 of 4 checks are
   EXTERNAL-UNVERIFIABLE (unknown rate 50%).
4. The intro's provenance sentence ("All numbers below come from the V0
   ledger and the meter output") is false.

All four are fixable with text edits. Nothing below requires new evidence
collection except saving a record of the pre-patch discriminating run
(finding V10).

---

## Violations and overstatements (each with exact quote and exact fix)

### V1 (MAJOR). Reproduction steps: test-patch extraction has no command, and `git apply` is pointed at a parquet file

- File: `case-study-1.md`, section "Reproduction steps", lines 198-205.
- Wrong text:
  > `curl -sL -o /tmp/test-patch.diff \`
  > `  "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet"`
  >
  > `The test patch is inside that parquet file, instance django__django-15930,`
  > `field test_patch. Extract it with Python (pyarrow reads the file) and`
  > `apply it:`
  >
  > `git apply /tmp/test-patch.diff`
- Problem: the curl downloads a parquet binary to a path named
  `/tmp/test-patch.diff`. No extraction command is given anywhere in the
  section; the only command after the prose is `git apply` on that path,
  which fails on a parquet file. A reader following the commands literally
  cannot reproduce the run. The prose describes extraction; the commands do
  not perform it.
- Correct text: give the extraction as an executable command writing to a
  different path, e.g. download to `/tmp/swebench-verified.parquet`, then a
  concrete `python3` snippet that reads the parquet with pyarrow, selects
  instance `django__django-15930`, writes field `test_patch` to
  `/tmp/test-patch.diff`, and only then `git apply /tmp/test-patch.diff`.
  The snippet must be pasted in full and tested end to end, not described.

### V2 (MAJOR). Reproduction steps: submission extraction has no command, and the newline is appended to the JSON file, not the patch

- File: `case-study-1.md`, section "Reproduction steps", lines 207-219.
- Wrong text:
  > `curl -sL -o /tmp/submission.diff \`
  > `  "https://s3.amazonaws.com/.../django__django-15930.traj.json"`
  >
  > `The submission is the info.submission field of that JSON file. Extract it`
  > `and add one trailing newline, then apply it:`
  >
  > `printf '\n' >> /tmp/submission.diff`
  > `git apply /tmp/submission.diff`
- Problem: same defect as V1, worse. `/tmp/submission.diff` at the
  `printf` step still contains the downloaded trajectory JSON (the
  extraction is described, never commanded), so the `printf` appends a
  newline to the JSON file and the following `git apply` runs on JSON, not
  on a patch. It fails. The step that the whole "missing trailing newline"
  finding turns on is therefore unreproducible as written.
- Correct text: download to `/tmp/django-15930.traj.json`, then a concrete
  `python3` snippet that loads the JSON, writes `info["submission"]` to
  `/tmp/submission.diff`, and only then `printf '\n' >> /tmp/submission.diff`
  followed by `git apply /tmp/submission.diff`. Paste the snippet in full
  and test it end to end.

### V3 (MAJOR). Reproduction steps: the V0 rerun has no executable command

- File: `case-study-1.md`, section "Reproduction steps", lines 236-240.
- Wrong text:
  > `To reproduce the V0 run itself, clone https://github.com/Wesley3141/Averth,`
  > `check out branch criterion-c-checks-digest, and run the verifier with the`
  > `checks file, allowlist, and trace events saved with this case study.`
- Problem: no module, entry point, CLI invocation, flags, or working
  directory is given. "Run the verifier with" is prose, not a reproduction
  step, and the ledger/report record no V0 invocation command either. The
  meter command immediately below (`python -m averth.cli trace ...`) shows
  the standard the V0 paragraph fails to meet.
- Correct text: replace with the literal tested V0 command (module,
  subcommand, `--checks`, `--allowlist`, and working-directory arguments as
  actually invoked for the ledger run), plus the expected output
  (2 VERIFIED, 2 EXTERNAL-UNVERIFIABLE, unknown rate 50.0%, the two digests).

### V4 (MAJOR). "Cost per accepted outcome" contradicts the ledger and C3

- File: `case-study-1.md`, section "What the run cost", lines 136-139.
- Wrong text:
  > `Cost per accepted outcome: the run produced one outcome that the recorded`
  > `tests accept (C1 and C2 VERIFIED), so the estimated cost per accepted outcome`
  > `is $0.98, against $0.3205 recorded.`
- Problem: two contradictions inside the case study's own evidence.
  (a) The ledger's `trace_summary.note` states: "This trace carries no
  acceptance join, so no cost-per-accepted-outcome figure is computed from
  it, and no judgment in any report may cite this summary as a verdict."
  The evidence report's limitation 7 says the same. The case study computes
  the figure anyway by joining V0 test verdicts to the meter.
  (b) C3's scope limitation, quoted elsewhere in the case study, states
  "Recorded test verdicts are evidence, not human acceptance," and the
  "What was not observed" section says "Do not cite this case study as a
  human accepting the agent's work." The sentence does exactly that by
  redefining "the recorded tests accept" as an "accepted outcome." The
  meter HTML's "per accepted outcome" label means an autonomous completion
  (the trace `end` event has `success: true`), not acceptance by anyone.
  Borrowing the meter's label while the case study disclaims acceptance is
  a wording-level acceptance claim.
- Correct text (either of these; do not keep the current sentence):
  > `Cost per completed run: the run completed once with the target test and`
  > `the module green (C1 and C2 VERIFIED), so the estimated cost per`
  > `completed run is $0.98, against $0.3205 recorded. No human accepted`
  > `this run (C3), so no cost per accepted outcome is claimed. That`
  > `statement holds for this one run only. One run does not establish a rate.`
  Also fix line 113 ("Trace-labelled completions: 1") to use the meter's own
  term, "Autonomous completions: 1", or define "trace-labelled" where it
  first appears; the meter HTML says "1 autonomous completions."

### V5 (MAJOR). Title overstates: "verified end to end" with 50% unknown

- File: `case-study-1.md`, line 1.
- Wrong text:
  > `# Case study 1: one public coding-agent run, verified end to end`
- Problem: 2 of 4 checks are VERIFIED and 2 are EXTERNAL-UNVERIFIABLE;
  unknown rate is 50.0%. The body is honest about this, but the title is
  the first thing a reader (and any quote of the page) sees, and "verified
  end to end" asserts full verification that the record does not support.
  The same overstatement would survive any excerpt that quotes the title.
- Correct text:
  > `# Case study 1: one public coding-agent run, two checks verified, two unverifiable`

### V6 (MEDIUM). Intro provenance sentence is false

- File: `case-study-1.md`, lines 5-8.
- Wrong text:
  > `the V0 verifier judges human-written checks against recorded evidence, and the meter reports what the run cost, with`
  > `every dollar labeled by provenance. All numbers below come from the V0 ledger`
  > `and the meter output saved with this case study.`
- Problem: two errors. (a) "All numbers below come from the V0 ledger and
  the meter output" is false. The 72-message / 35-tool-call counts come
  from the raw trajectory, the $0.3205 comes from the leaderboard
  `per_instance_details.json`, the 3.84x figure comes from
  `validation-traces/mini-swe-agent-s3/FINDINGS.md` (a 12-run aggregate),
  and the pre-patch failure comes from a live run recorded only in
  `trace-selection.md`, not in the ledger (the ledger contains only the two
  post-patch runs). (b) "The meter reports what the run cost" states the
  meter as reporting actual cost; the meter reports an estimate (see V7).
- Correct text:
  > `the V0 verifier judges human-written checks against recorded evidence, and the meter estimates what the run cost, with`
  > `every dollar labeled by provenance. The V0 and meter numbers below come from the V0 ledger`
  > `and the meter output saved with this case study; run counts come from the raw trajectory,`
  > `the $0.3205 recorded cost comes from the leaderboard entry, and the 3.84x comparison`
  > `comes from the 12-run mini-SWE-agent findings note.`

### V7 (MEDIUM). "All metered dollars below are ESTIMATED" contradicts the case study's own provenance split

- File: `case-study-1.md`, section "What the run cost", lines 109-110.
- Wrong text:
  > `All metered dollars below are ESTIMATED, not measured spend and not a`
  > `bill.`
- Problem: the same section then breaks the $0.98 into "$0.91 priced model
  spend + $0.07 estimated tool spend," and the provenance paragraph repeats
  "$0.91 priced ... $0.07 estimated ... $0.00 billed." The meter HTML
  partitions the same way (Priced $0.91, Estimated $0.07, Vendor-supplied
  $0.00). The $0.91 component is priced, not estimated; a blanket "all
  metered dollars are ESTIMATED" is inaccurate under Averth's own
  provenance buckets, even though the $0.98 total is ESTIMATED overall per
  the meter's cost-basis warning (list prices applied to unverified
  trace-supplied token counts).
- Correct text:
  > `The $0.98 total below is ESTIMATED overall, not measured spend and not a`
  > `bill. Within it, $0.91 is priced (vendor list prices on trace-supplied`
  > `token counts Averth does not verify) and $0.07 is estimated (built-in`
  > `per-call tool estimates).`

### V8 (MEDIUM). Caching presented as the explanation; the source's caveat is dropped

- File: `case-study-1.md`, section "What the run cost", lines 128-132.
- Wrong text:
  > `Why the meter says $0.98 and the record says $0.3205: the trace records no`
  > `prompt-cache counts, so the meter prices full-history resends at list rate.`
  > `The recorded cost is consistent with heavy prompt caching (the same gap was`
  > `3.84x across 12 runs from this leaderboard entry).`
- Problem: the 3.84x / 12-run figure is real (verified in
  `validation-traces/mini-swe-agent-s3/FINDINGS.md`: metered $17.49 vs
  recorded $4.55 across 12 trajectories), but the same source states the
  gap "also includes error from chars/4 token estimates; cache impact
  cannot be isolated from this artifact." The case study keeps the
  caching half of the source's conclusion and drops the estimation-error
  half, leaving the reader with caching as the explanation. "Consistent
  with" is hedged, but the sentence's structure (no-cache-counts, so list
  rate; recorded cost consistent with heavy caching) presents one cause.
- Correct text:
  > `Why the meter says $0.98 and the record says $0.3205: the trace records no`
  > `prompt-cache counts, so the meter prices full-history resends at list rate.`
  > `The recorded cost is consistent with heavy prompt caching, and the same gap was`
  > `3.84x across 12 runs from this leaderboard entry, but the gap also includes`
  > `error from the trace's chars/4 token estimates, and the cache share cannot be`
  > `isolated from this trace.`

### V9 (MEDIUM). "The leaderboard entry records FAIL_TO_PASS 1/1 and PASS_TO_PASS 88/88" misattributes the source

- File: `case-study-1.md`, section "The run", lines 22-23.
- Wrong text:
  > `Official outcome: RESOLVED. The leaderboard entry records FAIL_TO_PASS 1/1`
  > `and PASS_TO_PASS 88/88 for this run.`
- Problem: the leaderboard entry's `per_instance_details.json` (verified
  locally) records only `cost: 0.32052914999999993`, `api_calls: 35`,
  `resolved: true` for this instance. It records no per-test counts. The
  1/1 and 88/88 counts come from the official evaluation `report.json`
  (fetched live 2026-11-11: `resolved: true`, FAIL_TO_PASS success 1 /
  failure 0, PASS_TO_PASS success 88 / failure 0). The counts themselves
  are correct; the cited source is wrong.
- Correct text:
  > `Official outcome: RESOLVED. The official evaluation report records FAIL_TO_PASS 1/1`
  > `and PASS_TO_PASS 88/88 for this run.`

### V10 (MEDIUM). The discriminating pre-patch run and the gold-patch pass are asserted with no saved record

- File: `case-study-1.md`, section "What failed", item 1, lines 68-73;
  section "The agent patch vs the gold patch", lines 143-152.
- Wrong text (item 1):
  > `The target test fails without the patch. Before the agent patch was`
  > `applied, the same test failed with OperationalError: near "THEN": syntax`
  > `error, exactly the reported bug. The check discriminates: it fails on the`
  > `broken code and passes on the fixed code.`
- Wrong text (gold patch):
  > `Both pass the recorded tests.`
- Problem: the V0 ledger contains only the two post-patch runs (both exit
  0, after the final edit). The pre-patch failure run has no run entry, no
  output digest, and no saved log in the case-study files; its only support
  is the assertion in `trace-selection.md` ("verified live here"). The gold
  patch was likewise never run under V0; "both pass" rests on the same
  notes file. I re-ran both independently in a clean worktree with the
  worktree's own Django on the path, and the substance is true: without any
  patch the target test fails with
  `django.db.utils.OperationalError: near "THEN": syntax error`
  (`FAILED (errors=1)`), and with the gold patch applied the target test
  passes and the module runs 89 tests OK (skipped=1). So this is a missing
  record, not a false claim, but a case study that sells traceability
  cannot rest its discrimination claim on an unrecorded run. Note the trap
  I hit while verifying: reusing the case-study venv against a fresh
  checkout silently imports the editable Django from `django-base` (which
  already has the agent patch), and the no-patch test then passes. The
  reproduction steps should warn that the venv's editable install must
  point at the checkout under test.
- Correct text: keep the claims, but (a) save the pre-patch run output
  (command, exit code, output digest) as a file in the case study and cite
  it, or soften item 1 to state that the discriminating run was performed
  during trace selection and is not in the V0 ledger; and (b) change the
  gold sentence to:
  > `Both pass the recorded tests: the agent patch under V0 (C1, C2), and the gold patch in a`
  > `separate rerun during trace selection (target test passes, module 89 tests OK, 1 skipped);`
  > `no V0 run of the gold patch is recorded in the ledger.`
  And add to the reproduction steps a warning that the venv's editable
  Django install must point at the checkout being tested, or a no-patch
  check run with that venv against a second checkout will pass spuriously.

### V11 (MINOR). "Byte-identical apart from that newline" is literally false

- File: `case-study-1.md`, section "What failed", item 2, lines 78-83.
- Wrong text:
  > `Appending one newline makes git apply accept it cleanly, and the applied diff is`
  > `byte-identical to the recorded submission apart from that newline.`
- Problem: I verified the substance (raw submission: `git apply` fails
  with `error: corrupt patch at line 15`, exit 128; after appending one
  newline it applies cleanly, exit 0). But "byte-identical" is false at the
  byte level: `git diff` after applying is 742 bytes vs the submission's
  747, differing in the index line (submission:
  `index 822968ef56..02a49836d7`; `git diff` output:
  `index 822968e..02a4983`, abbreviated hashes). The hunk content is
  identical; the diff headers are not byte-identical.
- Correct text:
  > `Appending one newline makes git apply accept it cleanly, and the applied change is`
  > `identical to the recorded submission apart from that newline (the hunk matches exactly;`
  > `only git's abbreviated index hashes differ in the diff header).`

### V12 (MINOR). "35 tool calls, 0 tool failures" overclaims by one unobserved call

- File: `case-study-1.md`, section "The run", lines 18-19, and section
  "What was not observed", line 98.
- Wrong text:
  > `tool calls, 0 tool failures, 0 retries.`
  > `No retries. The run recorded 0 tool failures and 0 retries, so there is no`
- Problem: the trajectory has 35 assistant messages, each containing one
  bash block (35 issued calls), but only 34 user messages carry a tool
  result with a `<returncode>` (all 34 are `0`); the other two user
  messages are the initial task prompt and the final submission diff. One
  issued bash call therefore has no recorded result in the trajectory, so
  "0 tool failures" is established for 34 of 35 calls, not all 35. The
  trace-events file (35 tool events) counts issued calls, not results.
  "0 retries" is fine (ledger `retry_events: 0`; all observed returncodes 0).
- Correct text:
  > `35 tool calls, 0 observed tool failures (34 tool results recorded, all exit 0), 0 retries.`
  and in "What was not observed":
  > `No retries. The run recorded 0 tool failures among the 34 recorded tool results (all exit 0)`
  > `and 0 retries, so there is no`

### V13 (MINOR). "The run re-sent the growing history on every call" states an inference as a recorded fact

- File: `case-study-1.md`, section "What the run cost", lines 119-121.
- Wrong text:
  > `Context tax: $0.68, which is 75% of the model spend. The run re-sent the growing`
  > `history on every call, and the meter prices those resends at list rate.`
- Problem: the $0.68 / 75% figures are verified (meter HTML; 0.68/0.91 =
  74.7%). But the trace events record only per-call input token counts
  (first 1460, last 14465, monotonic growth, ratio 9.9x). They record no
  prompt contents and no cache counts, so "re-sent the growing history on
  every call" is an inference from the token growth, not a recorded
  observation.
- Correct text:
  > `Context tax: $0.68, which is 75% of the model spend. Input token counts grow monotonically`
  > `from first to last step, consistent with the run re-sending the growing`
  > `history on every call, and the meter prices those resends at list rate.`

---

## Rule-by-rule check

1. **Em dashes / en dashes.** PASS. Zero U+2014 and zero U+2013 in
   `case-study-1.md` (checked programmatically).
2. **No invented customers, deployments, fundraise, real-workflow validation,
   unverified demand, "people are asking," or failure statistics.** PASS.
   The intro explicitly disclaims customer/deployment/live-workflow
   validation, and the "What this does and does not show" section repeats
   it. No demand claim appears. The only failure statistics are the
   recorded ones (0 tool failures / 0 retries, with the V12 caveat).
3. **Averth is a meter, not a debugger or fixer.** PASS. No fixing,
   debugging, or repair is promised. "Diagnose" appears once ("no retry
   loop to diagnose") as an observation about the meter, not a capability
   promise. "The check discriminates" and "do not present the run as a
   fix" language is about the test, not about Averth fixing anything.
4. **Dollar labeling.** PASS except V7 (blanket "all ESTIMATED" vs the
   priced/estimated split). The $0.98 is never presented as a bill or
   measured spend; it is labeled ESTIMATED throughout and the provenance
   paragraph gives $0.91 priced / $0.07 estimated / $0.00 billed, matching
   the meter HTML. The $0.3205 is consistently labeled "recorded" / "from
   the leaderboard entry," never billed. Verified: leaderboard
   `per_instance_details.json` cost `0.32052914999999993`, trajectory
   `model_stats.instance_cost` identical, `api_calls` 35.
5. **VERIFIED scope / NOT OBSERVED / inferred.** PASS. The table and prose
   scope C1 to the one target test on SQLite and C2 to the
   `expressions_case` module on SQLite, matching the ledger's scope
   limitations verbatim. C3/C4 are EXTERNAL-UNVERIFIABLE and are never
   counted as detection. No inferred checks exist in this case study
   (all four checks are `recorded_run` or `external`); nothing is labeled
   inferred that should be, and nothing inferred is presented as verified.
6. **One public trace, no generalization.** PASS except V5 (title) and the
   V8 cross-run sentence, which is a sourced 12-run comparison rather than
   a generalization from this run but is presented without its caveat.
   The body repeatedly states one trace only ("One run does not establish
   a rate," "One public trace is one public trace") and states no rates
   beyond this run's own figures (unknown rate 50.0% is this run's check
   coverage, yield 100% is this run's meter output).
7. **V0 behavior vs ledger/report; checks file and allowlist.** PASS.
   Checks-file digest `sha256:6dde8826...` matches `sha256sum` of
   `case-study-1-checks.json` and the ledger `checks_digest`. C1/C2 output
   digests in the table match the ledger exactly
   (`081dd9cc...`, `498fa2e3...`). C1/C2 `required_command` strings match
   the allowlist commands and the ledger `command_raw` strings exactly.
   The allowlist is minimal: exactly the two runtests commands, nothing
   else. Scope limitations in the checks file match the ledger judgments
   verbatim. Branch/commit claim verified in the Averth repo: commit
   `8ec848b` exists with message "Freeze checks at load and refuse mid-run
   edits (criterion c)" on branch `criterion-c-checks-digest`. One note:
   the refuse-mid-run-edit behavior itself was not exercised in this run
   (no mid-run edit was attempted); the claim rests on the commit, and the
   no-edit-after-load fact is supported by `final_edit_marker` 04:50:39
   preceding the first run start 04:52:24. Coverage counts match:
   4 checks, 2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE, unknown
   50.0%, 2 runs, 0 superseded.
8. **"What failed" / "What was not observed" vs the records.** PASS in
   substance, FAIL in record-keeping (V10, V11). Verified independently:
   submission is 747 bytes, ends without a trailing newline, is
   byte-identical to the trajectory `info.submission` (747 bytes) and to
   the evaluation's saved `patch.diff` (747 bytes, `cmp` identical);
   raw `git apply` fails `error: corrupt patch at line 15`; GNU patch
   applies it with fuzz 1 ("Hunk #1 succeeded at 1299 with fuzz 1");
   appending one newline makes `git apply` succeed. Agent patch vs gold
   patch: agent hardcodes `"1=1"` under `if not condition_sql:`; gold
   uses `if condition_sql == ""` and `compiler.compile(Value(True))`.
   The quoted code lines reproduce the operative lines exactly (the
   comment lines above them are omitted from both quotes, which is an
   excerpt, not a misquote). SQLite-only scope is correct. Nothing
   material was found omitted from "What was not observed" beyond V12's
   one unobserved tool result.

## Claims verified as accurate (spot-check list)

- No em dashes, no en dashes used as em dashes (0 of each).
- Run counts: 72 messages (1 system, 35 assistant, 36 user), 35 API
  calls, 35 bash blocks; trajectory `model_stats` `instance_cost`
  `0.32052914999999993`, `api_calls` 35; leaderboard
  `per_instance_details.json` cost `0.32052914999999993`, `api_calls` 35,
  `resolved: true`.
- Official outcome RESOLVED, FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88:
  confirmed in the live S3 `report.json` (FAIL_TO_PASS success 1 /
  failure 0; PASS_TO_PASS success 88 / failure 0) and by the SWE-bench row
  file (1 FAIL_TO_PASS, 88 PASS_TO_PASS). Only the cited source is wrong
  (V9).
- 4-line agent patch to `django/db/models/expressions.py`; `if not
  condition_sql: condition_sql = "1=1"`.
- C1/C2 digests, Tier 2 executed mode, checks digest, branch/commit,
  allowlist minimality and exact command match (see rule 7).
- Meter figures against `trace-events-django-15930.html`: $0.98 fully
  loaded, $0.91 priced model spend, $0.07 estimated tool spend, $0.00
  billed, $0.00 retry path, 71 events (35 model, 35 tool, 1 end),
  9.9x input growth (14465/1460 = 9.906), context tax $0.68 = 75% of
  model spend (0.68/0.91 = 74.7%), yield 100%, 1 attempt, 1 autonomous
  completion, 0 escalations, 0 retries. Arithmetic: 0.98/0.3205 = 3.06x.
  3.84x across 12 runs: metered $17.49 vs recorded $4.55 in
  `validation-traces/mini-swe-agent-s3/FINDINGS.md` (12 trajectories).
- Token counts are chars/4 estimates and no cache counts exist in the
  trace events; no bill is recorded. The $0.98 is never called a bill.
- C2 scope: ledger stderr "Ran 89 tests in 0.152s / OK (skipped=1)";
  89 = 88 PASS_TO_PASS + 1 FAIL_TO_PASS.
- No human acceptance, no second backend, no other module run: correct
  per the ledger (C3/C4 EXTERNAL-UNVERIFIABLE, runs only in
  `expressions_case`, SQLite in memory).
- Files list at the end of the case study: all listed files exist in the
  case-study directory.
- Meter CLI form (`python -m averth.cli trace <file> --format jsonl`)
  matches the invocation recorded in the 12-run findings note.

## What must change before publication

1. Fix V1, V2, V3: paste full tested extraction commands and the literal
   V0 command into the reproduction steps, and run them end to end from
   a clean checkout.
2. Fix V4: drop "cost per accepted outcome"; use "cost per completed
   run" with an explicit no-acceptance disclaimer.
3. Fix V5: retitle to drop "verified end to end."
4. Fix V6: correct the intro provenance sentence.
5. Fix V7-V13 as specified above (each is a one- or two-sentence edit,
   except V10, which needs the pre-patch run output saved as a cited file).
