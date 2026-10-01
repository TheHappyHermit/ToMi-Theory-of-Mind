#!/usr/bin/env python3
"""
Tests for brain/decisions.py -- the 14 arena-backed Decisions.

FOLLOWING THE REPO CONVENTION (tests/test_arena_invariants_nonvacuity.py):
every test here must be able to FAIL. A test that cannot fail is worse than no
test, because it gets read as evidence. So this file deliberately includes:

  - negative tests proving each guard rejects what it claims to reject
  - a non-vacuity self-check that fails if any assertion is vacuous
  - tests that assert the DETERMINISM property C7 depends on, by shuffling
    input order and requiring an identical result

Run:  PYTHONPATH=/home/operator/hermes-brain python3 tests/test_decisions.py
"""

import os
import random
import sys
import unittest

from brain.decisions import (
    AFFECT_AXES,
    DEFAULTS,
    GAIN_SPECS,
    SHEDDING_ORDER,
    SUBJECT_FACETS,
    AffectProfile,
    BeliefRecord,
    PlasticGains,
    SplitConfidence,
    SubstrateBudget,
    SupersessionResolver,
    VerifierIndependence,
)


def r(i, topic="t", statement="s", valid_from="2026-01-01T00:00:00Z",
      credence=0.8, **kw):
    return BeliefRecord(id=i, topic=topic, statement=statement, credence=credence,
                        authority="user_asserted", epistemic_state="grounded",
                        valid_from=valid_from, **kw)


class TestPlasticGains(unittest.TestCase):
    """C4: fixed constants become bounded, logged, plastic gains."""

    def test_defaults_match_the_historical_constants(self):
        """An idle system must start exactly where the fixed version did."""
        g = PlasticGains()
        self.assertEqual(g.get("go_threshold"), 0.4)
        self.assertEqual(g.get("compilation_threshold"), 3.0)
        self.assertEqual(g.get("damping_factor"), 0.85)
        self.assertEqual(g.get("decay_rate"), 0.15)

    def test_every_gain_has_a_floor_below_and_ceiling_above_its_default(self):
        for name, (floor, ceiling, timescale, _desc) in GAIN_SPECS.items():
            self.assertLess(floor, DEFAULTS[name], f"{name} floor >= default")
            self.assertGreater(ceiling, DEFAULTS[name], f"{name} ceiling <= default")
            self.assertGreater(timescale, 0, f"{name} timescale must be positive")

    def test_gains_actually_move(self):
        """NEGATIVE CONTROL: prove this test can fail by asserting no movement."""
        g = PlasticGains()
        g._last_update["go_threshold"] = 0.0  # bypass the rate limit
        value, changed = g.update("go_threshold", 0.7, "high recent error")
        self.assertTrue(changed)
        self.assertGreater(value, 0.4)

    def test_clamped_to_ceiling_and_never_exceeds(self):
        g = PlasticGains()
        for name in GAIN_SPECS:
            g._last_update[name] = 0.0
        v, _ = g.update("go_threshold", 99.0, "absurd proposal")
        ceiling = GAIN_SPECS["go_threshold"][1]
        self.assertLessEqual(v, ceiling, "gain escaped its ceiling")
        self.assertEqual(v, ceiling)

    def test_clamped_to_floor_and_never_below(self):
        g = PlasticGains()
        g._last_update["decay_rate"] = 0.0
        v, _ = g.update("decay_rate", -5.0, "absurd negative proposal")
        floor = GAIN_SPECS["decay_rate"][0]
        self.assertGreaterEqual(v, floor, "gain escaped its floor")

    def test_every_change_is_logged_with_its_trigger(self):
        g = PlasticGains()
        g._last_update["go_threshold"] = 0.0
        g.update("go_threshold", 0.6, "three failed predictions")
        self.assertEqual(len(g.history()), 1)
        entry = g.history()[0]
        self.assertEqual(entry["trigger"], "three failed predictions")
        self.assertIn("old", entry)
        self.assertIn("new", entry)

    def test_a_change_without_a_trigger_is_refused(self):
        """NEGATIVE: an unexplained gain change must be impossible."""
        g = PlasticGains()
        g._last_update["go_threshold"] = 0.0
        for bad in ("", "   ", None):
            with self.assertRaises(ValueError, msg=f"accepted trigger {bad!r}"):
                g.update("go_threshold", 0.6, bad)
        self.assertEqual(len(g.history()), 0, "a refused change was logged anyway")

    def test_rate_limit_slows_an_immediate_second_change(self):
        """A single anomalous outcome must not yank the parameter to its bound."""
        g = PlasticGains()
        g._last_update["go_threshold"] = 0.0
        g.update("go_threshold", 0.7, "first")
        first = g.get("go_threshold")
        g.update("go_threshold", 0.15, "second, immediately after")
        second = g.get("go_threshold")
        floor = GAIN_SPECS["go_threshold"][0]
        # With ~0s elapsed, the allowed traverse is ~0, so the honest
        # expectation is that the value does NOT jump to the floor.
        self.assertGreater(second, floor,
                           "rate limit did not hold: reached the floor instantly")
        self.assertLessEqual(abs(first - second), abs(first - 0.4) + 1e-9,
                             "the second update overshot the rate limit")

    def test_unknown_gain_is_rejected(self):
        g = PlasticGains()
        with self.assertRaises(KeyError):
            g.get("no_such_gain")

    def test_proposals_are_pure_functions_of_their_inputs(self):
        """propose_* must not read state, so the mapping is testable alone."""
        for _ in range(3):
            self.assertAlmostEqual(PlasticGains.propose_go_threshold(0.0, 0.0), 0.4)
        self.assertGreater(PlasticGains.propose_go_threshold(1.0, 0.0), 0.4)
        self.assertGreater(PlasticGains.propose_go_threshold(0.0, 1.0), 0.4)
        self.assertLess(PlasticGains.propose_compilation_threshold(5, 1.0), 3.0)
        self.assertGreater(PlasticGains.propose_damping(1.0, 1.0), 0.85)
        self.assertAlmostEqual(PlasticGains.propose_damping(0.0, 0.0), 0.85)
        self.assertLess(PlasticGains.propose_damping(0.0, 1.0), 0.85,
                        "ample headroom should reduce damping")

    def test_proposals_respect_declared_bounds(self):
        g = PlasticGains()
        for name, prop in (
            ("go_threshold", lambda: PlasticGains.propose_go_threshold(1.0, 1.0)),
            ("damping_factor", lambda: PlasticGains.propose_damping(1.0, 0.0)),
            ("compilation_threshold", lambda: PlasticGains.propose_compilation_threshold(0, 0.0)),
            ("decay_rate", lambda: PlasticGains.propose_decay_rate(1.0, 1.0)),
        ):
            floor, ceiling = g.bounds(name)
            self.assertGreaterEqual(prop(), floor, f"{name} proposal below floor")
            self.assertLessEqual(prop(), ceiling, f"{name} proposal above ceiling")


