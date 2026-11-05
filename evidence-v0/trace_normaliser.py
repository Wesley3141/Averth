#!/usr/bin/env python3
"""Wave 2: JSONL trace normaliser, summary only, never a verdict.

Input shapes accepted, all local files the operator names:
  - One JSON object per line, each with type and case_id where
    present. This is the shape cli.py --trace summarises.
  - A single JSON array of event objects.
  - Pretty-printed JSON objects, one after another, possibly
    spanning many lines, including OpenTelemetry-style output.

Output: one JSON object per line, in input order, with the
original type and case_id preserved where present, and no
judgment added. Events that cannot be parsed are counted in
the summary printed to stderr, and are not silently dropped
from the count, and are not guessed into a case.

This normaliser never judges anything. A normalised trace
fed to cli.py --trace is summarised only, exactly like any
other trace. No cost-per-accepted-outcome figure is computed
from it, and no judgment may cite a trace summary as a
verdict. If the input carries no type or case_id fields, the
output carries none either; the normaliser does not invent
them, and a downstream summary will show that gap honestly.

Usage:
  python3 trace_normaliser.py --input trace.json --out events.jsonl
  python3 trace_normaliser.py --input trace.jsonl --out events.jsonl
"""
import argparse
import json
from pathlib import Path


def normalise_text(text):
    """Return (events, unparseable_count) from mixed JSON text."""
    events = []
    unparseable = 0
    stripped = text.strip()
    if not stripped:
        return events, unparseable
    decoder = json.JSONDecoder()
    # A top-level array is the cleanest shape: parse it whole.
    if stripped.startswith("["):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        events.append(item)
                    else:
                        unparseable += 1
                return events, unparseable
    # Otherwise, walk the text with raw_decode, skipping
    # whitespace between objects. A line that is not JSON is
    # counted once per line, not once per character, and the
    # walk continues after it where possible.
    idx = 0
    length = len(text)
    while idx < length:
        while idx < length and text[idx] in " \t\r\n":
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            # Skip to the next line and count one unparseable line.
            next_nl = text.find("\n", idx)
            if next_nl == -1:
                unparseable += 1
                break
            unparseable += 1
            idx = next_nl + 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    events.append(item)
                else:
                    unparseable += 1
        else:
            unparseable += 1
        idx = end
    return events, unparseable


def main(argv=None):
    ap = argparse.ArgumentParser(description="Normalise a trace to one JSON object per line")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    text = Path(args.input).read_text()
    events, unparseable = normalise_text(text)
    out_lines = []
    for ev in events:
        out_lines.append(json.dumps(ev, sort_keys=True))
    Path(args.out).write_text("\n".join(out_lines) + ("\n" if out_lines else ""))
    print(f"normalised {len(events)} events to {args.out}")
    if unparseable:
        print(f"unparseable: {unparseable} (counted, not guessed, not judged)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
