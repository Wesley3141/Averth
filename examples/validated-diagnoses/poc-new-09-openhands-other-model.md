# POC NEW 09: OpenHands, other model — clean-run test, second batch

Status: PASS (clean run). No one contacted, nothing sent, nothing posted,
no private data used. This is a clean-run test only, not a value pitch:
does the upgraded Averth run by itself cleanly on a new public workflow,
or does it fail?

## Upgraded Averth used

- Repo: ~/workspace/averth, commit fd84a0f
  ("Fix POC failures: Langfuse cached tokens, Claude importer, OTel
  recovered rule, price table v5, Measured label").
  Note: the commit message says price table v5, but the code in the
  checkout reports PRICE_TABLE_VERSION = 6 and the CLI header prints
  "Price table: v6 (verified 2026-10-22, 1 days old)". The numbers below
  come from the v6 code as run, not from the commit message.
- Importers present include claude.py, langfuse.py (cached handling),
  otel.py, langsmith.py, jsonl.py. This lane uses the jsonl importer
  only; the Claude, Langfuse, and OTel fixes are not exercised here.

## Workflow and source — different from the first batch

- Workflow: OpenHands v0.54.0 agent trajectories on real GitHub issues.
- Model: Qwen/Qwen3-Coder-480B-A35B-Instruct (per the dataset card).
  This is NOT the first batch: the first batch used
  SWE-Gym/OpenHands-Sampled-Trajectories, GPT-4o, maxiter 30, 20 cases.
  This lane uses a different dataset, a different model, and different
  instances. Instance overlap with the first-batch sample, checked
  directly: zero instances in common.
- Source: https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories
- Dataset card facts: 67,074 trajectories, issues from nebius/SWE-rebench,
  fields trajectory_id, instance_id, repo, trajectory, tools, model_patch,
  exit_status, resolved (int 0/1).
- File used: trajectories.parquet, 2,079,503,354 bytes, 67,074 rows,
  17 row groups, downloaded via huggingface_hub (unauthenticated, slow).

## Sample and conversion, reproducible

- Selection rule, applied in file order, no outcome filtering:
  first 20 trajectories with at least 8 assistant turns. All of the
  first 20 rows qualify (they are long trajectories, 91 to 185 messages
  in the first three rows checked).
- Result: 13 resolved, 7 unresolved, 65.0 percent resolved in this
  sample. This is NOT claimed as representative: the full dataset
  reports 32,161 successful of 67,074 trajectories (about 48 percent).
  Do not generalize the sample rate.
- All 20 exit_status values are "submit".
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/convert.py
  (mechanical only, mirroring the first-batch OpenHands converter).
  Mapping: case_id = instance_id (asserted distinct, 20/20);
  one model event per assistant turn, model
  "Qwen/Qwen3-Coder-480B-A35B-Instruct", provider omitted so Averth
  guesses "unknown" and prices at the documented fallback estimate
  ($1.00/$3.00 per 1M tokens), because Qwen has no price-table entry
  in this checkout; one tool event per assistant turn, name = first
  tool-call function name, or "unknown"; one retry event before the
  next model call when a tool observation matches
  "[Command finished with exit code N]" with N != 0, reason
  "exit code N" (a LOWER BOUND: editor errors and test failures
  without a bash exit code are not counted); end event success =
  bool(row["resolved"]), the dataset's test verdict.
- Token limits, stated plainly: the dataset records no per-call token
  counts, no cache counts, and no billed dollar costs. Input tokens
  are chars of all preceding message text (content plus tool-call
  arguments) divided by 4; output tokens are chars of the assistant
  turn divided by 4. Every dollar below is an ESTIMATE, not a bill,
  not a recorded cost, and not a saving.
- Converted events: 2,531 lines — 1,211 model, 1,211 tool, 89 retry,
  20 end. Tool names: execute_bash 631, str_replace_editor 494,
  think 53, finish 20, task_tracker 13.
  Model tokens (estimated): input 37,038,961, output 236,747.

## Averth run

Command, run from ~/workspace/averth:

python3 -c "import sys; sys.path.insert(0,'.'); from averth.cli import main; main(['trace','/home/hatch/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/events.jsonl','--format','jsonl','--html','/home/hatch/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/report.html','--agent','openhands-qwen3-coder-480b'])"

- CLI exit code: 0. No error, no traceback, no unknown-event rejection,
  no cached-tokens violation. HTML report written to
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/report.html.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run, all estimated

- Attempts: 20
- Autonomous completions (resolved): 13 (65.0 percent)
- Failed attempts: 7 (35.0 percent)
- Retries: 89 — exit code 1: 76, exit code 2: 6, exit code 4: 6,
  exit code 139: 1. These match an independent recount of the events
  file exactly.
- Total cost: $40.17 estimated
  - Model spend: $37.75 estimated (100 percent of model spend),
    model key unknown:Qwen/Qwen3-Coder-480B-A35B-Instruct, flagged in
    the report as unpriced / fallback.
  - Tool spend: $2.42, built-in per-call estimates.
  - Priced (tokens x vendor prices): $0 in substance (printed as -$0,
    see anomaly note below).
  - Vendor-supplied (billed): $0.00.
  - Estimated (fallback prices): $40.17.
- Fully loaded cost per successful outcome, estimated: $3.09
  (model terminal $0.20, retry path $2.71, tool calls $0.19,
  human review $0.00).
- Failed runs: $19.30 (48 percent of spend, zero outcomes).
- Retry path: $35.20 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 7 percent of tokens on the terminal path.
- Context compounding: 13.7x input growth first-to-last step;
  context tax $0.00 (0 percent of model spend) — see anomaly note.
- Heavy tail, estimated per attempt: p50 $1.72, p95 $4.28,
  max $4.95; top 5 percent consumed 12 percent of budget.
- Human escalations: 0. Reopened: 0.

## Anomalies noted (do not hide them; none blocked the run)

1. Priced bucket prints "-$0" in the text report, instead of "$0".
   Cosmetic, but it is not a clean label.
2. Context tax is $0.00 despite 13.7x context growth. The same
   zero-context-tax quirk was seen in the first batch. With all model
   spend on fallback pricing, the context-tax computation yields
   nothing, so the growth story has no dollar attached in this run.
3. Commit message says price table v5; the code reports v6.
   Minor version-label mismatch, recorded here, not a run failure.
4. Sample resolved rate (65 percent) is above the full-dataset rate
   (about 48 percent). First-20-in-file-order is reproducible, but
   it is not a representative sample, and no claim is made that it is.

## What this does NOT prove

- No billed cost, no recorded tokens, no cache data: every dollar is
  a chars/4 estimate at fallback prices. This run proves Averth can
  ingest and report a new OpenHands/Qwen trajectory set by itself,
  with exit 0 and a complete report. It does not prove an operator
  would use it repeatedly, act on a finding, or pay for it.
- No change was tested here. The retry finding (exit code 1, 76 of 89)
  is a report output, not a tested fix, and no saving is claimed.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/events.jsonl (2,531 lines)
- Sample list: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/sample.json
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-09/report.html
