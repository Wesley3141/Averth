"""Unit tests for the support benchmark grader (no API keys, no battery)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmark",
                                "support"))

import grader


def _task(**kw):
    t = {"id": "x#1", "title": "t", "body": "b",
         "resolution_label": "HOWTO", "resolution_summary": "s",
         "reopened": False, "time_to_close_hours": 5.0, "sla_breach": False}
    t.update(kw)
    return t


def test_grade_accepts_exact_label_match():
    g = grader.grade({"resolution_label": "HOWTO", "response_draft": "hi"},
                     _task())
    assert g["accepted"] is True
    assert g["predicted"] == "HOWTO"
    assert g["actual"] == "HOWTO"


def test_grade_rejects_mismatch():
    g = grader.grade({"resolution_label": "BUG_FIX", "response_draft": ""},
                     _task())
    assert g["accepted"] is False


def test_grade_normalizes_case():
    g = grader.grade({"resolution_label": "howto", "response_draft": ""},
                     _task())
    assert g["accepted"] is True


def test_grade_missing_label_is_not_accepted():
    g = grader.grade({"response_draft": "hi"}, _task())
    assert g["accepted"] is False
    assert g["predicted"] == ""


def test_grade_carries_crm_fields():
    g = grader.grade({"resolution_label": "HOWTO", "response_draft": ""},
                     _task(reopened=True, sla_breach=True,
                           time_to_close_hours=99.5))
    assert g["reopened"] is True
    assert g["sla_breach"] is True
    assert g["time_to_close_hours"] == 99.5


def test_summarize_acceptance_rate():
    grades = [
        {"accepted": True, "reopened": False},
        {"accepted": False, "reopened": False},
        {"accepted": True, "reopened": True},
        {"accepted": False, "reopened": True},
    ]
    s = grader.summarize(grades)
    assert s["n"] == 4
    assert s["acceptance_rate"] == 0.5
    assert s["accepted"] == 2
    assert s["reopened_n"] == 2
    assert s["reopened_acceptance_rate"] == 0.5


def test_summarize_no_reopened_is_none_not_zero():
    s = grader.summarize([{"accepted": True, "reopened": False}])
    assert s["reopened_n"] == 0
    assert s["reopened_acceptance_rate"] is None


def test_summarize_empty():
    s = grader.summarize([])
    assert s["n"] == 0
    assert s["acceptance_rate"] == 0.0
