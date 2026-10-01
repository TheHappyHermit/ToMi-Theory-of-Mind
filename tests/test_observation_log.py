#!/usr/bin/env python3
"""
Tests for brain.cortex.observation_log.

These assert the POLICY, not the current behaviour. A test that only checks the
writer stores what it was given would pass just as happily against a writer that
silently drops rows, which is the failure this module exists to prevent.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_observation_log.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.cortex.observation_log import (  # noqa: E402
    LogWriteError,
    ObservationLog,
    utc_now,
    VALID_STRATEGIES,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")


class LogTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="obslg-")
        self.db = os.path.join(self.tmp, "brain.db")
        with open(SCHEMA, encoding="utf-8") as fh:
            sqlite3.connect(self.db).executescript(fh.read())
        self.log = ObservationLog(self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def count(self, table):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            con.close()


class TestTimestampFormat(LogTestBase):
    """RFC 3339 UTC, and only that, in both tables."""

    def test_utc_now_shape(self):
        ts = utc_now()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                         "timestamp must be YYYY-MM-DDTHH:MM:SSZ")

    def test_both_tables_use_the_same_format(self):
        """Two formats in one column silently break sorting and indexes. A
        timestamp written by one table must be readable by the other's index."""
        self.log.log_retrieval(session_id="s", query="q", strategy="keyword",
                               doc_id="d1", source_path="/tmp/d1.md")
        self.log.log_confidence(session_id="s", claim="c", confidence=0.5,
                                mechanism="router", evidence_ids=[1])
        con = sqlite3.connect(self.db)
        try:
            for table in ("retrieval_log", "confidence_log"):
                rows = con.execute(
                    f"SELECT observed_at FROM {table}").fetchall()
                self.assertTrue(rows, f"{table} should have a row")
                for (ts,) in rows:
                    self.assertRegex(
                        ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                        f"{table}.observed_at is not RFC 3339 UTC: {ts}")
        finally:
            con.close()


class TestFailClosed(LogTestBase):
    """A writer that cannot log must refuse the write, not proceed unlogged."""

    def test_missing_db_path_raises(self):
        log = ObservationLog(None)
        with self.assertRaises(LogWriteError):
            log.log_retrieval(session_id="s", query="q", strategy="keyword", doc_id="d")

    def test_nonexistent_db_raises(self):
        log = ObservationLog(os.path.join(self.tmp, "nope.db"))
        with self.assertRaises(LogWriteError):
            log.log_retrieval(session_id="s", query="q", strategy="keyword", doc_id="d")

    def test_construction_without_db_does_not_raise(self):
        """Constructing must not fail. Only the write may refuse, so a brain
        without a database is still a usable object."""
        ObservationLog(None)  # must not raise

    def test_reads_on_missing_db_return_empty_not_raise(self):
        """Reads are diagnostic and must never take down a cognitive pass."""
        log = ObservationLog(None)
        self.assertEqual(log.recent_retrievals(), [])
        self.assertEqual(log.confidences_for_session("s"), [])