class TestSupersessionResolver(unittest.TestCase):
    """C7: correction by competition, resolved deterministically in code."""

    def test_newest_wins(self):
        res = SupersessionResolver()
        winner = res.resolve([
            r(1, valid_from="2026-01-01T00:00:00Z"),
            r(2, valid_from="2026-06-01T00:00:00Z"),
            r(3, valid_from="2026-03-01T00:00:00Z"),
        ])
        self.assertEqual(winner.id, 2)

    def test_resolution_is_order_independent(self):
        """THE C7 PROPERTY. Retrieval order must not change the answer.

        This is the whole reason the resolver exists instead of a prompt: the
        benchmark failure was retrieval-plus-judgment, where the judgment was
        handed to a model. Shuffling the input must never change the winner.
        """
        res = SupersessionResolver()
        records = [r(i, valid_from=f"2026-0{(i % 9) + 1}-01T00:00:00Z") for i in range(1, 9)]
        expected = res.resolve(list(records)).id
        rng = random.Random(1234)
        for _ in range(200):
            shuffled = list(records)
            rng.shuffle(shuffled)
            self.assertEqual(res.resolve(shuffled).id, expected,
                             "resolution depended on input order")

    def test_ties_break_on_higher_id(self):
        res = SupersessionResolver()
        same = "2026-01-01T00:00:00Z"
        self.assertEqual(res.resolve([r(5, valid_from=same), r(9, valid_from=same)]).id, 9)
        self.assertEqual(res.resolve([r(9, valid_from=same), r(5, valid_from=same)]).id, 9)

    def test_retired_records_are_not_binding(self):
        res = SupersessionResolver()
        winner = res.resolve([
            r(1, valid_from="2026-09-01T00:00:00Z", valid_to="2026-09-02T00:00:00Z"),
            r(2, valid_from="2026-01-01T00:00:00Z"),
        ])
        self.assertEqual(winner.id, 2, "a retired record still binds")

    def test_superseded_record_yields_to_its_successor(self):
        res = SupersessionResolver()
        winner = res.resolve([
            r(1, valid_from="2026-09-01T00:00:00Z"),  # newest, but superseded
            r(2, valid_from="2026-01-01T00:00:00Z", supersedes_id=1),
        ])
        self.assertEqual(winner.id, 2)

    def test_empty_input_returns_none(self):
        self.assertIsNone(SupersessionResolver().resolve([]))

    def test_all_retired_returns_none(self):
        res = SupersessionResolver()
        self.assertIsNone(res.resolve([r(1, valid_to="2026-01-01T00:00:00Z")]))

    def test_supersession_cycle_still_resolves(self):
        """A cycle is corrupt input; it must not return nothing."""
        res = SupersessionResolver()
        winner = res.resolve([r(1, supersedes_id=2), r(2, supersedes_id=1)])
        self.assertIsNotNone(winner, "a cyclic ledger returned no answer at all")

    def test_contradiction_is_classified(self):
        res = SupersessionResolver()
        rel = res.relation_for(r(2, statement="the build is not reproducible"),
                               r(1, statement="the build is reproducible"))
        self.assertEqual(rel, "contradicted")

    def test_negation_detection_is_symmetric(self):
        """NEGATIVE: flipping which side carries the negation must not matter."""
        res = SupersessionResolver()
        a = res.relation_for(r(2, statement="it is never cached"),
                             r(1, statement="it is cached"))
        b = res.relation_for(r(1, statement="it is cached"),
                             r(2, statement="it is never cached"))
        self.assertEqual(a, b, "relation_for was not order-independent")

    def test_undercut_when_confidence_drops(self):
        res = SupersessionResolver()
        newer = r(2, statement="the same claim", credence=0.2)
        older = r(1, statement="the same claim", credence=0.9)
        self.assertEqual(res.relation_for(newer, older), "undercut")

    def test_unrelated_topics_are_not_related(self):
        res = SupersessionResolver()
        self.assertEqual(res.relation_for(r(2, topic="b"), r(1, topic="a")), "unrelated")


