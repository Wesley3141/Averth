# POC new-12: SWE-Gym flask/requests slice — PASS via sibling Verified trajectories

## Verdict: PASS (clean-run diagnosis test only)

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated. This is a diagnosis run, not a value pitch and
not a send draft.

## Correction to the lane label, read first

The lane as named (SWE-Gym, flask or requests) does NOT exist in the
native SWE-Gym trajectory sets, and this file does not pretend it
does. Three public trajectory sets were checked first, all with zero
flask/requests rows, before the sibling slice below was used:

1. SWE-Gym OpenHands-Sampled-Trajectories
   (https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories):
   all 3 shards read, 2,019 + 2,018 + 2,018 = 6,055 rows, 0 rows with
   a flask or requests instance_id. Its 11 repos are moto, mypy, dvc,
   MONAI, pydantic, dask, conan, hydra, modin, pandas, bokeh. Flask
   and requests are simply not in SWE-Gym.
2. Nebius SWE-agent trajectories
   (https://huggingface.co/datasets/nebius/SWE-agent-trajectories):
   all 12 shards read, 80,036 rows, 0 flask/requests rows. This is
   SWE-bench Extra, which excludes the original SWE-bench repos
   (flask, requests, django included), so the zero is structural,
   not a search miss. Scan log saved with the work files.
3. Nebius SWE-rebench OpenHands trajectories
   (https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories):
   67,074 rows, repo column read in full, 0 rows for pallets/flask
   or psf/requests. SWE-rebench is new decontaminated instances, not
   the original SWE-bench repos.

Sibling slice used, per the lane's fallback clause: SWE-bench
Verified trajectories for the flask/requests repos, from a different
trajectory dataset than the first batch, with per-step messages and
the dataset's own resolved labels. The repos are the same ones the
lane named; the trajectory source is the sibling, and that
substitution is stated here, not hidden.

## Source used

- Dataset: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (5,002 files: 10 model runs x 500 SWE-bench Verified instances).
  This dataset is a trajectory collection, not the SWE-bench task set.
- Slice rule, mechanical: every file under
  `swebench_verified_raw/<model>/` whose instance_id starts with
  `pallets__flask` or `psf__requests`, for exactly two model runs:
  `gemini-3-pro` and `gemini-3-flash-high`. Each model run has
  exactly 9 such files (1 flask + 8 requests), so the slice is
  18 attempts, 9 distinct issues, 2 models. No cherry-picking
  inside the slice: all 9 per model are included.
- Distinctness: agent 11's slice is django (231 files, claude-opus-4.6);
  this slice is flask/requests, different repos and different
  models, zero attempt overlap with agent 11. First-batch POC 10
  (SWE-Gym broad) has zero overlap, since flask/requests are not in
  SWE-Gym at all. First-batch mini-SWE-agent's 12-instance sample
  included one of these issue ids (psf__requests-1921) under a
  different model and a different trajectory dataset; the 18 attempts
  here are new runs, not reused attempts.
- Issues (9): pallets__flask-5014; psf__requests-1142, -1724, -1766,
  -1921, -2317, -2931, -5414, -6028.

## Conversion, mechanical (same rules as batch-3 agent 11)

Work files:
`~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-12/`
(convert.py, events.jsonl, cli-output.txt, report.html, raw/ 18 files,
scan.log, rebench_matches.json).

- One file = one attempt, case_id = model run + "__" + instance_id,
  so the same issue under two models stays two attempts.
- Model mapping, stated: gemini-3-pro -> "gemini-3-pro";
  gemini-3-flash-high -> "gemini-3-flash" (Averth price table v6 key;
  "-high" is an effort variant of the same base model, not a
  distinct vendor-priced model). No price invented for a
  "flash-high" model.
- system/user/tool content lengths accumulate into context_chars.
- assistant: one model event (input = context_chars//4, output =
  (content chars + tool argument chars)//4), then one tool event
  per tool_call (function name, always "bash" here).
- retry event before the next assistant turn when the preceding
  tool observation contains "Traceback", a recorded failure signal.
  Flash-high tool messages also carry "Exit code:" prefixes (65
  nonzero exits across its 9 files); those counts are reported as
  a check below, not converted to retries, to stay identical to
  agent 11's rule. Pro tool messages carry no exit-code prefix.
- end event: success = info.resolved, the dataset's own label
  (also info.scores.resolved).
- Token counts are NOT recorded in these traj files, so tokens are
  chars//4 estimates, same limitation as batch 1 and agent 11.
  Recorded per-instance costs live in info.model_stats.instance_cost
  and are compared below, not replaced by Averth's dollars.

## Averth run (upgraded build)

- Repo: ~/workspace/averth, commit 071d0e1, price table v6
  (verified 2026-10-22).
- Command, from ~/workspace/averth:
  `.venv/bin/python -m averth.cli trace <events.jsonl> --format jsonl`
- CLI exit code: 0, no crash, no error.
- Attempts: 18. Autonomous completions (dataset resolved labels):
  17 (94.4%). Failed: 1 (gemini-3-flash-high, psf__requests-6028).
  By model: gemini-3-pro 9 of 9 resolved; gemini-3-flash-high
  8 of 9 resolved.
- Events: 2,053 total (976 model, 979 tool, 80 retries, 18 end).
  Retries: 80, all "traceback in previous tool observation"
  (flash-high 50 traceback tool observations, pro 30).
- Total cost, metered: $13.82.
- Cost basis, as printed by Averth itself: ESTIMATED. Priced
  (tokens x vendor prices, token provenance unverified) $11.86;
  vendor-supplied (billed) $0.00; estimated (fallback/tool)
  $1.96, which is entirely built-in bash per-call estimates
  (Averth's own warning line says so); both model keys are
  vendor list prices in v6, so no model dollars used fallback
  pricing. Cost per successful outcome (fully loaded): $0.81.
- Five layers: context compounding 15.3x first-to-last step,
  context tax $9.18 (77% of model spend); yield 11% of tokens on
  the terminal path (89% burned on retries and failed runs);
  heavy tail p50 $0.73 / p95 $1.34 / max $1.65 per attempt;
  model mix google:gemini-3-pro $7.14 (60% of model spend),
  google:gemini-3-flash $4.72 (40%).
- Failed runs: $0.56 (4% of spend, zero outcomes). Retry path:
  $10.59 model+retry spend on discarded paths (overlapping lens,
  not additive).

## Anomaly check required by the lane

- No -$0 and no $0 context-tax anomaly here. Context tax is
  $9.18, a real positive figure, not $0.00 and not -$0.
- No "Measured" label anywhere: the report's cost basis is
  ESTIMATED, with the do-not-quote-as-a-bill warning printed.

## Metered vs recorded (the honest comparison)

- Recorded per-instance costs from info.model_stats.instance_cost,
  summed over exactly these 18 files: $12.69 total
  (gemini-3-pro $9.62, gemini-3-flash-high $3.07).
- Averth metered $13.82 vs recorded $12.69: +$1.13 (+8.9%).
  Decomposition: metered model spend $11.86 is $0.83 BELOW
  recorded, and the $1.96 of built-in bash tool estimates more
  than accounts for the net +$1.13. In other words, on this slice
  the chars//4 token estimate slightly underprices model spend
  versus the real bill, and the tool default pushes the total
  above it. Do not quote $13.82 as what anyone was charged.
- Recorded costs are per-instance API costs from the run
  metadata, not Averth-measured bills; the comparison is a
  sanity check on the meter, not a reconciliation to an invoice.

## Limits that must travel with this number

- 17 of 18 resolved is NOT a general solve rate. It is 9 small
  Verified issues (1 flask, 8 requests) under two strong Gemini
  models. Do not present 94.4% as Gemini's or any scaffold's
  general SWE-bench rate.
- Tokens are chars//4 estimates, not recorded usage; dollars are
  list-price estimates plus tool defaults, not a bill.
- The native SWE-Gym flask/requests lane is still unfilled: no
  public SWE-Gym trajectory set contains those repos, as shown
  above. A future SWE-Gym-only claim for flask/requests would
  still be false.
- PASS criteria met: real per-step input (18 full trajectories,
  not aggregates), attempts 18 (>= 10), CLI exit 0, totals
  reported, honest ESTIMATED cost basis, no -$0/$0 anomaly.
