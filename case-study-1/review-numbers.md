# Numbers review: case study 1 (django__django-15930)

**Verdict: FAIL** — one headline derived number is wrong (3.06x should be 3.07x),
and the printed reproduction steps do not execute as written (two `git apply`
commands operate on the wrong files). Everything else checked passes, including
all meter dollars, all V0 counts and digests, all test counts, and all hashes
listed below. The fixes are small and enumerated in §2. The case study must not
be published until D1 and D2 are fixed; D3–D6 are wording/traceability fixes
that should ride along.

**Reviewer stance:** every number was treated as wrong until a source proved
it. Sources used: the raw trajectory
(`validation-traces/mini-swe-agent-s3/raw/django__django-15930.traj.json`),
`per_instance_details.json`, the official S3 `report.json` fetched live for
this instance (HTTP 200), `swebench-row-django-15930.json` and
`swebench-verified.parquet` (500 rows), the V0 ledger + report, the checks
file, the allowlist, the trace events file, the Averth meter re-run from the
venv, `compare.py`, `convert.py`, `FINDINGS.md`, the four `.diff` files,
`trace-selection.md`, and the git state of `django-base` and of the Averth repo
(branch `criterion-c-checks-digest`). The file
`eval-report-requests-1921.json` was ignored as instructed (different
instance). The case study itself was not edited.

**Method note / one mutation:** verifying the meter required running the exact
command the case study prints
(`/home/hatch/workspace/averth/.venv/bin/python -m averth.cli trace
trace-events-django-15930.jsonl --format jsonl`), which rewrites
`trace-events-django-15930.html` in place. The HTML on disk is therefore now
this review's re-run output, not the original bytes. Its figures match the CLI
stdout exactly and match the case study; the re-run is deterministic for the
same day (price table v8, "19 days old" on 2026-11-11). No other case-study
file was modified.

---

## 1. Defects (each blocks publication until fixed, or should be fixed with it)

### D1 — Ratio is 3.07x, not 3.06x (material: wrong headline derived number)

- **File/line:** `case-study-1.md:118` — "Metered estimate divided by recorded
  cost: 3.06x."
- **Wrong text:** `3.06x`
- **Correct text:** `3.07x`
- **Proof:** The meter's own unrounded figures are metered **$0.9832** and
  recorded **$0.3205**. `0.9832 / 0.3205 = 3.0674 → 3.07x`. This is not my
  reconstruction: the project's own cross-check script prints it —
  `compare.py` output for this instance is
  `django__django-15930  0.9832  0.3205  3.07  35  284094`.
  Independent recomputation from the price table agrees: input 279,017 tokens
  × $3.00/1M = $0.837051, output 5,077 × $15.00/1M = $0.076155, model
  $0.913206; tools 35 × $0.002 = $0.07; total $0.983206 → $0.98.
  `0.983206 / 0.32052915 = 3.0674 → 3.07x`.
- **How the error happened:** 3.06x is what you get by dividing the
  already-rounded display figures: `$0.98 / $0.3205 = 3.0577 → 3.06x`. A ratio
  must be computed from unrounded values, not from rounded display values.
  The case study therefore contradicts the project's own `compare.py` on the
  same instance.
- **Fix:** change line 118 to `Metered estimate divided by recorded cost:
  3.07x.` (Optionally add the unrounded basis in parentheses:
  `($0.9832 metered / $0.3205 recorded)`.)

### D2 — Reproduction steps do not execute as written (material: the steps fail)

Two commands in "Reproduction steps" operate on the wrong file contents. The
prose says "extract it" but no extraction command is given, so a reader
following the printed commands literally fails at both `git apply` steps.

**D2a — test patch (lines 196–205).**

- **Wrong text (lines 196–205):**
  ```
  curl -sL -o /tmp/test-patch.diff \
    "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet"
  ```
  …then `git apply /tmp/test-patch.diff`.
- **Problem:** the curl downloads the whole parquet dataset binary to
  `/tmp/test-patch.diff`. The printed `git apply /tmp/test-patch.diff` then
  tries to apply a parquet binary as a patch. Demonstrated in a scratch repo:
  `error: git diff header lacks filename information when removing 1 leading
  pathname component (line 1440)`.
