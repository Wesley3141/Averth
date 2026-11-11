# Review 1 — Usability for a stranger (adversarial)

**Verdict: FAIL**

**Reviewer:** reviewer 1 of 5, angle: usability for a stranger.
**Branch:** `try-it` (unmerged; nothing merged, pushed, deployed, or sent).
**Repo:** `~/workspace/averth`. All commands run as
`~/workspace/averth/.venv/bin/python -m averth.cli` from a clean shell
in `try-it/reviews/scratch-1/` unless stated otherwise.
**Scratch evidence:** `try-it/reviews/scratch-1/` (logs `f-*.log`,
`t1-case-study.log`, generated HTML, and the malformed inputs used).
Every command below was actually run; log filenames are given so any
finding can be re-run verbatim.

## What I did

Read `try-it/README.md` first, then `averth/importers/miniswe.py`,
`averth/try_report.py`, the `try` subcommand in `averth/cli.py`, and
`try-it/reproduce-case-study.py`. Then followed the README as a
stranger would: ran the case-study command, the documented install in
a throwaway venv, the `curl` download, and the failure paths a
stranger will hit (no `--model`, wrong `--format`, missing file,
unsupported file, `--checks` without `--ledger`, `--recorded 0` /
negative / non-numeric, unknown model, directory as input, binary
input, empty inputs, bad `--out`, `--ledger` missing / not-a-ledger /
digest mismatch, default `--out`, model-name inference from path,
auto-detection on every fixture shape, Langfuse-shaped inputs, and
the README's relative-path commands from a non-root cwd).

## What passed (checked, not assumed)

- **Case-study run reproduces exactly.** `t1-case-study.log`: Fully
  loaded $0.98, Retries 0, `Recorded cost: $0.3205; metered estimate
  per completed run: $0.98 ESTIMATED (3.07x)` — all three README
  expected lines present. The clean HTML (`clean-case-study.html`)
  contains $0.91 priced, $0.07 estimated, $0.00 billed, 9.9x input
  growth, $0.68 context tax, $0.3205, 3.07x, and the "not a bill"
  language. The `curl` URL in the README is live (HTTP 200, 69,126
  bytes, byte-identical to `try-it/fixtures/django-15930.traj.json`).
- **Auto-detection is right on every fixture shape.** traj, JSONL
  (`trace.jsonl` → $0.98), and both Langfuse shapes (`{"data": [...]}`
  and a bare JSON list) all auto-detect and meter. Content beats
  extension: JSONL content in a file named `renamed.traj.json`
  correctly meters as JSONL.
- **Model inference from the file path works.** A copy named
  `claude-sonnet-4-20250514-traj.json` with no `--model` reproduces
  $0.98 / 3.07x (`f-infer.log`).
- **Default `--out` name is sensible** (`my-run.traj.json` →
  `my-run-try.html`, `.traj` stripped correctly).
- **Good clean errors, exit 2, no tracebacks:** missing trace file
  (`f-missing.log`), no `--model` (`f-nomodel.log` — names the fix and
  gives an example), `--checks` without `--ledger`
  (`f-checks-noleder.log`), `--recorded 0` and `--recorded -1`
  (`f-recorded0.log`, `f-recorded-neg.log`), empty `messages`
  (`f-emptymsgs.log`).
- **Digest mismatch refuses the whole report and writes nothing.**
  `f-digest-mismatch2.log` (fresh `--out should-not-exist.html`):
  exit 2, no file created. Ledger-with-checks and ledger-without-
  checks both work and the HTML correctly says "Checks digest
  verified" vs "shown but not verified" (`with-v0.html`,
  `with-v0-nochecks.html`). V0 stdout line matches the published
  counts except for defect 9 below.
- **HTML is genuinely self-contained:** 0 `http` references in
  `django-15930-try.html` and `with-v0.html`.
- **Install as written works.** Fresh venv + `pip install -e .`
  from the repo root, then `averth pricing` runs (test venv deleted
  afterwards). `--help` is accurate; `--agent` renames the report
  header.
