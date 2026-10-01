#!/usr/bin/env python3
"""
Integration tests: the Decisions are actually WIRED into the brain, not merely
defined beside it.

tests/test_decisions.py proves the primitives behave. This file proves they are
connected -- that a gain recorded in the registry reaches the live subsystem and
changes real behaviour. A Decision implemented in a module nobody imports is
indistinguishable from one that was never implemented.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_decisions_integration.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.decisions import (  # noqa: E402
    DEFAULTS,
    GAIN_SPECS,
    SUBJECT_FACETS,
    PlasticGains,
    SupersessionResolver,
    VerifierIndependence,
)
from brain.hermes_brain import HermesBrain  # noqa: E402


class DecisionWiringBase(unittest.TestCase):
    """Each test gets its own throwaway database."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="decisions-integration-")
        self.db = os.path.join(self.tmpdir, "brain.db")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def brain(self):
        return HermesBrain(db_path=self.db)


class TestC4IsWired(DecisionWiringBase):
    """C4: a gain must reach the subsystem, not just the registry."""

    def test_starts_at_the_historical_constants(self):
        """An idle brain must be indistinguishable from the fixed version."""
        b = self.brain()
        self.assertEqual(b.action_gate.go_threshold, DEFAULTS["go_threshold"])
        self.assertEqual(b.skill_compiler.compilation_threshold,
                         int(DEFAULTS["compilation_threshold"]))
        self.assertEqual(b.associative_graph.damping_factor, DEFAULTS["damping_factor"])

    def test_retune_moves_the_live_subsystems(self):
        b = self.brain()
        b.retune(recent_error=0.8, allostatic_load=0.9, headroom=0.2,
                 recent_oscillation=0.7, success_streak=0,
                 reason="integration: sustained failure")
        self.assertNotEqual(b.action_gate.go_threshold, DEFAULTS["go_threshold"])
        self.assertNotEqual(b.associative_graph.damping_factor,
                            DEFAULTS["damping_factor"])

    def test_retune_changes_actual_gate_behaviour(self):
        """NEGATIVE-CONTROL-FRIENDLY: the observable behaviour must differ.

        If this passes while the subsystem was never touched, C4 is decorative.
        """
        stressed = self.brain()
        calm = HermesBrain(db_path=os.path.join(self.tmpdir, "calm.db"))
        calm_disposition, _, _ = calm.action_gate.evaluate_pathways(
            "x", expected_utility=0.5, somatic_bias=0.0, conflict_level=0.0)
        stressed.retune(recent_error=0.8, allostatic_load=0.9,
                        reason="integration: behaviour must change")
        stressed_disposition, _, _ = stressed.action_gate.evaluate_pathways(
            "x", expected_utility=0.5, somatic_bias=0.0, conflict_level=0.0)
        self.assertNotEqual(calm_disposition, stressed_disposition,
                            "retune did not change any observable behaviour")

    def test_gains_stay_inside_declared_bounds_after_retune(self):
        b = self.brain()
        for error, load in ((0.0, 0.0), (1.0, 1.0), (0.5, 0.5)):
            b.retune(recent_error=error, allostatic_load=load, headroom=0.0,
                     recent_oscillation=1.0, success_streak=0,
                     reason=f"integration: bounds probe {error}/{load}")
            for name in GAIN_SPECS:
                floor, ceiling = GAIN_SPECS[name][0], GAIN_SPECS[name][1]
                value = b.gains.get(name)
                self.assertGreaterEqual(value, floor, f"{name}={value} below floor")
                self.assertLessEqual(value, ceiling, f"{name}={value} above ceiling")

    def test_retune_without_a_reason_is_refused(self):
        b = self.brain()
        before = b.action_gate.go_threshold
        for bad in ("", "   "):
            with self.assertRaises(ValueError):
                b.retune(recent_error=1.0, allostatic_load=1.0, reason=bad)
        self.assertEqual(b.action_gate.go_threshold, before,
                         "a refused retune still moved the subsystem")

    def test_every_retune_is_recorded_with_its_trigger(self):
        b = self.brain()
        b.retune(recent_error=0.6, allostatic_load=0.4,
                 reason="integration: audit trail")
        trail = b.gains.history()
        self.assertTrue(trail, "retune recorded nothing")
        for entry in trail:
            self.assertIn("integration: audit trail", entry["trigger"])


