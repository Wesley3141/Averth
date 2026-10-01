# HOSTILE REVIEW — averth `hardening-pass` branch

Reviewer posture: adversarial. Mission was to break the meter, not praise it.
Baseline: master 27d82ee. Test suite: 112 passed before and after this review
(no repo files modified; repro scripts live in /tmp/attack{1,2,3}.py).

**Bottom line:** the additive dollar arithmetic is sound (no double-counting
found in any presented-as-additive bucket), and legacy-ledger degradation
works for real old ledgers. But the waste *attribution* has three concrete
misattribution bugs, the live Tracker API can be crashed or NaN-poisoned by
adversarial numerics, two importer paths have real parsing bugs, the insights
engine is simultaneously blind to whole pathological shapes and trigger-happy
on trivial spend, and several report numbers are approximations presented
without the caveats the code clearly knows about.

---

## 1. DOUBLE-COUNTING — verdict: CLEAN (with one presentation caveat)

Verified numerically (`/tmp/attack1.py`, section A) across a mixed ledger
(branch retries + reopened + unpriced estimate + cached tokens):

- `cost_model_terminal + cost_retry_path == cost_model + cost_retry` (exact)
- `per_success` parts (terminal + retry_path + tools + human) sum exactly to
  `fully_loaded`, and `cost_total == fully_loaded × successes`
- `unpriced_spend ⊆ cost_model`; `context_tax` and `cache_savings` are lenses,
  never added to totals
- Branch waste flags are per-step booleans, never double-summed

The only double-count vector is `log_retry(extra_model_cost=...)` for spend
already logged as a step — explicitly warned against in the docstring. Fine.

