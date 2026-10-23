# POC 01: SWE-smith trajectories, SWE-agent runs

Lane: SWE-smith public trajectories. Research and run only. No one was
contacted, nothing was sent, nothing was posted, no private data was used.

## Workflow and source

Workflow: SWE-agent harness runs against SWE-smith task instances, real
GitHub repos with synthetic bug-injection tasks, evaluated by whether the
final patch resolves the task.
Dataset: SWE-bench/SWE-smith-trajectories, split `tool`, HuggingFace.
Source URL: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
Paper: SWE-smith, arXiv:2504.21798.
License: MIT, per the dataset card as recorded in SOURCES.md.
Local source: ~/workspace/averth/validation-traces/swe-smith-trajectories/
Files used: events.jsonl (16 cases, 936 lines), FINDINGS.md, SOURCES.md,
convert.py. This is NOT the mini-SWE-agent set already used for the first
teardown. No intrusion was performed and no system was probed. The
security-bot philosophy here means only: find a workflow already public,
analyze it yourself, and show the finding and the fix first.

## Reproduction command

From ~/workspace/averth, using the CLI as shipped:

python3 -c "import sys; sys.path.insert(0, '.'); from averth.cli import main; main(['trace', 'validation-traces/swe-smith-trajectories/events.jsonl', '--format', 'jsonl'])"

Exit code: 0. Run date for this POC: Oct 22, 2026, evening CDT.
Price table in the run: v2, verified 2026-10-02.

## Numbers, fresh run Oct 22

Attempts: 16.
Accepted outcomes (dataset `resolved` verdict, a real pass/fail label):
8, 50.0 percent.
Failed attempts: 8, 50.0 percent.
Retries: 36, every one labeled `tool error` in the converted events.
Human escalations: 0. Reopened: 0.

Recorded, vendor-supplied costs: $0.00. This dataset records no per-call
token usage and no billed costs. Every dollar below is an estimate, not a
bill, and must not be quoted as one.

Metered, estimated costs, list prices, tokens estimated at characters/4
per SOURCES.md:
Total estimated cost: $24.79.
Measured (tokens x vendor prices): $23.91.
Estimated (fallback prices, mainly tool calls): $0.88.
Tool spend warning from the CLI: $0.88 uses built-in per-call estimates
for bash, str_replace_editor, and submit. Measure tool costs explicitly
before quoting actual spend.
Model mix, estimated: claude-3-7-sonnet-20250219 $18.11 (76 percent of
model spend), claude-3-5-sonnet-20241022 $5.80 (24 percent).

Cost per successful outcome, estimated only, not billed: $3.10 fully
loaded. Breakdown in the CLI output: model and API terminal $0.36, retry
path $2.63, tool calls $0.11, human review $0.00 at an assumed $70.20 per
hour loaded, which was not measured. Acceptance labels exist here
(`resolved`), so an estimated cost per accepted outcome can be computed.
It is still an estimate, because the underlying tokens are estimates and
no cache data is recorded. Do not present $3.10 as a billed cost.

Failed-run share, estimated: $13.06 of $24.79, 53 percent, for zero
accepted outcomes.
Retry-path spend, estimated, overlapping lens not additive: $21.03 of
model plus retry spend on discarded paths. Top finding in the CLI output:
retry loops burned $21.54, 87 percent of spend, with yield at 11 percent.
Top retry reason: tool error, 36 times.
Context compounding: 22.0x input growth first to last step. Context tax
$20.42, 85 percent of model spend.
Yield, fresh run: 11 percent of tokens on the terminal path, 89 percent
burned on retries and failed runs.
Heavy tail, fresh run: p50 $1.15, p95 $3.26, max $5.48 per attempt.
Costliest run consumed 22 percent of budget.

