"""Regression tests for review round 5 (2026-10-02): tracker.py + insights.py.

- H-PNL1: price_vintage is a read-through property (fresh on every access),
  not a construction-time stamp; explicit assignment still pins an override
  (ledger rehydration path); legacy ledgers keep "vintage unknown".
- Hostile H1: huge ints raise ValueError, never leak raw OverflowError.
- Hostile H2: zero-token first step zeroes context_tax (no contradiction
  with the guarded context_growth).
- pnl(): missing per_model key degrades gracefully (KeyError fix).
- insights C1: low_yield dollars == cost_retry_path (includes
  extra_model_cost), consistent with retry_waste on the same ledger.
- insights H1: reopened-failed shape never claims "booked as success";
  reopened-success shape keeps the original text.
- Pluralization: "1 failed run" / "2 failed runs".
"""

import pytest

from averth import pricing
from averth.tracker import Tracker
from averth.insights import findings
from averth.importers import common


def _tracker():
    return Tracker("round5")


# ---- H-PNL1: price_vintage is live ----

def test_price_vintage_reads_current_table_not_construction_time(monkeypatch):
    t = _tracker()
    before = t.pnl()["price_vintage"]
    assert before["updated"] == pricing.PRICE_TABLE_UPDATED
    # Simulate the table aging out AFTER the tracker was constructed.
    monkeypatch.setattr(pricing, "PRICE_TABLE_UPDATED", "2020-01-01")
    v = t.pnl()["price_vintage"]
    assert v["updated"] == "2020-01-01"
    assert v["stale"] is True
    assert v["age_days"] > pricing.PRICE_TABLE_STALE_AFTER_DAYS


def test_price_vintage_monkeypatched_price_vintage_fn(monkeypatch):
    # Alternative live-read check: replace pricing.price_vintage itself.
    t = _tracker()
    fake = {"version": 99, "updated": "2020-01-01", "age_days": 999,
            "stale": True, "stale_after_days": 90}
    monkeypatch.setattr(pricing, "price_vintage", lambda: fake)
    assert t.pnl()["price_vintage"] is fake


def test_price_vintage_explicit_assignment_pins_override(monkeypatch):
    t = _tracker()
    pinned = {"version": 1, "updated": "2020-01-01", "age_days": 999,
              "stale": True, "stale_after_days": 90}
    t.price_vintage = pinned  # what tracker_from_ledger does
    monkeypatch.setattr(pricing, "PRICE_TABLE_UPDATED", "2026-10-02")
    assert t.pnl()["price_vintage"] is pinned


