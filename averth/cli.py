"""Command line interface for averth.

Usage:
    averth trace <file> --format otel|langsmith|jsonl|langfuse|claude|codex [--html PATH]
                 [--policy-cap FLOAT] [--policy-yield FLOAT] [--agent NAME]
    averth try [<file>] [--format auto|traj|jsonl|langfuse] [--model NAME]
                 [--recorded DOLLARS] [--ledger PATH] [--checks PATH]
                 [--out PATH] [--receipt PATH] [--agent NAME]
    averth simulate --attempts N --seed S [--jsonl PATH] [--html PATH]
                 [--agent NAME]
    averth pricing

``try`` is the one-command free run: it meters a trace file (a
mini-SWE-agent trajectory, JSONL events, or a Langfuse export),
prints the text report, and writes a self-contained HTML report you
can share, plus an "Averth Agent PR Receipt (trace-observed)"
(compact Markdown for pasting into a GitHub PR description). With no
trace argument it scans your last 10 local Claude Code / Codex
sessions instead (zero-config: no flags required). ``--recorded`` is
an operator-supplied figure claimed to be the run's recorded cost,
shown next to the metered estimate; Averth does not verify it. It
is accepted for explicit traces only (refused in scan mode) and is
never used for the receipt's trace-recorded-vs-estimated check (D5),
which compares only the trace's own recorded cost. ``--ledger``
adds a V0 verdict summary from a V0 evidence ledger (``--checks``
verifies the ledger's checks digest and refuses on mismatch). The
receipt also carries the default checks (trace-observed): five
checks judged only on what the transcript shows, needing no
human-written checks. No network, no account, no upload.

Parses an agent trace into a cost ledger, prints the text P&L report to
stdout, and writes a shareable one-page HTML report. `simulate` generates
adversarial synthetic production traffic (retries, escalations, heavy-tail
runaways, context growth, cache hits, parallel branches) so you can see what
the report looks like on production-shaped data before instrumenting anything
real. `pricing` shows the price-table version, verification date, and
staleness status behind every dollar figure. Imports of the trace-importer
modules are deferred to main() so this
module always imports cleanly.
"""

import argparse
import math
import os
import stat
import sys


def _importer_for(fmt):
    if fmt == "otel":
        from averth.importers import otel as mod
        return mod.load_otel, "averth.importers.otel"
    if fmt == "langsmith":
        from averth.importers import langsmith as mod
        return mod.load_langsmith, "averth.importers.langsmith"
    if fmt == "jsonl":
        from averth.importers import jsonl as mod
        return mod.load_jsonl, "averth.importers.jsonl"
    if fmt == "langfuse":
        from averth.importers import langfuse as mod
        return mod.load_langfuse, "averth.importers.langfuse"
    if fmt == "claude":
        from averth.importers import claude as mod
        return mod.load_claude, "averth.importers.claude"
    if fmt == "codex":
        from averth.importers import codex as mod
        return mod.load_codex, "averth.importers.codex"
    raise ValueError("unsupported format: %r (use otel, langsmith, langfuse, jsonl, claude, or codex)"
                     % (fmt,))


