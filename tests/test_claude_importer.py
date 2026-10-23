"""Tests for the Claude Code session importer (averth/importers/claude.py).

Run from the repo root:  python3 -m unittest tests.test_claude_importer -v

The documented example record below is the one from POC 6 (public
Claude Code documentation posts, NOT Ken Imoto's session): input 137,
cache_creation 5521, cache_read 815193, output 4260, model
claude-opus-4-6. No test in this file claims to be Imoto's session:
his post publishes session totals only (2,098K tokens over 84 turns),
with no per-turn usage, model, or cache split, so a transcript sample
cannot be constructed from it without inventing his session. This
importer is therefore tested on example records only, not on his
session, and the wave-1 report says so.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from averth.importers import claude
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


def _assistant(msg_id, model="claude-opus-4-6", usage=None, **extra):
    rec = {"type": "assistant", "sessionId": "sess-1",
           "uuid": "line-%s" % msg_id,
           "message": {"id": msg_id, "model": model}}
    if usage is not None:
        rec["message"]["usage"] = usage
    rec.update(extra)
    return rec


# Documented example record from POC 6.
EXAMPLE_USAGE = {"input_tokens": 137,
                 "cache_creation_input_tokens": 5521,
                 "cache_read_input_tokens": 815193,
                 "output_tokens": 4260}


class TestClaudeImporter(unittest.TestCase):
    def test_documented_example_exit_and_cost(self):
        path = _write([_assistant("msg_01", usage=EXAMPLE_USAGE)])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(ledger["attempts"]), 1)
        attempt = ledger["attempts"][0]
        # Total context = 137 + 5521 + 815193 = 820851 input;
        # total tokens = 820851 + 4260 = 825111.
        self.assertEqual(attempt["total_tokens"], 825111)
        # Cached = cache_read only, never capped, never dropped.
        self.assertEqual(attempt["cached_tokens"], 815193)
        # claude-opus-4-6 = 15.00/75.00 per 1M:
        #   (137 + 5521) * 15.00 / 1e6 = 0.08487  (uncached + creation,
        #                                          creation at FULL price)
        #   815193 * 15.00 * 0.10 / 1e6 = 1.2227895 (cache reads)
        #   4260 * 75.00 / 1e6 = 0.3195 (output)
        #   total = 1.6271595, matching POC 6 Test 3 ($1.63 rounded).
        self.assertAlmostEqual(attempt["total_cost"], 1.6271595, places=6)
        # Cache saving at 0.10 discount: 815193 * 15.00 * 0.90 / 1e6.
        self.assertAlmostEqual(attempt["cache_savings"], 11.0051055, places=6)
        # No acceptance label in a transcript: outcome is inferred,
        # so cost per success is UNKNOWN (auto-ended, not a success).
        self.assertTrue(attempt["outcome_inferred"])
        self.assertFalse(attempt["success"])

    def test_cache_creation_is_priced_at_full_not_dropped_or_discounted(self):
        # If creation tokens were dropped, total input would be 815330
        # and cost would be 1.5443295. If creation were priced at the
        # 0.10 cache-read discount, cost would be 1.5527195. The
        # documented choice is full price: 1.6271595.
        path = _write([_assistant("msg_01", usage=EXAMPLE_USAGE)])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        cost = ledger["attempts"][0]["total_cost"]
        self.assertGreater(cost, 1.62)
        self.assertNotAlmostEqual(cost, 1.5443295, places=4)
        self.assertNotAlmostEqual(cost, 1.5527195, places=4)

    def test_cached_greater_than_uncached_does_not_crash_or_cap(self):
        # The original POC 6 failure: cached 815193 >> uncached 137.
        # Total-context mapping makes cached <= total by construction.
        path = _write([_assistant("msg_01", usage=EXAMPLE_USAGE)])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        stats = ledger["claude_import_stats"]
        self.assertEqual(stats["cache_read_tokens"], 815193)
        self.assertEqual(stats["input_tokens_uncached"], 137)
        self.assertEqual(stats["total_context_tokens"], 820851)
        self.assertGreater(stats["total_context_tokens"],
                           stats["cache_read_tokens"])

    def test_duplicate_message_id_is_counted_once(self):
        lines = [
            _assistant("msg_dup", usage=EXAMPLE_USAGE),
            # Same message id, same usage, logged again while streaming.
            _assistant("msg_dup", usage=EXAMPLE_USAGE),
            _assistant("msg_other", usage={"input_tokens": 100,
                                           "output_tokens": 10}),
        ]
        path = _write(lines)
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        stats = ledger["claude_import_stats"]
        self.assertEqual(stats["model_calls_kept"], 2)
        self.assertEqual(stats["duplicates_skipped"], 1)
        # Total tokens: example 825111 + second call 110 = 825221.
        self.assertEqual(ledger["attempts"][0]["total_tokens"], 825221)

    def test_duplicate_growing_output_keeps_per_field_max(self):
        # Real-session defect (Simon Willison session): the same
        # message id is logged twice with output growing 7 -> 402.
        # Keeping the first record undercounted output ~99%; summing
        # would double count. Per-field max gives 402.
        lines = [
            _assistant("msg_grow", usage={"input_tokens": 100,
                                          "output_tokens": 7}),
            _assistant("msg_grow", usage={"input_tokens": 100,
                                          "output_tokens": 402}),
        ]
        path = _write(lines)
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        stats = ledger["claude_import_stats"]
        self.assertEqual(stats["model_calls_kept"], 1)
        self.assertEqual(stats["duplicates_skipped"], 1)
        self.assertEqual(stats["output_tokens"], 402)
        # Total tokens = 100 input + 402 output, not 100 + 7.
        self.assertEqual(ledger["attempts"][0]["total_tokens"], 502)

    def test_no_result_session_is_outcome_unknown_not_failed(self):
        # A session with model calls but no result line records spend
        # with no outcome: it must not be counted as a failed attempt.
        path = _write([_assistant("msg_1", usage={"input_tokens": 100,
                                                 "output_tokens": 10})])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        attempt = ledger["attempts"][0]
        self.assertTrue(attempt["outcome_unknown"])
        self.assertFalse(attempt["success"])
        tracker = tracker_from_ledger(ledger)
        p = tracker.pnl()
        self.assertEqual(p["unknown_outcome"], 1)
        self.assertEqual(p["cost_failed"], 0.0)
        self.assertAlmostEqual(p["cost_unknown_outcome"],
                               attempt["total_cost"])

    def test_no_usage_record_does_not_block_later_duplicate_with_usage(self):
        lines = [
            _assistant("msg_x", usage=None),
            _assistant("msg_x", usage={"input_tokens": 50,
                                       "output_tokens": 5}),
        ]
        path = _write(lines)
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        stats = ledger["claude_import_stats"]
        self.assertEqual(stats["no_usage_skipped"], 1)
        self.assertEqual(stats["model_calls_kept"], 1)
        self.assertEqual(ledger["attempts"][0]["total_tokens"], 55)

    def test_sidechain_excluded_by_default_included_on_request(self):
        main = _assistant("msg_main", usage={"input_tokens": 100,
                                             "output_tokens": 10})
        side = _assistant("msg_side", usage={"input_tokens": 200,
                                             "output_tokens": 20},
                          isSidechain=True)
        path = _write([main, side])
        try:
            default = claude.load_claude(path)
            included = claude.load_claude(path, include_sidechain=True)
        finally:
            os.unlink(path)
        self.assertEqual(
            default["claude_import_stats"]["sidechain_skipped"], 1)
        self.assertEqual(
            default["claude_import_stats"]["model_calls_kept"], 1)
        self.assertEqual(
            included["claude_import_stats"]["model_calls_kept"], 2)
        self.assertEqual(
            included["attempts"][0]["total_tokens"], 110 + 220)

    def test_model_usage_aggregate_is_ignored_not_double_counted(self):
        rec = _assistant("msg_agg", usage={"input_tokens": 100,
                                           "output_tokens": 10})
        # modelUsage aggregates the same call at session level; counting
        # it as well would double the tokens.
        rec["modelUsage"] = {"claude-opus-4-6": {"inputTokens": 999999,
                                                 "outputTokens": 999999}}
        path = _write([rec])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        self.assertEqual(ledger["attempts"][0]["total_tokens"], 110)

    def test_result_line_ends_attempt_but_outcome_stays_inferred(self):
        lines = [
            _assistant("msg_1", usage={"input_tokens": 100,
                                       "output_tokens": 10}),
            {"type": "result", "sessionId": "sess-1", "is_error": False,
             "subtype": "success", "total_cost_usd": 99.99},
        ]
        path = _write(lines)
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        attempt = ledger["attempts"][0]
        self.assertTrue(attempt["success"])
        # Execution completion is not customer acceptance.
        self.assertTrue(attempt["outcome_inferred"])
        # total_cost_usd on the result line is ignored (would double
        # count the per-message usage); the dollars come from usage.
        self.assertLess(attempt["total_cost"], 1.0)

    def test_other_record_types_are_ignored(self):
        lines = [
            {"type": "user", "sessionId": "sess-1",
             "message": {"content": [{"type": "tool_result"}]}},
            {"type": "system", "sessionId": "sess-1"},
            {"type": "file-history-snapshot", "sessionId": "sess-1"},
            _assistant("msg_1", usage={"input_tokens": 10,
                                       "output_tokens": 1}),
        ]
        path = _write(lines)
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        self.assertEqual(
            ledger["claude_import_stats"]["other_lines_skipped"], 3)
        self.assertEqual(len(ledger["attempts"]), 1)

    def test_directory_is_rejected_not_globbed(self):
        with self.assertRaises(ValueError) as ctx:
            claude.load_claude(tempfile.gettempdir())
        self.assertIn("directory", str(ctx.exception))
        self.assertIn("single session", str(ctx.exception))

    def test_malformed_json_names_line(self):
        path = _write(['{"type": "assistant", broken'])
        try:
            with self.assertRaises(ValueError) as ctx:
                claude.load_claude(path)
        finally:
            os.unlink(path)
        self.assertIn("line 1", str(ctx.exception))

    def test_negative_token_names_line(self):
        rec = _assistant("msg_neg", usage={"input_tokens": -5,
                                           "output_tokens": 10})
        path = _write([rec])
        try:
            with self.assertRaises(ValueError) as ctx:
                claude.load_claude(path)
        finally:
            os.unlink(path)
        self.assertIn("line 1", str(ctx.exception))

    def test_fractional_token_rejected_not_truncated(self):
        rec = _assistant("msg_frac", usage={"input_tokens": 100.9,
                                            "output_tokens": 10})
        path = _write([rec])
        try:
            with self.assertRaises(ValueError):
                claude.load_claude(path)
        finally:
            os.unlink(path)

    def test_nested_cache_creation_dict_is_summed(self):
        usage = {"input_tokens": 100,
                 "cache_creation": {"ephemeral_1h_input_tokens": 40,
                                    "ephemeral_5m_input_tokens": 10},
                 "cache_read_input_tokens": 200,
                 "output_tokens": 5}
        path = _write([_assistant("msg_nest", usage=usage)])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        stats = ledger["claude_import_stats"]
        self.assertEqual(stats["cache_creation_tokens"], 50)
        self.assertEqual(stats["total_context_tokens"], 350)

    def test_cli_trace_claude_exit0(self):
        from averth.cli import main
        path = _write([_assistant("msg_cli", usage=EXAMPLE_USAGE)])
        html = tempfile.NamedTemporaryFile("w", suffix=".html",
                                           delete=False)
        html.close()
        try:
            rc = main(["trace", path, "--format", "claude",
                       "--html", html.name])
        finally:
            os.unlink(path)
            os.unlink(html.name)
        self.assertEqual(rc, 0)

    def test_ledger_roundtrip_preserves_attempt(self):
        path = _write([_assistant("msg_rt", usage=EXAMPLE_USAGE)])
        try:
            ledger = claude.load_claude(path)
        finally:
            os.unlink(path)
        tracker = tracker_from_ledger(ledger)
        self.assertEqual(tracker.pnl()["attempts"], 1)
        self.assertAlmostEqual(
            tracker.pnl()["cost_total"], 1.6271595, places=6)


if __name__ == "__main__":
    unittest.main()
