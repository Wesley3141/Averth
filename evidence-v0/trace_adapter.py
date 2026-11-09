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
import errno
import json
import os
import re
import shlex
import stat
from pathlib import Path

# Fix 2026-11-04 (Gap 0, generality review): the previous version dropped
# the first token unconditionally, so "npm test", "cargo test" and
# "make test" all normalised to "test" and could all cite the same npm
# run. Only a Python interpreter token may be dropped; every other
# first token is part of the command and must be kept.
_PYTHON_INTERPRETER_RE = re.compile(r"^python(\d+(\.\d+)*)?(\.exe)?$")


def _is_python_interpreter(token):
    return bool(_PYTHON_INTERPRETER_RE.match(os.path.basename(token)))


def normalize_command(command):
    """Compare commands ignoring only the interpreter token.

    The same pytest invocation recorded under the Averth venv python
    and under bare ``python`` is the same check. Everything after the
    interpreter (executable, args, targets) must match exactly.
    The raw command is always retained alongside the normalised form.
    Non-Python first tokens (npm, cargo, make, go, pytest, ...) are
    kept: dropping them collapsed distinct runners onto one another.
    """
    if isinstance(command, (list, tuple)):
        parts = [str(p) for p in command]
    else:
        try:
            parts = shlex.split(str(command))
        except ValueError:
            # Unbalanced quoting (for example an unclosed quote) is
            # not a crash: fall back to a plain split, as detect_runner
            # in universal_ingest.py already does. The fallback form
            # is used consistently for both the check and the recorded
            # runs, so matching still compares like with like.
            parts = str(command).split()
    if not parts:
        return ""
    if len(parts) > 1 and _is_python_interpreter(parts[0]):
        return " ".join(parts[1:])
    return " ".join(parts)


def read_regular_file_bytes(path):
    """Read a file's bytes through one open, refusing non-regular files.

    Opens with os.O_RDONLY | os.O_NONBLOCK and fstats the open fd,
    so the bytes read are exactly the bytes that were checked: a
    FIFO swapped in between a stat and a read cannot block the
    open, because the open does not block (O_NONBLOCK) and the
    fstat sees the FIFO. No O_NOFOLLOW: a symlink to a regular
    file must keep working. Missing file -> FileNotFoundError;
    directory -> IsADirectoryError; FIFO, socket, or device ->
    ValueError; symlink loop -> ELOOP OSError. A regular file
    reads normally under O_NONBLOCK.
    """
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno == errno.ENXIO:
            # Opening a Unix socket (or a device with no
            # counterpart) fails with ENXIO, not a clean type
            # error: it is a non-regular file, refused the same
            # way as a FIFO.
            raise ValueError(f"not a regular file: {path}") from exc
        raise
    try:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(path))
        if not stat.S_ISREG(mode):
            raise ValueError(f"not a regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def sha256_text(text):
    import hashlib

    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def sha256_bytes(data):
    """sha256 digest of raw bytes, for files whose bytes are the record.

    Hashing bytes directly means a file in any encoding the JSON
    parser accepts (UTF-8, UTF-16, UTF-32) can be hashed, and no
    decode step can crash or silently change what is hashed. The
    digest is over the raw bytes, so the same content in a different
    encoding has a different digest.
    """
    import hashlib

    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_recorded_runs(path):
    """Return a list of normalised run dicts from a ledger JSON file.

    Every malformed shape refuses with ValueError, never a
    traceback: the file must be valid JSON holding an object or
    a list, "runs" must be a list, each entry must be a JSON
    object, and the command, label, stdout, and stderr fields
    must be strings when present. exit_code must be an integer
    (not a bool) or null when present: a string "0", a float
    0.0, or a bool would otherwise compare equal to an int in
    the judge and produce a false verdict. A FIFO (or other
    non-regular file) refuses instead of hanging, because the
    read goes through the single-open helper.
    """
    try:
        data = json.loads(read_regular_file_bytes(path))
    except RecursionError as exc:
        raise ValueError("recorded-run file is nested too deeply to parse") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"recorded-run file is not valid JSON: {exc}") from exc
    runs = []
    if isinstance(data, dict):
        raw_runs = data.get("runs", [])
        marker = data.get("final_edit_marker")
    elif isinstance(data, list):
        raw_runs = data
        marker = None
    else:
        raise ValueError("recorded-run file must be a JSON object or list")
    if not isinstance(raw_runs, list):
        raise ValueError("'runs' must be a list")
    if marker is not None and not isinstance(marker, str):
        raise ValueError("final_edit_marker must be a string")
    for r in raw_runs:
        if not isinstance(r, dict):
            raise ValueError("each recorded run must be a JSON object")
        command = r.get("command", "")
        if command is None:
            command = ""
        if not isinstance(command, str):
            raise ValueError("recorded run command must be a string")
        stdout = r.get("stdout", "")
        stderr = r.get("stderr", "")
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            raise ValueError("recorded run stdout/stderr must be strings")
        label = r.get("label", "")
        if label is None:
            label = ""
        if not isinstance(label, str):
            raise ValueError("recorded run label must be a string")
        exit_code = r.get("exit_code")
        if exit_code is not None and (not isinstance(exit_code, int)
                                      or isinstance(exit_code, bool)):
            raise ValueError("recorded run exit_code must be an integer or null")
        output = stdout + stderr
        runs.append(
            {
                "label": label,
                "command_raw": command,
                "command_normalized": normalize_command(command),
                "working_directory": r.get("working_directory", ""),
                "start_timestamp": r.get("start_timestamp"),
                "end_timestamp": r.get("end_timestamp"),
                "exit_code": exit_code,
                "output_digest": r.get("output_digest") or sha256_text(output),
                "source": "imported",
                "trust_tier": 1,
            }
        )
    return runs, marker


