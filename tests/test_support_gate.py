"""Unit tests for the deployment gate (no API keys, no battery, no HTTP).

resolve_ticket and the Tracker ledger are stubbed; the gate's decision
math and async job layer are what's under test.
"""
import hashlib
import hmac
import os
import sys
import time

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


@pytest.fixture
def stubbed(monkeypatch):
    """Stub the agent (canned correct predictions) and an accumulating
    ledger: each fake model call adds $0.025."""
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
    t = {"max_cost_per_acceptable_resolution": 0.05,
         "min_acceptance_rate": 0.5}
    t.update(kw)
    return t


def test_pass_when_proposed_within_threshold(stubbed):
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c1", {}, _thr(), tasks, mode="mock")
    assert d["pass"] is True
    assert d["violations"] == []
    assert d["proposed"]["cost_per_acceptable_resolution"] == pytest.approx(
        0.025)
    assert d["baseline"]["cost_per_acceptable_resolution"] == pytest.approx(
        0.025)
    assert d["delta"]["acceptance_rate_pp"] == pytest.approx(0.0)
    assert d["mode"] == "mock"
    assert "MOCK" in d["note"]


def test_fail_when_proposed_over_threshold(stubbed):
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c2", {}, _thr(
        max_cost_per_acceptable_resolution=0.01), tasks, mode="mock")
    assert d["pass"] is False
    assert any("exceeds threshold" in v for v in d["violations"])


def test_fail_when_proposed_accepts_nothing(monkeypatch):
    state = {"cost": 0.0}

    def fake_resolve(task, **kw):
        state["cost"] += 0.025
        # baseline correct, but the variant (prompt override present)
        # breaks: distinguish via kw
        if kw.get("final_system"):
            return ({"resolution_label": "WONTFIX", "response_draft": ""},
                    None)
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c3", {"prompt": "be wrong"}, _thr(
        max_cost_per_acceptable_resolution=99.0), tasks, mode="mock")
    assert d["pass"] is False
    assert any("zero accepted resolutions" in v for v in d["violations"])
    assert d["baseline"]["accepted"] == 4  # baseline unaffected


def test_fail_on_acceptance_regression(monkeypatch):
    state = {"cost": 0.0}

    def fake_resolve(task, **kw):
        state["cost"] += 0.025
        # variant gets half right -> 50pp regression vs baseline
        if kw.get("final_system") and int(task["id"].split("#")[1]) % 2:
            return ({"resolution_label": "WONTFIX", "response_draft": ""},
                    None)
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c4", {"prompt": "be half wrong"},
                              _thr(max_cost_per_acceptable_resolution=99.0,
                                   min_acceptance_rate=0.0),
                              tasks, mode="mock")
    assert d["pass"] is False
    assert any("regressed" in v for v in d["violations"])
    assert d["delta"]["acceptance_rate_pp"] == pytest.approx(-50.0)


def test_build_variant_passes_overrides(monkeypatch):
    seen = {}

    def fake_resolve(task, model_haiku=None, model_sonnet=None,
                     final_system=None):
        seen["haiku"] = model_haiku
        seen["sonnet"] = model_sonnet
        seen["prompt"] = final_system
        return ({"resolution_label": "HOWTO", "response_draft": ""}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    fn = gate_service.build_variant({"model": "m2", "prompt": "p2",
                                     "haiku_model": "h2"})
    fn(_task(0))
    assert seen == {"haiku": "h2", "sonnet": "m2", "prompt": "p2"}
    # defaults fall back to pinned arm A
    fn2 = gate_service.build_variant({})
    fn2(_task(0))
    assert seen["sonnet"] == support_agent.SONNET
    assert seen["prompt"] is None


def test_live_without_key_raises():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            gate_service.evaluate("c5", {}, {}, [_task(0)], mode="live")
    finally:
        monkeypatch.undo()


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        gate_service.evaluate("c6", {}, {}, [_task(0)], mode="nope")


def test_hmac_enforced_when_secret_set(monkeypatch):
    monkeypatch.setenv("AVERTH_GATE_HMAC_SECRET", "s3cret")
    h = gate_service.Handler.__new__(gate_service.Handler)
    body = b'{"change_id":"x"}'
    good = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    h.headers = {"X-Averth-Signature": good}
    assert h._check_hmac(body) is True
    h.headers = {"X-Averth-Signature": "wrong"}
    assert h._check_hmac(body) is False


def test_hmac_open_when_no_secret(monkeypatch):
    monkeypatch.delenv("AVERTH_GATE_HMAC_SECRET", raising=False)
    h = gate_service.Handler.__new__(gate_service.Handler)
    h.headers = {}
    assert h._check_hmac(b"anything") is True


def test_client_restored_after_mock_eval(stubbed):
    sentinel = object()
    support_agent.client = sentinel
    gate_service.evaluate("c7", {}, _thr(
        max_cost_per_acceptable_resolution=99.0), [_task(0)], mode="mock")
    assert support_agent.client is sentinel


def test_async_submit_and_wait(stubbed):
    tasks = [_task(i) for i in range(2)]
    job_id = gate_service.submit_evaluation(
        "c8", {}, _thr(max_cost_per_acceptable_resolution=99.0),
        tasks, "mock")
    job = gate_service.wait_job(job_id, timeout_s=30)
    assert job is not None
    assert job["status"] == "done"
    assert job["result"]["pass"] is True
    assert job["result"]["proposed"]["accepted"] == 2


def test_async_unknown_job_is_none():
    assert gate_service.get_job("nope-not-real") is None