def build_parser():
    p = argparse.ArgumentParser(prog="averth", description="Averth: meter, attribute, report.")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("trace", help="Build a P&L report from an agent trace file.")
    t.add_argument("file", help="Trace file to parse.")
    t.add_argument("--format", required=True,
                   choices=["otel", "langsmith", "langfuse", "jsonl", "claude", "codex"],
                   help="Trace format.")
    t.add_argument("--html", default=None, metavar="PATH",
                   help="HTML report output path (default: <inputfile>.html in cwd).")
    t.add_argument("--policy-cap", type=float, default=None, metavar="FLOAT",
                   help="Replay a hypothetical max-cost-per-attempt policy.")
    t.add_argument("--policy-yield", type=float, default=None, metavar="FLOAT",
                   help="Replay a hypothetical minimum yield-floor policy.")
    t.add_argument("--agent", default=None, metavar="NAME",
                   help="Override the agent name shown in the report.")
    t.add_argument("--anomaly", action="store_true",
                   help="Flag runaway-shaped attempts: cost outliers above "
                        "p95 with their dominant driver. Cost-anomaly "
                        "detection, not attack attribution — inspect, "
                        "don't accuse.")

    y = sub.add_parser("try", help="One-command meter run with a shareable HTML report.")
    y.add_argument("file", nargs="?",
                   help="Trace file to meter (mini-SWE-agent .traj.json, JSONL events, or a Langfuse export). Omit it to scan your last 10 local Claude Code / Codex sessions instead (zero-config scan).")
    y.add_argument("--format", default="auto",
                   choices=["auto", "traj", "jsonl", "langfuse"],
                   help="Trace format (default: auto-detect). Refused in "
                        "scan mode (no trace file).")
    y.add_argument("--model", default=None, metavar="NAME",
                   help="Model name for mini-SWE-agent trajectories (e.g. claude-sonnet-4-20250514). Required unless the file name contains a priced model name. An explicit --model overrides the name inferred from the file name. Ignored for JSONL and Langfuse input, whose models come from the file itself. List priced models with 'averth pricing'. Refused in scan mode (no trace file).")
    y.add_argument("--recorded", type=float, default=None, metavar="DOLLARS",
                   help="Operator-supplied figure claimed to be the recorded cost for the same run (must be positive; e.g. the 'cost' field of a leaderboard per_instance_details.json entry). Averth does not verify it; shown next to the metered estimate. No comparison is shown when the run completed zero runs. Explicit traces only: refused in scan mode, and never used for the receipt's trace-recorded-vs-estimated check (D5), which compares only the trace's own recorded cost.")
    y.add_argument("--ledger", default=None, metavar="PATH",
                   help="V0 evidence ledger JSON to summarize in the report. Without --checks the ledger's checks digest is shown but not verified.")
    y.add_argument("--checks", default=None, metavar="PATH",
                   help="Checks file the V0 ledger was judged under; verifies the ledger's checks digest (refuses on mismatch). Needs --ledger.")
    y.add_argument("--out", default=None, metavar="PATH",
                   help="HTML report output path (default: <stem>-try.html in the current directory, where <stem> is the trace filename without .traj.json or .json). Refuses to overwrite an existing file unless --force is passed.")
    y.add_argument("--agent", default=None, metavar="NAME",
                   help="Agent name shown in the report (default for trajectory input: miniswe-import; for JSONL input: jsonl-import; for Langfuse input: langfuse-import).")
    y.add_argument("--force", action="store_true",
                   help="Overwrite an existing --out file or receipt instead of refusing.")
    y.add_argument("--receipt", default=None, metavar="PATH",
                   help="Markdown receipt output path (default: the HTML "
                        "report path with .html replaced by -receipt.md; "
                        "in scan mode the default is "
                        "averth-scan-receipt.md). The receipt is written "
                        "in both scan mode and explicit-trace mode. The "
                        "receipt is also printed to stdout in scan mode "
                        "only.")

    s = sub.add_parser("simulate",
                       help="Generate adversarial synthetic production traffic "
                            "and report its P&L.")
    s.add_argument("--attempts", type=int, default=2000,
                   help="Number of synthetic attempts (default: 2000).")
    s.add_argument("--seed", type=int, default=42,
                   help="RNG seed; same seed reproduces the same ledger.")
    s.add_argument("--jsonl", default=None, metavar="PATH",
                   help="Also write the synthetic events as JSONL.")
    s.add_argument("--html", default=None, metavar="PATH",
                   help="HTML report output path (default: simulate.html in cwd).")
    s.add_argument("--agent", default="synthetic-support", metavar="NAME",
                   help="Agent name shown in the report.")

    sub.add_parser("pricing",
                   help="Show the price-table version, verification date, "
                        "and staleness status.")

    a = sub.add_parser("advise",
                       help="LLM advisor: recommendation, plain-English "
                            "explanation, or attempt investigation. "
                            "Bring your own API key.")
    a.add_argument("file", help="Trace file to parse.")
    a.add_argument("--format", required=True,
                   choices=["otel", "langsmith", "langfuse", "jsonl", "claude", "codex"],
                   help="Trace format.")
    a.add_argument("--mode", default="recommend",
                   choices=["recommend", "explain", "investigate"],
                   help="What the advisor should do (default: recommend).")
    a.add_argument("--provider", default=None,
                   choices=["anthropic", "openai"],
                   help="LLM provider (default: whichever key is set).")
    a.add_argument("--api-key", default=None, metavar="KEY",
                   help="API key for one call; never stored. "
                        "Prefer AVERTH_ANTHROPIC_KEY / AVERTH_OPENAI_KEY.")
    a.add_argument("--attempt", default=None, metavar="CASE_ID",
                   help="Attempt to investigate (default: costliest).")
    a.add_argument("--agent", default=None, metavar="NAME",
                   help="Override the agent name shown in the report.")
    a.add_argument("--show-prompt", action="store_true",
                   help="Print exactly what would be sent to the LLM and "
                        "exit; no API call, no key needed.")
    a.add_argument("--output", default=None, metavar="PATH",
                   help="Write the advisory text to a file.")
    return p


def _report_and_html(tracker, html_path, policy_sim=None, anomaly=False,
                     try_extras=None, try_summary=(), try_mode=False,
                     model_cost_basis=None, default_checks_summary=None,
                     default_checks_failed=False):
    from averth.report import report_text, write_html
    from averth.insights import findings_text, anomalies_text

    p = tracker.pnl()
    print(report_text(p, try_mode=try_mode,
                      model_cost_basis=model_cost_basis))
    print()
    print("=" * 60)
    findings = findings_text(p)
    if default_checks_summary is not None:
        # The P&L findings must not call a run "clean" that the
        # receipt in the same output flags as failed.
        if default_checks_failed and findings.startswith(
                "No material findings"):
            print(default_checks_summary)
        else:
            print(findings)
            print(default_checks_summary)
    else:
        print(findings)
    if anomaly:
        print()
        print("=" * 60)
        print(anomalies_text(p))
    if policy_sim is not None:
        from averth import policy
        print()
        print(policy.policy_text(policy_sim))
    html_path = os.path.abspath(html_path)
    try:
        write_html(html_path, tracker, policy_sim=policy_sim,
                   try_extras=try_extras, try_mode=try_mode,
                   model_cost_basis=model_cost_basis)
    except Exception as e:
        # A bad --html path must honor the CLI's error contract (clean
        # "averth: error:" on stderr, exit 2), not dump a traceback after
        # printing a report that reads like success.
        print("averth: error: cannot write HTML report to %s: %s"
              % (html_path, e), file=sys.stderr)
        return 2
    print("\nHTML report written to %s" % html_path)
    for line in try_summary:
        print(line)
    return 0


