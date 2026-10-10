# Review pass 2 — VALIDATION.md docs review (hostile)

Reviewer: docs-validation subagent. Date: 2026-10-02.
Scope: `~/workspace/averth/VALIDATION.md` ONLY (248 lines), rubric item 7
(docs-vs-code) applied ruthlessly. Context: `AUDIT-2026-10-02.md`; Phase 1
fixes for C1-C3/H1-H4/M1-M3 are present as uncommitted working-tree changes
(reviewed via `git diff`).

Method: every re-runnable numeric claim was re-run against current code —
`demo.py`, `python3 -m averth.cli trace` on all four validation-trace inputs,
ledger/pnl recomputation via the importers, `stress.generate` determinism and
timing, plus grep-verification of every named regression test, finding count
in `HOSTILE_REVIEW.md`, and the code facts behind the appendix claims
(`insights.py`, `report.py`, `pricing.py`, `tracker.py`,
`importers/common.py`, `integrations/langchain.py`).

## Verdict

No CRITICAL findings (no live wrong-dollar computation; the meter math
reproduces). But the report's headline numbers are stale in exactly the way
that matters: three of the five trace "economic insights" quote
yield/waste percentages the current code no longer produces, the LangGraph
showcase dollar figure is built on the meter's own arbitrary tool-price
defaults applied to free APIs, the trajectory dollar figures rest on
estimated token counts the report never discloses, and the review-coverage
arithmetic (20 findings; 14/4/2) does not match `HOSTILE_REVIEW.md`.

Severity counts: CRITICAL 0 · HIGH 7 · MEDIUM 5 · LOW 2.

---

## HIGH findings

### H1 — Three trace-insight yield/waste percentages no longer reproduce; invalidated by the hardening pass's "failed attempts = 100% waste" rule

The main section is dated 2026-09-30 (first pass) but is presented as current
validation evidence (scorecard, "46 of 46"). The hardening appendix changed
yield semantics — "Failed attempts are now 100% waste tokens... the demo
month now reports 6% yield instead of 95%" — and explicitly notes "this moves
yield from a token-use ratio to a token-success ratio." The main-section
numbers were never updated, and all three now contradict current output:

