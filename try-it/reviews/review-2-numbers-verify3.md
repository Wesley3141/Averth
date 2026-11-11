# Review 2 (verify 3) — Correctness of the numbers, third re-verification

**Verdict: PASS** — both remaining items from my second re-verification
(review-2-numbers-verify2.md, FAIL, certification-only) are fixed and
proven live. D6(b) fixture half: the reproduce script now counts
`"type": "model"` lines in the fixture JSONL and asserts 35, and my
deletion proof shows it catches the exact drop that was previously
invisible — dropping the first (smallest) model event (1,460 in / 58
out tokens) makes the script FAIL with exactly one failing check,
"fixture JSONL model events (actual 34, published 35)", while the
cent-rounded total check still passes at $0.98, proving the count
check (not the total) is the detector. N3: the stray `)` is gone from
the CHANGELOG token-provenance bullet. The clean reproduce run is
51/51 PASS. The stale-artifact disposition is correct: the case-study
HTML stays untouched (see item 3 — the fresh-vs-saved diff is in fact
four hunks, not one line, which strengthens the leave-alone case).
The stale `try-it/.test-out/` reports are deleted.

Scope: numbers only, narrowly the two remaining items (D6(b) fixture
half, N3) plus the stale-artifact disposition. I edited no source
file. Scratch evidence is in `try-it/reviews/scratch-2-verify3/`
(`reproduce.log`, `reproduce-mutated.log`, `jsonl-drop-first-model.jsonl`,
`jsonl-clean-report.html`, `jsonl-drop-first-report.html`,
`jsonl-clean-stdout.txt`, `repro-work/`, and the mutated-repo copy
`repo-drop-first/` with its own `repro-work-mutated/`).

