# Review 3 — Honesty of labels: RE-VERIFICATION (adversarial)

- Reviewer: adversarial reviewer 3 of 5 (same reviewer as first pass)
- Scope: `averth try`, `try-it/reproduce-case-study.py`, generated reports, README, CLI help
- Branch: `try-it` (unmerged; nothing merged, pushed, deployed, or sent)
- Sources read in full before running anything: `try-it/reviews/review-3-honesty.md`
  (first pass, FAIL, D1–D6), `try-it/reviews/adjudication.md`,
  `averth/try_report.py` (`build_try_extras`, `try_summary_lines`),
  `averth/report.py` (COST BASIS / Data quality / MODEL COST BASIS lines),
  `averth/cli.py` (`_cmd_try`, `--recorded` help, `model_cost_basis` threading),
  `try-it/reproduce-case-study.py` (docstring, `PUBLISHED`, meter + combined-report checks),
  `try-it/README.md` (expected-output block, "does and does not claim" section).
- Live probes run (scratch in `try-it/reviews/scratch-3-verify/`):
  canonical run (traj + `--recorded 0.3205` + `--ledger` + `--checks`) →
  `full.html`, `stdout-full.txt`; `--ledger` without `--checks` → `no-checks.html`,
  `stdout-no-checks.txt`; `--recorded 99` (wrong) → `wrong-recorded.html`,
  `stdout-wrong-recorded.txt`; bare run → `bare.html`, `stdout-bare.txt`;
  JSONL input → `jsonl.html`, `stdout-jsonl.txt`; digest mismatch against a
  pre-existing `--out` → `stale-target.html`, `stdout-stale.txt`,
  `stderr-stale.txt`. All runs used
  `~/workspace/averth/.venv/bin/python -m averth.cli try` with
  `--model claude-sonnet-4-20250514` (the traj filename carries no model name;
  the CLI now refuses without `--model`, exit 2 — checked, see first command
  attempt, which failed exactly that way before I added the flag).
- Test suite: `pytest tests/test_try_it.py -q` → **52 passed**.
- **Verdict: PASS.** All six first-pass defects are fixed as adjudicated
  (D1 minimum, D2, D3, D4, D5, D6), the published numbers reproduce exactly,
  and the two new defects found are minor (N1, N2 below) — neither restores
  any first-pass mislabel, and neither blocks sign-off. Neither was fixed by
  me; no source file was edited.

## Published numbers (recomputed live, canonical run)

Stdout (`stdout-full.txt`): Fully loaded $0.98; Model/API $0.91; Tool calls
$0.07; Priced $0.91 / Vendor-supplied (billed) $0.00 / Estimated $0.07;
Recorded cost (operator-supplied) $0.3205, 3.07x; V0 VERIFIED 2, FAILED 0,
NOT OBSERVED 0, EXTERNAL-UNVERIFIABLE 2, NOT APPLICABLE 0; unknown rate
50.0%; Retries 0. All match the published case-study figures exactly.

## D1 — Priced bucket mislabel: FIXED (minimum adopted; preferred fix rejected — position stated below)

What I checked live:

- Stdout Data quality line (`stdout-full.txt`):
  > `Priced (vendor list prices on trace-supplied token counts, not verified as provider-recorded usage): $0.91`
- Same wording in HTML (`full.html:76`, Data quality list) and in the JSONL
  run (`jsonl.html:76`). A repo-wide grep for `recorded tokens` across
  `averth/`, `try-it/README.md`, `try-it/reproduce-case-study.py`, and the
  generated reports returns only a code comment at `averth/report.py:203`
  ("The parenthetical no longer says 'recorded tokens'") — the false phrase
  appears nowhere user-facing anymore.
