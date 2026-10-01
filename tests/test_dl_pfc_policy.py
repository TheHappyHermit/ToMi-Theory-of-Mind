#!/usr/bin/env python3
"""
Tests for the dlPFC eviction policy and per-category slot quotas.

These assert the POLICY, not the current behaviour. A test written against
whatever the code happens to do will keep passing after the policy changes, which
is the specific failure that let an unstated eviction rule survive in the
codebase: nobody could tell whether it was a decision or an accident.

Each test says in its name what must be true, so a failure reads as a statement
about the design rather than a stack trace.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_dl_pfc_policy.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.cortex.dl_pfc import DorsolateralPFC, WorkingMemorySlot  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")


def slot(key, importance=0.5, category="context", activation=1.0):
    s = WorkingMemorySlot(key=key, value=key, importance=importance, category=category)
    s.activation = activation
    return s


class TestEvictionPolicy(unittest.TestCase):
    """0.3 — the policy is now stated, so it can be asserted."""

    def setUp(self):
        self.wm = DorsolateralPFC(capacity=4, category_quotas={})

    def test_faded_untouched_slot_is_evicted_first(self):
        """The least attended slot goes, regardless of its category."""
        self.wm.slots = {
            "used": slot("used", importance=0.5, activation=0.9),
            "faded": slot("faded", importance=0.5, activation=0.1),
        }
        self.assertEqual(self.wm._evict_lowest(), "faded")

    def test_high_importance_does_not_outlive_a_used_slot(self):
        """A product, not a sum. An important slot nobody has touched in twenty
        turns is less current than a mediocre one used constantly."""
        self.wm.slots = {
            "important_but_stale": slot("important_but_stale", importance=1.0, activation=0.1),
            "mediocre_but_used": slot("mediocre_but_used", importance=0.2, activation=1.0),
        }
        self.assertEqual(self.wm._evict_lowest(), "important_but_stale")

    def test_equal_scores_evict_deterministically(self):
        """Two identical slots must not produce a coin flip. min() is stable on
        the first element, so the same one goes every time."""
        self.wm.slots = {"a": slot("a"), "b": slot("b")}
        first = self.wm._evict_lowest()
        self.wm.slots = {"a": slot("a"), "b": slot("b")}
        self.assertEqual(self.wm._evict_lowest(), first)

    def test_eviction_score_is_the_documented_product(self):
        s = slot("x", importance=0.5, activation=0.4)
        self.assertAlmostEqual(self.wm._eviction_score(s), 0.2)

    def test_empty_memory_evicts_nothing_and_does_not_raise(self):
        self.assertIsNone(self.wm._evict_lowest())

    def test_eviction_returns_the_key_it_removed(self):
        """Returning the key is what makes an eviction observable. A method that
        discards its result is unwired with extra steps."""
        self.wm.slots = {"a": slot("a", activation=0.2)}
        self.assertEqual(self.wm._evict_lowest(), "a")
        self.assertNotIn("a", self.wm.slots)


class TestCategoryQuotas(unittest.TestCase):
    """0.4 — one category must not take every slot."""

    def test_over_quota_category_is_the_only_one_that_loses_a_slot(self):
        wm = DorsolateralPFC(capacity=6, category_quotas={"context": 1, "fact": 3})
        wm.slots = {
            "c1": slot("c1", category="context", activation=0.9),
            "c2": slot("c2", category="context", activation=0.8),
            "f1": slot("f1", category="fact", activation=0.05),
        }
        # context holds 2 against a quota of 1, so context is over. fact is
        # under its quota of 3 and must be protected even though f1 is the
        # lowest-scoring slot overall.
        self.assertEqual(wm._evict_lowest(), "c2")

    def test_no_restriction_when_every_category_is_within_quota(self):
        wm = DorsolateralPFC(capacity=6, category_quotas={"context": 3, "fact": 3})
        wm.slots = {
            "c1": slot("c1", category="context", activation=0.9),
            "f1": slot("f1", category="fact", activation=0.1),
        }
        self.assertEqual(wm._evict_lowest(), "f1", "under quota, plain score decides")

    def test_unlimited_category_is_never_considered_over_quota(self):
        """A category absent from the dict is unlimited. Adding a new category
        must not silently become a quota of zero, which would make every one of
        its slots immediately evictable."""
        wm = DorsolateralPFC(capacity=6, category_quotas={"context": 1})
        wm.slots = {
            "novel": slot("novel", category="brand_new_category", activation=0.01),
            "c1": slot("c1", category="context", activation=0.9),
        }
        self.assertEqual(wm._over_quota_categories(), set())
        self.assertEqual(wm._evict_lowest(), "novel")

    def test_default_quotas_exist_and_are_sane(self):
        wm = DorsolateralPFC()
        for cat in ("context", "fact", "constraint", "hypothesis", "scratchpad"):
            self.assertIn(cat, wm.category_quotas)
        # Quotas must not exceed total capacity, or they would never bind.
        self.assertLessEqual(sum(wm.category_quotas.values()), wm.capacity)

    def test_constraint_is_the_most_protected_category(self):
        """Losing a constraint causes a wrong answer; losing a fact usually
        causes a re-derivation. That is the whole reason for the ordering."""
        wm = DorsolateralPFC()
        self.assertEqual(wm.category_quotas["constraint"], 1)
        self.assertGreater(wm.category_quotas["constraint"], wm.category_quotas["scratchpad"])


class TestQuotaUnderPressure(unittest.TestCase):
    """The real scenario: many slots, one type dominant."""

    def test_context_flood_cannot_starve_a_constraint(self):
        wm = DorsolateralPFC(capacity=5)
        wm.upsert_slot("ctx_a", "a", importance=0.9, category="context")
        wm.upsert_slot("ctx_b", "b", importance=0.9, category="context")
        wm.upsert_slot("ctx_c", "c", importance=0.9, category="context")
        wm.upsert_slot("fact_1", "important", importance=0.5, category="fact")
        wm.upsert_slot("constraint_1", "do not push to main",
                       importance=0.3, category="constraint")

        # Push hard. Context tries to take everything.
        for i in range(12):
            wm.upsert_slot(f"flood_{i}", f"v{i}", importance=0.95, category="context")

        self.assertIn("constraint_1", wm.slots,
                      "a constraint must survive any amount of context pressure")
        self.assertLessEqual(len(wm.slots), wm.capacity)

    def test_scratchpad_is_evicted_before_facts(self):
        wm = DorsolateralPFC(capacity=4, category_quotas={})
        wm.slots = {
            "scratch": slot("scratch", category="scratchpad", importance=0.5, activation=0.4),
            "fact": slot("fact", category="fact", importance=0.5, activation=0.5),
        }
        self.assertEqual(wm._evict_lowest(), "scratch")


class TestGoalsAreNotSlots(unittest.TestCase):
    """Goals live in their own field and must not compete for slots. A goal that
    can be evicted is not a goal."""

    def test_goal_slot_is_written_at_maximum_importance(self):
        """A goal does occupy a slot -- deliberately, at importance 1.0, so it
        outranks everything. What must hold is that it cannot be evicted."""
        wm = DorsolateralPFC(capacity=2)
        wm.set_active_goal("ship the thing", ["write tests", "push"])
        self.assertEqual(wm.active_goal, "ship the thing")
        self.assertEqual(wm.slots["active_goal"].importance, 1.0)

    def test_goal_survives_an_eviction_round(self):
        wm = DorsolateralPFC(capacity=2)
        wm.set_active_goal("the goal")
        wm.upsert_slot("noise", "x", importance=0.1, category="scratchpad")
        wm.upsert_slot("more_noise", "y", importance=0.1, category="scratchpad")
        self.assertIn("active_goal", wm.slots,
                      "a goal that can be evicted is not a goal")

    def test_goals_resist_decay(self):
        wm = DorsolateralPFC(capacity=4)
        wm.set_active_goal("hold this")
        wm.upsert_slot("goal_slot", "x", importance=0.5, category="goal")
        before = wm.slots["goal_slot"].activation
        wm.decay_all(rate=0.15)
        self.assertGreaterEqual(wm.slots["goal_slot"].activation, before)


class TestSnapshotPersistence(unittest.TestCase):
    """The snapshot path had two real defects: a space-separated timestamp in an
    RFC 3339 column, and exceptions swallowed into a print."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dlpfc-")
        self.db = os.path.join(self.tmp, "brain.db")
        with open(SCHEMA, encoding="utf-8") as fh:
            sqlite3.connect(self.db).executescript(fh.read())
        self.wm = DorsolateralPFC(capacity=5, db_path=self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_snapshot_roundtrips(self):
        self.wm.set_active_goal("the goal", ["sub one"])
        self.wm.upsert_slot("k1", "v1", importance=0.7, category="fact")
        self.wm.save_snapshot("sess-1")

        other = DorsolateralPFC(capacity=5, db_path=self.db)
        self.assertTrue(other.load_snapshot("sess-1"))
        self.assertEqual(other.active_goal, "the goal")
        self.assertEqual(other.sub_goals, ["sub one"])
        self.assertEqual(other.slots["k1"].value, "v1")

    def test_snapshot_timestamp_is_rfc3339_utc(self):
        """The column is declared TEXT and indexed. A space-separated
        datetime('now') sorts wrongly against the RFC 3339 values the rest of
        the schema writes, and the mismatch is silent."""
        self.wm.upsert_slot("k", "v")
        self.wm.save_snapshot("sess-2")
        con = sqlite3.connect(self.db)
        try:
            ts = con.execute(
                "SELECT updated_at FROM working_memory_snapshots").fetchone()[0]
        finally:
            con.close()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                         f"snapshot timestamp is not RFC 3339 UTC: {ts!r}")

    def test_failed_save_raises_rather_than_printing(self):
        """A snapshot that silently fails to write loses working memory with no
        signal. The pass that depended on it would report success regardless."""
        broken = DorsolateralPFC(capacity=3, db_path=os.path.join(self.tmp, "gone", "x.db"))
        with self.assertRaises(Exception):
            broken.save_snapshot("sess-3")

    def test_no_db_path_returns_false_rather_than_raising(self):
        """No database means no snapshot to restore. That is an absent state,
        not a failure, and must not take down a cognitive pass."""
        wm = DorsolateralPFC(capacity=3)
        self.assertFalse(wm.load_snapshot("any-session"))

    def test_corrupt_snapshot_raises_rather_than_half_restoring(self):
        """Continuing with a half-restored working memory is how a wrong answer
        becomes an untraceable one. A snapshot that cannot be parsed must fail
        loudly, not leave the slots dict in an unknown state."""
        con = sqlite3.connect(self.db)
        try:
            con.execute(
                "INSERT INTO working_memory_snapshots "
                "(session_id, active_goal, sub_goals_json, hypotheses_json, "
                " focus_slots_json, updated_at) VALUES (?,?,?,?,?,?)",
                ("bad", "goal", "not json at all", "[]", "also not json",
                 "2026-09-26T00:00:00Z"),
            )
            con.commit()
        finally:
            con.close()
        wm = DorsolateralPFC(capacity=3, db_path=self.db)
        with self.assertRaises(Exception):
            wm.load_snapshot("bad")
        self.assertEqual(wm.active_goal, None,
                         "a failed restore must not leave partial state behind")


if __name__ == "__main__":
    unittest.main(verbosity=2)
