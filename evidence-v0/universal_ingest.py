#!/usr/bin/env python3
"""Wave 3: universal ingestion front end, failure tolerant by design.

Principle: unknown input must never crash and never become a
false VERIFIED or FAILED. It becomes a recorded run with a
missing exit code, or a counted unparseable record, and any
check that cannot cite it stays NOT OBSERVED or
EXTERNAL-UNVERIFIABLE with the missing evidence named.

Accepted inputs, all local files or text the operator names:
  - JSON object with a runs list, or a bare JSON list of records
  - JSONL, one JSON object per line
  - Pretty printed JSON objects, one after another
  - Plain text logs, in key: value blocks separated by blank
    lines, or shell style lines with a command and an exit code
  - OpenTelemetry style span records: dicts with spanId,
    traceId, attributes, status, and start/end times in ISO,
    epoch seconds, epoch milliseconds, or nanoseconds. A
    span becomes a run only when its attributes carry an
    explicit command. A span name alone is never promoted
    to a command, because a span name is not evidence a
    command ran, and promoting it could create a false
    VERIFIED from a status code alone.
  - Meter style event records: dicts with a type field and
    token or tool fields. These are kept as events, not runs,
    unless they also carry a command and an exit code.

No format is required from the sender. The sender does not
have to pre-convert to ledger shape. A new format is a new
adapter function in this module, not a rewrite of the
verifier: add a record to run extractor, keep the ledger
shape unchanged.

Preservation rules:
  - Original record IDs are kept in raw_record, and the
    run label falls back in this order: label, id,
    record_id, run_id, spanId, traceId, case_id, then the
    command itself.
  - Command strings are kept verbatim in command_raw.
    Normalisation for matching is done by trace_adapter,
    which drops only a Python interpreter token.
  - Timestamps are kept verbatim in the raw record, and
    parsed where possible by parse_any_time. An unparseable
    timestamp is kept as text and the run is not citable,
    never given an invented timestamp.
  - Unknown fields are kept in raw_record. They are never
    silently dropped, and never turned into a verdict.

Runner detection:
  detect_runner returns the first token of the command for
  known runners (pytest, npm, yarn, pnpm, cargo, go, make,
  gradle, maven, dotnet, phpunit, rspec, jest, vitest,
  and others in KNOWN_RUNNERS), or "generic" for any other
  first token, or "unknown" when there is no command.
  Generic is not a failure: it means the runner is not in
  the known list, and the run is still recorded, still
  matched by exact command, and still judged only from
  its own exit code. A check is never judged from another
  runner's run, because verifier matching is exact
  command matching, not runner matching.

Safety: this module never executes anything. A command
string in the input is data only.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from trace_adapter import normalize_command, sha256_text

KNOWN_RUNNERS = {
    "pytest", "python", "python3", "npm", "yarn", "pnpm", "node",
    "cargo", "go", "make", "gradle", "gradlew", "mvn", "maven",
    "dotnet", "phpunit", "php", "rspec", "ruby", "jest", "vitest",
    "bun", "deno", "ctest", "bazel", "buck2", "swift", "xcodebuild",
    "sh", "bash", "zsh", "docker", "podman", "tox", "nox",
}

_EPOCH_RE = re.compile(r"^-?\d+(\.\d+)?$")
_SHELL_LINE_RE = re.compile(
    r"^(?:\S+\s+)?\$\s+(?P<cmd>.+?)(?:\s+exit\s+(?P<exit>-?\d+))?\s*$"
)
_BLOCK_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_ ]*):\s*(?P<val>.*)$")


def parse_any_time(value):
    """Parse ISO, common date forms, and epoch times, or None.

    Accepts: ISO 8601 with Z or offset, naive ISO treated as
    UTC, "YYYY-MM-DD HH:MM:SS", "YYYY/MM/DD HH:MM:SS",
    "MM/DD/YYYY HH:MM:SS", epoch seconds, epoch milliseconds
    (values above 1e12), epoch microseconds (above 1e15),
    and epoch nanoseconds (above 1e18). Numeric strings are
    treated the same as numbers. Anything else returns None,
    never an invented time.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return _epoch_to_dt(float(value))
        except (ValueError, OverflowError, OSError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if _EPOCH_RE.match(text):
        try:
            return _epoch_to_dt(float(text))
        except (ValueError, OverflowError, OSError):
            return None
    iso = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
                "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M",
                "%d %b %Y %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _epoch_to_dt(seconds):
    v = float(seconds)
    if abs(v) >= 1e18:
        v = v / 1e9
    elif abs(v) >= 1e15:
        v = v / 1e6
    elif abs(v) >= 1e12:
        v = v / 1e3
    # Out of range values raise here and are caught by the
    # caller, which returns None, never a crash. A numeric
    # epoch far outside the datetime range is unparseable
    # input, not a timestamp.
    return datetime.fromtimestamp(v, tz=timezone.utc)


def detect_runner(command):
    """Return a runner label for a command string or argv list."""
    if isinstance(command, (list, tuple)):
        parts = [str(p) for p in command if str(p).strip()]
    elif isinstance(command, str) and command.strip():
        import shlex
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.strip().split()
    else:
        return "unknown"
    if not parts:
        return "unknown"
    first = Path(parts[0]).name.lower()
    if first in KNOWN_RUNNERS:
        return first
    if first.endswith(".sh"):
        return "shell"
    if first.endswith(".py"):
        return "python"
    return "generic"


def _first_present(record, keys):
    for k in keys:
        v = record.get(k)
        if v not in (None, ""):
            return v
    return None


def _exit_code(record):
    for k in ("exit_code", "exitCode", "status_code", "returncode"):
        v = record.get(k)
        if isinstance(v, int) and not isinstance(v, bool):
            return v
    status = record.get("status")
    if isinstance(status, dict):
        # Interpretation, stated plainly: an OpenTelemetry
        # ERROR status is treated as a failed run, exit 1.
        # UNSET means no outcome is recorded, so exit is None
        # and the check stays NOT OBSERVED, never FAILED.
        code = status.get("code")
        if isinstance(code, str):
            if code in ("STATUS_CODE_OK", "OK", "Ok", "Success"):
                return 0
            if code in ("STATUS_CODE_ERROR", "STATUS_CODE_UNSET"):
                return None if code == "STATUS_CODE_UNSET" else 1
        if isinstance(code, int):
            return code
    return None


def _times(record):
    start_raw = _first_present(record, ("start_timestamp", "startTime",
                                        "start_time", "started_at", "timestamp"))
    end_raw = _first_present(record, ("end_timestamp", "endTime",
                                      "end_time", "completed_at", "finished_at"))
    if start_raw is None and record.get("startTimeUnixNano") is not None:
        start_raw = record["startTimeUnixNano"]
    if end_raw is None and record.get("endTimeUnixNano") is not None:
        end_raw = record["endTimeUnixNano"]
    start = parse_any_time(start_raw)
    end = parse_any_time(end_raw)
    return start_raw, end_raw, (start.isoformat() if start else None), (end.isoformat() if end else None)


def record_to_run(record):
    """Convert one dict record to a ledger shaped run, or None.

    Returns None when the record carries no explicit command
    in a command field, argv list, or attributes command.
    A span or event name is never treated as a command.
    Meter style events with no command return None here;
    the caller counts them as events, not as failed runs.
    """
    if not isinstance(record, dict):
        return None
    command = _first_present(record, ("command", "command_raw", "cmd"))
    if command is None and isinstance(record.get("argv"), (list, tuple)):
        command = " ".join(str(p) for p in record["argv"])
    if command is None:
        attrs = record.get("attributes") or {}
        if isinstance(attrs, dict):
            command = _first_present(attrs, ("command", "command_raw", "cmd"))
        # Deliberately no fallback to record name: a span or
        # event name is not evidence a command ran. A name
        # only record returns None here and is counted as an
        # event without a command, never as a run.
    if command is None or (isinstance(command, str) and not command.strip()):
        return None
    if isinstance(command, (list, tuple)):
        command = " ".join(str(p) for p in command)
    command = str(command)
    label = _first_present(record, ("label", "id", "record_id", "run_id",
                                    "spanId", "traceId", "case_id")) or command
    start_raw, end_raw, start_iso, end_iso = _times(record)
    exit_code = _exit_code(record)
    stdout = record.get("stdout", "") or ""
    stderr = record.get("stderr", "") or ""
    output = record.get("output")
    if output is not None and not stdout and not stderr:
        stdout = str(output)
    digest = record.get("output_digest") or sha256_text(stdout + stderr)
    return {
        "label": str(label),
        "command_raw": command,
        "command_normalized": normalize_command(command),
        "runner": detect_runner(command),
        "working_directory": str(_first_present(record, ("working_directory", "cwd", "workdir")) or ""),
        "start_timestamp": start_iso,
        "end_timestamp": end_iso,
        "start_timestamp_raw": start_raw,
        "end_timestamp_raw": end_raw,
        "exit_code": exit_code,
        "output_digest": digest,
        "source": "universal_ingest",
        "trust_tier": 1,
        "raw_record": record,
    }


def _parse_json_objects(text):
    """Parse JSON array, JSONL, or pretty printed objects, tolerant."""
    events, bad = [], 0
    stripped = text.strip()
    if not stripped:
        return events, bad
    try:
        data = json.loads(stripped)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    events.append(item)
                else:
                    bad += 1
            return events, bad
        if isinstance(data, dict):
            if isinstance(data.get("runs"), list):
                for item in data["runs"]:
                    if isinstance(item, dict):
                        events.append(item)
                    else:
                        bad += 1
                return events, bad
            return [data], bad
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    idx, length = 0, len(text)
    while idx < length:
        while idx < length and text[idx] in " \t\r\n":
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            nxt = text.find("\n", idx)
            if nxt == -1:
                bad += 1
                break
            bad += 1
            idx = nxt + 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    events.append(item)
                else:
                    bad += 1
        else:
            bad += 1
        idx = end
    return events, bad


def _parse_plain_log(text):
    """Parse key: value blocks and shell style lines, tolerant."""
    runs, bad = [], 0
    blocks = [b for b in text.split("\n\n") if b.strip()]
    for block in blocks:
        record = {}
        used_keys = False
        for line in block.splitlines():
            m = _BLOCK_KEY_RE.match(line.strip())
            if m and m.group("key").strip().lower().replace(" ", "_") in (
                    "label", "command", "working_directory", "start_timestamp",
                    "end_timestamp", "exit_code", "stdout", "stderr"):
                key = m.group("key").strip().lower().replace(" ", "_")
                record[key] = m.group("val").strip()
                used_keys = True
        if used_keys:
            if "exit_code" in record:
                try:
                    record["exit_code"] = int(record["exit_code"])
                except ValueError:
                    record.pop("exit_code")
            run = record_to_run(record)
            if run is not None:
                runs.append(run)
            else:
                bad += 1
            continue
        for line in block.splitlines():
            m = _SHELL_LINE_RE.match(line.strip())
            if m:
                rec = {"command": m.group("cmd")}
                if m.group("exit") is not None:
                    rec["exit_code"] = int(m.group("exit"))
                run = record_to_run(rec)
                if run is not None:
                    runs.append(run)
                else:
                    bad += 1
            elif line.strip():
                bad += 1
    return runs, bad


def ingest_text(text):
    """Ingest any supported text shape. Never raises on bad input.

    Returns (runs, summary). Runs are ledger shaped. Summary
    counts records, runs, events without a command, unparseable
    records, unknown and generic runners, and missing exit codes.
    """
    runs, events_without_command, unparseable = [], 0, 0
    if text is None:
        return runs, {"records": 0, "runs": 0, "events_without_command": 0,
                      "unparseable": 0, "unknown_runner": 0, "generic_runner": 0,
                      "missing_exit_code": 0, "formats": []}
    stripped = text.strip()
    if not stripped:
        return runs, {"records": 0, "runs": 0, "events_without_command": 0,
                      "unparseable": 0, "unknown_runner": 0, "generic_runner": 0,
                      "missing_exit_code": 0, "formats": []}
    records, bad = _parse_json_objects(text)
    formats = ["json"]
    if records:
        for rec in records:
            run = record_to_run(rec)
            if run is not None:
                runs.append(run)
            else:
                events_without_command += 1
        unparseable += bad
    else:
        # No JSON record parsed at all: this is not a JSON
        # failure to report, it is a plain log to try next.
        # A JSON file with only bad lines still falls here,
        # and the plain parser counts those lines honestly.
        plain_runs, plain_bad = _parse_plain_log(text)
        runs.extend(plain_runs)
        unparseable += plain_bad
        formats = ["plain_log"]
        if not plain_runs and plain_bad:
            formats = ["plain_log_unparseable"]
    summary = {
        "records": len(records) if formats == ["json"] else len(runs) + unparseable,
        "runs": len(runs),
        "events_without_command": events_without_command,
        "unparseable": unparseable,
        "unknown_runner": sum(1 for r in runs if r.get("runner") == "unknown"),
        "generic_runner": sum(1 for r in runs if r.get("runner") == "generic"),
        "missing_exit_code": sum(1 for r in runs if r.get("exit_code") is None),
        "formats": formats,
    }
    return runs, summary


def ingest_file(path):
    """Ingest a file by content, not by extension. Never crashes."""
    try:
        text = Path(path).read_text()
    except (OSError, UnicodeDecodeError) as exc:
        return [], {"records": 0, "runs": 0, "events_without_command": 0,
                    "unparseable": 1, "unknown_runner": 0, "generic_runner": 0,
                    "missing_exit_code": 0, "formats": ["unreadable"],
                    "error": str(exc)}
    runs, summary = ingest_text(text)
    summary["ingest_file"] = str(path)
    return runs, summary


def infer_checks_from_runs(runs):
    """Build INFERRED check rows from observed commands, never human.

    Each distinct normalised command becomes one inferred row.
    Inferred rows are labelled INFERRED in the check file shape,
    and verifier.judge always returns NOT OBSERVED for them,
    with a flag stating they are not human acceptance.
    """
    seen = {}
    for r in runs:
        key = r.get("command_normalized") or r.get("command_raw")
        if key not in seen:
            seen[key] = r
    checks = []
    for i, (key, r) in enumerate(sorted(seen.items()), start=1):
        checks.append({
            "id": f"I{i}",
            "text": f"observed command: {r.get('command_raw')}",
            "check_type": "inferred",
            "required_command": r.get("command_raw"),
            "inferred_from": r.get("label") or r.get("command_raw"),
            "source": "inferred from observed runs, not human written",
            "applicability": "applies",
        })
    return checks
