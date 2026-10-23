"""Model and tool pricing tables. Prices in USD.

PRICE TABLE VERSIONING (C2 fix): every dollar figure the meter reports is
only as current as this table. The table carries a version and the date it
was last verified against vendor list-price pages. price_vintage() reports
its age; staleness_warning() fires when it is older than
PRICE_TABLE_STALE_AFTER_DAYS. Reports stamp the vintage so a reader can
tell whether the dollars assume this month's or last year's prices.

There is deliberately no network code in this package (the meter must never
exfiltrate), so there is no live price feed. To update: edit the tables
below, bump PRICE_TABLE_VERSION, set PRICE_TABLE_UPDATED to today, and add
a regression test pinning the changed price. `averth pricing` shows the
current status.
"""

# Version of this price table. Bump on ANY price change.
PRICE_TABLE_VERSION = 6
# ISO date this table was last verified against vendor list-price pages.
# Dated 2026-10-22, the local date when the verification work ran in
# America/Chicago. Dating it 2026-10-23 (UTC date) broke price_vintage()
# for US local dates still on Oct 22, because that function compares
# against local date.today().
PRICE_TABLE_UPDATED = "2026-10-22"
# Warn (loudly, in reports) when the table is older than this.
PRICE_TABLE_STALE_AFTER_DAYS = 90
# Where the numbers came from, so a reviewer can re-verify them.
PRICE_TABLE_SOURCE = (
    "vendor list-price pages as of 2026-10-23 (OpenAI, Anthropic, Google, xAI); "
    "GPT-4o / GPT-4o-mini from OpenAI's model and pricing pages; "
    "Z.ai glm-5.3 from docs.z.ai/guides/overview/pricing (input $1.40, "
    "cached input $0.26, output $4.40 per 1M tokens, verified 2026-10-23)"
)

# (input per 1M tokens, output per 1M tokens)
MODEL_PRICES = {
    # OpenAI list prices, verified 2026-10-23 from developers.openai.com
    # model and pricing pages (GPT-4o-mini: $0.15/$0.60; GPT-4o: $2.50/$10.00).
    "openai:gpt-4o": (2.50, 10.00),
    # Snapshot alias, same base-model list price: the GPT-4o model page
    # (developers.openai.com/api/docs/models/gpt-4o, read 2026-10-23)
    # lists gpt-4o-2024-08-06 in its snapshot list and prices GPT-4o
    # text tokens at $2.50 input / $1.25 cached input / $10.00 output
    # per 1M tokens. POC 2's model key is openai:gpt-4o-2024-08-06, so
    # without this entry it fell back to $1.00/$3.00 entirely.
    "openai:gpt-4o-2024-08-06": (2.50, 10.00),
    "openai:gpt-4o-mini": (0.15, 0.60),
    "openai:gpt-5.6": (2.50, 10.00),
    "openai:gpt-5.6-mini": (0.30, 1.20),
    "openai:gpt-5-nano": (0.05, 0.40),
    "anthropic:claude-opus-4-6": (15.00, 75.00),
    "anthropic:claude-sonnet-4-5": (3.00, 15.00),
    "anthropic:claude-sonnet-4-20250514": (3.00, 15.00),  # published list price
    "anthropic:claude-3-7-sonnet-20250219": (3.00, 15.00),  # published list price
    "anthropic:claude-3-5-sonnet-20241022": (3.00, 15.00),  # published list price
    "anthropic:claude-haiku-4-5": (1.00, 5.00),  # verified 2026-10-02
    # Dated snapshot of the same model, as it appears in real Claude
    # Code session exports (Simon Willison session, 2025-12-19).
    # Anthropic's own Haiku 4.5 announcement prices Haiku 4.5 at
    # $1/$5 per 1M tokens, and the dated id claude-haiku-4-5-20251001
    # is listed at the same $1.00/$5.00 rate (verified 2026-10-22).
    "anthropic:claude-haiku-4-5-20251001": (1.00, 5.00),
    # (was 0.80/4.00 — wrong; corrected per review pass 2)
    "google:gemini-3-pro": (2.00, 12.00),
    "google:gemini-3-flash": (0.50, 3.00),
    "xai:grok-4": (3.00, 15.00),
    # Z.ai glm-5.3, verified 2026-10-23 from docs.z.ai/guides/overview/pricing.
    # "unknown:" is the key the importer actually hits for a bare model
    # name "glm-5.3" (guess_provider has no glm/z.ai rule); "zai:" covers
    # an explicit zai provider. Both carry the same list prices.
    "unknown:glm-5.3": (1.40, 4.40),
    "zai:glm-5.3": (1.40, 4.40),
}

