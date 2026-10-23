# 40-POC outreach-ready index (Averth clean-run diagnoses)

Built 2026-10-23 from the POC files in this directory, including all
wave-5 and wave-5b addenda. Where an addendum supersedes a filed total,
the addendum total is used and the old total appears only in the
corrections log at the end. Totals were read from the files, not from
any summary; two files were found stale at index time and are flagged
in place (POC 02, poc-new-10).

## Read this first

- Every dollar below is ESTIMATED unless the lane used recorded tokens
  (lanes 16 and new-10 only, plus lane 58's recorded tokens at fallback
  prices). "Priced" in an Averth report means vendor list prices applied
  to tokens; where those tokens are chars/4 estimates, this index labels
  the dollars ESTIMATED (tokens estimated) regardless of the bucket name
  Averth printed. No total below is a bill, a vendor invoice, or a saving.
- Yield is Averth's terminal-path token share, never a success rate.
  Never quote yield next to a resolved rate as if they were the same
  number. Cost per successful outcome is UNKNOWN wherever successes are
  zero or outcomes are unknown; Averth printing $0.00 in those cases is
  vacuous and is never quoted as "$0 per success".
- Retries are rule-dependent lower bounds (silent failures without the
  rule's signal are missed). Every row names its rule. Retry counts are
  NOT comparable across lanes without the rule.
- No POC in any batch has a verified individual recipient. Recipient
  status is "none verified" for every A lane below. Dataset teams and
  dataset author handles (for example the SWE-Gym team, the OpenHands
  team, tarsur385) are data sources, not verified outreach recipients.
  Nothing in this index is a send draft, and nothing here authorizes a
  send. Each send still needs Wesley's explicit tap under his staged
  protocol.
- Every A lane below is a clean-run diagnosis only: no change was
  tested, no saving was measured, no operator acted on a finding.
  None of these is production proof and none is a value POC on its own.

## Counts

- A (usable, counted): 43. Batch 1: 4. Batch 2: 3. Batch 3: 10.
  Batch 4: 11. Batch 5: 15. Target was 40; the count is 43, so no
  replacement batch was needed and no B or FAIL lane was reclassified
  to reach the target.
- B (clean run, biased sample, NOT counted): 5 (lanes 26, 30, 32, 33, 45).
- FAIL (no usable trace, no labels, or aggregate-only, NOT counted): 24.
- Reference, not counted (ran clean but is a demo or single trace,
  not an outreach POC): 3 (batch-1 POC 04, POC 08, POC 09).
- Total files reconciled: 43 + 5 + 24 + 3 = 75 (POC 01-10, poc-new-01-65).

## A lanes: summary table

Lane | Workflow / model | Att | Res | Retries (rule) | Total (basis) | Per success | Failed | Context / tax | Yield
--- | --- | --- | --- | --- | --- | --- | --- | --- | ---
POC 01 | SWE-smith, SWE-agent runs | 16 | 8 (50%) | 36 (tool-error) | $24.79 ESTIMATED, chars/4 | $3.10 | $13.06 (53%) | 22.0x / $20.42 | 11%
POC 02 | SWE-Gym OpenHands, GPT-4o-2024-08-06, t04 run | 20 | 5 (25%) | 22 (bash exit-code) | $3.61 filed fallback; $7.91 repriced, PROVISIONAL, see note | $0.72 filed ($1.58 if $7.91 holds) | $2.86 (79%, filed basis) | 13.4x / not stated in file | 8%
POC 03 | Nebius SWE-agent trajectories, rows 0-100 | 100 | 17 (17%) | 254 (syntax-error + traceback) | $30.67 ESTIMATED, chars/4, fallback | $1.80 | $26.97 (88%) | 6.5x / $0.00 vacuous, fallback | 5%
POC 10 | SWE-Gym OpenHands, Claude 3.5 Sonnet (file name says AutoGen; no AutoGen data was used) | 229 | 67 (29.3%) | 520 (traceback) | $464.06 ESTIMATED, chars/4 | $6.93 | $380.80 (82%) | 41.7x / $419.04 | 7%
new-04 | Semantic Kernel blog run, model named only "gpt-4", manual conversion, no native importer | 1 | 1 completion | 0 | $0.002246 ESTIMATED, unpriced model + tool default | $0.002246 per completed run | $0.00 | 1.7x / $0.00 | 100% (vacuous, n=1)
new-09 | Nebius OpenHands trajectories, Qwen3-Coder-480B, OpenHands v0.54.0 | 20 | 13 (65%) | 89 (bash exit-code) | $40.17 ESTIMATED, chars/4, fallback | $3.09 | $19.30 (48%) | 13.7x / $0.00 filed, fallback (v7: n/a) | 7%
new-10 | Simon Willison real Claude Code session, claude-haiku-4-5-20251001 | 1 | 0, outcome UNKNOWN | 0 | $0.19 PRICED, recorded tokens (v8 rerun; filed $0.14 FAIL superseded) | UNKNOWN | $0.00 | 2.3x / $0.05 | n/a
11 | tarsur385 django, claude-opus-4-6 | 231 | 184 (79.7%) | 742 (traceback) | $299.36 ESTIMATED, chars/4 (v8; was $873.38) | $1.63 | $64.04 (21%) | 6.9x / $223.57 | 13%
12 | tarsur385 flask/requests, gemini-3-pro + gemini-3-flash-high | 18 | 17 (94.4%) | 80 (traceback) | $13.82 ESTIMATED, chars/4 | $0.81 | $0.56 (4%) | 15.3x / $9.18 | 11%
13 | nvidia Open-SWE-Traces sweagent, scikit-learn-contrib/imbalanced-learn (NOT scikit-learn), Qwen3.8-Flash-Next fallback | 14 | 0 (0%) | 74 (traceback) | $60.99 ESTIMATED, fallback | UNKNOWN | $60.99 (100%) | 99.5x / $0.00 vacuous | 0%
15 | nvidia Open-SWE-Traces, DeepSeek-V4-Flash-0731 (NOT V3), fallback | 20 | 13 (65%) | 33 (bash exit-code) | $26.74 ESTIMATED, fallback | $2.06 | $17.31 (65%) | 15.3x / $0.00 filed, fallback (v7: n/a) | 15%
16 | OpenHands evaluation, claude-3-5-sonnet-20241022, SWE-bench Lite | 20 | 11 (55%) | 42 (exit-code 1) | $5.21 PRICED, recorded tokens | $0.47 | $2.50 (48%) | 12.8x / $2.96 | 11%
17 | Nebius SWE-agent rows 100-200, swe-agent-llama-70b (95) + 8b (5), 0 GPT-4o despite the file name | 100 | 0 (0%) | 375 (syntax 208 + traceback 167) | $43.52 ESTIMATED, chars/4, fallback | UNKNOWN | $43.52 (100%) | 7.2x / $0.00 filed, fallback (v7: n/a) | 0%
18 | SWE-smith tool split rows 1000-1019, Claude 3.5 Sonnet (NOT SWE-agent) | 20 | 5 (25%) | 50 (tool-error/traceback) | $29.25 ESTIMATED, chars/4 | $5.85 | $25.68 (88%) | 43.0x / $21.27 | 3%
19 | mini-SWE-agent, m0at SWE-bench Verified entry, every-42nd instance | 11 | 8 (72.7%) | 31 (bash exit-code) | $12.58 ESTIMATED, chars/4 | $1.57 | $6.07 (48%) | 8.7x / $9.15 | 22%
24 | SmolAgents GAIA, GPT-4o CodeAgent, strict grading | 20 | 11 (55%) | 6 (error-observation) | $1.84 ESTIMATED, chars/4 | $0.17 | $1.02 (55%) | 3.7x / $0.79 | 31%
27 | Nebius SWE-bench Extra shard 0 rows 400-499, llama-70b (94) + 8b (6) | 100 | 27 (27%) | 239 (syntax 151 + traceback) | $17.23 ESTIMATED, chars/4, fallback | $0.64 | $15.56 (90%) | 5.1x / $0.00 filed, fallback (v7: n/a) | 6%
31 | SWE-Gym pandas, FULL RUN, gpt-4o-2024-08-06 | 737 | 56 (7.6%) | 1237 (traceback) | $824.43 ESTIMATED, chars/4 | $14.72 | $785.21 (95%) | 21.4x / $706.87 | 3%
34 | SWE-Gym pydantic, gpt-4o-2024-08-06 | 20 | 0 (0%) | 0 (exit-code) / 82 (traceback), rule-dependent | $15.31 ESTIMATED, chars/4 | UNKNOWN | $15.31 (100%) | 23.9x / $12.61 | 0%
35 | SWE-smith sunpy, Claude 3.7 Sonnet, synthetic mutations | 20 | 10 (50%) | 24 (traceback) | $26.82 ESTIMATED, chars/4 | $2.68 | $19.38 (72%) | 13.1x / $21.80 | 12%
36 | tarsur385 sympy, gemini-3-pro | 20 | 20 (100%) | 97 (traceback) | $23.48 ESTIMATED, chars/4 | $1.17 | $0.00 | 8.8x / $16.52 | 1%
37 | tarsur385 astropy, claude-opus-4-6 | 20 | 11 (55%) | 93 (traceback) | $31.97 ESTIMATED, chars/4 (v8; was $92.90) | $2.91 | $19.27 (60%) | 6.4x / $22.06 | 2%
38 | OpenHands evaluation, gpt-4o-2024-05-13, v1.9 format | 20 | 3 (15%) | 90 (bash exit-code) | $23.76 ESTIMATED, chars/4, v1.9 undercount (v7; was $9.96 fallback) | $7.92 | $22.21 (93%) | 103.7x / $21.02 | 1%
40 | nvidia Open-SWE-Traces scale-swe, Qwen3.6-27B fallback | 20 | 11 (55%) | 139 (bash exit-code) | $64.66 ESTIMATED, chars/4, fallback | $5.88 | $30.91 (48%) | 21.6x / $0.00 filed, fallback (v7: n/a) | 7%
41 | nvidia Open-SWE-Traces v2.0 sweagent, AgnostiqHQ/covalent, Qwen3.8-Flash-Next fallback | 20 | 10 (50%) | 227 (traceback) | $105.38 ESTIMATED, chars/4, fallback | $10.54 | $62.96 (60%) | 63.0x / $0.00 filed, fallback (v7: n/a) | 4%
42 | tarsur385 matplotlib, claude-opus-4-6 | 20 | 15 (75%) | 58 (traceback) | $27.04 ESTIMATED, chars/4 (v8; was $78.75) | $1.80 | $8.74 (32%) | 6.6x / $19.77 | 9%
44 | SmolAgents GAIA next slice, GPT-4o CodeAgent, strict grading | 20 | 13 (65%) | 7 (error-observation) | $3.28 ESTIMATED, chars/4 | $0.25 | $1.26 (38%) | 6.2x / $2.13 | 45%
47 | OpenHands evaluation, gpt-4o-mini-2024-07-18, v1.9 format | 20 | 3 (15%) | 78 (bash exit-code) | $1.71 ESTIMATED, v1.9 undercount (v7 verbatim key reproduces it) | $0.57 | $1.58 (92%) | 39.7x / $0.74 | 1%
51 | tarsur385 xarray, claude-opus-4-6 | 20 | 16 (80%) | 62 (traceback) | $19.85 ESTIMATED, chars/4 (v8; was $57.36) | $1.24 | $6.35 (32%) | 5.1x / $12.50 | 8%
52 | tarsur385 sklearn, gpt-5.2-high | 20 | 17 (85%) | 43 (traceback) | $10.59 ESTIMATED, chars/4 (v7; was $6.34 fallback) | $0.62 | $0.98 (9%) | 8.0x / $7.23 | 24%
53 | tarsur385 sklearn, claude-4.5-haiku-high | 20 | 18 (90%) | 99 (traceback) | $13.78 ESTIMATED, chars/4 | $0.77 | $2.50 (18%) | 12.4x / $9.74 | 4%
54 | tarsur385 sklearn, claude-4.5-opus-high | 20 | 20 (100%) | 66 (traceback) | $28.74 ESTIMATED, chars/4 (v7; was $6.62 fallback) | $1.44 | $0.00 | 7.8x / $20.40 | 12%
55 | tarsur385 xarray, gpt-5-mini | 20 | 10 (50%) | 38 (traceback) | $1.98 ESTIMATED, chars/4 (v7; was $5.13 fallback) | $0.20 | $1.22 (62%) | 7.2x / $0.84 | 20%
56 | tarsur385 xarray, glm-5-high | 20 | 15 (75%) | 110 (traceback) | $33.17 ESTIMATED, chars/4 (v7; was $33.14 fallback) | $2.21 | $13.15 (40%) | 15.0x / $25.83 | 10%
57 | tarsur385 xarray, minimax-m2.5-high, unpriced | 20 | 17 (85%) | 115 (traceback) | $21.29 ESTIMATED, chars/4, fallback | $1.25 | $5.81 (27%) | 11.8x / n/a (v7) | 3%
58 | OpenHands evaluation, deepseek-chat, unpriced | 20 | 1 (5%) | 51 (bash exit-code) | $1.20 ESTIMATED, recorded tokens at fallback prices | $1.20 (total / 1 success; the resolved attempt itself cost $0.06) | $1.14 (95%) | 4.0x / n/a (v7) | 3%
59 | OpenHands evaluation, o1-mini-2024-09-12, v1.9 format | 20 | 7 (35%) | 44 (bash exit-code) | $4.86 ESTIMATED, chars/4, v1.9 undercount (v7; was $4.43 fallback) | $0.69 | $3.69 (76%) | 35.4x / $3.63 | 15%
60 | OpenHands evaluation, qwen-2.5-72b-instruct, unpriced, LONG-TRAJECTORY SAMPLE ONLY | 20 | 0 (0%) | 39 (bash exit-code) | $2.91 ESTIMATED, chars/4, fallback | UNKNOWN | $2.91 (100%) | 29.6x / n/a (v7) | 0%
61 | OpenHands evaluation, gemini-1.5-pro-002, unpriced, v1.9 format | 20 | 2 (10%) | 49 (bash exit-code) | $5.16 ESTIMATED, chars/4, fallback, output undercounted | $2.58 | $4.50 (87%) | 44.6x / n/a (v7) | 7%
62 | SWE-Gym moto, >=8 assistant turns, gpt-4o-2024-08-06 | 20 | 7 (35%) | 42 (traceback) | $13.12 ESTIMATED, chars/4 | $1.87 | $9.68 (74%) | 16.8x / $10.34 | 13%
63 | SWE-Gym MONAI, >=8 assistant turns, gpt-4o-2024-08-06 | 20 | 7 (35%) | 17 (traceback) | $5.87 ESTIMATED, chars/4 | $0.84 | $4.29 (73%) | 19.4x / $4.36 | 23%
64 | SWE-Gym dask, >=8 assistant turns, gpt-4o-2024-08-06 | 20 | 4 (20%) | 29 (bash exit-code; traceback recount 30) | $12.48 ESTIMATED, chars/4 | $3.12 | $11.13 (89%) | 20.5x / $10.24 | 8%
65 | SWE-Gym bokeh, >=8 assistant turns, gpt-4o-2024-08-06 | 20 | 1 (5%) | 16 (bash exit-code; traceback recount also 16) | $7.29 ESTIMATED, chars/4 (v7 bucket moved priced to estimated-token) | $7.29 (dominated by failures) | $7.00 (96%) | 9.0x / $5.20 | 1%

## A lanes: source, token basis, recorded comparison, bias, overlap, anomalies

Recipient status for every lane in this section: none verified. No
individual recipient, email, or role is attached to any lane. Do not
send any lane to anyone on the basis of this index alone.

- POC 01. Source: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
  (tool split). No recorded dollar cost in the dataset, so no
  metered-vs-recorded ratio exists. Bias: 16 attempts, one model family
  (Claude 3.5 Sonnet in the standout run). Anomaly: filed top finding
  says retry loops burned $21.54 while waste accounting says retry
  path $21.03; quote $21.03. Overlap: shares the SWE-smith family with
  lanes 18 and 35; trajectory overlap with lane 18 is zero (different
  rows) and with lane 35 is zero (different split and repo). Recipient: none verified.
- POC 02. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (shard 0, t04 run, GPT-4o-2024-08-06). STALE-FILE FLAG: the file
  still shows the $3.61 fallback total. A $7.91 repriced total was
  reported after the gpt-4o-2024-08-06 snapshot alias was added to
  the price table, but no saved rerun for this lane was found in
  the lane's files at index time, so $7.91 is PROVISIONAL. A saved
  rerun is required before this lane is used for outreach. Filed failed dollars ($2.86) are on the old fallback
  basis. Sample bias: shard 0 only; full shard-0 run resolves 9.5%,
  so 25% in this sample is above the run rate. Overlap: same dataset
  as POC 10 and lanes 31, 34, 62, 63, 64, 65; lane 64 excludes 2 exact
  POC 02 attempts by prior use, lane 65 excludes POC 02's only bokeh
  row, lane 62 repeats one POC 02 attempt (same issue, same run). Recipient: none verified.
- POC 03. Source: https://huggingface.co/datasets/nebius/SWE-agent-trajectories
  (rows 0-100). No recorded dollar cost in the dataset. Bias: all 17
  resolved attempts come from one issue (Melevir__cognitive_complexity-15,
  45 attempts); the other 6 issues resolve 0 of 55. Never quote 17%
  as a SWE-agent rate. Overlap: zero row overlap with lanes 17 and 27
  (rows 100-200 and shard-0 rows 400-499 respectively). Recipient: none verified.
- POC 10. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (229-row Claude 3.5 Sonnet run). No recorded dollar cost stated in
  the file. Bias: the file name says AutoGen, but no AutoGen
  trajectory dataset was found or used; this is a SWE-Gym lane and
  must be labelled as such. Overlap: issue overlap with POC 02's moto
  subset is 20 of 20 at issue level (same moto issues, different
  model and trajectories); lane 65 excludes POC 10's Claude-run
  bokeh row. Recipient: none verified.
- new-04. Source: https://systenics.ai/blog/2024-03-18-function-calling-with-semantic-kernel/
  (one published blog run, manually converted). Model named only
  "gpt-4", unpriced; $0.002 of the $0.002246 total is the built-in
  tool default. Limits: n=1, no waste, no native Semantic Kernel
  importer exists; Averth has never natively ingested a Semantic
  Kernel trace. Yield 100% and $0.00 tax are vacuous at n=1. Recipient: none verified.
- new-09. Source: https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories
  (OpenHands v0.54.0, Qwen3-Coder-480B, first 20). No recorded dollar
  cost stated in the file. Bias: first-20 sample, 65% resolved, above
  the dataset's overall rate. Anomaly: $0.00 context tax at filing is
  the fallback quirk, not "context was free"; wave-5 logic prints n/a
  for such runs. Overlap: zero overlap with batch-1 lanes by the
  file's check. Recipient: none verified.
- new-10. Source: https://gist.githubusercontent.com/simonw/bfe117b6007b9d7dfc5a81e4b2fd3d9a/raw/31e9df7c09c8a10c6fbd257aefa47dfa3f7863e5/3f5f590c-2795-4de2-875a-aa3686d523a1.jsonl
  (Simon Willison session, sessionId 3f5f590c-2795-4de2-875a-aa3686d523a1).
  STALE-FILE FLAG, RESOLVED AT INDEX TIME: the filed verdict was the
  pre-wave-3 FAIL ($0.14 fallback, output undercounted, auto-failed
  headline). The index-time v8 rerun (output saved in
  hidden_files/poc-new-10/averth-output-v8.txt) gives $0.19 priced,
  outcome unknown, failed $0.00, yield n/a, 38 model calls kept, 38
  duplicates skipped, 1,127,558 cached tokens, cache saving $1.01.
  An addendum recording this rerun was appended to the file. Limits:
  n=1, no acceptance label, cost per accepted outcome UNKNOWN.
  Cache-creation tokens are priced at full input price, not the
  1.25x vendor write rate, so $0.19 is slightly low. Recipient: none verified.
- 11. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-opus-4.6 run, django, 231 attempts). Recorded source cost
  $116.05 for the same 231 attempts; v8 metered $299.36 is 2.58x
  (was 7.52x at the wrong $15/$75 price). Gap hypothesis only:
  full-history accumulation, no truncation, no cache discount, at
  list prices on chars/4 tokens. Never quote $299.36 as a bill.
  Bias: full django slice of one model run, not a django rate.
  Overlap: repo-disjoint from lanes 12, 36, 37, 42 within tarsur385. Recipient: none verified.
