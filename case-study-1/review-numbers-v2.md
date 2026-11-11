# Numbers review v2: case study 1 (django__django-15930), rewritten text vs NEW V0 run

**Verdict: FAIL** — one number in the rewritten text is stale from the first V0
run and does not match the new ledger it cites. Everything else checked passes,
including all six D1–D6 fixes from the first numbers review, both new output
digests, the new checks digest, all meter dollars, all test counts, and the
3.07x ratio. The single defect is small and has a one-word fix, but it is a
wrong number attached to the cited digest, so the case study must not be
published until it is fixed.

**Reviewer stance:** every number was treated as wrong until a primary source
proved it. Sources used: the NEW V0 ledger
(`v0-run/evidence_ledger.json`, generated 2026-11-11T05:14:38.356674+00:00) and
report (`v0-run/evidence_report.md`), the saved checks/allowlist files, the
trace events file, the meter HTML, an independent meter re-run in `/tmp`
(CLI stdout + fresh HTML), the raw trajectory
(`validation-traces/mini-swe-agent-s3/raw/django__django-15930.traj.json`),
local `per_instance_details.json`, `compare.py` output, the SWE-bench row
file, `baseline-pre-patch-run.txt`, `gold-patch-run.txt`, the saved diffs,
`verifier-version.txt`, the Averth repo git state, and the official S3
`report.json` fetched live for this instance. The case study itself and all
evidence files were not edited.

**Method notes:**
- The meter was re-run from a copy of the trace events in `/tmp/numv2`, so the
  saved `trace-events-django-15930.html` was not rewritten. The fresh HTML is
  byte-identical to the saved file (`diff` clean).
- The V0 run was NOT re-executed (that would rewrite the ledger under review);
  digests were instead recomputed from the ledger's stored stdout/stderr.
- The `git apply` acceptance after appending a newline was NOT re-proven by
  this reviewer in a real checkout (my scratch repo has no `expressions.py`,
  so the apply fails there for want of the file, not the patch). The raw-patch
  rejection was re-proven in scratch (`error: corrupt patch at line 15`,
  exit 128). Acceptance after `+ "\n"` in a real checkout was verified by
  both prior reviews and by `repro-test-fixed-steps.md` Stage 2.

---

## 1. Defect (blocks publication until fixed)

### N1 — C2 run-time line is stale: `0.152s` in the text, `0.168s` in the new ledger

- **File/line:** `case-study-1.md:73` — "The output digests are over output
  that includes Django's run-time line (`Ran 89 tests in 0.152s`)…"
- **Wrong text:** `Ran 89 tests in 0.152s`
- **Correct text:** `Ran 89 tests in 0.168s`
- **Proof:** the NEW ledger's C2 run stderr is verbatim
  `Ran 89 tests in 0.168s\n\nOK (skipped=1)`. Recomputing
  `sha256(stdout + stderr)` from the ledger's stored C2 output gives exactly
  the cited digest `sha256:c3c5f341…` — i.e. the cited digest is a hash over
  output containing `0.168s`, not `0.152s`. `0.152s` was the FIRST V0 run's
  timing (its C2 digest was `sha256:498fa2e3…`); it survived the rewrite
  while the digest it describes was replaced. The sentence is about the
  published digests, so the quoted value is wrong for the run being cited.
  (The generic point — digests embed a wall-clock line and usually do not
  reproduce — is correct, and the repro-test note confirms the lottery: a
  rerun at 05:19 landed on `0.152s` / digest `498fa2e3…` again.)
- **Fix:** change line 73 to `Ran 89 tests in 0.168s`, or drop the specific
  value and write "Django's run-time line (`Ran 89 tests in …s`)".

---

## 2. First review's D1–D6: all fixed in the new text