- **Fix:** insert a real extraction command between the curl and the apply,
  e.g. extract the `test_patch` field of instance `django__django-15930`
  from the parquet (pyarrow) into `/tmp/test-patch.diff`, and only then run
  `git apply /tmp/test-patch.diff`. The current line 205 must not run against
  the downloaded parquet.

**D2b — agent submission (lines 211–220).**

- **Wrong text (lines 211–220):**
  ```
  curl -sL -o /tmp/submission.diff \
    "https://s3.amazonaws.com/.../django__django-15930.traj.json"
  ```
  …then `printf '\n' >> /tmp/submission.diff` and
  `git apply /tmp/submission.diff`.
- **Problem:** at that point `/tmp/submission.diff` holds the trajectory
  JSON, not the patch. The `printf` appends a newline to the JSON file
  itself, and `git apply` then fails on JSON. Demonstrated in a scratch repo:
  `error: No valid patches in input (allow with "--allow-empty")`.
- **Fix:** insert a real extraction command (e.g. Python `json.load`, write
  `info["submission"]` to `/tmp/submission.diff`) between the curl and the
  `printf`/`git apply`, so the newline is appended to the extracted diff,
  not to the JSON.

### D3 — "Byte-identical … apart from that newline" is false as written (wording)

- **File/lines:** `case-study-1.md:78–82` — "Appending one newline makes
  `git apply` accept it cleanly, and the applied diff is byte-identical to
  the recorded submission apart from that newline."
- **Wrong text:** `the applied diff is byte-identical to the recorded
  submission apart from that newline`
- **Proof:** the regenerated `git diff` (checked both in the real
  `django-base` repo and in a scratch repo) differs from the recorded
  submission in **two** places, not one: (1) the index line — recorded
  `index 822968ef56..02a49836d7 100644` vs regenerated
  `index 822968e..02a4983 100644` (different hash abbreviation); (2) the
  trailing newline (recorded patch ends `...compile(self.result)` with no
  newline; regenerated diff ends with `\n`). Real-repo regenerated diff is
  742 bytes vs 747 for the submission. The hunk bodies are identical, and
  the patched **file** bytes are identical (verified: git-applied file ==
  GNU-patched file), so the substance ("the code change is intact") holds —
  only the literal byte-identity claim about the diff is wrong.
- **Fix:** replace with `the applied file matches the submission's intended
  content exactly; the regenerated git diff differs only in the abbreviated
  index hashes (and the trailing newline).`

### D4 — Test counts misattributed to "the leaderboard entry" (wording)

- **File/line:** `case-study-1.md:22` — "The leaderboard entry records
  FAIL_TO_PASS 1/1 and PASS_TO_PASS 88/88 for this run."
- **Wrong text:** `The leaderboard entry records`
- **Proof:** the leaderboard entry's `per_instance_details.json` record for
  this instance holds only `{cost, api_calls, resolved}` — no test counts.
  The 1/1 and 88/88 live in the official evaluation `report.json` (fetched
  live: FAIL_TO_PASS success 1 / failure 0; PASS_TO_PASS success 88 /
  failure 0). The numbers are right; the attribution is not.
- **Fix:** `The official evaluation report (report.json) records FAIL_TO_PASS
  1/1 and PASS_TO_PASS 88/88 for this run.`

### D5 — Pre-patch discrimination run is asserted but not recorded (traceability)

- **File/lines:** `case-study-1.md:71–76` — "Before the agent patch was
  applied, the same test failed with `OperationalError: near "THEN": syntax
  error`…"
- **Problem:** the V0 ledger contains only the 2 post-patch runs. No
  pre-patch run (command, timestamp, exit code, output digest) exists in
  any artifact. The only support is prose in `trace-selection.md`
  ("Target test WITHOUT the agent patch: FAILED… verified live here") with
  no recorded output. The claim is plausible and is independently
  corroborated in substance by the FAIL_TO_PASS designation (the test failed
  on base code in SWE-bench's own validation), but the case study presents a
  live run "here" that no record backs.
- **Fix (either):** (a) record the pre-patch run — revert the agent patch
  under the allowlist, run the target test, keep the failed run in the
  ledger — and cite it; or (b) soften the wording to attribute the claim,
  e.g. "The test fails without the patch (trace-selection.md; consistent
  with its FAIL_TO_PASS designation)".