- **No tracebacks anywhere in ~30 runs.** The failure mode is never a
  crash; it is a misleading success or a misleading message, which
  is worse for a stranger because there is nothing to google.

## What I did NOT check

- **I did not run `try-it/reproduce-case-study.py` end to end.**
  It needs a Django checkout + install and several minutes; the
  README's claims about its output are therefore unverified by me.
  A prior run's artifacts exist under `try-it/repro-work/`, but I did
  not re-run it and do not sign off on it. (I did verify
  `--help` parses and that the README's relative invocation
  `python3 try-it/reproduce-case-study.py` fails from any cwd other
  than the repo root — see defect 7.)
- I did not test on Python 3.9/3.10 (only 3.12.3 here), macOS, or
  Windows, so the README's "Python 3.9 or newer" and its
  Unix-only `../averth-venv/bin/python` paths are unverified on
  those platforms.

---

## Defect 1 (BLOCKER) — A typo'd or unknown `--model` silently produces a plausible wrong report, exit 0

**File:** `averth/cli.py`, `_cmd_try` (~line 228) → `miniswe.load_miniswe`
with no model validation; fallback pricing happens downstream in the
tracker, invisible to `try`.

**What I did:**

```
python -m averth.cli try django-15930.traj.json --model gpt-99-nonexistent
```

