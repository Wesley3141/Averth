# POC 03: Original SWE-agent public trajectories

Lane: original SWE-agent, distinct from mini-SWE-agent, SWE-smith,
OpenHands, LangGraph, CrewAI, Claude Code, OpenAI Agents SDK, Langfuse,
OpenTelemetry, and AutoGen lanes used by sibling agents.

Status: READY TO SEND as a proof-first contact draft, with the limits
below attached to any send. Research and run only. No one was contacted,
nothing was sent, nothing was posted, no private data was used.

## Workflow analyzed

SWE-agent, the original scaffold from the SWE-agent project, running
software engineering issues from real repositories. The trajectories
analyzed here come from the Nebius collection of SWE-agent runs on
SWE-bench Extra instances, using SWE-agent as the scaffold and a
fine-tuned open-weight model as the action generator.

Source: https://huggingface.co/datasets/nebius/SWE-agent-trajectories
License: CC-BY-4.0, per the dataset card. Dataset size: 80,036
trajectories, 13,389 resolved, 66,647 not resolved, across the full
dataset. This POC uses only the sample defined below, not the full set.

Sample definition, exact: first 100 rows in file order of
data/train-00000-of-00012.parquet, row group 0, in the dataset above.
This is NOT a random sample of the 80,036 rows. It covers 7 distinct
issues, with multiple attempts per issue:
- Melevir__cognitive_complexity-15: 45 attempts, 17 resolved
- Azure__azure-functions-python-worker-890: 15 attempts, 0 resolved
- PyCQA__pyflakes-761: 12 attempts, 0 resolved
- AnalogJ__lexicon-336: 11 attempts, 0 resolved
- ReproNim__reproman-518: 7 attempts, 0 resolved
- RDFLib__rdflib-1130: 5 attempts, 0 resolved
- ShawHahnLab__igseq-2: 5 attempts, 0 resolved

Models in sample: swe-agent-llama-70b (95 attempts),
swe-agent-llama-8b (5 attempts). Exit statuses in sample: submitted 74,
submitted (exit_context) 24, exit_context 2. So 26 of 100 attempts
ended in a context exit of some form.

## Conversion, mechanical and documented

Script: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-03-swe-agent/convert.py
Input: train-00000-of-00012.parquet, row group 0, first 100 rows
Output: events.jsonl, 5,152 events

Rules:
- case_id is instance_id plus row index, so repeated attempts on the
  same issue stay separate attempts instead of merging into one case.
- System entry: system_prompt length counts toward context chars.
- User entry: text length counts toward context chars. If the text
  contains "syntax error" or starts with "Traceback", the next ai turn
  is preceded by a retry event with that reason. These are recorded
  failure signals in the observation text, not invented labels.
- Ai entry: one model event and one tool event named "bash" per turn.
  SWE-agent turns in these traces carry one tool action per turn by
  construction; the tool cost is Averth's default estimate and is
  flagged as such in the report, not a measured tool bill.
- Token counts are NOT recorded in this dataset. input_tokens is
  chars of all preceding message text divided by 4, output_tokens is
  chars of this ai turn divided by 4, the same mechanical estimate the
  mini-SWE-agent converter in this repo uses. These are estimates.
- Model names swe-agent-llama-70b and swe-agent-llama-8b are NOT in
  Averth's price table, so Averth prices them at its documented
  fallback estimate ($1.00 per 1M input tokens, $3.00 per 1M output
  tokens) and flags them as unpriced models. Dollar totals below are
  ESTIMATES, never a vendor bill.
- End event: success is the dataset "target" field, the dataset's own
  solved or unsolved label for that trajectory. Acceptance labels
  therefore exist for this sample, so cost per successful outcome can
  be computed, but only on the estimated dollar basis above.

## Reproduction command

From ~/workspace/averth, with the converted file at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-03-swe-agent/events.jsonl:

python3 -c "import sys; sys.path.insert(0, '.'); from averth.cli import main; main(['trace', 'events.jsonl', '--format', 'jsonl'])"

Averth CLI exit code on this run: 0. Full output is saved at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-03-swe-agent/averth-output.txt
and the HTML report at
~/workspace/goals/agent-p-l-validation/hidden_files/poc-03-swe-agent/report.html

## Results, from the Averth run

- Attempts: 100
- Accepted outcomes (dataset target true): 17, or 17.0%
- Failed attempts: 83, or 83.0%
- Critical skew, read before quoting 17%: all 17 resolved attempts
  come from Melevir__cognitive_complexity-15. The other 6 issues in
  this sample resolved 0 of 55 attempts. Do not present 17% as
  SWE-agent's general solve rate.
- Retries: 254 total. Top reasons: syntax error 161 times, traceback
  93 times.
- Yield: 5% of tokens on the terminal path, 95% burned on retries and
  failed runs, per Averth.
