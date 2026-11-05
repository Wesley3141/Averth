#!/usr/bin/env python3
"""Wave 2: artifact digest capture for non-Python repos.

A V0 artifact_presence check needs a file in a local repo
snapshot, with a SHA-256 digest V0 computed itself from the
file it scanned. For a non-Python repo, or for an artifact
built elsewhere, that means: copy the artifact into a local
snapshot directory, compute its digest from the copied file,
and record that digest, the source path, and the copied
path. V0 then scans the snapshot directory as its repo, and
the digest it computes matches the recorded digest only if
the file has not changed since copying.

Rules, enforced by this module, not just documented:
  - A remote URL is never accepted as a digest, and never
    accepted as a source file. If the source looks like a
    URL (http://, https://, or any scheme with ://), this
    module raises ValueError. A URL is a claim about where
    a file lives, not a file, and not a digest. The honest
    alternative for a remote artifact is a named human
    confirmation, recorded separately, scoped to that tester
    and procedure, with a pass or fail result. That record
    is Tier 4 in V0 terms, scoped exactly to the named
    procedure, and it is never presented as a digest.
  - A directory, a missing file, or a non-file source is
    rejected, not recorded as an empty artifact.
  - The snapshot record is a JSON file, snapshot.json, in
    the snapshot directory, listing each artifact, its
    copied relative path, its SHA-256 digest, its original
    source path as supplied, and the copy time in UTC.
    The digest in that record is a convenience for the
    operator; V0's own scan is what decides a check, and
    if the copied file changes after copying, V0's digest
    will differ and the check will not stand.

Usage:
  python3 artifact_snapshot.py --source dist/app.bin \
      --snapshot-dir ./snapshot --name app.bin
  python3 artifact_snapshot.py --source dist/app.bin \
      --snapshot-dir ./snapshot --name app.bin \
      --human-tester "Ada Lovelace" --human-procedure "ran app.bin on device X" --human-result pass

The human confirmation flags, when given, are written to
the snapshot record as a separate human_confirmation entry.
They do not change the digest, and they do not turn a
remote artifact into a local one.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _is_url(value):
    text = str(value)
    return "://" in text


def sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_artifact(source, snapshot_dir, name=None, human_confirmation=None):
    """Copy one artifact into a snapshot directory, with digest.

    Returns the snapshot record entry. Raises ValueError for
    a URL source, a missing source, or a non-file source.
    """
    if _is_url(source):
        raise ValueError("remote URL is not an artifact file and never a digest; copy the file locally or supply a named human confirmation instead")
    src = Path(source)
    if not src.is_file():
        raise ValueError(f"artifact source must be an existing file, not {source!r}")
    dest_dir = Path(snapshot_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_name = name or src.name
    if "/" in dest_name or "\\" in dest_name or dest_name in (".", ".."):
        raise ValueError("artifact name must be a plain filename, not a path")
    dest = dest_dir / dest_name
    shutil.copyfile(src, dest)
    digest = sha256_file(dest)
    entry = {
        "name": dest_name,
        "copied_path": dest_name,
        "source_path": str(src),
        "sha256_digest": digest,
        "copied_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if human_confirmation is not None:
        tester = human_confirmation.get("tester", "")
        procedure = human_confirmation.get("procedure", "")
        result = human_confirmation.get("result", "")
        if not tester or not procedure or result not in ("pass", "fail"):
            raise ValueError("human confirmation needs a tester, a procedure, and a result of pass or fail")
        entry["human_confirmation"] = {
            "tester": tester,
            "procedure": procedure,
            "result": result,
            "note": "Scoped to exactly this tester, procedure, and revision. Not a digest, not transferable.",
        }
    record_path = dest_dir / "snapshot.json"
    if record_path.exists():
        try:
            record = json.loads(record_path.read_text())
        except json.JSONDecodeError:
            record = {"artifacts": []}
    else:
        record = {"artifacts": []}
    record["artifacts"] = [a for a in record.get("artifacts", []) if a.get("name") != dest_name]
    record["artifacts"].append(entry)
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(description="Copy an artifact into a local snapshot with a digest")
    ap.add_argument("--source", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--name", default=None)
    ap.add_argument("--human-tester", default=None)
    ap.add_argument("--human-procedure", default=None)
    ap.add_argument("--human-result", default=None, choices=["pass", "fail"])
    args = ap.parse_args(argv)
    human = None
    if args.human_tester or args.human_procedure or args.human_result:
        human = {"tester": args.human_tester, "procedure": args.human_procedure, "result": args.human_result}
    try:
        entry = snapshot_artifact(args.source, args.snapshot_dir, name=args.name, human_confirmation=human)
    except ValueError as exc:
        print(f"error: {exc}", flush=True)
        return 2
    print(f"snapshot: {entry['copied_path']} {entry['sha256_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
