# POC new-61: OpenHands evaluation, Gemini 1.5 Pro — PASS (clean run, fallback-priced)

## Verdict: PASS as a clean-run diagnosis only

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft. No change was applied or measured, no saving is
claimed, and no individual recipient is verified.

## Source used

- Dataset: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
- Run folder: `outputs/SWE-bench_Lite-test/CodeActAgent/gemini-1.5-pro-002_maxiter_30_N_v1.9-no-hint-eval-24sep/`
- Model, from metadata.json: `gemini/gemini-1.5-pro-002`, CodeActAgent,
  SWE-bench Lite, maxiter 30, run 2024-10-02, temperature 0.0,
  top_p 0.5, max_message_chars 10000, caching_prompt false.
  metadata.json also leaves input_cost_per_token and
  output_cost_per_token null, which matters for the reconciliation
  below: the run's own cost log has no stated rate basis in its
  metadata.
- Full run, from report.json: 300 instances, 300 submitted,
  254 completed, 40 resolved (13.3%), 214 unresolved,
  46 empty-patch, 0 error.
- Files used: output.jsonl (streamed, not stored whole; the 20
  selected rows are stored verbatim in raw_sample.jsonl),
  report.json, metadata.json. The v2.2 Gemini 1.5 run in the same
  dataset was NOT used: it has no report.json, and this lane's
  brief requires end labels from report.json.

## Selection, mechanical, no outcome filtering

First 20 rows in file order with at least 8 agent actions
(run / run_ipython / finish). 199 of 300 rows meet the 8-call
threshold, so the sample is the first 20 of those, not a search
for successes.

Sample, 20 attempts: sympy__sympy-20212, django__django-13028,
django__django-11999, django__django-13401, sympy__sympy-22005,
matplotlib__matplotlib-26011, django__django-10924,
django__django-11049, matplotlib__matplotlib-23299,
pydata__xarray-4248, django__django-12908, sympy__sympy-13773,
sphinx-doc__sphinx-8627, sympy__sympy-13437,
pytest-dev__pytest-8906, django__django-12856,
django__django-16400, pylint-dev__pylint-7114,
scikit-learn__scikit-learn-13241, matplotlib__matplotlib-23913.
Repos: django 8, sympy 4, matplotlib 3, and one each of pydata,
sphinx-doc, pytest-dev, pylint-dev, scikit-learn.
Resolved in sample: 2 of 20 (10.0%): sympy__sympy-22005 and
django__django-11049. 10% is not a general Gemini 1.5 rate; it
is 20 rows in file order against a 13.3% full-run rate.

## Overlap honesty

Instance overlap is NOT zero, and is not claimed. These are the
same 300 SWE-bench Lite instances other OpenHands evaluation
lanes used, in the same file order, so overlap is expected.
Trajectories are distinct (different model, different run folder,
different histories), but instance ids repeat: 12 of 20 also
appear in the poc-new-47 (GPT-4o-mini) sample, 2 of 20 in the
poc-new-16 (Claude 3.5) sample, and 2 of 20 in the poc-new-38
(GPT-4o) sample. Do not present this lane as instance-disjoint
from those lanes.

## Conversion, mechanical (same rules as lanes 38 and 47)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-61/`
(convert.py, events.jsonl, sample.json, scan.json,
raw_sample.jsonl, report.json, metadata.json,
averth-output.txt, report.html).

- One row = one attempt, case_id = instance_id, asserted
  distinct in the sample (20 distinct ids).
- History steps flattened in order. For each agent action, one
  model event and one tool event (name = action).
- input_tokens = (cumulative characters of all prior flat-event
  text) // 4, where text = message for user/agent events and
  content (full observation) for observation events. This is the
  same cumulative-history convention as the first-batch SWE
  converters, not a per-turn prompt count.
- output_tokens = (thought + command/code/outputs text) // 4
  for that action: run -> thought + command; run_ipython ->
  thought + code; finish -> thought + outputs.
- Tokens are NOT recorded in these v1.9 files, so all tokens are
  chars/4 estimates, same limitation as lanes 38 and 47.
- retry event before the next model call when an observation
  carries exit_code != 0 (extras.exit_code, or message
  "executed with exit code N"). A LOWER BOUND: IPython
  observations carry no exit code, so failures without a bash
  exit code are not counted.
- end event: success = row report.resolved. Verified exactly
  against report.json resolved_ids over ALL 300 streamed rows:
  row-resolved count 40, report.json resolved count 40,
  0 mismatches. Rows with report == {} are unresolved.

## Model mapping and price-table gap

- Model key used, exactly as named in metadata.json:
  provider `google`, model `gemini-1.5-pro-002`.
- Price table v6 has NO Gemini 1.5 entry (only
  google:gemini-3-pro at $2.00/$12.00 and google:gemini-3-flash
  at $0.50/$3.00 per 1M). Averth therefore used its documented
  $1.00/$3.00 per 1M fallback and flagged the model unpriced.
- No price was invented and no mapping to gemini-3-pro was
  made: that would be a different model at a different price.
  Until a Gemini 1.5 Pro 002 price is verified from Google's
  own pricing pages and added to the table with a regression
  test, never quote this lane's total without its fallback
  basis. This is the same class of gap lanes 38 (gpt-4o-2024-05-13)
  and 47 (gpt-4o-mini-2024-07-18) flagged for dated snapshots.

## Averth run