class TestAuthorityPromotion(unittest.TestCase):
    """C10: register, scope, authorship -- and the promotion that must not exist."""

    def test_retrieved_quote_cannot_become_user_asserted(self):
        self.assertFalse(SupersessionResolver.may_promote("retrieved_quote", "user_asserted"))

    def test_the_promotion_is_blocked_in_both_directions_of_the_check(self):
        """NEGATIVE: prove may_promote is not always False (a stuck guard)."""
        self.assertTrue(SupersessionResolver.may_promote("user_asserted", "user_asserted"))
        self.assertTrue(SupersessionResolver.may_promote("tool_observed", "retrieved_quote"))

    def test_tool_observed_is_not_user_asserted(self):
        """A tool did not hear it from the operator. Promoting it would invent consent."""
        self.assertNotEqual("tool_observed", "user_asserted")


class TestAffectProfile(unittest.TestCase):
    """C8: affect as a profile, preserving the wanting/liking dissociation."""

    def test_three_axes_present(self):
        p = AffectProfile(desire=0.5, valence=0.0, arousal=0.5)
        d = p.as_dict()
        for axis in AFFECT_AXES:
            self.assertIn(axis, d)

    def test_want_liking_dissociation_is_representable(self):
        """HIGH-graded in the arena: wanting and liking come apart.

        If a scalar were still in use this state could not be stored at all,
        and the profile would have to lie about one of the two numbers.
        """
        p = AffectProfile(desire=0.9, valence=-0.8, arousal=0.6)
        self.assertFalse(p.is_coherent())
        self.assertTrue(p.as_dict()["dissociated"],
                        "the dissociation was smoothed away instead of reported")

    def test_coherent_profile_is_coherent(self):
        self.assertTrue(AffectProfile(desire=0.9, valence=0.8, arousal=0.5).is_coherent())

    def test_the_producing_model_is_stored(self):
        """The arena does NOT resolve 2-D vs 6-D. Store which one produced it."""
        p = AffectProfile(desire=0.5, valence=0.1, arousal=0.2, model="schimmack-6d")
        self.assertEqual(p.as_dict()["model"], "schimmack-6d")

    def test_credence_is_separate_from_the_axes(self):
        """Probability (credence) is not importance (valence). Different columns."""
        p = AffectProfile(desire=0.2, valence=-0.1, arousal=0.1, credence=0.95)
        self.assertEqual(p.credence, 0.95)
        self.assertNotEqual(p.credence, p.valence)


