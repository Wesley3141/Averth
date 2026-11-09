"""reporter: render the JSON ledger and the Markdown report from the
SAME judgments. The Markdown report is never hand-edited into a
different verdict; it is generated from the ledger rows, in order.
The LIMITATIONS section is mandatory and non-collapsible.
"""
import hashlib
import json
import os
import secrets
import stat

LIMITATIONS = [
    "This is a local retrospective evidence report, not a live customer workflow, not a merge certifier, and not a boot or correctness verdict.",
    "NOT OBSERVED is a statement about the records, not about reality. It is never upgraded to NOT EXECUTED or to FAILED by inference.",
    "A successful shell command is not proof of complete correctness. A VERIFIED row proves only what its cited observation shows, bounded by what the tests actually cover.",
    "A local hash detects alteration or mismatch between copies of a record; it is not tamper-resistant provenance. Tier 2 is stronger observation on a user-controlled host, never cryptographic proof.",
    "No Tier 3 evidence exists in this report: no independent CI runner with signed attestation is wired in. No Tier 4 evidence exists unless a named human confirmation record was supplied in the check file.",
    "This report does not prove test quality, correctness beyond the named assertions, acceptance by any human or operator, value, time saved, willingness to pay, or boot on untested hardware.",
    "The fixture case, if used, has no trace events and no acceptance join, so no cost-per-accepted-outcome figure is claimed for it. Any trace summary in this report is a summary only and is never cited as a verdict.",
    "No Qwen support, no cost savings, no subscription, and no production readiness are claimed anywhere in this report.",
    "Redaction can miss secrets. If a future version of this report ever ingests a real transcript, treat any shared report as potentially secret-bearing and review it before sharing. The default upload set is empty; nothing in this tool uploads anything.",
]


def build_markdown(ledger):
    cov = ledger["coverage"]
    lines = []
    lines.append(f"# Execution-evidence report (V0 verifier): {ledger['report_id']}")
    lines.append("")
    lines.append(f"Generated: {ledger['generated_at']}")
    lines.append(f"Target repo: {ledger['target_repo']}")
    lines.append(f"Target commit: {ledger['target_commit'] or 'none (not a git repo; identity is path plus file digests)'}")
    lines.append(f"Workspace dirty: {ledger['workspace_dirty']}")
    lines.append(f"Final edit marker: {ledger['final_edit_marker']}")
    lines.append(f"Task intent: {ledger['task_intent']} (source: {ledger['task_intent_source']})")
    lines.append(f"Checks digest: {ledger.get('checks_digest') or 'none (observe-only mode; no checks file supplied, no re-hash performed)'}")
    lines.append("")
    lines.append("## LIMITATIONS FIRST (read before any verdict below)")
    lines.append("")
    for i, text in enumerate(LIMITATIONS, 1):
        lines.append(f"{i}. {text}")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"Total criteria: {cov['criteria_total']}")
    for status, count in sorted(cov["counts"].items()):
        lines.append(f"- {status}: {count}")
    lines.append(f"Unknown (NOT OBSERVED + EXTERNAL-UNVERIFIABLE): {cov['unknown']}")
    rate = cov["unknown_rate"]
    lines.append(f"Unknown rate: {rate * 100:.1f}%" if rate is not None else "Unknown rate: n/a")
    lines.append(f"Decided (VERIFIED + FAILED): {cov['decided']}")
    lines.append(f"Runs recorded: {cov['runs_total']}, of which superseded and retained, never cited: {cov['superseded_runs_retained']}")
    if ledger.get("trace_summary"):
        ts = ledger["trace_summary"]
        lines.append("")
        lines.append("## Trace summary (summary only, never a verdict)")
        lines.append("")
        lines.append(f"File: {ts['trace_file']}, lines: {ts['lines']}, cases: {ts['cases']}, "
                     f"model events: {ts['model_events']}, retry events: {ts['retry_events']}, "
                     f"input tokens: {ts['input_tokens_total']}, output tokens: {ts['output_tokens_total']}")
        lines.append(ts["note"])
    if ledger.get("ingest_summary"):
        lines.append("")
        lines.append("## Ingest summary (ingested, never judged by itself)")
        lines.append("")
        for s in ledger["ingest_summary"]:
            lines.append(f"- File: {s.get('ingest_file', 'unknown')}, formats: {s.get('formats')}, runs: {s.get('runs')}, unparseable: {s.get('unparseable')}, missing exit code: {s.get('missing_exit_code')}, generic runner: {s.get('generic_runner')}.")
        lines.append("Ingested runs are records only. A check is judged only from its own exact command run, never from another runner, and never from an ingested record alone without a human check.")
    lines.append("")
    lines.append("## Judgments")
    lines.append("")
    for j in ledger["judgments"]:
        lines.append(f"### {j['criterion_id']}: {j['criterion_text']}")
        lines.append(f"- Status: **{j['status']}**. Trust tier: {j['trust_tier']}. Evidence source: {j['evidence_source']}. Evidence ID: {j['evidence_id']}.")
        for field in ("command", "working_directory", "start_timestamp", "end_timestamp",
                      "exit_code", "output_digest", "artifact_digest", "test_target", "after_final_edit"):
            if j.get(field) is not None:
                lines.append(f"- {field}: {j[field]}")
        if j.get("flags"):
            lines.append(f"- Flags: {', '.join(j['flags'])}")
        lines.append(f"- Scope limitation: {j['scope_limitation']}")
        if j.get("recommended_next_action"):
            lines.append(f"- Recommended next action: {j['recommended_next_action']}")
        lines.append("")
    lines.append("## Runs (history, including superseded runs)")
    lines.append("")
    for r in ledger["runs"]:
        sup = "SUPERSEDED, never cited" if r.get("superseded") else "citable"
        lines.append(f"- {r.get('label', '')}: {r['command_raw']} | exit {r['exit_code']} | "
                     f"start {r['start_timestamp']} | {r['output_digest']} | {sup} | source {r['source']}")
    return "\n".join(lines) + "\n"


