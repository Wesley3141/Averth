"""Measure runaway budget share across seeds for stress.generate."""
import os, sys
sys.path.insert(0, os.path.expanduser("~/workspace/averth"))
from averth import stress

for seed, attempts in [(42, 2000), (7, 2000), (123, 2000), (7, 5000), (99, 2000)]:
    runaway_cases = set()
    orig = stress._Gen.runaway
    def wrap(self, _orig=orig, _rc=runaway_cases):
        _rc.add(self.t._cur["case_id"])
        return _orig(self)
    stress._Gen.runaway = wrap
    t, _ = stress.generate(seed=seed, attempts=attempts)
    stress._Gen.runaway = orig
    p = t.pnl()
    rw = [a for a in t.attempts if a["case_id"] in runaway_cases]
    share = sum(a["total_cost"] for a in rw) / p["cost_total"]
    rw_frac = len(rw) / attempts
    # exact runaway count via thresholds vs the draw is stochastic; report both
    print("seed=%d attempts=%d: runaways=%d (%.2f%%) budget_share=%.4f top5_share=%.4f"
          % (seed, attempts, len(rw), 100 * rw_frac, share, p["tail"]["top5pct_share"]))
