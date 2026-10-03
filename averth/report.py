"""Render a P&L report from tracker.pnl(), organized by the five cost layers.

The report leads with the behavior-changing insight: the top finding from
averth.insights, ranked by dollars, with the concrete action it implies.
"""

import html as _html

from .insights import findings


def report_text(p, token_dashboard_per_success=None):
    ps = p["per_success"]
    t = p["tail"]
    L = []
    L.append("Averth: %s" % p["agent"])
    # C2: every report stamps which price table produced its dollars, plus
    # a loud warning when the table is stale. No silent price-era confusion.
    vint = p.get("price_vintage")
    if vint:
        L.append("Price table: v%s (verified %s, %d days old)"
                 % (vint["version"], vint["updated"], vint["age_days"]))
        if vint["stale"]:
            L.append("WARNING: pricing table is stale (>%d days) — vendor "
                     "prices may have changed; verify before trusting "
                     "dollar figures" % vint["stale_after_days"])
    else:
        L.append("Price table: vintage unknown (legacy ledger)")
    L.append("")
    top = findings(p)[:1]
    if top:
        f = top[0]
        L.append("TOP FINDING [%s]: %s" % (f["severity"].upper(), f["title"]))
        detail = f["detail"]
        # C3: the TOP FINDING is the first thing a VP Finance reads. When it
        # is the human-dominance finding AND the labor rate is the default
        # assumption, the headline number carries the caveat on the line
        # itself — a skimming reader must never take an assumption-driven
        # dollar figure as measured data.
        if (p.get("human_rate_assumed", True)
                and f.get("id") == "human_dominance"):
            detail += (" [ASSUMPTION: the labor rate driving this number is "
                       "the default, not measured — pass human_cost_per_min "
                       "with your real rate.]")
        L.append("  %s" % detail)
        L.append("  -> %s" % f["action"])
        L.append("")
    L.append("Attempts:              %s" % "{:,}".format(p["attempts"]))
    L.append("Autonomous completions:%s (%s)" % (
        "{:,}".format(p["successes"]), "%.1f%%" % (p["success_rate"] * 100)))
    L.append("Reopened:              %s accepted outcomes reopened"
             % "{:,}".format(p.get("reopened_successful", p["reopened"])))
    L.append("Human escalations:     %s" % "{:,}".format(p["escalations"]))
    L.append("Retries:               %s" % "{:,}".format(p["retries"]))
    L.append("")
    L.append("Cost per successful outcome:")
    L.append("  Model/API (terminal): $%.2f" % ps["model"])
    L.append("  Retry path:           $%.2f" % ps["retry_path"])
    L.append("  Tool calls:           $%.2f" % ps["tools"])
    # C3: the labor rate is a per-deployment parameter. When the default
    # assumption is in effect the report says so loudly — a VP Finance
    # reader must never mistake it for a measured number.
    if p.get("human_rate_assumed", True):
        L.append("  Human review:         $%.2f  (at $%.2f/hr loaded — "
                 "ASSUMPTION, not measured; pass human_cost_per_min=... "
                 "with your real rate)" % (ps["human"],
                                            p.get("human_cost_per_min", 0) * 60))
    else:
        L.append("  Human review:         $%.2f  (at $%.2f/hr loaded, "
                 "caller-supplied)" % (ps["human"],
                                       p.get("human_cost_per_min", 0) * 60))
    L.append("  Fully loaded:         $%.2f" % ps["fully_loaded"])
    if token_dashboard_per_success is not None:
        mult = (ps["fully_loaded"] / token_dashboard_per_success
                if token_dashboard_per_success else 0)
        L.append("  Token dashboard:      $%.2f  (real cost is %.1fx)"
                 % (token_dashboard_per_success, mult))
    L.append("")
    L.append("The five layers:")
    L.append("  1. Context compounding: %s input growth first-to-last step; "
             "context tax $%s (%.0f%% of model spend)"
             % ("%.1fx" % p["avg_context_growth"],
                "{:,.2f}".format(p["context_tax"]),
                p["context_tax_share_of_model"] * 100))
    L.append("  2. External tool spend: $%s total, $%.2f per success "
             "(invisible on provider invoices)"
             % ("{:,.2f}".format(p["cost_tools"]), ps["tools"]))
    L.append("  3. Yield ratio: %.0f%% of tokens on the terminal path "
             "(%.0f%% burned on retries and failed runs)"
             % (p["yield_ratio"] * 100, (1 - p["yield_ratio"]) * 100))
    L.append("  4. Heavy tail: p50 $%.2f / p95 $%.2f / max $%.2f per attempt; "
             "%s consumed %.0f%% of budget"
             % (t["p50"], t["p95"], t["max"], t["tail_label"],
                t["top5pct_share"] * 100))
    L.append("  5. Model mix:")
    tot_model = p["cost_model"] or 1
    for k, v in sorted(p["per_model"].items(), key=lambda kv: -kv[1]):
        L.append("       %s: $%s (%.0f%% of model spend)"
                 % (k, "{:,.2f}".format(v), v / tot_model * 100))
    if p["cached_tokens"] and p["cache_savings"] > 0:
        # H3: name the discount rate — it is vendor-specific (10% is
        # Anthropic's published rate), not a universal constant.
        L.append("     Prompt cache: %s input tokens cached, saving $%s "
                 "(priced at %.0f%% of input rate; override per vendor via "
                 "cache_read_discount=...)"
                 % ("{:,}".format(p["cached_tokens"]),
                    "{:,.2f}".format(p["cache_savings"]),
                    p.get("cache_read_discount", 0.10) * 100))
    # Waste lenses, not additive partitions: a failed attempt's retry-path
    # spend appears in both the failed-runs and retry-path lines by design.
    L.append("")
    L.append("Waste accounting (lenses, not additive):")
    L.append("  Failed runs:   $%s (%.0f%% of spend, zero outcomes)"
             % ("{:,.2f}".format(p["cost_failed"]),
                p["failed_spend_share"] * 100))
    L.append("  Retry path:    $%s model+retry spend on discarded paths "
             "(overlaps failed runs)"
             % "{:,.2f}".format(p["cost_retry_path"]))
    if p["reopened"]:
        L.append("  Reopened:      $%s (%.0f%% of spend)"
                 % ("{:,.2f}".format(p["cost_reopened"]),
                    p["reopened_spend_share"] * 100))
    if p["top_retry_reasons"]:
        L.append("  Top retry reasons:")
        for reason, count in p["top_retry_reasons"]:
            L.append("    %dx  %s" % (count, reason))
    if p["unpriced_spend"] > 0:
        L.append("")
        L.append("  WARNING: $%s of model spend is ESTIMATED (no vendor "
                 "price for: %s)"
                 % ("{:,.2f}".format(p["unpriced_spend"]),
                    ", ".join(p["unpriced_models"])))
    # H2: tool spend from built-in per-call estimates is flagged, never
    # presented as measured. Pass explicit costs to log_tool_call to clear.
    if p.get("tools_default_priced_spend", 0.0) > 0:
        L.append("")
        L.append("  WARNING: $%s of tool spend uses built-in per-call "
                 "ESTIMATES (for: %s) — measure your tool costs and pass "
                 "them explicitly"
                 % ("{:,.2f}".format(p["tools_default_priced_spend"]),
                    ", ".join(p.get("tools_default_priced_names", []))))
    # missing usage data is not free inference: warn so the $0.00
    # per-model lines above are never read as genuinely free.
    if p.get("missing_usage_models"):
        models = p["missing_usage_models"]
        L.append("")
        L.append("  WARNING: usage data missing for %d model%s (%s) — "
                 "their $0.00 is missing data, not free inference"
                 % (len(models), "s" if len(models) != 1 else "",
                    ", ".join(models)))
    L.append("")
    if p["business_value"] > 0:
        L.append("Business value:        $%s" % "{:,.2f}".format(p["business_value"]))
        L.append("Total cost:            $%s" % "{:,.2f}".format(p["cost_total"]))
        L.append("Net value:             $%s" % "{:,.2f}".format(p["net_value"]))
    else:
        # V1: business value in dollars is optional. Cost per accepted outcome
        # is objectively measurable; value often is not. Report the cost side
        # fully and leave value for deployments with a clean baseline.
        L.append("Total cost:            $%s" % "{:,.2f}".format(p["cost_total"]))
        L.append("Business value:        not baselined (optional in V1)")
    if p.get("budget_per_success") is not None:
        L.append("Budget: $%.2f/success, breaches: %d"
                 % (p["budget_per_success"], p["budget_breaches"]))
    return "\n".join(L)


