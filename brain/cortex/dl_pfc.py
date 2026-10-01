#!/usr/bin/env python3
"""
brain.cortex.dl_pfc — Dorsolateral Prefrontal Cortex (dlPFC) Working Memory.

Manages:
- Miller / Cowan limited-capacity active attention slots (typically 4-7 chunks).
- Goal stack (active root goal, sub-goals, hypotheses).
- Activation decay across interaction turns unless actively refreshed.
- Token budget management with graceful eviction and snapshotting to disk.
"""

import json
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional, Tuple


_log = logging.getLogger(__name__)


_CUE_WORDS = re.compile(r"[a-z0-9_]+")
_CUE_STOPWORDS = frozenset("""
a an the and or but if then of to in on at by for with from as is are was were
be do does did have has had it its this that these those we you they i
""".split())


def _cue_words(slot: "WorkingMemorySlot") -> frozenset:
    """The cues a slot can be retrieved by: its key and its value.

    Content words only. Counting function words would make every pair of slots
    look like they compete, since all English sentences share them -- which is
    how the attention gate came to treat "ok" as contextually relevant.
    """
    words = set()
    for source in (slot.key, slot.value):
        if source is None:
            continue
        words.update(w for w in _CUE_WORDS.findall(str(source).lower())
                     if len(w) > 2 and w not in _CUE_STOPWORDS)
    return frozenset(words)


