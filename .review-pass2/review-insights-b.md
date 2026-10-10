# Hostile review: averth/insights.py lines ~175-258 (findings 5-9, top_insight, findings_text)

Reviewer: insights-b lane. Scope: findings 5 (context_tax), 6 (reopened),
7 (low_yield), 8 (unpriced_spend), 9 (cache_savings), top_insight(),
findings_text(), the dollars-desc/severity-tiebreak sort, and the $1 noise
floor. Findings 1-4c are another reviewer's; not touched here.
Context: AUDIT-2026-10-02.md read; reviewing Phase-1-fixed code.

Method: every rule below was executed, not eyeballed. Three scratch
ledgers (/tmp/h2_verify*.py, since deleted) drove findings() with
hand-computed expectations: branch retry + extra_model_cost, failed
reopened attempts, zero-model-spend ledgers, 7 unpriced models,
NaN/inf/$0.99 totals, estimate-path cached tokens, and 1000x context
growth. Deltas are to 1e-9.

Security note: no web touched in this review; no injected directives
encountered. Package surface of insights.py: `import math` only, no
network, no deserialization, findings_text() is plain text (no HTML
injection surface).

---

## CRITICAL

### C1. low_yield dollars understate waste by exactly extra_model_cost — the "EXACT" identity comment is false
`averth/insights.py:205-207`:
```python
    # 7. Yield below the healthy band. Dollars are EXACT, not a ratio
    # approximation (H1): model spend minus terminal-path model spend is
    # precisely the model dollars off the terminal path.
    if p["yield_ratio"] < 0.60 and total > 0:
        waste_model_dollars = p["cost_model"] - p["cost_model_terminal"]
```
`tracker.py` `end_attempt` establishes the identity
`terminal + retry_path = model + retry_cost`, where `retry_cost` is the
`extra_model_cost` passed to `log_retry()` — model spend that is, per its
own docstring, "spend NOT otherwise logged as a model step (e.g. the
failed call that triggered this retry...)". That spend is unambiguously
model dollars off the terminal path, but `cost_model - cost_model_terminal`
excludes it. The true off-terminal-path model spend is `cost_retry_path`
(equivalently `cost_model + cost_retry - cost_model_terminal`).

Repro (executed):
```
attempt: 5000-in-token step on branch x, log_retry("bad schema",
         extra_model_cost=3.0, branch="x"), 5000-in redo step, success.
pnl: cost_model=3.0363  cost_model_terminal=0.0188  cost_retry=3.0000
     cost_retry_path=3.0175   (terminal+retry_path == model+retry == 3.0363 ✓)
finding low_yield dollars = $0.0175   (reported)
true off-terminal-path    = $3.0175   (cost_retry_path)
missing                   = $3.0000   == extra_model_cost, exactly
```
The report prints: "Failed attempts and retry paths together discarded 49%
of all tokens ($0.02 of model spend)" — a 172x understatement, and it
directly contradicts finding 3 (`retry_waste`) in the SAME report, which
correctly prices the identical retry paths at $3.02 via
`cost_retry_path + cost_retry_tools`. Two findings, one report, two
different dollar figures for the same waste. The comment's "precisely"
claim is what makes this CRITICAL rather than a rounding nit: the code
asserts an identity that its own tracker's bookkeeping disproves.
Fix: `waste_model_dollars = p["cost_retry_path"]`.

---

## HIGH

### H1. reopened finding prints a self-contradictory sentence when the reopened attempt failed
`averth/insights.py:186,194-199`:
```python
    reopened_ok = p.get("reopened_successful", p["reopened"])
    ...
            "%d accepted outcomes were reopened. Their first-pass cost was "
            "booked as success, then the work repeated."
            % reopened_ok,
```
The H7 counting itself is correct (verified: a failed+reopened attempt
yields `reopened_successful=0`, `reopened=1` — only successful attempts
count). But the gate fires on `reopened_spend_share >= 0.10`, which counts
the failed redo's spend, so the finding fires and prints:

"0 accepted outcomes were reopened. Their first-pass cost was booked as
success, then the work repeated."

Repro (executed, total=$10.00, above the noise floor): a $2 successful
attempt plus an $8 reopened attempt that FAILED → finding fires, text says
"0 accepted outcomes were reopened". The second sentence is then factually
false — the first-pass cost was booked as *failure*, not success — and
"Their" dangles with no referent. A user reading this concludes the meter
is confused about its own counting. Either the gate should require
`reopened_successful > 0`, or the text must branch on `reopened_ok == 0`.

