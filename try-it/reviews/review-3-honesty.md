# Review 3 — Honesty of labels (adversarial, angle: HONESTY OF LABELS)

- Reviewer: adversarial reviewer 3 of 5
- Scope: `averth try`, `try-it/reproduce-case-study.py`, generated reports, README, CLI help
- Branch: `try-it` (unmerged; nothing merged, pushed, deployed, or sent)
- Sources read in full: `try-it/README.md`, `averth/importers/miniswe.py`,
  `averth/try_report.py`, the `try` subcommand in `averth/cli.py`,
  `averth/report.py` (the shared meter report `try` reuses),
  `averth/importers/common.py` (event schema + `tokens_estimated` semantics),
  `averth/tracker.py` (provenance buckets, relevant lines),
  `try-it/.test-out/report.html`, `try-it/repro-work/report.html`,
  `tests/test_try_it.py`, `try-it/reproduce-case-study.py`,
  published case study source `~/workspace/averth-site/case-study-1.html`.
- Live probes run (scratch in `try-it/reviews/scratch-3/`): full `try` run with
  `--recorded 0.3205 --ledger … --checks …` (stdout saved as `stdout-full.txt`,
  HTML as `stdout-run.html`); `--ledger` without `--checks` (`no-checks.html`);
  `--recorded 99` (`wrong-recorded.html`); bare run with neither flag
  (`bare.html`); JSONL input (`jsonl.html`); digest mismatch against a
  pre-existing `--out` file (`stale-target.html`); programmatic check of
  `pnl()` buckets for the trajectory.
- **Verdict: FAIL.** Four FAIL-driving defects (D1–D4) plus two major defects
  (D5, D6). The report is honest in its README's "does and does not claim"
  section and in its bottom-of-page provenance note, but the numbers a stranger
  actually reads first — the top card, the Data quality buckets, the stdout
  `Fully loaded` line, the recorded-cost sentence, the V0 table — mislabel
  estimated dollars as priced/recorded and accepted outcomes that never
  happened. The case-study page discloses the chars/4 basis adjacent to the
  priced figure; the try report discloses it only at the very bottom, and
  stdout not at all.

## What holds up (credit where due — checked, not assumed)

- Digest mismatch refuses before writing anything new: verified live
  (exit 2, `averth: error: checks digest mismatch: … refusing to present
  these verdicts under those checks`), and `tests/test_try_it.py`
  `test_try_digest_mismatch_writes_no_report` covers the fresh-directory case.
- `--checks` without `--ledger` is a clean error; `--recorded <= 0` is rejected;
  missing `--model` / missing file are clean errors (all verified live or in tests).
- The "How this report was made" note for traj input is exactly honest:
  "Token counts are characters/4 estimates from the trajectory text, not
  provider-recorded usage; the dollars apply vendor list prices to those
  estimates." (`averth/cli.py`, `_cmd_try` traj `source_note`.) The problem is
  placement and reach (D1), not wording.
- The recorded-comparison paragraph does say "Averth does not claim the
  estimate is the bill. Reconcile against the invoice before calling any
  metered figure actual spend." (`averth/try_report.py:127-134`.) The problem
  is the sentence before it (D3), not this one.
- The V0 unverified-digest wording exists in the HTML (D5 is about where it
  lives and that stdout omits it entirely).

---

## D1 — FAIL driver: $0.91 is labelled "Priced (vendor prices on recorded tokens)" when the token counts are characters/4 estimates, never recorded

**The mechanism, verified programmatically.** The converter deliberately does
not set the flag the tracker's own Wave 5 machinery provides for exactly this:

> `averth/importers/miniswe.py:18-21` — "The events deliberately do NOT set
> ``tokens_estimated``: the published case-study numbers ($0.91 priced, $0.07
> estimated) were produced from events without that flag, and the acceptance
> test for the try-it requires the published numbers to reproduce exactly."

The justification is circular: the numbers were produced by the same
mislabeling, so preserving them byte-for-byte preserves the mislabel. The
event schema documents what the flag means
(`averth/importers/common.py:34-36`): "`tokens_estimated=True` marks counts
estimated by the converter (characters/4 or similar), not recorded from a
provider response: the dollars still use vendor list prices, but pnl()
reports them as Estimated, never as Priced/recorded." The converter bypasses
it anyway, and the fixture events file has the same gap (verified: no
`tokens_estimated` key in any of the 35 model events in
`try-it/fixtures/trace-events-django-15930.jsonl`), so `averth try` on the
published JSONL reproduces the same mislabel with an even weaker source note.