def _write_one(path, data):
    """Write bytes to path through a temp file and an atomic rename.

    The bytes are written to a fresh temp file in the same
    directory (O_EXCL, so no existing file is ever opened for
    writing, and a random component in the temp name, so an
    out-dir writer cannot pre-plant all the candidate names),
    the target is then lstat'd (a symlink, a hardlink to
    another file, or a non-regular file refuses before
    anything is replaced, and the target's mode is recorded,
    masked to the permission bits so a pre-planted setuid
    stale output cannot make the ledger setuid), the mode is
    applied to the temp inode with fchmod while its fd is
    still open, and os.replace moves the temp into place. A
    rename never truncates the target inode, so a symlink or
    hardlink planted between the check and the write cannot
    redirect the output onto another file. The temp entry
    itself is never trusted after the write, and the mode is
    never applied by path: while the temp fd is still open,
    the path is lstat'd again and must name the same inode
    the fd names, be regular, and have a link count of 1, and
    the fd itself is verified too, its mode must equal the
    expected mode (the pre-existing mode, masked to the
    permission bits, or the temp's create mode for a fresh
    file) and the bytes read back through the fd must hash to
    the digest of the bytes written, or the write refuses
    with exit 2 and the poisoned output-path entry is
    unlinked first (unlink removes only the entry, never a
    victim). The old check-then-ftruncate shape had a
    real escape in that window: a flip planted between the
    fstat and the ftruncate truncated the victim before the
    write. A rewrite changes the output inode while keeping a
    pre-existing file's mode, masked to the permission bits;
    a fresh file keeps the temp's explicit 0o666 mode (0666
    minus umask), never executable. The temp is unlinked on
    any failure. Returns the verified (st_dev, st_ino, mode)
    of the file written, so the caller can re-check both
    outputs still name the files it wrote after the second
    write. Raises OSError, which the CLI turns into an exit-2
    refusal with stale removal.

    Residual window, stated honestly: the verification above
    holds up to each file's own check. A swap planted after
    that check and before the process exits cannot be caught
    by this function; write_outputs narrows it by re-checking
    both output paths twice after both writes and then
    re-checking the ledger once more, so the window that
    remains opens after each file's last check (the report's last check is in the second pass, the ledger's is that final check).
    """
    directory = path.parent
    tmp_path = None
    fd = None
    expected_digest = hashlib.sha256(data).hexdigest()
    try:
        for attempt in range(10):
            candidate = directory / (
                f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(6)}-{attempt}")
            try:
                # O_RDWR, not O_WRONLY: the bytes are read back
                # through this same fd after the rename, so the
                # verification never re-opens the path (a path
                # re-open could be swapped onto a victim).
                fd = os.open(candidate, os.O_RDWR | os.O_CREAT | os.O_EXCL
                             | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
            except FileExistsError:
                continue
            tmp_path = candidate
            break
        if fd is None:
            raise OSError(f"could not create temporary output file in {directory}")
        # The create mode, captured before anything can tamper
        # with the temp inode: the expected mode for a fresh
        # file. A pre-existing target's recorded mode replaces
        # it below.
        expected_mode = stat.S_IMODE(os.fstat(fd).st_mode) & 0o777
        while data:
            written = os.write(fd, data)
            if written == 0:
                raise OSError(f"could not write output: {path}")
            data = data[written:]
        try:
            st = os.lstat(path)
        except FileNotFoundError:
            st = None
        if st is not None:
            if not stat.S_ISREG(st.st_mode):
                raise OSError(f"output path is not a regular file: {path}")
            if st.st_nlink != 1:
                raise OSError(f"output path is hardlinked to another file: {path}")
            expected_mode = stat.S_IMODE(st.st_mode) & 0o777
            os.fchmod(fd, expected_mode)
        os.replace(tmp_path, path)
        tmp_path = None
        # Verify, while the temp fd is still open, that the
        # path now names the inode we wrote, is regular, and
        # is not hardlinked; that the inode's mode is the
        # expected mode; and that the bytes read back through
        # the fd are the bytes written. Anything else refuses,
        # and the poisoned output-path entry is unlinked first
        # so a direct caller does not leave a symlink or
        # hardlink to a victim behind.
        after = os.lstat(path)
        mine = os.fstat(fd)
        if ((after.st_dev, after.st_ino) != (mine.st_dev, mine.st_ino)
                or not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
                or stat.S_IMODE(mine.st_mode) != expected_mode):
            try:
                os.unlink(path)
            except OSError:
                pass
            raise OSError(f"output path was replaced during the write: {path}")
        seen = hashlib.sha256()
        offset = 0
        while True:
            chunk = os.pread(fd, 65536, offset)
            if not chunk:
                break
            seen.update(chunk)
            offset += len(chunk)
        if seen.hexdigest() != expected_digest:
            try:
                os.unlink(path)
            except OSError:
                pass
            raise OSError(f"output file content changed during the write: {path}")
        return (mine.st_dev, mine.st_ino, expected_mode)
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def write_outputs(ledger, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "evidence_ledger.json"
    md_path = out_dir / "evidence_report.md"
    # Check both output paths up front, before writing either: a
    # FIFO (or other non-regular file) left in place of a stale
    # output refuses with a clear message before either file is
    # touched, and a hardlink to another file refuses the same
    # way (a link count other than 1 means the write would land
    # on the victim too). The temp-plus-rename write below is the
    # real guard against a swap after this check: a rename never
    # follows a symlink or truncates a hardlinked inode, so a
    # planted link is replaced, never followed, and the write
    # verifies after the rename that the output path still names
    # the temp inode it wrote. Each _write_one returns the
    # verified identity of the file it wrote; after both writes
    # both paths are re-checked against those identities twice in
    # a row, so a swap of the first file during the second file's
    # check is caught by the next pass instead of leaving a
    # poisoned first file behind under a success exit code, and
    # the ledger is then re-checked once more, so a swap planted
    # during the report's check in the second pass is caught too.
    # The residual window for each output opens only after that output's last check: the report's is in the second pass, the ledger's is that final check.
    for path in (json_path, md_path):
        try:
            st = path.stat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"output path is not a regular file: {path}")
        if st.st_nlink != 1:
            raise OSError(f"output path is hardlinked to another file: {path}")
    json_ident = _write_one(json_path, (json.dumps(ledger, indent=2) + "\n").encode("utf-8"))
    md_ident = _write_one(md_path, build_markdown(ledger).encode("utf-8"))
    # Two consecutive clean passes over both paths: a swap of the
    # first file during the second file's check is caught by the
    # next pass. A mismatch unlinks the poisoned entry and
    # refuses, as before. A final re-check of the ledger follows
    # the loop: a swap of the ledger during the report's check in
    # the second pass is caught here, so the residual window for
    # each output opens only after that output's last check (the
    # report's is in the second pass, the ledger's is this final check).
    clean_passes = 0
    while clean_passes < 2:
        for path, ident in ((json_path, json_ident), (md_path, md_ident)):
            st = os.lstat(path)
            if ((st.st_dev, st.st_ino) != (ident[0], ident[1])
                    or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                    or stat.S_IMODE(st.st_mode) != ident[2]):
                try:
                    os.unlink(path)
                except OSError:
                    pass
                raise OSError(f"output path was replaced during the write: {path}")
        clean_passes += 1
    st = os.lstat(json_path)
    if ((st.st_dev, st.st_ino) != (json_ident[0], json_ident[1])
            or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
            or stat.S_IMODE(st.st_mode) != json_ident[2]):
        try:
            os.unlink(json_path)
        except OSError:
            pass
        raise OSError(f"output path was replaced during the write: {json_path}")
    return json_path, md_path