- 12. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (gemini-3-pro and gemini-3-flash-high, flask/requests). Recorded
  source cost $12.69; metered $13.82 is +8.9%. Bias: 18 attempts, 9
  distinct issues, 94.4% is not a general rate. Overlap: zero attempt
  overlap with lane 11 by the file's check. Recipient: none verified.
- 13. Source: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
  (v2.0 sweagent split, scikit-learn-contrib/imbalanced-learn).
  LABEL CORRECTION: this is NOT scikit-learn. Exact scikit-learn is
  absent from SWE-smith, SWE-Gym, Nebius, and nvidia sets checked.
  All 55 imbalanced-learn rows across splits resolve 0. No recorded
  dollar comparison in the file. Bias: single repo, single teacher
  model family, 0% is a property of this slice, not a model rate. Recipient: none verified.
- 15. Source: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
  (DeepSeek-V4-Flash-0731). LABEL CORRECTION: V4-Flash, never V3;
  no public DeepSeek-V3 set was found. No billed cost, no recorded
  tokens, no cache data. Bias: first-20 sample; about 72% of output
  tokens are reasoning tokens. Recipient: none verified.
- 16. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (SWE-bench Lite, claude-3-5-sonnet-20241022). Recorded tokens
  (see table); this is the strongest recorded-token lane in the set.
  Source accumulated_cost ($13.24) double-counts every cost and was
  not used. Cache saving $16.94 already realized in the source run.
  Bias: sample 55% vs full run 41.7% (125/300). Anomaly: cache-creation
  tokens priced at full input price, about $0.38 (about 8%) low.
  Overlap: instance overlap with lanes 38, 47, 58, 59, 60, 61 (same
  300-instance benchmark, distinct trajectories); do not claim
  instance-disjointness. Recipient: none verified.