def _bar(label, value, total, color):
    width = (value / total * 100) if total else 0.0
    return (
        '<div class="brow"><span class="blabel">%s</span>'
        '<div class="btrack"><div class="bfill" style="width:%.1f%%;background:%s;"></div></div>'
        '<span class="bval">$%s</span></div>'
        % (_html.escape(label), width, color, "{:,.2f}".format(value))
    )


def _histogram_svg(costs, p50, p95):
    """Inline SVG histogram of per-attempt costs, 10 buckets, p50/p95 markers."""
    w, h, pad_l, pad_b = 640, 220, 56, 34
    n = len(costs)
    nb = 10
    lo, hi = (min(costs), max(costs)) if costs else (0.0, 1.0)
    if hi <= lo:
        hi = lo + 1.0
    buckets = [0] * nb
    for c in costs:
        b = min(nb - 1, int((c - lo) / (hi - lo) * nb))
        buckets[b] += 1
    peak = max(buckets) or 1
    iw = (w - pad_l - 20) / nb
    ih = h - pad_b - 30

    def x_of(v):
        return pad_l + (v - lo) / (hi - lo) * (w - pad_l - 20)

    parts = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Histogram of per-attempt costs">'
             % (w, h)]
    for i, b in enumerate(buckets):
        bh = b / peak * ih
        bx = pad_l + i * iw + 2
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" '
            'height="%.1f" fill="#4a7fd4"><title>%d attempts in bucket</title></rect>'
            % (bx, h - pad_b - bh, iw - 4, bh, b))
    for v, lab, col in ((p50, "p50", "#1c5c2a"), (p95, "p95", "#b3261e")):
        x = x_of(v)
        parts.append(
            '<line x1="%.1f" y1="30" x2="%.1f" y2="%d" stroke="%s" '
            'stroke-width="2" stroke-dasharray="5,3"/>'
            '<text x="%.1f" y="20" fill="%s" font-size="12" text-anchor="middle">'
            '%s $%.2f</text>' % (x, x, h - pad_b, col, x, col, lab, v))
    parts.append(
        '<text x="%d" y="%d" font-size="11" fill="#555">$%.2f</text>'
        '<text x="%d" y="%d" font-size="11" fill="#555" text-anchor="end">$%.2f</text>'
        '<text x="%d" y="%.1f" font-size="11" fill="#555">%d attempts max bucket</text>'
        % (pad_l, h - 8, lo, w - 20, h - 8, hi, pad_l, h - pad_b - ih - 6, peak))
    parts.append('</svg>')
    return "\n".join(parts)


