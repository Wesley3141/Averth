# Review 4 — Docs clarity (adversarial)

**Verdict: FAIL**

Read as a stranger who has never seen Averth. I ran every command I could
from a clean directory (`/tmp/try-clean`, empty, not inside the repo) using
the repo venv; probe log and full case-study stdout are in
`try-it/reviews/scratch-4/` (`probe-log.md`, `case-study-run.log`,
`case-study-report.html`). The numbers in the README are right. The
sentences around them are not: the install and case-study commands fail
literally as written outside the repo, the root README points a
master-branch install at a command that does not exist on master, the
"expected output" block is not output any real run produces, and the
`--out` default is wrong in both places that state it. Docs that almost
work are worse than docs that clearly fail, because the stranger burns
time assuming they misread something.

What I did **not** check (not signed off): the full
`reproduce-case-study.py` run was not executed (Django checkout + venv +
test runs + V0; many minutes of network/build work), so nothing below
asserts its runtime or end-to-end pass from my own run. Python 3.9
specifically was not tested. The `--recorded 0.3205` source value was
not independently fetched.

---

## D1 (blocking) — Install section has no clone, no checkout, no `cd`, and its commands only work from one unstated directory

**File:** `try-it/README.md`, lines 9–13

> "From a checkout of this repository, on the `try-it` branch:"
>
> ```
> python3 -m venv ../averth-venv
> ../averth-venv/bin/pip install -e .
> ```

A stranger has no checkout. There is no `git clone` URL, no
`git checkout try-it`, and no `cd` into anything, so "from a checkout"
is not an instruction. Worse, the commands silently assume the reader's
working directory is the repo root: `pip install -e .` installs whatever
`.` happens to be, and `../averth-venv` is a sibling of that directory.
From my clean directory the very next command in the README fails (see
D2). Nothing on the page tells the reader where to stand.

**Exact fix:** replace the section with a complete literal sequence,
e.g.:

```
git clone https://github.com/Wesley3141/Averth.git
cd Averth
git checkout try-it
python3 -m venv ../averth-venv
../averth-venv/bin/pip install -e .
```

and state once, explicitly, "run every command below from the `Averth`
directory unless told otherwise."

## D2 (blocking) — The one command and the case-study command fail literally as written from a clean directory

**File:** `try-it/README.md`, lines 21–23 and 56–59

> `../averth-venv/bin/python -m averth.cli try <trace> [options]`
>
> ```
> ../averth-venv/bin/python -m averth.cli try django-15930.traj.json \
>   --model claude-sonnet-4-20250514 --recorded 0.3205
> ```

Verified from empty `/tmp/try-clean`:

```
/bin/bash: ../averth-venv/bin/python: No such file or directory
```

The curl on the line above it succeeds (69,126-byte
`django-15930.traj.json` downloaded), so the stranger has the trace and
then a dead command. The relative venv path only resolves if the reader
is in the repo root (D1) — which the README never establishes — and the
trace file itself lands in whatever the working directory is, so the
reader cannot tell whether the failure is their venv, their download,
or their directory. Separately, the README never mentions that
`pip install -e .` installs a real `averth` console script
(`pyproject.toml` `[project.scripts]`, verified: `.venv/bin/averth try
--help` works), so the reader is forced onto the clunky module form
with a relative interpreter path for no stated reason.

**Exact fix:** after fixing D1, give the case-study command in the form
the reader will actually type from the stated directory, and add one
line: "After `pip install -e .`, plain `averth try …` also works; the
`../averth-venv/bin/python -m averth.cli` form below is the same thing
spelled out." If the intended working directory is the repo root, say
so before the curl, not after the failure.

## D3 (blocking) — Root README tells a master-branch install to run a command that does not exist on master

**Files:** `README.md` lines 6, 41, 47–51; `try-it/README.md` line 9

Root README install (lines 6 and 41, twice):

> `pip install git+https://github.com/Wesley3141/Averth.git`

