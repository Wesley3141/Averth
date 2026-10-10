# Claim Audit: prospect-sim test run (2026-10-10)

**Claim under audit:** "fresh venv, pip install git+https://github.com/Wesley3141/Averth.git,
averth trace on 3 fake trace files (langfuse/langsmith/otel), all produced correct
receipts — 3 passed, 0 failed."

**Verdict: the install works and the reported numbers are correct, BUT the script's
assertions are too weak to prove correctness, and the audit found one REAL bug
the script cannot see.**

---

## 1. Is the package on GitHub master actually complete? YES (verified, not assumed)

- `averth/_money.py`, `averth/cli.py`, `averth/importers/langfuse.py`,
  `averth/importers/langsmith.py`, `averth/importers/otel.py` all confirmed present
  on GitHub master via API tree listing (2026-10-10).
- CLI entry point `averth = "averth.cli:main"` present in pyproject.toml.
- The earlier `_money` ModuleNotFoundError is fixed: `_money.py` committed in
  a9a8a6b, pushed, and the fixed install was verified working from a clean venv.
- No LLM calls anywhere in this path: gen_traces.py uses arithmetic
  (`billed_cost()` = tokens × plausible rates × jitter) and fixed seeds.
  Network use is pip/GitHub only.

## 2. Are the reported numbers correct? YES (independently recomputed)

Recomputed expected values directly from the generated JSON files using only the
price table (gpt-5.6: $2.50/$10.00 per M; gpt-5.6-mini: $0.30/$1.20 per M),
without importing averth:

| format     | receipt claimed                          | independent recomputation              | match |
|------------|------------------------------------------|----------------------------------------|-------|
| langfuse   | billed $1.04, measured $0.11, unknown 5  | billed $1.0406, measured $0.1150, unknown 5 | YES |
| langsmith  | measured $0.40, unknown 5                | measured $0.3988, unknown 5            | YES |
| otel       | measured $0.40, unknown "none"           | measured $0.3988, unknown **5**        | **NO** |

The OTel discrepancy is a real product bug (see §4), not a recomputation error:
the generator emits 5 OTel spans with no usage attributes, and the receipt
reports "Unknown: none" for them.

## 3. Would the script catch a subtly wrong receipt? NO — assertions are label checks

`run_prospect_sim.sh` asserts exit code 0 plus the *presence* of section labels.
It asserts no values. Concrete scenarios that PASS the script while the receipt
is wrong:

a) **Billed bucket silently $0.00.** If the Langfuse importer dropped every
   `calculatedTotalCost`, the receipt would print "Vendor-supplied (billed): $0.00"
   and the script's `grep -q "Vendor-supplied (billed)"` still passes. The label
   is unconditional; only the number changes.

b) **Unknown calls silently dropped (langfuse/langsmith).** The script checks
   `grep -qi "unknown"`, but the receipt ALWAYS contains the line "Cost per
   successful outcome: UNKNOWN as an accepted-outcome metric" (no outcome labels
   in the sim). The word "unknown" matches even when `unknown_calls == 0`.
   The assertion is vacuous — it cannot distinguish 5 flagged unknowns from 0.

c) **Unknown calls silently dropped (otel).** The script explicitly skips the
   unknown check for OTel (`if [ "$fmt" != "otel" ]`). This carve-out hides the
   real bug in §4.

d) **Wrong attempt count / wrong totals.** The script prints "Attempts:" and
   "Total cost:" for human eyeballs but asserts nothing. 25 attempts becoming
   82 (one per call) would still print and pass.

e) **Retry attribution missing.** The fake data marks retries; nothing asserts
   retry-path costs appear in the receipt.

f) **Stale/wrong price table.** Measured-bucket values are never checked, so a
   wrong price table passes silently.

What the script DOES prove (fair credit): clean install works, the CLI entry
point resolves, all three importers parse their formats without crashing, and
all receipt sections render. A hard crash (like the original _money bug —
uncaught exception → exit 1, which the script's `$code` check would catch)
fails loudly. It is a smoke test, not a correctness test.

Note: the script did NOT catch the original _money bug — that was found by
manual testing before the script ran. The script would have caught it
(exit-code check is sound), but it never ran against the broken build.

## 4. REAL BUG FOUND: OTel importer drops missing-usage flags

`averth/importers/otel.py` never sets `usage_known` on its model events.
`common.py` defaults it: `usage_known=ev.get("usage_known", True)`.
Result: an OTel span with no usage attributes becomes a 0-token "measured" call
at $0.00 — recorded as free, not flagged as unknown. In the sim, 5 of 82 OTel
calls have no usage data; the receipt reports "Unknown: none".

This directly violates the standing requirement "missing usage must never look
free." LangSmith (`usage_known: has_usage`, line 211) and Langfuse
(`usage_known: has_usage or billed is not None`, line 153) both handle it;
OTel was missed. The sim script's OTel carve-out makes this invisible.

Recommended fix: in `otel.py`, track whether any usage attribute was found and
pass `"usage_known": has_usage` on the model event, mirroring langsmith.py.

## 5. Caching: could the pass be false? NO (for this run)

- `rm -rf /tmp/prospect-sim-venv` → genuinely fresh venv each run.
- pip caches git builds keyed by commit SHA. The broken run installed the
  pre-fix commit; the fixed run installed a new commit (a9a8a6b), forcing a
  fresh clone+build. No stale wheel could have masked the fix.
- Trace files are regenerated deterministically (seed 20261010) after install.
- Caveat for future runs: the script installs unpinned `master` HEAD, so "3 passed"
  is a point-in-time claim. A later broken commit would fail the script (good),
  but the claim does not pin what was tested. Consider logging the installed
  commit SHA in the script output.

## 6. Bottom line for Wesley

- "pip install works and receipts render for all 3 formats" — TRUE, verified.
- "The numbers on the receipts are correct" — TRUE for langfuse/langsmith
  (independently recomputed); FALSE for otel's unknown bucket (bug, §4).
- "3 passed, 0 failed proves correctness" — OVERSTATED. The script proves
  install+parse+render. It cannot detect wrong numbers, dropped unknowns
  (its own unknown check is vacuous), wrong attempt counts, or missing retry
  attribution.
- No LLM testing was used. Correct — the sim is pure arithmetic + fixed seeds.
- Recommended next steps: (1) fix the OTel `usage_known` bug; (2) harden the
  script with value assertions (expected billed/measured/unknown per format,
  attempts == 25); (3) remove the OTel unknown-check carve-out once fixed.
