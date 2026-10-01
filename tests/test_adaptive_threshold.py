"""Tests for the adaptive thalamic threshold.

The constant it replaces, 0.35, was borrowed from one observation and
compared against a saliency score whose distribution depends on the
corpus and the active context. The failure modes are silent in both
directions -- too high and the gate goes quietly blind, too low and it
does no work -- because evaluate_admission returns a boolean either way.

So these tests assert the two things that matter: that the threshold
TRACKS the distribution it sees, and that it stays INSIDE its bounds
when the input is degenerate.
"""
import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.thalamus.adaptive_threshold import AdaptiveThreshold  # noqa: E402
from brain.thalamus.attention import AttentionalGate  # noqa: E402


def feed(t, values, useful=True, seed=11):
    random.seed(seed)
    for raw in values:
        s = random.gauss(raw, 0.05)
        t.observe_admission(s, admitted=s >= t.threshold, useful=useful)
    return t


class TestTracking(unittest.TestCase):
    """The threshold must follow the distribution, not sit at 0.35."""

    def test_follows_a_high_saliency_regime_up(self):
        t = feed(AdaptiveThreshold(), [0.8] * 200)
        self.assertGreater(t.threshold, 0.6)

    def test_follows_a_low_saliency_regime_down(self):
        t = feed(AdaptiveThreshold(), [0.2] * 200)
        self.assertLess(t.threshold, 0.35)

    def test_follows_a_regime_change(self):
        t = feed(AdaptiveThreshold(), [0.2] * 150)
        low = t.threshold
        feed(t, [0.8] * 150)
        self.assertGreater(t.threshold, low + 0.3,
                           "a sustained shift must move the threshold")

    def test_admission_rate_near_target(self):
        t = AdaptiveThreshold(target_rate=0.25)
        feed(t, [0.5] * 300, seed=5)
        self.assertLess(abs(t._recent_rate() - 0.25), 0.20)

    def test_starts_at_the_initial_value(self):
        t = AdaptiveThreshold(initial=0.42)
        self.assertEqual(t.threshold, 0.42)

    def test_refuses_to_adapt_before_enough_samples(self):
        """Below min_samples the initial value must survive untouched.

        Adapting from two observations is how a controller becomes
        confidently wrong.
        """
        t = AdaptiveThreshold(min_samples=50, initial=0.35)
        t.observe_admission(0.99, admitted=True, useful=True)
        t.observe_admission(0.01, admitted=False, useful=False)
        self.assertEqual(t.threshold, 0.35)
        self.assertFalse(t.is_calibrated)


class TestWasteSignal(unittest.TestCase):
    """Rate-matching alone admits the wrong things happily."""

    def test_useless_admissions_raise_the_bar(self):
        t = feed(AdaptiveThreshold(), [0.5] * 250, useful=False)
        self.assertGreater(t.threshold, 0.35,
                           "admitting things that do not matter must "
                           "raise the threshold, not just hold the rate")

    def test_useful_admissions_do_not_raise(self):
        """Useful admissions must not trigger the waste correction.

        The bar here is the 75th percentile of the observed
        distribution, which for mean 0.5 / sd 0.05 is ~0.54 -- so the
        assertion is that the threshold sits near the quantile, not near
        the 0.35 default. An earlier version of this test asserted
        < 0.45, which was simply wrong about where a 75th percentile of
        that distribution falls; the code was right.
        """
        t = feed(AdaptiveThreshold(), [0.5] * 250, useful=True)
        self.assertLess(t.threshold, 0.60)
        self.assertGreater(t.threshold, 0.45)

    def test_unknown_usefulness_does_not_penalise(self):
        """useful=None means "not knowable", not "useless"."""
        t = AdaptiveThreshold()
        for _ in range(200):
            t.observe_admission(0.5, admitted=True, useful=None)
        self.assertEqual(t._waste_streak, 0)


class TestBounds(unittest.TestCase):
    def test_all_zero_input_clamps_low(self):
        t = AdaptiveThreshold()
        for _ in range(300):
            t.observe_admission(0.0, admitted=False, useful=False)
        self.assertGreaterEqual(t.threshold, 0.05)
        self.assertLessEqual(t.threshold, 0.95)

    def test_all_one_input_clamps_high(self):
        t = AdaptiveThreshold()
        for _ in range(300):
            t.observe_admission(1.0, admitted=True, useful=True)
        self.assertLessEqual(t.threshold, 0.95)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(TypeError):
            AdaptiveThreshold(nonsense=1)

    def test_reset_restores_initial(self):
        t = feed(AdaptiveThreshold(initial=0.33), [0.9] * 200)
        self.assertNotEqual(t.threshold, 0.33)
        t.reset()
        self.assertEqual(t.threshold, 0.33)
        self.assertEqual(t.samples, 0)
        self.assertFalse(t.is_calibrated)

    def test_reservoir_is_bounded(self):
        t = AdaptiveThreshold(reservoir=32)
        feed(t, [0.5] * 500)
        self.assertLessEqual(t.samples, 32)


class TestGateIntegration(unittest.TestCase):
    """Wiring: opt-in, observable, and a no-op when disabled."""

    def test_default_is_not_adaptive(self):
        g = AttentionalGate()
        self.assertFalse(g.is_adaptive)
        self.assertIsNone(g.threshold_stats())
        self.assertIsNone(g.observe_admission(0.5, True, True))
        self.assertEqual(g.saliency_threshold, 0.35,
                         "the default threshold must not move")

    def test_adaptive_flag_engages_it(self):
        g = AttentionalGate(adaptive=True)
        self.assertTrue(g.is_adaptive)
        self.assertIsNotNone(g.threshold_stats())

    def test_observe_updates_the_live_threshold(self):
        g = AttentionalGate(adaptive=True)
        for _ in range(200):
            g.observe_admission(0.9, admitted=True, useful=True)
        self.assertGreater(g.saliency_threshold, 0.5,
                           "the gate must use the learned value, not a copy")

    def test_existing_construction_still_works(self):
        g = AttentionalGate(saliency_threshold=0.5, active_context="x")
        self.assertEqual(g.saliency_threshold, 0.5)
        admitted, score, disp = g.evaluate_admission("a critical error here")
        self.assertIsInstance(admitted, bool)
        self.assertIn(disp, ("admit", "compress", "attenuate"))


if __name__ == '__main__':
    unittest.main()