**What happened** (`f-badmodel.log`): exit **0**, a full
successful-looking report, `Fully loaded: $0.36` (vs the true
$0.98), and an HTML file written. The only signal is a `WARNING`
buried mid-output ("$0.29 of model spend is ESTIMATED (no vendor
price for: openai:gpt-99-nonexistent)") plus a `COST BASIS:
ESTIMATED` banner. Nothing says "unknown model", nothing fails,
nothing suggests the correct name. The model is also silently
re-prefixed `openai:gpt-99-nonexistent` with no explanation of
where the `openai:` came from. A stranger who mistypes one digit
(`claude-sonnet-4-2025051`) gets a confident, shareable, wrong
report — the exact failure this tool's honesty claims exist to
prevent.

**Exact fix:** in `_cmd_try`, after the traj path is known and
before metering, reject a `--model` (and a path-inferred model)
that is not in `pricing.MODEL_PRICES`, exit 2 with
`averth: error: unknown model '<name>': not in the Averth price table;
run 'averth pricing' to list priced models` (which requires defect 2
to be fixed first so the list exists). If fallback pricing is ever
wanted, gate it behind an explicit `--allow-unpriced-model` flag.
Never write an HTML report for an unpriced model by default.

## Defect 2 (BLOCKER) — There is no way for a stranger to discover a valid `--model` string

**Files:** `averth/cli.py`, `_cmd_pricing` (~line 353); `try-it/README.md`
lines 37–38.

**What I did:** ran `averth pricing` (`f-pricing.log`); read the
README's `--model` bullet, which says only "for example
`claude-sonnet-4-20250514`".

**What happened:** `averth pricing` prints `models priced : 35`
and never lists a single name. The only source of valid names is
reading `averth/pricing.py` source (35 keys, e.g.
`anthropic:claude-sonnet-4-20250514`). A stranger with their own
trajectory has to guess the exact string, and defect 1 means a
wrong guess is silently accepted. The README gives one example and
no pointer to a list.

**Exact fix:** make `averth pricing` list the priced model names
(one per line, or a `--models` flag if the default output must stay
short), and add one line to the README's `--model` bullet:
"List priced models with `averth pricing`." Do not ship defect 1's
fix without this one.

## Defect 3 — Wrong `--format` leaks raw JSON-parser jargon and never hints the format choice is the problem

**File:** `averth/cli.py`, `_cmd_try` (~lines 259–266): the generic
`except Exception` wraps the importer error verbatim.

**What I did:**

```
python -m averth.cli try django-15930.traj.json --format jsonl --model claude-sonnet-4-20250514
python -m averth.cli try trace.jsonl --format traj --model claude-sonnet-4-20250514
python -m averth.cli try trace.jsonl --format langfuse
```

**What happened** (`f-wrongfmt-jsonl.log`, `f-wrongfmt-traj.log`,
`f-wrongfmt-langfuse.log`):

```
averth: error: failed to parse django-15930.traj.json (jsonl): line 1: invalid JSON: Expecting property name enclosed in double quotes: line 2 column 1 (char 2)
averth: error: failed to parse trace.jsonl (traj): Extra data: line 2 column 1 (char 133)
averth: error: failed to parse trace.jsonl (langfuse): Extra data: line 2 column 1 (char 133)
```

A stranger reads "invalid JSON / Extra data" and concludes their
file is corrupt. Nothing says "this file does not look like
`<fmt>`" or "you picked the wrong `--format`". The most likely
stranger mistake (forcing a format, or a file whose extension
lies) produces the least actionable message in the CLI.

**Exact fix:** when an explicitly-passed `--format` fails to parse,
rephrase to `averth: error: <file> does not parse as <fmt> (<parser
detail>); it may be another format — try --format auto or one of
traj|jsonl|langfuse`. Better: on explicit-format parse failure, run
`_detect_try_format` and, when it disagrees, name the detected
format: `...; auto-detection says this looks like <detected>`.

## Defect 4 — Unsupported files are told to "pass --format explicitly" when no format will save them

**File:** `averth/cli.py`, `_detect_try_format` (~lines 182–226).

**What I did:**

```
echo '{"hello": "world"}' > not-a-trace.json
python -m averth.cli try not-a-trace.json
echo 'hello world, this is not json at all' > not-a-trace.txt
python -m averth.cli try not-a-trace.txt
printf '' > empty.json
python -m averth.cli try empty.json
```

**What happened** (`f-unsupported-json.log`, `f-unsupported-txt.log`,
`f-empty.log`): the JSON-object case says "JSON object with
neither 'messages' (mini-SWE-agent trajectory) nor 'data'
(Langfuse export); pass --format explicitly or supply one of the
supported shapes". The plain-text/empty cases say "not a
mini-SWE-agent trajectory, Langfuse export, or JSONL events file;
pass --format explicitly or supply one of the supported shapes".
For these files there is no `--format` value that works — the
advice sends the stranger in a circle trying `traj`, then `jsonl`,
then `langfuse`, each failing with defect 3's jargon. The empty
file gets the same message as a garbage file, with no mention that
it is empty.

**Exact fix:** split the message. When the file parses as JSON but
matches no shape, say so and do NOT suggest `--format`: `averth:
error: <file> is JSON but none of the supported shapes (a
mini-SWE-agent trajectory has a 'messages' key; a Langfuse export
has a 'data' key or is a bare list; JSONL has one event object with
a 'type' key per line)`. Handle the empty file separately:
`<file> is empty`. For non-JSON input, name the three shapes with
one-line examples of each instead of the bare shape names.

## Defect 5 — A binary file leaks a codec error; a directory is reported as "not found"

**Files:** `averth/cli.py`, `_detect_try_format` (~line 193,
`open(path, encoding="utf-8")` unguarded) and `_cmd_try`
(~lines 231–233, `os.path.isfile` check).

**What I did:**

```
head -c 200 /bin/ls > binary.bin
python -m averth.cli try binary.bin
python -m averth.cli try elsewhere        # elsewhere/ is a directory
```

**What happened** (`f-binary.log`, `f-dir.log`):

```
averth: error: cannot detect trace format: 'utf-8' codec can't decode byte 0xd8 in position 96: invalid continuation byte
averth: error: file not found: elsewhere
```

The binary message is a Python codec error, not an instruction:
a stranger cannot act on a byte offset. The directory message is
factually wrong — the path exists, it is a directory — and sends
the stranger checking spelling and cwd for a file that is right
there.

**Exact fix:** catch `UnicodeDecodeError` in `_detect_try_format`
and report `averth: error: <file> is not readable text (binary or
non-UTF-8); supply a .traj.json, JSONL, or Langfuse JSON export`.
In `_cmd_try`, before the `isfile` check, test `os.path.isdir`
and report `averth: error: <path> is a directory; pass a trace
file, not a directory`.

## Defect 6 — Missing `--ledger` file gives a bare errno; the flag is never named

**File:** `averth/try_report.py`, `load_v0_ledger` (~line 47,
`open(ledger_path)` unguarded); `averth/cli.py` `_cmd_try`
(~lines 273–280) passes the raw exception through.

**What I did:**

```
python -m averth.cli try django-15930.traj.json --model claude-sonnet-4-20250514 --ledger nope.json
```

**What happened** (`f-ledger-missing.log`):

```
averth: error: [Errno 2] No such file or directory: 'nope.json'
```

Contrast the trace-file check, which names the problem cleanly
("file not found: ..."). Here the stranger gets a bare errno with
no mention of `--ledger`, no hint which of their paths is wrong
(they passed three), and no suggested fix. The not-a-ledger case
is fine ("`checks.json` is not a V0 evidence ledger (no
'judgments' key)") — only the missing-file path is raw.

**Exact fix:** in `load_v0_ledger`, catch `OSError` on both opens
and raise `ValueError("V0 ledger file not found: %s (passed via
--ledger)" % ledger_path)` / the same for `--checks`. Apply the
same wrapping to the `--checks` open.

