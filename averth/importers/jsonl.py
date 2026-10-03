"""Importer for JSONL event files: one EVENT-schema dict per line.

Expected schema (see averth.importers.common for the full definition):

    {"type": "start", "case_id": "CASE-1"}

    {"type": "model", "case_id": "CASE-1", "provider": "openai",
     "model": "gpt-5-nano", "input_tokens": 1200, "output_tokens": 300,
     "cached_input_tokens": 800, "branch": "research"}

    {"type": "tool", "case_id": "CASE-1", "name": "web_search",
     "cost": 0.005, "latency_ms": 320}

    {"type": "retry", "case_id": "CASE-1", "reason": "validation failed",
     "branch": "research"}

    {"type": "escalation", "case_id": "CASE-1", "minutes": 4.5,
     "reason": "low confidence"}

    {"type": "end", "case_id": "CASE-1", "success": true,
     "business_value": 11.20, "reopened": false}

Field rules, enforced strictly:
  - every line must be a JSON object with a known "type"
  - "case_id" is always required and must be a string
  - "provider" is optional (guessed from the model name when omitted)
  - numeric fields (input_tokens, output_tokens, cached_input_tokens, cost,
    latency_ms, minutes) must be int/float (not bool), finite, and >= 0;
    business_value must be finite but may be negative
  - cached_input_tokens may not exceed input_tokens
  - "branch" (model, tool, retry events) scopes retry-path waste marking
    to one parallel branch; omit for attempt-global marking. On tool
    events it tags which branch made the call, so retry-path tool spend
    is attributed to the discarded path (an untagged tool step survives
    a branch-scoped retry unmarked).
  - "success" and "reopened" must be real booleans, not 0/1
  - unknown keys are rejected
  - a case with no "end" line is auto-ended with success=False

Any violation raises ValueError naming the offending line number.
"""

import json

from .common import events_to_tracker, ledger_from_tracker


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_num(line_no, ev, field, minimum=0):
    import math
    value = ev[field]
    if not _is_num(value):
        raise ValueError("line %d: %r must be a number, got %r"
                         % (line_no, field, value))
    # C4: NaN/inf would poison the ledger and export invalid JSON
    if not math.isfinite(value):
        raise ValueError("line %d: %r must be finite, got %r"
                         % (line_no, field, value))
    if minimum is not None and value < minimum:
        raise ValueError("line %d: %r must be >= %s, got %r"
                         % (line_no, field, minimum, value))


def _check_bool(line_no, ev, field):
    if type(ev[field]) is not bool:
        raise ValueError("line %d: %r must be true/false, got %r"
                         % (line_no, field, ev[field]))


# type -> (required fields, optional fields, per-type extra checks)
_SPECS = {
    "start": ({"case_id": str}, {}),
    "model": ({"case_id": str, "model": str},
              {"provider": str, "input_tokens": None, "output_tokens": None,
               "cached_input_tokens": None, "branch": str}),
    "tool": ({"case_id": str, "name": str},
             {"cost": None, "latency_ms": None, "branch": str}),
    "retry": ({"case_id": str}, {"reason": str, "branch": str}),
    "escalation": ({"case_id": str, "minutes": None}, {"reason": str}),
    "end": ({"case_id": str, "success": None},
            {"business_value": None, "reopened": None}),
}

_NUM_FIELDS = {"input_tokens", "output_tokens", "cached_input_tokens",
               "cost", "latency_ms", "minutes", "business_value"}
# business_value may be negative (a bad outcome can destroy value); every
# other numeric field is a cost/count and must be >= 0.
_NUM_MINIMUM = {"business_value": None}


def _validate(line_no, ev):
    if not isinstance(ev, dict):
        raise ValueError("line %d: expected a JSON object, got %r"
                         % (line_no, ev))
    etype = ev.get("type")
    # H1: the membership test alone raises bare TypeError for unhashable
    # "type" values (e.g. a list); the documented contract is ValueError
    # naming the offending line number.
    if not isinstance(etype, str) or etype not in _SPECS:
        raise ValueError("line %d: unknown event type %r (expected one of %s)"
                         % (line_no, etype, ", ".join(sorted(_SPECS))))
    required, optional = _SPECS[etype]
    for field, ftype in required.items():
        if field not in ev:
            raise ValueError("line %d: %r event missing required field %r"
                             % (line_no, etype, field))
        if ftype is str and not isinstance(ev[field], str):
            raise ValueError("line %d: %r must be a string, got %r"
                             % (line_no, field, ev[field]))
    for field, ftype in optional.items():
        if field in ev and ftype is str and not isinstance(ev[field], str):
            raise ValueError("line %d: %r must be a string, got %r"
                             % (line_no, field, ev[field]))
    for field in _NUM_FIELDS:
        if field in ev:
            _check_num(line_no, ev, field,
                       minimum=_NUM_MINIMUM.get(field, 0))
    if "success" in ev:
        _check_bool(line_no, ev, "success")
    if "reopened" in ev:
        _check_bool(line_no, ev, "reopened")
    if "cached_input_tokens" in ev and "input_tokens" in ev:
        if ev["cached_input_tokens"] > ev["input_tokens"]:
            raise ValueError(
                "line %d: 'cached_input_tokens' (%r) may not exceed "
                "'input_tokens' (%r)" % (line_no, ev["cached_input_tokens"],
                                         ev["input_tokens"]))
    allowed = set(required) | set(optional) | {"type"}
    extra = set(ev) - allowed
    if extra:
        raise ValueError("line %d: unknown field(s) %s for event type %r"
                         % (line_no, sorted(extra), etype))
    return ev


def load_jsonl(path, agent_name="jsonl-import"):
    """Parse a JSONL event file (strict) and return a sanitized ledger dict.

    Raises ValueError naming the line number of the first invalid line.
    """
    events = []
    with open(path) as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("line %d: invalid JSON: %s" % (line_no, exc))
            events.append(_validate(line_no, ev))
    tracker = events_to_tracker(agent_name, events)
    return ledger_from_tracker(tracker)
