# POC NEW 15: OpenHands, DeepSeek model — clean-run test, batch 3

Status: PASS (clean run, with a disclosed fallback). No one contacted,
nothing sent, nothing posted, no private data used. This is a clean-run
diagnosis test only, not a value pitch and not an outreach claim: does
the upgraded Averth run by itself cleanly on a new public workflow, or
does it fail?

## Fallback disclosure first: this is DeepSeek-V4-Flash, NOT DeepSeek-V3

The brief asked for DeepSeek-V3 and allowed a fallback to another
DeepSeek OpenHands slice, reported as such. No public DeepSeek-V3
OpenHands trajectory dataset was found, and the brief's two example
sources do not contain DeepSeek-V3:

- HuggingFace search for "deepseek openhands", "DeepSeek-V3
  trajectories", and "openhands deepseek" returned no DeepSeek
  trajectory dataset.
- nebius/SWE-rebench-openhands-trajectories is Qwen3-Coder-480B, per
  its own README (batch 2 used it for the Qwen lane). It is not a
  DeepSeek slice.
- SWE-Gym/OpenHands-Sampled-Trajectories run_ids in the cached files
  are GPT-4o and Claude only, no DeepSeek.
- The Skywork-SWE and SWE-Dev papers describe DeepSeek-V3 rollouts
  with OpenHands, but no downloadable DeepSeek-V3 trajectory file
  was located; their published sets are success-filtered training
  trajectories or papers, not a V3 run export.

Fallback used, and labelled as such throughout: nvidia/Open-SWE-Traces,
config v1.1, OpenHands split, DeepSeek-V4-Flash-0731 slice. Do not
quote this file as a DeepSeek-V3 result.

## Upgraded Averth used

