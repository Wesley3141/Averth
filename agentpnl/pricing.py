"""Model and tool pricing tables. Prices in USD. Edit as vendors change them."""

# (input per 1M tokens, output per 1M tokens)
MODEL_PRICES = {
    "openai:gpt-5.6": (2.50, 10.00),
    "openai:gpt-5.6-mini": (0.30, 1.20),
    "openai:gpt-5-nano": (0.05, 0.40),
    "anthropic:claude-opus-4-6": (15.00, 75.00),
    "anthropic:claude-sonnet-4-5": (3.00, 15.00),
    "anthropic:claude-haiku-4-5": (0.80, 4.00),
    "google:gemini-3-pro": (2.00, 12.00),
    "google:gemini-3-flash": (0.50, 3.00),
    "xai:grok-4": (3.00, 15.00),
}

# per-call cost for common tools; override per deployment
TOOL_PRICES = {
    "web_search": 0.005,
    "crm_lookup": 0.002,
    "erp_lookup": 0.004,
    "vector_retrieval": 0.001,
    "code_execution": 0.003,
    "browser_action": 0.010,
    "email_send": 0.001,
    "default": 0.002,
}

# fully loaded human reviewer cost per minute (wages + benefits + overhead)
HUMAN_COST_PER_MIN = 1.17  # ~$70/hr loaded


# fallback per-1M-token prices (input, output) used when a model has no
# entry in MODEL_PRICES; estimated spend is flagged, never presented as exact
ESTIMATED_MODEL_PRICES = (1.00, 3.00)


def model_call_cost(provider, model, input_tokens, output_tokens):
    key = f"{provider}:{model}"
    if key not in MODEL_PRICES:
        raise KeyError(f"no price for {key}; add it to MODEL_PRICES")
    pin, pout = MODEL_PRICES[key]
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


def tool_call_cost(name):
    return TOOL_PRICES.get(name, TOOL_PRICES["default"])


def estimated_model_cost(provider, model, input_tokens, output_tokens):
    """Fallback cost for a model missing from MODEL_PRICES.

    Uses ESTIMATED_MODEL_PRICES (1.00/3.00 per 1M tokens). Integrations call
    this when model_call_cost raises KeyError and record the result via
    Tracker.log_model_cost_estimate, which flags the model in
    pnl()["unpriced_models"].
    """
    pin, pout = ESTIMATED_MODEL_PRICES
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout
