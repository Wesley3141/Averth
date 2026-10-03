"""Regression tests for review round 5 (report.py findings).

- C-HTML-1: stored XSS via unescaped price_vintage["version"] in write_html
  (vintage_line and stale_banner).
- H-HTML-1: cache_line mixed %-style and .format() placeholders, rendering a
  literal "%.0f%%" and swallowing the discount rate.
- M-HTML-1: policy_sim policy values rendered unescaped.
- New: report_text (and write_html) must warn when usage data is missing.
"""

import copy

from averth import Tracker
from averth.importers.common import ledger_from_tracker, tracker_from_ledger
from averth.report import report_text, write_html

XSS_VINTAGE = '<script>alert("xss-vintage")</script>'
XSS_POLICY = '<script>alert("xss-policy")</script>'


def _tracker_with_tampered_vintage(version, stale):
    """Rehydrate a Tracker from a ledger whose price_vintage is attacker-set,
    the documented cross-trust-boundary flow (CLI import -> tracker_from_ledger)."""
    t = Tracker("vintage-probe")
    t.start_attempt(case_id="V-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100)
    t.end_attempt(success=True)
    ledger = copy.deepcopy(ledger_from_tracker(t))
    ledger["price_vintage"] = {
        "version": version,
        "updated": "2026-09-01",
        "age_days": 120,
        "stale": stale,
        "stale_after_days": 30,
    }
    return tracker_from_ledger(ledger)


def _basic_tracker():
    t = Tracker("round5-probe")
    t.start_attempt(case_id="R5-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 1000, 100)
    t.end_attempt(success=True)
    return t


def test_hostile_vintage_version_escaped_vintage_line_and_stale_banner(tmp_path):
    # stale=True exercises BOTH sinks: vintage_line (always rendered) and
    # stale_banner.
    t = _tracker_with_tampered_vintage(XSS_VINTAGE, stale=True)
    out = tmp_path / "hostile-stale.html"
    write_html(str(out), t)
    body = out.read_text(encoding="utf-8")
    assert "Stale pricing" in body  # stale banner path fired
    assert "Price table v" in body  # vintage line path fired
    assert XSS_VINTAGE not in body  # no raw script from the version string
    assert "&lt;script&gt;alert(&quot;xss-vintage&quot;)&lt;/script&gt;" in body


def test_hostile_vintage_version_escaped_when_not_stale(tmp_path):
    t = _tracker_with_tampered_vintage(XSS_VINTAGE, stale=False)
    out = tmp_path / "hostile-fresh.html"
    write_html(str(out), t)
    body = out.read_text(encoding="utf-8")
    assert "Stale pricing" not in body
    assert "Price table v" in body
    assert XSS_VINTAGE not in body
    assert "&lt;script&gt;alert(&quot;xss-vintage&quot;)&lt;/script&gt;" in body


def test_cache_line_renders_actual_discount_rate(tmp_path):
    t = Tracker("cache-probe")
    t.start_attempt(case_id="C-1")
    t.log_model_call("anthropic", "claude-sonnet-4-5", 8000, 100,
                     cached_input_tokens=8000)
    t.end_attempt(success=True)
    p = t.pnl()
    assert p["cached_tokens"] and p["cache_savings"] > 0
    out = tmp_path / "cache.html"
    write_html(str(out), t)
    body = out.read_text(encoding="utf-8")
    assert "%.0f%%" not in body  # the swallowed-placeholder bug is gone
    assert "priced at 10% of input rate" in body  # default 0.10 discount named
    # text report matches (behavior parity required by H-HTML-1 fix)
    assert "priced at 10% of input rate" in report_text(p)


def test_policy_sim_values_escaped(tmp_path):
    sim = {
        "policy": {
            "max_cost_per_attempt": XSS_POLICY,
            "yield_floor": '<img src=x onerror=alert("xss-policy")>',
        },
        "flagged_runs": 1,
        "flagged_failed": 0,
        "flagged_success": 1,
        "flagged_failed_spend": 0.50,
        "flagged_success_spend": 0.20,
        "worst": [{"case_id": "R5-1", "total_cost": 0.20, "success": True,
                   "reasons": ["too slow"]}],
    }
    out = tmp_path / "hostile-policy.html"
    write_html(str(out), _basic_tracker(), policy_sim=sim)
    body = out.read_text(encoding="utf-8")
    assert "Historical policy screen" in body
    assert XSS_POLICY not in body
    assert '<img src=x onerror=alert("xss-policy")>' not in body
    assert "&lt;script&gt;alert(&quot;xss-policy&quot;)&lt;/script&gt;" in body
    assert "&lt;img src=x onerror=alert(&quot;xss-policy&quot;)&gt;" in body


def test_missing_usage_models_warning_in_text_report():
    t = _basic_tracker()
    t.missing_usage.add("some-mystery-model")
    txt = report_text(t.pnl())
    assert "WARNING" in txt
    assert "some-mystery-model" in txt
    assert "usage data missing for 1 model" in txt
    assert "$0.00 is missing data, not free inference" in txt


def test_missing_usage_models_multiple_models_in_text_report():
    t = _basic_tracker()
    t.missing_usage.update(["model-a", "model-b"])
    txt = report_text(t.pnl())
    assert "usage data missing for 2 models" in txt
    assert "model-a" in txt and "model-b" in txt


def test_missing_usage_models_banner_in_html(tmp_path):
    t = _basic_tracker()
    t.missing_usage.add('<script>alert("xss-usage")</script>')
    out = tmp_path / "missing-usage.html"
    write_html(str(out), t)
    body = out.read_text(encoding="utf-8")
    assert "Missing usage data" in body
    assert "missing data, not free inference" in body
    assert '<script>alert("xss-usage")</script>' not in body
    assert "&lt;script&gt;" in body


def test_missing_usage_models_empty_and_missing_key_no_warning_no_crash():
    # Empty set: no warning line, no crash.
    t = _basic_tracker()
    assert "missing data, not free inference" not in report_text(t.pnl())
    # Missing key entirely (e.g. a hand-built/legacy pnl dict): still no crash.
    p = t.pnl()
    del p["missing_usage_models"]
    assert "missing data, not free inference" not in report_text(p)
