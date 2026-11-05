#!/usr/bin/env python3
"""Wave 2: timestamp and final-edit capture, documented and checked.

A V0 judgment for a recorded_run check needs two time facts:
  - A parseable ISO 8601 start timestamp for the run itself.
  - A final-edit marker: the ISO 8601 time of the last edit
    before the run, so V0 can tell whether the run verifies
    the current revision or an older one.

What V0 does when a fact is missing, stated exactly, because
this is where a silent pass would be most tempting:
  - Run with no parseable start timestamp: V0 filters it out
    of citable runs, so the check is NOT OBSERVED, never
    VERIFIED and never FAILED on that run alone. NOT OBSERVED
    is a statement about the records, never proof the work
    never happened.
  - Run with a start timestamp before the final-edit marker:
    the run is superseded, retained in history, never cited,
    and the check is NOT OBSERVED with a superseded_only flag,
    unless another citable run exists.
  - No final-edit marker supplied by the operator, and no
    marker in the imported ledger: cli.py falls back to the
    latest file modification time in the repo snapshot. That
    fallback is a limitation, not a proof of edit order. A
    file touched by a tool, a checkout, or a rebuild can move
    that time without a human edit, and a run recorded
    before a real edit that did not touch a snapshotted file
    can look citable when it is not. The honest fix is for
    the sender harness to record its own final-edit marker,
    not for V0 to guess one.

How a sender harness should record these facts, in order:
  1. Record the final-edit marker before the run, as the
     ISO 8601 time the operator last edited the code under
     test, or the commit time of the revision under test.
     Do not use a file mtime as a substitute without saying
     so in the run record.
  2. Record start_timestamp when the command starts and
     end_timestamp when it ends, in ISO 8601 with a timezone
     offset or Z. A naive timestamp with no timezone is
     treated as UTC by V0, and that assumption must be stated
     in the harness notes if it is relied on.
  3. Put both facts in the recorded-run ledger, in the same
     shape load_recorded_runs accepts, or pass the marker
     with cli.py --final-edit-marker. A timestamp in a
     separate chat message, screenshot, or narrative is not
     a record V0 can cite.

This module implements only validation and marker
derivation from a directory. It does not execute any
command, and it does not change cli.py behaviour. Its
functions are tested, and its verdict helper returns the
exact status V0 will produce for a missing fact, so a
harness author can check before sending a run.

Usage as a library:
  from timestamp_capture import validate_iso, marker_from_directory, missing_fact_verdict
"""
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}


def validate_iso(value):
    """Return a timezone-aware datetime, or None if unparseable.

    Wave 3: delegates to the universal time parser, so ISO,
    common date forms, and epoch seconds, millis, micros,
    and nanos are all accepted. Unparseable input still
    returns None, never an invented time.
    """
    from universal_ingest import parse_any_time
    return parse_any_time(value)


def marker_from_directory(directory, exclude_dirs=None):
    """Return the latest file modification time in a directory.

    This is the same fallback cli.py uses when no marker is
    supplied. It is returned here so a harness author can see
    it, compare it with their real final edit, and supply
    their own marker when the two differ. It is not, by
    itself, proof of when a human last edited the code.
    """
    root = Path(directory)
    excluded = set(exclude_dirs or EXCLUDE_DIRS)
    latest = None
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in excluded for part in p.relative_to(root).parts):
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if latest is None or mtime > latest:
            latest = mtime
    return latest


def missing_fact_verdict(start_timestamp, final_edit_marker):
    """Return (status, reason) for a run missing a time fact.

    This mirrors verifier.judge for recorded_run checks:
    a run with no parseable start is never citable, and a
    run before the marker is superseded and never cited.
    A run at or after the marker, with a parseable start,
    is citable, subject to its exit code, which this helper
    does not judge.
    """
    start = validate_iso(start_timestamp)
    if start is None:
        return ("NOT OBSERVED", "no parseable start timestamp; run is not citable")
    marker = validate_iso(final_edit_marker)
    if marker is not None and start < marker:
        return ("NOT OBSERVED", "superseded_only; run started before the final-edit marker")
    return ("CITABLE", "run has a parseable start at or after the final-edit marker, if one was supplied")
