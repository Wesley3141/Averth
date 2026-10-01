"""Core tracker: meter everything an agent spends, tag outcomes, enforce budgets.

Implements Wesley's five cost layers:
  1. context compounding  — per-step input-token growth, priced as a dollar
     "context tax" against a flat-context counterfactual
  2. external tool spend  — log_tool_call with real per-call costs
  3. yield vs waste       — retry-path tokens AND failed-attempt tokens are
     waste; only terminal-path tokens of accepted outcomes count as useful
  4. heavy-tail outliers  — per-attempt cost distribution (interpolated
     percentiles), top-5% budget share
  5. multi-model + labor  — per-model attribution, loaded human-review cost,
     prompt-cache savings flagged as estimates

Waste semantics (the honest version): a token is useful only if it sits on
the terminal path of an accepted outcome. Tokens logged after a retry marker
are retry-path waste. Tokens of an attempt that never succeeded are waste in
full — a failed run has no terminal path, however interesting its partial
work. Cached input tokens are priced at a documented discount and the saving
is reported, never hidden.

Retry scope: log_retry() with no branch marks every subsequent step of the
attempt as waste (the historical behavior); earlier steps are assumed to
stand, which can overstate terminal spend when a global retry discards early
work — pass branch= when the discarded scope is known. log_retry(branch="b")
declares branch "b"'s work SO FAR discarded: that branch's existing steps
(past model and tool calls) count as retry-path waste, so a dead fan-out
branch no longer pollutes the yield. Work logged on the branch after the
retry is the redo and starts fresh; the productive merge step is never
smeared.

Numeric contract: every numeric input must be finite (NaN/inf rejected with
ValueError) and token counts are capped at 1e12. The live API validates
loudly rather than silently poisoning the ledger: a NaN anywhere would turn
cost_total into NaN and the exported ledger into invalid JSON.
"""

import math

from . import pricing


class BudgetBreach(Exception):
    """Raised (or passed to the callback) when an attempt exceeds budget_per_success.

    NOTE: live enforcement is Phase-1, built only after a buyer confirms who
    owns that authority and will pay for it. The Phase-0 pilot is read-only:
    record with Tracker, export the ledger, and replay hypothetical policies
    with agentpnl.policy.simulate_policy ("had policy X existed, these 37 runs
    would have been stopped").
    """


def _check_finite(name, value):
    """Reject NaN/inf: a single NaN poisons every downstream sum and the
    exported ledger would contain an invalid JSON NaN literal. Non-numeric
    types are rejected too (bool is not a number here)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


# Token counts above a trillion are malformed provider counters, not real
# usage (5,000x the largest context window). They would OverflowError the
# float cost math; reject them as the garbage they are.
_MAX_TOKENS = 10 ** 12


def _check_nonneg_int(name, value):
    _check_finite(name, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    if value > _MAX_TOKENS:
        raise ValueError("%s implausibly large: %r" % (name, value))
    return int(value)


def _check_nonneg(name, value):
    _check_finite(name, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return float(value)


def _percentile(sorted_values, p):
    """Linear-interpolation percentile (numpy 'linear' method).

    The old nearest-rank indexing biased p50/p95 upward on small samples;
    interpolation is the standard, defensible definition.
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_values[0])
    rank = p * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


