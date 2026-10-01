#!/usr/bin/env python3
"""
brain.limbic.somatic — Antonio Damasio's Somatic Marker Engine.

Implements the Somatic Marker Hypothesis:
Emotions and affective bodily/operational feelings guide decision-making by rapidly
biasing choices before conscious deliberative calculation begins.

Persistent storage in SQLite/Postgres `somatic_markers` table.
"""

import sqlite3
from typing import Dict, Any, Optional, Tuple

from brain.util.timeutil import utc_now_iso


class SomaticMarkerEngine:
    """
    Somatic Marker Engine:
    Evaluates proposed action/target patterns against historical somatic markers.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def assess(self, action_pattern: str, target_pattern: str) -> Tuple[float, str]:
        """
        Assess visceral bias for an action/target pair.
        Returns:
            (valence_bias: float [-1.0 to 1.0], rationale: str)
        """
        if not self.db_path:
            return 0.0, "No somatic memory database configured."

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT valence_bias, sample_count
                FROM somatic_markers
                WHERE action_pattern = ? AND target_pattern = ?
            """, (action_pattern, target_pattern))
            row = cur.fetchone()
            conn.close()

            if not row:
                return 0.0, "Neutral: No prior somatic marker recorded."

            bias, count = row
            if bias < -0.5:
                warning = f"Aversive Somatic Warning ({bias:.2f}, n={count}): Prior executions yielded severe negative outcomes."
            elif bias > 0.5:
                warning = f"Appetitive Somatic Endorsement ({bias:.2f}, n={count}): Prior executions reliably succeeded."
            else:
                warning = f"Moderate Somatic Bias ({bias:.2f}, n={count})."

            return bias, warning
        except Exception as e:
            return 0.0, f"Somatic lookup failed: {e}"

    def record_experience(self, action_pattern: str, target_pattern: str, outcome_success: bool, intensity: float = 0.3):
        """
        Update or create somatic marker following an action's execution.
        """
        if not self.db_path:
            return

        shift = intensity if outcome_success else -intensity

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("""
                SELECT valence_bias, sample_count
                FROM somatic_markers
                WHERE action_pattern = ? AND target_pattern = ?
            """, (action_pattern, target_pattern))
            row = cur.fetchone()

            if row:
                old_bias, count = row
                # Running weighted moving average
                new_bias = max(-1.0, min(1.0, (old_bias * count + shift) / (count + 1)))
                cur.execute("""
                    UPDATE somatic_markers
                    SET valence_bias = ?, sample_count = sample_count + 1, last_experienced = ?
                    WHERE action_pattern = ? AND target_pattern = ?
                """, (new_bias, utc_now_iso(), action_pattern, target_pattern))
            else:
                cur.execute("""
                    INSERT INTO somatic_markers (action_pattern, target_pattern, valence_bias, sample_count, last_experienced)
                    VALUES (?, ?, ?, 1, ?)
                """, (action_pattern, target_pattern, max(-1.0, min(1.0, shift)),
                        utc_now_iso()))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SomaticMarkerEngine] Failed to record experience: {e}")
