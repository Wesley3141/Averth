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
``is_error`` boolean, which IS the transcript's observed outcome for
that command (Claude Code sets it from the command's exit status),
so ``is_error: false`` counts as a successful run and ``is_error:
true`` as a failed run, and the observation says so ("is_error=false;
no numeric exit code in transcript"). A command with NO matching
tool_result, and no is_error / exit code anywhere, has an unknown
outcome: the check says so and judges NOT OBSERVED, never guesses.
Codex ``function_call_output`` records carry neither field in the
documented format, so Codex test/build commands are NOT OBSERVED
unless a record happens to carry an ``exit_code`` field.

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
  in observed test commands, matched by file stem). A bare test
  command with no file arguments runs the whole suite, so with a
  successful outcome it VERIFIES the touched files. When a test
  command names specific files and an edited source file has no
  stem-matching test among them -> FAILED, citing the unmatched
  files. When coverage cannot be established from the trace (no
  edited files, no test command, or no outcome signal on a
  full-suite run) -> NOT OBSERVED with the reason stated. Name
  matching is the criterion, stated in the observation; actual
  coverage is never inferred.
- D4 retry overhead: counts repeated identical tool invocations
  (the same command run 2+ times) as OBSERVED duplicate-invocation
  overhead. Labelled exactly that, NEVER as meter retries (the
  Claude/Codex importers emit no retry events, by design).
  Threshold (pinned): 3 or more duplicate invocations -> FAILED;
  fewer -> VERIFIED. The count is always shown. No commands at all
  -> NOT OBSERVED.
- D5 billed vs estimated: when the trace carries its own recorded
  cost (Claude ``result.total_cost_usd``, mini-SWE-agent
  ``info.model_stats.instance_cost``) compare with the metered
  estimate: agree within 5% -> VERIFIED; differ -> FAILED (both
  figures and the ratio stated); no recorded figure -> NOT OBSERVED;
  subscription billing where list-price comparison is meaningless
  (Codex) -> EXTERNAL-UNVERIFIABLE with the reason. In a scan, D5
  resolves only when every scanned Claude session carries a recorded
  cost and no Codex session is present; a partial comparison would
  mislead, so a partial record is NOT OBSERVED.

Unknown rate: the fraction of the five checks whose verdict is
NOT OBSERVED or EXTERNAL-UNVERIFIABLE.
"""

import json
import math
import os
import re

LABEL = "default checks (trace-observed)"

VERDICTS = ("VERIFIED", "FAILED", "NOT OBSERVED",
            "EXTERNAL-UNVERIFIABLE", "NOT APPLICABLE")

# D5: recorded vs estimated agree when within 5% of each other.
D5_TOLERANCE = 0.05

# D4: this many duplicate identical command invocations (counting
# each repeat past the first) fails the check. One or two re-runs are
# normal agent iteration (fix, then re-run); three or more identical
# re-invocations indicate a loop / overhead worth flagging.
D4_DUPLICATE_FAIL_THRESHOLD = 3

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


def classify_command(command):
    """Classify a shell command string.

    Returns ``("test", [test-file tokens])``,
    ``("build", [])``, or ``(None, [])``. Test patterns are checked
    first, so ``make test`` classifies as a test, not a build.
    """
    if not isinstance(command, str) or not command.strip():
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


def extract_claude(path):
    """Extract trace-observed evidence from one Claude Code session.

    Reads ``tool_use`` blocks (Bash commands, Edit/Write file paths),
    matching ``tool_result`` blocks (``is_error`` outcome), and the
    ``result`` record's ``total_cost_usd``. Sidechain records are
    skipped, matching the claude importer. Lines that fail to parse
    are counted, never crash the extraction: the importer has
    already validated the file when the scan runs, so a count here
    is a belt-and-braces signal, not a second validator.
    """
    evidence = _new_evidence("claude")
    session = os.path.basename(path)
    evidence["sessions"].append(session)
    # tool_use_id -> index into evidence["commands"].
    pending = {}
    last_cost = None
    try:
        f = open(path, encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return evidence
    with f:
        for line in f:
            if not line.strip():
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
                            pending[tool_id] = len(evidence["commands"])
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
    pending = {}
    try:
        f = open(path, encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return evidence
    with f:
        for line in f:
            if not line.strip():
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


def extract_traj(path):
    """Extract trace-observed evidence from a mini-SWE-agent trajectory.

    Bash fenced commands in assistant message text are the commands;
    the trajectory carries no per-command exit status, so their
    outcomes are unknown (D1/D2 judge NOT OBSERVED on a traj, never
    guess). The recorded cost is ``info.model_stats.instance_cost``.
    """
    from averth.importers import miniswe

    evidence = _new_evidence("traj")
    evidence["sessions"].append(os.path.basename(path))
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
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        text = miniswe._message_text(message)
        for match in _BASH_FENCE.finditer(text):
            command = match.group(1).strip()
            if command:
                evidence["commands"].append({
                    "command": command,
                    "outcome": None,
                    "outcome_note": "trajectory text carries no "
                                    "per-command exit status",
                    "session": evidence["sessions"][0],
                })
    return evidence


def extract_from_file(path):
    """Extract evidence from any explicit-trace file, sniffing shape.

    A JSON object with a ``messages`` key is a mini-SWE-agent
    trajectory; otherwise the first lines are sniffed for Claude
    ``tool_use`` blocks (``type: assistant``) or Codex
    ``response_item`` function_call records. A file matching neither
    shape yields empty evidence (every check NOT OBSERVED with the
    reason stated) instead of an error: JSONL events and Langfuse
    exports carry no tool-use records.
    """
    try:
        with open(path, encoding="utf-8") as f:
            whole = json.load(f)
    except (OSError, UnicodeDecodeError, ValueError):
        whole = None
    if isinstance(whole, dict) and "messages" in whole:
        return extract_traj(path)
    head = []
    try:
        with open(path, encoding="utf-8") as f:
            for _ in range(50):
                line = f.readline()
                if not line:
                    break
                head.append(line)
    except (OSError, UnicodeDecodeError):
        head = []
    is_claude = False
    is_codex = False
    for line in head:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("type") == "assistant":
            message = record.get("message")
            if isinstance(message, dict) \
                    and isinstance(message.get("content"), list):
                is_claude = True
        if record.get("type") == "response_item":
            is_codex = True
    if is_claude:
        return extract_claude(path)
    if is_codex:
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
        elif ev["source"] == "traj" and ev["recorded_cost"] is not None:
            recorded_total += ev["recorded_cost"]
    merged["has_codex"] = "codex" in merged["sources"]
    merged["recorded_cost"] = recorded_total if recorded_total else None
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


def _judge_command_check(check_id, name, kind, evidence):
    """D1/D2: judge the last observed command of one kind."""
    observed = []
    for cmd in evidence["commands"]:
        if cmd["command"] is None:
            continue
        classified, _targets = classify_command(cmd["command"])
        if classified == kind:
            observed.append(cmd)
    if not observed:
        return {"id": check_id, "name": name, "verdict": "NOT OBSERVED",
                "observation": "no %s command observed in trace"
                               % ("test" if kind == "test" else "build")}
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
            "observation": runs + "; no exit code or error flag in "
                           "trace, so the outcome is not judged"}


def _judge_d3(evidence):
    """D3: files touched vs files tested, by name matching only."""
    edited = [f for f in evidence["edited_files"]
              if not _is_test_path(f)]
    if not edited:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "NOT OBSERVED",
                "observation": "no Edit/Write tool calls observed in "
                               "trace"}
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
                               "unknown (%s); edited files: %s"
                               % (_outcome_text(last_cmd),
                                  ", ".join("`%s`" % f for f in edited))}
    named_stems = {_test_stem(t) for t in targets}
    unmatched = [f for f in edited
                 if _test_stem(f) not in named_stems]
    if not unmatched:
        return {"id": "D3", "name": "files touched vs files tested",
                "verdict": "VERIFIED",
                "observation": "every edited source file has a "
                               "stem-matching test file named in %s; "
                               "edited: %s"
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
        return {"id": "D4", "name": "retry overhead (duplicate "
                                    "invocations)",
                "verdict": "NOT OBSERVED",
                "observation": "no tool commands observed in trace"}
    duplicates = sum(n - 1 for n in counts.values() if n > 1)
    worst = max(counts.items(), key=lambda kv: kv[1])
    detail = ("OBSERVED duplicate-invocation overhead: %d duplicate "
              "invocation(s) of identical commands "
              "(threshold: %d+ fails); most-repeated command `%s` ran "
              "%d time(s)"
              % (duplicates, D4_DUPLICATE_FAIL_THRESHOLD,
                 worst[0], worst[1]))
    if duplicates >= D4_DUPLICATE_FAIL_THRESHOLD:
        return {"id": "D4", "name": "retry overhead (duplicate "
                                    "invocations)",
                "verdict": "FAILED", "observation": detail}
    return {"id": "D4", "name": "retry overhead (duplicate "
                                "invocations)",
            "verdict": "VERIFIED", "observation": detail}


def _judge_d5(evidence, estimated_cost):
    """D5: billed (recorded) vs estimated cost."""
    if evidence.get("has_codex"):
        return {"id": "D5", "name": "billed vs estimated cost",
                "verdict": "EXTERNAL-UNVERIFIABLE",
                "observation": "scan includes Codex session(s); Codex "
                               "subscription billing (per-seat plans, "
                               "rate limits) is not API list-price "
                               "metering, so a list-price comparison is "
                               "meaningless"}
    recorded = evidence.get("recorded_cost")
    if recorded is None:
        return {"id": "D5", "name": "billed vs estimated cost",
                "verdict": "NOT OBSERVED",
                "observation": "no session carries a recorded cost (no "
                               "result.total_cost_usd / instance_cost "
                               "in trace)"}
    total_sessions = evidence.get("claude_sessions", 0)
    with_cost = evidence.get("claude_with_cost", 0)
    if total_sessions and with_cost < total_sessions:
        return {"id": "D5", "name": "billed vs estimated cost",
                "verdict": "NOT OBSERVED",
                "observation": "only %d of %d Claude session(s) carry "
                               "a recorded cost; a partial comparison "
                               "would mislead" % (with_cost,
                                                  total_sessions)}
    if estimated_cost is None or estimated_cost == 0:
        if recorded == 0:
            return {"id": "D5", "name": "billed vs estimated cost",
                    "verdict": "VERIFIED",
                    "observation": "recorded $0.00 and metered estimate "
                                   "$0.00 agree"}
        return {"id": "D5", "name": "billed vs estimated cost",
                "verdict": "FAILED",
                "observation": "recorded $%.4f but metered estimate "
                               "$0.00" % recorded}
    ratio = estimated_cost / recorded if recorded else float("inf")
    detail = ("recorded $%.4f vs metered estimate $%.4f (ratio %.2fx; "
              "agree within %.0f%%)"
              % (recorded, estimated_cost, ratio,
                 D5_TOLERANCE * 100))
    if abs(ratio - 1.0) <= D5_TOLERANCE:
        return {"id": "D5", "name": "billed vs estimated cost",
                "verdict": "VERIFIED", "observation": detail}
    return {"id": "D5", "name": "billed vs estimated cost",
            "verdict": "FAILED", "observation": detail}


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
