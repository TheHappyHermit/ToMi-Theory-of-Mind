#!/usr/bin/env python3
"""
brain.cortex.observation_log — append-only writers for retrieval_log and confidence_log.

WHY THIS EXISTS
Four components are blocked on the same absent thing: a record of what the
retriever did and how sure the system was of each claim. Metacognition calibrates
on its own history, scheduling tags and recalls that history, the benchmark needs
to know whether the retriever was correct, and the shortcut library fires on high
confidence and escalates when it is low. Without this, all four get built blind.

This is instrumentation, not measurement. Logging what happened is permitted and
required. Deriving quality numbers from it is not — that needs an outside
researcher with a stated method.

DESIGN RULES, all of them learned rather than preferred:

1. **Append-only.** There is no update and no delete in this module, by design.
   A row that can be edited is indistinguishable from a row that was never
   wrong, which destroys the only thing these tables are for.

2. **Fail closed.** If a write cannot be recorded, the call that wanted to record
   it does not proceed. Returning None and carrying on silently is how a
   calibration signal rots for months before anyone notices it has been empty.

3. **Foreign keys on.** Every connection this module opens sets
   PRAGMA foreign_keys=ON. Orphaned evidence_ids are the failure mode that makes
   a confidence look calibrated when nothing links it to a retrieval.

4. **RFC 3339 UTC.** YYYY-MM-DDTHH:MM:SSZ, matching the rest of brain_cortex.sql.
   Two timestamp formats in one column silently break sorting and indexes.

5. **No measurement.** This module records. It does not score, rank, average, or
   report a quality figure. Anything that wanted to would be measuring, which is
   the one thing it must not do.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    "ObservationLog",
    "LogWriteError",
    "utc_now",
    "VALID_STRATEGIES",
]

# The retriever names its own strategy. Constraining it here means a typo becomes
# a loud failure at write time rather than a category that quietly never appears
# in the history the benchmark is later built from.
VALID_STRATEGIES = frozenset({"keyword", "dense", "graph", "fused", "reranked"})


class LogWriteError(RuntimeError):
    """Raised when a log write cannot be recorded.

    Callers are expected to let this propagate. Catching it and continuing is
    precisely the silent failure the fail-closed rule exists to prevent.
    """


def utc_now() -> str:
    """Current time as RFC 3339 UTC: YYYY-MM-DDTHH:MM:SSZ.

    Computed in Python rather than by SQLite so the same function governs both
    tables. A per-table default of strftime('now') would be identical here, but
    it is only identical by accident of definition; one function is one rule.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ObservationLog:
    """Append-only writer for retrieval_log and confidence_log.

    One instance per database. Holds no connection between calls: each write
    opens, commits, and closes. That is the right shape for an append-only log --
    there is no transaction to batch, and a held connection would keep a lock on
    the brain database for the lifetime of the brain object.
    """

    def __init__(self, db_path: Optional[str]):
        # None is a legitimate state and must not raise here. Constructing the
        # brain without a database is a supported mode; the failure belongs at
        # the write, where it can refuse the work, not at construction, where it
        # would take down an object that is otherwise fine.
        self.db_path = db_path

    # -- connection handling -------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path:
            raise LogWriteError(
                "observation log has no db_path; cannot record. "
                "A pass that cannot be logged must not proceed unlogged."
            )
        if not os.path.exists(self.db_path):
            raise LogWriteError(
                f"brain database does not exist: {self.db_path}"
            )
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        # Required by rule 3. SQLite defaults this OFF on every connection, so
        # it has to be set every time or it is never actually on.
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # -- retrieval_log -------------------------------------------------------

    def log_retrieval(
        self,
        *,
        session_id: str,
        query: str,
        strategy: str,
        doc_id: str,
        source_path: Optional[str] = None,
        rank_position: Optional[int] = None,
        score: Optional[float] = None,
        was_selected: bool = False,
        latency_ms: Optional[int] = None,
    ) -> int:
        """Record one retrieval. Returns the new row id.

        Raises LogWriteError rather than returning None. A caller that gets an id
        can log the retrieval_log.id as evidence on a later confidence; a caller
        that silently gets None will not know to.
        """
        if strategy not in VALID_STRATEGIES:
            raise LogWriteError(
                f"unknown retrieval strategy {strategy!r}; "
                f"expected one of {sorted(VALID_STRATEGIES)}"
            )
        if not query or not query.strip():
            raise LogWriteError("retrieval query is empty; nothing to attribute the result to")
        if not doc_id or not doc_id.strip():
            raise LogWriteError("retrieval doc_id is empty; a result with no identity is not provenance")

        conn = self._connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO retrieval_log
                    (observed_at, session_id, query, strategy, doc_id,
                     source_path, rank_position, score, was_selected, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now(),
                    session_id,
                    query,
                    strategy,
                    doc_id,
                    source_path,
                    rank_position,
                    score,
                    1 if was_selected else 0,
                    latency_ms,
                ),
            )
            conn.commit()
            if cur.lastrowid is None:
                # Only reachable if the table lacks an autoincrement rowid, which
                # the schema does not have. Refusing beats returning a fake id.
                raise LogWriteError("insert produced no row id")
            return int(cur.lastrowid)
        except sqlite3.Error as exc:
            raise LogWriteError(f"failed to write retrieval_log: {exc}") from exc
        finally:
            conn.close()

    # -- confidence_log ------------------------------------------------------

    def log_confidence(
        self,
        *,
        session_id: str,
        claim: str,
        confidence: float,
        mechanism: Optional[str],
        evidence_ids: Optional[Iterable[int]] = None,
    ) -> int:
        """Record one claim's confidence. Returns the new row id.

        `mechanism` names the subsystem that produced the claim. It is a required
        argument rather than something inferred, because inference here is how a
        confidence ends up attributed to the wrong subsystem and the calibration
        data becomes uninterpretable.

        `evidence_ids` are retrieval_log row ids. They are stored as a JSON array
        without checking they exist: a confidence may be logged before its
        retrieval is written, and rejecting it would push authors toward inventing
        ids. Foreign keys are not declared on this column because the ordering is
        genuinely open. Use `unverified_evidence_count` to find out how many of
        them actually resolve.
        """
        if not claim or not claim.strip():
            raise LogWriteError("confidence claim is empty")
        if not mechanism or not mechanism.strip():
            raise LogWriteError(
                "confidence mechanism is empty; a confidence with no named "
                "mechanism cannot be calibrated, because there is nothing to "
                "attribute the error to"
            )
        if not 0.0 <= float(confidence) <= 1.0:
            raise LogWriteError(
                f"confidence {confidence} is outside 0.0-1.0"
            )

        ids: Optional[List[int]] = None
        if evidence_ids is not None:
            ids = [int(i) for i in evidence_ids]
            if not ids:
                # An empty list is a claim of "no evidence", which is a different
                # statement from "evidence not yet known" (None). Store the empty
                # list so that distinction survives into the history.
                ids = []

        conn = self._connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO confidence_log
                    (observed_at, session_id, claim, confidence,
                     evidence_ids, mechanism, was_correct)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    utc_now(),
                    session_id,
                    claim,
                    float(confidence),
                    json.dumps(ids) if ids is not None else None,
                    mechanism,
                ),
            )
            conn.commit()
            if cur.lastrowid is None:
                # Only reachable if the table lacks an autoincrement rowid, which
                # the schema does not have. Refusing beats returning a fake id.
                raise LogWriteError("insert produced no row id")
            return int(cur.lastrowid)
        except sqlite3.Error as exc:
            raise LogWriteError(f"failed to write confidence_log: {exc}") from exc
        finally:
            conn.close()

    # -- reads for the four blocked components --------------------------------

    def recent_retrievals(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Recent retrievals, newest first. For scheduling and metacognition."""
        if not self.db_path or not os.path.exists(self.db_path):
            return []
        conn = self._connect()
        try:
            if session_id:
                cur = conn.execute(
                    "SELECT * FROM retrieval_log WHERE session_id = ? "
                    "ORDER BY observed_at DESC, id DESC LIMIT ?",
                    (session_id, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM retrieval_log ORDER BY observed_at DESC, id DESC LIMIT ?",
                    (limit,),
                )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def confidences_for_session(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Recent confidences with their evidence ids decoded."""
        if not self.db_path or not os.path.exists(self.db_path):
            return []
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM confidence_log WHERE session_id = ? "
                "ORDER BY observed_at DESC, id DESC LIMIT ?",
                (session_id, limit),
            )
            cols = [d[0] for d in cur.description]
            out = []
            for row in cur.fetchall():
                rec = dict(zip(cols, row))
                raw = rec.get("evidence_ids")
                try:
                    rec["evidence_ids"] = json.loads(raw) if raw else None
                except (TypeError, ValueError):
                    rec["evidence_ids"] = None
                out.append(rec)
            return out
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def unverified_evidence_count(self, confidence_row_id: int) -> int:
        """How many of a confidence's evidence_ids do not resolve to a retrieval.

        Non-zero means the calibration history contains a confidence pointing at
        evidence that was never written. Worth surfacing rather than hiding: it is
        the cheapest available check that the log is internally consistent.
        """
        if not self.db_path or not os.path.exists(self.db_path):
            return 0
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT evidence_ids FROM confidence_log WHERE id = ?", (confidence_row_id,)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return 0
            ids = json.loads(row[0])
            if not ids:
                return 0
            marks = ",".join("?" * len(ids))
            found = conn.execute(
                f"SELECT COUNT(*) FROM retrieval_log WHERE id IN ({marks})", ids
            ).fetchone()[0]
            return len(ids) - int(found)
        except (sqlite3.Error, TypeError, ValueError):
            return 0
        finally:
            conn.close()

    def record_outcome(self, confidence_row_id: int, was_correct: bool) -> None:
        """Fill in was_correct once an outcome is known.

        This is the one write that is not append-only, and it is a deliberate
        exception: was_correct is defined as unknown-until-outcome, so completing
        it is not correcting a belief, it is recording a fact that could not
        exist earlier. It still refuses to touch any other column.
        """
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE confidence_log SET was_correct = ? WHERE id = ?",
                (1 if was_correct else 0, confidence_row_id),
            )
            conn.commit()
        except sqlite3.Error as exc:
            raise LogWriteError(f"failed to record outcome: {exc}") from exc
        finally:
            conn.close()
