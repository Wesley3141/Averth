"""Default checks (trace-observed) for ``averth try``.

These checks need NO human-written checks. They judge only what a
local agent transcript shows, from a new read-only extraction pass
over the raw transcript: the meter's importers deliberately do NOT
emit tool events, so the evidence here comes from the transcript
itself (Claude ``tool_use`` / ``tool_result`` content blocks; Codex
``response_item`` function_call / function_call_output records;
mini-SWE-agent `````bash`` fenced commands in trajectory messages).

This judge is SEPARATE from V0 (evidence-v0 is a separate package,
not installed in the meter venv; nothing here shells out to it or
depends on it). It uses the same five-verdict vocabulary
(VERIFIED / FAILED / NOT OBSERVED / EXTERNAL-UNVERIFIABLE /
NOT APPLICABLE), but every verdict cites its observation (command +
exit code, or "no such record in trace") and is labelled everywhere
as "default checks (trace-observed)", never as human-written V0
checks. It never re-executes a command and never invents: only what
the record shows is claimed (command string, output, is_error /
exit code WHERE PRESENT).

Outcome signals, stated explicitly (a Wave 1 interpretation decision;
see WAVE1-REPORT.md): neither transcript shape carries a numeric exit
code on every command record. Claude ``tool_result`` blocks carry an
``is_error`` boolean, which the judge treats as the transcript's
observed outcome for that command. This assumes Claude Code sets
``is_error`` from the command's exit status; that assumption is not
verified against Claude Code's documentation. A command with NO
matching tool_result, and no is_error / exit code anywhere, has an
unknown outcome: the check says so and judges NOT OBSERVED, never
guesses. Codex ``function_call_output`` records carry neither field in
the documented format, so Codex test/build commands are NOT OBSERVED
unless a record happens to carry an ``exit_code`` field.
Mini-SWE-agent trajectories DO carry a per-command exit status: each
bash command's following user message carries a ``<returncode>``
tag, which ``extract_traj`` parses and D1/D2/D3 judge on.

The five default checks (semantics pinned here, in code and docs):

- D1 tests executed: a test command observed (pytest, unittest,
  npm/yarn/pnpm test, go test, cargo test, etc.) with a successful
  outcome -> VERIFIED; with a failed outcome -> FAILED; none
  observed, or observed with no outcome signal -> NOT OBSERVED.
  Judged on the LAST observed test command (the run's final state).
- D2 build passed: same shape for a build command (go build, cargo
  build, npm run build, make, tsc, ...).
- D3 files touched vs files tested: judged ONLY on what the trace
  shows (edited files from Edit/Write tool calls vs test files named
  in the LAST observed test command, matched by file stem). A bare test
  command with no file arguments runs the whole suite, so with a
  successful outcome it VERIFIES the touched files, with a failed
  outcome it FAILS, and with an unknown outcome it is NOT OBSERVED.
  A named test run is gated on outcome the same way: a passing named
  run whose files stem-match every edited source file VERIFIES them
  (name matching only; actual coverage is never inferred), a failing
  named run FAILS, and a named run with an unknown outcome is
  NOT OBSERVED. When a test command names specific files and an edited
  source file has no stem-matching test among them -> FAILED, citing
  the unmatched files. Edited files that are themselves test files
  are excluded before judging, so editing only test files yields
  NOT OBSERVED. When coverage cannot be established from the trace (no
  edited files, no test command, or no outcome signal on a
  full-suite run) -> NOT OBSERVED with the reason stated. Name
  matching is the criterion, stated in the observation; actual
  coverage is never inferred.
- D4 duplicate-invocation overhead: counts repeated identical tool
  invocations (the same command run 2+ times) as OBSERVED
  duplicate-invocation overhead. Labelled exactly that, NEVER as
  meter retries (the Claude/Codex importers emit no retry events,
  by design). Threshold (pinned): 5 or more duplicate invocations
  -> FAILED; fewer -> VERIFIED. The count is always shown when any
  tool command was observed. No commands at all -> NOT OBSERVED.
  The threshold is a pinned judgment call, not a measured bar: on
  the 50-trace public audit the duplicate-count distribution was
  {0: 2, 1: 16, 2: 8, 3: 7, 4: 7, 5: 3, 6: 2, 8: 1, 10: 1, 11: 1,
  20: 2}; 10/50 fail at >=5, 24/50 at >=3.
- D5 trace-recorded vs estimated cost: when the trace carries its own
  recorded cost (Claude ``result.total_cost_usd``, mini-SWE-agent
  ``info.model_stats.instance_cost``) compare with the metered
  estimate: agree within 5% -> VERIFIED; differ -> FAILED (both
  figures and the ratio stated, at 4dp in the observation); no recorded
  figure -> NOT OBSERVED; subscription billing where list-price
  comparison is meaningless (Codex) -> EXTERNAL-UNVERIFIABLE with
  the reason. The recorded figure is what the trace reports; Averth
  does not verify it against any invoice or bill. In a scan, D5
  resolves only when every scanned Claude session carries a recorded
  cost and no Codex session is present; a partial comparison would
  mislead, so a partial record is NOT OBSERVED.

Unknown rate: the fraction of the five checks whose verdict is
NOT OBSERVED or EXTERNAL-UNVERIFIABLE.
"""

import codecs
import json
import math
import os
import re
import stat

LABEL = "default checks (trace-observed)"

VERDICTS = ("VERIFIED", "FAILED", "NOT OBSERVED",
            "EXTERNAL-UNVERIFIABLE", "NOT APPLICABLE")

# D5: recorded vs estimated agree when within 5% of each other.
D5_TOLERANCE = 0.05

# Float slack for the inclusive 5% boundary: 0.0105/0.0100 is
# 1.0500000000000000444 in binary float, so a bare `<= 0.05`
# rejects a mathematically exact +5% while 0.21/0.20 (also exactly
# +5%) passes by float luck. 1e-9 is far larger than any float
# error in this ratio (~1e-16) and far smaller than any difference
# a reader could see at the printed 4dp, so it admits only the
# boundary itself, never a genuinely over-tolerance case.
D5_TOLERANCE_EPSILON = 1e-9

