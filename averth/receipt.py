"""The "Averth Agent PR Receipt (trace-observed)": a compact Markdown
summary designed to be pasted into a GitHub PR description.

Contents: header (Averth receipt, a per-receipt resolution scope
line, generated date, source sessions or a single source with its
kind), a trace-recorded vs metered estimate cost table (with the
known systematic ~3.2x overestimate disclosed), the default-checks
table (check, verdict, cited observation), the unknown rate (with
the 15% bar stated), a "What to do next" section generated from the
verdicts, and an honesty footer (what is NOT claimed: no cost per
accepted outcome; estimates are not bills; the recorded figure is
what the trace reports and is not verified against any invoice or
bill; default checks are trace-observed, not human-written).

The receipt is written as ``<stem>-receipt.md`` next to the HTML
report (same stem rule: the HTML path with ``.html`` stripped and
``-receipt.md`` appended) and, in scan mode, printed to stdout too.
``--receipt PATH`` overrides the path.

Hostile filenames / session ids are escaped: user-controlled strings
are rendered through ``_escape_cell`` / ``_escape_text``, which strip
control characters (including DEL), collapse newlines, and escape
the characters that could break a table, end a code span, or start
new Markdown structure or raw HTML (``|``, ``\\``, ``[``, ``]``,
backtick, ``<`` / ``>`` as ``&lt;`` / ``&gt;``).
"""

import datetime
import os

from averth.default_checks import LABEL

# The receipt's title never asserts verification: the body underneath
# it may carry FAILED and NOT OBSERVED rows.
TITLE = "Averth Agent PR Receipt (trace-observed)"

# Systematic meter bias measured on the 50-trace public audit of
# mini-SWE-agent trajectories (wave2/AUDIT-REPORT.md): the metered
# estimate ran ~3.2x the trace-recorded cost on every trace. The
# receipt states it bluntly in the cost section instead of leaving
# the reader to infer it from one ratio.
SYSTEMATIC_BIAS_LINE = (
    "On the 50-trace public audit of mini-SWE-agent trajectories, "
    "the metered estimate ran ~3.2x the trace-recorded cost on every "
    "trace (median 3.22x, 0/50 within 10%); treat the metered figure "
    "as an upper-bound-style estimate, not a measurement.")

UNKNOWN_RATE_BAR = 0.15


def receipt_path_for_html(html_path):
    """Receipt path for an HTML report path (same stem rule)."""
    if html_path.endswith(".html"):
        return html_path[:-5] + "-receipt.md"
    return html_path + "-receipt.md"


def _escape_cell(text):
    """Escape a user-controlled string for a Markdown table cell."""
    if text is None:
        return ""
    out = []
    for ch in str(text):
        if (ord(ch) < 32 and ch not in ("\t",)) or ord(ch) == 127:
            continue
        if ch in ("\n", "\r"):
            out.append(" ")
        elif ch == "|":
            out.append("\\|")
        elif ch == "\\":
            out.append("\\\\")
        elif ch in ("[", "]"):
            # A hostile session id must not form a Markdown link.
            out.append("\\" + ch)
        elif ch == "`":
            out.append("\\`")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        else:
            out.append(ch)
    return "".join(out).replace("\t", " ")


def _escape_text(text):
    """Escape a user-controlled string for Markdown body text."""
    if text is None:
        return ""
    out = []
    for ch in str(text):
        if (ord(ch) < 32 and ch not in ("\n", "\t")) or ord(ch) == 127:
            continue
        if ch == "\\":
            out.append("\\\\")
        elif ch in ("[", "]"):
            # A hostile session id must not form a Markdown link.
            out.append("\\" + ch)
        elif ch == "`":
            out.append("\\`")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        else:
            out.append(ch)
    return "".join(out)


def _money(value):
    return "$%.2f" % value


def _money_recorded(value):
    """Recorded cost at the same 2dp precision as the metered figure
    in the cost table (4dp lives only inside the D5 observation,
    labelled as such there)."""
    return "$%.2f" % value


def _next_steps(checks):
    """The "What to do next" lines, generated from the verdicts."""
    lines = ["Paste this whole receipt into the PR description."]
    failed = {c["id"]: c for c in checks if c["verdict"] == "FAILED"}
    if "D1" in failed or "D2" in failed:
        lines.append("Fix the failing command and re-run "
                     "(D1/D2 FAILED).")
    if "D3" in failed:
        lines.append("Check the unmatched files have a stem-matching "
                     "test named in the last test run, or run the full "
                     "test suite (D3 FAILED).")
    if "D4" in failed:
        lines.append("Inspect the most-repeated command — a loop, not "
                     "a verdict on the fix (D4 FAILED).")
    if "D5" in failed:
        lines.append("Do not quote the metered figure as spend; "
                     "reconcile against the invoice first (D5 FAILED).")
    unknown_n = sum(1 for c in checks
                    if c["verdict"] in ("NOT OBSERVED",
                                        "EXTERNAL-UNVERIFIABLE"))
    if unknown_n:
        lines.append("%d of %d checks could not be resolved from this "
                     "trace; they are unproven, not passing."
                     % (unknown_n, len(checks)))
    if checks and not failed and not unknown_n:
        lines.append("Ready to paste as-is.")
    return lines


