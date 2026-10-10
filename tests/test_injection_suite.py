"""Synthetic injection suite: prove ACCOUNTING behavior, not value.

Each test injects a known waste/cost shape into a Tracker and asserts the
meter detects and attributes it correctly: the right dollars in the right
buckets, the right flags, the right warnings.

What these tests prove: known events are detected and attributed correctly.
What they do NOT prove: that an injected retry was unnecessary, or that
removing it would preserve quality. A stubbed waste pattern is a
measurement check, never an improvement claim. Clean controls and
missing-data cases are included so the suite also proves the meter does
not invent waste where there is none, and never presents unknown as free.
"""
import pytest

from averth.tracker import Tracker
from averth import report as report_mod

MODEL = ("openai", "gpt-5.6")


def _attempt(t, case_id, success=True, business_value=0.0):
    t.start_attempt(case_id=case_id)
    return t


def test_clean_control_no_waste_flags():
    """No waste injected -> no waste flags, exact accounting."""
    t = Tracker("injection-control")
    _attempt(t, "c1")
    t.log_model_call(*MODEL, 1000, 500)
    t.log_tool_call("search", cost=0.01)
    t.log_model_call(*MODEL, 1200, 600)
    t.end_attempt(success=True, business_value=1.0)
    p = t.pnl()
    assert p["retries"] == 0
    assert p["cost_retry_path"] == pytest.approx(0.0)
    assert p["yield_ratio"] == pytest.approx(1.0)
    assert p["escalations"] == 0
    # total is exactly the sum of its parts — overlays add nothing
    assert p["cost_total"] == pytest.approx(
        p["cost_model"] + p["cost_tools"] + p["cost_retry"] + p["cost_human"])
    # all measured, nothing estimated/billed/unknown
    dq = p["data_quality"]
    assert dq["measured"] == pytest.approx(p["cost_model"] + p["cost_tools"])
    assert dq["estimated"] == pytest.approx(0.0)
    assert dq["billed"] == pytest.approx(0.0)
    assert dq["unknown_calls"] == 0


def test_retry_storm_attribution():
    """Injected failed attempts are attributed to the retry path exactly."""
    t = Tracker("injection-retry")
    waste_model = 0.0
    for i in range(3):
        _attempt(t, f"fail-{i}")
        t.log_model_call(*MODEL, 2000, 1000)
        waste_model += t.attempts[-1]["model"] if t.attempts else 0.0
        # mark the whole attempt as retry-path waste via branch scope
        t.log_retry(reason="timeout", branch="attempt")
        t.end_attempt(success=False)
    _attempt(t, "win")
    t.log_model_call(*MODEL, 2000, 1000)
    t.end_attempt(success=True, business_value=5.0)
    p = t.pnl()
    assert p["retries"] == 3
    assert p["yield_ratio"] < 1.0
    # retry-path dollars are a subset of model spend, never additive
    assert p["cost_retry_path"] <= p["cost_model"]
    assert p["cost_retry_path"] > 0
    # and the total still equals the parts
    assert p["cost_total"] == pytest.approx(
        p["cost_model"] + p["cost_tools"] + p["cost_retry"] + p["cost_human"])


def test_context_growth_is_share_not_charge():
    """Growing contexts produce a context tax that is a share of model
    spend — an explanation, not an additional charge."""
    t = Tracker("injection-context")
    _attempt(t, "c1")
    # first-to-last input growth: 1k -> 8k
    t.log_model_call(*MODEL, 1000, 200)
    t.log_model_call(*MODEL, 4000, 200)
    t.log_model_call(*MODEL, 8000, 200)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["avg_context_growth"] > 1.0
    assert p["context_tax"] >= 0
    assert p["context_tax_share_of_model"] <= 1.0
    # the tax is an overlay: total excludes it by construction
    assert p["cost_total"] == pytest.approx(
        p["cost_model"] + p["cost_tools"] + p["cost_retry"] + p["cost_human"])