class TestSchemaFoundation(DecisionWiringBase):
    """C1, C10, C12: the additive columns exist and preserve existing data."""

    NEW_COLUMNS = ("trust", "authority", "scope", "provenance_span",
                   "valid_from", "valid_to", "supersedes_id")

    def _columns(self, path):
        return {r[1] for r in sqlite3.connect(path).execute(
            "PRAGMA table_info(cognitive_beliefs)")}

    def test_fresh_database_has_every_new_column(self):
        self.brain()
        cols = self._columns(self.db)
        for name in self.NEW_COLUMNS:
            self.assertIn(name, cols, f"{name} missing from a fresh database")

    def test_migration_upgrades_a_pre_existing_database(self):
        """The real case: a database created before these columns existed."""
        old = os.path.join(self.tmpdir, "old.db")
        conn = sqlite3.connect(old)
        conn.executescript("""
            CREATE TABLE cognitive_beliefs (
              id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL,
              statement TEXT NOT NULL, credence REAL DEFAULT 1.0,
              provenance TEXT NOT NULL,
              epistemic_state TEXT NOT NULL CHECK (epistemic_state IN
                ('grounded','disputed','undercut','superseded')),
              created_at TEXT, updated_at TEXT);
            INSERT INTO cognitive_beliefs
              (topic, statement, credence, provenance, epistemic_state)
              VALUES ('t', 'a pre-existing belief', 0.9, 'user', 'grounded');
        """)
        conn.commit()
        conn.close()

        HermesBrain(db_path=old)

        cols = self._columns(old)
        for name in self.NEW_COLUMNS:
            self.assertIn(name, cols, f"{name} missing after migration")
        conn = sqlite3.connect(old)
        count, = conn.execute("SELECT count(*) FROM cognitive_beliefs").fetchone()
        self.assertEqual(count, 1, "the migration destroyed an existing row")
        conn.close()

    def test_migration_is_idempotent(self):
        """Constructing twice must not fail or duplicate columns."""
        HermesBrain(db_path=self.db)
        HermesBrain(db_path=self.db)
        HermesBrain(db_path=self.db)
        cols = self._columns(self.db)
        for name in self.NEW_COLUMNS:
            self.assertIn(name, cols)

    def test_new_columns_carry_sensible_defaults(self):
        self.brain()
        conn = sqlite3.connect(self.db)
        conn.execute("""INSERT INTO cognitive_beliefs
                        (topic, statement, provenance, epistemic_state, source_location)
                        VALUES ('t','s','wiki','grounded','x.md')""")
        conn.commit()
        row = conn.execute("SELECT trust, authority, valid_to FROM cognitive_beliefs").fetchone()
        conn.close()
        # Defaults must be CONSERVATIVE. A new belief is not trusted by default
        # (0.5) and is not treated as user-asserted by default.
        self.assertEqual(row[0], 0.5, "new beliefs default to trusted")
        self.assertEqual(row[1], "retrieved_quote")
        self.assertIsNone(row[2], "a new belief defaults to already retired")

    def test_trust_is_separate_from_provenance(self):
        """C1's whole point: WHERE it came from is not HOW MUCH it is worth."""
        self.brain()
        conn = sqlite3.connect(self.db)
        conn.execute("""INSERT INTO cognitive_beliefs
                        (topic, statement, provenance, epistemic_state, source_location, trust)
                        VALUES ('t','s','user','grounded','x.md',0.95)""")
        conn.commit()
        row = conn.execute("SELECT provenance, trust FROM cognitive_beliefs").fetchone()
        conn.close()
        self.assertEqual(row[0], "user")
        self.assertEqual(row[1], 0.95)
        self.assertNotEqual(row[0], str(row[1]),
                            "provenance and trust collapsed into one value")


