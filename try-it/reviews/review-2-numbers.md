# Review 2 — Correctness of the numbers (adversarial, numbers angle)

**Verdict: FAIL**

Every published *figure* recomputes exactly from the raw inputs — no
arithmetic is wrong. The FAIL is driven by two things that must be fixed
before this ships: (1) the headline $0.91 is labeled "Priced (vendor
prices on **recorded tokens**)" in the shareable report, but the tokens
are characters/4 estimates, not recorded usage — the label is false on
its face, contradicts the same report's own banner, and violates the
meter's own Wave-5 provenance rule; (2) the reproduction script that is
supposed to certify these numbers cannot detect a billed-bucket
regression at all (its billed check is vacuous) and never checks the
provenance split it certifies except by proxy. A wrong provenance label
on the flagship dollar figure, plus a certifier that cannot catch it, is
exactly the failure mode this review exists to stop.

Scope of this review: independent recomputation only. I did not edit any
source file. Scratch work (recompute script, live-run stdout/HTML) is in
`try-it/reviews/scratch-2/` (`recompute.py`, `traj-stdout.txt`,
`jsonl-stdout.txt`, `traj-try.html`, `jsonl-try.html`).

## What verified clean (independent recomputation, no averth imports)

My throwaway script (`scratch-2/recompute.py`) recomputes everything
from the raw trajectory, the fixture JSONL, the price-table literals,
and the V0 ledger, with plain arithmetic. Results:

