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
PRICE_TABLE_VERSION = 7
# ISO date this table was last verified against vendor list-price pages.
# 2026-10-23, the America/Chicago local date when the wave-5
# verification work ran. Dating it with a UTC-future date broke
# price_vintage() for US local dates (see the v6 comment history).
PRICE_TABLE_UPDATED = "2026-10-23"
# Warn (loudly, in reports) when the table is older than this.
PRICE_TABLE_STALE_AFTER_DAYS = 90
# Where the numbers came from, so a reviewer can re-verify them.
# Wave 5 additions (verified 2026-10-23 from the vendors' own pages,
# never from price aggregators or search snippets): OpenAI model pages
# for gpt-4o-2024-05-13 (GPT-4o snapshot list, GPT-4o text-token prices),
# gpt-4o-mini-2024-07-18 (GPT-4o Mini snapshot list), gpt-4.1,
# gpt-4.1-mini, gpt-5.2, gpt-5-mini, o1-mini and its 2024-09-12
# snapshot; Anthropic's pricing page for Claude Opus 4.5 and Haiku 4.5
# (the "-high" dataset labels are effort variants of those same models,
# priced at the base-model rate — never remapped to a different model);
# Z.ai's pricing page for GLM-5 (the "glm-5-high" dataset label is the
# GLM-5 model at high effort). Deliberately NOT added in wave 5:
# deepseek:deepseek-chat (alias retired July 2026; current DeepSeek
# pricing is peak/off-peak dual, and the 2024 lane's V3-era price
# cannot be verified from the current vendor page), google:gemini-1.5-
# pro-002 (absent from Google's current models page), minimax and qwen
# keys (no single vendor list price verified from the vendor page;
# Qwen 2.5-72B is open-weight with provider-varying proxy prices).
# NOTE (flagged, not changed): Anthropic's current pricing page lists
# Claude Opus 4.6 at $5/$25 per 1M, while this table still carries the
# v6 Opus 4.6 entry at $15/$75. Changing it would rewrite the
# tarsur385 Opus 4.6 lane totals (11, 37, 42, 51) and was out of the
# wave-5 brief; it needs an explicit decision before any edit.
PRICE_TABLE_SOURCE = (
    "vendor list-price pages as of 2026-10-23 (OpenAI model pages, "
    "Anthropic pricing page, Z.ai pricing page); GPT-4o / GPT-4o-mini "
    "from OpenAI's model and pricing pages; Z.ai glm-5.3 and glm-5 from "
    "docs.z.ai/guides/overview/pricing (verified 2026-10-23)"
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
    # Wave 5, OpenAI GPT-4o model page (verified 2026-10-23): the
    # snapshot list names gpt-4o-2024-05-13 as a GPT-4o snapshot, and
    # GPT-4o text tokens price at $2.50 input / $1.25 cached / $10.00
    # output per 1M — same precedent as the 2024-08-06 alias in v5.
    "openai:gpt-4o-2024-05-13": (2.50, 10.00),
    "openai:gpt-4o-mini": (0.15, 0.60),
    # Wave 5, OpenAI GPT-4o Mini model page (verified 2026-10-23):
    # gpt-4o-mini-2024-07-18 is listed as a GPT-4o Mini snapshot at
    # $0.15 input / $0.075 cached / $0.60 output per 1M.
    "openai:gpt-4o-mini-2024-07-18": (0.15, 0.60),
    # Wave 5, OpenAI model pages (verified 2026-10-23): GPT-4.1
    # $2.00/$0.50 cached/$8.00; GPT-4.1 Mini $0.40/$0.10 cached/$1.60;
    # GPT-5.2 $1.75/$0.175 cached/$14.00 (its page lists reasoning
    # effort levels including high, so the "gpt-5.2-high" dataset
    # label is that same model at high effort, not a different
    # model); GPT-5 Mini $0.25/$0.025 cached/$2.00; o1-mini
    # $1.10/$0.55 cached/$4.40, with o1-mini-2024-09-12 listed as its
    # snapshot. o1-mini reasoning tokens are billed as output but are
    # absent from trajectory text — pricing the key does not fix that
    # undercount in any lane that uses it.
    "openai:gpt-4.1": (2.00, 8.00),
    "openai:gpt-4.1-mini": (0.40, 1.60),
    "openai:gpt-5.2": (1.75, 14.00),
    "openai:gpt-5.2-high": (1.75, 14.00),
    "openai:gpt-5-mini": (0.25, 2.00),
    "openai:o1-mini": (1.10, 4.40),
    "openai:o1-mini-2024-09-12": (1.10, 4.40),
    "openai:gpt-5.6": (2.50, 10.00),
    "openai:gpt-5.6-mini": (0.30, 1.20),
    "openai:gpt-5-nano": (0.05, 0.40),
    # Wave 5, Anthropic pricing page (verified 2026-10-23): Claude
    # Opus 4.5 $5.00/$0.50 cached/$25.00; Claude Haiku 4.5 $1.00/$0.10
    # cached/$5.00. The tarsur385 dataset labels "claude-4.5-opus-high"
    # and "claude-4.5-haiku-high" are those same models at high effort
    # (the effort parameter changes token consumption, not the
    # per-token price), so they carry the base-model rates — never a
    # remap to Opus 4.6 or any other model. The pre-existing
    # claude-opus-4-6 entry at $15/$75 is left untouched in v7 (see the
    # NOTE above: the current Anthropic page lists Opus 4.6 at $5/$25).
    "anthropic:claude-opus-4-5": (5.00, 25.00),
    "anthropic:claude-4.5-opus-high": (5.00, 25.00),
    "anthropic:claude-4.5-haiku-high": (1.00, 5.00),
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
    # Wave 5, Z.ai pricing page (verified 2026-10-23): GLM-5 $1.00
    # input / $0.20 cached / $3.20 output per 1M. The tarsur385
    # "glm-5-high" label is GLM-5 at high effort, same-model rate.
    "unknown:glm-5": (1.00, 3.20),
    "zai:glm-5": (1.00, 3.20),
    "unknown:glm-5-high": (1.00, 3.20),
    "zai:glm-5-high": (1.00, 3.20),
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
    # Wave 5 cached rates, OpenAI model pages (verified 2026-10-23).
    "openai:gpt-4o-2024-05-13": 1.25,
    "openai:gpt-4o-mini-2024-07-18": 0.075,
    "openai:gpt-4.1": 0.50,
    "openai:gpt-4.1-mini": 0.10,
    "openai:gpt-5.2": 0.175,
    "openai:gpt-5.2-high": 0.175,
    "openai:gpt-5-mini": 0.025,
    "openai:o1-mini": 0.55,
    "openai:o1-mini-2024-09-12": 0.55,
    # Wave 5 cached rates, Anthropic pricing page (verified 2026-10-23):
    # Opus 4.5 cache read $0.50, Haiku 4.5 cache read $0.10 per 1M.
    "anthropic:claude-opus-4-5": 0.50,
    "anthropic:claude-4.5-opus-high": 0.50,
    "anthropic:claude-4.5-haiku-high": 0.10,
    # Wave 5 cached rates, Z.ai pricing page (verified 2026-10-23):
    # GLM-5 cached input $0.20 per 1M.
    "unknown:glm-5": 0.20,
    "zai:glm-5": 0.20,
    "unknown:glm-5-high": 0.20,
    "zai:glm-5-high": 0.20,
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