Repo state checked: branch `try-it`, HEAD `c1bc0cc` ("Reproduce
script counts fixture model events; fix CHANGELOG typo") on top of
`0750720`. Working tree clean of tracked modifications. All commands
run with `~/workspace/averth/.venv/bin/python -m averth.cli` where a
meter run was needed, and `python3 try-it/reproduce-case-study.py`
for the script runs.

## What I checked live

1. **Reproduce script end to end, clean** (fresh work dir):
   `python3 try-it/reproduce-case-study.py --work-dir
   try-it/reviews/scratch-2-verify3/repro-work --force` — exit 0,
   **all 51 checks PASSED** (50 in verify2; the +1 is the new
   "fixture JSONL model events" check). Log: `reproduce.log`
   (51 `PASS` lines, 0 `FAIL`, counted). The three step-7 lines read:
   `PASS meter model events (actual 35, published 35)`,
   `PASS JSONL meter fully loaded (actual 0.98, published 0.98)`,
   `PASS fixture JSONL model events (actual 35, published 35)`.
2. **Deletion proof, mutated repo copy** (the decisive check):
   copied the checkout to `scratch-2-verify3/repo-drop-first/`,
   dropped the first model event from the copy's fixture, and ran the
   copied script end to end. Result: exit nonzero,
   **"reproduce: 1 of 51 checks FAILED"** (50 PASS, 1 FAIL), and the
   single failure is `FAIL fixture JSONL model events (actual 34,
   published 35)`. See item 1.
3. **Fixture independently re-counted:** `try-it/fixtures/
   trace-events-django-15930.jsonl` has 71 lines, **35** `"type":
   "model"` events, token sums 279,017 in / 5,077 out; the first
   model event is `{"type": "model", "case_id":
   "django__django-15930", "model": "claude-sonnet-4-20250514",
   "input_tokens": 1460, "output_tokens": 58}` — the same smallest
   event as in verify2.
4. **Test suite:** `pytest tests/test_try_it.py -q` → **53 passed**
   (unchanged from verify2).
5. **CHANGELOG read** (item 2) and **stale-artifact diff**
   (item 3), both below.

## Item 1 — D6(b) fixture half: FIXED

What is in place (`try-it/reproduce-case-study.py:429-437`):

```python
# The fixture the second run meters must itself carry 35
# model events: a dropped small event leaves the
# cent-rounded total unchanged, so total equality alone
# would not detect it.
with open(os.path.join(
        fixtures, "trace-events-django-15930.jsonl"),
        encoding="utf-8") as f:
    check_int("fixture JSONL model events",
              sum(1 for line in f
                  if json.loads(line).get("type") == "model"),
              PUBLISHED["meter_model_events"])
```

with `PUBLISHED["meter_model_events"] = 35` (`:93`). This is exactly
the one-line fix my verify2 named (option (a)). The comment at
`:414-416` ("the converter's events must meter identically to the
trajectory run") no longer overclaims on its own: the total-equality
check is now accompanied by the count check, and the new comment
states the limitation the count closes.

Deletion proof (run, not asserted):

- Mutated fixture copy (`jsonl-drop-first-model.jsonl`, also the
  fixture inside `repo-drop-first/`): 70 lines, **34** model events
  — the first/smallest model event removed, everything else
  byte-identical.
- Meter on the mutated copy (`.venv` CLI, fresh run): Model/API
  **$0.91** / Fully loaded **$0.98** — unchanged from the clean
  fixture. The cent-rounded total is still blind to this drop,
  reproducing verify2's premise exactly.
- Full reproduce script run against the mutated-repo copy: exit
  nonzero, `1 of 51 checks FAILED`, and the only failure is
  `FAIL fixture JSONL model events (actual 34, published 35)`.
  The neighbouring checks prove the isolation:
  `PASS meter model events (actual 35, published 35)` (converter
  side reads the trajectory, unaffected) and `PASS JSONL meter
  fully loaded (actual 0.98, published 0.98)` (the total check
  still passes — it is the count check, and only the count check,
  that catches the drop).
- Clean run of the same script: 51/51 PASS, so the new check does
  not false-positive on the intact fixture.

## Item 2 — N3, CHANGELOG stray paren: FIXED

- `docs/CHANGELOG.md:205-210`, under `## Unreleased`, now reads:
  `Reports label the Priced bucket "vendor list prices on
  trace-supplied token counts, not verified as provider-recorded
  usage", name fallback-price, vendor-price-on-estimated-token,
  …` — the `)` after the closing quote is gone. Confirmed by
  direct read and by the `c1bc0cc` diff, which shows exactly that
  one-character deletion on that line.
- The adopted N2 wording is intact; no other character changed in
  the bullet.

## Item 3 — Stale-artifact disposition: AGREE (leave untouched)

Verified facts:

- `case-study-1/trace-events-django-15930.html` is still on disk,
  8,720 bytes, timestamped 2026-11-11 04:53, and its line 76 still
  carries the old Priced label: `Priced (vendor prices on
  recorded tokens; legacy traces without a provenance flag still
  land here): $0.91`.
- It is referenced as byte-identical evidence in
  `case-study-1/case-study-1.md:331` ("the saved HTML is
  byte-identical to a fresh run's output") and
  `case-study-1/review-reproduction.md:224` ("byte-identical to
  the saved `trace-events-django-15930.html` (8,720 bytes,
  `diff` clean)"), and in the same sense at
  `case-study-1/review-numbers.md:28` and
  `case-study-1/review-reproduction-v2.md:79`.
- `try-it/.test-out/` no longer exists (`ls`: No such file or
  directory) — the stale try-it reports are deleted, as stated.

My own check sharpens (not weakens) the disposition: a fresh meter
run on the *unmutated* fixture (`jsonl-clean-report.html`, Fully
loaded $0.98, new label) differs from the saved HTML in **four
hunks, not one line** — (a) the cost-basis banner, line 58
("versioned list prices and reported token/cache usage" →
"versioned list prices and trace-supplied token counts (not
verified as provider-recorded usage)"); (b) the per-run wording,
lines 63/73 ("per accepted outcome" / "Cost per successful
outcome" → "per completed run" / "Cost per completed run"); (c)
the Priced label itself, line 76 (the deliberate relabel); (d) a
whole new "How this report was made" section after line 110. So
regenerating would rewrite published case-study evidence in
several places, and the `case-study-1.md:331` "byte-identical to a
fresh run's output" claim is already no longer literally true
under current code regardless of what this branch does. The
correct home for any re-freeze is the case-study branch (regenerate
*and* update the byte-identical claims and the 8,720-byte figure
together), not a try-it fix. Leaving the artifact untouched here
is correct. No change needed in this branch.

## New defects

None. No new defect found in the scope checked.

## Note (provenance, not a defect) — the fixture check's commit history

The task framing says `c1bc0cc` carries both fixes. What git
actually shows: `git show c1bc0cc --stat` touches only
`docs/CHANGELOG.md` (the one-character N3 deletion), and the
fixture-count check is already present in `0750720` itself
(`git show 0750720:try-it/reproduce-case-study.py` contains
"fixture JSONL model events" at line 434). So `c1bc0cc`'s commit
message overclaims — it did not introduce the script check. This
changes nothing about the certified state (the check is committed
at HEAD, present in the working tree, and proven sensitive live),
but the record should not credit `c1bc0cc` with the script change.
No action required; do not rewrite history over it.

## What I did not verify

- The $3/$15 list prices against Anthropic's live pricing page
  (no live-browser access in this role; values taken as text
  literals from `averth/pricing.py`, as in both prior passes).
- The gold-patch / baseline Django claims beyond the reproduce
  script's own live runs (baseline failure, target pass, module
  89 tests / skipped=1, gold pass — all executed and passing in
  the 51/51 run I watched).

## Bottom line

D6(b) is now fully fixed on both halves: the converter count (35,
sensitive, verify2) and the fixture count (35, now sensitive —
proven by a full script run against a mutated repo copy failing
on exactly that one check). N3 is fixed (stray paren gone).
Clean reproduce run is 51/51 PASS; test suite 53 passed. The
stale case-study HTML stays untouched, correctly — regenerating
it would rewrite published evidence in four places, a
case-study-branch decision, not a try-it fix.
