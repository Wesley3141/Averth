"""requirement_spec: the human-written acceptance-check file. Manual only.

Checks are seeded by a human in a JSON file, NOT auto-extracted from a
transcript, issue, or PR. Auto-extraction is a later step and is not
claimed here. A check file looks like:

{
  "task_intent": "widget add, subtract and multiply behave as named",
  "task_intent_source": "fixture README, human-written for this experiment",
  "checks": [
    {"id": "C1", "text": "add behaves as named",
     "check_type": "recorded_run",
     "required_command": "python -m pytest -q widget_tests/test_widget.py::test_add",
     "test_target": "widget_tests/test_widget.py::test_add",
     "source": "fixture checks file",
     "expected_evidence": "a recorded run of that command, exit 0, after the final edit",
     "applicability": "applies",
     "scope_limitation": "proves only add(2,3)==5 in this one test"},
    ...
  ]
}

check_type values:
- recorded_run: a prescribed command must appear in the recorded runs.
- artifact_presence: a named file must exist in the repo snapshot. A
  missing artifact here is FAILED, because the tool itself scanned the
  repo and found it absent. This is deliberately different from a
  "build artifact exists" criterion where no build was ever run: that
  case must be written as a recorded_run check for the build command,
  which then correctly yields NOT OBSERVED when no build was recorded.
- external: data outside the tool's reach (hardware, private CI). It
  yields EXTERNAL-UNVERIFIABLE unless a human_confirmation record
  (named tester, named procedure, result pass/fail) is supplied.

applicability: "applies", or "not_applicable" with a recorded reason.
Applicability is judged before evidence, never retroactively to erase
an inconvenient FAILED.
"""
import json

from trace_adapter import read_regular_file_bytes, sha256_bytes

CHECK_TYPES = ("recorded_run", "artifact_presence", "external", "inferred")


def checks_digest(path):
    """sha256 digest of the checks file raw bytes, as recorded at load.

    The digest is over the raw bytes, so any edit present in the
    bytes at hashing time, even one that leaves the parsed checks
    identical (for example a whitespace-only edit), changes it. The
    bytes are hashed directly with no decode step, so a checks file
    in any encoding the JSON parser accepts (UTF-8, UTF-16, UTF-32)
    can be hashed. The digest is over the raw bytes, so the same
    content in a different encoding has a different digest, and a
    re-encoding that is present at the re-hash triggers refusal (a
    re-encoding reverted before the re-hash, or made after it,
    escapes detection).
    """
    return sha256_bytes(read_regular_file_bytes(path))


def verify_checks_unchanged(path, digest):
    """Re-hash the checks file and raise ValueError on mismatch.

    The checks file is frozen at load: any net change between load
    and the re-hash (a single comparison: an edit reverted
    byte-for-byte before the re-hash escapes detection, as does any
    edit made after the re-hash) is a new check set, not a correction
    to the frozen set, and the run must not be written out. A checks
    file that cannot be read at verify time (deleted, replaced by a
    directory, replaced by a non-regular file, unreadable) refuses the same way: the frozen set
    cannot be confirmed unchanged, so the run is refused rather than
    written out on trust.
    """
    try:
        current = checks_digest(path)
    except OSError as exc:
        raise ValueError(
            f"checks file unreadable during run: {path}: {exc}; refusing to write output. "
            f"To redo the run, restore the frozen file matching the load-time digest {digest} and re-run; "
            f"do not re-run against a missing or unreadable file as the frozen set"
        ) from exc
    except ValueError as exc:
        # A non-regular file (FIFO, socket, device) swapped in
        # between load and re-hash: the single-open read refuses
        # it with ValueError, not OSError. Re-raise in the same
        # unreadable style, naming the load-time digest and the
        # redo, so the re-hash refusal message has one shape for
        # every unreadable case. (The load path is untouched:
        # load_checks reads through the same single-open helper
        # directly.)
        raise ValueError(
            f"checks file unreadable during run: {path}: {exc}; refusing to write output. "
            f"To redo the run, restore the frozen file matching the load-time digest {digest} and re-run; "
            f"do not re-run against a missing or unreadable file as the frozen set"
        ) from exc
    if current != digest:
        raise ValueError(
            f"checks file changed during run: {path} digest {current} "
            f"does not match load-time digest {digest}; refusing to write output. "
            f"To redo the run, restore the frozen file matching the load-time digest {digest} and re-run; "
            f"do not re-run against the edited file as the frozen set"
        )


MAX_CHECKS_DEPTH = 100