1. `VALIDATION.md:14` — swe-smith: "74% of all tokens burned on the retry
   path." Re-ran `python3 -m averth.cli trace
   validation-traces/swe-smith-trajectories/events.jsonl --format jsonl`:
   current output is "Yield ratio: 11% of tokens on the terminal path (89%
   burned on retries and failed runs)". The 74% figure (26% yield, from the
   pre-hardening `FINDINGS.md`) is stale; the code now reports 89% waste.
   Dollar claims on the same line ($13.06 of $24.79, 53%) still reproduce
   exactly — only the token-share claim is wrong.
2. `VALIDATION.md:28` — OTel trace A: "put 42% of all tokens on the retry
   path." Recomputed via `load_otel` + `tracker_from_ledger`: waste_tokens =
   11,290 of 11,290 total tokens = 100% waste (the attempt failed, ERROR
   span, no `averth.success` override). The 42% (4,770 of 11,290, per
   `validation-traces/otel-live/FINDINGS.md`) was the pre-hardening
   retry-path count. Current code reports 100%.
3. `VALIDATION.md:35` — OTel trace B: "yield reads 56% but overstates waste
   under concurrency because the productive merge step is counted as
   retry-path waste." Current: the attempt failed, so yield is 0% and every
   token (13,890/13,890) is waste. The 56% figure and the "merge step counted
   as waste" mechanism description are both superseded — and the mechanism
   is doubly dead because the appendix's #11 branch-scoping fix changed how
   branch waste is attributed anyway.

The appendix acknowledges the semantic shift in the abstract but leaves the
three concrete numbers standing as if current. A prospect re-running the
traces gets different percentages than the report quotes.

### H2 — LangGraph "$0.174 of $0.178 (97.6%) external tool spend" is 100% default-estimated, on free APIs

`VALIDATION.md:42`: "$0.174 of $0.178 total (97.6%) is external tool spend,
the layer invisible on provider invoices... For agentic workloads with
per-call-priced tools, the lever is tool-call count and failure rate, not
model selection."

Reality, verified in code and artifacts:
- `averth/integrations/langchain.py:174-180` (`on_tool_end`): calls
  `self.tracker.log_tool_call(name)` with **no cost argument**.
- `averth/pricing.py:90-91`: `tool_call_cost(name)` returns
  `TOOL_PRICES.get(name, TOOL_PRICES["default"])` — the built-in defaults.
- `validation-traces/live-langgraph-agent/events.jsonl`: 63 tool events —
  `web_search` x16 @ $0.005 (the built-in `TOOL_PRICES["web_search"]`
  default), `github_lookup` x16 and `flaky_fetch` x31 @ $0.002 (the
  unknown-tool `"default"` fallback). 16×0.005 + 47×0.002 = $0.174 exactly.
- The tools are DuckDuckGo instant-answer, GitHub repo search, and httpbin —
  all free public APIs. No actual tool spend occurred; no per-call-priced
  tool was involved.

So the report's showcase example of "the layer invisible on provider
invoices" is itself built on the meter's own arbitrary per-deployment
defaults — the exact H2 failure mode the Phase 1 audit flagged ("a wrong
default does the most damage... invisible on provider invoices") and that
Phase 1 now forces reports to warn about ("WARNING: $X of tool spend uses
built-in per-call ESTIMATES"). `VALIDATION.md` never discloses that the
$0.174 is default-estimated, and the "per-call-priced tools" framing implies
measured vendor metering. The arithmetic (97.6%, $0.1783 total, 1,794
tokens, $0.0043 model) all reproduces — the dishonesty is presentation, not
math. (The trace dir's own `live_agent.py` header is careful: "Tool calls,
latency, retries, parallelism, and failures are 100% real" — notably not
claiming costs are real. The VALIDATION.md insight drops that care.)

### H3 — "a real recorded ConnectionRefusedError" is not in the artifact

`VALIDATION.md:24`: "13 real OpenTelemetry SDK spans (real timestamps, real
HTTP calls, a real recorded ConnectionRefusedError with ERROR status and
retry)".

- The file `validation-traces/otel-live/trace-a-sequential-retry.json`
  contains **zero span `events` keys** (verified by parse and by grep). The
  generator (`gen_otel_live.py:136-140`) did raise a real
  `ConnectionRefusedError` (localhost:9 refused) and called
  `span.record_exception(exc)`, but the exception event was lost in the
  JSON serialization — the shipped artifact records only the ERROR status
  and the `agentpnl.retry: "refund_api connection refused"` attribute
  string. The literal `ConnectionRefusedError` type name appears nowhere in
  the file.
- The dir's own `FINDINGS.md` repeats the overstatement ("real recorded
  exceptions").

A reviewer opening the trace file to verify the "real recorded" evidence
finds a retry-reason string, not a recorded exception. The underlying event
was real at generation time; "recorded" misdescribes the artifact.

### H4 — Appendix #11's branch-retry description contradicts the round-2 M1 fix documented in the same file

`VALIDATION.md:102-104` (hardening appendix): "a retry with
`branch="research"` marks only later "research" steps as waste, and the
merge step stays terminal."

But the round-2 section of the same file documents M1 — "Branch retry
retroactive (M1): `log_retry(branch="b")` now marks that branch's
*existing* steps (model and tool) as waste, not just future ones. Work
logged on the branch after the retry is the redo and starts fresh" — and
Phase 1's H1 fix just rewrote the `importers/common.py` EVENT-schema
docstring to match ("the branch's existing (past) steps are retroactively
marked... an earlier version of this docstring wrongly said 'past and
future'"). The hardening appendix still carries the pre-round-2
"only later steps" description. A customer implementing `branch=` from the
hardening section will mispredict their waste numbers in the opposite
direction from the actual (and now documented) behavior.

### H5 — Appendix claims the trace-B case "now attributes correctly: only the dead branch's tokens count as waste" — false for trace B itself

`VALIDATION.md:106-108`: "The trace-B case from the first pass (productive
merge step counted as waste) now attributes correctly: only the dead
branch's tokens count as waste."

Trace B's attempt **failed** (two dead payment-branch retries, no
`averth.success` override). Under the hardening pass's own failed-attempt
rule — documented three paragraphs earlier in the same appendix ("Failed
attempts are now 100% waste tokens... a failed attempt has no terminal path
by definition") — all 13,890 of trace B's tokens are waste regardless of
branch scoping. Verified: `waste_tokens=13890, total=13890`. The appendix
simultaneously claims (a) the merge step is no longer waste thanks to
branch scoping and (b) everything is waste because the attempt failed. Both
cannot hold for this trace; (b) is what the code does.

### H6 — Trajectory dollar figures rest on estimated token counts; the report never says so

- swe-smith `SOURCES.md:38-40`: "Token counts are mechanical estimates
  (characters/4 of accumulated [message text])... Dollar figures are
  estimates; the retry share, [structure] is real."
- mini-swe-agent `SOURCES.md:19-21`: "TOKEN ESTIMATION (not recorded data):
  the traces record no per-call token usage, so input_tokens =
  chars(all preceding message text)//4... Mechanical estimates only."

`VALIDATION.md` presents $13.06/$24.79 (swe-smith), $17.49 vs $4.55 recorded
(3.84x), and $3.92 metered / $0.92 recorded (mini-swe-agent) with no mention
that the metered side is built on chars//4 estimates. Worse, issue 9 frames
the 3.84x gap as "the largest known accuracy gap" attributable to prompt
caching ("Implied prompt-cache hit rates of 0.48-0.90 reproduce the recorded
costs exactly") — a theory that cannot be separated from token-estimation
error, since the metered numerator is itself estimated. The disclosure
exists one directory down; a validation report whose job is establishing
dollar trust must carry it itself. (The mini-swe-agent dollar claims were
all re-verified: subset recorded total $4.55, $0.51/resolved-instance,
3.84x, $3.92 metered, $0.92 recorded, 3 failed = 25% = 36% of spend —
arithmetic is exact; the omission is the token basis.)

### H7 — "20 findings" miscount; disposition arithmetic doesn't cover the review

`VALIDATION.md:180-181`: "A second hostile review (20 findings,
`HOSTILE_REVIEW.md`)... Disposition: 14 fixed in code, 4 documented as
known limitations, 2 were non-issues on re-examination."

- `HOSTILE_REVIEW.md` has **22** `###`-headed findings (M1–M4, C1–C10,
  H1–H8), plus P1/I1/I2 discussed in sections 7–8 and M5 referenced inline
  (line 95). "20 findings" matches none of these counts.