class WorkingMemorySlot:
    def __init__(self, key: str, value: Any, importance: float = 0.5, category: str = "context"):
        self.key = key
        self.value = value
        self.importance = importance  # 0.0 to 1.0
        self.category = category      # 'goal', 'constraint', 'fact', 'hypothesis', 'scratchpad'
        self.activation = 1.0         # Decays over time/turns
        self.last_accessed = time.time()

    def touch(self, boost: float = 0.3):
        self.last_accessed = time.time()
        self.activation = min(1.0, self.activation + boost)

    def decay(self, rate: float = 0.15):
        self.activation = max(0.0, self.activation - rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "importance": self.importance,
            "category": self.category,
            "activation": round(self.activation, 3),
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkingMemorySlot":
        slot = cls(
            key=data["key"],
            value=data["value"],
            importance=data.get("importance", 0.5),
            category=data.get("category", "context"),
        )
        slot.activation = data.get("activation", 1.0)
        slot.last_accessed = data.get("last_accessed", time.time())
        return slot


class DorsolateralPFC:
    """
    Working Memory Scratchpad and Attentional Workspace.
    Maintains Cowan/Miller capacity bounds (default 7 slots) and active goal hierarchies.
    """

    def __init__(
        self,
        capacity: int = 7,
        db_path: Optional[str] = None,
        category_quotas: Optional[Dict[str, int]] = None,
    ):
        self.capacity = capacity
        self.db_path = db_path
        self.slots: Dict[str, WorkingMemorySlot] = {}
        self.active_goal: Optional[str] = None
        self.sub_goals: List[str] = []
        self.hypotheses: List[str] = []
        # Per-category ceilings, so one kind of item cannot take every slot.
        # The default distribution is a policy choice, stated so it can be
        # argued with rather than inherited. Goals live in their own field and
        # never consume a slot, so they are absent here by design.
        #
        #   context    the raw input stream. Allowed to be the largest group
        #              because it is the cheapest to lose -- it is the newest
        #              turn and the least likely to be the point.
        #   fact       something established and worth keeping.
        #   constraint something that bounds what may be done. Scarce on
        #              purpose: losing a constraint causes a wrong answer, while
        #              losing a fact usually causes a re-derivation.
        #   hypothesis a guess under test. The most volatile, and the least
        #              costly to lose, since a hypothesis that is still live will
        #              be re-stated.
        #   scratchpad transient working notes. First to go.
        #
        # A category absent from this dict is unlimited, so adding a new category
        # does not silently become a quota of zero.
        self.category_quotas: Dict[str, int] = (
            dict(category_quotas) if category_quotas is not None else {
                "context": 3,
                "fact": 2,
                "constraint": 1,
                "hypothesis": 1,
                "scratchpad": 0,
            }
        )

    def set_active_goal(self, goal: str, sub_goals: Optional[List[str]] = None):
        self.active_goal = goal
        self.sub_goals = sub_goals or []
        self.upsert_slot("active_goal", goal, importance=1.0, category="goal")

    def add_sub_goal(self, sub_goal: str):
        if sub_goal not in self.sub_goals:
            self.sub_goals.append(sub_goal)

    def complete_sub_goal(self, sub_goal: str):
        if sub_goal in self.sub_goals:
            self.sub_goals.remove(sub_goal)

    def add_hypothesis(self, hypothesis: str):
        if hypothesis not in self.hypotheses:
            self.hypotheses.append(hypothesis)

    def upsert_slot(self, key: str, value: Any, importance: float = 0.5, category: str = "context") -> WorkingMemorySlot:
        if key in self.slots:
            slot = self.slots[key]
            slot.value = value
            slot.importance = max(slot.importance, importance)
            slot.category = category
            slot.touch()
            return slot

        # Capacity management: if full, evict lowest (activation * importance)
        if len(self.slots) >= self.capacity:
            self._evict_lowest()

        slot = WorkingMemorySlot(key=key, value=value, importance=importance, category=category)
        self.slots[key] = slot
        return slot

    def apply_interference(self, strength: float = 1.0) -> List[Tuple[str, str]]:
        """Attenuate competing slots against each other. Returns the pairs.

        Phase 2. Eviction decides which slot LEAVES. Interference decides how
        strongly the ones that remain pull against each other, which is the
        effect that actually degrades a working memory in practice: nothing is
        thrown out, but two items competing for the same cue each become
        harder to reach, and a third item for a different cue pays too because
        retrieval is not free.

        Competition is by shared cue -- overlapping content words -- because
        that is what makes two memories interfere. Two unrelated slots are
        retrieved by different cues and do not contend.

        Self-activation is restored afterwards. A slot that competes has been
        touched, and letting that touch count as use would mean that using
        working memory raises the activation of everything in it, which is the
        opposite of interference.

        strength scales the whole effect so a caller can model a partial
        competition rather than only the saturated case.
        """
        touched: List[Tuple[str, str]] = []
        for i, (k1, s1) in enumerate(self.slots.items()):
            for k2, s2 in list(self.slots.items())[i + 1:]:
                overlap = self._cue_overlap(s1, s2)
                if overlap <= 0.0:
                    continue
                # Stronger, more available slots interfere more: a weak item is
                # not what is disrupting a strong one.
                damping = strength * overlap * min(
                    1.0, (s1.activation + s2.activation) / 2.0)
                if damping <= 0.0:
                    continue
                for s in (s1, s2):
                    before = s.activation
                    s.activation = max(0.0, s.activation * (1.0 - damping))
                    # Do not let the touch count as a use.
                    s.activation = max(s.activation, before - damping)
                touched.append((k1, k2))
        return touched

    @staticmethod
    def _cue_overlap(a: WorkingMemorySlot, b: WorkingMemorySlot) -> float:
        """Fraction of the smaller cue set the two slots share."""
        ca = _cue_words(a)
        cb = _cue_words(b)
        if not ca or not cb:
            return 0.0
        return len(ca & cb) / min(len(ca), len(cb))

    def get_slot(self, key: str) -> Optional[Any]:
        if key in self.slots:
            slot = self.slots[key]
            slot.touch()
            return slot.value
        return None

    def decay_all(self, rate: float = 0.15):
        """Called at each turn to simulate attentional fade."""
        for slot in self.slots.values():
            if slot.category != "goal":  # Goals resist decay
                slot.decay(rate)

    def _eviction_score(self, slot: WorkingMemorySlot) -> float:
        """How much this slot wants to be kept. Higher survives longer.

        The policy, stated because it was previously unstated and therefore
        unarguable:

        A slot is evicted when its *attention* has faded and nothing has marked it
        as important. Two things protect a slot:

        1. **Activation** — how recently and how often it has been touched.
           Decays each turn; refreshed on every get_slot(). This is ordinary
           fading attention, not a value judgement.
        2. **Importance** — what the caller declared when the slot was written.
           Only the writer can raise this, so the system cannot promote a slot
           on its own to make a quota look satisfied.

        The product is used, not the sum. A slot with high importance that nobody
        has touched in twenty turns is less current than a mediocre one used
        constantly, and the product says so. A sum would let a permanently
        high-importance slot accumulate its own immunity and become unevictable,
        which is the failure mode that motivated per-category quotas in the first
        place.

        Goals are excluded upstream by decay_all() and are never scored here.
        """
        return slot.activation * slot.importance

    def _evict_lowest(self) -> Optional[str]:
        """Evict the least deserving slot, respecting the category quota.

        Returns the evicted key, or None if nothing was evicted. Never raises:
        losing a slot is not a reason to fail the write that triggered it.
        losing a slot is not a reason to fail the write that triggered it.

        Prefer to evict from a category that is over its quota. Restricting the
        loss to over-quota categories is what stops a flood from one category
        eating the others.

        When the memory is full but no category is over quota, quotas alone are
        not enough: something still has to go, and the plain score would pick
        the least important item regardless of what kind of thing it is. A
        constraint at importance 0.3 would be the first casualty of any flood,
        and losing a constraint produces a wrong answer rather than a
        re-derivation. So the fallback protects categories whose quota is
        binding -- at quota, and therefore not permitted to grow -- and evicts
        only from a category with room to spare.

        If every category is exactly at its quota there is nothing to protect
        and the score decides. That is the only case where a protected category
        can be evicted, and it is the right place for it: the memory is
        genuinely full of things that all deserve to stay.

        A quota of 0 means the category is entirely full and must shed, so it is
        over quota whenever it holds anything at all.
        """
        if not self.slots:
            return None

        over = self._over_quota_categories()
        if over:
            candidates = [(k, s) for k, s in self.slots.items() if s.category in over]
        else:
            at_quota = {
                c for c, n in Counter(s.category for s in self.slots.values()).items()
                if c in self.category_quotas and n >= self.category_quotas[c]
            }
            candidates = [
                (k, s) for k, s in self.slots.items()
                if not at_quota or s.category not in at_quota
            ]
            if not candidates:
                candidates = list(self.slots.items())

        evict_key = min(candidates, key=lambda item: self._eviction_score(item[1]))[0]
        del self.slots[evict_key]
        return evict_key

    def _over_quota_categories(self) -> set:
        """Categories currently holding more slots than their quota allows."""
        if not self.category_quotas:
            return set()
        counts = Counter(s.category for s in self.slots.values())
        return {c for c, n in counts.items()
                if c in self.category_quotas and n > self.category_quotas[c]}

    def render_context_summary(self, max_tokens: int = 1000) -> str:
        """Render working memory contents formatted for prompt injection."""
        lines = []
        if self.active_goal:
            lines.append(f"CURRENT ACTIVE GOAL: {self.active_goal}")
        if self.sub_goals:
            lines.append("SUB-GOALS IN PROGRESS:")
            for sg in self.sub_goals:
                lines.append(f"  - {sg}")
        if self.hypotheses:
            lines.append("ACTIVE HYPOTHESES:")
            for h in self.hypotheses:
                lines.append(f"  ? {h}")

        active_items = sorted(
            [s for s in self.slots.values() if s.category not in ("goal",)],
            key=lambda s: s.activation * s.importance,
            reverse=True,
        )
        if active_items:
            lines.append("WORKING CONTEXT (Active Chunks):")
            for item in active_items:
                lines.append(f"  [{item.category.upper()}] {item.key}: {item.value} (act: {item.activation:.2f})")

        return "\n".join(lines)

    def save_snapshot(self, session_id: str):
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            slots_data = [s.to_dict() for s in self.slots.values()]
            cur.execute("""
                INSERT OR REPLACE INTO working_memory_snapshots
                (session_id, active_goal, sub_goals_json, hypotheses_json, focus_slots_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                self.active_goal or "",
                json.dumps(self.sub_goals),
                json.dumps(self.hypotheses),
                json.dumps(slots_data),
                datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            ))
            conn.commit()
            conn.close()
        except Exception:
            # Fail loudly. A snapshot that silently fails to write means
            # working memory is lost with no signal, and the pass that depended
            # on it reports success regardless. Raise rather than print: the
            # caller's next recovery depends on knowing this did not happen.
            self._log.error("failed to save working memory snapshot", exc_info=True)
            raise

    def load_snapshot(self, session_id: str) -> bool:
        if not self.db_path:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT active_goal, sub_goals_json, hypotheses_json, focus_slots_json
                FROM working_memory_snapshots
                WHERE session_id = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (session_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return False

            # Parse everything into locals before touching any attribute. A
            # snapshot that turns out to be corrupt halfway through must not
            # leave the brain holding some of it: a half-restored working memory
            # produces answers traceable to no decision, which is worse than no
            # restore at all.
            active_goal = row[0] or None
            sub_goals = json.loads(row[1]) if row[1] else []
            hypotheses = json.loads(row[2]) if row[2] else []
            slots_data = json.loads(row[3]) if row[3] else []
            slots = {d["key"]: WorkingMemorySlot.from_dict(d) for d in slots_data}

            # Commit to the new state only once every field parsed.
            self.active_goal = active_goal
            self.sub_goals = sub_goals
            self.hypotheses = hypotheses
            self.slots = slots
            return True
        except Exception:
            # A restore that half-succeeds leaves working memory in a state
            # nobody chose. Log loudly and refuse: continuing with a partial
            # restore is how a wrong answer becomes an untraceable one.
            self._log.error("failed to load working memory snapshot", exc_info=True)
            raise
