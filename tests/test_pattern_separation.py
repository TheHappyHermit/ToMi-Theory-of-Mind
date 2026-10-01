"""Tests for geometric pattern separation.

The bug these exist to prevent: pattern separation was a SHA-256 hash,
which is a non-geometric function used to solve a geometric problem. Our
own Oracle vault states the failure exactly --

    "A hash is a maximally non-geometric function used to solve a
     geometric problem. It is not a weak implementation; it is the
     wrong function class."
    "You cannot compute distance between two hashes, so you cannot
     measure whether separation occurred."

So the tests below assert GEOMETRY, not just "returns a string". A hash
implementation would pass any test that only checked determinism or
uniqueness, and would fail every one of these.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.hippocampus.pattern_separation import (  # noqa: E402
    PatternSeparator, tokenize,
)
from brain.hippocampus.replay import HippocampalReplayEngine  # noqa: E402


class TestGeometry(unittest.TestCase):
    """The property the hash could not provide."""

    def setUp(self):
        self.s = PatternSeparator()

    def test_near_duplicates_are_near(self):
        pairs = [
            ("the deploy failed on staging", "the deploy failed on production"),
            ("port 5433 is in use by postgres", "port 5433 is in use by pgvector"),
            ("alice owns the verifier", "bob owns the verifier"),
        ]
        for a, b in pairs:
            with self.subTest(a=a[:30]):
                self.assertGreater(
                    self.s.similarity(a, b), 0.6,
                    "one-word-apart cues must be measurably close")

    def test_unrelated_are_far(self):
        pairs = [
            ("the deploy failed on staging", "a paper on somatosensory neurons"),
            ("port 5433 is in use", "the hippocampus replays episodes"),
        ]
        for a, b in pairs:
            with self.subTest(a=a[:30]):
                self.assertLess(
                    self.s.similarity(a, b), 0.4,
                    "unrelated cues must be measurably distant")

    def test_near_and_far_do_not_overlap(self):
        """The actual separation property, asserted as an ordering."""
        near = [("the deploy failed on staging", "the deploy failed on production"),
                ("port 5433 is in use by postgres", "port 5433 is in use by pgvector")]
        far = [("the deploy failed on staging", "a paper on somatosensory neurons"),
               ("port 5433 is in use", "the hippocampus replays episodes")]
        self.assertGreater(
            min(self.s.similarity(*p) for p in near),
            max(self.s.similarity(*p) for p in far),
            "similarity must order near-duplicates above unrelated pairs; "
            "a hash cannot satisfy this at all")

    def test_identical_text_is_distance_zero(self):
        """A hash cannot do this either -- it changes identical input."""
        self.assertAlmostEqual(self.s.distance("same", "same"), 0.0, places=9)

    def test_distance_is_bounded(self):
        for a, b in [("abc", "abc"), ("abc", "xyz"), ("", "abc")]:
            d = self.s.distance(a, b)
            self.assertGreaterEqual(d, 0.0)
            self.assertLessEqual(d, 2.0 + 1e-9)

    def test_empty_string_is_handled(self):
        self.assertEqual(len(self.s.embed("")), self.s.dim)
        self.assertEqual(self.s.similarity("", "abc"), 0.0)


class TestDeterminism(unittest.TestCase):
    def test_same_text_same_vector_across_instances(self):
        a = PatternSeparator().embed("stable")
        b = PatternSeparator().embed("stable")
        self.assertEqual(a, b,
                         "two engines must agree; a random seed would not")

    def test_repeated_calls_are_stable(self):
        s = PatternSeparator()
        self.assertEqual(s.embed("x"), s.embed("x"))

    def test_dim_is_configurable(self):
        self.assertEqual(len(PatternSeparator(dim=64).embed("x")), 64)

    def test_tiny_dim_rejected(self):
        with self.assertRaises(ValueError):
            PatternSeparator(dim=4)

    def test_tokenizer(self):
        self.assertEqual(tokenize("Hello, World! 42"),
                         ["hello", "world", "42"])


class TestSeparate(unittest.TestCase):
    def setUp(self):
        self.s = PatternSeparator()

    def test_reports_nearest_prior(self):
        r = self.s.separate(
            "the deploy failed on production",
            prior_cues=[("the deploy failed on staging", None),
                        ("a paper on somatosensory neurons", None)])
        self.assertEqual(r["nearest_prior"], "the deploy failed on staging")
        self.assertGreater(r["nearest_similarity"], 0.5)

    def test_detects_a_collision(self):
        """A near-duplicate must be reported as NOT separated."""
        r = self.s.separate(
            "the deploy failed on production",
            prior_cues=[("the deploy failed on production", None)])
        self.assertFalse(r["separated"])
        self.assertTrue(r["collisions"])

    def test_separates_genuinely_distinct(self):
        r = self.s.separate(
            "the deploy failed on production",
            prior_cues=[("a paper on somatosensory neurons", None)])
        self.assertTrue(r["separated"])
        self.assertFalse(r["collisions"])

    def test_no_priors_is_trivially_separated(self):
        r = self.s.separate("anything")
        self.assertTrue(r["separated"])
        self.assertIsNone(r["nearest_prior"])

    def test_code_is_a_label_not_a_distance(self):
        """Two codes being close means nothing; that is the point."""
        s = PatternSeparator()
        a, b = "the deploy failed", "the deploy failed on production"
        self.assertNotEqual(s.code(s.embed(a)), s.code(s.embed(b)))
        # yet they are geometrically close
        self.assertGreater(s.similarity(a, b), 0.6)


class TestEngineIntegration(unittest.TestCase):
    """The engine must expose the geometry, not just a label."""

    def test_separation_report_measures_against_recorded_traces(self):
        e = HippocampalReplayEngine()
        e.record_episode("1", "the deploy failed on staging", "staging logs",
                         surprise_score=0.5, valence=-0.5)
        r = e.separation_report("the deploy failed on production")
        self.assertEqual(r["nearest_prior"], "the deploy failed on staging")
        self.assertGreater(r["nearest_similarity"], 0.5)

    def test_legacy_method_still_returns_a_string(self):
        e = HippocampalReplayEngine()
        self.assertIsInstance(e.pattern_separation("x"), str)

    def test_legacy_method_is_deterministic(self):
        e = HippocampalReplayEngine()
        self.assertEqual(e.pattern_separation("x"),
                         e.pattern_separation("x"))

    def test_no_hashlib_in_replay(self):
        """Guard against the hash creeping back in.

        The original defect was `hashlib.sha256(...).hexdigest()`. This
        asserts the module no longer reaches for a hash to represent an
        episode at all.
        """
        src = (REPO / 'brain' / 'hippocampus' / 'replay.py').read_text(
            encoding='utf-8')
        self.assertNotIn('hashlib.sha256', src)
        self.assertNotIn('import hashlib', src)


if __name__ == '__main__':
    unittest.main()