- 14 + 4 + 2 = 20, so the disposition as stated leaves headed findings
  unaccounted for; the "Fixed" bullet list itself contains 15 bullets, not
  14. The per-item dispositions are individually checkable and mostly
  accurate — the headline arithmetic misrepresents review coverage.

---

## MEDIUM findings

### M1 — "98.5%" human-share is wrong rounding
`VALIDATION.md:28`: "the 3-minute human escalation ($3.51) is 98.5% of the
fully-loaded $3.57 attempt." Recomputed: human $3.5100 / total $3.5658 =
98.43% → 98.4%, not 98.5%. (Repeated in
`validation-traces/otel-live/FINDINGS.md`.) Minor, but a validation report
should not misstate its own recomputable ratios.

### M2 — "1.39x" model-spend multiple is off
`VALIDATION.md:28`: "made model spend 1.39x a clean run ($0.047 vs $0.034)."
0.047/0.034 = 1.382 → 1.38x. Same class of small numeric misstatement as M1.

### M3 — Stress scorecard specifics are not evidenced in the repo
`VALIDATION.md:168-170`: "Stress scenarios run: seeds 1/5/7/9/42/123/124 at
N=50..20,000; determinism verified (same seed -> identical P&L to the
cent); 20k attempts meter in ~1.2s with no performance cliff."
- `tests/test_stress.py` exercises seeds {1, 7, 42, 123, 124} at most 2,000
  attempts; no seed 5 or 9 and no 20,000-attempt run exist anywhere in
  `tests/` or `averth/stress.py`. The claimed seed set and range describe
  manual runs with no artifact.
