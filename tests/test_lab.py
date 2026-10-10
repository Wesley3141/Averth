"""Tests for averth.lab: the workflow-change verification harness."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from averth.lab import (
    Case,
    RealBackend,
    StubBackend,
    Usage,
    cost_for,
    human_judged,
    keyword_coverage,
    render,
    run_experiment,
)


def _case(cid="c1"):
    return Case(cid, {}, "fix-cmd", ("cause", "impact"))


def _arm(text, usage, action="fix-cmd"):
    def fn(case, model):
        return action, text, usage, {}
    return fn


def test_stub_backend_deterministic():
    s = StubBackend()
    assert s.generate("hi", tag="t") == s.generate("hi", tag="t")
    assert len(s.calls) == 2


def test_real_backend_refuses_without_credentials():
    try:
        RealBackend("x", "y")
    except RuntimeError:
        return
    raise AssertionError("must refuse without api_key")


def test_verdict_fails_closed_on_action_change():
    rep = run_experiment(
        "t", _arm("explanation text here", Usage(10, 10)),
        _arm("explanation text here", Usage(0, 0), action="OTHER"),
        [_case()], keyword_coverage, cost_for, StubBackend())
    assert rep.verdict() == "candidate changes behavior: do not ship"
    assert rep.actions_preserved == 0


def test_verdict_passes_when_behavior_preserved():
    rep = run_experiment(
        "t", _arm("cause and impact discussed", Usage(100, 50)),
        _arm("cause and impact discussed", Usage(0, 0)),
        [_case()], keyword_coverage, cost_for, StubBackend())
    assert rep.actions_preserved == 1 and rep.quality_preserved == 1
    assert "saves money" in rep.verdict()


def test_quality_proxy_labeled():
    q = keyword_coverage(_case(), "fix-cmd", "covers cause and impact", {})
    assert q["_proxy"] is True and q["action_correct"] is True


def test_human_judged_missing_case_fails_closed():
    q = human_judged({})(_case("nope"), "fix-cmd", "text", {})
    assert q["judged"] is False and q["action_correct"] is False


def test_cost_math():
    assert abs(cost_for(Usage(1000, 1000), "sonnet-class") - 0.018) < 1e-9
    assert cost_for(Usage(10 ** 9, 10 ** 9), "stub") == 0.0


def test_render_marks_stub_backend():
    rep = run_experiment("t", _arm("cause impact", Usage(10, 10)), _arm("cause impact", Usage(0, 0)),
                         [_case()], keyword_coverage, cost_for, StubBackend())
    text = render(rep)
    assert "stub backend" in text and "verdict:" in text
