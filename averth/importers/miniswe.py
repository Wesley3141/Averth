"""mini-SWE-agent trajectory importer.

Converts a public mini-SWE-agent ``.traj.json`` (the format published by
the SWE-bench leaderboard, e.g. ``django__django-15930.traj.json``) into
Averth events, so ``averth try`` can meter a run straight from the raw
trajectory file.

Conversion rules (these reproduce the case-study events, as parsed
event records; see ``try-it/fixtures/trace-events-django-15930.jsonl``
and the test in ``tests/test_try_it.py``):

- One model event per assistant message. ``input_tokens`` is the
  character count of all preceding message text divided by 4 (integer
  division); ``output_tokens`` is the character count of the assistant
  message itself divided by 4. Token counts are therefore estimates,
  not provider-recorded usage: the meter prices them at vendor list
  prices and the report must say so, exactly as the case study does.
  The events deliberately do NOT set ``tokens_estimated``: the
  published case-study numbers ($0.91 priced, $0.07 estimated) were
  produced from events without that flag, and the acceptance test for
  the try-it requires the published numbers to reproduce exactly.
  The estimate basis is disclosed in the report instead of being
  hidden in a flag the reader never sees.
- One tool event named ``bash`` per `````bash`` code block in the
  assistant message, immediately after its model event. A block is a
  fence of exactly `````bash`` (case-insensitive, optional trailing
  spaces, optional newline) through the closing ````` ``` `````.
- One end event when the trajectory carries an exit status.
  ``info.exit_status == "Submitted"`` (exact match, case-sensitive)
  means the agent submitted a patch, so ``success`` is True; any
  other recorded status means False. If the trajectory carries no
  exit status, no end event is emitted and the attempt auto-ends
  outcome-unknown (spend recorded, no outcome recorded), never
  invented failure.

The trajectory's own ``info.model_stats.instance_cost`` is NOT used
here: it is the leaderboard's recorded cost, and the honest place for
it is the try report's recorded-cost comparison (``--recorded``),
sourced from the leaderboard entry's ``per_instance_details.json``,
not folded into the metered events. ``traj_instance_cost`` reads it
separately so ``averth try`` can cross-check the operator-supplied
figure against it.
"""

import json
import os
import re

from .common import events_to_tracker, ledger_from_tracker

_BASH_FENCE = re.compile(r"```bash[ \t]*\n?(.*?)```",
                         re.DOTALL | re.IGNORECASE)


def _message_text(message):
    """Plain text of one trajectory message.

    Assistant messages carry a string; user messages carry a list of
    ``{"type": "text", "text": ...}`` parts. Anything else contributes
    nothing rather than crashing the conversion: non-string ``text``
    values are skipped, not coerced.
    """
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
            and isinstance(part.get("text", ""), str)
        )
    return ""


def _infer_model(path):
    """Best-effort model name from the file's basename, or None.

    Scans the basename (not the directory: a directory that merely
    mentions a model name must not price the run) for a model name
    that exists in the price table (longest match wins, so
    ``claude-sonnet-4-20250514`` beats the ``claude-sonnet-4``
    prefix). The name must sit on a non-alphanumeric boundary, so
    ``mygpt-4o-model.traj.json`` does not infer ``gpt-4o``. Returns
    None when nothing matches; the caller must then ask the user for
    ``--model``.
    """
    from averth import pricing

    base = os.path.basename(path)
    names = sorted(
        (key.split(":", 1)[-1] for key in pricing.MODEL_PRICES),
        key=len,
        reverse=True,
    )
    for name in names:
        if not name:
            continue
        if re.search(r"(?:^|[^A-Za-z0-9])%s(?:[^A-Za-z0-9]|$)"
                     % re.escape(name), base):
            return name
    return None


def is_priced_model(name):
    """True when ``name`` is a model the price table prices.

    Accepts a bare name (``claude-sonnet-4-20250514``) or a full
    ``provider:model`` key. A bare name is priced when the provider
    guessed from it plus the name is a table key.
    """
    from averth import pricing
    from .common import guess_provider

    if not name or not isinstance(name, str):
        return False
    if ":" in name:
        return name in pricing.MODEL_PRICES
    key = "%s:%s" % (guess_provider(name), name)
    return key in pricing.MODEL_PRICES


def traj_instance_cost(path):
    """The trajectory's own recorded cost, or None.

    Reads ``info.model_stats.instance_cost`` when present and a
    number. Never folded into the metered events; used only to
    cross-check an operator-supplied ``--recorded`` figure.
    """
    try:
        with open(path, encoding="utf-8") as f:
            traj = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(traj, dict):
        return None
    info = traj.get("info")
    if not isinstance(info, dict):
        return None
    stats = info.get("model_stats")
    if not isinstance(stats, dict):
        return None
    cost = stats.get("instance_cost")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        return None
    return float(cost)


def miniswe_events(path, model=None):
    """Convert a mini-SWE-agent trajectory file to Averth event dicts.

    Raises ValueError naming the problem when the file is not a
    trajectory, carries no messages, or names no model (pass ``model``
    explicitly or put the model name in the file name).
    """
    with open(path, encoding="utf-8") as f:
        traj = json.load(f)
    if not isinstance(traj, dict) or "messages" not in traj:
        raise ValueError(
            "%s is not a mini-SWE-agent trajectory (no 'messages' key)"
            % path
        )
    messages = traj["messages"]
    if not isinstance(messages, list) or not messages:
        raise ValueError("%s carries no messages" % path)
    case_id = traj.get("instance_id") or "miniswe-trace"
    if model is None:
        model = _infer_model(path)
    if not model:
        raise ValueError(
            "no model named for %s: pass --model (e.g. "
            "--model claude-sonnet-4-20250514) or put the model name in "
            "the file path" % path
        )
    events = []
    prior_chars = 0
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(
                "%s message %d is not an object (expected a message "
                "with 'role' and 'content')" % (path, index)
            )
        text = _message_text(message)
        if message.get("role") == "assistant":
            events.append({
                "type": "model",
                "case_id": case_id,
                "model": model,
                "input_tokens": prior_chars // 4,
                "output_tokens": len(text) // 4,
            })
            for _ in _BASH_FENCE.findall(text):
                events.append({
                    "type": "tool",
                    "case_id": case_id,
                    "name": "bash",
                })
        prior_chars += len(text)
    info = traj.get("info")
    status = info.get("exit_status") if isinstance(info, dict) else None
    if status is not None:
        events.append({
            "type": "end",
            "case_id": case_id,
            "success": status == "Submitted",
        })
    return events


def load_miniswe(path, model=None, agent_name="miniswe-import"):
    """Parse a mini-SWE-agent trajectory file and return a ledger dict.

    Mirrors the other importers: events go through
    ``events_to_tracker`` (auto-end outcome-unknown when the
    trajectory carries no exit status), then ``ledger_from_tracker``.
    """
    events = miniswe_events(path, model=model)
    tracker = events_to_tracker(
        agent_name, events, auto_end_unknown=True
    )
    return ledger_from_tracker(tracker)