- 17. Source: https://huggingface.co/datasets/nebius/SWE-agent-trajectories
  (rows 100-200). LABEL CORRECTION: the file name says GPT-4o, but
  the rows are swe-agent-llama-70b (95) and swe-agent-8b (5); GPT-4o
  count in this slice is 0. Combined rows 0-200: 17 of 200 resolved,
  all from Melevir__cognitive_complexity-15. No recorded dollar cost
  in the dataset. Recipient: none verified.
- 18. Source: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
  (tool split rows 1000-1019). LABEL CORRECTION: SWE-smith Claude
  slice, NOT SWE-agent; the file name is misleading. Zero trajectory
  overlap with POC 01. Priced bucket $28.45 is list prices on
  chars/4 tokens, so the index labels the total ESTIMATED. Recipient: none verified.
- 19. Source: m0at SWE-bench Verified entry (mini-SWE-agent, every-42nd
  instance from index 21, excluding batch-1's 12). Leaderboard
  recorded cost $3.50 for the same 11 attempts; metered $12.58 is
  about 3.6x. Bias: 11 attempts, systematic slice, not a general
  mini-SWE-agent rate. No different-model mini entry could be
  enumerated, so this fallback slice is used and labelled as such. Recipient: none verified.
- 24. Source: https://huggingface.co/datasets/smolagents/gaia-traces
  joined to https://huggingface.co/datasets/smolagents/GAIA-annotated
  (first 20 unique validation questions). Grading: strict
  normalized-exact 11/20 (55%); contains-grading 19/20 (95%) is
  secondary only and must never replace the strict figure.
  Overlap: zero task_id and zero trace_row overlap with lane 44
  (asserted programmatically). Recipient: none verified.
- 27. Source: Nebius SWE-agent trajectories, SWE-bench Extra shard 0
  rows 400-499. LABEL CORRECTION: original GPT-4o lane failed
  (GPT-4o count 0 in all 80,036 Nebius rows; models are only
  llama-70b/8b/405b); this fallback slice is llama-70b (94) plus
  llama-8b (6). Zero row and issue overlap with POC 03. All 27
  resolved attempts come from 2 of 6 issues. The "-$0" priced-bucket
  artifact appears in this lane's filed report. Recipient: none verified.
- 31. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (pandas, full run, not a slice). Pandas population 70/1,044
  (6.7%); this run 56/737 (7.6%). Count this lane once, as the
  full-run diagnosis. Literal first-20 and every-37th slices are
  both 0/20 by construction (first resolved main-run row at index
  152) and are audit notes only, never a pandas rate. Recipient: none verified.
- 34. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (pydantic, first 20 with at least 8 turns, excluding 2 exact POC 02
  attempts by prior use only). Pydantic population 11/243 (4.5%).
  Retry rule matters more here than anywhere: 0 retries under the
  POC 02 exit-code rule vs 82 under the traceback rule. The filed
  report's "retry loops burned $14.34" finding is wrong under the
  exit-code rule (0 retries); wave-5 suppresses the retry finding
  at 0 retries. Recipient: none verified.
- 35. Source: https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories
  (xml split, sunpy, Claude 3.7 Sonnet). LIMIT: these are SWE-smith
  synthetic mutations of one sunpy commit, split by task type
  (program-mutation 9/10 resolved, LM-rewrite 1/10), NOT real sunpy
  issues. Never present this to sunpy maintainers as a finding
  about their project. Zero trajectory overlap with POC 01 and
  lane 18. Recipient: none verified.
- 36. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (gemini-3-pro, sympy). LABEL CORRECTION: tarsur385, NOT SWE-smith
  sympy (SWE-smith has no sympy). Recorded source cost $25.61;
  metered $23.48 is -8.3%. Label anomalies: sympy-13031 exited with
  ServiceUnavailableError but resolved True; sympy-12489 and -13615
  exited LimitsExceeded but resolved True. 20/20 is not a general
  solve rate. Yield 1% is definitional (retry-expensive resolutions). Recipient: none verified.
- 37. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-opus-4.6, astropy). LABEL CORRECTION: tarsur385, NOT
  SWE-smith astropy. Recorded source cost $12.46; v8 metered $31.97
  is 2.57x (was 7.46x at the wrong price). Same wrong-price pattern
  as lanes 11, 42, 51. Recipient: none verified.
