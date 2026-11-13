"""Discovery for the zero-config local scan (``averth try`` with no trace).

Finds the developer's own Claude Code session transcripts and Codex
CLI rollout files under their home directory, newest first:

- Claude Code: ``~/.claude/projects/`` (``*.jsonl`` at any depth,
  including directly under the directory)
- Codex: ``~/.codex/sessions/`` (``*.jsonl`` at any depth; rollout
  files, per the codex importer docstring:
  ``~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl``)

Only the last 10 by modification time across both sources are
returned. Codex subagent rollout files are EXCLUDED by default
(counted as skipped, with the reason, per the codex importer
docstring: a subagent file can carry a replayed parent-history prefix
and would double count the same work). Excluded subagent rollouts do
not consume one of the 10 slots: the scan returns the 10 newest
sessions that are not subagent rollouts, and every candidate is
examined for the subagent check before capping, so the skipped count
is honest past the cap. Claude sidechain records are already excluded
by the claude importer, so no file-level exclusion is needed on the
Claude side.

Read-only: session files are never modified. No network, no upload.
``home`` is a parameter (tests pass a fake home) and defaults to the
real home directory; the scan respects ``HOME`` through
``os.path.expanduser``. Only regular files are considered: a FIFO,
socket, or other special file named ``*.jsonl`` is skipped with the
reason (opening one for read would block forever), as is a
permission-denied subdirectory.
"""

import json
import os
import stat

MAX_SESSIONS = 10

CLAUDE_REL = os.path.join(".claude", "projects")
CODEX_REL = os.path.join(".codex", "sessions")


def checked_directories(home=None):
    """The two directories a scan looks in, as absolute paths."""
    base = os.path.expanduser("~") if home is None else str(home)
    return [os.path.join(base, CLAUDE_REL),
            os.path.join(base, CODEX_REL)]


def _rglob_jsonl(directory):
    """All regular ``*.jsonl`` files under ``directory``, recursively.

    Returns ``(found, problems)`` where ``found`` is the list of
    regular-file paths and ``problems`` is a list of ``{"path",
    "reason"}`` dicts for entries skipped without opening them:
    non-regular files (a FIFO named ``*.jsonl`` would block forever
    on open for read) and permission-denied subdirectories. Returns
    ([], []) when the directory does not exist: an absent session
    directory is a normal state (no sessions yet), not an error.
    """
    found = []
    problems = []
    if not os.path.isdir(directory):
        return found, problems

    def _onerror(err):
        path = getattr(err, "filename", None) or str(err)
        problems.append({"path": path,
                         "reason": "unreadable directory (%s)" % err})

    for root, _dirs, files in os.walk(directory, onerror=_onerror):
        for name in files:
            if name.endswith(".jsonl"):
                path = os.path.join(root, name)
                try:
                    mode = os.lstat(path).st_mode
                except OSError:
                    continue
                if stat.S_ISREG(mode):
                    found.append(path)
                else:
                    problems.append(
                        {"path": path, "reason": "not a regular file"})
    return found, problems


def _is_codex_subagent(path):
    """True when a Codex rollout file marks itself a subagent thread.

    Reads lines until the first ``session_meta`` record, with no line
    cap (the codex importer scans the whole file for
    ``session_meta``; a subagent marker past line 50 must still
    exclude the file): a ``source`` that is an object rather than a
    plain string, or ``agent_nickname`` / ``agent_role`` fields, mark
    a subagent thread, exactly as the codex importer defines it. A
    file that cannot be read or parsed here is NOT treated as a
    subagent: the importer will raise on it later and the scan counts
    it as a parse failure, not a silent skip. A line that is not
    valid UTF-8 is skipped, never fatal.
    """
    if not _is_regular_file(path):
        return False
    try:
        with open(path, "rb") as f:
            for raw in f:
                try:
                    line = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
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
    except OSError:
        return False
    return False


def _is_regular_file(path):
    """True when ``path`` is a regular file (see ``_rglob_jsonl``)."""
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


def discover_sessions(home=None):
    """Discover local agent sessions for a zero-config scan.

    Returns ``(selected, skipped, checked, total_found)`` where
    ``selected`` is a list of ``{"path", "source", "mtime"}`` dicts
    (at most ``MAX_SESSIONS``, newest first by mtime across both
    sources), ``skipped`` is a list of ``{"path", "source",
    "reason"}`` dicts for files excluded before parsing (Codex
    subagent rollouts, non-regular files, unreadable directories),
    ``checked`` is the list of directories looked in, and
    ``total_found`` is the number of regular ``*.jsonl`` candidate
    files found across both sources (before the cap). Every
    candidate is examined for the subagent check before capping, so
    ``skipped`` is honest past the cap. A directory that does not
    exist contributes nothing; when both are absent (or empty)
    ``selected`` is empty and the caller reports that no sessions
    were found, naming ``checked``. Ties in mtime keep discovery
    order (Claude candidates first); the sort is stable.
    """
    checked = checked_directories(home)
    claude_dir, codex_dir = checked
    candidates = []
    skipped = []
    for directory, source in ((claude_dir, "claude"),
                              (codex_dir, "codex")):
        found, problems = _rglob_jsonl(directory)
        for problem in problems:
            skipped.append({"path": problem["path"], "source": source,
                            "reason": problem["reason"]})
        for path in found:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            candidates.append({"path": path, "source": source,
                               "mtime": mtime})
    candidates.sort(key=lambda c: c["mtime"], reverse=True)
    total_found = len(candidates)
    selected = []
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
        if len(selected) < MAX_SESSIONS:
            selected.append(candidate)
    return selected, skipped, checked, total_found


# Path segments locating a session under its source root, e.g.
# (".claude", "projects") for Claude Code, (".codex", "sessions")
# for Codex. The display name keeps the part below the root, so two
# sessions that share a basename (one per project, or one per day)
# never render as the same string.
_SOURCE_ROOTS = {"claude": (".claude", "projects"),
                 "codex": (".codex", "sessions")}


def display_name(candidate):
    """Short display name for a session in reports.

    ``source/<path below the source root>``: the project slug
    (Claude) or date path (Codex) plus the basename. A bare basename
    repeats the same string for distinct files — every project
    directory can hold a file named ``session.jsonl`` — so the
    relative path is what makes the receipt's source list truthful.
    Falls back to the full path (below the filesystem root) when
    the path does not sit under the expected root (defensive:
    discovery only returns files under it): a bare basename there
    would reintroduce the same collision for outside-root files.
    """
    path = candidate["path"]
    root = _SOURCE_ROOTS.get(candidate["source"])
    if root:
        parts = path.split(os.sep)
        # The discovery root is the first matching pair of
        # segments: discovery only returns files under it, so the
        # first match is the root; a later pair would sit inside
        # a project directory.
        idx = -1
        for i in range(len(parts) - 1):
            if parts[i] == root[0] and parts[i + 1] == root[1]:
                idx = i
                break
        if idx >= 0 and len(parts) > idx + 2:
            rel = os.sep.join(parts[idx + 2:])
            return "%s/%s" % (candidate["source"], rel)
    return "%s/%s" % (candidate["source"],
                      candidate["path"].lstrip(os.sep))
