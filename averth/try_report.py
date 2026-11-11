"""Shareable-report extras for ``averth try``.

``averth try`` reuses the meter's own HTML report (``averth.report``)
and adds three sections this module builds:

1. A recorded-cost comparison, when the operator passes ``--recorded``:
   the metered estimate next to the operator-supplied recorded cost
   (for the case study: the leaderboard entry's
   ``per_instance_details.json``), with the ratio. The figure is
   labelled operator-supplied and unverified everywhere it appears:
   ``averth try`` never checks it, so it never states it as a fact
   about the run.
2. A V0 verdict summary, when the operator passes ``--ledger``: the
   counts (all five verdicts, zeros included), the unknown rate, and
   one row per check with its criterion text, the command that ran,
   its exit code, and its output digest, so a VERIFIED row can be
   checked from the report itself. A VERIFIED row proves only what
   its cited observation shows.
3. A provenance note: where the trace came from, how token counts
   were derived, which price table was used, and what the report does
   not claim (no cost per accepted outcome: ``averth try`` never joins
   human acceptance labels).

Nothing here phones home: every input is a local file. The V0 digest
check below follows the same rule as the verifier's criterion (c)
fix: the checks file is hashed on its raw bytes, and a mismatch
refuses the report rather than presenting verdicts under the wrong
checks.
"""

import datetime
import hashlib
import html as _html
import json
import math

_VERDICT_ORDER = ["VERIFIED", "FAILED", "NOT OBSERVED",
                  "EXTERNAL-UNVERIFIABLE", "NOT APPLICABLE"]


def _money(value):
    return "$%.2f" % value


def _money_recorded(value):
    """Recorded dollars keep up to four decimals ($0.3205, not $0.32)."""
    text = "%.4f" % value
    return "$" + text.rstrip("0").rstrip(".")


def _check_recorded(recorded):
    if recorded is None:
        return
    if (not isinstance(recorded, (int, float))
            or not math.isfinite(recorded) or recorded <= 0):
        raise ValueError("--recorded must be a positive dollar figure")


def load_v0_ledger(ledger_path, checks_path=None):
    """Load a V0 evidence ledger and summarize it for the report.

    Returns ``(summary, digest_verified)`` where ``digest_verified``
    is True when a ``--checks`` file was given and its raw-bytes
    sha256 matches the ledger's checks digest, and None when no
    checks file was given (the digest is then shown but labelled
    unverified).

    Raises ValueError when the ledger file or the checks file cannot
    be read, when the ledger is not a V0 ledger, when any field has
    the wrong shape, or when the digest mismatches.
    """
    try:
        with open(ledger_path, encoding="utf-8") as f:
            ledger = json.load(f)
    except OSError as e:
        raise ValueError(
            "V0 ledger file not found: %s (passed via --ledger)" % ledger_path
        ) from e
    except json.JSONDecodeError as e:
        raise ValueError(
            "V0 ledger file is not valid JSON: %s (%s)"
            % (ledger_path, e)
        ) from e
    if not isinstance(ledger, dict) or "judgments" not in ledger:
        raise ValueError(
            "%s is not a V0 evidence ledger (no 'judgments' key)"
            % ledger_path
        )
    judgments = ledger.get("judgments")
    if not isinstance(judgments, list) or not all(
            isinstance(j, dict) for j in judgments):
        raise ValueError(
            "%s is not a V0 evidence ledger ('judgments' must be a list "
            "of objects)" % ledger_path
        )
    coverage = ledger.get("coverage") or {}
    if not isinstance(coverage, dict):
        raise ValueError(
            "%s is not a V0 evidence ledger ('coverage' must be an "
            "object)" % ledger_path
        )
    counts = coverage.get("counts") or {}
    if (not isinstance(counts, dict)
            or not all(isinstance(v, (int, float))
                       and not isinstance(v, bool)
                       and math.isfinite(v)
                       for v in counts.values())):
        raise ValueError(
            "%s is not a V0 evidence ledger ('coverage.counts' must map "
            "verdict names to numbers)" % ledger_path
        )
    unknown_rate = coverage.get("unknown_rate")
    if unknown_rate is not None and not (
            isinstance(unknown_rate, (int, float))
            and not isinstance(unknown_rate, bool)
            and math.isfinite(unknown_rate)):
        raise ValueError(
            "%s is not a V0 evidence ledger ('coverage.unknown_rate' "
            "must be a number)" % ledger_path
        )
    unknown = coverage.get("unknown", 0)
    if not isinstance(unknown, int) or isinstance(unknown, bool):
        raise ValueError(
            "%s is not a V0 evidence ledger ('coverage.unknown' must "
            "be an integer)" % ledger_path
        )
    superseded = coverage.get("superseded_runs_retained", 0)
    if not isinstance(superseded, int) or isinstance(superseded, bool):
        raise ValueError(
            "%s is not a V0 evidence ledger "
            "('coverage.superseded_runs_retained' must be an integer)"
            % ledger_path
        )
    runs_total = coverage.get("runs_total", len(ledger.get("runs", [])))
    if not isinstance(runs_total, int) or isinstance(runs_total, bool):
        raise ValueError(
            "%s is not a V0 evidence ledger ('coverage.runs_total' must "
            "be an integer)" % ledger_path
        )
    summary = {
        "report_id": ledger.get("report_id"),
        "generated_at": ledger.get("generated_at"),
        "checks_digest": ledger.get("checks_digest"),
        "counts": counts,
        "unknown": unknown,
        "unknown_rate": unknown_rate,
        "runs_total": runs_total,
        "superseded_runs_retained": superseded,
        "judgments": [
            {
                "criterion_id": j.get("criterion_id"),
                "status": j.get("status"),
                "criterion_text": j.get("criterion_text"),
                "scope_limitation": j.get("scope_limitation"),
                "command": j.get("command"),
                "exit_code": j.get("exit_code"),
                "output_digest": j.get("output_digest"),
                "evidence_id": j.get("evidence_id"),
            }
            for j in judgments
        ],
    }
    digest_verified = None
    if checks_path is not None:
        try:
            with open(checks_path, "rb") as f:
                digest = "sha256:" + hashlib.sha256(f.read()).hexdigest()
        except OSError as e:
            raise ValueError(
                "checks file not found: %s (passed via --checks)"
                % checks_path
            ) from e
        if digest != ledger.get("checks_digest"):
            raise ValueError(
                "checks digest mismatch: %s hashes to %s but the ledger "
                "records %s; refusing to present these verdicts under "
                "those checks" % (checks_path, digest,
                                 ledger.get("checks_digest"))
            )
        digest_verified = True
    return summary, digest_verified


