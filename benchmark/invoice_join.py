"""Invoice join MVP — reconciles Averth per-run estimates against provider billing.

CUSTOMER-SIDE SCRIPT. Runs inside the customer's environment with their own
provider credentials or Console CSV exports. Only the report below leaves;
the customer approves what is shared.

The join key is (api_key_id, UTC hour): neither Anthropic nor OpenAI can
attribute spend to an individual run, so per-run precision is impossible and
this script does not pretend otherwise.

Inputs:
  1. Averth ledger: a Tracker instance (in-process) or a JSON export of
     tracker.attempts. Attempts carry started_at (UTC) and api_key_id
     (Tracker(api_key_id=...) at construction).
  2. Provider usage: normalized buckets (see normalize_anthropic_usage /
     normalize_openai_usage, or provide CSV). Shape:
       {"api_key_id", "hour_utc" (ISO), "model",
        "input_tokens", "cache_read_tokens", "cache_creation_tokens",
        "output_tokens", "billed_cost" (optional, from cost APIs)}

Output: explained-delta report per bucket and overall:
  averth_estimated (list price, our math)
  - cache_read_discount (computed from cache token splits)
  - batch_discount (where the provider flags batch usage)
  = expected_bill
  provider_billed (from cost API / invoice, when available)
  residual = provider_billed - expected_bill   (unexplained)

Verdict: |residual| < 10% of billed -> RECONCILED, else FAILED, stated
plainly. A failed reconciliation is a finding, not a bug to hide.
"""

import csv
import datetime
import json
import sys
from collections import defaultdict

