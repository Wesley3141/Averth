# Hostile review: averth/report.py — write_html() + helpers (_bar, _histogram_svg)

Scope: `~/workspace/averth/averth/report.py` lines ~130–477 only
(`_bar`, `_histogram_svg`, `write_html`, incl. new `tool_est_banner`,
`stale_banner`, `vintage_line`, `human_note`, `cache_line`). `report_text`
explicitly out of scope (other reviewer). Reviewed against the FIXED code
post Phase-1 (C1–C3/H1–H4/M1–M3).

Method: read the full file; traced every interpolation into the HTML
template; built a hostile Tracker (XSS payloads as agent name, case_id,
retry reason, unpriced model name, default-priced tool name); rehydrated a
Tracker from a tampered ledger via `importers.common.tracker_from_ledger`;
passed a hostile hand-built `policy_sim`; rendered all outputs and scanned
for raw payloads; hand-verified the bar↔fully-loaded identity numerically;
ran SVG math on 0/1/all-equal attempt counts; grepped the package for
network imports.

No web access was used; no prompt-injection content encountered.

## Severity counts

- CRITICAL: 1 (stored XSS in the shareable HTML report)
- HIGH: 1 (broken discount-rate label — H3 requirement not met in HTML)
- MEDIUM: 1 (unescaped policy values)
- LOW: 2 (cosmetic/robustness nits)

---

## CRITICAL

### C-HTML-1 — Stored XSS via unescaped `price_vintage["version"]` in `write_html`

`~/workspace/averth/averth/report.py:240` (`vintage_line`) and
`~/workspace/averth/averth/report.py:248` (`stale_banner`):

```python
vintage_line = ("Price table v%s &middot; verified %s &middot; %d days old"
                % (vint["version"], _html.escape(vint["updated"]),
                   vint["age_days"]))
...
stale_banner = (
    '<div class="warn"><b>Stale pricing:</b> price table v%s is %d '
    ...
    % (vint["version"], vint["age_days"],
       _html.escape(vint["updated"])))
```

`vint["version"]` is interpolated **raw** in both places while the
adjacent `vint["updated"]` *is* escaped — an oversight, not a decision.

Reachability is real, not theoretical. The version string is
attacker-controlled through the documented cross-organization sharing
flow:

1. `averth/importers/common.py:247` — `tracker_from_ledger()` does
   `tracker.price_vintage = ledger.get("price_vintage")`, copying the
   dict **verbatim** from a ledger JSON file.
2. `averth/cli.py:164` — the CLI import command loads an arbitrary
   ledger path and calls `tracker_from_ledger`.
3. `averth/cli.py:86` — `_report_and_html()` then calls
   `write_html(html_path, tracker, ...)`.

