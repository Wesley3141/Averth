# Hostile review — averth/importers/common.py lines 140-248 (pass 2)

Scope: `LEDGER_ATTEMPT_KEYS` (line 202), `ledger_from_tracker` (217),
`tracker_from_ledger` (237), including the new `price_vintage` restore (247).
Lines 1-140 reviewed by someone else; not touched here.

Method: every claim below was executed, not eyeballed. Concrete trace
hand-computed, both export paths diffed programmatically (AST extraction of
the policy.py literal vs the imported tuple), JSON round trip, legacy-ledger
degradation, and all 150 existing tests run (pass).

## What verified clean

1. **Key-list drift: NONE today.** `LEDGER_ATTEMPT_KEYS` (25 keys) is
   ordered-identical to the inline tuple in `policy.export_ledger`
   (policy.py:33-43). Programmatic check: `policy_keys == common_keys`
   → True, both set-diffs empty.
2. **Both export paths carry identical data.** `ledger_from_tracker(t)` vs
   `policy.export_ledger(t, path)` + `load_ledger`: top-level keys equal
   (`agent`, `unpriced_models`, `price_vintage`, `attempts`); per-attempt
   values element-wise equal. (Only in-memory type difference: see LOW-1.)
3. **price_vintage restore is exact.** After JSON round trip,
   `t2.price_vintage == t.price_vintage` (full dict, version/updated/
   age_days/stale all preserved) and the rehydrated `pnl()` stamps the OLD
   vintage — an old ledger cannot be mistaken for current-price dollars.
4. **Legacy ledgers degrade gracefully (vintage None).**
   `tracker_from_ledger({"agent": ..., "attempts": [...]})` (no
   `price_vintage`, no `unpriced_models`) → `price_vintage is None`;
   `pnl()` does not crash; `report_text` prints
   "Price table: vintage unknown (legacy ledger)"; `write_html` prints
   "Price table vintage unknown (legacy ledger)". Empty-attempts ledger
   also fine (`pnl()` → rate 0.0, both report formats render).
5. **explicit_cost survives the round trip.** Tool steps `[explicit,
   estimated]` → `[True, False]` after `ledger_from_tracker` → JSON →
   `tracker_from_ledger`; `pnl()["tools_default_priced_spend"]` identical
   pre/post (0.002, names `['unknown-thing-xyz']`).
6. **Math hand-verified to the cent, identical after rehydrate.**
   Trace: 1M in + 100k out on anthropic:claude-opus-4-6 ($15/$75 per 1M) →
   $22.50 model; grep $0.05 explicit + $0.002 estimate; 2 min escalation @
   $1.17/min → $2.34; total $24.892. All numeric `pnl()` fields, plus
   `per_success` and `tail`, byte-identical before and after round trip.
7. **Docs-vs-code consistent:** the "Must match the key list in
   policy.export_ledger" comment (202-204) is true; the H2 legacy
   `explicit_cost` default-True rationale ("avoid false warnings") matches
   `ts.get("explicit_cost", True)` in tracker.py:476/479.
8. No network imports, no HTML built, no secrets in this range. `json.load`
   of untrusted ledgers cannot execute code (json only) — but see MEDIUM-2
   on validation.

## Findings

### MEDIUM-1 — common.py:202 + policy.py:33-43 — Key-list match is a comment, not a contract
`LEDGER_ATTEMPT_KEYS` and the inline tuple in `policy.export_ledger` are two
independent literals that "must match" per the comment at common.py:202-204,
but NOTHING enforces it: no test in `tests/` references `LEDGER_ATTEMPT_KEYS`
at all, and no code derives one from the other. A future edit adding a key to
one path (e.g. a new metered field) silently drops it from the other export
path — exactly the silent-data-loss-on-round-trip failure this review was
asked to hunt. Today they match; the guardrail is missing.
Fix: delete one literal (have `export_ledger` use `LEDGER_ATTEMPT_KEYS`, or
vice versa) or add a test asserting ordered equality.

### MEDIUM-2 — common.py:237-248 — tracker_from_ledger validates nothing; malformed vintage crashes the report layer with a confusing error
`tracker_from_ledger` passes `ledger.get("price_vintage")` through blindly.
A hand-edited/corrupt ledger with `"price_vintage": "2026-01-01"` (string,
not dict) rehydrates without complaint; `pnl()` succeeds; then
`report_text` crashes with `TypeError: string indices must be integers, not
'str'` at report.py:21 (`vint["version"]`). Loud, but the wrong layer and an
opaque message — the user sees a string-indices TypeError instead of "ledger
has a malformed price_vintage". For a library whose stated threat model
includes untrusted JSON ledgers (rubric item 6), the rehydrate boundary
should reject malformed vintages (and, arguably, malformed attempt dicts)
with a clear `ValueError` at load time rather than letting a bad shape
detonate two layers later.
Note: `None` (legacy) IS handled correctly — this is strictly about
wrong-type values.

### LOW-1 — common.py:217-234 — `events` are tuples in the live dict, lists after JSON; strict == across export paths is False
`ledger_from_tracker(t)["attempts"] != policy.load_ledger(...)["attempts"]`
on strict equality, solely because `events` entries are tuples in memory
(`tracker.log_*` appends tuples) and lists after a JSON round trip.
Element-wise identical; `pnl()` treats both the same. Inherent to JSON, but
the docstring's "Same schema as policy.export_ledger" is only element-wise
true. Consider normalizing `events` to lists in `ledger_from_tracker` so
`ledger_from_tracker(t) == json.loads(json.dumps(ledger_from_tracker(t)))`.

### LOW-2 — common.py:213-220 — ledger_from_tracker docstring's schema shorthand omits two real top-level keys
Docstring says: `{"agent": name, "attempts": [...]}`. The actual dict also
carries `unpriced_models` and `price_vintage`. The "Same schema as
policy.export_ledger" claim is correct; the shorthand is just incomplete.

### LOW-3 — common.py:241 — shallow copy of attempts aliases nested structures
`tracker.attempts = [dict(a) for a in ledger["attempts"]]` copies each
attempt dict but shares the nested `tool_steps`/`events`/`per_model` objects
with the caller's ledger dict. Mutating the rehydrated tracker mutates the
input ledger. Read-only consumers (cli.py:164, all current callers) are
unaffected; still, `copy.deepcopy` would be the honest contract for a
"rehydrate" function.

## Verdict on this slice
The fixed code does what it claims: no drift today, vintage restore works,
legacy ledgers degrade with loud-but-clear labels, `explicit_cost` survives,
and the dollar math is exact through the round trip. Two MEDIUMs are both
latent rather than active — no test pins the key-list match, and the
rehydrate boundary trusts malformed input until the report layer trips over
it. No CRITICAL, no HIGH in this range.
