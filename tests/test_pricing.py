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
    # OpenAI list prices, verified 2026-10-23 from developers.openai.com
    # model and pricing pages.
    "openai:gpt-4o": (2.50, 10.00),
    # Snapshot alias, same base-model price; verified on the GPT-4o
    # model page (gpt-4o-2024-08-06 listed as a snapshot, $2.50/$10.00).
    "openai:gpt-4o-2024-08-06": (2.50, 10.00),
    "openai:gpt-4o-mini": (0.15, 0.60),
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
    # Z.ai glm-5.3, verified 2026-10-23 from docs.z.ai/guides/overview/
    # pricing (input $1.40, cached $0.26, output $4.40 per 1M tokens).
    "unknown:glm-5.3": (1.40, 4.40),
    "zai:glm-5.3": (1.40, 4.40),
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


def test_vendor_cached_price_used_for_glm():
    # glm-5.3: input $1.40, cached $0.26, output $4.40 per 1M.
    # 1000 non-cached + 1000 cached + 1000 output must cost
    # 0.001*1.40 + 0.001*0.26 + 0.001*4.40 = $0.00606, not the
    # generic-discount figure 0.001*1.40 + 0.001*1.40*0.10 + 0.001*4.40.
    t = Tracker("cached-vendor")
    t.start_attempt(case_id="C-1")
    t.log_model_call("unknown", "glm-5.3", 2000, 1000,
                     cached_input_tokens=1000)
    a = t.end_attempt(success=True)
    assert a["model"] == pytest.approx(0.00606)
    assert a["cache_savings"] == pytest.approx(0.00114)
    assert t.pnl()["vendor_cached_models"] == ["unknown:glm-5.3"]


def test_gpt4o_snapshot_alias_does_not_fall_back():
    t = Tracker("snapshot")
    t.start_attempt(case_id="C-1")
    t.log_model_call("openai", "gpt-4o-2024-08-06", 1_000_000, 1_000_000)
    t.end_attempt(success=True)
    assert t.unpriced_models == set()
    assert t.attempts[0]["model"] == pytest.approx(12.50)