def test_ledger_roundtrip_preserves_vintage(tmp_path):
    from averth import policy
    t = _tracker()
    t.start_attempt()
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    # dict path: ledger_from_tracker -> tracker_from_ledger
    ledger = common.ledger_from_tracker(t)
    assert ledger["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION
    t2 = common.tracker_from_ledger(ledger)
    assert t2.pnl()["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION
    # file path: export_ledger -> load_ledger -> tracker_from_ledger
    path = str(tmp_path / "ledger.json")
    policy.export_ledger(t, path)
    file_ledger = policy.load_ledger(path)
    assert file_ledger["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION
    t3 = common.tracker_from_ledger(file_ledger)
    assert t3.pnl()["price_vintage"]["version"] == pricing.PRICE_TABLE_VERSION


def test_legacy_ledger_without_vintage_stays_unknown():
    legacy = {"agent": "old", "attempts": []}
    t = common.tracker_from_ledger(legacy)
    assert t.pnl()["price_vintage"] is None  # "vintage unknown", not fresh


# ---- Hostile H1: huge ints -> ValueError, never OverflowError ----

def test_huge_int_token_count_raises_valueerror():
    t = _tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5.6-mini", 10**400, 10)


def test_inf_and_nan_token_counts_still_valueerror():
    t = _tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5.6-mini", float("inf"), 10)
    with pytest.raises(ValueError):
        t.log_model_call("openai", "gpt-5.6-mini", float("nan"), 10)


def test_huge_int_cost_raises_valueerror_not_overflow():
    t = _tracker()
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_tool_call("browser_action", 10**400)


def test_over_cap_int_still_rejected_as_implausible():
    # Just over the 1e12 cap: the documented ValueError, not OverflowError.
    t = _tracker()
    t.start_attempt()
    with pytest.raises(ValueError, match="implausibly large"):
        t.log_model_call("openai", "gpt-5.6-mini", 10**12 + 1, 10)


# ---- Hostile H2: zero-base context tax guard ----

def test_zero_token_first_step_zeroes_context_tax():
    t = _tracker()
    t.start_attempt()
    t.log_model_call("openai", "gpt-5.6-mini", 0, 10)      # streaming, no usage
    t.log_model_call("openai", "gpt-5.6-mini", 1000, 10)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["context_tax"] == 0.0
    # the guarded growth lens agrees: no compounding reported either
    assert t.attempts[0]["context_growth"] == 1.0
    # and the second step still priced normally
    assert p["cost_model"] > 0


def test_nonzero_base_prices_context_tax_normally():
    t = _tracker()
    t.start_attempt()
    t.log_model_call("openai", "gpt-5.6-mini", 100, 10)
    t.log_model_call("openai", "gpt-5.6-mini", 1000, 10)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["context_tax"] > 0


# ---- pnl(): missing per_model degrades gracefully ----

def test_pnl_survives_attempt_missing_per_model():
    t = _tracker()
    t.start_attempt()
    t.log_tool_call("x", 1.00)
    t.end_attempt(success=True)
    del t.attempts[0]["per_model"]  # pre-hardening ledger shape
    p = t.pnl()  # must not raise KeyError
    assert p["cost_total"] == pytest.approx(1.0)
    assert p["per_model"] == {}


# ---- insights C1: low_yield dollars == cost_retry_path ----

def test_low_yield_dollars_include_extra_model_cost():
    t = _tracker()
    t.start_attempt()
    t.log_model_call("openai", "gpt-5.6-mini", 5000, 100, branch="x")
    t.log_retry("bad schema", extra_model_cost=3.0, branch="x")
    t.log_model_call("openai", "gpt-5.6-mini", 5000, 100)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["cost_retry_path"] == pytest.approx(
        p["cost_model"] + p["cost_retry"] - p["cost_model_terminal"])
    fs = {f["id"]: f for f in findings(p)}
    assert "low_yield" in fs
    # the fix: dollars are the full off-terminal-path model spend
    assert fs["low_yield"]["dollars"] == pytest.approx(p["cost_retry_path"])
    assert fs["low_yield"]["dollars"] > p["cost_model"] - p["cost_model_terminal"]
    # no longer contradicts retry_waste on the same ledger
    assert "retry_waste" in fs
    assert fs["retry_waste"]["dollars"] == pytest.approx(
        fs["low_yield"]["dollars"] + p["cost_retry_tools"])


# ---- insights H1: reopened text branches on success ----

def _reopened_tracker(redo_succeeds):
    t = Tracker("reopened")
    t.start_attempt()
    t.log_tool_call("x", 2.00)
    t.end_attempt(success=True)
    t.start_attempt()
    t.log_tool_call("y", 8.00)
    t.end_attempt(success=redo_succeeds, reopened=True)
    return t


def test_reopened_failed_shape_never_claims_booked_as_success():
    t = _reopened_tracker(redo_succeeds=False)
    p = t.pnl()
    assert p["reopened"] == 1
    assert p["reopened_successful"] == 0
    fs = {f["id"]: f for f in findings(p)}
    assert "reopened" in fs
    # the false sentence from the review must be gone; the honest text
    # explicitly negates the success booking instead of claiming it
    assert "Their first-pass cost was booked as success" \
        not in fs["reopened"]["detail"]
    assert "0 accepted outcomes" not in fs["reopened"]["detail"]
    assert "nothing was booked as success" in fs["reopened"]["detail"]


def test_reopened_success_shape_keeps_original_text():
    t = _reopened_tracker(redo_succeeds=True)
    p = t.pnl()
    assert p["reopened_successful"] == 1
    fs = {f["id"]: f for f in findings(p)}
    assert "reopened" in fs
    assert "booked as success" in fs["reopened"]["detail"]
    assert "1 accepted outcome was reopened" in fs["reopened"]["detail"]


# ---- insights H2: unpriced_spend provenance is honest ----

def test_unpriced_spend_detail_covers_caller_supplied_cost():
    t = _tracker()
    t.start_attempt()
    # direct API user: takes the dollar cost directly, not the fallback
    t.log_model_cost_estimate("acme", "model-z", 2.50, 1000, 100)
    t.end_attempt(success=True)
    p = t.pnl()
    fs = {f["id"]: f for f in findings(p)}
    assert "unpriced_spend" in fs
    detail = fs["unpriced_spend"]["detail"]
    assert "caller-supplied" in detail
    assert "fallback estimate" in detail


# ---- pluralization ----

def _breach_detail(n_failed):
    t = Tracker("plural", budget_per_success=1.00,
                on_breach=lambda a, b: None)
    for _ in range(n_failed):
        t.start_attempt()
        t.log_tool_call("x", 5.00)
        t.end_attempt(success=False)
    fs = {f["id"]: f for f in findings(t.pnl())}
    return fs["budget_breach"]["detail"]


def test_pluralization_one_failed_run():
    d = _breach_detail(1)
    assert "1 failed run" in d
    assert "1 failed runs" not in d


def test_pluralization_two_failed_runs():
    d = _breach_detail(2)
    assert "2 failed runs" in d


def test_pluralization_retry_finding():
    t = _tracker()
    t.start_attempt()
    t.log_model_call("openai", "gpt-5.6-mini", 5000, 100)
    # extra_model_cost lifts retry spend above the $1 materiality floor
    t.log_retry("timeout", extra_model_cost=3.0)
    t.log_model_call("openai", "gpt-5.6-mini", 5000, 100)
    t.end_attempt(success=True)
    fs = {f["id"]: f for f in findings(t.pnl())}
    assert "retry_waste" in fs
    assert "(1 retry)" in fs["retry_waste"]["detail"]
    assert "1 retries" not in fs["retry_waste"]["detail"]
