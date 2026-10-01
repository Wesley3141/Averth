"""Tests for pricing table entries added during real-trace validation.

The Claude model versions below surfaced as unpriced when running genuine
public agent trajectories through the CLI (SWE-bench/SWE-smith-trajectories
and mini-SWE-agent runs from the SWE-bench experiments leaderboard). They
carry their published Anthropic list prices ($3.00/1M input, $15.00/1M
output), so they are real entries, not estimates.
"""

import pytest

from agentpnl import pricing
from agentpnl import Tracker


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
