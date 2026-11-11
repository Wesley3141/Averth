# Review 1 — Usability for a stranger: RE-VERIFICATION

**Verdict: FAIL**

**Reviewer:** reviewer 1 of 5, angle: usability for a stranger (re-verification pass).
**First-pass review:** `try-it/reviews/review-1-usability.md` (FAIL, D1–D12 + M1–M6).
**Adjudication:** `try-it/reviews/adjudication.md` (read in full first).
**Branch:** `try-it` (unmerged; nothing merged, pushed, deployed, or sent by me).
**Repo:** `~/workspace/averth`. All commands run as
`~/workspace/averth/.venv/bin/python -m averth.cli` from
`try-it/reviews/scratch-1-verify/` unless stated otherwise.
**Scratch evidence:** `try-it/reviews/scratch-1-verify/` (64 files:
logs `f-*.log`, `t1-case-study.log`, generated HTML, malformed inputs,
and the clean-clone logs `f-clone.log`, `f-checkout-tryit.log`,
`f-clean-venv.log`, `f-clean-install.log`, `f-clean-try-help.log`).
Every command below was actually run; log filenames are given so any
finding can be re-run verbatim.

## Summary

11 of 12 numbered defects and all 6 minors are FIXED live, including
both first-pass blockers: an unknown/typo'd `--model` is now refused
(exit 2, no report written) and `averth pricing` lists the model
names. The failure is carried by exactly one defect, **D8 (PARTLY)**:
the clone/checkout commands are now printed in the README, but they
do not work literally from a clean directory — `git checkout try-it`
fails because the `try-it` branch was never pushed to origin
(`git ls-remote origin try-it` returns nothing; a literal fresh clone
plus checkout exits 1). A stranger following the README's first three
commands cannot obtain the code that contains `averth try` at all,
and the clean-clone cascade ends at argparse's "invalid choice" error
— the exact failure D8 existed to prevent. That is a stranger-facing
FAIL, not a wording nit. Five new minor defects (N1–N5) are listed at
the end; N1 is the D8 root cause restated as its own defect with its
fix.

## What I re-checked and still passes (live, not from the diff)

- **Case-study run reproduces exactly** (`t1-case-study.log`):
  `Retries: 0`, `Fully loaded: $0.98`, `Recorded cost
  (operator-supplied): $0.3205; metered estimate per completed run:
  $0.98 ESTIMATED (3.07x)`. HTML `case-study-recorded.html` contains
  $0.91 / $0.07 / $0.00, 9.9x, $0.68, 3.07x, $0.3205.
- **Auto-detection, model inference, ledger/digest paths** still
  behave as first pass: JSONL + unknown `--model` meters $0.98
  (`--model` correctly ignored for JSONL, `f-jsonl-model-ignored.log`);
  a file named `claude-sonnet-4-20250514-traj.json` with no `--model`
  reproduces $0.98 (`f-infer.log`); a model name in the directory
  only is correctly NOT inferred (`f-dir-infer.log`, exit 2 asking
  for `--model`); `--checks` without `--ledger` refused
  (`f-checks-noleder.log`); a tampered checks file refuses the whole
  report with a digest mismatch and writes no HTML
  (`f-digest-mismatch.log`); no `--model` on a plain-named file
  exits 2 naming the fix (`f-nomodel.log`).

## What I did NOT check

- **I did not run `try-it/reproduce-case-study.py` end to end.**
  Same scope exclusion as the first pass: it needs a Django checkout
  + install and several minutes. Its `--help` parses; the README's
  relative invocation still fails from any cwd other than the repo
  root (`f-repro-wrongcwd.log`), which the README now warns about
  globally (see D7).
- I did not test on Python 3.9/3.10 (only 3.12.3 here), macOS, or
  Windows.

---

## Per-defect re-verification

### D1 (BLOCKER) — Unknown/typo'd `--model` — FIXED

**Code:** `averth/cli.py:307–315` (refusal before metering, names
`averth pricing`).

