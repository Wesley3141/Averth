"""Replay v3: identical 9-delivery sequences against baseline and candidate.

Shared sequence: firing A, 5x duplicate A, resolved A, firing B (changed),
firing A again (repeat, new startsAt).
  Baseline: 9 Sonnet calls. Candidate: 3. Avoided: 6 of 9.

Separate branch tests (candidate only):
  - changed-C while A in-flight -> diagnosed (different key)
  - annotation-only change while in-flight -> diagnosed (annotations in key)
  - degenerate alert (no fingerprint, no labels) x2 -> never merged
  - key auto-cleanup after real task completion (no race: polled)

In-flight overlap is simulated by seeding `_diagnosing` with a fake non-done
task — the exact state a real in-flight job produces. The merge branch
(`if key in _diagnosing and not task.done()`) is the real code under test;
real task lifecycle (register/pop) is tested for real.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rig import load_webhook

VENV_PY = str(Path(__file__).resolve().parent / ".venv" / "bin" / "python")
assert "webhook_dedup/.venv" in sys.executable, f"run with the venv python: {VENV_PY}"


class FakeTask:
    def __init__(self, done: bool):
        self._done = done

    def done(self):
        return self._done


def make_alert(fp, status, pod="api-1", ns="lab", name="PodCrashLooping",
               starts_at="2026-10-10T12:00:00Z", annotations=None, labels=None):
    return {
        "status": status,
        "labels": {"alertname": name, "pod": pod, "namespace": ns} if labels is None else labels,
        "annotations": {"summary": f"{name} on {pod}"} if annotations is None else annotations,
        "startsAt": starts_at,
        "endsAt": "0001-01-01T00:00:00Z" if status == "firing" else "2026-10-10T12:05:00Z",
        "fingerprint": fp,
    }


def delivery(*alerts):
    return {
        "receiver": "webhook",
        "status": alerts[0]["status"],
        "alerts": list(alerts),
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "http://grafana/",
    }


def wait_for(pred, timeout=15.0, desc="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return
        time.sleep(0.05)
    raise TimeoutError(f"timed out waiting for: {desc}")


def shared_sequence():
    return [
        make_alert("aaa", "firing"),
        make_alert("aaa", "firing"),
        make_alert("aaa", "firing"),
        make_alert("aaa", "firing"),
        make_alert("aaa", "firing"),
        make_alert("aaa", "firing"),
        make_alert("aaa", "resolved"),
        make_alert("bbb", "firing", pod="api-2"),
        make_alert("aaa", "firing", starts_at="2026-10-10T12:30:00Z"),
    ]


def run_baseline(path):
    from fastapi.testclient import TestClient

    mod, fakes = load_webhook("baseline_webhook", path)
    tg = fakes["telegram"]
    sonnet = fakes["anthropic_client"].messages
    client = TestClient(mod.app)
    for a in shared_sequence():
        client.post("/webhook/grafana", json=delivery(a))
    wait_for(lambda: len(tg.messages) >= 9, desc="9 baseline telegrams")
    time.sleep(0.5)
    return {"sonnet_calls": len(sonnet.calls), "call_details": sonnet.calls,
            "telegrams": list(tg.messages)}


def run_candidate(path):
    from fastapi.testclient import TestClient

    mod, fakes = load_webhook("candidate_webhook", path)
    tg = fakes["telegram"]
    sonnet = fakes["anthropic_client"].messages
    client = TestClient(mod.app)
    post = lambda a: client.post("/webhook/grafana", json=delivery(a)).json()
    actions = []

    # 1. fresh firing A -> diagnosed; key auto-cleaned after real completion
    a = make_alert("aaa", "firing")
    actions.append(post(a)["action"])
    key_a = mod._alert_key(a)
    wait_for(lambda: len(tg.messages) >= 1, desc="A diagnosis telegram")
    wait_for(lambda: key_a not in mod._diagnosing, desc="key cleanup after completion")

    # 2. simulate A's job in-flight; 5 duplicates -> merged, 0 new calls
    mod._diagnosing[key_a] = FakeTask(done=False)
    for _ in range(5):
        actions.append(post(make_alert("aaa", "firing"))["action"])
    assert len(sonnet.calls) == 1, f"duplicates must not dispatch, got {len(sonnet.calls)}"
    del mod._diagnosing[key_a]

    # 3. resolved A -> fire-and-forget notice, 0 model calls
    actions.append(post(make_alert("aaa", "resolved"))["action"])
    wait_for(lambda: any(m.startswith("RESOLVED") for m in tg.messages), desc="resolved notice")
    assert len(sonnet.calls) == 1

    # 4. firing B (changed value) -> diagnosed
    actions.append(post(make_alert("bbb", "firing", pod="api-2"))["action"])
    # 5. firing A repeat with NEW startsAt -> diagnosed (flap-safe)
    actions.append(post(make_alert("aaa", "firing", starts_at="2026-10-10T12:30:00Z"))["action"])
    wait_for(lambda: len(sonnet.calls) >= 3, desc="B + repeat diagnoses")
    time.sleep(0.5)
    return {"actions": actions, "sonnet_calls": len(sonnet.calls),
            "call_details": sonnet.calls, "telegrams": list(tg.messages),
            "mod": mod, "fakes": fakes, "client": client, "post": post}


def branch_tests(ctx):
    """Separate branch tests on the candidate (not part of the 9v9 count)."""
    mod, fakes, client, post = ctx["mod"], ctx["fakes"], ctx["client"], ctx["post"]
    tg = fakes["telegram"]
    sonnet = fakes["anthropic_client"].messages
    results = {}

    # changed-C while A in-flight -> diagnosed (different key)
    a = make_alert("aaa", "firing")
    key_a = mod._alert_key(a)
    mod._diagnosing[key_a] = FakeTask(done=False)
    before = len(sonnet.calls)
    r = post(make_alert("ccc", "firing", pod="api-3"))
    results["changed_while_inflight"] = r["action"]
    assert r["action"] == "diagnosed" and len(sonnet.calls) == before + 1
    del mod._diagnosing[key_a]

    # annotation-only change while in-flight -> diagnosed (annotations in key)
    mod._diagnosing[key_a] = FakeTask(done=False)
    before = len(sonnet.calls)
    changed_ann = make_alert("aaa", "firing", annotations={"summary": "x", "value": "99"})
    r = post(changed_ann)
    results["annotation_change_while_inflight"] = r["action"]
    assert r["action"] == "diagnosed" and len(sonnet.calls) == before + 1
    del mod._diagnosing[key_a]

    # degenerate: no fingerprint, no labels -> never merged
    deg = make_alert(None, "firing", labels={})
    before = len(sonnet.calls)
    r1 = post(deg)["action"]
    wait_for(lambda: len(sonnet.calls) >= before + 1, desc="degenerate 1")
    r2 = post(deg)["action"]
    wait_for(lambda: len(sonnet.calls) >= before + 2, desc="degenerate 2")
    results["degenerate_never_merged"] = (r1, r2)
    assert (r1, r2) == ("diagnosed", "diagnosed")

    # flap: firing(t0) in-flight, resolved, firing again with NEW startsAt -> diagnosed
    a_old = make_alert("aaa", "firing", starts_at="2026-10-10T12:00:00Z")
    key_old = mod._alert_key(a_old)
    mod._diagnosing[key_old] = FakeTask(done=False)
    before = len(sonnet.calls)
    r = post(make_alert("aaa", "resolved"))
    assert r["action"] == "resolved-notice"
    r = post(make_alert("aaa", "firing", starts_at="2026-10-10T12:40:00Z"))
    results["flap_refire_new_startsAt"] = r["action"]
    assert r["action"] == "diagnosed" and len(sonnet.calls) == before + 1, \
        "flap re-fire must not merge into the old job"
    wait_for(lambda: len(sonnet.calls) >= before + 1, desc="flap diagnosis")
    mod._diagnosing.pop(key_old, None)

    # malformed alerts (non-list) -> ignored, no 500
    r = client.post("/webhook/grafana", json={"status": "firing", "alerts": {"x": 1}})
    results["malformed_alerts"] = (r.status_code, r.json().get("action"))
    assert r.status_code == 200 and r.json()["action"] == "ignored-malformed"

    # empty alerts -> ignored
    r = client.post("/webhook/grafana", json={"status": "firing", "alerts": []}).json()
    results["empty_alerts"] = r["action"]
    assert r["action"] == "ignored-empty"
    return results


def main():
    here = Path(__file__).resolve().parent
    base = run_baseline(str(here / "baseline_webhook.py"))
    ctx = run_candidate(str(here / "candidate_webhook.py"))
    branches = branch_tests(ctx)
    cand_calls_main = ctx["sonnet_calls"]

    print("=== BASELINE (9 deliveries) ===")
    print(f"sonnet calls: {base['sonnet_calls']}, telegrams: {len(base['telegrams'])}")
    print("=== CANDIDATE (same 9 deliveries) ===")
    print(f"sonnet calls: {cand_calls_main}, telegrams: {len(ctx['telegrams'])}")
    print(f"actions: {ctx['actions']}")
    print("=== BRANCH TESTS ===")
    for k, v in branches.items():
        print(f"  {k}: {v}")

    assert base["sonnet_calls"] == 9, f"baseline expected 9, got {base['sonnet_calls']}"
    assert cand_calls_main == 3, f"candidate expected 3, got {cand_calls_main}"
    assert ctx["actions"] == (["diagnosed"] + ["merged-duplicate"] * 5 +
                              ["resolved-notice", "diagnosed", "diagnosed"]), ctx["actions"]
    for arm in (base, {"call_details": ctx["call_details"]}):
        for call in arm["call_details"]:
            assert call["model"] == "claude-sonnet-4-6", call
            assert call["max_tokens"] == 600, call
    assert {c["system"] for c in base["call_details"]} == {c["system"] for c in ctx["call_details"]}
    notices = [m for m in ctx["telegrams"] if m.startswith("RESOLVED")]
    assert len(notices) == 1 and "api-1" in notices[0], ctx["telegrams"]

    avoided = base["sonnet_calls"] - cand_calls_main
    avg_chars = sum(c["prompt_chars"] for c in ctx["call_details"]) / len(ctx["call_details"])
    est_per_call = (avg_chars / 4 / 1e6) * 3 + (400 / 1e6) * 15
    print(f"\nsonnet calls avoided (identical sequences): {avoided} of {base['sonnet_calls']}")
    print(f"avg prompt ~{avg_chars:.0f} chars -> est ~${est_per_call:.4f}/call "
          "(Sonnet $3/$15 per 1M; illustrative, real prompts vary)")
    print("ALL REPLAY ASSERTIONS PASSED")

    (here / "replay-results.json").write_text(json.dumps({
        "baseline_calls": base["sonnet_calls"],
        "candidate_calls": cand_calls_main,
        "avoided": avoided,
        "candidate_actions": ctx["actions"],
        "branch_tests": {k: str(v) for k, v in branches.items()},
        "est_per_call_usd": round(est_per_call, 4),
        "note": "Dollar figure is illustrative from stub prompt size; "
                "independent reviewers recomputed $0.008-$0.025/call for real prompts. "
                "Realized savings depend on unmeasured live traffic mix.",
    }, indent=2))


if __name__ == "__main__":
    main()