| Finding | Required fix | Status in rewritten text |
| --- | --- | --- |
| D1 — ratio 3.06x, should be 3.07x | Change to 3.07x | **FIXED.** Line 139: `3.07x ($0.9832 unrounded / $0.3205)`. Recomputed: `0.9832/0.3205 = 3.0677 → 3.07x`; full precision `0.983206/0.32052915 = 3.0674 → 3.07x`; `compare.py` prints `3.07`. |
| D2 — reproduction steps lacked extraction commands | Add real parquet→test_patch and JSON→submission extraction | **FIXED.** Lines 261–270 (parquet saved as `/tmp/swebench-verified.parquet`, pyarrow extraction writing `/tmp/test-patch.diff`) and 284–290 (traj JSON saved as `/tmp/django-15930.traj.json`, stdlib-json extraction writing `/tmp/submission.diff`). `repro-test-fixed-steps.md` ran the fixed steps verbatim end to end, exit 0 at every stage. |
| D3 — "byte-identical … apart from that newline" false | State file-level identity + index-line difference | **FIXED.** Lines 98–101: "the applied file matches the submission's intended content exactly. The regenerated git diff differs from the recorded patch only in the abbreviated index hashes and the trailing newline." Consistent with the first review's measured difference (index `822968ef56..02a49836d7` vs `822968e..02a4983`, 747 B vs 742 B). |
| D4 — 1/1 and 88/88 attributed to "the leaderboard entry" | Attribute to official evaluation `report.json` | **FIXED.** Line 26: "The official evaluation record (`report.json`) records FAIL_TO_PASS 1/1 and PASS_TO_PASS 88/88 for this run." Verified live (see §3 item 12). |
| D5 — pre-patch discrimination run asserted but not recorded | Record the run or soften the claim | **FIXED (recorded).** `baseline-pre-patch-run.txt` exists and is cited (lines 88–91, 202). It records command, working directory, state (test patch applied, agent patch NOT applied), timestamp 2026-11-11T04:57:12Z, exit code 1, `OperationalError: near "THEN": syntax error`, `Ran 1 test … FAILED (errors=1)`. |
| D6 — verifier branch/commit asserted but not in ledger | Record in ledger or qualify as operator's record | **FIXED (qualified).** Lines 52–55: "The verifier used here is the `criterion-c-checks-digest` branch (commit 8ec848b), not master, per the operator's record in `verifier-version.txt`; the ledger itself carries no verifier version field." The ledger indeed has no verifier key (top keys checked; only `target_commit`, `commit_note: null`). `verifier-version.txt` states branch, commit `8ec848b`, full hash `8ec848b7d3085c752f340ffe2754d90ada432edd`; the Averth repo confirms branch `criterion-c-checks-digest` at exactly that HEAD with message "Freeze checks at load and refuse mid-run edits (criterion c)". |

---

## 3. Per-item check table (task items a–g plus full number sweep)

### (a) 3.07x ratio and unrounded basis

| # | Claim | Source / recomputation | Result |
| --- | --- | --- | --- |
| 1 | Ratio 3.07x | `0.9832 / 0.3205 = 3.0677 → 3.07x`; full precision `0.983206 / 0.32052915 = 3.0674 → 3.07x` | PASS |
| 2 | Unrounded basis `$0.9832 / $0.3205` | Meter total recomputed from trace tokens: input 279,017 × $3/1M = $0.837051, output 5,077 × $15/1M = $0.076155, model $0.913206; tools 35 × $0.002 = $0.07; total $0.983206 → `$0.9832` (4dp). Recorded $0.32052914999999993 → `$0.3205` (4dp) in both `per_instance_details.json` and traj `model_stats` | PASS |
| 3 | Rounded-display trap avoided | Text no longer divides $0.98/$0.3205 (= 3.06x); the unrounded basis is printed alongside | PASS |

### (b) Checks digest

