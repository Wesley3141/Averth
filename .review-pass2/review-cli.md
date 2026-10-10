# Hostile review, pass 2 — averth/cli.py (2026-10-02)

Reviewer brief: CLI only (`averth/averth/cli.py`, 189 lines), including the
new `averth pricing` subcommand. Reviewed against RUBRIC.md. Every claim
below was verified by running code, not by reading.

## Verdict

**No criticals.** The CLI is functionally correct end-to-end: all three
subcommands work, every subcommand was traced against the real fixtures,
error paths exit non-zero with clear messages, the pricing output matches
`pricing.price_vintage()` exactly, HTML output is tag-balanced, and the
prior `--policy-cap 0` bug is confirmed fixed through the CLI path. Two
findings above nit level: one HIGH (raw traceback on bad `--html` path,
breaking the CLI's own error contract) and one MEDIUM (module docstring
usage block omits the new `pricing` subcommand).

Scope note: `json.load` of untrusted ledgers happens in the importers, not
the CLI; the CLI passes only a path string. No network imports, no secrets,
no eval/exec/subprocess in cli.py.

## Findings

### HIGH

**H1. Bad `--html` path breaks the CLI's error contract: full report
prints, then an unhandled traceback, exit 1.**
`averth/averth/cli.py:99-100` (`_report_and_html`): `write_html()` is called
without any try/except, while every other failure in `main()` gets a clean
`averth: error: ...` message on stderr and exit 2. Reproduced:
`averth trace tests/fixtures/events.jsonl --format jsonl --html
/no/such/dir/x.html` prints the entire text report (which reads like
success), then dies with an unhandled `FileNotFoundError` traceback,
exit code 1. Same exposure on `averth simulate`'s `--jsonl` write
(cli.py:108-110, `stress.write_jsonl` unguarded). A typo'd output directory
is a realistic input; the user gets a Python traceback instead of the
`averth: error:` style the rest of the CLI promises. Fix: wrap the HTML
(and JSONL) writes in try/except, print `averth: error: cannot write HTML
report to <path>: <e>` to stderr, return 2.

### MEDIUM

**M1. Module docstring usage block omits the new `pricing` subcommand.**
`averth/averth/cli.py:3-9` documents `trace` and `simulate` but not
`pricing`, although the file now defines it (cli.py:66, cli.py:105-128).
The `--help` output covers all three, so interactive users are fine, but the
docstring claims to be the CLI's usage reference and is now incomplete.
Add a `averth pricing` line to the docstring.

### LOW

**L1. Directory passed as trace file reports "file not found".**
cli.py:137-140: `trace /tmp --format jsonl` prints `averth: error: file
not found: /tmp`. The path exists; it is a directory. Message should say
"not a file". Exit code is correct (2).

**L2. Empty input file exits 0 with a zero-attempt report and no warning.**
An empty `.jsonl` parses to 0 attempts; CLI prints a full P&L of $0.00 and
writes HTML, exit 0. The numbers are honest (all zero, not corrupt), but an
empty trace almost always means a broken exporter, and nothing flags it.
Consider a stderr warning or non-zero exit for zero-event input.

**L3. `_cmd_simulate` generates the synthetic data twice.**
cli.py:105-110: `stress.generate(...)` builds the tracker, then
`stress.write_jsonl(...)` regenerates the same events from scratch when
`--jsonl` is given. Deterministic (verified byte-identical stdout/HTML
across runs, and the JSONL re-imports to the same 25 attempts / totals),
so this is waste, not a bug — but it doubles CPU on the default
2000-attempt run and is a latent divergence risk if `generate` and
`write_jsonl` defaults ever drift.

**L4. ImportError from an importer is mislabeled "bad trace format".**
cli.py:142-146: `_importer_for` is caught with `(ImportError, ValueError)`
and reported as `averth: error: bad trace format`. If an importer's own
dependency import ever fails, the message blames the user's format choice
instead of the environment (the separate `except Exception` →
"cannot load importer" branch is the right label but is shadowed for
ImportError). Currently unreachable — all three importers import only
stdlib + averth (verified by reading their heads) — so this is a latent
labeling wart, not a live bug.

## Verified working (evidence, not findings)

- **trace x 3 formats**: jsonl (`tests/fixtures/events.jsonl`), otel
  (`otel_spans.json`), langsmith (`langsmith_runs.json`) — all exit 0,
  HTML written and tag-balanced (HTMLParser check: no unclosed/mismatched
  tags on events.html, otel_spans.html, langsmith_runs.html).
- **simulate**: `--attempts 10/25` exit 0; stdout and HTML byte-identical
  across two `--seed 7` runs (deterministic); `--jsonl` wrote 25 `start`
  events for `--attempts 25`, and re-importing the JSONL through the real
  importer reproduces the reported totals (25 attempts). Default HTML path
  `simulate.html` in cwd; custom `--html` honored.
- **pricing**: output matches `price_vintage()` exactly — v1, updated
  2026-10-02, 12 models, 8 tools, $1.17/min (~$70/hr loaded), status fresh.
  STALE branch forced by monkeypatching `PRICE_TABLE_UPDATED` to
  2025-01-01: prints `STALE — pricing table v1 is 640 days old ...`,
  exit 0.
- **Error paths (all exit non-zero, messages clear)**:
  missing file → 2 (`file not found`); bad `--format xml` → 2 (argparse
  invalid choice); no subcommand → 2 (`the following arguments are
  required: cmd`); missing `--format` → 2; `--attempts 0` and `-3` → 2
  (`--attempts must be >= 1`); `--attempts abc` → 2; malformed JSONL →
  2 (`failed to parse ... invalid JSON ...`).
- **Prior bug fix confirmed**: `--policy-cap 0` now replays (audit P1 fix):
  "Policy replay: max_cost_per_attempt=$0.0 ... Would have stopped 3 of 3
  runs". `--policy-yield 0.5` alone also works; `--policy-cap` +
  `--policy-yield` combos flow into `policy.simulate_policy(ledger,
  max_cost_per_attempt=..., yield_floor=...)` with matching signatures.
- **Security through CLI**: `--agent '<script>alert("xss")</script>'` —
  HTML contains only `&lt;script&gt;` (escaped; audit's report.py escaping
  holds on the CLI path). Zero network imports in cli.py.
- **C2/C3 fixes visible in CLI output**: text report stamps
  `Price table: v1 (verified 2026-10-02, 1 days old)`; human cost labeled
  `at $70.20/hr loaded — ASSUMPTION, not measured`.
- **argparse**: `--help` lists all three subcommands; `prog="averth"`;
  `--agent` override appears in HTML report.
- **Hardcoded values**: none of concern in cli.py — defaults
  (attempts=2000, seed=42, agent names, "simulate.html") are all exposed as
  flags; all dollar figures flow from `pricing` module constants.
- No TODOs, no dead functions, no unused imports in cli.py
  (argparse/os/sys all used).

## Severity counts

- CRITICAL: 0
- HIGH: 1 (H1)
- MEDIUM: 1 (M1)
- LOW: 4 (L1-L4)

## Recommendation

Ship-blocking: none. H1 should be fixed before the CLI is demoed to anyone
who might typo an output path — a Python traceback is the one thing the
CLI's error design was built to avoid. M1 is a one-line docstring edit.
