"""Importer for Claude Code session transcripts (JSONL).

Accepted input: ONE Claude Code session JSONL file. Each line is one
record from a session export. The records this importer reads are:

    {"type": "assistant",
     "sessionId": "sess-1",
     "uuid": "line-uuid-1",
     "isSidechain": false,
     "message": {
         "id": "msg_01abc",
         "model": "claude-opus-4-6",
         "usage": {
             "input_tokens": 137,
             "cache_creation_input_tokens": 5521,
             "cache_read_input_tokens": 815193,
             "output_tokens": 4260
         }
     }}

Records of any other type ("user", "system", "file-history-snapshot",
"queue-operation", ...) carry no model usage and are ignored. A record
with type "result" is honoured only as a session end marker (see below);
its "total_cost_usd", if present, is deliberately NOT used as a billed
cost, because the per-message usage records already drive the dollars
and adding the session total would double count.

Cache pricing, stated explicitly (this is the decision POC 6 required):
Claude Code reports three separate input counts, and cache reads
routinely dwarf uncached input. Averth's internal model event only has
one input count and one cached count, and its Tracker silently clamps
cached > input to input. This importer therefore maps to TOTAL CONTEXT,
never by copying the fields across and never by capping:

    total_input_tokens   = input_tokens
                         + cache_read_input_tokens
                         + cache_creation_input_tokens
    cached_input_tokens  = cache_read_input_tokens

So cached_input_tokens is always <= total_input_tokens by construction,
with nothing dropped and nothing capped. Pricing then follows Averth's
normal rule on the mapped event:

  - cache_read tokens are priced at the Tracker's cache_read_discount
    (0.10 by default, Anthropic's published cache-read rate).
  - uncached input tokens AND cache_creation tokens are priced at the
    FULL input price. Averth does not model cache creation separately:
    there is no 1.25x cache-write rate in its price table. Pricing
    creation at full rate therefore UNDERPRICES it relative to a vendor
    1.25x write rate, by 20% of the creation tokens' full-price value.
    That underprice is documented here and in the wave-1 report, not
    hidden, and it is the reason a Claude Code dollar figure from this
    importer must be labelled an estimate, never a vendor bill, until
    cache-creation pricing is modelled separately.

Deduplication, stated explicitly:
One API response can be logged several times while streaming, sharing
one message id and one usage object. A naive sum double counts it.
This importer keeps only the FIRST record for a given message id that
carries usage, and counts every later record with that id in
stats["duplicates_skipped"]. A record with no message id falls back to
its line "uuid" as the dedupe key. A record with no usage at all is NOT
marked seen, so a later record for the same id that does carry usage
still counts. The aggregated "modelUsage" object, when present on a
record, is IGNORED: it already includes the per-message usage, so
counting both would double count.

Subagent / sidechain records, stated explicitly:
A record is a sidechain record when "isSidechain" is true (also
accepted: "is_sidechain"). By default (include_sidechain=False) such
records are SKIPPED and counted in stats["sidechain_skipped"], because
their usage is already reflected in the top-level loop in some exports
and because sidechain transcripts are separate files in others.
Passing include_sidechain=True includes them in the SAME attempt with
branch="sidechain" (so they are visible, not silently merged into the
main path, and so a future retry marker could scope them). This
importer NEVER globs a directory: passing a directory raises
ValueError. Pass one session file at a time; do not pass a project
directory and let it recurse into subagent transcript files, or the
same calls will be counted twice.

Tool calls and retries:
Claude Code "tool_use" blocks are local shell/file/editor calls with no
vendor price, so they are NOT emitted as Averth tool events (emitting
them would add built-in $0.002 defaults and invent tool spend). A
"tool_result" line is not a retry marker: it may be an error, a
success, or quoted repo output, and inferring a retry from it would be
guessing. This importer therefore emits NO retry events. If a session
has no "result" end marker, the attempt is auto-ended by
events_to_tracker with success=False and outcome_inferred=True.
A "result" marker with is_error=false (or subtype "success") ends the
attempt with success=True but outcome_inferred=True, because execution
completion is not customer acceptance: cost per accepted outcome is
UNKNOWN for every Claude Code session imported here unless acceptance
labels are joined separately. Do not quote a cost-per-success from a
Claude Code import alone.

Output privacy: only cost/token metadata reaches the ledger (case_id,
model, tokens, costs). Prompts, completions, tool names, tool payloads,
and message text are never copied into events. Case_id is the
sessionId from the transcript, or "claude-session" when absent; it may
contain user data, so redact before sharing, as with every importer.

Validation is loud, not silent: malformed JSON, a non-object line,
a non-numeric / boolean / negative / non-finite / fractional token
count, or a token count above 1e12 all raise ValueError naming the
line number. Nothing is truncated, clamped, or dropped silently except
the documented duplicate, sidechain, and modelUsage exclusions above,
all of which are counted in the returned stats.
"""