| # | Claim | Source / recomputation | Result |
| --- | --- | --- | --- |
| 4 | Checks digest `sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a` | `sha256sum case-study-1-checks.json` = same value; ledger `checks_digest` = same; report header = same. Three-way match. (Note: this is the NEW portable-file digest; the first run's absolute-paths file still hashes to the old `6dde8826…`, and is kept separately as `case-study-1-checks-v1-absolute-paths.json`.) | PASS |

### (c) C1 / C2 output digests vs the NEW ledger

| # | Claim | Source / recomputation | Result |
| --- | --- | --- | --- |
| 5 | C1 digest `sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3` | Ledger judgment C1 + run 1: exit 0, `after_final_edit: true`, `sha256(stdout+stderr)` recomputed from stored outputs = exact match. C1 stderr `Ran 1 test in 0.007s / OK`. | PASS |
| 6 | C2 digest `sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b` | Ledger judgment C2 + run 2: exit 0, `after_final_edit: true`, `sha256(stdout+stderr)` recomputed from stored outputs = exact match. C2 stderr `Ran 89 tests in 0.168s / OK (skipped=1)`. This is the NEW digest (first run's was `498fa2e3…`); the text cites the new one correctly. | PASS |
| 7 | Both runs Tier 2, after final edit | Ledger judgments: trust tier 2 for C1/C2; run starts 05:14:36.75 and 05:14:37.61, both after final-edit marker 2026-11-11T05:14:32+00:00; ledger `generated_at` 05:14:38.356674+00:00 = report "Generated" timestamp | PASS |

### (d) Coverage counts

| # | Claim | Source / recomputation | Result |
| --- | --- | --- | --- |
| 8 | 4 checks, 2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE | Ledger `coverage`: `criteria_total 4`, counts `{VERIFIED: 2, EXTERNAL-UNVERIFIABLE: 2}` (no FAILED key), `decided 2` | PASS |
| 9 | Unknown rate 50.0% | Ledger `unknown 2`, `unknown_rate 0.5`; 2/4 = 50.0% | PASS |
| 10 | Runs 2, superseded 0 | Ledger `runs_total 2`, `superseded_runs_retained 0`; both runs `superseded: false` | PASS |

### (e) Run counts, meter figures, test counts, attribution

| # | Claim | Source / recomputation | Result |
| --- | --- | --- | --- |
| 11 | 72 messages (1 system, 35 assistant, 36 user); 35 API calls; 35 tool calls; 34 recorded tool results, all exit 0; 0 retries | Raw traj: 72 messages, roles system 1 / assistant 35 / user 36; `model_stats api_calls: 35`; all 35 assistant messages contain exactly one ```bash block; returncodes found: 34, all `0`; no other failure signal. Ledger `trace_summary.retry_events: 0`. | PASS |
| 12 | Official outcome RESOLVED; FAIL_TO_PASS 1/1; PASS_TO_PASS 88/88 | Live S3 `report.json`: `resolved: true`, `patch_successfully_applied: true`; FAIL_TO_PASS success 1 / failure 0; PASS_TO_PASS success 88 / failure 0. Corroborated by SWE-bench row (FTP list length 1, PTP list length 88) and by the module run (89 = 88 + 1). Attribution now to `report.json`, not the leaderboard entry. | PASS |
| 13 | Recorded cost $0.3205; traj `model_stats` agrees exactly | `per_instance_details.json`: `cost 0.32052914999999993, api_calls 35, resolved true`; traj `model_stats`: `instance_cost 0.32052914999999993, api_calls 35` — identical | PASS |
| 14 | Meter: $0.98 total, $0.91 priced, $0.07 estimated, $0.00 billed | Independent meter re-run in `/tmp` (CLI stdout): Model/API $0.91, Tool calls $0.07, Fully loaded $0.98; provenance Priced $0.91, Vendor-supplied (billed) $0.00, Estimated $0.07. Fresh HTML byte-identical to saved HTML. | PASS |
| 15 | Meter: Attempts 1; Autonomous completions 1 (100.0%); Human escalations 0; Retries 0; retry path $0.00 | Same independent re-run stdout: `Attempts: 1`, `Autonomous completions: 1 (100.0%)`, `Human escalations: 0`, `Retries: 0`, `Retry path: $0.00` | PASS |
| 16 | Context compounding 9.9x; context tax $0.68, 75% of model spend | Trace events: first input 1,460, last 14,465; 14465/1460 = 9.9075 → 9.9x; inputs monotonic non-decreasing (verified). Tax = Σ(inᵢ − 1460) × $3/1M over steps 2–35 = 227,917 × 3e-6 = $0.683751 → $0.68; share 0.683751/0.913206 = 74.87% → 75%. CLI stdout prints both figures identically. | PASS |
| 17 | Yield 100% of tokens on terminal path | CLI stdout and HTML: "100% of tokens on the terminal path (0% burned on retries and failed runs)" | PASS |
| 18 | 71 events: 35 model, 35 tool, 1 end; input 279,017 / output 5,077 tokens | Trace events file: 71 lines, counts model 35 / tool 35 / end 1; Σ input 279,017, Σ output 5,077; matches ledger `trace_summary` exactly (lines 71, cases 1, model 35, retry 0) | PASS |
| 19 | Test counts: 1 test OK; 89 tests OK, skipped=1 | Ledger C1 stderr `Ran 1 test in 0.007s / OK`; C2 stderr `Ran 89 tests in 0.168s / OK (skipped=1)` | PASS |
| 20 | 3.84x across 12 runs from this leaderboard entry | `compare.py` re-run: totals metered $17.4896 vs recorded $4.5547, ratio 3.84; 12 instances listed; this instance's row `0.9832 / 0.3205 / 3.07 / 35 / 284094` (token total 284,094 = 279,017 + 5,077) | PASS |
| 21 | "Cost per completed run $0.98 … No human accepted this run (C3), so no cost per accepted outcome is claimed" | Follows from items 14–15 and C3 EXTERNAL-UNVERIFIABLE; consistent with ledger `trace_summary.note` ("no acceptance join, so no cost-per-accepted-outcome figure is computed") | PASS |
| 22 | 4-line patch; `1=1` under `if not condition_sql:`; 747 bytes; missing final newline; `git apply` "corrupt patch at line 15"; GNU patch fuzz 1 | Traj submission: 4 added lines (comment + `if not condition_sql:` + 2 assignments), 747 bytes, no trailing newline; sha256 `dd420b03…` identical across traj submission, eval `patch.diff`, and saved agent file. Scratch re-test: raw `git apply` fails `error: corrupt patch at line 15`, exit 128. GNU-patch fuzz-1 behavior verified by both prior reviews (not re-proven here; see method note). | PASS |
| 23 | Gold patch compiles `Value(True)` under `if condition_sql == ""` | Saved gold diff verbatim: `if condition_sql == "":` / `condition_sql, condition_params = compiler.compile(Value(True))` | PASS |
| 24 | Gold patch rerun: "target test passes, module 89 tests OK, 1 skipped, saved as `gold-patch-run.txt`" | `gold-patch-run.txt` records ONE command (module run, exit 0, `Ran 89 tests in 0.171s / OK (skipped=1)`), timestamp 2026-11-11T04:57:17Z, state "GOLD patch applied". No standalone target-test run is in the file — but the module run's 89 tests are the 88 PTP + 1 FTP, and the FTP test IS the target test, so "target test passes" is entailed by the recorded module run, not separately recorded. No numeric error; noted as a precision observation, not a defect. | PASS (with note) |
| 25 | Base commit `63884829acd207404f2a5c3cc1d6b4cd0a822b70`; model `claude-sonnet-4-20250514`; harness mini-SWE-agent v1.0.0 | Ledger `target_commit`, SWE-bench row `base_commit`, S3 path prefix `20250726_mini-v1.0.0_claude-sonnet-4-20250514`, trace model events all `claude-sonnet-4-20250514` — all agree | PASS |
| 26 | Final-edit marker `2026-11-11T05:14:32Z` | Ledger `final_edit_marker 2026-11-11T05:14:32+00:00`; report header identical; both runs start after it | PASS |
| 27 | C3/C4 EXTERNAL-UNVERIFIABLE; "No human reviewed"; "SQLite in memory only" | Ledger judgments C3/C4: status EXTERNAL-UNVERIFIABLE, evidence `none`; report scope limitations match the text | PASS |
| 28 | Files list: all listed files exist | All 12 listed files present in the case-study directory (ledger, report, checks, allowlist, trace events, HTML, baseline run, gold run, verifier-version, both v1 files, trace-selection) | PASS |

### (f) D1–D6 fixed?

Yes — all six, per §2 above. D1, D3, D4 are exact text fixes verified
character-for-character; D2 is verified by the fixed steps plus the operator's
verbatim end-to-end test (`repro-test-fixed-steps.md`, all stages exit 0);
D5 is verified by the saved baseline file's contents; D6 is verified by the
qualification sentence plus the ledger's key list.

### (g) Verifier branch/commit claim properly qualified?

Yes. The sentence now attributes the branch/commit to the operator's record
in `verifier-version.txt` and states in the same sentence that the ledger
carries no verifier version field. That is the honest form: the commit exists
and is the branch tip (verified in the Averth repo), but nothing in the
ledger binds this run to it, and the text no longer implies otherwise.

---

## 4. The one failure, restated

| # | Location | Wrong | Correct | Evidence |
| --- | --- | --- | --- | --- |
| N1 | `case-study-1.md:73` | `Ran 89 tests in 0.152s` | `Ran 89 tests in 0.168s` | New ledger C2 stderr verbatim; `sha256(stdout+stderr)` recomputed = cited digest `c3c5f341…`, which hashes output containing `0.168s` |

## 5. Required fix before publication

1. **N1:** `case-study-1.md:73` — `0.152s` → `0.168s` (or drop the specific
   timing value). After the fix, re-verify by re-reading the ledger C2 stderr
   against the line; no new V0 run is needed.

## 6. Observations (not defects, no fix required)

- The HTML report's `$1.98` is only a chart-axis maximum, not a cost figure;
  the case study does not cite it. (Same note as the first review.)
- The HTML labels the $0.00 figure "Vendor-supplied (billed)"; the case
  study's "$0.00 billed" is the same bucket under the meter's CLI wording.
- The gold-patch "target test passes" claim rests on the module run's 89
  tests (88 PTP + 1 FTP) rather than a standalone target-test run in
  `gold-patch-run.txt`. Entailed, but a reader checking the file finds only
  the module command.