Standout case, from the converted events:
Project-MONAI__MONAI.a09c1f08.pr_6147.02e4bqrh, success true, 14 retries,
60 tool calls, 1,727,856 estimated input tokens, 11,975 estimated output
tokens, on claude-3-5-sonnet-20241022. This is the longest successful
grind in the set, and it is why a blanket dollar cap is the wrong fix:
a $1.00 per-attempt cap, suggested in the older FINDINGS.md, would also
stop this successful run, which is the $5.48 max case in the CLI output.

## Discrepancy to disclose, not hide

The older FINDINGS.md in the same directory lists yield at 26 percent,
p50 $1.24, and p95 $5.48. The fresh Oct 22 CLI run lists yield at 11
percent, p50 $1.15, and p95 $3.26, with the same total $24.79, the same
$3.10 estimated cost per success, the same $13.06 failed-run share, and
the same $5.48 max. Use the fresh run numbers in any contact. Do not
quote the older yield, p50, or p95 figures alongside them without
explaining they came from an earlier run.

## One change worth testing, and what it is not

Test this, on the same cases, judging acceptance alongside cost:
after a run hits its third tool error in a row, pause, compact or
summarize the carried context, and continue only if the next planned
step changes. Otherwise stop the attempt. Then compare acceptance rate
and estimated cost per accepted outcome before and after, on the same
cases.

This is not a savings claim. No saving is claimed here, because the
costs are estimates, the tokens are estimated, cache data is missing,
and the change has not been run yet. A blanket call-count cap is also
not recommended: the longest successful run took 14 retries and 60 tool
calls, so a simple retry or call cap would cut winners as well as
losers.

## Limits

1. Token counts are mechanical estimates, characters/4, per SOURCES.md.
   The dataset records no per-call usage.
2. No billed or recorded costs exist in this dataset. All dollars are
   estimated list-price figures. Reconcile against an invoice before
   calling any figure actual spend.
3. Tool calls carry no latency or per-call cost in the source. Tool
   spend is the library default estimate.
4. The retry heuristic flags only observably failed tool calls. Silent
   failures, wrong but clean command output, are missed, and it has no
   access to exit codes.
5. Waste figures are overlapping lenses on the same spend, not additive
   partitions. Do not sum failed-run spend and retry-path spend.
6. 16 trajectories is a small sample. This is a POC finding about this
   public set, not a claim about SWE-agent in general.
7. Contact target is not a verified person. The dataset is published by
   the SWE-bench and SWE-agent teams, but no individual recipient was
   verified in this lane. The parent agent must pick a verified
   recipient before any contact, and must not send this draft to a
   guessed name or address.

## Contact draft, under 120 words, not sent

Your public SWE-smith trajectories show something worth a look: 8 of 16
SWE-agent runs failed, and those failed runs were 53 percent of
estimated spend, for zero accepted outcomes. The longest successful run
took 14 retries and 60 tool calls. We ran the set through Averth, our
local cost per finished task meter, and the top retry reason was tool
error, 36 times. One change worth testing is stopping after a run
enters a tool-error tail, then compacting context before continuing,
and measuring acceptance alongside cost on the same cases. Happy to run
it on one workflow you pick, on your machine, redacted.

Wesley
Averth
https://getaverth.com

Word count check for the draft body above, excluding sign-off: 103 words.
No em dashes. The only link is https://getaverth.com.

## Self-review

Every number above traces to either the fresh Oct 22 CLI run in this
lane or to a direct count of validation-traces/swe-smith-trajectories/events.jsonl.
No private data was used. No savings claim was made. No billed cost
was claimed, because recorded costs are $0.00 in this dataset. No
format claim beyond what was run: the CLI was run with --format jsonl
on the converted events file. No contact was made. The one open item
is recipient verification: do not send the draft until a real, verified
recipient at the SWE-agent or SWE-smith team is chosen.

## Verdict

POC ready to use, not ready to send. The analysis, numbers, limits, and
draft are complete and honest. Sending is blocked on one step only:
picking and verifying a real recipient. Once that is done, the draft
above can go as written.
