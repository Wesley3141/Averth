"""Convert raw mini-SWE-agent .traj.json files to agentpnl JSONL events.

MECHANICAL conversion only: walks each raw trajectory's message list and
emits EVENT-schema lines (see agentpnl/importers/jsonl.py). No record
content is edited; field mapping rules are fixed below and documented in
SOURCES.md.

Mapping rules:
  - case_id = file's instance_id
  - one "model" event per assistant turn, model "claude-sonnet-4-20250514"
  - one "tool" event per assistant turn, name "bash" (mini-SWE-agent issues
    exactly one bash command per turn by construction)
  - "retry" event before the next model call when the tool result message
    carries <returncode> != 0 (a real recorded failure signal)
  - "end" event with success = per_instance_details.json["resolved"] for
    the instance (the leaderboard's real pass/fail verdict); falls back to
    info.exit_status == "Submitted" when the instance is absent

TOKEN ESTIMATION (not recorded data): the traces record no per-call token
usage, so input_tokens = chars(all preceding message text)//4 and
output_tokens = chars(this assistant turn)//4. Mechanical estimates only.
per_instance_details.json DOES record real per-instance cost and api_calls;
compare.py cross-checks the meter against those real numbers.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "events.jsonl")
DETAILS = os.path.join(HERE, "per_instance_details.json")

MODEL = "claude-sonnet-4-20250514"
RC = re.compile(r"<returncode>(-?\d+)</returncode>")


def text_of(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def convert_file(path, details):
    with open(path) as f:
        data = json.load(f)
    instance_id = data["instance_id"]
    msgs = data["messages"]
    events = []
    context_chars = 0
    pending_retry = None

    for msg in msgs:
        role = msg.get("role")
        if role == "assistant":
            if pending_retry is not None:
                events.append({"type": "retry", "case_id": instance_id,
                               "reason": pending_retry})
                pending_retry = None
            text = text_of(msg.get("content"))
            events.append({
                "type": "model", "case_id": instance_id, "model": MODEL,
                "input_tokens": context_chars // 4,
                "output_tokens": len(text) // 4,
            })
            events.append({"type": "tool", "case_id": instance_id,
                           "name": "bash"})
            context_chars += len(text)
        elif role == "user":
            txt = text_of(msg.get("content"))
            context_chars += len(txt)
            m = RC.search(txt)
            if m and int(m.group(1)) != 0:
                pending_retry = "returncode %s" % m.group(1)
        elif role == "system":
            context_chars += len(text_of(msg.get("content")))

    if pending_retry is not None:
        events.append({"type": "retry", "case_id": instance_id,
                       "reason": pending_retry})

    det = details.get(instance_id) or {}
    if "resolved" in det:
        success = bool(det["resolved"])
    else:
        success = (data.get("info", {}).get("exit_status") == "Submitted")
    events.append({"type": "end", "case_id": instance_id, "success": success})
    return events


def main():
    with open(DETAILS) as f:
        details = json.load(f)
    paths = sorted(f for f in os.listdir(RAW) if f.endswith(".traj.json"))
    if not paths:
        print("no raw files in %s" % RAW, file=sys.stderr)
        sys.exit(1)
    n_events = 0
    with open(OUT, "w") as out:
        for name in paths:
            for ev in convert_file(os.path.join(RAW, name), details):
                out.write(json.dumps(ev) + "\n")
                n_events += 1
    print("converted %d trajectories -> %s (%d events)"
          % (len(paths), OUT, n_events))


if __name__ == "__main__":
    main()
