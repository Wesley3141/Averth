# POC new-34: SWE-Gym pydantic — PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft.

## Verdict: PASS as a clean Averth run, NOT as a value POC

Averth ingested a real, public, per-step pydantic trajectory set and
produced a complete report with CLI exit 0, no crash, no unpriced model,
and no "Measured" label. No change was applied or measured, no saving is
claimed, and the dollars below are list prices applied to chars/4 token
estimates, never a bill. Cost per successful outcome is UNKNOWN
(Averth prints $0.00 with zero successes; read that as unknown, never
as "$0 per success").

## Source

- Dataset: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
- Files, in order: `data/train.raw-00000-of-00003.parquet` (2,019 rows),
  `train.raw-00001-of-00003.parquet` (2,018 rows, 0 pydantic),
  `train.raw-00002-of-00003.parquet` (2,018 rows). Total 6,055 rows.
- Pydantic rows in the whole dataset: 243, of which 163 have at least
  8 assistant turns. Overall pydantic resolved rate in the dataset is
  only 11 of 243 (4.5%), and 11 of 163 (6.7%) among the >=8-turn rows,
  so a low resolve rate in any small pydantic slice is not, by itself,
  evidence of cherry-picking.
- Scaffold: OpenHands CodeActAgent, model GPT-4o (see below).
  Distinct from batch-1 POC 2 (first 20 trajectories overall, all
  repos, GPT-4o) and from batch-1 POC 10 (SWE-Gym, Claude 3.5 Sonnet,
  229 cases): this lane is pydantic-only and GPT-4o, and the dedupe
  check below gives it zero exact attempt overlap with POC 2.

## Selection, mechanical, with a documented dedupe correction

Rule, applied in dataset order (shard 0, then 1, then 2, row order
within shard), with no outcome filtering:

1. instance_id starts with `pydantic__pydantic`;
2. at least 8 assistant turns (the same turn-count filter as POC 2);
3. first 20 rows meeting 1–2.

That rule, taken literally, fails the zero-overlap check: its first 20
rows include 2 attempts already used in batch-1 POC 2, namely
pydantic-5662 and pydantic-8525 under run
`gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1`
(see `~/workspace/poc-02-openhands/sample.json`). Those 2 exact
run+instance attempts are excluded, and the next 2 rows in file order
are taken instead. The exclusion is by prior use only, never by
resolved status: both excluded attempts are unresolved, and all 20
selected attempts are also unresolved, so the correction cannot have
manufactured the 0/20 result.

Final sample: 20 attempts, 16 distinct issues, 20 distinct case_ids
(case_id = run_id + "__" + instance_id, so the same issue under two
temperature runs counts as two distinct attempts, which it is).
Runs in the sample: 9 attempts under
`gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1` and
11 under `...-train-t03-run_1`. All 20 share model
gpt-4o-2024-08-06, so there is no model-mix ambiguity.

Issues (16): pydantic-9214, -6104, -8500, -8583, -8004, -6126, -6043,
-5706, -8793, -9066, -9134, -6283, -8567, -8316, -8525, -5662.
Full list with run_id, resolved flag, and message counts is in
`sample.json` under the work files.

## Conversion, mechanical (same rules as POC 2)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-34/`
(convert.py, events.jsonl, sample.json, scan.py, scan.json, scan.log,
cli_output.txt, report.html).

- One model event per assistant turn; input_tokens = chars of all
  preceding message text (content plus tool-call arguments) // 4;
  output_tokens = chars of this assistant turn (content plus its
  tool-call arguments) // 4.
- Token counts are NOT recorded in these traj files: the message
  objects carry only content / function_call / name / role /
  tool_call_id / tool_calls, no usage or token field. Every token
  figure below is therefore a chars/4 estimate, same limitation as
  batch 1. Averth's own banner says the same thing (see below).
- One tool event per assistant turn, name = first tool-call function
  name, or "unknown" if none. Tool mix: str_replace_editor 340,
  execute_bash 102, unknown 35, finish 5.
- Retry event before the next model call when a tool observation
  matches "[Command finished with exit code N]" with N != 0, reason
  "exit code N" (the POC 2 rule). This is a LOWER BOUND, and in this
  slice it binds hard: see the retry anomaly below.
- End event: success = row's resolved flag (the dataset's real test
  verdict).

Event counts, independently counted from events.jsonl: 984 events =
482 model + 482 tool + 20 end + 0 retry. No events were hand-edited.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6
  (verified 2026-10-22; `averth pricing` exits 0, 18 models, 8 tools).
- Command, from ~/workspace/averth:
  `.venv/bin/averth trace <events.jsonl> --format jsonl
  --html <report.html> --anomaly`
- CLI exit code: 0, no crash, no rejected events.
- Model key: openai:gpt-4o-2024-08-06 at $2.50 input / $10.00 output
  per 1M tokens in price table v6, with cached rate $1.25 per 1M
  (no cached tokens exist in this dataset, so the cached rate is
  unused here).

## Results

- Attempts: 20. Resolved (accepted): 0 (0.0%). Failed: 20.
- Total: **$15.31**.
- Cost basis as printed by Averth: **ESTIMATED** — "$0.96 of spend
  uses built-in tool estimates. Remaining priced dollars apply vendor
  list prices to trace-supplied token counts that Averth does not
  verify as recorded usage. Do not quote this report as measured
  spend or as a bill."
