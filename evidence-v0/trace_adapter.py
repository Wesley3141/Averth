"""trace_adapter: read recorded runs and public trace events. Read-only.

Two input shapes, both local files the operator names:
1. A recorded-run ledger JSON (the shape written by the earlier fixture
   generator): an object with a "runs" list. Each run keeps its raw
   command, timestamps, exit code and output digest. Imported runs are
   Tier 1 evidence: observed in a log, potentially incomplete/editable.
2. A JSONL trace of agent events (e.g. the public mini-swe-agent
   events.jsonl). This adapter only SUMMARISES it: event counts by
   type, cases, model token totals, retry events. It never turns a
   trace into a judgment, and it never computes cost per accepted
   outcome, because these traces carry no acceptance join.
No network, no model calls, no credentials.
"""
import json
import shlex
from pathlib import Path


def normalize_command(command):
    """Compare commands ignoring only the interpreter token.

    The same pytest invocation recorded under the Averth venv python
    and under bare ``python`` is the same check. Everything after the
    interpreter (executable, args, targets) must match exactly.
    The raw command is always retained alongside the normalised form.
    """
    if isinstance(command, (list, tuple)):
        parts = [str(p) for p in command]
    else:
        parts = shlex.split(str(command))
    if not parts:
        return ""
    return " ".join(parts[1:])


def sha256_text(text):
    import hashlib

    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def load_recorded_runs(path):
    """Return a list of normalised run dicts from a ledger JSON file."""
    data = json.loads(Path(path).read_text())
    runs = []
    if isinstance(data, dict):
        raw_runs = data.get("runs", [])
        marker = data.get("final_edit_marker")
    elif isinstance(data, list):
        raw_runs = data
        marker = None
    else:
        raise ValueError("recorded-run file must be a JSON object or list")
    for r in raw_runs:
        command = r.get("command", "")
        output = (r.get("stdout", "") or "") + (r.get("stderr", "") or "")
        runs.append(
            {
                "label": r.get("label", ""),
                "command_raw": command,
                "command_normalized": normalize_command(command),
                "working_directory": r.get("working_directory", ""),
                "start_timestamp": r.get("start_timestamp"),
                "end_timestamp": r.get("end_timestamp"),
                "exit_code": r.get("exit_code"),
                "output_digest": r.get("output_digest") or sha256_text(output),
                "source": "imported",
                "trust_tier": 1,
            }
        )
    return runs, marker


def load_trace_events(path):
    """Summarise a JSONL agent trace. No judgments are produced here."""
    counts = {}
    cases = set()
    model_events = 0
    input_tokens = 0
    output_tokens = 0
    retry_events = 0
    lines = 0
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            lines += 1
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                counts["unparseable"] = counts.get("unparseable", 0) + 1
                continue
            t = ev.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
            if ev.get("case_id"):
                cases.add(ev["case_id"])
            if t == "model":
                model_events += 1
                input_tokens += int(ev.get("input_tokens") or 0)
                output_tokens += int(ev.get("output_tokens") or 0)
            if t == "retry":
                retry_events += 1
    return {
        "trace_file": str(path),
        "lines": lines,
        "cases": len(cases),
        "events_by_type": counts,
        "model_events": model_events,
        "input_tokens_total": input_tokens,
        "output_tokens_total": output_tokens,
        "retry_events": retry_events,
        "note": (
            "Summary only. This trace carries no acceptance join, so no "
            "cost-per-accepted-outcome figure is computed from it, and no "
            "judgment in any report may cite this summary as a verdict."
        ),
    }
