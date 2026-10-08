"""Unit tests for the deployment gate (no API keys, no battery, no HTTP).

resolve_ticket and the Tracker ledger are stubbed; the gate's decision
math is what's under test.
"""
import hashlib
import hmac
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


@pytest.fixture
def stubbed(monkeypatch):
    """Stub the agent (canned correct predictions) and an accumulating
    ledger: each fake model call adds $0.025."""
    state = {"cost": 0.0}

    def fake_resolve(task):
        state["cost"] += 0.025
        return ({"resolution_label": task["resolution_label"],
                 "response_draft": "draft"}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    monkeypatch.setattr(support_agent, "client", object())
    return fake_resolve


def test_pass_when_under_threshold(stubbed):
    tasks = [_task(i) for i in range(4)]  # 4 accepted, $0.10 -> $0.025 each
    d = gate_service.evaluate("c1", {"model": "m"}, {
        "max_cost_per_acceptable_resolution": 0.05,
        "min_acceptance_rate": 0.5}, tasks, mode="mock")
    assert d["pass"] is True
    assert d["violations"] == []
    assert d["cost_per_acceptable_resolution"] == pytest.approx(0.025)
    assert d["mode"] == "mock"
    assert "MOCK" in d["note"]


def test_fail_when_over_cost_threshold(stubbed):
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c2", {}, {
        "max_cost_per_acceptable_resolution": 0.01,  # $0.025 > $0.01
        "min_acceptance_rate": 0.5}, tasks, mode="mock")
    assert d["pass"] is False
    assert any("exceeds threshold" in v for v in d["violations"])


def test_fail_when_acceptance_below_floor(monkeypatch):
    state = {"cost": 0.0}

    def fake_resolve(task):
        # wrong label on every ticket
        state["cost"] += 0.025
        return ({"resolution_label": "WONTFIX", "response_draft": ""}, None)
    monkeypatch.setattr(support_agent, "resolve_ticket", fake_resolve)
    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(i) for i in range(4)]
    d = gate_service.evaluate("c3", {}, {
        "max_cost_per_acceptable_resolution": 99.0,
        "min_acceptance_rate": 0.5}, tasks, mode="mock")
    assert d["pass"] is False
    assert any("zero accepted resolutions" in v for v in d["violations"])


def test_live_without_key_raises():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            gate_service.evaluate("c4", {}, {}, [_task(0)], mode="live")
    finally:
        monkeypatch.undo()


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        gate_service.evaluate("c5", {}, {}, [_task(0)], mode="nope")


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
    gate_service.evaluate("c6", {}, {
        "max_cost_per_acceptable_resolution": 99.0,
        "min_acceptance_rate": 0.0}, [_task(0)], mode="mock")
    assert support_agent.client is sentinel


def test_agent_fn_injection_used(monkeypatch):
    """A proposed-config variant can be shadow-tested via agent_fn."""
    calls = []
    state = {"cost": 0.0}

    def variant_agent(task):
        calls.append(task["id"])
        state["cost"] += 0.01
        return ({"resolution_label": "CONFIG", "response_draft": ""}, None)

    monkeypatch.setattr(support_agent.TRACKER, "pnl",
                        lambda: {"cost_total": state["cost"]})
    tasks = [_task(0, label="CONFIG"), _task(1, label="CONFIG")]
    d = gate_service.evaluate("c7", {"prompt_version": "v99"}, {
        "max_cost_per_acceptable_resolution": 99.0,
        "min_acceptance_rate": 0.0}, tasks, mode="mock",
        agent_fn=variant_agent)
    assert calls == ["x#0", "x#1"]
    assert d["accepted"] == 2
    assert d["pass"] is True