# Vendor cached-input prices per 1M tokens, where the vendor publishes one
# separately from the input price. CONSUMED by Tracker.log_model_call:
# for a model key present here, cached tokens are priced at this rate,
# not at the generic CACHE_READ_DISCOUNT (0.10 of the input price).
# Models absent from this dict keep the generic discount (or an explicit
# Tracker cache_read_discount override). The saving reported for a
# vendor-cached model is therefore input price minus this cached rate,
# not input price minus the generic discount.
MODEL_CACHED_PRICES = {
    "unknown:glm-5.3": 0.26,
    "zai:glm-5.3": 0.26,
    # OpenAI cached rates verified 2026-10-22 from the GPT-4o model page:
    # GPT-4o cached $1.25, GPT-4o-mini cached $0.075 per 1M tokens.
    "openai:gpt-4o": 1.25,
    "openai:gpt-4o-2024-08-06": 1.25,
    "openai:gpt-4o-mini": 0.075,
}

# per-call cost for common tools.
#
# H2 WARNING: these are rough per-deployment estimates baked in as
# universals, NOT measured costs. Any trace that does not pass an explicit
# cost to log_tool_call(name, cost=...) silently gets these numbers — and
# external tool spend is exactly the layer where a wrong default does the
# most damage (it is invisible on provider invoices). The meter now tracks
# which tool calls used these defaults and pnl()/reports flag the estimated
# portion loudly (see "tools_default_priced_spend"). For a real deployment,
# measure your tool costs and pass them explicitly or override this table.
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

# Fraction of the base input-token price charged for cache-read tokens.
# Anthropic publishes 0.10x for cache reads (1.25x for cache writes, which we
# do not model separately); other vendors differ, so Tracker accepts an
# override. Any cache saving the meter reports is labeled as derived from
# this documented assumption, never as a vendor invoice line.
CACHE_READ_DISCOUNT = 0.10


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


def price_vintage():
    """Report which price table the meter is using and how old it is.

    Returns {"version", "updated", "age_days", "stale", "stale_after_days"}.
    Every report stamps this so dollar figures are never silently
    misattributed to the wrong price era.

    A future PRICE_TABLE_UPDATED raises loudly: a typo'd future date would
    otherwise make age_days negative and silently disable the staleness
    alarm until 90 days past the wrong date.
    """
    from datetime import date
    updated = date.fromisoformat(PRICE_TABLE_UPDATED)
    today = date.today()
    if updated > today:
        raise ValueError(
            "PRICE_TABLE_UPDATED (%s) is in the future — fix the date in "
            "averth/pricing.py. A future date silently disables the "
            "staleness alarm." % PRICE_TABLE_UPDATED)
    age_days = (today - updated).days
    return {
        "version": PRICE_TABLE_VERSION,
        "updated": PRICE_TABLE_UPDATED,
        "age_days": age_days,
        "stale": age_days > PRICE_TABLE_STALE_AFTER_DAYS,
        "stale_after_days": PRICE_TABLE_STALE_AFTER_DAYS,
    }


def staleness_warning():
    """Human-readable warning when the price table is stale, else None.

    Callers (reports, CLI) surface this loudly: a vendor price change after
    PRICE_TABLE_UPDATED silently corrupts every dollar figure otherwise.
    """
    v = price_vintage()
    if v["stale"]:
        return (
            "pricing table v%s is %d days old (last verified %s against %s); "
            "vendor prices may have changed — verify before trusting dollar "
            "figures" % (v["version"], v["age_days"], v["updated"],
                         PRICE_TABLE_SOURCE))
    return None
