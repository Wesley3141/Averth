"""Tests for the one-command try-it (``averth try``).

The fixture trajectory is the public case-study trace
(mini-SWE-agent v1.0.0, django__django-15930). Every number asserted
here is a published case-study number; a mismatch is a defect, not a
rounding note.
"""

import json
import os
import shutil

import pytest

averth = pytest.importorskip("averth")
from averth.cli import main  # noqa: E402
from averth.importers import common, miniswe  # noqa: E402
from averth import try_report  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "try-it", "fixtures")
TRAJ = os.path.join(FIXTURES, "django-15930.traj.json")
EVENTS = os.path.join(FIXTURES, "trace-events-django-15930.jsonl")
CHECKS = os.path.join(FIXTURES, "case-study-1-checks.json")
ALLOWLIST = os.path.join(FIXTURES, "case-study-1-allowlist.json")
LEDGER = os.path.join(REPO, "case-study-1", "v0-run", "evidence_ledger.json")
MODEL = "claude-sonnet-4-20250514"


def _fixture_events():
    with open(EVENTS, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pnl_for_traj():
    ledger = miniswe.load_miniswe(TRAJ, model=MODEL)
    return common.tracker_from_ledger(ledger).pnl()


# --- converter -------------------------------------------------------


def test_converter_reproduces_published_events():
    mine = miniswe.miniswe_events(TRAJ, model=MODEL)
    assert mine == _fixture_events()


def test_converter_model_inferred_from_path(tmp_path):
    named = tmp_path / ("django__django-15930_claude-sonnet-4-20250514"
                        ".traj.json")
    shutil.copy(TRAJ, named)
    assert miniswe.miniswe_events(str(named)) == _fixture_events()


def test_converter_missing_model_is_a_clean_error():
    with pytest.raises(ValueError, match="--model"):
        miniswe.miniswe_events(TRAJ, model=None)


def test_converter_rejects_non_trajectory(tmp_path):
    bad = tmp_path / "nope.json"
    bad.write_text(json.dumps({"data": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a mini-SWE-agent trajectory"):
        miniswe.miniswe_events(str(bad))


def test_converter_rejects_empty_messages(tmp_path):
    bad = tmp_path / "empty.traj.json"
    bad.write_text(json.dumps({"instance_id": "x", "messages": []}),
                   encoding="utf-8")
    with pytest.raises(ValueError, match="no messages"):
        miniswe.miniswe_events(str(bad))


def test_converter_missing_exit_status_is_outcome_unknown():
    traj = json.loads(open(TRAJ, encoding="utf-8").read())
    del traj["info"]["exit_status"]
    # Build events from the modified trajectory via a temp file.
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".traj.json",
                                     delete=False) as f:
        json.dump(traj, f)
        tmp = f.name
    try:
        evs = miniswe.miniswe_events(tmp, model=MODEL)
        assert not [e for e in evs if e["type"] == "end"]
        ledger = miniswe.load_miniswe(tmp, model=MODEL)
        tracker = common.tracker_from_ledger(ledger)
        assert tracker.pnl()["unknown_outcome"] == 1
    finally:
        os.unlink(tmp)


# --- meter numbers ---------------------------------------------------


def test_meter_numbers_match_the_published_case_study():
    p = _pnl_for_traj()
    assert p["attempts"] == 1
    assert p["successes"] == 1
    assert p["retries"] == 0
    assert round(p["cost_total"], 2) == 0.98
    assert round(p["cost_model"], 2) == 0.91
    assert round(p["cost_tools"], 2) == 0.07
    assert p["cost_billed"] == 0.0
    assert round(p["avg_context_growth"], 1) == 9.9
    assert round(p["context_tax"], 2) == 0.68
    dq = p["data_quality"]
    assert round(dq["measured"], 2) == 0.91
    assert round(dq["estimated"], 2) == 0.07
    assert dq["billed"] == 0.0


# --- V0 ledger --------------------------------------------------------


def test_v0_ledger_summary_matches_the_published_case_study():
    summary, verified = try_report.load_v0_ledger(LEDGER, CHECKS)
    assert verified is True
    assert summary["counts"] == {"VERIFIED": 2, "EXTERNAL-UNVERIFIABLE": 2}
    assert summary["unknown"] == 2
    assert summary["unknown_rate"] == 0.5
    assert summary["runs_total"] == 2
    assert summary["superseded_runs_retained"] == 0
    assert [j["status"] for j in summary["judgments"]] == [
        "VERIFIED", "VERIFIED", "EXTERNAL-UNVERIFIABLE",
        "EXTERNAL-UNVERIFIABLE",
    ]
    # Each judgment carries its cited observation.
    assert summary["judgments"][0]["criterion_text"] == (
        "the FAIL_TO_PASS test passes with the agent patch")
    assert "test_annotate_with_full_when" in summary["judgments"][0]["command"]
    assert summary["judgments"][0]["exit_code"] == 0
    assert summary["judgments"][0]["output_digest"].startswith("sha256:")


def test_v0_ledger_without_checks_is_labelled_unverified():
    summary, verified = try_report.load_v0_ledger(LEDGER)
    assert verified is None
    assert summary["counts"]["VERIFIED"] == 2


def test_v0_ledger_digest_mismatch_refuses(tmp_path):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        try_report.load_v0_ledger(LEDGER, str(tampered))


def test_v0_ledger_rejects_non_ledger(tmp_path):
    bad = tmp_path / "ledger.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(ValueError, match="not a V0 evidence ledger"):
        try_report.load_v0_ledger(str(bad))


def test_v0_ledger_rejects_malformed_shapes(tmp_path):
    def _write(obj):
        bad = tmp_path / "ledger.json"
        bad.write_text(json.dumps(obj), encoding="utf-8")
        return str(bad)

    with pytest.raises(ValueError, match="judgments"):
        try_report.load_v0_ledger(_write({"judgments": "oops"}))
    with pytest.raises(ValueError, match="judgments"):
        try_report.load_v0_ledger(_write({"judgments": [42]}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": "two"}}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": "high"}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": True}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": float("nan")}}))
    with pytest.raises(ValueError, match="unknown_rate"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown_rate": float("inf")}}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": float("nan")}}}))
    with pytest.raises(ValueError, match="counts"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {"VERIFIED": True}}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": "two"}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": True}}))
    with pytest.raises(ValueError, match="unknown"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "unknown": 1.5}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": "two"}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": True}}))
    with pytest.raises(ValueError, match="superseded"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {},
                         "superseded_runs_retained": 1.5}}))
    with pytest.raises(ValueError, match="runs_total"):
        try_report.load_v0_ledger(_write({
            "judgments": [],
            "coverage": {"counts": {}, "runs_total": "two"}}))
    missing = tmp_path / "nope.json"
    with pytest.raises(ValueError, match="--ledger"):
        try_report.load_v0_ledger(str(missing))
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        try_report.load_v0_ledger(str(bad_json))
    with pytest.raises(ValueError, match="--checks"):
        try_report.load_v0_ledger(LEDGER, str(missing))


