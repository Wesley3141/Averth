"""Hostile-review measurement harness for averth/stress.py (pass 2)."""
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter

sys.path.insert(0, os.path.expanduser("~/workspace/averth"))
from averth import stress
from averth.importers import jsonl as J
from averth.importers import common


def shape_counts(seed=42, attempts=2000):
    counts = Counter()
    for name in ("quick_resolve", "standard", "retry_storm", "escalation",
                 "failed_clean", "runaway", "_router_triage"):
        orig = getattr(stress._Gen, name)
        def wrap(self, _orig=orig, _name=name):
            counts[_name] += 1
            return _orig(self)
        setattr(stress._Gen, name, wrap)
    # reopened-success path calls _router_triage directly, count it too
    t, _ = stress.generate(seed=seed, attempts=attempts)
    return counts, t


def main():
    seed, attempts = 42, 2000
    counts, t = shape_counts(seed, attempts)
    print("== shape distribution (seed=42, attempts=2000) ==")
    for k in ("quick_resolve", "standard", "retry_storm", "escalation",
              "failed_clean", "runaway", "_router_triage"):
        frac = counts[k] / attempts
        print(f"  {k:15s} {counts[k]:5d}  ({frac*100:.2f}%)")

    p = t.pnl()
    print("\n== pnl headline figures ==")
    print("  attempts:", p["attempts"], "successes:", p["successes"],
          "retries:", p["retries"], "escalations:", p["escalations"])
    print("  cost_total: %.4f  cost_model: %.4f  cost_tools: %.4f  cost_human: %.4f"
          % (p["cost_total"], p["cost_model"], p["cost_tools"], p["cost_human"]))
    print("  yield_ratio: %.4f  avg_context_growth: %.4f  context_tax: %.4f"
          % (p["yield_ratio"], p["avg_context_growth"], p["context_tax"]))
    print("  top5pct_share: %.4f" % p["tail"]["top5pct_share"])
    print("  p50: %.4f  p95: %.4f  max: %.4f"
          % (p["tail"]["p50"], p["tail"]["p95"], p["tail"]["max"]))
    print("  cost_failed: %.4f  per_model keys: %d  cached_tokens: %d  cache_savings: %.4f"
          % (p["cost_failed"], len(p["per_model"]), p["cached_tokens"], p["cache_savings"]))
    ca = p["costliest_attempts"][0]
    print("  costliest attempt: success=%s cost=%.4f" % (ca["success"], ca["total_cost"]))
    print("  tail[success flags of top 10 costliest]:",
          [c["success"] for c in p["costliest_attempts"]])

    # runaway share of budget: attempts with >= 20 model calls (runaway marker)
    step_counts = [len(a["steps"]) for a in t.attempts]
    heavy = [a for a in t.attempts if len(a["steps"]) >= 20]
    heavy_cost = sum(a["total_cost"] for a in heavy)
    print("\n== heavy-tail measurement (steps>=20 as runaway proxy) ==")
    print("  heavy attempts: %d (%.2f%%), budget share: %.4f"
          % (len(heavy), 100 * len(heavy) / len(t.attempts),
             heavy_cost / p["cost_total"]))

    # determinism: byte-identical JSONL
    d = tempfile.mkdtemp()
    p1 = os.path.join(d, "a.jsonl")
    p2 = os.path.join(d, "b.jsonl")
    stress.write_jsonl(p1, seed=7, attempts=500)
    stress.write_jsonl(p2, seed=7, attempts=500)
    h1 = hashlib.sha256(open(p1, "rb").read()).hexdigest()
    h2 = hashlib.sha256(open(p2, "rb").read()).hexdigest()
    print("\n== determinism ==")
    print("  same-seed jsonl byte-identical:", h1 == h2)
    p3 = os.path.join(d, "c.jsonl")
    stress.write_jsonl(p3, seed=8, attempts=500)
    h3 = hashlib.sha256(open(p3, "rb").read()).hexdigest()
    print("  different-seed jsonl differs:", h1 != h3)

    # round-trip: FULL pnl key comparison to the cent
    t_direct, _ = stress.generate(seed=7, attempts=500)
    path = os.path.join(d, "rt.jsonl")
    stress.write_jsonl(path, seed=7, attempts=500)
    ledger = J.load_jsonl(path)
    t_rt = common.tracker_from_ledger(ledger)
    p1d, p2d = t_direct.pnl(), t_rt.pnl()
    mismatches = []
    for k in p1d:
        v1, v2 = p1d[k], p2d.get(k, "<missing>")
        if isinstance(v1, float):
            if not (isinstance(v2, float) and abs(v1 - v2) < 1e-9):
                mismatches.append((k, v1, v2))
        elif isinstance(v1, (int, bool)):
            if v1 != v2:
                mismatches.append((k, v1, v2))
        elif isinstance(v1, str):
            if v1 != v2:
                mismatches.append((k, v1, v2))
        elif isinstance(v1, (list, tuple)):
            if list(v1) != list(v2):
                mismatches.append((k, "list-len %d" % len(v1),
                                   "list-len %d" % (len(v2) if isinstance(v2, (list, tuple)) else -1)))
        elif isinstance(v1, dict):
            if v1 != v2:
                mismatches.append((k, "dict differs", "dict differs"))
    print("\n== round-trip full-pnl comparison (500 attempts, to 1e-9) ==")
    print("  mismatches:", len(mismatches))
    for k, v1, v2 in mismatches[:20]:
        print("   ", k, "direct=", v1, "rt=", v2)

    # edge cases
    print("\n== edge cases ==")
    for n in (0, 1):
        try:
            te, _ = stress.generate(seed=1, attempts=n)
            pe = te.pnl()
            print("  attempts=%d: pnl ok, attempts=%r cost_total=%r"
                  % (n, pe["attempts"], pe.get("cost_total")))
        except Exception as e:
            print("  attempts=%d: RAISED %r" % (n, e))
    try:
        te, _ = stress.generate(seed=1, attempts=0, record_events=True)
        pth = os.path.join(d, "empty.jsonl")
        stress.write_jsonl(pth, seed=1, attempts=0)
        print("  attempts=0: jsonl bytes=%d" % os.path.getsize(pth))
    except Exception as e:
        print("  attempts=0 jsonl: RAISED %r" % e)


if __name__ == "__main__":
    main()
