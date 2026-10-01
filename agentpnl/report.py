"""Render a P&L report from tracker.pnl(), organized by the five cost layers."""

import html as _html


def report_text(p, token_dashboard_per_success=None):
    ps = p["per_success"]
    t = p["tail"]
    L = []
    L.append(f"Agent P&L: {p['agent']}")
    L.append("")
    L.append(f"Attempts:              {p['attempts']:,}")
    L.append(f"Autonomous completions:{p['successes']:,} ({p['success_rate']:.1%})")
    L.append(f"Reopened:              {p['reopened']:,}")
    L.append(f"Human escalations:     {p['escalations']:,}")
    L.append(f"Retries:               {p['retries']:,}")
    L.append("")
    L.append("Cost per successful outcome:")
    L.append(f"  Model/API:        ${ps['model']:.2f}")
    L.append(f"  Tool calls:       ${ps['tools']:.2f}")
    L.append(f"  Retries:          ${ps['retry']:.2f}")
    L.append(f"  Human review:     ${ps['human']:.2f}")
    L.append(f"  Fully loaded:     ${ps['fully_loaded']:.2f}")
    if token_dashboard_per_success is not None:
        mult = ps['fully_loaded'] / token_dashboard_per_success if token_dashboard_per_success else 0
        L.append(f"  Token dashboard:  ${token_dashboard_per_success:.2f}  (real cost is {mult:.1f}x)")
    L.append("")
    L.append("The five layers:")
    L.append(f"  1. Context compounding: {p['avg_context_growth']:.1f}x input growth, "
             "first to last step (state accumulation tax)")
    L.append(f"  2. External tool spend: ${p['cost_tools']:,.2f} total, "
             f"${ps['tools']:.2f} per success (invisible on provider invoices)")
    L.append(f"  3. Yield ratio: {p['yield_ratio']:.0%} of tokens on the terminal path "
             f"({1 - p['yield_ratio']:.0%} burned on retries and dead ends)")
    L.append(f"  4. Heavy tail: p50 ${t['p50']:.2f} / p95 ${t['p95']:.2f} / max ${t['max']:.2f} "
             f"per attempt; top 5% of attempts consumed {t['top5pct_share']:.0%} of budget")
    L.append("  5. Model mix:")
    tot_model = p["cost_model"] or 1
    for k, v in sorted(p["per_model"].items(), key=lambda kv: -kv[1]):
        L.append(f"       {k}: ${v:,.2f} ({v / tot_model:.0%} of model spend)")
    L.append("")
    if p["business_value"] > 0:
        L.append(f"Business value:        ${p['business_value']:,.2f}")
        L.append(f"Total cost:            ${p['cost_total']:,.2f}")
        L.append(f"Net value:             ${p['net_value']:,.2f}")
    else:
        # V1: business value in dollars is optional. Cost per accepted outcome
        # is objectively measurable; value often is not. Report the cost side
        # fully and leave value for deployments with a clean baseline.
        L.append(f"Total cost:            ${p['cost_total']:,.2f}")
        L.append("Business value:        not baselined (optional in V1)")
    if p["budget_per_success"]:
        L.append(f"Budget: ${p['budget_per_success']:.2f}/success, breaches: {p['budget_breaches']}")
    return "\n".join(L)


