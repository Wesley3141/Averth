"""reporter: render the JSON ledger and the Markdown report from the
SAME judgments. The Markdown report is never hand-edited into a
different verdict; it is generated from the ledger rows, in order.
The LIMITATIONS section is mandatory and non-collapsible.
"""
import json

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


def write_outputs(ledger, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "evidence_ledger.json"
    md_path = out_dir / "evidence_report.md"
    json_path.write_text(json.dumps(ledger, indent=2) + "\n")
    md_path.write_text(build_markdown(ledger))
    return json_path, md_path
