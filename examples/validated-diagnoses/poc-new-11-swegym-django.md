# POC new-11: django repo slice

## Verdict, in one line

- SWE-Gym django slice: FAIL, it does not exist. Django is not one of
  SWE-Gym's 11 repos, in any SWE-Gym trajectory dataset checked.
- Fallback django slice: PASS as a clean Averth run (exit 0), on a
  real public django trajectory set from a different dataset family,
  SWE-bench Verified trajectories. Do NOT count this as a SWE-Gym
  result. It is a django result, not a SWE-Gym result.

No one contacted, nothing sent, nothing posted, no private data used.
No numbers fabricated, no aggregates converted into events.

## Averth version used

- Repo `~/workspace/averth`, commit `071d0e1`, price table v6
  (verified 2026-10-22), with Claude dedupe max, outcome-unknown,
  and zero-token guard.
- Command, from `~/workspace/averth`:
  `.venv/bin/python -m averth.cli trace
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/events.jsonl
  --format jsonl --html report.html`
- CLI exit code: 0.

## Part 1: why the SWE-Gym django lane fails

SWE-Gym's repos are exactly 11, and django is not one of them.
Checked, with repo counts read from the files themselves:

- `SWE-Gym/OpenHands-Sampled-Trajectories` (all 3 shards, 6,055
  rows): Project-MONAI, bokeh, conan-io, dask, facebookresearch,
  getmoto, iterative, modin-project, pandas-dev, pydantic, python.
  Django rows: 0 in every shard.
- `SWE-Gym/OpenHands-SFT-Trajectories` (491 rows, messages only,
  repo read from the uploaded-files path in the first user message):
  same 11 repos. Django rows: 0.
- `SWE-Gym/OpenHands-Verifier-Trajectories` (mixture 2,636,
  offpolicy 886, onpolicy 1,750 rows, `resolved` present, no
  instance_id column, repo read the same way): same 11 repos.
  Django rows: 0.
- The first batch's SWE-Gym sample (POC 10) is the same dataset
  family: 229 Claude attempts from shard 0, also with 0 django.

So "SWE-Gym, django" is not a slice that exists to run. Any file
claiming a SWE-Gym django run would be fabricated. This lane is
reported as FAIL on SWE-Gym, and the fallback below is reported
separately, with its own source, so the parent can decide whether
to count a django POC at all.

## Part 2: fallback source (NOT SWE-Gym)

- Source: https://huggingface.co/datasets/tarsur385/swebench-verified-trajectories
- Slice: `swebench_verified_raw/claude-opus-4.6/django__django-*`,
  231 files, 231 unique instance_ids, one attempt per instance.
  This is a SWE-bench Verified trajectory set, mini-swe-agent 1.1
  format, model run claude-opus-4.6. It is NOT SWE-Gym, and it is
  distinct from first-batch POC 10 (different dataset family,
  different model, django only) and from batch-3 agent 12
  (flask/requests, different repo).
- Per-step input is real: each traj file has a `messages` list
  (system, user, assistant with bash tool_calls, tool observations)
  and `info.resolved` plus `info.scores.resolved` as the dataset's
  own solved label, and `info.exit_status` (Submitted 226,
  LimitsExceeded 5).
- What is NOT in the source: per-call token usage. Assistant
  message metadata is None. So tokens are estimated, exactly as in
  POC 10 and POC 3, and labelled as such. Nothing was converted
  from an aggregate: the source's own `info.model_stats` totals
  (instance_cost sum $116.05, api_calls sum 5,728) were NOT turned
  into events; they are used only as a cross-check below.

## Conversion (mechanical, converter in hidden_files)

- Converter: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/convert.py`
- Events: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/events.jsonl`
  (12,876 events: 5,728 model, 6,175 tool, 742 retry, 231 end).
- Rules, fixed: system/user/tool content lengths accumulate into
  context chars; one model event per assistant turn, input =
  context chars // 4, output = (assistant content chars + tool
  argument chars) // 4; one tool event per tool_call (function
  name, always "bash" in this slice); a retry event before the
  next assistant turn when the preceding tool observation contains
  the literal string "Traceback", a recorded failure signal, the
  same rule as POC 10; end event success = `info.resolved`.
- Model mapping, documented: the traj label is
  `info.docent.model_label` = "claude-opus-4.6" (assistant message
  model fields are None). Averth's price table key is
  "anthropic:claude-opus-4-6" at $15 input / $75 output per 1M
  tokens, so the converter emits model "claude-opus-4-6". Same
  model, hyphenated key; no price invented.
- Cross-check that the conversion did not drop calls: model events
  5,728 exactly equal the source's api_calls sum 5,728.

## Averth run numbers (fallback django slice)

- Attempts: 231
- Autonomous completions (dataset resolved label): 184 (79.7%)
- Failed attempts: 47 (20.3%)
- Retries: 742, all with reason "traceback in previous tool
  observation"
