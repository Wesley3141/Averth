"""Importer for OpenAI Codex CLI session rollouts (JSONL).

Accepted input: ONE Codex rollout file, e.g.
``~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl``.
Each line is one record. Two line shapes are accepted, because the
rollout format has shipped both across versions:

    {"type": "session_meta",
     "payload": {"id": "01a1...", "cwd": "/Users/me/shop-api",
                  "cli_version": "0.130.0",
                  "model_provider": "openai",
                  "source": "cli"}}
    {"type": "event_msg",
     "payload": {"type": "token_count",
                 "info": {"total_token_usage": {
                     "input_tokens": 1200,
                     "cached_input_tokens": 800,
                     "output_tokens": 300,
                     "reasoning_output_tokens": 50}}}}
    {"type": "turn_context",
     "payload": {"model": "gpt-5", ...}}

A flattened variant (payload fields inline on the record, no
"payload" wrapper) is also accepted: the importer reads the payload
dict when present, otherwise the record itself.

What this importer reads, and nothing else:

- "session_meta": the thread id becomes the Averth case_id
  (fallback: the file stem). A "source" that is an object rather than
  a plain string, or "agent_nickname"/"agent_role" fields, mark a
  subagent thread; that fact is recorded in stats, not hidden, and
  the file is still parsed as its own case (see below).
- "event_msg" with payload type "token_count": cumulative session
  totals. Codex counts are CUMULATIVE, so this importer emits one
  Averth model event per ADVANCE (the delta between successive
  token_count snapshots), never the running total itself. Summing
  the snapshots would multiply-count the session.
- "turn_context": the active model for subsequently counted usage.
  A token_count seen before any turn_context is attributed to model
  "unknown", which prices at Averth's documented fallback estimate
  and is flagged in unpriced_models, never silently given a vendor
  price. A model seen on a turn_context applies until the next
  turn_context changes it.

Token semantics, stated explicitly because they decide the dollars:

- input_tokens is treated as TOTAL input following the OpenAI usage
  convention (it includes cached_input_tokens). So:
      total_input_tokens = input_tokens
      cached_input_tokens = cached_input_tokens
      uncached input = input_tokens - cached_input_tokens
  If a snapshot ever reports cached_input_tokens greater than
  input_tokens, that convention cannot hold for that snapshot, and
  the importer falls back for that snapshot to
  total = input + cached. Either way nothing is dropped and the
  fallback is counted in stats["cache_convention_fallbacks"].
  These dollars are estimates until checked against a real Codex
  bill: Codex subscription billing (per-seat plans, rate limits)
  is not the same thing as API list-price metering, and this
  importer prices at list prices like every other Averth importer.
- output_tokens + reasoning_output_tokens are priced as output:
  reasoning tokens are billed as output tokens. The split is kept
  in stats so a reviewer can see how much of the output is
  reasoning.
- cache reads are priced at the Tracker's cache_read_discount
  (0.10 by default), exactly like every other importer.

Compaction / resets, stated explicitly:
A "compacted" record, or a token_count snapshot whose totals fall
below the previous snapshot on any field, resets the cumulative
baseline: the next snapshot's totals count in full as a new
segment, rather than going negative. Resets are counted in
stats["baseline_resets"]; a reset never silently discards the
segment that follows it.

What is deliberately NOT emitted:

- Tool calls: "response_item" function_call / function_call_output
  records are local shell/file/editor calls with no vendor price,
  so they are NOT emitted as Averth tool events (emitting them
  would add built-in defaults and invent tool spend). Their names,
  arguments, and outputs are never copied into events.
- Retries: nothing in a rollout reliably marks a retry (a failed
  command, a re-issued prompt, and a compaction are different
  things), so this importer emits NO retry events. Inferring one
  would be guessing.
- Acceptance: a rollout records execution, not customer
  acceptance, so every imported case ends with an EXPLICIT
  unknown-outcome end (success=False, outcome_inferred=True,
  outcome_unknown=True). Cost per accepted outcome is UNKNOWN for
  every Codex import unless acceptance labels are joined
  separately. Do not quote a cost-per-success from a Codex import
  alone.
- Prompts, completions, tool payloads, and message text are never
  copied into events. Only cost/token metadata reaches the ledger.

Subagent rollouts, stated explicitly:
Subagent threads are separate rollout files whose session_meta
source is an object (e.g. {"subagent": {...}}) and which may carry
a parent_thread_id. This importer NEVER globs a directory: passing
a directory raises ValueError. Pass one rollout file at a time.
A subagent file parsed on its own becomes its own case, flagged in
stats["subagent_thread"]. Known limitation, not hidden: current
MultiAgent subagent rollouts can persist a replayed parent-history
prefix, and this importer counts deltas from the first snapshot
it sees, so a subagent file with a replayed prefix can overcount
against the parent thread. For a live call, import the main thread
file, not a subagent file, and check stats["subagent_thread"]
before quoting any number.

Validation is loud, not silent: malformed JSON, a non-object line,
a non-numeric / boolean / negative / non-finite / fractional token
count, or a token count above 1e12 all raise ValueError naming the
line number. Nothing is truncated, clamped, or dropped silently
except the documented exclusions above (non-token records,
tool records, prompts), all of which are counted in stats.
"""

