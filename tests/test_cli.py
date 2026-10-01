"""Tests for agentpnl.cli.main.

If agentpnl.importers is not ready yet, the fixture path is exercised via
monkeypatched stand-ins rather than failing the suite.
"""

import json
import sys

import pytest

agentpnl = pytest.importorskip("agentpnl")
from agentpnl.cli import main  # noqa: E402


def _fixture_jsonl(path):
    # EVENT schema from agentpnl.importers.common (the real importer path).
    events = [
        {"type": "start", "case_id": "F-1"},
        {"type": "model", "case_id": "F-1", "provider": "anthropic",
         "model": "claude-sonnet-4-5", "input_tokens": 3200, "output_tokens": 850},
        {"type": "tool", "case_id": "F-1", "name": "crm_lookup"},
        {"type": "end", "case_id": "F-1", "success": True, "business_value": 11.20},
        {"type": "start", "case_id": "F-2"},
        {"type": "model", "case_id": "F-2", "provider": "openai",
         "model": "gpt-5.6-mini", "input_tokens": 20000, "output_tokens": 3000},
        {"type": "end", "case_id": "F-2", "success": False},
    ]
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return str(path)


def _fake_tracker():
    from agentpnl import Tracker
    t = Tracker("fixture-bot")
    t.start_attempt(case_id="F-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 3200, 850)
    t.log_tool_call("crm_lookup")
    t.end_attempt(success=True, business_value=11.20)
    t.start_attempt(case_id="F-2")
    t.log_model_call("openai", "gpt-5.6-mini", 20000, 3000)
    t.end_attempt(success=False)
    return t


def _install_fake_importer(monkeypatch):
    """Install stand-in importer modules; returns the tracker built."""
    import types
    import agentpnl.cli as cli_mod

    ledger_holder = {}

    def fake_load_jsonl(path):
        with open(path) as f:
            events = [json.loads(l) for l in f if l.strip()]
        t = _fake_tracker()
        from agentpnl.policy import export_ledger
        import tempfile
        tmp = tempfile.mktemp(suffix=".json")
        export_ledger(t, tmp)
        ledger = json.load(open(tmp))
        ledger_holder["tracker"] = t
        return ledger

    jsonl_mod = types.ModuleType("agentpnl.importers.jsonl")
    jsonl_mod.load_jsonl = fake_load_jsonl
    common_mod = types.ModuleType("agentpnl.importers.common")
    common_mod.tracker_from_ledger = lambda ledger: ledger_holder["tracker"]

    importers_pkg = types.ModuleType("agentpnl.importers")
    importers_pkg.jsonl = jsonl_mod
    importers_pkg.common = common_mod

    monkeypatch.setitem(sys.modules, "agentpnl.importers", importers_pkg)
    monkeypatch.setitem(sys.modules, "agentpnl.importers.jsonl", jsonl_mod)
    monkeypatch.setitem(sys.modules, "agentpnl.importers.common", common_mod)
    monkeypatch.setattr(cli_mod, "_importer_for",
                        lambda fmt: (fake_load_jsonl, "agentpnl.importers.jsonl")
                        if fmt == "jsonl" else (_ for _ in ()).throw(
                            ValueError("unsupported format")))


def _try_real_importer(monkeypatch):
    """Prefer the real importer path; fall back to fakes when absent."""
    try:
        import importlib
        importlib.import_module("agentpnl.importers.jsonl")
        importlib.import_module("agentpnl.importers.common")
        return True
    except ImportError:
        _install_fake_importer(monkeypatch)
        return False


def test_trace_jsonl_exit0(tmp_path, monkeypatch, capsys):
    trace = _fixture_jsonl(tmp_path / "trace.jsonl")
    monkeypatch.chdir(tmp_path)
    _try_real_importer(monkeypatch)
    rc = main(["trace", trace, "--format", "jsonl", "--agent", "fixture-bot"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Agent P&L" in out
    html_file = tmp_path / "trace.html"
    assert html_file.exists()
    assert "fixture-bot" in html_file.read_text(encoding="utf-8")


def test_trace_policy_flags(tmp_path, monkeypatch, capsys):
    trace = _fixture_jsonl(tmp_path / "trace2.jsonl")
    monkeypatch.chdir(tmp_path)
    _try_real_importer(monkeypatch)
    rc = main(["trace", trace, "--format", "jsonl", "--policy-cap", "0.01",
               "--html", str(tmp_path / "custom.html")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Policy replay" in out
    assert (tmp_path / "custom.html").exists()


def test_missing_file_exit2(capsys):
    rc = main(["trace", "/no/such/file.jsonl", "--format", "jsonl"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err


def test_bad_format_flag_exit2(capsys):
    try:
        main(["trace", "x", "--format", "xml"])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("expected SystemExit(2) from bad --format")
