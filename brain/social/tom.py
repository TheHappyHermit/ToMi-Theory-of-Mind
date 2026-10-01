#!/usr/bin/env python3
"""
brain.social.tom — Recursive Theory of Mind (ToM) User Modeling.

Implements cognitive Theory of Mind:
- Tracks user epistemic states, knowledge boundaries, and mental models.
- Level 1 ToM: "What does the user believe or know?"
- Level 2 ToM: "What does the user believe the agent knows or intends?"
- False-Belief / Discrepancy Detection: Flags discrepancies between user assumptions
  and verified empirical ground truth to deliver gentle, non-condescending calibrations.
"""

import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from brain.util.timeutil import utc_now_iso


class UserMentalState:
    def __init__(self, domain: str, attributed_belief: str, ground_truth: str, discrepancy: bool = False):
        self.domain = domain
        self.attributed_belief = attributed_belief
        self.ground_truth = ground_truth
        self.discrepancy = discrepancy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "attributed_belief": self.attributed_belief,
            "ground_truth": self.ground_truth,
            "discrepancy": self.discrepancy,
        }


class TheoryOfMind:
    """
    Theory of Mind Engine: Tracks and models user mental state.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def update_model(self, domain: str, attributed_belief: str, ground_truth: str) -> UserMentalState:
        """
        Record or update the agent's model of the user's belief regarding a domain.
        Automatically flags discrepancies between user belief and ground truth.
        """
        discrepancy = attributed_belief.strip().lower() != ground_truth.strip().lower()
        state = UserMentalState(domain, attributed_belief, ground_truth, discrepancy)

        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO user_mental_models (domain, attributed_belief, ground_truth, discrepancy, last_verified)
                    VALUES (?, ?, ?, ?, ?)
                """, (domain, attributed_belief, ground_truth, 1 if discrepancy else 0,
                        utc_now_iso()))
                conn.commit()
                conn.close()
            except Exception as e:
                # A discrepancy that failed to persist is a discrepancy the brain
                # will not learn from, so this must be visible in the logs.
                logging.getLogger(__name__).error(
                    "user mental model not persisted: %s: %s",
                    type(e).__name__, e, exc_info=True)

        return state

    def check_discrepancies(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all active discrepancies where the user's belief diverges from ground truth."""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if domain:
                cur.execute("""
                    SELECT domain, attributed_belief, ground_truth, last_verified
                    FROM user_mental_models
                    WHERE discrepancy = 1 AND domain = ?
                    ORDER BY id DESC LIMIT 5
                """, (domain,))
            else:
                cur.execute("""
                    SELECT domain, attributed_belief, ground_truth, last_verified
                    FROM user_mental_models
                    WHERE discrepancy = 1
                    ORDER BY id DESC LIMIT 10
                """)
            rows = cur.fetchall()
            conn.close()

            return [
                {
                    "domain": r[0],
                    "attributed_belief": r[1],
                    "ground_truth": r[2],
                    "last_verified": r[3],
                    "pedagogical_nudge": f"Note: User assumes '{r[1]}' but verified state is '{r[2]}'. Tactfully clarify.",
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[TheoryOfMind] Failed to query discrepancies: {e}")
            return []
