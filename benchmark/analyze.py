"""Benchmark analysis: robust stats per the v3 spec.

- Primary contrast: C vs B on cost per accepted task (A = sanity anchor).
- Ratio-estimator CIs via bootstrap (percentile).
- Non-inferiority on acceptance rate with margin delta.
- Robust location: trimmed mean + median; p50/p95/max per arm.
- Kill criteria check: >=20% reduction, p<0.05 (bootstrap), payback <6mo.

Validates itself on synthetic data with planted effects (--selftest).
"""
import argparse, json, math, random, sys

def trimmed_mean(xs, p=0.1):
    xs = sorted(xs)
    k = int(len(xs) * p)
    core = xs[k:len(xs)-k] if len(xs) - 2*k > 0 else xs
    return sum(core) / len(core)

def percentile(xs, q):
    xs = sorted(xs)
    i = (len(xs) - 1) * q / 100
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)

def bootstrap_ratio_ci(costs_c, acc_c, costs_b, acc_b, n_boot=2000, seed=0):
    """CI for (cost_per_accepted_C - cost_per_accepted_B) / cost_per_accepted_B."""
    rng = random.Random(seed)
    base_b = sum(costs_b) / acc_b if acc_b else float("nan")
    diffs = []
    for _ in range(n_boot):
        sc = [rng.choice(costs_c) for _ in costs_c]
        sb = [rng.choice(costs_b) for _ in costs_b]
        # resample acceptance counts binomially
        ac = sum(1 for _ in costs_c if rng.random() < acc_c / len(costs_c))
        ab = sum(1 for _ in costs_b if rng.random() < acc_b / len(costs_b))
        if ac == 0 or ab == 0:
            continue
        rc, rb = sum(sc) / ac, sum(sb) / ab
        diffs.append((rc - rb) / rb if rb else float("nan"))
    diffs = [d for d in diffs if d == d]
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs))]
    mid = sum(diffs) / len(diffs)
    # one-sided p-value for H0: reduction <= 0  (i.e., diff >= 0)
    p = sum(1 for d in diffs if d >= 0) / len(diffs)
    return {"reduction_mean": -mid, "reduction_ci95": (-hi, -lo),
            "p_value": p, "base_b": base_b}

def arm_summary(costs, accepted):
    n = len(costs)
    return {
        "n": n, "accepted": accepted,
        "accept_rate": accepted / n if n else 0,
        "cost_per_accepted": sum(costs) / accepted if accepted else None,
        "mean": sum(costs) / n if n else 0,
        "trimmed_mean": trimmed_mean(costs),
        "median": percentile(costs, 50),
        "p95": percentile(costs, 95),
        "max": max(costs) if costs else 0,
    }

def evaluate(arms, noninf_delta=0.05, volume_per_month=10000,
             experiment_cost=0):
    """arms: dict arm -> (costs list, accepted count). Returns verdict dict."""
    out = {a: arm_summary(c, acc) for a, (c, acc) in arms.items()}
    boot = bootstrap_ratio_ci(*arms["C"], *arms["B"])
    out["contrast_CvB"] = boot
    # non-inferiority: C accept rate not worse than B by more than delta
    ra_c = out["C"]["accept_rate"]; ra_b = out["B"]["accept_rate"]
    out["noninferior_quality"] = (ra_c >= ra_b - noninf_delta)
    red = boot["reduction_mean"]
    lo_red = boot["reduction_ci95"][0]
    kill = (red >= 0.20 and boot["p_value"] < 0.05
            and out["noninferior_quality"])
    # payback: experiment cost vs monthly savings at volume
    # (reduction_mean is positive when C wins, so no extra negation)
    monthly_save = red * out["C"]["cost_per_accepted"] * volume_per_month \
        if out["C"]["cost_per_accepted"] and red > 0 else 0
    payback_mo = experiment_cost / monthly_save if monthly_save > 0 else float("inf")
    out["payback_months"] = payback_mo
    out["kill_criteria_met"] = bool(kill and payback_mo < 6)
    out["ci_lower_above_10pct"] = lo_red > 0.10
    return out

def selftest():
    """Planted effects: does the instrument detect what it should?"""
    rng = random.Random(11)
    # heavy-tailed costs like the five-cost-layers finding
    def gen(n, mu, acc):
        costs = [rng.lognormvariate(math.log(mu), 1.2) for _ in range(n)]
        return costs, int(n * acc)
    print("== planted 30% reduction, C vs B ==")
    arms = {"A": gen(120, 0.010, 0.85), "B": gen(120, 0.008, 0.87),
            "C": gen(120, 0.0056, 0.87)}
    r = evaluate(arms, experiment_cost=40)
    print(json.dumps({k: r[k] for k in
          ["contrast_CvB", "noninferior_quality", "kill_criteria_met"]},
          indent=2, default=str))
    assert r["kill_criteria_met"], "should detect planted 30% win"
    print("== no effect (C == B) ==")
    arms2 = {"A": gen(120, 0.010, 0.85), "B": gen(120, 0.008, 0.87),
             "C": gen(120, 0.008, 0.87)}
    r2 = evaluate(arms2)
    print("kill_criteria_met:", r2["kill_criteria_met"],
          "p:", round(r2["contrast_CvB"]["p_value"], 3))
    assert not r2["kill_criteria_met"], "should NOT fire with no effect"
    print("SELFTEST PASS: instrument detects planted wins, ignores noise")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        print("pass --selftest, or import evaluate()")