## Defect 7 — Every README command silently assumes cwd is the repo root; from anywhere else they fail

**File:** `try-it/README.md` lines 12–13, 22, 56–59, 103. No line
anywhere states which directory to run the commands from.

**What I did (from `try-it/reviews/scratch-1/`):**

```
../averth-venv/bin/python -m averth.cli try django-15930.traj.json --model claude-sonnet-4-20250514 --recorded 0.3205
python3 try-it/reproduce-case-study.py
```

**What happened** (`f-relpath.log`, `f-repro-wrongcwd.log`):

```
/bin/bash: line 10: ../averth-venv/bin/python: No such file or directory   (exit 127)
python3: can't open file '.../scratch-1/try-it/reproduce-case-study.py': [Errno 2] No such file or directory   (exit 2)
```

All four path-bearing commands (`../averth-venv/...` ×3,
`try-it/reproduce-case-study.py` ×1) are relative and only resolve
inside the checkout root. The README never says "run these from
the repository root" and never says where the checkout is. A
stranger who `cd`s to their trace's directory (the natural move:
the case-study `curl` downloads the trace into cwd, so their trace
lives wherever they happened to be) gets a bare shell "no such
file" with no indication that cwd is the problem.

**Exact fix:** add one line at the top of Install: "Run every
command below from the repository root (the directory containing
`pyproject.toml`)." Prefer absolute-path-proof forms: use
`$REPO` / `<checkout>` placeholders, or tell the stranger to
`cd` into the checkout first and stay there. Also fix the
reproduce invocation to work from the root only by stating the
cwd requirement next to it.

## Defect 8 — The README has no clone/checkout instructions and no repo URL

**File:** `try-it/README.md` lines 10–11: "From a checkout of this
repository, on the `try-it` branch:" — then straight to venv
creation. No `git clone` URL, no `git checkout try-it` command.

**What I did:** read the README end to end; grepped it for a URL.
The URL (`https://github.com/Wesley3141/Averth.git`) exists only
in the top-level `README.md` and in `git remote -v`, not in
`try-it/README.md`.

**What happened:** a stranger who lands on this file alone — e.g.
linked from the case-study page, which is the whole point of
try-it — cannot obtain the checkout the first sentence assumes.
They also cannot tell that `try-it` is an unmerged branch that
must be checked out explicitly; on `master`/`main` the `try`
subcommand does not exist and `averth try` fails with argparse's
"invalid choice" error, which never mentions the branch.

**Exact fix:** add the commands before the venv step:

```
git clone https://github.com/Wesley3141/Averth.git
cd Averth
git checkout try-it
```

and a line: "If `averth try` reports an invalid choice, you are
not on the `try-it` branch (`git branch --show-current`)."

## Defect 9 — README's V0 summary promises "0 FAILED"; the CLI never prints or renders a zero count

**Files:** `try-it/README.md` lines 68–71; `averth/try_report.py`
`try_summary_lines` (~lines 200–211) and `build_try_extras`
(~lines 140–150, `for name in order if name in counts`).

**What I did:** ran the ledger+checks case-study run
(`f-ledger-ok.log`, `with-v0.html`).

**What happened:** stdout is `V0 verdicts: VERIFIED 2,
EXTERNAL-UNVERIFIABLE 2; unknown rate 50.0%` — no `FAILED 0`.
The HTML verdict table has exactly two rows (VERIFIED 2,
EXTERNAL-UNVERIFIABLE 2); there is no FAILED row at all. The
README says the summary is "(2 VERIFIED, 0 FAILED, 2
EXTERNAL-UNVERIFIABLE, 50.0% unknown rate)". A stranger comparing
their output to the README sees a missing item and cannot tell
whether FAILED was zero or was silently dropped.

**Exact fix:** always render all five verdict rows/counts in both
the stdout line and the HTML table, including zeros — or change
the README to quote the actual output verbatim. Prefer rendering
the zeros: a missing FAILED row in a verification summary reads as
an omission, not a zero.

## Defect 10 — Default `--out` wording is wrong, and the report lands in cwd, not next to the trace

**Files:** `try-it/README.md` line 49–50; `averth/cli.py`
`_cmd_try` (~lines 307–317) and `--out` help (~line 96).

**What I did:** from `scratch-1/`, ran `try
elsewhere/remote.traj.json --model ...` with no `--out`
(`f-remote-trace.log`).

**What happened:** the HTML was written to
`scratch-1/remote-try.html` (cwd), not to
`elsewhere/remote-try.html` next to the trace. The README says
"Default: `<trace>-try.html` next to the current directory" —
a phrase that is meaningless as written ("next to the current
directory"?) and wrong under the natural reading (next to the
trace). The `--help` text ("in cwd") contradicts the README.
The stdout line does print the absolute path, which mitigates
it, but a stranger who runs the command from home against a
trace in Downloads will hunt Downloads for a file that landed
in home.

**Exact fix:** change the README bullet to "Default: in the
current directory, named after the trace file
(`<basename>-try.html`; `.traj.json` → `-try.html`). Pass
`--out` to put it elsewhere." Make `--help` and the README use
the identical sentence.

## Defect 11 — A failed `--out` prints the full success-looking report first, then errors

**File:** `averth/cli.py`, `_report_and_html` (~lines 148–180):
prints `report_text`, findings, and the full P&L, and only then
attempts `write_html`.

**What I did:**

```
python -m averth.cli try django-15930.traj.json --model claude-sonnet-4-20250514 --out /nonexistent-dir-xyz/report.html
```

