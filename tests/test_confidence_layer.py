#!/usr/bin/env python3
"""
Tests for the confidence layer.

The layer's value is entirely in what it REFUSES. A confidence that can be
emitted without evidence, without a mechanism, or by averaging a disagreement
into a middle number is a number that looks like a measurement and is not one.

So the tests are weighted toward the refusals. Each says in its name what must
not be possible.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_confidence_layer.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.cortex.confidence import (  # noqa: E402
    Claim,
    ConfidenceError,
    ConfidenceLayer,
)
from brain.cortex.observation_log import ObservationLog  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")


def fresh():
    tmp = tempfile.mkdtemp(prefix="conf-")
    db = os.path.join(tmp, "brain.db")
    with open(SCHEMA, encoding="utf-8") as fh:
        sqlite3.connect(db).executescript(fh.read())
    return db, tmp


def retrieval(db, session="s1", n=1):
    """Write n retrievals and return their ids."""
    log = ObservationLog(db)
    return [log.log_retrieval(session_id=session, query=f"query {i}",
                              strategy="keyword", doc_id=f"doc/{i}.md",
                              rank_position=i, score=1.0 / (i + 1),
                              was_selected=True, latency_ms=1)
            for i in range(n)]


class TestRule1MechanismIsNamed(unittest.TestCase):
    """The subsystem names itself. The layer must never guess."""

    def test_claim_without_a_mechanism_is_refused(self):
        with self.assertRaises(ConfidenceError) as cm:
            Claim("the graph is faster", 0.8, mechanism="")
        self.assertIn("mechanism", str(cm.exception))

    def test_whitespace_mechanism_is_refused(self):
        with self.assertRaises(ConfidenceError):
            Claim("the graph is faster", 0.8, mechanism="   ")

    def test_mechanism_is_preserved_verbatim(self):
        c = Claim("x", 0.5, mechanism="retriever.bm25", evidence_ids=[1])
        self.assertEqual(c.mechanism, "retriever.bm25")


class TestRule2ConfidenceIsPerClaim(unittest.TestCase):
    """A paragraph is three confidences, not one."""

    def test_each_claim_keeps_its_own_value(self):
        c1 = Claim("part one is well supported", 0.95, "retriever.keyword", [1])
        c2 = Claim("part two is a guess", 0.2, "inference", [1])
        self.assertAlmostEqual(c1.confidence, 0.95)
        self.assertAlmostEqual(c2.confidence, 0.2)
        self.assertNotAlmostEqual(c1.confidence, c2.confidence)

    def test_values_outside_the_unit_interval_are_refused(self):
        for bad in (-0.1, 1.1, 2.0, -1):
            with self.subTest(bad=bad):
                with self.assertRaises(ConfidenceError):
                    Claim("x", bad, "retriever.keyword", [1])

    def test_a_boolean_is_not_a_confidence(self):
        """True would silently become 1.0, the most confident value there is,
        from something that was never a measurement."""
        for bad in (True, False):
            with self.subTest(bad=bad):
                with self.assertRaises(ConfidenceError):
                    Claim("x", bad, "retriever.keyword", [1])

    def test_a_string_is_not_a_confidence(self):
        with self.assertRaises(ConfidenceError):
            Claim("x", "0.8", "retriever.keyword", [1])  # type: ignore[arg-type]

    def test_empty_claim_text_is_refused(self):
        with self.assertRaises(ConfidenceError):
            Claim("   ", 0.5, "retriever.keyword", [1])


class TestRule3NoEvidenceNoConfidence(unittest.TestCase):
    """A confidence with no provenance is a vibe."""

    def setUp(self):
        self.db, self.tmp = fresh()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_claim_without_evidence_is_refused(self):
        with self.assertRaises(ConfidenceError) as cm:
            Claim("something plausible", 0.9, "inference", evidence_ids=[])
        msg = str(cm.exception).lower()
        self.assertIn("no evidence", msg)
        self.assertIn("calibrat", msg,
                      "the error should say what an unevidenced confidence costs")

    def test_claim_with_none_evidence_is_refused(self):
        with self.assertRaises(ConfidenceError):
            Claim("something plausible", 0.9, "inference", evidence_ids=None)

    def test_evidence_that_was_never_retrieved_is_refused(self):
        """The subtler version: ids that look real but are not. Catching it
        here names the claim, rather than leaving it to surface as an
        unexplainable calibration result."""
        layer = ConfidenceLayer(self.db)
        good = retrieval(self.db)
        with self.assertRaises(ConfidenceError) as cm:
            layer.emit(Claim("x", 0.9, "retriever.keyword", [good[0], 999_999]), "s1")
        self.assertIn("999999", str(cm.exception).replace(",", ""))

    def test_a_refused_claim_is_not_written(self):
        layer = ConfidenceLayer(self.db)
        before = sqlite3.connect(self.db).execute(
            "SELECT COUNT(*) FROM confidence_log").fetchone()[0]
        with self.assertRaises(ConfidenceError):
            layer.emit(Claim("x", 0.9, "retriever.keyword", [999_999]), "s1")
        after = sqlite3.connect(self.db).execute(
            "SELECT COUNT(*) FROM confidence_log").fetchone()[0]
        self.assertEqual(before, after, "a refused claim was still recorded")

    def test_verification_returns_the_ids_when_present(self):
        layer = ConfidenceLayer(self.db)
        ids = retrieval(self.db, n=3)
        self.assertEqual(layer.verify_evidence(ids), ids)

    def test_empty_evidence_list_fails_verification(self):
        layer = ConfidenceLayer(self.db)
        with self.assertRaises(ConfidenceError):
            layer.verify_evidence([])

    def test_without_a_database_evidence_cannot_be_verified(self):
        """Passing ids through unverified would be the exact failure rule 3
        exists to prevent, wearing a different hat."""
        layer = ConfidenceLayer(None)
        with self.assertRaises(ConfidenceError) as cm:
            layer.verify_evidence([1])
        self.assertIn("no database", str(cm.exception))


class TestRule4NoAveragedDisagreement(unittest.TestCase):
    """Two sources that conflict produce two confidences, never a middle."""

    def setUp(self):
        self.db, self.tmp = fresh()
        self.layer = ConfidenceLayer(self.db)
        self.rid = retrieval(self.db, n=1)[0]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_both_are_recorded_separately(self):
        ids = self.layer.emit_disagreement([
            Claim("the graph is faster", 0.9, "retriever", [self.rid]),
            Claim("the graph is slower", 0.1, "inference", [self.rid]),
        ], "s1")
        self.assertEqual(len(ids), 2)
        rows = sqlite3.connect(self.db).execute(
            "SELECT confidence, mechanism FROM confidence_log ORDER BY id").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual({r[0] for r in rows}, {0.9, 0.1},
                         "a middle value appeared; the disagreement was averaged")
        self.assertEqual(len({r[1] for r in rows}), 2, "both mechanisms must survive")

    def test_a_single_claim_is_not_a_disagreement(self):
        with self.assertRaises(ConfidenceError):
            self.layer.emit_disagreement(
                [Claim("x", 0.5, "retriever.keyword", [self.rid])], "s1")

    def test_duplicate_claims_are_not_a_disagreement(self):
        with self.assertRaises(ConfidenceError) as cm:
            self.layer.emit_disagreement([
                Claim("same", 0.5, "retriever.keyword", [self.rid]),
                Claim("same", 0.5, "retriever.keyword", [self.rid]),
            ], "s1")
        self.assertIn("identical", str(cm.exception))


class TestEmission(unittest.TestCase):
    def setUp(self):
        self.db, self.tmp = fresh()
        self.layer = ConfidenceLayer(self.db)
        self.rid = retrieval(self.db, n=2)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_valid_claim_is_recorded_and_returns_an_id(self):
        cid = self.layer.emit(Claim("supported", 0.8, "retriever", [self.rid[0]]), "s1")
        self.assertIsInstance(cid, int)
        row = sqlite3.connect(self.db).execute(
            "SELECT claim, confidence, mechanism, was_correct FROM confidence_log "
            "WHERE id=?", (cid,)).fetchone()
        self.assertEqual(row[0], "supported")
        self.assertAlmostEqual(row[1], 0.8)
        self.assertEqual(row[2], "retriever")
        self.assertIsNone(row[3], "was_correct must start null, not defaulted")

    def test_emit_many_records_all_of_them(self):
        ids = self.layer.emit_many([
            Claim("first", 0.9, "a", [self.rid[0]]),
            Claim("second", 0.4, "b", [self.rid[1]]),
            Claim("third", 0.6, "c", [self.rid[0]]),
        ], "s1")
        self.assertEqual(len(ids), 3)

    def test_emit_many_refuses_an_empty_list(self):
        """An empty result is a missing answer, not a set of high
        confidences, and returning [] invites the two being confused."""
        with self.assertRaises(ConfidenceError):
            self.layer.emit_many([], "s1")

    def test_a_later_bad_claim_writes_nothing_at_all(self):
        """Partial emission leaves the caller unable to tell which claim went
        unrecorded, and a missing confidence silently becomes an unexamined
        one."""
        with self.assertRaises(ConfidenceError):
            self.layer.emit_many([
                Claim("good", 0.8, "a", [self.rid[0]]),
                Claim("bad", 0.8, "a", [999_999]),
            ], "s1")
        count = sqlite3.connect(self.db).execute(
            "SELECT COUNT(*) FROM confidence_log").fetchone()[0]
        self.assertEqual(count, 0, "a claim was recorded despite the batch failing")

    def test_session_id_is_required(self):
        with self.assertRaises(ConfidenceError):
            self.layer.emit(Claim("x", 0.5, "a", [self.rid[0]]), "")

    def test_without_a_database_nothing_is_emitted(self):
        layer = ConfidenceLayer(None)
        with self.assertRaises(ConfidenceError) as cm:
            layer.emit(Claim("x", 0.5, "a", [1]), "s1")
        self.assertIn("no database", str(cm.exception))

    def test_a_long_evidence_list_is_chunked_not_rejected(self):
        """SQLite caps bound variables. A 600-id claim must verify, not fail on
        a limit the caller cannot see."""
        ids = retrieval(self.db, n=600)
        layer = ConfidenceLayer(self.db)
        self.assertEqual(len(layer.verify_evidence(ids)), 600)


class TestOutcomes(unittest.TestCase):
    def setUp(self):
        self.db, self.tmp = fresh()
        self.layer = ConfidenceLayer(self.db)
        self.rid = retrieval(self.db)[0]
        self.cid = self.layer.emit(Claim("checkable", 0.85, "a", [self.rid]), "s1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_an_outcome_can_be_recorded_once(self):
        self.layer.record_outcome(self.cid, True)
        row = sqlite3.connect(self.db).execute(
            "SELECT was_correct, confidence FROM confidence_log WHERE id=?",
            (self.cid,)).fetchone()
        self.assertEqual(row[0], 1)
        self.assertAlmostEqual(row[1], 0.85, msg="the emitted value must not change")

    def test_a_second_outcome_is_refused(self):
        """Otherwise a later, more convenient answer overwrites the first and
        the log stops describing what happened."""
        self.layer.record_outcome(self.cid, True)
        with self.assertRaises(ConfidenceError):
            self.layer.record_outcome(self.cid, False)

    def test_an_outcome_for_an_unknown_row_is_refused(self):
        with self.assertRaises(ConfidenceError):
            self.layer.record_outcome(999_999, True)

    def test_uncorrected_lists_what_calibration_has_not_seen(self):
        pending = self.layer.get_uncorrected()
        self.assertEqual([p["id"] for p in pending], [self.cid])
        self.layer.record_outcome(self.cid, True)
        self.assertEqual(self.layer.get_uncorrected(), [])

    def test_observed_at_is_rfc3339(self):
        from brain.util.timeutil import is_rfc3339
        (ts,) = sqlite3.connect(self.db).execute(
            "SELECT observed_at FROM confidence_log WHERE id=?", (self.cid,)).fetchone()
        self.assertTrue(is_rfc3339(ts), f"observed_at is {ts!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
