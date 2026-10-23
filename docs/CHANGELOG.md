# Changelog

## Unreleased

### Corrected

- Price table v8 (verified 2026-10-23 from Anthropic's own pricing
  page, docs.anthropic.com/en/docs/about-claude/pricing):
  `anthropic:claude-opus-4-6` corrected from $15.00/$75.00 to
  $5.00/$25.00 per 1M tokens ($0.50 cached). The $15/$75 figure was
  Opus 4.1's price, wrongly carried onto Opus 4.6 in v6/v7; Opus 4.1
  keeps its own $15.00/$75.00 entry ($1.50 cached) as a distinct
  model. This supersedes the v6/v7 totals for the tarsur385
  Opus 4.6 lanes (11 django, 37 astropy, 42 matplotlib, 51 xarray),
  which were rerun under v8 with addenda in their POC files. The
  v7 changelog note saying the entry was "untouched pending a
  decision" is superseded by this correction.

### Added

- Price table v7 (verified 2026-10-23 from each vendor's own pricing
  page; `PRICE_TABLE_UPDATED` 2026-10-23, America/Chicago local date):
  OpenAI `gpt-4o-2024-05-13` ($2.50/$10.00, $1.25 cached) and
  `gpt-4o-mini-2024-07-18` ($0.15/$0.60, $0.075 cached) as snapshots
  listed on their base-model pages; `gpt-4.1` ($2.00/$8.00, $0.50
  cached) and `gpt-4.1-mini` ($0.40/$1.60, $0.10 cached); `gpt-5.2`
  and `gpt-5.2-high` ($1.75/$14.00, $0.175 cached — high is GPT-5.2 at
  high reasoning effort, same model); `gpt-5-mini` ($0.25/$2.00,
  $0.025 cached); `o1-mini` and `o1-mini-2024-09-12` ($1.10/$4.40,
  $0.55 cached); Anthropic `claude-opus-4-5` and
  `claude-4.5-opus-high` ($5.00/$25.00, $0.50 cached — the dataset
  label is Opus 4.5 at high effort, never a remap to Opus 4.6) and
  `claude-4.5-haiku-high` ($1.00/$5.00, $0.10 cached); Z.ai `glm-5`
  and `glm-5-high` ($1.00/$3.20, $0.20 cached). Deliberately NOT
  added: `deepseek:deepseek-chat` (alias retired July 2026;
  peak/off-peak dual pricing, no single standard rate),
  `google:gemini-1.5-pro-002` (absent from Google's models page),
  `minimax:minimax-m2.5-high` and `qwen-2.5-72b-instruct` (no single
  vendor list price verified). The pre-existing Opus 4.6 $15/$75
  entry is untouched in v7 pending a decision: Anthropic's current
  page lists Opus 4.6 at $5/$25, which would rewrite earlier
  Opus 4.6 lane totals if applied.
- Token provenance: `Tracker.log_model_call` accepts
  `tokens_estimated`; spend computed from estimated (chars/4, not
  recorded) tokens is accumulated as `estimated_token_spend` and
  lands in the Estimated bucket, not Priced, including across the
  ledger round-trip (`LEDGER_ATTEMPT_KEYS` carries
  `estimated_token_cost`). Converters and the JSONL importer accept
  and validate a `tokens_estimated` flag. Reports label the Priced
  bucket "vendor prices on recorded tokens" (legacy traces without
  a provenance flag still land there), name fallback-price, vendor-
  price-on-estimated-token, and tool-estimate contributions in the
  COST BASIS banner, and print an "of which vendor prices on
  estimated tokens" line when that spend is nonzero.
- JSONL outcome-unknown: `averth/importers/jsonl.py` passes
  `auto_end_unknown=True` to `events_to_tracker`, so a JSONL case
  with recorded calls but no end line ends outcome_unknown (cost
  $0 failed, yield n/a) instead of auto-failed. Explicit JSONL end
  events accept `outcome_unknown` (rejected with `success: true`);
  `Tracker.end_attempt` forces `success=False` when
  `outcome_unknown=True`. Other importers keep the historical failed
  auto-end.
- Context-tax completeness: `Tracker.end_attempt` sets
  `context_tax_incomplete` when a nonzero-baseline attempt skipped
  a step because its input price was 0 (fallback-priced or
  vendor-billed calls). Reports print context tax n/a with a
  "growth is not free" note in that case, and "partial" when the
  flag is set and tax is nonzero. The zero-token-first-step case
  still reports tax $0.00 by definition.
- Retry-finding decomposition: `pnl()` now exposes
  `cost_retry_path_failed`, `cost_retry_path_success`, and
  `cost_retry_path_unknown`, and the retry-waste finding decomposes
  its headline into the waste-lens model figure plus retry-path
  tool spend. The text waste accounting prints a "Retry-path
  tools" line when that spend is nonzero, so the finding and the
  lens reconcile on the page.
- `tests/test_wave5.py` — regression tests for every wave-5 fix.

### Added

- `averth trace --format claude` — Claude Code session JSONL importer
  (`averth/importers/claude.py`): one session file at a time, deduplication
  by message id, sidechain records excluded by default, total-context
  mapping so cache reads that dwarf uncached input do not crash or get
  capped, cache-creation tokens priced at full input price (not at the
  cache-read discount, and not at a separate write rate, which Averth
  does not model). No retry inference, no tool spend, no acceptance
  label is invented from a transcript; cost per accepted outcome stays
  UNKNOWN unless labels are joined separately.
- Price table v6: adds `anthropic:claude-haiku-4-5-20251001` at
  $1.00 input / $5.00 output per 1M, verified from Anthropic's Haiku
  4.5 pricing, 2026-10-22.
- Outcome-unknown attempts: a trace with spend but no result marker
  or acceptance label is now reported as OUTCOME UNKNOWN, excluded
  from failed spend and from successes, with yield n/a when no known
  outcome exists, instead of being labelled 100% failed.
- Price table v5: GPT-4o and GPT-4o-mini list prices, Z.ai glm-5.3
  ($1.40 input / $0.26 cached input / $4.40 output per 1M tokens), and
  a `gpt-4o-2024-08-06` snapshot alias at the GPT-4o price (that
  snapshot is listed on the GPT-4o model page, which prices GPT-4o
  text tokens at $2.50 input / $1.25 cached input / $10.00 output
  per 1M tokens, verified 2026-10-22), plus vendor cached rates for
  GPT-4o ($1.25) and GPT-4o-mini ($0.075).
- Vendor cached-input pricing in the tracker: `pricing.MODEL_CACHED_PRICES`
  is now consumed by `Tracker.log_model_call`, so a model with a
  published cached rate (glm-5.3 at $0.26) is priced at that rate, not
  at the generic 0.10 cache-read discount. Reports name the vendor
  cached models instead of claiming a single generic discount rate.
- `averth advise` — BYOK LLM advisor with three modes: `recommend` (the one
  change worth testing, with arithmetic), `explain` (plain-English receipt
  for budget owners), `investigate` (why an attempt cost what it did,
  vs p50/p95). Keys via `AVERTH_ANTHROPIC_KEY` / `AVERTH_OPENAI_KEY`;
  `--show-prompt` prints exactly what the LLM would see without spending
  the call. Caller free text is `[DATA]`-delimited against prompt injection.
- `pilot-sim/` — clean-install prospect simulation: fake 25-ticket
  production traces (Langfuse/LangSmith/OTel), fresh venv, uncached GitHub
  install, numeric receipt assertions (attempts, bucket sums, retries,
  failures, unknown calls).
- `tests/test_chaos.py` — 22 adversarial tests: malformed files, garbage
  costs, null usage, unicode models, absurd token counts, orphan spans.
- `--anomaly` flag on `averth trace` — runaway lens: flags cost outliers
  above p95 with their dominant driver, ranked by dollars. Cost-anomaly
  detection, never attack attribution ("inspect, not accusations").

### Fixed

- Text reports printed "-$0" for the priced bucket when it was a
  tiny negative float (rounding residue): `dollars()` now renders
  any nonzero value below half a micro-dollar as "$0". Exact zero
  keeps the standard "$0.00" rendering.
- The retry-waste finding fired on attempts with zero retries and
  labelled failed-run spend as retry spend: it no longer fires
  when `retries == 0` (failed spend keeps its own finding), and
  when it fires its detail decomposes into the waste-lens figure
  so the two lenses can no longer diverge silently.
- JSONL end events now accept an outcome-unknown outcome without
  requiring a `success` field (a missing success defaults to
  False, and is forced False for unknown outcomes).

### Fixed

- Langfuse importer dropped cached tokens to $0: it now reads cached
  tokens from `usageDetails` / OpenAI-style cached fields and passes
  them through as `cached_input_tokens`. Combined with vendor cached
  pricing above, the reconstructed AcruxCore msg-06 trace now totals
  $0.001972, matching the vendor-computed figure (316 non-cached
  input, 1,600 cached input, 253 output), instead of $0.001075.
  The msg-06 trace used here is reconstructed from the POC totals,
  not the original trace file, which was not left in the workspace.
- OTel importer marked any ERROR span as a terminal failure: an
  attempt is now recovered, not failed, when substantive non-ERROR
  work starts after the last ERROR span, with retries scoped to the
  failed branch or call so post-recovery work is not counted as
  waste. `validation-traces/otel-live/verify_expected.py` now asserts
  the recovered rule for both traces (21 checks pass).
- Reports labelled tokens-x-vendor-price spend "Measured" even when
  tokens were estimated or prices were fallback: that label is
  removed, replaced by "Priced (tokens x vendor prices; token
  provenance unverified)" plus a COST BASIS banner on every report.
  No true "Measured" label exists until token provenance is carried
  through tracker/importers.