```
$PY try django-15930.traj.json --model gpt-99-nonexistent --out badmodel.html
exit=2
averth: error: unknown model 'gpt-99-nonexistent': not in the Averth price table; run 'averth pricing' to list priced models
# badmodel.html: no such file (f-badmodel.log)

$PY try django-15930.traj.json --model claude-sonnet-4-2025051 --out badmodel2.html
exit=2
averth: error: unknown model 'claude-sonnet-4-2025051': not in the Averth price table; run 'averth pricing' to list priced models
# badmodel2.html: no such file (f-badmodel-typo.log)
```

Exact wording matches the first-pass fix request verbatim. No report
is written, no WARNING-buried fallback, exit 2. One nuance, behavior
not defect: an unpriced name in the file path
(`gpt-99-nonexistent-traj.json`, no `--model`) is refused via a
different message — `failed to parse ... (traj): no model named for
...: pass --model ... or put the model name in the file path`
(`f-badmodel-inferred.log`, exit 2, no HTML) — because
`_infer_model` (`averth/importers/miniswe.py:76`) only ever returns
priced names, so an inferred unpriced model cannot occur. The intent
(no confident wrong report from a typo) is fully satisfied either
way.

### D2 (BLOCKER) — No way to discover a valid `--model` — FIXED (with new minor N2)

**Code:** `averth/cli.py:462–465` (`_cmd_pricing` lists every key).

`averth pricing` (`f-pricing.log`, exit 0) now prints `models priced
: 35` followed by 35 indented bare names, including
`claude-sonnet-4-20250514` and `gpt-4o`. The README's `--model`
bullet (lines 55–56) adds "list priced models with `averth
pricing`". Caveat recorded as new minor N2: three bare names appear
twice each (`glm-5`, `glm-5-high`, `glm-5.3` — the price table holds
both `unknown:` and `zai:` keys for each at identical prices), so 35
lines cover 32 distinct bare names. `--model glm-5` still resolves
and meters ($0.37, `f-glm5.log`), so this is cosmetic confusion, not
a blocker — but a stranger counting lines against "35 models" will
notice the duplicates.

### D3 — Wrong `--format` leaks parser jargon — FIXED

All three first-pass cases now name the detected format
(`averth/cli.py:330–341`):

```
$PY try django-15930.traj.json --format jsonl ...
exit=2
averth: error: django-15930.traj.json does not parse as jsonl (line 1: invalid JSON: ...); it may be another format -- try --format auto or one of traj|jsonl|langfuse; auto-detection says this looks like traj
# f-wrongfmt-jsonl.log; no HTML written