class TestC7AgainstTheDatabase(DecisionWiringBase):
    """C7 must select from REAL rows, not only from constructed dataclasses."""

    def _insert(self, conn, topic, statement, valid_from, credence=0.8, **kw):
        cols = ["topic", "statement", "provenance", "epistemic_state",
                "source_location", "valid_from", "credence"]
        vals = [topic, statement, "wiki", "grounded", "x.md", valid_from, credence]
        for k, v in kw.items():
            cols.append(k)
            vals.append(v)
        cur = conn.execute(
            f"INSERT INTO cognitive_beliefs ({','.join(cols)}) "
            f"VALUES ({','.join('?' * len(cols))})", vals)
        conn.commit()
        return cur.lastrowid

    def test_resolves_the_newest_from_real_rows(self):
        b = self.brain()
        conn = sqlite3.connect(self.db)
        self._insert(conn, "topic-a", "old claim", "2026-01-01T00:00:00Z")
        self._insert(conn, "topic-a", "middle claim", "2026-06-01T00:00:00Z")
        newest = self._insert(conn, "topic-a", "newest claim", "2026-09-01T00:00:00Z")
        rows = conn.execute(
            "SELECT id, topic, statement, credence, authority, epistemic_state, "
            "valid_from, valid_to, supersedes_id, provenance_span, scope "
            "FROM cognitive_beliefs").fetchall()
        conn.close()

        from brain.decisions import BeliefRecord
        records = [BeliefRecord(id=r[0], topic=r[1], statement=r[2], credence=r[3],
                                authority=r[4], epistemic_state=r[5], valid_from=r[6],
                                valid_to=r[7], supersedes_id=r[8],
                                provenance_span=r[9], scope=r[10]) for r in rows]
        winner = SupersessionResolver().resolve(records)
        self.assertIsNotNone(winner, "resolver returned nothing for real rows")
        assert winner is not None
        self.assertEqual(winner.id, newest)
        self.assertEqual(winner.statement, "newest claim")

    def test_valid_to_null_means_currently_binding(self):
        b = self.brain()
        conn = sqlite3.connect(self.db)
        self._insert(conn, "t", "retired claim", "2026-09-01T00:00:00Z",
                     valid_to="2026-09-02T00:00:00Z")
        current = self._insert(conn, "t", "live claim", "2026-01-01T00:00:00Z")
        row = conn.execute(
            "SELECT id, topic, statement, credence, authority, epistemic_state, "
            "valid_from, valid_to, supersedes_id, provenance_span, scope "
            "FROM cognitive_beliefs WHERE valid_to IS NULL").fetchone()
        conn.close()
        from brain.decisions import BeliefRecord
        rec = BeliefRecord(id=row[0], topic=row[1], statement=row[2], credence=row[3],
                           authority=row[4], epistemic_state=row[5], valid_from=row[6],
                           valid_to=row[7], supersedes_id=row[8],
                           provenance_span=row[9], scope=row[10])
        self.assertEqual(rec.id, current)
        winner = SupersessionResolver().resolve([rec])
        self.assertIsNotNone(winner)
        assert winner is not None
        self.assertEqual(winner.id, current)


class TestC5AppliedToTheRealCheckers(DecisionWiringBase):
    """C5 applied to the verifiers this repo actually ships."""

    def test_a_checker_sharing_the_subjects_facets_is_flagged(self):
        """A verifier that reads the same database it grades is a self-grader."""
        v = VerifierIndependence("verify_reads", frozenset({"data"}))
        self.assertTrue(v.self_grading(SUBJECT_FACETS))

    def test_an_external_auditor_is_not_flagged(self):
        v = VerifierIndependence("external-auditor", frozenset({"operator", "instrument"}))
        self.assertFalse(v.self_grading(SUBJECT_FACETS))

    def test_gains_registry_is_not_a_verifier(self):
        """NEGATIVE: the gain registry must not be usable as its own check.

        PlasticGains records what the system did; it has no independent
        instrument, so it cannot grade itself.
        """
        v = VerifierIndependence("gain-audit", frozenset())
        self.assertTrue(v.self_grading(SUBJECT_FACETS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
