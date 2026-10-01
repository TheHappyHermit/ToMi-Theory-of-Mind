#!/usr/bin/env python3
"""
brain.epistemology.defeater_graph — Pollock Defeasible Reasoning & Defeater Lattice.

Implements John Pollock's Theory of Defeasible Reasoning:
- Beliefs are held defeasibly with varying credence.
- Rebutting Defeaters: Directly contest the truth of the conclusion.
- Undercutting Defeaters: Attack the inferential link between premise and conclusion.
- Computes epistemic status: 'grounded', 'disputed', 'undercut', or 'superseded'.
"""

import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from brain.util.timeutil import utc_now_iso


class DefeaterGraph:
    """
    Defeasible Epistemic Graph and Justification Evaluator.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def add_belief(
        self,
        topic: str,
        statement: str,
        credence: float = 1.0,
        provenance: str = "user",
        source_location: str = "",
    ) -> int:
        """Add or update a defeasible belief node.

        source_location is REQUIRED and is not defaulted to a placeholder.
        It is the path, page slug or message id the belief came from.

        Why this is refused rather than stored empty: provenance says who spoke
        ('user', 'tool', 'inference'), which is a category, not an address. A
        belief that cannot be re-read is indistinguishable from one that should
        never have been stored, and the cost of discovering that later is
        having already acted on it. An empty string would satisfy the column
        while making the belief unreferenceable, which is the failure the
        requirement exists to prevent -- so an empty value is an error, not a
        default.

        Callers that genuinely have no location yet should not store the
        belief. Nothing is lost by that: an unsourced belief has nowhere to be
        checked later.
        """
        # A placeholder satisfies a presence check while addressing nothing, and
        # a required field that everyone fills with the same four letters is not
        # a required field. So the near-empty values are rejected too. The list
        # is short on purpose: it catches the lazy values, not legitimate short
        # locations, which look like paths.
        _PLACEHOLDERS = frozenset({
            "unknown", "n/a", "na", "-", "--", "none", "null", "nil",
            "tbd", "todo", "???", "??", "?", "here", "somewhere",
            "no source", "no location", "unspecified",
        })
        if (not isinstance(source_location, str)
                or not source_location.strip()
                or source_location.strip().lower() in _PLACEHOLDERS):
            raise ValueError(
                "source_location is required: give the path, page slug or "
                "message id this belief came from. 'user' records who spoke, "
                "not which of several hundred pages to re-read when the belief "
                "turns out to be wrong."
            )
        if not self.db_path:
            return 1

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cognitive_beliefs (topic, statement, credence, provenance,
                                           source_location, epistemic_state,
                                           created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'grounded', ?, ?)
        """, (topic, statement, max(0.0, min(1.0, credence)), provenance,
                source_location.strip(), utc_now_iso(), utc_now_iso()))
        belief_id = cur.lastrowid
        conn.commit()
        conn.close()
        return belief_id

    def add_defeater(self, target_belief_id: int, defeater_belief_id: int, defeater_type: str, justification: str):
        """
        Record a defeater relationship between two beliefs.
        defeater_type: 'rebutting' | 'undercutting'
        """
        if defeater_type not in ("rebutting", "undercutting"):
            raise ValueError(f"Invalid defeater_type: {defeater_type}")

        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cognitive_defeaters (target_belief_id, defeater_belief_id, defeater_type, rational_justification, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (target_belief_id, defeater_belief_id, defeater_type, justification,
                utc_now_iso()))

        # Re-evaluate target belief status
        new_state = "disputed" if defeater_type == "rebutting" else "undercut"
        cur.execute("""
            UPDATE cognitive_beliefs
            SET epistemic_state = ?, updated_at = ?
            WHERE id = ?
        """, (new_state, utc_now_iso(), target_belief_id))

        conn.commit()
        conn.close()

    def get_grounded_beliefs(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all currently grounded (non-defeated) beliefs."""
        if not self.db_path:
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if topic:
            cur.execute("""
                SELECT id, topic, statement, credence, provenance, epistemic_state
                FROM cognitive_beliefs
                WHERE epistemic_state = 'grounded' AND topic = ?
            """, (topic,))
        else:
            cur.execute("""
                SELECT id, topic, statement, credence, provenance, epistemic_state
                FROM cognitive_beliefs
                WHERE epistemic_state = 'grounded'
            """)
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "topic": r[1],
                "statement": r[2],
                "credence": r[3],
                "provenance": r[4],
                "state": r[5],
            }
            for r in rows
        ]

    def get_disputed_beliefs(self) -> List[Dict[str, Any]]:
        """Retrieve beliefs that are currently disputed or undercut with their defeaters."""
        if not self.db_path:
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT b.id, b.topic, b.statement, b.epistemic_state, d.defeater_type, d.rational_justification
            FROM cognitive_beliefs b
            JOIN cognitive_defeaters d ON b.id = d.target_belief_id
            WHERE b.epistemic_state IN ('disputed', 'undercut')
        """)
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "belief_id": r[0],
                "topic": r[1],
                "statement": r[2],
                "state": r[3],
                "defeater_type": r[4],
                "justification": r[5],
            }
            for r in rows
        ]