def _check_depth(value, max_depth=MAX_CHECKS_DEPTH):
    """Iteratively refuse a checks file nested deeper than max_depth.

    The C JSON scanner tolerates nesting the pure-Python encoder in
    json.dumps does not, so a deeply nested value in a field the
    ledger copies verbatim (task_intent, task_intent_source, or a
    check field such as text) parses fine and then crashes uncaught
    when the ledger is written. Walk the parsed structure with an
    explicit stack (never recursion) and refuse anything deeper than
    max_depth, well under the encoder's limit. Covers the whole
    parsed file: task_intent, task_intent_source, checks, and every
    nested value.
    """
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise ValueError("checks file is nested too deeply")
        if isinstance(current, dict):
            stack.extend((v, depth + 1) for v in current.values())
        elif isinstance(current, list):
            stack.extend((v, depth + 1) for v in current)


def load_checks(path):
    raw = read_regular_file_bytes(path)
    try:
        data = json.loads(raw)
    except RecursionError as exc:
        raise ValueError(
            "checks file is nested too deeply to parse"
        ) from exc
    _check_depth(data)
    if not isinstance(data, dict):
        raise ValueError("checks file must contain a JSON object")
    checks = data.get("checks", [])
    if not isinstance(checks, list):
        raise ValueError("'checks' must be a list")
    for c in checks:
        if not isinstance(c, dict):
            raise ValueError("each check must be a JSON object")
    seen = set()
    for c in checks:
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError(f"check id missing or not a string: {cid!r}")
        if cid in seen:
            raise ValueError(f"check id duplicated: {cid!r}")
        seen.add(cid)
        if c.get("check_type") not in CHECK_TYPES:
            raise ValueError(f"check {cid}: unknown check_type {c.get('check_type')!r}")
        if c.get("applicability", "applies") not in ("applies", "not_applicable"):
            raise ValueError(f"check {cid}: bad applicability")
        if c.get("check_type") in ("recorded_run", "inferred"):
            rc = c.get("required_command")
            if not isinstance(rc, str) or not rc.strip():
                raise ValueError(f"check {cid}: recorded_run or inferred needs a non-empty string required_command")
        if c.get("check_type") == "artifact_presence":
            ap = c.get("artifact_path")
            if not isinstance(ap, str) or not ap.strip():
                raise ValueError(f"check {cid}: artifact_presence needs a non-empty string artifact_path")
        # artifact_path and expected_digest are also read by the
        # recorded_run digest check, not only by artifact_presence:
        # a non-string value there crashes the judge (unhashable
        # snapshot lookup) or, with no expected_digest, judges
        # VERIFIED on garbage. Require non-empty strings on any
        # check type whenever the fields are present.
        for field in ("artifact_path", "expected_digest"):
            if field in c and (not isinstance(c[field], str) or not c[field].strip()):
                raise ValueError(f"check {cid}: {field} must be a non-empty string")
        if "human_confirmation" in c and not isinstance(c["human_confirmation"], dict):
            raise ValueError(f"check {cid}: human_confirmation must be a JSON object")
        if "human_confirmation" in c and isinstance(c["human_confirmation"], dict):
            rec = c["human_confirmation"]
            for field in ("tester", "procedure"):
                if field in rec and (not isinstance(rec[field], str) or not rec[field].strip()):
                    raise ValueError(f"check {cid}: human_confirmation {field} must be a non-empty string")
        for field in ("text", "source", "expected_evidence", "scope_limitation",
                      "recommended_next_action", "not_applicable_reason"):
            if field in c and not isinstance(c[field], str):
                raise ValueError(f"check {cid}: {field} must be a string")
        # test_target is copied verbatim into a VERIFIED row by
        # the judge, so a list there lands verbatim in the ledger.
        # It must be a string when present; null is the existing
        # "no test target" value in the fixture checks files, so
        # null stays allowed, like an absent test_target.
        if "test_target" in c and c["test_target"] is not None \
                and not isinstance(c["test_target"], str):
            raise ValueError(f"check {cid}: test_target must be a string or null")
    # task_intent and task_intent_source are copied verbatim into
    # the ledger and the report: a non-string value there lands
    # verbatim too, so refuse it at load like the check-level
    # string fields. Absent is fine (the loaders record "").
    for field in ("task_intent", "task_intent_source"):
        if field in data and not isinstance(data[field], str):
            raise ValueError(f"checks file {field} must be a string")
    return {
        "task_intent": data.get("task_intent", ""),
        "task_intent_source": data.get("task_intent_source", ""),
        "checks": checks,
        "checks_digest": sha256_bytes(raw),
    }
