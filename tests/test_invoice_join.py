"""Contract-fixture tests for the invoice-join provider adapters.

Fixtures are shaped per the providers' documented API contracts
(see INVOICE_JOIN_RESEARCH.md), not per real responses — no live
credentials were used. A passing suite proves the adapters read the
documented fields; it does not prove reconciliation against a real bill.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmark"))

import invoice_join as ij


def test_openai_numeric_start_time_no_typeerror():
    # OpenAI documents start_time as Unix seconds (numeric).
    resp = {"data": [{
        "start_time": 1791424800, "end_time": 1791428400,
        "results": [{
            "api_key_id": "k1", "model": "gpt-5.6-luna",
            "input_tokens": 1000, "input_cached_tokens": 200,
            "input_cache_write_tokens": 50, "input_uncached_tokens": 750,
            "output_tokens": 100, "num_model_requests": 4,
        }],
    }]}
    buckets = ij.normalize_openai_usage(resp)
    assert len(buckets) == 1
    b = buckets[0]
    assert b["hour_utc"].startswith("2026-10-08T02")
    assert b["grain"] == "hour"
    assert b["input_tokens"] == 1000
    assert b["cache_read_tokens"] == 200
    assert b["cache_creation_tokens"] == 50
    assert b["input_uncached_tokens"] == 750
    assert b["output_tokens"] == 100
    assert b["num_requests"] == 4


def test_anthropic_uncached_and_nested_cache_creation():
    # Anthropic documents uncached_input_tokens and nested
    # cache_creation.ephemeral_{5m,1h}_input_tokens.
    resp = {"data": [{
        "starting_at": "2026-10-08T02:00:00Z",
        "ending_at": "2026-10-08T03:00:00Z",
        "results": [{
            "api_key_id": "k9", "model": "claude-sonnet-4-5",
            "uncached_input_tokens": 1500,
            "cache_creation": {"ephemeral_5m_input_tokens": 100,
                               "ephemeral_1h_input_tokens": 150},
            "cache_read_input_tokens": 3000,
            "output_tokens": 200,
        }],
    }]}
    buckets = ij.normalize_anthropic_usage(resp)
    assert len(buckets) == 1
    b = buckets[0]
    assert b["input_tokens"] == 1500
    assert b["cache_read_tokens"] == 3000
    assert b["cache_creation_tokens"] == 250
    assert b["output_tokens"] == 200
    assert b["billed_cost"] is None  # usage API carries no cost


def test_anthropic_missing_cache_creation_defaults_zero():
    resp = {"data": [{
        "starting_at": "2026-10-08T02:00:00Z",
        "ending_at": "2026-10-08T03:00:00Z",
        "results": [{"uncached_input_tokens": 10, "output_tokens": 5}],
    }]}
    b = ij.normalize_anthropic_usage(resp)[0]
    assert b["cache_creation_tokens"] == 0
    assert b["cache_read_tokens"] == 0
    assert b["api_key_id"] == "unknown"


def test_anthropic_cost_daily_cents_to_usd():
    # cost_report: daily buckets; records in data[].results[]; amount is
    # a USD decimal STRING in cents (not an object); description is a
    # string; the model comes from row["model"].
    resp = {"data": [{
        "starting_at": "2026-10-08T00:00:00Z",
        "ending_at": "2026-10-09T00:00:00Z",
        "results": [{
            "workspace_id": "ws1",
            "model": "claude-sonnet-4-5",
            "description": "claude-sonnet-4-5",
            "cost_type": "tokens",
            "token_type": "output_tokens",
            "amount": "1250",
        }],
    }]}
    buckets = ij.normalize_anthropic_cost(resp)
    assert len(buckets) == 1
    b = buckets[0]
    assert b["grain"] == "day"
    assert b["billed_cost"] == 12.50
    assert b["model"] == "claude-sonnet-4-5"
    assert b["description"] == "claude-sonnet-4-5"


def test_openai_cost_daily_numeric_amount():
    # organization/costs: daily buckets; records in data[].results[];
    # amount.value is the numeric cost (not cents).
    resp = {"data": [{
        "start_time": 1791417600, "end_time": 1791504000,
        "results": [{
            "object": "organization.costs.result",
            "amount": {"value": 3.75, "currency": "usd"},
            "api_key_id": "k1", "project_id": "p1",
            "line_item": "gpt-5.6-luna, output_tokens",
            "quantity": 150000, "quantity_unit": "tokens",
        }],
    }]}
    buckets = ij.normalize_openai_cost(resp)
    assert len(buckets) == 1
    b = buckets[0]
    assert b["grain"] == "day"
    assert b["billed_cost"] == 3.75
    assert b["hour_utc"].startswith("2026-10-08T00")


def test_openai_cost_non_usd_not_summed():
    # A non-USD amount must not be silently treated as USD.
    resp = {"data": [{
        "start_time": 1791417600, "end_time": 1791504000,
        "results": [{
            "amount": {"value": 320.0, "currency": "jpy"},
            "line_item": "gpt-5.6-luna, output_tokens",
        }],
    }]}
    b = ij.normalize_openai_cost(resp)[0]
    assert b["currency"] == "jpy"
    assert b["billed_cost"] is None


def test_time_bucket_accepts_both_shapes():
    iso = ij._time_bucket("2026-10-08T02:34:56Z")
    epoch = ij._time_bucket(1791426896)
    assert iso == epoch
    assert iso == "2026-10-08T02:00:00+00:00"