followed by (lines 47–51):

> "**Just want to try it on one trace?** `averth try <trace>` meters a
> mini-SWE-agent trajectory, a JSONL events file, or a Langfuse export
> and writes one self-contained HTML report you can share, with an
> optional recorded-cost comparison (`--recorded`) and V0 verdict
> summary (`--ledger` + `--checks`). See `try-it/README.md`."

Verified: `git show master:averth/cli.py` contains no
`add_parser("try")` and no `_cmd_try`, and `git ls-tree master --
try-it/` is empty. On master there is no `try` subcommand and no
`try-it/README.md` to see. A reader who follows the root README alone —
the page a stranger lands on — gets an argparse "invalid choice" failure for `try` and a dangling pointer, with no hint that a branch
exists. The try-it README's "on the `try-it` branch" (line 9) is the
only place the branch is named, and the root README never repeats it.

**Exact fix:** in the root README, either (a) scope the pointer —
"on the unmerged `try-it` branch only: `git checkout try-it`, then see
`try-it/README.md`" — and do not present `averth try` alongside the
master install commands, or (b) remove the pointer until the branch
merges. Do not leave a master install and a branch-only command in the
same Quickstart as if they were one path.

## D4 (blocking) — "Expected output lines" is not output any real run produces

**File:** `try-it/README.md`, lines 62–68

> "Expected output lines:"
>
> ```
> Fully loaded:         $0.98
> Retries:               0
> Recorded cost: $0.3205; metered estimate per completed run: $0.98 ESTIMATED (3.07x)
> ```

The values are all correct — my run produced each of them — but the
block as presented is fiction as a block. The real stdout is 46 lines
(saved as `scratch-4/case-study-run.log`): `Retries:` is line 10,
`Fully loaded:` is line 17, the `Recorded cost:` line is line 46, and a
full cost report, findings section, and `HTML report written to …` line
sit between them. The `Fully loaded:` line also carries a two-space
leading indent in real output (`  Fully loaded:         $0.98`, under
"Cost per successful outcome:") that the README's block omits. A
stranger who diffs or greps for this block will conclude the run is
wrong when it is right.

**Exact fix:** label it honestly and give the real order, e.g.:

```
The run prints a full report (46 lines). These three lines appear in
it, in this order:
  Retries:               0
    Fully loaded:         $0.98
  Recorded cost: $0.3205; metered estimate per completed run: $0.98 ESTIMATED (3.07x)
```

or show the full stdout. Do not present scattered excerpts as a
contiguous block.

## D5 — `--out` default is wrong in both places that state it

**Files:** `try-it/README.md` lines 49–50; `averth/cli.py` line 96
(help text, surfaced by `averth try --help`)

README:

> "- `--out PATH` — where to write the HTML report. Default:
>   `<trace>-try.html` next to the current directory."

Help:

> "HTML report output path (default: `<inputfile>-try.html` in cwd)."

Reality (`averth/cli.py` lines 311–316, verified by running): the stem
strips `.json` and then a trailing `.traj`, and the file is written in
the current directory — `django-15930.traj.json` becomes
`django-15930-try.html`, which I confirmed exists in cwd after my run.
`<trace>-try.html` taken literally would be
`django-15930.traj.json-try.html`, a filename no run ever produces.
"Next to the current directory" is also meaningless — the report is
*in* the current directory, not next to it. The help's "in cwd" is
right about location but repeats the wrong filename pattern.

**Exact fix (both places):** "Default: `<stem>-try.html` in the current
directory, where `<stem>` is the trace filename without `.traj.json`
(or `.json`): `django-15930.traj.json` → `django-15930-try.html`."

## D6 — `--format` omits `auto`, and auto-detection rules appear nowhere in the docs

**File:** `try-it/README.md`, lines 32–33

> "The format is auto-detected. Use `--format traj|jsonl|langfuse` only
> if auto-detection guesses wrong."