The ledger is explicitly designed to cross trust boundaries
(`policy.py` docstring: "the customer runs the meter inside their own
environment (Tracker), exports the sanitized ledger … and we run the
simulation here"). The HTML report is explicitly "single-file
shareable". So: a crafted ledger with
`"price_vintage": {"version": "<script>…</script>", …}` produces a
report that executes JavaScript when the analyst opens it — with the
report's financial data in scope for exfiltration via `fetch()`.

Demonstrated: rehydrated a ledger whose version was
`<script>alert("xss-vintage")</script>` and rendered. Output contained,
verbatim:

```
Price table v<script>alert("xss-vintage")</script> &middot;
…
Stale pricing:</b> price table v<script>alert("xss-vintage")</script> is
```

both sinks fire. Fix: `_html.escape(str(vint["version"]))` in both
places (escape `updated` already done; also coerce/validate `age_days`
rather than trusting `%d` on untrusted input — currently a tampered
non-int raises a loud TypeError, which is acceptable fail-loud
behavior but worth a deliberate choice).

---

## HIGH

### H-HTML-1 — `cache_line` renders a literal `%.0f%%`: the H3 discount rate never displays

`~/workspace/averth/averth/report.py:461-466`:

```python
"cache_line": ("Prompt cache: {:,} input tokens cached, saving "
               "${:,.2f} (priced at %.0f%% of input rate — "
               "vendor-specific; override via "
               "cache_read_discount).".format(p["cached_tokens"],
                                  p["cache_savings"],
                                  p.get("cache_read_discount", 0.10) * 100)
               ) if p["cached_tokens"] and p["cache_savings"] > 0 else "",
```

The string is formatted with `.format()` (brace style) but contains a
`%`-style `%.0f%%` placeholder. `.format()` ignores `%` placeholders,
so the rendered report shows the raw spec and the third argument
(`discount * 100`) is silently swallowed. Actual output from a live
run:

```
Prompt cache: 8,000 input tokens cached, saving $0.02 (priced at %.0f%% of input rate — vendor-specific; override via cache_read_discount).
```

This directly defeats the H3 audit fix ("name the discount rate — it
is vendor-specific … not a universal constant"): the HTML report is
the artifact a VP Finance actually reads, and it fails to name the
rate while `report_text` (`report.py:93`) does it correctly with `%`
formatting. Classic copy-paste inconsistency between the two
renderers. The dollar math underneath (tokens, savings) is correct;
the label is visibly broken — exactly the "AI slop" signal Wesley's
bar forbids. Fix: use `%` formatting like `report_text`, or
`"priced at {:.0f}% …".format(…)`.

---

## MEDIUM

### M-HTML-1 — `policy_sim` policy values rendered unescaped

`~/workspace/averth/averth/report.py:324`:

```python
'Policy tested: max cost per attempt $%s, yield floor %s. '
...
% (..., pol["max_cost_per_attempt"], pol["yield_floor"]))
```

`pol["max_cost_per_attempt"]` and `pol["yield_floor"]` go into the
HTML raw. The *same block* escapes `w["case_id"]` and
`w["reasons"]` — inconsistent. Normally these are numbers echoed back
from `simulate_policy()`, so the practical path is self-XSS by the
report author; but `write_html` is a public API and a `policy_sim`
assembled from a team-shared JSON policy config (rather than
`simulate_policy()`) turns this into a real injection sink.
Demonstrated: hand-built `policy_sim` with
`"<script>alert(\"xss-policy\")</script>"` as both values rendered the
raw payload in the output (while the hostile `worst[].case_id` and
`reasons` in the same section were correctly escaped). Fix: escape,
or coerce to float at the top of the policy section (fail loud on
non-numeric).

---

## LOW

### L-HTML-1 — `_bar` can emit `width:>100%` or negative widths

`~/workspace/averth/averth/report.py:130-138`. If `value > total`,
`width` exceeds 100% (the `.btrack` has `overflow:hidden`, so it just
clips — cosmetic). A negative `value` yields an invalid negative CSS
width (bar silently doesn't draw; no crash). All current callers pass
non-negative per-success components, so this is latent only. Consider
clamping to `[0, 100]`.

### L-HTML-2 — bare `KeyError` on malformed hand-built `policy_sim`

`write_html(..., policy_sim={})` (or a dict missing `"policy"`,
`"would_stop"`, etc.) raises an undecorated `KeyError`. Loud, not
silent — acceptable — but a one-line validation with a clear message
would beat a traceback for a public API.

---

## Verified good (attack surface checked, no finding)

- **Tracker-sourced strings all escaped**: agent name, `case_id`,
  retry reasons, unpriced model keys, default-priced tool names, and
  finding title/detail/action all render escaped. Hostile Tracker
  with `<script>`/`<img onerror>` payloads in all four produced zero
  raw leaks; escaped forms confirmed present.
- **Template keys complete**: `vintage_line`, `tool_est_banner`,
  `stale_banner`, `human_note`, `cache_line`, `retry_section`,
  `policy_section`, `mult_card` etc. all present in the `%`-format
  dict; generation succeeds with no `KeyError`/`ValueError`. The four
  new keys were each confirmed rendered in output (`tool_est_banner`
  and `human_note` in the standard run; `stale_banner` in the stale-
  vintage run; `vintage_line` in the meta paragraph).
- **Bar↔card identity holds (M3 verified numerically)**:
  `end_attempt` documents "terminal + retry_path + tools + human =
  total" with retry-path tool spend deliberately excluded from
  `retry_path_cost`; the four `_bar` widths sum exactly to the
  "Fully loaded" card (`$1.3725` vs `$1.3725`, delta 0.0000 in test).
  No double-count, no missing slice.
- **SVG histogram edge cases**: 0 attempts (empty `costs` → lo=0,
  hi=1.0, ten zero-height rects, markers at p50=p95=0), 1 attempt,
  and 7 identical costs (single full-height bucket at 156.0, rest
  0.0) all render without crash or div-by-zero (`hi = lo + 1.0`
  guard; `peak = max(buckets) or 1` guard). Docstring "10 buckets,
  p50/p95 markers" is accurate.
- **No network surface**: `report.py` imports only `html` and
  `.insights`; package-wide grep for socket/urllib/requests/http
  imports is clean. The footer claim "No data leaves your
  environment" holds for this module.
- **Staleness machinery works**: `stale_banner` renders when
  `vint["stale"]`; `vintage_line` stamps version/date/age in the
  meta paragraph; `human_note` fires loudly on the default labor
  assumption and disappears when a real rate is passed.
- **`_bar` label escaping**: quotes escaped (`&quot;` confirmed).

## Review caveats

- `~/workspace/averth/averth/pricing.py` was mutated *during* this
  review (`PRICE_TABLE_VERSION` 1 → 2 between two reads, ~03:02).
  `report.py` itself was untouched throughout (mtime Oct 3 02:58,
  md5 `2dadee9a3f7df4b0e91001556b23a470`); all findings above are
  against that exact file. Line numbers may drift if the file is
  edited after this review.
- `/tmp` was wiped mid-task (known runtime volatility); hostile
  tests were re-run from workspace paths and all printed evidence
  above comes from successful runs.
