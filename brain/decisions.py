#!/usr/bin/env python3
"""
brain.decisions — The 14 arena-backed Decisions, implemented as one substrate.

Source of truth: PRELIMINARY-PROPOSAL.md (C1-C14). The arena corpus was
exhausted after that document was written (2,217 files, 0 remaining) and the
strike test was run against the finished arena: 0 MUST STRIKE events, 0 Rank-1
re-ranks across 91 tranches, 0 grade changes after tranche 70. All 14 stand.

DESIGN RULE, from Decision C5 -- nothing grades itself
-----------------------------------------------------
Every threshold, weight and confidence in this file is a NUMBER WITH A FLOOR,
A CEILING, AND A DOCUMENTED TIMESCALE. An adaptive parameter you cannot
explain after the fact is indistinguishable from a bug, so every change records
its trigger in an audit trail and refuses to move outside its declared bounds.

This is the opposite of Decision C4, which is the highest-leverage change in
the proposal: the brain's fixed constants (go_threshold=0.4,
compilation_threshold=3, damping_factor=0.85, decay=0.15) become gains that
adapt to recent prediction error, arousal and substrate headroom -- but only
within bounds, and only with the change recorded.

RFC 3339 UTC everywhere, per the schema discipline. No space-separated
datetime('now') in any new column.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# C4 -- Plastic gains. The substrate every other Decision reads its state from.
# ---------------------------------------------------------------------------

# A gain is a parameter that moves. These bounds are the whole safety argument:
# a gain that can reach 0.0 or infinity is not adaptive, it is unstable.
#
# name            floor   ceiling  timescale  what it trades
GAIN_SPECS: Dict[str, Tuple[float, float, float, str]] = {
    # Lower the bar to act when the system is predicting well and has headroom;
    # raise it when recent actions were wrong or the substrate is loaded.
    "go_threshold": (0.15, 0.75, 300.0,
                     "act more easily when accurate and unloaded; less easily when not"),
    # Compile a skill sooner when it keeps succeeding; later when it does not.
    "compilation_threshold": (2.0, 8.0, 600.0,
                              "consolidate repeated successes sooner; successes must repeat"),
    # Damping toward the 0.85 default. Below 0.8 random-walk behaviour appears in
    # the PPR iteration; above 0.95 the graph stops converging inside 20
    # iterations. The ceiling is not arbitrary.
    "damping_factor": (0.80, 0.95, 900.0,
                       "less damped when retrieval is confident; more when it oscillates"),
    # Working-memory activation lost per touch.
    "decay_rate": (0.05, 0.40, 120.0,
                   "forget faster under load; slower when the substrate is quiet"),
}

DEFAULTS: Dict[str, float] = {
    "go_threshold": 0.4,
    "compilation_threshold": 3.0,
    "damping_factor": 0.85,
    "decay_rate": 0.15,
}


@dataclass
class GainChange:
    """One recorded movement of one gain. C4's audit trail, C5's evidence."""
    name: str
    old: float
    new: float
    trigger: str
    at: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "old": round(self.old, 4), "new": round(self.new, 4),
            "trigger": self.trigger, "at": self.at,
        }


class PlasticGains:
    """
    Bounded, logged, self-correcting parameters (Decision C4).

    Every update is clamped to the gain's declared [floor, ceiling], and every
    accepted update appends to an audit trail. An update that would be clamped
    is recorded as REJECTED rather than silently truncated -- a gain that keeps
    hitting its ceiling is a signal, and hiding that is how a stuck parameter
    looks like a healthy one.
    """

    def __init__(self, **overrides: float):
        self._values: Dict[str, float] = dict(DEFAULTS)
        for name, value in overrides.items():
            if name not in GAIN_SPECS:
                raise KeyError(f"unknown gain {name!r}; known: {sorted(GAIN_SPECS)}")
            self._values[name] = self._clamp(name, value)
        self._last_update: Dict[str, float] = {k: 0.0 for k in GAIN_SPECS}
        self.audit: List[GainChange] = []

    @staticmethod
    def _clamp(name: str, value: float) -> float:
        floor, ceiling, _, _ = GAIN_SPECS[name]
        return max(floor, min(ceiling, float(value)))

    def get(self, name: str) -> float:
        if name not in self._values:
            raise KeyError(f"unknown gain {name!r}")
        return self._values[name]

    def bounds(self, name: str) -> Tuple[float, float]:
        return GAIN_SPECS[name][0], GAIN_SPECS[name][1]

    def _rate_limited(self, name: str) -> Tuple[Optional[float], bool]:
        """A gain may not move faster than its declared timescale.

        Returns (max_distance_allowed_or_None, is_rate_limited). Without the
        rate limit, a single anomalous outcome -- one confusing tool result --
        yanks the threshold to its bound and back, and the system oscillates
        instead of adapting.
        """
        floor, ceiling, timescale, _ = GAIN_SPECS[name]
        elapsed = time.time() - self._last_update[name]
        # last_update == 0.0 means "never moved yet" (time.time() is ~1.7e9).
        # The first update is never rate-limited: a gain that cannot move on
        # its first observation is not plastic, it is stuck.
        if self._last_update[name] == 0.0:
            return None, False
        if elapsed < timescale:
            span = ceiling - floor
            # Allow at most a 10% traverse of the range per elapsed fraction.
            allowed = span * 0.10 * (elapsed / timescale)
            return allowed, True
        return None, False

    def update(self, name: str, proposed: float, trigger: str) -> Tuple[float, bool]:
        """
        Propose a new value for a gain.

        Returns (effective_value, changed). The effective value is always a
        legal one -- the caller's proposal is advisory and may be refused.

        `trigger` is REQUIRED and non-empty. A gain that moved with no recorded
        cause cannot be explained later, which is the failure mode C4 exists to
        prevent.
        """
        if not trigger or not str(trigger).strip():
            raise ValueError("every gain change needs a non-empty trigger")
        floor, ceiling, _, _ = GAIN_SPECS[name]
        old = self._values[name]
        target = self._clamp(name, proposed)
        if abs(target - old) < 1e-9:
            return old, False

        allowed, limited = self._rate_limited(name)
        if limited and allowed is not None:
            # Move only as far as the timescale permits, toward the target.
            if target > old:
                target = min(target, old + allowed)
            else:
                target = max(target, old - allowed)

        if abs(target - old) < 1e-9:
            return old, False

        self._values[name] = target
        self._last_update[name] = time.time()
        self.audit.append(GainChange(name, old, target, trigger))
        return target, True

    # -- C4 feedback rules -------------------------------------------------
    # Each is a pure function of observed outcomes to a proposed value. Kept
    # separate from update() so the mapping is testable without touching state.

    @staticmethod
    def propose_go_threshold(recent_error: float, allostatic_load: float) -> float:
        """
        Higher recent error or higher load => require more evidence to act.

        recent_error    mean |predicted - actual| over recent actions, [0..1]
        allostatic_load sustained arousal, [0..1]
        """
        e = min(1.0, max(0.0, recent_error))
        a = min(1.0, max(0.0, allostatic_load))
        # At zero error and zero load this yields 0.4, the historical constant,
        # so an idle system starts exactly where the fixed version did.
        # Weights sum to 0.30 so the worst case (0.70) lands inside the
        # declared ceiling of 0.75 rather than overshooting it.
        return 0.4 + 0.20 * e + 0.10 * a

    @staticmethod
    def propose_damping(recent_oscillation: float, headroom: float) -> float:
        """
        More oscillation => more damping. Less headroom => more damping too, so
        a loaded substrate converges rather than wandering.
        """
        o = min(1.0, max(0.0, recent_oscillation))
        h = min(1.0, max(0.0, headroom))
        return 0.85 + 0.08 * o - 0.05 * h

    @staticmethod
    def propose_compilation_threshold(success_streak: int, headroom: float) -> float:
        """
        A longer success streak lowers the bar for compiling a skill.
        """
        s = max(0, int(success_streak))
        h = min(1.0, max(0.0, headroom))
        return 3.0 - min(1.0, s * 0.2) + (1.0 - h) * 2.0

    @staticmethod
    def propose_decay_rate(allostatic_load: float, headroom: float) -> float:
        """Forget faster under load; slower when quiet and roomy."""
        a = min(1.0, max(0.0, allostatic_load))
        h = min(1.0, max(0.0, headroom))
        return 0.15 + 0.20 * a - 0.08 * h

    def history(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        if name is None:
            return [c.as_dict() for c in self.audit]
        return [c.as_dict() for c in self.audit if c.name == name]


# ---------------------------------------------------------------------------
# C7 -- Correction by competition. Deterministic newest-wins resolution.
# ---------------------------------------------------------------------------

# The supersession relation. Replacing `superseded` with a richer vocabulary is
# the Decision; keeping one blunt value is what made correction unrepresentable.
EPISTEMIC_STATES = (
    "grounded",      # supported and current
    "disputed",      # contradicted, neither side retracted
    "undercut",      # the defeater for its support failed
    "replaced",      # a newer belief about the same topic took over
    "narrowed",      # still true, but of less scope than it claimed
    "contradicted",  # a newer belief asserts the opposite
    "expired",       # true when written, no longer asserted
    "superseded",    # legacy value, retained so old rows still validate
)


@dataclass
class BeliefRecord:
    id: int
    topic: str
    statement: str
    credence: float
    authority: str
    epistemic_state: str
    valid_from: str
    valid_to: Optional[str] = None
    supersedes_id: Optional[int] = None
    provenance_span: Optional[str] = None
    scope: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "topic": self.topic, "statement": self.statement,
            "credence": self.credence, "authority": self.authority,
            "epistemic_state": self.epistemic_state,
            "valid_from": self.valid_from, "valid_to": self.valid_to,
            "supersedes_id": self.supersedes_id,
            "provenance_span": self.provenance_span, "scope": self.scope,
        }


class SupersessionResolver:
    """
    C7. Decides which belief currently binds for a topic -- in code, not by
    asking a model to choose between two retrieved facts.

    Why this is deterministic, and why it has to be: the benchmark that
    motivated C7 (MemoryAgentBench, arXiv:2507.05257) scores exactly this task,
    retrieving the newest fact given a fact and a contradictory rewrite. The
    best deployed system of that shape scored 7%, and BM25 -- no memory
    substrate at all -- scored 48%. The failure was never storage. It was
    retrieval-plus-judgment, with the judgment handed to a language model.
    The correct answer here is newest-wins, so the system must KNOW that rather
    than infer it per call.

    Ties are broken by id, descending, so the outcome does not depend on the
    order rows happened to come back from the database.
    """

    # A retrieved quote is evidence someone wrote something down. It is never
    # evidence the writer was told it by the user. Letting the two collapse is
    # the single most flattering error a memory system can make.
    PROMOTION_FORBIDDEN = {("retrieved_quote", "user_asserted")}

    def resolve(self, records: List[BeliefRecord]) -> Optional[BeliefRecord]:
        """
        Return the single binding belief for a topic, or None.

        Current = not retired (valid_to is NULL) and not replaced by another
        current record. Among those, the newest valid_from wins; ties break on
        the higher id.
        """
        if not records:
            return None

        current = [r for r in records if r.valid_to is None]
        if not current:
            return None

        replaced_ids = {r.supersedes_id for r in current if r.supersedes_id is not None}
        survivors = [r for r in current if r.id not in replaced_ids]
        if not survivors:
            # Every record claims to supersede another (a cycle). Fall back to
            # the whole current set rather than returning nothing -- an
            # unresolvable ledger must still yield an answer.
            survivors = current

        # Deterministic: newest valid_from, then highest id. Independent of the
        # order the caller supplied, which is the property that matters.
        return sorted(survivors, key=lambda r: (r.valid_from, r.id), reverse=True)[0]

    @classmethod
    def may_promote(cls, frm: str, to: str) -> bool:
        """C10. Is this authority promotion allowed? See PROMOTION_FORBIDDEN."""
        return (frm, to) not in cls.PROMOTION_FORBIDDEN

    def relation_for(self, newer: BeliefRecord, older: BeliefRecord) -> str:
        """
        Classify how `newer` supersedes `older` -- the richer relation from C7.
        Deterministic and content-based, so the same pair always classifies the
        same way.
        """
        if newer.topic != older.topic:
            return "unrelated"
        if self._negates(newer.statement, older.statement):
            return "contradicted"
        if self._narrower(newer.statement, older.statement):
            return "narrowed"
        # Undercut is a drop in support for the SAME claim, so it is checked
        # before the generic "replaced". A claim that is merely restated at
        # lower credence has not been replaced by a different belief; its
        # support has been undercut, and conflating the two loses the reason
        # the old belief stopped binding.
        if newer.credence < older.credence:
            return "undercut"
        return "replaced"

    @staticmethod
    def _negates(a: str, b: str) -> bool:
        negators = (" not ", " no ", " never ", " isn't ", " isn't", " cannot ", " isn't")
        return any(n in a.lower() for n in negators) != any(n in b.lower() for n in negators)

    @staticmethod
    def _narrower(a: str, b: str) -> bool:
        """True when `a` looks like a restriction of `b` (longer, same topic)."""
        return len(a) > len(b) * 1.3 and b.lower()[:20] in a.lower()[:60]


# ---------------------------------------------------------------------------
# C8 -- Affect as a profile, not a scalar.
# ---------------------------------------------------------------------------

# The 2-D and 6-D appraisal models BOTH survive their sources in the arena.
# This is not resolved here on purpose: the appraisal vector is stored along
# with the model that produced it, so a later decision can compare them.
APPRAISAL_MODELS = ("circumplex-2d", "schimmack-6d", "unresolved")

AFFECT_AXES = ("desire", "valence", "arousal")


@dataclass
class AffectProfile:
    """C8. Three axes plus the model that produced them.

    Replacing a single valence scalar loses the wanting/liking dissociation,
    which the arena grades HIGH: a thing can be desired and disliked at once,
    and a scalar forces those to agree.
    """
    desire: float      # how much it is wanted, [0..1]
    valence: float     # how it is valued, [-1..1] -- signed
    arousal: float     # how much it activates, [0..1]
    model: str = "circumplex-2d"
    credence: float = 0.5

    def is_coherent(self) -> bool:
        """
        Coherence = want and value are not forced to agree.

        A coherent profile has valence >= 0 when desire is high (wanted things
        are usually valued) or desire near zero. The incoherent case --
        maximum desire with strongly negative valence -- is the wanting/liking
        dissociation, and it is a REAL state, not a bug. This method reports it
        rather than smoothing it away.
        """
        return not (self.desire > 0.7 and self.valence < -0.5)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "desire": round(self.desire, 4), "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4), "model": self.model,
            "credence": round(self.credence, 4),
            "dissociated": not self.is_coherent(),
        }


# ---------------------------------------------------------------------------
# C9 -- The substrate is a budget with a declared shedding order.
# ---------------------------------------------------------------------------

# Declared, not computed at runtime. The order is a design commitment: identity
# and user assertions are the most expensive to rebuild and the most damaging to
# lose, so they are shed LAST. Retrieval caches are cheap to rebuild and lose
# nothing, so they go FIRST. An undeclared order is an arbitrary one.
SHEDDING_ORDER: Tuple[str, ...] = (
    "retrieval_cache",      # pure cache; recomputed on demand
    "replay_buffers",       # derived; replay regenerates them
    "associative_edges",    # rebuildable from source text
    "affect_profiles",      # derived from appraisals
    "counterfactual_rollouts",
    "narrative_summaries",
    "tool_observations",    # expensive to re-observe, but reproducible
    "sourced_quotes",       # traceable back to a span; re-derivable
    "user_assertions",      # only the operator can supply these again
    "identity",             # never shed
)

# Bands are read as "at least this much headroom". They must be contiguous and
# strictly ordered, or a value falls through two tiers at once.
BUDGET_TIERS = {"comfortable": 0.60, "tight": 0.35, "critical": 0.0}


class SubstrateBudget:
    """
    C9. Track headroom and declare what gets shed, in a fixed order, when it
    runs low. The point is that the order is a documented commitment rather
    than whatever the eviction heuristic happened to prefer.
    """

    def __init__(self, capacity_units: float = 1000.0):
        self.capacity = float(capacity_units)
        self.used = 0.0

    @property
    def headroom(self) -> float:
        return max(0.0, 1.0 - (self.used / self.capacity)) if self.capacity else 0.0

    @property
    def tier(self) -> str:
        h = self.headroom
        for name, threshold in sorted(BUDGET_TIERS.items(), key=lambda kv: -kv[1]):
            if h >= threshold:
                return name
        return "critical"

    def shed_until(self, target_headroom: float, holdings: Dict[str, float]) -> List[str]:
        """
        Return the classes to shed, in SHEDDING_ORDER, until headroom recovers.

        `holdings` maps class name to its unit cost. Classes not in the
        shedding order are never shed -- if something is not declared
        disposable, this method will not dispose of it.
        """
        # Shortfall: how many units must be freed to REACH the target headroom.
        # This is a floor to satisfy, not a value to exceed -- which is why the
        # loop stops as soon as `freed >= needed` instead of continuing to the
        # next class. Over-shedding here would evict an expensive class
        # (sourced_quotes, user_assertions) while a cheap cache was still
        # available, which is the exact failure C9's declared order prevents.
        needed = (target_headroom * self.capacity) - (self.capacity - self.used)
        if needed <= 0:
            return []
        shed: List[str] = []
        freed = 0.0
        for name in SHEDDING_ORDER:
            if freed >= needed:
                break
            if name == "identity":
                continue
            cost = holdings.get(name, 0.0)
            if cost <= 0:
                continue
            shed.append(name)
            freed += cost
        self.used = max(0.0, self.used - freed)
        return shed


# ---------------------------------------------------------------------------
# C3 -- The dorsal/ventral split, as a design constraint on every confidence.
# ---------------------------------------------------------------------------

# C3 rests on ONE line of evidence: the Goodale & Milner double dissociation.
# Two patients, mirror-image lesions, replicated. Its second corroboration
# (arXiv:2606.14512) was withdrawn 2026-09-27 -- that paper is real and is
# "Fodor and Pylyshyn's Systematicity Challenge Still Stands", which concerns
# systematicity, not this dissociation. Do not reinstate it.
#
# The constraint: VENTRAL confidence is safe to act on; DORSAL is not. Anything
# derived from dorsal estimates must carry its uncertainty forward instead of
# collapsing to a point value.


@dataclass
class SplitConfidence:
    ventral: float   # what the system believes it knows; [0..1]
    dorsal: float    # what the visuomotor/predictive system believes; [0..1]

    def action_safe(self) -> bool:
        """May this be acted on without further checking? Ventral only."""
        return self.ventral >= 0.7 and self.dorsal < 0.6

    def report(self) -> str:
        if self.ventral - self.dorsal >= 0.3:
            return ("DORSAL-VENTRAL DIVERGENCE: confidence outruns calibration; "
                    "do not act on the ventral value alone")
        return "aligned"


# ---------------------------------------------------------------------------
# C5 -- Nothing grades itself.
# ---------------------------------------------------------------------------

@dataclass
class VerifierIndependence:
    """
    A verifier that shares its full independence set with what it verifies is a
    self-grader. The arena's support is Mackworth 1943: performance feedback
    eliminated the vigilance decrement where instructing subjects to try harder
    did nothing. Feedback has to come from outside the graded system.
    """
    name: str
    independent_facets: frozenset = frozenset()

    def is_independent_of(self, subject_facets: frozenset) -> bool:
        """
        A verifier is independent only if it DECLARES facets and shares NONE of
        them with the subject. One shared facet -- same credentials, same
        model, same process -- makes it a self-grader.

        An undeclared verifier is NOT independent. Absence of evidence of
        independence is not evidence of independence, and for a self-grading
        check the permissive direction is the dangerous one: a verifier that
        forgot to declare itself would otherwise pass every audit.
        """
        if not self.independent_facets:
            return False
        return not (self.independent_facets & subject_facets)

    def self_grading(self, subject_facets: frozenset) -> bool:
        return not self.is_independent_of(subject_facets)


SUBJECT_FACETS = frozenset({"credentials", "process", "model", "data"})
