#!/usr/bin/env python3
"""
brain.limbic.valence — Affective State & Allostatic Load Engine.

Models:
- Epistemic Valence: (-1.0 = deep frustration/failure to +1.0 = breakthrough/triumph).
- Epistemic Arousal: (0.0 = calm/quiescent to 1.0 = high urgency/alarm).
- Allostatic Load: Cumulative cognitive strain and stress from sustained failures,
  recovering during successful resolution or idle consolidation.
- Curiosity Drive: Intrinsic reward for novelty, knowledge gap reduction, and exploration.
"""

from typing import Dict, Any


class CognitiveValenceEngine:
    """
    Affective and Allostatic State Tracker for Hermes Brain.
    Provides internal emotional feedback to modulate cognitive exploration vs exploitation.
    """

    def __init__(self):
        self.valence: float = 0.0        # -1.0 to 1.0
        self.arousal: float = 0.2        # 0.0 to 1.0
        self.allostatic_load: float = 0.0 # 0.0 to 1.0 (stress accumulation)
        self.curiosity: float = 0.5      # 0.0 to 1.0

    def record_outcome(self, success: bool, magnitude: float = 0.2, novelty: float = 0.1):
        """
        Update emotional and allostatic metrics following an action outcome.
        """
        if success:
            # Positive valence shift, lower allostatic load, moderate arousal
            self.valence = min(1.0, self.valence + magnitude)
            self.allostatic_load = max(0.0, self.allostatic_load - (magnitude * 0.5))
            self.arousal = max(0.1, self.arousal - (magnitude * 0.2))
            # Novelty feeds curiosity
            self.curiosity = min(1.0, self.curiosity + (novelty * 0.3))
        else:
            # Negative valence shift, increase allostatic load, spike arousal
            self.valence = max(-1.0, self.valence - magnitude)
            self.allostatic_load = min(1.0, self.allostatic_load + (magnitude * 0.8))
            self.arousal = min(1.0, self.arousal + (magnitude * 0.5))
            # Prolonged frustration dampens curiosity if allostatic load is too high
            if self.allostatic_load > 0.7:
                self.curiosity = max(0.1, self.curiosity - 0.2)

    def rest_and_recover(self, rate: float = 0.2):
        """Called during idle or sleep replay to dissipate allostatic load."""
        self.allostatic_load = max(0.0, self.allostatic_load - rate)
        self.arousal = max(0.1, self.arousal - rate)
        self.valence = self.valence * 0.5  # Reverts toward baseline 0

    def get_state(self) -> Dict[str, Any]:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "allostatic_load": round(self.allostatic_load, 3),
            "curiosity": round(self.curiosity, 3),
            "affective_summary": self._describe_affect(),
        }

    def _describe_affect(self) -> str:
        if self.allostatic_load > 0.8:
            return "Cognitive Exhaustion / High Allostatic Load (Caution Required)"
        if self.valence > 0.5:
            return "Confident & Flow State"
        if self.valence < -0.4:
            return "Perplexed / Frustrated (Deliberation Needed)"
        if self.arousal > 0.7:
            return "High Alertness / Crisis Mode"
        return "Equanimous & Attentive"
