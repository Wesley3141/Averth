"""Regression tests for review pass 2 (2026-10-02): C1-C3, H1-H4, M1-M3.

Each test pins one audit fix so it cannot silently regress.
"""

import pytest

from averth import Tracker, BudgetBreach
from averth import pricing
from averth.report import report_text
from averth.insights import findings


def make_tracker(**kw):
    kw.setdefault("budget_per_success", None)
    return Tracker("test-agent", **kw)


# ---- C1: budget-breach hook fires on failed attempts too ----

def test_breach_hook_fires_on_failed_attempt():
    fired = []
    t = make_tracker(budget_per_success=1.00,
                     on_breach=lambda a, e: fired.append((a, e)))
    t.start_attempt(case_id="F-1")
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=False)  # failed runaway: must still fire
    assert len(fired) == 1
    attempt, breach = fired[0]
    assert isinstance(breach, BudgetBreach)
    assert attempt["case_id"] == "F-1"
    assert "failed" in str(breach)


def test_breach_raises_on_failed_attempt_without_callback():
    t = make_tracker(budget_per_success=1.00)
    t.start_attempt(case_id="F-1")
    t.log_tool_call("x", 5.00)
    with pytest.raises(BudgetBreach):
        t.end_attempt(success=False)


def test_pnl_breach_counts_include_failed_attempts():
    t = make_tracker(budget_per_success=1.00,
                     on_breach=lambda a, e: None)
    t.start_attempt(case_id="ok")
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=True)
    t.start_attempt(case_id="bad")
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=False)
    p = t.pnl()
    assert p["budget_breaches"] == 2
    assert p["budget_breaches_failed"] == 1
    assert p["budget_breach_spend"] == pytest.approx(10.00)
    ids = [f["id"] for f in findings(p)]
    assert "budget_breach" in ids


def test_no_breach_under_envelope_still_quiet():
    fired = []
    t = make_tracker(budget_per_success=100.00,
                     on_breach=lambda a, e: fired.append(e))
    t.start_attempt()
    t.log_tool_call("x", 5.00)
    t.end_attempt(success=False)
    assert fired == []
    assert t.pnl()["budget_breaches"] == 0


# ---- C2: versioned/dated price table, staleness, vintage stamping ----

def test_price_vintage_shape():
    v = pricing.price_vintage()
    assert set(v) == {"version", "updated", "age_days", "stale",
                      "stale_after_days"}
    assert v["version"] == pricing.PRICE_TABLE_VERSION
    assert v["updated"] == pricing.PRICE_TABLE_UPDATED
    # No hardcoded stale expectation: the table legitimately goes stale 90
    # days after PRICE_TABLE_UPDATED, so `stale is False` would be a date
    # time-bomb. Pin the semantics instead: stale iff older than the window,
    # and age never negative (future dates are rejected loudly).
    assert v["stale"] == (v["age_days"] > v["stale_after_days"])
    assert v["age_days"] >= 0
    # staleness_warning() agrees with the stale flag: None exactly when
    # fresh, a message exactly when stale.
    assert (pricing.staleness_warning() is None) == (not v["stale"])


def test_staleness_warning_fires_on_old_table(monkeypatch):
    monkeypatch.setattr(pricing, "PRICE_TABLE_UPDATED", "2020-01-01")
    v = pricing.price_vintage()
    assert v["stale"] is True
    w = pricing.staleness_warning()
    assert w is not None
    assert "2020-01-01" in w
    # and the stale warning lands in the text report
    t = make_tracker()
    t.start_attempt()
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    # refresh the tracker's vintage to the (mocked) stale table
    t.price_vintage = pricing.price_vintage()
    txt = report_text(t.pnl())
    assert "WARNING: pricing table is stale" in txt


def test_pnl_carries_price_vintage_and_report_stamps_it():
    t = make_tracker()
    t.start_attempt()
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION
    txt = report_text(p)
    assert "Price table: v%s" % pricing.PRICE_TABLE_VERSION in txt
    assert pricing.PRICE_TABLE_UPDATED in txt