- 38. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (SWE-bench Lite, gpt-4o-2024-05-13, v1.9 format). v1.9 has no
  per-call usage, so output tokens are severely undercounted and
  context (103.7x) is computed on truncated text. v7 total $23.76
  is close to the source $22.43; the v6 $9.96 was a fallback
  artifact of the missing price key. At the run's configured
  $3/$15 the same tokens would cost $28.68, so $23.76 is not the
  only defensible figure; the file states the basis. Overlap:
  same benchmark instances as lanes 16, 47, 58, 59, 60, 61. Recipient: none verified.
- 40. Source: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
  (OpenHands, Qwen3.6-27B, scale-swe). No recorded dollar comparison
  in the file. Bias: first 20 with at least 8 turns; zero instance
  overlap with lanes 09 and 15 verified programmatically.
  Anomaly: $0.00 context tax at filing is the fallback quirk. Recipient: none verified.
- 41. Source: https://huggingface.co/datasets/nvidia/Open-SWE-Traces
  (v2.0 sweagent, AgnostiqHQ/covalent, Qwen3.8-Flash-Next, first
  alphabetical repo with at least 20 labelled rows). The 21st row
  was resolved and was excluded only by the 20-row cut. Reasoning
  is about 96% of assistant content chars. Do not compare its
  $10.54 per success against priced-model lanes (fallback basis). Recipient: none verified.
- 42. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-opus-4.6, matplotlib). Recorded source cost $9.541; v8
  metered $27.04 is 2.83x (was 8.25x at the wrong price). Next
  qualifying repo in that run, noted in the file: pydata__xarray
  (22 files), which lanes 51, 55, 56, 57 later used. Recipient: none verified.
- 44. Source: https://huggingface.co/datasets/smolagents/gaia-traces
  joined to https://huggingface.co/datasets/smolagents/GAIA-annotated
  (rows 20-39 of the qualifying join). Strict grading 13/20 (65%);
  contains-grading 18/20 (90%) is secondary only. Strict grading
  penalizes formatting ("b,e" vs "b, e", "corn starch" vs
  "cornstarch"); never mix strict and contains figures across
  lanes 24 and 44. Zero overlap with lane 24. Recipient: none verified.
