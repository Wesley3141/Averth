"""Convert raw SWE-smith trajectory rows to averth JSONL events.

MECHANICAL conversion only: walks each raw trajectory's message list and
emits EVENT-schema lines (see averth/importers/jsonl.py). No record
content is edited; field mapping rules are fixed below and documented in
SOURCES.md.

Mapping rules:
  - case_id = row["traj_id"] (unique per sampled run)
  - one "model" event per assistant turn; model name from row["model"]
  - one "tool" event per tool call: structured tool_calls[].function.name
    in the tool-call layout, or <function=NAME> tags parsed from the
    assistant text in the XML-embedded layout
  - "retry" event before the next model call when the preceding tool
    observation matches the error heuristic (documented in SOURCES.md)
  - "end" event with success = row["resolved"] (the dataset's real
    pass/fail verdict for the run)

TOKEN ESTIMATION (not recorded data): neither layout records per-call
token usage, so input_tokens = chars(all preceding message text)//4 and
output_tokens = chars(this assistant turn)//4. These are mechanical
estimates, never presented as recorded usage. See SOURCES.md.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "events.jsonl")

# error heuristic applied ONLY to tool observation text (never the task
# prompt). A tool call counts as failed when its observation contains a
# Python traceback, a unittest/pytest failure line, or a shell
# "command not found". Documented approximation, see SOURCES.md.
_TRACEBACK = "traceback (most recent call last):"
_FAILED_LINE = re.compile(r"^(FAILED|ERROR)\b", re.M)
_CMD_NOT_FOUND = "command not found"


def _observation_failed(txt):
    low = txt.lower()
    return (_TRACEBACK in low
            or _FAILED_LINE.search(txt) is not None
            or _CMD_NOT_FOUND in low)

FUNC_TAG = re.compile(r"<function=([A-Za-z0-9_.-]+)>")


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


def assistant_text(msg):
    bits = [text_of(msg.get("content"))]
    if msg.get("thought"):
        bits.append(str(msg["thought"]))
    if msg.get("action"):
        bits.append(str(msg["action"]))
    for tc in msg.get("tool_calls") or []:
        fn = (tc.get("function") or {})
        bits.append(str(fn.get("name", "")))
        bits.append(str(fn.get("arguments", "")))
    return "\n".join(b for b in bits if b)


def convert_row(row):
    case_id = row["traj_id"]
    model = row["model"]
    events = []
    msgs = json.loads(row["messages"])

    context_chars = 0  # chars of conversation text before current turn
    pending_retry = None

    def flush_retry():
        nonlocal pending_retry
        if pending_retry is not None:
            events.append({"type": "retry", "case_id": case_id,
                           "reason": pending_retry})
            pending_retry = None

    for msg in msgs:
        role = msg.get("role")
        if role == "assistant":
            flush_retry()
            text = assistant_text(msg)
            events.append({
                "type": "model", "case_id": case_id, "model": model,
                "input_tokens": context_chars // 4,
                "output_tokens": len(text) // 4,
            })
            tools = []
            for tc in msg.get("tool_calls") or []:
                fn = (tc.get("function") or {})
                name = str(fn.get("name") or "unknown")
                tools.append(name)
            if not tools:
                for name in FUNC_TAG.findall(text_of(msg.get("content"))):
                    tools.append(name)
            if not tools and msg.get("action"):
                tools.append("bash")
            for name in tools:
                events.append({"type": "tool", "case_id": case_id,
                               "name": name})
            context_chars += len(text)
        elif role in ("tool", "user"):
            txt = text_of(msg.get("content"))
            context_chars += len(txt)
            is_observation = (role == "tool"
                              or txt.startswith("OBSERVATION:"))
            if is_observation and _observation_failed(txt):
                # retry marks the steps that FOLLOW it; queue until the
                # next assistant turn so ordering stays causal
                pending_retry = "tool error"
        elif role == "system":
            context_chars += len(text_of(msg.get("content")))

    flush_retry()
    events.append({"type": "end", "case_id": case_id,
                   "success": bool(row["resolved"])})
    return events


def main():
    paths = sorted(f for f in os.listdir(RAW) if f.endswith(".json"))
    if not paths:
        print("no raw files in %s" % RAW, file=sys.stderr)
        sys.exit(1)
    n_events = 0
    with open(OUT, "w") as out:
        for name in paths:
            with open(os.path.join(RAW, name)) as f:
                row = json.load(f)
            for ev in convert_row(row):
                out.write(json.dumps(ev) + "\n")
                n_events += 1
    print("converted %d trajectories -> %s (%d events)"
          % (len(paths), OUT, n_events))


if __name__ == "__main__":
    main()