def _detect_try_format(path):
    """Auto-detect a try-it trace format from the file's shape.

    A JSON object with a ``messages`` key is a mini-SWE-agent
    trajectory; a JSON object with ``data`` (or a bare JSON list) is a
    Langfuse export; one JSON object per line is Averth JSONL (a
    single-line JSONL file counts: the line scan runs whenever the
    whole-file parse does not match a shape, and it looks at the
    first 10 non-blank lines, so a header event without a ``type``
    key does not hide valid events below it). Anything else raises
    ValueError naming the supported shapes. The file is read
    incrementally — the object-shape sniff scans the top-level keys
    in chunks until found or the object closes (capped at 16 MiB),
    then the first 10 non-blank lines (1 MiB each at most) are
    scanned for the JSONL shape — never loaded whole, so a
    multi-hundred-MB session file does not cost a whole-file string
    plus a whole-file parse. Corner: a bare JSON list larger than 1 MiB on
    a single line is not detected (its first line is truncated by
    the scan cap).
    """
    import json

    from averth.default_checks import _scan_file_top_level_keys

    try:
        head = bytearray()
        eof = False
        with open(path, "rb") as f:
            while len(head) < 1024 * 1024:
                chunk = f.read(min(65536, 1024 * 1024 - len(head)))
                if not chunk:
                    eof = True
                    break
                head += chunk
    except OSError as e:
        raise ValueError("%s is not readable: %s" % (path, e))
    if not bytes(head).strip():
        raise ValueError("%s is empty" % path)
    try:
        text = bytes(head).decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            "%s is not readable text (binary or non-UTF-8); supply a "
            ".traj.json, JSONL, or Langfuse JSON export" % path
        )
    data = None
    if eof:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
    if isinstance(data, dict):
        if "messages" in data:
            return "traj"
        if "data" in data:
            return "langfuse"
        # A dict with neither key may still be a one-event JSONL file,
        # so fall through to the line scan before rejecting it.
    elif isinstance(data, list):
        return "langfuse"
    if not eof:
        # Only a prefix was read: a truncated object still carries
        # its top-level keys, but a large leading value (e.g. a
        # trajectory's "info" block) can push "messages" past any
        # fixed prefix, so the keys are scanned in chunks until
        # found or the object closes (capped at 16 MiB). A
        # pretty-printed bare list opens with a lone "[" line.
        keys = _scan_file_top_level_keys(path)
        if "messages" in keys:
            return "traj"
        if "data" in keys:
            return "langfuse"
        first_line = text.lstrip().splitlines()[0].strip() \
            if text.lstrip().splitlines() else ""
        if first_line == "[":
            return "langfuse"
    scanned = 0
    try:
        with open(path, "rb") as f:
            while True:
                raw = f.readline(1024 * 1024)
                if not raw:
                    break
                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    break
                if not line:
                    continue
                scanned += 1
                if scanned > 10:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    break
                if isinstance(obj, dict) and "type" in obj:
                    return "jsonl"
    except OSError as e:
        raise ValueError("%s is not readable: %s" % (path, e))
    if isinstance(data, dict):
        raise ValueError(
            "%s is JSON but none of the supported shapes: a "
            "mini-SWE-agent trajectory is a JSON object with a "
            "'messages' key; a Langfuse export is a JSON object with a "
            "'data' key or a bare JSON list; JSONL is one event object "
            "with a 'type' key per line" % path
        )
    raise ValueError(
        "%s is not a mini-SWE-agent trajectory (a JSON object with a "
        "'messages' key), a Langfuse export (a JSON object with a "
        "'data' key or a bare JSON list), or a JSONL events file (one "
        "event object with a 'type' key per line)" % path
    )


def _check_output_parent(abs_path):
    """Validate the parent directory of an output path.

    Returns an error string when the parent does not exist, is not a
    directory, or is not writable; None when the path can be written.
    """
    parent = os.path.dirname(abs_path)
    if not os.path.isdir(parent):
        if os.path.exists(parent):
            reason = "the path %s is not a directory" % parent
        else:
            reason = "the directory %s does not exist" % parent
        return reason
    if not os.access(parent, os.W_OK):
        return "the directory %s is not writable" % parent
    return None


def _refuse_existing(abs_path, force, what):
    """Refuse (or warn) when an output file already exists.

    Returns an exit code (2 on refusal, None to proceed).
    """
    if os.path.exists(abs_path) and not force:
        print("averth: error: %s already exists; pass --force to "
              "overwrite it" % abs_path, file=sys.stderr)
        return 2
    if os.path.exists(abs_path) and force:
        print("averth: warning: overwriting existing %s at %s"
              % (what, abs_path), file=sys.stderr)
    return None


def _refuse_path_collision(first_abs, second_abs, first_what,
                           second_what):
    """Refuse (exit 2) when two output/input paths name the same file.

    ``--force`` means overwrite a *file*, never destroy the other
    output or the input trace: a receipt equal to the HTML report,
    or either output equal to the input trace, is refused up front,
    before any metering, with or without ``--force``.
    """
    if first_abs == second_abs:
        print("averth: error: %s path %s is the same as the %s path; "
              "use a different path"
              % (first_what, first_abs, second_what), file=sys.stderr)
        return 2
    return None