- Context growth: 6.5x input growth first step to last step, per
  Averth. The report's context tax line reads $0.00 for this run, which
  looks like a quirk of the unpriced-model fallback, so this POC does
  NOT quote a context tax dollar figure. It quotes only the 6.5x
  growth multiple.
- Heavy tail, estimated basis: p50 $0.16, p95 $0.94, max $3.10 per
  attempt, top 5% of attempts consumed 25% of estimated budget.
- Longest run in sample, by ai turns: AnalogJ__lexicon-336#6, 155 ai
  turns, unresolved, 6 retries in the converted events, estimated
  model cost $2.79 before tool estimates. This is a token-count
  ranking from the converted events, not a claim that it is the
  $3.10 max-cost attempt in the Averth report.
- Failed-run token share, from converted events: 88.6% of estimated
  input plus output tokens sit in failed attempts, consistent with
  Averth's 88% failed-run spend share below.

## Costs, recorded first, metered second

- Recorded costs in this dataset: NONE. This dataset publishes no
  per-instance dollar cost, so there is no recorded bill to reconcile
  against. Any dollar figure below is an Averth estimate, not a bill.
- Metered total, Averth estimated fallback basis: $30.67
  - Model spend, estimated: $25.87, all flagged as estimated, no
    vendor price for unknown:swe-agent-llama-70b or
    unknown:swe-agent-llama-8b
  - Tool spend, built-in per-call estimates for bash: $4.80
  - Measured tokens times vendor prices: $0.00
  - Vendor-supplied billed costs: $0.00
- Failed runs, estimated basis: $26.97, or 88% of estimated spend,
  for zero accepted outcomes.
- Retry path, estimated basis: $27.11 in Averth's top finding, 88% of
  estimated spend. Averth's waste accounting lists $24.55 of
  model plus retry spend on discarded paths. These are overlapping
  lenses on the same spend, not additive partitions. Do not sum them.
- Cost per successful outcome, estimated basis only: $1.80 fully
  loaded, made of $0.08 terminal model, $1.44 retry path, $0.28 tool
  calls, $0.00 human review at an assumed $70.20 per hour loaded,
  which was not measured. Because the dollar basis is estimated, this
  $1.80 is an estimated cost per resolved attempt in this sample,
  not a measured bill and not a savings figure.

## One change worth testing

Validate edit syntax before the next model turn, and stop an attempt
after 3 consecutive syntax-error retries. Then rerun the same issues
and compare cost per resolved issue and resolution rate before and
after, on the same acceptance labels. This is a test proposal, not a
savings claim. No savings number is claimed in this POC, because the
dollar basis is estimated and the intervention has not been run.

Why this change, from the data: syntax errors are the single largest
retry reason in the sample (161 of 254 retries), and 26 of 100
attempts ended in a context exit, so long retry loops also feed
context exhaustion. A syntax check is cheap, local, and testable on
the same public issues.

## Limits and what would break this POC

- Sample is first 100 rows in file order, 7 issues, heavily skewed
  by one issue with 45 attempts. Do not generalize rates to the
  full 80,036-row dataset or to current SWE-agent runs.
- No recorded dollar costs exist in this dataset, so every dollar
  figure is an Averth fallback estimate. Real Llama hosting costs
  could be higher or lower. Do not quote $30.67 or $1.80 as a bill.
- Token counts are chars divided by 4 estimates, not recorded usage.
- Tool costs are Averth defaults for bash, not measured tool bills.
- The context tax dollar line in the Averth report reads $0.00 and
  is not quoted here, pending a pricing-table explanation.
- The contact draft below is addressed to the SWE-agent team as a
  scaffold audience, not to a named individual, because no private
  contact data was used and no individual was identified from this
  public dataset.

## Contact draft, under 120 words, no em dashes

Hi SWE-agent team, I ran your public SWE-agent trajectories from nebius/SWE-agent-trajectories through Averth, first 100 rows in file order. 17 of 100 attempts resolved, and all 17 came from one issue. Failed attempts took 88% of estimated spend. 254 retries appeared, 161 after syntax errors, and 26 of 100 attempts ended in a context exit. The costliest pattern is not model choice, it is edit syntax retries plus context exhaustion. One change worth testing: validate edit syntax before the next turn and stop after 3 consecutive syntax retries, then compare cost per resolved issue before and after. Want me to run the same receipt on a current run set, on your machine, redacted?

Wesley
Averth
https://getaverth.com

## Self-review

- Every number above traces to the Averth run on events.jsonl or to
  counts taken directly from the first 100 parquet rows. No number
  was invented.
- No private data was used. Source is a public CC-BY-4.0 dataset.
- No savings claim is made. The one change is a test proposal with
  a before and after comparison, not a promised reduction.
- No unverified format claim is made. The bash tool assumption, the
  chars divided by 4 token estimate, and the fallback pricing are
  all stated as assumptions or estimates in the conversion section.
- No cost per success claim is made without an acceptance label:
  success here is the dataset target field, and the dollar basis is
  explicitly estimated, not recorded.