$PY try trace.jsonl --format traj ...   → "... does not parse as traj (Extra data: ...); ...; auto-detection says this looks like jsonl"  (f-wrongfmt-traj.log)
$PY try trace.jsonl --format langfuse → "... does not parse as langfuse (Extra data: ...); ...; auto-detection says this looks like jsonl"  (f-wrongfmt-langfuse.log)
```

### D4 — Unsupported files told to "pass --format explicitly" — FIXED

`averth/cli.py:212,243–255` (`_detect_try_format`):

- JSON object with neither key (`f-unsupported-json.log`, exit 2):
  `... is JSON but none of the supported shapes: a mini-SWE-agent
  trajectory is a JSON object with a 'messages' key; a Langfuse
  export is a JSON object with a 'data' key or a bare JSON list;
  JSONL is one event object with a 'type' key per line` — no
  `--format` suggestion anywhere in the message.
- Plain text (`f-unsupported-txt.log`, exit 2): names all three
  shapes with their one-line definitions.
- Empty file (`f-empty.log`, exit 2): `empty.json is empty` — its own
  error, as required.

### D5 — Binary file / directory — FIXED

- Binary (`f-binary.log`, exit 2): `binary.bin is not readable text
  (binary or non-UTF-8); supply a .traj.json, JSONL, or Langfuse
  JSON export` — no codec error, no byte offset.
- Directory (`f-dir.log`, exit 2): `elsewhere is a directory; pass a
  trace file, not a directory` — no longer "file not found".

### D6 — Missing `--ledger` gives a bare errno — FIXED

`averth/try_report.py:75–78` (and checks equivalent):

```
$PY try django-15930.traj.json --model ... --ledger nope.json --out led1.html
exit=2
averth: error: V0 ledger file not found: nope.json (passed via --ledger)
# led1.html: no such file (f-ledger-missing.log)
```

Bonus verified beyond the first-pass ask: a missing `--checks` file
is wrapped the same way — `averth: error: checks file not found:
nope-checks.json (passed via --checks)` (`f-checks-missing.log`,
exit 2, no HTML).

### D7 — README commands assume repo-root cwd — FIXED (with new nit N4)

`try-it/README.md:10–11` now states: "Run every command below from
the repository root (the directory containing `pyproject.toml`)
unless told otherwise." Verified live from `scratch-1-verify/` that
the relative forms still fail there as before (`f-relpath.log`,
exit 127 for `../averth-venv/bin/python`; `f-repro-wrongcwd.log`,
exit 2 for `python3 try-it/reproduce-case-study.py`) — the failure
mode is unchanged, but it is now a documented precondition instead
of a silent assumption, which is what the fix asked for. Nit (N4):
the reproduce section itself never repeats the cwd requirement next
to its invocation; only the global Install line covers it.

### D8 — No clone/checkout instructions and no repo URL — PARTLY (FAIL driver)

The text fix is present: `try-it/README.md:14–16` now gives

```
git clone https://github.com/Wesley3141/Averth.git
cd Averth
git checkout try-it
```

and line 24–25 adds the invalid-choice pointer
("If `averth try` reports an invalid choice, you are not on the
`try-it` branch (`git branch --show-current`)"). But the commands do
not work literally from a clean directory — the branch does not exist
on the remote. Verified live:

```
$ git ls-remote origin try-it        # (empty — no such ref on origin)
$ git ls-remote origin HEAD          # 1431bef... (remote reachable; not a network issue)
$ rm -rf /tmp/clean-clone-test && git clone https://github.com/Wesley3141/Averth.git
# clone exit=0 (f-clone.log)
$ cd /tmp/clean-clone-test/Averth && git checkout try-it
# checkout exit=1 (f-checkout-tryit.log)
# error: pathspec 'try-it' did not match any file(s) known to git
```

The cascade, also run live in the clean clone (`f-clean-venv.log`,
`f-clean-install.log`, `f-clean-try-help.log`): `python3 -m venv
../averth-venv` exits 0, `pip install -e .` exits 0 (installs
averth-0.3.0 from master), then `averth try --help` exits 2 with
`averth: error: argument cmd: invalid choice: 'try' (choose from
'trace', 'simulate', 'pricing', 'advise')`. So a stranger who follows
the README exactly lands on master, gets the invalid-choice error
the README's pointer line anticipates, and has no way to reach the
branch the pointer tells them they need — there is no `try-it` ref to
check out. (Clean clone deleted afterwards, `/tmp/clean-clone-test`
removed.) This is restated as new defect N1 with the fix. The text
addition alone does not satisfy "instructions work literally from a
clean directory", which was the re-verification brief for this
defect.

### D9 — V0 summary promises "0 FAILED", CLI never prints/renders zero — FIXED

`averth/try_report.py:231–238` (HTML, all five rows via
`_VERDICT_ORDER`) and `try_summary_lines` (stdout, all five counts).
Live ledger+checks run (`f-ledger-ok.log`, exit 0):

```
V0 verdicts: VERIFIED 2, FAILED 0, NOT OBSERVED 0, EXTERNAL-UNVERIFIABLE 2, NOT APPLICABLE 0; unknown rate 50.0%; checks digest verified against the checks file
```

`with-v0.html` contains all five rows with counts 2 / 0 / 0 / 2 / 0
(verified by grep on the `<th>…</th><td class="r">…</td>` rows).
Matches the README's "(2 VERIFIED, 0 FAILED, 2
EXTERNAL-UNVERIFIABLE, 50.0% unknown rate)" with the two extra zero
rows now visible rather than silently dropped.

### D10 — Default `--out` wording wrong, report lands in cwd — FIXED

README line 82–86 now reads: "Default: `<stem>-try.html` in the
current directory, where `<stem>` is the trace filename without
`.traj.json` (or `.json`)". `--help` uses the identical sentence
("default: <stem>-try.html in the current directory..."). Live:
running from `scratch-1-verify/` against `elsewhere/remote.traj.json`
with no `--out` wrote
`scratch-1-verify/remote-try.html` (cwd), and no
`elsewhere/remote-try.html` exists (`f-remote-trace.log`). Wording
and behavior now agree, in both places.

### D11 — Failed `--out` prints the full success-looking report first — FIXED

`averth/cli.py:283–302` validates the parent directory before any
metering or printing. Live (`f-badout.log`):

```
$PY try django-15930.traj.json --model ... --out /nonexistent-dir-xyz/report.html
exit=2
averth: error: cannot write HTML report to /nonexistent-dir-xyz/report.html: the directory /nonexistent-dir-xyz does not exist
```

The log file is exactly 1 line: no meter report, no P&L, no
"success-looking" output before the error. (One wording wrinkle is
new minor N5: when the parent path exists as a *file*, the same
branch reports "the directory ... does not exist", which is false —
it exists but is not a directory. Verified live in
`f-badout-fileparent.log`.)

### D12 — Re-running silently overwrites the previous report — FIXED

`averth/cli.py:377–382` refuses an existing `--out` unless `--force`:

```
$PY try ... --out case-study.html            # case-study.html already exists from t1 run
exit=2
averth: error: /home/hatch/.../scratch-1-verify/case-study.html already exists; pass --force to overwrite it
# f-rerun.log; file mtime/size unchanged (2026-11-11 20:12:13, 9862 bytes)