def _refuse_directory_output(abs_path, what):
    """Refuse (exit 2) when an output path is an existing directory.

    ``--force`` never replaces a directory. Checked up front, so a
    bad receipt path cannot fail after the HTML report has already
    been written and printed as a success.
    """
    if os.path.isdir(abs_path):
        print("averth: error: cannot write %s to %s: it is a "
              "directory (--force never replaces a directory)"
              % (what, abs_path), file=sys.stderr)
        return 2
    return None


def _write_receipt_file(receipt_abs, receipt_text):
    """Write the receipt Markdown file. Returns 0 or 2."""
    try:
        with open(receipt_abs, "w", encoding="utf-8") as f:
            f.write(receipt_text)
    except Exception as e:
        print("averth: error: cannot write receipt to %s: %s"
              % (receipt_abs, e), file=sys.stderr)
        return 2
    print("Receipt written to %s (Markdown for pasting into a GitHub "
          "PR description)" % receipt_abs)
    return 0


def _default_checks_summary(checks):
    """One-line default-checks summary for the P&L findings."""
    counts = {v: 0 for v in
              ("VERIFIED", "FAILED", "NOT OBSERVED",
               "EXTERNAL-UNVERIFIABLE")}
    for check in checks:
        if check["verdict"] in counts:
            counts[check["verdict"]] += 1
    return ("Default checks (trace-observed): %d VERIFIED, %d FAILED, "
            "%d NOT OBSERVED, %d EXTERNAL-UNVERIFIABLE — see the "
            "receipt."
            % (counts["VERIFIED"], counts["FAILED"],
               counts["NOT OBSERVED"],
               counts["EXTERNAL-UNVERIFIABLE"]))


