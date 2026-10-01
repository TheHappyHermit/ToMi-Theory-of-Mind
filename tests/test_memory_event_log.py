"""Tests for scripts/memory_event_log.py.

The failure this guards against is specific and documented: Honcho #1236 burns
queued work after ~90s of upstream unavailability and has no recovery path, so a
replay-safe log is the only mitigation. These tests therefore care most about
idempotency and about never refusing to read a damaged log.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import memory_event_log as mel  # noqa: E402


class TestIngestionId(unittest.TestCase):
    def test_deterministic_for_same_logical_event(self):
        a = mel.make_ingestion_id("ws", "p", "user", "hello")
        b = mel.make_ingestion_id("ws", "p", "user", "hello")
        self.assertEqual(a, b, "re-appending the same event must be recognisable")

    def test_differs_on_any_field(self):
        base = mel.make_ingestion_id("ws", "p", "user", "hello")
        self.assertNotEqual(base, mel.make_ingestion_id("ws2", "p", "user", "hello"))
        self.assertNotEqual(base, mel.make_ingestion_id("ws", "p2", "user", "hello"))
        self.assertNotEqual(base, mel.make_ingestion_id("ws", "p", "user", "hello2"))

    def test_contains_no_field_separator_collision(self):
        # A naive "ws|p|role|text" join would let these collide.
        a = mel.make_ingestion_id("a|b", "c", "user", "t")
        b = mel.make_ingestion_id("a", "b|c", "user", "t")
        self.assertNotEqual(a, b, "separator must not allow field-boundary collisions")


class TestAppendOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _ev(self, text="hello", ws="ws", peer="p", role="user"):
        return mel.build_event(ws, peer, role, text)

    def test_creates_parent_directory(self):
        nested = self.log.parent / "a" / "b" / "events.jsonl"
        self.assertTrue(mel.append_event(nested, self._ev()))
        self.assertTrue(nested.exists())

    def test_duplicate_is_a_noop(self):
        ev = self._ev()
        self.assertTrue(mel.append_event(self.log, ev))
        self.assertFalse(mel.append_event(self.log, self._ev()),
                         "same logical event must not be written twice")
        self.assertEqual(len(list(mel.read_events(self.log))), 1)

    def test_distinct_events_both_persist(self):
        mel.append_event(self.log, self._ev("one"))
        mel.append_event(self.log, self._ev("two"))
        self.assertEqual(len(list(mel.read_events(self.log))), 2)

    def test_line_is_valid_json_with_required_fields(self):
        mel.append_event(self.log, self._ev())
        raw = self.log.read_text().strip().split("\n")
        rec = json.loads(raw[0])
        for key in ("schema_version", "event_id", "ingestion_id",
                    "recorded_at", "workspace", "peer", "role", "text", "derived"):
            self.assertIn(key, rec)

    def test_timestamp_is_rfc3339_utc(self):
        import re
        mel.append_event(self.log, self._ev())
        rec = json.loads(self.log.read_text().strip())
        self.assertRegex(rec["recorded_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_new_events_default_to_not_derived(self):
        mel.append_event(self.log, self._ev())
        rec = json.loads(self.log.read_text().strip())
        self.assertFalse(rec["derived"],
                         "an event is unproven until a reconciler says otherwise")


class TestDamagedLogRecovery(unittest.TestCase):
    """A hard kill mid-write leaves a torn final line. Reading must still work."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_torn_final_line_is_skipped_not_fatal(self):
        good = mel.build_event("ws", "p", "user", "intact")
        mel.append_event(self.log, good)
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write('{"ingestion_id":"abc","text":"torn')  # no newline, no close
        events = list(mel.read_events(self.log))
        self.assertEqual(len(events), 1, "intact events must still be readable")
        self.assertEqual(events[0]["text"], "intact")

    def test_blank_lines_ignored(self):
        mel.append_event(self.log, mel.build_event("ws", "p", "user", "x"))
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("\n\n")
        self.assertEqual(len(list(mel.read_events(self.log))), 1)

    def test_missing_file_reads_as_empty(self):
        self.assertEqual(list(mel.read_events(self.log)), [])


class TestReconcileExitCode(unittest.TestCase):
    """Exit code is the contract: a cron job keys off it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_exit_1_when_nothing_confirmed_derived(self):
        mel.append_event(self.log, mel.build_event("ws", "p", "user", "a"))
        code = mel.main(["--log", str(self.log), "reconcile"])
        self.assertEqual(code, 1, "unconfirmed derivation must not report success")

    def test_exit_0_once_all_derived(self):
        ev = mel.build_event("ws", "p", "user", "a")
        ev["derived"] = True
        mel.append_event(self.log, ev)
        self.assertEqual(mel.main(["--log", str(self.log), "reconcile"]), 0)

    def test_exit_0_on_empty_log(self):
        self.assertEqual(mel.main(["--log", str(self.log), "reconcile"]), 0)

    def test_export_round_trips(self):
        mel.append_event(self.log, mel.build_event("ws", "p", "user", "a"))
        mel.append_event(self.log, mel.build_event("ws", "p", "assistant", "b"))
        out = Path(self.tmp.name) / "export.jsonl"
        self.assertEqual(mel.main(["--log", str(self.log), "export", "--out", str(out)]), 0)
        rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["role"] for r in rows}, {"user", "assistant"})


if __name__ == "__main__":
    unittest.main()