`auto` is the actual default and a valid choice (`--format
{auto,traj,jsonl,langfuse}` in `--help`), yet the README never names
it — a stranger reading the option list would conclude a `--format`
value is one of three, and has no way to write "detect it" explicitly
or to reset to the default. "The format is auto-detected" also says
nothing about *how*: the rules live only in the `_detect_try_format`
docstring in `averth/cli.py` (a JSON object with `messages` is a
trajectory; with `data`, or a bare JSON list, is a Langfuse export;
one-JSON-object-per-line with a `type` key is JSONL). When detection
fails the CLI prints a good error naming the supported shapes
(verified, exit 2), but the README gives the reader no way to predict
or fix that failure other than "pass `--format`" — and no example of a
file that fails detection.

**Exact fix:** "The format is auto-detected (`--format auto`, the
default): a JSON object with a `messages` key is a mini-SWE-agent
trajectory, a JSON object with a `data` key (or a bare JSON list) is a
Langfuse export, and one JSON object per line is Averth JSONL. Use
`--format traj|jsonl|langfuse` only if auto-detection guesses wrong;
if detection fails the command exits 2 naming the shapes it tried."

## D7 — `--model` does not say what "names a priced model" means, what failure looks like, or that it is ignored for two of three formats

**File:** `try-it/README.md`, lines 37–39

> "- `--model NAME` — model name for trajectory input, for example
>   `claude-sonnet-4-20250514`. Required unless the file path names a
>   priced model. The model decides the list prices applied."

Three gaps, all verified against `averth/importers/miniswe.py`:

1. "Names a priced model" is undefined. The implementation does a
   substring scan of the *whole file path* against price-table names,
   longest match wins (`_infer_model`). The README does not say
   substring (so is `my-claude-sonnet-4-20250514-run.traj.json` enough?
   yes — I verified inference works with the model mid-filename), does
   not say which names count as "priced" (the price table's keys), and
   does not say the directory part of the path counts too.
2. The failure mode is unstated. Omitting `--model` on a path with no
   model in it is a clean exit 2: "no model named for …: pass --model
   (e.g. --model claude-sonnet-4-20250514) or put the model name in the
   file path" (verified). The README should quote that, so the
   stranger recognises it as the expected error rather than a crash.
3. `--model` is silently ignored for JSONL and Langfuse input
   (`_cmd_try` passes it only to `load_miniswe`). A stranger who
   passes `--model` with a JSONL file will believe it priced the run
   at that model; it did nothing.

**Exact fix:** "Required for trajectory input unless the file path
contains a priced model name as a substring (longest match wins; the
directory counts too). If neither is given the command exits 2 asking
for `--model`. `--model` is ignored for JSONL and Langfuse input, whose
models come from the file itself."

## D8 — `--recorded` omits the positivity rule, the source field, and the zero-success case

**File:** `try-it/README.md`, lines 40–43

> "- `--recorded DOLLARS` — the recorded cost for the same run, from the
>   run's own record (for the case study: the leaderboard entry's
>   `per_instance_details.json`). The report shows it next to the
>   metered estimate, with the ratio."

Verified gaps:

1. `--recorded 0` (and any non-positive value) is refused with exit 2
   ("`--recorded` must be a positive dollar figure"). The README's
   `DOLLARS` placeholder suggests any number works.
2. "From the run's own record" never says *which field*: the
   leaderboard file's `cost` field. The URL of that file appears only
   in `reproduce-case-study.py`, never in the README, so a stranger
   cannot verify the 0.3205 or find the record for another run.
3. If the run has zero successes there is no per-run figure and no
   comparison is printed at all (`try_report.py`: "No completed runs,
   so there is no per-run figure to compare against the recorded
   cost"). The README's "shows it next to the metered estimate, with
   the ratio" is unconditional and therefore false for that case.

**Exact fix:** "Pass the run's recorded cost in dollars (must be
positive; `--recorded 0` is refused). For the case study it is the
`cost` field of the leaderboard entry in `per_instance_details.json`.
If the run completed zero runs, no comparison is shown."