- The chars/4 disclosure is now in stdout, not only at the bottom of the
  HTML. Canonical stdout carries it twice: the COST BASIS banner
  ("Remaining priced dollars apply vendor list prices to trace-supplied
  token counts that Averth does not verify as recorded usage") and the
  source-note line ("Token counts are characters/4 estimates from the
  trajectory text, not provider-recorded usage; the dollars apply vendor
  list prices to those estimates."). The bare run (`stdout-bare.txt`) also
  carries both. This is exactly the minimum fix option 2 from my first pass.
- MODEL COST BASIS for traj input, stdout (`stdout-full.txt:4`) and HTML
  (`full.html:58`):
  > `MODEL COST BASIS: versioned list prices and converter-estimated token counts (characters/4 from the trajectory text, not provider-reported usage); reconcile against the customer invoice before calling this actual spend.`
  The "reported token/cache usage" falsehood is gone for traj input.
- The split is unchanged: $0.91 priced / $0.07 estimated / $0.00 billed,
  as the adjudication requires. README (`try-it/README.md`, report section)
  now states the bucket label verbatim and adds "for trajectory input those
  token counts are the characters/4 estimates described below, not
  provider-recorded usage."

**On the rejected preferred fix (set `tokens_estimated`, split becomes
$0.00 priced / $0.98 estimated, republish the case study): I accept the
rejection for this branch, and I am not objecting to PASS on that ground.**
My reasons, stated plainly: (1) the adopted minimum is the fix I specified
as acceptable in my first pass (option 2), and it is implemented completely
— the false words are gone and the true basis is disclosed where the figure
is read, in stdout as well as HTML; (2) the preferred fix contradicts the
task's acceptance criterion (reproduce $0.91 priced exactly), so adopting
it here would trade one defect for a failed acceptance test; (3) republishing
the live case-study page is a Wesley decision, not a reviewer fix. I still
hold that `tokens_estimated` would be the cleaner fix and the $0.00/$0.98
split the more honest one — the converter still deliberately omits the flag
(`averth/importers/miniswe.py:18-21`) and the fixture events still carry no
`tokens_estimated` key in any of the 35 model events (re-verified by
counting) — but that residual is now disclosed rather than concealed, and
it is flagged for Wesley, not hidden. If he ever republishes the case
study, the preferred fix should be revisited then.

## D2 — "per accepted outcome" claim: FIXED

What I checked live:

- Card sub-label (`full.html`): `per completed run`. Section heading:
  `<h2>Cost per completed run</h2>`. Stdout heading (`stdout-full.txt:12`):
  > `Cost per completed run (not per accepted outcome — no human acceptance labels were joined):`
- `Reopened:              0` in stdout — "accepted outcomes reopened" is gone.
- The disclaimer sentence prints on stdout on **every** run, including the
  bare run (`stdout-bare.txt`, last two lines):
  > `No human accepted this run, so no cost per accepted outcome is claimed. Cost per completed run is $0.98 ESTIMATED, not a bill.`
- "per accepted outcome" now occurs in `full.html` exactly twice, both
  inside that disclaimer sentence (the V0-section paragraph and the
  "How this report was made" paragraph); once in `bare.html` and
  `jsonl.html` (disclaimer only). Grep for `successful outcome` and for
  `accepted outcomes reopened` across all generated HTML and stdout:
  zero matches.

## D3 — `--recorded` stated as fact: FIXED (with one minor residual, N1)

What I checked live:

- Labelled operator-supplied everywhere it appears: stdout line
  (`stdout-full.txt:48`)
  > `Recorded cost (operator-supplied): $0.3205; metered estimate per completed run: $0.98 ESTIMATED (3.07x)`
  HTML table row (`full.html:111`):
  `Recorded cost (operator-supplied via --recorded; not verified by Averth)`,
  and the declarative sentence rewritten as specified:
  > `The operator supplied $0.3205 as the recorded cost for this run; a meter working from this trace alone would estimate $0.98.`
  `--recorded` help (`averth/cli.py:91-92`): "Operator-supplied figure
  claimed to be the recorded cost … Averth does not verify it". Module
  docstring (`cli.py:16-17`) and README (`try-it/README.md:66-70, 140-144`)
  corrected the same way.
- Cross-check, wrong figure: `--recorded 99` produced in `wrong-recorded.html:111`:
  > `<p><b>Warning:</b> the trajectory's own recorded cost is $0.3205, which differs from the operator-supplied $99. One of the two figures is wrong; reconcile before quoting either.</p>`
  and the stdout ratio line duly collapses to 0.01x. Cross-check,
  correct figure: `full.html:111` carries
  > `<p>The trajectory's own recorded cost ($0.3205) agrees with the operator-supplied figure.</p>`
  The traj figure itself (`info.model_stats.instance_cost =
  0.32052914999999993`) was re-verified against the leaderboard value by
  reading the fixture directly.
- Residual (N1, minor, not FAIL-driving): the cross-check warning/agreement
  appears **only in the HTML**. `stdout-wrong-recorded.txt` contains no
  `instance_cost` / mismatch line at all — the operator who reads only
  stdout sees `Recorded cost (operator-supplied): $99 … (0.01x)` with no
  hint the traj itself says $0.3205. Cause, read in the code:
  `try_summary_lines` (`averth/try_report.py:333`) takes no
  `traj_recorded` parameter, and `_cmd_try` (`averth/cli.py:419-425`)
  passes `traj_recorded` only to `build_try_extras`. The core dishonesty
  is fixed (the figure is labelled operator-supplied, never stated as
  fact), so this is a gap in the second layer, not a restored defect.
  See N1 for the exact fix.

## D4 — V0 rows cite no observation: FIXED

What I checked live (`full.html:112`, V0 judgments table, columns Check /
Verdict / What was checked / Cited observation):

- C1 VERIFIED — "the FAIL_TO_PASS test passes with the agent patch" plus
  scope limitation, cited observation:
  `python tests/runtests.py expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0`,
  `exit 0`, `output digest sha256:beecfd536…` with the full
  `sha256:beecfd536410b5949febd97f2f53d21b08829afa47d552a92b015040962ff8b8`
  in the `title` attribute. C2 VERIFIED likewise (command, exit 0, full
  digest in title).
- C3 / C4 EXTERNAL-UNVERIFIABLE — criterion text + scope limitation, and
  the observation cells honestly read `not recorded` /
  `exit code not recorded` / `output digest not recorded` rather than
  inventing an observation.
- The sentence "A VERIFIED row proves only what its cited observation
  shows." now points at real cited observations in the same table.

## D5 — Digest qualifier + stale report + zero rows: FIXED

What I checked live:

- Stdout V0 line, verified case (`stdout-full.txt`):
  > `V0 verdicts: VERIFIED 2, FAILED 0, NOT OBSERVED 0, EXTERNAL-UNVERIFIABLE 2, NOT APPLICABLE 0; unknown rate 50.0%; checks digest verified against the checks file`
- Stdout V0 line, unverified case (`stdout-no-checks.txt`):
  > `…; unknown rate 50.0%; checks digest NOT verified (no --checks given; verdicts may have been judged under different checks)`
- HTML heading, unverified case (`no-checks.html`):
  `<h2>What the evidence supports (V0) &mdash; checks digest not verified</h2>`
  with the footer small print carrying the full "Checks digest shown but not
  verified (no --checks file given)…" sentence. All five verdict rows render
  with zeros in both HTML (`full.html:112`, `no-checks.html`) and stdout.
  "Runs recorded: 2, of which superseded and retained, never cited: 0."
  renders in the HTML.
- Stale report: with a report already present at `--out`, a digest-mismatch
  run exits 2, writes nothing new (the old file's mtime/content untouched),
  and prints to stderr (`stderr-stale.txt`):
  > `averth: warning: a previous report remains at …/scratch-3-verify/stale-target.html; it is NOT this run's output (this run was refused)`
  followed by the digest-mismatch error naming both hashes.
- Generation timestamp: each report stamps its own
  (`full.html`: `report generated 2026-11-11T20:12:09Z`;
  `no-checks.html`: `…20:12:14Z`), so a stale file is detectable from its
  own contents.
- Observation (not a defect): in the *verified* case the HTML heading
  carries no qualifier — only the footer small print says "Checks digest
  verified against the checks file." The dangerous direction (unverified
  verdicts presented bare) is the one that is headlined, and stdout states
  the digest state in both cases, so I do not count this against PASS.
  The dead `digest_verified is False` branch is gone (read
  `try_report.py`: `load_v0_ledger` raises on mismatch; no False branch
  remains in the rendering path I read).

## D6 — Reproduce script tautology + overclaim: FIXED

Verified by reading the script and by testing its extraction regexes
against the live outputs I produced (I did **not** execute the full
reproduce script — network downloads + Django install — same stated
limitation as my first pass):

- The tautology is gone: `try-it/reproduce-case-study.py:372-373` now
  parses the billed bucket from real stdout
  (`bucket(r"Vendor-supplied \(billed\)")`), and `:474-476` parses it
  from the HTML (`bucket_html(r"<b>Vendor-supplied</b> \(billed\)")`).
  I ran both regexes against `stdout-full.txt` and `full.html`: both
  return $0.00. A bucket-math regression now fails the script. Priced /
  estimated buckets are likewise parsed from the real Data quality lines
  in both surfaces (stdout 0.91 / 0.07, HTML 0.91 / 0.07 — verified by
  running the same expressions).
- The claim is narrowed: the docstring (`:24-30`) now says "What it
  checks: the published numbers listed in PUBLISHED below, plus a
  gold-patch cross-check and consistency checks that are not published
  numbers … What it does NOT check: the 3.84x 12-run leaderboard gap,
  the 0-tool-failures claim, and the $0.9832 unrounded total (checked
  only through its rounded parts and the ratio)."
- New checks present in the script: 72 trajectory messages, 35 meter
  model events, traj-vs-leaderboard `instance_cost` agreement (`:229-230`),
  FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88 (`:265, :269`), context-tax share
  75%, yield 100.0%, 0 superseded runs (`:433-436`).
- Wording assertions added to the combined-report step (`:477-490`):
  "characters/4" disclosure, "no cost per accepted outcome is claimed",
  "Checks digest verified", "operator-supplied", "Cited observation" +
  "output digest", all-verdicts presence. All six substrings are present
  in my live `full.html` (verified by grep, not by trusting the script).
- Weak checks tightened: ratio regex anchored to `ESTIMATED \(([0-9.]+)x\)`
  (verified: returns 3.07 against live stdout); baseline asserts the full
  `'OperationalError: near "THEN": syntax error'` line (`:300-301`).

## New defects found

### N1 (minor) — traj cross-check warning is HTML-only; stdout never surfaces it

- Location: `averth/try_report.py:333` (`try_summary_lines` signature has
  no `traj_recorded` parameter) and `averth/cli.py:419-425` (passes
  `traj_recorded` only to `build_try_extras`).
- Evidence: `stdout-wrong-recorded.txt` (live `--recorded 99` run) contains
  no `instance_cost`, no mismatch warning, no agreement line; the warning
  exists only in `wrong-recorded.html:111`.
- Exact fix: add `traj_recorded=None` to `try_summary_lines`, pass it from
  `_cmd_try`, and append one line when `recorded` and `traj_recorded` are
  both present: agreement ("Trajectory's own recorded cost $X agrees with
  the operator-supplied figure.") or warning ("WARNING: trajectory's own
  recorded cost is $X, which differs from the operator-supplied $Y.").
- Why minor, not FAIL: the D3 core fix (operator-supplied label everywhere)
  is complete, so stdout no longer states a false fact; the missing warning
  is defense-in-depth for the operator, and the shareable artifact (HTML)
  carries it.

### N2 (minor) — JSONL/Langfuse default MODEL COST BASIS still says "reported token/cache usage"

- Location: `averth/report.py:85-87` (default `model_cost_basis`,
  used when the CLI passes `None`) and `averth/cli.py:385` (`model_cost_basis`
  set only in the `traj` branch, `:394-398`).
- Evidence (live): `jsonl.html:58` —
  > `<div class="warn"><b>Model cost basis:</b> versioned list prices and reported token/cache usage. Reconcile against the customer's invoice before calling this actual spend.</div>`
  (`stdout-jsonl.txt:4` identical). The published JSONL fixture's 35 model
  events carry token counts (279,017 in / 5,077 out, counted live) with no
  `tokens_estimated` flag — counts the traj converter manufactured as
  characters/4 — so for this fixture nothing "reported" token usage, in the
  same sense D1 was false. The same report's own COST BASIS banner, bucket
  label, and source note all hedge correctly ("trace-supplied … not
  verified as recorded usage"), so the report as a whole does not mislead
  the way the old D1 did; this is one inconsistent line, and "reported"
  can be read as "reported by the trace file" for genuinely provider-sourced
  JSONL/Langfuse input.
- Exact fix: change the default `model_cost_basis` in `report.py` to
  "versioned list prices and trace-supplied token counts (not verified as
  provider-recorded usage); reconcile against the customer's invoice
  before calling this actual spend." — matching the bucket label and the
  banner. (Traj input already overrides it with the converter-estimated
  line; leave that override as is.)
- Why minor, not FAIL: D1 as specified covered traj input and the bucket
  label, both fixed; this is a residual of the same family on a path whose
  other three disclosures are honest.

## Observations (not defects)

- The bare `Fully loaded:         $0.98` line persists in stdout and in
  the README expected-output block (`try-it/README.md:106`) with no
  ESTIMATED qualifier on that line itself. I raised this in my first pass
  ("Other overclaims"); the adjudication did not adopt it, and on
  re-check I do not press it: the README block quotes real stdout
  verbatim (annotating it would make the quote false), and the same stdout
  output carries ESTIMATED three times (COST BASIS banner, disclaimer
  sentence, recorded-comparison line), so a reader of the full output is
  not misled. Noted for the record only.
- In the verified case the HTML V0 heading carries no digest qualifier
  (see D5); the unverified case — the material one — is headlined, and
  stdout states the digest state in both cases.

## Not checked (stated, not signed off)

- I did **not** execute the full `try-it/reproduce-case-study.py`
  (network downloads + Django install); D6 was verified by reading the
  script and running its extraction regexes against live `averth try`
  stdout/HTML I produced myself.
- I did **not** verify the live published page at
  `https://getaverth.com/case-study-1.html`; case-study comparisons are
  against the local source, as in the first pass.
- I did **not** check Langfuse-input honesty beyond reading its
  `source_note` (`averth/cli.py`, langfuse branch) — no Langfuse run was
  executed. N2 covers the shared default basis line that the Langfuse
  path also uses.
- I did **not** audit the V0 verifier itself or the pricing table's
  accuracy. V0 findings here concern only how `try` presents a ledger.

## Scratch evidence

- `try-it/reviews/scratch-3-verify/stdout-full.txt`,
  `stdout-no-checks.txt`, `stdout-wrong-recorded.txt`,
  `stdout-bare.txt`, `stdout-jsonl.txt`, `stdout-stale.txt`,
  `stderr-stale.txt` — live stdout/stderr of the six probed runs.
- `try-it/reviews/scratch-3-verify/full.html`, `no-checks.html`,
  `wrong-recorded.html`, `bare.html`, `jsonl.html`,
  `stale-target.html` — the HTML outputs of the probed variants
  (`stale-target.html` is the pre-existing report left in place by the
  refused run, as intended).
