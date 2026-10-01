"""Importer tests: each importer against its fixture, plus validation tests.

Run from the repo root:  python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentpnl.importers import otel, langsmith, jsonl
from agentpnl.importers.common import (
    events_to_tracker, ledger_from_tracker, tracker_from_ledger,
)

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _pnl(ledger):
    return tracker_from_ledger(ledger).pnl()


class TestOtelImporter(unittest.TestCase):
    def test_otel_fixture(self):
        ledger = otel.load_otel(os.path.join(FIX, "otel_spans.json"))
        self.assertEqual(len(ledger["attempts"]), 3)
        self.assertEqual(ledger["attempts"][0]["case_id"], "trace-a")
        self.assertEqual(ledger["attempts"][1]["case_id"], "trace-b")
        self.assertEqual(ledger["attempts"][2]["case_id"], "trace-c")

        tracker = tracker_from_ledger(ledger)
        p = tracker.pnl()
        self.assertEqual(p["attempts"], 3)
        self.assertEqual(p["successes"], 2)
        self.assertGreater(p["cost_total"], 0)

        failed = [a for a in tracker.attempts if not a["success"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["case_id"], "trace-c")

        # retry + escalation exercised on trace-b
        b = [a for a in tracker.attempts if a["case_id"] == "trace-b"][0]
        self.assertEqual(b["retries"], 1)
        self.assertEqual(b["human_min"], 5)

        # unpriced model (mistral-large-2407) got the documented fallback:
        # its cost is attributed under the guessed provider key
        self.assertGreater(
            p["per_model"].get("unknown:mistral-large-2407", 0), 0)

    def test_otel_accepts_bare_list(self):
        path = os.path.join(FIX, "otel_spans.json")
        with open(path) as f:
            data = json.load(f)
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as tmp:
            json.dump(data["spans"], tmp)
        try:
            ledger = otel.load_otel(tmp.name)
        finally:
            os.unlink(tmp.name)
        self.assertEqual(len(ledger["attempts"]), 3)


class TestLangsmithImporter(unittest.TestCase):
    def test_langsmith_fixture(self):
        ledger = langsmith.load_langsmith(os.path.join(FIX, "langsmith_runs.json"))
        self.assertEqual(len(ledger["attempts"]), 3)

        tracker = tracker_from_ledger(ledger)
        p = tracker.pnl()
        self.assertEqual(p["attempts"], 3)
        self.assertEqual(p["successes"], 2)
        self.assertGreater(p["cost_total"], 0)

        failed = [a for a in tracker.attempts if not a["success"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["case_id"], "trace-3")

        # retry + escalation markers on trace-2
        t2 = [a for a in tracker.attempts if a["case_id"] == "trace-2"][0]
        self.assertEqual(t2["retries"], 1)
        self.assertEqual(t2["human_min"], 8)
        # two llm calls costed under the right provider key
        self.assertGreater(p["per_model"].get("anthropic:claude-haiku-4-5", 0), 0)


class TestJsonlImporter(unittest.TestCase):
    def test_jsonl_fixture(self):
        ledger = jsonl.load_jsonl(os.path.join(FIX, "events.jsonl"))
        tracker = tracker_from_ledger(ledger)
        p = tracker.pnl()
        self.assertEqual(p["attempts"], 3)
        self.assertEqual(p["successes"], 2)
        self.assertGreater(p["cost_total"], 0)

        failed = [a for a in tracker.attempts if not a["success"]]
        self.assertEqual(len(failed), 1)
        # case-3 has no end event: auto-ended as failed; the unknown model
        # was costed at the fallback estimate (visible in per_model)
        self.assertEqual(failed[0]["case_id"], "case-3")
        self.assertGreater(p["per_model"].get("unknown:command-r", 0), 0)

        case2 = [a for a in tracker.attempts if a["case_id"] == "case-2"][0]
        self.assertEqual(case2["retries"], 1)
        self.assertEqual(case2["human_min"], 10)
        self.assertEqual(case2["business_value"], 8.0)

    def test_jsonl_invalid_lines_raise(self):
        bad = [
            '{"type": "model", "case_id": "x"}',                       # missing model
            '{"type": "bogus", "case_id": "x"}',                       # unknown type
            '{"type": "end", "case_id": "x", "success": 1}',           # bool required
            '{"type": "tool", "case_id": "x", "name": "t", "cost": -1}',  # >= 0
            '{"type": "retry", "case_id": "x", "bogus_key": 1}',       # unknown key
            'not json at all',
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                         delete=False) as tmp:
            tmp.write("\n".join(bad) + "\n")
        try:
            with self.assertRaises(ValueError) as ctx:
                jsonl.load_jsonl(tmp.name)
        finally:
            os.unlink(tmp.name)
        self.assertIn("line 1", str(ctx.exception))

    def test_jsonl_invalid_line_number_reported(self):
        lines = [
            '{"type": "start", "case_id": "x"}',
            '{"type": "model", "case_id": "x", "model": "m", "input_tokens": "lots"}',
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                         delete=False) as tmp:
            tmp.write("\n".join(lines) + "\n")
        try:
            with self.assertRaises(ValueError) as ctx:
                jsonl.load_jsonl(tmp.name)
        finally:
            os.unlink(tmp.name)
        self.assertIn("line 2", str(ctx.exception))


class TestCommonRoundtrip(unittest.TestCase):
    def test_ledger_roundtrip_preserves_unpriced_models(self):
        # Estimated model spend must stay flagged after export/import;
        # otherwise reimported ledgers present estimates as exact prices.
        t1 = events_to_tracker("flags", [
            {"type": "model", "case_id": "f1", "model": "mystery-7b",
             "input_tokens": 100, "output_tokens": 50},
            {"type": "end", "case_id": "f1", "success": True},
        ])
        self.assertEqual(t1.pnl()["unpriced_models"], ["unknown:mystery-7b"])
        ledger = ledger_from_tracker(t1)
        self.assertEqual(ledger["unpriced_models"], ["unknown:mystery-7b"])
        t2 = tracker_from_ledger(ledger)
        self.assertEqual(t2.unpriced_models, {"unknown:mystery-7b"})
        self.assertEqual(t2.pnl()["unpriced_models"], ["unknown:mystery-7b"])

    def test_tracker_from_ledger_accepts_legacy_ledger_without_flags(self):
        t2 = tracker_from_ledger({"agent": "old", "attempts": []})
        self.assertEqual(t2.unpriced_models, set())
        self.assertEqual(t2.pnl()["unpriced_models"], [])

    def test_ledger_roundtrip_preserves_pnl(self):
        events = [
            {"type": "model", "case_id": "r1", "provider": "openai",
             "model": "gpt-5-nano", "input_tokens": 1000, "output_tokens": 200},
            {"type": "tool", "case_id": "r1", "name": "web_search"},
            {"type": "end", "case_id": "r1", "success": True,
             "business_value": 3.0},
        ]
        t1 = events_to_tracker("roundtrip", events)
        ledger = ledger_from_tracker(t1)
        t2 = tracker_from_ledger(ledger)
        p1, p2 = t1.pnl(), t2.pnl()
        self.assertEqual(p1["attempts"], p2["attempts"])
        self.assertEqual(p1["successes"], p2["successes"])
        self.assertAlmostEqual(p1["cost_total"], p2["cost_total"])
        self.assertAlmostEqual(p1["business_value"], p2["business_value"])

    def test_unknown_event_type_raises(self):
        with self.assertRaises(ValueError):
            events_to_tracker("x", [{"type": "nope", "case_id": "c"}])

    def test_unpriced_model_fallback_and_collection(self):
        tracker = events_to_tracker("fallback", [
            {"type": "model", "case_id": "f1", "model": "mystery-7b",
             "input_tokens": 1_000_000, "output_tokens": 1_000_000},
            {"type": "end", "case_id": "f1", "success": True},
        ])
        p = tracker.pnl()
        # (1.00, 3.00) USD per 1M in/out tokens
        self.assertAlmostEqual(p["cost_model"], 4.0)
        self.assertEqual(p["unpriced_models"], ["unknown:mystery-7b"])
        self.assertEqual(tracker.unpriced_models, {"unknown:mystery-7b"})

    def test_provider_guess_from_model_name(self):
        tracker = events_to_tracker("guess", [
            {"type": "model", "case_id": "g1", "model": "claude-mystery",
             "input_tokens": 100, "output_tokens": 50},
            {"type": "end", "case_id": "g1", "success": True},
        ])
        p = tracker.pnl()
        self.assertEqual(p["unpriced_models"], ["anthropic:claude-mystery"])


if __name__ == "__main__":
    unittest.main()
