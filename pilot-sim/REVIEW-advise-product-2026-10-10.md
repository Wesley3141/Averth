# Product review: averth/advise.py (BYOK LLM advisor)

Reviewer: product-minded code audit, 2026-10-10.
Scope: `averth/advise.py`, CLI wiring in `averth/cli.py` (`_cmd_advise`),
tests in `tests/test_advise.py`. Compared every field against the real
`Tracker.pnl()` output (key list dumped from a live Tracker).

## Verdict

The architecture is right (BYOK, aggregates-only, LLM never touches
numbers, advisory label). But `_summary_from_pnl` is broken against the
real pnl schema: **9 of its 17 summary fields will be `null`** on every
real receipt. The LLM will receive a JSON blob that is mostly holes, and
the SYSTEM prompt's "never invent numbers" rule will either produce
"I don't have enough data" or hallucination. This must be fixed before
any prospect sees it. The investigate mode is additionally starved by a
thin attempt summary. Prompts are serviceable but will produce generic
slop without the data fix. Tests do not catch any of this.

---

## 1. `_summary_from_pnl` field audit (advise.py lines 41-68)

Dumped the real `pnl()` keys from a live Tracker. Results per field:

| Summary field (advise.py) | pnl key requested | Real pnl key | Verdict |
|---|---|---|---|
| attempts | `attempts` | `attempts` | OK |
| success_rate | `success_rate` | `success_rate` | OK |
| cost_per_attempt | `cost_per_attempt` | **none** — compute `cost_total / attempts` | **None** |
| cost_per_success | `cost_per_success` | **none** — real key is `per_success` (dict: model / retry_path / tools / human / fully_loaded) | **None** |
| cost_per_success_basis | `cost_per_success_basis` | **none** — derive: `inferred_outcomes >= attempts` → "UNKNOWN (no accepted-outcome labels)" | **None** |
| total_cost | `total_cost` | **`cost_total`** | **None** |
| buckets.measured/billed/estimated/unknown_calls | `data_quality.*` | `data_quality.*` | OK (all four keys verified present) |
| retry.count | `retries` | `retries` | OK |
| retry.path_cost | `retry_path_cost` | **`cost_retry_path`** | **None** |
| retry.top_reasons | `top_retry_reasons` | `top_retry_reasons` | OK |
| failed_run_waste | `failed_run_waste` | **none** — real keys are `cost_failed` + `failed_spend_share` | **None** |
| heavy_tail | `heavy_tail` | **none** — real key is `tail` (dict: p50 / p95 / max / top5pct_share / tail_label) | **None** |
| five_layers | `five_layers` | **none** — no such key anywhere; build from `avg_context_growth`, `context_tax`, `context_tax_share_of_model`, `cost_tools`, `yield_ratio`, `tail`, `per_model`, `cached_tokens`, `cache_savings` (this is what report.py lines 116-140 renders) | **None** |
| top_finding | `(pnl.get("findings") or [None])[0]` | **none** — findings live in `averth/insights.py:findings(p)`, which takes the pnl dict and returns ranked findings | **None, always** |

**Impact:** the JSON sent to the LLM contains `"total_cost": null`,
`"cost_per_attempt": null`, `"heavy_tail": null`, `"five_layers": null`,
`"top_finding": null`, etc. The recommend prompt asks for "expected
saving at the observed volume" — the volume (attempts) is present but the
cost figures are null. The SYSTEM prompt says "if a figure you need is
missing, say so instead of estimating," so the best case is a refusal and
the worst case is hallucinated numbers wearing the advisory label.

**Exact fix** — rewrite `_summary_from_pnl` (advise.py:41-68):

