"""The "Verified Agent PR Receipt": a compact Markdown summary designed
to be pasted into a GitHub PR description.

Contents: header (Averth receipt, generated date, source sessions),
billed vs estimated cost table, the default-checks table (check,
verdict, cited observation), the unknown rate, and an honesty footer
(what is NOT claimed: no cost per accepted outcome; estimates are
not bills; default checks are trace-observed, not human-written).

The receipt is written as ``<stem>-receipt.md`` next to the HTML
report (same stem rule: the HTML path with ``.html`` stripped and
``-receipt.md`` appended) and, in scan mode, printed to stdout too.
``--receipt PATH`` overrides the path.

Hostile filenames / session ids are escaped: user-controlled strings
are rendered through ``_escape_cell`` / ``_escape_text``, which strip
control characters, collapse newlines, and backslash-escape the
characters that could break a table or start new Markdown structure.
"""

import datetime
import os

from averth.default_checks import LABEL


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
        if ord(ch) < 32 and ch not in ("\t",):
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
        else:
            out.append(ch)
    return "".join(out).replace("\t", " ")


def _escape_text(text):
    """Escape a user-controlled string for Markdown body text."""
    if text is None:
        return ""
    out = []
    for ch in str(text):
        if ord(ch) < 32 and ch not in ("\n", "\t"):
            continue
        if ch == "\\":
            out.append("\\\\")
        elif ch in ("[", "]"):
            # A hostile session id must not form a Markdown link.
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _money(value):
    return "$%.2f" % value


def _money_recorded(value):
    text = "%.4f" % value
    return "$" + text.rstrip("0").rstrip(".")


def render_receipt(*, generated_at=None, sources=(), estimated_cost=None,
                   recorded_cost=None, recorded_note=None, checks=(),
                   unknown_rate=None, scan_note=None):
    """Render the receipt Markdown.

    ``sources`` is a list of session display names (``source/basename``
    strings). ``estimated_cost`` is the metered total (ESTIMATED).
    ``recorded_cost`` is the trace's own recorded total, or None when
    the trace carries none. ``recorded_note`` replaces the recorded
    row's amount when the figure is not comparable (e.g. Codex
    subscription billing). ``checks`` is the judged default-checks
    list. ``scan_note`` is an extra line about the scan (sessions
    scanned / skipped), shown under the header when given.
    """
    if generated_at is None:
        generated_at = datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = []
    lines.append("# Averth Verified Agent PR Receipt")
    lines.append("")
    lines.append("Generated: %s" % _escape_text(generated_at))
    if sources:
        lines.append("Source sessions: %s"
                     % ", ".join("`%s`" % _escape_cell(s)
                                 for s in sources))
    if scan_note:
        lines.append(_escape_text(scan_note))
    lines.append("")
    lines.append("## Billed vs estimated cost")
    lines.append("")
    lines.append("| | Amount |")
    lines.append("|---|---|")
    if estimated_cost is None:
        lines.append("| Metered estimate (total) | not metered |")
    else:
        lines.append("| Metered estimate (total) | %s ESTIMATED |"
                     % _money(estimated_cost))
    if recorded_note is not None:
        lines.append("| Recorded cost (trace) | %s |"
                     % _escape_cell(recorded_note))
    elif recorded_cost is None:
        lines.append("| Recorded cost (trace) | not recorded in trace |")
    else:
        lines.append("| Recorded cost (trace) | %s |"
                     % _money_recorded(recorded_cost))
    if recorded_cost is not None and estimated_cost \
            and recorded_note is None:
        lines.append("| Metered estimate / recorded cost | %.2fx |"
                     % (estimated_cost / recorded_cost))
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
        lines.append("Unknown rate: %.1f%% (%d of %d checks NOT OBSERVED "
                     "or EXTERNAL-UNVERIFIABLE)."
                     % (unknown_rate * 100, unknown_n, len(checks)))
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