# D4: this many duplicate identical command invocations (counting
# each repeat past the first) fails the check. Up to four re-runs are
# normal agent iteration (fix, then re-run); five or more identical
# re-invocations indicate a loop / overhead worth flagging. The
# threshold is a pinned judgment call, not a measured bar: on the
# 50-trace public audit the duplicate-count distribution was
# {0: 2, 1: 16, 2: 8, 3: 7, 4: 7, 5: 3, 6: 2, 8: 1, 10: 1, 11: 1,
# 20: 2} (10/50 fail at >=5, 24/50 at >=3, 7/50 at >=6).
D4_DUPLICATE_FAIL_THRESHOLD = 5

_BASH_FENCE = re.compile(r"```bash[ \t]*\n?(.*?)```",
                         re.DOTALL | re.IGNORECASE)

# Test runners, matched as whole words / phrases in the command
# string. Checked before build patterns (``make test`` is a test,
# not a build).
_TEST_PATTERNS = [
    r"\bpytest\b",
    r"\bpython3?\s+-m\s+pytest\b",
    r"\bpython3?\s+-m\s+unittest\b",
    r"\bunittest\b",
    r"\bgo\s+test\b",
    r"\bcargo\s+test\b",
    r"\bnpm\s+(?:test|run\s+test)\b",
    r"\byarn\s+test\b",
    r"\bpnpm\s+test\b",
    r"\bbun\s+test\b",
    r"\bnpx\s+(?:jest|vitest)\b",
    r"\bjest\b",
    r"\bvitest\b",
    r"\bmake\s+test\b",
    r"\bctest\b",
    r"\brspec\b",
    r"\bmvn\w*\s+.*\btest\b",
    r"\bgradle\w*\s+test\b",
    r"\bdotnet\s+test\b",
]

# Build commands. Bare ``make`` (default target) counts as a build;
# ``make <other-target>`` does not (``make lint`` builds nothing).
_BUILD_PATTERNS = [
    r"\bgo\s+build\b",
    r"\bcargo\s+build\b",
    r"\bnpm\s+run\s+build\b",
    r"\byarn\s+build\b",
    r"\bpnpm\s+build\b",
    r"\btsc\b",
    r"\bwebpack\b",
    r"\bvite\s+build\b",
    r"\bmvn\w*\s+.*\b(?:compile|package)\b",
    r"\bgradle\w*\s+(?:build|assemble)\b",
    r"\bdotnet\s+build\b",
    r"\bcmake\s+--build\b",
    r"\bxcodebuild\b",
    r"\bmake\s+(?:build|all)\b",
    r"(?:^|;|&&|\|\|)\s*make\s*(?:$|;|&&|\|\||\s*--)",
]

_TEST_FILE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".go",
                       ".rs", ".rb", ".java", ".kt", ".swift", ".php")


def _is_test_file_token(token):
    """True when a command token names a test file.

    A token counts when it ends with a known source suffix and looks
    like a test path: it sits under a test(s) directory, or its stem
    starts with ``test_``, ends with ``_test``, or contains
    ``.test.`` / ``.spec.``.
    """
    token = token.strip("\"'")
    if not token.endswith(_TEST_FILE_SUFFIXES):
        return False
    base = os.path.basename(token)
    stem = os.path.splitext(base)[0]
    if "/test/" in token or "/tests/" in token \
            or token.startswith("test/") or token.startswith("tests/"):
        return True
    if stem.startswith("test_") or stem.endswith("_test") \
            or ".test." in base or ".spec." in base:
        return True
    return False


def _test_stem(path):
    """Stem used to match an edited file to its test file.

    ``tests/test_cli.py`` -> ``cli``; ``src/foo.test.ts`` -> ``foo``;
    ``pkg/bar_test.go`` -> ``bar``.
    """
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    if stem.endswith(".test"):
        stem = stem[:-5]
    if stem.endswith(".spec"):
        stem = stem[:-5]
    if stem.startswith("test_"):
        stem = stem[5:]
    if stem.endswith("_test"):
        stem = stem[:-5]
    return stem


def _is_test_path(path):
    """True when an edited file is itself a test file."""
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    return (stem.startswith("test_") or stem.endswith("_test")
            or ".test." in base or ".spec." in base
            or "/test/" in path or "/tests/" in path
            or path.startswith("test/") or path.startswith("tests/"))


# A heredoc file-creation write: ``cat <<'EOF' > test_x.py`` (or
# ``>>`` append, or the redirect before the heredoc marker). The
# command being run is ``cat`` writing a file; the test-named file
# is a redirection target, not an executed script, and the heredoc
# body is file contents, not a command line — so a word in the body
# (e.g. ``import unittest`` inside the written script) must not
# classify the write as a test or build run. Checked against the
# 50-trace public audit: every false test classification of this
# shape is a bare ``cat <<'EOF' > <file>`` first line; no ``tee`` /
# ``printf`` / ``echo`` write false-classifies there, so coverage
# is ``cat`` only.
_HEREDOC_WRITE = re.compile(
    r"^\s*cat\s+[^\n]*<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")


def _strip_heredoc_writes(command):
    """Remove ``cat <<DELIM > file`` heredoc writes from a
    multi-line fence command: each write's fence line through its
    terminator line (the line equal to the delimiter) is dropped,
    so the written file's contents are never pattern-matched as a
    command line. Any shell text outside a heredoc write is kept
    and still classified on its own merits (a fence may chain a
    write and a genuine run). An unterminated heredoc drops the
    rest of the fence: the remainder is body, not commands."""
    lines = command.split("\n")
    kept = []
    i = 0
    while i < len(lines):
        match = _HEREDOC_WRITE.match(lines[i])
        if not match:
            kept.append(lines[i])
            i += 1
            continue
        delim = match.group(1)
        i += 1
        while i < len(lines) and lines[i].strip() != delim:
            i += 1
        if i < len(lines):
            i += 1  # drop the terminator line itself
    return "\n".join(kept)


