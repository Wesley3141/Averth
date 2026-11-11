# Review 2 (verify) — Correctness of the numbers, re-verification

**Verdict: FAIL** — narrowly, and certification-only. Every published
figure still recomputes exactly (see below), the relabel is in place
and true as written, the billed/priced/estimated buckets are now
certified from the real Data quality lines in stdout AND HTML, the
ratio regex is anchored, and the reproduce script passes 47/47 end
to end. What fails is the same failure mode as my first pass: two of
the reproduce script's checks pass while certifying something other
than what they claim — the new "yield rate" check parses the success
rate, not the yield ratio (proven by mutation: yield 100% → 42%
leaves the check PASS), and the "meter model events" check counts
trajectory assistant messages, not meter model events (proven by
deletion: dropping the smallest model event leaves meter $0.91 /
$0.98 unchanged and the check would still read 35). A certifier that
cannot detect the regression it names is not a certifier. Both fixes
are one-line regex/count changes (exact fixes below). One further
stale label survives in the CHANGELOG (N2).

Scope: numbers only. I edited no source file. Scratch evidence is in
`try-it/reviews/scratch-2-verify/` (`recompute-verify.py`,
`sensitivity.py`, `reproduce.log`, `repro-work/`, fresh live
`traj-stdout.txt` / `traj-try.html`, `jsonl-stdout.txt` /
`jsonl-try.html`, `traj-v0-stdout.txt` / `traj-v0.html`, and the two
mutated-JSONL experiments `jsonl-34model*.jsonl` /
`jsonl-34model-first*.jsonl`).

## What I checked live

1. **Reproduce script end to end** (this pass, fresh work dir):
   `python3 try-it/reproduce-case-study.py --work-dir
   try-it/reviews/scratch-2-verify/repro-work --force` — exit 0,
   **all 47 checks PASSED** in ~69 s (log: `reproduce.log`). This
   includes the Django baseline/gold-patch runs, the V0 executed run
   (fresh ledger), and the combined-report rebuild.
2. **Independent recomputation** (`recompute-verify.py`, no averth
   imports; prices read as text literals from `averth/pricing.py`):
   all assertions PASS. Trajectory 72 messages (1 system + 36 user +
   35 assistant); chars/4 tokens 279,017 in / 5,077 out; model cost
   279,017 × $3/1M + 5,077 × $15/1M = $0.913206 → **$0.91**; 35 bash
   × $0.002 = **$0.07**; fully loaded $0.983206 → **$0.98**; recorded
   `instance_cost` 0.32052914999999993 → **$0.3205**; ratio 3.0677 →
   **3.07x** (also 3.07x on the unrounded recorded cost); context
   growth 14,465/1,460 = 9.9075 → **9.9x**; context tax
   Σ(in − 1,460)/1e6 × $3 = $0.683751 → **$0.68**, 74.9% → **75%**;
   fixture JSONL 71 events (35 model / 35 tool / 1 end), model token
   sums (279,017, 5,077) matching the traj recomputation; V0 from
   the fresh repro ledger: VERIFIED 2, FAILED 0,
   EXTERNAL-UNVERIFIABLE 2, unknown rate 0.5, runs_total 2,
   judgments in order VERIFIED, VERIFIED, EXTERNAL-UNVERIFIABLE,
   EXTERNAL-UNVERIFIABLE; checks digest
   `sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a`
   matches a fresh sha256 of `fixtures/case-study-1-checks.json`.
3. **Live `averth try` runs** (`.venv/bin/python -m averth.cli`,
   exit 0 each): traj, JSONL, and traj + fresh V0 ledger. My parser
   confirmed in fresh stdout AND HTML for both input paths: Priced
   $0.91, Billed $0.00, Estimated $0.07, Fully loaded $0.98, ratio
   3.07x, Retries 0, no `http`, and **zero occurrences of "recorded
   tokens"** in any of the six fresh outputs (the old wording
   survives only in first-pass scratch artifacts and in N2 below,
   not in any current output).
