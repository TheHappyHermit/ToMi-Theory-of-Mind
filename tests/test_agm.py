"""Tests for a real AGM implementation.

The module these replace was 82 lines, named after AGM, and did not
implement it. Four of the tests below assert behaviour the old code got
wrong outright, and each names the specific failure so a future
regression points at a known defect rather than a vague one.

  * expansion did not check consistency (violates K2)
  * contraction was dict.pop -- deletion, not minimal mutilation
  * entrenchment was a float, i.e. a total order, not a partial order
  * revision compared conflicts_with against keys, but the only real
    caller passes propositions -- so the conflict branch never fired
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.epistemology.agm import (  # noqa: E402
    AGMBeliefRevision, PartialOrder, negate, normal_form,
)


class TestPropositionalHelpers(unittest.TestCase):
    def test_negate(self):
        self.assertEqual(negate("X"), "not X")
        self.assertEqual(negate("not X"), "X")

    def test_normal_form_collapses_case_and_space(self):
        self.assertEqual(normal_form("NOT  X "), "x")

    def test_normal_form_strips_polarity(self):
        """Both polarities must normalise alike, or contradiction is
        invisible. This is a deliberate lossiness."""
        self.assertEqual(normal_form("not X"), normal_form("X"))


class TestK2Consistency(unittest.TestCase):
    """K2: if K+phi entails a contradiction, K+phi is not a belief set."""

    def test_expansion_rejects_contradiction(self):
        a = AGMBeliefRevision()
        a.expand("b1", "Server is live", 0.4)
        r = a.expand("b2", "not Server is live", 0.9)
        self.assertTrue(r.rejected, "K2 violated: contradiction accepted")
        self.assertNotIn("b2", a.corpus)

    def test_rejection_is_legible(self):
        a = AGMBeliefRevision()
        a.expand("b1", "Server is live", 0.4)
        r = a.expand("b2", "not Server is live", 0.9)
        self.assertIn("b1", r.reason)
        self.assertTrue(r.to_dict()["rejected"])

    def test_consistent_expansion_is_accepted(self):
        a = AGMBeliefRevision()
        r = a.expand("b2", "Server is offline", 0.9)
        self.assertFalse(r.rejected)
        self.assertIn("b2", a.corpus)

    def test_inconsistencies_detected(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.4)
        a.corpus["b2"] = _mk("b2", "not X")
        self.assertFalse(a.is_consistent())
        self.assertEqual(len(a.inconsistencies()), 1)

    def test_consistent_corpus_reports_clean(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.4)
        a.expand("b2", "Y", 0.4)
        self.assertTrue(a.is_consistent())
        self.assertEqual(a.inconsistencies(), [])


def _mk(key, prop):
    from brain.epistemology.agm import BeliefItem
    return BeliefItem(key=key, proposition=prop)


class TestLeviIdentity(unittest.TestCase):
    """K*phi = (K - ~phi) + phi, and the real caller path."""

    def test_revision_by_proposition_not_key(self):
        """The production bug: wiring.py passes PROPOSITIONS.

        The old code did `if conflict_key in self.corpus`, which is
        false for a proposition, so the conflict branch never fired and
        revision silently expanded instead of revising.
        """
        a = AGMBeliefRevision()
        a.expand("b1", "Server is live", 0.4)
        res = a.revise("b2", "Server is offline",
                       conflicts_with=["Server is live"], entrenchment=0.7)
        self.assertEqual(res["status"], "revised")
        self.assertEqual(res["mutilated"], ["b1"],
                         "the conflicting belief must actually be removed")
        self.assertNotIn("b1", a.corpus)
        self.assertIn("b2", a.corpus)

    def test_revision_by_key_still_works(self):
        a = AGMBeliefRevision()
        a.expand("b1", "Server is live", 0.4)
        res = a.revise("b2", "Server is offline",
                       conflicts_with=["b1"], entrenchment=0.7)
        self.assertEqual(res["mutilated"], ["b1"])

    def test_more_entrenched_conflict_is_rejected(self):
        a = AGMBeliefRevision()
        a.expand("axiom", "Never delete user data", 0.95)
        res = a.revise("b2", "It is fine to delete user data",
                       conflicts_with=["Never delete user data"], entrenchment=0.2)
        self.assertEqual(res["status"], "rejected")
        self.assertIn("axiom", a.corpus)

    def test_unknown_conflict_is_ignored(self):
        a = AGMBeliefRevision()
        res = a.revise("b2", "X", conflicts_with=["never said this"], entrenchment=0.5)
        self.assertEqual(res["status"], "revised")


class TestContraction(unittest.TestCase):
    """Contraction is not deletion. The old contract() was pop()."""

    def test_contract_removes_dependents(self):
        a = AGMBeliefRevision()
        a.expand("premise", "The test suite passes", 0.9)
        a.expand("derived", "The build is green", 0.5)
        a.corpus["derived"].supports = {"premise"}
        a.contract("premise")
        self.assertNotIn("premise", a.corpus)
        self.assertNotIn("derived", a.corpus,
                         "a belief with no premise left must not survive")

    def test_contract_returns_the_item(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.5)
        got = a.contract("b1")
        self.assertIsNotNone(got)
        self.assertEqual(got.key, "b1")

    def test_contract_missing_key_returns_none(self):
        self.assertIsNone(AGMBeliefRevision().contract("nope"))

    def test_remainders_reported(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.5)
        a.expand("derived", "Y", 0.4)
        a.corpus["derived"].supports = {"b1"}
        rem = a.remainders("b1")
        self.assertEqual(len(rem), 1)
        self.assertEqual(rem[0], {"b1", "derived"})

    def test_remainders_empty_for_unknown(self):
        self.assertEqual(AGMBeliefRevision().remainders("nope"), [])

    def test_unrelated_belief_survives(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.5)
        a.expand("other", "Z", 0.5)
        a.contract("b1")
        self.assertIn("other", a.corpus)

    def test_dangling_support_edges_dropped(self):
        """A survivor must not keep a support edge to a retracted belief.

        `d` is supported by BOTH `p` and `keep`. Retracting `p` should
        drop that edge while `d` and `keep` both survive -- an earlier
        version of this test asserted the edge was cleared on a belief
        that contraction had correctly removed entirely, so it was
        checking a KeyError's worth of nothing.
        """
        a = AGMBeliefRevision()
        a.expand("p", "X", 0.9)
        a.expand("keep", "Z", 0.9)
        a.expand("d", "Y", 0.5)
        a.corpus["d"].supports = {"p", "keep"}
        a.contract("p")
        self.assertIn("d", a.corpus, "d is not solely dependent on p")
        self.assertIn("keep", a.corpus)
        self.assertEqual(a.corpus["d"].supports, {"keep"},
                         "the edge to a retracted belief must be dropped")


class TestPartialOrder(unittest.TestCase):
    """A total order cannot express the case AGM exists to handle."""

    def test_incomparability_is_representable(self):
        po = PartialOrder()
        po.add("a")
        po.add("b")
        self.assertFalse(po.dominates("a", "b"))
        self.assertFalse(po.comparable("a", "b"),
                         "a total order made this unrepresentable")

    def test_dominance(self):
        po = PartialOrder()
        po.add_relation("a", "c")
        self.assertTrue(po.dominates("a", "c"))

    def test_reflexive(self):
        po = PartialOrder()
        po.add("a")
        self.assertTrue(po.dominates("a", "a"))

    def test_transitive_closure(self):
        po = PartialOrder()
        po.add_relation("a", "b")
        po.add_relation("b", "c")
        self.assertTrue(po.dominates("a", "c"), "transitivity not closed")

    def test_cycle_rejected(self):
        po = PartialOrder()
        po.add_relation("a", "b")
        po.add_relation("b", "c")
        with self.assertRaises(ValueError):
            po.add_relation("c", "a")

    def test_minimal_and_maximal(self):
        po = PartialOrder()
        for k in ("a", "b", "c"):
            po.add(k)
        po.add_relation("a", "c")
        self.assertEqual(po.maximal(), {"a", "b"})
        self.assertEqual(po.minimal(), {"b", "c"})

    def test_remove(self):
        po = PartialOrder()
        po.add_relation("a", "b")
        po.remove("a")
        self.assertNotIn("a", po.members())


class TestBackwardCompatibility(unittest.TestCase):
    """Every existing caller must keep working unchanged."""

    def test_legacy_construction(self):
        a = AGMBeliefRevision()
        a.expand("b1", "Server is live", entrenchment=0.4)
        a.revise("b2", "Server is offline",
                 conflicts_with=["b1"], entrenchment=0.8)
        self.assertNotIn("b1", a.corpus)
        self.assertIn("b2", a.corpus)

    def test_list_beliefs_shape(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.4)
        rows = a.list_beliefs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "b1")
        self.assertEqual(rows[0]["entrenchment"], 0.4)

    def test_list_beliefs_sorted_desc(self):
        a = AGMBeliefRevision()
        a.expand("lo", "X", 0.1)
        a.expand("hi", "Y", 0.9)
        keys = [b["key"] for b in a.list_beliefs()]
        self.assertEqual(keys[0], "hi")

    def test_wiring_contradiction_path(self):
        """brain/cortex/wiring.py::_run_agm shape."""
        a = AGMBeliefRevision()
        a.expand("stm:server", "server is live", 0.9)
        res = a.revise(key="stm:server2", proposition="server is offline",
                       conflicts_with=["server is live"],
                       entrenchment=float(0.4))
        self.assertEqual(res["status"], "rejected")

    def test_closure_contains_corpus(self):
        a = AGMBeliefRevision()
        a.expand("b1", "X", 0.5)
        self.assertIn("b1", a.closure())


if __name__ == '__main__':
    unittest.main()