def _cmd_try_scan(args):
    """Zero-config scan: meter the last 10 local sessions.

    Discovers Claude Code sessions and Codex rollouts under the home
    directory, meters them with the existing importers, judges the
    default checks (trace-observed) over the raw transcripts, and
    writes the HTML report plus the PR receipt (printed to stdout
    too). A session file that fails to parse is skipped with a
    warning counted in the report, never silently dropped; if ALL
    fail, exit 2. No sessions at all is exit 2 naming the
    directories checked.
    """
    offending = []
    if args.format != "auto":
        offending.append("--format")
    if args.model:
        offending.append("--model")
    if args.recorded is not None:
        offending.append("--recorded")
    if offending:
        if len(offending) == 1:
            names, verb = offending[0], "applies"
        elif len(offending) == 2:
            names, verb = " and ".join(offending), "apply"
        else:
            names = ", ".join(offending[:-1]) + ", and " + offending[-1]
            verb = "apply"
        hint = ""
        if "--recorded" in offending:
            hint = ("; the receipt compares the trace's own recorded "
                    "cost")
        print("averth: error: scan mode does not accept %s; %s %s to "
              "explicit traces only — run 'averth try <file>' for a "
              "single trace%s"
              % (names, "it" if len(offending) == 1 else "they", verb,
                 hint), file=sys.stderr)
        return 2
    if args.checks and not args.ledger:
        print("averth: error: --checks needs --ledger", file=sys.stderr)
        return 2
    if args.recorded is not None and (
            not math.isfinite(args.recorded) or args.recorded <= 0):
        print("averth: error: --recorded must be a positive dollar figure",
              file=sys.stderr)
        return 2
    from averth import default_checks, local_scan
    from averth import receipt as receipt_mod
    selected, skipped, checked, total_found = \
        local_scan.discover_sessions()
    if not selected:
        extra = ""
        n_subagent = sum(1 for s in skipped
                         if s["reason"].startswith("subagent rollout"))
        if n_subagent:
            extra = (" (%d subagent rollout(s) found but excluded by "
                     "default; pass a rollout file explicitly: "
                     "averth try <path-to-rollout.jsonl>)"
                     % n_subagent)
        print("averth: error: no local Claude Code or Codex sessions "
              "found%s; checked %s and %s. No sessions yet? Run "
              "Claude Code or Codex once to create one, or meter a "
              "single trace file instead: averth try <trace-file>"
              % (extra, checked[0], checked[1]), file=sys.stderr)
        return 2
    html_path = args.out or "averth-scan.html"
    html_abs = os.path.abspath(html_path)
    err = _check_output_parent(html_abs)
    if err is not None:
        print("averth: error: cannot write HTML report to %s: %s"
              % (html_abs, err), file=sys.stderr)
        return 2
    receipt_path = (args.receipt
                    or receipt_mod.receipt_path_for_html(html_abs))
    receipt_abs = os.path.abspath(receipt_path)
    err = _check_output_parent(receipt_abs)
    if err is not None:
        print("averth: error: cannot write receipt to %s: %s"
              % (receipt_abs, err), file=sys.stderr)
        return 2
    # Collision guards, up front before any metering: the receipt
    # must never overwrite the HTML report (or vice versa).
    rc = _refuse_path_collision(receipt_abs, html_abs, "--receipt",
                                "HTML report")
    if rc is not None:
        return rc
    rc = _refuse_directory_output(receipt_abs, "receipt")
    if rc is not None:
        return rc
    rc = _refuse_directory_output(html_abs, "HTML report")
    if rc is not None:
        return rc
    from averth.importers import claude as claude_mod
    from averth.importers import codex as codex_mod
    from averth.importers import common
    events = []
    evidences = []
    scanned = []
    parse_failures = []
    for cand in selected:
        path = cand["path"]
        try:
            if cand["source"] == "claude":
                file_events, _stats = claude_mod.parse_claude_session(path)
            else:
                file_events, _stats = codex_mod.parse_codex_rollout(path)
        except Exception as e:
            parse_failures.append(path)
            print("averth: warning: skipping %s: failed to parse (%s)"
                  % (path, e), file=sys.stderr)
            continue
        events.extend(file_events)
        if cand["source"] == "claude":
            evidences.append(default_checks.extract_claude(path))
        else:
            evidences.append(default_checks.extract_codex(path))
        scanned.append(cand)
    if not scanned:
        print("averth: error: all %d session file(s) failed to parse "
              "(%s); nothing to meter. Check the newest session file "
              "opens as JSONL, or meter one file explicitly to see its "
              "parse error: averth try <file>"
              % (len(selected), ", ".join(parse_failures)),
              file=sys.stderr)
        return 2
    try:
        tracker = common.events_to_tracker("local-scan", events)
    except Exception as e:
        print("averth: error: cannot build tracker from sessions: %s" % e,
              file=sys.stderr)
        return 2
    if args.agent:
        tracker.agent_name = args.agent
    pnl = tracker.pnl()
    if pnl["attempts"] == 0:
        print("averth: error: the scanned sessions contain no model "
              "calls (no usage records found); nothing to meter. "
              "Sessions without model usage cannot be metered — run a "
              "session that makes model calls, or meter a trace file "
              "instead: averth try <trace-file>", file=sys.stderr)
        return 2
    # The V0 ledger is verified BEFORE anything is written, as in
    # explicit mode.
    v0 = None
    digest_verified = None
    if args.ledger:
        try:
            from averth import try_report
            v0, digest_verified = try_report.load_v0_ledger(
                args.ledger, args.checks)
        except Exception as e:
            if ("digest mismatch" in str(e)
                    and os.path.exists(html_abs)):
                print("averth: warning: a previous report remains at "
                      "%s; it is NOT this run's output (this run was "
                      "refused)" % html_abs, file=sys.stderr)
            print("averth: error: %s" % e, file=sys.stderr)
            return 2
    rc = _refuse_existing(html_abs, args.force, "report")
    if rc is not None:
        return rc
    rc = _refuse_existing(receipt_abs, args.force, "receipt")
    if rc is not None:
        return rc
    evidence = default_checks.merge_evidence(evidences)
    checks = default_checks.judge_default_checks(
        evidence, pnl["cost_total"])
    n_claude = sum(1 for c in scanned if c["source"] == "claude")
    n_codex = len(scanned) - n_claude
    n_subagent = sum(1 for s in skipped
                     if s["reason"].startswith("subagent rollout"))
    n_other_skipped = len(skipped) - n_subagent
    if total_found > len(scanned):
        scanned_part = ("%d session(s) scanned (of %d found; newest %d)"
                        % (len(scanned), total_found, len(scanned)))
    else:
        scanned_part = ("%d session(s) scanned (of %d found)"
                        % (len(scanned), total_found))
    scan_note = (
        "Local scan: %s (%d Claude Code, %d Codex); "
        "%d skipped (subagent rollouts); %d failed to parse. Token "
        "counts are trace-supplied; Averth does not verify them as "
        "recorded usage."
        % (scanned_part, n_claude, n_codex, n_subagent,
           len(parse_failures)))
    if n_other_skipped:
        scan_note += (" %d other file(s) skipped (not a regular file "
                      "or unreadable)." % n_other_skipped)
    source_note = (
        "Trace: local scan of %d session(s) (%s). Token counts are "
        "trace-supplied; Averth does not verify them as recorded "
        "usage."
        % (len(scanned),
           ", ".join(local_scan.display_name(c) for c in scanned)))
    from averth import try_report
    try:
        extras = try_report.build_try_extras(
            pnl, recorded=args.recorded, v0=v0,
            digest_verified=digest_verified, source_note=source_note)
        summary = try_report.try_summary_lines(
            pnl, recorded=args.recorded, v0=v0,
            digest_verified=digest_verified, source_note=source_note)
    except Exception as e:
        print("averth: error: %s" % e, file=sys.stderr)
        return 2
    receipt_text = receipt_mod.render_receipt(
        sources=[local_scan.display_name(c) for c in scanned],
        estimated_cost=pnl["cost_total"],
        recorded_cost=evidence["recorded_cost"],
        recorded_note=receipt_mod.recorded_note_for(checks),
        checks=checks,
        unknown_rate=default_checks.unknown_rate(checks),
        scan_note=scan_note)
    # The receipt is written BEFORE the HTML report, so a receipt
    # failure can never follow a success-looking report write.
    rc = _write_receipt_file(receipt_abs, receipt_text)
    if rc != 0:
        return rc
    checks_summary = _default_checks_summary(checks)
    checks_failed = any(c["verdict"] == "FAILED" for c in checks)
    rc = _report_and_html(tracker, html_path, try_extras=extras,
                          try_summary=summary, try_mode=True,
                          default_checks_summary=checks_summary,
                          default_checks_failed=checks_failed)
    if rc != 0:
        return rc
    print()
    print("--- Averth PR receipt (also written to %s): copy from the "
          "line below to the end of the output ---" % receipt_abs)
    print(receipt_text)
    return 0


