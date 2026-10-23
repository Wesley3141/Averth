# Changelog

## Unreleased

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