def render_receipt(*, generated_at=None, sources=(), source_kind=None,
                   estimated_cost=None,
                   recorded_cost=None, recorded_note=None, checks=(),
                   unknown_rate=None, scan_note=None):
    """Render the receipt Markdown.

    ``sources`` is a list of session display names (``source/<path
    below the source root>`` strings, so two sessions sharing a
    basename still render distinctly) in scan mode, or the single
    input file's display name (session files) or basename (other
    traces) in explicit mode.
    ``source_kind`` names an explicit trace's kind ("mini-SWE-agent
    trajectory", "Claude session", "Codex rollout", "JSONL",
    "Langfuse"); scan mode passes None and keeps the "Source
    sessions" label. ``estimated_cost`` is the metered total
    (ESTIMATED). ``recorded_cost`` is the trace's own recorded total,
    or None when the trace carries none. ``recorded_note`` replaces
    the recorded row's amount when the figure is not comparable (e.g.
    Codex subscription billing). ``checks`` is the judged
    default-checks list. ``scan_note`` is an extra line about the
    scan (sessions scanned / skipped), shown under the header when
    given.
    """
    if generated_at is None:
        generated_at = datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = []
    lines.append("# " + TITLE)
    lines.append("")
    if checks:
        unknown_n = sum(1 for c in checks
                        if c["verdict"] in ("NOT OBSERVED",
                                            "EXTERNAL-UNVERIFIABLE"))
        failed_n = sum(1 for c in checks if c["verdict"] == "FAILED")
        lines.append("Outcome: %d of %d checks resolved, %d FAILED, "
                     "%d unknown — this receipt verifies only the rows "
                     "marked VERIFIED, and only as their cited "
                     "observations state."
                     % (len(checks) - unknown_n, len(checks),
                        failed_n, unknown_n))
        lines.append("")
    lines.append("Generated: %s" % _escape_text(generated_at))
    if sources:
        if source_kind is not None:
            lines.append("Source: %s (%s)"
                         % (", ".join("`%s`" % _escape_cell(s)
                                     for s in sources),
                            _escape_text(source_kind)))
        else:
            lines.append("Source sessions: %s"
                         % ", ".join("`%s`" % _escape_cell(s)
                                     for s in sources))
    if scan_note:
        lines.append(_escape_text(scan_note))
    lines.append("")
    lines.append("## Trace-recorded cost vs metered estimate")
    lines.append("")
    lines.append("| | Amount |")
    lines.append("|---|---|")
    if estimated_cost is None:
        lines.append("| Metered estimate (total) | not metered |")
    else:
        lines.append("| Metered estimate (total) | %s ESTIMATED |"
                     % _money(estimated_cost))
    if recorded_note is not None:
        lines.append("| Recorded cost (trace-reported, not verified "
                     "against any invoice or bill) | %s |"
                     % _escape_cell(recorded_note))
    elif recorded_cost is None:
        lines.append("| Recorded cost (trace-reported, not verified "
                     "against any invoice or bill) | not recorded in "
                     "trace |")
    else:
        lines.append("| Recorded cost (trace-reported, not verified "
                     "against any invoice or bill) | %s |"
                     % _money_recorded(recorded_cost))
    if recorded_cost is not None and recorded_cost != 0 \
            and estimated_cost and recorded_note is None:
        lines.append("| Metered estimate / recorded cost | %.2fx |"
                     % (estimated_cost / recorded_cost))
    lines.append("")
    lines.append(SYSTEMATIC_BIAS_LINE)
    lines.append("")
    lines.append("## " + LABEL[0].upper() + LABEL[1:])
    lines.append("")
    lines.append("| Check | Verdict | Cited observation |")
    lines.append("|---|---|---|")
    for check in checks:
        lines.append("| %s | %s | %s |"
                     % (_escape_cell(check["id"] + " " + check["name"]),
                        _escape_cell(check["verdict"]),
                        _escape_cell(check["observation"])))
    lines.append("")
    if unknown_rate is not None:
        unknown_n = sum(1 for c in checks
                        if c["verdict"] in ("NOT OBSERVED",
                                            "EXTERNAL-UNVERIFIABLE"))
        bar_line = "Bar: under 15% for a resolvable receipt. "
        if unknown_rate < UNKNOWN_RATE_BAR:
            bar_line += "This receipt is under the bar."
        else:
            bar_line += ("At %.1f%%, treat the FAILED/NOT OBSERVED "
                         "rows as unproven, not as a pass — do not "
                         "present this receipt as verification."
                         % (unknown_rate * 100))
        lines.append("Unknown rate: %.1f%% (%d of %d checks NOT OBSERVED "
                     "or EXTERNAL-UNVERIFIABLE). %s"
                     % (unknown_rate * 100, unknown_n, len(checks),
                        bar_line))
        lines.append("")
    lines.append("## What to do next")
    lines.append("")
    for step in _next_steps(checks):
        lines.append("- %s" % step)
    lines.append("")
    lines.append("## What this receipt does NOT claim")
    lines.append("")
    lines.append("- No cost per accepted outcome: no human accepted "
                 "these runs, so nothing here is a cost per accepted "
                 "outcome.")
    lines.append("- Estimates are not bills: the metered figure applies "
                 "vendor list prices to trace-reported or estimated "
                 "token counts. Reconcile against the invoice before "
                 "calling any metered figure actual spend.")
    lines.append("- The recorded figure is what the trace reports "
                 "(`info.model_stats.instance_cost` / "
                 "`result.total_cost_usd`); Averth does not verify it "
                 "against any invoice or bill.")
    lines.append("- Default checks are trace-observed, not human-written "
                 "V0 checks: each verdict cites only what the transcript "
                 "shows. A VERIFIED row proves only what its cited "
                 "observation shows.")
    lines.append("")
    return "\n".join(lines) + "\n"


def recorded_note_for(checks):
    """Recorded-row note when D5 says the figure is not comparable.

    Returns the note string when D5 is EXTERNAL-UNVERIFIABLE (Codex
    subscription billing), else None.
    """
    for check in checks:
        if check["id"] == "D5" \
                and check["verdict"] == "EXTERNAL-UNVERIFIABLE":
            return ("not comparable: Codex subscription billing is not "
                    "API list-price metering")
    return None