import json
import math
import os

from .common import events_to_tracker, ledger_from_tracker, guess_provider

# Cache-creation pricing decision, in one place, so a reviewer can find
# it without reading the whole module: creation tokens are priced at the
# FULL input price (see module docstring). They are NOT priced at the
# cache-read discount, NOT priced at a 1.25x write rate (unmodelled),
# and NOT dropped.
CACHE_CREATION_PRICING = (
    "cache_creation_input_tokens are included in total input and priced "
    "at the full input price; Averth does not model cache writes "
    "separately, so this underprices creation relative to a 1.25x "
    "vendor write rate and must be labelled an estimate"
)

_MAX_TOKENS = 10 ** 12

_INPUT_ALIASES = ("input_tokens",)
_CACHE_READ_ALIASES = ("cache_read_input_tokens",
                        "cacheReadInputTokens")
_CACHE_CREATION_ALIASES = ("cache_creation_input_tokens",
                           "cacheCreationInputTokens")
_OUTPUT_ALIASES = ("output_tokens",)


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
        raise ValueError("line %d: %r must be an integer token count, got %r"
                         % (line_no, field, value))
    return int(value)


def _first_num(usage, aliases):
    """Return the first present alias value, or None if none present."""
    for key in aliases:
        if key in usage and usage[key] is not None:
            return usage[key]
    return None


def _usage_counts(line_no, usage):
    """Extract (input, cache_read, cache_creation, output) from a usage
    dict, or return None when it carries no numeric token field at all.

    A nested "cache_creation" dict (ephemeral_1h/5m breakdown, as in some
    Anthropic usage payloads) is summed; a flat
    cache_creation_input_tokens value takes precedence over the dict.
    """
    if not isinstance(usage, dict):
        return None
    raw_input = _first_num(usage, _INPUT_ALIASES)
    raw_read = _first_num(usage, _CACHE_READ_ALIASES)
    raw_creation = _first_num(usage, _CACHE_CREATION_ALIASES)
    if raw_creation is None:
        nested = usage.get("cache_creation")
        if isinstance(nested, dict) and nested:
            total = 0
            for key, value in nested.items():
                total += _token_value(line_no,
                                      "cache_creation.%s" % key, value)
            raw_creation = total
    raw_output = _first_num(usage, _OUTPUT_ALIASES)
    if (raw_input is None and raw_read is None
            and raw_creation is None and raw_output is None):
        return None
    return (
        _token_value(line_no, "input_tokens", raw_input)
        if raw_input is not None else 0,
        _token_value(line_no, "cache_read_input_tokens", raw_read)
        if raw_read is not None else 0,
        _token_value(line_no, "cache_creation_input_tokens", raw_creation)
        if raw_creation is not None else 0,
        _token_value(line_no, "output_tokens", raw_output)
        if raw_output is not None else 0,
    )


def _is_sidechain(record):
    return record.get("isSidechain") is True \
        or record.get("is_sidechain") is True


def _message_and_model(record):
    """Return (message dict, model name) for an assistant record.

    Prefers message.model; falls back to a top-level "model" on
    simplified exports. Returns (None, None) when neither is a dict/str
    in the expected shape, so the caller can skip loudly-counted.
    """
    message = record.get("message")
    if isinstance(message, dict):
        model = message.get("model") or record.get("model") or "unknown"
        return message, model
    # Simplified export: usage/model at top level, no message wrapper.
    if isinstance(record.get("usage"), dict) or "model" in record:
        return record, record.get("model") or "unknown"
    return None, None