def _judgment_row(j):
    """One V0 table row: criterion, verdict, and the cited observation.

    The observation is the command that ran, its exit code, and its
    output digest, so a VERIFIED row can be checked from the report
    itself instead of appealing to an unseen ledger.
    """
    digest = j.get("output_digest")
    if digest:
        digest_cell = (
            '<span title="%s">%s&hellip;</span>'
            % (_html.escape(str(digest)),
               _html.escape(str(digest)[:16]))
        )
    else:
        digest_cell = "not recorded"
    command = j.get("command")
    command_cell = (
        "<code>%s</code>" % _html.escape(str(command))
        if command else "not recorded"
    )
    exit_code = j.get("exit_code")
    exit_cell = (
        "exit %d" % exit_code
        if isinstance(exit_code, int) and not isinstance(exit_code, bool)
        else "exit code not recorded"
    )
    return (
        "<tr><td>%s</td><td>%s</td>"
        "<td>%s<br><span class=\"s\">%s</span></td>"
        "<td>%s<br>%s<br>output digest %s</td></tr>"
        % (_html.escape(str(j["criterion_id"])),
           _html.escape(str(j["status"])),
           _html.escape(str(j["criterion_text"] or "")),
           _html.escape(str(j["scope_limitation"] or "")),
           command_cell, exit_cell, digest_cell)
    )