- 47. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (gpt-4o-mini-2024-07-18, v1.9 format). Labels verified against
  report.json with 0 mismatches over all 300 rows. v1.9 output is
  severely undercounted. Tool defaults ($0.91) are 53% of the total.
  v7 note: the verbatim snapshot key reproduces $1.71 exactly, so
  the base-model mapping is no longer needed and the old "$6.19 if
  verbatim" warning is retired. Overlap: 4/20 instance overlap with
  lane 16 (same benchmark, different model/run); trajectories are
  distinct. Recipient: none verified.
- 51. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-opus-4.6, xarray, first 20 of 22 sorted). Recorded source
  cost $8.4055; v8 metered $19.85 is 2.36x (was 6.82x at the wrong
  price). Overlap: same 20 issue ids as lanes 55, 56, 57 (different
  model runs, trajectory overlap zero, issue overlap total).
  Empty signal note: info.submission is empty for all files
  including resolved ones and is NOT an empty-generation signal
  in this dataset. Recipient: none verified.
- 52. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (gpt-5.2-high, sklearn, first 20 sorted). Recorded source cost
  $5.74; v7 metered $10.59 is 1.84x (was 1.10x at fallback). Do NOT
  remap gpt-5.2-high to gpt-5.6. Overlap: many of these sklearn
  issue ids are the same issues as lane 54 under a different model
  (issue overlap high, trajectory overlap zero). Recipient: none verified.
- 53. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-4.5-haiku-high, sklearn, first 20 numeric). First REAL
  scikit-learn/scikit-learn slice in the set (lane 13 was
  imbalanced-learn). Model mapped to the priced haiku-4-5 key at
  identical $1/$5 rates ("high" is an effort variant, same
  treatment lane 12 gave gemini-3-flash-high); v7 rerun moves
  nothing. Recorded source cost $3.67; metered $13.78 is 3.75x.
  Tokens are chars/4 estimates (assistant model/metadata fields
  are None in all 20 files). Top-finding vs waste-lens gap:
  report says retry loops $13.00, waste lens says $11.51; this
  index quotes $11.51 and the $1.49 gap is unexplained in Averth's
  output (wave-5 explains such gaps as retry-path tool spend in
  other lanes, but lane 53 was not decomposed in its addendum). Recipient: none verified.
- 54. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (claude-4.5-opus-high, sklearn, first 20 sorted). First real
  sklearn slice alongside lane 53, and the file's own check of the
  remaining 12 files (11 resolved, 1 failed; full run 31/32, 96.9%)
  shows 20/20 is consistent with the run, not a hidden-failures
  block. Still NOT a general sklearn rate and far above published
  SWE-bench rates; treat the labels as run-specific. Recorded
  source cost $10.72; v7 metered $28.74 is 2.68x (was 0.62x at
  fallback, the opposite direction from the opus-4.6 slices
  because those used real $15/$75 prices). Do NOT remap
  claude-4.5-opus-high to claude-opus-4-6. Recipient: none verified.
- 55. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (gpt-5-mini, xarray, first 20 sorted, same ids as lanes 51/57).
  Recorded source cost $1.0611; v7 metered $1.98 is 1.87x (was
  4.8x at fallback). Least price-anchored total among the tarsur
  lanes at filing; compare only to other fallback lanes, never to
  priced lanes. Do NOT back out a gpt-5-mini price from the ratio. Recipient: none verified.
- 56. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (glm-5-high, xarray, first 20 sorted, same 20 ids as lane 51).
  Recorded source cost $13.1481; v7 metered $33.17 is 2.52x. The
  v7 move from $33.14 is only $0.03 (output $3.00 to $3.20 on
  144,650 tokens). Model events 1,745 vs source api_calls sum
  1,753: the 8 gap is in the source's counts (assistant-message
  count is api_calls minus 1 in the 8 affected files), not a
  converter drop. Do NOT compare $33.17 with lane 51's $19.85 as
  model efficiency: the price bases differ (glm-5 $1/$3.20 vs
  opus-4.6 $5/$25) and the turn counts differ (1,745 vs 504). Recipient: none verified.
- 57. Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
  (minimax-m2.5-high, xarray, same 20 ids as lanes 51/55).
  Recorded source cost $1.60; metered $21.29 is about 13.3x. Why
  the source field is so low is NOT established and must not be
  claimed. Model remains unpriced in v8 (third-party $0.30/$1.20
  consensus was not fetched from MiniMax's own page and was not
  used). Tax is n/a at v7, not $0.00. Recipient: none verified.
- 58. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (deepseek-chat, maxiter 100, run starting 2024-11-09). Full run
  23/300 (7.7%), 73 empty-patch. Sample is 14 django + 6 astropy,
  first 20 with at least 8 unique model calls. 7/20 sample rows are
  empty-generation (no patch produced), including one row whose
  source cost is $0.00 despite 14 recorded calls. Source metrics
  double-count every cost (sample accumulated $0.1713, deduped
  $0.0856); Averth's fallback model $0.63 is about 7.4x the deduped
  source log, which is the fallback-rate gap, not an arithmetic
  error. DeepSeek remains unpriced in v8 (the deepseek-chat alias
  was retired July 2026; current DeepSeek pricing is peak/off-peak
  dual, so no single standard rate was pinned). Overlap: 9/20 ids
  also in lane 16, 3/20 in lane 47 (same benchmark). Recipient: none verified.
- 59. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (o1-mini-2024-09-12, v1.9 format). Full run 57/300 (19.0%).
  Recorded source cost $23.78 for the sample; v7 metered $4.86 is
  far below it, consistent with hidden o1 reasoning tokens (billed
  as output, absent from trajectory text) plus 10,000-char message
  truncation. Pricing the key does not fix that undercount. At
  configured $3/$12 a manual check gives $11.98, still 50% below
  source. Source cost-count mismatch: 43 of 300 rows have action
  count different from cost count, so "one action = one model call"
  is approximate. Overlap: 10/20 with lane 16, 16/20 with lane 38,
  3/20 with lane 47. Recipient: none verified.
- 60. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (qwen-2.5-72b-instruct, maxiter 30, v1.9 format). BIAS FLAG (part
  of the pass, not a footnote): the >=8-action rule excludes every
  early success (file indices 4, 6, 10, 16 resolved with 5, 6, 6, 5
  calls), so 0/20 is NOT a Qwen solve rate. Unfiltered first 20
  are 4/20 resolved; full run is 23/300 (7.7%). Sample is 17 django
  + 3 astropy by file order; 5 attempts have no finish action.
  Message actions count as model events in this lane (11 in the
  sample). Qwen remains unpriced in v8 (open-weight, provider-varying
  proxy prices, no single vendor price). Overlap: 8/20 ids in lane
  16, 6/20 in lane 38, 3/20 in lane 47. Recipient: none verified.