## D9 — "Add `--ledger` and `--checks`" is not an actionable instruction, and `--ledger`-alone behaviour is undocumented

**File:** `try-it/README.md`, lines 44–48 and 74–76

> "- `--ledger PATH` — a V0 evidence ledger (JSON) to summarize in the
>   report: verdict counts, unknown rate, and one row per check."
> "- `--checks PATH` — the checks file the ledger was judged under.
>   Verifies the ledger's checks digest and refuses the whole report on
>   mismatch. Needs `--ledger`."
>
> "Add `--ledger` and `--checks` to include the V0 verdict summary (2
> VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE, 50.0% unknown rate)."

No path is given for either flag and no command that produces a ledger
is shown anywhere in the README. The stranger is told a V0 summary
exists and given no way to obtain one. This is especially bad because
a working pair *ships in the repo*: `case-study-1/v0-run/
evidence_ledger.json` with `try-it/fixtures/case-study-1-checks.json`
(digest verified by hashing: both
`sha256:f25cd3bc…`; I ran `try` with them and got the V0 line and the
HTML section). The README hides the one runnable example behind a
bare "add". Two further behaviours are undocumented: `--ledger` without
`--checks` still works but the digest is shown *unverified* (verified:
prints the V0 line; the report says "Checks digest shown but not
verified"), and `--checks` without `--ledger` refuses with exit 2
(verified: "`--checks` needs `--ledger`") — "Needs `--ledger`" hints
at the dependency but not that it is a hard refusal, and nothing says
a digest mismatch refuses *before anything is written* (verified: no
HTML file is produced on mismatch).

**Exact fix:** give the runnable command:

```
../averth-venv/bin/python -m averth.cli try django-15930.traj.json \
  --model claude-sonnet-4-20250514 --recorded 0.3205 \
  --ledger case-study-1/v0-run/evidence_ledger.json \
  --checks try-it/fixtures/case-study-1-checks.json
```

(from the repo root; adjust paths if you run elsewhere), and add:
"`--ledger` alone still includes the summary but the digest is shown
unverified. `--checks` without `--ledger` is refused (exit 2). A digest
mismatch refuses the whole report and writes no HTML."

## D10 — `--agent` has no documented default, and the default is a strange string

**File:** `try-it/README.md`, line 51

> "- `--agent NAME` — agent name shown in the report."

If omitted, a trajectory run reports as `miniswe-import` (report
header in my run: "Averth: miniswe-import"; default in
`load_miniswe`). Neither the README nor the help says so, so the
stranger's first report greets them with an implementer's internal
label and no explanation of where it came from. The default for JSONL
and Langfuse input is likewise unstated anywhere.

**Exact fix:** "Agent name shown in the report (default for trajectory
input: `miniswe-import`; for JSONL/Langfuse input: [state the actual
default or that it comes from the file])." If the default is
embarrassing, rename it — but either way, document it.

## D11 — Reproduce section omits `--force`, the re-run refusal, and the fact that the work dir is relative to the caller's cwd

**File:** `try-it/README.md`, lines 101–110

> ```
> python3 try-it/reproduce-case-study.py
> ```
>
> "It needs internet access (public S3, GitHub, and Hugging Face URLs),
> git, curl, and a few minutes for the Django install. It writes
> everything under `./repro-work` (pass `--work-dir` to change it) and
> prints a PASS/FAIL line per published number at the end."

