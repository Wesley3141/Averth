# Gate interceptor spec — how config dashboards call the Averth gate

The gate is a deployment webhook/API interceptor, not (only) a CI job.
For support agents the "merge" is usually a LaunchDarkly flag flip, a
prompt-registry version bump, or a dashboard config change — none of which
passes through GitHub Actions. The gate sits between that config surface
and production.

## Call sequence

1. Operator proposes a change in the config surface (new prompt version,
   model swap, threshold tweak).
2. The config surface (or its webhook) POSTs to
   `POST /v1/gate/evaluate` with the proposed config and the
   FinOps-governed threshold BEFORE applying it to production traffic.
3. The gate runs the shadow support-ticket battery against the proposed
   config (pinned battery, fixed seed) and returns pass/fail.
4. PASS → the config surface applies the change (optionally with a
   canary). FAIL → the change is held; the violations list tells the
   operator exactly what breached (cost per acceptable resolution over
   budget, acceptance rate below floor).

## Wiring per platform

- **LaunchDarkly:** a webhook on flag-change (or a custom integration)
  calls the gate with `{"change_id": <flag key + version>,
  "proposed": {"model": ..., "prompt_version": ...}}`. Hold rollout until
  pass.
- **Prompt registry (e.g. LangSmith Hub, Humanloop):** a pre-publish hook
  calls the gate; publish is blocked on fail.
- **Dashboard / internal tool:** synchronous check in the "deploy" button
  handler; show violations inline.
- **GitHub Actions (for prompt-in-repo teams):** thin workflow that POSTs
  the diff's prompt/model and fails the check on gate fail. This is the
  fallback, not the primary path.

## Failure semantics

- **Fail closed on gate errors.** If the gate errors (battery missing,
  model outage), the change does NOT go out. A gate that silently waves
  changes through when it can't measure is worse than no gate.
- **Block on `pass: false` OR any non-200 response OR a timeout.** Callers
  must not treat HTTP 200 alone as approval; only `"pass": true` in the
  body approves.
- **Timeouts:** callers set a deadline (default 120s for n=20 shadow
  battery in mock; live batteries run async — v2). On timeout, treat as
  gate error → fail closed.
- **v1 scope note:** the HTTP layer shadow-tests the CURRENT agent
  against the threshold (answers "is this config within budget?").
  Proposed-config A/B (does the NEW prompt beat the old one?) needs the
  agent to accept config overrides — the `agent_fn` injection point
  exists in `evaluate()` for this; wiring it through HTTP is v2.
- **Signing:** when `AVERTH_GATE_HMAC_SECRET` is set, requests must carry
  `X-Averth-Signature: hex(hmac_sha256(secret, body))`. Production
  deployments MUST set this; without it any caller can forge a pass.

## Threshold governance

Thresholds are FinOps-owned, not engineer-owned. `GET /v1/thresholds`
returns the active set; changes to thresholds are versioned and logged
(v2: append-only threshold ledger). The gate never invents a threshold:
if the caller omits one, service defaults apply and are stamped on the
decision.

## What v1 does NOT do

- No async queue (live batteries run inline; keep n small).
- No canary analysis or automatic rollback (the gate blocks bad deploys;
  it doesn't watch good ones — v2).
- No multi-tenant isolation (one partner, one process — v1).
