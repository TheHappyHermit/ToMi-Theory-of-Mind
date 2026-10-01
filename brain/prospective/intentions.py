"""Prospective memory — standing intentions with trigger conditions.

What this is
------------
Humans do not reliably act on a stated intention ("I should email her"). What
works is a conditional plan: *if situation X arises, then do Y.* Gollwitzer calls
these **implementation intentions** and they are one of the most robust findings in
behavioural science — reliable enough to become a standard clinical intervention
for health behaviour change.

The mapping to software is unusually direct, which is the whole reason it is here.
An agent can already write an `if` statement. What it lacked was a *store of
standing intentions, each with a trigger condition, checked against every turn.*

Evidence
--------
- Gollwitzer & Sheeran (2006), "Implementation Intentions and Goal Achievement:
  A Meta-analysis of Effects", Advances in Experimental Social Psychology.
  DOI 10.1016/S0065-2601(06)38002-1
- Gollwitzer (1999), "Implementation intentions: Strong effects of simple plans",
  American Psychologist 54(7). DOI 10.1037/0003-066x.54.7.493

Evidence tier: peer-reviewed meta-analysis plus a large primary literature in human
health-behaviour studies. **Not yet replicated in LLM agents** — that is the honest
caveat, recorded in docs/COGNITIVE-COVERAGE-REVIEW.md.

Design notes
------------
Why deterministic matching rather than an LLM deciding whether an intention applies:
a 2026 study (arXiv:2606.01435) found model-judged freshness resolution scoring 7%
against BM25's 48%. Anything that can be a table lookup *should* be. Trigger
matching here is substring/keyword based and makes no model call.

Why expiry is mandatory: the suppression literature documents rebound effects, where
repeatedly suppressing an intention produces the opposite of the intended behaviour.
Indefinite triggers are how a system acquires stale intentions that fire at the worst
possible moment.

Why demote rather than delete: see Honcho issue #989, where semantic similarity
permanently deleted the incumbent memory. Nothing here deletes.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Deliberately small vocabulary. An over-broad matcher fires intentions constantly,
# which is worse than never firing them.
DEFAULT_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or",
    "in", "on", "at", "for", "with", "it", "this", "that", "i", "we", "you",
})

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospective_memory (
    intention_id  TEXT PRIMARY KEY,
    trigger_text  TEXT NOT NULL,
    action_text   TEXT NOT NULL,
    trigger_kind  TEXT NOT NULL DEFAULT 'any',
    created_at    TEXT NOT NULL,
    expires_at    TEXT,
    state         TEXT NOT NULL DEFAULT 'pending',
    fired_count   INTEGER NOT NULL DEFAULT 0,
    last_fired_at TEXT,
    note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_pm_state ON prospective_memory(state);
CREATE INDEX IF NOT EXISTS idx_pm_expiry ON prospective_memory(expires_at);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_rfc3339(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass
class Intention:
    intention_id: str
    trigger_text: str
    action_text: str
    trigger_kind: str = "any"  # 'any' | 'all' | 'phrase'
    created_at: str = ""
    expires_at: Optional[str] = None
    state: str = "pending"  # pending | fired | expired | cancelled
    fired_count: int = 0
    last_fired_at: Optional[str] = None
    note: Optional[str] = None
    trigger_tokens: frozenset = field(default_factory=frozenset, repr=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "trigger_text": self.trigger_text,
            "action_text": self.action_text,
            "trigger_kind": self.trigger_kind,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "state": self.state,
            "fired_count": self.fired_count,
            "last_fired_at": self.last_fired_at,
            "note": self.note,
        }


def tokenize(text: Optional[str]) -> frozenset:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return frozenset(w for w in words if len(w) > 2 and w not in DEFAULT_STOPWORDS)


def _tokens_match(needles: Iterable[str], haystack_lower: str, haystack_tokens: frozenset) -> bool:
    """A token matches if it appears as a word OR as a substring.

    Substring matching is deliberate: triggers get written as 'postgres down' and
    turn up as 'postgres appears to be down'. Requiring exact whole-word hits would
    miss that, and a missed intention is a silent failure.
    """
    for n in needles:
        if n in haystack_tokens:
            return True
        if len(n) > 4 and n in haystack_lower:
            return True
    return False


class ProspectiveMemory:
    """Standing intentions with trigger conditions.

    Foreign keys are enabled on every connection: an orphaned intention row is
    exactly the kind of silent data loss this project has already been bitten by.
    """

    def __init__(self, db_path: Path | str | None):
        # Reject a falsy path BEFORE str(). str(None) is the four-character
        # string "None", and sqlite3.connect("None") does not fail -- it
        # creates a file called `None` in the cwd and returns a working
        # connection to it. That is a silent write to an unintended path,
        # the same defect class this project keeps re-finding: the call
        # succeeds, the data lands somewhere nobody looks, and the schema
        # makes it look legitimate. A real path is required.
        #
        # The annotation admits None on purpose: it is the value this guard
        # exists to reject, and a caller may well pass one by mistake.
        if db_path is None or (isinstance(db_path, str) and not db_path.strip()):
            raise ValueError(
                "ProspectiveMemory requires a database path; got "
                f"{db_path!r}. Pass a Path or a non-empty string."
            )
        self.db_path = str(db_path)
        self._ensure_schema()

    # ---- connection handling -------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # ---- writing -------------------------------------------------------------
    def add(
        self,
        trigger: str,
        action: str,
        trigger_kind: str = "any",
        ttl_days: Optional[int] = 30,
        note: Optional[str] = None,
    ) -> Intention:
        """Record a standing intention. `ttl_days=None` never expires (discouraged)."""
        trigger = (trigger or "").strip()
        action = (action or "").strip()
        if not trigger:
            raise ValueError("trigger must not be empty")
        if not action:
            raise ValueError("action must not be empty")
        if trigger_kind not in ("any", "all", "phrase"):
            raise ValueError(f"unknown trigger_kind: {trigger_kind!r}")

        tokens = tokenize(trigger)
        if not tokens:
            raise ValueError(f"trigger has no usable tokens: {trigger!r}")

        now = utc_now()
        expires = rfc3339(now + timedelta(days=ttl_days)) if ttl_days else None
        iid = uuid.uuid4().hex

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO prospective_memory "
                "(intention_id, trigger_text, action_text, trigger_kind, created_at, "
                " expires_at, state, note) VALUES (?,?,?,?,?,?,'pending',?)",
                (iid, trigger, action, trigger_kind, rfc3339(now), expires, note),
            )
        return self.get(iid)  # type: ignore[return-value]

    def cancel(self, intention_id: str) -> bool:
        """Retire an intention. Never deletes — see module docstring."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE prospective_memory SET state='cancelled' WHERE intention_id=? "
                "AND state='pending'",
                (intention_id,),
            )
            return cur.rowcount > 0

    # ---- reading -------------------------------------------------------------
    def _row_to_intention(self, row: sqlite3.Row) -> Intention:
        return Intention(
            intention_id=row["intention_id"],
            trigger_text=row["trigger_text"],
            action_text=row["action_text"],
            trigger_kind=row["trigger_kind"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            state=row["state"],
            fired_count=row["fired_count"],
            last_fired_at=row["last_fired_at"],
            note=row["note"],
            trigger_tokens=tokenize(row["trigger_text"]),
        )

    def get(self, intention_id: str) -> Optional[Intention]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM prospective_memory WHERE intention_id=?", (intention_id,)
            ).fetchone()
        return self._row_to_intention(row) if row else None

    def pending(self, include_expired: bool = False) -> List[Intention]:
        now = rfc3339(utc_now())
        q = "SELECT * FROM prospective_memory WHERE state='pending'"
        params: List[Any] = []
        if not include_expired:
            q += " AND (expires_at IS NULL OR expires_at > ?)"
            params.append(now)
        with self._connect() as conn:
            rows = conn.execute(q + " ORDER BY created_at", params).fetchall()
        return [self._row_to_intention(r) for r in rows]

    def all_intentions(self) -> List[Intention]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM prospective_memory ORDER BY created_at"
            ).fetchall()
        return [self._row_to_intention(r) for r in rows]

    # ---- the actual mechanism ----------------------------------------------
    def check(self, text: str, max_fires: int = 3) -> List[Intention]:
        """Return intentions whose trigger is present in `text`.

        Deterministic, no model call, no side effects. Callers decide what to do
        with a match — some may want to merely surface it.

        `max_fires` caps how many are returned per turn. An intention store that
        can flood the prompt is worse than one that stays quiet.
        """
        # Lazily transition past-due intentions. Without this an intention whose TTL
        # elapsed keeps state='pending' until someone remembers to sweep, so any direct
        # query on state='pending' returns rows that are already dead.
        self.expire_due()

        text_l = (text or "").lower()
        if not text_l.strip():
            return []
        text_tokens = tokenize(text_l)

        fired: List[Intention] = []
        for intent in self.pending():
            if intent.trigger_kind == "phrase":
                if intent.trigger_text.lower() in text_l:
                    fired.append(intent)
                continue
            hits = sum(
                1 for n in intent.trigger_tokens if _tokens_match({n}, text_l, text_tokens)
            )
            if intent.trigger_kind == "all":
                if hits == len(intent.trigger_tokens):
                    fired.append(intent)
            else:  # 'any'
                if hits > 0:
                    fired.append(intent)
            if len(fired) >= max_fires:
                break
        return fired

    def mark_fired(self, intention_ids: Sequence[str]) -> int:
        """Record that intentions were surfaced. Does NOT auto-expire them.

        Returning an intention to 'pending' after a fire is a product decision, not
        a default: a one-shot reminder ('email her when you see the transcript')
        should not re-fire forever, but a standing check should. Expiry and explicit
        cancellation are the supported ways to stop one.
        """
        if not intention_ids:
            return 0
        now = rfc3339(utc_now())
        q = ",".join("?" * len(intention_ids))
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE prospective_memory SET fired_count=fired_count+1, last_fired_at=? "
                f"WHERE intention_id IN ({q})",
                [now, *intention_ids],
            )
            return cur.rowcount

    def expire_due(self) -> int:
        """Transition past-due intentions to 'expired'. Returns how many."""
        now = rfc3339(utc_now())
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE prospective_memory SET state='expired' "
                "WHERE state='pending' AND expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
            return cur.rowcount

    def stats(self) -> Dict[str, Any]:
        # Sweep first: reporting a past-due intention as "pending" is exactly the
        # staleness this class exists to prevent.
        self.expire_due()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT state, COUNT(*) c FROM prospective_memory GROUP BY state"
            ).fetchall()
        by_state = {r["state"]: r["c"] for r in rows}
        return {
            "total": sum(by_state.values()),
            "by_state": by_state,
            "pending": by_state.get("pending", 0),
            "fired": by_state.get("fired", 0),
            "expired": by_state.get("expired", 0),
            "cancelled": by_state.get("cancelled", 0),
        }
