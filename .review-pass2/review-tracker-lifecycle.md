# Hostile review, pass 2 — averth/tracker.py lifecycle (lines 1–~301)

Reviewer: hostile-reviewer-tracker-lifecycle. Scope per assignment:
module docstring, BudgetBreach, _check_finite/_check_nonneg/_check_nonneg_int/_percentile,
Tracker.__init__ (human_cost_per_min is-None fix, price_vintage stamping),
start_attempt, _step_is_waste, _record_step, log_model_call,
log_model_cost_estimate, log_tool_call (explicit_cost flag), log_retry, log_escalation.

NOTE: the task brief said "lines 1-240", but log_tool_call/log_retry/log_escalation
actually live at lines 229–300. I reviewed through the end of log_escalation
(~line 301) since the brief names those functions explicitly. end_attempt and
pnl() were NOT reviewed (other reviewers own them).

All numeric claims below were verified by executing scripts against the code
(/tmp/ht_trace.py, /tmp/ht2.py), not by reading alone.

## Verdict

2 HIGH, 4 MEDIUM, 3 LOW. The Phase-1 fixes under review (M3 is-None fix,
price_vintage stamping, explicit_cost flag) all check out. The headline finding
is that the Phase-1 fix validated the twin parameter human_cost_per_min but
MISSED cache_read_discount — a NaN or negative discount silently corrupts dollar
figures, violating the module's own stated numeric contract. Separately, float
token counts are silently truncated instead of rejected.

---

## HIGH-1. cache_read_discount has zero validation — NaN/negative discounts silently corrupt costs (tracker.py:121-123)

Tracker.__init__ (tracker.py:121-123):
```python
self.cache_read_discount = (pricing.CACHE_READ_DISCOUNT
                            if cache_read_discount is None
                            else cache_read_discount)
```
No _check_finite, no range check, nothing. The sibling parameter got the full
treatment (is-None fix + _check_nonneg at tracker.py:114-117), but the twin
parameter was missed. Verified by execution:

- Tracker("x", cache_read_discount=float("nan")) → accepted. A subsequent
  log_model_call with cached tokens computes cost = NaN; end_attempt totals
  come out total_cost = nan. json.dumps emits the non-standard `NaN` literal —
  the EXACT failure mode the module docstring (tracker.py:29-31) says the
  numeric contract exists to prevent: "a NaN anywhere would turn cost_total
  into NaN and the exported ledger into invalid JSON."
- Tracker("x", cache_read_discount=-0.5) → accepted; the same 100k/2k/40k-cached
  call bills $0.150 instead of $0.222 (cached tokens priced negatively).
- Tracker("x", cache_read_discount=2.0) → accepted; bills $0.450 instead of
  $0.222 (cached tokens charged at 2x list price).
- Tracker("x", cache_read_discount="x") → accepted at init, then raises a raw
  TypeError deep inside log_model_call (tracker.py:186-189 float*str), not the
  ValueError the numeric contract promises.

The module docstring states "every numeric input must be finite (NaN/inf
rejected with ValueError)". cache_read_discount IS a numeric input and is not.
This is both missing validation that corrupts output and docs-vs-code. The
NaN case is the CRITICAL-shaped variant (silent NaN poisoning of cost_total and
the exported ledger); I'm rating HIGH overall since a NaN discount requires a
caller config error, but the negative/>1 cases silently misprice real money.

Fix: apply _check_finite plus a [0, 1] range check at init, same posture as
human_cost_per_min.

## HIGH-2. Float token counts silently truncated instead of rejected (tracker.py:70-76)

```python
def _check_nonneg_int(name, value):
    _check_finite(name, value)
    if value < 0: raise ValueError(...)
    if value > _MAX_TOKENS: raise ValueError(...)
    return int(value)
```
int(value) truncates toward zero. Verified: log_model_call("openai","gpt-5-nano",
100.9, 5) is accepted and stores in_tok = 100 — the 0.9 token is silently
dropped. A metering library whose entire brand is "loud, never silent"
should not silently floor malformed input; a float token count is always a
caller bug, and truncation masks it while billing slightly wrong numbers.
Fix: reject non-integral floats (value != int(value) → ValueError). Same issue
affects log_model_cost_estimate's token args, which share the helper.

Rating note: dollar impact is sub-cent per call, but it is silent acceptance of
invalid input in a metering library — HIGH by the rubric's "wrong behavior on
edge cases" standard, one notch above a nit because it masks caller bugs.

---

## MEDIUM-1. budget_per_success and on_breach unvalidated in __init__ (tracker.py:108-109)

```python
self.budget_per_success = budget_per_success
self.on_breach = on_breach
```
- A negative budget_per_success is accepted silently. Whatever end_attempt does
  with it, a negative cap is never a meaningful configuration; at minimum a
  negative budget should raise at construction, not detonate later.
- A non-callable on_breach (e.g. a string) is accepted and only fails with a
  TypeError at breach time — deep in a run, far from the config error.
- NaN/inf budgets are accepted, again contradicting the module docstring's
  "every numeric input must be finite".

Contrast with the careful _check_nonneg on human_cost_per_min three lines
below. Fix: _check_nonneg("budget_per_success", ...) when not None; callable()
check on on_breach.

## MEDIUM-2. _step_is_waste(self, branch) ignores its parameter (tracker.py:149-152)