$PY try ... --out case-study.html --force
exit=0
averth: warning: overwriting existing report at /home/hatch/.../scratch-1-verify/case-study.html
HTML report written to /home/hatch/.../scratch-1-verify/case-study.html
# f-rerun-force.log
```

Default-`--out` path checked too: first run writes
`django-15930-try.html`, the second identical run exits 2 with the
same refusal (`f-default1.log`, `f-default2.log`). The first-pass
accident (a bad run destroying a good report) can no longer happen
silently.

### M1 — Prerequisites incomplete and misattributed — FIXED (with new nit N3)

`try-it/README.md:21–22`: "Prerequisites: Python 3.9 or newer,
`curl` (for the download below), and git (for the reproduction script
below)." All three tools are now named. Nit (N3): git is still
attributed only to the reproduction script, although D8's fix makes
git the tool that obtains the checkout in the first place.

### M2 — "Expected output lines" reads as the whole output — FIXED

`try-it/README.md:101–107`: "The run prints a full report (about 50
lines). Look for these lines in the output, in this order:" followed
by the three-line block. Verified byte-exact against
`t1-case-study.log`: `Retries:               0` (log line 10),
`  Fully loaded:         $0.98` (line 17), `Recorded cost
(operator-supplied): $0.3205; metered estimate per completed run:
$0.98 ESTIMATED (3.07x)` (line 48) — same order, same indentation.

### M3 — `--model` precedence undocumented — FIXED

README lines 57–58: "An explicit `--model` overrides the name
inferred from the file name." Verified live: a file named
`claude-sonnet-4-20250514-traj.json` with `--model gpt-4o` meters
$0.82 with `openai:gpt-4o` in the model mix (`f-precedence.log`,
`f-precedence.html`); without the flag the same file meters $0.98
(`f-infer.log`).

### M4 — Empty Langfuse export exits 0 with a $0.00 report — FIXED

`averth/cli.py:352–355` (zero-attempt refusal after tracker build).
Both empty shapes exit 2 with no HTML:

```
$PY try langfuse-empty.json            # {"data": []}
exit=2
averth: error: langfuse-empty.json contains no traces (empty export); nothing to meter
# f-langfuse-empty.log; lf-empty.html does not exist

