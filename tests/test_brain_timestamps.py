#!/usr/bin/env python3
"""
Every brain write path, executed against a real database.

The timestamp work (0.5) changed seven SQL statements from datetime('now') to a
bound RFC 3339 parameter. A statement that compiles can still be wrong: a
placeholder count that does not match the parameter tuple fails at execute time,
and a mismatched-format value sorts wrongly without raising. Neither shows up in
a syntax check, so these tests call the real methods and then read the stored
value back.

The second half asserts the format of what actually landed in each column, which
is the property the change was for.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_brain_timestamps.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.util.timeutil import is_rfc3339, to_iso, utc_now_iso  # noqa: E402
from brain.limbic.somatic import SomaticMarkerEngine  # noqa: E402
from brain.epistemology.defeater_graph import DefeaterGraph  # noqa: E402
from brain.social.tom import TheoryOfMind  # noqa: E402
from brain.dmn.counterfactual import CounterfactualEngine  # noqa: E402
from brain.epistemology.agm import AGMBeliefRevision  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")


def fresh_db():
    tmp = tempfile.mkdtemp(prefix="ts-")
    db = os.path.join(tmp, "brain.db")
    with open(SCHEMA, encoding="utf-8") as fh:
        sqlite3.connect(db).executescript(fh.read())
    return db, tmp


def one(db, sql, *params):
    con = sqlite3.connect(db)
    try:
        row = con.execute(sql, params).fetchone()
        con.commit()
        return row
    finally:
        con.close()


class TestTimeUtil(unittest.TestCase):
    def test_utc_now_is_rfc3339(self):
        self.assertTrue(is_rfc3339(utc_now_iso()), utc_now_iso())

    def test_rejects_the_space_separated_form(self):
        """The whole point. datetime('now') output must fail the check, or the
        check proves nothing."""
        self.assertFalse(is_rfc3339("2026-09-26 12:15:16"))
        self.assertFalse(is_rfc3339("2026-09-26T12:15:16+00:00"))
        self.assertFalse(is_rfc3339(""))
        self.assertFalse(is_rfc3339(None))  # type: ignore[arg-type]

    def test_naive_datetime_is_treated_as_utc(self):
        """Assuming local would make the same wall-clock reading store different
        strings depending on where the process runs, which defeats ordering."""
        from datetime import datetime
        self.assertEqual(to_iso(datetime(2026, 9, 26, 12, 15, 16)), "2026-09-26T12:15:16Z")

    def test_aware_datetime_is_converted_not_relabelled(self):
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=5))
        self.assertEqual(to_iso(datetime(2026, 9, 26, 17, 15, 16, tzinfo=tz)),
                         "2026-09-26T12:15:16Z")

    def test_generated_timestamps_sort_chronologically(self):
        """Ordering is what mixed formats break, so assert the ordering directly
        rather than trusting the format check."""
        from datetime import datetime, timedelta
        base = datetime(2026, 9, 26, 12, 0, 0)
        stamps = [to_iso(base + timedelta(seconds=i * 7)) for i in range(40)]
        self.assertEqual(sorted(stamps), stamps)
        self.assertNotIn(" ", stamps[0])


class TestEveryWritePathExecutes(unittest.TestCase):
    """Placeholder counts that do not match the parameter tuple raise here and
    nowhere else."""

    def setUp(self):
        self.db, self.tmp = fresh_db()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_somatic_update_path(self):
        sm = SomaticMarkerEngine(db_path=self.db)
        sm.record_experience("reach", "door", True, 0.4)
        sm.record_experience("reach", "door", False, 0.6)  # UPDATE branch
        sm.record_experience("reach", "window", True, 0.2)  # INSERT branch
        rows = one(self.db,
                   "SELECT last_experienced FROM somatic_markers WHERE action_pattern=?",
                   "reach")
        self.assertIsNotNone(rows)

    def test_somatic_timestamps_are_rfc3339(self):
        SomaticMarkerEngine(db_path=self.db).record_experience("reach", "door", True, 0.4)
        for (ts,) in sqlite3.connect(self.db).execute(
                "SELECT last_experienced FROM somatic_markers"):
            self.assertTrue(is_rfc3339(ts), f"somatic last_experienced is {ts!r}")

    def test_defeater_belief_insert(self):
        dg = DefeaterGraph(db_path=self.db)
        bid = dg.add_belief("graph", "the graph is faster", 0.7, source_location="test:ts")
        self.assertIsInstance(bid, int)
        for ts in one(self.db, "SELECT created_at, updated_at FROM cognitive_beliefs "
                              "WHERE id=?", bid):
            self.assertTrue(is_rfc3339(ts), f"belief timestamp is {ts!r}")

    def test_defeater_insert_and_reassignment(self):
        dg = DefeaterGraph(db_path=self.db)
        a = dg.add_belief("t", "A is true", 0.8, source_location="test:ts")
        b = dg.add_belief("t", "B is true", 0.4, source_location="test:ts")
        dg.add_defeater(a, b, "rebutting", "they conflict")
        created = one(self.db, "SELECT created_at FROM cognitive_defeaters "
                              "WHERE target_belief_id=?", a)[0]
        updated = one(self.db, "SELECT updated_at FROM cognitive_beliefs "
                              "WHERE id=?", a)[0]
        self.assertTrue(is_rfc3339(created), f"defeater created_at is {created!r}")
        self.assertTrue(is_rfc3339(updated), f"belief updated_at is {updated!r}")

    def test_tom_mental_model(self):
        tom = TheoryOfMind(db_path=self.db)
        tom.update_model("the plan", "I said Monday", "Tuesday")
        ts = one(self.db, "SELECT last_verified FROM user_mental_models")[0]
        self.assertTrue(is_rfc3339(ts), f"user_mental_models last_verified is {ts!r}")

    def test_counterfactual_rollout(self):
        CounterfactualEngine(db_path=self.db).analyze_regret(
            trigger_event="shipped on main", actual_path="main",
            counterfactual_path="branch", predicted_advantage="safer",
            lesson_extracted="use a branch")
        ts = one(self.db, "SELECT created_at FROM counterfactual_rollouts")[0]
        self.assertTrue(is_rfc3339(ts), f"counterfactual created_at is {ts!r}")

    def test_agm_is_in_memory_and_writes_no_timestamps(self):
        """AGMBeliefRevision holds a plain dict and takes no db_path, so it
        writes nothing and has no timestamp to be in the wrong format. Asserted
        so a future change adding persistence also adds a format check."""
        agm = AGMBeliefRevision()
        result = agm.revise("k1", "A holds", ["A does not hold"], 0.7)
        self.assertEqual([b["key"] for b in agm.list_beliefs()], ["k1"])
        self.assertIsNotNone(result)
        tables = {r[0] for r in sqlite3.connect(self.db).execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("belief_revisions", tables)

class TestNoMixedFormatsRemain(unittest.TestCase):
    """Sweep the whole schema's timestamp columns after exercising them."""

    def setUp(self):
        self.db, self.tmp = fresh_db()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_timestamp_column_holds_a_space_separated_value(self):
        sm = SomaticMarkerEngine(db_path=self.db)
        sm.record_experience("a", "b", True, 0.1)
        sm.record_experience("a", "b", False, 0.2)
        dg = DefeaterGraph(db_path=self.db)
        x = dg.add_belief("t", "one", 0.5, source_location="test:sweep")
        y = dg.add_belief("t", "two", 0.5, source_location="test:sweep")
        dg.add_defeater(x, y, "undercutting", "no")
        TheoryOfMind(db_path=self.db).update_model("d", "a", "b")
        CounterfactualEngine(db_path=self.db).analyze_regret(
            "e", "a", "b", "c", "d")
        AGMBeliefRevision().revise("k", "p", ["q"], 0.5)

        con = sqlite3.connect(self.db)
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")]
            for t in tables:
                cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")
                        if r[1].endswith(("_at", "_verified", "_time"))]
                for c in cols:
                    # Nothing written to this column in this test, so there is
                    # no format to check. Query for the offending value, not for
                    # a row that may not exist.
                    bad = con.execute(
                        f"SELECT {c} FROM {t} WHERE {c} IS NOT NULL "
                        f"AND {c} NOT LIKE '%T%' LIMIT 1").fetchone()
                    self.assertIsNone(
                        bad, f"{t}.{c} holds a non-RFC3331 value: {bad[0]!r}"
                             if bad else "")
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
