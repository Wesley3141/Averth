"""Support benchmark runner: executes an arm over N tickets, grades, reports.

Usage:
  python runner.py --arm A --n 30 [--mock] [--seed 7] [--split dev]

--mock: deterministic mock model (plumbing validation ONLY; mock results
        are never benchmark results and never gate decisions).
Real runs require ANTHROPIC_API_KEY via the custom.anthropic connector.

Output: results/<arm>_n<N>_seed<S>[_mock].json with per-ticket grades and
tracker PnL summary. Primary metric: cost per acceptable resolution.
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", ".."))

import support_agent
from support_agent import TRACKER, build_corpus
import grader

HERE = os.path.dirname(os.path.abspath(__file__))


class MockMsg:
    def __init__(self, text, in_tok, out_tok):
        self._text = text
        self.usage = type("U", (), {"input_tokens": in_tok,
                                    "output_tokens": out_tok})()
        self.content = [type("C", (), {"text": text})()]


class MockClient:
    class messages:
        @staticmethod
        def create(model, max_tokens, system, messages):
            user = messages[0]["content"]
            # deterministic mock: keyword guess (NOT a real model)
            low = user.lower()
            if any(w in low for w in ["traceback", "error", "crash", "broken"]):
                guess = "BUG_FIX"
            elif any(w in low for w in ["how do i", "how to", "can i "]) :
                guess = "HOWTO"
            elif "duplicate" in low:
                guess = "DUPLICATE"
            else:
                guess = "CONFIG"
            if "LABEL:" in system:
                text = (f"LABEL: {guess}\n\nMock response draft for the "
                        f"customer.")
            else:
                text = guess
            in_tok = len(system + user) // 4
            out_tok = len(text) // 4
            return MockMsg(text, in_tok, out_tok)


def run_arm(arm, tasks, mock=False):
    """Run one arm over tasks. Returns (grades, summary). Shared by CLI
    and the deployment gate."""
    real_client = support_agent.client
    if mock:
        support_agent.client = MockClient()
    try:
        grades = []
        cost_before = TRACKER.pnl().get("cost_total", 0)
        for t in tasks:
            try:
                pred, _ = support_agent.resolve_ticket(t)
                g = grader.grade(pred, t)
            except Exception as e:
                try:
                    TRACKER.end_attempt(success=False)
                except Exception:
                    pass
                g = {"task_id": t["id"], "predicted": "ERROR",
                     "actual": t["resolution_label"], "accepted": False,
                     "reopened": bool(t.get("reopened")),
                     "sla_breach": bool(t.get("sla_breach")),
                     "time_to_close_hours": t.get("time_to_close_hours"),
                     "response_draft": "", "error": str(e)[:200]}
            grades.append(g)
    finally:
        support_agent.client = real_client
    summary = grader.summarize(grades)
    total_cost = TRACKER.pnl().get("cost_total", 0) - cost_before
    accepted = summary["accepted"]
    summary["cost_per_accepted_resolution"] = (
        total_cost / accepted) if accepted else None
    summary["total_cost"] = total_cost
    summary["mock"] = mock
    summary["arm"] = arm
    return grades, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--tasks", default=os.path.join(HERE, "tasks.json"))
    args = ap.parse_args()

    if args.mock:
        print("MOCK MODE - plumbing validation only, NOT benchmark results")

    random.seed(args.seed)
    with open(args.tasks) as f:
        data = json.load(f)
    pool = data[args.split][:]
    random.shuffle(pool)
    tasks = pool[:args.n]
    build_corpus(data["dev"] + data["heldout"])

    t0 = time.time()
    grades, summary = run_arm(args.arm, tasks, mock=args.mock)
    summary["elapsed_s"] = round(time.time() - t0, 1)

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    tag = f"{args.arm}_n{args.n}_seed{args.seed}_{args.split}"
    if args.mock:
        tag += "_mock"
    with open(os.path.join(HERE, "results", f"{tag}.json"), "w") as f:
        json.dump({"summary": summary, "grades": grades}, f, indent=1)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
