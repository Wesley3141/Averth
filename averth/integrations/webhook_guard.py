"""Guard for LLM-backed alert webhooks: stop paying for lifecycle-only diagnoses.

Two waste categories this eliminates, both common wherever an alert webhook
fans out to a model:

1. **Lifecycle-only notifications** (``status == "resolved"``) routed through
   a fresh diagnosis. The incident is over; a notice suffices.
2. **Duplicate deliveries** of the same alert re-diagnosed while a diagnosis
   is already in flight. One active diagnosis per identical input.

Framework-agnostic: no FastAPI/Flask/asyncio imports. The caller owns task
lifecycle; the guard only answers the routing question and tracks in-flight
keys. Thread-safe.

Example::

    guard = AlertGuard()

    # inside your webhook handler:
    decision = guard.route(alert)
    if decision == "diagnose":
        guard.mark_inflight(alert)
        asyncio.create_task(diagnose_and_release(alert))  # call guard.complete(alert) in finally
    elif decision == "lifecycle-notice":
        asyncio.create_task(send_notice(alert))  # fire-and-forget; never block the webhook
    # "merged-duplicate": do nothing

Decisions: ``"diagnose"`` | ``"merged-duplicate"`` | ``"lifecycle-notice"``.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Optional

#: Alert statuses that carry no new incident information.
LIFECYCLE_STATUSES = frozenset({"resolved"})


def default_key(alert: dict) -> Optional[str]:
    """Identity for dedup. Returns None when the alert carries no identity
    (no fingerprint, no labels) — such deliveries are never merged.

    The key includes fingerprint (or a label hash fallback), status,
    ``startsAt`` (genuine re-fires get a new one, so a flap never merges into
    an old job), and an annotations hash (changed measurements re-diagnose).
    """
    labels = alert.get("labels", {}) or {}
    fingerprint = alert.get("fingerprint")
    if not fingerprint and not labels:
        return None
    status = alert.get("status", "firing")
    starts_at = alert.get("startsAt", "")
    annotations = alert.get("annotations", {}) or {}
    ann_sig = "|".join("%s=%s" % (k, annotations[k]) for k in sorted(annotations))
    if fingerprint:
        base = str(fingerprint)
    else:
        sig = "|".join("%s=%s" % (k, labels[k]) for k in sorted(labels))
        base = str(abs(hash(sig)))
    return "%s:%s:%s:%s" % (base, status, starts_at, abs(hash(ann_sig)))


class AlertGuard:
    """Routes alert deliveries; tracks in-flight diagnoses for dedup."""

    def __init__(
        self,
        key_fn: Callable[[dict], Optional[str]] = default_key,
        lifecycle_statuses=LIFECYCLE_STATUSES,
    ):
        self._key_fn = key_fn
        self._lifecycle = frozenset(lifecycle_statuses)
        self._inflight: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def route(self, alert: dict) -> str:
        """Return the routing decision for one alert delivery."""
        if not isinstance(alert, dict):
            return "diagnose"  # fail open: never suppress what we can't read
        if alert.get("status", "firing") in self._lifecycle:
            return "lifecycle-notice"
        key = self._key_fn(alert)
        if key is None:
            return "diagnose"
        with self._lock:
            if self._inflight.get(key):
                return "merged-duplicate"
        return "diagnose"

    def mark_inflight(self, alert: dict) -> Optional[str]:
        """Record that a diagnosis started; returns the key (or None)."""
        key = self._key_fn(alert)
        if key is None:
            return None
        with self._lock:
            self._inflight[key] = True
        return key

    def complete(self, alert: dict) -> None:
        """Record that a diagnosis finished; safe to call unconditionally."""
        key = self._key_fn(alert)
        if key is None:
            return
        with self._lock:
            self._inflight.pop(key, None)

    @property
    def inflight_count(self) -> int:
        with self._lock:
            return len(self._inflight)
