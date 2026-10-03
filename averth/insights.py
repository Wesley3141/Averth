"""Behavior-changing insights from a single P&L run.

The venture's kill rule: at least one finding must change behavior. findings()
ranks every candidate lever by dollars so the report can lead with the one
that matters, each paired with the concrete action it implies. No finding
fires on noise: every rule has a materiality threshold, and every dollar
figure traces back to tracker.pnl().
"""

HIGH = "high"
MEDIUM = "medium"
INFO = "info"


def _finding(fid, severity, title, detail, dollars, action):
    return {"id": fid, "severity": severity, "title": title,
            "detail": detail, "dollars": dollars, "action": action}


def _plural(n, singular, plural=None):
    """User-facing counts must agree: "1 failed run", "2 failed runs"."""
    return "%d %s" % (n, singular if n == 1 else (plural or singular + "s"))


def findings(p):
    """Rank behavior-changing findings for a pnl() dict, by dollars."""
    import math
    out = []
    total = p["cost_total"] or 0.0
    # H8 / materiality: a NaN-poisoned ledger reports nothing, and ledgers
    # under $1 of total spend are below the noise floor — no finding fires
    # on trivial absolute spend, however pathological the shares look.
    if not math.isfinite(total) or total < 1.0:
        return out
    ps = p["per_success"]
    t = p["tail"]
    n = p["attempts"]

    # 1. Failed runs: spend with zero outcomes. The purest waste there is.
    if p["failed_spend_share"] >= 0.15 and p["cost_failed"] > 0:
        n_failed = p["attempts"] - p["successes"]
        out.append(_finding(
            "failed_spend", HIGH,
            "Failed runs burned $%s (%s of spend) for zero outcomes"
            % ("{:,.2f}".format(p["cost_failed"]),
               "%.0f%%" % (p["failed_spend_share"] * 100)),
            "%s of %s never produced an accepted outcome, yet "
            "consumed $%s. Every dollar is waste by definition — there is no "
            "terminal path without an outcome."
            % (_plural(n_failed, "attempt"), _plural(p["attempts"], "attempt"),
               "{:,.2f}".format(p["cost_failed"])),
            p["cost_failed"],
            "Cap per-attempt spend near p95 ($%.2f) and replay the policy: "
            "runs that blow past it are overwhelmingly failed runs."
            % t["p95"]))

    # 2. Tail concentration: the 2%-burns-60% shape. The "top 5%" label is
    # only honest for n >= 20 (H3); on smaller ledgers the rule stays silent
    # instead of firing HIGH on a single sample.
    if n >= 20 and t["top5pct_share"] >= 0.40 and total > 0:
        n_tail = max(1, int(n * 0.05))
        out.append(_finding(
            "tail_concentration", HIGH,
            "The costliest %s consumed %.0f%% of the budget"
            % (_plural(n_tail, "run"), t["top5pct_share"] * 100),
            "p50 is $%.2f but p95 is $%.2f and max is $%.2f. Median unit "
            "economics look fine; the tail is where the budget goes."
            % (t["p50"], t["p95"], t["max"]),
            t["top5pct_share"] * total,
            "Put a hard per-attempt envelope at ~p95 ($%.2f). The policy "
            "replay below shows exactly what it would have saved — and what "
            "good outcomes it would have cost." % t["p95"]))

    # 3. Retry-path waste with the top reason named. Dollars include
    # retry-path tool spend (M3): a $5 tool call on a discarded path is
    # retry waste, not just "tools".
    retry_dollars = p["cost_retry_path"] + p.get("cost_retry_tools", 0.0)
    retry_share = retry_dollars / total if total else 0.0
    if retry_share >= 0.20 and retry_dollars > 0:
        top = p["top_retry_reasons"][0] if p["top_retry_reasons"] else None
        reason_bit = (" Top culprit: '%s' (%s)."
                      % (top[0], _plural(top[1], "retry", "retries"))) if top else ""
        action = ("Fix the top retry reason before touching models: '%s'. One "
                  "validation fix upstream is worth more than a cheaper model."
                  % top[0]) if top else \
                 ("Name retry reasons via log_retry(reason=...): the meter can "
                  "price the waste but only you can say what to fix first.")
        out.append(_finding(
            "retry_waste", HIGH if retry_share >= 0.35 else MEDIUM,
            "Retry loops burned $%s (%.0f%% of spend)"
            % ("{:,.2f}".format(retry_dollars), retry_share * 100),
            "Yield is %.0f%%: %s across %s, and the "
            "discarded paths cost real money, not just tokens.%s"
            % (p["yield_ratio"] * 100, _plural(p["retries"], "retry", "retries"),
               _plural(n, "attempt"), reason_bit),
            retry_dollars, action))

    # 4. Human labor dominance.
    # C3: the dollars here ride on the loaded labor rate. When the default
    # assumption is in effect the finding says so — it must never read as
    # a measured fact about the prospect's workforce.
    human_share = p["cost_human"] / total if total else 0.0
    if human_share >= 0.50 and p["cost_human"] > 0:
        per_esc = p["cost_human"] / max(p["escalations"], 1)
        rate_note = ""
        if p.get("human_rate_assumed", True):
            rate_note = (" Labor is costed at $%.2f/hr loaded (default "
                         "assumption — set your real rate with "
                         "human_cost_per_min)." % (p.get("human_cost_per_min",
                                                          1.17) * 60))
        out.append(_finding(
            "human_dominance", HIGH,
            "Human review is %.0f%% of fully-loaded cost ($%s)"
            % (human_share * 100, "{:,.2f}".format(p["cost_human"])),
            "%s at $%.2f loaded each. The model bill ($%s) is a "
            "rounding error next to the labor it summons.%s"
            % (_plural(p["escalations"], "escalation"), per_esc,
               "{:,.2f}".format(p["cost_model"]), rate_note),
            p["cost_human"],
            "Attack escalation rate, not model price: tighten auto-resolve "
            "confidence, or add a cheaper first review tier."))

    # 4b. Tool-spend dominance (layer 2 finally has a finding): the agent is
    # mostly a wrapper around paid APIs, and the model bill is the distraction.
    tool_share = p["cost_tools"] / total if total else 0.0
    if tool_share >= 0.50 and p["cost_tools"] > 0:
        out.append(_finding(
            "tool_dominance", HIGH,
            "Tool/API calls are %.0f%% of spend ($%s)"
            % (tool_share * 100, "{:,.2f}".format(p["cost_tools"])),
            "The model bill ($%s) is %.0f%% of the total; the agent is "
            "economically a wrapper around paid external calls."
            % ("{:,.2f}".format(p["cost_model"]),
               (p["cost_model"] / total * 100) if total else 0.0),
            p["cost_tools"],
            "Renegotiate, cache, or batch the top tool calls by spend; "
            "model-price tuning cannot move this number."))

    # 4c. Budget breaches: the spend envelope was blown, repeatedly.
    # C1: breaches now count EVERY over-envelope attempt (failed runaways
    # included), consistent with the live hook. Failed-run breaches are
    # pure waste and are named separately.
    if p.get("budget_breaches", 0) > 0:
        n_br = p["budget_breaches"]
        n_br_failed = p.get("budget_breaches_failed", 0)
        n_br_ok = n_br - n_br_failed
        if n_br_failed == 1:
            failed_bit = " 1 of them was a failed run (pure waste)."
        elif n_br_failed > 1:
            failed_bit = (" %d of them were failed runs (pure waste)."
                          % n_br_failed)
        else:
            failed_bit = ""
        out.append(_finding(
            "budget_breach", HIGH if n_br >= max(p["attempts"], 1) * 0.10 else MEDIUM,
            "%s of %s blew the $%.2f spend envelope"
            % (_plural(n_br, "attempt"), _plural(p["attempts"], "attempt"),
               p.get("budget_per_success") or 0.0),
            "%s and %s exceeded the envelope "
            "you set, burning $%s.%s"
            % (_plural(n_br_ok, "accepted outcome"),
               _plural(n_br_failed, "failed run"),
               "{:,.2f}".format(p.get("budget_breach_spend", 0.0)),
               failed_bit),
            p.get("budget_breach_spend", 0.0),
            "Treat the envelope as a kill-switch threshold in Phase 1, or "
            "replay a tighter envelope with the policy simulator."))

    # 5. Context tax.
    tax_share = p["context_tax_share_of_model"]
    if tax_share >= 0.25 and p["context_tax"] > 0:
        out.append(_finding(
            "context_tax", MEDIUM,
            "Context growth added $%s (%.0f%% of model spend)"
            % ("{:,.2f}".format(p["context_tax"]), tax_share * 100),
            "Input state grew %.1fx first-to-last step on average; the "
            "marginal late step costs multiples of the first. Dashboards "
            "show the tokens but not the compounding."
            % p["avg_context_growth"],
            p["context_tax"],
            "Compact or summarize carried state between steps. Measure the "
            "tax again after: it should drop faster than token count."))

    # 6. Reopened cases: the fix didn't stick. Counts only successful
    # attempts (H7): a failed+reopened attempt was never an accepted outcome.
    # H1: the gate fires on reopened_spend_share, which includes failed-redo
    # spend — when no reopened attempt succeeded, the text must not claim
    # anything was "booked as success".
    reopened_ok = p.get("reopened_successful", p["reopened"])
    if p["reopened_spend_share"] >= 0.10 and p["cost_reopened"] > 0:
        n_reopened = p["reopened"]
        if reopened_ok:
            verb = "was" if reopened_ok == 1 else "were"
            poss = "Its" if reopened_ok == 1 else "Their"
            reopened_detail = (
                "%s %s reopened. %s first-pass cost was "
                "booked as success, then the work repeated."
                % (_plural(reopened_ok, "accepted outcome"), verb, poss))
        else:
            verb = "was" if n_reopened == 1 else "were"
            reopened_detail = (
                "%s %s reopened but every redo failed — nothing was "
                "booked as success, yet the repeated work still burned "
                "spend."
                % (_plural(n_reopened, "attempt"), verb))
        out.append(_finding(
            "reopened", MEDIUM,
            "Reopened cases cost $%s (%.0f%% of spend)"
            % ("{:,.2f}".format(p["cost_reopened"]),
               p["reopened_spend_share"] * 100),
            reopened_detail,
            p["cost_reopened"],
            "Track reopen reasons the way retries are tracked: a reopen is "
            "a retry with a longer fuse."))

    # 7. Yield below the healthy band. Dollars are EXACT, not a ratio
    # approximation (H1): cost_retry_path is precisely the model dollars off
    # the terminal path — retry-flagged steps PLUS the extra_model_cost
    # passed to log_retry(), which the tracker books as model-side waste
    # outside the per-step model spend (C1: cost_model - cost_model_terminal
    # silently excludes extra_model_cost and understates the waste by
    # exactly that amount).
    if p["yield_ratio"] < 0.60 and total > 0:
        waste_model_dollars = p["cost_retry_path"]
        out.append(_finding(
            "low_yield", MEDIUM,
            "Only %.0f%% of tokens were on a terminal path"
            % (p["yield_ratio"] * 100),
            "Failed attempts and retry paths together discarded %.0f%% of "
            "all tokens ($%s of model spend). Token dashboards report this "
            "as usage; it is waste."
            % ((1 - p["yield_ratio"]) * 100,
               "{:,.2f}".format(waste_model_dollars)),
            waste_model_dollars,
            "Terminate attempts that cross the retry-count or cost "
            "threshold where historical yield collapses."))

    # 8. Estimated (unpriced) spend: transparency, not a lever.
    if p["unpriced_spend"] > 0:
        models = ", ".join(p["unpriced_models"][:5])
        out.append(_finding(
            "unpriced_spend", INFO,
            "$%s of model spend is estimated, not vendor-priced"
            % "{:,.2f}".format(p["unpriced_spend"]),
            "Models without a pricing-table entry (%s%s) were costed by "
            "estimate — a caller-supplied dollar figure, or the documented "
            "fallback estimate where the caller supplied none."
            % (models, ", ..." if len(p["unpriced_models"]) > 5 else ""),
            p["unpriced_spend"],
            "Add verified per-1M prices to pricing.MODEL_PRICES; the flag "
            "clears automatically."))

    # 9. Cache: credit where due.
    if p["cached_tokens"] > 0 and p["cache_savings"] > 0:
        cached = p["cached_tokens"]
        tokens_bit = ("1 input token" if cached == 1
                      else "%s input tokens" % "{:,}".format(cached))
        out.append(_finding(
            "cache_savings", INFO,
            "Prompt cache saved $%s on %s"
            % ("{:,.2f}".format(p["cache_savings"]), tokens_bit),
            "Cache-read tokens were priced at the documented discount "
            "instead of full input price. Without caching this run would "
            "have cost $%s more in model spend."
            % "{:,.2f}".format(p["cache_savings"]),
            p["cache_savings"],
            "Keep it: cache-heavy workloads are the cheapest place to buy "
            "back margin."))

    out.sort(key=lambda f: (-f["dollars"],
                            {HIGH: 0, MEDIUM: 1, INFO: 2}[f["severity"]]))
    return out


def top_insight(p):
    """The single finding that should change behavior, or None."""
    fs = findings(p)
    return fs[0] if fs else None


def findings_text(p, limit=3):
    """Plain-text rendering of the top findings for CLI / text reports."""
    fs = findings(p)[:limit]
    if not fs:
        return "No material findings: spend is clean across all five layers."
    lines = []
    for i, f in enumerate(fs, 1):
        lines.append("%d. [%s] %s" % (i, f["severity"].upper(), f["title"]))
        lines.append("   %s" % f["detail"])
        lines.append("   -> %s" % f["action"])
    # H4: the waste lenses are overlapping views, not additive partitions.
    lines.append("")
    lines.append("Note: waste figures are overlapping lenses on the same "
                 "spend, not additive partitions — do not sum them.")
    return "\n".join(lines)
