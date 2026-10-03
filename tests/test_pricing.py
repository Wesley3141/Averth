"""Tests for pricing table entries added during real-trace validation.

The Claude model versions below surfaced as unpriced when running genuine
public agent trajectories through the CLI (SWE-bench/SWE-smith-trajectories
and mini-SWE-agent runs from the SWE-bench experiments leaderboard). They
carry their published Anthropic list prices ($3.00/1M input, $15.00/1M
output), so they are real entries, not estimates.
"""

import pytest

from averth import pricing
from averth import Tracker


VALIDATION_MODELS = [
    "anthropic:claude-3-7-sonnet-20250219",
    "anthropic:claude-sonnet-4-20250514",
    "anthropic:claude-3-5-sonnet-20241022",
]


@pytest.mark.parametrize("key", VALIDATION_MODELS)
def test_validation_models_have_list_prices(key):
    provider, model = key.split(":", 1)
    assert key in pricing.MODEL_PRICES
    pin, pout = pricing.MODEL_PRICES[key]
    assert (pin, pout) == (3.00, 15.00)
    cost = pricing.model_call_cost(provider, model, 1_000_000, 1_000_000)
    assert cost == pytest.approx(18.00)


@pytest.mark.parametrize("key", VALIDATION_MODELS)
def test_validation_models_do_not_hit_fallback(key):
    provider, model = key.split(":", 1)
    t = Tracker("validation")
    t.start_attempt(case_id="C-1")
    t.log_model_call(provider, model, 1000, 500)
    t.end_attempt(success=True)
    assert t.unpriced_models == set()
    assert t.attempts[0]["per_model"][key] == pytest.approx(
        1000 / 1e6 * 3.00 + 500 / 1e6 * 15.00)


# H2 (review pass 2): pin EVERY table entry. A price edit without updating
# these pins breaks the suite — the editor must then also bump
# PRICE_TABLE_VERSION and move PRICE_TABLE_UPDATED. This is what makes the
# "bump on any change" convention enforceable instead of aspirational.
PINNED_MODEL_PRICES = {
    "openai:gpt-5.6": (2.50, 10.00),
    "openai:gpt-5.6-mini": (0.30, 1.20),
    "openai:gpt-5-nano": (0.05, 0.40),
    "anthropic:claude-opus-4-6": (15.00, 75.00),
    "anthropic:claude-sonnet-4-5": (3.00, 15.00),
    "anthropic:claude-sonnet-4-20250514": (3.00, 15.00),
    "anthropic:claude-3-7-sonnet-20250219": (3.00, 15.00),
    "anthropic:claude-3-5-sonnet-20241022": (3.00, 15.00),
    # verified 2026-10-02 against Anthropic's official pricing page
    # (via economize.cloud): was wrongly (0.80, 4.00) before review pass 2.
    "anthropic:claude-haiku-4-5": (1.00, 5.00),
    "google:gemini-3-pro": (2.00, 12.00),
    "google:gemini-3-flash": (0.50, 3.00),
    "xai:grok-4": (3.00, 15.00),
}

PINNED_TOOL_PRICES = {
    "web_search": 0.005,
    "crm_lookup": 0.002,
    "erp_lookup": 0.004,
    "vector_retrieval": 0.001,
    "code_execution": 0.003,
    "browser_action": 0.010,
    "email_send": 0.001,
    "default": 0.002,
}


def test_all_model_prices_pinned():
    assert set(pricing.MODEL_PRICES) == set(PINNED_MODEL_PRICES)
    for key, (pin, pout) in PINNED_MODEL_PRICES.items():
        assert pricing.MODEL_PRICES[key] == (pin, pout), key


def test_all_tool_prices_pinned():
    assert set(pricing.TOOL_PRICES) == set(PINNED_TOOL_PRICES)
    for key, price in PINNED_TOOL_PRICES.items():
        assert pricing.TOOL_PRICES[key] == price, key


def test_future_table_date_rejected_loudly(monkeypatch):
    monkeypatch.setattr(pricing, "PRICE_TABLE_UPDATED", "2999-01-01")
    with pytest.raises(ValueError, match="in the future"):
        pricing.price_vintage()
