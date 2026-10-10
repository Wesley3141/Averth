# Hostile review: policy.py export_ledger() / load_ledger() (lines 17–52)
Scope: `export_ledger`, `load_ledger` ONLY (incl. the new `price_vintage` top-level key).
`simulate_policy`/`policy_text` are another reviewer's problem. Reviewed against
`~/workspace/averth/averth/policy.py` lines 17–52, `averth/tracker.py` (attempt
construction), `averth/pricing.py`, `averth/importers/common.py`.

Method: hand-read the code, then ran a verification script that built a real
Tracker, exported it, enumerated every exported key, round-tripped `price_vintage`,
injected NaN into an attempt, fed malformed and wrong-shape JSON to `load_ledger`,
and exported an empty tracker. All claims below were observed, not inferred.

## Verdict summary
- CRITICAL: 0
- HIGH: 2
- MEDIUM: 3
- LOW: 3

---

## HIGH 1 — `export_ledger` silently emits invalid JSON when a NaN/inf slips into an attempt (averth/policy.py:44–46)
`json.dump(ledger, f, indent=2)` uses Python's default `allow_nan=True`. I injected
`total_cost = float("nan")` into a tracker attempt and exported: **no exception**,
and the file contains the literal text `NaN`, which is invalid JSON per RFC 8259 —
Go's `encoding/json`, JavaScript's `JSON.parse`, Java Jackson, and serde_json all
reject it. A strict `json.loads(..., parse_constant=...)` re-parse of the emitted
file FAILS. Python's own `json.load` accepts the NaN back silently, so the
existing round-trip test (`tests/test_policy.py:40`) cannot catch this — the
corruption is invisible to the Python-only test suite while the file itself is
poison for any non-Python consumer (e.g. a customer's billing pipeline or a
vendor's Go/JS tooling). The whole point of this file is to be handed to a third
party ("we run the simulation here" — policy.py:1–14).
NaN cannot enter through today's public API (every log_* path runs `_check_finite`
via `_check_nonneg*`, and `pricing.MODEL_PRICES` currently holds only finite
literals — verified), but the export is the last line of defense and there are
realistic paths: direct mutation of `tracker.attempts` by an importer/subclass, a
future pricing-table entry with inf, or float overflow in derived math. The fix is
one keyword — `json.dump(..., allow_nan=False)` — which converts this into a loud
`ValueError` at export instead of a corrupt file in a vendor's inbox. Per the
rubric §5, NaN must never become silent corruption; here it literally does.

## HIGH 2 — docstring guarantees "no customer data" but the export ships arbitrary caller strings verbatim (averth/policy.py:18–22)
The docstring asserts: "Never contains prompts, completions, tool payloads, or
customer data — the Tracker only ever records cost/token/timing metadata."
Demonstrably false by construction. The exported `events` list (whitelisted at
policy.py:41) carries free-text caller input:
- `("retry", reason, extra_model_cost, branch)` — `log_retry(reason=...)` is an
  unconstrained string (tracker.py:254).
- `("escalation", reason, minutes)` — `log_escalation(minutes, reason="...")`
  (tracker.py:285).
- `("tool", name, c)` — tool `name` is an arbitrary caller string (tracker.py:246).
- `case_id` is an arbitrary caller string, exported verbatim.
My verification run exported `reason="bad draft v2"`, escalation reason
`"manual review of draft"`, and tool name `"search_api"` straight into the ledger
file. A production integration passing tool error text (which routinely contains
customer identifiers, ticket IDs, or user content) into `log_retry(reason=...)`
leaks it into a file whose stated threat model is "send this to the vendor."
The codebase itself treats retry reasons as user-controlled: the audit notes
`report.py` html-escapes retry reasons (AUDIT-2026-10-02.md §10). So one module
sanitizes these strings as untrusted input while another exports them under an
absolute "never contains customer data" guarantee. Rubric §7: docstring says X,
code does Y → HIGH. Fix options: weaken the guarantee to "structured metadata
plus caller-supplied labels/reasons (sanitize before sharing)", or strip/scrub
free-text fields at export.

---

## MEDIUM 1 — `load_ledger` accepts any JSON shape with no schema validation (averth/policy.py:50–52)
Malformed JSON fails loudly (`json.JSONDecodeError`) — good. But valid JSON of the
wrong shape passes silently: I loaded `[1,2,3]` and got a list back with no
complaint; the failure only surfaces later as `TypeError: list indices must be
integers or slices, not str` inside `simulate_policy`, and a hand-crafted dict
missing `"attempts"` dies with a bare `KeyError`. A one-line schema check
("is this dict shaped like an Averth ledger?") would fail fast with an actionable
message instead of leaking an internal TypeError to the caller.