def classify_command(command):
    """Classify a shell command string.

    Returns ``("test", [test-file tokens])``,
    ``("build", [])``, or ``(None, [])``. Test patterns are checked
    first, so ``make test`` classifies as a test, not a build.
    Heredoc file-creation writes are stripped first (see
    ``_strip_heredoc_writes``): ``cat <<'EOF' > test_x.py`` is a
    file write, not a test run, even when the written script's body
    mentions a test runner.
    """
    if not isinstance(command, str) or not command.strip():
        return None, []
    command = _strip_heredoc_writes(command)
    if not command.strip():
        return None, []
    for pattern in _TEST_PATTERNS:
        if re.search(pattern, command):
            targets = [t for t in re.split(r"\s+", command)
                       if _is_test_file_token(t)]
            return "test", targets
    for pattern in _BUILD_PATTERNS:
        if re.search(pattern, command):
            return "build", []
    return None, []


def _new_evidence(source):
    return {
        "source": source,
        "commands": [],       # {"command", "outcome": True/False/None,
                              #  "outcome_note", "session"}
        "edited_files": [],   # file paths from Edit/Write tool calls
        "recorded_cost": None,
        "sessions": [],       # session ids / file basenames seen
        "unparseable_lines": 0,
    }


def _is_sidechain(record):
    return record.get("isSidechain") is True \
        or record.get("is_sidechain") is True


def _content_blocks(record):
    """Content blocks of a Claude record's message, or [].

    Accepts the ``message.content`` list shape; a plain-string
    content carries no tool blocks.
    """
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _is_regular_file(path):
    """True when ``path`` is a regular file (not a FIFO, socket, or
    directory). A FIFO named ``*.jsonl`` would block forever on open
    for read, so discovery and extraction refuse non-regular files
    instead of opening them."""
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


# A trajectory's top-level keys precede its ``messages`` array, but a
# large leading ``info`` object can push ``messages`` far past any
# fixed sniff prefix: three of the 50 public-audit trajectories carry
# ``messages`` at byte 68,872 / 97,401 / 154,285, past a 64 KiB
# prefix, so a fixed-prefix sniff silently reads them as "no tool
# records" (every check NOT OBSERVED). The scanner below reads in
# chunks until the key is found or the outermost object closes, so
# detection does not depend on where the key sits. The 16 MiB cap
# only guards against pathological files; a real trajectory's
# leading block is under 200 KiB.
_TRAJ_SNIFF_LIMIT = 16 * 1024 * 1024
_TOP_KEY_MAX_LEN = 256


class _TopLevelKeyScanner:
    """Incremental scanner for the top-level keys of one JSON object.

    Feed text chunks; ``keys`` accumulates the depth-1 keys seen so
    far and ``closed`` turns True when the outermost value ends (or
    when the first non-whitespace character shows the top-level
    value is not an object at all, e.g. a bare JSON list). A string
    that starts at depth 1 and is followed (after whitespace) by
    ``:`` is a key; a string value at depth 1 is followed by ``,``
    or ``}`` instead, and keys of nested objects start deeper, so
    the rule is exact for valid JSON. String, escape, depth, and
    pending-key state carry across chunk boundaries. Keys longer
    than 256 characters are skipped (no key this scanner is asked
    about is anywhere near that long).
    """

    def __init__(self):
        self.keys = set()
        self.closed = False
        self.depth = 0
        self.in_string = False
        self.escaped = False
        self._str_depth = None
        self._buf = []
        self._too_long = False
        self._pending = None
        self._saw_value = False

    def feed(self, text):
        for ch in text:
            if self.closed:
                return
            if self.in_string:
                if self.escaped:
                    self.escaped = False
                    if self._str_depth == 1 and not self._too_long:
                        self._buf.append(ch)
                elif ch == "\\":
                    self.escaped = True
                    if self._str_depth == 1 and not self._too_long:
                        self._buf.append(ch)
                elif ch == '"':
                    self.in_string = False
                    if self._str_depth == 0:
                        # A string is the whole top-level value: no
                        # top-level keys can follow it.
                        self.closed = True
                        return
                    if self._str_depth == 1 and not self._too_long:
                        self._pending = "".join(self._buf)
                    self._buf = []
                else:
                    if self._str_depth == 1 and not self._too_long:
                        self._buf.append(ch)
                        if len(self._buf) > _TOP_KEY_MAX_LEN:
                            self._too_long = True
                            self._buf = []
                continue
            if self._pending is not None:
                if ch in " \t\r\n":
                    continue
                if ch == ":":
                    self.keys.add(self._pending)
                self._pending = None
            if ch == '"':
                self.in_string = True
                self.escaped = False
                self._str_depth = self.depth
                self._buf = []
                self._too_long = False
            elif ch in "{[":
                if not self._saw_value:
                    self._saw_value = True
                    if ch != "{":
                        # Top-level value is not an object: no
                        # top-level keys exist. (A bare JSON list,
                        # e.g. a Langfuse export, stops here.)
                        self.closed = True
                        return
                self.depth += 1
            elif ch in "}]":
                self.depth -= 1
                if self.depth <= 0:
                    self.closed = True
                    return
            elif ch not in " \t\r\n":
                self._saw_value = True


