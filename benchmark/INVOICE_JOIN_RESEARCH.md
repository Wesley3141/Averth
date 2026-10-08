# Invoice Join Research — Averth
Researched 2026-10-07. Sources: official Anthropic and OpenAI API docs,
corroborated by two independent third-party integration writeups.
No endpoints invented; where an API does not exist, that is stated.

## 1. Anthropic — Usage and Cost Admin API

Official doc: https://platform.claude.com/docs/en/manage-claude/usage-cost-api
Anthropic explicitly names the use case: "Cost reconciliation: match internal
records with Anthropic billing for finance and accounting teams."

### Auth (critical constraint)
- Requires an **Admin API key** (`sk-ant-admin...`), sent as `x-api-key`
  header with `anthropic-version: 2023-06-01`.
- Regular API keys and OAuth tokens get `403 Authentication method not allowed`.
- **Unavailable for individual accounts** — org account with admin role only.
- **There is no read-only scope on Console admin keys**: the key can
  administer the whole org. Consequence: the key must never leave the
  customer's environment. Customer-side execution is not optional.

### Endpoint A — Usage
`GET https://api.anthropic.com/v1/organizations/usage_report/messages`
- Time: `starting_at` / `ending_at` (RFC 3339, buckets snapped to UTC).
- Buckets: `1m` (max 1440), `1h` (max 168), `1d` (max 31).
- Filter/group dimensions: `api_key_id`, `workspace_id`, `model`,
  `service_tier`, `context_window`, `inference_geo`, `account_id`,
  `service_account_id`, `speed` (beta).
- Token fields per bucket: `uncached_input_tokens`,
  `cache_creation.ephemeral_5m_input_tokens`,
  `cache_creation.ephemeral_1h_input_tokens`, `cache_read_input_tokens`,
  `output_tokens`, plus `server_tool_use.web_search_requests`.
- Freshness: typically within 5 minutes of request completion. Polling:
  once/minute sustained is acceptable.

### Endpoint B — Cost
`GET https://api.anthropic.com/v1/organizations/cost_report`
- Buckets: **daily only** (`1d`).
- `group_by` accepts ONLY `workspace_id` and `description`. **There is no
  api_key_id grouping on the cost endpoint.** Grouping by `description`
  returns parsed fields including `model` and `inference_geo`.
- `cost_type` values: `tokens`, `web_search`, `code_execution`,
  `session_usage`.
- `token_type` values: `uncached_input_tokens`, `output_tokens`,
  `cache_read_input_tokens`, `cache_creation.ephemeral_5m_input_tokens`,
  `cache_creation.ephemeral_1h_input_tokens`.
- Amounts: USD decimal strings in lowest units (cents); currency always USD.
- Pagination: `has_more` / `next_page` -> `page`.

### What you CANNOT get from Anthropic
- **No trace/request-level data.** Finest grain is api_key_id x 1h bucket
  (usage) or description x 1d (cost). You can never map spend to an
  individual run from the provider side.