- Re-ran `stress.generate(seed=7, attempts=20000)`: 2.04s on this machine
  vs claimed "~1.2s" (machine-dependent, but the figure is presented as a
  measured fact).
- Substance verified: determinism holds to the cent (re-ran seed 7/400:
  identical), JSONL round-trip is byte-identical on all pnl buckets
  (`test_jsonl_roundtrip_identical`), and there is no performance cliff —
  but the specific seeds/range/time claims overstate what is evidenced.

### M4 — "4 concurrent branches via ThreadPoolExecutor" has no artifact evidence
`VALIDATION.md` (trace B section) / `FINDINGS.md:25`. True of the generator
(`gen_otel_live.py:225`: `ThreadPoolExecutor(max_workers=4)`), but the
shipped `trace-b-parallel-fanout.json` records no thread attributes and all
tool steps carry `branch=None` (the importer emits global retries by
default — documented M4 limitation). The "dead payment branch burned 44%
($0.024 of $0.055)" attribution is reconstructed from span names/timing,
not from branch metadata in the trace. The 44% arithmetic itself checks out
($0.004 dead-branch tools + ~$0.020 grok-4 waste ≈ $0.024 of $0.0546).

### M5 — "zero hand-fixing" framing vs converter tuning
`VALIDATION.md:5,12,19,26,33,40,68`. The swe-smith converter's retry
heuristic was tuned after first results (substring-"error" matching fired
208 retry events → tightened to observation/failure markers, 36 events),
disclosed in `validation-traces/swe-smith-trajectories/FINDINGS.md` as
"converter accuracy work, not a library change." That is analysis-pipeline
tuning, not trace-content editing, so the literal claim holds — but
"zero hand-fixing" reads stronger than "we iterated the converter until the
retry classification looked right." Caveat, not a falsehood.

---

## LOW findings

### L1 — Report label "$6.00/success" vs doc "$6.00/attempt cap"
`VALIDATION.md` (appendix): "a $6.00/attempt cap with 50% yield floor would
have 'saved' $297.18 while destroying $897.79" — verified exactly in current
`demo.py` output ($297.18 saved / $897.79 collateral). But the demo report
header still prints "Budget: $6.00/success, breaches: 96". Post-C1 the hook
is per-attempt (fires on failed runaways too); the doc's "$6.00/attempt" is
the accurate description and the report label lags it. Doc-side is correct;
noting for the report owner.

### L2 — "1 days old" price-table age is a clock artifact
Reports print "Price table: v2 (verified 2026-10-02, 1 days old)" because
the VM clock is 2026-10-03 UTC while the task date is 2026-10-02 CDT. Not a
doc error; noting so nobody "fixes" the age math.

---

## Phase 1 invalidation check (C1-C3/H1-H4/M1-M3) — result: no direct invalidation

Reviewed the uncommitted Phase 1 diff (`README.md`, `averth/cli.py`,
`averth/importers/common.py`, `averth/insights.py`, `averth/policy.py`,
`averth/pricing.py`, `averth/report.py`, `averth/tracker.py`,
`sample-output.txt`) against every `VALIDATION.md` claim:

- **C1 (breach hook now fires on failed attempts):** `VALIDATION.md` states
  no numeric breach count and no hook-semantics claim, so nothing is
  invalidated. (The doc's "budget_breach finding" reference remains true;
  `insights.py:136-143` still emits it.)
- **C2 (price-table versioning/staleness):** no price *values* changed for
  any model used in the validation traces (the three Anthropic models are
  still ($3.00, $15.00)/1M; `CACHE_READ_DISCOUNT` still 0.10). One
  concurrent pass-2 correction (`claude-haiku-4-5` 0.80/4.00 → 1.00/5.00,
  bumping `PRICE_TABLE_VERSION` 1→2) moves trace-A total by <$0.001 —
  immaterial to every quoted figure. All dollar claims re-verified
  unchanged.
- **C3 (labor-rate assumption labeling):** default `HUMAN_COST_PER_MIN`
  unchanged ($1.17); only labeling + explicit-0 handling changed. The $3.51
  / 3-minute escalation claim is unaffected.
