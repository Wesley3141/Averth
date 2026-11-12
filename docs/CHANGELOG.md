# Changelog

## Unreleased

### Added

- Zero-config local scan (`averth try` with no trace argument):
  scans the last 10 local Claude Code sessions
  (`~/.claude/projects/**/**/*.jsonl`) and Codex rollouts
  (`~/.codex/sessions/**/*.jsonl`) by mtime, meters them with the
  existing importers, and writes `averth-scan.html`. Codex subagent
  rollouts are excluded by default (counted as skipped, with the
  reason); a session file that fails to parse is skipped with a
  warning counted in the report, never silently dropped, and if all
  fail the command exits 2. No sessions found exits 2 naming the
  directories checked. New `averth/local_scan.py` (discovery only);
  CLI changes confined to `averth/cli.py`.
- "Verified Agent PR Receipt": compact Markdown for pasting into a
  GitHub PR description, written as `<stem>-receipt.md` next to the
  HTML report (same stem rule; `--receipt PATH` overrides) in both
  scan mode and explicit-trace mode, and printed to stdout in scan
  mode. Contents: billed vs estimated cost table, the default-checks
  table, unknown rate, and an honesty footer (no cost per accepted
  outcome; estimates are not bills; default checks are
  trace-observed, not human-written). New `averth/receipt.py`;
  hostile session ids / filenames are escaped so they cannot form
  Markdown links or break tables.