```python
def _summary_from_pnl(pnl: dict) -> dict:
    from averth.insights import findings  # local import: insights is optional-ish
    dq = pnl.get("data_quality", {})
    ps = pnl.get("per_success", {}) or {}
    tail = pnl.get("tail", {}) or {}
    attempts = pnl.get("attempts") or 0
    cost_total = pnl.get("cost_total") or 0.0
    inferred = pnl.get("inferred_outcomes", 0)
    # accepted-outcome honesty: mirrors report.py lines 65-69
    if attempts and inferred >= attempts:
        cps = {"basis": "UNKNOWN — no accepted-outcome labels joined; "
                        "per inferred success only", "per_success": ps}
    else:
        cps = {"basis": "per accepted outcome", "per_success": ps}
    found = findings(pnl)
    top = found[0] if found else None
    return {
        "attempts": attempts,
        "success_rate": pnl.get("success_rate"),
        "cost_per_attempt": (cost_total / attempts) if attempts else None,
        "cost_per_success": cps,
        "total_cost": cost_total,
        "buckets": {
            "measured": dq.get("measured"),
            "billed": dq.get("billed"),
            "estimated": dq.get("estimated"),
            "unknown_calls": dq.get("unknown_calls"),
        },
        "retry": {
            "count": pnl.get("retries"),
            "path_cost": pnl.get("cost_retry_path"),
            "top_reasons": pnl.get("top_retry_reasons"),
        },
        "failed_run_waste": {
            "dollars": pnl.get("cost_failed"),
            "share_of_spend": pnl.get("failed_spend_share"),
        },
        "heavy_tail": {
            "p50": tail.get("p50"), "p95": tail.get("p95"),
            "max": tail.get("max"),
            "top5pct_share": tail.get("top5pct_share"),
        },
        "five_layers": {
            "context_growth": pnl.get("avg_context_growth"),
            "context_tax": pnl.get("context_tax"),
            "context_tax_share_of_model": pnl.get("context_tax_share_of_model"),
            "tool_spend": pnl.get("cost_tools"),
            "yield_ratio": pnl.get("yield_ratio"),
            "per_model": pnl.get("per_model"),
            "cache_savings": pnl.get("cache_savings"),
        },
        "top_finding": ({
            "title": top.get("title"), "detail": top.get("detail"),
            "dollars": top.get("dollars"),
        } if top else None),
    }
```

Notes on the fix:
- `insights.findings(p)` has a $1.00 materiality floor (insights.py:33-37):
  small ledgers return `[]`, so `top_finding: None` is legitimate there —
  the prompt must tolerate it (see prompt rewrites below).
- Check what keys a finding dict actually carries before finalizing
  (`title`/`detail`/`dollars` assumed from the `_finding` call shape at
  insights.py:44-58 — verify).
- The local import avoids a hard dependency cycle if insights ever imports
  advise; alternatively import at module top (no cycle exists today).

---

## 2. MODE_PROMPTS rewrite (advise.py lines 85-105)

Current prompts are directionally right but will produce generic slop
("consider optimizing prompts," "monitor your usage") because they don't
constrain the LLM to the data or to the product's voice. Rewrites:

**recommend** — the money prompt; must be the sharpest:
```python
"recommend": (
    "Recommend the SINGLE change worth testing first. Your answer must "
    "name: (1) the exact step or failure mode from the ledger (quote the "
    "retry reason or finding title), (2) the concrete change to test, "
    "(3) the expected saving computed ONLY from the figures below "
    "(per-attempt waste x attempts = monthly figure; show the arithmetic). "
    "If no finding clears the bar of 'worth a prospect's engineering time', "
    "say so in one sentence and do not pad with generic advice. "
    "Never present inferred-success cost as accepted-outcome cost."
),
```

**explain** — fine structure, needs the honesty kicker and a tighter brief:
```python
"explain": (
    "Explain this cost receipt in plain English for the person who owns "
    "the budget (non-technical). Cover: what the workflow cost per "
    "attempt, where the money went in one sentence per major bucket, and "
    "the single most important caveat about the data quality "
    "(billed vs measured vs unknown). Under 150 words. No jargon, "
    "no hype, no recommendations — explanation only."
),
```

**investigate** — needs a comparison anchor or it narrates in a vacuum:
```python
"investigate": (
    "Explain why this attempt cost what it did. Walk through its cost "
    "components largest-first and name the single driver. Compare its "
    "total against the ledger's p50 and p95: if it is an outlier, say "
    "what makes it one (retries? human review? context growth?). "
    "End with one sentence on whether this looks fixable or structural."
),
```
For this prompt to work, the attempt summary must include the p50/p95
context — currently it doesn't (see section 3).