def test_ledger_roundtrip_preserves_vintage(tmp_path):
    from averth import policy
    t = make_tracker()
    t.start_attempt(case_id="L-1")
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    path = str(tmp_path / "ledger.json")
    policy.export_ledger(t, path)
    ledger = policy.load_ledger(path)
    assert ledger["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION
    from averth.importers import common
    t2 = common.tracker_from_ledger(ledger)
    assert t2.pnl()["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION


# ---- C3 + M3: explicit labor rate, no silent default ----

def test_default_labor_rate_flagged_as_assumption():
    t = make_tracker()
    assert t.pnl()["human_rate_assumed"] is True
    assert t.pnl()["human_cost_per_min"] == pytest.approx(pricing.HUMAN_COST_PER_MIN)


def test_explicit_labor_rate_not_flagged():
    t = make_tracker(human_cost_per_min=0.50)
    p = t.pnl()
    assert p["human_rate_assumed"] is False
    assert p["human_cost_per_min"] == pytest.approx(0.50)


def test_explicit_zero_labor_rate_honored():  # M3
    t = make_tracker(human_cost_per_min=0.0)
    assert t.human_cost_per_min == 0.0
    assert t.pnl()["human_rate_assumed"] is False
    t.start_attempt()
    t.log_escalation(10.0, "review")
    a = t.end_attempt(success=True)
    assert a["human_cost"] == pytest.approx(0.0)


def test_negative_labor_rate_rejected():
    with pytest.raises(ValueError):
        make_tracker(human_cost_per_min=-1.0)


def test_report_labels_default_rate_as_assumption():
    t = make_tracker()
    t.start_attempt()
    t.log_escalation(10.0, "review")
    t.end_attempt(success=True)
    txt = report_text(t.pnl())
    assert "ASSUMPTION" in txt
    assert "human_cost_per_min" in txt


def test_human_dominance_finding_notes_assumption():
    t = make_tracker()
    for _ in range(3):
        t.start_attempt()
        t.log_escalation(60.0, "review")  # 60 * 1.17 = 70.20 human
        t.end_attempt(success=True)
    p = t.pnl()
    f = [x for x in findings(p) if x["id"] == "human_dominance"]
    assert f, "human_dominance should fire"
    assert "assumption" in f[0]["detail"].lower()


# ---- H2: default-priced tool spend is flagged ----

def test_default_tool_costs_flagged_in_pnl():
    t = make_tracker()
    t.start_attempt()
    t.log_tool_call("web_search")        # default estimate
    t.log_tool_call("custom_api", 0.02)  # explicit
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["tools_default_priced_spend"] == pytest.approx(0.005)
    assert p["tools_default_priced_names"] == ["web_search"]


def test_all_explicit_tool_costs_no_warning():
    t = make_tracker()
    t.start_attempt()
    t.log_tool_call("custom_api", 0.02)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["tools_default_priced_spend"] == pytest.approx(0.0)
    assert "built-in per-call" not in report_text(p)


def test_report_warns_on_estimated_tool_spend():
    t = make_tracker()
    t.start_attempt()
    t.log_tool_call("web_search")
    t.end_attempt(success=True)
    txt = report_text(t.pnl())
    assert "WARNING" in txt and "tool spend uses built-in" in txt


# ---- H3: cache discount rate surfaced ----

def test_cache_discount_in_pnl_and_report():
    t = make_tracker(cache_read_discount=0.25)
    t.start_attempt()
    t.log_model_call("anthropic", "claude-haiku-4-5", 1000, 100,
                     cached_input_tokens=500)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["cache_read_discount"] == pytest.approx(0.25)
    txt = report_text(p)
    assert "25%" in txt  # rate named, not silent


# ---- H1: importer docstring matches past-only branch semantics ----

def test_branch_retry_docstring_matches_code():
    from averth.importers import common
    doc = common.__doc__
    # the old wrong claim ("all of that branch's steps, past and future,
    # count as retry-path waste") must be gone; the corrected docstring
    # says the redo starts fresh and is not pre-tainted.
    assert "all of that branch's steps, past and future" not in doc
    assert "starts fresh" in doc
    # and the behavior really is past-only:
    t = make_tracker()
    t.start_attempt(case_id="B-1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="b1")
    t.log_retry("fan-out dead", branch="b1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100, branch="b1")  # redo
    a = t.end_attempt(success=True)
    waste = [s for s in a["steps"] if s["retry"]]
    assert len(waste) == 1  # only the pre-retry step, not the redo


# ---- M1: single source of truth for fallback price ----

def test_fallback_price_matches_pricing_estimate():
    from averth.importers import common
    assert common.FALLBACK_PRICE == pricing.ESTIMATED_MODEL_PRICES
