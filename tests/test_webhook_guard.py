"""Tests for averth.integrations.webhook_guard. Stdlib only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from averth.integrations.webhook_guard import AlertGuard, default_key


def alert(fp="aaa", status="firing", labels=None, annotations=None, starts_at="t0"):
    return {
        "fingerprint": fp,
        "status": status,
        "labels": {"pod": "api-1"} if labels is None else labels,
        "annotations": {"v": "1"} if annotations is None else annotations,
        "startsAt": starts_at,
    }


def test_fresh_firing_diagnoses():
    g = AlertGuard()
    assert g.route(alert()) == "diagnose"


def test_resolved_is_lifecycle_notice():
    g = AlertGuard()
    assert g.route(alert(status="resolved")) == "lifecycle-notice"


def test_duplicate_merges_while_inflight():
    g = AlertGuard()
    a = alert()
    assert g.route(a) == "diagnose"
    g.mark_inflight(a)
    assert g.route(alert()) == "merged-duplicate"
    g.complete(a)
    assert g.route(alert()) == "diagnose"


def test_changed_annotations_redagnose():
    g = AlertGuard()
    g.mark_inflight(alert())
    assert g.route(alert(annotations={"v": "99"})) == "diagnose"


def test_flap_refire_new_starts_at_diagnoses():
    g = AlertGuard()
    g.mark_inflight(alert(starts_at="t0"))
    assert g.route(alert(starts_at="t1")) == "diagnose"


def test_degenerate_alert_never_merges():
    g = AlertGuard()
    a = {"fingerprint": None, "status": "firing", "labels": {}, "annotations": {}}
    assert default_key(a) is None
    assert g.route(a) == "diagnose"
    g.mark_inflight(a)
    assert g.route({"fingerprint": None, "status": "firing", "labels": {}, "annotations": {}}) == "diagnose"


def test_non_dict_fails_open():
    g = AlertGuard()
    assert g.route("nonsense") == "diagnose"


def test_complete_is_idempotent():
    g = AlertGuard()
    a = alert()
    g.complete(a)  # never marked; must not raise
    g.mark_inflight(a)
    g.complete(a)
    g.complete(a)
    assert g.inflight_count == 0


def test_custom_lifecycle_statuses():
    g = AlertGuard(lifecycle_statuses={"resolved", "ok"})
    assert g.route(alert(status="ok")) == "lifecycle-notice"
    assert g.route(alert(status="firing")) == "diagnose"