- Total cost: $873.38
- Model spend: $861.03, all anthropic:claude-opus-4-6 (100%)
- Tool spend: $12.35, all Averth built-in per-call estimates for
  bash, flagged as estimates in the report, not a measured tool bill
- Cost per successful outcome, fully loaded: $4.75
  (model terminal $0.65, retry path $4.03, tool $0.07, human $0.00)
- Failed runs: $186.47 (21% of spend, zero outcomes)
- Retry path spend (overlapping lens, not additive): $740.91
- Context compounding: 6.9x input growth first to last step;
  context tax $670.70 (78% of model spend)
- Yield: 13% of tokens on the terminal path
- Heavy tail per attempt: p50 $1.68, p95 $17.99, max $30.68;
  top 5% consumed 32% of budget
- Human review: $0.00, none measured; the $70.20/hr loaded rate
  printed by Averth is an assumption, not a measured input

## Cost basis, honestly

- Averth printed: COST BASIS: ESTIMATED, with the banner "Do not
  quote this report as measured spend or as a bill."
- Data quality: Priced (tokens x vendor prices; token provenance
  unverified) $861.03, Vendor-supplied (billed) $0.00, Estimated
  (fallback prices) $12.35, Unknown none.
- Tokens are chars/4 estimates, NOT recorded usage. Dollars are
  list-price estimates at Opus $15/$75, NOT a bill.
- No "-$0" priced bucket is present (priced bucket is $861.03),
  and no $0 context tax is present (context tax is $670.70).
  Those two artifacts were checked for and are absent.
- Zero-token guard did not trigger: the trace has tokens throughout.

## Material discrepancy, not hidden

- The source's own `info.model_stats.instance_cost` sums to
  $116.05 across the same 231 attempts. Averth's chars/4 estimate
  is $873.38, about 7.5x higher.
- Likely causes, stated as hypotheses, not verified: Averth
  accumulates full history into context with no truncation and
  applies no cache discount, while the source's cost field
  presumably reflects actual API usage (with whatever caching and
  truncation the real run used). The Averth figure therefore
  overstates what the source says the run cost.
- Consequence: quote $873.38 only as "Averth chars/4 list-price
  estimate", never as what anyone was charged, and never
  alongside the source's $116.05 as if they were the same thing.
  A real billed-cost POC would need recorded token usage, which
  this source does not publish in its messages.

## PASS / FAIL

- SWE-Gym django: FAIL, no such slice exists in any SWE-Gym
  trajectory dataset checked.
- Fallback django (SWE-bench Verified, claude-opus-4.6, 231
  attempts): PASS as a clean Averth diagnosis run. Exit 0, real
  per-step input, attempts >= 10, totals reported, cost basis
  labelled ESTIMATED with priced/estimated split shown, and the
  -$0 / $0-context-tax artifacts checked and absent.
- This is a clean-run diagnosis test, not a value POC: no change
  was applied or measured, and cost per success here is an
  estimate built on estimated tokens, not a billed saving.

## Files

- Result: `~/workspace/goals/agent-p-l-validation/files/poc-new-11-swegym-django.md`
- Converter: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/convert.py`
- Events: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/events.jsonl`
- Averth output: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/averth-output.txt`
- HTML report: `~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-11/report.html`

## Wave-5b addendum (price-table v8, 2026-10-23) — supersedes the totals above

Correction: Anthropic's own pricing page (docs.anthropic.com/en/docs/
about-claude/pricing) lists Claude Opus 4.6 at $5.00 input / $0.50
cached / $25.00 output per 1M tokens. The v6/v7 table carried Opus
4.1's $15/$75 rates onto Opus 4.6, so every dollar above was
overstated 3x on the model side. Opus 4.1 is a distinct model at
$15/$75 and keeps its own entry. The v8 rerun below uses the
corrected price and flags the chars/4 tokens as estimated, so model
spend now lands in the Estimated bucket, not Priced. Attempts 231,
resolved 184, retries 742 are unchanged; only dollars move.
Fresh report: hidden_files/poc-new-11/averth-output-v8.txt and
report-v8.html; pre-correction events preserved as events-v7.jsonl.
- Total $299.36 (was $873.38), all Estimated: model $287.01
  (exactly $861.03 / 3) plus $12.35 tool estimates.
- Cost per successful outcome $1.63 fully loaded (was $4.75).
- Failed runs $64.04 (21% of spend, share unchanged; was $186.47).
- Context tax $223.57 (was $670.70; 78% of model spend, unchanged
  share). Yield 13%, retries 742, context 6.9x unchanged.
- Metered vs recorded: source instance_cost sums to $116.05, so
  Averth v8 is 2.58x the source field (was 7.52x). Still not a bill:
  dollars are list prices on chars/4 estimated tokens with full-
  history accumulation and no cache discount. Never quote $299.36
  as what anyone was charged, and never quote the old $873.38.
