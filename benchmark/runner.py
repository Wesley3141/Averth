"""Benchmark runner: executes an arm over N tasks, grades, reports cost/accuracy.

Usage:
  python runner.py --arm A --n 30 [--mock] [--seed 7]

--mock: uses a deterministic mock model (plumbing validation ONLY;
        mock results are never benchmark results).
Real runs require ANTHROPIC_API_KEY via the custom.anthropic connector.

Output: results/<arm>_n<N>_seed<S>[_mock].json with per-task grades and
tracker PnL summary.
"""
import argparse, json, os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import triage_agent
from triage_agent import TRACKER, build_corpus
import grader

MOCK = False

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
            # deterministic mock: guess from keywords (NOT a real model)
            low = user.lower()
            guess = "FEATURE_REQUEST" if any(
                w in low for w in ["feature", "add ", "support ", "request"]) \
                else "BUG"
            if "CLASS:" in system:
                text = f"CLASS: {guess}\nSUMMARY: mock summary line"
            else:
                text = guess
            in_tok = len(system + user) // 4
            out_tok = len(text) // 4
            return MockMsg(text, in_tok, out_tok)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--split", default="dev",
                    choices=["dev", "heldout"])
    args = ap.parse_args()

    if args.mock:
        triage_agent.client = MockClient()
        print("MOCK MODE - plumbing validation only, NOT benchmark results")

    random.seed(args.seed)
    with open("tasks.json") as f:
        data = json.load(f)
    pool = data[args.split][:]
    random.shuffle(pool)
    tasks = pool[:args.n]
    build_corpus(data["dev"])  # dev-only: heldout labels must not leak via retrieval

    grades = []
    costs = []
    t0 = time.time()
    for i, t in enumerate(tasks):
        try:
            pred = triage_agent.triage(t)
            g = grader.grade(pred, t)
        except Exception as e:
            try:
                TRACKER.end_attempt(success=False)
            except Exception:
                pass
            g = {"task_id": t["id"], "predicted": "ERROR",
                 "actual": t["class"], "correct": False,
                 "error": str(e)[:200]}
        grades.append(g)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(tasks)} done", flush=True)

    summary = grader.summarize(grades)
    pnl = TRACKER.pnl()
    # cost per accepted task from tracker ledger
    total_cost = pnl.get("cost_total", 0)
    accepted = summary["correct"]
    summary["cost_per_accepted"] = (total_cost / accepted) if accepted else None
    summary["total_cost"] = total_cost
    summary["elapsed_s"] = round(time.time() - t0, 1)
    summary["mock"] = args.mock

    os.makedirs("results", exist_ok=True)
    tag = f"{args.arm}_n{args.n}_seed{args.seed}_{args.split}"
    if args.mock:
        tag += "_mock"
    with open(f"results/{tag}.json", "w") as f:
        json.dump({"summary": summary, "grades": grades}, f, indent=1)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
