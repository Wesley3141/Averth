# Hostile review: averth/importers/jsonl.py (review pass 2)

Reviewer assignment: the JSONL trace importer (149 lines). Read against
.review-pass2/RUBRIC.md. Context: AUDIT-2026-10-02.md Phase 1 fixes are in
(common.py carries the C2/M1/M2/H1/H5 fixes); this review covers the FIXED
code, jsonl.py only.

Method: hand-built JSONL fixture with independently computed expected
values (run and compared to 1e-12); 26-case malformed-input battery;
step-level branch/retry flag inspection via events_to_tracker;
report.py escaping audit for every user-controlled string jsonl accepts.

## Verdict

The importer is strict and correct on the happy path and on almost every
abuse path: math verifies exactly, branch/retry mapping matches the EVENT
schema, and every malformed line I could construct fails loud with a line
number — except one. Two HIGH findings, both docs-vs-code contract breaks
in jsonl.py itself. No CRITICAL findings.

Severity counts: CRITICAL 0 / HIGH 2 / MEDIUM 3 / LOW 4.

---

## HIGH

### H1. Docstring contract broken: unhashable "type" raises bare TypeError, no line number

`averth/importers/jsonl.py:108`

The module docstring promises: "Any violation raises ValueError naming
the offending line number." But `_validate` does `if etype not in _SPECS`
on the raw parsed value. A JSON line like:

    {"type": ["model"], "case_id": "x"}

raises `TypeError: unhashable type: 'list'` — not ValueError, and with no
line number. Reproduced:

    type-list: TypeError (no line number!): unhashable type: 'list'

Any caller written against the documented contract (catch ValueError,
report line N) misses this entirely. The fix is one line: check
`isinstance(etype, str)` before the membership test, or wrap in the same
ValueError format. Also note the same class of hole one layer down:
an implausibly large token count (e.g. 10^20) passes jsonl validation and
then dies inside tracker._check_nonneg_int with `ValueError: input_tokens
implausibly large: ...` — loud, but with no line number, again violating
the line-number contract (see M3).

### H2. Docstring says branch applies to "(model, retry events)" — tool events accept it too

`averth/importers/jsonl.py:26` (docstring) vs `averth/importers/jsonl.py:70` (_SPECS)

The field-rules docstring reads: `"branch" (model, retry events) scopes
retry-path waste marking to one parallel branch`. But `_SPECS` allows
`branch` on **tool** events as well:

    "tool": ({"case_id": str, "name": str},
             {"cost": None, "latency_ms": None, "branch": str}),

and common.py's EVENT schema documents why: "branch tags which parallel
branch made the call so retry-path tool spend is attributed to the
discarded path." This is a docstring-says-X-code-does-Y mismatch (rubric
rule 7). It has a real behavioral consequence for docstring readers: a
user who tags model calls with branch but leaves branch off tool calls
(because the docstring told them branch is a model/retry thing) gets
retry-path tool spend silently attributed to the terminal path. Verified
in the fixture run: the `web_search` tool step (no branch tag) survived a
`retry branch="research"` unmarked, so `retry_tool_cost` was 0.0 while
`retry_path_cost` carried the model step — correct per schema, but only if
the user knows tool events take branch.

---

## MEDIUM

### M1. Float token counts are allowed by the docstring but silently truncated by the tracker

`averth/importers/jsonl.py:21` (docstring: numeric fields "must be
int/float (not bool)") + `averth/tracker.py:70-77` (`_check_nonneg_int`
does `return int(value)`)

jsonl explicitly permits floats for token fields. The tracker then
silently truncates: `input_tokens: 100.9, output_tokens: 50.5` is recorded
as `total_tokens=150` (verified: source said 151.4). Dollar impact is
negligible (fractions of a token at $/1M rates), but the ledger's token
accounting no longer equals the source file's — silent corruption of an
input the importer's own contract blesses. Either reject non-integral
tokens at the jsonl boundary (loud, matches "tokens are counts") or round
explicitly and document it. Truncation via int() is the worst option
because it is invisible.

### M2. Duplicate JSON keys in one line silently last-wins

`averth/importers/jsonl.py:137` (`json.loads(line)`)

