# Gate interceptor spec — how config dashboards call the Averth gate

The gate is a deployment webhook/API interceptor, not (only) a CI job.
For support agents the "merge" is usually a LaunchDarkly flag flip, a
prompt-registry version bump, or a dashboard config change — none of which
passes through GitHub Actions. The gate sits between that config surface
and production.

## Call sequence

1. Operator proposes a change in the config surface (new prompt version,
   model swap, threshold tweak).
2. The config surface POSTs to `POST /v1/gate/evaluations` with the
   proposed config — the ACTUAL prompt text and model id, not a version
   reference the gate can't resolve — BEFORE applying it to production
   traffic.
3. The gate responds **202 Accepted** with an `evaluation_id` and a poll
   URL. The shadow battery runs in the background: the CURRENT (pinned)
   agent and the PROPOSED config each run the battery, and the decision
   compares the delta.
4. The caller polls `GET /v1/gate/evaluations/{id}` until `status` is
   `done` (or passes `?wait_seconds=25` on the POST to long-poll behind
   a webhook timeout). PASS → apply the change (optionally canary).
   FAIL → hold; `violations` names what breached: proposed cost over
   budget, acceptance below floor, or acceptance regressed vs current.
5. Block on `"pass": false` OR any non-200 response OR a timeout OR a
   job that ends in `error`. Only `"pass": true` approves.

## Wiring per platform

- **LaunchDarkly:** a webhook on flag-change (or a custom integration)
  calls the gate with `{"change_id": <flag key + version>,
  "proposed": {"model": ..., "prompt": "<full proposed prompt text>"}}`.
  Note: send the actual prompt text, not a version reference — the gate
  cannot resolve registry versions. Hold rollout until pass.
- **Prompt registry (e.g. LangSmith Hub, Humanloop):** a pre-publish hook
  calls the gate with the candidate prompt text; publish is blocked on
  fail.
- **Dashboard / internal tool:** the "deploy" button handler POSTs and
  then polls (or long-polls with `?wait_seconds=25`); show violations
  inline on fail.
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
- **Timeouts:** evaluations are async (202 + poll), so webhook caps are
  handled by the long-poll (`?wait_seconds=`) or by polling. If the poll
  itself times out or the job errors, treat as gate error → fail closed.
- **Delta semantics:** the gate always evaluates the CURRENT pinned agent
  and the PROPOSED config side by side. Pass requires the proposed
  config to be within threshold AND within 5pp acceptance of baseline.
  The `proposed` payload carries the actual change (`model`,
  `haiku_model`, `prompt`); there is no registry-version resolution.
- **Signing:** when `AVERTH_GATE_HMAC_SECRET` is set, requests must carry
  `X-Averth-Signature: hex(hmac_sha256(secret, body))`. Production
  deployments MUST set this; without it any caller can forge a pass.

## Threshold governance

Thresholds are FinOps-owned, not engineer-owned. `GET /v1/thresholds`
returns the active set. The gate never invents a threshold:
if the caller omits one, service defaults apply and are stamped on the
decision.

### Day-one calibration (no invented thresholds)

Nobody knows the right threshold on day one, so don't guess it:
1. Run the gate once in shadow mode against the CURRENT production
   config with a permissive threshold (e.g. `max_cost_per_acceptable_
   resolution: 999`).
2. Read back the measured `cost_per_acceptable_resolution` and
   `acceptance_rate` from the decision.
3. Set the governed threshold at measured cost × (1 + headroom), with
   headroom ~10-20%, and the acceptance floor at the measured rate.
The threshold then means "don't regress past today's economics," which
is a defensible FinOps position from the first deploy. Re-calibrate
after deliberate cost-structure changes (model swaps), never silently.

### Anti-gaming

The gate reuses the dev battery by default. A team that tunes prompts
against the same battery will eventually overfit it. Mitigations (v2):
rotate fresh tickets into the gate battery on a schedule, and reserve a
third split the prompt engineers never see. Until then, treat a long
green streak with suspicion, not celebration.

## What v1 does NOT do

- No canary analysis or automatic rollback (the gate blocks bad deploys;
  it doesn't watch good ones — future).
- No multi-tenant isolation (one partner, one process — v1).
- No append-only threshold ledger (threshold changes are caller-managed;
  the active set is stamped on every decision — future).