def extract_claude(path):
    """Extract trace-observed evidence from one Claude Code session.

    Reads ``tool_use`` blocks (Bash commands, Edit/Write file paths),
    matching ``tool_result`` blocks (``is_error`` outcome), and the
    ``result`` record's ``total_cost_usd``. Sidechain records are
    skipped, matching the claude importer. Lines that fail to parse
    are counted, never crash the extraction: the importer has
    already validated the file when the scan runs, so a count here
    is a belt-and-braces signal, not a second validator. ``#``
    comment lines are skipped, not counted: like the importer and
    the sniffer, they carry no records. A line
    that is not valid UTF-8 is counted the same way (the file is
    read as bytes and decoded line by line, so one bad line cannot
    abort the rest). ``pending`` is keyed only by non-empty-string
    tool ids, so a ``tool_use`` block with no id can never claim
    another command's outcome.
    """
    evidence = _new_evidence("claude")
    session = os.path.basename(path)
    evidence["sessions"].append(session)
    if not _is_regular_file(path):
        return evidence
    # tool_use_id -> index into evidence["commands"].
    pending = {}
    last_cost = None
    try:
        f = open(path, "rb")
    except OSError:
        return evidence
    with f:
        for raw in f:
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                evidence["unparseable_lines"] += 1
                continue
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                # Comment lines carry no records: skipped, not
                # counted as unparseable (matches the importer).
                continue
            try:
                record = json.loads(line)
            except ValueError:
                evidence["unparseable_lines"] += 1
                continue
            if not isinstance(record, dict):
                evidence["unparseable_lines"] += 1
                continue
            rtype = record.get("type")
            if rtype == "result":
                cost = record.get("total_cost_usd")
                if (isinstance(cost, (int, float))
                        and not isinstance(cost, bool)
                        and math.isfinite(cost) and cost >= 0):
                    last_cost = float(cost)
                continue
            if _is_sidechain(record):
                continue
            if rtype not in ("assistant", "user"):
                continue
            for block in _content_blocks(record):
                btype = block.get("type")
                if btype == "tool_use":
                    name = block.get("name")
                    tool_id = block.get("id")
                    data = block.get("input")
                    if not isinstance(data, dict):
                        continue
                    if name == "Bash":
                        command = data.get("command")
                        if isinstance(command, str) and command.strip():
                            if isinstance(tool_id, str) and tool_id:
                                pending[tool_id] = len(
                                    evidence["commands"])
                            evidence["commands"].append({
                                "command": command,
                                "outcome": None,
                                "outcome_note": "no matching tool_result "
                                                "in trace",
                                "session": session,
                            })
                    elif name in ("Edit", "Write"):
                        file_path = data.get("file_path")
                        if isinstance(file_path, str) and file_path:
                            evidence["edited_files"].append(file_path)
                elif btype == "tool_result":
                    tool_id = block.get("tool_use_id")
                    if tool_id in pending:
                        idx = pending.pop(tool_id)
                        is_error = block.get("is_error")
                        if is_error is True:
                            evidence["commands"][idx]["outcome"] = False
                            evidence["commands"][idx]["outcome_note"] = (
                                "tool_result is_error=true; no numeric "
                                "exit code in transcript")
                        elif is_error is False:
                            evidence["commands"][idx]["outcome"] = True
                            evidence["commands"][idx]["outcome_note"] = (
                                "tool_result is_error=false; no numeric "
                                "exit code in transcript")
                        # is_error absent or non-boolean: outcome stays
                        # unknown; the note already says so.
    if last_cost is not None:
        evidence["recorded_cost"] = last_cost
    return evidence


def _codex_command(arguments):
    """Command string from a Codex function_call's arguments.

    ``arguments`` may be a JSON string (``{"cmd": [...]}`` or
    ``{"command": "..."}``) or a dict. Returns the command string, or
    None when the call carries no command string (the invocation is
    still recorded, but it cannot be classified as a test/build
    command or counted as a duplicate of a known command).
    """
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return None
    if not isinstance(arguments, dict):
        return None
    cmd = arguments.get("command")
    if isinstance(cmd, str) and cmd.strip():
        return cmd
    cmd = arguments.get("cmd")
    if isinstance(cmd, str) and cmd.strip():
        return cmd
    if isinstance(cmd, list):
        parts = [p for p in cmd if isinstance(p, str)]
        if parts:
            return " ".join(parts)
    return None


def extract_codex(path):
    """Extract trace-observed evidence from one Codex rollout file.

    Reads ``response_item`` function_call records (command string
    where present) and matching function_call_output records
    (``exit_code`` where present; the documented format carries
    none, so Codex command outcomes are usually unknown). Codex
    carries no recorded cost: subscription billing makes list-price
    comparison meaningless, so D5 is EXTERNAL-UNVERIFIABLE for any
    scan containing a Codex session.
    """
    evidence = _new_evidence("codex")
    session = os.path.basename(path)
    evidence["sessions"].append(session)
    if not _is_regular_file(path):
        return evidence
    pending = {}
    try:
        f = open(path, "rb")
    except OSError:
        return evidence
    with f:
        for raw in f:
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                evidence["unparseable_lines"] += 1
                continue
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                # Comment lines carry no records: skipped, not
                # counted as unparseable (matches the importer).
                continue
            try:
                record = json.loads(line)
            except ValueError:
                evidence["unparseable_lines"] += 1
                continue
            if not isinstance(record, dict):
                evidence["unparseable_lines"] += 1
                continue
            if record.get("type") != "response_item":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                payload = record
            ptype = payload.get("type")
            if ptype == "function_call":
                command = _codex_command(payload.get("arguments"))
                call_id = payload.get("call_id")
                if isinstance(call_id, str) and call_id:
                    pending[call_id] = len(evidence["commands"])
                evidence["commands"].append({
                    "command": command,
                    "outcome": None,
                    "outcome_note": "function_call_output carries no "
                                    "exit code in the documented "
                                    "rollout format",
                    "session": session,
                })
            elif ptype == "function_call_output":
                call_id = payload.get("call_id")
                if call_id in pending:
                    idx = pending.pop(call_id)
                    exit_code = payload.get("exit_code")
                    if (isinstance(exit_code, int)
                            and not isinstance(exit_code, bool)):
                        evidence["commands"][idx]["outcome"] = (
                            exit_code == 0)
                        evidence["commands"][idx]["outcome_note"] = (
                            "function_call_output exit_code=%d"
                            % exit_code)
                    # No exit_code field: outcome stays unknown.
    return evidence


_RETURNCODE = re.compile(r"<returncode>(-?\d+)</returncode>")