# --- report extras ----------------------------------------------------


def test_try_extras_carry_the_published_comparison():
    p = _pnl_for_traj()
    summary, _ = try_report.load_v0_ledger(LEDGER, CHECKS)
    html = try_report.build_try_extras(
        p, recorded=0.3205, v0=summary, digest_verified=True,
        source_note="Trace: django-15930.traj.json (mini-SWE-agent "
        "trajectory). Token counts are characters/4 estimates from the "
        "trajectory text, not provider-recorded usage.")
    assert "3.07x" in html
    assert "$0.3205" in html
    assert "$0.98" in html
    assert "VERIFIED" in html
    assert "50.0%" in html
    assert "Checks digest verified" in html
    assert "no cost per accepted outcome is claimed" in html
    assert "characters/4 estimates" in html
    # Recorded is operator-supplied, never stated as fact.
    assert "operator-supplied" in html
    assert "The operator supplied $0.3205" in html
    # All five verdict rows render, zeros included.
    for verdict in ("VERIFIED", "FAILED", "NOT OBSERVED",
                    "EXTERNAL-UNVERIFIABLE", "NOT APPLICABLE"):
        assert verdict in html
    # V0 rows cite their observations.
    assert "the FAIL_TO_PASS test passes with the agent patch" in html
    assert "test_annotate_with_full_when" in html
    assert "exit 0" in html
    assert "output digest" in html
    assert "sha256:081d" in html
    assert "superseded and retained, never cited: 0" in html
    assert "report generated" in html