4. **Test suite:** `pytest tests/test_try_it.py -q` → **52 passed**
   (22 in the first pass; the suite grew with the fixes).
5. **Sensitivity mutations** (`sensitivity.py`, exact regexes copied
   from the reproduce script, run against a copy of live stdout):
   see D2/D3/D5 (mutations correctly FAIL) and N1 (mutation
   incorrectly PASSes). Plus the two JSONL deletion experiments for
   D6(b) (see below).

## Original defects

### D1 — Priced-bucket label: FIXED (as the adjudicated minimum)

- `averth/report.py:206-208` (stdout) and `:617-619` (HTML) now
  read: `Priced (vendor list prices on trace-supplied token counts,
  not verified as provider-recorded usage): $0.91`. Verified live
  in fresh stdout and HTML for both the traj and JSONL runs. The
  words "recorded tokens" and the "legacy traces" clause are gone
  from both render paths; the label now agrees with the COST BASIS
  banner in the same report ("may be estimated (characters/4, …)").
  The split is unchanged: $0.91 / $0.07 / $0.00, as adjudicated.
- **Position on the rejected preferred fix (tokens_estimated,
  split $0.00 / $0.98): I accept the adjudication's decision for
  this branch.** The label as now written states no falsehood: it
  says the counts are trace-supplied and not verified as
  provider-recorded, which is true, and the chars/4 basis is
  disclosed in the report (`cli.py` source note) and in the
  miniswe docstring. I still object on principle to the underlying
  classification — vendor prices applied to characters/4 estimates
  sit in "Priced" while the meter's own Wave-5 rule
  (`averth/tracker.py`, and the CHANGELOG's own token-provenance
  bullet) says spend on estimated tokens lands in Estimated — and
  the miniswe docstring (`averth/importers/miniswe.py:18-24`)
  still openly says the flag is omitted so the published numbers
  reproduce exactly. That tension is real, but it is a
  Wesley-level republishing decision the adjudication explicitly
  reserved, not a false statement in the shipped report, so it is
  recorded here as dissent, not a FAIL driver. The adjudication
  already flags it for the parent; nothing further I can add
  changes the call.

### D2 — Vacuous billed check: FIXED

- `try-it/reproduce-case-study.py:372`: `check("meter billed
  bucket", bucket(r"Vendor-supplied \(billed\)"),
  PUBLISHED["meter_billed"])` — parses the real Data quality line
  from live stdout (verified $0.00 in the 47/47 run), and
  `:474` does the same from the combined-report HTML.
- Sensitivity-proven: mutating the stdout line to
  `Vendor-supplied (billed): $0.50` makes the script's own
  bucket regex return 0.50 and the check FAIL. The check is real.

### D3 — Provenance split certified only by proxy: FIXED

- `try-it/reproduce-case-study.py:368-372` parses the three Data
  quality bucket lines from stdout (`Priced (…)`, `Estimated
  (…)`, `Vendor-supplied (billed)`); `:468-474` parses the same
  three from the HTML data-quality block. Both sets passed in the
  live 47/47 run and match my independent parse of the fresh
  outputs ($0.91 / $0.07 / $0.00 in both places).
- Sensitivity-proven: mutating the stdout Priced line to $0.50
  makes the bucket regex return 0.50 and the check FAIL. A
  bucket-math regression can no longer hide behind the
  cost-component lines (which are still checked separately at
  `:360-366` and also pass).

### D4 — Report never shows "0 FAILED": FIXED

- `averth/try_report.py:279` (HTML rows) and `:360-361` (stdout
  `ordered` join) now iterate `_VERDICT_ORDER` with
  `counts.get(name, 0)` — all five verdicts, zeros included.
  Verified live: fresh stdout line 49 reads `V0 verdicts:
  VERIFIED 2, FAILED 0, NOT OBSERVED 0, EXTERNAL-UNVERIFIABLE 2,
  NOT APPLICABLE 0; unknown rate 50.0%; checks digest verified
  against the checks file`, and the fresh V0 HTML contains a
  `FAILED` row (value 0). The README claim at `try-it/README.md:75`
  is now true.

