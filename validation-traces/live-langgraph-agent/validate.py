"""Zero-hand-fixing validator for the live LangGraph validation batch.

Compares frozen snapshots against the archived 16-run event stream and fails
on drift. The ledger and P&L snapshots were regenerated from events.jsonl
after the failed-attempt waste rule changed; they no longer provide an
independent in-process comparison:
  1. pnl.json            - current expected report metrics snapshot
  2. ledger.json         - current ledger snapshot
  3. events.jsonl        - archived EVENT-schema input, fed through the
                           CLI importer path (load_jsonl -> events_to_tracker)

Also runs structural checks: attempt counts, case ids, success flags vs
the run log, retry attribution, parallel-branch tool capture, failed-run
marking, per-model splits, unpriced-model flagging.

Usage: .venv/bin/python validate.py   (exit 0 = all clean)
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from averth.importers import jsonl as jsonl_importer
from averth.importers import common as importer_common

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    truth = json.load(open(os.path.join(HERE, "pnl.json")))
    ledger = json.load(open(os.path.join(HERE, "ledger.json")))

    # View 2: ledger round-trip through tracker_from_ledger
    t_ledger = importer_common.tracker_from_ledger(ledger)
    p_ledger = t_ledger.pnl()

    # View 3: events.jsonl through the real CLI importer path
    ev_ledger = jsonl_importer.load_jsonl(os.path.join(HERE, "events.jsonl"),
                                          agent_name="live-langgraph-validation")
    t_cli = importer_common.tracker_from_ledger(ev_ledger)
    p_cli = t_cli.pnl()

    # ---- 1. the three views agree on headline numbers ----
    for label, p in (("ledger", p_ledger), ("cli", p_cli)):
        check(f"{label}: attempts == 16", p["attempts"] == 16, p["attempts"])
        check(f"{label}: successes == 12", p["successes"] == 12, p["successes"])
        check(f"{label}: retries == 21", p["retries"] == 21, p["retries"])
        for key in ("cost_model", "cost_tools", "cost_retry", "cost_human",
                    "cost_total", "yield_ratio", "avg_context_growth",
                    "business_value", "net_value"):
            check(f"{label}: {key} matches expected snapshot",
                  close(p[key], truth[key]), f"{p[key]} vs {truth[key]}")
        check(f"{label}: per_success.fully_loaded matches",
              close(p["per_success"]["fully_loaded"],
                    truth["per_success"]["fully_loaded"]))
        check(f"{label}: per_model keys match",
              set(p["per_model"]) == set(truth["per_model"]),
              f"{p['per_model']} vs {truth['per_model']}")
        for k in truth["per_model"]:
            check(f"{label}: per_model[{k}] matches",
                  close(p["per_model"][k], truth["per_model"][k]))
        check(f"{label}: tail stats match",
              all(close(p["tail"][k], truth["tail"][k])
                  for k in ("p50", "p95", "max", "top5pct_share")))
        check(f"{label}: unpriced_models match",
              p["unpriced_models"] == truth["unpriced_models"],
              f"{p['unpriced_models']}")

    # ---- 2. structural checks on the ledger ----
    attempts = ledger["attempts"]
    check("ledger: 16 attempt rows", len(attempts) == 16)
    case_ids = [a["case_id"] for a in attempts]
    check("ledger: case ids RUN-01..RUN-16 in order",
          case_ids == [f"RUN-{i:02d}" for i in range(1, 17)], case_ids)

    failed = {a["case_id"] for a in attempts if not a["success"]}
    check("ledger: failed runs are RUN-04,08,13,16",
          failed == {"RUN-04", "RUN-08", "RUN-13", "RUN-16"}, sorted(failed))

    # every attempt recorded both parallel-branch tools (fan-out capture)
    # tool spend per attempt >= web_search(0.005) + github_lookup(0.002)
    for a in attempts:
        check(f"ledger: {a['case_id']} captured fan-out tools",
              a["tools"] >= 0.005 + 0.002 - 1e-12, a["tools"])

    # RUN-04: genuine network degradation -> BOTH parallel tools timed out
    # (ReadTimeout on web_search AND github_lookup), 2 retries, failed
    # attempt; both failed tool costs still recorded.
    r04 = next(a for a in attempts if a["case_id"] == "RUN-04")
    check("ledger: RUN-04 retries == 2 (real double timeout)", r04["retries"] == 2)
    check("ledger: RUN-04 failed", r04["success"] is False)
    check("ledger: RUN-04 tool spend covers both failed tools",
          close(r04["tools"], 0.005 + 0.002), r04["tools"])

    # doomed runs: 3 genuine HTTP 500s each -> 3 retries, failed
    for cid in ("RUN-08", "RUN-13", "RUN-16"):
        a = next(x for x in attempts if x["case_id"] == cid)
        check(f"ledger: {cid} retries == 3", a["retries"] == 3, a["retries"])
        check(f"ledger: {cid} tool spend covers 3 failed fetches",
              a["tools"] >= 0.005 + 0.002 + 3 * 0.002 - 1e-12, a["tools"])

    # flaky runs: 2 retries then success; report model call lands on the
    # retry path -> waste_tokens > 0 (yield < 1)
    for cid in ("RUN-05", "RUN-06", "RUN-09", "RUN-11", "RUN-15"):
        a = next(x for x in attempts if x["case_id"] == cid)
        check(f"ledger: {cid} retries == 2", a["retries"] == 2, a["retries"])
        check(f"ledger: {cid} waste_tokens > 0", a["waste_tokens"] > 0,
              a["waste_tokens"])

    # clean runs: no retries, no waste
    for cid in ("RUN-01", "RUN-02", "RUN-03", "RUN-07", "RUN-10", "RUN-12", "RUN-14"):
        a = next(x for x in attempts if x["case_id"] == cid)
        check(f"ledger: {cid} retries == 0", a["retries"] == 0)
        check(f"ledger: {cid} waste_tokens == 0", a["waste_tokens"] == 0)

    # totals reconcile
    check("ledger: sum(total_cost) == cost_total",
          close(sum(a["total_cost"] for a in attempts), truth["cost_total"]))
    check("ledger: sum(retries) == 21",
          sum(a["retries"] for a in attempts) == 21)
    check("ledger: sum(total_tokens) > 0",
          sum(a["total_tokens"] for a in attempts) > 0)

    # events.jsonl line count: per attempt 1 start + 1 end; model events:
    # 16 plans + 12 reports = 28; tool events: 16 web_search + 16
    # github_lookup + 31 flaky_fetch (7 clean x1 + 5 flaky x3 + 3 doomed x3);
    # retries = 21. Total: 32 + 28 + 63 + 21 = 144.
    n_lines = sum(1 for ln in open(os.path.join(HERE, "events.jsonl"))
                  if ln.strip())
    check("events.jsonl: 144 lines", n_lines == 144, n_lines)

    print()
    if FAILURES:
        print(f"VALIDATION FAILED: {len(FAILURES)} check(s)")
        sys.exit(1)
    print("VALIDATION CLEAN: archived events match current snapshots")


if __name__ == "__main__":
    main()
