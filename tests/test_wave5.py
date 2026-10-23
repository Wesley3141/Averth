"""Wave 5 regression tests.

(a) "-$0" display artifact.
(b) JSONL outcome-unknown support (explicit end flag + auto-end).
(c) Token provenance: priced spend on estimated tokens leaves the
    Priced bucket for Estimated, including across the ledger round-trip.
(d) Context tax on fallback-priced runs: n/a, not $0.00.
(e) Retry finding: never fires on 0 retries; when it fires, its detail
    decomposes into the waste-lens figure plus retry-path tool spend.
(f) Price table v7 additions, pinned to the vendor pages they were
    verified from on 2026-10-23.
"""

import os
import tempfile

import pytest

from averth._money import dollars
from averth import pricing
from averth.tracker import Tracker
from averth.importers import common, jsonl
from averth.report import report_text
from averth.insights import findings


# ---- (a) "-$0" -------------------------------------------------------

def test_tiny_negative_renders_zero_not_minus_zero():
    assert dollars(-1e-9) == "$0"
    assert dollars(-0.0000004) == "$0"
    # Exact zero keeps the standard cent rendering.
    assert dollars(0.0) == "$0.00"


def test_real_negative_still_signed():
    assert dollars(-0.005) == "-$0.005"
    assert dollars(-2.5) == "-$2.50"


# ---- (b) JSONL outcome-unknown ---------------------------------------

def _load_jsonl(text):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                     delete=False) as tmp:
        tmp.write(text)
        path = tmp.name
    try:
        return jsonl.load_jsonl(path)
    finally:
        os.unlink(path)


def test_jsonl_explicit_outcome_unknown_end():
    ledger = _load_jsonl(
        '{"type": "model", "case_id": "c1", "model": "gpt-5-nano",'
        ' "input_tokens": 1000, "output_tokens": 100}\n'
        '{"type": "end", "case_id": "c1", "outcome_unknown": true}\n')
    tracker = common.tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["unknown_outcome"] == 1
    assert p["successes"] == 0
    assert p["cost_failed"] == 0.0
    assert p["cost_unknown_outcome"] > 0
    assert tracker.attempts[0]["success"] is False


def test_jsonl_auto_end_is_unknown_not_failed():
    ledger = _load_jsonl(
        '{"type": "model", "case_id": "c1", "model": "gpt-5-nano",'
        ' "input_tokens": 1000, "output_tokens": 100}\n')
    tracker = common.tracker_from_ledger(ledger)
    p = tracker.pnl()
    assert p["unknown_outcome"] == 1
    assert p["cost_failed"] == 0.0
    # No known outcome: yield is the unknown-only n/a case in reports,
    # and failed share must not read 100%.
    assert p["failed_spend_share"] == 0.0


def test_jsonl_unknown_plus_success_rejected():
    with pytest.raises(ValueError):
        _load_jsonl(
            '{"type": "model", "case_id": "c1", "model": "gpt-5-nano",'
            ' "input_tokens": 1000, "output_tokens": 100}\n'
            '{"type": "end", "case_id": "c1", "success": true,'
            ' "outcome_unknown": true}\n')


def test_events_to_tracker_default_auto_end_still_failed():
    # Other importers keep the historical failed auto-end; only JSONL
    # opts into unknown auto-end.
    tracker = common.events_to_tracker("t", [
        {"type": "model", "case_id": "c1", "model": "gpt-5-nano",
         "input_tokens": 1000, "output_tokens": 100}])
    p = tracker.pnl()
    assert p["unknown_outcome"] == 0
    assert p["cost_failed"] > 0


def test_end_attempt_unknown_forces_success_false():
    t = Tracker("t")
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 100)
    a = t.end_attempt(success=True, outcome_unknown=True)
    assert a["success"] is False
    assert a["outcome_unknown"] is True


# ---- (c) token provenance --------------------------------------------

def test_estimated_tokens_leave_priced_bucket():
    t = Tracker("t")
    t.start_attempt(case_id="c1")
    # Recorded tokens: stay Priced.
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0)
    t.end_attempt(success=True)
    t.start_attempt(case_id="c2")
    # Estimated tokens at the same vendor price: move to Estimated.
    t.log_model_call("openai", "gpt-5-nano", 1_000_000, 0,
                     tokens_estimated=True)
    t.end_attempt(success=True)
    p = t.pnl()
    # gpt-5-nano is $0.05 input per 1M in v7's table lineage (unchanged
    # entry); one recorded call and one estimated call at the same price.
    assert p["estimated_token_spend"] == pytest.approx(0.05)
    # Priced bucket holds only the recorded call's model spend.
    assert p["data_quality"]["measured"] == pytest.approx(0.05)
    assert p["data_quality"]["estimated"] == pytest.approx(0.05)


def test_estimated_tokens_survive_ledger_round_trip():
    tracker = common.events_to_tracker("t", [
        {"type": "model", "case_id": "c1", "model": "gpt-5-nano",
         "input_tokens": 1_000_000, "output_tokens": 0,
         "tokens_estimated": True},
        {"type": "end", "case_id": "c1", "success": True}])
    ledger = common.ledger_from_tracker(tracker)
    t2 = common.tracker_from_ledger(ledger)
    p = t2.pnl()
    assert p["estimated_token_spend"] == pytest.approx(0.05)
    assert p["data_quality"]["measured"] == pytest.approx(0.0)


# ---- (d) context tax --------------------------------------------------

