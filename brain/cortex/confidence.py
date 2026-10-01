#!/usr/bin/env python3
"""
brain.cortex.confidence — emit a confidence for every claim, with its evidence.

WHAT THIS IS
The root component. Routing, scheduling and the shortcut library all consume
confidence, and calibration is computed from the confidence_log this writes,
which is why the log had to exist first.

FOUR RULES, AND WHY EACH IS HERE

1. THE SUBSYSTEM NAMES ITSELF. `mechanism` is supplied by whoever produced the
   claim, never guessed here. A confidence layer that infers the source is a
   confidence layer that can be confidently wrong about where a number came
   from, and then calibration attributes the error to the wrong subsystem.

2. CONFIDENCE IS PER CLAIM, NOT PER ANSWER. A paragraph with three claims has
   three confidences. A single number for the paragraph is a number about
   nothing: it cannot be checked, because a partly-supported paragraph is
   partly-right, and "82% confident" on it describes neither half.

3. NO EVIDENCE, NO CONFIDENCE. A confidence with no evidence ids is a vibe.
   This module will not emit one. The value exists to be checked later against
   was_correct, and a number with no retrievals behind it has nothing to check
   it against -- it would sit in the log looking like evidence and calibrate
   against outcomes it did not produce.

4. NEVER AVERAGE A DISAGREEMENT INTO A MIDDLE. If two sources conflict, both
   confidences are emitted with both mechanisms, and choosing between them is
   the consumer's job. Averaging produces a number that neither source believes,
   which is worse than useless: it looks like a measurement and it is the
   product of a rule nobody would defend if asked.

WHAT THIS DOES NOT DO
It does not compute a number from nothing. There is no "assign 0.7 because
partial support" path. A confidence here is either supplied by a subsystem that
knows its own basis, or it is not emitted.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence

from brain.cortex.observation_log import LogWriteError, ObservationLog
from brain.util.timeutil import utc_now_iso

__all__ = ["Claim", "ConfidenceLayer", "ConfidenceError"]

log = logging.getLogger(__name__)


class ConfidenceError(ValueError):
    """A confidence could not be emitted.

    Raised rather than logged-and-continued: a caller that wanted a confidence
    and got silence will proceed as though it had one, which is the failure
    this layer exists to prevent.
    """


class Claim:
    """One claim with the basis for believing it.

    A paragraph is three of these, not one. See rule 2.
    """

    __slots__ = ("text", "confidence", "evidence_ids", "mechanism")

    def __init__(
        self,
        text: str,
        confidence: float,
        mechanism: str,
        evidence_ids: Optional[Sequence[int]] = None,
    ):
        if not isinstance(text, str) or not text.strip():
            raise ConfidenceError("a claim needs text")
        if not isinstance(mechanism, str) or not mechanism.strip():
            # Rule 1. A guess here would make calibration attribute errors to
            # the wrong subsystem, permanently.
            raise ConfidenceError(
                "mechanism is required: the subsystem that produced this claim "
                "names itself. The confidence layer must not guess, because a "
                "wrong guess misattributes the error in calibration."
            )
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ConfidenceError(
                f"confidence must be a number, got {type(confidence).__name__}. "
                "A boolean is not a confidence."
            )
        if not 0.0 <= float(confidence) <= 1.0:
            raise ConfidenceError(
                f"confidence {confidence} is outside [0.0, 1.0]. A value above 1 "
                "is not more certain, it is a different kind of number."
            )
        ids = list(evidence_ids or [])
        if not ids:
            # Rule 3.
            raise ConfidenceError(
                f"claim {text[:60]!r} has no evidence_ids. A confidence with no "
                "provenance cannot be checked against an outcome, so it cannot "
                "be calibrated -- and a row in confidence_log with no evidence "
                "looks like evidence while being nothing. Retrieve first, then "
                "claim."
            )
        if not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
            raise ConfidenceError(
                f"evidence_ids must be integers from retrieval_log, got {ids!r}")

        self.text = text.strip()
        self.confidence = float(confidence)
        self.mechanism = mechanism.strip()
        self.evidence_ids = ids

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.text,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "mechanism": self.mechanism,
        }

    def __repr__(self) -> str:
        return (f"Claim({self.text[:32]!r}, conf={self.confidence:.2f}, "
                f"mech={self.mechanism!r}, evidence={len(self.evidence_ids)})")


class ConfidenceLayer:
    """Validates claims and records them against their evidence.

    Every emission is written to confidence_log. A claim that cannot be written
    is an error, not a silent skip -- the caller asked for a confidence and the
    system must not pretend it has one.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._log = ObservationLog(db_path) if db_path else None

    # -- evidence check -----------------------------------------------------

    def verify_evidence(self, evidence_ids: Iterable[int]) -> List[int]:
        """Return the ids that exist in retrieval_log; raise if any do not.

        A claim citing evidence that was never written is a claim resting on
        something imaginary. Catching it here means the error names the claim,
        rather than surfacing later as a calibration result nobody can explain.
        """
        ids = list(evidence_ids or [])
        if not ids:
            raise ConfidenceError("no evidence ids to verify")
        if not self.db_path:
            # Nothing to check against. Say so rather than passing them through
            # as though they had been verified.
            raise ConfidenceError(
                "cannot verify evidence: no database, so there is no "
                "retrieval_log to check these ids against")
        con = sqlite3.connect(self.db_path)
        try:
            present = set()
            # Chunked so a long evidence list cannot exceed SQLite's variable
            # limit, which is a confusing failure at an unrelated call site.
            for i in range(0, len(ids), 500):
                chunk = ids[i:i + 500]
                q = ",".join("?" * len(chunk))
                present.update(r[0] for r in con.execute(
                    f"SELECT id FROM retrieval_log WHERE id IN ({q})", chunk))
        finally:
            con.close()
        missing = [i for i in ids if i not in present]
        if missing:
            raise ConfidenceError(
                f"evidence_ids not found in retrieval_log: {missing}. These "
                "retrievals were never recorded, so the claim rests on "
                "something that does not exist."
            )
        return ids

    # -- emission -----------------------------------------------------------

    def emit(self, claim: Claim, session_id: str) -> int:
        """Record one claim. Returns the confidence_log row id.

        The evidence is verified first. Verifying after the write would leave a
        row citing retrievals that do not exist, which is the one outcome this
        layer is built to make impossible.
        """
        if not self._log:
            raise ConfidenceError(
                "no database: cannot record a confidence, and refusing to "
                "return an unrecorded one")
        if not session_id or not str(session_id).strip():
            raise ConfidenceError("session_id is required")
        self.verify_evidence(claim.evidence_ids)
        return self._log.log_confidence(
            claim=claim.text,
            confidence=claim.confidence,
            mechanism=claim.mechanism,
            evidence_ids=claim.evidence_ids,
            session_id=str(session_id),
        )

    def emit_many(self, claims: Sequence[Claim], session_id: str) -> List[int]:
        """Record several claims. All of them, or none of them.

        Partial emission is not an option: a caller holding three claims and
        getting one id back cannot tell which claim went unrecorded, and a
        missing confidence silently becomes an unexamined one.

        So every claim is verified BEFORE any is written. Validating as it goes
        and rolling back on failure would also leave the first claim written,
        and "written then undone" is indistinguishable from "written" to
        anything reading the log afterwards.
        """
        if not claims:
            raise ConfidenceError(
                "no claims supplied. An empty result is not a set of high "
                "confidences; it is a missing answer, and returning it as an "
                "empty list invites the two being confused.")
        if not self._log:
            raise ConfidenceError(
                "no database: cannot record confidences, and refusing to "
                "return unrecorded ones")
        if not session_id or not str(session_id).strip():
            raise ConfidenceError("session_id is required")
        # Verify the whole batch first, so a bad claim late in the list cannot
        # leave earlier ones committed.
        for claim in claims:
            self.verify_evidence(claim.evidence_ids)
        return [self.emit(c, session_id) for c in claims]

    def emit_disagreement(
        self,
        claims: Sequence[Claim],
        session_id: str,
    ) -> List[int]:
        """Record claims that conflict, WITHOUT collapsing them.

        Rule 4. This is emit_many plus a check that the claims really are
        distinct, because the failure it prevents -- averaging two positions
        into a number neither holds -- is easy to reintroduce by accident in a
        caller. It refuses a single claim, since a disagreement needs two.
        """
        if len(claims) < 2:
            raise ConfidenceError(
                "a disagreement needs at least two claims; one is not a "
                "disagreement")
        mechanisms = {c.mechanism for c in claims}
        if len(mechanisms) < 2 and len({c.text for c in claims}) < 2:
            raise ConfidenceError(
                "these claims are identical. Recording one twice is not a "
                "disagreement.")
        return self.emit_many(claims, session_id)

    # -- reading back -------------------------------------------------------

    def get_uncorrected(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Claims still awaiting an outcome.

        These are the ones calibration has not seen yet. A large backlog means
        calibration is measuring on stale data, which is worth knowing.
        """
        if not self.db_path:
            return []
        con = sqlite3.connect(self.db_path)
        try:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT id, observed_at, session_id, claim, confidence, "
                "mechanism, evidence_ids FROM confidence_log "
                "WHERE was_correct IS NULL "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    def record_outcome(self, confidence_id: int, was_correct: bool) -> None:
        """Fill in the outcome for a previously emitted claim.

        Append-only still: this fills a column that was deliberately left null,
        it does not rewrite the confidence. The value that was emitted is the
        value that gets checked.
        """
        if not self.db_path:
            raise ConfidenceError("no database")
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute(
                "UPDATE confidence_log SET was_correct = ? WHERE id = ? "
                "AND was_correct IS NULL",
                (1 if was_correct else 0, confidence_id))
            if cur.rowcount == 0:
                raise ConfidenceError(
                    f"confidence_log row {confidence_id} is absent or already "
                    "corrected. An outcome may only be recorded once -- "
                    "recording it twice would let a later, more convenient "
                    "answer overwrite the first."
                )
            con.commit()
        finally:
            con.close()
