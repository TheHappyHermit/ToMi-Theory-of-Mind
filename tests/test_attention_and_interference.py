#!/usr/bin/env python3
"""
Tests for Phase 2: attentional cost, and working-memory interference.

The old gate scored character entropy. These tests include the specific cases
that exposed it, because "the old behaviour was wrong" is only worth asserting
if the wrongness is pinned down:

  - "aaaaaaaaaaaa" scored near zero however important it was
  - a base64 blob scored high while saying nothing
  - any two English sentences shared enough function words to look relevant

The interference tests assert the property that distinguishes interference from
eviction: nothing is removed, and what remains is harder to reach.

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_attention_and_interference.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.thalamus.attention import (  # noqa: E402
    AttentionalGate,
    SwitchCost,
    ThalamicGate,
)
from brain.cortex.dl_pfc import DorsolateralPFC  # noqa: E402


class TestEntropyIsNoLongerTheScore(unittest.TestCase):
    """The defect that motivated the phase."""

    def test_a_repetitive_but_important_line_is_not_scored_zero(self):
        g = AttentionalGate()
        score = g.bottom_up_saliency(
            "CRITICAL: deploy failed, database is corrupt, rollback now")
        self.assertGreater(score, 0.5,
                           "a repetitive string about a failure is not unimportant")

    def test_a_high_entropy_blob_with_no_content_is_not_important(self):
        g = AttentionalGate()
        blob = "aGVsbG8gd29ybGQ=" * 12   # varied characters, says nothing
        self.assertLessEqual(g.bottom_up_saliency(blob), 0.1,
                             "string randomness is not saliency")

    def test_chatter_scores_exactly_zero(self):
        """Not a small penalty. 'ok' carries nothing, and letting it score a
        little above zero is how a log stream of them fills a context."""
        g = AttentionalGate()
        for chatter in ("ok", "OK.", "done", "heartbeat", "ping", "thanks!"):
            with self.subTest(text=chatter):
                self.assertEqual(g.bottom_up_saliency(chatter), 0.0)

    def test_urgent_text_outscores_incidental_text(self):
        g = AttentionalGate()
        urgent = g.bottom_up_saliency("FATAL: database connection refused in production")
        incidental = g.bottom_up_saliency("the meeting is at three in the afternoon")
        self.assertGreater(urgent, incidental)

    def test_a_named_file_earns_specificity(self):
        g = AttentionalGate()
        with_file = g.bottom_up_saliency("check scripts/verify_stack.py for the failure")
        without = g.bottom_up_saliency("check the thing for the failure")
        self.assertGreater(with_file, without)


class TestOverlapIsOverContentWords(unittest.TestCase):
    def test_two_ordinary_sentences_do_not_look_relevant(self):
        """The old overlap divided by min() over all words, so shared grammar
        read as shared subject matter."""
        g = AttentionalGate()
        overlap = g.contextual_relevance(
            "the database connection was refused by the server",
            "the deployment pipeline failed after the migration")
        self.assertLess(overlap, 0.15, "function words are not shared subject matter")

    def test_genuinely_related_text_does_overlap(self):
        g = AttentionalGate()
        overlap = g.contextual_relevance(
            "the graph retrieval index is stale",
            "rebuild the graph retrieval index")
        self.assertGreater(overlap, 0.4)

    def test_chatter_does_not_overlap_anything(self):
        g = AttentionalGate()
        self.assertEqual(g.contextual_relevance("ok", "deploy the graph index"), 0.0)


class TestThreeSwitchComponents(unittest.TestCase):
    """Separated, because a pre-summed float cannot be decomposed later."""

    def test_components_are_reported_individually(self):
        g = AttentionalGate()
        c = g.switch_cost("unrelated text", "graph retrieval rebuild")
        self.assertIsInstance(c, SwitchCost)
        d = c.as_dict()
        for k in ("reconfiguration", "resumption", "residue", "total"):
            self.assertIn(k, d)
        self.assertAlmostEqual(
            d["total"], d["reconfiguration"] + d["resumption"] + d["residue"])

    def test_unrelated_switch_costs_more_to_reconfigure(self):
        g = AttentionalGate()
        unrelated = g.switch_cost("completely different topic", "graph retrieval")
        related = g.switch_cost("graph retrieval tuning", "graph retrieval rebuild")
        self.assertGreater(unrelated.reconfiguration, related.reconfiguration,
                           "no priming to help means a dearer switch")

    def test_a_resume_note_lowers_resumption(self):
        g = AttentionalGate()
        before = g.switch_cost("something else", "graph retrieval").resumption
        g.set_resume_note("resume at scripts/verify_stack.py, step 3")
        after = g.switch_cost("something else", "graph retrieval").resumption
        self.assertLess(after, before)

    def test_a_resume_note_does_NOT_lower_residue(self):
        """The finding is that anticipating resumption pressure makes
        disengagement harder. A resume note is a priming cue, not a cure."""
        g = AttentionalGate()
        g.retire_task("migrate the schema", finished=False)
        before = g.switch_cost("x", "y").residue
        g.set_resume_note("resume at step 3")
        after = g.switch_cost("x", "y").residue
        self.assertEqual(before, after,
                         "treating a resume note as a residue cure inverts the finding")

    def test_unfinished_task_leaves_more_residue_than_finished(self):
        g = AttentionalGate()
        g.retire_task("task a", finished=False)
        unfinished = g.switch_cost("x", "y").residue
        g.retire_task("task a", finished=True)
        finished = g.switch_cost("x", "y").residue
        self.assertGreater(unfinished, finished)

    def test_no_active_task_means_no_residue(self):
        self.assertEqual(AttentionalGate().switch_cost("x", "y").residue, 0.0)

    def test_retiring_a_task_clears_its_stale_resume_note(self):
        """A resume note for a finished task must not prime the next one."""
        g = AttentionalGate()
        g.retire_task("old task", finished=True)
        g.set_resume_note("resume old task at step 2")
        g.retire_task("new task", finished=False)
        self.assertIsNone(g._resume_note)

    def test_unrelated_incoming_text_worsens_residue(self):
        """Two unrelated task sets live at once is the mixing cost."""
        g = AttentionalGate()
        g.retire_task("graph work", finished=False)
        same = g.switch_cost("graph retrieval index", "graph retrieval index").residue
        unrelated = g.switch_cost("rotate the log files", "graph retrieval index").residue
        self.assertGreater(unrelated, same)


class TestUrgencyIsNotSuppressed(unittest.TestCase):
    def test_an_urgent_interruption_survives_high_residue(self):
        """Residue may suppress a low-saliency text. It must not be able to
        suppress an urgent one, or the gate goes blind exactly when something
        breaks."""
        g = AttentionalGate(saliency_threshold=0.35)
        g.retire_task("unfinished feature work", finished=False)
        admitted, score, _ = g.evaluate_admission(
            "FATAL: production database is corrupt, data loss in progress")
        self.assertTrue(admitted, f"urgent text was suppressed at score {score:.2f}")

    def test_a_trivial_text_is_still_attenuated_under_residue(self):
        g = AttentionalGate()
        g.retire_task("unfinished feature work", finished=False)
        _, _, disposition = g.evaluate_admission("ok")
        self.assertEqual(disposition, "attenuate")


class TestExplain(unittest.TestCase):
    def test_the_breakdown_is_available(self):
        """A gate returning only a score cannot be debugged."""
        g = AttentionalGate()
        g.retire_task("task", finished=False)
        d = g.explain("fix the failing deploy in scripts/deploy.sh")
        for k in ("disposition", "admitted", "score", "bottom_up", "relevance",
                  "switch_cost", "active_task", "active_task_finished"):
            self.assertIn(k, d)
        self.assertEqual(d["active_task"], "task")
        self.assertFalse(d["active_task_finished"])

    def test_thalamic_gate_is_the_same_gate(self):
        """One definition of attention. Two gates would be two definitions and
        the disagreement between them invisible."""
        self.assertTrue(issubclass(ThalamicGate, AttentionalGate))
        self.assertEqual(
            ThalamicGate().bottom_up_saliency("FATAL: everything is broken"),
            AttentionalGate().bottom_up_saliency("FATAL: everything is broken"))


class TestInterference(unittest.TestCase):
    """The property that separates interference from eviction: nothing leaves."""

    def setUp(self):
        self.wm = DorsolateralPFC(capacity=7, category_quotas={})
        self.wm.upsert_slot("graph_a", "the graph retrieval index is stale", 0.6)
        self.wm.upsert_slot("graph_b", "the graph retrieval index needs rebuild", 0.6)
        self.wm.upsert_slot("deploy", "the deploy script failed on migration", 0.6)

    def test_nothing_is_removed(self):
        before = set(self.wm.slots)
        self.wm.apply_interference()
        self.assertEqual(set(self.wm.slots), before,
                         "interference must not evict anything")

    def test_competing_slots_weaken(self):
        a, b = self.wm.slots["graph_a"].activation, self.wm.slots["graph_b"].activation
        self.wm.apply_interference()
        self.assertLess(self.wm.slots["graph_a"].activation, a)
        self.assertLess(self.wm.slots["graph_b"].activation, b)

    def test_unrelated_slot_is_untouched(self):
        """Two unrelated slots are retrieved by different cues and do not
        contend."""
        before = self.wm.slots["deploy"].activation
        self.wm.apply_interference()
        self.assertAlmostEqual(self.wm.slots["deploy"].activation, before)

    def test_the_competing_pairs_are_reported(self):
        pairs = self.wm.apply_interference()
        self.assertIn(("graph_a", "graph_b"), pairs)
        self.assertNotIn(("graph_a", "deploy"), pairs)

    def test_zero_strength_changes_nothing(self):
        before = {k: v.activation for k, v in self.wm.slots.items()}
        self.wm.apply_interference(strength=0.0)
        for k, v in self.wm.slots.items():
            self.assertAlmostEqual(v.activation, before[k])

    def test_stronger_interference_weakens_more(self):
        self.wm.apply_interference(strength=0.5)
        weak = self.wm.slots["graph_a"].activation
        wm2 = DorsolateralPFC(capacity=7, category_quotas={})
        wm2.upsert_slot("graph_a", "the graph retrieval index is stale", 0.6)
        wm2.upsert_slot("graph_b", "the graph retrieval index needs rebuild", 0.6)
        wm2.apply_interference(strength=1.0)
        self.assertLess(wm2.slots["graph_a"].activation, weak)

    def test_activation_never_goes_negative(self):
        self.wm.apply_interference(strength=1.0)
        self.wm.apply_interference(strength=1.0)
        self.wm.apply_interference(strength=1.0)
        for k, v in self.wm.slots.items():
            self.assertGreaterEqual(v.activation, 0.0, f"{k} went negative")

    def test_using_working_memory_does_not_strengthen_it(self):
        """Otherwise reading a slot would raise the activation of everything it
        competes with, which is the opposite of interference."""
        self.wm.get_slot("graph_a")
        self.wm.get_slot("graph_b")
        self.wm.apply_interference()
        self.assertLess(self.wm.slots["graph_a"].activation, 1.0)

    def test_chatter_shares_no_cue_with_a_task(self):
        """Counting function words would make every pair of slots compete."""
        wm = DorsolateralPFC(capacity=4, category_quotas={})
        wm.upsert_slot("a", "the graph index is stale", 0.5)
        wm.upsert_slot("b", "ok", 0.5)
        self.assertEqual(wm.apply_interference(), [])

    def test_empty_memory_does_not_raise(self):
        self.assertEqual(DorsolateralPFC(capacity=3).apply_interference(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