**What happened** (`f-badout.log`): exit 2, but only after the
entire meter report (Fully loaded $0.98, all five layers, "No
material findings") printed to stdout, followed by
`averth: error: cannot write HTML report to
/nonexistent-dir-xyz/report.html: [Errno 2] No such file or
directory`. (When stdout and stderr share a file the error line
lands first due to buffering, which is a second confusion, but
the defect is the ordering itself.) A stranger skimming the
output sees a complete, successful-looking report and may never
notice the trailing error or the missing HTML file — the command's
whole deliverable is the HTML file.

**Exact fix:** validate the `--out` path (parent directory exists
and is writable) before metering/printing anything, and fail fast
with `averth: error: cannot write HTML report to <path>: <reason>;
check the directory exists` before any report output. At minimum,
do not print the meter report when the HTML write is going to
fail: attempt the write (or a writability probe) first.

## Defect 12 — Re-running silently overwrites the previous report (demonstrated accidentally)

**File:** `averth/cli.py`, `_cmd_try` default-`--out` path and
`_report_and_html` `write_html` call — no existence check
anywhere.

**What I did:** nothing deliberate. The unknown-model run in
defect 1 wrote to the default `django-15930-try.html` and silently
replaced the correct $0.98 report from the case-study run with a
$0.36 wrong-model report — same filename, no warning. I only
noticed because a later HTML grep returned $0.91: 0 on a file I
believed was the case-study report, and had to regenerate it as
`clean-case-study.html`. The re-run at the end (`stat` before/after)
confirms: same path, new mtime/size, no prompt, no message.

**What happened:** a stranger re-running the command after a typo
(or after fixing a typo) cannot tell which run a report file came
from, and a bad run destroys a good report. For a tool whose
deliverable is a shareable file, silent destructive overwrite is a
usability defect, not a convenience.

**Exact fix:** refuse to overwrite an existing `--out`/default
file unless `--force` is passed (or print a loud `Overwriting
<path>` warning to stderr). At minimum, print `HTML report written
to <path> (overwrote previous report)` so the destruction is
visible.

---

## Minor defects (fix in the same pass)

**M1 — Prerequisites are incomplete and misattributed.**
`try-it/README.md` lines 16–17: "Prerequisites: Python 3.9 or
newer and git (for the reproduction script below)." Git is needed
to obtain the checkout at all (defect 8), and `curl` is needed for
the case-study download on lines 56–57 but is never listed — on a
machine without curl the headline example fails at its first
command. Fix: "Prerequisites: Python 3.9+, git, and curl."

**M2 — "Expected output lines" reads as the whole output.**
README lines 62–68 show three lines; the actual output is ~45
lines of P&L, findings, and provenance. A stranger diffing the
two will think something is wrong (or that extra output means
failure). Fix: retitle to "Look for these lines in the output:"
and say the full meter report prints above them.

**M3 — `--model` precedence is undocumented.** When the path names
one model and `--model` names another, the flag wins
(`claude-...-traj.json` + `--model gpt-4o` → $0.82, `openai:gpt-4o`
in the mix, `f-precedence.log`). Sensible, but the README's
"--model ... Required unless the file path names a priced model"
never states it. Fix: add "An explicit `--model` overrides the
name inferred from the file path."

**M4 — Empty Langfuse export exits 0 with a $0.00 report.**
`{"data": []}` (`f-langfuse-empty.log`) exits 0 and writes an
HTML report headlined by a "NOT A COST REPORT — no model spend
recorded" banner. The banner mitigates it, but exit 0 on zero
attempts lets a stranger with an empty/broken export walk away
with a file that looks like a result. Fix: exit 2 with
`averth: error: <file> contains no traces (empty export); nothing
to meter` when the event list is empty.

**M5 — No `--force`/overwrite flag exists** (see defect 12);
adding the refusal needs the flag in the same change, plus a
`--help` line.

**M6 — The `openai:`/`anthropic:` prefixing of model names is
never explained.** The report's "Model mix" shows
`anthropic:claude-sonnet-4-20250514` for an input of
`claude-sonnet-4-20250514`, and defect 1's run showed
`openai:gpt-99-nonexistent`. A stranger will wonder whether they
typed the wrong thing. One sentence in the README (provider is
guessed from the model name; the prefix is Averth's, not the
vendor's) closes it.

## Scope note

This review covers usability for a stranger only: following the
README, running the command, and hitting failure paths. I did not
audit the meter's arithmetic beyond the case-study reproduction,
the V0 verifier, or the reproduce script's full run (see "What I
did NOT check"). The happy path is genuinely good — the
case-study numbers reproduce exactly, detection is right, the
HTML is self-contained and honest about ESTIMATED vs billed.
The FAIL is carried by defects 1 and 2 (silent wrong numbers for
an undiscoverable input) and the cluster of 3–12, each of which is
a way a stranger gets stuck, misled, or silently wrong with no
signal that anything went wrong.
