# Reddit insertion targets — AI agent cost threads

Prepared 2026-10-10. Strategy: Wesley participates as a technical founder with
genuine insight, NOT a pitch. Add value first; mention Averth only if it
naturally answers the question. Every URL below was verified to exist via
search results — no invented links.

## How to use this

1. Read the thread first. Understand what OP actually needs.
2. Comment with the suggested angle IN YOUR OWN VOICE. Never copy-paste.
3. Mention Averth only when it directly answers something asked. One mention
   max per thread, phrased as "I built X for this" not "check out my startup."
4. Do NOT post standalone threads about Averth in these subs (see rules).

---

## Tier 1 — direct pain, perfect fit

### 1. r/AI_Agents — "How are you tracking AI agent costs?"
- URL: https://www.reddit.com/r/AI_Agents/comments/1sshj0q/how_are_you_tracking_ai_agent_costs/
- Date: ~2026 (recent)
- OP's struggle: asking the community how anyone tracks what agents cost.
  No good answers exist — vendor dashboards are aggregate, DIY is the norm.
- Why it's a fit: this is literally the question Averth answers. OP is
  asking for a tool; the thread is a request, not a complaint.
- Suggested angle: Share the honest-accounting insight — that the hard part
  isn't summing tokens, it's handling missing usage data without lying about
  it. Mention that you built an open-source tool that reads Langfuse/LangSmith
  traces locally and labels every dollar by provenance.

### 2. r/ClaudeAI — "I accidentally burned $6000 of Claude usage"
- URL: https://old.reddit.com/r/ClaudeAI/comments/1t11mmy/i_accidentally_burned_6000_of_claude_usage/
- Date: May 1, 2026
- Stats: ~1,175 upvotes, 314 comments
- OP's struggle: left a `/loop` command running 26 hours unattended on
  Claude Opus; Anthropic's dashboard lagged by days so the spike was
  invisible until the limit email landed.
- Why it's a fit: this is the runaway-lens use case exactly. Dashboard lag
  is the villain; per-attempt cost visibility is the fix.
- Suggested angle: The killer detail is dashboard lag — "by the time it
  shows a spike, the money is already spent." Share that the fix isn't
  better alerts, it's per-attempt cost attribution so one runaway run is
  visible in minutes, not days.

### 3. r/ClaudeAI — "$200 subscription vs $7,470 of API usage"
- URL: https://www.reddit.com/r/ClaudeAI/comments/1vbvdzl/200_subscription_vs_7470_of_api_usage/
- Date: ~August 2026
- OP's struggle: reconstructed Claude Code session logs; one month of Max
  usage priced at API list rates came to ~$7,470 against a $200 subscription.
  Trying to understand the true cost of their usage.
- Why it's a fit: OP already did the hard work (dedup session logs, price
  at API rates). This is exactly the "metered vs subscription" analysis
  Averth automates. Technical audience, deep in the weeds.
- Suggested angle: Validate their methodology — deduping session logs and
  pricing at list rates is the right approach. Note the thing most people
  miss: cached tokens dominate these reconstructions, and the cache-hit
  assumption changes the number more than the model choice does.

### 4. r/ChatGPTCoding — "Has anyone figured out how to track per-developer [spend]?"
- URL: https://www.reddit.com/r/ChatGPTCoding/comments/1ro9772/has_anyone_figured_out_how_to_track_perdeveloper/
- Date: ~March 2026
- OP's struggle: 50 Cursor Enterprise seats on a shared pool; $1,500 burned
  in a single day with no per-developer attribution. Finance wants answers.
- Why it's a fit: per-developer/per-agent attribution is the #1 missing
  thing in vendor dashboards. OP is a buyer-shaped person (team lead dealing
  with finance).
- Suggested angle: The shared-pool problem is structural — vendors bill the
  org, so attribution has to happen at the trace level, not the billing
  level. Share that per-agent/per-run attribution from existing traces
  (Langfuse, OTel) is the only way to answer "which developer, which run."

---

## Tier 2 — strong pain, good fit

### 5. r/ClaudeAI — PSA: "the string HERMES.md in your git commit"
- URL: https://old.reddit.com/r/ClaudeAI/comments/1svdm1w/psa_the_string_hermesmd_in_your_git_commit/
- Date: ~2026 (recent)
- Stats: ~1,464 upvotes, 202 comments
- OP's struggle: a string in a git commit silently rerouted Claude Code
  billing from Max subscription to API tier — lost ~$200. Vendor-acknowledged
  bug in harness detection.
- Why it's a fit: billing-routing surprises are a cost-attribution problem.
  The thread is about invisible billing mechanics — Averth's home turf.
- Suggested angle: The deeper issue isn't this specific bug, it's that
  billing routing is invisible — there's no per-run record of *which* tier
  a call billed against. That's an attribution gap no dashboard fills.