- Repo: ~/workspace/averth, commit 071d0e1 ("Fix wave 3: Claude dedupe
  max, outcome unknown, Haiku dated alias, zero-token guard").
- Price table v6, verified 2026-10-22. `averth pricing` exits 0, 18
  models, 8 tools. DeepSeek has no price-table entry in v6, so every
  model dollar below is a fallback ESTIMATE, not a vendor price.
- Full suite run during this lane: 378 passed, 1 skipped.
- This lane uses the jsonl importer only; the wave-3 Claude, outcome,
  and zero-token fixes are not exercised here.

## Workflow and source — different from batches 1 and 2

- Workflow: OpenHands agent trajectories on real GitHub issues
  (Scale-SWE tasks), teacher model DeepSeek-V4-Flash-0731,
  enable_thinking=True, reasoning_effort=max, per the rows themselves.
- Source: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
- File used: data/openhands/deepseek_v4_flash_0731/scale-swe/
  train-00000-of-00011.parquet (2500 rows, 185 MB). Config v1.1,
  split openhands. Dataset card: CC BY 4.0.
- Distinct from batch 1 (SWE-Gym OpenHands, GPT-4o) and batch 2
  (nebius SWE-rebench OpenHands, Qwen3-Coder-480B): different dataset,
  different model, different instances. Instance ids in this sample
  (e.g. pre-commit_identify_pr63) are Scale-SWE ids, not the
  SWE-rebench ids of batch 2.

## Sample and conversion, reproducible

- Selection rule, applied in file order, no outcome filtering:
  first 20 trajectories with at least 8 assistant turns.
- Result: 13 resolved, 7 unresolved, 65.0 percent resolved in this
  sample. This is NOT claimed as representative of the full slice
  (first 200 rows of the file are 120 resolved / 80 unresolved, 60
  percent). Do not generalize the sample rate.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/convert.py
  (mechanical only, mirroring the batch-2 OpenHands converter).
  Mapping: case_id = instance_id (asserted distinct, 20/20);
  one model event per assistant turn, model
  "DeepSeek-V4-Flash-0731", provider omitted so Averth guesses
  "unknown" and prices at the documented fallback estimate
  ($1.00/$3.00 per 1M tokens); one tool event per assistant turn,
  name = first tool-call function name, or "unknown"; one retry
  event before the next model call when a tool observation matches
  "[Command finished with exit code N]" with N != 0, reason
  "exit code N" (a LOWER BOUND: editor errors and test failures
  without a bash exit code are not counted); end event success =
  bool(row["resolved"]), the dataset's test verdict (int 0/1).
- Token limits, stated plainly: the dataset records no per-call
  token counts, no cache counts, and no billed dollar costs. Input
  tokens are chars of all preceding message text (content plus
  reasoning_content plus tool-call arguments) divided by 4; output
  tokens are chars of the assistant turn (content plus
  reasoning_content plus its tool-call arguments) divided by 4.
  Reasoning content is model output, so it is counted in output
  tokens and in later context, like any other generated text. About
  72 percent of output tokens in this sample are reasoning_content
  (recomputed without reasoning: ~102,772 output tokens, versus
  370,128 with reasoning; the small gap to the events-file total is
  the "\n" join between text parts). Every dollar below is an
  ESTIMATE, not a bill, not a recorded cost, and not a saving.
- Converted events: 1,469 lines — 708 model, 708 tool, 33 retry,
  20 end. Tool names: execute_bash 568, str_replace_editor 119,
  finish 20, think 1.
  Model tokens (estimated): input 24,212,011, output 370,128.

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl \
  --html <report.html> --agent openhands-deepseek-v4-flash-0731

- CLI exit code: 0. No error, no traceback, no unknown-event
  rejection, no cached-tokens violation. HTML report written.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run, all estimated

- Attempts: 20
- Autonomous completions (resolved): 13 (65.0 percent)
- Failed attempts: 7 (35.0 percent)
- Retries: 33 — exit code 1: 29, exit code 2: 3, exit code 130: 1.
  These match an independent recount of the events file exactly.
- Total cost: $26.74 estimated
  - Model spend: $25.32 estimated (100 percent of model spend),
    model key unknown:DeepSeek-V4-Flash-0731, flagged in the
    report as unpriced / fallback. Independent check: input
    24,212,011 x $1.00/1M = $24.21, output 370,128 x $3.00/1M =
    $1.11, sum $25.32. Matches.
  - Tool spend: $1.42, built-in per-call estimates (708 calls x
    $0.002 default = $1.42, matches).
  - Priced (tokens x vendor prices): $0.
  - Vendor-supplied (billed): $0.00.
  - Estimated (fallback prices): $26.74.
- Cost basis printed by Averth: ESTIMATED, with the warning "Do not
  quote this report as measured spend or as a bill."
- Fully loaded cost per successful outcome, estimated: $2.06
  (model terminal $0.29, retry path $1.65, tool calls $0.11,
  human review $0.00).
- Failed runs: $17.31 (65 percent of spend, zero outcomes).
- Retry path: $21.51 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 15 percent of tokens on the terminal path.
- Context compounding: 15.3x input growth first-to-last step;
  context tax $0.00 (0 percent of model spend) — see anomaly note.
- Heavy tail, estimated per attempt: p50 $0.35, p95 $4.98,
  max $7.35; top 5 percent consumed 27 percent of budget.
- Human escalations: 0. Reopened: 0.

## Anomalies noted (do not hide them; none blocked the run)

1. $0 context tax despite 15.3x context growth. The same
   zero-context-tax quirk was seen in batch 2. With all model spend
   on fallback pricing, the context-tax computation yields nothing,
   so the growth story has no dollar attached in this run.
2. The "-$0" priced-bucket artifact from batch 2 did NOT reproduce
   here: the text report prints Priced as "$0", not "-$0".
3. DeepSeek has no v6 price-table entry, so the headline $26.74 is
   entirely fallback-priced. A real DeepSeek list price (input,
   output, and cached, if published) would move every model dollar;
   do not compare $2.06 per success against priced-model lanes.
4. Sample resolved rate (65 percent) is above the first-200-row
   rate (60 percent). First-20-in-file-order is reproducible, but
   it is not a representative sample, and no claim is made that it
   is.
5. Reasoning dominates output: ~72 percent of output tokens are
   reasoning_content (thinking on, effort max). Any cost-reduction
   reading must say reasoning, not final answers, is most of the
   output spend in this slice.

## What this does NOT prove

- No billed cost, no recorded tokens, no cache data: every dollar is
  a chars/4 estimate at fallback prices. This run proves Averth can
  ingest and report a new OpenHands/DeepSeek trajectory set by
  itself, with exit 0 and a complete report. It does not prove an
  operator would use it repeatedly, act on a finding, or pay for it.
- No change was tested here. The retry finding (exit code 1, 29 of
  33) is a report output, not a tested fix, and no saving is claimed.
- This is not a DeepSeek-V3 result. Any rollup that counts it as
  V3 would be wrong; count it as DeepSeek-V4-Flash-0731, OpenHands,
  Scale-SWE.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/events.jsonl (1,469 lines)
- Sample list: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/sample.json
- Averth CLI output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/cli-output.txt
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-15/report.html