- 61. Source: https://huggingface.co/datasets/OpenHands/openhands-evaluation-outputs
  (gemini-1.5-pro-002, maxiter 30, v1.9 format, run 2024-10-02).
  Full run 40/300 (13.3%). 7/20 attempts hit the 30-action cap and
  were truncated with no finish. Output tokens (25,141 total,
  about 54 per call) are severely undercounted by construction
  (v1.9 stores thought + command, not full responses). Source
  sample cost $27.83 vs Averth $5.16 (about 5.4x lower); neither is
  a bill, and the source log's rate basis is unstated (input and
  output cost rates are both null in metadata.json). Gemini 1.5
  remains unpriced in v8 (absent from Google's models page;
  third-party $1.25/$5.00 was not used). Overlap: 12/20 ids in lane
  47, 2/20 in lane 16, 2/20 in lane 38. Recipient: none verified.
- 62. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (moto, first 20 with at least 8 assistant turns; replaces lane
  32). Empty rate 1/20 (5%; the one flagged row is a 28-turn run
  with no patch, not a view-only run). Overlap: trajectory and
  issue overlap 0/20 vs lane 32; issue overlap 20/20 vs POC 10
  (same moto issues, different model/trajectories); one attempt
  repeats a POC 02 attempt (same issue, same run). Recipient: none verified.
- 63. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (MONAI, first 20 with at least 8 turns, 15 t04 + 5 t03; replaces
  lane 33). Empty rate 3/20 (15%, vs 12/20 in lane 33; all 3 empty
  rows are t03). Sample is still not representative (35% vs the
  9.9% MONAI population rate). Overlap caveat that must travel:
  8 trajectories were already run in lane 33 and issue overlap is
  9 of 16 distinct issues; this lane adds 12 new trajectories,
  not 20. Deduplicate those 8 in any aggregate over lanes 33 + 63.
  Overlap with POC 02 is 0. Recipient: none verified.
- 64. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (dask, first 20 with at least 8 turns, scanned 26; 2 exact POC 02
  attempts excluded by prior use only). 12 distinct issues, all
  GPT-4o-2024-08-06. Dask population 45/306 (14.7%). Empty rate
  1/20 (5%; the one empty case cost $1.41, 11% of the total, and
  produced no patch; empty means no patch, not no spend).
  Trajectory overlap 0 after exclusions; issue overlap 2 of 12
  vs POC 02. Recipient: none verified.
- 65. Source: https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories
  (bokeh, first 20 with at least 8 turns, after 2 prior-use
  exclusions). Bias caveats that are part of the pass: 17 distinct
  issues, but 17 of 20 attempts come from a single t0 maxiter-50 run
  and 4 attempts are the same issue (bokeh-13289) under different
  runs, so 1/20 is NOT a bokeh, GPT-4o, or OpenHands solve rate
  (dataset bokeh rate is 3/60, 5.0%). Empty rate 9/20 (45%):
  below the lane's 50% bias-flag threshold, but the 9 empty
  attempts total only $0.37 while the 11 patch-producing attempts
  total $6.92. Sample empty rate (45%) is above the >=8-turn
  population rate (13/46, 28%) because its shard-0 pilot rows are
  mostly empty. Exclusion did not manufacture the low rate:
  pre-exclusion sample was 2/20, deduped sample 1/20. Final exact
  overlap with POC 02 is 0/20 and with POC 10 is 0/20. Recipient: none verified.

## Dataset-family grouping (never present slices as independent audiences)

- SWE-smith trajectories: 3 A runs (POC 01, 18, 35). Three distinct
  row sets (tool split, tool-split rows 1000-1019, xml-split sunpy);
  trajectory overlap between them is zero, but they are one dataset
  family, not three independent audiences.
- tarsur385 SWE-bench Verified trajectories: 12 A runs
  (11, 12, 36, 37, 42, 51, 52, 53, 54, 55, 56, 57). Distinct repo issue
  sets: django (11), flask/requests (12), sympy (36), astropy (37),
  matplotlib (42), xarray (51, 55, 56, 57: same 20 issues, four
  model runs), sklearn (52, 53, 54: overlapping issue ids, three
  model runs). So 12 runs represent about 7 repo issue sets.
  Model runs are the unit of comparison here, not issues.
- SWE-Gym OpenHands sampled trajectories: 8 A runs (POC 02, POC 10,
  31, 34, 62, 63, 64, 65). Lane 31 is the full pandas run (737
  attempts); the rest are slices of one 6,055-row dataset. Issue
  overlap across slices is extensive by construction (same repos,
  same runs, different models); trajectories are distinct except
  lane 63's 8 repeats of lane 33 (B, not counted) and lane 62's
  single POC 02 repeat. Never sum resolved counts across these
  lanes as if they were distinct attempts.
- Nebius SWE-agent trajectories: 3 A runs (POC 03, 17, 27). Zero row
  overlap (rows 0-100, 100-200, shard-0 rows 400-499). One dataset
  family, two model families (mixed in POC 03, Llama in 17 and 27).
- nvidia Open-SWE-Traces: 4 A runs (13, 15, 40, 41). Distinct repos
  and models (imbalanced-learn, DeepSeek-V4-Flash scale run,
  Qwen3.6-27B scale-swe, covalent); one dataset family.
- OpenHands evaluation outputs (SWE-bench Lite, 300 instances): 7 A
  runs (16, 38, 47, 58, 59, 60, 61). Same benchmark instances across
  runs; trajectories are distinct, issues are not new. Never claim
  instance-disjointness for this family.
- SmolAgents GAIA: 2 A runs (24, 44). Disjoint task slices of one
  join (rows 0-19 and 20-39); one family, two slices.
- Single-run families (1 A run each): Semantic Kernel blog run
  (new-04), Nebius OpenHands trajectories Qwen run (new-09), Simon
  Willison Claude session (new-10), mini-SWE-agent m0at entry (19).
- Total: 3 + 12 + 8 + 3 + 4 + 7 + 2 + 4 = 43 A runs across 11
  dataset families. The honest outreach unit is the run, with its
  family and issue set named, never "43 independent audiences".

## B lanes: clean runs, biased samples, NOT counted

- 26 WebArena: PASS as a clean run, successful-only by construction
  (WebArena-Infinity trajectories, Gemini 2.5 Flash via browser-use,
  first 20 Gemini entries, all elation-clinical easy tasks). 20
  attempts, 20 verifier-passed, $0.46 all estimated (Gemini 2.5
  Flash unpriced/fallback; tool $0.23 is 51% of total), retries 2,
  yield 98%, context 1.0x, step-0 input 0, screenshot vision input
  uncounted. 100% must never be quoted as a success rate.
  Source: WebArena-Infinity trajectories. Excluded because the
  sample is successful-only by construction.
- 30 R2E-Gym: PASS with filter. R2E-Gym/R2EGym-SFT-Trajectories rows
  0-19; success only where the final tool output has an explicit
  success marker AND the final assistant message claims the fix
  works. 13 rows kept, 7 excluded (not failures). $1.57 all
  estimated (model unknown, fallback). 100% completions and 100%
  yield are selection artifacts. Excluded because the sample is
  filtered by the outcome rule itself.
- 32 SWE-Gym moto, literal first 20: all 20 are empty generations
  (4-6 view-only turns, no patch, no test), $0.38, 0 resolved, and
  issue overlap 20/20 with POC 10's moto subset (trajectory
  overlap 0, different model/run). Addendum verified 463 of all
  1,150 moto rows are flagged empty_generation (40%), so this
  block is an extreme concentration of a common failure mode.
  Replaced by lane 62 (>=8 turns). Excluded as an
  empty-generation-dominated block.