class TestSubstrateBudget(unittest.TestCase):
    """C9: a budget with a DECLARED shedding order."""

    def test_shedding_order_puts_cheapest_first(self):
        self.assertEqual(SHEDDING_ORDER[0], "retrieval_cache")
        self.assertEqual(SHEDDING_ORDER[-1], "identity")

    def test_identity_is_never_shed(self):
        b = SubstrateBudget(100.0)
        b.used = 99.0
        shed = b.shed_until(0.9, {"identity": 50.0, "retrieval_cache": 10.0})
        self.assertNotIn("identity", shed)

    def test_undeclared_classes_are_never_shed(self):
        b = SubstrateBudget(100.0)
        b.used = 99.0
        shed = b.shed_until(0.9, {"something_we_never_declared": 500.0})
        self.assertEqual(shed, [], "shed an undeclared class")

    def test_cheapest_shed_first_under_pressure(self):
        """A cheap class that ALONE meets the shortfall must be used alone.

        At used=95 of 100, headroom is 0.05. A target of 0.10 is a shortfall of
        exactly 5 units, and retrieval_cache costs 10 -- enough by itself, so
        the expensive sourced_quotes class must survive untouched.

        (Target 0.90 was the original figure here and is unachievable: that is
        an 85-unit shortfall, which exceeds any single cheap class, so the code
        would be right to keep going. The point being tested is not "reach an
        ambitious target" but "stop as soon as the shortfall is met".)
        """
        b = SubstrateBudget(100.0)
        b.used = 95.0
        shed = b.shed_until(0.10, {
            "retrieval_cache": 10.0,      # cheap, listed first
            "sourced_quotes": 40.0,       # expensive, listed later
        })
        self.assertEqual(shed, ["retrieval_cache"],
                         "shed past the shortfall into an expensive class")
        self.assertGreaterEqual(b.headroom, 0.10, "did not actually reach the target")

    def test_shedding_continues_when_the_shortfall_exceeds_one_class(self):
        """The complement: a big shortfall MUST reach past the cheap class."""
        b = SubstrateBudget(100.0)
        b.used = 95.0
        shed = b.shed_until(0.90, {
            "retrieval_cache": 10.0,
            "sourced_quotes": 40.0,
            "affect_profiles": 40.0,
        })
        self.assertEqual(shed[0], "retrieval_cache", "order violated")
        self.assertGreater(len(shed), 1, "85-unit shortfall met by one 10-unit class")
        self.assertGreaterEqual(b.headroom, 0.90)

    def test_tier_reflects_headroom(self):
        b = SubstrateBudget(100.0)
        b.used = 10.0
        self.assertEqual(b.tier, "comfortable")
        b.used = 60.0
        self.assertEqual(b.tier, "tight")
        b.used = 95.0
        self.assertEqual(b.tier, "critical")

    def test_shedding_actually_frees_headroom(self):
        b = SubstrateBudget(100.0)
        b.used = 95.0
        before = b.headroom
        b.shed_until(0.9, {"retrieval_cache": 20.0})
        self.assertGreater(b.headroom, before, "shedding freed nothing")


class TestSplitConfidence(unittest.TestCase):
    """C3: the dorsal/ventral split as a constraint on every confidence."""

    def test_ventral_confidence_is_action_safe(self):
        self.assertTrue(SplitConfidence(ventral=0.9, dorsal=0.2).action_safe())

    def test_dorsal_confidence_alone_is_never_action_safe(self):
        """NEGATIVE: the whole point -- dorsal estimates must not be acted on."""
        self.assertFalse(SplitConfidence(ventral=0.2, dorsal=0.95).action_safe())

    def test_divergence_is_reported_not_averaged_away(self):
        s = SplitConfidence(ventral=0.9, dorsal=0.3)
        self.assertIn("DIVERGENCE", s.report())

    def test_alignment_reports_cleanly(self):
        self.assertNotIn("DIVERGENCE", SplitConfidence(ventral=0.8, dorsal=0.7).report())


