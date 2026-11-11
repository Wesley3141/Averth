# Averth try-it: one command, one shareable report

Run the meter on a trace file and get a self-contained HTML report you
can send to anyone. No account, no server, no upload. The `try`
command itself makes no network calls and uploads nothing; fetching
a public trace (the `curl` below) is the only network step.

## Install

Run all commands in this guide from the repository root (the directory
containing `pyproject.toml`), unless a command explicitly specifies a
different working directory.

The `try-it` branch is not yet published. This feature cannot
currently be installed from a fresh public clone.

For internal testing, start from an existing checkout that already
contains the `try-it` branch.

Run the following from the repository root:

```
python3 -m venv ../averth-venv
../averth-venv/bin/pip install -e .
```

Once the branch is published, this section will include the public
clone and installation commands.

Prerequisites: Python 3.9 or newer, `curl` (for the download below),
and git (for the reproduction script below). Averth itself has zero required dependencies. After `pip install -e .`, plain `averth try …`
also works; the `../averth-venv/bin/python -m averth.cli` form below
is the same thing spelled out. If averth reports invalid choice: 'try'
for the subcommand, your checkout does not have the `try-it` branch
checked out (`git branch --show-current`).

## The one command

```
../averth-venv/bin/python -m averth.cli try <trace> [options]
```

`<trace>` is one of:

- a mini-SWE-agent trajectory (`.traj.json`, as published by the
  SWE-bench leaderboard),
- an Averth JSONL events file,
- a Langfuse trace export (JSON).

The format is auto-detected (`--format auto`, the default): a JSON
object with a `messages` key is a mini-SWE-agent trajectory, a JSON
object with a `data` key (or a bare JSON list) is a Langfuse export,
and one JSON object per line is Averth JSONL. Use
`--format traj|jsonl|langfuse` only if auto-detection guesses wrong;
if detection fails the command exits 2 naming the shapes it tried.
See "Trace formats" below for one example of each.

Options:

- `--model NAME` — model name for trajectory input, for example
  `claude-sonnet-4-20250514`. Required unless the file name contains
  a priced model name as a substring (longest match wins; the name
  must sit on a non-alphanumeric boundary, and only the file name
  counts, not the directory). If neither is given the command exits
  2 asking for `--model`. An explicit `--model` overrides the name
  inferred from the file name. A `--model` that is not in the price
  table is refused (exit 2); list priced models with
  `averth pricing`. `--model` is ignored for JSONL and Langfuse
  input, whose models come from the file itself. The model decides
  the list prices applied. The report shows the model as
  `provider:model` (for example `anthropic:claude-sonnet-4-20250514`):
  the provider prefix is guessed from the model name by Averth, it
  is not part of what you typed.
- `--recorded DOLLARS` — an operator-supplied figure claimed to be
  the recorded cost for the same run, in dollars (must be positive;
  `--recorded 0` is refused). For the case study it is the `cost`
  field of the leaderboard entry in `per_instance_details.json`.
  Averth does not verify it; the report labels it operator-supplied
  and shows it next to the metered estimate, with the ratio. If the
  run completed zero runs, no comparison is shown.
- `--ledger PATH` — a V0 evidence ledger (JSON) to summarize in the
  report: verdict counts, unknown rate, and one row per check with
  the criterion text and the cited observation (command, exit code,
  output digest). Without `--checks` the ledger's checks digest is
  shown but not verified.
- `--checks PATH` — the checks file the ledger was judged under.
  Verifies the ledger's checks digest and refuses the whole report on
  mismatch (before anything is written). Needs `--ledger`; without
  it the command is refused (exit 2).
- `--out PATH` — where to write the HTML report. Default:
  `<stem>-try.html` in the current directory, where `<stem>` is the
  trace filename without `.traj.json` (or `.json`):
  `django-15930.traj.json` becomes `django-15930-try.html`. Pass
  `--out` to put it elsewhere. The command refuses to overwrite an
  existing file; pass `--force` to overwrite it.
- `--force` — overwrite an existing HTML report at the specified
  output path. The reproduction script also accepts `--force` to
  remove an existing work directory before rerunning.
- `--agent NAME` — agent name shown in the report (default for
  trajectory input: `miniswe-import`; for JSONL input:
  `jsonl-import`; for Langfuse input: `langfuse-import`).

## The case-study run

```
curl -sL -o django-15930.traj.json \
  "https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json"
../averth-venv/bin/python -m averth.cli try django-15930.traj.json \
  --model claude-sonnet-4-20250514 --recorded 0.3205
```

The run prints a full report (about 50 lines). Look for these lines
in the output, in this order:

```
Retries:               0
  Fully loaded:         $0.98
Recorded cost (operator-supplied): $0.3205; metered estimate per completed run: $0.98 ESTIMATED (3.07x, calculated using the unrounded estimate)
```

The HTML report (`django-15930-try.html`) shows cost per completed
run with priced/estimated/billed provenance ($0.91 priced, $0.07
estimated, $0.00 billed), Retries: 0, context growth (9.9x input
growth, $0.68 context tax), and the recorded-cost comparison. The
report labels the $0.91 bucket "vendor list prices on trace-supplied
token counts, not verified as provider-recorded usage"; for
trajectory input those token counts are the characters/4 estimates
described below, not provider-recorded usage. To include the V0
verdict summary (2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE,
50.0% unknown rate), add `--ledger` and `--checks` with the pair
that ships in the repo:

```
../averth-venv/bin/python -m averth.cli try django-15930.traj.json \
  --model claude-sonnet-4-20250514 --recorded 0.3205 \
  --ledger case-study-1/v0-run/evidence_ledger.json \
  --checks try-it/fixtures/case-study-1-checks.json
```

`--ledger` alone still includes the summary but the digest is shown
unverified. `--checks` without `--ledger` is refused (exit 2). A
digest mismatch refuses the whole report and writes no HTML.

## What the report does and does not claim

- The $0.98 is an ESTIMATE, not a bill. For trajectory input, token
  counts are characters/4 estimates from the trajectory text, not
  provider-recorded usage; the dollars apply vendor list prices to
  those estimates. Reconcile against the invoice before calling any
  metered figure actual spend.
- The recorded cost is operator-supplied, not verified by the meter.
  The meter never invents a recorded cost: without `--recorded`, no
  comparison is shown. When the trajectory carries its own recorded
  cost (`info.model_stats.instance_cost`), the report shows whether
  it agrees with the operator-supplied figure.
- No cost per accepted outcome is claimed. `averth try` never joins
  human acceptance labels, so it reports cost per completed run.
  The report heads this figure "Cost per completed run"; "completed"
  means the run finished and submitted, not that a human accepted it.
- A V0 VERIFIED row proves only what its cited observation shows.
  The ledger's checks digest is verified only when `--checks` is
  given; without it, the report says so.

## Trace formats

- **Trajectory** (`.traj.json`, as published by the SWE-bench
  leaderboard): a JSON object with a `messages` key. The fixture
  `try-it/fixtures/django-15930.traj.json` is one. The leaderboard
  submissions live under
  `https://s3.amazonaws.com/swe-bench-submissions/`; see the
  case-study `curl` above for the exact URL shape.
- **JSONL**: one Averth event object per line, each with a `type`
  key. The fixture `try-it/fixtures/trace-events-django-15930.jsonl`
  is one; its first lines look like this:

  ```
  {"type": "model", "case_id": "django__django-15930", "model": "claude-sonnet-4-20250514", "input_tokens": 1460, "output_tokens": 58}
  {"type": "tool", "case_id": "django__django-15930", "name": "bash"}
  ```

  An events file is what `averth trace --format jsonl` reads, and
  what the trajectory converter produces. To get one from a
  trajectory, run the converter (see "How the trajectory conversion
  works" below) or copy the fixture. Every line must be an event
  object with a `type` key; a file whose first line is a header or
  comment with no `type` is not supported.
- **Langfuse export** (JSON): a JSON object with a `data` key, or a
  bare JSON list of observations, as exported from Langfuse
  (project settings, export). Token counts and costs are
  trace-supplied; Averth does not verify them as recorded usage.

## Reproduce the case study

`reproduce-case-study.py` reproduces the published case-study numbers
listed in `PUBLISHED` from public sources: it fetches the trajectory,
the leaderboard record, and the SWE-bench task definition; checks out
Django at the base commit; runs the target test before and after the
agent patch (plus a gold-patch cross-check against the fix Django
actually merged); runs the meter and V0; and checks the published
numbers in `PUBLISHED`, plus a few consistency checks that are not
published numbers (leaderboard `api_calls`, baseline failure mode).
It does not independently check the 3.84x 12-run leaderboard gap, the
zero-tool-failures claim, or the exact $0.9832 unrounded total. The
latter is checked through its rounded components and the recorded-cost
ratio.

```
python3 try-it/reproduce-case-study.py
```

Run this from the repository root. It needs internet access (public S3, GitHub, Hugging Face, and PyPI
URLs), git, curl, and about a minute for the Django install (47 to 86
seconds measured; allow more on a slow connection). It
writes its reproduction artifacts under `./repro-work` relative to the
directory you run it from (pass `--work-dir` to change it). The
editable Averth install also creates a git-ignored averth.egg-info/
directory in the source checkout; no tracked file is modified. It
prints a PASS/FAIL line per check at the end. Exit code 0 means every
check passed; anything else is a defect to fix, not a rounding note.
If the work directory already exists the script refuses; pass `--force`
to wipe it and redo the run. The script refuses to wipe the filesystem
root, home directory, current directory, repository root, or an
ancestor of the checkout, even with `--force`.

## How the trajectory conversion works

`averth/importers/miniswe.py` converts a mini-SWE-agent trajectory
to Averth events: one model event per assistant message, with input
tokens equal to the characters of all preceding message text (text
parts only) integer-divided by 4 and output tokens equal to the
characters of the assistant message integer-divided by 4; one `bash` tool
event per ```` ```bash ```` fenced block (the fence is exactly
```` ```bash ````, case-insensitive, optionally followed by trailing
spaces and optionally by a newline, through the closing ```` ``` ````); one end event when `info.exit_status` is
present (`Submitted` means the agent submitted a patch, exactly and
case-sensitively; anything else means failure) and no end event when
it is absent, in which case the attempt ends outcome-unknown. The
conversion reproduces the published case-study events file
(`try-it/fixtures/trace-events-django-15930.jsonl`); the regression
test in `tests/test_try_it.py` compares the parsed events.