def _bar(label, value, total, color):
    width = (value / total * 100) if total else 0.0
    return (
        f'<div class="brow"><span class="blabel">{label}</span>'
        f'<div class="btrack"><div class="bfill" style="width:{width:.1f}%;background:{color};"></div></div>'
        f'<span class="bval">${value:,.2f}</span></div>'
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

    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Histogram of per-attempt costs">']
    for i, b in enumerate(buckets):
        bh = b / peak * ih
        bx = pad_l + i * iw + 2
        parts.append(
            f'<rect x="{bx:.1f}" y="{h - pad_b - bh:.1f}" width="{iw - 4:.1f}" '
            f'height="{bh:.1f}" fill="#4a7fd4"><title>{b} attempts in bucket</title></rect>')
    for v, lab, col in ((p50, "p50", "#1c5c2a"), (p95, "p95", "#b3261e")):
        x = x_of(v)
        parts.append(
            f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="{h - pad_b}" stroke="{col}" '
            f'stroke-width="2" stroke-dasharray="5,3"/>'
            f'<text x="{x:.1f}" y="20" fill="{col}" font-size="12" text-anchor="middle">'
            f'{lab} ${v:.2f}</text>')
    parts.append(
        f'<text x="{pad_l}" y="{h - 8}" font-size="11" fill="#555">${lo:.2f}</text>'
        f'<text x="{w - 20}" y="{h - 8}" font-size="11" fill="#555" text-anchor="end">${hi:.2f}</text>'
        f'<text x="{pad_l}" y="{h - pad_b - ih - 6}" font-size="11" fill="#555">{peak} attempts max bucket</text>')
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
        mult_card = (f'<div class="card"><div class="k">Token-dashboard multiple</div>'
                     f'<div class="v">{mult:.1f}x</div>'
                     f'<div class="s">real cost vs ${token_dashboard_per_success:.2f} dashboard view</div></div>')
    else:
        mult_card = ""

    ps_total = sum(ps[k] for k in ("model", "tools", "retry", "human"))
    breakdown = "".join([
        _bar("Model / API", ps["model"], ps_total, "#4a7fd4"),
        _bar("Tool calls", ps["tools"], ps_total, "#7ab648"),
        _bar("Retries", ps["retry"], ps_total, "#e0a32e"),
        _bar("Human review", ps["human"], ps_total, "#c25bb5"),
    ])

    tot_model = p["cost_model"] or 1
    model_rows = "".join(
        f'<tr><td>{_html.escape(k)}</td><td class="r">${v:,.2f}</td>'
        f'<td class="r">{v / tot_model:.0%} of model spend</td></tr>'
        for k, v in sorted(p["per_model"].items(), key=lambda kv: -kv[1]))

    policy_section = ""
    if policy_sim is not None:
        pol = policy_sim["policy"]
        policy_section = (
            '<h2>Policy replay (read only)</h2>'
            f'<p class="lede">Had policy X existed, <b>{policy_sim["would_stop"]} runs</b> '
            f'would have been stopped, exposing <b>${policy_sim["exposed_spend"]:,.2f}</b> '
            f'({policy_sim["exposed_share"]:.0%} of total spend).</p>'
            f'<p class="s">Policy tested: max cost per attempt ${pol["max_cost_per_attempt"]}, '
            f'yield floor {pol["yield_floor"]}. No enforcement was applied; this is a '
            f'replay of recorded history.</p>')
        if policy_sim["worst"]:
            policy_section += (
                '<table><tr><th>Run</th><th>Cost</th><th>Outcome</th><th>Reason</th></tr>' +
                "".join(
                    f'<tr><td>{_html.escape(str(w["case_id"]))}</td>'
                    f'<td class="r">${w["total_cost"]:.2f}</td>'
                    f'<td>{"success" if w["success"] else "FAILED"}</td>'
                    f'<td>{_html.escape("; ".join(w["reasons"]))}</td></tr>'
                    for w in policy_sim["worst"]) + '</table>')

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent P&L report: {_html.escape(p['agent'])}</title>
<style>
body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: #1f2933;
  max-width: 860px; margin: 0 auto; padding: 24px; background: #f7f8fa; }}
main {{ background: #fff; border: 1px solid #e2e6ec; border-radius: 10px; padding: 28px; }}
h1 {{ margin: 0 0 4px; font-size: 26px; }}
.meta {{ color: #5b6470; margin: 0 0 20px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px; margin: 18px 0; }}
.card {{ border: 1px solid #e2e6ec; border-radius: 8px; padding: 12px 14px; background: #fafbfc; }}
.card .k {{ font-size: 12px; color: #5b6470; text-transform: uppercase; letter-spacing: .04em; }}
.card .v {{ font-size: 24px; font-weight: 700; margin: 4px 0; }}
.card .s {{ font-size: 12px; color: #5b6470; }}
h2 {{ font-size: 18px; margin: 26px 0 10px; border-bottom: 1px solid #eef1f4; padding-bottom: 6px; }}
.lede {{ font-size: 15px; }}
.brow {{ display: flex; align-items: center; gap: 10px; margin: 6px 0; }}
.blabel {{ width: 130px; font-size: 13px; }}
.btrack {{ flex: 1; height: 18px; background: #eef1f4; border-radius: 9px; overflow: hidden; }}
.bfill {{ height: 100%; }}
.bval {{ width: 90px; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #eef1f4; }}
th {{ color: #5b6470; font-weight: 600; }}
.r {{ text-align: right; font-variant-numeric: tabular-nums; }}
svg {{ width: 100%; height: auto; background: #fafbfc; border: 1px solid #eef1f4; border-radius: 8px; }}
.layers li {{ margin: 6px 0; font-size: 14px; }}
footer {{ margin-top: 24px; font-size: 12px; color: #8a94a1; text-align: center; }}
</style>
</head>
<body>
<main>
<h1>Agent P&L: {_html.escape(p['agent'])}</h1>
<p class="meta">{p['attempts']:,} attempts &middot; {p['successes']:,} autonomous completions &middot;
{p['success_rate']:.1%} success rate &middot; {p['escalations']:,} escalations &middot; {p['reopened']:,} reopened</p>
<div class="cards">
<div class="card"><div class="k">Fully loaded</div><div class="v">${ps['fully_loaded']:,.2f}</div>
<div class="s">per accepted outcome</div></div>
{mult_card}
<div class="card"><div class="k">Yield ratio</div><div class="v">{p['yield_ratio']:.0%}</div>
<div class="s">terminal-path tokens / total</div></div>
<div class="card"><div class="k">Top 5% tail share</div><div class="v">{t['top5pct_share']:.0%}</div>
<div class="s">of total spend in costliest runs</div></div>
</div>
<h2>Cost per successful outcome</h2>
{breakdown}
<h2>Per-attempt cost distribution</h2>
{_histogram_svg(costs, t['p50'], t['p95'])}
<p class="s">p50 ${t['p50']:.2f} &middot; p95 ${t['p95']:.2f} &middot; max ${t['max']:.2f} per attempt</p>
<h2>The five layers</h2>
<ul class="layers">
<li><b>Context compounding:</b> {p['avg_context_growth']:.1f}x input growth, first to last step
(state accumulation tax).</li>
<li><b>External tool spend:</b> ${p['cost_tools']:,.2f} total, ${ps['tools']:,.2f} per success
(invisible on provider invoices).</li>
<li><b>Yield ratio:</b> {p['yield_ratio']:.0%} of tokens on the terminal path,
{1 - p['yield_ratio']:.0%} burned on retries and dead ends.</li>
<li><b>Heavy tail:</b> p50 ${t['p50']:.2f} / p95 ${t['p95']:.2f} / max ${t['max']:.2f} per attempt;
top 5% of attempts consumed {t['top5pct_share']:.0%} of budget.</li>
<li><b>Model mix:</b> ${p['cost_model']:,.2f} total model spend (see table).</li>
</ul>
<h2>Top cost drivers (per model)</h2>
<table><tr><th>Model</th><th class="r">Spend</th><th class="r">Share</th></tr>{model_rows}</table>
{policy_section}
</main>
<footer>Generated locally by agentpnl. No data leaves your environment.</footer>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path
