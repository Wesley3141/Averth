"""Cross-check the meter against real recorded numbers.

per_instance_details.json (from the SWE-bench leaderboard entry) records,
per instance, the REAL cost the submitter measured and the REAL api_calls
count. This script compares those against what averth computed from the
converted trace. Token counts in the trace are mechanical estimates
(chars/4), so this comparison measures how close the estimate lands, not
whether the library arithmetic is right (that is covered by unit tests).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from averth.importers import jsonl, common  # noqa: E402

ledger = jsonl.load_jsonl(os.path.join(HERE, "events.jsonl"),
                          agent_name="mini-swe-agent/claude-sonnet-4")
with open(os.path.join(HERE, "per_instance_details.json")) as f:
    details = json.load(f)

print("%-32s %10s %10s %8s %10s %9s" %
      ("instance", "metered$", "recorded$", "ratio", "api_calls", "turns"))
tot_metered = tot_recorded = 0.0
ratios = []
for a in ledger["attempts"]:
    cid = a["case_id"]
    det = details.get(cid, {})
    recorded = det.get("cost")
    metered = a["total_cost"]
    if recorded:
        tot_metered += metered
        tot_recorded += recorded
        ratios.append(metered / recorded)
    turns = len(a.get("per_model", {})) and a["total_tokens"] or 0
    print("%-32s %10.4f %10.4f %8s %10s %9d" % (
        cid[:32], metered, recorded if recorded else float("nan"),
        ("%.2f" % (metered / recorded)) if recorded else "n/a",
        det.get("api_calls", "n/a"), int(a["total_tokens"] // 1)))
print("-" * 80)
print("total metered $%.4f vs total recorded $%.4f (ratio %.2f)" %
      (tot_metered, tot_recorded, tot_metered / tot_recorded))
import statistics
print("per-instance metered/recorded: median %.2f, mean %.2f, min %.2f, max %.2f" %
      (statistics.median(ratios), statistics.mean(ratios),
       min(ratios), max(ratios)))
