# Review pass 2 — QUICKSTART.md + TERMS.md (docs reviewer)
Date: 2026-10-02. Reviewer posture: hostile. Rubric item 7 (docs-vs-code)
applied ruthlessly; every behavioral claim below was verified by running the
code, not by reading the docs.

## Method
- Ran the exact QUICKSTART step-2/3 snippets verbatim (Tracker + export_ledger).
- Ran `python -m averth.cli trace <file> --format jsonl` against a real
  validation trace (`validation-traces/live-langgraph-agent/events.jsonl`).
- Verified every API signature in the snippets against source.
- Checked the GitHub install URL returns HTTP 200.
- Read the post-C1-fix hook path (`tracker.py:358-372`) and the
  `BudgetBreach` docstring (`tracker.py:42-50`) for the TERMS "never
  enforces" tension analysis.

## Verdict
QUICKSTART is runnable — every command and snippet works as printed — but
it misdescribes three material behaviors and its terminal step is a dead
end. TERMS is factually sound and internally honest, but its "never
enforces anything" posture is verbally undermined by the codebase's own
words (and by one stale README claim the C1 fix silently invalidated).

---

## HIGH

### H1. QUICKSTART arms `budget_per_success` but never documents the raise — an unhandled `BudgetBreach` propagates out of the customer's production attempt loop
- QUICKSTART.md:24 shows `t = Tracker("support-agent", budget_per_success=6.00)`.
  Nowhere in the 81-line doc is `on_breach` mentioned, nor that
  `end_attempt()` can raise. The doc's framing is "Read-only. The meter runs
  inside your environment and records cost/token/timing metadata only."
  (QUICKSTART.md:3-4).
- Code: `tracker.py:364-372` — if `total_cost > budget_per_success`, it
  builds a `BudgetBreach` and, with no `on_breach` callback, **raises it out
  of `end_attempt()`** into the caller's attempt loop.
- Verified live:
  ```
  BudgetBreach raised out of end_attempt():
      BudgetBreach('support-agent: case cost $7.62 exceeded budget $6.00')
  ```
- The doc's own sample attempt costs **$5.2835** against the $6.00 budget —
  88% of the envelope. A user who copies the example and adds one more
  escalation or model call trips an exception they were never warned about.
- Mitigating facts (do not remove the finding, but scope it): the attempt
  IS recorded before the raise (`len(t.attempts) == 1` after the exception),
  so no metering data is lost; and the raise is a notification, not spend
  prevention — it cannot stop anything, since it fires post-hoc at
  `end_attempt`.
- Why HIGH: a metering library that throws into a production agent loop is a
  pilot-killing surprise, and "Read-only" framing makes it worse. The doc
  must say: breaches raise `BudgetBreach` unless you pass
  `on_breach=...`, and show the two-line handler.

### H2. "On LangChain, the same data is captured" is false — the handler captures a strict subset
- QUICKSTART.md:45: "On LangChain, the same data is captured with three
  lines, no manual calls".
- Code (`averth/integrations/langchain.py`):
  - `on_tool_end` (line ~192): `self.tracker.log_tool_call(name)` — **no
    cost**. Tool spend via the LangChain path is always $0, vs the manual
    path's explicit `t.log_tool_call("zendesk_lookup", 0.004)`.
  - `_chain_done` (line ~141): `self.tracker.end_attempt(success=success)` —
    **no `business_value`**, so value is always 0 and "net value" is
    meaningless for LangChain-instrumented agents.
  - No path records human review minutes, retry extra costs, or reopened
    flags from callbacks.
- Consequence: the "fully loaded cost per accepted outcome" the pilot
  promises (QUICKSTART.md:76) is computed on systematically incomplete
  data for LangChain users — $0 tool spend, $0 business value — and the doc
  tells them it is "the same data." The five-layers report will show
  "External tool spend: $0.00" as if measured. That is a HIGH-grade
  misleading label: it corrupts the trust story, not just a sentence.

### H3. QUICKSTART's terminal step is uncompletable: "Email the JSON to the pilot address" names no address
- QUICKSTART.md:74: "Email the JSON to the pilot address. We return within
  48 hours:".
- No address appears anywhere in QUICKSTART.md, and a grep of README.md for
  a pilot/diagnostic email address finds none (README mentions "pilot" only
  at lines 65 and 175, neither with an address).
- The entire 81-line doc funnels to this CTA; a new user who follows every
  step hits a dead end at the one action that matters. HIGH because the doc
  fails its primary conversion job, not because of a typo.