def extract_traj(path):
    """Extract trace-observed evidence from a mini-SWE-agent trajectory.

    Bash fenced commands in assistant message text are the commands.
    Each command's exit status is the ``<returncode>`` tag in the
    following user message: returncodes are associated with their
    preceding bash command in order (the first returncode in a user
    message belongs to the earliest preceding command still awaiting
    one). A command with no following returncode has an unknown
    outcome (D1/D2 judge NOT OBSERVED on it, never guess). The
    recorded cost is ``info.model_stats.instance_cost``.
    """
    from averth.importers import miniswe

    evidence = _new_evidence("traj")
    evidence["sessions"].append(os.path.basename(path))
    if not _is_regular_file(path):
        return evidence
    evidence["recorded_cost"] = miniswe.traj_instance_cost(path)
    try:
        with open(path, encoding="utf-8") as f:
            traj = json.load(f)
    except (OSError, ValueError):
        return evidence
    if not isinstance(traj, dict):
        return evidence
    messages = traj.get("messages")
    if not isinstance(messages, list):
        return evidence
    pending = []  # indices of commands awaiting a <returncode>
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        text = miniswe._message_text(message)
        if role == "assistant":
            for match in _BASH_FENCE.finditer(text):
                command = match.group(1).strip()
                if command:
                    pending.append(len(evidence["commands"]))
                    evidence["commands"].append({
                        "command": command,
                        "outcome": None,
                        "outcome_note": "no <returncode> for this "
                                        "command in the following user "
                                        "message",
                        "session": evidence["sessions"][0],
                    })
        elif role == "user":
            for match in _RETURNCODE.finditer(text):
                if not pending:
                    break
                idx = pending.pop(0)
                rc = int(match.group(1))
                evidence["commands"][idx]["outcome"] = (rc == 0)
                evidence["commands"][idx]["outcome_note"] = (
                    "trajectory <returncode>%d</returncode>" % rc)
    return evidence


def _scan_file_top_level_keys(path):
    """Top-level keys of the JSON object in ``path``.

    Scans the file in chunks with ``_TopLevelKeyScanner`` until the
    keys are resolved (``messages`` found, or the outermost object
    closes) or the 16 MiB cap is hit. Never raises: an unreadable
    file yields an empty set. The cap only guards against
    pathological files; a real trajectory's leading block is under
    200 KiB, but a fixed small prefix is not safe (three of the 50
    public-audit trajectories carry ``messages`` past 64 KiB).
    """
    scanner = _TopLevelKeyScanner()
    try:
        decoder = codecs.getincrementaldecoder("utf-8")(
            errors="replace")
        with open(path, "rb") as f:
            scanned = 0
            while scanned < _TRAJ_SNIFF_LIMIT:
                chunk = f.read(65536)
                if not chunk:
                    break
                scanned += len(chunk)
                scanner.feed(decoder.decode(chunk))
                if "messages" in scanner.keys or scanner.closed:
                    break
    except OSError:
        return set()
    return scanner.keys


# Record-type markers for the JSONL shapes ``averth try`` meters.
# Strong markers decide a shape on their own; weak markers decide
# only with corroboration (see ``sniff_jsonl_shape``).
_JSONL_EVENT_TYPES = frozenset(
    ("start", "model", "tool", "retry", "escalation", "end"))
_CLAUDE_GENERIC_TYPES = frozenset(
    ("system", "summary", "result", "file-history-snapshot",
     "queue-operation"))
_CODEX_GENERIC_TYPES = frozenset(
    ("session_meta", "turn_context", "event_msg"))


