# Adversarial honesty review, round 3: case-study-1.md (narrow re-verification of N1, N2, N3)

Reviewer role: independent adversarial honesty reviewer. Scope is narrow by
brief: verify ONLY the three findings from round 2 (review-honesty-v2.md)
are fixed in the current `case-study-1.md` and `gold-patch-run.txt`. I did
not re-review anything else and did not edit any file.

## Verdict: PASS

All three round-2 findings are fixed, verified word for word below.

---

## N1 (BLOCKING in round 2) — FIXED

The V0 paragraph in the reproduction steps now tells the reader to check
out the branch, and states the reason. From `case-study-1.md`
("To reproduce the V0 run itself..."):

> `To reproduce the V0 run itself, use the same Averth checkout. You are still`
> `in it from the meter step above. Check out the branch first: master's`
> `verifier has no checks digest, so a run on master cannot reproduce the`
> `ledger. Run V0 last, with the Django checkout at base commit plus test patch`
> `plus agent patch applied.`

And the checkout line is present in the V0 command block itself (line 348):

> `git checkout criterion-c-checks-digest`

The reason is stated in the paragraph ("master's verifier has no checks
digest, so a run on master cannot reproduce the ledger"), matching the
round-2 finding exactly. A literal reader now runs the branch verifier
(`criterion-c-checks-digest`, commit 8ec848b) that the case study says was
used, and the `checks_digest` in the ledger is reproducible as written.
The blocking issue is closed.

## N2 (MINOR in round 2) — FIXED

`gold-patch-run.txt` now contains a separate target-test run under the gold
patch, with its own command, state, timestamp, exit code, and output.
Appended section:

> `--- TARGET TEST (appended 2026-11-11) ---`
> `COMMAND: /home/hatch/workspace/averth/case-study-1/django-venv/bin/python tests/runtests.py expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0`
> `WORKING DIRECTORY: /home/hatch/workspace/averth/case-study-1/django-base`
> `STATE: test patch applied, GOLD patch applied (not the agent patch)`
> `TIMESTAMP (UTC): 2026-11-11T05:22:09Z`
> `--- OUTPUT ---`
> `EXIT CODE: 0`
> `System check identified no issues (0 silenced).`
> `----------------------------------------------------------------------`
> `Ran 1 test in 0.007s`
> ``
> `OK`

This is distinct from the module run already in the file (89 tests,
`OK (skipped=1)`, exit 0, timestamp `2026-11-11T04:57:17Z`).

The case study's wording now matches what the file shows. From
`case-study-1.md` ("The agent patch vs the gold patch"):

> `Both pass the recorded tests: the agent patch under V0 (C1, C2), and the gold`
> `patch in a separate rerun during trace selection (target test passes, module`
> `89 tests OK, 1 skipped, saved as `gold-patch-run.txt`); no V0 run of the gold`
> `patch is recorded in the ledger.`

"Target test passes" is now backed by the separate target-test run in the
file (exit 0, 1 test OK), and "module 89 tests OK, 1 skipped" by the
module run in the same file. No softening was needed; the file now
contains the evidence the sentence cites.

## N3 (MINOR in round 2) — FIXED

The `--python` parenthetical no longer claims the flag "was part of the
recorded invocation" or any other unverifiable claim about the invocation.
A grep of `case-study-1.md` for `recorded invocation` and `was part of`
returns zero hits. The new wording, from `case-study-1.md` directly below
the V0 command block:

> `The `--python` flag is unused when an allowlist is given, so it does not`
> `affect the run.`

This states only a verifiable fact about the flag's behavior, and I
verified it against the branch CLI source rather than taking the sentence
on trust. In `evidence-v0/cli.py` on branch
`criterion-c-checks-digest` (commit 8ec848b), the allowlist path calls
`run_via_allowlist(check["required_command"], repo, allowlist)` with no
interpreter argument, while `args.python` is passed as
`interpreter=args.python` only on the non-allowlist path
(`run_allowlisted(...)`). So with an allowlist given, `--python` is indeed
unused and cannot affect the run. The unverifiable operator-record claim
is gone, and its replacement is true in the code.

---

## Scope note

This pass verified only N1, N2, and N3 as briefed. No other claim in
`case-study-1.md` was re-checked, and no file was edited.
