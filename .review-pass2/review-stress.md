# Hostile review: averth/stress.py (review pass 2, 2026-10-02)

Reviewer posture: prove this is not production-ready. Every number below was
measured by running the code, not by reading it. File:line refs are to
`~/workspace/averth/averth/stress.py` unless noted.

Method: `~/workspace/averth/.review-pass2/measure_stress.py`,
`check_branch.py`, `check_runaway_share.py` (kept alongside this file).
Canonical workload for measurements: `generate(seed=42, attempts=2000)`
unless noted.

## What verified CLEAN (with receipts)

1. **Determinism.** Two `write_jsonl(seed=7, attempts=500)` runs are
   byte-identical (sha256 match); seed 8 differs. `generate` uses only
   `random.Random(seed)`; no wall-clock, no dict-ordering, no global RNG
   leakage. Module docstring "Deterministic for a fixed seed" is TRUE.
2. **Shape mix matches the coded thresholds.** seed=42, n=2000 (counted by
   monkeypatching the shape methods): quick_resolve 52.60% (target 55),
   standard 22.00% (20), retry_storm 10.40% (10), escalation 5.00% (6),
   failed_clean 4.25% (4), runaway 1.85% (2). Sampling noise only.
3. **All five cost layers genuinely exercised** (seed=42, n=2000):
   avg_context_growth 5.60, context_tax $770.67, cost_tools $188.89,
   retries 1841, yield_ratio 0.0508, cost_failed $798.41,
   tail top5pct_share 0.7899, max $33.52 vs p50 $0.0118 (2840x),
   per_model 4 keys, escalations 100, cost_human $763.54,
   cached_tokens 1,726,489, cache_savings $0.08 > 0. Not stubbed.
4. **Runaways land in the tail.** All 10 costliest attempts are failures;
   costliest = $33.52 failed runaway. Docstring claim TRUE.
5. **Failed attempts read as 100% waste.** Single failed attempt through a
   bare Tracker: yield_ratio = 0.0. Docstring claim TRUE.
6. **Dead branch does not smear the productive merge step.** 53 branched
   attempts inspected: the dead branch's pre-retry steps are retro-marked
   waste, the redo starts fresh, and the unbranched merge step is never
   marked waste (merge marked waste: 0 in all 53). Docstring claim TRUE.
7. **Round-trip dollar integrity.** `write_jsonl(seed=7, attempts=500)` →
   `jsonl.load_jsonl` → `common.tracker_from_ledger`: EVERY pnl key
   (floats to 1e-9, ints, dicts, lists, price_vintage) matches the direct
   tracker. The 14 keys the test suite checks are a subset; the full dict
   was compared. No silent corruption.
8. **Edge cases.** `attempts=0`: pnl() returns attempts=0, cost_total=0;
   0-byte JSONL loads to an empty tracker without raising. `attempts=1`
   fine. Unknown-model KeyError would fail loud (all four generator models
   exist in pricing.py).
9. **Security.** Imports: `json`, `random`, `.tracker`. Zero network
   imports, no eval/exec/subprocess, no secrets. Nothing to exfiltrate with.
10. **`averth simulate` end-to-end works** (CLI → stress.generate → report +
    HTML), 20k attempts in ~4s wall.

## Findings

### HIGH

**H1. Docstring says "failed-then-reopened runs"; the code generates
accepted-then-reopened successes.** `averth/stress.py:27` (module
docstring) lists "failed-then-reopened runs" as a workload pathology.
The actual shape (`averth/stress.py:206-210`) is:

```python
# reopened success: accepted, then the customer came back
g._router_triage()
g.model(*WORKER, out_base=300)
g.end(success=True, reopened=True)
```

`success=True`, `business_value=11.20` — the run SUCCEEDED and was later
reopened. There is no failed-then-reopened shape anywhere in the file.
A reader (or a prospect reading the shipped docstring) gets the wrong
mental model of what the workload contains. The code's own comment says
"reopened success", so the docstring contradicts both the code and its
comment. Per rubric item 7 (docs-vs-code), HIGH.

**H2. README claims the `averth simulate` workload's "2% runaways ... burn
most of the budget" — measured 27-44%, never most.**
`README.md` "Adversarial simulation" section describes `averth simulate`
(which is `stress.generate` per `averth/cli.py:91-99`) as having "2%
runaways that burn most of the budget". Measured with runaway attempts
exactly tagged (monkeypatched `_Gen.runaway`):