def sniff_jsonl_shape(path):
    """Sniff which JSONL shape a file is, by a tally over record types.

    Returns ``"jsonl"``, ``"claude"``, or ``"codex"``, or ``None``
    when no record decides the shape. Raises ``ValueError`` when
    the file mixes shapes, or is not readable.

    Strong markers: Averth JSONL events (start/model/tool/retry/
    escalation/end); Claude assistant/user records with a
    ``message.content`` list; Codex ``response_item`` records.
    Exactly one format with strong markers wins; strong markers
    from two formats make the file ambiguous, never first-wins: a
    stray record must not silently reclassify the rest of the
    file. Weak markers: a Claude assistant/user record without a
    ``message.content`` list decides alone; generic weak markers
    (system/summary/result/file-history-snapshot/queue-operation
    for Claude; session_meta/turn_context/event_msg for Codex)
    decide only with corroboration — two or more weak records of
    the same format. Weak markers from both sides, each decisive,
    make the file ambiguous.

    The scan reads the first 10 JSON object lines (``#`` comment
    lines are skipped before parsing and do not count; blank lines
    and non-dict JSON values do not count toward the 10 object
    lines, though a non-dict JSON value still counts toward the
    raw-line cap below; a line that is not JSON, or not UTF-8,
    stops the scan). A raw-line cap of 50 JSON-parseable lines per
    phase bounds the scan; ``#`` comment lines and blank lines do
    not count toward it. When no strong
    marker was seen in the first 10 object lines and the file has
    more lines, the scan continues up to 50 object lines looking
    for a strong marker. A strong marker past the 50-line extension
    is never seen: once the extension is exhausted, the weak markers
    decide. A record whose ``type`` is not a string decides nothing
    (an unhashable ``type`` must never raise). The file is read
    incrementally, never loaded whole.
    """
    strong = {"jsonl": 0, "claude": 0, "codex": 0}
    weak_bare_claude = 0
    weak_claude = 0
    weak_codex = 0
    dict_lines = 0
    raw_lines = 0
    limit = 10
    try:
        with open(path, "rb") as f:
            while True:
                raw = f.readline(1024 * 1024)
                if not raw:
                    break
                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    break
                if not line or line.startswith("#"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    break
                # Only JSON-parseable lines count toward the cap:
                # comment and blank lines do not.
                raw_lines += 1
                if raw_lines > 50:
                    break
                if not isinstance(obj, dict):
                    continue
                dict_lines += 1
                rtype = obj.get("type")
                if isinstance(rtype, str):
                    if rtype == "response_item":
                        strong["codex"] += 1
                    elif rtype in ("assistant", "user"):
                        message = obj.get("message")
                        if isinstance(message, dict) \
                                and isinstance(message.get("content"),
                                               list):
                            strong["claude"] += 1
                        else:
                            weak_bare_claude += 1
                    elif rtype in _JSONL_EVENT_TYPES:
                        strong["jsonl"] += 1
                    elif rtype in _CLAUDE_GENERIC_TYPES:
                        weak_claude += 1
                    elif rtype in _CODEX_GENERIC_TYPES:
                        weak_codex += 1
                if dict_lines >= limit:
                    if limit == 10 and not any(strong.values()):
                        limit = 50
                        raw_lines = 0
                        continue
                    break
    except OSError as e:
        raise ValueError("%s is not readable: %s" % (path, e))
    strong_formats = [k for k, v in strong.items() if v]
    if len(strong_formats) > 1:
        raise ValueError(
            "%s is ambiguous: it mixes record types from more than "
            "one shape (%s); it is not one supported shape (Averth "
            "JSONL, Claude session, or Codex rollout)"
            % (path, " and ".join(sorted(strong_formats))))
    if len(strong_formats) == 1:
        return strong_formats[0]
    claude_decisive = weak_bare_claude >= 1 or weak_claude >= 2
    codex_decisive = weak_codex >= 2
    if claude_decisive and codex_decisive:
        raise ValueError(
            "%s is ambiguous: it carries weak markers for both the "
            "Claude session and Codex rollout shapes; it is not one "
            "supported shape"
            % path)
    if claude_decisive:
        return "claude"
    if codex_decisive:
        return "codex"
    return None


def extract_from_file(path):
    """Extract evidence from any explicit-trace file, sniffing shape.

    A JSON object with a top-level ``messages`` key is a mini-SWE-agent
    trajectory; otherwise the first lines are sniffed for Claude
    ``tool_use`` blocks (``type: assistant``) or Codex
    ``response_item`` function_call records. A file matching neither
    shape yields empty evidence (every check NOT OBSERVED with the
    reason stated) instead of an error: JSONL events and Langfuse
    exports carry no tool-use records.

    The sniff is incremental and bounded: the top-level keys are
    scanned in chunks (see ``_TopLevelKeyScanner``) until ``messages``
    is found or the outermost object closes, capped at 16 MiB, and
    the JSONL shape is sniffed by ``sniff_jsonl_shape`` (first 10
    object lines, extended to 50 when only weak markers were seen).
    The whole file is never loaded just to detect its shape. Only
    a detected trajectory is then parsed in full, once, by
    ``extract_traj``. A file whose shape is ambiguous yields empty
    evidence (every check NOT OBSERVED with the reason stated),
    never an error: the CLI refuses ambiguous files before this
    function is ever called for a report.
    """
    if not _is_regular_file(path):
        evidence = _new_evidence("unknown")
        evidence["sessions"].append(os.path.basename(path))
        return evidence
    if "messages" in _scan_file_top_level_keys(path):
        return extract_traj(path)
    try:
        shape = sniff_jsonl_shape(path)
    except ValueError:
        shape = None
    if shape == "claude":
        return extract_claude(path)
    if shape == "codex":
        return extract_codex(path)
    evidence = _new_evidence("unknown")
    evidence["sessions"].append(os.path.basename(path))
    return evidence


def merge_evidence(evidences):
    """Merge per-file evidence into one scan-wide evidence dict."""
    merged = _new_evidence("scan")
    merged["sessions"] = []
    merged["sources"] = set()
    recorded_total = 0.0
    saw_recorded = False
    claude_sessions = 0
    claude_with_cost = 0
    for ev in evidences:
        merged["sources"].add(ev["source"])
        merged["commands"].extend(ev["commands"])
        merged["edited_files"].extend(ev["edited_files"])
        merged["sessions"].extend(ev["sessions"])
        merged["unparseable_lines"] += ev["unparseable_lines"]
        if ev["source"] == "claude":
            claude_sessions += 1
            if ev["recorded_cost"] is not None:
                recorded_total += ev["recorded_cost"]
                claude_with_cost += 1
                saw_recorded = True
        elif ev["source"] == "traj" and ev["recorded_cost"] is not None:
            recorded_total += ev["recorded_cost"]
            saw_recorded = True
    merged["has_codex"] = "codex" in merged["sources"]
    # A recorded $0.00 is a recorded cost, not an absence: presence is
    # tracked separately from the total, so a $0.00 record is not
    # dropped to None.
    merged["recorded_cost"] = recorded_total if saw_recorded else None
    merged["claude_sessions"] = claude_sessions
    merged["claude_with_cost"] = claude_with_cost
    merged["sources"] = sorted(merged["sources"])
    return merged


def _outcome_text(command):
    """One-line citation for a judged command."""
    outcome = command["outcome"]
    if outcome is True:
        result = "succeeded"
    elif outcome is False:
        result = "failed"
    else:
        result = "outcome unknown"
    return "`%s` (%s; %s)" % (command["command"], result,
                              command["outcome_note"])


def _evidence_sources(evidence):
    """Source kinds in the evidence: {"traj"} / {"claude"} / {"codex"}
    / {"unknown"} (JSONL / Langfuse) / a mix (scan mode)."""
    sources = evidence.get("sources")
    if isinstance(sources, (list, tuple, set)) and sources:
        return set(sources)
    source = evidence.get("source")
    return {source} if source else set()


def _format_limitation(sources, kind):
    """Format-limitation sentence for a NOT OBSERVED row, or "".

    The absence is in the format, not the run, when the only source
    is a mini-SWE-agent trajectory (D3: it edits via bash, never
    Edit/Write calls) or a JSONL/Langfuse file (no tool-use records
    at all)."""
    if sources == {"traj"} and kind in ("d3",):
        return (" (mini-SWE-agent edits files via bash, not Edit/Write "
                "calls, so this check cannot resolve on this format)")
    if sources == {"unknown"}:
        return (" (JSONL events and Langfuse exports carry no "
                "tool-use records, so this check cannot resolve on "
                "these formats)")
    return ""


def _earlier_outcomes_note(observed, kind_word):
    """Note when earlier runs of the same kind resolved but the last
    did not, so a passing run is never hidden behind a later unknown
    one. ``observed`` is the list of command dicts in order."""
    earlier = observed[:-1]
    passed = sum(1 for c in earlier if c.get("outcome") is True)
    failed = sum(1 for c in earlier if c.get("outcome") is False)
    if not passed and not failed:
        return ""
    parts = []
    if passed:
        parts.append("%d earlier %s run(s) passed"
                     % (passed, kind_word))
    if failed:
        parts.append("%d earlier %s run(s) failed"
                     % (failed, kind_word))
    return ("; %s but the latest run's outcome is unknown, so the "
            "check is NOT OBSERVED" % " and ".join(parts))


def _judge_command_check(check_id, name, kind, evidence):
    """D1/D2: judge the last observed command of one kind."""
    observed = []
    for cmd in evidence["commands"]:
        if cmd["command"] is None:
            continue
        classified, _targets = classify_command(cmd["command"])
        if classified == kind:
            observed.append(cmd)
    kind_word = "test" if kind == "test" else "build"
    if not observed:
        return {"id": check_id, "name": name, "verdict": "NOT OBSERVED",
                "observation": "no %s command observed in trace%s"
                               % (kind_word,
                                  _format_limitation(
                                      _evidence_sources(evidence), "d1"))}
    last = observed[-1]
    runs = "observed %d time(s); last run: %s" % (
        len(observed), _outcome_text(last))
    if last["outcome"] is True:
        return {"id": check_id, "name": name, "verdict": "VERIFIED",
                "observation": runs}
    if last["outcome"] is False:
        return {"id": check_id, "name": name, "verdict": "FAILED",
                "observation": runs}
    return {"id": check_id, "name": name, "verdict": "NOT OBSERVED",
            "observation": runs + "; no exit code or error flag for "
                           "this command in the trace, so the outcome "
                           "is not judged"
                           + _earlier_outcomes_note(observed, kind_word)}


def _judge_d3(evidence):
    """D3: files touched vs files tested, by name matching only.

    The named-test branch is gated on the last test command's
    outcome exactly like the bare-suite branch: a passing named run
    VERIFIES (name matching only), a failing named run FAILS, and a
    named run with an unknown outcome is NOT OBSERVED. Only the LAST
    test command's named files are matched."""
    edited = [f for f in evidence["edited_files"]
              if not _is_test_path(f)]
    if not edited:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "NOT OBSERVED",
                "observation": "no Edit/Write tool calls observed in "
                               "trace%s"
                               % _format_limitation(
                                   _evidence_sources(evidence), "d3")}
    tests = []
    for cmd in evidence["commands"]:
        if cmd["command"] is None:
            continue
        classified, targets = classify_command(cmd["command"])
        if classified == "test":
            tests.append((cmd, targets))
    if not tests:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "NOT OBSERVED",
                "observation": "edited files observed (%s) but no test "
                               "command observed in trace"
                               % ", ".join("`%s`" % f for f in edited)}
    last_cmd, targets = tests[-1]
    test_cmds = [cmd for cmd, _t in tests]
    earlier_note = _earlier_outcomes_note(test_cmds, "test")
    if not targets:
        # A bare test command runs the whole suite.
        if last_cmd["outcome"] is True:
            return {"id": "D3", "name": "files touched vs files tested",
                    "verdict": "VERIFIED",
                    "observation": "full test suite ran and passed "
                                   "(%s); edited files: %s"
                                   % (_outcome_text(last_cmd),
                                      ", ".join("`%s`" % f
                                                for f in edited))}
        if last_cmd["outcome"] is False:
            return {"id": "D3", "name": "files touched vs files tested",
                    "verdict": "FAILED",
                    "observation": "full test suite ran and failed "
                                   "(%s); edited files: %s"
                                   % (_outcome_text(last_cmd),
                                      ", ".join("`%s`" % f
                                                for f in edited))}
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "NOT OBSERVED",
                "observation": "full test suite ran but its outcome is "
                               "unknown (%s); edited files: %s%s"
                               % (_outcome_text(last_cmd),
                                  ", ".join("`%s`" % f for f in edited),
                                  earlier_note)}
    named_stems = {_test_stem(t) for t in targets}
    unmatched = [f for f in edited
                 if _test_stem(f) not in named_stems]
    unmatched_note = ""
    if unmatched:
        unmatched_note = ("; edited file(s) with no stem-matching "
                          "test file in %s: %s (name matching only; "
                          "actual coverage is not inferred)"
                          % (_outcome_text(last_cmd),
                             ", ".join("`%s`" % f for f in unmatched)))
    if last_cmd["outcome"] is None:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "NOT OBSERVED",
                "observation": "the named tests' outcome is unknown, "
                               "so no verdict (%s); edited: %s%s%s"
                               % (_outcome_text(last_cmd),
                                  ", ".join("`%s`" % f for f in edited),
                                  unmatched_note, earlier_note)}
    if last_cmd["outcome"] is False:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "FAILED",
                "observation": "the named tests failed, so the "
                               "touched files are not verified as "
                               "tested (%s); edited: %s%s"
                               % (_outcome_text(last_cmd),
                                  ", ".join("`%s`" % f for f in edited),
                                  unmatched_note)}
    if not unmatched:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "VERIFIED",
                "observation": "every edited source file has a "
                               "stem-matching test file named in %s "
                               "(name matching only; actual coverage "
                               "is not inferred; the named tests "
                               "passed); edited: %s"
                               % (_outcome_text(last_cmd),
                                  ", ".join("`%s`" % f for f in edited))}
    return {"id": "D3", "name": "files touched vs files tested",
            "verdict": "FAILED",
            "observation": "edited file(s) with no stem-matching test "
                           "file in %s: %s (name matching only; actual "
                           "coverage is not inferred)"
                           % (_outcome_text(last_cmd),
                              ", ".join("`%s`" % f for f in unmatched))}


