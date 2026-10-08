"""Unit tests for the deployment gate (no API keys, no battery, no HTTP).

resolve_ticket and the Tracker ledger are stubbed; the gate's decision
contract and async job layer are what's under test.
"""
import hashlib
import hmac
import json
import os
import sys

import pytest

SUPPORT = os.path.join(os.path.dirname(__file__), "..", "benchmark", "support")
sys.path.insert(0, SUPPORT)
sys.path.insert(0, os.path.join(SUPPORT, "gate"))

import support_agent
import gate_service


def _task(i, label="HOWTO"):
    return {"id": f"x#{i}", "title": "t", "body": "b",
            "resolution_label": label, "resolution_summary": "s",
            "reopened": False, "time_to_close_hours": 1.0,
            "sla_breach": False}


BASE = {"version": "prod-v3"}          # current approved production config
CAND = {"version": "cand-v4"}         # proposed config


@pytest.fixture
def stubbed(monkeypatch):
    """Stub the agent (canned correct predictions) and an accumulating
    ledger: each fake call adds $0.025."""
    state = {"cost": 0.0}

    def fake_resolve(task, **kw):
        state["cost"] += 0.025
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    monkeypatch.setattr(support_agent, "client", object())
    return fake_resolve


def _thr(**kw):
    t = {"max_cost_per_correctly_classified": 0.05,
         "min_acceptance_rate": 0.5}
    t.update(kw)
    return t


def _eval(*a, **kw):
    kw.setdefault("mode", "mock")
    return gate_service.evaluate(*a, **kw)


def test_mock_never_approves(stubbed):
    # Even when the hypothetical passes, mock output must not approve.
    tasks = [_task(i) for i in range(4)]
    d = _eval("c1", BASE, CAND, _thr(
        max_cost_per_correctly_classified=99.0), tasks)
    assert d["pass"] is False
    assert d["would_pass"] is True
    assert "NEVER" in d["note"]


def test_would_pass_reflects_decision_math(stubbed):
    tasks = [_task(i) for i in range(4)]  # 4 correct, $0.10 -> $0.025 each
    d = _eval("c2", BASE, CAND, _thr(), tasks)
    assert d["would_pass"] is True
    assert d["violations"] == []
    assert d["candidate"]["cost_per_correctly_classified"] == pytest.approx(
        0.025)
    assert d["baseline"]["cost_per_correctly_classified"] == pytest.approx(
        0.025)
    assert d["delta"]["acceptance_rate_pp"] == pytest.approx(0.0)


def test_null_threshold_fails_closed():
    # An explicit null cost limit must not disable the check.
    with pytest.raises(ValueError, match="must be a number"):
        _eval("c3", BASE, CAND,
              {"max_cost_per_correctly_classified": None,
               "min_acceptance_rate": 0.5}, [_task(0)])


def test_nan_threshold_fails_closed():
    with pytest.raises(ValueError, match="must be finite"):
        _eval("c4", BASE, CAND,
              {"max_cost_per_correctly_classified": float("nan"),
               "min_acceptance_rate": 0.5}, [_task(0)])


def test_non_numeric_threshold_fails_closed():
    with pytest.raises(ValueError, match="must be a number"):
        _eval("c5", BASE, CAND,
              {"max_cost_per_correctly_classified": "cheap",
               "min_acceptance_rate": 0.5}, [_task(0)])


def test_fail_when_candidate_over_threshold(stubbed):
    tasks = [_task(i) for i in range(4)]
    d = _eval("c6", BASE, CAND, _thr(
        max_cost_per_correctly_classified=0.01), tasks)
    assert d["would_pass"] is False
    assert any("exceeds threshold" in v for v in d["violations"])


def test_fail_when_candidate_accepts_nothing(monkeypatch):
    state = {"cost": 0.0}

    def fake_resolve(task, **kw):
        state["cost"] += 0.025
        if kw.get("final_system"):  # candidate prompt breaks it
            return ({"resolution_label": "WONTFIX", "response_draft": ""},
                    None)
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(i) for i in range(4)]
    d = _eval("c7", BASE, {"version": "bad", "prompt": "be wrong"},
              _thr(max_cost_per_correctly_classified=99.0), tasks)
    assert d["would_pass"] is False
    assert any("zero correct" in v for v in d["violations"])
    assert d["baseline"]["accepted"] == 4  # baseline unaffected


def test_fail_on_acceptance_regression(monkeypatch):
    state = {"cost": 0.0}

    def fake_resolve(task, **kw):
        state["cost"] += 0.025
        if kw.get("final_system") and int(task["id"].split("#")[1]) % 2:
            return ({"resolution_label": "WONTFIX", "response_draft": ""},
                    None)
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(i) for i in range(4)]
    d = _eval("c8", BASE, {"version": "half", "prompt": "be half wrong"},
              _thr(max_cost_per_correctly_classified=99.0,
                   min_acceptance_rate=0.0), tasks)
    assert d["would_pass"] is False
    assert any("regressed" in v for v in d["violations"])
    assert d["delta"]["acceptance_rate_pp"] == pytest.approx(-50.0)


