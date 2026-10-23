# POC NEW-10: Real public Claude Code session, upgraded Averth

## Verdict: FAIL as a bulletproof run

The CLI did not crash (exit 0, no manual conversion, no fabricated data),
but the run is not clean: it silently undercounts output tokens by
about 99 percent and labels the session 100 percent failed, for reasons
shown below. Do not count this as a clean pass.

## Source (public, not Ken Imoto, not the first-batch example record)

- Source file: https://gist.githubusercontent.com/simonw/bfe117b6007b9d7dfc5a81e4b2fd3d9a/raw/31e9df7c09c8a10c6fbd257aefa47dfa3f7863e5/3f5f590c-2795-4de2-875a-aa3686d523a1.jsonl
- Published as a Simon Willison Claude Code session example, used by the
  claude-code-transcripts tooling. SessionId:
  3f5f590c-2795-4de2-875a-aa3686d523a1.
- Session: 2025-12-19, cwd /private/tmp/hi, task: build a uvicorn+httpx
  HTTP proxy to simonwillison.net with an x-proxied-by header and a
  microsecond response-time header, using the uv-tdd skill.
- Model on every assistant record: claude-haiku-4-5-20251001.
- Local copy (for rerun only, not redistributed as a product claim):
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-10/session.jsonl
- No one contacted, nothing sent, nothing posted, no private data used.
  Averth's Claude importer copies only cost/token metadata, not prompts
  or completions, into the ledger.

## Reproduction (upgraded Averth, commit fd84a0f)

```
cd ~/workspace/averth
python3 -m averth.cli trace \
  ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-10/session.jsonl \
  --format claude \
  --html ~/workspace/goals/agent-p-l-validation/hidden_files/poc-new-10/report.html
```

CLI exit code: 0. Price table: v5 (verified 2026-10-22).
Label printed by Averth itself: COST BASIS: ESTIMATED.

## What Averth reported

- Attempts: 1. Autonomous completions: 0 (0.0 percent, inferred).
  Retries: 0. Human escalations: 0.
- Total cost: $0.14. Priced (tokens x vendor prices): $0.00.
  Vendor-supplied (billed): $0.00. Estimated (fallback prices): $0.14.
- Cost per successful outcome: UNKNOWN as an accepted-outcome metric,
  no outcome labels joined. Averth warns 1 of 1 outcomes were inferred.
- Context growth: 2.3x first-to-last step. Context tax: $0.00.
  Yield: 0 percent of tokens on the terminal path.
  Failed runs: $0.14 (100 percent of spend, zero outcomes).
  Retry path: $0.14 (overlapping lens, not additive).
- Prompt cache: 1,127,558 input tokens cached, saving $1.01 at 10 percent
  of the input rate.
- p50 / p95 / max per attempt: $0.14 / $0.14 / $0.14 (n = 1).

## Importer stats (from parse_claude_session, independently counted)

- Lines total: 123. Assistant lines: 76. Model calls kept: 38.
  Duplicates skipped: 38. Sidechain skipped: 0. No-usage skipped: 0.
  Other lines skipped: 47. Result lines: 0.
- Distinct message ids: 38 (76 assistant lines, 2 records per id).
- Input tokens (uncached): 309. Cache-read tokens: 1,127,558.
  Cache-creation tokens: 29,452. Total context tokens: 1,157,319.
  Output tokens as counted by the importer: 96.
- Raw type counts in the file: summary 2, file-history-snapshot 6,
  user 39, assistant 76. No `result` record anywhere in the file.

## Defect 1: output tokens undercounted by about 99 percent (material)

The importer's dedupe rule keeps the FIRST record per message id.
In this real session that assumption is false for output tokens:
input and cache counts are identical across the two records for an id,
but output grows across the records (for example msg_014RWMroyGPZWsL8BQtG8TzH:
output 7, then 402; msg_01AXTjyyqj2aX3dfX6EBbKLz: 6, then 301).

- Naive sum over all 76 assistant records: output 9,804.
- Last-record-per-id sum: output 9,708.
- Importer (first-record-per-id) sum: output 96.
- Undercount versus last-per-id: 9,612 tokens, about 99 percent.
- Dollar effect at the fallback output price used ($3.00 per 1M):
  about $0.029, so the total should be about $0.17, not $0.14,
  roughly 20 percent low, before any model-price correction.
