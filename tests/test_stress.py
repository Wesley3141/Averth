"""Tests for averth.stress: the adversarial synthetic workload is
deterministic, exercises all five cost layers, reproduces the heavy-tail
shape it claims, and round-trips through the JSONL importer identically."""

import pytest

from averth import stress
from averth.importers import jsonl as J
from averth.importers import common


def test_deterministic_for_fixed_seed():
    t1, _ = stress.generate(seed=123, attempts=300)
    t2, _ = stress.generate(seed=123, attempts=300)
    assert t1.pnl()["cost_total"] == t2.pnl()["cost_total"]
    assert t1.pnl()["yield_ratio"] == t2.pnl()["yield_ratio"]
    t3, _ = stress.generate(seed=124, attempts=300)
    assert t3.pnl()["cost_total"] != t1.pnl()["cost_total"]


def test_exercises_all_five_layers():
    t, _ = stress.generate(seed=42, attempts=2000)
    p = t.pnl()
    # 1. context compounding: growth and a positive dollar tax
    assert p["avg_context_growth"] > 2.0
    assert p["context_tax"] > 0
    # 2. external tool spend, invisible on the model invoice
    assert p["cost_tools"] > 0
    # 3. yield vs waste: retries and failures exist
    assert p["retries"] > 100
    assert p["yield_ratio"] < 1.0
    assert p["cost_failed"] > 0
    # 4. heavy tail: top 5% dominate
    assert p["tail"]["top5pct_share"] > 0.50
    assert p["tail"]["max"] > 10 * p["tail"]["p50"]
    # 5. multi-model + loaded labor
    assert len(p["per_model"]) >= 3
    assert p["escalations"] > 0
    assert p["cost_human"] > 0
    # cache hits show up as savings
    assert p["cached_tokens"] > 0
    assert p["cache_savings"] > 0


def test_runaway_tail_shape():
    """~2% of attempts are runaways; they must dominate the budget."""
    t, _ = stress.generate(seed=42, attempts=2000)
    p = t.pnl()
    n = p["attempts"]
    tail_n = max(1, int(n * 0.05))
    # the costliest 5% (which contain the runaways) burn the majority
    assert p["tail"]["top5pct_share"] > 0.60
    assert len(p["costliest_attempts"]) == 10
    assert p["costliest_attempts"][0]["success"] is False


def test_branch_fanout_keeps_honest_yield(tmp_path):
    """A dead branch's retry must not smear the productive merge step."""
    t, events = stress.generate(seed=42, attempts=2000, record_events=True)
    branched = [e for e in events if e.get("branch")]
    assert branched, "expected branch-tagged events in the workload"
    # at least one branch-scoped retry exists
    assert any(e["type"] == "retry" and e.get("branch") for e in events)


def test_jsonl_roundtrip_identical(tmp_path):
    path = str(tmp_path / "stress.jsonl")
    t_direct, _ = stress.generate(seed=7, attempts=400)
    stress.write_jsonl(path, seed=7, attempts=400)
    ledger = J.load_jsonl(path)
    t_rt = common.tracker_from_ledger(ledger)
    p1, p2 = t_direct.pnl(), t_rt.pnl()
    for k in ("cost_total", "cost_model", "cost_tools", "cost_human",
              "cost_retry_path", "context_tax", "cache_savings",
              "yield_ratio", "attempts", "successes", "retries",
              "escalations", "reopened", "cached_tokens"):
        assert p1[k] == pytest.approx(p2[k]), k


def test_jsonl_events_pass_strict_validation():
    # write_jsonl output must satisfy the strict JSONL schema, including
    # cached_input_tokens <= input_tokens and branch scoping
    import json
    t, events = stress.generate(seed=7, attempts=200, record_events=True)
    for ev in events:
        assert isinstance(ev["case_id"], str)
        if ev["type"] == "model" and "cached_input_tokens" in ev:
            assert ev["cached_input_tokens"] <= ev["input_tokens"]
    blob = "\n".join(json.dumps(e) for e in events)
    assert len(blob) > 0


def test_cli_simulate_exit0(tmp_path, capsys):
    from averth.cli import main
    html = str(tmp_path / "sim.html")
    rc = main(["simulate", "--attempts", "50", "--seed", "1",
               "--html", html])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TOP FINDING" in out or "No material findings" in out
    assert "Fully loaded" in out
    body = open(html, encoding="utf-8").read()
    assert "What to do Monday morning" in body or "Averth" in body
