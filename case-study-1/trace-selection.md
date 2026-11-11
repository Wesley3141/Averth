# Trace selection: Averth case study 1

## Decision

**Chosen trace: mini-SWE-agent run `django__django-15930` (Django, SWE-bench Verified).**

- Agent: mini-SWE-agent v1.0.0 (bash-only harness), model `claude-sonnet-4-20250514`.
- Task: Django issue, `Case()` crashes with `~Q(pk__in=[])`. The generated SQL is
  `CASE WHEN THEN true ...`, a syntax error. The fix must make an empty `When`
  condition behave as always true.
- Outcome: RESOLVED. The agent submitted a 4-line patch to
  `django/db/models/expressions.py`. Official evaluation: FAIL_TO_PASS 1/1,
  PASS_TO_PASS 88/88.
- Recorded cost: $0.3205 (real recorded cost from the leaderboard entry),
  35 API calls, 72 messages (1 system, 35 assistant, 36 user).
- Why this one: a real run with a testable outcome in a repo that runs on the
  machine we have (Python 3.12, SQLite), a real recorded dollar cost to compare
  the meter against, and a small readable patch. The target test fails without
  the patch and passes with it, verified live here (see below).

## Public links (all fetched without login, key, or signup)

- Trajectory (raw `.traj.json`):
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/django__django-15930/django__django-15930.traj.json
- Leaderboard entry (metadata, aggregate cost, resolve rate):
  https://github.com/m0at/experiments/tree/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514
- Official evaluation records for this instance (patch, per-test report, full
  test output):
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/report.json
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/test_output.txt
  https://s3.amazonaws.com/swe-bench-submissions/bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/logs/django__django-15930/patch.diff
- Task definition (base commit, test patch, FAIL_TO_PASS / PASS_TO_PASS lists):
  Hugging Face dataset `princeton-nlp/SWE-bench_Verified`, instance
  `django__django-15930`, repo `django/django`, base commit
  `63884829acd207404f2a5c3cc1d6b4cd0a822b70` (2022-08-09).
- Subject repo: https://github.com/django/django

## Verification done before choosing (all live, 2026-11-11)

1. Base commit checked out (shallow fetch of the exact SHA), Django 4.2.dev
   installed editable into a clean venv with `asgiref` and `sqlparse`.
2. Test patch from SWE-bench Verified applied cleanly (adds
   `test_annotate_with_full_when` to `tests/expressions_case/tests.py`).
3. Target test WITHOUT the agent patch: FAILED, `OperationalError: near
   "THEN": syntax error`, exactly the reported bug. The check discriminates.
4. Agent submission applied (see quirk below). Target test WITH the patch:
   PASSED (`Ran 1 test ... OK`).
5. Full `expressions_case` module WITH the patch: 89 tests ran, OK (skipped=1).
   That covers the 1 FAIL_TO_PASS test and all 88 PASS_TO_PASS tests.
6. Working tree after both patches: exactly 2 files, 14 insertions, nothing
   else. The agent submission touches only `django/db/models/expressions.py`.
7. Official evaluation report confirms the same outcome independently:
   `resolved: true`, FAIL_TO_PASS success 1/1, PASS_TO_PASS success 88/88.
8. Recorded cost cross-check: `per_instance_details.json` for this instance
   says cost $0.32052915, api_calls 35, resolved true. The trajectory
   `info.model_stats` says the same (`instance_cost: 0.32052914999999993`,
   `api_calls: 35`). Two independent records agree.

## Quirks found (stated plainly, not hidden)

1. The recorded agent submission is missing its final newline. Strict
   `git apply` rejects it as "corrupt patch at line 15". GNU patch applies it
   with fuzz 1. Appending one newline makes `git apply` accept it cleanly,
   and the applied diff is byte-identical to the recorded submission apart
   from that newline. The S3 `patch.diff` saved by the evaluation is
   byte-identical to the trajectory submission (same 747 bytes, same missing
   newline), so this is a property of the recorded artifact, not a transcription
   error on our side. Reproduction step: append one newline before applying.