### D6 — Verifier commit is asserted but not recorded in the ledger (traceability)

- **File/line:** `case-study-1.md:47` — "The verifier used here is the
  `criterion-c-checks-digest` branch (commit 8ec848b), not master."
- **Problem:** the commit exists and is the current branch tip
  (`8ec848b7d3085c752f340ffe2754d90ada432edd`, 2026-11-09, "Freeze checks at
  load and refuse mid-run edits (criterion c)"), and the freeze code/tests
  exist on the branch — but the ledger carries **no** verifier version or
  commit field (keys checked; only `target_commit` and `commit_note: null`).
  Nothing in the artifacts binds this run to 8ec848b; the linkage rests on
  the operator's statement plus the current checkout.
- **Fix:** add the verifier commit/branch to the ledger (or to the report
  header) for the run, or qualify the sentence as the operator's record
  rather than a ledger-backed fact.

### D7 — Minor precision nit (not a defect, no fix required)

- "35 tool calls, 0 tool failures" (line ~20): only **34** of the 35 turns
  produced a recorded `<returncode>` in the trajectory (all 34 are `0`); the
  35th turn is the submission turn (`echo MICRO_SWE_AGENT_FINAL_OUTPUT &&
  git add -A && git diff --cached`), whose result is the diff echo, not a
  returncode. No failure signal exists anywhere, so "0 tool failures" is
  true — but its evidence base is 34 returncodes, not 35. Separately, the
  trace-events tool events are synthetic by construction (`convert.py`: one
  tool event per assistant turn); the "35 tool calls" count is nonetheless
  independently corroborated — all 35 assistant messages contain exactly
  one ```bash block. No change required; noted for precision.

---

## 2. Full verification table (every number checked)

### Run identity and trajectory

| # | Claim (case-study-1.md) | Source checked | Recomputed / found | Result |
|---|---|---|---|---|
| 1 | 72 messages (1 system, 35 assistant, 36 user) | raw `.traj.json` `messages` | 72 total; roles system 1, assistant 35, user 36 | PASS |
| 2 | 35 API calls | `per_instance_details.json` + traj `info.model_stats` + trace events | `api_calls: 35` in both records; 35 model events | PASS |
| 3 | 35 tool calls | traj assistant messages + trace events | all 35 assistant msgs contain exactly 1 ```bash block; 35 tool events | PASS (see D7 nit) |
| 4 | 0 tool failures | traj `<returncode>` values | 34 returncodes present, all `0`; no other failure signal | PASS (see D7 nit) |
| 5 | 0 retries | traj returncodes + `convert.py` rule + meter | no nonzero returncode → 0 retry events; meter `Retries: 0` | PASS |
| 6 | Agent `mini-SWE-agent v1.0.0 (bash-only)`, model `claude-sonnet-4-20250514` | traj / trace events / S3 paths | model field `claude-sonnet-4-20250514` on all 35 model events; harness per S3 path `20250726_mini-v1.0.0` | PASS |
| 7 | Task `django__django-15930`, repo `django/django`, base commit `63884829acd207404f2a5c3cc1d6b4cd0a822b70` | parquet row 210 + row JSON + ledger `target_commit` + `django-base` HEAD | all agree exactly; `django-base` HEAD is that commit (2022-08-09) | PASS |
| 8 | Generated SQL `CASE WHEN THEN true ...` | row JSON `problem_statement` | verbatim: `ORDER BY CASE WHEN THEN true ...` | PASS |
| 9 | 4-line patch to `django/db/models/expressions.py` | traj `info.submission` + `agent-submission-*.diff` | 4 added lines (comment + `if not condition_sql:` + 2 assignments) | PASS |
| 10 | Patch: "if the compiled condition is empty, use the SQL literal `1=1`" | submission diff | `if not condition_sql:` / `condition_sql = "1=1"` / `condition_params = []` verbatim | PASS |
| 11 | Official outcome RESOLVED | S3 `report.json` (live fetch, HTTP 200) + `per_instance_details.json` | `resolved: true` in both; `patch_successfully_applied: true`, `patch_exists: true` | PASS |
| 12 | FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88 | S3 `report.json` | FTP success 1 / failure 0; PTP success 88 / failure 0; F2F/P2F empty | PASS on numbers; attribution wrong, see D4 |
| 13 | Recorded cost $0.3205 | `per_instance_details.json` | `cost: 0.32052914999999993` → $0.3205 (4dp) | PASS |
| 14 | Traj `model_stats` agrees exactly (`instance_cost: 0.32052914999999993`, `api_calls: 35`) | traj `info.model_stats` (a dict, not a string) | `{'instance_cost': 0.32052914999999993, 'api_calls': 35}` exact | PASS |
| 15 | Submission 747 bytes; eval `patch.diff` byte-identical, 747 bytes | traj submission + both `.diff` files | traj 747 B, both files 747 B, sha256 `dd420b03…` for both, `cmp` identical; both lack trailing newline | PASS |
| 16 | Missing final newline; `git apply` rejects "corrupt patch at line 15" | scratch-repo `git apply` test | reproduced: `error: corrupt patch at line 15`, exit 128 | PASS |
| 17 | GNU patch applies it with fuzz 1 | scratch-repo `patch -p1` test | `Hunk #1 succeeded at 1299 with fuzz 1` (+ "patch unexpectedly ends in middle of line") | PASS |
| 18 | Appending one newline makes `git apply` accept it cleanly | scratch-repo test | `git apply --check` and apply succeed after `printf '\n'` | PASS |
| 19 | "Applied diff is byte-identical … apart from that newline" | real `django-base` `git diff` + scratch repo | FALSE: regenerated diff also differs in index line (`822968ef56..02a49836d7` vs `822968e..02a4983`); 742 B vs 747 B. Patched file bytes identical. | **FAIL — D3** |
| 20 | Target test fails without patch (`OperationalError: near "THEN"`) | ledger + `trace-selection.md` | No run in ledger; only prose in `trace-selection.md`. Substance corroborated by FAIL_TO_PASS designation. | **FAIL (traceability) — D5** |
| 21 | Gold patch compiles `Value(True)`; `if condition_sql == ""` | parquet `patch` + gold `.diff` file | verbatim in both; parquet patch == gold file exactly | PASS |
| 22 | Agent patch vs gold patch differ; both pass recorded tests | submission vs gold diff; S3 report; V0 C1/C2 | agent hardcodes `"1=1"`, gold compiles `Value(True)`; agent passes per report + V0; gold passing is the SWE-bench merged fix | PASS |

### V0 ledger, report, checks, allowlist

| # | Claim | Source checked | Recomputed / found | Result |
|---|---|---|---|---|
| 23 | Checks digest `sha256:6dde8826cdd36df16d9a33464d847b2bd3da47e16055ed809a52202011d79739` | `sha256sum case-study-1-checks.json` + ledger + report | all four copies identical; `sha256sum` matches | PASS |
| 24 | Verifier branch `criterion-c-checks-digest`, commit `8ec848b` | Averth repo git | `8ec848b7d3085c752f340ffe2754d90ada432edd`, branch tip, 2026-11-09, msg "Freeze checks at load and refuse mid-run edits (criterion c)"; freeze code/tests on branch | PASS on existence; not recorded in ledger — **D6** |
| 25 | C1 VERIFIED, exit 0, digest `sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3`, Tier 2, after final edit | ledger judgments + runs + report | exit 0; digest reproduced exactly as `sha256(stdout+stderr)` from stored outputs; `after_final_edit: true`; run 2026-11-11T04:52:24.433824–04:52:25.856465Z, after final-edit marker 04:50:39Z | PASS |
| 26 | C2 VERIFIED, exit 0, digest `sha256:498fa2e366e99d81cea0e892d34670d1e06da5bd9b7bdb7cdb6251e471ddac91`, Tier 2, after final edit | ledger + report | exit 0; digest reproduced exactly as `sha256(stdout+stderr)`; `after_final_edit: true`; run 04:52:25.857086–04:52:26.503730Z | PASS |
| 27 | C3, C4 EXTERNAL-UNVERIFIABLE | ledger judgments | both `EXTERNAL-UNVERIFIABLE`, evidence `none`, no human/second-backend record | PASS |
| 28 | Coverage: 4 checks, 2 VERIFIED, 0 FAILED, 2 EXTERNAL-UNVERIFIABLE; unknown rate 50.0% | ledger `coverage` + report | `criteria_total 4`, counts `{VERIFIED: 2, EXTERNAL-UNVERIFIABLE: 2}`, `unknown 2`, `unknown_rate 0.5`, `decided 2`; 2/4 = 50.0% | PASS |
| 29 | Runs recorded: 2; superseded and retained, never cited: 0 | ledger `coverage` + runs | `runs_total 2`, `superseded_runs_retained 0`; both runs `superseded: false`, sequential, no overlap | PASS |
| 30 | C2: "89 tests ran, OK, 1 skipped" | ledger C2 stderr | `Ran 89 tests in 0.152s / OK (skipped=1)` verbatim | PASS |
| 31 | C1: "Ran 1 test" | ledger C1 stderr | `Ran 1 test in 0.007s / OK` | PASS |
| 32 | 89 = 88 PASS_TO_PASS + 1 FAIL_TO_PASS | row JSON / parquet (parsed) | PTP parsed list = 88, FTP = 1, both equal row JSON; module run covers both | PASS |
| 33 | Ledger generated_at = report Generated | ledger + report | `2026-11-11T04:52:26.504850+00:00` in both; generated 1.1 ms after C2 end | PASS |
| 34 | Allowlist "exactly the two runtests commands" | allowlist JSON vs ledger run commands | exactly 2 commands; both match ledger `command_raw` exactly | PASS |
| 35 | `django-base` state matches ledger snapshot | `git status` + `sha256sum` | exactly 2 modified files (`expressions.py`, `tests/expressions_case/tests.py`); `expressions.py` sha256 `7a091204…` = ledger `files` entry; `workspace_dirty: true` | PASS |
| 36 | Working tree: "exactly 2 files, 14 insertions" (`trace-selection.md`) | `git diff --numstat` | 4 + 10 = 14 insertions, 0 deletions, 2 files | PASS |

### Meter (re-run from the Averth venv on the saved trace events)

| # | Claim | Source checked | Recomputed / found | Result |
|---|---|---|---|---|
| 37 | 71 events: 35 model, 35 tool, 1 end | trace events file | `wc -l` 71; counter model 35, tool 35, end 1; file identical to the django subset of `events.jsonl` (71/71, byte-equal as parsed JSON) | PASS |
| 38 | Attempts 1; trace-labelled completions 1; human escalations 0; retries 0 | meter re-run stdout | `Attempts: 1`, `Autonomous completions: 1 (100.0%)`, `Human escalations: 0`, `Retries: 0` | PASS |
| 39 | Fully loaded $0.98 ESTIMATED ($0.91 priced model + $0.07 estimated tool) | meter re-run + price table + recomputation | model $0.913206 → $0.91; tools 35 × $0.002 = $0.07; total $0.983206 → $0.98; provenance priced $0.91 / estimated $0.07 / billed $0.00 | PASS |
| 40 | Recorded $0.3205; metered/recorded ratio | `compare.py` + recomputation | metered $0.9832 / recorded $0.3205 = **3.07x**; case study says 3.06x | **FAIL — D1** |
| 41 | Context compounding 9.9x first-to-last input growth | trace events + meter source (`tracker.py`) | first input 1460, last 14465; 14465/1460 = 9.9075 → 9.9x; inputs monotonic non-decreasing; meter prints 9.9x | PASS |
| 42 | Context tax $0.68, 75% of model spend | trace events + `tracker.py` formula | tax = Σ(inᵢ − 1460) × $3/1M over steps 2–35 = 227,917 × 3e-6 = $0.683751 → $0.68; share 0.683751/0.913206 = 74.87% → 75% | PASS |
| 43 | Yield 100% of tokens on terminal path | meter re-run | `100% of tokens on the terminal path (0% burned on retries and failed runs)`; total tokens 279,017 + 5,077 = 284,094 = `compare.py` "turns" column | PASS |
| 44 | Provenance: $0.91 priced, $0.07 estimated, $0.00 billed | meter re-run | matches exactly; tool spend flagged as built-in estimates (bash) | PASS |
| 45 | Token counts are estimates (chars/4); no prompt-cache counts; no bill | `convert.py` + trace event keys | `convert.py` documents chars//4 estimation; model events carry only `{type, case_id, model, input_tokens, output_tokens}` — no cache fields | PASS |
| 46 | "Same gap was 3.84x across 12 runs from this leaderboard entry" | `compare.py` re-run + `FINDINGS.md` | totals metered $17.4896 vs recorded $4.5547 → 3.8405 → 3.84x; 12 traj files, 12 cases in `events.jsonl` (938 events); per-instance ratios 1.91–4.47 as stated in FINDINGS.md | PASS |
| 47 | Trace token totals: input 279,017, output 5,077 (ledger/report trace summary) | trace events | Σ input 279,017; Σ output 5,077; matches ledger `trace_summary` and report | PASS |
| 48 | Cost per accepted outcome $0.98 estimated vs $0.3205 recorded, "this one run only" | meter + recorded cost | $0.98 (rounded) / $0.3205; one outcome, one run — arithmetic follows from #39/#13 | PASS |
| 49 | Price table v8, Sonnet 4 $3.00/$15.00 per 1M | `averth/pricing.py` | `anthropic:claude-sonnet-4-20250514: (3.00, 15.00)` "published list price"; tool default $0.002/call | PASS |
| 50 | Meter HTML figures ($0.98, $0.91, $0.07, $0.68, 75%, 9.9x, 100%) | regenerated HTML (see method note) | all present and matching CLI stdout; `$1.98` in the HTML is only a chart-axis maximum, not a cost figure | PASS |

### Dates, hashes, misc

| # | Claim | Source checked | Recomputed / found | Result |
|---|---|---|---|---|
| 51 | Base commit date 2022-08-09 (`trace-selection.md`) | `django-base` git log | commit + author date `2022-08-09 06:08:48 +0200` (row JSON `created_at` is 2022-08-07, the issue date — different field, no conflict) | PASS |
| 52 | S3 / leaderboard URLs, date `20250726` | live fetch | `report.json` fetched HTTP 200 (9,284 B); `test_output.txt` HTTP 200 (26,276 B, 530 lines); paths match the `20250726_mini-v1.0.0_claude-sonnet-4-20250514` prefix | PASS |
| 53 | Python 3.12 (reproduction steps) | `django-venv` python | Python 3.12.3 | PASS |
| 54 | Reproduction: target test passes; module passes (89 tests, 1 skipped) | ledger C1/C2 (see #25/#26/#30) | consistent; the exact `runtests.py` commands in the repro match the allowlisted/ledger commands | PASS |
| 55 | `eval-report-requests-1921.json` is a different instance | (ignored per task instructions) | not cited anywhere in the case study; no numbers taken from it | PASS (by instruction) |

---

## 3. What passed (summary)

Out of 55 checked items, 50 pass outright. The meter dollars, the token
arithmetic, the context-tax derivation, the V0 verdicts/exit codes/timestamps/
digests (both output digests reproduce exactly as `sha256(stdout+stderr)`),
the test counts (1/1, 88/88, 89 run / 1 skipped), the checks digest, the
747-byte submission and its eval-copy identity, the git-apply / GNU-patch
behavior, the gold-vs-agent patch quotes, the 12-run 3.84x cross-check, and
the repo/commit state all verify exactly against their sources.

## 4. Required fixes before publication

1. **D1:** `case-study-1.md:118` — `3.06x` → `3.07x`.
2. **D2a/D2b:** `case-study-1.md:196–220` — add real extraction commands for
   the test patch (parquet → `test_patch` field) and the submission
   (traj JSON → `info.submission`) before the `git apply` steps; verify the
   printed sequence end-to-end in a clean checkout.
3. **D3:** `case-study-1.md:78–82` — drop the literal "byte-identical …
   apart from that newline" claim; state the file-level identity and the
   index-line difference.
4. **D4:** `case-study-1.md:22` — attribute 1/1 and 88/88 to the official
   evaluation `report.json`, not "the leaderboard entry".
5. **D5:** record the pre-patch run in the ledger, or soften the
   discrimination claim to its actual sources.
6. **D6:** record the verifier commit (8ec848b) in the ledger/report, or
   qualify the sentence.

After fixes, re-verify D1 by re-running `compare.py` and D2 by executing the
printed reproduction steps verbatim in a clean directory.