### D5 — Unanchored ratio regex: FIXED

- `try-it/reproduce-case-study.py:392`: `re.search(r"ESTIMATED
  \(([0-9.]+)x\)", out)` — anchored to the recorded-cost summary
  line. Passed at 3.07 in the live run.
- Sensitivity-proven: prepending a decoy `(9.99x)` line to stdout
  makes the old regex `r"\(([0-9.]+)x\)"` return 9.99 while the new
  anchored regex still returns 3.07.

### D6 — Coverage gaps: PARTLY (a, c, d FIXED; b NOT FIXED)

- **(a) FIXED.** `:204`: `check_int("trajectory messages",
  len(traj["messages"]), 72)` — passed in the live run; I
  independently counted 72 (1 + 36 + 35).
- **(b) NOT FIXED — check exists but still measures the wrong
  thing.** `:206-209`:
  `check_int("trajectory assistant messages (meter model events)",
  sum(1 for m in traj["messages"] if m.get("role") ==
  "assistant"), 35)`. This counts assistant messages in the
  *trajectory input*, not model events in the meter. The name
  claims "meter model events"; the implementation never touches
  the meter, the converter output, or the fixture JSONL (the only
  JSONL reference in the script is the `--trace` passed to V0 at
  `:412`). A converter drop is therefore still invisible to this
  check, and the cent-rounded total does not save it in general.
  Proof by deletion (fresh experiments in scratch):
  - Dropping the *last* model event from a copy of the fixture
    JSONL (14,465 in / 123 out tokens) moves the meter to
    Model/API $0.87 / Fully loaded $0.94 — the total check would
    catch that one.
  - Dropping the *first* model event (1,460 in / 58 out tokens,
    ≈ $0.0053) leaves the meter at Model/API **$0.91** /
    Fully loaded **$0.98** — unchanged at the cent. The traj
    assistant count is still 35, so the "meter model events"
    check would still PASS, and no other script check counts
    model events. A dropped small event is undetectable by the
    script as written. This is the exact hole D6(b) asked to
    close ("a check that the meter's own model-event count is
    35").
  - **Exact fix:** count model events from the meter's own input
    side — e.g. count `"type": "model"` lines in
    `try-it/fixtures/trace-events-django-15930.jsonl` (35) and
    assert the converter reproduces that fixture (or, better,
    run `averth try` on the fixture JSONL as a second meter run
    and check its fully-loaded total equals the traj run's
    $0.98 — that certifies converter fidelity and the meter's
    event count together). Rename the check to what it measures
    until then; a check named "meter model events" that reads
    the trajectory is a mislabel of the same kind D1 was.
- **(c) FIXED.** `:431`: `check("V0 unknown rate", …,
  places=2)` — unknown rate compared at 2 dp (0.5 vs 0.5).
- **(d) FIXED.** `:301`: baseline asserts the full
  `'OperationalError: near "THEN": syntax error'` string; passed
  in the live run.

## New checks (adjudication list) — verified

All present in the script and passing in the live 47/47 run, except
as noted: 72 trajectory messages (`:204`, genuine); 35 "meter model
events" (`:206`, **proxy — see D6(b)**); traj-vs-leaderboard
`instance_cost` agreement (`:230`, genuine — exact equality
against the downloaded leaderboard record); FAIL_TO_PASS 1/1
(`:262`) and PASS_TO_PASS 88/88 (`:266`, genuine — decoded from
the JSON-encoded parquet strings); context-tax share 75%
(`:385-386`, genuine — parsed from the real context-tax line);
yield 100.0% (`:387`, **wrong source — see N1**); V0 superseded
runs retained 0 (`:434`, genuine); V0 digest match (`:437`,
genuine — fresh sha256 confirmed independently above). The
"checks every published number" claim is narrowed to an explicit
checked / not-checked list in the module docstring (verified by
reading), and the checks table prints on mid-run failure
(`print_table()` in the `except` path).

## New defects

### N1 (major, certification) — The "yield rate" check parses the success rate, not the yield ratio

- **File/lines:** `try-it/reproduce-case-study.py:387-391`:
  `check("yield rate", float(re.search(r"Autonomous completions:
  \s*\d+ \(([0-9.]+)%\)", out).group(1)), PUBLISHED["yield_rate"],
  places=1)`.
- **Expected:** the check reads the yield ratio — live stdout line
  28: `3. Yield ratio: 100% of tokens on the terminal path (0%
  burned on retries and failed runs)`.
- **Actual:** it reads `Autonomous completions:1 (100.0%)`
  (stdout line 7) — the success rate. Yield and success rate are
  different quantities: a single successful run with retries has
  success rate 100% and yield < 100%. They coincide at 100.0%
  here only because this run has 0 retries.
- **Proof by mutation** (`sensitivity.py`): changing only the
  yield line in a copy of live stdout from `Yield ratio: 100%` to
  `Yield ratio: 42%` leaves the script's regex returning 100.0
  and the check PASSing. The check cannot detect a yield
  regression at all — the same luck-of-coincidence flaw D5 had
  for the ratio, now in a check added by this round of fixes.
- **Exact fix:** parse the yield line itself, e.g.
  `float(re.search(r"Yield ratio: ([0-9.]+)% of tokens on the
  terminal path", out).group(1))`, and likewise check the HTML
  yield card. (I verified the true yield is 100% — 0 retries, 0
  failed spend — so this fix changes no published number.)

### N2 (minor, docs) — CHANGELOG still describes the Priced bucket with the old, rejected label

- **File/lines:** `docs/CHANGELOG.md:205-210`, under `## Unreleased`
  (lines 3–350), token-provenance bullet: `Reports label the Priced
  bucket "vendor prices on recorded tokens" (legacy traces without
  a provenance flag still land there), …`.
- That sentence describes the pre-fix label. The shipped label
  (D1) no longer says "recorded tokens" anywhere. The CHANGELOG is
  the durable record a reader consults after the report; as written
  it re-asserts the false claim the relabel just removed.
- **Exact fix:** rewrite the clause to the adopted wording, e.g.
  `Reports label the Priced bucket "vendor list prices on
  trace-supplied token counts, not verified as
  provider-recorded usage"`. (Note: the `miniswe.py:18-24`
  docstring's "deliberately do NOT set tokens_estimated" is
  *not* listed as a defect — it documents the adjudicated
  decision, and changing it would contradict the accepted split.)

## What I did not verify

- The $3/$15 list prices against Anthropic's live pricing page
  (no live-browser access in this role; values taken as text
  literals from `averth/pricing.py`, as in the first pass).
- The gold-patch / baseline Django claims beyond the reproduce
  script's own live runs (baseline failure, target pass, module
  89 tests / skipped=1, gold pass — all executed and passing in
  the 47/47 run I watched).

## Bottom line

Numbers: every published figure recomputes exactly, both input
paths agree, V0 renders all five verdicts with zeros, and the
47-check reproduce run passes end to end. Labels: D1 is fixed as
the adjudicated minimum and I accept that decision (with the
classification dissent noted above, reserved to Wesley).
Certification: D2, D3, D5, D6(a/c/d) are fixed and
sensitivity-proven; but the script still certifies two numbers by
proxy — yield via the success rate (N1) and meter model events
via the trajectory assistant count (D6(b)) — and I proved by
mutation and by deletion that neither check can detect the
regression it names. Fix those two checks (plus the one-line
CHANGELOG correction, N2), re-run, and this passes.