Verified: a second run against an existing work dir fails with exit 2
("`reproduce: error: … already exists; pass --force to wipe it and redo
the run`"). The README's only command is therefore a one-shot command
whose second invocation errors in a way the page never mentions, and
`--force` — the documented-in-`--help` escape hatch, which *wipes* the
directory — is never named in the README at all. Also, `./repro-work`
is relative to the caller's working directory, which the README never
states: run it from the repo root and the work lands in
`./repro-work`; run it from `try-it/` and it lands in
`try-it/repro-work`. The on-disk evidence agrees the location is
ambiguous in practice: a prior run's work sits at
`try-it/repro-work/`, not at repo-root `./repro-work`.

**Exact fix:** "It writes everything under `./repro-work` relative to
the directory you run it from (pass `--work-dir` to change it). If that
directory already exists the script refuses; pass `--force` to wipe it
and redo the run."

## D12 — The reproduce script's docstring and the README both overstate what it checks, and understate what it needs

**Files:** `try-it/reproduce-case-study.py` docstring (lines 1–24);
`try-it/README.md` lines 95–99, 105–110

Docstring:

> "What it does, in order: 1. Downloads … 2. Checks out Django at the
> case-study base commit, installs it in a venv, and runs the target
> test before the agent patch (expected: fails with the reported SQL
> syntax error) and after it (expected: passes, module green: 89 tests,
> 1 skipped). A gold-patch cross-check runs the same target test under
> the merged fix. 3. Runs `averth try` … 4. Runs V0 in executed mode …
> 5. Prints one PASS/FAIL line per published number."

README:

> "`reproduce-case-study.py` runs the full published reproduction from
> public sources: it fetches the trajectory, the leaderboard record,
> and the SWE-bench task definition; checks out Django at the base
> commit; runs the target test before and after the agent patch; runs
> the meter and V0; and checks every published number."

Problems:

1. The docstring's ordered list is actually accurate about the
   gold-patch cross-check (it is there, step 2) — credit where due —
   but the *README's* summary omits the gold-patch cross-check, the
   leaderboard `api_calls`/`resolved` checks, and the baseline
   THEN-syntax-error check entirely, while claiming the script
   "checks every published number." Those extra checks are *not*
   published numbers, and the script's own output header calls them
   "Published-number checks:" — so unpublished checks are printed
   under a published-numbers header. Either the header or the claim is
   wrong.
2. Prerequisites omit PyPI. The script `pip install`s `asgiref`,
   `sqlparse`, `pytest`, and `pyarrow` (plus `pip install -e` of the
   repo) — that is a fourth network source after S3/GitHub/Hugging
   Face, and a PyPI outage fails the run in a way "needs internet
   access (public S3, GitHub, and Hugging Face URLs)" does not cover.
3. "A few minutes for the Django install" is the only time bound on
   the page, for a script that creates two venvs, fetches Django,
   installs PyPI packages, runs three test suites, meters, and runs
   V0. I did not run it end to end, so I will not assert a number —
   but the README asserts one ("a few minutes") with no evidence, and
   no total is given.
4. Docstring: "the repository checkout itself is never modified." Run
   from the repo root with the default work dir, the script creates a
   new `repro-work/` directory *inside the checkout*. That is a
   modification of the checkout tree (an untracked directory the
   reader did not ask for by name). The sentence is false as written.

**Exact fix:** README: "…and checks every published number, plus a
gold-patch cross-check and a few consistency checks (leaderboard
`api_calls`, baseline failure mode) that are not published numbers."
Prerequisites: add "and PyPI (for the Django venv's packages)." Time:
give a measured total or drop "a few minutes" for "allow up to [N]
minutes; most of it is the Django install." Docstring: "the repository
checkout itself is never modified, except that the default work
directory `./repro-work` is created inside it when run from the repo
root" — or change the default work dir to outside the repo.

## D13 — "How the trajectory conversion works" misstates three behaviours

**File:** `try-it/README.md`, lines 114–123

> "`averth/importers/miniswe.py` converts a mini-SWE-agent trajectory
> to Averth events: one model event per assistant message, with input
> tokens equal to the characters of all preceding message text divided
> by 4 and output tokens equal to the characters of the assistant
> message divided by 4; one `bash` tool event per bash code block; one
> end event whose success follows `info.exit_status` (`Submitted`
> means the agent submitted a patch). The conversion reproduces the
> published case-study events file byte for byte
> (`try-it/fixtures/trace-events-django-15930.jsonl`); that is the
> regression test in `tests/test_try_it.py`."

1. **"one end event" is false when there is no exit status.** The
   code emits *no* end event if `info.exit_status` is absent, and the
   attempt auto-ends outcome-unknown (verified in code and in
   `test_converter_missing_exit_status_is_outcome_unknown`, which
   asserts zero end events). The README's sentence implies an end
   event always exists.
2. **"Byte for byte" is false as a description of the test.** The test
   (`tests/test_try_it.py:43–45`,
   `test_converter_reproduces_published_events_byte_for_byte`) asserts
   `mine == _fixture_events()` — parsed event *dicts* compared for
   equality, never bytes. A converter emitting the same events with
   different JSON serialisation would pass. The function name says
   byte-for-byte; the assertion does not check it.
3. **"Per bash code block" hides the exact fence rule.** The code
   matches only ```` ```bash\n…``` ```` — a fence with no trailing
   newline after `bash`, or with an info-string suffix, does not
   match. "Characters … divided by 4" also omits that the division is
   integer division, that non-text content parts contribute nothing,
   and that the assistant message's own text counts toward its output
   but not its input.

**Exact fix:** "…; one `bash` tool event per ```` ```bash ```` fenced
block (the fence must be exactly ```` ```bash ```` followed by a
newline); one end event when `info.exit_status` is present (`Submitted`
means success, anything else means failure) and no end event when it
is absent — the attempt then ends outcome-unknown. Input tokens are the
characters of all preceding message text (text parts only) integer-
divided by 4. The conversion reproduces the published events file
(`…jsonl`); the regression test compares the parsed events."

## D14 — Missing docs: no trace example, no trace source, no failure recovery

No file in the review set tells a stranger:

1. **What a trace looks like.** There is no example line of an Averth
   JSONL events file and no example of a Langfuse export's shape
   anywhere in `try-it/README.md`. The trajectory format gets one
   clause ("`.traj.json`, as published by the SWE-bench leaderboard")
   with no URL to that leaderboard and no pointer to the fixture that
   *is* one (`try-it/fixtures/django-15930.traj.json`). A stranger
   with their own JSONL file cannot tell whether it is the right
   shape until the command fails.
2. **Where to get a trace.** Only the case-study trajectory has a
   source (the curl URL). For JSONL ("your own Averth events file"?)
   and Langfuse ("export how, from where?") there is nothing.
3. **What to do when auto-detection fails**, beyond the bare
   `--format` flag (see D6).
4. **That `--model` is ignored for JSONL/Langfuse** (see D7) and that
   `--recorded` needs a positive value from a named field (see D8).

**Exact fix:** add a short "Trace formats" section with one minimal
example per format (a two-line JSONL snippet; the Langfuse shape — a
JSON object with `data` or a bare list; the trajectory's `messages`
key), a link to the SWE-bench leaderboard submissions, and a pointer
to the in-repo fixtures as specimens.

## D15 — Terminology collisions the reader cannot resolve

1. **"Completed run" vs "successful outcome".** The README says
   "`averth try` never joins human acceptance labels, so it reports
   cost per completed run" (lines 87–88) and the summary line says
   "metered estimate per completed run" — but the report itself heads
   the same number "Cost per successful outcome:" (line 1 of the
   report body in my run). One number, two names, and "successful
   outcome" is exactly the phrase the README elsewhere reserves for
   human-accepted outcomes ("No cost per accepted outcome is
   claimed"). A stranger cannot tell whether $0.98 is per completed
   run, per success, or per accepted outcome.
2. **"Retry share (0 retries)"** (lines 71–72) is not a phrase in the
   output. The output prints `Retries: 0` and a yield-ratio sentence.
   "Retry share" sounds like a percentage the report never shows.
3. **"No account, no server, no upload, no network"** (lines 3–5).
   True of the `try` command itself; false of the page as a whole,
   whose case-study command downloads from S3 over the network and
   whose reproduce script needs S3, GitHub, Hugging Face, and PyPI.
   As the lede of the whole document it misleads.
4. **"Priced" vs "recorded tokens".** The README calls $0.91
   "priced" and discloses (lines 80–81) that trajectory token counts
   are chars/4 estimates — but the report the reader actually sees
   labels that $0.91 bucket "Priced (vendor prices on recorded
   tokens…)". The importer deliberately does *not* set
   `tokens_estimated` (see its docstring: the published numbers were
   produced without the flag). So the README and the report use
   "recorded" in opposite directions on the same dollars, and nothing
   on the page warns the reader that the report's own bucket label
   says "recorded tokens" for estimated counts.

**Exact fix:** (1) one sentence: "The report heads this figure 'Cost
per successful outcome'; here 'successful' means the run completed
and submitted, not that a human accepted it." (2) Say "Retries: 0"
instead of "retry share". (3) Scope the lede: "The `try` command
itself makes no network calls and uploads nothing; fetching a public
trace (the `curl` below) is the only network step." (4) Add one
sentence where $0.91 is introduced: "The report labels this bucket
'vendor prices on recorded tokens'; for trajectory input those token
counts are the characters/4 estimates described below, not
provider-recorded usage."

## D16 — Smaller contradictions and omissions (README vs help vs CHANGELOG)

1. **Prerequisites omit `curl` for the case-study command.**
   `try-it/README.md` lines 16–17 list "Python 3.9 or newer and git
   (for the reproduction script below)"; `curl` is listed only as a
   reproduce-script need (line 106), but the case-study section itself
   runs `curl`. Fix: "Python 3.9 or newer, `curl` (for the download
   below), and git (for the reproduction script)."
2. **CHANGELOG repeats the D12 overstatement.** `docs/CHANGELOG.md`
   lines 14–16: "`try-it/reproduce-case-study.py` replays the full
   published case-study reproduction from public sources and checks
   every published number." Same fix as D12: qualify with the
   non-published checks.
3. **CHANGELOG vs README on scope.** The CHANGELOG entry (lines 7–16)
   is otherwise consistent with the README on formats and flags; no
   separate contradiction found there. (Stating this so the absence is
   a checked absence, not an oversight.)
4. **Help vs README on `--model`.** Help: "Inferred from the file path
   when it names a priced model." README: "Required unless the file
   path names a priced model." Consistent with each other; both share
   the D7 gap (neither defines "names").

---

## What checked out (verified, not assumed)

- All published numbers reproduce: $0.98 / $0.91 / $0.07 / $0.00,
  3.07x, 0 retries, 9.9x growth, $0.68 context tax, V0 2/0/2 at 50.0%
  unknown (full stdout in `scratch-4/case-study-run.log`).
- The case-study S3 URL downloads (69,126 bytes).
- The generated HTML contains zero `http` occurrences — the
  "self-contained" claim holds for this run.
- Python ≥3.9 and zero required dependencies match `pyproject.toml`
  (`requires-python = ">=3.9"`, `dependencies = []`).
- `--ledger` alone, `--ledger` + `--checks`, and digest-mismatch
  refusal all behave as the README's `--checks` bullet promises in
  outline (exit 2, no HTML on mismatch).
- Model inference from a filename works; `--recorded 0` and
  `--checks`-without-`--ledger` refuse cleanly with exit 2.

## Files

- Review: `try-it/reviews/review-4-docs.md` (this file)
- Probe log: `try-it/reviews/scratch-4/probe-log.md`
- Case-study stdout: `try-it/reviews/scratch-4/case-study-run.log`
- Generated report: `try-it/reviews/scratch-4/case-study-report.html`

No source files were edited. Nothing was merged, pushed, deployed, or
sent to anyone.