- Separately unverifiable (not graded): "We return within 48 hours" is a
  service SLA no code can substantiate.

---

## MEDIUM

### M1. "No customer data" in the ledger is conditional on user discipline — QUICKSTART states it as a guarantee
- QUICKSTART.md:4-6 and :68-70: "the sanitized ledger contains no prompts,
  no completions, no tool payloads, and no customer data" / "No prompts, no
  completions, no payloads, no customer data."
- Verified export keys contain no prompt/completion/payload fields (true —
  no Tracker API accepts them). BUT the exported `events` array includes
  retry and escalation reasons **verbatim, as user-controlled free text**:
  ```json
  ["retry", "confidence check failed", 0.0, ""],
  ["escalation", "low confidence", 4.5]
  ```
  plus `case_id` verbatim. A customer who writes
  `t.log_retry(f"user {email} disputed charge")` ships that string in the
  ledger, and QUICKSTART told them the ledger "contains no customer data."
- TERMS.md handles this honestly ("you are responsible for keeping
  restricted data out of your submissions"), which makes QUICKSTART's
  absolute phrasing the outlier. Fix: "contains no prompts/completions/
  payloads by construction; keep identifiers out of free-text reasons and
  case IDs."

### M2. tracker.py's own module docstring says "enforce budgets" — verbally contradicting TERMS' "never enforces anything"
- `tracker.py:1`: "Core tracker: meter everything an agent spends, tag
  outcomes, enforce budgets."
- TERMS.md:10-12: "It performs retrospective analysis only. It does not
  enforce policies, modify any system, or take any action on your behalf."
- The codebase's own `BudgetBreach` docstring (`tracker.py:42-50`) and
  `policy.py` module docstring both state the opposite of line 1: "live
  enforcement is Phase-1, built only after a buyer confirms who owns that
  authority... The Phase-0 pilot is read-only." So the module docstring is
  the outlier — but it is the first line of the core file, and a customer
  reading it alongside TERMS reasonably asks which statement is true.
- This is the sharpest edge of the assigned TERMS question (see analysis
  below). One-word fix: "flag budget breaches."

### M3. README.md:63 says the breach hook "is Phase-1 (built only after a buyer confirms...)" — the C1 fix built it, and it fires today
- README.md:63-64: "The `budget_per_success` + `on_breach` hook is Phase-1
  (built only after a buyer confirms who owns that authority and will pay
  for it)."
- Post-C1-fix code fires the hook on every over-budget attempt, including
  failed runaways (`tracker.py:358-372`), raising by default. The README
  sentence was true before the fix landed and is now stale.
- Not strictly in my two-file assignment, but it is load-bearing for the
  TERMS tension: TERMS says "never enforces," README says the hook doesn't
  exist yet, the code fires it. Three documents, three stories. README must
  be updated to describe the hook as a Phase-0 notification (post-hoc
  signal, not enforcement), matching the `BudgetBreach` docstring.

---

## LOW

- L1. QUICKSTART.md:45 "three lines" — the LangChain snippet is 3
  statements plus the import (4 physical lines with the blank). Not worth
  changing; noting for completeness.
- L2. `averth trace run-2026-09.json --format jsonl` (QUICKSTART.md:59)
  names a `.json` file for `--format jsonl`. It works (format is explicit,
  not inferred), but the example filename invites confusion. Rename to
  `run-2026-09.jsonl`.
- L3. Install-time claims ("Install (30 seconds)", "3 minutes", "30
  seconds") are unverifiable marketing; harmless.
- L4. `pip install "averth[langchain] @ git+https://github.com/Wesley3141/Averth.git"`
  is valid PEP 508, the `langchain`/`openai` extras exist in
  `pyproject.toml:15-16`, and the GitHub URL returns HTTP 200. Install
  path checks out (network install itself not executed).

---

## What checked out clean (verified, not just read)
- Every snippet signature: `log_model_call(provider, model, in, out)`,
  `log_tool_call(name, cost)`, `log_retry(reason)`,
  `log_escalation(minutes, reason)`,
  `end_attempt(success, business_value, reopened)`,
  `Tracker(name, budget_per_success)`, `P.export_ledger(t, path)` — all
  match QUICKSTART.md:24-40,68-70 exactly. The step-2/3 script runs
  cleanly end to end.
- `averth trace <file> --format jsonl --html report.html`: `--format`
  accepts exactly `otel|langsmith|jsonl` (cli.py:41), `--html` exists
  (cli.py:43); ran against a real validation trace — report prints, and the
  C3 fix is visible in output ("at $70.20/hr loaded — ASSUMPTION, not
  measured").
- `AverthCallbackHandler(tracker)` constructor and
  `config={"callbacks": [handler]}` attachment match
  `integrations/langchain.py:100-128`.
- "Makes no network calls": consistent with the audit's grep (zero network
  imports in the package); nothing in the QUICKSTART path touches the
  network.
- Failed-attempt breach path (the C1 fix): a failed over-budget attempt now
  fires the hook with a "(failed attempt)" suffix — verified the message
  format.

## TERMS.md claim-by-claim verification
1. "Averth MCP is a free, read-only analysis service." — Internally
   consistent: QUICKSTART closes with "read-only, free"; no pricing
   anywhere in the repo. (The MCP server itself is deployed separately and
   has no code in this repo, so server-side behavior is unverifiable here;
   the audit's live probe is the only server evidence.)
2. "You submit a sanitized batch of agent run records (cost and timing
   metadata only) and it returns computed economics: fully-loaded cost per
   accepted outcome, expensive-tail share, and offline policy replays." —
   Matches `tracker.pnl()` + `policy.simulate_policy` outputs. ✓
3. "It performs retrospective analysis only. It does not enforce policies,
   modify any system, or take any action on your behalf." (TERMS.md:10-12)
   — see tension analysis below. No direct contradiction found in code.
4. "Submit only data you have the right to share... you are responsible for
   keeping restricted data out of your submissions." — Honest and
   consistent with the code (cf. M1: the guarantee is on the submitter, not
   the format). ✓
5. "Effective October 1, 2026. Operator: Averth (Wesley Deklich)."
   "Questions: wesleyd3141@gmail.com." — Both check out. ✓
6. "We do not guarantee accuracy... Nothing returned constitutes financial
   advice." — Consistent with the audit's C2/C3 (frozen prices, assumed
   labor rate); the disclaimer is doing real work. ✓

## TERMS tension analysis: does the hook's raise path constitute enforcement?
**No — on the evidence, the raise path is not enforcement, and it does not
contradict TERMS as written.** Four facts:
1. It fires in `end_attempt()`, after all spend for the attempt has already
   occurred. It cannot prevent, stop, cap, or reduce any spend.
2. It takes no action in the customer's systems: with no `on_breach`
   callback it raises `BudgetBreach` into the customer's own call stack —
   control flow, not system modification. The attempt is recorded before the
   raise (verified: `len(t.attempts) == 1` post-exception).
3. The codebase classifies it the same way: the `BudgetBreach` docstring
   (`tracker.py:42-50`) says "live enforcement is Phase-1... The Phase-0
   pilot is read-only," and `policy.py`'s module docstring says "Read-only
   means read-only. There is no live enforcement in the pilot."
4. TERMS governs the *MCP service* ("Averth MCP... It performs retrospective
   analysis only"), which is deployed separately; the library hook lives in
   the customer's process.
**But the tension is real at the language level**, and a hostile reader
will find it: `tracker.py:1` says "enforce budgets" (M2); README.md:63
says the hook is unbuilt Phase-1 while it fires today (M3); QUICKSTART
arms `budget_per_success` with no explanation of the raise (H1). A VP
Finance prospect reading "never enforces anything" next to a library whose
docstring says "enforce budgets" will ask exactly the question this task
poses. Fix M2/M3/H1 and the tension dissolves: the story becomes "the
meter *notifies* on budget breach; enforcement is Phase-1."

## Recommended fixes (in order)
1. H3: put the actual pilot email address in QUICKSTART.md:74 (or say who
   to ask for it). The doc's CTA is currently a dead end.
2. H1: document the breach behavior in QUICKSTART step 2 — one line: "if an
   attempt exceeds `budget_per_success`, `end_attempt` raises
   `BudgetBreach` unless you pass `on_breach=fn`." Show the callback.
3. H2: correct "the same data" to the honest subset (no business value, no
   tool costs, no human minutes via the LangChain handler) or add manual
   follow-up calls for the missing fields.
4. M1: soften the "no customer data" guarantee; warn against PII in
   retry/escalation reasons and case IDs.
5. M2: `tracker.py:1` — "enforce budgets" → "flag budget breaches."
6. M3: update README.md:63-64 to describe the hook as a built Phase-0
   notification, not unbuilt Phase-1.
7. L2: rename the trace example to `run-2026-09.jsonl`.

## Injection note
Per the rubric's security note: no injected developer-style messages were
encountered during this review (no web fetches were needed; all
verification was local code execution). Nothing opened or computed from
untrusted sources.