## MEDIUM 2 — two divergent export implementations, no single source of truth (averth/policy.py:23–42 vs averth/importers/common.py:202–235)
`policy.export_ledger` hardcodes its own inline per-attempt key tuple while
`importers/common.py` defines `LEDGER_ATTEMPT_KEYS` and `ledger_from_tracker`
with the same keys plus the claim "Same schema as policy.export_ledger."
The key lists match *today* (verified by diffing both against the tracker attempt
dict), but nothing enforces that: adding a field to one silently desyncs the
other, and the two docstrings will then contradict each other. `export_ledger`
should consume `LEDGER_ATTEMPT_KEYS` (or vice versa). Classic parallel-reviewers
drift hazard.

## MEDIUM 3 — `events` tuples round-trip as JSON lists; `json.load` also accepts NaN literals (averth/policy.py:41,50–52)
In-memory `events` are tuples (`("retry", reason, cost, branch)`); after
export→load they are lists. Nothing in-tree depends on tuple semantics today
(`tracker_from_ledger` rehydrates and re-exports stably), but any consumer
diffing a reimported ledger against the original sees inequality, and a
ledger hand-crafted with `NaN` literals loads without complaint (Python's
`json.load` accepts them by default). A strict loader (`parse_constant` raising)
plus a documented "events are lists after load" note would close both.

---

## LOW 1 — confusing key name: `model` holds dollars, not the model name (averth/policy.py:25)
The whitelisted key `"model"` is the model *spend in dollars* (tracker.py:158:
`cur["model"] += cost`); the actual model identity lives in `per_model` keys
(`"provider:model"`) and in `events`. Anyone reading the ledger cold will
misread `"model": 15.0` as a model name. Rename or document in the schema comment.

## LOW 2 — docstring says "per-attempt cost metadata only" but top level carries non-per-attempt keys (averth/policy.py:18–28)
`agent`, `unpriced_models`, and `price_vintage` are top-level and not per-attempt.
All are legitimate metadata; the sentence just overstates. One-word fix.

## LOW 3 — `price_vintage.age_days` is frozen at export time (averth/policy.py:31)
Verified: `price_vintage` survives export→load byte-identical
(`{'version': 1, 'updated': '2026-10-02', 'age_days': 1, 'stale': False,
'stale_after_days': 90}` == `tracker.price_vintage`). The frozen `age_days` is
correct as a vintage marker, but a consumer reading a months-old ledger could
misread `age_days: 1` as "the table is 1 day old now." The `updated` date is
present, so this is interpretable — a comment noting the snapshot semantics
would remove the ambiguity.

---

## Verified PASS (no finding)
- **Exported key enumeration (all 25 attempt keys + 4 top-level):** top-level
  `{agent, attempts, price_vintage, unpriced_models}`; attempts carry
  `ai_cost, business_value, cache_savings, cached_tokens, case_id,
  context_growth, context_tax, events, human_cost, human_min, model, per_model,
  reopened, retries, retry_cost, retry_path_cost, retry_tool_cost, success,
  terminal_model_cost, tool_latency_ms, tool_steps, tools, total_cost,
  total_tokens, waste_tokens`. Every one is cost/token/timing metadata or an
  identifier/reason string — no prompt/completion/payload/message/content keys
  (substring scan of the raw file: clean). Internal keys correctly excluded:
  `steps`, `retry_all`. Tracker attempt dict has exactly these keys plus the
  two excluded internals — the whitelist is complete, nothing cost-related is
  dropped.
- **`price_vintage` round trip:** identical before/after; `unpriced_models`
  sorted list survives; empty tracker exports `[]` attempts and loads fine.
- **Malformed JSON:** `load_ledger` raises `json.JSONDecodeError` with a clear
  message — loud, as required.
- **NaN via public API:** blocked at every `log_*` entry point by `_check_finite`
  (tracker.py:53); pricing table holds no non-finite entries (checked
  programmatically). The gap is only at the export boundary (HIGH 1).
- **Security:** no network imports, no eval/exec, `json.load` is safe
  deserialization; no secrets in code. The only exfil-relevant vector is the
  free-text fields covered by HIGH 2.

## Security note
No web contact was made during this review; no injected directives encountered.