def build_try_extras(pnl, *, recorded=None, v0=None,
                     digest_verified=None, source_note=None,
                     traj_recorded=None):
    """Render the try-it extra HTML sections for the meter report.

    ``pnl`` is the tracker's ``pnl()`` dict. ``recorded`` is an
    operator-supplied recorded cost or None. ``v0`` is the summary
    from ``load_v0_ledger`` or None. ``traj_recorded`` is the
    trajectory's own recorded-cost figure (``info.model_stats.
    instance_cost``) when the trace carries one, or None: when
    present it is shown next to the operator-supplied figure so a
    recipient can tell whether the two agree. Returns an HTML string
    (already escaped) to insert before ``</main>``.
    """
    _check_recorded(recorded)
    generated_at = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = []
    per_success = pnl["per_success"]["fully_loaded"]
    successes = pnl["successes"]
    if recorded is not None:
        if successes == 0:
            comparison = (
                "<p>No completed runs, so there is no per-run figure to "
                "compare against the recorded cost.</p>"
            )
        else:
            ratio = per_success / recorded
            if traj_recorded is not None:
                if abs(traj_recorded - recorded) <= 0.001:
                    corroboration = (
                        "<p>The trajectory's own recorded cost (%s) "
                        "agrees with the operator-supplied figure.</p>"
                        % _money_recorded(traj_recorded)
                    )
                else:
                    corroboration = (
                        "<p><b>Warning:</b> the trajectory's own "
                        "recorded cost is %s, which differs from the "
                        "operator-supplied %s. One of the two figures "
                        "is wrong; reconcile before quoting either.</p>"
                        % (_money_recorded(traj_recorded),
                           _money_recorded(recorded))
                    )
            else:
                corroboration = ""
            comparison = (
                "<table><tr><th>Metered estimate per completed run</th>"
                '<td class="r">%s ESTIMATED</td></tr>'
                "<tr><th>Recorded cost (operator-supplied via "
                "--recorded; not verified by Averth)</th>"
                '<td class="r">%s</td></tr>'
                "<tr><th>Metered estimate divided by recorded cost</th>"
                '<td class="r">%.2fx</td></tr></table>'
                "<p>The operator supplied %s as the recorded cost for "
                "this run; a meter working from this trace alone would "
                "estimate %s. Averth does not claim the estimate is "
                "the bill. Reconcile against the invoice before "
                "calling any metered figure actual spend.</p>"
                "%s"
                % (_money(per_success), _money_recorded(recorded),
                   ratio, _money_recorded(recorded),
                   _money(per_success), corroboration)
            )
        parts.append(
            "<h2>Metered estimate vs recorded cost</h2>" + comparison
        )
    if v0 is not None:
        counts = v0["counts"]
        rows = "".join(
            "<tr><th>%s</th><td class=\"r\">%d</td></tr>"
            % (_html.escape(name), counts.get(name, 0))
            for name in _VERDICT_ORDER
        )
        judgments = "".join(_judgment_row(j) for j in v0["judgments"])
        if digest_verified is True:
            digest_line = "Checks digest verified against the checks file."
            heading = "What the evidence supports (V0)"
        else:
            digest_line = (
                "Checks digest shown but not verified (no --checks "
                "file given); pass --checks to verify the verdicts "
                "were judged under those checks."
            )
            heading = ("What the evidence supports (V0) &mdash; checks "
                       "digest not verified")
        unknown_rate = v0["unknown_rate"]
        unknown_line = (
            "Unknown rate %.1f%%." % (unknown_rate * 100)
            if unknown_rate is not None else "Unknown rate not recorded."
        )
        parts.append(
            "<h2>%s</h2>"
            "<table><tr><th>Verdict</th>"
            '<th class="r">Checks</th></tr>%s</table>'
            "<p>%s Runs recorded: %d, of which superseded and retained, "
            "never cited: %d.</p>"
            "<table><tr><th>Check</th><th>Verdict</th>"
            "<th>What was checked</th><th>Cited observation</th></tr>%s"
            "</table>"
            "<p>A VERIFIED row proves only what its cited observation "
            "shows. No human accepted this run, so no cost per accepted "
            "outcome is claimed.</p>"
            "<p class=\"s\">Ledger %s &middot; generated %s &middot; "
            "checks digest %s &middot; %s &middot; report generated %s"
            "</p>"
            % (heading, rows, unknown_line, v0["runs_total"],
               v0.get("superseded_runs_retained", 0),
               judgments,
               _html.escape(str(v0["report_id"])),
               _html.escape(str(v0["generated_at"])),
               _html.escape(str(v0["checks_digest"])), digest_line,
               generated_at)
        )
    if source_note is not None:
        parts.append(
            "<h2>How this report was made</h2><p>%s</p>"
            "<p>No human accepted this run, so no cost per accepted "
            "outcome is claimed. Cost per completed run is %s "
            "ESTIMATED, not a bill.</p>"
            % (_html.escape(source_note), _money(per_success))
        )
    return "\n".join(parts)


def try_summary_lines(pnl, *, recorded=None, v0=None,
                      digest_verified=None, source_note=None,
                      traj_recorded=None):
    """Short stdout lines for ``averth try`` after the meter report.

    The source note and the no-acceptance sentence print on every
    run, so stdout alone never presents the dollars without their
    provenance and their limit. When the trajectory carries its own
    recorded cost (``traj_recorded``), stdout says whether it agrees
    with the operator-supplied figure, so a wrong ``--recorded``
    cannot pass silently for a reader of stdout alone.
    """
    _check_recorded(recorded)
    lines = []
    per_success = pnl["per_success"]["fully_loaded"]
    if source_note is not None:
        lines.append(source_note)
        lines.append(
            "No human accepted this run, so no cost per accepted "
            "outcome is claimed. Cost per completed run is %s "
            "ESTIMATED, not a bill." % _money(per_success)
        )
    if pnl["successes"] and recorded is not None:
        lines.append(
            "Recorded cost (operator-supplied): %s; metered estimate "
            "per completed run: %s ESTIMATED (%.2fx)"
            % (_money_recorded(recorded), _money(per_success),
               per_success / recorded)
        )
        if traj_recorded is not None:
            if abs(traj_recorded - recorded) <= 0.001:
                lines.append(
                    "Trajectory's own recorded cost %s agrees with the "
                    "operator-supplied figure."
                    % _money_recorded(traj_recorded)
                )
            else:
                lines.append(
                    "WARNING: trajectory's own recorded cost is %s, "
                    "which differs from the operator-supplied %s. One "
                    "of the two figures is wrong; reconcile before "
                    "quoting either."
                    % (_money_recorded(traj_recorded),
                       _money_recorded(recorded))
                )
    if v0 is not None:
        counts = v0["counts"]
        ordered = ", ".join(
            "%s %d" % (name, counts.get(name, 0))
            for name in _VERDICT_ORDER
        )
        unknown_rate = v0["unknown_rate"]
        if digest_verified is True:
            digest_note = "; checks digest verified against the checks file"
        else:
            digest_note = (
                "; checks digest NOT verified (no --checks given; "
                "verdicts may have been judged under different checks)"
            )
        lines.append(
            "V0 verdicts: %s; unknown rate %s%s"
            % (ordered,
               "%.1f%%" % (unknown_rate * 100)
               if unknown_rate is not None else "not recorded",
               digest_note)
        )
    return lines
