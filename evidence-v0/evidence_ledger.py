"""evidence_ledger: repo snapshot, run history, and the JSON ledger.

Append-only history: a re-judgment adds a new entry; it never silently
overwrites an old verdict. Superseded runs (started before the final
edit marker) are retained in the ledger and are never cited as
verification of the current revision.

Trust tiers, per the evidence schema:
- 1: imported transcript / agent-side tool output (observed in a log).
- 2: this tool's own local recorder: it captured the command, exit
  status, and workspace snapshot itself. Tier 2 is stronger
  observation, NOT tamper-proof provenance: the host is
  user-controlled, a local record can be regenerated with its hash.
  Tier 2 is never presented as cryptographic proof.
- 3: independent CI / isolated runner with signed attestation. This
  tool does not wire one in, so no Tier 3 row is ever produced here.
- 4: human / hardware confirmation, only when a named tester and a
  named procedure are supplied in the check file.
"""
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
EXCLUDE_FILES = {"evidence_ledger.json", "evidence_report.md"}


def sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def parse_time(value):
    """Parse ISO, common date forms, and epoch times, or None.

    Wave 3 extension, backward compatible: naive ISO is still
    treated as UTC, unparseable input still returns None and
    is never given an invented time. Epoch seconds, millis,
    micros, and nanos are accepted, as are space separated
    date times and slash dates.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        v = float(value)
        if abs(v) >= 1e18:
            v = v / 1e9
        elif abs(v) >= 1e15:
            v = v / 1e6
        elif abs(v) >= 1e12:
            v = v / 1e3
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    text = str(value).strip()
    if not text:
        return None
    import re as _re
    if _re.match(r"^-?\d+(\.\d+)?$", text):
        return parse_time(float(text))
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


def snapshot_repo(repo_path):
    """Map relative path -> SHA-256 digest for every file under repo.

    Excludes version-control, caches, and virtualenvs. Returns
    (snapshot, latest_mtime) where latest_mtime is the newest file
    modification time, used as the default final-edit marker when the
    operator does not supply one.
    """
    repo = Path(repo_path)
    snapshot = {}
    latest = None
    for p in sorted(repo.rglob("*")):
        if not p.is_file():
            continue
        if p.name in EXCLUDE_FILES:
            continue
        if any(part in EXCLUDE_DIRS for part in p.relative_to(repo).parts):
            continue
        rel = str(p.relative_to(repo))
        snapshot[rel] = sha256_file(p)
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        if latest is None or mtime > latest:
            latest = mtime
    return snapshot, latest


def git_state(repo_path):
    """Read-only git identity: commit and dirty flag, or None/None."""
    repo = Path(repo_path)
    if not (repo / ".git").exists():
        return None, None, "Not a git repository; identity is path plus file digests."
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or None
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        return commit, bool(status), None
    except Exception:
        return None, None, "Git state could not be read; identity is path plus file digests."


def is_superseded(run, marker):
    start = parse_time(run.get("start_timestamp"))
    marker_dt = parse_time(marker) if not isinstance(marker, datetime) else marker
    if start is None or marker_dt is None:
        return False
    return start < marker_dt


def build_ledger(*, report_id, repo_path, checks_spec, judgments, runs,
                 snapshot, commit, workspace_dirty, commit_note,
                 final_edit_marker, trace_summary):
    total = len(judgments)
    counts = {}
    for j in judgments:
        counts[j["status"]] = counts.get(j["status"], 0) + 1
    unknown = counts.get("NOT OBSERVED", 0) + counts.get("EXTERNAL-UNVERIFIABLE", 0)
    coverage = {
        "criteria_total": total,
        "counts": counts,
        "unknown": unknown,
        "unknown_rate": (unknown / total) if total else None,
        "decided": counts.get("VERIFIED", 0) + counts.get("FAILED", 0),
        "superseded_runs_retained": sum(1 for r in runs if r.get("superseded")),
        "runs_total": len(runs),
    }
    return {
        "schema_version": "averth-evidence-0.1-v0",
        "report_id": report_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_intent": checks_spec.get("task_intent", ""),
        "task_intent_source": checks_spec.get("task_intent_source", ""),
        "target_repo": str(repo_path),
        "target_commit": commit,
        "commit_note": commit_note,
        "workspace_dirty": workspace_dirty,
        "final_edit_marker": final_edit_marker.isoformat() if final_edit_marker else None,
        "files": snapshot,
        "runs": runs,
        "judgments": judgments,
        "coverage": coverage,
        "trace_summary": trace_summary,
    }