def parse_claude_session(path, include_sidechain=False):
    """Parse one Claude Code session file.

    Returns (events, stats). events are EVENT-schema dicts ready for
    events_to_tracker(); stats counts every exclusion so nothing is
    silently dropped (see module docstring for the three documented
    exclusions: duplicates, sidechain, modelUsage).
    """
    if os.path.isdir(path):
        raise ValueError(
            "claude import: %r is a directory; pass a single session "
            "JSONL file, never a directory. Averth never globs session "
            "files, because subagent transcript files would double count "
            "the same calls." % (path,))
    events = []
    stats = {
        "lines_total": 0,
        "lines_skipped_blank": 0,
        "assistant_lines": 0,
        "model_calls_kept": 0,
        "duplicates_skipped": 0,
        "sidechain_skipped": 0,
        "no_usage_skipped": 0,
        "other_lines_skipped": 0,
        "result_lines": 0,
        "sessions": [],
        "input_tokens_uncached": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "total_context_tokens": 0,
        "output_tokens": 0,
    }
    seen_ids = set()
    cases_with_models = set()

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
            case_id = (record.get("sessionId")
                       or record.get("session_id")
                       or "claude-session")
            if not isinstance(case_id, str):
                raise ValueError("line %d: sessionId must be a string, "
                                 "got %r" % (line_no, case_id))
            if case_id not in stats["sessions"]:
                stats["sessions"].append(case_id)
            rtype = record.get("type")

            if rtype == "result":
                stats["result_lines"] += 1
                if case_id not in cases_with_models:
                    # No model calls for this case: a bare result must not
                    # fabricate a zero-cost attempt (mirrors the stray-end
                    # rule in events_to_tracker).
                    continue
                is_error = record.get("is_error")
                subtype = record.get("subtype")
                if is_error is True:
                    success = False
                elif is_error is False:
                    success = True
                elif subtype == "success":
                    success = True
                elif subtype == "error":
                    success = False
                else:
                    continue
                events.append({"type": "end", "case_id": case_id,
                               "success": success,
                               "outcome_inferred": True})
                continue

            if rtype != "assistant":
                stats["other_lines_skipped"] += 1
                continue
            stats["assistant_lines"] += 1

            if _is_sidechain(record) and not include_sidechain:
                stats["sidechain_skipped"] += 1
                continue

            message, model = _message_and_model(record)
            if message is None:
                stats["no_usage_skipped"] += 1
                continue
            usage = message.get("usage")
            # A simplified export may put usage at top level.
            if usage is None and message is record:
                usage = record.get("usage")
            counts = _usage_counts(line_no, usage) if usage is not None \
                else None
            if counts is None:
                stats["no_usage_skipped"] += 1
                continue

            # Dedupe key: message id first, line uuid as fallback.
            dedupe_id = None
            if isinstance(message, dict):
                mid = message.get("id")
                if isinstance(mid, str) and mid:
                    dedupe_id = "msg:%s" % mid
            if dedupe_id is None:
                uuid = record.get("uuid")
                if isinstance(uuid, str) and uuid:
                    dedupe_id = "uuid:%s" % uuid
            if dedupe_id is not None and dedupe_id in seen_ids:
                stats["duplicates_skipped"] += 1
                continue
            if dedupe_id is not None:
                seen_ids.add(dedupe_id)

            in_tok, cache_read, cache_creation, out_tok = counts
            total_input = in_tok + cache_read + cache_creation
            # By construction cached (cache_read) <= total_input, so the
            # Tracker never needs to clamp, and no token is dropped.
            event = {"type": "model", "case_id": case_id,
                     "provider": guess_provider(model),
                     "model": model,
                     "input_tokens": total_input,
                     "output_tokens": out_tok,
                     "cached_input_tokens": cache_read,
                     "usage_known": True}
            if _is_sidechain(record):
                event["branch"] = "sidechain"
            events.append(event)
            cases_with_models.add(case_id)
            stats["model_calls_kept"] += 1
            stats["input_tokens_uncached"] += in_tok
            stats["cache_read_tokens"] += cache_read
            stats["cache_creation_tokens"] += cache_creation
            stats["total_context_tokens"] += total_input
            stats["output_tokens"] += out_tok
            # Note: "modelUsage" on this record, if present, is ignored
            # on purpose (it aggregates the per-message usage already
            # counted above); it is not a separate exclusion count,
            # because it rides on a kept record, not a skipped one.
    return events, stats


def load_claude(path, agent_name="claude-import",
                include_sidechain=False):
    """Parse one Claude Code session file and return a sanitized ledger.

    The ledger carries an extra top-level "claude_import_stats" key
    (the parse stats, so dedupe/sidechain exclusions stay visible after
    the load). tracker_from_ledger ignores that key, so the CLI
    round-trip (ledger -> tracker -> pnl) is unaffected.
    """
    events, stats = parse_claude_session(
        path, include_sidechain=include_sidechain)
    tracker = events_to_tracker(agent_name, events)
    ledger = ledger_from_tracker(tracker)
    ledger["claude_import_stats"] = stats
    return ledger


# Backwards-friendly alias: the format name in the CLI is "claude".
load_claude_code = load_claude