Also consider appending to SYSTEM: "When a summary field is null, treat
it as unknown and say so; never fill it in." (Currently implied by
"never invent numbers" but null-handling deserves one explicit line.)

---

## 3. Investigate mode: thin attempt summary (advise.py lines 71-82)

`_attempt_summary` pulls from `pnl["costliest_attempts"]`, whose entries
carry only 6 fields (tracker.py:605-610): case_id, total_cost, success,
retries, human_min, reopened. The full attempt dict has 30 fields,
including exactly what an outlier investigation needs:
`terminal_model_cost`, `retry_path_cost`, `tools`, `human_cost`,
`context_growth`, `context_tax`, `per_model`, `steps`, `total_tokens`,
`waste_tokens`, `billed_cost`, `outcome_inferred`.

With the current 6-field summary, "walk through its cost components
largest-first" is impossible — the components aren't in the prompt.

**Exact fix:** `costliest_attempts` is the right *source* (it's already
ranked), but the entries need enriching at the tracker level
(tracker.py:605-610), or `_attempt_summary` needs the full attempt.
Cleanest: enrich the pnl entries — every consumer benefits:

```python
# tracker.py, in the costliest_attempts comprehension, add:
{"case_id": ..., "total_cost": ...,
 "terminal_model_cost": a["terminal_model_cost"],
 "retry_path_cost": a["retry_path_cost"],
 "tools": a["tools"], "human_cost": a["human_cost"],
 "context_growth": a.get("context_growth"),
 "steps": a.get("steps"),
 "total_tokens": a.get("total_tokens"),
 "outcome_inferred": a.get("outcome_inferred", False),
 ...}
```

Then `_attempt_summary` passes these through, plus ledger p50/p95 for
the comparison anchor the rewritten prompt needs. Privacy check: none
of these fields contain prompts, completions, or customer data (case_id
is caller-provided and could theoretically contain PII — the existing
module docstring already discloses this class; keep the redact-before-
sharing guidance in the CLI help).

Default-to-costliest behavior (advise.py:121-127) is correct — max by
total_cost with `or 0` guard. One edge: ties or a ledger where the
max is $0.00 (all-unknown) — investigating a $0 outlier is noise; add
a guard that warns when the costliest attempt costs $0.

---

## 4. CLI UX (cli.py lines 78-96, 175-209)

`averth advise file --format X --mode Y` is the right shape. Gaps:

1. **No `--show-prompt` / `--dry-run`.** For a trust product, the single
   most valuable flag is one that prints exactly what would be sent to
   the LLM *without* spending the call. Prospects will ask "what does it
   see?" — this answers it. Add `--show-prompt` (print prompt, exit 0,
   no key required).
2. **No `--output`.** Advisory text worth keeping should go to a file:
   `--output advice.md`. Trivial to add, matches `--html` on trace.
3. **`--api-key` on the command line lands in shell history.** The help
   text already says "Prefer env vars" — good — but consider a
   `getpass` fallback or at minimum a stderr warning when `--api-key`
   is passed interactively. (Low priority; the env-first design is right.)
4. **Double-parse.** `advise` re-parses the trace file from scratch; a
   user who just ran `averth trace` pays the parse twice. Acceptable
   for v1, but a `--ledger` input (accept an exported ledger JSON)
   would compose better with the existing `policy.export_ledger` flow.
