# POC new-41: nvidia Open-SWE-Traces, AgnostiqHQ/covalent — clean-run test, batch 4

Status: PASS (clean run). No one contacted, nothing sent, nothing
posted, no private data used. This is a clean-run diagnosis test
only, not a value proof and not a sendable outreach piece: does the
upgraded Averth run by itself cleanly on a new public workflow, or
does it fail? No change was tested here, and no saving is claimed.

## Repo chosen, and why

Task rule: pick the first repo alphabetically in nvidia
Open-SWE-Traces v2.0 with at least 20 rows and a resolved label,
excluding the two Open-SWE-Traces lanes already used (poc-new-13
imbalanced-learn, poc-new-15 DeepSeek-V4-Flash-0731).

Method: column-pruned scan of all 15 shards of the v2.0 sweagent
split (repo, resolved, instance_id, trajectory_id only — no full
downloads for the scan), sorted alphabetically. Full scan log:
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/scan.log
(total repos counted across the split; the scan output is long
because every repo in the split is listed).

Chosen repo: AgnostiqHQ/covalent — 21 rows in the v2.0 sweagent
split, all 21 with a non-null resolved label. It is the first
alphabetical repo meeting the >= 20-row rule. It was not used in
any earlier POC: no earlier poc-new file mentions covalent, and
its instance ids (agnostiqhq__covalent-*) cannot overlap
poc-new-13 (scikit-learn-contrib/imbalanced-learn) or poc-new-15
(DeepSeek-V4-Flash Scale-SWE ids such as pre-commit_identify_pr63)
by construction — different repo, different instances.

Sample: the first 20 covalent rows in shard order (shards 7–14;
full ordered list with shard and row index in sample.json). The
21st covalent row (shard 14, row 754, agnostiqhq__covalent-1886,
resolved 1) was excluded only by the 20-row cut, not by outcome:
including it would have made the sample 11/21 resolved instead of
10/20. No outcome filtering was applied within the 20.

## Source

- Dataset: nvidia/Open-SWE-Traces, config v2.0, split sweagent.
  Source URL: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
- Repo in the rows: AgnostiqHQ/covalent (a Python workflow
  orchestration library; the rows are bug-fix-category SWE-agent
  trajectories).
- Teacher model for all 20 rows, from each row's metadata:
  Qwen3.8-Flash-Next, enable_thinking true, reasoning_effort xhigh.
  Same teacher family as poc-new-13, different repo — do not
  merge this lane's numbers with poc-new-13's.
- Raw rows (verbatim, one JSON per trajectory, columns
  trajectory_id, instance_id, repo, resolved, metadata, messages):
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/raw/
  (20 files, named by trajectory_id).

## Conversion (mechanical, no per-record editing)

Script:
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/convert.py
Events:
~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/events.jsonl
(3,543 events). Rules, mirroring the poc-new-13 converter for the
same dataset and split:

- case_id = trajectory_id; one model event per assistant turn;
  model = Qwen3.8-Flash-Next for every turn.
- One tool event per tool_call in the assistant message, name =
  function name (bash 1,236, str_replace_editor 372, submit 40).
- Retry event before the next model call when the preceding tool
  observation matches the poc-new-13 heuristic: Python traceback,
  FAILED/ERROR line, or "command not found". Observations only;
  the issue text is never scanned. This is a lower bound: editor
  errors and test failures without those signals are not counted.