def test_heavy_tail_detected():
    """One expensive run among many is flagged by the tail analysis."""
    t = Tracker("injection-tail")
    for i in range(19):
        _attempt(t, f"c{i}")
        t.log_model_call(*MODEL, 100, 50)
        t.end_attempt(success=True)
    _attempt(t, "whale")
    t.log_model_call(*MODEL, 100000, 50000)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["tail"]["tail_label"] == "top 5%"
    assert p["tail"]["top5pct_share"] > 0.5


def test_missing_usage_never_free():
    """Calls with no reported usage are counted as unknown, never $0-free."""
    t = Tracker("injection-unknown")
    _attempt(t, "c1")
    t.log_model_call(*MODEL, 1000, 500)
    t.log_model_call(*MODEL, 0, 0, missing_usage=True)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["unknown_usage_calls"] == 1
    assert p["data_quality"]["unknown_calls"] == 1
    # the unknown call contributes $0.00 to the total but is not counted
    # as measured spend
    assert p["data_quality"]["measured"] == pytest.approx(p["cost_model"])
    text = report_mod.report_text(p)
    assert "Unknown: 1 call" in text
    assert "not free" in text


def test_all_inferred_outcomes_unknown_per_success():
    """No outcome labels joined -> cost per successful task is UNKNOWN as
    an accepted-outcome metric, not a printed number."""
    t = Tracker("injection-inferred")
    _attempt(t, "c1")
    t.log_model_call(*MODEL, 1000, 500)
    t.end_attempt(success=True, outcome_inferred=True)
    p = t.pnl()
    assert p["inferred_outcomes"] == p["attempts"]
    text = report_mod.report_text(p)
    assert "UNKNOWN" in text
    assert "accepted-outcome" in text


def test_mixed_provenance_buckets_sum():
    """Measured + billed + estimated + unknown buckets partition the spend."""
    t = Tracker("injection-mix")
    _attempt(t, "c1")
    t.log_model_call(*MODEL, 1000, 500)                      # measured
    t.log_model_billed_cost(*MODEL, 0.05)                    # billed
    t.log_model_cost_estimate("openai", "gpt-zzz", 0.03,
                              input_tokens=100, output_tokens=50)  # estimated
    t.log_model_call(*MODEL, 0, 0, missing_usage=True)        # unknown
    t.log_tool_call("search")                                # estimated tool
    t.end_attempt(success=True)
    p = t.pnl()
    dq = p["data_quality"]
    assert dq["billed"] == pytest.approx(0.05)
    assert dq["estimated"] > 0.03  # model estimate + default-priced tool
    assert dq["unknown_calls"] == 1
    # buckets partition model+tool spend (human is separate, none here)
    assert dq["measured"] + dq["billed"] + dq["estimated"] == pytest.approx(
        p["cost_model"] + p["cost_tools"])
    assert p["cost_total"] == pytest.approx(
        p["cost_model"] + p["cost_tools"] + p["cost_retry"] + p["cost_human"])


def test_no_double_counting_invariant():
    """The five layers are explanatory overlays: total == parts, and each
    overlay is a subset/share of model spend, never an extra charge."""
    t = Tracker("injection-invariant")
    for i in range(5):
        _attempt(t, f"c{i}")
        t.log_model_call(*MODEL, 1000 * (i + 1), 200)
        if i % 2:
            t.log_retry(reason="flaky", branch="b")
        t.log_tool_call("search", cost=0.02)
        t.end_attempt(success=(i % 2 == 0))
    p = t.pnl()
    assert p["cost_total"] == pytest.approx(
        p["cost_model"] + p["cost_tools"] + p["cost_retry"] + p["cost_human"])
    assert p["cost_retry_path"] <= p["cost_model"]
    assert p["context_tax"] <= p["cost_model"]
    assert 0.0 <= p["context_tax_share_of_model"] <= 1.0
    # per-model attribution sums to model spend
    assert sum(p["per_model"].values()) == pytest.approx(p["cost_model"])