- **No invoice-list API.** Invoices live in Console -> Settings -> Billing ->
  Invoice history (monthly, typically one line: "Claude API Usage --
  <Month>" plus addons like Priority Support). The "invoice join" is really a
  cost_report join plus manual invoice cross-check.
- **Priority Tier costs are not in the cost endpoint** (official FAQ).
- Playground/Workbench usage has `api_key_id = null` even when grouped.
- **Claude Code on OAuth (Pro/Max subscription) does not appear here at
  all** — subscription and API are separate billing systems. Enterprise
  orgs use a separate Analytics API with a different key type.
- Default workspace shows `workspace_id = null`.

## 2. OpenAI — Organization Usage & Costs (Admin API)

### Auth
- Admin API key from platform.openai.com -> Settings -> Organization ->
  Admin keys, sent as `Authorization: Bearer`.
- Standard project keys (`sk-proj-...`) return 403 on these endpoints.
- Admin keys cannot be used for non-administration endpoints.

### Endpoint A — Costs
`GET https://api.openai.com/v1/organization/costs`
- Time: `start_time` / `end_time` (Unix seconds, start inclusive, end
  exclusive).
- `bucket_width`: **only `1d` supported**. Limit 1-180 buckets (default 7).
- Filters: `project_ids[]`, `api_key_ids[]`, `line_items[]` (exact match,
  e.g. `gpt-6-astra, input_tokens`).
- `group_by`: `project_id`, `user_id`, `line_item`, `api_key_id`,
  `api_source`. (`user_id`+`project_id` combos depend on org; 400 if
  unsupported.)
- `api_source` grouping is notable: `agents_api` = attributed Agents API
  activity, `unlabeled` = everything else. OpenAI's own agent attribution.
- Returns `organization.costs.result`: `amount.value` (number),
  `amount.currency` (lowercase ISO-4217, e.g. `usd`), `line_item`,
  `project_id`, `api_key_id`, `quantity`, `quantity_unit`.
- Pagination: `has_more` / `next_page` cursor.
- **There is no model grouping for costs** — model appears inside the
  `line_item` string.

### Endpoint B — Usage (completions)
`GET https://api.openai.com/v1/organization/usage/completions`
- Buckets: `1m` (max 1440), `1h` (max 168), `1d` (max 31).
- Filters: `project_ids[]`, `user_ids[]`, `api_key_ids[]`, `models[]`,
  `batch` (true = batch jobs only, false = non-batch only).
- `group_by`: `project_id`, `user_id`, `api_key_id`, `model`, `batch`,
  `service_tier`, `api_source`.
- Fields: `input_tokens` (includes cached + cache-write), `input_cached_tokens`,
  `input_cache_write_tokens`, `input_uncached_tokens` (excludes cache-write),
  `output_tokens`, audio/image token splits, `num_model_requests`.
- Sibling endpoints (same auth/params shape): `audio_speeches`,
  `audio_transcriptions`, `embeddings`, `images`, `moderations`,
  `vector_stores`, `code_interpreter_sessions`, `file_search_calls`,
  `web_search_calls`.
- Per-request `usage` on chat completions gives prompt/completion splits
  incl. `prompt_tokens_details.cached_tokens`.

### What you CANNOT get from OpenAI
- **No invoice-list REST API.** Billing history is Console UI
  (platform.openai.com -> Org -> Billing -> History).
- **ChatGPT Plus/Pro/Team/Enterprise subscriptions are a separate billing
  system** — no API returns those invoices to a project key.
- Latency of usage/costs data is **not documented**.
- No per-trace granularity (finest = api_key_id x model x 1m bucket).

## 3. The join key

Neither provider can attribute spend to an individual run. The join is at
the **(api_key_id, time bucket)** level:

| Provider | Usage grain | Cost grain | Join key vs our logs |
|---|---|---|---|
| Anthropic | (api_key_id, model, 1h) | (description->model+token_type, 1d) | Sum our per-run tokens by (key, UTC hour); compare to usage_report. Price it ourselves; compare to cost_report daily by parsed model. |
| OpenAI | (api_key_id, model, 1h) | (api_key_id, line_item, 1d) | Sum our per-run tokens by (key, model, UTC hour); compare to usage. Costs join directly on (api_key_id, day) — cleaner than Anthropic. |

Requirements on our side: every logged run must record the **API key id**
(not the secret — the `key_id` shown in Console) and a **UTC timestamp**.
Anthropic buckets snap to UTC; align to that.

### What breaks the join (and how each is handled)
1. **Prompt caching discounts** — COMPUTABLE. Both APIs split cached vs
   uncached tokens. Apply the provider's cache price schedule to our
   per-run cache token counts. Requires our tracker to record cache
   tokens separately (it does: `cached_tokens`, `cache_savings`).
2. **Batch API 50% discount** — DETECTABLE. OpenAI: `batch` filter/group on
   usage. Anthropic: `service_tier` dimension. If our runs don't use batch,
   exclude batch-flagged provider rows from the comparison and label them.
3. **Server-side tools** (Anthropic web_search, code_execution) — LABELED
   GAP. They appear in Anthropic's cost_report under their own cost_type but
   our meter may not capture them per run. Report as its own line, not as
   error.
4. **Committed-use / volume / enterprise discounts** — UNKNOWABLE from API.
   Becomes part of the unexplained residual unless the customer supplies
   their effective rate as an input.
5. **Credits and promotions** — invoice-level only, not in cost_report.
   Residual.
6. **Priority Tier (Anthropic)** — not in cost endpoint at all. Residual;
   flag if customer uses it.
7. **Subscription/OAuth usage** (Claude Code on Pro/Max, ChatGPT) —
   invisible to both Admin APIs. Out of scope; say so in the report.
8. **Playground usage** (Anthropic `api_key_id=null`) — exclude or label.
9. **Timing skew** — provider data lags ~5 min (Anthropic; OpenAI
   undocumented). Never reconcile a window fresher than ~1h old.

## 4. The "explained delta" report

For a chosen window (e.g., last 7/30 days) and a set of API keys the
customer maps to workflows:

```
A  Metered estimate ......... our per-run tokens x price book, by (key, day, model)
B  Provider usage tokens ..... usage API by (key, [model,] day)
     B-A  Token-count delta ... dropped/retried/streaming-partial requests
C  Cache pricing delta ....... our cache tokens x (cache_price - list_price)
D  Batch discount ............ provider-flagged batch rows, priced at 0.5x
E  Server-side tools ......... provider cost_report cost_type != tokens
F  Provider cost total ....... cost API by (key|description, day)
     F-(A+C+D+E)  Residual ... committed use, credits, priority tier, timing
```

Rules: every component labeled measured / computed / unknowable. Residual
over ~10% with no explained cause = failed reconciliation, say so — do not
paper it over. No number leaves the repo without a source (API response or
experiment id).

## 5. MVP recommendation (pilot, customer-side, aggregates only)

**Do not ask for their admin key. Do not ask for logs.** Ship a small
script the customer runs in their own VPC with their own admin key:

1. Script pulls, for a customer-chosen window (default last 30d):
   - Anthropic: `usage_report/messages` grouped by (api_key_id, model),
     `bucket_width=1d`; `cost_report` grouped by `description`, `1d`.
   - OpenAI: `usage/completions` grouped by (api_key_id, model), `1d`;
     `costs` grouped by (api_key_id, line_item), `1d`.
2. Script emits ONLY aggregates: per (provider, day, key_id, model)
   token totals and per (provider, day, key_id|description) cost totals.
   No prompts, no traces, no raw logs, no key material leaves the building.
3. Customer tells us (out of band) which key_id belongs to which workflow.
4. We produce the explained-delta report against our metered estimates for
   the same keys/days.

Why this shape: the admin keys are god-mode with no read-only scope, so
customer-side execution is the only defensible posture; aggregates-only
output dodges the DPA/redaction fight (reviewers 2 and 6 both demanded
this); and the join needs nothing finer than key x day to prove the
reconciliation works. Trace-level attribution remains our side's job —
the provider can never supply it.

Prior art doing this pattern: tanso-oss (github.com/tanso-oss) pulls both
vendors into `vendor_usage_buckets` and runs usage/reconcile/allocation
reports with the same "metered = tokens x price book, marked estimate when
unpriced" semantics.

Open question for M3.5: whether customers will run even this script
(admin-key handling is sensitive). Fallback: they export the Console CSVs
(both providers offer CSV export on the usage/cost pages) and send those.