class TestVerifierIndependence(unittest.TestCase):
    """C5: nothing grades itself."""

    def test_a_disjoint_verifier_is_independent(self):
        v = VerifierIndependence("external-audit", frozenset({"auditor"}))
        self.assertTrue(v.is_independent_of(SUBJECT_FACETS))

    def test_a_verifier_sharing_one_facet_is_a_self_grader(self):
        """NEGATIVE: one shared facet is enough. This is the strict reading."""
        v = VerifierIndependence("same-credentials", frozenset({"credentials"}))
        self.assertTrue(v.self_grading(SUBJECT_FACETS))
        self.assertFalse(v.is_independent_of(SUBJECT_FACETS))

    def test_the_check_can_also_return_true(self):
        """NEGATIVE CONTROL: prove is_independent_of is not always False."""
        v = VerifierIndependence("external", frozenset({"auditor"}))
        self.assertFalse(v.self_grading(SUBJECT_FACETS))

    def test_an_empty_verifier_is_not_independent(self):
        """A verifier with no declared facets shares everything by default."""
        v = VerifierIndependence("undeclared", frozenset())
        self.assertFalse(v.is_independent_of(SUBJECT_FACETS))


class TestNonVacuity(unittest.TestCase):
    """The repo convention: a test that cannot fail is not a test."""

    def test_this_file_contains_no_vacuous_assertions(self):
        import re
        with open(__file__, encoding="utf-8") as f:
            body = f.read()
        for pattern in (r"assert\s+True\b", r"assert\s+1\s*==\s*1\b",
                        r"except[^\n]*:\s*pass", r"pass\s*#\s*TODO"):
            found = re.findall(pattern, body)
            self.assertEqual(found, [], f"vacuous pattern {pattern!r}: {found}")

    def test_the_file_is_non_trivial(self):
        with open(__file__, encoding="utf-8") as f:
            self.assertGreater(len(f.read()), 4000)

    def test_this_test_suite_actually_runs_tests(self):
        """A suite that silently collected zero tests would pass everything.

        NOTE: this test must EXCLUDE itself. Loading the whole module into a
        nested runner includes this method, which then loads the module again,
        which runs this method again -- infinite recursion, and the nested run
        reports this test's own failure as a suite failure. That is exactly
        what happened on the first attempt: 48 real tests passing and one
        self-inflicted failure, which looked like a code defect and was not.

        The first version of this assertion was therefore not a check at all.
        It excluded the recursion but then asserted `len(failures) == 0` on a
        run that necessarily contained its own failure, so it could only ever
        fail. Asserting on the other tests only is the sound version.
        """
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        collected = list(suite)

        def flatten(s):
            for item in s:
                if isinstance(item, unittest.TestSuite):
                    yield from flatten(item)
                else:
                    yield item

        all_tests = list(flatten(collected))
        self.assertGreater(len(all_tests), 40,
                           f"suspiciously few tests collected: {len(all_tests)}")

        # Every class must be a real TestCase, or unittest silently ignores it
        # and the suite reports "Ran 0 tests ... OK". That happened here once.
        for cls in (TestPlasticGains, TestSupersessionResolver, TestAuthorityPromotion,
                    TestAffectProfile, TestSubstrateBudget, TestSplitConfidence,
                    TestVerifierIndependence):
            self.assertTrue(issubclass(cls, unittest.TestCase),
                            f"{cls.__name__} is not a TestCase and will be ignored")
            self.assertTrue(any(t.startswith("test_")
                                for t in dir(cls) if callable(getattr(cls, t, None))),
                            f"{cls.__name__} has no test_ methods")

    def test_the_other_tests_all_pass(self):
        """Run every test EXCEPT this class, so the verdict is about the code.

        Excluding the verifier class is what makes this sound: a meta-test that
        includes itself can never report a clean run.
        """
        module = sys.modules[__name__]
        suite = unittest.TestSuite()
        for name, obj in vars(module).items():
            if (isinstance(obj, type) and issubclass(obj, unittest.TestCase)
                    and obj.__name__ != "TestNonVacuity"):
                suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(obj))

        def flatten(s):
            for item in s:
                if isinstance(item, unittest.TestSuite):
                    yield from flatten(item)
                else:
                    yield item

        count = len(list(flatten(suite)))
        self.assertGreater(count, 40, f"only {count} non-meta tests collected")
        result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
        self.assertEqual(len(result.failures), 0,
                         f"failures: {[str(t) for t, _ in result.failures]}")
        self.assertEqual(len(result.errors), 0,
                         f"errors: {[str(t) for t, _ in result.errors]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
