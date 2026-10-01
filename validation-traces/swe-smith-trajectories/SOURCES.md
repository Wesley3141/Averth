# Source: SWE-bench/SWE-smith-trajectories

## Provenance
- Dataset: `SWE-bench/SWE-smith-trajectories`, split `tool` (HuggingFace)
- URL: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
- Paper: SWE-smith (arXiv:2504.21798), NeurIPS 2025 D&B Spotlight
- License: MIT (dataset card, verified via the HuggingFace API 2026-09-30)
- Produced by: SWE-agent harness runs of `claude-3-7-sonnet-20250219`
  (plus some `claude-3-5-sonnet-20241022` rows) against SWE-smith task
  instances (real GitHub repos, synthetic bug-injection tasks)

## How the trace was produced
Real agent executions: the SWE-agent harness ran the model against a live
repository checkout, issuing shell/file actions and observing results, then
evaluated the final patch. Each row is one sampled rollout: `messages` (the
full turn history), `resolved` (real pass/fail verdict), `model`, `traj_id`.

## Files in this directory
- `fetch.py` — mechanical fetch of 16 rows at fixed offsets via the public
  datasets-server rows API; rows stored verbatim
- `raw/` — the 16 raw rows, one JSON file per trajectory (fields: messages,
  instance_id, resolved, model, traj_id, patch), unedited
- `convert.py` — mechanical conversion to agentpnl JSONL events
- `events.jsonl` — converted events (16 cases, one per trajectory)
- `report.html` — CLI HTML report output

## Conversion rules (fixed, no per-record editing)
- case_id = row `traj_id`; one model event per assistant turn
- tool events: `tool_calls[].function.name` in the structured layout, or
  `<function=NAME>` tags parsed from assistant text in the XML-embedded
  layout (the `tool` split mixes both layouts)
- retry event before the next model call when a tool observation shows a
  real failure: Python traceback, unittest/pytest FAIL line, or
  "command not found". Observations only; the task prompt is never scanned.
- end event: success = row `resolved` (the dataset's real verdict)

## Known limitations of the conversion
- Token counts are mechanical estimates (characters/4 of accumulated
  context for input, characters/4 of the turn text for output). The dataset
  records no per-call usage. Dollar figures are estimates; the retry share,
  failure counts, and cost-shape findings reflect real trace structure.
- Tool calls carry no latency or per-call cost in the source; tools are
  costed at the library's default per-call price.
- The retry heuristic can miss silent failures (wrong-but-clean command
  output) and has no access to exit codes; it only flags observably failed
  tool calls.
