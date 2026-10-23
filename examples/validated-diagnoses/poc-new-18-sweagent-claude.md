# POC New 18: SWE-agent, Claude 3.5 Sonnet trajectories

Lane: SWE-agent, Claude model, distinct from the GPT-4o lanes.
Verdict: PASS (clean-run diagnosis test only, not a value POC, not a billed-cost proof).
No one contacted, nothing sent, nothing posted, no private data used.

## Workflow and source

- Workflow: SWE-agent harness runs against SWE-smith task instances
  (real GitHub repos; these 20 are all PR-mirror tasks, instance ids
  ending in `pr_*`), evaluated by whether the final patch resolves the task.
- Dataset: SWE-bench/SWE-smith-trajectories, split `tool`, HuggingFace.
- Source URL: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
- Paper: SWE-smith, arXiv:2504.21798.
- Model: claude-3-5-sonnet-20241022 only, all 20 attempts.
- Sampling: consecutive rows at datasets-server offsets 1000-1019
  (one 20-row block, all Claude 3.5), fetched verbatim via the public
  datasets-server rows API, the same method as POC-01's fetch.py.
  No cherry-picking by outcome: the block was taken whole, before
  counting resolved cases.
- Disjointness: 0 traj_ids overlap POC-01's 16 SWE-smith trajectories
  (verified programmatically). Same dataset family as POC-01, but a
  disjoint instance set, a single model (3.5 only, vs POC-01's 14x 3.7
  plus 2x 3.5), and all PR-mirror tasks. It is not a re-run of POC-01
  and not a GPT-4o lane.

## Conversion (mechanical, no per-record editing)

Same fixed rules as POC-01's convert.py, copied to
`poc-new-18-work/convert.py`:

- case_id = row `traj_id`; one model event per assistant turn,
  model name copied from the row.
- One tool event per tool call (structured tool_calls, or
  `<function=NAME>` tags, or `bash` when an action exists with no
  tool call).
- A retry event before the next model call when the preceding tool
  observation matches the failure heuristic only: Python traceback,
  a unittest/pytest FAILED/ERROR line, or "command not found".
  Observations only; the task prompt is never scanned.
- End event: success = row `resolved`, the dataset's real pass/fail
  verdict for the run.

Raw rows (verbatim): `poc-new-18-work/raw/` (20 files).
Converted events: `poc-new-18-work/events.jsonl` (872 events).

## Token honesty (read this before quoting any dollar)

This dataset records NO per-call token usage and NO billed costs.
Input tokens are a mechanical estimate (characters of all preceding
message text / 4) and output tokens are characters of the turn / 4,
exactly as in POC-01. So:

- The CLI's "Priced" bucket ($28.45) is vendor list prices applied
  to ESTIMATED tokens, with token provenance explicitly unverified.
- The overall COST BASIS printed by Averth is ESTIMATED.
- $29.25 is NOT a bill, NOT recorded spend, and must not be quoted
  as one. Reconcile against an invoice before calling any figure
  actual spend.
- Tool spend ($0.80) is entirely the library's built-in per-call
  estimates (bash, str_replace_editor, submit), not measured costs.

What IS real here: per-step text, per-step tool calls, the retry
structure derived from real tool observations, and the `resolved`
acceptance labels. The cost shape (retry share, yield, context
growth) reflects real trace structure; the dollar scale is estimated.

## Averth run

- Averth: ~/workspace/averth, commit 071d0e1, price table v6
  (verified 2026-10-22). Claude 3.5 Sonnet priced at $3.00 input /
  $15.00 output per 1M tokens via the anthropic: key (bare dataset
  name mapped by guess_provider); no fallback pricing on model spend.
- Command (from ~/workspace/averth):
  `.venv/bin/python -m averth.cli trace <work>/events.jsonl
  --format jsonl --html <work>/report.html --anomaly`
- CLI exit code: 0. No crash, no dropped cases, no unpriced model,
  no "Measured" label. Full output: `poc-new-18-work/cli-output.txt`,
  HTML: `poc-new-18-work/report.html`.

## Numbers (estimated dollars, real labels)

- Attempts: 20. Accepted outcomes (dataset `resolved`): 5 (25.0%).
  Failed attempts: 15 (75.0%).
- Resolved cases: getmoto__moto pr_8342, iterative__dvc pr_7360,
  pydicom__pydicom pr_1938, pallets__click pr_2555,
  facebookresearch__hydra pr_2290 (full traj_ids in the work dir).
- Model events: 402. Tool events: 400. Retries: 50, all labelled
  `tool error` by the observation heuristic.
- Total cost (estimated): $29.25.
  Priced (list prices x estimated tokens, provenance unverified):
  $28.45, all anthropic:claude-3-5-sonnet-20241022.
  Vendor-supplied (billed): $0.00.
  Estimated (fallback, tool defaults): $0.80.
- Cost per successful outcome (estimated, fully loaded): $5.85
  (terminal model $0.19, retry path $5.50, tool calls $0.16,
  human review $0.00 at the assumed $70.20/hr loaded rate).
- Failed-run share: $25.68 (88% of spend, zero outcomes).
- Retry-path spend: $27.51 on discarded paths (overlapping lens,
  not additive with failed runs). Retry loops: $28.00, 96% of spend.
- Yield: 3% of tokens on the terminal path.
- Context compounding: 43.0x input growth first to last step;
  context tax $21.27 (75% of model spend). This growth is computed
  from the cumulative estimated input tokens, so it inherits the
  chars/4 estimation caveat.
- Heavy tail: p50 $0.44, p95 $9.58, max $9.68 per attempt;
  top 5% consumed 33% of budget.
- Messages per trajectory: min 13, median 31, max 141.

## Anomalies noted (not hidden)

1. Yield of 3% is far below POC-01's 11%, and the retry share
   (96%) is higher. Part of this is real (15 of 20 failed, 50
   tool-error retries), and part is definitional: Averth counts
   only the terminal path as yield, so long failed runs with
   repeated tool errors collapse the ratio. Do not quote 3% as
   "3% of the model's work was useful" without that definition.
2. Cost anomaly flagged by Averth itself (--anomaly):
   pylint-dev__astroid pr_2158 cost $9.68 (22x p50, just above
   p95 $9.58), driven by retry path ($9.56), 8 retries, context
   grew 2.7x, and the run failed. It is the max-cost case, not a
   success, so a p95-style cap would have cut a loser here, but
   that is one case, not a cap recommendation on its own.
3. The retry heuristic only flags observably failed tool calls
   (traceback / FAILED / ERROR / command not found). Silent
   failures (wrong but clean output) are missed, so 50 is a
   lower bound on bad steps, not a complete failure count.
4. Tool calls carry no latency or per-call cost in the source;
   the $0.80 is a default, and it is 100% of the tool spend.

## Why PASS, and what it is not

PASS because the task's criteria are met: real per-step input
(20 trajectories, 402 model turns, real tool observations),
attempts >= 10, CLI exit 0, totals produced, honest cost basis
(ESTIMATED, $0 billed, provenance unverified), and anomalies
flagged rather than smoothed over. No aggregate was converted
into a fake trace, and no other workflow was substituted.

It is NOT a value POC: Averth did not fix anything, `averth advise`
was not run, and no before/after change was tested. It is NOT a
billed-cost receipt, because tokens are chars/4 estimates. For
outreach use, the honest line is the cost shape on a real
Claude 3.5 SWE-agent slice (25% resolved, 88% of estimated spend
on failed runs, 50 tool-error retries), with dollars labelled
estimated throughout.
