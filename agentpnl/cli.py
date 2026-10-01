"""Command line interface for agentpnl.

Usage:
    agentpnl trace <file> --format otel|langsmith|jsonl [--html PATH]
                 [--policy-cap FLOAT] [--policy-yield FLOAT] [--agent NAME]
    agentpnl simulate --attempts N --seed S [--jsonl PATH] [--html PATH]
                 [--agent NAME]

Parses an agent trace into a cost ledger, prints the text P&L report to
stdout, and writes a shareable one-page HTML report. `simulate` generates
adversarial synthetic production traffic (retries, escalations, heavy-tail
runaways, context growth, cache hits, parallel branches) so you can see what
the report looks like on production-shaped data before instrumenting anything
real. Imports of the trace-importer modules are deferred to main() so this
module always imports cleanly.
"""

import argparse
import os
import sys


def _importer_for(fmt):
    if fmt == "otel":
        from agentpnl.importers import otel as mod
        return mod.load_otel, "agentpnl.importers.otel"
    if fmt == "langsmith":
        from agentpnl.importers import langsmith as mod
        return mod.load_langsmith, "agentpnl.importers.langsmith"
    if fmt == "jsonl":
        from agentpnl.importers import jsonl as mod
        return mod.load_jsonl, "agentpnl.importers.jsonl"
    raise ValueError("unsupported format: %r (use otel, langsmith, or jsonl)" % (fmt,))


def build_parser():
    p = argparse.ArgumentParser(prog="agentpnl", description="Agent P&L: meter, attribute, report.")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("trace", help="Build a P&L report from an agent trace file.")
    t.add_argument("file", help="Trace file to parse.")
    t.add_argument("--format", required=True, choices=["otel", "langsmith", "jsonl"],
                   help="Trace format.")
    t.add_argument("--html", default=None, metavar="PATH",
                   help="HTML report output path (default: <inputfile>.html in cwd).")
    t.add_argument("--policy-cap", type=float, default=None, metavar="FLOAT",
                   help="Replay a hypothetical max-cost-per-attempt policy.")
    t.add_argument("--policy-yield", type=float, default=None, metavar="FLOAT",
                   help="Replay a hypothetical minimum yield-floor policy.")
    t.add_argument("--agent", default=None, metavar="NAME",
                   help="Override the agent name shown in the report.")

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
    return p


def _report_and_html(tracker, html_path, policy_sim=None):
    from agentpnl.report import report_text, write_html
    from agentpnl.insights import findings_text

    p = tracker.pnl()
    print(report_text(p))
    print()
    print("=" * 60)
    print(findings_text(p))
    if policy_sim is not None:
        from agentpnl import policy
        print()
        print(policy.policy_text(policy_sim))
    html_path = os.path.abspath(html_path)
    write_html(html_path, tracker, policy_sim=policy_sim)
    print("\nHTML report written to %s" % html_path)
    return 0


def _cmd_simulate(args):
    from agentpnl import stress
    if args.attempts < 1:
        print("agentpnl: error: --attempts must be >= 1", file=sys.stderr)
        return 2
    tracker, _ = stress.generate(seed=args.seed, attempts=args.attempts,
                                 agent_name=args.agent)
    if args.jsonl:
        stress.write_jsonl(args.jsonl, seed=args.seed,
                           attempts=args.attempts, agent_name=args.agent)
        print("Synthetic JSONL written to %s" % os.path.abspath(args.jsonl))
    return _report_and_html(tracker, args.html or "simulate.html")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "simulate":
        return _cmd_simulate(args)

    path = args.file
    if not os.path.isfile(path):
        print("agentpnl: error: file not found: %s" % path, file=sys.stderr)
        return 2

    try:
        load, mod_name = _importer_for(args.format)
    except (ImportError, ValueError) as e:
        print("agentpnl: error: bad trace format: %s" % e, file=sys.stderr)
        return 2
    except Exception as e:
        print("agentpnl: error: cannot load importer: %s" % e, file=sys.stderr)
        return 2

    try:
        ledger = load(path)
    except Exception as e:
        print("agentpnl: error: failed to parse %s with %s: %s" % (path, mod_name, e),
              file=sys.stderr)
        return 2

    try:
        from agentpnl.importers import common
        tracker = common.tracker_from_ledger(ledger)
    except Exception as e:
        print("agentpnl: error: cannot build tracker from ledger: %s" % e, file=sys.stderr)
        return 2

    if args.agent:
        tracker.agent_name = args.agent

    from agentpnl import policy

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
    return _report_and_html(tracker, html_path, policy_sim=sim)


if __name__ == "__main__":
    sys.exit(main())