def test_try_extras_escape_source_note():
    p = _pnl_for_traj()
    html = try_report.build_try_extras(
        p, source_note='Trace: <img src=x onerror=alert(1)>.traj.json')
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_try_extras_reject_nonpositive_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=0.0)


def test_try_extras_reject_nonfinite_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=float("nan"))
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.build_try_extras(p, recorded=float("inf"))


def test_try_extras_recorded_cross_check():
    p = _pnl_for_traj()
    html = try_report.build_try_extras(
        p, recorded=0.3205, traj_recorded=0.32052914999999993)
    assert "agrees with the operator-supplied figure" in html
    html = try_report.build_try_extras(
        p, recorded=99.0, traj_recorded=0.32052914999999993)
    assert "differs from the operator-supplied" in html


def test_try_summary_lines():
    p = _pnl_for_traj()
    summary, verified = try_report.load_v0_ledger(LEDGER, CHECKS)
    lines = try_report.try_summary_lines(
        p, recorded=0.3205, v0=summary, digest_verified=verified,
        source_note="Trace: django-15930.traj.json (mini-SWE-agent "
        "trajectory). Token counts are characters/4 estimates.")
    assert any("3.07x" in line for line in lines)
    assert any("unknown rate 50.0%" in line for line in lines)
    assert any("characters/4 estimates" in line for line in lines)
    assert any("No human accepted this run" in line for line in lines)
    assert any("operator-supplied" in line for line in lines)
    assert any("checks digest verified" in line for line in lines)
    # All five verdicts, zeros included.
    v0_line = [l for l in lines if l.startswith("V0 verdicts:")][0]
    assert "FAILED 0" in v0_line
    assert "NOT OBSERVED 0" in v0_line


def test_try_summary_lines_unverified_digest():
    p = _pnl_for_traj()
    summary, _ = try_report.load_v0_ledger(LEDGER)
    lines = try_report.try_summary_lines(p, v0=summary)
    assert any("checks digest NOT verified" in line for line in lines)


def test_try_summary_lines_traj_recorded_cross_check():
    p = _pnl_for_traj()
    lines = try_report.try_summary_lines(
        p, recorded=0.3205, traj_recorded=0.32052914999999993)
    assert any("agrees with the operator-supplied figure" in line
               for line in lines)
    lines = try_report.try_summary_lines(
        p, recorded=99.0, traj_recorded=0.32052914999999993)
    assert any("WARNING: trajectory's own recorded cost is $0.3205"
               in line for line in lines)


def test_try_summary_lines_reject_bad_recorded():
    p = _pnl_for_traj()
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.try_summary_lines(p, recorded=0.0)
    with pytest.raises(ValueError, match="positive dollar figure"):
        try_report.try_summary_lines(p, recorded=float("nan"))


# --- CLI --------------------------------------------------------------