def test_decision_binds_configs():
    # The decision must identify exactly which configs were evaluated.
    d = _eval("c9", {"version": "prod-v3", "model": "m1"},
              {"version": "cand-v4", "model": "m2"},
              _thr(max_cost_per_correctly_classified=99.0), [_task(0)])
    assert d["baseline"]["config_version"] == "prod-v3"
    assert d["candidate"]["config_version"] == "cand-v4"
    assert d["baseline"]["config_hash"] != d["candidate"]["config_hash"]
    assert d["policy_rev"] == "default"
    # same inputs -> same hashes (immutable binding)
    d2 = _eval("c9", {"version": "prod-v3", "model": "m1"},
               {"version": "cand-v4", "model": "m2"},
               _thr(max_cost_per_correctly_classified=99.0), [_task(0)])
    assert d["candidate"]["config_hash"] == d2["candidate"]["config_hash"]


def test_build_variant_passes_overrides(monkeypatch):
    seen = {}

    def fake_resolve(task, model_haiku=None, model_sonnet=None,
                     final_system=None):
        seen.update(haiku=model_haiku, sonnet=model_sonnet,
                    prompt=final_system)
        return ({"resolution_label": "HOWTO", "response_draft": ""}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    fn = gate_service.build_variant({"model": "m2", "prompt": "p2",
                                     "haiku_model": "h2"})
    fn(_task(0))
    assert seen == {"haiku": "h2", "sonnet": "m2", "prompt": "p2"}


def test_live_without_key_raises():
    mp = pytest.MonkeyPatch()
    mp.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            _eval("c10", BASE, CAND, _thr(), [_task(0)], mode="live")
    finally:
        mp.undo()


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        _eval("c11", BASE, CAND, _thr(), [_task(0)], mode="nope")


def test_hmac_enforced_when_secret_set(monkeypatch):
    monkeypatch.setenv("AVERTH_GATE_HMAC_SECRET", "s3cret")
    h = gate_service.Handler.__new__(gate_service.Handler)
    body = b'{"change_id":"x"}'
    good = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    h.headers = {"X-Averth-Signature": good}
    assert h._check_hmac(body) is True
    h.headers = {"X-Averth-Signature": "wrong"}
    assert h._check_hmac(body) is False


def test_auth_required_for_evaluations(monkeypatch):
    # No secret and no explicit insecure flag -> evaluations refused.
    monkeypatch.delenv("AVERTH_GATE_HMAC_SECRET", raising=False)
    monkeypatch.delenv("AVERTH_GATE_ALLOW_INSECURE", raising=False)
    h = gate_service.Handler.__new__(gate_service.Handler)
    assert gate_service._auth_ok(h) is False
    monkeypatch.setenv("AVERTH_GATE_ALLOW_INSECURE", "1")
    assert gate_service._auth_ok(h) is True


def test_client_restored_after_mock_eval(stubbed):
    sentinel = object()
    support_agent.client = sentinel
    _eval("c12", BASE, CAND, _thr(
        max_cost_per_correctly_classified=99.0), [_task(0)])
    assert support_agent.client is sentinel


def test_async_submit_and_wait(stubbed):
    tasks = [_task(i) for i in range(2)]
    job_id = gate_service.submit_evaluation(
        "c13", BASE, CAND, _thr(max_cost_per_correctly_classified=99.0),
        tasks, "mock")
    job = gate_service.wait_job(job_id, timeout_s=30)
    assert job is not None
    assert job["status"] == "done"
    assert job["result"]["would_pass"] is True
    assert job["result"]["pass"] is False  # mock never approves
    assert job["result"]["candidate"]["accepted"] == 2


def test_async_unknown_job_is_none():
    assert gate_service.get_job("nope-not-real") is None


def test_eviction_never_drops_running_job(monkeypatch):
    # Fill the store with terminal jobs, then verify a running job
    # survives eviction pressure.
    monkeypatch.setattr(gate_service, "_MAX_JOBS", 3)
    for i in range(3):
        jid = gate_service.submit_evaluation(
            f"e{i}", BASE, CAND, _thr(
                max_cost_per_correctly_classified=99.0),
            [_task(0)], "mock")
        gate_service.wait_job(jid, timeout_s=30)
    jid4 = gate_service.submit_evaluation(
        "e3", BASE, CAND, _thr(max_cost_per_correctly_classified=99.0),
        [_task(0)], "mock")
    assert gate_service.get_job(jid4) is not None
    job = gate_service.wait_job(jid4, timeout_s=30)
    assert job["status"] == "done"