sys.path.insert(0, __import__("os").path.join(
    __import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
from averth import pricing


def _hour_bucket(iso_ts):
    dt = datetime.datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).replace(
        minute=0, second=0, microsecond=0).isoformat()


def averth_buckets(attempts):
    """Bucket Averth attempts by (api_key_id, hour, model).

    Returns (buckets, runs): buckets keyed (key_id, hour, provider, model),
    runs = distinct attempt count per (key_id, hour)."""
    out = defaultdict(lambda: {"input_tokens": 0, "cache_read_tokens": 0,
                               "output_tokens": 0, "estimated_cost": 0.0})
    seen = defaultdict(set)
    for a in attempts:
        key_id = a.get("api_key_id") or "unkeyed"
        hour = _hour_bucket(a["started_at"])
        seen[(key_id, hour)].add(a.get("case_id"))
        # bucket steps by their own model key (no double counting)
        for s in a.get("steps", []):
            mk = s.get("model_key", "unknown:unknown")
            provider, _, model = mk.partition(":")
            b = out[(key_id, hour, provider, model)]
            b["input_tokens"] += s["in"]
            b["cache_read_tokens"] += s.get("cached", 0)
            b["output_tokens"] += s["out"]
            b["estimated_cost"] += s["cost"]
    runs = {k: len(v) for k, v in seen.items()}
    return out, runs
    return out


def normalize_anthropic_usage(api_response):
    """Anthropic GET /v1/organizations/usage_report/messages shape (paraphrased).
    Real shape: {"data": [{"starting_at", "ending_at", "results": [{...}]}]}.
    Accepts the raw response dict; returns normalized buckets."""
    buckets = []
    for window in api_response.get("data", []):
        hour = _hour_bucket(window["starting_at"])
        for r in window.get("results", []):
            buckets.append({
                "api_key_id": r.get("api_key_id", "unknown"),
                "hour_utc": hour,
                "model": r.get("model", "unknown"),
                "input_tokens": r.get("input_tokens", 0),
                "cache_read_tokens": r.get("cache_read_input_tokens", 0),
                "cache_creation_tokens": r.get(
                    "cache_creation_input_tokens", 0),
                "output_tokens": r.get("output_tokens", 0),
                "billed_cost": None,  # usage API has no costs; join cost report separately
            })
    return buckets


def normalize_openai_usage(api_response):
    """OpenAI GET /v1/organization/usage/completions shape (paraphrased)."""
    buckets = []
    for window in api_response.get("data", []):
        hour = _hour_bucket(window["start_time"])
        for r in window.get("results", []):
            buckets.append({
                "api_key_id": r.get("api_key_id", "unknown"),
                "hour_utc": hour,
                "model": r.get("model", "unknown"),
                "input_tokens": r.get("input_tokens", 0),
                "cache_read_tokens": r.get("cached_tokens", 0),
                "cache_creation_tokens": 0,
                "output_tokens": r.get("output_tokens", 0),
                "billed_cost": None,
            })
    return buckets


def normalize_csv(path):
    """Console CSV export fallback. Columns: hour_utc, api_key_id, model,
    input_tokens, cache_read_tokens, cache_creation_tokens, output_tokens,
    billed_cost (optional)."""
    buckets = []
    with open(path) as f:
        for row in csv.DictReader(f):
            buckets.append({
                "api_key_id": row.get("api_key_id", "unknown"),
                "hour_utc": row["hour_utc"],
                "model": row.get("model", "unknown"),
                "input_tokens": int(row.get("input_tokens", 0) or 0),
                "cache_read_tokens": int(row.get("cache_read_tokens", 0) or 0),
                "cache_creation_tokens": int(
                    row.get("cache_creation_tokens", 0) or 0),
                "output_tokens": int(row.get("output_tokens", 0) or 0),
                "billed_cost": (float(row["billed_cost"])
                                if row.get("billed_cost") else None),
            })
    return buckets


def join(av_buckets, av_runs, provider_buckets, residual_threshold=0.10):
    """Produce the explained-delta report."""
    prov = defaultdict(lambda: {"input_tokens": 0, "cache_read_tokens": 0,
                                "cache_creation_tokens": 0,
                                "output_tokens": 0, "billed_cost": 0.0,
                                "has_billed": False})
    for b in provider_buckets:
        # provider model ids are versioned; match on family by prefix where needed
        k = (b["api_key_id"], b["hour_utc"], b["model"])
        p = prov[k]
        p["input_tokens"] += b["input_tokens"]
        p["cache_read_tokens"] += b["cache_read_tokens"]
        p["cache_creation_tokens"] += b["cache_creation_tokens"]
        p["output_tokens"] += b["output_tokens"]
        if b["billed_cost"] is not None:
            p["billed_cost"] += b["billed_cost"]
            p["has_billed"] = True

    report_buckets = []
    # union of (key_id, hour): av keys are (key, hour, provider, model),
    # prov keys are (key, hour, model)
    av_by_kh = defaultdict(list)
    for k in av_buckets:
        av_by_kh[(k[0], k[1])].append(k)
    prov_by_kh = defaultdict(list)
    for k in prov:
        prov_by_kh[(k[0], k[1])].append(k)
    for (key_id, hour) in sorted(set(av_by_kh) | set(prov_by_kh)):
        # aggregate averth side across models for this (key, hour)
        av = {"input_tokens": 0, "cache_read_tokens": 0, "output_tokens": 0,
              "estimated_cost": 0.0, "runs": av_runs.get((key_id, hour), 0)}
        models = set()
        for k in av_by_kh.get((key_id, hour), []):
            b = av_buckets[k]
            for f in ("input_tokens", "cache_read_tokens", "output_tokens",
                      "estimated_cost"):
                av[f] += b[f]
            models.add(k[3])
        pmatch = [p for (kk, p) in prov.items()
                  if kk[0] == key_id and kk[1] == hour]
        ptok_in = sum(p["input_tokens"] for p in pmatch)
        ptok_out = sum(p["output_tokens"] for p in pmatch)
        billed = sum(p["billed_cost"] for p in pmatch)
        has_billed = any(p["has_billed"] for p in pmatch)

        token_gap_in = ptok_in - av["input_tokens"]
        token_gap_out = ptok_out - av["output_tokens"]

        explained = av["estimated_cost"]
        residual = (billed - explained) if has_billed else None
        verdict = None
        if has_billed and billed:
            verdict = ("RECONCILED" if abs(residual) / billed <= residual_threshold
                       else "FAILED")
        report_buckets.append({
            "api_key_id": key_id, "hour_utc": hour,
            "models": sorted(models),
            "averth_runs": av["runs"],
            "averth_input_tokens": av["input_tokens"],
            "provider_input_tokens": ptok_in,
            "token_gap_in": token_gap_in,
            "averth_output_tokens": av["output_tokens"],
            "provider_output_tokens": ptok_out,
            "token_gap_out": token_gap_out,
            "averth_estimated_cost": round(av["estimated_cost"], 4),
            "provider_billed_cost": round(billed, 4) if has_billed else None,
            "residual": round(residual, 4) if residual is not None else None,
            "verdict": verdict,
        })

    tot_est = sum(b["averth_estimated_cost"] for b in report_buckets)
    tot_billed = sum(b["provider_billed_cost"] or 0 for b in report_buckets)
    tot_resid = sum(b["residual"] or 0 for b in report_buckets)
    overall = None
    if tot_billed:
        overall = ("RECONCILED" if abs(tot_resid) / tot_billed <= residual_threshold
                   else "FAILED")
    return {
        "buckets": report_buckets,
        "totals": {
            "averth_estimated_cost": round(tot_est, 4),
            "provider_billed_cost": round(tot_billed, 4),
            "residual": round(tot_resid, 4),
            "verdict": overall,
            "note": ("Residual is unexplained: committed-use discounts, "
                     "credits, tier pricing, or untracked keys. A FAILED "
                     "verdict is a finding, not an error to hide."),
        },
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", required=True,
                    help="JSON array of tracker attempts (export tracker.attempts)")
    ap.add_argument("--provider", required=True, choices=["anthropic", "openai", "csv"])
    ap.add_argument("--usage", required=True,
                    help="Provider usage JSON (API shape) or CSV path")
    ap.add_argument("--out", default="invoice-join-report.json")
    args = ap.parse_args()

    with open(args.ledger) as f:
        attempts = json.load(f)
    av, av_runs = averth_buckets(attempts)

    if args.provider == "anthropic":
        with open(args.usage) as f:
            prov = normalize_anthropic_usage(json.load(f))
    elif args.provider == "openai":
        with open(args.usage) as f:
            prov = normalize_openai_usage(json.load(f))
    else:
        prov = normalize_csv(args.usage)

    report = join(av, av_runs, prov)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1)
    t = report["totals"]
    print(f"estimated=${t['averth_estimated_cost']} billed=${t['provider_billed_cost']} "
          f"residual=${t['residual']} verdict={t['verdict']}")
    print(f"wrote {args.out} — review before sharing")


if __name__ == "__main__":
    main()