def test_try_traj_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--recorded", "0.3205",
               "--ledger", LEDGER, "--checks", CHECKS])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Fully loaded:         $0.98" in out
    assert "Retries:               0" in out
    assert "Recorded cost (operator-supplied): $0.3205" in out
    assert "3.07x" in out
    assert "unknown rate 50.0%" in out
    assert "Cost per completed run" in out
    assert "No human accepted this run" in out
    assert "characters/4 estimates" in out
    assert "checks digest verified" in out
    assert "FAILED 0" in out
    html_file = tmp_path / "django-15930-try.html"
    assert html_file.exists()
    html = html_file.read_text(encoding="utf-8")
    assert "Metered estimate vs recorded cost" in html
    assert "What the evidence supports (V0)" in html
    assert "characters/4 estimates" in html
    assert "http" not in html  # self-contained: no external references
    assert "per completed run" in html
    assert '<div class="s">per completed run</div>' in html
    assert "<h2>Cost per completed run</h2>" in html
    assert "operator-supplied" in html
    assert "Cited observation" in html
    assert "test_annotate_with_full_when" in html
    assert "output digest" in html


def test_try_auto_detects_traj_without_format_flag(tmp_path, monkeypatch,
                                                  capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL])
    assert rc == 0
    assert (tmp_path / "django-15930-try.html").exists()


def test_try_jsonl_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", EVENTS, "--format", "jsonl"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Fully loaded:         $0.98" in out
    assert (tmp_path / "trace-events-django-15930-try.html").exists()
    html = (tmp_path / "trace-events-django-15930-try.html").read_text(
        encoding="utf-8")
    # The default cost-basis line never claims reported token usage.
    assert "reported token/cache usage" not in html
    assert "trace-supplied token counts" in html


def test_try_digest_mismatch_writes_no_report(tmp_path, monkeypatch, capsys):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", str(tampered)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "digest mismatch" in err
    assert not (tmp_path / "django-15930-try.html").exists()


