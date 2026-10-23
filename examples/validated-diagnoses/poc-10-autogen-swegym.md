# POC 10: SWE-Gym, Claude 3.5 Sonnet, OpenHands sampled runs

Lane: AutoGen or SWE-Gym. No real AutoGen trajectory dataset with
steps, tokens, and success labels was found in public search, only
documentation examples, so this POC uses the SWE-Gym lane, which the
task allows. The scaffold recorded in this data is OpenHands
CodeActAgent v2.1. This POC is about the SWE-Gym task set, not about
reusing another lane's scaffold dataset, and it uses a different run
and sample from the mini-SWE-agent POC.

Status: READY TO SEND, with the limits below. No contact has been made.
Research and run only. No private data was used. No message was sent
or posted.

## Workflow and source

Workflow: OpenHands CodeActAgent v2.1, model Claude 3.5 Sonnet
20241022, maxiter 50, running SWE-Gym task instances, one attempt per
instance, from the public SWE-Gym sampled trajectories.

Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories

Sample used: only rows with run_id
claude-3-5-sonnet-20241022_maxiter_50_N_v2.1-no-hint-run_1, from the
first parquet shard of that dataset. That run has 229 unique
instance_ids, one attempt each. The full dataset has 6,055 rows across
three shards, but this POC reports only the 229-row Claude run it
actually converted and ran. Do not present these numbers as the full
dataset.

Conversion: hidden working file
goals/agent-p-l-validation/hidden_files/poc10/convert.py, output
events.jsonl with 13,418 events. Rules, fixed and mechanical:
one model event per assistant message, model
claude-3-5-sonnet-20241022; one tool event per tool call, name only;
a retry event before the next model call when the preceding tool
observation contains the literal string "Traceback", a genuinely
recorded failure signal; end event success equals the row "resolved"
bool, which matches test_result.report.resolved in the source.
No prompts, completions, or record content are kept in the events file.

Token method, and why the dollars are estimates: the source records
no per-call token usage and no per-instance billed cost. Input tokens
are characters of accumulated context divided by 4, output tokens are
characters of the assistant turn divided by 4, the same mechanical
method as the mini-SWE-agent converter in the Averth repo. No cache
counts exist in this data, so no cache discount is applied. Tool spend
is Averth's default per-call estimate, not a measured tool bill.

## Reproduction command

From ~/workspace/averth, with the converted events file at
goals/agent-p-l-validation/hidden_files/poc10/events.jsonl:

python3 -c "import sys; sys.path.insert(0, '.'); from averth.cli import main; main(['trace', 'events.jsonl', '--format', 'jsonl'])"

The CLI run used for this POC exited 0. Price table v2, verified
2026-10-02. Model price used: Claude 3.5 Sonnet 20241022 at $3 per 1M
input tokens and $15 per 1M output tokens, published list price in
averth/pricing.py.

## Numbers, from the run Averth actually did

Attempts: 229
Accepted outcomes, resolved: 67, 29.3 percent
Failed attempts: 162, 70.7 percent
Model events: 6,405 assistant messages, 6,264 with tool calls
Tool calls: 6,264 total, str_replace_editor 3,300, execute_bash 2,782,
finish 182
Retries, traceback in previous tool observation: 520, across 229 attempts
Total cost, metered list-price estimate: $464.06
Model spend, metered list-price estimate: $451.53
Tool spend, default estimate, not measured: $12.53
Cost per successful outcome, metered list-price estimate: $6.93
Model cost per successful outcome, terminal: $0.45
Retry path cost per successful outcome: $6.29
Tool cost per successful outcome: $0.19
Failed runs, metered list-price estimate: $380.80, 82 percent of total
spend, zero outcomes
Retry path spend, overlapping lens, not additive: $421.30
Context compounding: 41.7 times input growth, first to last step
Context tax, metered list-price estimate: $419.04, 93 percent of
model spend
Yield: 7 percent of tokens on the terminal path, 93 percent burned on
retries and failed runs
Heavy tail, per attempt, metered list-price estimate: p50 $1.33,
p95 $5.51, max $9.02, top 5 percent consumed 17 percent of budget
Human review: $0.00, none measured, the CLI default $70.20 per hour
loaded rate is an assumption, not a measured input

Recorded costs: NONE in this source. There is no per-instance billed
cost field in this dataset, unlike the mini-SWE-agent leaderboard
entry. Every dollar above is therefore a list-price estimate from
estimated tokens, not a bill and not recorded spend. Do not quote
$464.06 or $6.93 as what anyone was charged.

Cost per success: COMPUTABLE on the metered view, because resolved
labels exist, but it is an estimate for the reasons above, not a
measured bill. No savings claim is made. No change has been applied
or measured yet.

Retry bucket check, computed from the converted events, model cost
only: 0 retries, 81 attempts, 25.9 percent resolved, mean model cost
$1.83; 1 to 2 retries, 80 attempts, 37.5 percent resolved, $1.56;
3 to 5 retries, 40 attempts, 25.0 percent resolved, $1.98; 6 or more
retries, 28 attempts, 21.4 percent resolved, $3.54. The retry count
alone does not cleanly predict failure, so the change below is aimed
at context, not at a simple retry cap.

Costliest runs, model cost only, all unresolved, all 50 model calls:
pandas-dev__pandas-56849, $8.92, 4 retries; getmoto__moto-5478,
$8.79, 0 retries; conan-io__conan-12397, $8.06, 20 retries;
python__mypy-11966, $7.50, 2 retries; python__mypy-11945, $7.02,
0 retries. Together, $40.29 of model cost for zero outcomes. The
costliest runs are not all retry-heavy, which is why a retry cap
alone is not the finding.

## One change worth testing

Compact or summarize carried state between steps, then rerun the
same 229 cases and compare resolved rate alongside cost per resolved
case. Reason: context tax is $419.04, 93 percent of model spend, and
input grows 41.7 times from first to last step, while yield is only
7 percent. This is a test to run, not a saving to claim. If lower
spend comes with a lower resolved rate, that is not an improvement,
and the test must say so.

## Limits, stated plainly

Tokens are characters divided by 4, not recorded usage, and the full
tool observations are carried in the accumulated context in this
conversion, which may overstate billed context if the real harness
truncates history. No cache discount is applied. Tool costs are
estimates. The sample is one Claude run, one scaffold, one maxiter
setting, from one parquet shard, not the full SWE-Gym dataset and not
a production deployment. The contact draft below is addressed to the
SWE-Gym team as a group, with no individual name or email invented.

## Contact draft, under 120 words, no em dashes, finding first

Your Claude 3.5 Sonnet run on SWE-Gym resolved 67 of 229 cases. Failed runs took 82 percent of metered spend, and context grew 41.7 times from first to last step. The five costliest runs each used 50 calls and resolved none. One change worth testing is compacting carried context between steps, then rerunning the same cases and checking resolved rate alongside cost per resolved case. We ran your public trajectories through Averth and can share the full receipt and reproduction command. Want us to run the same receipt on a newer run, on your machine, redacted?

Wesley
Averth
https://getaverth.com