def _judge_d4(evidence):
    """D4: OBSERVED duplicate-invocation overhead (never 'retries')."""
    counts = {}
    for cmd in evidence["commands"]:
        if cmd["command"] is None:
            continue
        key = " ".join(cmd["command"].split())
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return {"id": "D4", "name": "duplicate-invocation overhead",
                "verdict": "NOT OBSERVED",
                "observation": "no tool commands observed in trace%s"
                               % _format_limitation(
                                   _evidence_sources(evidence), "d4")}
    duplicates = sum(n - 1 for n in counts.values() if n > 1)
    worst = max(counts.items(), key=lambda kv: kv[1])
    detail = ("OBSERVED duplicate-invocation overhead: %d duplicate "
              "invocation(s) of identical commands "
              "(threshold: %d+ fails; pinned judgment call, not a "
              "measured bar - 50-trace public audit distribution "
              "0:2, 1:16, 2:8, 3:7, 4:7, 5:3, 6:2, 8:1, 10:1, 11:1, "
              "20:2; 10/50 fail at >=5); most-repeated command `%s` "
              "ran %d time(s)"
              % (duplicates, D4_DUPLICATE_FAIL_THRESHOLD,
                 worst[0], worst[1]))
    if duplicates >= D4_DUPLICATE_FAIL_THRESHOLD:
        return {"id": "D4", "name": "duplicate-invocation overhead",
                "verdict": "FAILED", "observation": detail}
    return {"id": "D4", "name": "duplicate-invocation overhead",
            "verdict": "VERIFIED", "observation": detail}


