# Adapter 6: check-writing interview

Purpose: turn a task intent into 3 to 5 human-written checks
before V0 judges anything. V0 cannot auto-extract checks from
intent, and it must not treat an agent summary as a check. If
no checks are written, V0 has nothing to judge, and that is
correct behaviour, not a gap to paper over.

## The interview, in order

1. Intent, in one sentence. What was the change supposed to
   do, in the user's terms, not the agent's summary? Write it
   down before looking at any run output.
2. Done, in observable terms. For each part of the intent,
   what would a person see, in a file, in a command result, or
   in a named procedure, if that part actually worked? "Tests
   pass" in general is not an answer. A named test command is.
3. Failure, in observable terms. What would show, in the same
   places, if that part silently failed? An empty run exiting
   0, a skipped test, a file never written, a deploy that
   shipped without the feature: name the observable failure.
4. Evidence, per check. For each check, pick one check type:
   recorded_run (exact command, exit code, after final edit),
   artifact_presence (exact artifact path, expected digest
   if known), or external (named tester, named procedure,
   pass or fail result). If no evidence of that kind exists,
   write the check anyway and let V0 return NOT OBSERVED.
   Do not invent a record to fill the gap.
5. Scope, per check. Write the scope limitation in the check:
   what this check proves, and what it does not prove. A
   passing command proves only that the named command exited
   0 on that revision. It never proves correctness in general.
6. Count check. You need 3 to 5 checks, not 1 and not 20. One
   check is a slogan. Twenty checks is a test suite relabelled.
   If you have more than 5, pick the 5 that would change the
   decision if they failed.

## Worked example: a no-test workflow

Intent: a small command line tool reads a CSV file and writes
a Markdown summary report, with one row per category and a
total. There are no tests in the repo, and no test suite to
cite. The sender must not claim "tests pass", because no
tests exist.

Check 1, recorded_run: command "python -m reportgen --input
data.csv --output report.md", exit 0, after the final edit.
Scope: proves only that the named command exited 0 on that
revision, not that the totals are right.

Check 2, artifact_presence: artifact path "report.md" exists
in the repo snapshot after the run. Scope: proves only that
a file with that name exists, not that its contents are
correct.

Check 3, artifact_presence with a digest: the same report.md
digest matches a digest computed from a manually verified
expected report for a small known input. Scope: proves only
that the output matches that one known input, not all inputs.

Check 4, external: named tester, named procedure, result.
Illustrative only, not a record to copy: tester "A. Operator",
procedure "recompute the category totals for the known input
by hand and compare each row to report.md", result pass or
fail, supplied by the real operator for the real run. Scope:
scoped to exactly that tester, procedure, and revision. It
does not transfer to other inputs or revisions.

Check 5, recorded_run, negative control: command "python -m
reportgen --input missing.csv --output report.md" is expected
to fail, and its recorded exit code is non-zero. Scope:
proves only that the missing-input case fails loudly, not
that all bad inputs fail loudly.

If check 1 has no recorded run, V0 returns NOT OBSERVED, and
the honest report says exactly that: the run was not recorded,
so nothing is claimed about it. If check 4 has no named
tester record, V0 returns EXTERNAL-UNVERIFIABLE, not a pass.

## Template

See examples/no-test-checks.json. Fill in task_intent, then
one object per check, with id, text, check_type, and the
fields that type requires. Do not copy the worked example
verbatim into a real check file: replace every command, path,
tester, and procedure with the real ones for that workflow,
or delete the check.

## What this adapter does not do

It does not generate checks from a trace, a diff, or an agent
summary. It does not upgrade a Tier 0 body claim into evidence.
It does not turn a high unknown rate into a pass. A report
with a high unknown rate is a triage report: it states exactly
what evidence is missing, for which check.
