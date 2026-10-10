"""Tests for the runaway lens: cost-anomaly detection, never attack claims."""
import subprocess
import sys

from averth import Tracker
from averth.insights import anomalies, anomalies_text


def _tracker_with_runaway():
    t = Tracker("x")
    # 20 normal attempts
    for i in range(20):
        t.start_attempt(case_id=f"ok-{i}")
        t.log_model_call("openai", "gpt-5.6", 1000, 500)
        t.end_attempt(success=True)
    # 1 runaway: 50 retries
    t.start_attempt(case_id="runaway-1")
    t.log_model_call("openai", "gpt-5.6", 1000, 500)
    for _ in range(50):
        t.log_retry("timeout", extra_model_cost=0.05)
    t.end_attempt(success=False)
    return t


def test_no_anomalies_on_clean_ledger():
    t = Tracker("x")
    for i in range(25):
        t.start_attempt(case_id=f"c{i}")
        t.log_model_call("openai", "gpt-5.6", 1000, 500)
        t.end_attempt(success=True)
    assert anomalies(t.pnl()) == []


def test_runaway_flagged():
    ans = anomalies(_tracker_with_runaway().pnl())
    assert len(ans) >= 1
    top = ans[0]
    assert "runaway-1" in top["title"]
    assert top["severity"] in ("high", "medium")


def test_never_claims_attack():
    ans = anomalies(_tracker_with_runaway().pnl())
    text = anomalies_text(_tracker_with_runaway().pnl()).lower()
    for word in ("attack", "malicious", "hacker", "intrusion", "threat actor"):
        assert word not in text, f"forbidden word: {word}"
    assert "inspect" in text


def test_materiality_floor():
    t = Tracker("x")
    t.start_attempt(case_id="c1")
    t.log_model_call("openai", "gpt-5.6", 10, 5)  # pennies
    t.end_attempt(success=True)
    assert anomalies(t.pnl()) == []


def test_anomalies_ranked_by_dollars():
    ans = anomalies(_tracker_with_runaway().pnl())
    dollars = [a["dollars"] for a in ans]
    assert dollars == sorted(dollars, reverse=True)


def test_cli_anomaly_flag(tmp_path):
    import json
    trace = tmp_path / "t.json"
    trace.write_text(json.dumps({"data": [{"id": "t1", "observations": [
        {"id": "g1", "type": "GENERATION", "model": "gpt-5.6",
         "level": "DEFAULT",
         "usageDetails": {"input": 100, "output": 50},
         "metadata": {}}]}]}))
    r = subprocess.run(
        [sys.executable, "-m", "averth.cli", "trace", str(trace),
         "--format", "langfuse", "--anomaly"],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert "Suspicious attempts" in r.stdout or "No runaway-shaped" in r.stdout