| seed | attempts | runaways | runaway budget share | top-5% share |
|------|----------|----------|---------------------|--------------|
| 42   | 2000     | 1.85%    | 43.5%               | 78.9%        |
| 7    | 2000     | 1.60%    | 27.1%               | 71.6%        |
| 123  | 2000     | 2.10%    | 38.7%               | 73.6%        |
| 99   | 2000     | 1.55%    | 33.5%               | 73.0%        |
| 7    | 5000     | 1.72%    | 29.9%               | 72.0%        |

"Most" means majority; the runaways never exceed 44%. What IS true is
that the top 5% of attempts (which contain the runaways plus retry
storms) burn 72-79% — and the 61% figure belongs to `demo.py`'s separate
generator (`README.md` correctly attributes 61% to the demo). The README
sentence conflates the two. Anyone who runs the documented command
(`averth simulate --attempts 2000 --seed 42`) and checks the proof line
against the generator's actual runaway share gets a false statement.
Misleading docs about the generator's headline statistic: HIGH.

### MEDIUM

**M1. Round-trip loses the agent name: "synthetic-support" → "jsonl-import".**
Full-pnl comparison found exactly one mismatch: `p["agent"]`. The EVENT
schema (`averth/importers/jsonl.py`) has no agent event type, and
`load_jsonl(path, agent_name="jsonl-import")` stamps the default. All
dollar figures round-trip exactly, so this is label-only, no financial
impact — but README's "reproduces the identical P&L" is not literally true
(the `agent` label differs), and a prospect diffing the two P&Ls will see
it. MEDIUM.

**M2. `HUMAN_VALUE_PER_CASE = 11.20` is hardcoded with no override.**
`averth/stress.py:24`; `generate()` exposes `seed`, `attempts`,
`agent_name`, `record_events` — but no `value` knob, so the $11.20/case
business value (which feeds value/ROI figures) cannot be changed without
editing source. Undated, unsourced, unparameterized: the same class of
assumption the audit flagged as C3 for the $70/hr labor rate, baked into
the canonical "production-shaped" workload. MEDIUM.

**M3. Latent inconsistency in `_Gen.tool` for branched tool failures.**
If a branch-scoped tool call failed, `self.t.log_retry(reason)` fires a
GLOBAL retry (`retry_all=True`) while the tool step itself is
branch-scoped — smearing all subsequent steps as waste, contradicting the
branch-scoping the module docstring brags about. Currently unreachable:
every branched tool call in the shapes passes `fail_rate=0.0`
(`averth/stress.py:116`). But the mirror helper's contract is wrong for
the first person who adds `fail_rate` to a branched tool call, and the
failure mode is silent yield corruption, not a crash. MEDIUM.

### LOW

**L1. `_Gen` reaches into Tracker privates** (`self.t._cur["case_id"]`
at stress.py:86, 138, 142, 146, 149, 153; `self.t.attempts[-1]` at
stress.py:149). Same-package coupling; works today, brittle tomorrow.
Rename risk is real (`_cur` is underscore-private).

**L2. Cache-savings claim is technically true but economically vacuous.**
Cache hits "show up as savings rather than vanishing": $0.0777 of savings
on $818.00 of model spend (0.0095%). The cached call is the cheap nano
triage router at ~900 input tokens with `cache_frac=0.70` — the workload
demonstrates the metering of cache discounts, not cache economics. A
prospect could reasonably expect the "prompt-cache hits" bullet to move a
number. Note, not a bug.

**L3. README "20k attempts meter in about a second" is ~3x optimistic.**
Measured: `generate(20000)` = 3.17s; CLI end-to-end (`simulate`) ~4s wall.
(README claim, not stress.py's; the module itself makes no perf claim.)

**L4. `write_jsonl` silently overwrites an existing file.** No
existence check, no warning. Standard footgun, low stakes.

## Severity counts

- CRITICAL: 0
- HIGH: 2
- MEDIUM: 3
- LOW: 4

## Notes for the coordinator

- No prompt-injection content encountered (no web use in this review).
- The outreach proof line ("most expensive 5% ... 61% of total spend") is
  sourced from `demo.py`, not `stress.py` — README attributes it
  correctly. But `stress.generate(seed=42, attempts=2000)` yields 79% for
  its top 5%, so the two shipped "2,000-run workloads" disagree with each
  other by 18 points. If the proof line ever gets attached to `averth
  simulate` output, it will be wrong. Worth a docs pass beyond this file.
- Measurement scripts kept at
  `~/workspace/averth/.review-pass2/measure_stress.py`,
  `check_branch.py`, `check_runaway_share.py`.