- End event: success = row resolved (the dataset's real verdict).

Token disclosure, stated plainly: the dataset records no per-call
token usage. Input tokens = characters of all preceding message
text / 4; output tokens = characters of the assistant turn / 4,
where assistant turn text = content + reasoning_content +
tool-call names and arguments. These are mechanical estimates in
the same style as poc-new-13, never recorded usage, and every
dollar below inherits that status. Reasoning dominates the
assistant text: reasoning_content is 96.1% of content +
reasoning characters (2,327,866 of 2,423,032), about 70% of the
estimated output tokens — so most of the spend below is
accumulated thinking, not final answers.

## Averth run

- Averth: ~/workspace/averth at commit fafab07 ("Fix Langfuse
  cached alias: input_cached_tokens"), price table v6 (verified
  2026-10-22; `averth pricing` exits 0, 18 models, 8 tools).
  No Averth code was edited for this lane.
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace
  <hidden_files/poc-new-41/events.jsonl> --format jsonl
  --html <hidden_files/poc-new-41/report.html>
  --agent openswe-covalent`
- CLI exit code: 0, confirmed twice (the reported run, plus a
  clean re-run to /dev/null). No crash, no dropped-case error.
- Full CLI output:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/cli_output.txt
- HTML report:
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/report.html

## Numbers, fresh run

- Attempts: 20. Accepted outcomes (resolved): 10 (50.0%).
  Failed: 10. This matches the dataset's resolved labels exactly
  (10/20 in the sample; 11/21 across all covalent rows).
- Model events: 1,648. Tool events: 1,648. Retries: 227, every
  one reason "tool error". Assistant turns per case: 20 to 163.
- Model tokens (estimated): input 99,586,157, output 833,073.
- Total cost: $105.38.
  - Model spend: $102.09 (100% unknown:Qwen3.8-Flash-Next).
    Independent check: input 99,586,157 x $1.00/1M = $99.59,
    output 833,073 x $3.00/1M = $2.50, sum $102.09. Matches.
    A direct per-case recomputation from events.jsonl also
    totals $105.38 exactly.
  - Tool spend: $3.30 (1,648 calls x $0.002 built-in default).
- Cost basis, exactly as Averth printed it: COST BASIS
  ESTIMATED. Priced (tokens x vendor prices): $0.00.
  Vendor-supplied (billed): $0.00. Estimated (fallback
  prices): $105.38.
- Model price status: Qwen3.8-Flash-Next is NOT in price table
  v6, so Averth used its documented fallback $1.00 input /
  $3.00 output per 1M tokens and flagged it as unpriced model
  unknown:Qwen3.8-Flash-Next. No Qwen list price was invented.
- Cost per successful outcome (estimated, fully loaded):
  $10.54 (model terminal $0.37, retry path $9.84, tool calls
  $0.33, human review $0.00). The retry path is 93% of the
  per-success cost — the headline finding, not the terminal
  cost.
- Failed runs: $62.96 (60% of spend, zero outcomes).
- Retry path (overlapping lens, not additive with failed
  runs): $98.43 model + retry spend on discarded paths.
- Yield: 4% of tokens on the terminal path (96% burned on
  retries and failed runs).
- Context compounding: 63.0x input growth first-to-last step;
  context tax $0.00 (0% of model spend) — see anomaly 1.
- Heavy tail: p50 $3.20 / p95 $14.16 / max $14.40 per attempt;
  top 5% consumed 14% of budget. Costliest case:
  b06c6478-8d91-4ef1-acaf-6bbe4f71887a (agnostiqhq__covalent-1620,
  unresolved, 146 turns, 12 retries, $14.40); second costliest
  is a resolved case at $14.14, so cost does not separate
  success from failure here.

## Anomalies noted, as the task requires

1. Context tax $0.00 despite 63.0x compounding. Same
   fallback-pricing quirk as poc-new-13 and poc-new-15: with
   all model spend on fallback prices, the context-tax
   computation yields nothing. Do not quote "$0 context tax"
   as a result; the growth story has no dollar attached in
   this run.
2. No "-$0" priced-bucket artifact in this run's CLI output
   (searched, zero occurrences; priced bucket is $0).
3. No "Measured" label appears anywhere in the CLI output.
4. Tool spend $3.30 uses Averth's built-in per-call defaults
   for bash, str_replace_editor, and submit. It is not measured
   tool cost; Averth prints that warning itself.
5. The 50.0% sample rate is first-20-in-shard-order, not a
   representative rate: shard 12 alone contributes 4 resolved
   of 4, while shards 10, 11, and 13 contribute 0 resolved of
   5 combined. Do not generalize it to covalent, to
   Open-SWE-Traces, or to Qwen3.8-Flash-Next.
6. Cost per success ($10.54) rests entirely on fallback
   prices and chars/4 token estimates. A real Qwen list price
   would move every model dollar; do not compare $10.54
   against priced-model lanes.

## Independent cross-check

Direct count of events.jsonl (not the CLI's own summary):
model 1,648, tool 1,648, retry 227, end 20 (10 success True,
10 False). Matches the CLI's attempts, retries, and 50.0%
acceptance exactly. Per-case cost recomputation from the
events file (fallback prices + $0.002 tool default) totals
$105.38, matching the CLI total to the cent.

## Verdict: PASS as a clean-run diagnosis, with the limits above

PASS criteria from the task, checked:
- Real per-step input: yes, 20 verbatim trajectories, 41 to
  327 messages each, assistant turns with tool calls and
  observations.
- Attempts >= 10: yes, 20.
- Totals and honest cost basis: yes, exit 0, $105.38
  ESTIMATED, $0 priced, $0 billed, fallback model price
  flagged, anomalies above noted, no -$0 artifact.
- Aggregates alone: no, this is not an aggregate conversion;
  no paper total or blog total was turned into a single event.
- Repo rule: yes, first alphabetical v2.0 sweagent repo with
  >= 20 labelled rows, excluding the two prior
  Open-SWE-Traces lanes.

What this is not:
- Not a value POC: no change was applied or measured, no
  billed cost, no recorded tokens, and no finding a prospect
  can act on beyond "retry paths dominate the per-success
  cost in these 20 runs, at estimated prices".
- Not a Qwen pricing result: the model is unpriced in v6.
- Not ready to send to anyone. No recipient was verified,
  and with fallback prices plus chars/4 estimates, this
  would need verification before any contact. No contact
  was made.

## Reproduction files

- POC file: this file.
- Converter: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/convert.py
- Converted events: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/events.jsonl (3,543 lines)
- Sample list (shard order): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/sample.json
- All covalent positions (21 rows): ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/covalent_positions.json
- Scan log: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/scan.log
- Averth CLI output: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/cli_output.txt
- Averth HTML report: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/report.html
- Raw trajectories: ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-41/raw/ (20 files)