- 33 SWE-Gym MONAI, literal first 20 of one t04 run: 12 of 20 empty
  generations ($0.25 total), 20 attempts, 3 resolved (15%; MONAI
  population 95/962, 9.9%), $2.78 estimated, per success $0.93,
  failed $2.03 (73%), retries 7, context 10.7x, tax $1.98, yield
  20%. Zero overlap with POC 02 and lanes up to 30. "15% resolved"
  must not be read as "85% tried and failed on tests".
  Replaced by lane 63 (>=8 turns). Excluded as an
  empty-generation-dominated block.
- 45 R2E-Gym rows 20-39: PASS as a clean run with the same filter
  as lane 30 (8 rows pass the success-marker rule, 12 excluded,
  not failures). $0.73 all estimated (model unknown, fallback),
  context 4.3x, tax $0.00 filed (fallback quirk), yield 100% as a
  selection artifact, retries 0 (none inferred, not none occurred).
  Zero row overlap with lane 30. Excluded because the sample is
  filtered by the outcome rule itself.

## FAIL lanes: no usable trace, no labels, or aggregate-only, NOT counted

Batch 1 (not A, not reference): POC 05 CrewAI (tutorial totals only,
18,432 tokens, then fallback $0.03; growth and yield are artifacts
of one aggregate event); POC 06 Claude Code (Ken Imoto public post,
7h12m, 84 turns, 2,098K tokens, dormant skills 231K; no session
file has ever been obtained; the Claude importer is tested on
example records and Simon Willison's session, never Imoto's);
POC 07 OpenAI Agents SDK (tutorial estimates, about 7,000 input /
3,400 output tokens; cost per accepted outcome UNKNOWN).

Batch 2: new-01 Aider (no usable public trace; patches and aggregate
resolved counts only, no per-call tokens; no Aider importer exists);
new-02 LangChain/LangSmith (public trace links "Trace not found" or
0 runs; no downloadable export); new-03 LlamaIndex (code-only
cookbooks; one span table explicitly "Illustrative example");
new-05 Google ADK (tool-only: eval file converted with zero
invention, 3 cases, 21 tool uses, no model events, tokens, or
verdicts; Averth $0.04 all tool estimates; after wave 3 the report
banners NOT A COST REPORT); new-06 MetaGPT (aggregates only:
31,255 tokens, $0.915-$1.385 ablation); new-07 AutoGen GroupChat
(no usable public trajectory set); new-08 Haystack (no usable trace).

Batch 3: new-14 sympy/astropy (absent from SWE-smith; 76,002 rows
scanned across tool/xml/ticks splits, 0 hits; in-dataset
substitute noted in the file is sunpy, 291 xml rows, used in lane
35); new-20 Agentless (publishes scores and patches only, no
per-step calls; also flagged the missing price key
gpt-4o-2024-05-13, added in v7); new-21 Langfuse msg-01 to msg-05
(do not exist publicly; the AcruxCore repo contains exactly one
trace file, msg-06); new-22 Langfuse msg-07 to msg-12
(expectations and aggregates only; this lane's control run on the
real msg-06 trace found the wave-4 cached-token bug, but the lane
itself has no public traces to run); new-23 other Langfuse project
(partial check only: one Mistral cookbook generation, $0.000092
estimated, not a pass); new-25 Open Deep Research (publishes no
per-step traces; the bench file has only id, prompt, and final
article; a chars/4 conversion understated the project's own
aggregate about 46x on cost at v6 and about 17x after v7 repricing
to $0.27, and about 170x on tokens, and must never be quoted; also
recorded gpt-4.1, unpriced in v6, priced in v7); new-28 Multi-SWE-bench
Java (real trajectories, ByteDance-Seed/Multi-SWE-bench_trajs, 144
MopenHands Claude-3.7 files, first 20 converted, $58.19, context
10.1x, tax $44.89, but NO per-instance resolved label anywhere, so
the filed "100% burned, yield 0%" was an auto-end artifact; at v7
the lane is a cost-only diagnosis: failed $0.00, unknown $58.19,
yield n/a, still NOT a pass); new-29 SWE-Lancer (official release
is dataset plus harness, 463 Diamond tasks, aggregates only;
zero-model diagnostic confirmed the NOT A COST REPORT guard works).

Batch 4: new-39 OpenHands evaluation Claude 3.7 (the run does not
exist: openhands-evaluation-outputs has only SWE-bench_Lite-test
and webarena under outputs, 19 CodeActAgent model folders, none
Claude 3.7; the closest real source, Multi-SWE-bench Python
OpenHands Claude-3.7, has the same label gap as lane 28; diagnostic
$49.75 estimated, at v7 failed $0.00, unknown $49.75, yield n/a,
still diagnostic only); new-43 WorkArena (no public
agent-trajectory set exists in the sources checked; official repo
is benchmark plus live environment; ServiceNow/WorkArena-Instances
is gated task instances, not runs; WebArena-Infinity was
deliberately NOT substituted); new-46 SWE-Gym verifier onpolicy
(the split contains no agent trajectories: every row is a
verifier-training example, resolved True 875 / False 875, judgement
equals resolved in every row by construction, first 20 rows are
outcome-sorted; the quarantined judge-call diagnostic, $0.29 with
100% "completions", is a tautology and must never be quoted);
new-48 tarsur385 Sonnet 4 (no Sonnet 4 run exists in that dataset;
exhaustive listing: exactly 10 model runs, claude-4.5-haiku-high,
claude-4.5-opus-high, claude-opus-4.6, gemini-3-flash-high,
gemini-3-pro, glm-5-high, gpt-5-mini, gpt-5.2-codex, gpt-5.2-high,
minimax-m2.5-high; no substitution made); new-49 Multi-SWE-bench Go
(no per-instance label in any Go family checked; MopenHands
Claude-3.7 Go has cost 0.0 and model None everywhere; MagentLess
and MSWE-agent DeepSeek-R1 Go have no verdict; "submitted" exit
status is not a test pass; wave-5 diagnostic $47.80 estimated,
20/20 outcome_unknown, failed $0.00, yield n/a, context 9.0x, tax
$36.84, still FAIL as a labelled lane); new-50 SWE-Gym SFT
(dataset has a single messages column: no instance_id, model,
resolved, token, or cost column; split name train.success.oss is
not a per-row verdict and is contradicted by the rows; diagnostic
20 attempts outcomes UNKNOWN, $4.05 all estimated, still NOT a
pass; at v7 failed $0.00, unknown $4.05, yield n/a, tax n/a).

## Reference, not counted (ran clean, not outreach POCs)

- POC 04 LangGraph: Averth's own validation graph, not external.
  16 attempts, 12 completed graph runs (75%, completion flags, not
  judged outcomes), $0.178, tool estimates 97.6% of the total,
  failed 26%, retries 21, context 3.3x, yield 64%. Shape only.
- POC 08 Langfuse: AcruxCore public quote agent, single trace
  msg-06, clean (0 retries, 0 failures), context 6.2x. Total
  $0.001972, cached 1,600 tokens (see corrections log). Cost per
  accepted outcome UNKNOWN (population of one, outcome inferred).
  Team-level note only: the AcruxCore team is the source's author
  team, not a verified outreach recipient. Not counted because it
  is a single trace, not a usable POC sample.