import json
import math
import os

from .common import events_to_tracker, ledger_from_tracker, guess_provider

_MAX_TOKENS = 10 ** 12

_INPUT_KEYS = ("input_tokens",)
_CACHED_KEYS = ("cached_input_tokens",)
_OUTPUT_KEYS = ("output_tokens",)
_REASONING_KEYS = ("reasoning_output_tokens",)


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _token_value(line_no, field, value):
    """Validate one token count, loudly. Returns an int."""
    if not _is_num(value):
        raise ValueError("line %d: %r must be a number, got %r"
                         % (line_no, field, value))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("line %d: %r must be finite, got %r"
                         % (line_no, field, value))
    if value < 0:
        raise ValueError("line %d: %r must be >= 0, got %r"
                         % (line_no, field, value))
    if value > _MAX_TOKENS:
        raise ValueError("line %d: %r implausibly large: %r"
                         % (line_no, field, value))
    if isinstance(value, float) and not value.is_integer():
        raise ValueError("line %d: %r must be an integer token count, "
                         "got %r" % (line_no, field, value))
    return int(value)


def _first_num(mapping, keys):
    """Return the first present key value, or None if none present."""
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _payload_of(record):
    """Return the payload dict for a rollout record.

    Accepts the payload-wrapped shape and the flattened shape.
    Returns None when neither yields a dict.
    """
    payload = record.get("payload")
    if isinstance(payload, dict):
        return payload
    return record


def _usage_counts(line_no, total_usage):
    """Extract (input, cached, output, reasoning) from a
    total_token_usage dict, or None when it carries no numeric token
    field at all."""
    if not isinstance(total_usage, dict):
        return None
    raw_input = _first_num(total_usage, _INPUT_KEYS)
    raw_cached = _first_num(total_usage, _CACHED_KEYS)
    raw_output = _first_num(total_usage, _OUTPUT_KEYS)
    raw_reasoning = _first_num(total_usage, _REASONING_KEYS)
    if (raw_input is None and raw_cached is None
            and raw_output is None and raw_reasoning is None):
        return None
    return (
        _token_value(line_no, "input_tokens", raw_input)
        if raw_input is not None else 0,
        _token_value(line_no, "cached_input_tokens", raw_cached)
        if raw_cached is not None else 0,
        _token_value(line_no, "output_tokens", raw_output)
        if raw_output is not None else 0,
        _token_value(line_no, "reasoning_output_tokens", raw_reasoning)
        if raw_reasoning is not None else 0,
    )