| Published claim | My recomputation | Result |
|---|---|---|
| Converter reproduces fixture events | Rebuilt all 71 events from `django-15930.traj.json` (35 assistant messages, 35 `` ```bash `` fences, 1 end event): **0 event mismatches**, and the canonical serialization is **byte-for-byte identical** to `trace-events-django-15930.jsonl` | PASS |
| Fixture is the published file | `curl` of the S3 URL in the README; `cmp` vs fixture: **identical** | PASS |
| 72 messages / 35 API calls | traj has 72 messages (1 system + 36 user + 35 assistant); 35 model events; leaderboard `model_stats.api_calls` = 35; `instance_cost` = 0.32052914999999993 | PASS |
| Model cost $0.91 | 279,017 input tokens × $3/1M + 5,077 output tokens × $15/1M = **$0.913206 → $0.91** | PASS |
| Tool cost $0.07 | 35 bash events × $0.002 default (`TOOL_PRICES` has no `bash` key, so the $0.002 default applies) = **$0.070000 → $0.07** | PASS |
| Fully loaded $0.98 | 0.913206 + 0.07 = **$0.983206 → $0.98**; rounded parts sum consistently (0.91 + 0.07 + 0.00 = 0.98) | PASS |
| Recorded $0.3205 | `instance_cost` 0.32052914999999993 rounds to **0.3205** at 4 dp | PASS |
| Ratio 3.07x | 0.983206 / 0.3205 = **3.0677 → 3.07x**; with the unrounded recorded cost, 3.0674 → also 3.07x (not sensitive to the rounding) | PASS |
| Context growth 9.9x | Last input 14,465 / first input 1,460 = **9.9075 → 9.9x** | PASS |
| Context tax $0.68 | Σ(in − 1,460)/1e6 × $3 over steps 2..35 = **$0.683751 → $0.68** (74.9% of model spend → "75%", correct rounding) | PASS |
| Retries 0 | No retry events in the fixture; `averth try` prints `Retries: 0` | PASS |
| V0 2 / 0 / 2, 50.0%, 2 runs | Counted from the judgments list, not the coverage block: VERIFIED 2, EXTERNAL-UNVERIFIABLE 2, FAILED 0, criteria_total 4, unknown 2/4 = **0.5000 → 50.0%**, `len(runs)` = 2, order VERIFIED, VERIFIED, EXTERNAL-UNVERIFIABLE, EXTERNAL-UNVERIFIABLE. Checks digest `sha256:f25cd3…` **matches** a fresh sha256 of `fixtures/case-study-1-checks.json`. The two runs' stderr corroborate "Ran 1 test … OK" and "Ran 89 tests … OK (skipped=1)" | PASS |
| `averth try` on the traj | Exit 0; stdout shows Fully loaded $0.98, Model/API (terminal) $0.91, Tool calls $0.07, Priced $0.91 / Billed $0.00 / Estimated $0.07, 9.9x, $0.68, 0 retries, `Recorded cost: $0.3205; … $0.98 ESTIMATED (3.07x)`, `V0 verdicts: VERIFIED 2, EXTERNAL-UNVERIFIABLE 2; unknown rate 50.0%` | PASS |
| `averth try` on the JSONL | Exit 0; stdout **identical** to the traj run (modulo agent name/out path) | PASS |
| Generated HTML | Contains $0.98 (×14), $0.91, $0.07, $0.00, 3.07x, 9.9x, $0.68, $0.3205, 50.0%, V0 section, recorded-cost section, chars/4 source note, cost-basis banner, estimated-tool-spend warning; **no `http`** (self-contained) | PASS |
| `tests/test_try_it.py` | 22 passed | PASS |

Prices used were taken from `averth/pricing.py` as instructed
(`anthropic:claude-sonnet-4-20250514: (3.00, 15.00)`; `TOOL_PRICES`
default 0.002). I did **not** re-verify those list prices against
Anthropic's live pricing page (no live-browser access in this role);
that is a stated boundary, not a verified fact. I also did not re-run
the reproduce script end to end (Django install + V0 execution); the
V0 numbers above are verified statically against the stored ledger and
its digest, and the reproduce script's meter-section logic was audited
against real `averth try` stdout (see Defects 2, 3, 5, 6).

## Defect 1 (major) — The $0.91 is labeled "Priced (vendor prices on recorded tokens)" but the tokens are estimates, not recorded

- **Files/lines:** `averth/report.py:180-182` (stdout) and
  `averth/report.py:580-581` (HTML data-quality block). Root cause in
  `averth/importers/miniswe.py:18-24` (docstring) and the model-event
  dict it builds: the events deliberately do **not** set
  `tokens_estimated`, so the $0.9132 lands in the Priced bucket.
- **Expected:** the Priced bucket holds "vendor prices on recorded
  tokens" (the label's own words, and the meter's own Wave-5 rule in
  `averth/tracker.py`: "vendor prices applied to ESTIMATED tokens are
  not measured spend — they move from 'measured' to 'estimated'").
  Under that rule the honest split for this trace is **$0.00 priced /
  $0.98 estimated**, because every token count here is characters/4
  from trajectory text.
- **Actual:** the report prints `Priced (vendor prices on recorded
  tokens; legacy traces without a provenance flag still land here):
  $0.91`. The miniswe docstring admits the reason: the flag is omitted
  so "the published numbers reproduce exactly" — i.e. the
  classification was chosen to preserve the published $0.91/$0.07
  split, not because it is correct.
- **Why this is not saved by the existing disclosures:** the same HTML
  carries a banner saying the dollars apply "vendor list prices to
  trace-supplied token counts that Averth does not verify as recorded
  usage" — which directly contradicts the "recorded tokens" label two
  sections above it. The case-study page (`averth-site/case-study-1.html:227`)
  has to add a footnote redefining "Priced" ("labels the $0.91
  'Priced' because it applies vendor list prices") — evidence the label
  as written is confusing enough to need rescue. And the rescue lives
  on the website, not in the self-contained report a recipient
  actually receives.
- **Exact fix (keeps every published number intact):** relabel the
  bucket to match what it actually is. In `averth/report.py:180-182`
  and `averth/report.py:580-581`, change the parenthetical to
  `vendor list prices applied to trace-supplied token counts` (drop
  "on recorded tokens" and the "legacy traces" clause, which is not a
  disclosure a reader can act on). Do **not** instead set
  `tokens_estimated=True` in miniswe.py unless the published split is
  being republished as $0.00/$0.98 — that is the alternative honest
  fix, but it changes the published numbers and needs a deliberate
  decision, not a silent edit. Either way, the label and the banner
  must agree in the shipped report.

## Defect 2 (major) — The reproduce script's billed check is vacuous: it can never fail

- **File/line:** `try-it/reproduce-case-study.py:281`:
  `check("meter billed", 0.0, PUBLISHED["meter_billed"])`.
- **Expected:** the check parses the meter's billed figure from its
  output and compares it to $0.00.
- **Actual:** the "actual" argument is the hardcoded literal `0.0`.
  If the meter ever reported billed $0.50 (e.g. a Langfuse-style
  vendor cost leaking into this path, or a bucket regression), this
  check would still print PASS. The billed leg of the published
  $0.91/$0.07/$0.00 split is therefore uncertified by the script
  whose job is to certify the split.
- **Exact fix:** parse the real line, e.g.
  `check("meter billed", money(r"Vendor-supplied \(billed\)"),
  PUBLISHED["meter_billed"])` — the line exists in stdout
  (`Vendor-supplied (billed): $0.00`, verified in my run) — or parse
  the HTML data-quality block. I verified the true value is $0.00, so
  this fix changes no published number; it makes the check real.

## Defect 3 (major) — The reproduce script certifies the provenance split only by proxy, never directly

- **File/lines:** `try-it/reproduce-case-study.py:277-280`.
- **Expected:** "meter priced" and "meter estimated" should read the
  Data quality lines (`Priced … $0.91`, `Estimated … $0.07`), which
  are the actual published provenance claims.
- **Actual:** "meter priced" parses the per-success `Model/API
  (terminal)` line and "meter estimated" parses the per-success `Tool
  calls` line. Those are cost-component lines, not provenance buckets.
  A bucket-math regression (e.g. `estimated_token_spend`
  misclassified, or the `pnl()` overwrite at `averth/tracker.py:788`,
  `estimated_model = unpriced_spend`, misfiring on a mixed ledger)
  would leave both proxy lines unchanged and the script would still
  pass. Combined with Defect 2, the entire $0.91/$0.07/$0.00
  provenance split — the most honesty-sensitive claim in the report —
  is effectively uncertified.
- **Exact fix:** add checks parsing the three Data quality lines from
  stdout (`Priced (vendor prices…): $…`, `Vendor-supplied (billed):
  $…`, `Estimated (fallback…): $…`) and the same three values from
  the generated HTML's data-quality block, compared to
  `PUBLISHED["meter_priced"]` / `["meter_estimated"]` /
  `["meter_billed"]` at the cent. (I verified all six values by hand
  against the real outputs; they match.)

## Defect 4 (minor) — README says the report shows "0 FAILED"; it never does

- **Files/lines:** `try-it/README.md:75` claims the report shows
  "(2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE, 50.0% unknown
  rate)". `averth/try_report.py:146` (HTML rows) and `:213-218`
  (stdout line) render only verdict names present in the ledger's
  `coverage.counts` dict — and the ledger's counts dict contains only
  `VERIFIED` and `EXTERNAL-UNVERIFIABLE`, no `FAILED: 0`. Verified in
  my generated HTML and stdout: the string `FAILED` occurs **0**
  times; the reader never sees an explicit "0 FAILED".
- **Exact fix:** in `try_report.py`, drop the `if name in counts`
  filter and render all five verdicts with `counts.get(name, 0)`
  (both the HTML rows at :146 and the stdout `ordered` join at
  :213-218). Then the README claim becomes true. Alternatively correct
  the README — but rendering the zeros is the better fix: a verdict
  table that omits a zero row invites the reader to wonder whether
  FAILED was checked at all.

## Defect 5 (minor) — The ratio regex is an unanchored first-match; it works today only by luck of ordering

- **File/line:** `try-it/reproduce-case-study.py:292`:
  `re.search(r"\(([0-9.]+)x\)", out)`.
- **Expected:** the check reads the ratio from the recorded-cost
  summary line.
- **Actual:** it takes the *first* `(Nx)` anywhere in the whole
  stdout. I verified against real stdout that the only match today is
  `3.07` (the summary line), so the check currently passes for the
  right reason — but any future `(Nx)` earlier in the output (e.g. a
  new findings line) would silently hijack the check and could pass
  on, or fail on, the wrong number.
- **Exact fix:** anchor it to the line it claims to check, e.g.
  `re.search(r"ESTIMATED \(([0-9.]+)x\)", out)`.

## Defect 6 (minor) — Coverage gaps in the reproduce script's published-number checks

- **(a) "72 messages" is a published page claim with no check.**
  The script checks `record["api_calls"] == 35` from the leaderboard
  record, but nothing checks the trajectory's 72 messages. I verified
  72 by hand (1 system + 36 user + 35 assistant). Add
  `check_int("trajectory messages", len(traj["messages"]), 72)`.
- **(b) "35 API calls" is checked against the leaderboard record,
  not against the meter.** If the converter dropped a message, the
  leaderboard check still passes; the meter total would catch it only
  if the dropped call moved the cent-rounded total. Add a check that
  the meter's own model-event count is 35 (e.g. count model lines in
  the fixture JSONL, or a `--json`-style count from the run).
- **(c) Unknown-rate rounding hides error:** `check("V0 unknown
  rate", …, places=1)` rounds to one decimal, so a true rate of 0.54
  would pass against published 0.5. The published rate is stated to
  one decimal (50.0%), so this is arguably within display precision —
  but compare the unrounded rate to 0.5 with `places=2` or an exact
  equality to make the check do what its name says.
- **(d) Weak baseline assertion:** `:219`,
  `"THEN" in baseline.stdout`, is a 4-letter substring that can occur
  in unrelated Django/SQL output. Assert on a longer, specific
  fragment of the reported SQL syntax error instead (e.g. the full
  error line the case study names).

## Observation (not a defect in these numbers)

- `averth/tracker.py:788` overwrites the accumulator-based
  `estimated_model` with `unpriced_spend` (duplicating line 748's
  computation path). For this run both are 0.0, so it has no effect on
  any figure above — but it is a latent trap: on any mixed ledger the
  accumulator value is silently discarded. Worth a cleanup, not a
  blocker for this release.
- The stdout `COST BASIS` header and the HTML banner are honest and
  consistent with each other ("trace-supplied token counts that
  Averth does not verify as recorded usage"); the contradiction is
  specifically the Data quality *label*, Defect 1.

## What I did not verify

- The $3/$15 list prices against Anthropic's live pricing page (no
  live-browser access in this role; values taken from
  `averth/pricing.py` as the task scoped it).
- The reproduce script end to end (Django install + live V0 run); the
  V0 figures are verified against the stored ledger and its digest,
  and the script's meter-section logic was audited against real
  `averth try` output rather than run.
- The gold-patch / baseline Django test claims in the reproduce
  script beyond the ledger's own run records (which do corroborate
  "Ran 1 test … OK" and "Ran 89 tests … OK (skipped=1)").

## Bottom line

Arithmetic: 14/14 published figures recompute exactly, the converter
is byte-for-byte faithful to the published trajectory, and both
`averth try` input paths agree. What fails is the labeling and the
certification: the shareable report calls estimated-token dollars
"vendor prices on recorded tokens", and the script meant to guard the
numbers has a vacuous billed check and proxy-only provenance checks.
Fix Defects 1–3 (one label change, two script changes), apply 4–6,
re-run, and this passes.