class Tracker:
    def __init__(self, agent_name, budget_per_success=None, on_breach=None,
                 human_cost_per_min=None, cache_read_discount=None):
        self.agent_name = agent_name
        self.budget_per_success = budget_per_success
        self.on_breach = on_breach
        self.human_cost_per_min = human_cost_per_min or pricing.HUMAN_COST_PER_MIN
        self.cache_read_discount = (pricing.CACHE_READ_DISCOUNT
                                    if cache_read_discount is None
                                    else cache_read_discount)
        self.attempts = []
        # "provider:model" keys priced by estimate (unknown to pricing.MODEL_PRICES)
        self.unpriced_models = set()
        self._cur = None

    # ---- per-attempt lifecycle ----
    def start_attempt(self, case_id=None):
        if self._cur is not None:
            raise RuntimeError("previous attempt not ended; call end_attempt first")
        self._cur = {"case_id": case_id, "model": 0.0, "tools": 0.0,
                     "retries": 0, "retry_cost": 0.0,
                     "human_min": 0.0, "events": [],
                     # step dicts: in/out/cost/retry/in_price/cached/branch
                     "steps": [],
                     # tool step dicts: name/cost/retry/branch
                     "tool_steps": [],
                     "retry_all": False,      # attempt-global retry marker
                     "tool_latency_ms": 0.0,
                     "per_model": {},
                     "cached_tokens": 0,
                     "cache_savings": 0.0}

    def _step_is_waste(self, branch):
        # Branch retries are retroactive (applied to past steps at retry
        # time), so only the global marker affects future steps.
        return self._cur["retry_all"]

    def _record_step(self, provider, model, in_tok, out_tok, cost,
                     in_price_per_m, cached_tok=0, branch=None):
        cur = self._cur
        waste = self._step_is_waste(branch)
        cur["model"] += cost
        cur["steps"].append({
            "in": in_tok, "out": out_tok, "cost": cost,
            "retry": waste, "in_price": in_price_per_m,
            "cached": cached_tok, "branch": branch,
        })
        key = "%s:%s" % (provider, model)
        cur["per_model"][key] = cur["per_model"].get(key, 0.0) + cost
        cur["events"].append(("model", provider, model, cost))
        cur["cached_tokens"] += cached_tok

    def log_model_call(self, provider, model, input_tokens, output_tokens,
                       cached_input_tokens=0, branch=None):
        """Record one model call. cached_input_tokens are priced at the
        Tracker's cache_read_discount; the saving is tracked in
        cache_savings so it is visible, never silently netted."""
        self._req()
        in_tok = _check_nonneg_int("input_tokens", input_tokens)
        out_tok = _check_nonneg_int("output_tokens", output_tokens)
        cached = _check_nonneg_int("cached_input_tokens", cached_input_tokens)
        if cached > in_tok:
            cached = in_tok  # malformed trace data; never price phantom tokens
        key = "%s:%s" % (provider, model)
        try:
            pin, pout = pricing.MODEL_PRICES[key]
        except KeyError:
            raise KeyError("no price for %s; add it to MODEL_PRICES "
                           "or use log_model_cost_estimate" % key)
        d = self.cache_read_discount
        cost = ((in_tok - cached) / 1e6 * pin
                + cached / 1e6 * pin * d
                + out_tok / 1e6 * pout)
        saving = cached / 1e6 * pin * (1.0 - d)
        self._cur["cache_savings"] += saving
        self._record_step(provider, model, in_tok, out_tok, cost,
                          pin, cached_tok=cached, branch=branch)

    def log_model_cost_estimate(self, provider, model, cost,
                                input_tokens=0, output_tokens=0,
                                cached_input_tokens=0, branch=None):
        """Record a model call priced by estimate (model unknown to pricing tables).

        Used by framework integrations when pricing.model_call_cost raises
        KeyError. Behaves like log_model_call but takes the dollar cost
        directly; the model key is flagged in tracker.unpriced_models and
        surfaced in pnl() so estimated spend is visible, never hidden.
        Cached tokens are recorded for token accounting; the explicit cost
        is used as given (no cache math on an already-estimated number).
        """
        self._req()
        in_tok = _check_nonneg_int("input_tokens", input_tokens)
        out_tok = _check_nonneg_int("output_tokens", output_tokens)
        cached = _check_nonneg_int("cached_input_tokens", cached_input_tokens)
        if cached > in_tok:
            cached = in_tok
        cost = _check_nonneg("cost", cost)
        cur = self._cur
        cur["model"] += cost
        # in_price unknown for estimates; 0.0 keeps the context-tax math safe
        # (estimate calls contribute no compounding tax rather than a wrong one)
        cur["steps"].append({
            "in": in_tok, "out": out_tok, "cost": cost,
            "retry": self._step_is_waste(branch), "in_price": 0.0,
            "cached": cached, "branch": branch,
        })
        key = "%s:%s" % (provider, model)
        cur["per_model"][key] = cur["per_model"].get(key, 0.0) + cost
        cur["events"].append(("model_estimate", provider, model, cost))
        cur["cached_tokens"] += cached
        self.unpriced_models.add(key)

    def log_tool_call(self, name, cost=None, branch=None):
        """Record a tool call. branch= tags which parallel branch made the
        call so retry-path tool spend is attributed to the discarded path
        instead of vanishing into the tools total."""
        self._req()
        c = cost if cost is not None else pricing.tool_call_cost(name)
        c = _check_nonneg("tool cost", c)
        cur = self._cur
        cur["tools"] += c
        cur["tool_steps"].append({
            "name": name, "cost": c,
            "retry": self._step_is_waste(branch), "branch": branch,
        })
        cur["events"].append(("tool", name, c))

    def log_retry(self, reason="", extra_model_cost=0.0, branch=None):
        """Mark the retry path as waste.

        extra_model_cost is spend NOT otherwise logged as a model step (e.g.
        the failed call that triggered this retry when the integration did
        not log it via log_model_call). Do not pass it for spend already
        recorded — that would double-count.

        When branch is given, this declares that branch's work SO FAR in this
        attempt discarded: the branch's existing steps (model and tool) are
        retroactively marked as retry-path waste (M1). Work logged on the
        branch after this point is the redo and starts fresh — it is not
        pre-tainted. A global retry (no branch) keeps the historical
        forward-only behavior: subsequent steps are waste, earlier steps are
        assumed to stand. That assumption can overstate terminal spend when
        the retry discards early work — a documented limitation; use branch=
        when the discarded scope is known.
        """
        self._req()
        extra_model_cost = _check_nonneg("extra_model_cost", extra_model_cost)
        cur = self._cur
        cur["retries"] += 1
        cur["retry_cost"] += extra_model_cost
        if branch is None:
            cur["retry_all"] = True   # subsequent steps count as waste-path
        else:
            # Branch-scoped retry (M1): declares that branch's work SO FAR
            # discarded. Retroactively mark the branch's existing steps
            # (model and tool) as waste. Work logged on the branch AFTER
            # this point is the redo — it starts fresh, not pre-tainted.
            # (A second retry on the same branch discards the redo as well.)
            for s in cur["steps"]:
                if s["branch"] == branch:
                    s["retry"] = True
            for ts in cur["tool_steps"]:
                if ts["branch"] == branch:
                    ts["retry"] = True
        cur["events"].append(("retry", reason, extra_model_cost,
                              branch if branch is not None else ""))

    def log_escalation(self, minutes, reason=""):
        self._req()
        minutes = _check_nonneg("minutes", minutes)
        self._cur["human_min"] += minutes
        self._cur["events"].append(("escalation", reason, minutes))

    def end_attempt(self, success, business_value=0.0, reopened=False):
        self._req()
        business_value = _check_finite("business_value", business_value)
        a = self._cur
        a["success"] = bool(success)
        a["business_value"] = business_value
        a["reopened"] = bool(reopened)
        a["human_cost"] = a["human_min"] * self.human_cost_per_min
        a["ai_cost"] = a["model"] + a["tools"] + a["retry_cost"]
        a["total_cost"] = a["ai_cost"] + a["human_cost"]
        steps = a["steps"]
        # layer 1a: context compounding ratio, first -> last step (kept for
        # continuity; the dollar tax below is the primary metric)
        a["context_growth"] = ((steps[-1]["in"] / steps[0]["in"])
                               if len(steps) > 1 and steps[0]["in"] else 1.0)
        # layer 1b: context tax in dollars — extra input-token spend vs the
        # counterfactual where every step cost what the first step's input
        # size would have cost at that step's own input price. Signed: state
        # that shrinks genuinely costs less than flat context. Priced at the
        # cache-discounted effective input rate: cached re-reads are cheap,
        # so taxing them at full price would overstate compounding.
        base_in = steps[0]["in"] if steps else 0
        tax = 0.0
        d = self.cache_read_discount
        for s in steps[1:]:
            if s["in"] <= 0 or s["in_price"] <= 0:
                continue
            cached_frac = min(s["cached"] / s["in"], 1.0)
            eff_price = s["in_price"] * (1.0 - cached_frac * (1.0 - d))
            tax += (s["in"] - base_in) / 1e6 * eff_price
        a["context_tax"] = tax
        # layer 3: yield — terminal-path tokens vs total. Retry-path tokens
        # are waste; every token of a failed attempt is waste (no terminal
        # path exists without an accepted outcome).
        tot_tok = sum(s["in"] + s["out"] for s in steps)
        if a["success"]:
            waste_tok = sum(s["in"] + s["out"] for s in steps if s["retry"])
        else:
            waste_tok = tot_tok
        a["total_tokens"] = tot_tok
        a["waste_tokens"] = waste_tok
        # Dollar split: terminal model spend is ONLY the model spend on the
        # terminal path (successful attempt, non-waste steps). Everything
        # else model-side — retry-flagged steps, extra_model_cost, and the
        # entire model spend of failed attempts — is retry-path (discarded
        # paths). Identity preserved: terminal + retry_path = model + retry.
        waste_step_cost = sum(s["cost"] for s in steps if s["retry"])
        if a["success"]:
            a["terminal_model_cost"] = a["model"] - waste_step_cost
            a["retry_path_cost"] = waste_step_cost + a["retry_cost"]
        else:
            a["terminal_model_cost"] = 0.0
            a["retry_path_cost"] = a["model"] + a["retry_cost"]
        # retry-path tool spend (M3): waste-flagged tool calls are a separate
        # lens, not part of retry_path_cost, so the per-success buckets stay
        # additive (terminal + retry_path + tools + human = total).
        a["retry_tool_cost"] = sum(ts["cost"] for ts in a["tool_steps"]
                                   if ts["retry"])
        self.attempts.append(a)
        self._cur = None
        if success and self.budget_per_success and a["total_cost"] > self.budget_per_success:
            breach = BudgetBreach(
                "%s: case cost $%.2f exceeded budget $%.2f"
                % (self.agent_name, a["total_cost"], self.budget_per_success))
            if self.on_breach:
                self.on_breach(a, breach)
            else:
                raise breach
        return a

    def _req(self):
        if self._cur is None:
            raise RuntimeError("call start_attempt() first")

    # ---- aggregation ----
    def pnl(self):
        atts = self.attempts
        n = len(atts)
        ok = [a for a in atts if a["success"]]
        s = len(ok)
        esc = [a for a in atts if a["human_min"] > 0]
        reopened_atts = [a for a in atts if a.get("reopened")]
        reopened_ok_n = sum(1 for a in reopened_atts if a["success"])
        failed = [a for a in atts if not a["success"]]
        model = sum(a["model"] for a in atts)
        tools = sum(a["tools"] for a in atts)
        retry = sum(a["retry_cost"] for a in atts)
        # .get defaults: ledgers written before the hardening pass lack the
        # new attempt keys; pnl() must degrade gracefully, not crash.
        retry_path = sum(a.get("retry_path_cost", 0.0) for a in atts)
        terminal_model = sum(a.get("terminal_model_cost", a["model"])
                             for a in atts)
        retries_n = sum(a["retries"] for a in atts)
        human = sum(a["human_cost"] for a in atts)
        value = sum(a["business_value"] for a in ok)
        total = model + tools + retry + human
        failed_cost = sum(a["total_cost"] for a in failed)
        reopened_cost = sum(a["total_cost"] for a in reopened_atts)
        context_tax = sum(a.get("context_tax", 0.0) for a in atts)
        cache_savings = sum(a.get("cache_savings", 0.0) for a in atts)
        cached_tokens = sum(a.get("cached_tokens", 0) for a in atts)
        retry_tool = sum(a.get("retry_tool_cost", 0.0) for a in atts)
        per = (lambda x: x / s if s else 0.0)

        # layer 3: yield ratio (failed-attempt tokens are waste by definition)
        tot_tok = sum(a["total_tokens"] for a in atts)
        waste_tok = sum(a["waste_tokens"] for a in atts)
        yield_ratio = 1 - waste_tok / tot_tok if tot_tok else 1.0

        # layer 1: avg context compounding (ratio form, kept for continuity).
        # .get with default: minimal hand-built ledgers may lack the key (C7).
        growths = [a.get("context_growth", 1.0) for a in atts]
        avg_growth = sum(growths) / len(growths) if growths else 1.0

        # layer 4: heavy tail (interpolated percentiles). The "top 5%" label
        # is only honest for n >= 20; below that we report the costliest
        # single run's share instead of a false "5%".
        costs = sorted(a["total_cost"] for a in atts)  # ascending
        if n >= 20:
            tail_n = max(1, int(n * 0.05))
            tail_label = "top 5%"
        else:
            tail_n = 1
            tail_label = "costliest run"
        tail_share = sum(costs[-tail_n:]) / total if total else 0.0

        # layer 5: per-model attribution
        per_model = {}
        for a in atts:
            for k, v in a["per_model"].items():
                per_model[k] = per_model.get(k, 0.0) + v

        # retry reasons: the operational lever behind retry-path spend.
        # Events are preserved through export -> reimport, so reasons
        # survive on the ledger artifact (H5); .get guards ancient ledgers.
        from collections import Counter
        reasons = Counter()
        for a in atts:
            for ev in a.get("events", []) or []:
                if ev[0] == "retry" and ev[1]:
                    reasons[ev[1]] += 1
        top_retry_reasons = reasons.most_common(5)

        costliest = sorted(atts, key=lambda a: -a["total_cost"])[:10]
        costliest_attempts = [
            {"case_id": a["case_id"], "total_cost": a["total_cost"],
             "success": a["success"], "retries": a["retries"],
             "human_min": a["human_min"], "reopened": a.get("reopened", False)}
            for a in costliest
        ]

        unpriced_spend = sum(v for k, v in per_model.items()
                             if k in self.unpriced_models)

        breaches = sum(1 for a in ok
                       if self.budget_per_success and a["total_cost"] > self.budget_per_success)
        breach_spend = sum(a["total_cost"] for a in ok
                           if self.budget_per_success and a["total_cost"] > self.budget_per_success)
        return {
            "agent": self.agent_name,
            "attempts": n,
            "successes": s,
            "success_rate": s / n if n else 0.0,
            "reopened": len(reopened_atts),
            "reopened_successful": reopened_ok_n,
            "escalations": len(esc),
            "retries": retries_n,
            "cost_model": model,
            "cost_model_terminal": terminal_model,
            "cost_tools": tools,
            "cost_retry": retry,
            "cost_retry_path": retry_path,
            "cost_retry_tools": retry_tool,
            "cost_human": human,
            "cost_total": total,
            "cost_failed": failed_cost,
            "failed_spend_share": failed_cost / total if total else 0.0,
            "cost_reopened": reopened_cost,
            "reopened_spend_share": reopened_cost / total if total else 0.0,
            "context_tax": context_tax,
            "context_tax_per_success": per(context_tax),
            "context_tax_share_of_model": context_tax / model if model else 0.0,
            "cache_savings": cache_savings,
            "cached_tokens": cached_tokens,
            "unpriced_spend": unpriced_spend,
            "per_success": {
                "model": per(terminal_model),
                "retry_path": per(retry_path),
                "tools": per(tools),
                "human": per(human),
                "fully_loaded": per(total),
            },
            "yield_ratio": yield_ratio,
            "avg_context_growth": avg_growth,
            "tail": {"p50": _percentile(costs, 0.50),
                     "p95": _percentile(costs, 0.95),
                     "max": costs[-1] if costs else 0.0,
                     "top5pct_share": tail_share,
                     "tail_label": tail_label},
            "per_model": per_model,
            "unpriced_models": sorted(self.unpriced_models),
            "top_retry_reasons": [(r, c) for r, c in top_retry_reasons],
            "costliest_attempts": costliest_attempts,
            "business_value": value,
            "net_value": value - total,
            "budget_per_success": self.budget_per_success,
            "budget_breaches": breaches,
            "budget_breach_spend": breach_spend,
        }