def parse_codex_rollout(path):
    """Parse one Codex rollout file.

    Returns (events, stats). events are EVENT-schema dicts ready for
    events_to_tracker(); stats counts every exclusion so nothing is
    silently dropped.
    """
    if os.path.isdir(path):
        raise ValueError(
            "codex import: %r is a directory; pass a single rollout "
            "JSONL file, never a directory. Averth never globs session "
            "files, because subagent rollout files would double count "
            "the same work." % (path,))
    events = []
    stats = {
        "lines_total": 0,
        "lines_skipped_blank": 0,
        "token_count_events": 0,
        "model_events_emitted": 0,
        "other_lines_skipped": 0,
        "baseline_resets": 0,
        "cache_convention_fallbacks": 0,
        "sessions": [],
        "subagent_thread": False,
        "model": None,
        "input_tokens_total": 0,
        "cache_read_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
    }
    case_id = os.path.splitext(os.path.basename(path))[0] or "codex-session"
    # Cumulative baseline: (input, cached, output, reasoning) from
    # the previous token_count snapshot, or None before the first.
    baseline = None
    current_model = "unknown"
    saw_model = False

    with open(path) as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                stats["lines_skipped_blank"] += 1
                continue
            stats["lines_total"] += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("line %d: invalid JSON: %s"
                                 % (line_no, exc))
            if not isinstance(record, dict):
                raise ValueError("line %d: expected a JSON object, got %r"
                                 % (line_no, record))
            rtype = record.get("type")
            payload = _payload_of(record)

            if rtype == "session_meta":
                meta_id = payload.get("id")
                if isinstance(meta_id, str) and meta_id:
                    case_id = meta_id
                source = payload.get("source")
                if (isinstance(source, dict)
                        or payload.get("agent_nickname") is not None
                        or payload.get("agent_role") is not None):
                    stats["subagent_thread"] = True
                if case_id not in stats["sessions"]:
                    stats["sessions"].append(case_id)
                continue

            if rtype == "turn_context":
                model = payload.get("model")
                if isinstance(model, str) and model:
                    current_model = model
                    saw_model = True
                    stats["model"] = model
                continue

            if rtype == "event_msg":
                msg_type = payload.get("type")
                if msg_type != "token_count":
                    stats["other_lines_skipped"] += 1
                    continue
                info = payload.get("info")
                total_usage = None
                if isinstance(info, dict):
                    total_usage = info.get("total_token_usage")
                if total_usage is None:
                    # Some shapes put total_token_usage beside info.
                    total_usage = payload.get("total_token_usage")
                counts = _usage_counts(line_no, total_usage) \
                    if total_usage is not None else None
                if counts is None:
                    stats["other_lines_skipped"] += 1
                    continue
                stats["token_count_events"] += 1
                in_tok, cache_tok, out_tok, reason_tok = counts
                if baseline is None:
                    delta = counts
                elif (in_tok < baseline[0] or cache_tok < baseline[1]
                        or out_tok < baseline[2]
                        or reason_tok < baseline[3]):
                    # Compaction or a new segment: totals fell, so the
                    # new snapshot counts in full, never negative.
                    stats["baseline_resets"] += 1
                    delta = counts
                else:
                    delta = tuple(new - old for old, new
                                  in zip(baseline, counts))
                baseline = counts
                d_in, d_cache, d_out, d_reason = delta
                if d_in == 0 and d_cache == 0 and d_out == 0 \
                        and d_reason == 0:
                    continue
                # OpenAI usage convention: input includes cached.
                if d_cache <= d_in:
                    total_input = d_in
                    cached = d_cache
                else:
                    stats["cache_convention_fallbacks"] += 1
                    total_input = d_in + d_cache
                    cached = d_cache
                event = {"type": "model", "case_id": case_id,
                         "provider": guess_provider(current_model),
                         "model": current_model,
                         "input_tokens": total_input,
                         "output_tokens": d_out + d_reason,
                         "cached_input_tokens": cached,
                         "usage_known": True}
                events.append(event)
                stats["model_events_emitted"] += 1
                stats["input_tokens_total"] += total_input
                stats["cache_read_tokens"] += cached
                stats["output_tokens"] += d_out
                stats["reasoning_tokens"] += d_reason
                continue

            # response_item (messages, tool calls, tool outputs),
            # compacted, and every other record type carry no new
            # token totals and are counted, not parsed for spend.
            stats["other_lines_skipped"] += 1

    if not saw_model:
        stats["model"] = "unknown"
    if events:
        events.append({"type": "end", "case_id": case_id,
                       "success": False, "outcome_inferred": True,
                       "outcome_unknown": True})
    return events, stats


def load_codex(path, agent_name="codex-import"):
    """Parse one Codex rollout file and return a sanitized ledger.

    The ledger carries an extra top-level "codex_import_stats" key
    (the parse stats, so deltas, resets, and the subagent flag stay
    visible after the load). tracker_from_ledger ignores that key,
    so the CLI round-trip (ledger -> tracker -> pnl) is unaffected.
    """
    events, stats = parse_codex_rollout(path)
    tracker = events_to_tracker(agent_name, events)
    ledger = ledger_from_tracker(tracker)
    ledger["codex_import_stats"] = stats
    return ledger