- Data quality by provenance (Averth's own buckets): Priced (tokens x
  vendor prices, token provenance unverified) $14.34; vendor-supplied
  (billed) $0.00; Estimated (fallback prices) $0.96, which is entirely
  the built-in tool estimates, not model fallback (the model is priced).
  Read the $14.34 as "list prices x estimated tokens", not as
  recorded usage, because the tokens are chars/4 estimates.
- Model spend: $14.34, 100% openai:gpt-4o-2024-08-06. Independently
  rechecked: 5,457,310 input tokens x $2.50 + 69,838 output tokens x
  $10.00 per 1M = $13.6433 + $0.6984 = $14.3417, matching Averth's
  $14.34 after rounding.
- Tool spend: $0.96, 100% built-in per-call estimates
  (execute_bash, finish, str_replace_editor, unknown) — flagged as
  estimates in the report itself, not measured tool costs.
- Failed runs: $15.31 (100% of spend, zero outcomes).
- Cost per successful outcome: UNKNOWN. Averth prints $0.00 for every
  component with zero successes; that is a vacuous print, not a price.
- Context compounding: 23.9x input growth first-to-last step;
  context tax $12.61 (88% of model spend).
- Yield ratio: 0% of tokens on a terminal path (100% burned on failed
  runs). This is definitional with zero successes, not a separate
  finding about pydantic.
- Heavy tail: p50 $0.72 / p95 $1.64 / max $2.52 per attempt;
  costliest run consumed 16% of budget. Costliest attempt:
  t03-run pydantic-8567 at $2.52 model spend ($2.46 retry-path
  driver per the anomaly flag; context grew 84.6x in that run),
  vs p50 $0.72. Averth's --anomaly flag also names it runaway-shaped
  at 4x p50.
- Model calls: 482 across 20 attempts (10–30 per attempt).

## Anomalies, not hidden

1. **Retries: 0 under the POC 2 rule, 82 under the traceback rule.**
   No tool observation in this slice matches the POC 2 exit-code
   pattern, so the converted events contain 0 retry events and
   Averth reports "Retries: 0". But the same tool observations do
   contain Python tracebacks: recounting with the batch-1 SWE-smith
   heuristic (traceback, FAILED/ERROR line, or "command not found"
   in a tool observation) gives 82 retries across 434 tool
   observations (per-attempt counts 0–16; 5 attempts have 0, the rest
   1–16). The 0 is therefore a rule artifact, not evidence that
   these runs never errored and retried. Any rollup quoting a retry
   count for this lane must state which rule produced it, and must
   not quote 0 as "no retries happened".
2. **Averth's "retry loops" wording with 0 retries.** The report's
   finding 2 says "Retry loops burned $14.34 (94% of spend)" and
   "Yield is 0%: 0 retries across 20 attempts" in the same breath.
   With 0 retry events, that $14.34 is failed-run spend, not retry
   spend; the retry-path lens overlaps the failed-run lens when
   every attempt fails. Do not quote "$14.34 burned on retry loops"
   for this lane.
3. **0/20 resolved is a run-grouped sample, not a pydantic rate.**
   The dataset orders rows by run, so this slice is two GPT-4o
   temperature runs (t04, t03) that each resolved 0 of their 20
   pydantic rows. The full-dataset pydantic rate is 11/243 (4.5%),
   so 0/20 is low but not inexplicable, and it must never be quoted
   as "pydantic tasks resolve 0% of the time" or as a GPT-4o rate.
   It is 20 attempts from two runs, 16 issues.
4. **Context tax with zero successes.** Averth prints context tax
   $12.61 (88% of model spend) even though no attempt succeeded.
   That tax is computed from input growth, not from a terminal
   path, so it describes where tokens went, not a cost that would
   have been saved by succeeding. Contrast batch-3 agent 13, where
   context tax printed $0.00 with zero successes only because that
   model was fallback-priced (in_price 0.0); here the model is
   priced, so the tax is non-zero. The two $0 / non-$0 prints are
   both artifacts of the tax definition, and neither should be
   quoted as "context was free" or "context cost $12.61 extra".
5. **No "-$0" priced-bucket artifact in this run** (priced bucket is
   $14.34, positive), and the zero-token guard did not trigger
   (5,527,148 total tokens). No "Measured" label appears anywhere
   in the CLI output; the report says ESTIMATED throughout.

## Limits that must travel with it

- Tokens are chars/4 estimates, not recorded usage; no cache counts,
  no bill, no recorded per-instance cost to reconcile against.
  Averth's $15.31 is a list-price estimate of the text in the
  trajectories, with full history accumulated and no truncation or
  cache discount (compare batch-3 agent 11, where the same method
  gave 7.5x the source's own recorded cost for django).
- Tool spend is entirely built-in defaults ($0.002 per call implied
  by $0.96 over 482 calls), not measured tool costs.
- Retry count depends on the rule chosen (0 vs 82, above); neither
  is a tool-log count.
- 16 distinct issues, 20 attempts, 2 runs, 1 model, 1 repo. Not a
  general pydantic, GPT-4o, or SWE-Gym rate.
- No tested change, no before/after, no operator, no bill: this is a
  clean-run diagnosis, not a value POC and not proof anyone would pay.

## Recipient status: none verified

No individual recipient is verified for this lane. The source is a
public dataset published by the SWE-Gym team as a group; no
individual name or email is claimed here, and none may be invented
for outreach. Do not send this POC to anyone on the basis of this
file alone.