- **H1 (branch-retry docstring → past-only):** no `VALIDATION.md` dollar
  figure changes, but the fix *exposes* H4 — the hardening appendix's #11
  prose now contradicts both the fixed docstring and the round-2 M1 note.
- **H2 (tool-estimate flagging):** no figure changes, but the new
  `tools_default_priced_spend` machinery makes H2's non-disclosure sharper:
  the current code would flag the LangGraph $0.174 as estimated; the report
  predates the flag and never mentions it.
- **H3/M1/M2/M3:** no `VALIDATION.md` claim touches these behaviors.

## Verified-accurate claims (spot-checked, all reproduce)

- Demo: "token dashboard $0.20 vs fully loaded $0.82 (4.1x)" ✓ (current
  `demo.py`: Token dashboard $0.20, Fully loaded $0.82, "real cost is 4.1x");
  "top 5% consumed 61% of budget" ✓; "demo month now reports 6% yield" ✓
  (6%); policy replay "$297.18 saved / $897.79 collateral" ✓ exact;
  "p50 of $1..$20: $10.00 -> $10.50" ✓ (linear interpolation = 10.5).
- Trace counts: 16 + 12 + 2 + 16 = 46 trace units ✓ (28 raw trajectory
  files + 2 OTel files + 16 live runs); exit 0 on all four CLI invocations
  ✓; all 9 named regression tests for issues 1–6 exist ✓.
- mini-swe-agent: $3.92 metered / $0.92 recorded (django__django-11265,
  api_calls=63, unresolved) ✓; 3 failed = 25% = $6.36 = 36% of $17.49 ✓;
  recorded subset $4.55, $0.51/resolved ✓; 3.84x ✓.
- LangGraph: 16 attempts / 12 successes / 21 retries / $0.1783 ✓
  (`pnl.json`); ledger total == pnl total to the cent ✓ ("three ways"
  agreement on the headline bucket); 1,794 tokens ✓; $0.0043 model ✓;
  21/63 = one-third failed ✓; $0.045 = 26% of tool spend ✓ (issue 6).
- Appendix machinery: `budget_breach` + `tool_dominance` findings exist ✓;
  tail rule n>=20 ✓; $1.00 materiality floor ✓; reopened counts accepted
  outcomes ✓; cache line requires savings > $0 ✓; low_yield dollars exact
  (`cost_model - cost_model_terminal`) ✓; token dashboard =
  `cost_model/successes` ✓ (`demo.py:79`); retry-tool lens $63.39 on seed-7
  workload ✓ exact; strict JSONL rejects `cached_input_tokens >
  input_tokens` (test) ✓; legacy-ledger backward compat (test) ✓;
  "3-line AverthCallbackHandler" integration ✓ (`live_agent.py:274`);
  real tiktoken measurements ✓ (`stub_model.py`); real OTel SDK in
  `gen_otel_live.py` ✓; no `Lock` in LangChain handler ✓ (issue 15 still
  accurate); `deepseek-v3.2` correctly absent from `MODEL_PRICES` and
  flagged via fallback ✓ (trace-A CLI warning).

## Marketing-vs-fact notes

The doc is an internal validation report, not customer copy, and most
"economic insight" lines are labeled as interpretation. Concrete
marketing-risk items: H2 (the $0.174 insight would mislead a prospect about
measured tool spend), H3 ("real recorded" evidence that isn't in the
artifact), H6 (accuracy-gap framing that omits token estimation). The
outreach proof line derived from this work ("most expensive 5% of runs
consumed 61% of total spend") was verified against current `demo.py` and is
accurate. Tone issues ("the honest version", "most vendors would hide") are
audit voice, not factual claims — left alone.

## Note on the price-table version bump during review

Between my first and second read of `averth/pricing.py`, `PRICE_TABLE_VERSION`
went 1 → 2 with `claude-haiku-4-5` corrected 0.80/4.00 → 1.00/5.00
("corrected per review pass 2"). A concurrent reviewer is actively editing
the file; the version-2 table is what all re-runs above used. Impact on
`VALIDATION.md` figures: immaterial (<$0.001 on trace A).

No prompt-injection content encountered (no web use in this review).
