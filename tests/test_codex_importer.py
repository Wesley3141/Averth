"""Tests for the Codex CLI rollout importer (averth/importers/codex.py).

Run from the repo root:  python3 -m unittest tests.test_codex_importer -v

Fixtures are synthetic records in the documented rollout shapes
(payload-wrapped and flattened), NOT any real person's session.
No test here claims to be a real Codex session: rollout files are
local agent logs, and no real rollout was available to this repo.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from averth.importers import codex
from averth.importers.common import tracker_from_ledger


def _write(lines):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for line in lines:
        if isinstance(line, str):
            tmp.write(line + "\n")
        else:
            tmp.write(json.dumps(line) + "\n")
    tmp.close()
    return tmp.name


def _meta(thread_id="thread-1", source="cli"):
    return {"type": "session_meta",
            "payload": {"id": thread_id, "cwd": "/tmp/shop",
                        "cli_version": "0.130.0", "source": source}}


def _turn(model):
    return {"type": "turn_context", "payload": {"model": model}}


def _tokens(input_tokens, cached, output, reasoning=0):
    return {"type": "event_msg",
            "payload": {"type": "token_count",
                        "info": {"total_token_usage": {
                            "input_tokens": input_tokens,
                            "cached_input_tokens": cached,
                            "output_tokens": output,
                            "reasoning_output_tokens": reasoning}}}}


class CodexImporterTest(unittest.TestCase):
    def test_cumulative_snapshots_become_deltas(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       _tokens(1000, 600, 100, 20),
                       _tokens(3000, 2000, 400, 100)])
        events, stats = codex.parse_codex_rollout(path)
        model_events = [e for e in events if e["type"] == "model"]
        self.assertEqual(len(model_events), 2)
        # First snapshot counts in full.
        self.assertEqual(model_events[0]["input_tokens"], 1000)
        self.assertEqual(model_events[0]["cached_input_tokens"], 600)
        self.assertEqual(model_events[0]["output_tokens"], 120)
        # Second event is the delta, including reasoning as output.
        self.assertEqual(model_events[1]["input_tokens"], 2000)
        self.assertEqual(model_events[1]["cached_input_tokens"], 1400)
        self.assertEqual(model_events[1]["output_tokens"], 380)
        self.assertEqual(stats["token_count_events"], 2)
        self.assertEqual(stats["model_events_emitted"], 2)
        self.assertEqual(stats["reasoning_tokens"], 100)

    def test_deltas_priced_and_outcome_unknown(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       _tokens(1000, 600, 100, 20),
                       _tokens(3000, 2000, 400, 100)])
        ledger = codex.load_codex(path)
        self.assertEqual(len(ledger["attempts"]), 1)
        attempt = ledger["attempts"][0]
        self.assertEqual(attempt["total_tokens"], 3500)
        self.assertEqual(attempt["cached_tokens"], 2000)
        # gpt-5.2: $1.75/$14.00 per 1M, $0.175 cached.
        # Uncached 1000 * 1.75 + cached 2000 * 0.175
        #   + output 500 * 14.00, all per 1M = $0.0091.
        self.assertAlmostEqual(attempt["total_cost"], 0.0091, places=6)
        self.assertAlmostEqual(attempt["cache_savings"], 0.00315, places=6)
        self.assertTrue(attempt["outcome_unknown"])
        self.assertFalse(attempt["success"])
        tracker = tracker_from_ledger(ledger)
        pnl = tracker.pnl()
        self.assertEqual(pnl["unknown_outcome"], 1)
        self.assertEqual(pnl["cost_failed"], 0.0)

    def test_repeated_snapshot_emits_nothing(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       _tokens(1000, 600, 100),
                       _tokens(1000, 600, 100)])
        events, stats = codex.parse_codex_rollout(path)
        model_events = [e for e in events if e["type"] == "model"]
        self.assertEqual(len(model_events), 1)
        self.assertEqual(stats["token_count_events"], 2)

    def test_falling_snapshot_resets_baseline(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       _tokens(3000, 2000, 400),
                       {"type": "compacted", "payload": {}},
                       _tokens(500, 100, 50)])
        events, stats = codex.parse_codex_rollout(path)
        model_events = [e for e in events if e["type"] == "model"]
        self.assertEqual(len(model_events), 2)
        # Post-compaction snapshot counts in full, never negative.
        self.assertEqual(model_events[1]["input_tokens"], 500)
        self.assertEqual(model_events[1]["output_tokens"], 50)
        self.assertEqual(stats["baseline_resets"], 1)

    def test_model_unknown_before_turn_context(self):
        path = _write([_meta(), _tokens(1000, 0, 100),
                       _turn("gpt-5.2"), _tokens(2000, 0, 200)])
        events, stats = codex.parse_codex_rollout(path)
        model_events = [e for e in events if e["type"] == "model"]
        self.assertEqual(model_events[0]["model"], "unknown")
        self.assertEqual(model_events[1]["model"], "gpt-5.2")

    def test_flattened_shape_accepted(self):
        path = _write([
            {"type": "session_meta", "id": "flat-1", "source": "cli"},
            {"type": "turn_context", "model": "gpt-5.2"},
            {"type": "event_msg", "payload": {"type": "token_count",
                "info": {"total_token_usage": {
                    "input_tokens": 100, "cached_input_tokens": 0,
                    "output_tokens": 10, "reasoning_output_tokens": 0}}}},
        ])
        events, stats = codex.parse_codex_rollout(path)
        model_events = [e for e in events if e["type"] == "model"]
        self.assertEqual(len(model_events), 1)
        self.assertEqual(model_events[0]["case_id"], "flat-1")

    def test_subagent_thread_flagged_not_hidden(self):
        path = _write([_meta(source={"subagent": {"other": "guardian"}}),
                       _turn("gpt-5.2"), _tokens(100, 0, 10)])
        events, stats = codex.parse_codex_rollout(path)
        self.assertTrue(stats["subagent_thread"])
        self.assertEqual(len([e for e in events
                              if e["type"] == "model"]), 1)

    def test_tool_records_not_emitted_as_spend(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       {"type": "response_item",
                        "payload": {"type": "function_call",
                                    "name": "exec_command",
                                    "call_id": "call_1"}},
                       {"type": "response_item",
                        "payload": {"type": "function_call_output",
                                    "call_id": "call_1", "output": "ok"}},
                       _tokens(100, 0, 10)])
        events, stats = codex.parse_codex_rollout(path)
        self.assertEqual(len([e for e in events
                              if e["type"] == "model"]), 1)
        self.assertEqual(len([e for e in events
                              if e["type"] == "tool"]), 0)

    def test_directory_raises(self):
        with self.assertRaises(ValueError):
            codex.parse_codex_rollout(tempfile.gettempdir())

    def test_malformed_json_raises_with_line(self):
        path = _write([_meta(), "{not json"])
        with self.assertRaises(ValueError) as ctx:
            codex.parse_codex_rollout(path)
        self.assertIn("line 2", str(ctx.exception))

    def test_negative_token_raises(self):
        path = _write([_meta(), _turn("gpt-5.2"),
                       _tokens(-5, 0, 10)])
        with self.assertRaises(ValueError):
            codex.parse_codex_rollout(path)

    def test_no_events_no_end_fabricated(self):
        path = _write([_meta()])
        events, stats = codex.parse_codex_rollout(path)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
