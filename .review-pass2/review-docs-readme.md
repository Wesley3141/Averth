# Docs-vs-code review: README.md (175 lines) — 2026-10-02

Reviewer posture: hostile. Every behavioral claim in README.md was checked
against the fixed code (post-C1–C3/H1–H4/M1–M3) by running it, not by reading
it. Rubric item 7 applied ruthlessly.

Method: ran the instrument snippet, the policy snippet, `demo.py`,
`averth simulate`/`averth trace` (via `python3 -m averth.cli`), a 20k
determinism+timing check, a legacy-ledger degradation probe, and grepped
`tracker.py`, `pricing.py`, `policy.py`, `report.py`, `cli.py`,
`importers/*`, `integrations/langchain.py`, `stress.py`, `pyproject.toml`.

## Verdict

The headline numbers are honest and current ($0.20/$0.82 verified against a
fresh `demo.py` run). No stale $0.03/$0.62 anywhere. But the README has one
genuinely misleading code example (policy output comment is unattainable
from the shown snippet), one undisclosed always-on side effect (HTML files
written on every CLI run), and two dead doc references. The budget-hook and
pricing-scheme questions the assignment posed both come back clean.

---

## CRITICAL

None. (The README's dollar figures are all currently accurate.)

## HIGH

### H1. Policy example's shown output is impossible to produce from the shown snippet (README.md:68-77)

The snippet operates on `t`, the 1-attempt tracker built in the Instrument
section above it:

```python
P.export_ledger(t, "ledger.json")   # metadata only: no prompts, no customer data
ledger = P.load_ledger("ledger.json")
sim = P.simulate_policy(ledger, max_cost_per_attempt=6.00, yield_floor=0.50)
print(P.policy_text(sim))
# "Would have stopped 1020 of 2000 runs: 426 failed (pure savings $297.18)
#  and 594 that went on to succeed (collateral $897.79 — good outcomes this
#  policy would have destroyed)."
```

Ran it verbatim (single successful $5.30 attempt, cap $6.00, yield floor
0.50). Actual output:

```
Policy replay: max_cost_per_attempt=$6.0, yield_floor=0.5
Would have stopped 0 of 1 runs: 0 failed (pure savings $0.00) and 0 that went on to succeed (collateral $0.00 — good outcomes this policy would have destroyed).
```

The quoted numbers (1020/426/$297.18/594/$897.79) are real — they match
`demo.py`'s policy replay exactly — but they are the output of running the
same three lines against the **demo ledger**, not against `t`. A reader who
runs the README's getting-started flow top to bottom gets different output
than the comment promises and will reasonably conclude the library is
broken. Fix: run the example against the demo ledger, or relabel the
comment as demo-ledger output. Per rubric item 7 (docstring says X, code
does Y) this is HIGH: misleading docs in the onboarding path.

## MEDIUM

### M1. `--html` is described as opt-in; the CLI writes an HTML report unconditionally (README.md:160-167)

README: "The text report prints to stdout; `--html` writes a one-page HTML
report (defaults to `<inputfile>.html` in the current directory)."

Code (`averth/cli.py`):
- `_cmd_simulate` (line 102): `return _report_and_html(tracker, args.html or "simulate.html")` —
  `averth simulate` **always** writes `simulate.html` into the CWD, flag or no flag.
- `_cmd_trace` (lines 180-185): without `--html`, writes `<basename>.html` into the CWD.

Verified empirically: `python3 -m averth.cli trace --format jsonl /tmp/sim.jsonl`
printed the text report AND created `./sim.html` in the working directory
(no `--html` passed). Note it is basename-based, so tracing `/tmp/sim.jsonl`
writes `./sim.html` in the CWD — not next to the input file, and colliding
across runs in the same directory. The README's framing ("`--html` writes…")
implies no HTML without the flag; the truthful version is "an HTML report is
always written (default `<basename>.html` in CWD); `--html PATH` overrides the
path." Undisclosed side effect + wrong opt-in framing = misleading docs.

### M2. Two dead doc references (README.md:58, README.md:175)

- Line 58: `see ../research/agent-pnl/five-cost-layers.md`. That file lives
  at `~/workspace/research/agent-pnl/five-cost-layers.md` — **outside the
  Averth repo**. From the repo root on GitHub, `../research` does not exist;
  the link is dead for every external reader.
- Line 175: `See ~/workspace/research/agent-pnl/PLAN.md`. A machine-local
  absolute path. Meaningless to anyone but Wesley on this VM.

For a repo whose install line points at a public GitHub URL, both
references should be in-repo files (or real URLs).

### M3. "Pre-hardening ledgers … retry-path cost unknown" is not what the code does (README.md:119-120)

README Known-limits bullet: "Pre-hardening ledgers load without crashing;
new fields degrade to documented defaults (retry-path cost unknown,
context tax $0)."

Two inaccuracies, both verified by running:
1. Retry-path does **not** degrade to "unknown" — it degrades to **$0.00**,
   printed indistinguishably from "no retry waste". Probe: legacy-shaped
   ledger (only the pre-hardening keys) → `report_text` prints
   `Retry path: $0.00`; `pnl()["cost_retry_path"] == 0.0` (the test suite
   even asserts this: `tests/test_tracker_hardening.py:251`). Nothing in the
   report says "unknown" for retry path. $0.00-vs-unknown is a meaningful
   interpretive difference (absent waste vs unmeasured waste).
2. "Load without crashing" holds only for the narrow legacy schema the test
   suite defines (it still includes `per_model`, `context_growth`, etc.).
   A ledger missing `per_model` — itself a newer field — crashes `pnl()` and
   `report_text` with `KeyError: 'per_model'` (reproduced). `pnl()` uses
   `.get()` defaults for `retry_path_cost`, `terminal_model_cost`,
   `context_tax`, `cache_savings`, `cached_tokens`, `retry_tool_cost`,
   `context_growth` (`tracker.py:383-421`) but hard-indexes `per_model`
   and the core cost fields. The blanket claim overpromises.

## LOW

### L1. "20k attempts meter in about a second" is ~4x off end-to-end (README.md:105)

`pnl()` aggregation alone on 20k attempts: **0.51s** ✓. But the sentence
("Use it to stress the meter…") points at `averth simulate`, whose full run
(generate 3.27s + report) measured **4.1s** wall on this machine
(`time python3 -m averth.cli simulate --attempts 20000 --seed 42`). A user
running the suggested command waits ~4s, not ~1s. Defensible if "meter" =
`pnl()` only; the surrounding sentence invites the end-to-end reading.

### L2. Output-list wording vs the text report (README.md:52-55)

- "reopen rate" — the text report shows a count ("Reopened: 73 accepted
  outcomes reopened"), not a rate.
- "costliest attempts" — the text report has no costliest-attempts list
  (only the layer-4 tail line); the per-run table exists only in the HTML
  report (`report.py:301-307`). The Output list blends text+HTML outputs
  without saying so.

### L3. "no customer data" in the ledger vs verbatim free-text metadata (README.md:24, 70)

The ledger export preserves retry reasons and escalation notes verbatim
(`policy.export_ledger` exports `events`; `importers/common.py` notes events
"preserve retry reasons (H5)"). These are user-supplied free-text strings —
if a caller logs customer data in a retry reason, it lands in the exported
ledger. The "no customer data" guarantee holds for prompts/completions/
payloads (the meter never records those) but is only as strong as caller
discipline for the free-text metadata fields. Docs-precision nit; the audit's
security PASS stands.

### L4. README is silent on the versioned pricing scheme (no "edit as vendors change them" language — verified absent)

Grep confirms the README contains **zero** mentions of version, vintage, or
staleness, and does not contain the old "edit as vendors change them"
phrasing. Pricing is described only as "per-provider pricing tables"
(line 48). Not contradictory — but the marquee C2 hardening (versioned
table, staleness warning, `averth pricing`, vintage stamped on every report,
verified live in `demo.py` output: "Price table: v1 (verified 2026-10-02,
1 days old)") is invisible to a README-only reader. Consider one line under
Known limits.

---

## Verified clean (ran the code; no finding)

- **Instrument example** runs end-to-end; all API names, kwargs
  (`budget_per_success`, `case_id`, `cached_input_tokens` default,
  `extra_model_cost`, `business_value`) and the `report_text(...,
  token_dashboard_per_success=0.03)` call work as shown.
- **Five-layers description** (README 58-62) matches `tracker.py`: context
  compounding (growth ratio + dollar tax, 241-257), external tool spend,
  yield ratio (terminal/total, failed = 100% waste, 259-266), heavy tail
  (interpolated p50/p95/max + top-5% share, 441-449), per-model attribution +
  loaded human cost.
- **Budget hook**: README does **not** imply success-only. The C1 fix is in
  place — `tracker.py:362-370` fires the hook / raises for **any**
  over-budget attempt ("whatever its outcome"); `pnl()` counts all
  over-envelope attempts (`budget_breaches`) with `budget_breaches_failed`
  split out (459-468). `demo.py` itself reports "Budget breaches captured
  by on_breach hook: 96". No README change needed on this point.
- **Demo numbers**: fresh `demo.py` run → token dashboard **$0.20** vs
  fully-loaded **$0.82** (4.1x), **4.7x** context growth, **6%** yield,
  top 5% consuming **61%** of budget — all match README lines 42-44 and 80-82
  exactly. No stale $0.03/$0.62 anywhere in the file.
- **Adversarial-simulation claims**: 2% runaways (`stress.py:231-243`,
  `r >= 0.98`), 1.15–1.6x context growth (line 75), 70% cache-hit triage
  router (line 144, `cache_frac=0.70`), parallel 3-branch fan-out
  (research/billing/history, lines 161-165) — all verified in code. Same
  seed → byte-identical P&L to the cent (verified True for 2000 attempts).
  JSONL round-trip asserted in `tests/test_stress.py:66`
  (`test_jsonl_roundtrip_identical`). `averth trace --format jsonl`
  reproduces the report (ran it).
- **CLI surface**: `--policy-cap`/`--policy-yield` (cli.py:45-47),
  `--format otel|langsmith|jsonl`, importers `jsonl.load_jsonl`,
  `common.tracker_from_ledger`, `otel.load_otel`, `langsmith.load_langsmith`
  all exist as documented.
- **LangChain**: `AverthCallbackHandler(tracker)` signature matches;
  handler opens/closes attempts on outermost chain start/end/error and meters
  LLM calls, tool use, and errors (`integrations/langchain.py:100-140`).
- **Install**: `requires-python = ">=3.9"` ✓; `[langchain]`/`[openai]`
  extras exist in `pyproject.toml` ✓ (direct-reference `@ git+…` syntax is
  valid PEP 508; repo existence taken from project memory, not re-verified).
- **Known-limits bullets** (all verified): importer strictly rejects
  `cached_input_tokens > input_tokens` (`importers/jsonl.py:119-123`);
  live `Tracker.log_model_call` clamps instead of raising
  (`tracker.py:178-179`); `extra_model_cost` double-count warning matches
  `log_retry` semantics (adds to `retry_cost`; logging the step too would
  double-count); waste-lenses-not-additive matches the report's own
  "(lenses, not additive)" label and overlap design; cache-read discount
  override via `Tracker(cache_read_discount=...)` exists (`tracker.py:106,
  121-122`); yield-counts-failed-as-waste paragraph matches the yield
  computation.
- **No network posture**: not re-audited here (covered by the Phase-1 audit);
  nothing in the README contradicts it.

## Files touched during verification (cleanup)

- `/tmp/sim.jsonl`, `/tmp/s20k.jsonl`, `/tmp/t-ledger.json`, `/tmp/leg*.json`,
  `/tmp/simulate.html` — all removed or in /tmp.
- `~/workspace/averth/sim.html` (created by my `averth trace` run) — removed.
- `~/workspace/averth/simulate.html` (rewritten by my `averth simulate` run)
  — removed; it was untracked/ignored, `git status` clean apart from the
  pre-existing Phase-1 modifications.