`{"type": "model", "model": "a", "model": "b", ...}` parses with no
warning and records model "b". json.loads keeps the last duplicate key.
A strict importer that rejects unknown keys (line 120-124) but silently
accepts duplicated keys has an odd hole: a hand-edited or
machine-concatenated trace can change which model name (and therefore
which price) applies without any error. Low probability, but the fix is
cheap (`object_pairs_hook` rejecting duplicates). Noted as MEDIUM because
it can silently change the priced model.

### M3. Tracker's "implausibly large" rejection bypasses the line-number contract

`averth/importers/jsonl.py` (no _MAX_TOKENS check) + `averth/tracker.py:74`

A token count of 10^20 passes jsonl validation cleanly, then raises
`ValueError: input_tokens implausibly large: 99999999999999999999` from
inside the tracker — loud, but with no line number, in a file where every
other violation names its line. Either mirror the bound in `_check_num`
(with line number) or accept the diagnostic gap. Fail-loud, so MEDIUM.

---

## LOW

- **L1.** `import math` inside `_check_num` (line 49) on every numeric
  field of every line. Harmless (import cache) but slop; move to module
  top.
- **L2.** Empty-string `case_id` (`""`) is accepted as valid. Groups and
  exports work, but it is a degenerate key; a warning or rejection would
  be friendlier.
- **L3.** `open(path)` (line 132) with no explicit encoding; a BOM or
  non-UTF-8 file raises a raw UnicodeDecodeError/JSON error rather than
  the documented ValueError-with-line-number.
- **L4.** `_validate` returns the raw `json.loads` dict, not a copy;
  callers mutating the event list could corrupt the tracker's steps.
  Internal-only today, but the "sanitized" framing in `load_jsonl`'s
  docstring overpromises slightly.

---

## Verified OK (not findings)

- **Token/cost math, hand-verified.** Fixture: gpt-5-nano (0.05/0.40 per
  1M), 1200 in / 300 out / 800 cached + branch retry + redo call +
  explicit-cost tool + 4.5 min escalation. All 19 assertions matched to
  1e-12: model=0.000169, tools=0.005, human=5.265, total=5.270169,
  retry_path_cost=0.000144 (exactly call 1), terminal=0.000025,
  waste_tokens=1500/1650, cache_savings=0.000036, latency 320ms, etc.
- **Branch/retry mapping matches the EVENT schema exactly.**
  `retry branch="research"` retro-marked only the branch's past step
  (1200/300 → retry=True); the redo call logged after the retry starts
  fresh (retry=False); the untagged tool step correctly not discarded;
  `("retry", "validation failed", 0.0, "research")` preserved in events.
- **26-case malformed battery:** 25/26 fail loud with `line N: ...`
  (bad JSON, non-object lines, missing/unknown type, missing case_id,
  int/str/bool/null/NaN/±inf/negative tokens, cached>input, success as
  1/"yes", reopened as 0, unknown keys, success on a model event,
  negative cost, null minutes). The 26th (dup `type` key resolving to a
  valid "end" without success) also raised loudly. Empty file and
  blank-line-only files → zero attempts, no crash.
- **No unescaped user strings reach the HTML report.** jsonl accepts
  attacker-controlled strings in `name`, `reason`, `branch`, `model`,
  `provider`, `case_id`. All are passed through raw into tracker events —
  and report.py escapes every one of them at render time (13
  `_html.escape` calls covering agent, case_id, retry reasons, per-model
  keys, estimated-tool names, vintage strings, finding titles/details).
  Spot-checked with `<script>alert(1)</script>` tool names and
  `<img onerror>` reasons: raw in the ledger JSON (correct — JSON needs
  no escaping), escaped in HTML output. The plain-text report needs no
  escaping. Architecture (escape at the render boundary) is sound; jsonl
  needs no sanitization of its own.
- **Fallback pricing honest:** unpriced model → (1.00, 3.00)/1M fallback,
  cost exactly 4.0000 for 1M/1M, flagged in `unpriced_models`;
  provider-guess miss → `unknown:mystery-model-7b`, same fallback,
  flagged. Price vintage stamped.
- **Auto-end / duplicate-end (C6):** case with no end → one attempt,
  success=False; duplicate end and stray end (no open attempt) ignored —
  no phantom zero-cost attempts; events after an end start a new attempt.
- **Line numbers count physical lines** (blank lines included) — the
  reported line matches the file.

## Note on injection

Per the rubric's security note: no web access was used in this review
(fixture and battery were local files; pricing/report/tracker read from
the repo). No injected directives were encountered.