class TestRetrievalLogging(LogTestBase):
    def test_row_is_written(self):
        rid = self.log.log_retrieval(
            session_id="s1", query="what is graph fusion", strategy="graph",
            doc_id="doc-42", source_path="/vault/doc-42.md", rank_position=1,
            score=0.87, was_selected=True, latency_ms=12)
        self.assertIsInstance(rid, int)
        self.assertEqual(self.count("retrieval_log"), 1)

    def test_unknown_strategy_is_rejected(self):
        """A typo'd strategy becomes a category that never appears in the
        history the benchmark is later built from. Fail at write time."""
        for bad in ("keywordish", "", "BM25", "KEYWORD"):
            with self.assertRaises(LogWriteError, msg=f"{bad!r} should be rejected"):
                self.log.log_retrieval(session_id="s", query="q", strategy=bad, doc_id="d")

    def test_all_declared_strategies_accepted(self):
        for i, strat in enumerate(sorted(VALID_STRATEGIES)):
            self.log.log_retrieval(session_id="s", query=f"q{i}", strategy=strat, doc_id=f"d{i}")
        self.assertEqual(self.count("retrieval_log"), len(VALID_STRATEGIES))

    def test_empty_query_rejected(self):
        """A result with nothing to attribute it to is not provenance."""
        with self.assertRaises(LogWriteError):
            self.log.log_retrieval(session_id="s", query="   ", strategy="keyword", doc_id="d")

    def test_empty_doc_id_rejected(self):
        with self.assertRaises(LogWriteError):
            self.log.log_retrieval(session_id="s", query="q", strategy="keyword", doc_id="")

    def test_was_selected_stored_as_integer(self):
        self.log.log_retrieval(session_id="s", query="q", strategy="dense",
                               doc_id="d1", was_selected=True)
        self.log.log_retrieval(session_id="s", query="q", strategy="dense",
                               doc_id="d2", was_selected=False)
        con = sqlite3.connect(self.db)
        try:
            vals = dict(con.execute("SELECT doc_id, was_selected FROM retrieval_log"))
        finally:
            con.close()
        self.assertEqual(vals, {"d1": 1, "d2": 0})


class TestConfidenceLogging(LogTestBase):
    def test_row_is_written_with_null_outcome(self):
        cid = self.log.log_confidence(session_id="s", claim="the graph helps",
                                      confidence=0.7, mechanism="router")
        con = sqlite3.connect(self.db)
        try:
            was = con.execute(
                "SELECT was_correct FROM confidence_log WHERE id = ?", (cid,)).fetchone()[0]
        finally:
            con.close()
        self.assertIsNone(was, "was_correct must start null, not 0")

    def test_mechanism_is_required(self):
        """A confidence with no named mechanism cannot be calibrated: there is
        nothing to attribute the error to."""
        for bad in ("", "   ", None):
            with self.assertRaises(LogWriteError):
                self.log.log_confidence(session_id="s", claim="c", confidence=0.5,
                                        mechanism=bad)

    def test_confidence_bounds_enforced(self):
        for bad in (-0.1, 1.1, 2.0, -1.0):
            with self.assertRaises(LogWriteError):
                self.log.log_confidence(session_id="s", claim="c", confidence=bad,
                                        mechanism="router")

    def test_bounds_accepted(self):
        for good in (0.0, 1.0, 0.5):
            self.log.log_confidence(session_id="s", claim=f"c{good}", confidence=good,
                                    mechanism="router")
        self.assertEqual(self.count("confidence_log"), 3)

    def test_empty_claim_rejected(self):
        with self.assertRaises(LogWriteError):
            self.log.log_confidence(session_id="s", claim="  ", confidence=0.5,
                                    mechanism="router")

    def test_empty_evidence_list_differs_from_absent(self):
        """'no evidence' and 'evidence not yet known' are different claims and
        must not collapse into the same stored value."""
        none_id = self.log.log_confidence(session_id="s", claim="a", confidence=0.5,
                                          mechanism="router")
        empty_id = self.log.log_confidence(session_id="s", claim="b", confidence=0.5,
                                           mechanism="router", evidence_ids=[])
        con = sqlite3.connect(self.db)
        try:
            a = con.execute("SELECT evidence_ids FROM confidence_log WHERE id=?",
                            (none_id,)).fetchone()[0]
            b = con.execute("SELECT evidence_ids FROM confidence_log WHERE id=?",
                            (empty_id,)).fetchone()[0]
        finally:
            con.close()
        self.assertIsNone(a, "absent evidence must store SQL NULL")
        self.assertEqual(b, "[]", "explicitly-empty evidence must store an empty array")

    def test_evidence_ids_are_json_array(self):
        ids = [self.log.log_retrieval(session_id="s", query="q", strategy="graph",
                                      doc_id=f"d{i}") for i in range(3)]
        cid = self.log.log_confidence(session_id="s", claim="c", confidence=0.9,
                                      mechanism="graph", evidence_ids=ids)
        self.assertEqual(self.log.unverified_evidence_count(cid), 0)
        rec = self.log.confidences_for_session("s")[0]
        self.assertEqual(sorted(rec["evidence_ids"]), sorted(ids))

    def test_unverified_evidence_is_detectable(self):
        """A confidence pointing at evidence that was never written is the
        cheapest internal-consistency check there is. It must be findable."""
        cid = self.log.log_confidence(session_id="s", claim="c", confidence=0.9,
                                      mechanism="graph", evidence_ids=[999, 1000])
        self.assertEqual(self.log.unverified_evidence_count(cid), 2)

    def test_outcome_fills_only_was_correct(self):
        cid = self.log.log_confidence(session_id="s", claim="original claim",
                                      confidence=0.4, mechanism="router")
        self.log.record_outcome(cid, was_correct=True)
        con = sqlite3.connect(self.db)
        try:
            row = con.execute(
                "SELECT claim, confidence, mechanism, was_correct "
                "FROM confidence_log WHERE id = ?", (cid,)).fetchone()
        finally:
            con.close()
        self.assertEqual(row[0], "original claim", "claim must not change")
        self.assertEqual(row[1], 0.4, "confidence must not change")
        self.assertEqual(row[2], "router", "mechanism must not change")
        self.assertEqual(row[3], 1, "only was_correct should have been written")