- POC 09 OpenTelemetry: Averth's own otel-live set, 2 traces, $3.62
  total, $3.51 of it an assumed human review rate ($70.20/hr, not
  measured). After the wave-1 recovered rule, Trace A and Trace B
  are recovered, not terminally failed, when a non-ERROR span
  starts after the last ERROR span (verify_expected.py 21 of 21).
  Demo only, not external proof.

## Corrections log (old totals that must never be quoted again)

- Langfuse msg-06 (POC 08 and lane 22 control run): filed Averth
  $0.001075 fallback, then $0.001556 at v6 with cached tokens
  read as 0, then $0.001972 at wave 4 after adding
  `input_cached_tokens` to the Langfuse alias list (real trace
  cached 1,600 tokens: 704 + 64 + 704 + 128). The "exact match with
  the vendor quote" claim holds for the real file only after
  wave 4.
- Opus 4.6 price (wave-5b, price table v8): $15/$75 was Opus 4.1's
  price, wrongly carried onto claude-opus-4-6. Anthropic's own
  pricing page lists Opus 4.6 at $5.00 input / $0.50 cached /
  $25.00 output per 1M; Opus 4.1 keeps its own $15/$75 entry.
  Rewritten lanes: 11 ($873.38 to $299.36, per success $4.75 to
  $1.63, failed $186.47 to $64.04, tax $670.70 to $223.57,
  metered-vs-recorded 7.52x to 2.58x vs source $116.05);
  37 ($92.90 to $31.97, per success $8.45 to $2.91, failed $56.21
  to $19.27, tax $66.19 to $22.06, 7.46x to 2.57x vs $12.46);
  42 ($78.75 to $27.04, per success $5.25 to $1.80, failed $25.52
  to $8.74, tax $59.30 to $19.77, 8.25x to 2.83x vs $9.541);
  51 ($57.36 to $19.85, per success $3.59 to $1.24, failed $18.53
  to $6.35, tax $37.50 to $12.50, 6.82x to 2.36x vs $8.4055).
  In each lane only dollars moved; attempts, resolved, and retries
  are unchanged, and failed shares are unchanged except lane 37
  (61% to 60%, because tool estimates do not scale with the price
  correction). New totals sit in the Estimated bucket (vendor
  prices on estimated tokens plus tool estimates).
- Wave-5 price table v7 (verified from vendor pages only; no
  remaps): added gpt-4o-2024-05-13 ($2.50/$10.00, cached $1.25),
  gpt-4o-mini-2024-07-18 ($0.15/$0.60, cached $0.075), gpt-4.1
  ($2.00/$8.00, cached $0.50), gpt-4.1-mini ($0.40/$1.60, cached
  $0.10), gpt-5.2 and gpt-5.2-high ($1.75/$14.00, cached $0.175),
  gpt-5-mini ($0.25/$2.00, cached $0.025), o1-mini and
  o1-mini-2024-09-12 ($1.10/$4.40, cached $0.55),
  claude-opus-4-5 and claude-4.5-opus-high ($5.00/$25.00, cached
  $0.50), claude-4.5-haiku-high ($1.00/$5.00, cached $0.10), glm-5
  and glm-5-high ($1.00/$3.20, cached $0.20). Left unpriced after
  checking: deepseek-chat (alias retired July 2026; current
  DeepSeek pricing is peak/off-peak dual), gemini-1.5-pro-002
  (absent from Google's models page; third-party $1.25/$5.00 not
  used), minimax-m2.5-high (third-party consensus $0.30/$1.20 not
  fetched from MiniMax's own page), qwen-2.5-72b-instruct
  (open-weight, provider-varying proxy prices).
- Wave-5 rerun totals: 38 ($9.96 fallback to $23.76 priced, per
  success $3.32 to $7.92, failed $9.29 to $22.21, tax $0.00 to
  $21.02, retry path $8.86 to $22.45); 52 ($6.34 fallback to
  $10.59, per success $0.37 to $0.62, failed $0.59 to $0.98, tax
  $0.00 to $7.23, source ratio 1.10x to 1.84x vs $5.74);
  54 ($6.62 fallback to $28.74, per success $0.33 to $1.44, tax
  $0.00 to $20.40, retry path $4.68 to $24.00, source ratio 0.62x
  to 2.68x vs $10.72); 55 ($5.13 fallback to $1.98, per success
  $0.51 to $0.20, failed $3.26 to $1.22, tax $0.00 to $0.84,
  source ratio 4.8x to 1.87x vs $1.06); 56 ($33.14 fallback to
  $33.17, per success $2.21 unchanged, tax $0.00 to $25.83,
  retry path $26.54 to $26.57); 59 ($4.43 fallback to $4.86, per
  success $0.63 to $0.69, failed $3.37 to $3.69, tax $0.00 to
  $3.63); 25 ($0.10 fallback to $0.27 priced, still FAIL);
  47 ($1.71 unchanged; verbatim snapshot key reproduces it);
  53, 57, 58, 60, 61, 62, 63, 64 unchanged totals (fallback lanes'
  context tax now prints n/a instead of $0.00); 65 ($7.29
  unchanged, bucket moved from priced $6.63 to estimated-token
  $6.63); 28, 39, 50 failed spend to $0.00 with outcomes UNKNOWN
  and yield n/a (totals unchanged: $58.19, $49.75, $4.05).
- Wave-5 display and definition fixes (no totals moved except as
  noted above): "-$0" priced bucket now prints "$0" (lane 60
  verified); JSONL label-less cases now end outcome_unknown
  instead of failed (lanes 28, 39, 49, 50); chars/4 estimated-token
  spend now lands in the Estimated bucket when flagged (lanes 11,
  37, 42, 51, 65 verified); context tax prints n/a with a reason
  when input prices are missing/fallback instead of $0.00 (lanes
  57, 58, 60, 61 verified, and all other fallback lanes by the
  same code path); the retry-waste finding no longer fires at 0
  retries (kills the lane-34 mislabel class) and now decomposes
  to the waste-lens figure plus retry-path tool spend (lanes 38,
  52, 54 gaps explained as tool spend, not hidden).
- Label corrections (applied throughout this index): lane 13 is
  imbalanced-learn, not scikit-learn; lane 17 is Llama, not GPT-4o;
  lane 18 is a SWE-smith Claude slice, not SWE-agent; lane 15 is
  DeepSeek V4-Flash, not V3; lanes 36 and 37 are tarsur385, not
  SWE-smith; lane 54 is a first real sklearn slice (with lane 53);
  POC 10's file name says AutoGen but no AutoGen data was used;
  POC 02's $7.91 repricing is provisional (see its detail note);
  poc-new-10's filed FAIL is superseded by the index-time v8 rerun
  (see its detail note).
- Standing rules applied in this index: aggregates, tutorial
  totals, no-trace lanes, empty-generation blocks, successful-only
  samples, and auto-ended label-less files do NOT count as usable
  POCs and were never merged into the pass count. Sample resolved
  rates are never quoted as general model, scaffold, repo, or
  benchmark rates. Yield is never conflated with resolved rate.
  Retries are lower bounds with the rule named.
