#!/usr/bin/env python3
"""
Tests that each of the six gates FIRES, and does not fire when it should not.

The point of gating is that a gate which never fires is a defect, not a safety
property: it means a subsystem that is still unwired, just with extra code
around it. So every gate gets a positive test that drives it to True, and a
negative test that proves it is not simply always-on.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_cognitive_wiring.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.hermes_brain import HermesBrain  # noqa: E402
from brain.cortex.wiring import CognitiveWiring, GATE_NAMES  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "brain", "schema", "brain_cortex.sql")


def make_brain(with_beliefs=()):
    tmp = tempfile.mkdtemp(prefix="wire-")
    db = os.path.join(tmp, "brain.db")
    with open(SCHEMA, encoding="utf-8") as fh:
        sqlite3.connect(db).executescript(fh.read())
    brain = HermesBrain(db_path=db)
    for topic, statement, credence in with_beliefs:
        brain.defeater_graph.add_belief(topic, statement, credence,
                                       provenance="test",
                                       source_location="test:wiring")
    return brain, tmp, db


class GateTestBase(unittest.TestCase):
    BELIEFS = ()

    def setUp(self):
        self.brain, self.tmp, self.db = make_brain(self.BELIEFS)
        self.w = CognitiveWiring(self.brain)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestDefeaterGate(GateTestBase):
    """Fires on a negation that lands on a stored belief."""

    BELIEFS = (("graph", "the graph is faster than plain retrieval", 0.7),)

    def test_fires_on_negation_over_a_stored_belief(self):
        should, why = self.w.gate_defeater("the graph is not faster than plain retrieval")
        self.assertTrue(should, f"gate failed to fire: {why}")

    def test_does_not_fire_without_negation(self):
        """Restating a belief is agreement, not contradiction. A gate that fires
        here would flag every repetition as a dispute."""
        should, why = self.w.gate_defeater("the graph is faster than plain retrieval")
        self.assertFalse(should, f"gate fired on mere agreement: {why}")

    def test_does_not_fire_on_unrelated_text(self):
        should, why = self.w.gate_defeater("please add a button to the dashboard")
        self.assertFalse(should, f"gate fired with no belief overlap: {why}")

    def test_reports_why_it_declined(self):
        _, why = self.w.gate_defeater("hello there")
        self.assertIn("overlap", why)


class TestDefeaterGateWithNoBeliefs(GateTestBase):
    """With nothing stored there is nothing to contradict."""

    def test_cannot_fire(self):
        should, why = self.w.gate_defeater("this is not true")
        self.assertFalse(should)
        self.assertIn("no stored beliefs", why)


class TestAGMGate(GateTestBase):
    def test_does_not_fire_without_contradiction(self):
        should, why = self.w.gate_agm(None)
        self.assertFalse(should)
        self.assertIn("no contradiction", why)

    def test_does_not_fire_with_one_belief(self):
        """Entrenchment ordering over one element is a no-op dressed as a
        decision. There is nothing to choose between."""
        should, why = self.w.gate_agm({"contradiction": True, "contested": [{"topic": "x"}]})
        self.assertFalse(should)
        self.assertIn("nothing to choose", why)

    def test_fires_with_two_contested_beliefs(self):
        should, why = self.w.gate_agm({"contradiction": True, "contested": [
            {"topic": "graph", "statement": "a", "credence": 0.7},
            {"topic": "graph", "statement": "b", "credence": 0.3},
        ]})
        self.assertTrue(should, f"gate failed to fire: {why}")


class TestDialecticGate(GateTestBase):
    def test_does_not_fire_with_one_position(self):
        should, why = self.w.gate_dialectic({"contested": [{"statement": "a"}]})
        self.assertFalse(should)
        self.assertIn("two or more", why)

    def test_does_not_fire_when_all_superseded(self):
        should, _ = self.w.gate_dialectic({"contested": [
            {"statement": "a", "epistemic_state": "superseded"},
            {"statement": "b", "epistemic_state": "superseded"},
        ]})
        self.assertFalse(should, "a superseded position is not an active one")

    def test_fires_with_two_active_positions(self):
        should, why = self.w.gate_dialectic({"contested": [
            {"statement": "a"}, {"statement": "b"},
        ]})
        self.assertTrue(should, f"gate failed to fire: {why}")


class TestChronesthesiaGate(GateTestBase):
    def test_does_not_fire_without_temporal_reference(self):
        should, why = self.w.gate_chronesthesia("deploy the new dashboard")
        self.assertFalse(should)
        self.assertIn("no temporal reference", why)

    def test_does_not_fire_on_temporal_word_with_empty_timeline(self):
        """The reference is there but there is nothing to travel to. Firing
        would return None, indistinguishable from 'asked and found nothing'."""
        should, why = self.w.gate_chronesthesia("what did we do yesterday")
        self.assertFalse(should)
        self.assertIn("no timeline", why)

    def test_fires_once_a_timeline_exists(self):
        """The positive case. Without this the gate has never been observed to
        work, and an unobserved gate is indistinguishable from a broken one."""
        self.brain.chronesthesia.record_timeline_event(
            "e1", "switched to graphify", {"graph": False})
        should, why = self.w.gate_chronesthesia("what did we do yesterday")
        self.assertTrue(should, f"gate failed to fire: {why}")


class TestCounterfactualGate(GateTestBase):
    def test_does_not_fire_on_system_1(self):
        """The expensive subsystem must not run on a reflex."""
        should, why = self.w.gate_counterfactual("should we switch to graph", "SYSTEM_1")
        self.assertFalse(should)
        self.assertIn("SYSTEM_1", why)

    def test_does_not_fire_without_decision_language(self):
        should, why = self.w.gate_counterfactual("explain the schema", "SYSTEM_2")
        self.assertFalse(should)
        self.assertIn("no decision language", why)

    def test_fires_on_system_2_with_a_decision(self):
        should, why = self.w.gate_counterfactual(
            "should we switch to the graph store", "SYSTEM_2")
        self.assertTrue(should, f"gate failed to fire: {why}")


class TestAssociativeGate(GateTestBase):
    def test_fires_on_system_2(self):
        should, why = self.w.gate_associative_graph("SYSTEM_2", "anything at all")
        self.assertTrue(should, f"gate failed to fire: {why}")

    def test_does_not_fire_on_a_short_reflexive_turn(self):
        should, why = self.w.gate_associative_graph("SYSTEM_1", "fix the typo")
        self.assertFalse(should)
        self.assertIn("reflexive route", why)

    def test_fires_on_a_wide_system_1_turn(self):
        """Many distinct concepts means no single document probably holds the
        whole answer, which is exactly when association earns its keep."""
        wide = ("graph retrieval fusion benchmark recall precision latency index "
                "corpus vault schema migration rollback")
        should, why = self.w.gate_associative_graph("SYSTEM_1", wide)
        self.assertTrue(should, f"gate failed to fire: {why}")


class TestThePassRuns(unittest.TestCase):
    """End-to-end: the wiring runs and reports every gate."""

    def setUp(self):
        self.brain, self.tmp, self.db = make_brain(
            (("graph", "the graph is faster", 0.7),
             ("graph", "the graph is slower", 0.3)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_gate_is_reported(self):
        w = CognitiveWiring(self.brain)
        out = w.run("the graph is not faster than plain retrieval", "SYSTEM_2", "s1")
        for name in GATE_NAMES:
            self.assertIn(name, out, f"{name} missing from the pass output")
            self.assertIn("ran", out[name])
            self.assertIn("why", out[name], f"{name} must say why it ran or did not")

    def test_counts_are_tracked(self):
        w = CognitiveWiring(self.brain)
        w.run("hello", "SYSTEM_1", "s1")
        w.run("should we switch", "SYSTEM_2", "s2")
        counts = w.run("x", "SYSTEM_1", "s3")["_counts"]
        self.assertEqual(set(counts["fired"]), set(GATE_NAMES))
        self.assertGreaterEqual(sum(counts["fired"].values()), 1)
        self.assertGreaterEqual(sum(counts["skipped"].values()), 1)

    def test_contradicting_text_actually_drives_the_chain(self):
        """The chain is the argument of the design: defeater detects, AGM
        chooses. Test the whole path, not the predicates in isolation."""
        w = CognitiveWiring(self.brain)
        out = w.run("the graph is not faster than plain retrieval", "SYSTEM_1", "s1")
        self.assertTrue(out["defeater_graph"]["ran"],
                        "defeater graph should fire on a stored-belief contradiction")
        self.assertTrue(out["defeater_graph"]["result"].get("contradiction"))
        # AGM needs two contested beliefs, which this text does produce.
        self.assertTrue(out["agm"]["ran"], f"AGM should follow: {out['agm']['why']}")

    def test_a_subsystem_error_does_not_take_down_the_pass(self):
        """The seven steps that already work are worth more than the one that
        just failed. A gate that raises would lose the whole pass."""
        w = CognitiveWiring(self.brain)

        def boom(*a, **k):
            raise RuntimeError("subsystem is down")
        self.brain.chronesthesia.retrospection = boom
        self.brain.chronesthesia.timeline_events = [{"event_id": "e1"}]
        out = w.run("what did we do yesterday", "SYSTEM_1", "s1")
        self.assertIn("chronesthesia", out)
        self.assertIn("error", out["chronesthesia"]["result"],
                      "the failure must be recorded, not swallowed")
        self.assertIn("_counts", out, "the pass must still complete")

    def test_brain_exposes_wiring_without_breaking_the_old_contract(self):
        self.assertTrue(hasattr(self.brain, "wiring"))
        result = self.brain.process_incoming_stimulus(
            source="test", text="the graph is not faster", session_id="s1")
        self.assertIn("gated_subsystems", result)
        for key in ("saliency", "pragmatics", "cognitive_route", "somatic_appraisal",
                    "action_gate", "working_memory_summary", "fired_intentions",
                    "tom_alerts", "affective_state"):
            self.assertIn(key, result, f"existing key {key} must survive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