$PY try langfuse-empty2.json           # []
exit=2
averth: error: langfuse-empty2.json contains no traces (empty export); nothing to meter
# f-langfuse-empty2.log; lf-empty2.html does not exist
```

### M5 — No `--force`/overwrite flag exists — FIXED

`--force` exists, is in `try --help` ("Overwrite an existing --out
file instead of refusing."), and behaves as verified under D12
(refusal without it, stderr warning + overwrite with it).

### M6 — `openai:`/`anthropic:` prefixing never explained — FIXED

README lines 62–65: "The report shows the model as
`provider:model` (for example `anthropic:claude-sonnet-4-20250514`):
the provider prefix is guessed from the model name by Averth, it is
not part of what you typed." `--help` for `--model` carries the
same pointer ("List priced models with 'averth pricing'").

---

## New defects found in this pass

**N1 (BLOCKER, root cause of D8-PARTLY) — The `try-it` branch does
not exist on origin, so no stranger can check it out.**

- **File/evidence:** remote state, not a source file:
  `git ls-remote origin try-it` → empty; literal fresh clone +
  `git checkout try-it` → exit 1, `error: pathspec 'try-it' did not
  match any file(s) known to git` (`f-checkout-tryit.log`); remote
  branches are only `master`, `case-study-1`,
  `criterion-c-checks-digest`, `release/v0.3.0`, `v0-evidence-verifier`,
  `v0.2-product`, `validation-fixes`, `validation-fixes-live-agent`.
- **Fix:** push the `try-it` branch to origin
  (`git push -u origin try-it`) — this is a publish step, so it needs
  Wesley's explicit tap; do not do it as part of a review fix. If the
  branch is deliberately not pushed yet, the README must say so
  plainly and give a real way to obtain the code (e.g. "the `try-it`
  branch is unmerged and not yet pushed; until it is, this command
  is only runnable from a checkout that already has the branch"),
  rather than printing clone/checkout commands that fail.

**N2 (minor) — `averth pricing` lists three bare model names twice.**

- **File:** `averth/cli.py:462–465` (`for key in
  sorted(pricing.MODEL_PRICES): print("    %s" %
  key.split(":", 1)[-1])`); table `averth/pricing.py:135–143` holds
  both `unknown:glm-5{,-high,.3}` and `zai:glm-5{,-high,.3}` at
  identical prices.
- **Effect:** 35 lines for 32 distinct bare names; `glm-5`,
  `glm-5-high`, `glm-5.3` each appear twice, so "models priced: 35"
  does not match a stranger counting distinct names. `--model glm-5`
  still resolves (verified, $0.37), so nothing is broken.
- **Fix:** dedupe the bare names in the listing (or print the full
  `provider:model` keys so the duplicates are visibly distinct
  entries).

**N3 (nit) — Prerequisites line still attributes git only to the
reproduction script.**

- **File:** `try-it/README.md:21–22`: "and git (for the reproduction
  script below)".
- **Fix:** "and git (to obtain the checkout, and for the
  reproduction script below)."

**N4 (nit) — Reproduce section never repeats the cwd requirement
next to its invocation.**

- **File:** `try-it/README.md`, "Reproduce the case study" section
  (`python3 try-it/reproduce-case-study.py`); only the global
  Install line (lines 10–11) states the repo-root requirement.
- **Fix:** one line in that section: "Run this from the repository
  root."

**N5 (minor) — Bad `--out` parent-is-a-file message claims the
directory "does not exist".**

- **File:** `averth/cli.py:296–301`: `if not
  os.path.isdir(parent)` reports "the directory %s does not exist".
  Verified live: `--out plain-name.traj.json/report.html` (parent is
  an existing file) yields `... the directory
  .../plain-name.traj.json does not exist`
  (`f-badout-fileparent.log`, exit 2, correct refusal, wrong reason).
- **Fix:** distinguish the cases — if the parent exists but is not a
  directory, say "… is not a directory"; only say "does not exist"
  when it is absent.

---

## Verdict rationale

D1 and D2 (the first-pass blockers) are genuinely fixed and verified
live, as are D3–D7, D9–D12, and M1–M6. The FAIL rests on D8 alone:
the README's install path is now written down but is not executable
by the person it is written for, because the branch it tells them to
check out is not on the remote. A stranger's first three commands
fail, and the only fallback the README offers (the invalid-choice
pointer) points at a branch they cannot obtain. Until N1 is fixed —
push the branch (Wesley's tap) or rewrite the README to be honest
about the branch's availability — a stranger cannot reach `averth
try` from the published instructions, however good the command itself
now is.
