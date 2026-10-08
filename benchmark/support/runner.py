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


def run_arm(arm, tasks, agent_fn=None, mock=False):
    """Run one arm over tasks. Returns (grades, summary). Shared by CLI
    and the deployment gate.

    agent_fn: callable(task) -> (prediction, _). Defaults to the pinned
    arm-A agent. Arms B/C MUST supply their own config via make_variant;
    there is no silent fallback to arm A.
    """
    agent_fn = agent_fn or support_agent.resolve_ticket
    real_client = support_agent.client
    if mock:
        support_agent.client = MockClient()
    try:
        grades = []
        cost_before = TRACKER.pnl().get("cost_total", 0)
        for t in tasks:
            try:
                pred, _ = agent_fn(t)
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
    # Honest name: v1 acceptance is label accuracy, not resolved work.
    summary["cost_per_correctly_classified"] = (
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
    ap.add_argument("--manifest",
                    help="JSON config manifest for arm B/C "
                         "(required for B/C; e.g. {\"version\": \"b1\", "
                         "\"model\": ..., \"prompt\": ...}). Arm A always "
                         "uses the pinned agent.")
    args = ap.parse_args()

    if args.mock:
        print("MOCK MODE - plumbing validation only, NOT benchmark results")

    # Explicit arm dispatch: B/C are separate implementations, not labels.
    manifest = None
    if args.arm in ("B", "C"):
        if not args.manifest:
            ap.error(f"--arm {args.arm} requires --manifest with the arm's "
                     f"config (refusing to silently run arm A)")
        with open(args.manifest) as f:
            manifest = json.load(f)
        agent_fn = support_agent.make_variant(manifest)
    elif args.arm == "A":
        agent_fn = support_agent.resolve_ticket
    else:
        ap.error(f"unknown arm {args.arm!r} (expected A, B, or C)")

    random.seed(args.seed)
    with open(args.tasks) as f:
        data = json.load(f)
    pool = data[args.split][:]
    random.shuffle(pool)
    tasks = pool[:args.n]
    # Retrieval corpus is dev-only, always: at heldout-evaluation time the
    # agent may only consult past (dev) tickets, mirroring deployment.
    # (Including heldout in the corpus would leak heldout labels via the
    # similar-ticket tool.)
    build_corpus(data["dev"])

    t0 = time.time()
    grades, summary = run_arm(args.arm, tasks, agent_fn=agent_fn,
                              mock=args.mock)
    summary["elapsed_s"] = round(time.time() - t0, 1)
    if manifest:
        summary["manifest"] = manifest  # immutable record of what ran

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    tag = f"{args.arm}_n{args.n}_seed{args.seed}_{args.split}"
    if args.mock:
        tag += "_mock"
    with open(os.path.join(HERE, "results", f"{tag}.json"), "w") as f:
        json.dump({"summary": summary, "grades": grades}, f, indent=1)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