def _cmd_try(args):
    if args.file is None:
        return _cmd_try_scan(args)
    path = args.file
    if os.path.isdir(path):
        print("averth: error: %s is a directory; pass a trace file, not "
              "a directory" % path, file=sys.stderr)
        return 2
    if not os.path.exists(path):
        print("averth: error: file not found: %s" % path, file=sys.stderr)
        return 2
    if not stat.S_ISREG(os.lstat(path).st_mode):
        print("averth: error: %s is not a regular file; pass a trace "
              "file, not a special file" % path, file=sys.stderr)
        return 2
    if args.checks and not args.ledger:
        print("averth: error: --checks needs --ledger", file=sys.stderr)
        return 2
    if args.recorded is not None and (
            not math.isfinite(args.recorded) or args.recorded <= 0):
        print("averth: error: --recorded must be a positive dollar figure",
              file=sys.stderr)
        return 2
    fmt = args.format
    if fmt == "auto":
        try:
            fmt = _detect_try_format(path)
        except ValueError as e:
            print("averth: error: cannot detect trace format: %s" % e,
                  file=sys.stderr)
            return 2
    # Resolve the default --out path now, and validate its parent
    # directory before any metering or printing, so a bad --out fails
    # fast instead of printing a success-looking report first.
    base = os.path.basename(path)
    if args.out:
        html_path = args.out
    else:
        # "django-15930.traj.json" -> "django-15930-try.html", not
        # "django-15930.traj-try.html".
        stem = os.path.splitext(base)[0]
        if stem.endswith(".traj"):
            stem = stem[:-5]
        html_path = stem + "-try.html"
    html_abs = os.path.abspath(html_path)
    parent = os.path.dirname(html_abs)
    if not os.path.isdir(parent):
        if os.path.exists(parent):
            reason = "the path %s is not a directory" % parent
        else:
            reason = "the directory %s does not exist" % parent
        print("averth: error: cannot write HTML report to %s: %s"
              % (html_abs, reason), file=sys.stderr)
        return 2
    if not os.access(parent, os.W_OK):
        print("averth: error: cannot write HTML report to %s: the "
              "directory %s is not writable" % (html_abs, parent),
              file=sys.stderr)
        return 2
    # Receipt path: default derives from the HTML report path (same
    # stem rule); --receipt overrides it. Validated up front like
    # --out, so a bad --receipt fails fast too.
    from averth import receipt as receipt_mod
    receipt_path = (args.receipt
                    or receipt_mod.receipt_path_for_html(html_abs))
    receipt_abs = os.path.abspath(receipt_path)
    err = _check_output_parent(receipt_abs)
    if err is not None:
        print("averth: error: cannot write receipt to %s: %s"
              % (receipt_abs, err), file=sys.stderr)
        return 2
    # Collision guards, up front before any metering: the receipt
    # must never overwrite the HTML report or the input trace, and
    # --out must never overwrite the input trace either.
    trace_abs = os.path.abspath(path)
    rc = _refuse_path_collision(receipt_abs, html_abs, "--receipt",
                                "HTML report")
    if rc is not None:
        return rc
    rc = _refuse_path_collision(receipt_abs, trace_abs, "--receipt",
                                "input trace")
    if rc is not None:
        return rc
    rc = _refuse_path_collision(html_abs, trace_abs, "--out",
                                "input trace")
    if rc is not None:
        return rc
    rc = _refuse_directory_output(receipt_abs, "receipt")
    if rc is not None:
        return rc
    rc = _refuse_directory_output(html_abs, "HTML report")
    if rc is not None:
        return rc
    # An unknown model is refused, never silently fallback-priced: a
    # typo'd --model must not produce a confident wrong report.
    if fmt == "traj":
        from averth.importers import miniswe as miniswe_mod
        model = args.model or miniswe_mod._infer_model(path)
        if model is not None and not miniswe_mod.is_priced_model(model):
            print("averth: error: unknown model '%s': not in the Averth "
                  "price table; run 'averth pricing' to list priced "
                  "models" % model, file=sys.stderr)
            return 2
    try:
        if fmt == "traj":
            from averth.importers import miniswe as mod
            ledger = mod.load_miniswe(path, model=args.model)
        else:
            load, _mod_name = _importer_for(fmt)
            ledger = load(path)
    except Exception as e:
        if args.format != "auto":
            # An explicitly forced format that fails to parse is most
            # often the wrong format, not a corrupt file: say so, and
            # name what auto-detection sees.
            try:
                detected = _detect_try_format(path)
            except ValueError:
                detected = None
            hint = ("; auto-detection says this looks like %s" % detected
                    if detected and detected != fmt else "")
            print("averth: error: %s does not parse as %s (%s); it may "
                  "be another format -- try --format auto or one of "
                  "traj|jsonl|langfuse%s" % (path, fmt, e, hint),
                  file=sys.stderr)
            return 2
        print("averth: error: failed to parse %s (%s): %s" % (path, fmt, e),
              file=sys.stderr)
        return 2
    try:
        from averth.importers import common
        tracker = common.tracker_from_ledger(ledger)
    except Exception as e:
        print("averth: error: cannot build tracker from ledger: %s" % e,
              file=sys.stderr)
        return 2
    if args.agent:
        tracker.agent_name = args.agent
    if tracker.pnl()["attempts"] == 0:
        print("averth: error: %s contains no traces (empty export); "
              "nothing to meter" % path, file=sys.stderr)
        return 2
    # The V0 ledger is verified BEFORE anything is written: a digest
    # mismatch refuses the whole report instead of writing a report
    # that presents verdicts judged under different checks.
    v0 = None
    digest_verified = None
    if args.ledger:
        try:
            from averth import try_report
            v0, digest_verified = try_report.load_v0_ledger(
                args.ledger, args.checks)
        except Exception as e:
            if ("digest mismatch" in str(e)
                    and os.path.exists(html_abs)):
                print("averth: warning: a previous report remains at "
                      "%s; it is NOT this run's output (this run was "
                      "refused)" % html_abs, file=sys.stderr)
            print("averth: error: %s" % e, file=sys.stderr)
            return 2
    # A previous report is never silently overwritten: re-running the
    # command after a typo must not destroy a good report. The same
    # rule covers the receipt.
    if os.path.exists(html_abs) and not args.force:
        print("averth: error: %s already exists; pass --force to "
              "overwrite it" % html_abs, file=sys.stderr)
        return 2
    if os.path.exists(html_abs) and args.force:
        print("averth: warning: overwriting existing report at %s"
              % html_abs, file=sys.stderr)
    rc = _refuse_existing(receipt_abs, args.force, "receipt")
    if rc is not None:
        return rc
    from averth import try_report
    traj_recorded = None
    model_cost_basis = None
    if fmt == "traj":
        traj_recorded = miniswe_mod.traj_instance_cost(path)
        source_note = (
            "Trace: %s (mini-SWE-agent trajectory). Token counts are "
            "characters/4 estimates from the trajectory text, not "
            "provider-recorded usage; the dollars apply vendor list "
            "prices to those estimates." % base
        )
        model_cost_basis = (
            "versioned list prices and converter-estimated token "
            "counts (characters/4 from the trajectory text, not "
            "provider-reported usage); reconcile against the customer "
            "invoice before calling this actual spend.")
    elif fmt == "jsonl":
        source_note = (
            "Trace: %s (Averth JSONL events). Token counts are "
            "trace-supplied; Averth does not verify them as recorded "
            "usage." % base
        )
    else:
        source_note = (
            "Trace: %s (Langfuse export). Token counts and costs are "
            "trace-supplied; Averth does not verify them as recorded "
            "usage." % base
        )
    pnl = tracker.pnl()
    try:
        extras = try_report.build_try_extras(
            pnl, recorded=args.recorded, v0=v0,
            digest_verified=digest_verified, source_note=source_note,
            traj_recorded=traj_recorded)
        summary = try_report.try_summary_lines(
            pnl, recorded=args.recorded, v0=v0,
            digest_verified=digest_verified, source_note=source_note,
            traj_recorded=traj_recorded)
    except Exception as e:
        print("averth: error: %s" % e, file=sys.stderr)
        return 2
    # The receipt is written in both scan mode and explicit-trace
    # mode (one behavior). Its default checks are judged on the raw
    # trace file, not on the metered ledger: the importers emit no
    # tool events, so the evidence comes from the transcript itself.
    # The operator-supplied --recorded figure is NOT used for D5:
    # D5 compares the trace's own recorded cost (traj instance_cost
    # / Claude result.total_cost_usd) with the metered estimate.
    from averth import default_checks
    evidence = default_checks.merge_evidence(
        [default_checks.extract_from_file(path)])
    checks = default_checks.judge_default_checks(
        evidence, pnl["cost_total"])
    sources = evidence.get("sources") or []
    if len(sources) == 1 and sources[0] in ("traj", "claude", "codex"):
        source_kind = {"traj": "mini-SWE-agent trajectory",
                       "claude": "Claude session",
                       "codex": "Codex rollout"}[sources[0]]
    elif fmt in ("jsonl", "langfuse"):
        source_kind = {"jsonl": "JSONL",
                       "langfuse": "Langfuse"}[fmt]
    else:
        source_kind = None
    receipt_text = receipt_mod.render_receipt(
        sources=evidence["sessions"],
        source_kind=source_kind,
        estimated_cost=pnl["cost_total"],
        recorded_cost=evidence["recorded_cost"],
        recorded_note=receipt_mod.recorded_note_for(checks),
        checks=checks,
        unknown_rate=default_checks.unknown_rate(checks))
    # The receipt is written BEFORE the HTML report, so a receipt
    # failure can never follow a success-looking report write.
    rc = _write_receipt_file(receipt_abs, receipt_text)
    if rc != 0:
        return rc
    checks_summary = _default_checks_summary(checks)
    checks_failed = any(c["verdict"] == "FAILED" for c in checks)
    rc = _report_and_html(tracker, html_path, try_extras=extras,
                          try_summary=summary, try_mode=True,
                          model_cost_basis=model_cost_basis,
                          default_checks_summary=checks_summary,
                          default_checks_failed=checks_failed)
    if rc != 0:
        return rc
    return 0


