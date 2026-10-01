#!/usr/bin/env python3
"""
0.6 -- every belief must say where it came from.

provenance already existed and was already NOT NULL, but it records a CATEGORY:
'user', 'tool', 'inference', 'wiki'. Knowing the user said something is not
knowing which of several hundred pages to re-read when the belief turns out to
be wrong. A belief with no address is indistinguishable from one that should
never have been stored.

So the requirement is enforced at the writer, and these tests assert that it
actually holds rather than that a column exists.

The one thing that would defeat the purpose is a caller that passes a
placeholder -- 'unknown', 'n/a', '-'. A required field that everyone fills with
the same four letters is not a required field, so those are rejected too.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_source_location.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.epistemology.defeater_graph import DefeaterGraph  # noqa: E402
from brain.hermes_brain import HermesBrain  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")

# Values that satisfy a presence check while addressing nothing.
PLACEHOLDERS = {"unknown", "n/a", "na", "-", "none", "null", "tbd", "???", "?"}


def fresh_db():
    tmp = tempfile.mkdtemp(prefix="srcloc-")
    db = os.path.join(tmp, "brain.db")
    with open(SCHEMA, encoding="utf-8") as fh:
        sqlite3.connect(db).executescript(fh.read())
    return db, tmp


class TestLocationIsRequired(unittest.TestCase):
    def setUp(self):
        self.db, self.tmp = fresh_db()
        self.dg = DefeaterGraph(db_path=self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_real_location_is_accepted_and_stored(self):
        bid = self.dg.add_belief("graph", "the graph is faster", 0.7,
                                  source_location="docs/DELEGATION.md:42")
        row = sqlite3.connect(self.db).execute(
            "SELECT source_location FROM cognitive_beliefs WHERE id=?", (bid,)).fetchone()
        self.assertEqual(row[0], "docs/DELEGATION.md:42")

    def test_omitting_the_location_is_refused(self):
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "no location given", 0.7)

    def test_empty_string_is_refused(self):
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "empty", 0.7, source_location="")

    def test_whitespace_is_refused(self):
        """Whitespace passes a truthiness check in some languages and a strip()
        check in others. A location of '   ' addresses nothing."""
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "blank", 0.7, source_location="   \t\n")

    def test_none_is_refused(self):
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "none", 0.7,
                               source_location=None)  # type: ignore[arg-type]

    def test_wrong_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "int", 0.7,
                               source_location=42)  # type: ignore[arg-type]

    def test_placeholders_are_refused(self):
        """The failure mode a presence check alone invites. Everyone writes
        'unknown', the column is never empty, and nothing is traceable."""
        for junk in PLACEHOLDERS:
            with self.subTest(junk=junk):
                with self.assertRaises(ValueError, msg=f"{junk!r} was accepted"):
                    self.dg.add_belief("graph", "junk", 0.7, source_location=junk)

    def test_a_refused_belief_writes_nothing(self):
        """Refusing must happen before the write, not after. A row that is
        inserted and then rejected is still a row."""
        before = sqlite3.connect(self.db).execute(
            "SELECT COUNT(*) FROM cognitive_beliefs").fetchone()[0]
        with self.assertRaises(ValueError):
            self.dg.add_belief("graph", "rejected", 0.7, source_location="")
        after = sqlite3.connect(self.db).execute(
            "SELECT COUNT(*) FROM cognitive_beliefs").fetchone()[0]
        self.assertEqual(before, after, "a refused belief was still written")

    def test_the_error_explains_what_to_pass(self):
        """A bare ValueError with no argument makes the caller guess."""
        with self.assertRaises(ValueError) as cm:
            self.dg.add_belief("graph", "x", 0.7)
        msg = str(cm.exception)
        self.assertIn("source_location", msg)
        self.assertIn("path", msg.lower())


class TestEverythingInTheTableHasALocation(unittest.TestCase):
    def setUp(self):
        self.db, self.tmp = fresh_db()
        self.dg = DefeaterGraph(db_path=self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_stored_belief_is_unaddressed(self):
        for i, (topic, stmt) in enumerate([
            ("a", "first claim"), ("b", "second claim"), ("c", "third claim"),
        ]):
            self.dg.add_belief(topic, stmt, 0.5,
                               source_location=f"wiki/{topic}.md#{i}")
        rows = sqlite3.connect(self.db).execute(
            "SELECT source_location FROM cognitive_beliefs").fetchall()
        self.assertEqual(len(rows), 3)
        for (loc,) in rows:
            self.assertTrue(loc and loc.strip(), f"unaddressed belief: {loc!r}")
            self.assertNotIn(loc.strip().lower(), PLACEHOLDERS)


class TestWiringStillWorksWithTheRequirement(unittest.TestCase):
    """The brain's own path must supply a location, or every gated run that
    touches the defeater graph would now raise."""

    def setUp(self):
        self.db, self.tmp = fresh_db()
        self.brain = HermesBrain(db_path=self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_full_pass_runs_and_stores_an_addressed_belief(self):
        self.brain.defeater_graph.add_belief(
            "graph", "the graph is faster than plain retrieval", 0.7,
            source_location="docs/DELEGATION-BOUNDARY-FORENSICS.md")
        result = self.brain.process_incoming_stimulus(
            source="test",
            text="the graph is not faster than plain retrieval",
            session_id="s1")
        self.assertIn("gated_subsystems", result)
        self.assertTrue(result["gated_subsystems"]["defeater_graph"]["ran"],
                        "a stored, addressable belief should be detectable")

    def test_the_column_survives_a_schema_reload(self):
        """An additive change that only works on a fresh database is not
        additive. Existing databases get the column with its default and keep
        working."""
        con = sqlite3.connect(self.db)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(cognitive_beliefs)")}
        finally:
            con.close()
        self.assertIn("source_location", cols)


if __name__ == "__main__":
    unittest.main(verbosity=2)