### H2. unpriced_spend detail misstates cost provenance for direct API users
`averth/insights.py:217-219`:
```python
            "Models without a pricing-table entry (%s%s) were costed at "
            "the documented fallback estimate."
```
True for the shipped integrations (`integrations/openai.py:84`,
`integrations/langchain.py:195` route through
`pricing.estimated_model_cost` → `ESTIMATED_MODEL_PRICES`). FALSE for any
direct caller of the public `Tracker.log_model_cost_estimate()`, whose
docstring says it "takes the dollar cost directly" — the caller may pass
their own measured invoice cost, and the report will still claim it was
"the documented fallback estimate". The provenance claim is about the
user's own data and it is wrong whenever the cost did not come from the
fallback. Docs-vs-code: the sentence should say "were costed by estimate
(caller-supplied or the documented fallback)" or the tracker should record
which path was used.

---

## MEDIUM

### M1. cache_savings title attributes savings to a token base they were not computed on
`averth/insights.py:228-230`:
```python
            "Prompt cache saved $%s on %s input tokens"
            % (..., "{:,}".format(p["cached_tokens"])),
```
`cached_tokens` aggregates cache-read tokens from BOTH priced calls and
`log_model_cost_estimate` calls — but the estimate path explicitly does
"no cache math on an already-estimated number" (`tracker.py:206-208`), so
estimate-path cached tokens contribute zero to `cache_savings`. Repro
(executed): 4000 priced-path cached tokens + 600 estimate-path cached
tokens → title reads "Prompt cache saved $0.01 on 4,600 input tokens"
while the $0.01 was computed on 4,000. The implied savings rate is
understated ~15% and the sentence asserts a relationship between the
dollars and the token count that does not hold. Fix: track
priced-path cached tokens separately, or qualify the title.

### M2. low_yield fires on $0.00 of model spend — the one rule with no dollar materiality floor
`averth/insights.py:204`: `if p["yield_ratio"] < 0.60 and total > 0:` —
no `waste_model_dollars > 0` guard, unlike rules 5 (`context_tax > 0`),
6 (`cost_reopened > 0`), and 9 (`cache_savings > 0`). Repro (executed):
tool-only ledger, `cost_model=0.00`, `yield=0.000` → finding fires:
"Only 0% of tokens were on a terminal path … ($0.00 of model spend)".
The module docstring promises "No finding fires on noise: every rule has
a materiality threshold" — this rule's threshold is token-based while its
dollars are zero, so it reports a waste finding about $0.00. Add
`waste_model_dollars > 0` to the gate.

---

## LOW

### L1. Dead defensive fallback with silent semantic drift
`averth/insights.py:186`: `reopened_ok = p.get("reopened_successful", p["reopened"])`.
`pnl()` unconditionally sets `"reopened_successful"` (`tracker.py:486`),
so the fallback never fires on real output. On a foreign/hand-built dict
missing the key it silently reverts to counting ALL reopened attempts
including failed ones — the exact semantics the H7 comment says must not
be used. Either drop the fallback (the function's contract is "a pnl()
dict") or keep H7 semantics in the fallback.

---

## Verified OK (hand-checked, no finding)

- **context_tax math** (`insights.py:175-184`, `tracker.py:318-328`): tax =
  Σ (in − base_in)/1e6 × cache-discounted effective input price over
  steps[1:], exactly the "first step's input size at that step's own
  price" counterfactual. Repro: single attempt in=[100, 200000, 200000],
  pin=2.50 → hand 0.999500 = code 0.999500. Gate `share >= 0.25 and
  tax > 0` correct; negative tax (shrinking context) correctly never
  fires; estimate-path steps (`in_price=0.0`) correctly contribute no tax
  rather than a wrong one. Title "added $1.00 (100% of model spend)"
  matches share=0.9993.
- **reopened_successful counting** (`tracker.py:384-385`): failed+reopened
  attempt → `reopened=1, reopened_successful=0` ✓ (H7 honored).
- **low_yield identity when extra_model_cost=0**: reported dollars ==
  cost_retry_path to the cent (test A: $8.00 == $8.00) — the bug is
  specifically the extra_model_cost exclusion, not the split logic.
- **cache_savings math**: hand 0.040500 = code 0.040500
  (2 × 9000/1e6 × pin × (1−0.10)); `cached>input` clamp and d=1.0
  (savings=0 → no fire) paths reviewed.
- **Sort order** (`insights.py:240-241`): dollars descending verified on a
  live 3-finding ledger; severity tiebreak HIGH<M
...[truncated 1167 chars]