**Caveat (H4 below):** `failed_spend` and `retry_waste` findings overlap by
construction (a failed attempt's retry-path spend is in both). `report_text`
carries a "lenses, not additive" disclaimer; `insights.findings_text()` and
the HTML finding cards do not — a reader summing finding dollars double-counts.

---

## 2. MISATTRIBUTION — 4 concrete bugs

### M1 (High): dead branch's discarded work is booked as terminal/useful
`averth/tracker.py` — `end_attempt` marks waste only for steps logged
*after* a retry marker. A branch-scoped `log_retry(branch="dead")` does not
retroactively mark the dead branch's earlier steps, so the discarded output
that the retry explicitly rejected lands in `terminal_model_cost`.
Repro (`/tmp/attack1.py` §B):
```
t.log_model_call(..., branch="dead")   # discarded work
t.log_retry("dead branch returned conflicting data", branch="dead")
...
dead_first["retry"] is False  →  counted in terminal_model_cost
```
The stress generator's own fan-out (`stress.py` `standard()`) produces this
shape: the dead branch's first result is thrown away yet booked as useful.
There is no API to mark it waste — `extra_model_cost` only covers *unlogged*
spend.

### M2 (High): the failed call that triggers a retry stays terminal when logged first
Same root cause, global variant (`/tmp/attack1.py` §C):
```
t.log_model_call(...)          # the draft the judge rejects
t.log_retry("judge rejected draft")
t.log_model_call(...)          # redo → waste. The rejected draft → terminal.
```
The rejected draft ($0.008250 in the repro) is booked as *useful* terminal
spend while its redo is waste. The generator's own retry reasons ("judge
rejected draft", "answer failed confidence check") describe exactly this
causal shape, yet the meter cannot represent it through the Tracker API.
**Cross-path inconsistency:** the OTel importer emits the retry event
*before* the model event for a span carrying both attributes (`otel.py`
loop order), so the identical logical trace attributes the failed call as
waste via OTel but terminal via the Tracker API / JSONL. Two input paths,
two different P&Ls for the same trace.

### M3 (Medium): tool spend on the retry path is invisible to `cost_retry_path`
`tracker.py` `end_attempt`: `retry_path_cost = Σ retry-flagged step costs +
retry_cost`. Tool calls have no retry flag, so a $5.00 tool call logged after
a retry marker lands in `cost_tools`, never in the retry-path lens
(`/tmp/attack1.py` §D: `cost_retry_path=$0.0001` with $5.00 of retry-path tool
spend). The `retry_waste` finding therefore understates retry waste whenever
retry paths use expensive tools — while `extra_model_cost` (unlogged *model*
spend) *is* included. Inconsistent: unlogged model waste counts, logged tool
waste doesn't.

### M4 (Medium): one global retry voids the branch feature's honest-yield guarantee
`log_retry()` with no branch sets `retry_all`, prospectively marking *every*
later step waste — including the productive merge step of a fan-out
(`test_global_retry_still_marks_all_branches` enshrines this). Documented,
but: the OTel and LangSmith importers emit *global* retries whenever the
branch attribute is absent — the common case in real traces. So the
branch-scoping precision exists in the API but is defeated by default in both
real-trace import paths. Additionally, OTel sorts spans by *start* time;
causal order ≠ start order across parallel branches, so a global retry can
smear causally-independent, later-starting work on other branches (M5, Low).

---

## 3. CRASHES / CORRUPTION

### C1 (Critical): `inf` / huge token counts raise inside the live Tracker API
`tracker.py:46` (`_check_nonneg_int` → `int(value)`):
- `log_model_call(..., float("inf"), ...)` → `OverflowError: cannot convert
  float infinity to integer`
- `log_model_call(..., float("nan"), ...)` → `ValueError` with a confusing
  message (not the intended validation error)
- `log_model_call(..., 10**400, ...)` → `OverflowError: int too large to
  convert to float` (in the cost math)
Negative/None/bool/str raise the intended `ValueError`; inf/nan/huge raise
the *wrong* exceptions. The task contract is "the live Tracker API must never
raise inside an agent run" — malformed provider counters currently crash it.

### C2 (High): NaN is *accepted* by 4 of 5 numeric paths and poisons the ledger
`log_tool_call(cost=nan)` (`tracker.py:181`, `nan < 0` is False),
`log_escalation(minutes=nan)` (`:212`), `log_retry(extra_model_cost=nan)`
(`:197`), `log_model_cost_estimate(cost=nan)`, and `end_attempt`
`business_value` (no validation at all) all accept NaN. One NaN tool cost →
`cost_total = nan`, every share = nan (`/tmp/attack2.py`: `(nan, nan, nan)`).
Worse: `policy.export_ledger` then writes **invalid JSON containing a `NaN`
literal** — corrupt artifact handed to the buyer.

### C3 (High): `inf` costs/minutes accepted → `$inf` totals
`log_tool_call(cost=inf)`, `log_escalation(minutes=inf)` accepted; shares
degrade to 0.0/nan; reports print `$inf`.

### C4 (Medium): strict JSONL importer doesn't reject inf/NaN at validation
`jsonl.py` `_check_num` passes `1e400`/`NaN` (valid JSON floats); they blow up
later in `_check_nonneg_int` with `OverflowError` / misleading `ValueError`
instead of the documented line-numbered `ValueError`. The "strict" gate has
a hole for exactly the adversarial numerics it should catch.

### C5 (Medium): LangSmith — one malformed run kills the entire import
`langsmith.py` `_llm_tokens` returns negative floats unclamped (OTel clamps
via `_nonneg`; JSONL rejects per-line), and `:125`
`float(meta["agentpnl_escalation_minutes"])` is unvalidated →
`ValueError: input_tokens must be >= 0` / `minutes must be >= 0` aborts the
*whole* import. Three input paths, three different behaviors for the same
bad datum (OTel clamps, JSONL pinpoints the line, LangSmith dies).

### C6 (Medium): duplicate `end` events fabricate phantom attempts
`common.py` `events_to_tracker` auto-starts an attempt on *any* event,
including a second `end` for an already-closed case → a zero-cost phantom
attempt. Repro: `[start, end, end]` → 2 attempts. Malformed traces inflate
attempt counts silently.

### C7 (Low): `pnl()` KeyError on rehydrated attempts with steps but no `context_growth`
`tracker.py:305` indexes `a["context_growth"]` while its own filter uses
`.get()` — inconsistent. Real old ledgers carry the key, but any minimal or
hand-built ledger with `steps` crashes `pnl()`.

### C8 (Low): `business_value="abc"` passes `end_attempt`, crashes `pnl()`
No validation at log time; `sum()` in `pnl()` → `TypeError`. Fail-late.

### C9 (Hygiene): dead `cli.py:68` `_finish()` contains `raise
AssertionError("unreachable")`
Never called (main uses `_report_and_html`), but it's a landmine with a
doctest-shaped name sitting in the shipped CLI.

### C10 (Low): OpenAI integration `_int_or_zero` doesn't catch `OverflowError`
`integrations/openai.py`: a provider returning `inf` usage →
`int(inf)` → `OverflowError` propagates out of the wrapped `create()` call,
crashing the agent's own run. (The 4300-digit `ValueError` *is* caught;
`inf` is not.)

---

## 4. HONESTY — numbers presented misleadingly

### H1 (High): `low_yield` dollars are an approximation; the exact figure exists
`insights.py:135`: `(1 - yield_ratio) × cost_model`. `yield_ratio` is a
*token* ratio; multiplying it by model *dollars* assumes uniform $/token
across waste and terminal tokens. The tracker already knows exact waste
dollars (Σ retry-flagged step costs + failed attempts' model spend) and
doesn't use them. Demo: cheap-model waste + expensive-model terminal →
finding reports $0.0167 vs true $0.0279 (0.6× understatement); the reverse
pricing mix overstates. A "behavior-changing" dollar figure shouldn't be a
blend when the ledger has the exact number.

### H2 (High): `context_tax` ignores the cache discount, and has no zero-base guard
`tracker.py:235-238` prices the tax at full `in_price`. With heavy caching
the true marginal input cost is ~10% of that; demo (`/tmp/attack3.py` §J):
reported tax $0.0320 vs true discounted marginal $0.0061 (**5.3×
overstatement**). Separately, `base_in = steps[0]["in"]` with no guard: a
zero-token first step — exactly what the OpenAI wrapper logs for streaming
calls with no usage — makes `context_tax` equal **100% of input-token
spend** (demo: tax $0.0020 = entire input spend, "83% of model spend"),
presented as compounding growth.

### H3 (Medium): "top 5%" label is false for n < 20; findings fire on n = 1
`tail_n = max(1, int(n*0.05))`: for n=10 the "top 5%" is the top 1 attempt
(10%), yet `report.py:57,333` prints "top 5% of attempts consumed …".
`insights.tail_concentration` fires on a *single* attempt:
"**The costliest 1 runs consumed 100% of the budget**" [HIGH], advising a
"hard per-attempt envelope at ~p95" where p95 is the one sample.

### H4 (Medium): findings lack the "lenses, not additive" disclaimer
`report_text` warns that Failed-runs and Retry-path overlap; `findings_text`
(the CLI output) and the HTML finding cards present them as separate
dollar-ranked findings with no warning. Summing finding dollars double-counts
by construction.

### H5 (Medium): export drops the event log → retry finding degrades to 'unknown'
`policy.export_ledger` / `common.ledger_from_tracker` exclude `events`, so
*every* rehydrated ledger has empty `top_retry_reasons`. The retry-waste
finding then advises: "**Fix the top retry reason before touching models:
'unknown'.**" Verified on a stress round-trip (direct: 5 reasons; reimported:
0). The artifact a buyer hands over is exactly the one where the #1
operational recommendation becomes a shrug.

### H6 (Low): "N input tokens cached, saving $0.00"
`report_text` prints the cache line whenever `cached_tokens > 0`, but the
estimate path never computes `cache_savings` — caching through
`log_model_cost_estimate` reports tokens cached with $0.00 saved.

### H7 (Low): reopened finding miscounts failed attempts
Detail says "%d **accepted outcomes** were reopened" but counts
`reopened=True` regardless of success — a failed+reopened attempt is reported
as an accepted outcome.

### H8 (Low): NaN-poisoned ledger reports "spend is clean"
`total = nan` is truthy; all share comparisons with nan are False → zero
findings → "No material findings: spend is clean across all five layers."

---

## 5. TEST GAPS — the three most important uncovered behaviors

1. **Insights at degenerate inputs** (no test asserts silence *or* sanity):
   trivial absolute spend must not fire HIGH findings; tool-spend dominance
   (an entire cost layer!) currently fires nothing; 100%-budget-breach
   ledgers fire nothing. The venture kill rule ("at least one finding must
   change behavior") rests on findings being decision-grade — nothing tests
   that.
2. **NaN/inf adversarial numerics**: no test that a NaN tool cost /
   escalation / retry-extra cannot poison `cost_total`, and no test that
   `export_ledger` never emits invalid JSON. The live-API-never-corrupts
   contract is untested.
3. **Export→reimport fidelity**: no test that `top_retry_reasons` (or the
   events behind them) survive `export_ledger` → `tracker_from_ledger`; the
   silent degradation to `'unknown'` in the top action is untested.

Secondary gaps: OTel `averth.success="false"` string parsing; CLI
`--policy-cap 0`; zero-token first-step tax base; duplicate-`end` phantom
attempts; LangSmith single-bad-run import failure; `low_yield` exactness vs
approximation.

---

## 6. INSIGHTS THRESHOLDS — blind spots and hair triggers

**Pathological spend, zero findings:**
- (a) **Tool-spend dominance**: 200 attempts, $2,400 total, **99.996% tool
  spend**, all success, no retries → "No material findings: spend is clean
  across all five layers." There is *no rule at all* for tool-spend
  dominance — layer 2 of the five has no finding.
- (b) **Budget obliteration**: 50/50 attempts at 4.5× `budget_per_success`,
  100% success → zero findings. `budget_breaches` is computed in `pnl()` but
  *no insight rule references it*.
- (c) Uniform-cost ledgers: any pathology invisible to shares/ratios
  (e.g. uniformly terrible unit economics) is silent by construction.

**Trivial spend, HIGH findings:** total spend **$0.00002** (2 attempts, 1
failed) → `failed_spend` [HIGH], `tail_concentration` [HIGH],
`low_yield` [MEDIUM], with titles rendering "**$0.00**". No rule has an
absolute-dollar materiality floor — every threshold is a share/ratio or
`> 0`. A $0.001 ledger can emit the same severity parade as a $1M one.

**Small-n degeneracy:** n=1 → `tail_concentration` [HIGH] ("costliest 1
runs consumed 100%"); n=2 with one failure → three findings.

---

## 7. POLICY SIMULATION

- **P1 (Medium): `--policy-cap 0` silently simulates *no* cap.**
  `policy.py:64`: `if max_cost_per_attempt and …` — 0 is falsy, so the cap
  is ignored (`would_stop=0`); `yield_floor=0` works. `is not None` was the
  intended check, and the CLI explicitly offers `--policy-cap` as a float.
- The saved-vs-collateral split itself is honest and verified.

---

## 8. IMPORTER BUGS (beyond §3)

- **I1 (High): OTel `averth.success="false"` (string) → success=True.**
  `otel.py:125`: `bool(attrs["averth.success"])` — `bool("false")` is
  `True`. OTLP attributes are commonly strings; a span explicitly marked
  failed is imported as a success. Repro in `/tmp/attack3.py` §F.
- **I2 (Low): negative `business_value` rejected by JSONL but accepted by
  Tracker API, OTel, and LangSmith.** Cross-path inconsistency (and negative
  value is arguably legitimate — a run that destroyed value).
- OTel missing-`trace_id` grouping (by span_id, no silent merge) verified
  working as documented.

---

### Repro index
- `/tmp/attack1.py` — double-counting verification (§A), M1 (§B), M2 (§C), M3 (§D)
- `/tmp/attack2.py` — C1–C4, C6–C8, NaN/legacy/JSONL batteries
- `/tmp/attack3.py` — threshold blind spots §A–E, I1 §F, C5 §H–I, H2 §J
- Determinism + JSONL round-trip cost fidelity verified (`seed=7`, 300
  attempts: `cost_total` identical to 4dp; retry reasons lost per H5).

### What I did *not* find
No additive double-counting in any presented bucket; legacy ledgers (real
ones, e.g. `sample-ledger.json`) degrade gracefully through `pnl()`;
`simulate_policy` math is honest about collateral; HTML escaping is thorough;
the 10% cache-discount math itself (`cost + saving = full price`) checks out.
