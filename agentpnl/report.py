"""Render a P&L report from tracker.pnl() — organized by the five cost layers."""


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