def _trace_token_count(value):
    """Parse a trace token count: int (not bool) or a numeric string.

    Returns the int, or None when the value is not a usable
    count. A bool is an int subclass but is never a token count;
    a float counts only when integral; a string counts only when
    it parses as an int. A negative count is malformed content,
    never a count: token totals must not go negative. Anything
    else (list, dict, "abc", 12.5, -5) is malformed content,
    not a count.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer():
        return int(value) if value >= 0 else None
    if isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def load_trace_events(path):
    """Summarise a JSONL agent trace. No judgments are produced here.

    The file is read through the single-open helper, so a FIFO
    (or other non-regular file) refuses with ValueError instead
    of hanging the open. A line that is not a JSON object is
    counted unparseable, never a crash, and a line nested too
    deeply to parse is counted unparseable the same way. A line
    that parses but carries a wrong-typed field the summary
    reads (a non-string type, a non-string case_id, or
    non-numeric token counts on a model event) refuses with
    ValueError: the summary must not silently drop or miscount
    malformed content.
    """
    counts = {}
    cases = set()
    model_events = 0
    input_tokens = 0
    output_tokens = 0
    retry_events = 0
    lines = 0
    text = read_regular_file_bytes(path).decode("utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lines += 1
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, RecursionError):
            counts["unparseable"] = counts.get("unparseable", 0) + 1
            continue
        if not isinstance(ev, dict):
            counts["unparseable"] = counts.get("unparseable", 0) + 1
            continue
        t = ev.get("type", "unknown")
        if not isinstance(t, str):
            raise ValueError(f"trace line has a non-string type: {t!r}")
        case_id = ev.get("case_id")
        if (case_id is not None and (isinstance(case_id, bool)
                                     or not isinstance(case_id, (str, int)))):
            raise ValueError(f"trace line has a non-string case_id: {case_id!r}")
        in_tok = out_tok = 0
        if t == "model":
            raw_in = ev.get("input_tokens", 0)
            raw_out = ev.get("output_tokens", 0)
            in_tok = _trace_token_count(0 if raw_in is None else raw_in)
            out_tok = _trace_token_count(0 if raw_out is None else raw_out)
            if in_tok is None or out_tok is None:
                raise ValueError("trace model event has non-numeric token counts")
        counts[t] = counts.get(t, 0) + 1
        if case_id is not None:
            cases.add(case_id)
        if t == "model":
            model_events += 1
            input_tokens += in_tok
            output_tokens += out_tok
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