- Price table pin test: `unknown:glm-5.3` and `zai:glm-5.3` are now in
  `PINNED_MODEL_PRICES`, and the `gpt-4o-2024-08-06` snapshot alias
  is pinned, so the combined wave-1 tree no longer fails
  `test_all_model_prices_pinned`.
- Price table date was set to the UTC date (2026-10-23) while
  `price_vintage()` compares against local date, so the whole CLI
  failed on US local dates still on Oct 22. Date is now 2026-10-22,
  the local date the verification work ran, and the suite passes
  in America/Chicago as well as UTC.
- Claude importer kept the FIRST record per message id, undercounting
  output by about 99% on a real session where streaming records grow
  (7 then 402): it now keeps the per-field maximum across duplicates.
  The Simon Willison session now totals $0.19 priced, output 9,708,
  outcome unknown, failed $0.00, instead of $0.14 estimated, output
  96, 100% failed.
- Zero-token traces no longer read as cost reports: reports print
  NOT A COST REPORT and replace failed, yield, and context figures
  with n/a when a trace has no model events and no tokens.
- Langfuse importer missed the real cached-token field
  `input_cached_tokens` used in the AcruxCore msg-06 trace, so that
  trace totalled $0.001556 with cached 0 instead of the vendor
  $0.001972. The alias is added, with a regression test, and the
  real trace now totals $0.001972 with cached 1,600.
