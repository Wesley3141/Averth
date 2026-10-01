# Source: mini-SWE-agent runs, SWE-bench experiments leaderboard

## Provenance
- Leaderboard entry: `20250726_mini-v1.0.0_claude-sonnet-4-20250514` in the
  SWE-bench experiments repository (m0at/experiments, `evaluation/verified/`)
- Entry metadata: https://github.com/m0at/experiments/tree/main/evaluation/verified/20250726_mini-v1.0.0_claude-sonnet-4-20250514
- Trajectories: public S3 bucket `swe-bench-submissions`, prefix
  `bash-only/20250726_mini-v1.0.0_claude-sonnet-4-20250514/trajs/`
  (anonymous read; no credentials used)
- Per-instance details (real recorded cost, api_calls, resolved):
  `per_instance_details.json` from the same entry, saved here verbatim
- License: no license file found in the experiments repository and no
  license stated on the bucket listing (checked 2026-09-30). A 12-file
  subset is kept here for validation only; the canonical copies remain at
  the public URLs above.
- Produced by: mini-SWE-agent v1.0.0 (bash-only) running
  `claude-sonnet-4-20250514` against SWE-bench Verified instances; 500
  instances, 64.9% reported resolved

## How the trace was produced
Real agent executions: the harness ran the model in a loop where each
assistant turn emits THOUGHT plus exactly one bash command, and each tool
result comes back wrapped as `<returncode>N</returncode><output>...</output>`.
Every nonzero return code is a genuinely recorded tool failure. The run
ends with the `MICRO_SWE_AGENT_FINAL_OUTPUT` submission command.

## Files in this directory
- `fetch.py` — mechanical download of 12 trajectories (every ~42nd key of
  the 504-key listing) plus the entry's metadata.yaml; files stored verbatim
- `raw/` — the 12 raw `.traj.json` files (instance_id, info.exit_status,
  info.submission, messages), unedited
- `metadata.yaml` — the leaderboard entry metadata (aggregate cost,
  instance cost, api_calls), saved verbatim
- `per_instance_details.json` — per-instance real cost/api_calls/resolved,
  saved verbatim
- `convert.py` — mechanical conversion to averth JSONL events
- `compare.py` — cross-check of metered cost vs the real recorded
  per-instance costs
- `events.jsonl` — converted events (12 cases, one per trajectory)
- `report.html` — CLI HTML report output

## Conversion rules (fixed, no per-record editing)
- case_id = `instance_id`; one model event per assistant turn
  (model `claude-sonnet-4-20250514`), one `bash` tool event per turn
- retry event before the next model call when the tool result message
  carries `<returncode>` != 0 (a real recorded failure signal)
- end event: success = `per_instance_details.json[instance]["resolved"]`
  (the leaderboard's real pass/fail verdict)

## Known limitations of the conversion
- Token counts are mechanical estimates (characters/4 of accumulated
  context for input, characters/4 of the turn text for output). The traces
  record no per-call usage. The per-instance RECORDED costs in
  `per_instance_details.json` are real; see FINDINGS.md for the comparison.
- Tool calls carry no latency; costed at the library's default per-call
  price.
