# Execution-evidence report (V0 verifier): averth-case-study-1

Generated: 2026-11-11T05:14:38.356674+00:00
Target repo: /home/hatch/workspace/averth/case-study-1/django-base
Target commit: 63884829acd207404f2a5c3cc1d6b4cd0a822b70
Workspace dirty: True
Final edit marker: 2026-11-11T05:14:32+00:00
Task intent: The Django Case() with an empty When condition (~Q(pk__in=[])) no longer generates invalid SQL; the annotated query runs and marks all rows selected; the existing expressions_case tests still pass. (source: SWE-bench Verified instance django__django-15930 problem statement and test patch, human-written for this case study)
Checks digest: sha256:f25cd3bc39c5db75c4590baa26a3b38fe8401f985f9b196370d2259d27d4ed2a

## LIMITATIONS FIRST (read before any verdict below)

1. This is a local retrospective evidence report, not a live customer workflow, not a merge certifier, and not a boot or correctness verdict.
2. NOT OBSERVED is a statement about the records, not about reality. It is never upgraded to NOT EXECUTED or to FAILED by inference.
3. A successful shell command is not proof of complete correctness. A VERIFIED row proves only what its cited observation shows, bounded by what the tests actually cover.
4. A local hash detects alteration or mismatch between copies of a record; it is not tamper-resistant provenance. Tier 2 is stronger observation on a user-controlled host, never cryptographic proof.
5. No Tier 3 evidence exists in this report: no independent CI runner with signed attestation is wired in. No Tier 4 evidence exists unless a named human confirmation record was supplied in the check file.
6. This report does not prove test quality, correctness beyond the named assertions, acceptance by any human or operator, value, time saved, willingness to pay, or boot on untested hardware.
7. The fixture case, if used, has no trace events and no acceptance join, so no cost-per-accepted-outcome figure is claimed for it. Any trace summary in this report is a summary only and is never cited as a verdict.
8. No Qwen support, no cost savings, no subscription, and no production readiness are claimed anywhere in this report.
9. Redaction can miss secrets. If a future version of this report ever ingests a real transcript, treat any shared report as potentially secret-bearing and review it before sharing. The default upload set is empty; nothing in this tool uploads anything.

## Coverage

Total criteria: 4
- EXTERNAL-UNVERIFIABLE: 2
- VERIFIED: 2
Unknown (NOT OBSERVED + EXTERNAL-UNVERIFIABLE): 2
Unknown rate: 50.0%
Decided (VERIFIED + FAILED): 2
Runs recorded: 2, of which superseded and retained, never cited: 0

## Trace summary (summary only, never a verdict)

File: /home/hatch/workspace/averth/case-study-1/trace-events-django-15930.jsonl, lines: 71, cases: 1, model events: 35, retry events: 0, input tokens: 279017, output tokens: 5077
Summary only. This trace carries no acceptance join, so no cost-per-accepted-outcome figure is computed from it, and no judgment in any report may cite this summary as a verdict.

## Judgments

### C1: the FAIL_TO_PASS test passes with the agent patch
- Status: **VERIFIED**. Trust tier: 2. Evidence source: allowlist_recorder. Evidence ID: FAIL_TO_PASS test with agent patch.
- command: python tests/runtests.py expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0
- working_directory: /home/hatch/workspace/averth/case-study-1/django-base
- start_timestamp: 2026-11-11T05:14:36.752297+00:00
- end_timestamp: 2026-11-11T05:14:37.607191+00:00
- exit_code: 0
- output_digest: sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3
- test_target: expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when
- after_final_edit: True
- Scope limitation: Proves only that this one test passes on this revision with this patch, on SQLite. It does not prove the fix is correct in general or on other database backends.
- Recommended next action: If the test fails, the agent patch does not fix the reported issue on this revision; do not present the run as a fix.

### C2: the PASS_TO_PASS tests still pass with the agent patch
- Status: **VERIFIED**. Trust tier: 2. Evidence source: allowlist_recorder. Evidence ID: expressions_case module, PASS_TO_PASS tests with agent patch.
- command: python tests/runtests.py expressions_case -v 0
- working_directory: /home/hatch/workspace/averth/case-study-1/django-base
- start_timestamp: 2026-11-11T05:14:37.607693+00:00
- end_timestamp: 2026-11-11T05:14:38.353170+00:00
- exit_code: 0
- output_digest: sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b
- test_target: expressions_case
- after_final_edit: True
- Scope limitation: Proves only that the expressions_case module is green on SQLite on this revision. It does not prove no other module regressed and does not cover other database backends.
- Recommended next action: If the module run fails, list which PASS_TO_PASS tests broke and say so; do not present the run as clean.

### C3: an independent human reviewed and accepted this run
- Status: **EXTERNAL-UNVERIFIABLE**. Trust tier: None. Evidence source: none. Evidence ID: None.
- Scope limitation: No human reviewed this run. Recorded test verdicts are evidence, not human acceptance.
- Recommended next action: Supply a named human/hardware confirmation record (tester, procedure, result), or drop the claim.

### C4: the fix is verified on a second database backend besides SQLite
- Status: **EXTERNAL-UNVERIFIABLE**. Trust tier: None. Evidence source: none. Evidence ID: None.
- Scope limitation: The recorded runs used SQLite in memory only. The agent patch hardcodes the SQL literal 1=1; other backends were not run.
- Recommended next action: Supply a named human/hardware confirmation record (tester, procedure, result), or drop the claim.

## Runs (history, including superseded runs)

- FAIL_TO_PASS test with agent patch: python tests/runtests.py expressions_case.tests.CaseExpressionTests.test_annotate_with_full_when -v 0 | exit 0 | start 2026-11-11T05:14:36.752297+00:00 | sha256:081dd9ccbd551b443ee5554359cea03703e65789a783ae5e179e076d4e790cd3 | citable | source allowlist_recorder
- expressions_case module, PASS_TO_PASS tests with agent patch: python tests/runtests.py expressions_case -v 0 | exit 0 | start 2026-11-11T05:14:37.607693+00:00 | sha256:c3c5f341bb3d0653a3c57f95eed374cd7514923781914cc43742b0f24e0be33b | citable | source allowlist_recorder