- Default checks (trace-observed): five checks that need no
  human-written checks, judged only on what the transcript shows by
  a judge separate from V0 (evidence-v0 is not installed in the
  meter venv; nothing shells out to it or depends on it). New
  `averth/default_checks.py`: D1 tests executed, D2 build passed,
  D3 files touched vs files tested (stem matching only; actual
  coverage never inferred; the named-test branch is gated on the
  test run's outcome exactly like the bare-suite branch, and only
  the last test command's named files are matched), D4
  duplicate-invocation overhead (never meter retries; 5+ duplicate
  invocations fail — a pinned judgment call, not a measured bar:
  on the 50-trace public audit the duplicate-count distribution
  was {0: 2, 1: 16, 2: 8, 3: 7, 4: 7, 5: 3, 6: 2, 8: 1, 10: 1,
  11: 1, 20: 2}, so 10/50 fail at >=5 and 24/50 at >=3), D5
  trace-recorded vs estimated cost (agree within 5% of the recorded
  figure, inclusive; a partial recorded-cost record is
  NOT OBSERVED; any Codex session is EXTERNAL-UNVERIFIABLE; the
  operator-supplied `--recorded` figure is never used for D5; a
  recorded $0.00 is a recorded cost, not an absence). Evidence
  comes from a new read-only extraction pass over the raw transcript
  (Claude `tool_use`/`tool_result`, Codex `response_item`
  function_call/output, mini-SWE-agent bash fences). Outcome
  signals: Claude `tool_result` `is_error` is treated as the
  transcript's observed outcome (no numeric exit code is present on
  the command records the judge reads; the judge assumes Claude
  Code sets `is_error` from the command's exit status, which is not
  verified against Claude Code's documentation); a command with no
  outcome signal is NOT OBSERVED, never guessed. Mini-SWE-agent
  trajectories carry a per-command exit status (`<returncode>` in
  the following user message), which the extractor parses and
  D1/D2/D3 judge on. Codex `function_call_output` carries no exit code
  in the documented format, so Codex test/build commands are
  NOT OBSERVED unless a record carries an `exit_code` field.
  58 tests in `tests/test_self_serve_scan.py` (discovery with a fake
  home, extraction, every verdict including the NOT OBSERVED paths,
  receipt escaping, CLI scan and explicit-trace behavior).
  `try-it/README.md` documents the scan, the receipt, and the D1-D5
  semantics.
- One-command try-it (`averth try`): meter
  a trace file and write a self-contained shareable HTML report. It
  accepts a mini-SWE-agent trajectory (new `averth/importers/miniswe.py`,
  which reproduces the published case-study events, as parsed event
  records),
  Averth JSONL, or a Langfuse export, with `--recorded` for the
  recorded-cost comparison and `--ledger`/`--checks` for a V0 verdict
  summary (the checks digest is verified and refuses on mismatch).
  `try-it/reproduce-case-study.py` replays the full published
  case-study reproduction from public sources and checks the
  published numbers listed in its PUBLISHED table, plus a gold-patch
  cross-check and consistency checks that are not published numbers.
  It does not recheck the 3.84x 12-run leaderboard gap, the
  0-tool-failures claim, or the $0.9832 unrounded total. See
  `try-it/README.md`.

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

### Fixed

- V0 evidence verifier, frozen checks (rehearsal criterion (c)): the checks file is now hashed
  on its raw bytes at load, re-hashed before the ledger is built and
  written, and a net change between load and re-hash refuses to write
  output with exit code 2. The timing is a single net-change check: an
  edit reverted byte-for-byte before the re-hash escapes detection, as
  does any edit made after the re-hash, in the window where the ledger
  and report are written. A checks file deleted, unreadable,
  replaced by a directory, or replaced by a non-regular file
  between load and the re-hash refuses the same way, except the
  message states the file was unreadable rather than changed, and
  names only the load-time digest, and a refused
  run attempts to remove any stale ledger and
  report from a reused output directory (best-effort; a removal
  failure is warned about on stderr but does not change the exit
  code) instead of leaving a pass-looking report behind. If
  --checks names one of the output files, directly, or through a
  hardlink or symlink, the run refuses with
  exit 2 and attempts to remove the other stale output (if both
  outputs are the same file, both are left in place), leaving
  the colliding file byte-identical. For --checks runs, the digest
  is printed in the Markdown report and on success (observe-only runs
  print none and record null), and the re-hash refusal message states
  how to redo the run: restore the frozen file matching the load-time
  digest and re-run. A checks file that cannot be loaded at all
  refuses with exit code 2 and an `error: cannot load checks file ...`
  line (no digest exists yet; a stale-removal warning may also
  appear on stderr). The stale `evidence-v0/build/`
  copy of the tool, which had none of this fix, is deleted and `build/`
  is now ignored.

- V0 evidence verifier, loader and judge hardening (same change as above):
  a --runs file whose exit_code is a string, float, bool, or list
  refuses at load with exit 2 and stale removal, instead of
  judging a false verdict; a trace model event with bool,
  non-integral float (such as 12.5), negative, or non-numeric
  string token counts, or a bool case_id, refuses
  at load with exit 2, while an integral float such as 12.0 or a
  numeric string such as "10" counts as its integer value;
  deeply nested allowlist, runs, and ingest files refuse with
  exit 2 instead of escaping with an uncaught RecursionError
  (the suite pins a 20000-deep file for each); ingest input nested deeper than 100, measured from the parsed
  file root, refuses with exit 2 at load (so a list-wrapped
  record's own limit is one level lower); below that bound a
  nested record is ingested as a run, so a record the loader
  accepts can always be written; while a deeply
  nested trace line is counted unparseable and tolerated
  (rc 0); a cited run missing its exit code and another
  evidence field now reports every applicable flag and resets its
  evidence identity, and each wrong-typed evidence value in the
  row is neutralised instead of being recorded as if it were real
  (to None, except evidence_source, which takes its "none"
  sentinel); a cited run with a wrong-typed label, command_raw,
  or trust_tier reports an invalid_* flag and never verifies on
  the malformed value; an int or float epoch start_timestamp is
  accepted by design (parse_time documents epoch seconds, millis,
  micros, and nanos) and is normalised to ISO in the row rather
  than recorded verbatim as a bare number, while
  end_timestamp must be a string or null, a deliberate asymmetry,
  since an epoch number is a legitimate timestamp representation
  under the tool's own contract, not a wrong-typed evidence
  value; a missing or unreadable --ingest file
  refuses with exit 2 and stale removal instead of silently
  completing with a clean-looking empty report; an output path
  hardlinked to another file refuses with exit 2 instead of
  overwriting the victim; a --execute run whose interpreter or
  runner binary is missing refuses with exit 2 and stale removal
  instead of a traceback; a non-string task_intent or
  task_intent_source refuses at load with exit 2; fresh output
  files are created without execute permission; an ingested
  record with a wrong-typed label, command, or working directory
  no longer stringifies the value into a run: the label falls
  back to the command, a non-string working directory becomes
  the empty string, and a non-string command means no run at all
  (non-string stdout and stderr are still coerced to str, since
  they feed only the digest), and a list or argv command with a
  non-string element means no run at all instead of joining its
  Python repr into a command; an unreadable file in the target
  repo refuses with exit 2 and stale removal instead of a
  traceback; any input file (--runs, --trace, --ingest, or
  --allowlist, as well as --checks) naming an output file refuses
  with exit 2 instead of being overwritten with ledger or report
  content; outputs are now written to a temp file in the same
  directory and renamed into place, with the mode applied to the
  temp inode before the rename and the output path verified
  after the rename to still name the temp inode, be regular,
  and not be hardlinked, with the written file's mode and bytes
  verified through its open file descriptor, so a hardlink or
  symlink flipped in between the check and each file's own
  write is refused with exit 2 by that file's identity check,
  which holds up to that file's own verification (after both
  files are written the tool re-checks both output paths still
  name the files it wrote, twice in a row, so a swap of the first
  file during the second file's check is caught by the next pass,
  and the ledger is re-checked once more after the two passes,
  so the residual window for each output opens only after that output's last check (the report's last check is in the second pass, the ledger's is that final check)),
  the tool never truncates or
  overwrites a victim and never touches a victim's mode, and a
  rewrite changes the output inode while keeping a pre-existing
  file's mode, masked to the permission bits, so a pre-planted
  setuid stale output cannot make the ledger setuid; the collision check
  runs again after the re-hash, and again after the ledger is built and
  once more after the ledger and report are written, so a checks path
  swapped to an output file with byte-identical content refuses instead
  of being destroyed, and a post-write refusal removes both outputs
  instead of leaving the colliding file in place; a non-string, non-null test_target refuses at
  load with exit 2, and direct judge() calls now validate the
  check_type, the applicability, and the string fields the judge
  copies into a row, as load_checks does; a timed-out --execute
  run is recorded with exit code 124 in both runners; a trace
  event with case_id 0 counts as one case; ingest input nested deeper than 100, measured from the parsed
  file root, refuses with exit 2 at load (so a list-wrapped
  record's own limit is one level lower); below that bound a
  nested record is ingested as a run, so a record the loader
  accepts can always be written; the written file's
  mode and bytes are verified through its open file descriptor,
  including setuid, setgid, and sticky bits, so a temp inode
  whose mode or content is tampered with after
  the write refuses with exit 2 and the poisoned output-path
  entry is unlinked; an int or float epoch start_timestamp is
  normalised to ISO in the judged row rather than recorded
  verbatim as a bare number.

### Added

- Codex CLI rollout importer (`averth trace <file> --format codex`,
  also accepted by `averth advise --format codex`): one rollout file
  at a time, never a directory. Codex token_count snapshots are
  cumulative, so the importer counts deltas between snapshots;
  the model comes from turn_context, and a token_count seen before
  any turn_context is priced at the documented fallback estimate
  and flagged unpriced. Compaction resets the baseline instead of
  going negative. Tool records are not emitted as spend, no retry
  is inferred, and every case ends outcome-unknown, so no
  cost-per-success is quoted from a Codex import alone. The
  rollout format is undocumented and changes across versions, so
  the importer accepts both payload-wrapped and flattened lines
  and validates loudly; dollars are list-price estimates until
  checked against a real Codex bill, and subagent rollouts with a
  replayed parent prefix can overcount (flagged in stats).
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
  bucket "vendor list prices on trace-supplied token counts, not
  verified as provider-recorded usage", name fallback-price, vendor-
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
