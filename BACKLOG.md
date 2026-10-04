# Averth backlog

Product ideas parked for later. Not committed, not scheduled.

## Prompt-cache economics (parked 2026-10-04)

Prompt caching is the highest-leverage no-quality-tradeoff cost lever for
LLM agents: up to 90% off input tokens on cache hits, but exact-prefix
matching means one dynamic timestamp or history rewrite silently drops hit
rates from 99% to 0% with no error.

Meter as a first-class dimension:

- Per-workflow cache hit rate (cache-read vs cache-created input tokens).
- Flag prefix instability: dynamic timestamps, request IDs, UI state injected
  into system prompts; history rewrites/trimming that invalidate the cache.
- Recommend the fix: lock the static system prefix at the top of the payload,
  treat chat history as append-only.

Fits the "fixes worth testing" framing: unlike spend caps, cache discipline
costs nothing in output quality. Needs importers to capture provider
cache-read/cache-created token splits (Anthropic `cache_read_input_tokens`,
`cache_creation_input_tokens`; OpenAI `cached_tokens`).