- Fresh installs crashed: `report.py` imported uncommitted `averth/_money.py`.
- Cases with zero billable events were silently dropped from receipts
  (LangSmith/Langfuse/OTel now emit a `start` marker per case).
- OTel importer never set `usage_known`: missing usage rendered as $0.00
  measured (looking free) instead of flagged unknown.
- Advisor prompt injection: retry reasons/case IDs now `[DATA]`-delimited;
  SYSTEM prompt treats them as data only.


## 0.3.0 — 2026-10-03

### Changed

- Historical policy screening now reports completed runs that crossed a
  threshold and their recorded spend by outcome. It no longer presents final
  run totals as savings or predicts which outcomes a live policy would lose.
- Reports warn when an outcome is inferred from trace execution status and
  when list-price model costs still need reconciliation against an invoice.
- Demo output explicitly identifies simulated tickets and business values.
- Removed the former product-name alias and metadata fallback. Integrations
  and fixtures now use Averth names only.
- Regenerated sample and validation reports with the current accounting
  rules, and made validation scripts runnable from this repository.

### Compatibility

- `simulate_policy()` now returns `flagged_runs`, `flagged_failed`,
  `flagged_success`, `flagged_failed_spend`, `flagged_success_spend`,
  `flagged_spend`, and `flagged_share`. Callers using the old stop/savings
  result keys must update their code and wording.
- The LangChain callback is exported as `AverthCallbackHandler`. Old
  integration aliases and old metadata prefixes are no longer accepted.
- Exported attempts include `outcome_inferred`; older ledgers without it
  continue to load and are treated as inferred when exported again.

### Validation

- 258 unit tests pass with Python 3.9; LangChain and OpenAI optional
  dependencies are installed and their integration tests pass.
- OpenTelemetry trace checks and the archived LangGraph event-stream
  reproducibility check pass. The LangGraph snapshots were regenerated from
  the archived events after the failed-attempt accounting rule changed, so
  that check is not an independent live-run comparison.

### Known limits

- Customer cost per accepted outcome requires their acceptance labels, tool
  costs, labor rate, and billing data. [PILOT.md](PILOT.md) specifies the
  inputs and the claims to withhold when they are missing.
- The mini-SWE public trace computes $17.49 at estimated tokens and list
  prices against $4.55 of recorded spend. Its traces omit cache-read counts;
  this comparison cannot isolate token-estimation error from billing effects.
