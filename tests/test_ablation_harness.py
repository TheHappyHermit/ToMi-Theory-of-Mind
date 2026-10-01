"""Tests for the ablation harness.

The harness has one job that matters more than its numbers: it must not
report a result for a workload that never exercised the subsystem. Every
test here is about that failure mode, because it is the one that produced
a confidently wrong answer during development.
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from brain.cortex.wiring import GATE_NAMES  # noqa: E402
from scripts.ablation_harness import (  # noqa: E402
    LOADS, MUST_FIRE, AblationRun, run_load,
)


class TestWorkloadValidity(unittest.TestCase):
    """A workload that fires nothing must be reported INVALID."""

    def test_baseline_load_is_invalid(self):
        """Light load fires no gates, and must SAY so.

        This is the ZenBrain trap. The harness exists because mild-load
        ablation under-reports contribution; if this test ever passes
        silently, the harness has started lying.
        """
        res = run_load("baseline", trials=1)
        self.assertFalse(res["valid"])
        self.assertIsNotNone(res["invalid_reason"])

    def test_every_gate_required(self):
        """All six gates must fire, not a hand-picked subset.

        A partial MUST_FIRE is how a dead gate reports a clean zero
        delta and reads as 'this subsystem costs nothing'.
        """
        self.assertEqual(set(MUST_FIRE), set(GATE_NAMES))

    def test_stressed_load_uses_system_2_mode(self):
        """The gates only fire under SYSTEM_2.

        'chat' and 'deliberate' are both silently wrong: every gate
        returns early and the run looks like a valid negative result.
        """
        for text, mode in LOADS["stressed"]:
            self.assertEqual(
                mode, "SYSTEM_2",
                "stressed turn %r uses mode %r; gates require SYSTEM_2"
                % (text[:30], mode))

    def test_stressed_load_is_valid(self):
        """The real workload must exercise all six gates."""
        res = run_load("stressed", trials=1)
        self.assertTrue(res["valid"], res["invalid_reason"])
        for gate in GATE_NAMES:
            self.assertGreater(
                res["control_fired"][gate], 0,
                "gate %s never fired under the stressed load" % gate)


class TestSuppression(unittest.TestCase):
    """Ablation must actually suppress, and must not leak."""

    def test_disabled_gate_does_not_fire(self):
        run = AblationRun(["counterfactual"]).measure(LOADS["stressed"])
        self.assertEqual(run["fired"].get("counterfactual", 0), 0)

    def test_other_gates_still_fire_when_one_disabled(self):
        """Suppressing one gate must not silence the rest."""
        run = AblationRun(["counterfactual"]).measure(LOADS["stressed"])
        self.assertGreater(run["fired"].get("defeater_graph", 0), 0)

    def test_suppression_does_not_leak_across_turns(self):
        """A leaked wrapper would silently shrink every later trial.

        This is the failure that would make an ablation look free: the
        gate stays off for the rest of the run, so the control and the
        ablation measure the same thing.
        """
        run = AblationRun(["defeater_graph"]).measure(LOADS["stressed"])
        # every turn after the first must still evaluate the other gates
        self.assertEqual(run["turns_with_any_subsystem"], run["turns"])

    def test_control_fires_every_gate(self):
        run = AblationRun().measure(LOADS["stressed"])
        for gate in GATE_NAMES:
            self.assertGreater(run["fired"].get(gate, 0), 0,
                               "%s did not fire in the control" % gate)

    def test_no_errors_under_stress(self):
        run = AblationRun().measure(LOADS["stressed"])
        self.assertEqual(run["errors"], 0)


class TestArtifact(unittest.TestCase):
    """Evidence must be honest about its own limits."""

    def test_result_records_known_limits(self):
        res = run_load("stressed", trials=1)
        self.assertTrue(res["known_limits"])
        joined = " ".join(res["known_limits"]).lower()
        self.assertIn("marginal", joined)

    def test_result_is_serialisable(self):
        res = run_load("stressed", trials=1)
        json.dumps(res)  # must not raise

    def test_committed_results_are_valid(self):
        """A checked-in result file must not be a known-invalid run."""
        for p in (REPO / "docs" / "audit").glob("ablation-*.json"):
            data = json.loads(p.read_text())
            if p.stem == "ablation-stressed":
                self.assertTrue(data["valid"],
                                "%s is committed INVALID" % p.name)


if __name__ == "__main__":
    unittest.main()
