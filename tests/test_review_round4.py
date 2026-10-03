"""Regression tests for Review Pass 2 HIGH findings (2026-10-03).

Each test pins one fixed HIGH finding so it can never regress silently:
- budget_per_success=0 falsy trap (tracker end_attempt + pnl + report)
- cache_read_discount unvalidated at init (NaN / negative / >1 / string)
- fractional float token counts silently truncated
- export_ledger emitting invalid-JSON NaN literals
- "no customer data" guarantee vs verbatim free-text export
- TOP FINDING headline missing the labor-assumption marker
- importer fallback path ignoring the cache discount
- a lone "start" event fabricating a failed attempt
"""

import json
import math

import pytest

from averth.tracker import Tracker, BudgetBreach
from averth import pricing
from averth.policy import export_ledger
from averth.report import report_text
from averth.importers.common import events_to_tracker


def _tiny_model_call(t):
    t.start_attempt()
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 500)
    t.end_attempt(success=False)


# --- budget_per_success=0 is a live "no spend allowed" value, not "disabled" ---

def test_budget_zero_hook_fires_on_any_spend():
    fired = []
    t = Tracker("a", budget_per_success=0.0,
                on_breach=lambda a, e: fired.append(e))
    _tiny_model_call(t)
    assert len(fired) == 1
    assert "(failed attempt)" in str(fired[0])


def test_budget_zero_hook_silent_at_exactly_zero():
    fired = []
    t = Tracker("a", budget_per_success=0.0,
                on_breach=lambda a, e: fired.append(e))
    t.start_attempt()
    t.end_attempt(success=True)  # $0 cost: 0 > 0 is False
    assert fired == []
    assert t.pnl()["budget_breaches"] == 0


def test_budget_zero_pnl_counts_breaches():
    t = Tracker("a", budget_per_success=0.0,
                on_breach=lambda a, e: None)
    _tiny_model_call(t)
    p = t.pnl()
    assert p["budget_breaches"] == 1
    assert p["budget_breaches_failed"] == 1
    assert p["budget_breach_spend"] > 0


def test_budget_zero_raises_without_callback():
    t = Tracker("a", budget_per_success=0.0)
    t.start_attempt()
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 500)
    with pytest.raises(BudgetBreach):
        t.end_attempt(success=False)


def test_budget_negative_rejected_at_init():
    with pytest.raises(ValueError):
        Tracker("a", budget_per_success=-1.0)


def test_budget_zero_report_shows_budget_line():
    t = Tracker("a", budget_per_success=0.0,
                on_breach=lambda a, e: None)
    _tiny_model_call(t)
    txt = report_text(t.pnl())
    assert "Budget: $0.00/success, breaches: 1" in txt


# --- cache_read_discount validated at init ---

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.5, 2.0,
                                 "0.1", object()])
def test_cache_read_discount_bad_values_rejected(bad):
    with pytest.raises((ValueError, TypeError)):
        Tracker("a", cache_read_discount=bad)


@pytest.mark.parametrize("good", [0.0, 0.1, 0.5, 1.0])
def test_cache_read_discount_boundaries_accepted(good):
    t = Tracker("a", cache_read_discount=good)
    assert t.cache_read_discount == pytest.approx(good)


def test_cache_read_discount_math_on_custom_value():
    t = Tracker("a", cache_read_discount=0.5)
    t.start_attempt()
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 0,
                     cached_input_tokens=1000)
    a = t.end_attempt(success=True)
    # cached 1000 tokens at 50% of the $3/1M input price
    assert a["model"] == pytest.approx(1000 / 1e6 * 3.0 * 0.5)
    assert a["cache_savings"] == pytest.approx(1000 / 1e6 * 3.0 * 0.5)


def test_cache_read_discount_default_unchanged():
    assert Tracker("a").cache_read_discount == pricing.CACHE_READ_DISCOUNT


# --- fractional float token counts rejected, not truncated ---

def test_fractional_tokens_rejected():
    t = Tracker("a")
    t.start_attempt()
    with pytest.raises(ValueError):
        t.log_model_call("anthropic", "claude-sonnet-4-5", 100.9, 5)


def test_integral_float_tokens_accepted():
    t = Tracker("a")
    t.start_attempt()
    t.log_model_call("anthropic", "claude-sonnet-4-5", 100.0, 5)
    a = t.end_attempt(success=True)
    assert a["total_tokens"] == 105


# --- export_ledger refuses NaN loudly ---

def test_export_ledger_nan_raises(tmp_path):
    t = Tracker("a")
    _tiny_model_call(t)
    t.attempts[0]["model"] = float("nan")  # injected past the API validators
    with pytest.raises(ValueError):
        export_ledger(t, str(tmp_path / "ledger.json"))


