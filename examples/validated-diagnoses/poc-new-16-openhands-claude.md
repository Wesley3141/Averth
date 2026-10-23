# POC NEW-16: OpenHands, Claude-3.5-Sonnet — clean-run test, batch 3

Status: PASS (clean run). No one contacted, nothing sent, nothing posted,
no private data used. This is a clean-run diagnosis test only, not a value
pitch: does the upgraded Averth run by itself cleanly on a new public
workflow, or does it fail?

## Upgraded Averth used

- Repo: ~/workspace/averth, commit 071d0e1
  ("Fix wave 3: Claude dedupe max, outcome unknown, Haiku dated alias,
  zero-token guard"), price table v6 (verified 2026-10-22).
- This lane uses the jsonl importer only. It does not exercise the
  Claude importer, Langfuse cached handling, or OTel recovered rule.

## Workflow and source — distinct from the GPT-4o and Qwen lanes

- Workflow: OpenHands CodeActAgent on real GitHub issues (SWE-bench Lite).
- Model: anthropic/claude-3-5-sonnet-20241022, maxiter 100, OpenHands
  v2.1, run 2024-10-28 (metadata.json). This is NOT the first batch
  (SWE-Gym/OpenHands-Sampled-Trajectories, GPT-4o, maxiter 30, 20 cases)
  and NOT poc-new-09 (nebius/SWE-rebench, Qwen3-Coder-480B).
  Different dataset, different model, different run.
- Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  Folder: outputs/SWE-bench_Lite-test/CodeActAgent/
  claude-3-5-sonnet-20241022_maxiter_100_N_v2.1-no-hint/
  Files used: output.jsonl (147 MB, 300 instances), report.json,
  metadata.json.
- Full-run facts from report.json: 300 instances, 300 submitted,
  295 completed, 125 resolved (41.7%), 170 unresolved, 4 empty-patch,
  1 error instance. The sample below is NOT that rate; see the
  sample warning.
- Instance overlap with the poc-new-09 Qwen sample: 0 of 20
  (different benchmark families: SWE-bench Lite vs SWE-rebench).

## Sample and conversion, reproducible

- Selection rule, applied in file order, no outcome filtering:
  first 20 rows with at least 8 unique model calls. (One early row
  was skipped for having fewer than 8 calls; the rule, not the
  outcome, decided it.)
- Result: 11 resolved, 9 unresolved, 55.0% resolved in this sample.
  This is NOT claimed as representative: the full run is 41.7%
  resolved, and first-20-in-file-order is reproducible, not random.
  Do not generalize the sample rate.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/convert.py
  (mechanical only).
- Mapping, with the one structural fact that matters:
  each model call appears TWICE in the source history (an action
  event and an observation event carrying the identical
  model_response id). The converter keeps only the action event
  (action not None) and dedupes by model_response id, so no call
  is counted twice. The source's own metrics.costs list has the
  same duplication: each cost appears twice, and accumulated_cost
  equals the sum of the duplicated list (verified on the first
  row). Averth's total is therefore NOT expected to match the
  source's accumulated_cost, and the source figure is not used.
- Per call: one model event, one tool event (function_name, or
  "unknown" for finish calls). Model = claude-3-5-sonnet-20241022,
  provider = anthropic, so Averth prices at the v6 list price
  ($3.00 input / $15.00 output per 1M).
- Tokens are RECORDED usage from the source, not chars/4 estimates:
  input_tokens = usage.prompt_tokens,
  cached_input_tokens = usage.cache_read_input_tokens,
  output_tokens = usage.completion_tokens. Zero cached > input
  violations in the converted file.
- Retry event before the next model call when an observation
  message matches "executed with exit code N" with N != 0, reason
  "exit code N". A LOWER BOUND: editor errors and test failures
  without a bash exit code are not counted.
- End event success = report.resolved (the dataset's test verdict).
- Converted events: 748 lines — 343 model, 343 tool, 42 retry,
  20 end. Tool names: str_replace_editor 166, execute_bash 157,
  finish 20. Recorded tokens: input 6,777,330, cached-read
  6,273,522 (92.5% of input), output 75,186.

## Averth run

Command, run from ~/workspace/averth:

.venv/bin/python -m averth.cli trace
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/events.jsonl
  --format jsonl
  --html ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/report.html
  --agent openhands-claude-3-5-sonnet

- CLI exit code: 0. No error, no traceback, no unknown-event
  rejection, no cached-tokens violation.
- Verdict: PASS for a clean run.

## Numbers, from that Averth run

- Attempts: 20
- Autonomous completions (resolved): 11 (55.0%)
- Failed attempts: 9 (45.0%)
- Retries: 42, all exit code 1. These match an independent recount
  of the events file exactly.
- Total cost: $5.21
  - Priced (tokens x vendor prices): $4.52, all model spend,
    model key anthropic:claude-3-5-sonnet-20241022 (100% of model
    spend). Manual check: (6,777,330 - 6,273,522) x $3.00 +
    6,273,522 x $0.30 + 75,186 x $15.00, per 1M = $4.5213, matching
    Averth's $4.52.
  - Vendor-supplied (billed): $0.00. No billed cost is claimed.
  - Estimated (fallback prices): $0.69, all built-in per-call tool
    estimates (execute_bash, str_replace_editor, finish). The
    report header therefore reads COST BASIS: ESTIMATED, with the
    do-not-quote-as-a-bill warning. That is the honest label:
    model dollars are priced from recorded tokens, tool dollars
    are defaults.
- Fully loaded cost per successful outcome: $0.47
  (model terminal $0.08, retry path $0.33, tool calls $0.06,
  human review $0.00 at the $70.20/hr assumption, not measured).
- Failed runs: $2.50 (48% of spend, zero outcomes).
- Retry path: $3.66 model+retry spend on discarded paths
  (overlapping lens, not additive with failed-run spend).
- Yield: 11% of tokens on the terminal path.
- Context compounding: 12.8x input growth first-to-last step;
  context tax $2.96 (65% of model spend).
- Heavy tail per attempt: p50 $0.21, p95 $0.48, max $0.49;
  top 5% consumed 9% of budget.
- Prompt cache: 6,273,522 cached tokens, saving $16.94
  (priced at 10% of input rate; without caching the model spend
  would have been $16.94 higher). This is the run's real
  diagnosis story: a cache-heavy workload where caching, not
  model choice, is most of the margin.
- Human escalations: 0. Reopened: 0.

## Anomalies noted (do not hide them; none blocked the run)

1. Source accumulated_cost does not reconcile, and is not used.
   Sample sum of source accumulated_cost: $13.24, versus Averth
   total $5.21 ($4.52 model). Two reasons, both verified:
   (a) the source costs list double-counts every cost, so even
   halved it is $6.62, still above Averth's $4.52 model spend;
   (b) the source's per-call costs exceed token x v6 list-price
   cost (first row: source unique cost $0.0092 per call vs
   $0.0060 token-based even with cache-creation at 1.25x).
   The source figure is OpenHands' own cost log, not a vendor
   bill, and Averth recomputes from recorded tokens instead.
2. Cache-creation underprice (known, unadjusted): 502,962
   cache-creation tokens in the sample sit inside
   input-minus-cached and are priced by Averth at the full $3.00
   input rate, not Anthropic's 1.25x cache-write rate ($3.75).
   At 1.25x the model spend would be $0.38 higher ($4.90, not
   $4.52, about 8%). Averth's figure is therefore slightly low
   versus a vendor bill; it is not presented as billed.
3. Sample resolved rate (55.0%) is above the full-run rate
   (41.7%). First-20-in-file-order is reproducible but not a
   representative sample, and no claim is made that it is.
4. Retry count is a lower bound (exit-code rule only; see above).
5. Tool spend ($0.69) is built-in defaults, not measured tool
   costs, and is flagged as estimated in the report itself.

## What this does NOT prove

- No billed cost, no vendor invoice: model dollars are list
  prices applied to recorded tokens, tool dollars are defaults.
  This run proves Averth can ingest and report a new
  OpenHands/Claude-3.5-Sonnet trajectory set by itself, with
  exit 0, a complete report, and arithmetic that checks out
  against an independent recount. It does not prove an operator
  would use it repeatedly, act on a finding, or pay for it.
- No change was tested here. The retry finding (exit code 1,
  42 of 42) and the cache finding ($16.94 saved) are report
  outputs, not tested fixes, and no saving is claimed beyond
  the cache saving already realized in the source run.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/events.jsonl (748 lines)
- Sample list: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/sample.json
- Source files (local copies): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/output.jsonl, report.json, metadata.json
- Averth text output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/averth-output.txt
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-16/report.html
