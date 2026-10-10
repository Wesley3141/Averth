"""Check: dead-branch retry must not smear the productive merge step."""
import os, sys
sys.path.insert(0, os.path.expanduser("~/workspace/averth"))
from averth import stress

# count standard() fan-out attempts via events
t, events = stress.generate(seed=42, attempts=2000, record_events=True)
# find attempts with branch events
by_case = {}
for e in events:
    by_case.setdefault(e["case_id"], []).append(e)
branched_cases = [c for c, evs in by_case.items() if any(e.get("branch") for e in evs)]
print("attempts with branch-tagged events:", len(branched_cases))

# inspect the tracker state for one such attempt: the merge step must NOT be waste
n_checked = 0
for a in t.attempts:
    if a["case_id"] not in branched_cases:
        continue
    steps = a["steps"]
    # merge step: last PLANNER model call with branch None after a branched retry
    br_steps = [s for s in steps if s.get("branch")]
    unbr = [s for s in steps if not s.get("branch")]
    assert br_steps, "expected branch steps"
    # the dead branch's pre-retry steps should be marked retry=True
    dead_marked = [s for s in br_steps if s["retry"]]
    # merge = model steps with branch None that come after the last branch step
    last_br_idx = max(i for i, s in enumerate(steps) if s.get("branch"))
    merge_steps = [s for i, s in enumerate(steps) if i > last_br_idx]
    merge_waste = [s for s in merge_steps if s["retry"]]
    n_checked += 1
    if n_checked <= 2:
        print(a["case_id"], "branch steps:", len(br_steps),
              "dead marked waste:", len(dead_marked),
              "merge steps after last branch:", len(merge_steps),
              "merge marked waste:", len(merge_waste))
print("branched attempts inspected:", n_checked)

# yield impact: compare yield of branched attempts vs global
import statistics
br_yield = []
for a in t.attempts:
    term = a.get("terminal_tokens", 0)
    tot = a.get("total_tokens", 0)
    if tot:
        br_yield.append(term / tot)
print("attempt-level mean yield overall: %.4f" % statistics.mean(br_yield))

# confirm events schema strictness: a branched retry round-trips through jsonl importer
from averth.importers import jsonl as J
br_retry_evs = [e for e in events if e["type"] == "retry" and e.get("branch")]
print("branch-scoped retry events:", len(br_retry_evs))