def _cmd_simulate(args):
    from averth import stress
    if args.attempts < 1:
        print("averth: error: --attempts must be >= 1", file=sys.stderr)
        return 2
    tracker, _ = stress.generate(seed=args.seed, attempts=args.attempts,
                                 agent_name=args.agent)
    if args.jsonl:
        try:
            stress.write_jsonl(args.jsonl, seed=args.seed,
                               attempts=args.attempts, agent_name=args.agent)
        except Exception as e:
            print("averth: error: cannot write JSONL to %s: %s"
                  % (args.jsonl, e), file=sys.stderr)
            return 2
        print("Synthetic JSONL written to %s" % os.path.abspath(args.jsonl))
    return _report_and_html(tracker, args.html or "simulate.html")


def _cmd_pricing(args):
    """One-command visibility into the price table (C2).

    The meter has no network code by design, so there is no live price
    feed; this command shows exactly which table the dollars come from and
    how stale it is, and tells the operator how to update it.
    """
    from averth import pricing
    v = pricing.price_vintage()
    w = pricing.staleness_warning()
    print("Averth price table v%s" % v["version"])
    print("  last verified : %s (%d days ago)" % (v["updated"], v["age_days"]))
    print("  source        : %s" % pricing.PRICE_TABLE_SOURCE)
    print("  models priced : %d" % len(pricing.MODEL_PRICES))
    print("  tools priced  : %d" % len(pricing.TOOL_PRICES))
    print("  priced models :")
    by_name = {}
    for key in sorted(pricing.MODEL_PRICES):
        # Bare names are what --model takes; the provider prefix
        # (openai:/anthropic:/...) is guessed from the name. A model
        # priced under two provider keys is listed once.
        by_name.setdefault(key.split(":", 1)[-1], set()).add(
            key.split(":", 1)[0])
    for name in sorted(by_name):
        print("    %s" % name)
    multi = sorted(n for n, ps in by_name.items() if len(ps) > 1)
    if multi:
        print("    (%s priced under more than one provider key.)"
              % ", ".join(multi))
    print("  human default : $%.2f/min (~$%.0f/hr loaded, assumption)"
          % (pricing.HUMAN_COST_PER_MIN, pricing.HUMAN_COST_PER_MIN * 60))
    print("  status        : %s" % ("STALE — " + w if w else
                                    "fresh (warns after %d days)"
                                    % v["stale_after_days"]))
    print()
    print("To update: edit averth/pricing.py, bump PRICE_TABLE_VERSION,")
    print("set PRICE_TABLE_UPDATED to today, and add a regression test")
    print("pinning the changed price.")
    return 0


