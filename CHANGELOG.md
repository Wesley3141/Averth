# Changelog

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
