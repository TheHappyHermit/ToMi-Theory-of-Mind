#!/usr/bin/env python3
"""
brain.basal_ganglia.action_gate — Striatal Action Arbitration & Gating.

Implements the classic neurocomputational model of the Basal Ganglia:
1. Direct Pathway (Go): Promotes selected motor/tool action when expected utility > threshold.
2. Indirect Pathway (No-Go): Suppresses actions when risk, somatic penalty, or conflict exceeds tolerance.
3. Hyperdirect Pathway (Emergency Brake): Rapidly arrests all active processing upon catastrophic alerts.
"""

from typing import Dict, Any, Tuple, Optional


class ActionGate:
    """
    Arbitrates candidate actions between competing alternatives.
    """

    def __init__(self, go_threshold: float = 0.4):
        self.go_threshold = go_threshold

    def evaluate_pathways(
        self,
        candidate_action: str,
        expected_utility: float,
        somatic_bias: float,
        conflict_level: float,
        emergency_alert: bool = False,
    ) -> Tuple[str, float, str]:
        """
        Evaluate candidate action through the three basal ganglia pathways.
        Returns:
            (disposition: "GO" | "NO_GO" | "HYPERDIRECT_BRAKE", net_drive: float, rationale: str)
        """
        # 1. Hyperdirect Pathway check (Emergency Brake)
        if emergency_alert:
            return "HYPERDIRECT_BRAKE", -1.0, "Hyperdirect Pathway Triggered: Emergency halt on all execution."

        # 2. Direct Pathway drive (Go)
        # Utility [0..1] boosted by positive somatic bias [0..1]
        go_drive = expected_utility + max(0.0, somatic_bias * 0.5)

        # 3. Indirect Pathway drive (No-Go)
        # Driven by conflict level [0..1] and negative somatic bias [-1..0]
        nogo_drive = conflict_level + max(0.0, -somatic_bias * 0.7)

        net_drive = go_drive - nogo_drive

        if net_drive >= self.go_threshold:
            return "GO", round(net_drive, 3), f"Go pathway dominant (net_drive={net_drive:.2f} >= {self.go_threshold}). Action permitted."
        else:
            return "NO_GO", round(net_drive, 3), f"No-Go pathway dominant (net_drive={net_drive:.2f} < {self.go_threshold}). Action suppressed or queued for confirmation."
