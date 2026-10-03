"""Tests for averth.cli.main."""

import json

import pytest

averth = pytest.importorskip("averth")
from averth.cli import main  # noqa: E402


def _fixture_jsonl(path):
    # EVENT schema from averth.importers.common (the real importer path).
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


def test_trace_jsonl_exit0(tmp_path, monkeypatch, capsys):
    trace = _fixture_jsonl(tmp_path / "trace.jsonl")
    monkeypatch.chdir(tmp_path)
    rc = main(["trace", trace, "--format", "jsonl", "--agent", "fixture-bot"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Averth" in out
    html_file = tmp_path / "trace.html"
    assert html_file.exists()
    assert "fixture-bot" in html_file.read_text(encoding="utf-8")


def test_trace_policy_flags(tmp_path, monkeypatch, capsys):
    trace = _fixture_jsonl(tmp_path / "trace2.jsonl")
    monkeypatch.chdir(tmp_path)
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


def test_bad_html_path_exit2(tmp_path, capsys):
    # A typo'd --html directory must honor the CLI error contract: clean
    # "averth: error:" on stderr and exit 2, never a traceback.
    trace = _fixture_jsonl(tmp_path / "trace3.jsonl")
    rc = main(["trace", trace, "--format", "jsonl",
               "--html", "/no/such/dir/x.html"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "averth: error: cannot write HTML report" in err


def test_console_script_entry_point_resolves():
    # pyproject declares [project.scripts] averth = "averth.cli:main".
    # The installed entry point must resolve to a callable; a stale or
    # missing install (the pre-rename agentpnl dist-info shipped in .venv
    # for a while) silently breaks the documented `averth` command.
    from importlib.metadata import distribution, PackageNotFoundError
    try:
        dist = distribution("averth")
    except PackageNotFoundError:
        pytest.skip("averth not installed in this interpreter")
    eps = [ep for ep in dist.entry_points if ep.name == "averth"]
    assert eps, "averth console script not installed"
    assert callable(eps[0].load())


def test_pricing_exit0(capsys):
    # The C2 user-facing fix: `averth pricing` shows the table version,
    # verification date, and staleness status.
    from averth import pricing
    rc = main(["pricing"])
    out = capsys.readouterr().out
    assert rc == 0
    assert ("Averth price table v%s" % pricing.PRICE_TABLE_VERSION) in out
    assert pricing.PRICE_TABLE_UPDATED in out
    assert "models priced : %d" % len(pricing.MODEL_PRICES) in out
    assert "tools priced  : %d" % len(pricing.TOOL_PRICES) in out
    assert "To update:" in out
