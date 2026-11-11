# Adjudication of the 5 first-pass reviews (2026-11-11)

All five reviewers returned FAIL. Every published figure recomputes
exactly (reviewer 2: 14/14); the failures are labels, error paths,
hardening, docs, and certification gaps. This file records what was
adopted, what was rejected, and why, so the re-verification reviewers
can check the decisions, not just the diffs.

## Adopted

- **Priced-bucket relabel (numbers D1, honesty D1-minimum, docs
  D15.4):** the Data quality label drops "recorded tokens" and now
  reads "vendor list prices on trace-supplied token counts, not
  verified as provider-recorded usage" (text report and HTML). No
  number changes: the split stays $0.91 / $0.07 / $0.00.
- **Per-completed-run labels (honesty D2):** `averth try` threads a
  try-mode label override through the shared report: card sub-label
  "per completed run", heading "Cost per completed run", stdout
  heading carries "(not per accepted outcome ...)", "Reopened"
  drops "accepted outcomes reopened", and the "No human accepted
  this run" sentence prints on stdout on every try run.
- **Recorded-cost relabel + cross-check (honesty D3):** "Recorded
  cost (operator-supplied ...)" everywhere; the declarative sentence
  now says the operator supplied the figure; when the trajectory
  carries `info.model_stats.instance_cost` it is surfaced and a
  mismatch warns. Help text, module docstring, and README corrected.
- **V0 table cites its observations (honesty D4):** per-row criterion
  text, command, exit code, output digest (truncated, full value in
  the title attribute).
- **Digest qualifier on stdout + heading (honesty D5):** the stdout
  V0 line and the HTML heading state the digest state; a refused
  digest-mismatch run warns when a stale report remains at `--out`;
  the report carries its own generation timestamp; the dead
  `digest_verified is False` branch is deleted.
- **All five verdict rows render with zeros (usability D9, numbers
  D4, honesty D5-minor):** HTML table and stdout line.
- **Unknown-model rejection + model discovery (usability D1/D2):**
  `averth try` on a trajectory refuses an `--model` (or inferred
  model) that is not in the price table (exit 2, names `averth
  pricing`); `averth pricing` lists every priced model name.
- **Format-error clarity (usability D3/D4/D5, engineering D5):**
  explicit-format parse failures name the detected format when
  detection disagrees; JSON-but-no-shape no longer suggests
  `--format`; empty files get their own error; binary/non-UTF-8
  and directory inputs get actionable messages; single-line JSONL
  detects; the line scan looks past a typeless first line (first
  10 non-blank lines); empty exports exit 2 with no report.
- **Missing ledger/checks errno (usability D6, engineering D3):**
  `load_v0_ledger` raises ValueError naming the flag for missing
  files and validates ledger shapes (judgments a list of dicts,
  counts a dict of numbers, unknown_rate a number or None,
  runs_total an int); `build_try_extras` / `try_summary_lines`
  failures in `_cmd_try` honor the `averth: error:` / exit-2
  contract.
- **Non-finite recorded (engineering D2):** `nan` / `inf` refused
  in the CLI and in `build_try_extras` / `try_summary_lines`.
- **HTML injection (engineering D1):** `source_note` escaped at the
  sink in `build_try_extras`.
- **Converter hardening (engineering D4/D8):** non-string text
  parts contribute nothing; non-dict messages are a clean
  ValueError naming the index; non-dict `info` is tolerated;
  files open as UTF-8; model inference matches the basename only
  with non-alphanumeric boundaries; the bash-fence rule accepts a
  trailing space / missing newline / `BASH`; exit-status match is
  documented as exact and case-sensitive.
- **Byte-identity (engineering D6):** the try-extras block is
  inserted only when non-empty, so `try_extras=None` output is
  byte-identical to the pre-change report; pinned by a test.
- **Reproduce script (honesty D6, numbers D2/D3/D5/D6, engineering
  D7, docs D11/D12):** billed/priced/estimated buckets parsed
  from the real Data quality lines in stdout and HTML; ratio
  regex anchored; unknown rate compared at 2 dp; baseline asserts
  the full `OperationalError: near "THEN"` line; new checks for 72
  trajectory messages, 35 meter model events, traj-vs-leaderboard
  `instance_cost` agreement, FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88,
  context-tax share 75%, yield 100.0%, 0 superseded runs; the
  "checks every published number" claim narrowed to an explicit
  list of what is and is not checked; the checks table prints on
  mid-run failure; `--force` refuses `/`, cwd, the repo root,
  `$HOME`, and repo ancestors, and refuses a work-dir that is a
  file; `curl --fail` plus immediate JSON validation of the
  trajectory; PyPI listed as a prerequisite; measured runtime
  (74 s on 2026-11-11) replaces "a few minutes"; the "checkout
  never modified" sentence corrected (work dir + egg-info).
- **README + root README + CHANGELOG (docs D1-D16, usability
  D7/D8/D10/M1-M6):** clone/checkout/cd, "run from the repo root",
  curl in prerequisites, `averth` console-script form, `--out`
  default corrected in both places, "Look for these lines" with
  real order/indentation, `--format auto` and detection rules,
  `--model` precedence + ignored-for-JSONL/Langfuse, `--recorded`
  positivity + `cost` field + zero-success case, runnable
  `--ledger`/`--checks` example, `--agent` defaults, reproduce
  `--force`/work-dir notes, conversion-section corrections
  (no end event without exit status, parsed-events regression
  test, exact fence rule, integer division), a "Trace formats"
  section with examples, terminology fixes ("Retries: 0",
  scoped no-network lede, "per completed run" naming), root
  README try-it pointer scoped to the unmerged branch, CHANGELOG
  claim qualified.

## Rejected / deferred (with reasons)

- **Honesty D1-preferred (set `tokens_estimated`, split becomes
  $0.00 priced / $0.98 estimated, republish the case study):**
  REJECTED for this branch. It directly contradicts the task's
  acceptance criterion (reproduce $0.91 priced exactly; any
  mismatch is a defect) and would require republishing the live
  case-study page. That is a Wesley decision, not a reviewer fix.
  The minimum fix (adjacent relabel + chars/4 disclosure in
  stdout and in the report) is adopted instead. Flagged for the
  parent in the final report.
- **Usability D1's `--allow-unpriced-model` flag:** not added.
  Rejection is the fix; the meter's fallback pricing remains
  available on its other paths. A stranger who genuinely needs
  an unpriced model can ask for the flag later.
- **Engineering D9 (bounded prefix read for huge traces):**
  noted, not fixed. No performance failure was measured
  (20k-message trajectories convert in 0.08 s); the detector now
  reads the file once instead of twice.
- **Reviewer 2's `tracker.py:788` observation (estimated_model
  overwrite):** noted, out of scope for the try-it branch; it has
  no effect on any figure here.
- **Docs D7(1) vs engineering D8 conflict:** docs said "the
  directory counts too" for model inference; engineering said
  match the basename with boundaries. Engineering wins (less
  surprising, kills the `notes-about-gpt-4o` false positive);
  the README documents the new behavior.

## Re-verification

The same five reviewers re-verify against this adjudication and
their own review files. Each writes a `-verify` file with PASS/FAIL.