def write_html(path, tracker, policy_sim=None, token_dashboard_per_success=None):
    """Write a single-file shareable P&L report. Returns the path written."""
    p = tracker.pnl()
    ps = p["per_success"]
    t = p["tail"]
    costs = [a["total_cost"] for a in tracker.attempts]

    if token_dashboard_per_success:
        mult = ps["fully_loaded"] / token_dashboard_per_success
        mult_card = ('<div class="card"><div class="k">Token-dashboard multiple</div>'
                     '<div class="v">%.1fx</div>'
                     '<div class="s">real cost vs $%.2f dashboard view</div></div>'
                     % (mult, token_dashboard_per_success))
    else:
        mult_card = ""

    unpriced_banner = ""
    if p["unpriced_spend"] > 0:
        unpriced_banner = (
            '<div class="warn"><b>Estimated spend:</b> $%s of model spend uses '
            'the documented fallback estimate (no vendor price for %s).</div>'
            % ("{:,.2f}".format(p["unpriced_spend"]),
               _html.escape(", ".join(p["unpriced_models"]))))

    # H2: tool spend from built-in estimates is flagged, never hidden.
    tool_est_banner = ""
    if p.get("tools_default_priced_spend", 0.0) > 0:
        tool_est_banner = (
            '<div class="warn"><b>Estimated tool spend:</b> $%s of tool spend '
            'uses built-in per-call estimates (for %s) — measure your tool '
            'costs and pass them explicitly to log_tool_call.</div>'
            % ("{:,.2f}".format(p["tools_default_priced_spend"]),
               _html.escape(", ".join(p.get("tools_default_priced_names", [])))))

    # missing usage data is not free inference: warn loudly so the $0.00
    # per-model rows are never read as genuinely free.
    missing_usage_banner = ""
    missing_models = p.get("missing_usage_models")
    if missing_models:
        missing_usage_banner = (
            '<div class="warn"><b>Missing usage data:</b> usage data is '
            'missing for %d model%s (%s) — their $0.00 is missing data, '
            'not free inference.</div>'
            % (len(missing_models), "s" if len(missing_models) != 1 else "",
               _html.escape(", ".join(missing_models))))

    # C2: stamp the price vintage on every report; stale tables warn loudly.
    vint = p.get("price_vintage")
    if vint:
        vintage_line = ("Price table v%s &middot; verified %s &middot; %d days old"
                        % (_html.escape(str(vint["version"])),
                           _html.escape(vint["updated"]),
                           vint["age_days"]))
        stale_banner = ""
        if vint["stale"]:
            stale_banner = (
                '<div class="warn"><b>Stale pricing:</b> price table v%s is %d '
                'days old (last verified %s). Vendor prices may have changed '
                '— verify before trusting dollar figures.</div>'
                % (_html.escape(str(vint["version"])), vint["age_days"],
                   _html.escape(vint["updated"])))
    else:
        vintage_line = "Price table vintage unknown (legacy ledger)"
        stale_banner = ""

    insight_cards = ""
    top_findings = findings(p)[:3]
    if top_findings:
        cards = []
        for f in top_findings:
            cards.append(
                '<div class="finding %s"><div class="fk">%s FINDING &middot; $%s</div>'
                '<div class="ft">%s</div><div class="fs">%s</div>'
                '<div class="fa">&rarr; %s</div></div>'
                % (f["severity"], f["severity"].upper(),
                   "{:,.2f}".format(f["dollars"]),
                   _html.escape(f["title"]), _html.escape(f["detail"]),
                   _html.escape(f["action"])))
        insight_cards = ('<h2>What to do Monday morning</h2><div class="findings">%s</div>'
                         '<p class="fineprint">Waste figures are overlapping lenses on the same '
                         'spend, not additive partitions — do not sum them.</p>'
                         % "".join(cards))

    ps_total = sum(ps[k] for k in ("model", "retry_path", "tools", "human"))
    breakdown = "".join([
        _bar("Model / API (terminal)", ps["model"], ps_total, "#4a7fd4"),
        _bar("Retry path", ps["retry_path"], ps_total, "#e0a32e"),
        _bar("Tool calls", ps["tools"], ps_total, "#7ab648"),
        _bar("Human review", ps["human"], ps_total, "#c25bb5"),
    ])
    # C3: never let the default labor assumption pass silently in the
    # visual report either.
    if p.get("human_rate_assumed", True):
        human_note = (
            '<p class="s">Human review costed at $%.2f/hr loaded — '
            '<b>default assumption</b>, not a measured number. Pass '
            'human_cost_per_min=... with your real loaded rate.</p>'
            % (p.get("human_cost_per_min", 0) * 60))
    else:
        human_note = ""

    tot_model = p["cost_model"] or 1
    model_rows = "".join(
        '<tr><td>%s</td><td class="r">$%s</td>'
        '<td class="r">%.0f%% of model spend</td></tr>'
        % (_html.escape(k), "{:,.2f}".format(v), v / tot_model * 100)
        for k, v in sorted(p["per_model"].items(), key=lambda kv: -kv[1]))

    retry_rows = "".join(
        '<tr><td class="r">%dx</td><td>%s</td></tr>'
        % (c, _html.escape(r)) for r, c in p["top_retry_reasons"])

    costliest_rows = "".join(
        '<tr><td>%s</td><td class="r">$%.2f</td><td>%s</td>'
        '<td class="r">%d</td><td class="r">%.1f min</td></tr>'
        % (_html.escape(str(c["case_id"])), c["total_cost"],
           "success" if c["success"] else "FAILED", c["retries"],
           c["human_min"])
        for c in p["costliest_attempts"])

    policy_section = ""
    if policy_sim is not None:
        pol = policy_sim["policy"]
        policy_section = (
            '<h2>Policy replay (read only)</h2>'
            '<p class="lede">Had this policy existed, <b>%d runs</b> would have '
            'been stopped: <b>%d failed</b> (pure savings <b>$%s</b>) and '
            '<b>%d that went on to succeed</b> (collateral <b>$%s</b> — good '
            'outcomes the policy would have destroyed).</p>'
            '<p class="s">Policy tested: max cost per attempt $%s, yield floor %s. '
            'No enforcement was applied; this is a replay of recorded history.</p>'
            % (policy_sim["would_stop"], policy_sim["would_stop_failed"],
               "{:,.2f}".format(policy_sim["saved_spend"]),
               policy_sim["would_stop_success"],
               "{:,.2f}".format(policy_sim["collateral_spend"]),
               _html.escape(str(pol["max_cost_per_attempt"])),
               _html.escape(str(pol["yield_floor"]))))
        if policy_sim["worst"]:
            policy_section += (
                '<table><tr><th>Run</th><th>Cost</th><th>Outcome</th><th>Reason</th></tr>' +
                "".join(
                    '<tr><td>%s</td><td class="r">$%.2f</td><td>%s</td><td>%s</td></tr>'
                    % (_html.escape(str(w["case_id"])), w["total_cost"],
                       "success" if w["success"] else "FAILED",
                       _html.escape("; ".join(w["reasons"])))
                    for w in policy_sim["worst"]) + '</table>')

    html_doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Averth report: %(agent)s</title>
