"""Core tracker: meter everything an agent spends, tag outcomes, enforce budgets.

Implements Wesley's five cost layers:
  1. context compounding  — per-step input-token growth within an attempt
  2. external tool spend  — log_tool_call with real per-call costs
  3. yield vs waste       — retry-path tokens vs terminal-path tokens
  4. heavy-tail outliers  — per-attempt cost distribution, top-5% share
  5. multi-model + labor  — per-model attribution, loaded human-review cost
"""

from . import pricing


class BudgetBreach(Exception):
    """Raised (or passed to the callback) when an attempt exceeds budget_per_success.

    NOTE: live enforcement is Phase-1, built only after a buyer confirms who
    owns that authority and will pay for it. The Phase-0 pilot is read-only:
    record with Tracker, export the ledger, and replay hypothetical policies
    with agentpnl.policy.simulate_policy ("had policy X existed, these runs
    would have been stopped").
    """


class Tracker:
    def __init__(self, agent_name, budget_per_success=None, on_breach=None,
                 human_cost_per_min=None):
        self.agent_name = agent_name
        self.budget_per_success = budget_per_success
        self.on_breach = on_breach
        self.human_cost_per_min = human_cost_per_min or pricing.HUMAN_COST_PER_MIN
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
                     "steps": [],            # (input_tok, output_tok, cost, retry_path)
                     "in_retry_path": False,
                     "tool_latency_ms": 0.0,
                     "per_model": {}}

    def log_model_call(self, provider, model, input_tokens, output_tokens):
        self._req()
        c = pricing.model_call_cost(provider, model, input_tokens, output_tokens)
        cur = self._cur
        cur["model"] += c
        cur["steps"].append((input_tokens, output_tokens, c, cur["in_retry_path"]))
        key = f"{provider}:{model}"
        cur["per_model"][key] = cur["per_model"].get(key, 0.0) + c
        cur["events"].append(("model", provider, model, c))

    def log_model_cost_estimate(self, provider, model, cost,
                                input_tokens=0, output_tokens=0):
        """Record a model call priced by estimate (model unknown to pricing tables).

        Used by framework integrations when pricing.model_call_cost raises
        KeyError. Behaves like log_model_call but takes the dollar cost
        directly; the model key is flagged in tracker.unpriced_models and
        surfaced in pnl() so estimated spend is visible, never hidden.
        """
        self._req()
        cur = self._cur
        cur["model"] += cost
        cur["steps"].append((input_tokens, output_tokens, cost, cur["in_retry_path"]))
        key = f"{provider}:{model}"
        cur["per_model"][key] = cur["per_model"].get(key, 0.0) + cost
        cur["events"].append(("model_estimate", provider, model, cost))
        self.unpriced_models.add(key)

    def log_tool_call(self, name, cost=None):
        self._req()
        c = cost if cost is not None else pricing.tool_call_cost(name)
        self._cur["tools"] += c
        self._cur["events"].append(("tool", name, c))

    def log_retry(self, reason="", extra_model_cost=0.0):
        self._req()
        cur = self._cur
        cur["retries"] += 1
        cur["retry_cost"] += extra_model_cost
        cur["in_retry_path"] = True   # subsequent steps count as waste-path
        cur["events"].append(("retry", reason, extra_model_cost))

    def log_escalation(self, minutes, reason=""):
        self._req()
        self._cur["human_min"] += minutes
        self._cur["events"].append(("escalation", reason, minutes))

    def end_attempt(self, success, business_value=0.0, reopened=False):
        self._req()
        a = self._cur
        a["success"] = bool(success)
        a["business_value"] = business_value
        a["reopened"] = bool(reopened)
        a["human_cost"] = a["human_min"] * self.human_cost_per_min
        a["ai_cost"] = a["model"] + a["tools"] + a["retry_cost"]
        a["total_cost"] = a["ai_cost"] + a["human_cost"]
        # layer 1: context compounding — input growth first -> last step
        steps = a["steps"]
        a["context_growth"] = (steps[-1][0] / steps[0][0]) if len(steps) > 1 and steps[0][0] else 1.0
        # layer 3: yield — terminal-path tokens vs total
        tot_tok = sum(s[0] + s[1] for s in steps)
        waste_tok = sum(s[0] + s[1] for s in steps if s[3])
        a["total_tokens"] = tot_tok
        a["waste_tokens"] = waste_tok
        self.attempts.append(a)
        self._cur = None
        if success and self.budget_per_success and a["total_cost"] > self.budget_per_success:
            breach = BudgetBreach(
                f"{self.agent_name}: case cost ${a['total_cost']:.2f} exceeded "
                f"budget ${self.budget_per_success:.2f}")
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
        reopened = sum(1 for a in atts if a.get("reopened"))
        model = sum(a["model"] for a in atts)
        tools = sum(a["tools"] for a in atts)
        retry = sum(a["retry_cost"] for a in atts)
        retries_n = sum(a["retries"] for a in atts)
        human = sum(a["human_cost"] for a in atts)
        value = sum(a["business_value"] for a in ok)
        total = model + tools + retry + human
        per = (lambda x: x / s if s else 0.0)

        # layer 3: yield ratio (approx: non-retry-path tokens / total tokens)
        tot_tok = sum(a["total_tokens"] for a in atts)
        waste_tok = sum(a["waste_tokens"] for a in atts)
        yield_ratio = 1 - waste_tok / tot_tok if tot_tok else 1.0

        # layer 1: avg context compounding
        growths = [a["context_growth"] for a in atts
               if len(a.get("steps", [])) > 1 or a.get("context_growth")]
        avg_growth = sum(growths) / len(growths) if growths else 1.0

        # layer 4: heavy tail
        costs = sorted(a["total_cost"] for a in atts)  # ascending
        def pct(p):
            return costs[min(int(n * p), n - 1)] if n else 0.0
        tail_n = max(1, int(n * 0.05))
        tail_share = sum(costs[-tail_n:]) / total if total else 0.0

        # layer 5: per-model attribution
        per_model = {}
        for a in atts:
            for k, v in a["per_model"].items():
                per_model[k] = per_model.get(k, 0.0) + v

        breaches = sum(1 for a in ok
                       if self.budget_per_success and a["total_cost"] > self.budget_per_success)
        return {
            "agent": self.agent_name,
            "attempts": n,
            "successes": s,
            "success_rate": s / n if n else 0.0,
            "reopened": reopened,
            "escalations": len(esc),
            "retries": retries_n,
            "cost_model": model, "cost_tools": tools,
            "cost_retry": retry, "cost_human": human,
            "cost_total": total,
            "per_success": {
                "model": per(model), "tools": per(tools),
                "retry": per(retry), "human": per(human),
                "fully_loaded": per(total),
            },
            "yield_ratio": yield_ratio,
            "avg_context_growth": avg_growth,
            "tail": {"p50": pct(0.50), "p95": pct(0.95),
                     "max": costs[-1] if costs else 0.0,
                     "top5pct_share": tail_share},
            "per_model": per_model,
            "unpriced_models": sorted(self.unpriced_models),
            "business_value": value,
            "net_value": value - total,
            "budget_per_success": self.budget_per_success,
            "budget_breaches": breaches,
        }