- Input and cache totals are unaffected here (first = last for those
  fields), so this defect is output-specific, but it is silent: no
  warning is printed, and exit code is still 0.

Fix required: dedupe on the LAST record per message id for output
(or on the record with the largest output for that id), and state
which record wins, instead of keeping the first. The importer's
docstring claim that duplicate records share "one usage object" is
disproved by this session and must be corrected.

## Defect 2: a session with no result marker is reported as 100 percent failed

The file contains no `result` record, so the attempt is auto-ended
with success=False and outcome_inferred=True. The report therefore
says 0 completions, yield 0 percent, and failed runs $0.14 (100
percent of spend, zero outcomes). That is not a proven failure; it
is a missing end marker in a published example file. A reader who
does not know the importer rule will read this as "the whole session
failed", which is not established. The UNKNOWN cost-per-success
warning is correct and must stay attached; the failed-share and
yield headlines must not be quoted without the missing-marker
caveat.

Minor related wart: the importer's stats `sessions` list includes
"claude-session" (from summary/snapshot lines with no sessionId)
alongside the real session id. Harmless here, but it shows stats
are polluted by non-session lines.

## Defect 3: model-alias gap in price table v5 (all dollars estimated)

Price table v5 contains `anthropic:claude-haiku-4-5` at $1.00/$5.00
per 1M, but not the dated variant actually in this session,
`anthropic:claude-haiku-4-5-20251001`. Averth therefore used fallback
prices ($1.00/$3.00 per 1M) and labelled the whole $0.14 ESTIMATED.
That labelling is honest and correct, but it means this run proves
nothing about priced accuracy for dated Claude model ids. Fix: add
dated model aliases (or a prefix/family match) to the price table,
with a vendor source, before quoting any Claude Code dollar figure.

## What did pass

- The new `--format claude` importer runs by itself, exit 0, with no
  manual conversion and no crash on a real session file. That is a
  genuine improvement over the first batch, where a direct Claude
  transcript failed with exit 2 (unknown event type 'assistant').
- Duplicate skipping works for input and cache counts: 38 duplicates
  skipped, and first = last for input, cache-read, and cache-creation,
  so those totals are not double counted.
- The ESTIMATED label, the $0.00 billed figure, and the UNKNOWN
  cost-per-accepted-outcome warning are all printed by Averth itself
  and are correct. Nothing in this run claims a bill, a saving, or
  an accepted outcome.

## Bottom line for the bulletproof test

- Run-cleanly: yes, exit 0.
- Measurement-cleanly: no. Output undercounted about 99 percent,
  failed share and yield are artifacts of a missing result marker,
  and every dollar is fallback-estimated because of a model-alias gap.
- Overall verdict for this lane: FAIL. Do not mark Claude Code as
  bulletproof on the basis of this run. Fix dedupe-last for output,
  handle missing-result sessions without a failed headline, and add
  dated model aliases, then rerun this exact file and compare.

## Index-time verification rerun (2026-10-23, Averth price table v8)

The filed verdict above (FAIL, $0.14 fallback) predates the wave-3 fixes
and was never updated in this file. Rerun for the index from the saved
session file (`hidden_files/poc-new-10/session.jsonl`, Simon Willison
session `3f5f590c-2795-4de2-875a-aa3686d523a1`, model
`claude-haiku-4-5-20251001`) with current Averth, `--format claude`:

- CLI exit 0. Total $0.19, all priced (vendor list prices on recorded
  tokens), billed $0.00, estimated $0.00.
- Attempts 1, outcome UNKNOWN (no result marker, no acceptance label),
  failed spend $0.00, yield n/a, retries 0.
- Context compounding 2.3x, context tax $0.05 (28% of model spend).
- Prompt cache: 1,127,558 input tokens cached, saving $1.01 at the
  10% cache-read rate.
- Saved output: `hidden_files/poc-new-10/averth-output-v8.txt`,
  `hidden_files/poc-new-10/report-v8.html`.

This rerun supersedes the filed $0.14 FAIL verdict for index purposes:
the wave-3 fixes (dedupe keeping per-field max, dated Haiku alias,
outcome-unknown end state) are what moved the total from $0.14
fallback-estimated to $0.19 priced and removed the false failed
headline. Cost per accepted outcome remains UNKNOWN (no label joined).