def test_export_ledger_roundtrip_still_valid_json(tmp_path):
    t = Tracker("a")
    _tiny_model_call(t)
    p = export_ledger(t, str(tmp_path / "ledger.json"))
    with open(p) as f:
        ledger = json.load(f)
    assert ledger["attempts"][0]["model"] > 0
    assert math.isfinite(ledger["attempts"][0]["model"])


# --- ledger exports caller free text verbatim (documented, not guaranteed clean) ---

def test_export_ledger_preserves_free_text_verbatim(tmp_path):
    t = Tracker("a")
    t.start_attempt(case_id="case-42 ACME Corp")
    t.log_retry(reason="customer PII would sit here verbatim")
    t.end_attempt(success=False)
    p = export_ledger(t, str(tmp_path / "ledger.json"))
    with open(p) as f:
        ledger = json.load(f)
    events = ledger["attempts"][0]["events"]
    assert any("customer PII would sit here verbatim" in str(e) for e in events)
    assert ledger["attempts"][0]["case_id"] == "case-42 ACME Corp"


# --- TOP FINDING carries the labor-assumption marker on its own line ---

def _human_dominant_tracker(**kw):
    t = Tracker("a", **kw)
    t.start_attempt()
    t.log_model_call("anthropic", "claude-sonnet-4-5", 100, 50)
    t.log_escalation(60, reason="review")
    t.end_attempt(success=True)
    return t


def test_top_finding_marks_assumed_labor_rate():
    txt = report_text(_human_dominant_tracker().pnl())
    top_lines = [ln for ln in txt.splitlines() if ln.startswith("TOP FINDING")]
    assert len(top_lines) == 1
    assert "Human review is" in top_lines[0]
    detail = txt.splitlines()[txt.splitlines().index(top_lines[0]) + 1]
    assert "ASSUMPTION" in detail


def test_top_finding_no_marker_with_explicit_rate():
    txt = report_text(
        _human_dominant_tracker(human_cost_per_min=1.17).pnl())
    assert "ASSUMPTION" not in txt


# --- importer fallback path applies the cache discount ---

def test_importer_fallback_applies_cache_discount():
    events = [
        {"type": "model", "case_id": "c", "model": "mystery-1",
         "provider": "unknown", "input_tokens": 10000,
         "output_tokens": 1000, "cached_input_tokens": 10000},
        {"type": "end", "case_id": "c", "success": True},
    ]
    t = events_to_tracker("imp", events)
    a = t.attempts[0]
    pin, pout = pricing.ESTIMATED_MODEL_PRICES
    d = pricing.CACHE_READ_DISCOUNT
    expected = 10000 / 1e6 * pin * d + 1000 / 1e6 * pout
    assert a["model"] == pytest.approx(expected)
    assert a["cache_savings"] == pytest.approx(10000 / 1e6 * pin * (1.0 - d))
    assert "unknown:mystery-1" in t.unpriced_models


def test_importer_fallback_clamps_cached_above_input():
    events = [
        {"type": "model", "case_id": "c", "model": "mystery-1",
         "provider": "unknown", "input_tokens": 100,
         "output_tokens": 10, "cached_input_tokens": 99999},
        {"type": "end", "case_id": "c", "success": True},
    ]
    t = events_to_tracker("imp", events)
    a = t.attempts[0]
    assert a["cached_tokens"] == 100  # clamped, no phantom tokens


# --- lone "start" creates nothing; [start, end] still closes a real attempt ---

def test_lone_start_creates_no_attempt():
    t = events_to_tracker("imp", [{"type": "start", "case_id": "c"}])
    assert t.attempts == []
    assert t.pnl()["attempts"] == 0


def test_start_then_end_closes_real_attempt():
    t = events_to_tracker("imp", [
        {"type": "start", "case_id": "c"},
        {"type": "end", "case_id": "c", "success": True},
    ])
    assert len(t.attempts) == 1
    assert t.attempts[0]["success"] is True


def test_start_after_end_creates_no_phantom():
    t = events_to_tracker("imp", [
        {"type": "model", "case_id": "c", "model": "mystery-1",
         "provider": "unknown", "input_tokens": 10, "output_tokens": 5},
        {"type": "end", "case_id": "c", "success": True},
        {"type": "start", "case_id": "c"},
    ])
    assert len(t.attempts) == 1
    assert t.attempts[0]["success"] is True


def test_start_then_model_still_auto_starts():
    t = events_to_tracker("imp", [
        {"type": "start", "case_id": "c"},
        {"type": "model", "case_id": "c", "model": "mystery-1",
         "provider": "unknown", "input_tokens": 10, "output_tokens": 5},
        {"type": "end", "case_id": "c", "success": True},
    ])
    assert len(t.attempts) == 1
    assert t.attempts[0]["model"] > 0
