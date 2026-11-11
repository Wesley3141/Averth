"""Discovery for the zero-config local scan (``averth try`` with no trace).

Finds the developer's own Claude Code session transcripts and Codex
CLI rollout files under their home directory, newest first:

- Claude Code: ``~/.claude/projects/**/**/*.jsonl``
- Codex: ``~/.codex/sessions/**/*.jsonl`` (rollout files, per the codex
  importer docstring: ``~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl``)

Only the last 10 by modification time across both sources are
returned. Codex subagent rollout files are EXCLUDED by default
(counted as skipped, with the reason, per the codex importer
docstring: a subagent file can carry a replayed parent-history prefix
and would double count the same work). Claude sidechain records are
already excluded by the claude importer, so no file-level exclusion
is needed on the Claude side.

Read-only: session files are never modified. No network, no upload.
``home`` is a parameter (tests pass a fake home) and defaults to the
real home directory; the scan respects ``HOME`` through
``os.path.expanduser``.
"""

import json
import os

MAX_SESSIONS = 10

CLAUDE_REL = os.path.join(".claude", "projects")
CODEX_REL = os.path.join(".codex", "sessions")


def checked_directories(home=None):
    """The two directories a scan looks in, as absolute paths."""
    base = os.path.expanduser("~") if home is None else str(home)
    return [os.path.join(base, CLAUDE_REL),
            os.path.join(base, CODEX_REL)]


def _rglob_jsonl(directory):
    """All ``*.jsonl`` files under ``directory``, recursively.

    Returns [] when the directory does not exist: an absent session
    directory is a normal state (no sessions yet), not an error.
    """
    found = []
    if not os.path.isdir(directory):
        return found
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if name.endswith(".jsonl"):
                found.append(os.path.join(root, name))
    return found


def _is_codex_subagent(path):
    """True when a Codex rollout file marks itself a subagent thread.

    Reads lines until the first ``session_meta`` record (or the first
    50 lines, whichever comes first): a ``source`` that is an object
    rather than a plain string, or ``agent_nickname`` / ``agent_role``
    fields, mark a subagent thread, exactly as the codex importer
    defines it. A file that cannot be read or parsed here is NOT
    treated as a subagent: the importer will raise on it later and
    the scan counts it as a parse failure, not a silent skip.
    """
    try:
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if line_no > 50:
                    break
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("type") != "session_meta":
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    payload = record
                source = payload.get("source")
                if (isinstance(source, dict)
                        or payload.get("agent_nickname") is not None
                        or payload.get("agent_role") is not None):
                    return True
                return False
    except (OSError, UnicodeDecodeError):
        return False
    return False


def discover_sessions(home=None):
    """Discover local agent sessions for a zero-config scan.

    Returns ``(selected, skipped, checked)`` where ``selected`` is a
    list of ``{"path", "source", "mtime"}`` dicts (at most
    ``MAX_SESSIONS``, newest first by mtime across both sources),
    ``skipped`` is a list of ``{"path", "source", "reason"}`` dicts
    for files excluded before parsing (Codex subagent rollouts), and
    ``checked`` is the list of directories looked in. A directory
    that does not exist contributes nothing; when both are absent
    (or empty) ``selected`` is empty and the caller reports that no
    sessions were found, naming ``checked``.
    """
    checked = checked_directories(home)
    claude_dir, codex_dir = checked
    candidates = []
    for path in _rglob_jsonl(claude_dir):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        candidates.append({"path": path, "source": "claude",
                           "mtime": mtime})
    for path in _rglob_jsonl(codex_dir):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        candidates.append({"path": path, "source": "codex",
                           "mtime": mtime})
    candidates.sort(key=lambda c: c["mtime"], reverse=True)
    selected = []
    skipped = []
    for candidate in candidates:
        if candidate["source"] == "codex" \
                and _is_codex_subagent(candidate["path"]):
            skipped.append({
                "path": candidate["path"], "source": "codex",
                "reason": "subagent rollout (session_meta source is an "
                          "object or agent_nickname/agent_role present); "
                          "excluded by default so a replayed "
                          "parent-history prefix cannot double count"})
            continue
        selected.append(candidate)
        if len(selected) >= MAX_SESSIONS:
            break
    return selected, skipped, checked


def display_name(candidate):
    """Short display name for a session in reports: ``source/basename``."""
    return "%s/%s" % (candidate["source"],
                      os.path.basename(candidate["path"]))
