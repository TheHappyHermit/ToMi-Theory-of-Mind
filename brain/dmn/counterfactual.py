#!/usr/bin/env python3
"""
brain.dmn.counterfactual — counterfactual branch records and regret lessons.

WHAT THIS DOES NOT DO
This does not implement Pearl's third rung. A genuine counterfactual requires a
structural causal model, abduction to infer the exogenous states, and the
do-operator to intervene. None of those are here, and a counterfactual cannot
be recovered from a table of strings after the fact.

What this actually does is record a counterfactual branch that something else
already evaluated, and keep the lesson extracted from it. Every row is the
caller's claim, not a derivation. The columns are named accordingly: they are
'actual_path' and 'counterfactual_path' rather than 'counterfactual_effect',
because nothing here establishes that the alternative would have produced a
different outcome. "We did A, we believe B would have been better" is a
judgement; "doing B would have caused X" is a causal claim this module cannot
support.

That distinction matters when reading the table. These rows are a record of
deliberation, and they are only as good as the reasoning that filled them in.
"""

import logging
import sqlite3
from typing import Dict, Any, List, Optional

from brain.util.timeutil import utc_now_iso


class CounterfactualEngine:
    """
    Stores counterfactual branches and the lessons drawn from them.

    Not a simulator. It has no model of the world to simulate against, which is
    why every field is supplied by the caller.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def analyze_regret(
        self,
        trigger_event: str,
        actual_path: str,
        counterfactual_path: str,
        predicted_advantage: str,
        lesson_extracted: str,
    ) -> Dict[str, Any]:
        """
        Evaluate a counterfactual branch and record the extracted operational rule.
        """
        record = {
            "trigger_event": trigger_event,
            "actual_path": actual_path,
            "counterfactual_path": counterfactual_path,
            "predicted_advantage": predicted_advantage,
            "lesson_extracted": lesson_extracted,
        }

        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO counterfactual_rollouts
                    (trigger_event, actual_path, counterfactual_path, predicted_advantage, lesson_extracted, created_at)
                    VALUES (?, ?, ?, ?, ?, :created_at)
                """, (trigger_event, actual_path, counterfactual_path,
                      predicted_advantage, lesson_extracted, utc_now_iso()))
                conn.commit()
                conn.close()
            except Exception as e:
                # Recorded, not swallowed: a lesson that failed to persist is
                # re-learned at the next occurrence.
                logging.getLogger(__name__).error(
                    "counterfactual rollout not persisted: %s: %s",
                    type(e).__name__, e, exc_info=True)

        return record

    def get_past_lessons(self, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant historical counterfactual lessons."""
        if not self.db_path:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if query:
                cur.execute("""
                    SELECT trigger_event, actual_path, counterfactual_path, predicted_advantage, lesson_extracted, created_at
                    FROM counterfactual_rollouts
                    WHERE trigger_event LIKE ? OR lesson_extracted LIKE ?
                    ORDER BY id DESC LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
            else:
                cur.execute("""
                    SELECT trigger_event, actual_path, counterfactual_path, predicted_advantage, lesson_extracted, created_at
                    FROM counterfactual_rollouts
                    ORDER BY id DESC LIMIT ?
                """, (limit,))
            rows = cur.fetchall()
            conn.close()

            return [
                {
                    "trigger_event": r[0],
                    "actual_path": r[1],
                    "counterfactual_path": r[2],
                    "predicted_advantage": r[3],
                    "lesson_extracted": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[CounterfactualEngine] Failed to retrieve lessons: {e}")
            return []