- Repo: ~/workspace/averth, commit fafab07, price table v6.
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl --html report.html --agent "OpenHands Gemini 1.5 Pro" --anomaly`
- CLI exit code: 0, confirmed on a direct rerun (identical
  totals; only the header agent name differs without --agent).
  No crash, no error, no "Measured" label.
- Events: 993 total (462 model, 462 tool, 49 retry, 20 end).
  Tool mix: run_ipython 380, run 70, finish 12. Only 12 finish
  tool events, not 20: 7 of 20 attempts hit the 30-action
  maxiter cap and were truncated with no finish action.
- Attempts: 20. Autonomous completions (dataset resolved
  labels): 2 (10.0%). Failed: 18.
- Total cost: $5.16.
- Cost basis, as printed by Averth itself: ESTIMATED.
  Priced (tokens x vendor prices, token provenance unverified)
  $0.00; vendor-supplied (billed) $0.00; estimated
  (fallback prices) $5.16. Model spend $4.23 is entirely
  fallback; tool spend $0.92 is entirely built-in per-call
  estimates (462 calls x $0.002).
- Independent check: model input tokens 4,156,852 and output
  tokens 25,141 at fallback $1.00/$3.00 per 1M give
  $4.1569 + $0.0754 = $4.2323, matching Averth's $4.23.
  Tool math: 462 x $0.002 = $0.924, matching $0.92.
- Cost per successful outcome, fully loaded: $2.58
  (terminal $0.15, retry path $1.97, tool $0.46, human $0.00
  at the assumed $70.20/hr rate). Quote the fully loaded
  figure, never the $0.15 terminal-model line alone.
- Failed runs: $4.50 (87% of spend, zero outcomes).
  Retry path: $3.94 model+retry spend on discarded paths
  (overlapping lens, not additive). Retries: 49, all exit
  codes: exit code 1: 28, exit code 2: 14, exit code -1: 5,
  exit code 127: 2.
- Five layers: context compounding 44.6x first-to-last step,
  context tax $0.00 (see anomaly below); yield 7% of tokens
  on the terminal path (93% burned on retries and failed
  runs); heavy tail p50 $0.21 / p95 $0.50 / max $0.59 per
  attempt (costliest: matplotlib__matplotlib-26011, $0.59,
  flagged runaway-shaped, retry path $0.53, context 61.9x);
  top 5% consumed 12% of budget; model mix 100%
  google:gemini-1.5-pro-002 at $4.23.

## Anomaly check required by the lane

- $0 context tax despite 44.6x growth: PRESENT, and it is
  the known fallback-pricing quirk (the fallback path records
  in_price 0.0, and the context-tax loop skips steps with no
  input price). Do not quote it as "context was free."
- No "-$0" priced-bucket artifact: the priced bucket prints
  $0, a real zero (nothing was vendor-priced), not -$0.
- Report inconsistency, flagged not hidden: the text output's
  top finding says retry loops burned $4.19, while the waste
  lens says retry path $3.94. The $0.25 gap is unexplained
  in the report; this file quotes the waste-lens $3.94.
  Lane 38 flagged the same class of gap ($0.52 there).
- Output tokens are severely undercounted by construction:
  25,141 total across 462 calls, about 54 per call, because
  v1.9 stores thought + command/code, not full model
  responses (same limitation lane 47 noted for GPT-4o-mini).
  Model spend is therefore input-dominated and understates
  any real bill even before the fallback price is considered.
- Source cost-count mismatch, negligible: the sample's source
  metrics.costs total 463 entries against 462 model events.
  The single extra cost is in sphinx-doc__sphinx-8627
  (14 costs, 13 model calls; that row also has one agent
  message event that is not an action). It moves nothing
  material and is not a model call Averth missed by design;
  it is noted so the 462 vs 463 difference is not mistaken
  for a conversion error elsewhere.

## Reconciliation vs source cost (the honest comparison)

- The 20 sample rows' own metrics.accumulated_cost sums to
  $27.83. Averth's total is $5.16, about 5.4x lower.
  Decomposition: Averth model $4.23 vs source $27.83, plus
  $0.92 of built-in tool defaults that the source log does
  not include in the same way.
- Do not present either figure as a bill. The source figure
  is OpenHands' own cost log at proxy rates whose basis is
  not stated in metadata.json (input_cost_per_token and
  output_cost_per_token are both null), and Averth's figure
  is fallback $1.00/$3.00 applied to chars/4 estimated tokens
  with output tokens undercounted as above. The gap is
  therefore expected, not a bug in either arithmetic: both
  totals check out from their own inputs, and neither is a
  vendor invoice. A priced rerun at a verified Gemini 1.5
  Pro 002 list price would move Averth's model spend up, not
  down, and would still not reconcile to $27.83 without the
  source's token accounting.

## Limits that must travel with this number

- 2 of 20 resolved is NOT a general solve rate. It is 20
  rows in file order (7 truncated at the maxiter cap) under
  one model and one scaffold, against a 13.3% full-run rate.
- Tokens are chars/4 estimates, not recorded usage; dollars
  are fallback estimates plus tool defaults, not a bill.
- The native Gemini 1.5 lane in the v2.2 run (maxiter 100,
  non-fncall) was not run here and remains a separate lane;
  do not merge its numbers with this v1.9 run.
- PASS criteria met: real per-step input (20 full
  trajectories, not aggregates), attempts 20, CLI exit 0,
  totals reported, honest ESTIMATED cost basis, anomalies
  disclosed. Clean-run diagnosis only.

## Wave 5 rerun (2026-10-23, Averth price table v7, uncommitted wave-5 code)

Reran the filed events.jsonl unchanged under wave 5. Total is
unchanged at $5.16, all ESTIMATED at fallback, because
google:gemini-1.5-pro-002 could NOT be verified from Google's own
models page (absent from the previous-models list) and was left
unpriced; third-party $1.25/$5.00 figures were not used. Attempts 20,
resolved 2/20, retries 49, context 44.6x, context tax now n/a instead
of $0.00. Still ESTIMATED (chars/4, output undercounted). New report:
hidden_files/poc-new-61/averth-output-v7.txt.