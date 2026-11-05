# V0 demo script — 5 minutes, widget fixture only

Audience: anyone evaluating the V0 verifier. No real workflow, no
customer data, no live model. Everything below runs locally with
commands already proven on 2026-11-03. Do not improvise claims
during the demo; if asked about anything beyond the fixture, say
it is unproven and point to the limitations section.

## Minute 0–1: the setup (say this, then run nothing yet)

"We built a small local tool that checks a handful of
human-written acceptance checks against the actual record, and
says plainly what it does not know. The example is toy code on
purpose: a widget with add, subtract, and multiply, where multiply
is intentionally buggy — it returns a sum, so multiply(3, 4)
returns 7, not 12. The checks were written by a human. Nothing was
auto-extracted, nothing was auto-repaired."

## Minute 1–2: run it (imported mode)

```bash
cd ~/workspace/research/averth-pivot-2026-11-02/experiment-14day/v0-verifier
python3 cli.py --repo ../evidence-fixture \
  --checks examples/fixture-checks.json \
  --runs ../evidence-fixture/evidence_ledger.json \
  --out runs/demo --report-id v0-demo
```

Show the counts line: VERIFIED 2, FAILED 2, NOT OBSERVED 2,
EXTERNAL-UNVERIFIABLE 1, NOT APPLICABLE 1, unknown rate 37.5%.

## Minute 2–3: one of each — VERIFIED, FAILED, NOT OBSERVED

- VERIFIED (C1, add): "The record shows the add test ran after
  the final edit and exited 0. That proves only add(2, 3) == 5
  in this one test. It does not prove add is correct in general."
- FAILED (C3, multiply): "The record shows the multiply test ran
  after the final edit and exited 1, assert 7 == 12. That is a
  real observed failure, not a prediction. So any claim that all
  tests pass is contradicted by the record."
- NOT OBSERVED (C5, edge tests): "The edge test file exists, but
  it was never run in any recorded run. The report says
  NOT OBSERVED. That is a statement about the records, not a
  claim that edge cases were never tested anywhere, and it is
  not upgraded to FAILED. The fix is to run the check, not to
  relabel the row."

Then show the live-recorded mode in one line: with `--execute`,
the tool runs the edge tests, they pass, C5 becomes VERIFIED,
and the unknown rate falls to 25.0%. "The row moved because the
check was actually run."

## Minute 3–4: what the report refuses to say

Point at the LIMITATIONS section in the generated Markdown
report and read two lines aloud: "A successful shell command is
not proof of complete correctness," and "A local hash is not
tamper-resistant provenance." Then: "There is no Tier 3 evidence
here — no independent CI attestation is wired in — and no
hardware claim is verified, because no hardware record exists."

## Minute 4–5: what this does not prove (say this verbatim)

"This report does not prove test quality, correctness beyond the
named assertions, acceptance by any human or operator, value,
time saved, willingness to pay, or boot on untested hardware. It
does not repair anything, and it has not been validated on a
real workflow. The next step is one controlled repair experiment
on matched tasks, which is blocked on model access until a newly
authorised evaluation environment is provided. Until then, this
is a credible local report and a defined experiment, not a
proven product."

Close by offering the report files (JSON ledger + Markdown) for
inspection, not a signup, not a price, not a repair.
