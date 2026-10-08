# Support-Ticket Source Research (for Averth support-agent benchmark)

Date: 2026-10-07. Research only; no benchmark code written.
Goal: a PUBLIC source of real support tickets with (a) accepted resolutions and (b) reopen events, to pin an evaluation battery.

## Recommendation

**Primary: GitHub issues on `microsoft/vscode` labeled `*question`, state closed.**

Verified via the GitHub REST API (unauthenticated) on 2026-10-07:

| Criterion | Evidence |
|---|---|
| >= 500 closed support-question items | `GET /search/issues?q=repo:microsoft/vscode+label:"*question"+state:closed` -> **total_count 6,731**, `incomplete_results: false` |
| Reopen events observable | `GET /repos/microsoft/vscode/issues/{n}/events` exposes `"reopened"` events. Positive in 2/12 high-comment issues sampled (issues #109078, #78738). Reopen rate in support is typically 3-7%, so expect ~200-450 reopened in the full set. |
| Accepted-resolution signal | Issue field `state_reason`: in a 100-issue sample, **94 `completed` / 6 `not_planned`**. `completed` = maintainer closed after answering; `not_planned` = deflected (e.g., redirected to Stack Overflow). Usable as `resolution_label`. |

Why vscode over the alternatives: largest verified volume, highest completed-rate, reopen events positively confirmed, single label (`*question`) that the repo's own triage applies to user questions.

**Backup: GitHub issues on `kubernetes/kubernetes` labeled `kind/support`, state closed.**

Verified: 2,914 closed (`total_count`), 98/100 sampled `state_reason: completed`. Same API surface as the primary. Caveat: reopened events were NOT observed in a 27-issue sample (15 high-comment + repo-wide recent events window). The mechanism is identical to the primary, so this is likely a sampling artifact of rare events, but confirm the reopen rate on a larger sample during the build before relying on it.

## Evaluated and rejected

1. **GitHub Discussions (e.g. `vercel/next.js`)** — has a clean "answered" state (accepted answer), which is a better acceptance signal than `state_reason`. But Discussions have **no reopen events** (documented platform gap; no event stream exposes reopens). Fails criterion (b). Also requires a GraphQL token; not verifiable unauthenticated.
2. **Kaggle `suraj520/customer-support-ticket-dataset` (8,469 rows, CC0)** — schema is `Customer Email, Product Purchased, Ticket Type, Ticket Priority, Ticket Subject, Combined Text`. No reopen field, no resolution text, and the data reads synthetic. Fails (a) and (b).
3. **HuggingFace `Tobi-Bueck/customer-support-tickets`, `air5978/synthetic_customer_support_crm`** — have answer/resolution columns but are synthetic and lack reopen signals. Fails the "real tickets" bar.
4. **CFPB consumer-complaint database** — real complaints with company responses, but no reopen/acceptance events. Fails (b).
5. **Customer Support on Twitter (Kaggle)** — real threads, but no resolution or reopen labels. Fails (a) and (b).

## Exact fetch plan (primary source)

Base: `https://api.github.com`

1. **Enumerate** (search API caps at 1,000 results, so use the issues list endpoint for full enumeration):
   `GET /repos/microsoft/vscode/issues?labels=%2Aquestion&state=closed&per_page=100&page=N`
   Follow the `Link` response header for pagination (~68 pages for 6,731). Filter out pull requests (drop items containing a `pull_request` key).
2. **Detail per issue** (or reuse list-endpoint payload, which already includes most fields):
   `GET /repos/microsoft/vscode/issues/{number}`
3. **Reopen detection**:
   `GET /repos/microsoft/vscode/issues/{number}/events` -> `reopened_bool = any(e["event"] == "reopened")`
4. **Count sanity check**:
   `GET /search/issues?q=repo:microsoft/vscode+label:"*question"+state:closed&per_page=1` (read `total_count`)

### Field mapping

| Battery field | Source |
|---|---|
| `ticket_id` | `"microsoft/vscode#" + number` (or the issue `node_id`) |
| `title` | `title` |
| `body` | `body` (markdown; first user message; scrub emails/PII before pinning) |
| `resolution_label` | `state_reason`: `completed` -> accepted, `not_planned` -> deflected, `duplicate` -> duplicate |
| `reopened_bool` | any `events[].event == "reopened"` |
| `time_to_close_hours` | `(closed_at - created_at) / 3600` |

### Fetch effort estimate

- ~68 list pages + up to 6,731 events calls (+ detail calls if needed).
- Unauthenticated: 60 req/hour core -> full pull is infeasible (~110+ hours). Fine for validation sampling.
- With any personal access token: 5,000 req/hour -> ~1.5-2 hours for the full set. **Recommend a token for the build, or pin a random sample of ~1,000 issues** (~10 pages + 1,000 events calls; ~17h unauthenticated, ~15 min with token).
- Use `If-None-Match` / ETags and the `Link` header; cache aggressively since the battery is pinned.

## Licensing / ToS notes

- GitHub ToS permits API access to public data; respect rate limits (checked: `X-RateLimit` headers observed during research).
- Issue bodies are user-contributed content, not code under an OSS license. Viewing/analysis is fine; if redistributing a derived dataset, include attribution to the source repo and note the provenance. Do not republish raw bodies containing PII — scrub emails/addresses before pinning the battery.
- No scraping outside the API (no HTML scraping needed; everything above is API-available).
- This is Microsoft's public support queue; using it for benchmark research is standard practice (cf. SWE-bench-style datasets built on public GitHub data), but keep the pinned battery to what's needed and document the source.

## Open caveats for the build

- `state_reason: completed` is a **maintainer-close** signal, not customer-confirmed acceptance. Honest semantics: "maintainer treated as resolved." The reopen flag is the customer-side counter-signal (reopen after close ~= acceptance failed).
- `*question` label application is by repo triage/bot; spot-check a sample for label precision before pinning.
- Bodies are markdown with images/links; the agent under test will need the rendered text plus comment threads for full context (comments endpoint: `/repos/microsoft/vscode/issues/{number}/comments`).