2. The SWE-bench test patch applies cleanly. (An earlier read of the failure
   output misattributed the "corrupt patch" error to the test patch; it belongs
   to the submission patch. Corrected here.)
3. The agent patch hardcodes `"1=1"` as the always-true condition. The gold
   patch instead compiles `Value(True)`. Both pass the recorded tests. The
   case study states this difference and does not claim the agent patch equals
   the gold patch.
4. The verdict is SQLite-scoped. The official evaluation and this reproduction
   both ran the Django tests on SQLite in memory. No second database backend
   was run. That is a stated limitation, not a hidden one.
5. Token counts in the converted events are estimates (characters/4), as
   documented in the source trace directory. The metered dollars are therefore
   ESTIMATED. The recorded $0.3205 is the real recorded cost from the
   leaderboard entry and is the number to compare against.

## Why not the other candidates

- `psf__requests-1921` (mini-SWE-agent, Claude Sonnet 4, $0.1515 recorded,
  17 calls, UNRESOLVED): the most interesting story found. The agent fixed all
  6 FAIL_TO_PASS tests, but the official verdict is unresolved because 2
  PASS_TO_PASS tests failed on live httpbin.org 502 Bad Gateway responses and
  a third failed on a pytest API incompatibility (`pytest.raises` with a
  string), none caused by the agent patch. It is the runner-up and a strong
  candidate for case study 2. It was NOT chosen because the 2014 requests code
  cannot import on Python 3.12 (`collections.MutableMapping`,
  `collections.Callable`, vendored urllib3 implicit relative imports), so V0
  executed mode cannot run its tests here, and its tests depend on live
  httpbin.org, which is not reproducible. The 502 finding is verified from the
  official `test_output.txt` and `report.json`, saved in this directory.
- Live-SWE-agent `django__django-10097` (Devstral 2, 103 calls, UNRESOLVED):
  a failed run with a large effort, but the recorded cost is $0.00 because the
  model ran on the OpenRouter free tier, which weakens the cost story, and the
  Django setup would be the same work as the chosen trace for a worse meter
  comparison. Scout report: `scout-swebench.md`.
- SWE-agent demo `marshmallow-code__marshmallow-1867`: cleanest format, but
  `model_stats` is all zeros and the file carries no test verdict.
- SWE-smith trajectories (Claude 3.7 Sonnet, MIT): no single-trace file URL,
  no cost or token fields, 3.2 GB corpus.
- SWE-Gym OpenHands trajectories (GPT-4o): no license stated on the dataset
  card, so not used for a published case study until confirmed.
- thomwolf `am-session-sharing-design` (Claude Code, Opus 5) and ultralazr
  `claude-code-traces` (Claude Code, multi-model): real sessions with per-message
  token counts, good meter material, but neither has a testable repo outcome
  (no FAIL_TO_PASS tests, no patch to verify), so V0 cannot judge them. The
  Claude Code JSONL `input_tokens` field is a streaming placeholder on most
  lines, so any dollar figure needs a stated counting method. Scout report:
  `scout-session-logs.md`. Both are candidates for a future meter-only
  case study.
- Codex rollouts (cfahlgren1/codex-sessions, GPT-5): research-only runs, no
  code written, no tests. Useful as a sidebar only.
- Langfuse demo traces: require a free account signup. Ruled out.
- The rehearsal fixture: synthetic, explicitly excluded by the task brief.
- Devya materials: private, explicitly excluded by the task brief.

## What the case study will show

- V0 executed mode (Tier 2) judging human-written checks against runs it
  records itself: the FAIL_TO_PASS test and the PASS_TO_PASS module run, plus
  external checks for human acceptance and a second database backend (both
  expected EXTERNAL-UNVERIFIABLE, stated as limits).
- The Averth meter on the single-case trace events: ESTIMATED dollars, retry
  share, context growth, yield, compared against the RECORDED $0.3205.
- Exact reproduction steps (links plus commands) so a reader can rerun it.
- One public trace only, stated plainly. No invented customers, deployments,
  fundraise, or validation claims.
