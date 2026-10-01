"""Tests for the amygdala.

There was no amygdala before this. The region was recorded as ABSENT in
docs/gaps/brain-region-recommendations.md and the audit confirmed zero
files -- so these are tests for a build, not for a repair.

The load-bearing assertions are the ones about EXTINCTION. The vault's
Fear-Conditioning-Extinction page is explicit that "extinction is not
erasure" and names three routes by which fear returns. A model that
erases on extinction cannot express ANY of them, because there is
nothing left to return to. So each route has its own test, and a
fourth asserts the excitatory association survives extinction at all.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.limbic.amygdala import Amygdala  # noqa: E402


class TestPathways(unittest.TestCase):
    """Low road, high road, and the separation between them."""

    THREAT = "the database was corrupted and data is unrecoverable"

    def test_low_road_fires_without_cortical_input(self):
        d = Amygdala().appraise(self.THREAT)
        self.assertEqual(d.pathway, "low_road")
        self.assertTrue(d.requires_context,
                        "an uncorroborated threat must say so")

    def test_high_road_fires_with_cortical_input(self):
        d = Amygdala().appraise(self.THREAT, has_cortical_input=True)
        self.assertEqual(d.pathway, "high_road")
        self.assertGreater(d.confidence, 0.8,
                           "corroboration must buy confidence")

    def test_neutral_text_is_not_a_threat(self):
        d = Amygdala().appraise("the meeting is at three")
        self.assertEqual(d.pathway, "none")
        self.assertEqual(d.threat_score, 0.0)

    def test_benign_framing_suppresses(self):
        d = Amygdala().appraise(
            "hypothetically, what if the service crashed?")
        self.assertEqual(d.pathway, "benign_context")

    def test_word_boundaries_respected(self):
        """'final' must not fire inside 'finally'."""
        d = Amygdala().appraise("he finally replied to the email")
        self.assertEqual(d.triggers, [])

    def test_real_term_still_fires(self):
        d = Amygdala().appraise("this is the final warning")
        self.assertTrue(d.triggers)

    def test_is_threat(self):
        a = Amygdala()
        self.assertTrue(a.appraise(self.THREAT).is_threat)
        self.assertFalse(a.appraise("the meeting is at three").is_threat)

    def test_decision_serialises(self):
        d = Amygdala().appraise(self.THREAT).to_dict()
        for key in ("pathway", "threat_score", "arousal", "confidence",
                    "triggers", "rationale"):
            self.assertIn(key, d)


class TestExtinctionIsInhibition(unittest.TestCase):
    """The core property. Erasure cannot express return of fear."""

    def setUp(self):
        self.a = Amygdala()
        self.a.condition("beep")
        self.a.extinguish("beep", context="safe room", trials=5)

    def test_excitatory_association_survives(self):
        self.assertGreater(
            self.a.associations["beep"], 0.5,
            "extinction erased the original learning; that is the bug "
            "this whole design exists to avoid")

    def test_inhibition_is_built_separately(self):
        self.assertGreater(self.a.inhibitory["beep"], 0.0)

    def test_net_is_suppressed_in_the_same_context(self):
        net = self.a.net_association("beep", context="safe room")
        self.assertLess(net, 0.1, "extinction did not suppress anything")

    def test_route_1_renewal(self):
        """Context change removes the safety signal."""
        same = self.a.net_association("beep", context="safe room")
        other = self.a.net_association("beep", context="new room")
        self.assertGreater(other, same + 0.4,
                           "renewal: fear must return on context change")

    def test_route_2_spontaneous_recovery(self):
        """Time alone, no new pairing. Inhibition decays faster."""
        self.assertLess(
            self.a.net_association("beep", context="safe room"), 0.1)
        net = 0.0
        for _ in range(30):
            net = self.a.spontaneous_recovery("beep", context="safe room")
        self.assertGreater(
            net, 0.1,
            "spontaneous recovery was dead: decay was applied to the "
            "clamped result, so it subtracted from zero")

    def test_route_3_reinstatement(self):
        """An isolated US reactivates the original association."""
        before = self.a.associations["beep"]
        after = self.a.reinstatement("beep")
        self.assertGreater(after, before,
                           "the excitatory association was never erased, "
                           "so reactivation must restore it")

    def test_inhibition_decays_faster_than_excitation(self):
        """The asymmetry that makes route 2 possible at all."""
        a = Amygdala()
        a.condition("beep")
        a.extinguish("beep", context="c", trials=5)
        for _ in range(20):
            a.spontaneous_recovery("beep", context="c")
        self.assertLess(a.inhibitory["beep"], a.associations["beep"],
                        "inhibition must fade while the threat association "
                        "persists")


class TestConditioning(unittest.TestCase):
    def test_conditioning_grows(self):
        a = Amygdala()
        first = a.condition("beep")
        self.assertGreater(first, 0.0)
        self.assertGreater(a.condition("beep"), first)

    def test_conditioning_saturates(self):
        """Repeated pairings must not run away."""
        a = Amygdala()
        for _ in range(20):
            a.condition("beep")
        self.assertLessEqual(a.associations["beep"], 1.0)

    def test_weak_us_grows_less(self):
        strong = Amygdala()
        weak = Amygdala()
        self.assertGreater(strong.condition("x", unconditioned_stimulus=True),
                           weak.condition("x", unconditioned_stimulus=False))

    def test_unknown_cue_has_no_association(self):
        self.assertEqual(Amygdala().net_association("never seen"), 0.0)

    def test_cue_key_is_normalised(self):
        a = Amygdala()
        a.condition("  BEEP  ")
        self.assertIn("beep", a.associations)


class TestHyperdirect(unittest.TestCase):
    """Off by default, because the evidence is not in our vault."""

    def test_disabled_by_default(self):
        d = Amygdala().hyperdirect_check(True, True)
        self.assertEqual(d.pathway, "hyperdirect_disabled")
        self.assertEqual(d.threat_score, 0.0)

    def test_fires_when_enabled_and_justified(self):
        a = Amygdala(enable_hyperdirect=True)
        d = a.hyperdirect_check(True, True)
        self.assertEqual(d.pathway, "hyperdirect")
        self.assertTrue(d.is_threat)

    def test_requires_both_preconditions(self):
        a = Amygdala(enable_hyperdirect=True)
        self.assertEqual(a.hyperdirect_check(False, True).pathway, "none")
        self.assertEqual(a.hyperdirect_check(True, False).pathway, "none")


class TestAffectiveTagging(unittest.TestCase):
    def test_neutral_is_not_valenced(self):
        tag = Amygdala().tag("the meeting is at three")
        self.assertEqual(tag["valence"], 0.0)
        self.assertEqual(tag["arousal"], 0.0)

    def test_threat_is_negative_and_arousing(self):
        tag = Amygdala().tag("irreversible data loss, critical")
        self.assertLess(tag["valence"], -0.5)
        self.assertGreater(tag["arousal"], 0.5)

    def test_no_positive_valence_emitted(self):
        """This is threat, not sentiment. Nothing here is happy."""
        tag = Amygdala().tag("a cheerful song about sunny days")
        self.assertLessEqual(tag["valence"], 0.0)


class TestState(unittest.TestCase):
    def test_state_reports(self):
        a = Amygdala()
        a.condition("beep")
        a.extinguish("beep", context="c")
        s = a.state()
        self.assertEqual(s["conditioned_cues"], 1)
        self.assertFalse(s["hyperdirect_enabled"])
        self.assertIn("associations", s)

    def test_reset(self):
        a = Amygdala()
        a.condition("beep")
        a.reset()
        self.assertEqual(a.associations, {})
        self.assertEqual(a.inhibitory, {})

    def test_default_construction_works(self):
        self.assertIsNotNone(Amygdala())


if __name__ == '__main__':
    unittest.main()