### 6. r/ClaudeCode — "Finance asked me what we spend per engineer on [Claude Code]"
- URL: https://www.reddit.com/r/ClaudeCode/comments/1v9hfow/finance_asked_me_what_we_spend_per_engineer_on/
- Date: ~July 2026
- OP's struggle: bill went 4x from Feb to Jul; finance is asking for
  per-engineer spend breakdown and OP can't produce it from the console.
- Why it's a fit: "finance asked" is the exact buyer moment. OP needs
  per-engineer attribution from traces, which is the product.
- Suggested angle: Finance doesn't want token counts, they want dollars per
  engineer per month with a defensible methodology. The console won't give
  it; the answer is joining trace data to the billing period. Keep it
  practical, not salesy.

### 7. r/ClaudeCode — "My company now has daily limits to Claude Code"
- URL: https://www.reddit.com/r/ClaudeCode/comments/1vhxlhh/my_company_now_has_daily_limits_to_claude_code/
- Date: ~August 2026
- OP's struggle: company imposed $90/day per-developer limits after
  runaway spend. Developers chafing; the limit is blunt.
- Why it's a fit: daily limits are the blunt instrument; per-attempt cost
  visibility is the scalpel. Thread is about the tension between control
  and productivity.
- Suggested angle: Blunt daily caps punish everyone for the top 5% of runs.
  The data usually shows a heavy tail — a handful of runaway sessions, not
  everyday usage. Flag the outliers instead of capping everyone.

### 8. r/ClaudeAI — "API equivalent cost" report
- URL: https://www.reddit.com/r/ClaudeAI/comments/1vjxabk/api_equivalent_cost/
- Date: ~2026 (recent)
- OP's struggle: $6,790 over 30 days ($1,835 over 7 days) in API-equivalent
  terms; trying to understand if their usage is normal.
- Why it's a fit: same "what does my usage actually cost" question as #3.
  Technical, data-driven OP.
- Suggested angle: Compare notes on methodology — what counts as
  "API-equivalent" varies wildly with cache assumptions. The most useful
  thing is stating the cache-hit rate alongside the dollar figure.

---

## Tier 3 — adjacent, worth watching

### 9. r/codex — "Did Pro 5x weekly Codex usage drop 44% after the [change]?"
- URL: https://www.reddit.com/r/codex/comments/1vu3u05/did_pro_5x_weekly_codex_usage_drop_44_after_the/
- Date: ~2026 (recent)
- OP's struggle: quota measurements, reconstructing usage from token logs;
  trying to figure out what changed in Codex billing.
- Why it's a fit: quota/cost reconstruction from logs is the same muscle.
  Smaller sub, but highly technical.
- Suggested angle: Share the methodology insight — reconstructing cost from
  logs requires stating your price-table vintage, because rate changes
  silently rewrite history.

### 10. r/codex — "AI subsidies will end and Codex will cost [more]"
- URL: https://www.reddit.com/r/codex/comments/1w059nm/ai_subsidies_will_end_and_codex_will_cost/
- Date: ~2026 (recent)
- OP's struggle: logged a real month ($4,615–$4,828, 6.69B input tokens);
  discussing the end of subsidized pricing.
- Why it's a fit: real measured numbers, discussing what things will cost
  when subsidies end. Forward-looking cost discussion.
- Suggested angle: The subsidy question makes honest measurement more
  valuable, not less — when you pay full price, the difference between
  measured and estimated stops being academic.

---

## Subreddit self-promotion rules — READ BEFORE POSTING

General principle across all of these: **comment, don't post.** Reply to
existing threads with genuine insight. Standalone "I built X" posts will
get removed or downvuted in most of these subs.

What I could verify (from a public reddit-targets guide, cross-check
before relying on it):

- r/ClaudeAI: reply or workflow post only. Generic tool promotion reads
  off-topic. Only mention Averth if the thread is specifically about
  Claude Code costs/workflows.
- r/ClaudeCode: standalone only if Claude Code-specific; otherwise reply.
- r/codex: reply only, or only during allowed self-promo windows. Verify
  any self-promo day before posting.
- r/ChatGPTCoding, r/cursor: reply or workflow post only.
- r/AI_Agents: smaller sub, likely more tolerant — but still lead with
  the answer, not the tool.
- r/LocalLLaMA: typically requires high participation ratio before any
  self-promotion (often cited as 10:1). Lurk and contribute first.
- r/programming: effectively no self-promotion. Don't try.
- r/startups, r/SaaS: have dedicated promo threads/days; standalone
  pitches get removed.

**Account hygiene:** Wesley should use an established account with real
comment history, not a fresh account whose first comment links a GitHub
repo. A few genuine technical comments before any mention is the safe
play. Never ask for upvotes. Never argue with mods.

**The line:** "I built an open-source tool that does X" inside a comment
that already delivered value = fine. A comment that IS the pitch = spam.
If the comment would be useless with the tool mention removed, don't
post it.