def test_try_checks_without_ledger_is_an_error(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--checks", CHECKS])
    assert rc == 2
    assert "--checks needs --ledger" in capsys.readouterr().err


def test_try_missing_model_is_a_clean_error(capsys):
    rc = main(["try", TRAJ])
    assert rc == 2
    assert "--model" in capsys.readouterr().err


def test_try_missing_file_is_an_error(capsys):
    rc = main(["try", "/no/such/trace.traj.json"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_try_bad_recorded_is_an_error(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--recorded", "0"])
    assert rc == 2
    assert "positive dollar figure" in capsys.readouterr().err

# --- model validation ------------------------------------------------


def test_try_unknown_model_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", "gpt-99-nonexistent"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "unknown model 'gpt-99-nonexistent'" in err
    assert "averth pricing" in err
    assert not (tmp_path / "django-15930-try.html").exists()


def test_try_typo_model_is_refused(capsys):
    rc = main(["try", TRAJ, "--model", "claude-sonnet-4-2025051"])
    assert rc == 2
    assert "unknown model" in capsys.readouterr().err


def test_pricing_lists_model_names(capsys):
    rc = main(["pricing"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "models priced : 35" in out
    assert "claude-sonnet-4-20250514" in out
    assert "gpt-4o" in out
    # Each bare name is listed once, even when priced under two keys.
    listed = [line.strip() for line in out.splitlines()
              if line.startswith("    ") and not line.strip().startswith("(")]
    assert len(listed) == len(set(listed))
    assert listed.count("glm-5") == 1


# --- format detection --------------------------------------------------


def test_detect_try_format_single_line_jsonl(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "one.jsonl"
    f.write_text('{"type": "model", "case_id": "x"}', encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"


def test_detect_try_format_skips_typeless_first_line(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "head.jsonl"
    f.write_text('{"note": "header"}\n{"type": "model", "case_id": "x"}\n',
                 encoding="utf-8")
    assert _detect_try_format(str(f)) == "jsonl"


def test_detect_try_format_finds_messages_past_1mib(tmp_path):
    # Same class as the default-checks sniff bug: a trajectory whose
    # leading "info" object pushes "messages" past a fixed prefix
    # must still detect as traj (the old 1 MiB prefix missed it).
    from averth.cli import _detect_try_format

    f = tmp_path / "big.traj.json"
    f.write_text(json.dumps({
        "info": {"padding": "x" * (2 * 1024 * 1024)},
        "messages": [
            {"role": "assistant",
             "content": "```bash\npytest\n```"},
        ]}), encoding="utf-8")
    assert f.stat().st_size > 1024 * 1024
    assert _detect_try_format(str(f)) == "traj"


def test_detect_try_format_rejects_garbage(tmp_path):
    from averth.cli import _detect_try_format

    f = tmp_path / "nope.json"
    f.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(ValueError, match="none of the supported shapes"):
        _detect_try_format(str(f))
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="is empty"):
        _detect_try_format(str(empty))
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xd8\xff\x00\x01")
    with pytest.raises(ValueError, match="not readable text"):
        _detect_try_format(str(binary))
    text = tmp_path / "text.txt"
    text.write_text("hello world, this is not json at all",
                    encoding="utf-8")
    with pytest.raises(ValueError, match="mini-SWE-agent trajectory"):
        _detect_try_format(str(text))


def test_try_wrong_format_names_detected_format(capsys):
    rc = main(["try", TRAJ, "--format", "jsonl", "--model", MODEL])
    err = capsys.readouterr().err
    assert rc == 2
    assert "does not parse as jsonl" in err
    assert "looks like traj" in err


def test_try_unsupported_file_is_an_error(tmp_path, capsys):
    bad = tmp_path / "not-a-trace.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    rc = main(["try", str(bad)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "none of the supported shapes" in err
    assert "pass --format" not in err


def test_try_empty_file_is_an_error(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    rc = main(["try", str(empty)])
    assert rc == 2
    assert "is empty" in capsys.readouterr().err


def test_try_binary_file_is_an_error(tmp_path, capsys):
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xd8\xff\x00\x01")
    rc = main(["try", str(binary)])
    assert rc == 2
    assert "not readable text" in capsys.readouterr().err


def test_try_directory_is_an_error(tmp_path, capsys):
    rc = main(["try", str(tmp_path)])
    assert rc == 2
    assert "is a directory" in capsys.readouterr().err


def test_try_empty_langfuse_is_an_error(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"data": []}), encoding="utf-8")
    rc = main(["try", str(empty)])
    assert rc == 2
    assert "contains no traces" in capsys.readouterr().err


def test_try_missing_ledger_is_named(capsys):
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", "nope.json"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "V0 ledger file not found" in err
    assert "--ledger" in err


def test_try_recorded_nan_inf_are_errors(capsys):
    for bad in ("nan", "inf", "-1"):
        rc = main(["try", TRAJ, "--model", MODEL, "--recorded", bad])
        assert rc == 2
        assert "positive dollar figure" in capsys.readouterr().err


# --- output path -------------------------------------------------------


def test_try_bad_out_parent_fails_before_report(tmp_path, monkeypatch,
                                               capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL,
               "--out", str(tmp_path / "nope" / "report.html")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "does not exist" in captured.err
    assert "Fully loaded" not in captured.out
    # A parent path that exists as a file is reported as such, not as
    # a missing directory.
    blocker = tmp_path / "blocker.json"
    blocker.write_text("{}", encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL,
               "--out", str(blocker / "report.html")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "is not a directory" in captured.err
    assert "Fully loaded" not in captured.out


def test_try_overwrite_refused_and_force(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL])
    assert rc == 0
    first = (tmp_path / "django-15930-try.html").read_text(encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL])
    err = capsys.readouterr().err
    assert rc == 2
    assert "already exists" in err
    assert "pass --force" in err
    assert (tmp_path / "django-15930-try.html").read_text(
        encoding="utf-8") == first
    rc = main(["try", TRAJ, "--model", MODEL, "--force"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "overwriting" in captured.err


def test_try_digest_mismatch_warns_about_stale_report(
        tmp_path, monkeypatch, capsys):
    tampered = tmp_path / "checks.json"
    tampered.write_text(open(CHECKS, encoding="utf-8").read() + " ",
                        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", CHECKS])
    assert rc == 0
    before = (tmp_path / "django-15930-try.html").read_text(encoding="utf-8")
    rc = main(["try", TRAJ, "--model", MODEL, "--ledger", LEDGER,
               "--checks", str(tampered)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "digest mismatch" in err
    assert "previous report remains" in err
    assert (tmp_path / "django-15930-try.html").read_text(
        encoding="utf-8") == before


def test_try_hostile_filename_is_escaped(tmp_path, monkeypatch, capsys):
    evil = tmp_path / "<img src=x onerror=alert(1)>.traj.json"
    shutil.copy(TRAJ, evil)
    monkeypatch.chdir(tmp_path)
    rc = main(["try", str(evil), "--model", MODEL,
               "--out", "report.html"])
    assert rc == 0
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<img src=x" not in html
    assert "&lt;img" in html


# --- converter hardening ----------------------------------------------


def test_converter_skips_non_string_text_parts(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "user", "content": [
            {"type": "text", "text": 123},
            {"type": "text", "text": "hello"}]},
        {"role": "assistant", "content": "```bash\necho hi\n```"},
    ], "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert [e for e in events if e["type"] == "model"][0]["input_tokens"] == 1


def test_converter_rejects_non_dict_message(tmp_path):
    traj = {"instance_id": "x", "messages": ["oops"],
            "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    with pytest.raises(ValueError, match="message 0"):
        miniswe.miniswe_events(str(f), model=MODEL)


def test_converter_tolerates_non_dict_info(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "assistant", "content": "hi"}],
        "info": "Submitted"}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert not [e for e in events if e["type"] == "end"]


def test_converter_bash_fence_variants(tmp_path):
    traj = {"instance_id": "x", "messages": [
        {"role": "assistant", "content": "```bash echo hi```"},
        {"role": "assistant", "content": "```bash \necho hi\n```"},
        {"role": "assistant", "content": "```BASH\necho hi\n```"},
    ], "info": {"exit_status": "Submitted"}}
    f = tmp_path / "t.traj.json"
    f.write_text(json.dumps(traj), encoding="utf-8")
    events = miniswe.miniswe_events(str(f), model=MODEL)
    assert len([e for e in events if e["type"] == "tool"]) == 3


def test_infer_model_matches_basename_only():
    assert miniswe._infer_model("/tmp/notes-about-gpt-4o/traj.json") is None
    assert miniswe._infer_model("mygpt-4o-model.traj.json") is None
    assert miniswe._infer_model(
        "django__django-15930_claude-sonnet-4-20250514.traj.json") == MODEL
    assert miniswe.is_priced_model(MODEL) is True
    assert miniswe.is_priced_model("gpt-99-nonexistent") is False
    assert miniswe.is_priced_model("anthropic:" + MODEL) is True


# --- report byte identity ----------------------------------------------


def test_write_html_without_try_extras_is_unchanged(tmp_path):
    from averth.report import write_html

    ledger = miniswe.load_miniswe(TRAJ, model=MODEL)
    tracker = common.tracker_from_ledger(ledger)
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    c = tmp_path / "c.html"
    write_html(str(a), tracker, try_extras=None)
    write_html(str(b), tracker, try_extras="")
    # None and "" render identically: no stray blank line is added.
    assert a.read_bytes() == b.read_bytes()
    write_html(str(c), tracker, try_extras="<p>EXTRA</p>")
    html_c = c.read_text(encoding="utf-8")
    assert html_c.count("<p>EXTRA</p>") == 1
    assert "<p>EXTRA</p>\n</main>" in html_c