<style>
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: #1f2933;
  max-width: 860px; margin: 0 auto; padding: 24px; background: #f7f8fa; }
main { background: #fff; border: 1px solid #e2e6ec; border-radius: 10px; padding: 28px; }
h1 { margin: 0 0 4px; font-size: 26px; }
.meta { color: #5b6470; margin: 0 0 20px; }
.warn { background: #fff8e6; border: 1px solid #e8c547; border-radius: 8px;
  padding: 10px 14px; font-size: 13px; margin: 14px 0; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px; margin: 18px 0; }
.card { border: 1px solid #e2e6ec; border-radius: 8px; padding: 12px 14px; background: #fafbfc; }
.card .k { font-size: 12px; color: #5b6470; text-transform: uppercase; letter-spacing: .04em; }
.card .v { font-size: 24px; font-weight: 700; margin: 4px 0; }
.card .s { font-size: 12px; color: #5b6470; }
.findings { display: grid; gap: 10px; margin: 12px 0; }
.finding { border-radius: 8px; padding: 12px 14px; border: 1px solid #e2e6ec; }
.finding.high { border-left: 5px solid #b3261e; background: #fdf3f2; }
.finding.medium { border-left: 5px solid #e0a32e; background: #fdf9f0; }
.finding.info { border-left: 5px solid #4a7fd4; background: #f2f6fd; }
.finding .fk { font-size: 11px; font-weight: 700; letter-spacing: .05em; color: #5b6470; }
.finding .ft { font-size: 15px; font-weight: 700; margin: 4px 0; }
.finding .fs { font-size: 13px; color: #3c4450; }
.finding .fa { font-size: 13px; margin-top: 6px; font-weight: 600; }
h2 { font-size: 18px; margin: 26px 0 10px; border-bottom: 1px solid #eef1f4; padding-bottom: 6px; }
.lede { font-size: 15px; }
.brow { display: flex; align-items: center; gap: 10px; margin: 6px 0; }
.blabel { width: 170px; font-size: 13px; }
.btrack { flex: 1; height: 18px; background: #eef1f4; border-radius: 9px; overflow: hidden; }
.bfill { height: 100%%; }
.bval { width: 90px; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }
table { width: 100%%; border-collapse: collapse; font-size: 13px; margin: 10px 0; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #eef1f4; }
th { color: #5b6470; font-weight: 600; }
.r { text-align: right; font-variant-numeric: tabular-nums; }
svg { width: 100%%; height: auto; background: #fafbfc; border: 1px solid #eef1f4; border-radius: 8px; }
.layers li { margin: 6px 0; font-size: 14px; }
footer { margin-top: 24px; font-size: 12px; color: #8a94a1; text-align: center; }
</style>
</head>
<body>
<main>
<h1>Agent P&L: %(agent)s</h1>
<p class="meta">%(attempts)s attempts &middot; %(successes)s autonomous completions &middot;
%(success_rate)s success rate &middot; %(escalations)s escalations &middot; %(reopened)s reopened<br>
<span class="s">%(vintage_line)s</span></p>
%(unpriced_banner)s
%(tool_est_banner)s
%(missing_usage_banner)s
%(stale_banner)s
<div class="cards">
<div class="card"><div class="k">Fully loaded</div><div class="v">$%(fully_loaded)s</div>
<div class="s">per accepted outcome</div></div>
%(mult_card)s
<div class="card"><div class="k">Yield ratio</div><div class="v">%(yield_ratio)s</div>
<div class="s">terminal-path tokens / total</div></div>
<div class="card"><div class="k">Top 5%% tail share</div><div class="v">%(tail_share)s</div>
<div class="s">of total spend in costliest runs</div></div>
<div class="card"><div class="k">Failed-run waste</div><div class="v">$%(failed_cost)s</div>
<div class="s">%(failed_share)s of spend, zero outcomes</div></div>
</div>
%(insight_cards)s
<h2>Cost per successful outcome</h2>
%(breakdown)s
%(human_note)s
<h2>Per-attempt cost distribution</h2>
%(histogram)s
<p class="s">p50 $%(p50).2f &middot; p95 $%(p95).2f &middot; max $%(max).2f per attempt</p>
<h2>The five layers</h2>
<ul class="layers">
<li><b>Context compounding:</b> %(growth).1fx input growth, first to last step.
Context tax: <b>$%(context_tax)s</b> (%(tax_share).0f%% of model spend) vs a flat-context counterfactual.</li>
<li><b>External tool spend:</b> $%(tools_total)s total, $%(tools_ps).2f per success
(invisible on provider invoices).</li>
<li><b>Yield ratio:</b> %(yield).0f%% of tokens on the terminal path,
%(waste).0f%% burned on retries and failed runs.</li>
<li><b>Heavy tail:</b> p50 $%(p50).2f / p95 $%(p95).2f / max $%(max).2f per attempt;
%(tail_label)s consumed %(tail_share)s of budget.</li>
<li><b>Model mix:</b> $%(model_total)s total model spend (see table).
%(cache_line)s</li>
</ul>
<h2>Top cost drivers (per model)</h2>
<table><tr><th>Model</th><th class="r">Spend</th><th class="r">Share</th></tr>%(model_rows)s</table>
<h2>Costliest attempts</h2>
<table><tr><th>Run</th><th class="r">Cost</th><th>Outcome</th><th class="r">Retries</th><th class="r">Human</th></tr>%(costliest_rows)s</table>
%(retry_section)s
%(policy_section)s
</main>
<footer>Generated locally by averth. No data leaves your environment.</footer>
</body>
</html>
""" % {
        "agent": _html.escape(p["agent"]),
        "attempts": "{:,}".format(p["attempts"]),
        "successes": "{:,}".format(p["successes"]),
        "success_rate": "%.1f%%" % (p["success_rate"] * 100),
        "escalations": "{:,}".format(p["escalations"]),
        "reopened": "{:,}".format(p["reopened"]),
        "unpriced_banner": unpriced_banner,
        "tool_est_banner": tool_est_banner,
        "missing_usage_banner": missing_usage_banner,
        "stale_banner": stale_banner,
        "vintage_line": vintage_line,
        "human_note": human_note,
        "fully_loaded": "{:,.2f}".format(ps["fully_loaded"]),        "mult_card": mult_card,
        "yield_ratio": "%.0f%%" % (p["yield_ratio"] * 100),
        "tail_share": "%.0f%%" % (t["top5pct_share"] * 100),
        "tail_label": "the %s" % t["tail_label"],
        "failed_cost": "{:,.2f}".format(p["cost_failed"]),
        "failed_share": "%.0f%%" % (p["failed_spend_share"] * 100),
        "insight_cards": insight_cards,
        "breakdown": breakdown,
        "histogram": _histogram_svg(costs, t["p50"], t["p95"]),
        "p50": t["p50"], "p95": t["p95"], "max": t["max"],
        "growth": p["avg_context_growth"],
        "context_tax": "{:,.2f}".format(p["context_tax"]),
        "tax_share": p["context_tax_share_of_model"] * 100,
        "tools_total": "{:,.2f}".format(p["cost_tools"]),
        "tools_ps": ps["tools"],
        "yield": p["yield_ratio"] * 100,
        "waste": (1 - p["yield_ratio"]) * 100,
        "model_total": "{:,.2f}".format(p["cost_model"]),
        "cache_line": ("Prompt cache: {:,} input tokens cached, saving "
                       "${:,.2f} (priced at {:.0f}% of input rate — "
                       "vendor-specific; override via "
                       "cache_read_discount).".format(p["cached_tokens"],
                                          p["cache_savings"],
                                          p.get("cache_read_discount", 0.10) * 100)
                       ) if p["cached_tokens"] and p["cache_savings"] > 0 else "",
        "model_rows": model_rows,
        "costliest_rows": costliest_rows,
        "retry_section": (
            '<h2>Retry reasons</h2><table><tr><th class="r">Count</th>'
            '<th>Reason</th></tr>%s</table>' % retry_rows
        ) if retry_rows else "",
        "policy_section": policy_section,
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path