5. **Missing `--agent` passthrough is present** (line 93-94) — good.
6. Error paths are clean (file-not-found → 2, no key → 2 with "No API
   key" on stderr, key never echoed). Verified in tests.

Suggested flag set: `--mode`, `--provider`, `--api-key`, `--attempt`,
`--agent` (all present) + `--show-prompt`, `--output` (missing).

---

## 5. Tests (tests/test_advise.py) — several are tautological

- `test_recommend_advisory_label`: meaningful (label + transport passthrough).
- `test_explain_mode`: **weak** — asserts only the label. Add: prompt
  contains the mode instruction and the summary JSON.
- `test_investigate_defaults_to_costliest`: meaningful (checks "t1" in prompt).
- `test_investigate_bad_case_id`: meaningful.
- `test_prompt_contains_aggregates_not_raw_traces`: **tautological for its
  purpose.** It asserts `"attempts" in prompt` — but "attempts" appears in
  the JSON *key* even when the value is None (`"attempts": 1` vs
  `"cost_per_attempt": null` — the key is present either way). This test
  passes on the current broken summary and would not catch the 9-field
  None bug. It also never actually verifies the absence of raw trace
  content.
- `test_build_prompt_all_modes`: **tautological** — `len(p) > 50` proves nothing.
- `test_resolve_key_*` (3 tests): meaningful.
- `test_cli_advise_no_key_clean_error`: meaningful and good (checks the
  key never appears in output).
- `test_cli_advise_missing_file`: meaningful.

**The missing test that matters** — the one that would have caught
section 1:

```python
def test_summary_has_no_unexpected_nones():
    # Regression: _summary_from_pnl must map to real pnl() keys.
    # Every field below was None before the fix (wrong key names).
    from averth.advise import _summary_from_pnl
    s = _summary_from_pnl(_pnl())
    assert s["total_cost"] is not None
    assert s["cost_per_attempt"] is not None
    assert s["retry"]["path_cost"] is not None
    assert isinstance(s["heavy_tail"], dict) and s["heavy_tail"]["p95"] is not None
    assert isinstance(s["five_layers"], dict)
    assert s["cost_per_success"]["basis"] is not None
```

Additional tests to add:
- `_attempt_summary` includes cost components (terminal_model_cost,
  retry_path_cost, tools, human_cost) once section 3 is fixed.
- `build_prompt("investigate", ...)` includes p50/p95 context.
- `--show-prompt` CLI flag prints the prompt and exits 0 without a key
  (once added).
- Prompt privacy: assert the built prompt contains no `events` payloads
  / no per-call token arrays beyond aggregates (documents the privacy
  contract in code).

---

## 6. Smaller correctness notes

- **Model names** (`_call_anthropic`: "claude-sonnet-4-5"; `_call_openai`:
  "gpt-5.6"): verify these are current valid model IDs; a wrong ID fails
  at call time with a confusing provider error. Consider making the model
  a module constant so it's greppable.
- **`max_tokens: 600`** for OpenAI chat completions is correct param
  name; fine. For Anthropic it's also `max_tokens`. OK.
- **`resolve_key` provider inference** (advise.py:155-172): if a user
  passes `--api-key` without `--provider`, it defaults to anthropic —
  an OpenAI key will then fail with an auth error against the wrong
  endpoint. Consider a cheap heuristic is *not* advisable (key prefixes
  are not contractual); better: error message telling the user to pass
  `--provider`. One-line improvement in the RuntimeError path — actually
  the cleaner fix is: when `--api-key` is given without `--provider`,
  raise a clear error asking for `--provider` instead of guessing.
- **`default=str` in `json.dumps`** (build_prompt): fine for Decimals,
  but masks type bugs — with the section-1 fix the summary should be
  JSON-native; consider dropping `default=str` so a non-serializable
  value fails loudly in tests rather than silently stringifying.
- **Timeout 60s, no retry**: acceptable for v1; a 429/5xx surfaces as
  "advisor failed: ...". Fine.
- **`_transport` seam**: good design, tests use it correctly, no real
  LLM calls in the suite. Confirmed zero network in tests.

---

## Priority order for the parent

1. **P0 — fix `_summary_from_pnl`** (section 1). 9 null fields; the
   feature is broken without it.
2. **P0 — add the `test_summary_has_no_unexpected_nones` regression
   test** so this can never silently regress.
3. **P1 — enrich investigate attempt data** (section 3) + rewritten
   prompts (section 2). These two ship together; the new investigate
   prompt needs the new data.
4. **P2 — `--show-prompt` and `--output` CLI flags** (section 4).
5. **P3 — provider-guessing fix, model-name constants** (section 6).