Measured on the trajectory (live probe):

- `pnl()["estimated_token_spend"]` is `0.0`
- `pnl()["data_quality"]` is `{'measured': 0.913206…, 'billed': 0.0,
  'estimated': 0.07, 'unknown_calls': 0}`

**Offending wording, verbatim.** In both generated reports
(`try-it/.test-out/report.html`, `try-it/repro-work/report.html`) and in
stdout:

> "Priced (vendor prices on recorded tokens; legacy traces without a provenance flag still land here): $0.91"

and the stdout twin (`averth/report.py:180-182`):

> "Priced (vendor prices on recorded tokens; legacy traces without a provenance flag still land here): $0.91"

"Recorded tokens" is false for this input: the trajectory supplies no token
counts at all — the converter manufactures them as `characters // 4`
(`miniswe.py`, `input_tokens: prior_chars // 4`,
`output_tokens: len(text) // 4`). The parenthetical about "legacy traces
without a provenance flag" is a mechanism excuse, not a disclosure: no reader
can tell from the report that *this* trace is one of those legacy traces.
"Trace-supplied token counts" (stdout COST BASIS banner, `report.py:64-66`)
commits the same error in the other direction — it implies the trace supplied
counts, which for `.traj.json` input it did not.

**Why the case-study comparison does not save it.** The case-study page puts
the disclosure in the same section as the figure:

> "Within it, $0.91 is priced (vendor list prices on trace-supplied token
> counts Averth does not verify) and $0.07 is estimated (built-in per-call
> tool estimates). The trace's token counts are themselves estimates
> (characters/4), and the trace records no prompt-cache counts."

The try report discloses characters/4 exactly once, in the "How this report
was made" section at the very bottom of the HTML (line 111 of the generated
file, after the V0 section), and **nowhere in stdout** — I grepped the bare-run
stdout for "characters" and got zero matches. A reader of the top half of the
report (cards, Data quality) or of stdout alone takes away "$0.91 priced on
recorded tokens". That is the sentence that will mislead a stranger, and it
is the first dollar figure in the report. The README repeats the mislabel as
fact (`try-it/README.md:71`): "The HTML report … shows cost per completed
run with priced/estimated/billed provenance ($0.91 priced, $0.07 estimated,
$0.00 billed)".

**Exact fix wanted (one of the two; no third option).**

1. Preferred: set `"tokens_estimated": True` on the converter's model events
   in `miniswe.py` (and add the flag to the fixture events file). The $0.91
   then moves to the Estimated bucket; the total stays $0.98 but the split
   becomes $0.00 priced / $0.98 estimated. Update the case-study page, the
   README, and `tests/test_try_it.py::test_meter_numbers_match_the_published_case_study`
   (which currently asserts `dq["measured"] == 0.91`) to the corrected split.
   This is the fix the tracker's own Wave 5 design already implements; the
   byte-for-byte fixture test must be updated to the honest fixture, not used
   as a reason to keep the dishonest one.
2. Minimum, if the authors insist on preserving the $0.91 "priced" figure:
   change the Data quality line (both `report.py` text and HTML paths) for
   any input whose counts are not flagged recorded to read, adjacent to the
   dollar figure, "Priced (vendor list prices on token counts estimated as
   characters/4 from the trajectory text; NOT provider-recorded usage)"; delete
   the words "recorded tokens" from that line for unflagged traces; and put
   the characters/4 disclosure into the stdout COST BASIS banner itself, e.g.
   "…vendor list prices applied to token counts estimated as characters/4
   from the trajectory text (not recorded usage)". Disclosure at the bottom
   of the page does not cure a false label at the top.

Also fix the adjacent falsehood in `averth/report.py:81` (stdout) /
`report.py:519` (HTML): "MODEL COST BASIS: versioned list prices and reported
token/cache usage" — for traj input no token or cache usage was reported by
anything; the trace reports no usage at all. For traj input it must say the
counts are converter-estimated, not "reported".

---

## D2 — FAIL driver: the report claims "per accepted outcome" for a run no human accepted — in the top card, the section heading, and stdout — contradicting its own disclaimer at the bottom