def _judge_d5(evidence, estimated_cost):
    """D5: trace-recorded vs estimated cost."""
    if evidence.get("has_codex"):
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "EXTERNAL-UNVERIFIABLE",
                "observation": "scan includes Codex session(s); Codex "
                               "subscription billing (per-seat plans, "
                               "rate limits) is not API list-price "
                               "metering, so a list-price comparison is "
                               "meaningless"}
    recorded = evidence.get("recorded_cost")
    if recorded is None:
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "NOT OBSERVED",
                "observation": "no session carries a recorded cost (no "
                               "result.total_cost_usd / instance_cost "
                               "in trace)"}
    total_sessions = evidence.get("claude_sessions", 0)
    with_cost = evidence.get("claude_with_cost", 0)
    if total_sessions and with_cost < total_sessions:
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "NOT OBSERVED",
                "observation": "only %d of %d Claude session(s) carry "
                               "a recorded cost; a partial comparison "
                               "would mislead" % (with_cost,
                                                  total_sessions)}
    if estimated_cost is None or estimated_cost == 0:
        if recorded == 0:
            return {"id": "D5", "name": "trace-recorded vs estimated cost",
                    "verdict": "VERIFIED",
                    "observation": "recorded $0.00 and metered estimate "
                                   "$0.00 agree"}
        # A $0.00 (or missing) metered estimate means no priced usage
        # was observed in the trace, so there is nothing to compare
        # against the recorded figure: absence of a measurement, not
        # a measurement of zero cost. NOT OBSERVED, never FAILED.
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "NOT OBSERVED",
                "observation": "metered estimate is $0.00 — no priced "
                               "usage was observed in the trace, so "
                               "there is nothing to compare against "
                               "the recorded $%.4f" % recorded}
    if recorded == 0:
        # A recorded $0.00 with a nonzero estimate: FAILED, with no
        # ratio (a ratio against zero is meaningless, never "infx").
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "FAILED",
                "observation": "recorded $0.0000 vs metered estimate "
                               "$%.4f; no ratio (recorded cost is "
                               "$0.00)" % estimated_cost}
    ratio = estimated_cost / recorded
    if abs(ratio - 1.0) <= D5_TOLERANCE + D5_TOLERANCE_EPSILON:
        return {"id": "D5", "name": "trace-recorded vs estimated cost",
                "verdict": "VERIFIED",
                "observation": ("recorded $%.4f vs metered estimate "
                                "$%.4f (4dp figures; ratio %.2fx; agree "
                                "within %.0f%%)"
                                % (recorded, estimated_cost, ratio,
                                   D5_TOLERANCE * 100))}
    return {"id": "D5", "name": "trace-recorded vs estimated cost",
            "verdict": "FAILED",
            "observation": ("recorded $%.4f vs metered estimate $%.4f "
                            "(4dp figures; ratio %.2fx; differ by "
                            "%.0f%%, tolerance %.0f%%)"
                            % (recorded, estimated_cost, ratio,
                               abs(ratio - 1.0) * 100,
                               D5_TOLERANCE * 100))}


def judge_default_checks(evidence, estimated_cost):
    """Judge the five default checks over merged evidence.

    ``evidence`` is a merged dict from ``merge_evidence`` (or a
    single-file dict from an ``extract_*`` function, which carries
    the same keys after ``merge_evidence`` normalizes it);
    ``estimated_cost`` is the metered total cost for the same runs.
    Returns a list of five ``{"id", "name", "verdict",
    "observation"}`` dicts, D1-D5 in order.
    """
    if "claude_sessions" not in evidence:
        evidence = merge_evidence([evidence])
    checks = [
        _judge_command_check("D1", "tests executed", "test", evidence),
        _judge_command_check("D2", "build passed", "build", evidence),
        _judge_d3(evidence),
        _judge_d4(evidence),
        _judge_d5(evidence, estimated_cost),
    ]
    return checks


def unknown_rate(checks):
    """Fraction of checks whose verdict is unknown.

    Unknown = NOT OBSERVED or EXTERNAL-UNVERIFIABLE. The audit bar
    (Gemini assessment) is unknown < 15% for default checks to
    resolve on >= 85% of rows; the receipt reports the actual
    number either way.
    """
    if not checks:
        return 0.0
    unknown = sum(1 for c in checks
                  if c["verdict"] in ("NOT OBSERVED",
                                      "EXTERNAL-UNVERIFIABLE"))
    return unknown / len(checks)
