# Case study: Grafana webhook diagnosis costs

**Source:** public code at `absence77/ai-agents-production`, pinned commit `39b3119`
(webhook: `agents/webhook_v2.py`). Studied October 10, 2026.

## The waste

The webhook ran a fresh Sonnet diagnosis (`claude-sonnet-4-6`, 600 max tokens)
on **every** delivery: firing alerts, resolved notifications, and duplicate
retries of the same alert. No status branch, no dedup key.

## The candidate

`Averth-Ahmad-webhook-candidate.patch` (against `baseline_webhook.py`):

1. **Lifecycle routing** — `status: resolved` deliveries get a plain Telegram
   notice, fire-and-forget. Zero model calls, and the webhook never blocks on
   Telegram I/O.
2. **In-flight dedup** — deliveries whose key (fingerprint/labels, status,
   `startsAt`, annotations hash) matches an already-running diagnosis merge
   instead of spawning a new one. Genuine re-fires get a new `startsAt`, so a
   flap never merges into an old job. Identity-less or malformed deliveries
   are never merged.

New firing alerts, changed alerts, and repeats after completion are diagnosed
exactly as before — the diagnosis function is byte-identical.

## The replay

`replay.py` (needs `fastapi` + `httpx` to run; all model/cluster/Telegram
calls are stubbed) replays an identical 9-delivery sequence against the
original and patched handlers:

| Delivery | Original | Candidate |
|---|---|---|
| Fresh firing alert | 1 call | 1 call |
| Five in-flight duplicates | 5 calls | 0 (merged) |
| Resolved notification | 1 call | 0 (notice) |
| Changed alert | 1 call | 1 call |
| Repeat after completion | 1 call | 1 call |
| **Total** | **9** | **3** |

`replay-results.json` holds the machine-readable result. This is a
constructed sequence demonstrating routing behavior, not a savings forecast:
realized savings = the operator's waste rate x alert volume x per-call cost.

## Reuse

The general pattern lives in `averth/integrations/webhook_guard.py`
(framework-agnostic `AlertGuard`). This directory is the worked example that
proved it.