def _cmd_advise(args):
    path = args.file
    if not os.path.isfile(path):
        print("averth: error: file not found: %s" % path, file=sys.stderr)
        return 2
    try:
        load, mod_name = _importer_for(args.format)
    except (ImportError, ValueError) as e:
        print("averth: error: bad trace format: %s" % e, file=sys.stderr)
        return 2
    try:
        ledger = load(path)
    except Exception as e:
        print("averth: error: failed to parse %s with %s: %s" % (path, mod_name, e),
              file=sys.stderr)
        return 2
    try:
        from averth.importers import common
        tracker = common.tracker_from_ledger(ledger)
    except Exception as e:
        print("averth: error: cannot build tracker from ledger: %s" % e, file=sys.stderr)
        return 2
    if args.agent:
        tracker.agent_name = args.agent
    try:
        from averth import advise as advise_mod
        pnl = tracker.pnl()
        if args.show_prompt:
            from averth.advise import (_summary_from_pnl, _attempt_summary,
                                      build_prompt)
            summary = _summary_from_pnl(pnl)
            attempt = None
            if args.mode == "investigate":
                cid = args.attempt
                if not cid:
                    det = pnl.get("costliest_attempts") or []
                    cid = det[0]["case_id"] if det else None
                attempt = _attempt_summary(pnl, cid) if cid else None
            print(build_prompt(args.mode, summary, attempt))
            return 0
        text = advise_mod.advise(args.mode, pnl, provider=args.provider,
                                 api_key=args.api_key, case_id=args.attempt)
        if args.output:
            with open(args.output, "w") as f:
                f.write(text + "\n")
            print("Advisory written to %s" % args.output)
        else:
            print(text)
    except RuntimeError as e:
        print("averth: error: %s" % e, file=sys.stderr)
        return 2
    except Exception as e:
        print("averth: error: advisor failed: %s" % e, file=sys.stderr)
        return 2
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "simulate":
        return _cmd_simulate(args)
    if args.cmd == "pricing":
        return _cmd_pricing(args)
    if args.cmd == "advise":
        return _cmd_advise(args)
    if args.cmd == "try":
        return _cmd_try(args)

    path = args.file
    if not os.path.isfile(path):
        print("averth: error: file not found: %s" % path, file=sys.stderr)
        return 2

    try:
        load, mod_name = _importer_for(args.format)
    except (ImportError, ValueError) as e:
        print("averth: error: bad trace format: %s" % e, file=sys.stderr)
        return 2
    except Exception as e:
        print("averth: error: cannot load importer: %s" % e, file=sys.stderr)
        return 2

    try:
        ledger = load(path)
    except Exception as e:
        print("averth: error: failed to parse %s with %s: %s" % (path, mod_name, e),
              file=sys.stderr)
        return 2

    try:
        from averth.importers import common
        tracker = common.tracker_from_ledger(ledger)
    except Exception as e:
        print("averth: error: cannot build tracker from ledger: %s" % e, file=sys.stderr)
        return 2

    if args.agent:
        tracker.agent_name = args.agent

    from averth import policy

    sim = None
    if args.policy_cap is not None or args.policy_yield is not None:
        sim = policy.simulate_policy(ledger,
                                     max_cost_per_attempt=args.policy_cap,
                                     yield_floor=args.policy_yield)

    if args.html:
        html_path = args.html
    else:
        base = os.path.basename(path)
        html_path = os.path.splitext(base)[0] + ".html"
    return _report_and_html(tracker, html_path, policy_sim=sim,
                               anomaly=args.anomaly)


if __name__ == "__main__":
    sys.exit(main())