class TestAppendOnly(LogTestBase):
    """There is no update or delete in the writer. This asserts it at the
    interface level: no such method exists to be called by mistake."""

    def test_no_mutating_methods_exposed(self):
        for forbidden in ("update_retrieval", "delete_retrieval",
                          "update_confidence", "delete_confidence", "truncate"):
            self.assertFalse(
                hasattr(self.log, forbidden),
                f"append-only log must not expose {forbidden}")

    def test_repeated_writes_accumulate(self):
        for i in range(5):
            self.log.log_retrieval(session_id="s", query=f"q{i}", strategy="keyword",
                                   doc_id=f"d{i}")
        self.assertEqual(self.count("retrieval_log"), 5)


class TestForeignKeys(LogTestBase):
    def test_fk_pragma_is_enabled_on_write_connections(self):
        """SQLite defaults foreign_keys OFF on every connection, so it is never
        actually on unless set each time. Verify it is genuinely enforced."""
        self.log.log_retrieval(session_id="s", query="q", strategy="keyword", doc_id="d1")
        con = sqlite3.connect(self.db)
        con.execute("PRAGMA foreign_keys=ON")
        try:
            on = con.execute("PRAGMA foreign_keys").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(on, 1, "foreign key enforcement must be available on the db")

    def test_connect_helper_enables_fk(self):
        conn = self.log._connect()
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            conn.close()


class TestReadHelpers(LogTestBase):
    def test_recent_retrievals_newest_first(self):
        for i in range(3):
            self.log.log_retrieval(session_id="s", query=f"q{i}", strategy="keyword",
                                   doc_id=f"d{i}")
        rows = self.log.recent_retrievals(limit=10)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["doc_id"], "d2", "newest first")

    def test_session_filter(self):
        self.log.log_retrieval(session_id="a", query="q", strategy="keyword", doc_id="d1")
        self.log.log_retrieval(session_id="b", query="q", strategy="keyword", doc_id="d2")
        rows = self.log.recent_retrievals(session_id="a")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["doc_id"], "d1")

    def test_limit_is_respected(self):
        for i in range(10):
            self.log.log_retrieval(session_id="s", query=f"q{i}", strategy="keyword",
                                   doc_id=f"d{i}")
        self.assertEqual(len(self.log.recent_retrievals(limit=3)), 3)

    def test_evidence_ids_decoded_on_read(self):
        rid = self.log.log_retrieval(session_id="s", query="q", strategy="graph", doc_id="d")
        self.log.log_confidence(session_id="s", claim="c", confidence=0.5,
                                mechanism="graph", evidence_ids=[rid])
        rec = self.log.confidences_for_session("s")[0]
        self.assertIsInstance(rec["evidence_ids"], list)
        self.assertEqual(rec["evidence_ids"], [rid])


if __name__ == "__main__":
    unittest.main(verbosity=2)