```python
def _step_is_waste(self, branch):
    # Branch retries are retroactive (applied to past steps at retry
    # time), so only the global marker affects future steps.
    return self._cur["retry_all"]
```
Both callers (_record_step at tracker.py:154, log_tool_call at tracker.py:246)
pass branch=, and the signature implies the branch matters. The comment
explains the design, but a vestigial parameter that every call site passes is
a copy-paste hazard: a future reader will "use" branch here and double-taint
redo work. Drop the parameter (or rename to _branch to signal intentional
non-use).

## MEDIUM-3. _percentile accepts out-of-range p and returns garbage (tracker.py:86-100)

Docstring claims "Linear-interpolation percentile (numpy 'linear' method)".
numpy's percentile raises ValueError for q outside [0, 100]. This one doesn't:
_percentile([1,2,3], -0.5) → rank=-1.0, lo=int(-1.0)=-1 → indexes
sorted_values[-1] and returns 3.0 (verified). p=1.5 similarly overshoots the
top. Silent garbage on invalid input, plus docs-vs-code (numpy parity claim is
false for out-of-range p). Guard: raise ValueError unless 0 <= p <= 1.

## MEDIUM-4. Cross-reviewer note: events store raw user-controlled strings

log_tool_call (name), log_retry (reason), log_escalation (reason), and model
names are appended to cur["events"] verbatim. If report.py interpolates these
into HTML without escaping, that's an injection vector — but escaping is
report.py's job, which I don't own. Flagging for the report reviewer; NOT
scored against tracker.

---

## LOW-1. human_cost_per_min=False now raises (behavior note)

Old `or` code mapped False → default silently; the is-None fix correctly
rejects bool via _check_finite. Loud > silent, this is the intended behavior —
noted only because someone upgrading might trip on it.

## LOW-2. cached>input clamp is silent but documented

log_model_call (tracker.py:182-183) and log_model_cost_estimate (tracker.py:218-219)
clamp cached to in_tok with an inline comment ("malformed trace data; never
price phantom tokens"). Silent correction, but it's a conscious, documented
design choice with the right direction (never bill phantom tokens). Acceptable
as-is; ideally it would emit the clamp into events for traceability.

## LOW-3. Scope/line-number drift

The brief said lines 1-240 but the named functions extend to ~line 301;
reviewed through log_escalation (tracker.py:292-300) per intent. Also noted:
tracker.py:541 exports cache_read_discount into the pnl/ledger dict — the
unvalidated value from HIGH-1 propagates there too (other reviewer's code, but
the fix belongs at init).

---

## What PASSED (verified hostile, no finding)

- **log_model_call cost math, hand-traced**: anthropic:claude-sonnet-4-5
  (pin=3.00, pout=15.00), in=100000, out=2000, cached=40000, discount=0.10 →
  cost = 60000/1e6*3.00 + 40000/1e6*3.00*0.10 + 2000/1e6*15.00 = 0.222
  exactly (code output 0.222, math.isclose to 1e-12). cache_savings = 0.108.
  Identity cost + saving == full cached-token price holds exactly.
- **M3 is-None fix**: human_cost_per_min=0 → stored 0.0, _human_rate_explicit=True
  (verified). None → 1.17 default, flag False. -1.0, NaN, True all raise ValueError.
- **explicit_cost flag**: omitted cost → False with TOOL_PRICES default (0.005 for
  web_search); explicit cost=0.042 → True; explicit cost=0.0 → True with cost
  honored (the is-not-None parallel of the M3 fix — correct).
- **price_vintage stamping**: tracker.price_vintage = {'version': 1, 'updated':
  '2026-10-02', 'age_days': 1, 'stale': False, 'stale_after_days': 90}. Stamped at
  init, not looked up lazily — correct design.
- **Branch-retry semantics match the docstring**: log_retry(branch="b1")
  retroactively marked only b1's past model+tool steps as waste; b2 untouched;
  work logged on b1 AFTER the retry starts fresh (not pre-tainted); global retry
  taints only subsequent steps. Step-flag sequences verified: [True, False, False]
  for branch case, [False, True] for global case.
- **Edge rejections, all loud**: negative/NaN/inf/bool tokens → ValueError;
  >1e12 tokens → ValueError; negative/NaN tool cost, retry cost, minutes →
  ValueError; unknown model → KeyError with a helpful message ("add it to
  MODEL_PRICES or use log_model_cost_estimate"); double start_attempt →
  RuntimeError; logging without start_attempt → RuntimeError via _req().
- **Zero-token calls**: cost 0.0, no division issues. cached>input clamp works
  in both model-call paths and uses the clamped value for cached_tokens.
- **_percentile in-range**: p50([1,2,3,4])=2.5, p0/p1 exact, empty→0.0,
  single→value. Correct numpy-'linear' behavior for valid p.
- **Security**: tracker.py imports only math and .pricing — zero network calls.
  No secrets, no unsafe deserialization, no HTML generation in this file.

## Suggested fix priority

1. HIGH-1: validate cache_read_discount at __init__ (finite + [0,1]). One-line-ish,
   closes both the silent-mispricing and NaN-poisoning paths.
2. HIGH-2: reject non-integral floats in _check_nonneg_int.
3. MEDIUM-1/3: budget_per_success/on_breach validation; _percentile p range guard.
