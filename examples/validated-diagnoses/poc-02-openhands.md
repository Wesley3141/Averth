# POC 02: OpenHands lane

Status: READY TO SEND as a proof draft, with the limits below. Do not
send until the parent picks a named recipient and channel. No one was
contacted, nothing was sent, nothing was posted, no private data was used.

## Workflow analyzed

OpenHands agent trajectories, model gpt-4o-2024-08-06, maxiter 30, from
the public SWE-Gym dataset SWE-Gym/OpenHands-Sampled-Trajectories.

Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories

Dataset facts from the source card: 6,055 trajectories in train.raw,
fields include instance_id, run_id, resolved (bool), messages, and
test_result with a resolved verdict. All rows in the sample below share
run_id prefix gpt-4o-2024-08-06_maxiter_30_N_v2.1-no-hint-train-t04-run_1.

## Sample and conversion, reproducible

Sample rule, applied in dataset order to shard 0, with no outcome
filtering: the first 20 trajectories with at least 8 assistant turns.
Result: 5 resolved, 15 unresolved, 25 percent resolved. This sample is
NOT representative of the full dataset: shard 0 overall is 192 resolved
out of 2,019 rows, 9.5 percent, because the turn-count filter selects
longer runs. Do not generalize the sample rate to all OpenHands runs.

Converter: ~/workspace/poc-02-openhands/convert.py, mechanical only,
mirroring averth/validation-traces/mini-swe-agent-s3/convert.py.

Mapping: case_id is instance_id; one model event per assistant turn,
model gpt-4o-2024-08-06, provider openai; one tool event per assistant
turn, name is the first tool-call function name; one retry event before
the next model call when a tool observation matches "[Command finished
with exit code N]" with N not 0, reason "exit code N"; end event success
is the row's resolved flag, the dataset's real test verdict.

Token and price limits, stated plainly: the dataset records no per-call
token counts, no cache counts, and no billed dollar costs. Input tokens
are chars of all preceding message text (content plus tool-call
arguments) divided by 4, output tokens are chars of the assistant turn
divided by 4, exactly as in the mini-SWE-agent converter. Averth has no
price-table entry for openai:gpt-4o-2024-08-06, so it costed model spend
at the documented fallback estimate, 1.00 dollar per 1M input tokens and
3.00 dollars per 1M output tokens, and flagged the full 2.81 dollars of
model spend as estimated. Tool spend, 0.80 dollars, uses built-in
per-call estimates. Every dollar below is an ESTIMATE, not a bill, not
a recorded cost, and not a saving.

Reproduction command, run from ~/workspace/averth:

python3 -c "import sys; sys.path.insert(0,'.'); from averth.cli import main; main(['trace','/home/hatch/workspace/poc-02-openhands/events.jsonl','--format','jsonl','--html','/home/hatch/workspace/poc-02-openhands/report.html','--agent','openhands-gpt4o'])"

Exit code 0. Converted events: 842 lines, 20 cases.
Full Averth HTML report: ~/workspace/poc-02-openhands/report.html

## Numbers, from the Averth run, all estimated

Attempts: 20
Accepted outcomes (resolved): 5, 25.0 percent
Failed attempts: 15, 75.0 percent
Total estimated cost: 3.61 dollars
Measured (tokens x vendor prices): 0 dollars
Vendor-supplied (billed): 0.00 dollars
Estimated (fallback prices): 3.61 dollars
Failed runs, estimated: 2.86 dollars, 79 percent of estimated spend,
for zero accepted outcomes
Resolved runs, estimated: 0.75 dollars
Fully loaded cost per accepted outcome, estimated view: 0.72 dollars
Model and API, terminal path: 0.04 dollars per success
Retry path: 0.52 dollars per success
Tool calls: 0.16 dollars per success
Human review: 0.00 dollars, no human minutes in the data
Retries, conservative bash-exit-code rule only: 22
Top retry reasons: exit code 1, 19 times; exit code 2, 1 time;
exit code 100, 1 time; exit code 255, 1 time
Retry path spend: 2.59 dollars, overlapping lens, not additive with
failed-run spend
Yield: 8 percent of tokens on the terminal path, 92 percent burned on
retries and failed runs
Context compounding: 13.4x input growth, first step to last step
Heavy tail, estimated per attempt: p50 0.18 dollars, p95 0.34 dollars,
max 0.34 dollars; top 5 percent consumed 10 percent of budget

Costliest attempt, estimated: iterative__dvc-9391, unresolved, 0.34
dollars, 25 tool calls, 1 recorded retry. Second: getmoto__moto-6470,
unresolved, 0.33 dollars, 28 tool calls, 0 recorded retries.

What this does NOT show: no billed saving, no recorded cost reduction,
and no claim that any failed run was avoidable. Acceptance labels are
present, so estimated cost per accepted outcome is defined, but it is
still an estimate built on chars-divided-by-4 tokens and fallback
prices. The retry count is a lower bound: editor errors and test
failures without a bash exit code are not counted.

## One change worth testing

Test a stop rule for long failed grinds, not a retry cap alone. The
costliest run had only 1 recorded retry, and several failed runs had
none, so a retry cap would miss them. Proposed test, on the same cases
with the same acceptance tests: terminate or escalate an attempt once
it crosses the p95 estimated cost, 0.34 dollars, or 30 turns with no
passing test signal, and separately fix the exit code 1 validation
step that produced 19 of 22 recorded retries. Then re-measure cost per
accepted outcome and acceptance rate on the same cases. If lower
estimated spend comes with worse acceptance, that is not an
improvement, and the test should say so.

## Contact draft, 100 words including sign-off, proof first

Hi OpenHands team, I ran 20 of your public OpenHands trajectories through Averth, GPT-4o, maxiter 30. Five resolved. The other 15 took 79 percent of estimated spend for zero accepted outcomes, and only 8 percent of tokens were on a terminal path. The costliest run, iterative__dvc-9391, was unresolved at about 0.34 dollars estimated, with 25 tool calls and only 1 recorded retry, so a retry cap alone would miss it. The top retry reason was exit code 1, 19 times. Want the same receipt on a run you pick, on your machine, redacted, with the adviser off?

Wesley
Averth
https://getaverth.com

Notes on the draft: recipient is the OpenHands team, not a named
person, because no individual contact was verified. The parent must
pick a channel and a named recipient before sending. The draft states
estimated figures only, names a real instance, and does not claim a
saving, a billed cost, or a production result.

## Self-review

Every number above traces to the Averth CLI run on the converted
sample, or to the per-case totals computed from the same events file,
which sum to 3.61 dollars and match the Averth total. No private data
was used: only the public HuggingFace dataset, and no prompt or
completion text is reproduced in this file. No savings claim is made.
No format claim is made beyond the converter rules above. The two
known weaknesses are stated in the file: token and price estimates,
not recorded usage or bills, and a sample selected by turn count that
is not representative of the full 6,055-trajectory dataset.