**Offending wording, verbatim.** In both generated reports:

> `<div class="k">Fully loaded</div><div class="v">$0.98</div><div class="s">per accepted outcome</div>`

> `<h2>Cost per successful outcome</h2>`

and in stdout (verified in the bare run, `scratch-3/bare.html` run's stdout):

> "Cost per successful outcome:"
> "  Fully loaded:         $0.98"
> "Reopened:              0 accepted outcomes reopened"

"0 accepted outcomes reopened" asserts accepted outcomes exist. None do: the
case-study page is explicit that C3 (human review/acceptance) is
EXTERNAL-UNVERIFIABLE — "No human reviewed this run."

**Why the report's own guard never fires.** `averth/report.py:441-447`:

> `all_inferred = (p["attempts"] > 0 and p.get("inferred_outcomes", 0) >= p["attempts"])`
> `per_success_label = ("per inferred success (no outcome labels joined)" if all_inferred else "per accepted outcome")`

For a traj run, `miniswe.py` emits an end event with `success` derived from
`info.exit_status == "Submitted"` — a patch *submission*, not an acceptance
label — so `outcome_inferred` is `False` (verified: `pnl()
["inferred_outcomes"] == 0`, attempt `outcome_inferred == False`) and the
guard that would relabel the card never triggers. The inferred-outcome banner
(`report.py:449-456`) likewise never renders. The try extras then contradict
the card three screens later: "No human accepted this run, so no cost per
accepted outcome is claimed. Cost per completed run is $0.98 ESTIMATED, not
a bill." (`averth/try_report.py:192-194`.) A stranger reads the card, not the
footnote. The heading "Cost per successful outcome" is the shared meter's
default; `try` inherits it unchanged.

**The "no cost per accepted outcome" disclaimer is also missing from stdout
entirely.** In the bare run (no `--recorded`, no `--ledger`), stdout contains
no try-specific disclaimer at all: grep for "accept", "characters",
"recorded", "per completed" across the bare stdout returned only the COST
BASIS banner and "Reopened: 0 accepted outcomes reopened". `try_summary_lines`
(`try_report.py`) returns `[]` when neither `--recorded` nor `--ledger` is
given, so the most common invocation prints the unqualified
"Cost per successful outcome: … Fully loaded: $0.98" and nothing else. The
README's claim (`README.md:88`) — "No cost per accepted outcome is claimed.
`averth try` never joins human acceptance labels, so it reports cost per
completed run" — is true of the bottom-of-page note and false of the card,
the heading, and stdout.

**Exact fix wanted.** `averth try` must not reuse the shared report's
"per accepted outcome" label. Add a try-specific label override threaded
through `_report_and_html` / `report_text` / `write_html` (or an equivalent
parameter): the card sub-label becomes "per completed run", the heading
becomes "Cost per completed run", the stdout block becomes "Cost per
completed run (not per accepted outcome — no human acceptance labels were
joined):", "Reopened: 0 accepted outcomes reopened" becomes "Reopened: 0"
(or is omitted for try runs), and the sentence "No human accepted this run,
so no cost per accepted outcome is claimed" is printed on stdout on every
`try` run, not only in the HTML extras. Until then the top of the report
asserts the thing the bottom denies.

---

## D3 — FAIL driver: `--recorded` is operator-typed, unverified input, but the report states it as a fact ("The run cost $99 recorded") with no source and no "operator-supplied" qualifier

**Verified live.** `averth try … --recorded 99` produced, on stdout:

> "Recorded cost: $99; metered estimate per completed run: $0.98 ESTIMATED (0.01x)"

and in the HTML (`try_report.py:127-134`):

> "The run cost $99 recorded, and a meter working from this trace alone would
> estimate $0.98. Averth does not claim the estimate is the bill. Reconcile
> against the invoice before calling any metered figure actual spend."

$99 was invented by me on the command line. The report presents it as a fact
about the run, in the same declarative voice as the metered figure, with no
named source anywhere in the report — no filename, no "operator-supplied",
no "claimed to be from per_instance_details.json". The README says the
recorded cost comes "from the run's own record" (`README.md:85-86`: "The
recorded cost comes from the run's own record, not from the meter. The meter
never invents a recorded cost: without `--recorded`, no comparison is
shown.") — true only in the sense that the *operator* supplies it; the meter
never checks it. There is no validation beyond `> 0` (`cli.py`, `_cmd_try`;
`try_report.py:build_try_extras`).

**The corroboration the code deliberately discards.** The trajectory itself
carries the recorded cost, and it agrees exactly with the leaderboard
(verified live: traj `info.model_stats.instance_cost` =
`0.32052914999999993`; leaderboard `per_instance_details.json` `cost` =
`0.32052914999999993`). The converter refuses to use it
(`miniswe.py`, module docstring, final paragraph): "The trajectory's own
``info.model_stats.instance_cost`` is NOT used here: it is the leaderboard's
recorded cost, and the honest place for it is the try report's recorded-cost
comparison (``--recorded``)". That is a defensible separation — but then the
comparison must label the figure for what it is (an operator assertion) and,
where the trace carries its own figure, must cross-check or at least surface
it. Currently a stranger who passes a wrong number gets a confident false
statement in a shareable report, and nothing in the report lets the *recipient*
tell the $0.3205 came from the leaderboard rather than from the sender's
keyboard.

**Exact fix wanted.** (a) Relabel everywhere the figure appears: HTML table
row "Recorded cost (operator-supplied via --recorded; not verified by
Averth)", stdout line "Recorded cost (operator-supplied): $…", and rewrite
the declarative sentence to "The operator supplied $X as the recorded cost
for this run; a meter working from this trace alone would estimate $Y."
unless the figure is corroborated. (b) When the traj carries
`info.model_stats.instance_cost`, surface it and warn on mismatch (or refuse
on gross mismatch): the one corroborating record the trace itself offers
should not be silently ignored while an unverified typed number is printed
as fact. (c) Fix the help text (`averth/cli.py:90`): "Recorded cost for the
same run, from the run's own record (e.g. a leaderboard
per_instance_details.json). Shown next to the metered estimate." — replace
with "Operator-supplied figure claimed to be the recorded cost for the same
run (e.g. from a leaderboard per_instance_details.json). Averth does not
verify it; shown next to the metered estimate." Same correction to the
`cli.py` module docstring ("``--recorded`` adds the run's recorded cost next
to the metered estimate") and to `README.md:85-86`, which must say the
figure is operator-supplied and unverified.

---

## D4 — FAIL driver (V0): the try report's V0 table cites no observation — the sentence "proves only what its cited observation shows" points at nothing — and it drops the check text the ledger already carries

The case-study page earns its VERIFIED rows: per check it shows the full
check text ("C1: the FAIL_TO_PASS test passes with the agent patch") and the
evidence ("Run exit 0, output digest sha256:081d…"). The try report shows
neither. `load_v0_ledger` captures both (`try_report.py:76`
`criterion_text`, `:78` `exit_code`) — and the ledger itself carries
`criterion_text`, `command`, `exit_code`, `output_digest`, `evidence_id`,
`after_final_edit` (verified by reading
`try-it/repro-work/v0-run-repro/evidence_ledger.json`) — but
`build_try_extras` renders only three columns (`try_report.py:148-154`):

> `"<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (criterion_id, status, scope_limitation)`

A recipient sees "C1 — VERIFIED — Proves only that this one test passes on
this revision with this patch, on SQLite." They cannot see what C1 *is*
(the criterion text is dropped), what command ran, what its exit code was,
or any output digest. The sentence underneath
(`try_report.py:178-179`) — "A VERIFIED row proves only what its cited
observation shows." — is self-referentially false in this report: there is
no cited observation. The scope-limitation column partially carries the
meaning, but a scope limitation is not the observation; it is the caveat on
an observation the reader never sees. For a stranger receiving only this
HTML, "VERIFIED" is an appeal to an unseen ledger.

**Exact fix wanted.** Render, per judgment row, the criterion text, the
command (or evidence_id), the exit code, and the output digest (truncated
with full value available, e.g. title attribute), in the same table — i.e.
make the try report's V0 section match the case-study page's table, which
has Check / Result / Evidence columns. Do not ship a "VERIFIED" that cannot
be checked from the report itself.

---

## D5 — Major: with `--ledger` but no `--checks`, stdout reports the verdicts with no digest qualifier at all, and the HTML caveat is buried in footer small print

Verified live (`scratch-3/no-checks.html` run): stdout ends with

> "V0 verdicts: VERIFIED 2, EXTERNAL-UNVERIFIABLE 2; unknown rate 50.0%"

with no mention that the digest was not verified. The only caveat is in the
HTML, in a `<p class="s">` footer line alongside the ledger id and timestamp
(`try_report.py:160-164, 187`):

> "Checks digest shown but not verified (no --checks file given); pass
> --checks to verify the verdicts were judged under those checks."

A reader who copies the stdout line, or skims the V0 table, takes away
unqualified verdicts. The heading "What the evidence supports (V0)" carries
no qualifier either.

**Exact fix wanted.** (a) `try_summary_lines` must append the digest state
to the stdout V0 line in both cases: "…; checks digest verified against the
checks file" or "…; checks digest NOT verified (no --checks given — verdicts
may have been judged under different checks)". (b) The HTML V0 heading must
carry the qualifier ("What the evidence supports (V0) — checks digest not
verified"), not only the footer small print. (c) Fix the `--ledger` help
(`cli.py:92`): "V0 evidence ledger JSON to summarize in the report." — add
"Without --checks the ledger's checks digest is shown but not verified."

**Related, same defect family — stale report survives a refused run.**
Verified live: with a report already present at `--out`, a digest-mismatch
run exits 2 with the correct error, but the old file remains in place
(`scratch-3/stale-target.html`, still containing VERIFIED content). The
existing test (`test_try_digest_mismatch_writes_no_report`) only covers a
fresh directory, so this passes the suite and misleads in practice: the
operator (or a recipient) can read yesterday's report as if it were the
refused run's output. Exact fix wanted: on a digest-mismatch refusal the CLI
must print to stderr that a previous report remains at `<path>` and must not
be treated as the current run's output; add a test with a pre-existing `--out`
file asserting that warning; and stamp the meter report itself with a
generation timestamp so a stale file is detectable from its own contents
(the report currently carries only the ledger's `generated_at`, not its own).

Minor, same section: the counts table omits zero rows — only verdicts present
in `counts` are rendered (`try_report.py`, `for name in order if name in
counts`), so FAILED 0 and NOT OBSERVED 0 never appear, unlike the case-study
page which states "0 Failed" explicitly. Render all five rows with zeros.
Also "Runs recorded: 2" omits the superseded count the case-study page states
("Runs recorded: 2, of which superseded and retained, never cited: 0").
Render it. And the `digest_verified is False` branch (`try_report.py:158`)
is dead code — `load_v0_ledger` raises on mismatch and never returns False —
so the "Checks digest mismatch." label can never render; delete it or make
the function actually return False somewhere. Not a FAIL driver on its own.

---

## D6 — Major: the reproduce script claims to check "every published number" but one of its checks is a tautology, and it checks no report wording at all

**The fake check.** `try-it/reproduce-case-study.py:281`:

> `check("meter billed", 0.0, PUBLISHED["meter_billed"])`

It compares the literal `0.0` to the literal `0.00`. It parses neither stdout
nor the HTML. If the meter ever started reporting billed dollars, this check
would still print PASS. Every neighbouring check parses real output
(`money("Fully loaded")`, `money(r"Model/API \(terminal\)")`,
`money("Tool calls")`); the billed one checks nothing. A script whose exit
code 0 is supposed to mean "every number matched" must not contain a check
that cannot fail.

**The overclaim.** The module docstring says the script "checks every
published number" and "Exit code 0 means every number matched". The
`PUBLISHED` dict (lines 66-82) holds 15 numbers. The case-study page publishes
more that the script never touches: 72 messages, 35 tool calls, 0 tool
failures, FAIL_TO_PASS 1/1, PASS_TO_PASS 88/88, the 3.84x 12-run gap, the
$0.9832 unrounded total, the 75% context-tax share, 100% yield, 0 superseded
runs — and the cross-check the page leans on for the recorded cost's
credibility, that the trajectory's `instance_cost` agrees exactly with the
leaderboard cost (verified by me: both `0.32052914999999993`; unchecked by
the script). It also checks no HTML provenance wording at all: the combined
report is verified only by two substring assertions (lines 354-358,
"\"What the evidence supports (V0)\" in report" and "\"3.07x\" in report").
Nothing in the script would catch D1 (the $0.91 "Priced on recorded tokens"
line), D2 (the "per accepted outcome" card), D3 (an unverified recorded
figure), or D4 (V0 rows with no cited observation) — the four defects above
all survive a green reproduce run.

**Exact fix wanted.** (a) Replace the tautology with a real parse: extract
the billed figure from stdout (`Vendor-supplied (billed): $…`) and from the
HTML Data quality block and assert both are $0.00. (b) Either narrow the
docstring claim to "checks the 15 numbers in PUBLISHED" and list them, or
extend the checks to the remaining published numbers (message/tool-call
counts from the trajectory, FAIL_TO_PASS/PASS_TO_PASS from the leaderboard
record, the traj-vs-leaderboard `instance_cost` agreement, $0.9832 unrounded,
75% tax share, 100% yield, 0 superseded runs, 3.84x 12-run gap or an explicit
statement that it is not rechecked). (c) Add report-wording assertions to the
combined-report step: the characters/4 disclosure present in the HTML, the
"no cost per accepted outcome is claimed" sentence present, the digest-verified
line present, and (once D1 is fixed) the corrected provenance label present.

**Weak checks (not fake — noted, not FAIL drivers).** Baseline
discrimination is checked only as `"THEN" in baseline.stdout` — it does not
check `OperationalError` / "syntax error", so a different failure mentioning
THEN would pass. The ratio is parsed with `re.search(r"\(([0-9.]+)x\)", out)`
over the whole stdout — the first parenthetical number followed by `x`,
fragile against any future findings text. The "leaderboard resolved" check
relies on `int(True) == int(True)` bool/int punning. Tighten all three when
D6 is fixed.

---

## Other overclaims found (README / CLI help)

- `try-it/README.md`, expected-output block: "Fully loaded: $0.98" is printed
  bare, with no ESTIMATED qualifier; only the following recorded-comparison
  line carries ESTIMATED. The bare line is the one a stranger will quote.
  Prefix or annotate it (e.g. "Fully loaded: $0.98 ESTIMATED") in the README
  and, per D2, in stdout itself.
- `averth/cli.py` module docstring: "``--recorded`` adds the run's recorded
  cost next to the metered estimate" — same unverified-provenance assertion
  as D3; fix as in D3(c).
- `try-it/README.md:71` repeats the D1 mislabel — fix as in D1.
- `try-it/README.md:80-82` ("The $0.98 is an ESTIMATE, not a bill. For
  trajectory input, token counts are characters/4 estimates…") is accurate
  and is the right disclosure — but it lives in the README, which a recipient
  of the standalone HTML never sees. The report must carry it (D1, D2).

---

## Not checked (stated, not signed off)

- I did **not** re-run the full `reproduce-case-study.py` (network downloads
  + Django install); my reproduce-script findings are from reading the script
  and verifying its individual claims against the case-study page and the
  artifacts already in `try-it/repro-work/`.
- I did **not** verify the live published page at
  `https://getaverth.com/case-study-1.html`; all case-study quotations are
  from the local source `~/workspace/averth-site/case-study-1.html`. If the
  live page differs from that source, the comparisons above need re-checking
  against the live text.
- I did **not** check Langfuse-input honesty beyond reading its `source_note`
  (`cli.py`, langfuse branch: "Token counts and costs are trace-supplied;
  Averth does not verify them as recorded usage") — no Langfuse run was
  executed, so no verdict on that path.
- I did **not** audit the V0 verifier itself (`evidence-v0/`) or the pricing
  table's accuracy (report stamps "Price table v8 · verified 2026-10-23 · 19
  days old"; staleness threshold not evaluated). V0 findings here concern
  only how `try` *presents* a ledger, not whether the ledger is correct.
- I did **not** check the `.test-out/report.html` generation command's stdout
  (only the file); the stdout claims in this review come from my own live
  runs saved under `try-it/reviews/scratch-3/`.

## Scratch evidence

- `try-it/reviews/scratch-3/stdout-full.txt` — full stdout of the canonical
  run (recorded + ledger + checks); note "Fully loaded: $0.98" bare,
  "Cost per successful outcome:", "Reopened: 0 accepted outcomes reopened",
  and the V0 line with no digest qualifier.
- `try-it/reviews/scratch-3/stdout-run.html`, `no-checks.html`,
  `wrong-recorded.html`, `bare.html`, `jsonl.html`, `stale-target.html` —
  the HTML outputs of the probed variants.
