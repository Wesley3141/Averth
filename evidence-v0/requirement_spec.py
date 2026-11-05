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
from pathlib import Path

CHECK_TYPES = ("recorded_run", "artifact_presence", "external", "inferred")


def load_checks(path):
    data = json.loads(Path(path).read_text())
    checks = data.get("checks", [])
    seen = set()
    for c in checks:
        cid = c.get("id")
        if not cid or cid in seen:
            raise ValueError(f"check id missing or duplicated: {cid!r}")
        seen.add(cid)
        if c.get("check_type") not in CHECK_TYPES:
            raise ValueError(f"check {cid}: unknown check_type {c.get('check_type')!r}")
        if c.get("applicability", "applies") not in ("applies", "not_applicable"):
            raise ValueError(f"check {cid}: bad applicability")
        if c.get("check_type") in ("recorded_run", "inferred") and not c.get("required_command"):
            raise ValueError(f"check {cid}: recorded_run or inferred needs required_command")
        if c.get("check_type") == "artifact_presence" and not c.get("artifact_path"):
            raise ValueError(f"check {cid}: artifact_presence needs artifact_path")
    return {
        "task_intent": data.get("task_intent", ""),
        "task_intent_source": data.get("task_intent_source", ""),
        "checks": checks,
    }