def test_fallback_context_tax_is_incomplete_not_free():
    t = Tracker("t")
    t.start_attempt(case_id="c1")
    # Fallback-priced calls record in_price 0.0; growth is real.
    t.log_model_cost_estimate("unknown", "mystery-model", 1.0,
                              input_tokens=1000, output_tokens=10)
    t.log_model_cost_estimate("unknown", "mystery-model", 2.0,
                              input_tokens=10000, output_tokens=10)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["context_tax"] == 0.0
    assert p["context_tax_incomplete"] is True
    assert p["avg_context_growth"] == pytest.approx(10.0)
    text = report_text(p)
    assert "context tax n/a" in text
    assert "context tax $0.00" not in text


def test_priced_context_tax_is_complete():
    t = Tracker("t")
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5-nano", 1000, 10)
    t.log_model_call("openai", "gpt-5-nano", 10000, 10)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["context_tax"] > 0
    assert p["context_tax_incomplete"] is False


# ---- (e) retry finding -----------------------------------------------

def _failed_no_retry_tracker():
    t = Tracker("t")
    for i in range(20):
        t.start_attempt(case_id="c%d" % i)
        t.log_model_call("openai", "gpt-5-nano", 2_000_000, 0)
        t.end_attempt(success=False)
    return t


def test_retry_finding_does_not_fire_on_zero_retries():
    p = _failed_no_retry_tracker().pnl()
    assert p["retries"] == 0
    ids = [f["id"] for f in findings(p)]
    assert "retry_waste" not in ids
    # Failed spend still has its own finding.
    assert "failed_spend" in ids


def test_retry_finding_decomposes_to_waste_lens():
    t = Tracker("t")
    t.start_attempt(case_id="ok")
    t.log_model_call("openai", "gpt-5-nano", 100_000_000, 0)
    t.log_retry("boom")
    t.log_model_call("openai", "gpt-5-nano", 100_000_000, 0)
    t.log_tool_call("bash", branch=None)
    t.end_attempt(success=True)
    # A failed attempt with a retry, so failed spend is in the mix too.
    t.start_attempt(case_id="bad")
    t.log_model_call("openai", "gpt-5-nano", 100_000_000, 0)
    t.log_retry("boom")
    t.log_model_call("openai", "gpt-5-nano", 100_000_000, 0)
    t.end_attempt(success=False)
    p = t.pnl()
    f = next(f for f in findings(p) if f["id"] == "retry_waste")
    # The detail names the waste-lens model figure and the tool figure,
    # and the three components sum to the waste-lens figure.
    assert p["cost_retry_path"] == pytest.approx(
        p["cost_retry_path_failed"] + p["cost_retry_path_success"]
        + p["cost_retry_path_unknown"])
    assert "$%.2f" % p["cost_retry_path"] in f["detail"]
    assert "$%.2f" % p["cost_retry_tools"] in f["detail"]


# ---- (f) price table v7 ----------------------------------------------

def test_price_table_v7_version_and_date():
    assert pricing.PRICE_TABLE_VERSION == 7
    assert pricing.PRICE_TABLE_UPDATED == "2026-10-23"


@pytest.mark.parametrize("key, pin, pout", [
    ("openai:gpt-4o-2024-05-13", 2.50, 10.00),
    ("openai:gpt-4o-mini-2024-07-18", 0.15, 0.60),
    ("openai:gpt-4.1", 2.00, 8.00),
    ("openai:gpt-4.1-mini", 0.40, 1.60),
    ("openai:gpt-5.2", 1.75, 14.00),
    ("openai:gpt-5.2-high", 1.75, 14.00),
    ("openai:gpt-5-mini", 0.25, 2.00),
    ("openai:o1-mini", 1.10, 4.40),
    ("openai:o1-mini-2024-09-12", 1.10, 4.40),
    ("anthropic:claude-opus-4-5", 5.00, 25.00),
    ("anthropic:claude-4.5-opus-high", 5.00, 25.00),
    ("anthropic:claude-4.5-haiku-high", 1.00, 5.00),
    ("unknown:glm-5", 1.00, 3.20),
    ("unknown:glm-5-high", 1.00, 3.20),
])
def test_wave5_prices_pinned(key, pin, pout):
    provider, model = key.split(":", 1)
    assert pricing.model_call_cost(provider, model, 1_000_000, 1_000_000) \
        == pytest.approx(pin + pout)


@pytest.mark.parametrize("key", [
    "deepseek:deepseek-chat",
    "google:gemini-1.5-pro-002",
    "unknown:qwen-2.5-72b-instruct",
    "minimax:minimax-m2.5-high",
])
def test_unverified_keys_stay_unpriced(key):
    provider, model = key.split(":", 1)
    with pytest.raises(KeyError):
        pricing.model_call_cost(provider, model, 1000, 100)


def test_wave5_cached_rates():
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-4o-2024-05-13"] == 1.25
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-4o-mini-2024-07-18"] == 0.075
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-4.1"] == 0.50
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-4.1-mini"] == 0.10
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-5.2"] == 0.175
    assert pricing.MODEL_CACHED_PRICES["openai:gpt-5-mini"] == 0.025
    assert pricing.MODEL_CACHED_PRICES["openai:o1-mini"] == 0.55
    assert pricing.MODEL_CACHED_PRICES["anthropic:claude-opus-4-5"] == 0.50
    assert pricing.MODEL_CACHED_PRICES["anthropic:claude-4.5-haiku-high"] == 0.10
    assert pricing.MODEL_CACHED_PRICES["unknown:glm-5-high"] == 0.20
