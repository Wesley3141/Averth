# Review 4 — Docs clarity, THIRD RE-VERIFICATION (N1 only)

**Verdict: PASS**

The single remaining item from the second re-verification
(`review-4-docs-verify2.md`, FAIL on N1 only) is fixed and verified
live. The `ValueError` the CLI actually surfaces now says "file
name", matching the docstring and the basename-only inference rule.
No new defects found in scope. No source file was edited.

## Scope

Narrowly scoped to N1 only, per the brief. Items D1, D13, N2, N3
and the JSONL-header item from verify2 were not re-checked here;
this verdict covers N1 alone and does not re-sign off on them.

Branch: `try-it`, HEAD `81477df` ("Fix the no-model error string
to say file name, not file path"). Parent commits `0750720`
(feature) and `c1bc0cc` as briefed. Nothing was merged, pushed,
deployed, or sent to anyone.

## What I checked live (commands and outputs)

All runs used `~/workspace/averth/.venv/bin/python -m averth.cli`.
Scratch evidence: `try-it/reviews/scratch-4-verify3/no-model-run.log`.

1. **Fix commit.** `git show 81477df` is a one-line change in
   `averth/importers/miniswe.py` only: line 173 `"the file path"`
   → `"the file name"`. No other file touched by that commit.
2. **No-model error, live.** `averth try
   try-it/fixtures/django-15930.traj.json` with NO `--model`
   (fixture filename `django-15930.traj.json` carries no model
   name) exited **2** with:
   `averth: error: failed to parse
   try-it/fixtures/django-15930.traj.json (traj): no model named
   for try-it/fixtures/django-15930.traj.json: pass --model (e.g.
   --model claude-sonnet-4-20250514) or put the model name in the
   file name`
   — contains "file name" (1 occurrence in the log), contains
   "file path" **0** times. This is the exact condition the brief
   specified, and it passes.
3. **Docstring agreement.** `miniswe_events` docstring,
   `averth/importers/miniswe.py:154`, still reads "put the model
   name in the file name". It agrees word-for-word with the
   `ValueError` at lines 172–173 ("or put the model name in the
   file name"). The docstring/error split from verify2 is gone.
4. **Residual wording grep.** `grep -rn "in the file path"
   averth/importers/miniswe.py try-it/README.md` returns no
   matches. Broader `grep -rn "file path"` over the same two
   files also returns no matches. The README's model-naming
   wording (lines 58–63) already uses "file name" only
   ("Required unless the file name contains …", "only the file
   name … inferred from the file name").

## Item verdict

- **N1 — FIXED.** The user-facing error now says "file name",
  verified live (exit 2, check 2), the docstring agrees
  (check 3), and no "in the file path" / "file path" wording
  about model naming remains in `miniswe.py` or
  `try-it/README.md` (check 4).

## New defects found

None in scope. No exact file/line fix to propose.

## Not checked / not signed off

- D1, D13, N2, N3 and the JSONL-header item from verify2 were
  not re-checked in this round (out of scope by design).
- Python 3.9 specifically was not tested (same gap as before).
- No other error strings, importers, or README sections were
  audited beyond the greps above.

## Files

- Review: `try-it/reviews/review-4-docs-verify3.md` (this file)
- Scratch: `try-it/reviews/scratch-4-verify3/no-model-run.log`
  (live no-model run, exit 2, full stderr plus exit line)
