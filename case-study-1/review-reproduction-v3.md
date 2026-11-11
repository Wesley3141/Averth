# Review: reproduction of case study 1, round 3 (narrow second verification of v2 findings N1/N2/N3)

Reviewer: independent adversarial reproduction reviewer (subagent, no coordination with authors or operator)
Date: 2026-11-11
Scope: ONLY the three v2 findings (N1, N2, N3) from `review-reproduction-v2.md`.
Nothing else was re-reviewed. No file in `~/workspace/averth/case-study-1/` was
edited by this review except this verdict file itself.
Sources read: `case-study-1.md` (current), `review-reproduction-v2.md`,
`repro-test-fixed-steps.md` (including its addendum on the v2 fixes and the
operator's re-test).

## Verdict: PASS

All three v2 findings are fixed in the current `case-study-1.md`, with the
exact fixed lines quoted below. The directory logic was additionally verified
live against `/tmp/repro-cs1-fixed` (see §4).

## 1. N1 — working-directory flow: FIXED

V2 required: the meter block must start with `cd ..` so Averth is cloned
next to `django-base`, not inside it; and the V0 block must use
`cd evidence-v0`, not `cd averth/evidence-v0`, because the reader is already
inside `averth/` after the meter step.

Meter block, current text (lines 317–325), first line verbatim:

```
cd ..
git clone https://github.com/Wesley3141/Averth.git averth
cd averth
python3 -m venv ../averth-venv
../averth-venv/bin/pip install -e .
cp /path/to/trace-events-django-15930.jsonl .
../averth-venv/bin/python -m averth.cli trace trace-events-django-15930.jsonl --format jsonl
```

The prose immediately above the block states the reason verbatim:

> "Clone it next to `django-base`, not inside it: you are still in
> `django-base` from the test commands above, so go up one directory first,
> or V0 will hash the Averth checkout into the Django repo snapshot."

V0 block, current text (lines 347–349), first two lines verbatim:

```
git checkout criterion-c-checks-digest
cd evidence-v0
```

And the V0 prose states the reader's location verbatim: "You are still in it
from the meter step above." A grep for `averth/evidence-v0` across the whole
file returns no match — the broken path is gone entirely, not just from the
V0 block.

## 2. N2 — branch checkout in the V0 block, with reason: FIXED

V2 required: the V0 block must contain `git checkout
criterion-c-checks-digest` with the reason stated, since master's verifier
has no checks digest.

The V0 block's first line is verbatim (line 348):

```
git checkout criterion-c-checks-digest
```

The reason is stated in the prose immediately above the block, verbatim:

> "Check out the branch first: master's verifier has no checks digest, so a
> run on master cannot reproduce the ledger."

Note on placement: v2's suggested fix put the checkout in the meter block;
this round's task specifies the checkout in the V0 block, and that is where
it is. Either placement would work; the V0-block placement satisfies the
stated requirement, and the checkout runs before any V0 command, so the
verifier version is correct at the point of use.

## 3. N3 — marker upper bound: FIXED

V2 required: the marker wording must state the upper bound — a marker in the
future supersedes the runs.

Current prose (lines 340–343), verbatim:

> "The `--final-edit-marker` must be an ISO-8601 timestamp from just before
> you run the command, after your last edit to the checkout. A marker in the
> future supersedes the runs, and so does a marker from before your last
> edit."

Both bounds are now stated: lower bound (after the last edit) and upper
bound (just before the run; a future marker supersedes). This is the exact
failure v2 demonstrated in §1.4 (a marker 2 minutes in the future produced
exit 0 with 2 superseded runs and unknown rate 1.0), now warned against in
the text.

Non-blocking observation (not a defect under the stated criterion): the
placeholder inside the V0 command itself still reads only the lower bound —
`--final-edit-marker <ISO-8601 timestamp after your last repo edit>` — while
the full rule (including "just before you run the command") lives in the
prose directly above the block. A reader following the section in order
reads the prose before the command, so the upper bound is conveyed; the
placeholder could be tightened to match the prose, but it does not omit any
instruction the prose does not already give.

## 4. Directory-logic verification in /tmp/repro-cs1-fixed

Checked live, not taken from the operator's word:

- `averth` and `django-base` are siblings under `/tmp/repro-cs1-fixed/`
  (alongside `averth-venv` and `django-venv`); there is no nested
  `django-base/averth` directory.
- Averth checkout: branch `criterion-c-checks-digest`, HEAD `8ec848b` —
  the branch the V0 block now checks out.
- From inside `averth/`: `cd evidence-v0` succeeds (exit 0, lands in
  `/tmp/repro-cs1-fixed/averth/evidence-v0`, `cli.py` present).
- From inside `averth/`: the old `cd averth/evidence-v0` fails with
  `No such file or directory`, exit 1 — confirming the v2 failure mode is
  real and the new line is the correct replacement.
- The on-disk V0 output at `averth/evidence-v0/v0-run-repro/` carries
  checks digest `sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`
  (matching the published digest), counts `{'VERIFIED': 2,
  'EXTERNAL-UNVERIFIABLE': 2}`, unknown rate 0.5, runs 2, 0 superseded —
  consistent with the operator's addendum re-test outcome
  (marker `2026-11-11T05:23:22Z`, exit 0, same digest and counts).

Limitation, stated honestly: the on-disk `v0-run-repro` ledger still carries
the stage-4 marker `2026-11-11T05:19:19+00:00`, not the addendum re-test
marker `2026-11-11T05:23:22Z`, so that specific re-run is corroborated by
the addendum text and by the matching digest/counts of the preserved ledger,
not by a distinct on-disk artifact for the 05:23:22 run. That does not bear
on N1/N2/N3, which are text fixes verified verbatim above plus the live
directory checks; no V0 re-run was performed in this review, as the task
did not require one.

## 5. Out of scope

Per the task, nothing else was re-reviewed: no D1–D14 re-check, no meter
figures, no C2 digest discussion, no other v2-review findings (honesty,
numbers). This PASS covers only N1, N2, and N3 as defined above.
