#!/usr/bin/env python3
"""
brain.limbic.amygdala — threat appraisal, low-road threat detection, and
affective tagging.

There was no amygdala in this codebase. docs/gaps/brain-region-recommendations.md
recorded it as "ABSENT / BUILD -- unclaimed territory", and the audit
confirmed it: zero files. The limbic package existed and contained no
amygdala, so the region was missing rather than broken.

WHAT THIS IS NOT
----------------
Not a sentiment classifier, and not a "how does this text feel" score.
Those are the things people reach for when they conflate affect with
valence, and they are measurably different things: a neutral sentence
about a terminal diagnosis is not valenced, and a cheerful sentence
about terminal diagnosis is positively valenced and correctly
threatening. The amygdala here is about THREAT and APPRAISAL, with
valence as one input rather than the output.

THE THREE-PATHWAY ARCHITECTURE
-------------------------------
The vault's Fear-Conditioning-Extinction page is explicit that threat
information reaches the amygdala by two routes:

  Low road  (sensory -> amygdala):      fast, crude, subcortical.
                                        Rough, ahead of comprehension.
  High road (sensory -> cortex -> amygdala): slower, accurate,
                                        contextualised, revisable.

Our own earlier recommendation named a THIRD: the hyperdirect pathway
(cortex -> amygdala), a top-down shortcut that lets a known threat be
acted on before analysis completes. LeDoux's later work treats the low
road and hyperdirect as a single fast system precisely because both
skip the bottleneck of thalamic relay. This module implements all three
and reports which one fired -- because "the amygdala said no" is not
an answerable question, while "the low road fired at 0.3 with no
cortical corroboration" is.

The threshold between them is LATENCY, and it is a parameter, not a
constant. A cheap check fast-pathing to a threat response is a
different system from one that waits 500ms for context.

EXTINCTION IS INHIBITION, NOT ERASURE
------------------------------------
The single most important thing the vault says, and the thing a naive
implementation gets backwards:

  "Extinction is not erasure."
  Return of fear has THREE routes:
    1. Renewal          -- context change removes the safety signal
    2. Spontaneous recovery -- inhibition decays faster than excitation
    3. Reinstatement    -- an isolated US reactivates the association

So extinction is modelled as a second, INHIBITORY association layered
over the original excitatory one, and both are retained. The original
threat learning is never deleted. This is not a stylistic choice: a
model that erases on extinction cannot express renewal, because there
is nothing left to return to. Three tests assert the three routes
individually, because getting any one of them wrong is the standard way
this gets built incorrectly.

HYPERDIRECT / VAULT DISAGREEMENT
--------------------------------
The vault's Extinction page does not contain the word "hyperdirect",
and a bounded Oracle query for it came back a confident MISS. The
hyperdirect pathway is nonetheless real and is in our recommendation
doc, which cites LeDoux. Rather than resolve that by assertion, this
module implements the two pathways the vault DOES describe (low road,
high road) as the primary architecture, and treats hyperdirect as a
configurable top-down input that is OFF by default with its evidence
source recorded in the docstring. That way nothing rests on a claim I
could not source.

HONEST LIMITS
-------------
- Lexical matching, not semantic. "the process was killed" and "the
  process was terminated" are the same threat; "the tumour was
  resected" may not be caught. Deterministic and inspectable, which is
  the point, but it misses paraphrase.
- No decay of the excitatory association over time. Only the INHIBITORY
  association decays, which reproduces spontaneous recovery
  quantitatively but is a simplification of the biology.
- Threat detection is not a moral or clinical judgement. It is a
  salience signal for gating decisions, and a false positive here
  should cost a latency, not a refusal. A refusal belongs to the
  basal ganglia, which is the region that can actually deny.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

__all__ = ["Amygdala", "AmygdalaDecision", "APPARAL_TERMS", "THREAT_TERMS"]


# ── appraisal vocabulary ────────────────────────────────────────────
# Deliberately small and inspectable. Every term is a class of cue, not
# a sentiment score: "consequence" and "irreversible" signal severity,
# while "sudden" and "unknown" signal unpredictability. Lazarus's
# appraisal dimensions, reduced to what can be detected lexically.

THREAT_TERMS: Dict[str, float] = {
    # irreversibility / severity
    "fatal": 0.9, "deadly": 0.9, "catastrophic": 0.95, "irreversible": 0.85,
    "destroy": 0.85, "destroyed": 0.85, "corrupt": 0.8, "corrupted": 0.8,
    "breach": 0.85, "breached": 0.85, "leak": 0.8, "leaked": 0.8,
    "data loss": 0.9, "lost data": 0.9, "wiped": 0.85, "overwritten": 0.7,
    "revoked": 0.7, "terminated": 0.6, "deleted": 0.6, "crash": 0.7,
    "crashed": 0.7, "failed": 0.5, "failure": 0.55, "outage": 0.8,
    # irreversibility of time
    "expired": 0.6, "expiring": 0.6, "deadline": 0.5, "overdue": 0.6,
    "last chance": 0.7, "final": 0.5, "final warning": 0.8,
}

APPARAL_TERMS: Dict[str, float] = {
    # unpredictability / lack of control
    "unknown": 0.6, "unexpected": 0.65, "suddenly": 0.55, "sudden": 0.55,
    "random": 0.5, "unpredictable": 0.7, "maybe": 0.35, "possibly": 0.35,
    "might": 0.3, "unsure": 0.5, "unclear": 0.4, "warning": 0.6,
    # loss of control
    "cannot": 0.5, "can't": 0.5, "unable": 0.55, "blocked": 0.6,
    "stuck": 0.5, "lost": 0.6, "lost control": 0.75,
    # escalation
    "escalat": 0.7, "urgent": 0.6, "critical": 0.75, "emergency": 0.85,
    "danger": 0.85, "dangerous": 0.85, "risk": 0.55, "unsafe": 0.7,
}

# Safety / no-threat markers. These suppress the high road's alarm when
# the context is explicitly benign -- the contextual modulation the vault
# attributes to the hippocampus and PFC.
SAFETY_TERMS = (
    "hypothetical", "for example", "e.g.", "in theory", "simulated",
    "mock", "test environment", "sandbox", "toy", "imagine", "fictional",
    "documentation", "as a metaphor", "no risk",
)

# Word-boundary matcher built once. Substring matching would fire
# "final" inside "finally" and "leak" inside "leakage-check", which is
# how a threshold detector becomes noise.
_WORD = {t: re.compile(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", re.I)
         for t in list(THREAT_TERMS) + list(APPARAL_TERMS)}


class AmygdalaDecision:
    """What the amygdala concluded, and by which route.

    `pathway` is load-bearing. "The amygdala responded" is not an
    answerable question; "the low road fired without cortical
    corroboration" is.
    """

    def __init__(self, pathway: str, threat_score: float,
                 arousal: float, confidence: float,
                 triggers: List[str], rationale: str,
                 requires_context: bool = False):
        self.pathway = pathway
        self.threat_score = threat_score
        self.arousal = arousal
        self.confidence = confidence
        self.triggers = triggers
        self.rationale = rationale
        self.requires_context = requires_context

    @property
    def is_threat(self) -> bool:
        return self.pathway in ("low_road", "hyperdirect")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pathway": self.pathway,
            "is_threat": self.is_threat,
            "threat_score": round(self.threat_score, 4),
            "arousal": round(self.arousal, 4),
            "confidence": round(self.confidence, 4),
            "triggers": list(self.triggers),
            "rationale": self.rationale,
            "requires_context": self.requires_context,
        }

    def __repr__(self) -> str:
        return "AmygdalaDecision(%s, threat=%.3f, arousal=%.3f)" % (
            self.pathway, self.threat_score, self.arousal)


class Amygdala:
    """Threat appraisal and affective tagging, with the three pathways
    separated and extinction modelled as inhibition.

    Deterministic and dependency-free by design. Every trigger it
    fires on is inspectable, which is the property that matters for a
    component that can fast-path a response before comprehension.
    """

    def __init__(self, low_road_threshold: float = 0.55,
                 decay_rate: float = 0.02,
                 enable_hyperdirect: bool = False):
        # Excitatory (original) associations: cue -> strength.
        self.associations: Dict[str, float] = {}
        # Inhibitory (extinction) associations: cue -> strength.
        # Both are retained. See the module docstring: extinction is
        # not erasure, and a model that erases cannot express renewal.
        self.inhibitory: Dict[str, float] = {}
        self.low_road_threshold = low_road_threshold
        self.decay_rate = decay_rate
        # Off by default. The hyperdirect pathway is real (LeDoux) but
        # is not described in our vault's fear-conditioning page, and a
        # bounded Oracle query for it returned a confident MISS. It is
        # wired and switchable rather than quietly assumed.
        self.enable_hyperdirect = enable_hyperdirect
        # Contexts in which extinction was learned. Renewal happens
        # when the context changes and the inhibitor no longer applies.
        self.extinction_contexts: Dict[str, Set[str]] = {}
        self.history: List[Dict[str, Any]] = []

    # ── appraisal ────────────────────────────────────────────────────

    def _scan(self, text: str) -> Tuple[float, float, List[str]]:
        """Lexical appraisal. Returns (severity, unpredictability, hits)."""
        severity = 0.0
        unpredict = 0.0
        hits: List[str] = []
        for term, weight in THREAT_TERMS.items():
            if _WORD[term].search(text):
                severity = max(severity, weight)
                hits.append("threat:" + term)
        for term, weight in APPARAL_TERMS.items():
            if _WORD[term].search(text):
                unpredict = max(unpredict, weight)
                hits.append("appraisal:" + term)
        return severity, unpredict, hits

    def _is_explicitly_benign(self, text: str) -> bool:
        low = text.lower()
        return any(marker in low for marker in SAFETY_TERMS)

    def appraise(self, text: str, context: Optional[str] = None,
                 has_cortical_input: bool = False) -> AmygdalaDecision:
        """Appraise `text` for threat and return a decision.

        `has_cortical_input` is the high road's precondition. Without it
        the decision is low-road: fast, crude, and explicitly marked as
        uncorroborated via `requires_context`.
        """
        severity, unpredict, hits = self._scan(text)
        threat = max(severity, unpredict * 0.8)

        if self._is_explicitly_benign(text):
            return AmygdalaDecision(
                pathway="benign_context", threat_score=0.0, arousal=0.1,
                confidence=0.6, triggers=[],
                rationale="explicitly benign framing; threat cues suppressed")

        # Learned association for this text, minus any inhibition.
        learned = self.net_association(text, context)

        if not has_cortical_input:
            # LOW ROAD: no cortical corroboration available.
            effective = max(threat, learned)
            if effective >= self.low_road_threshold:
                return AmygdalaDecision(
                    pathway="low_road", threat_score=effective,
                    arousal=min(1.0, effective + unpredict * 0.2),
                    confidence=0.5, triggers=hits,
                    rationale=("fast subcortical detection without cortical "
                               "corroboration"),
                    requires_context=True)
            return AmygdalaDecision(
                pathway="none", threat_score=effective,
                arousal=min(1.0, effective), confidence=0.6, triggers=hits,
                rationale="below low-road threshold")

        # HIGH ROAD: cortical input present, so the decision can be
        # revised by context. Deliberately more conservative than the low
        # road -- that asymmetry is the point of having two pathways.
        if threat >= self.low_road_threshold:
            return AmygdalaDecision(
                pathway="high_road", threat_score=threat,
                arousal=min(1.0, threat + unpredict * 0.2),
                confidence=0.85, triggers=hits,
                rationale="corroborated appraisal; context available")
        return AmygdalaDecision(
            pathway="none", threat_score=threat, arousal=min(1.0, threat),
            confidence=0.8, triggers=hits,
            rationale="corroborated; below threshold")

    def hyperdirect_check(self, known_threat: bool,
                          is_urgent: bool) -> AmygdalaDecision:
        """Top-down shortcut: a threat we already know, acted on now.

        Disabled unless `enable_hyperdirect` is set. See the module
        docstring on the evidence status of this pathway.
        """
        if not self.enable_hyperdirect:
            return AmygdalaDecision(
                pathway="hyperdirect_disabled", threat_score=0.0,
                arousal=0.0, confidence=1.0, triggers=[],
                rationale="hyperdirect pathway not enabled")
        if known_threat and is_urgent:
            return AmygdalaDecision(
                pathway="hyperdirect", threat_score=0.9, arousal=0.85,
                confidence=0.75, triggers=["known_threat", "urgent"],
                rationale="top-down shortcut for an established, urgent threat")
        return AmygdalaDecision(
            pathway="none", threat_score=0.0, arousal=0.0, confidence=0.9,
            triggers=[], rationale="hyperdirect preconditions not met")

    # ── conditioning ─────────────────────────────────────────────────

    def condition(self, cue: str, unconditioned_stimulus: bool = True) -> float:
        """Pair a cue with a threat (classical conditioning).

        Returns the new association strength. The excitatory
        association only ever grows here; extinction is a separate
        operation because conflating them is what makes models unable
        to express return of fear.
        """
        key = self._key(cue)
        current = self.associations.get(key, 0.0)
        # Rescorla-Wagner style: growth is larger when the association is
        # weak, so repeated pairings saturate rather than run away.
        delta = (1.0 - current) * (0.6 if unconditioned_stimulus else 0.3)
        self.associations[key] = min(1.0, current + delta)
        return self.associations[key]

    def extinguish(self, cue: str, context: str = "default",
                   trials: int = 1) -> float:
        """Present the cue without the threat.

        Builds an INHIBITORY association. The excitatory association is
        untouched -- that is what makes renewal, spontaneous recovery
        and reinstatement possible at all.
        """
        key = self._key(cue)
        current = self.inhibitory.get(key, 0.0)
        self.inhibitory[key] = min(1.0, current + 0.3 * trials)
        self.extinction_contexts.setdefault(key, set()).add(context)
        return self.inhibitory[key]

    def net_association(self, cue: str,
                        context: Optional[str] = None) -> float:
        """Excitatory minus inhibitory, less decay.

        The inhibitory term decays FASTER than the excitatory one. That
        asymmetry IS spontaneous recovery (route 2 of return of fear)
        and is the reason a well-extinguished fear comes back on its own
        rather than needing anything to happen to it.

        The decay is applied to the EXCITATORY term before the
        subtraction, not to the result afterwards. Applying it to the
        clamped result was a real bug: once inhibition had driven net
        below zero, net was pinned at 0.0 and further decay subtracted
        from nothing, so spontaneous recovery could never lift a
        fully-extinguished association back above zero. That is the
        single most characteristic property of return of fear, and it
        was silently dead.
        """
        key = self._key(cue)
        exc = self.associations.get(key, 0.0)
        inh = self.inhibitory.get(key, 0.0)
        if exc <= 0.0:
            return 0.0
        # Excitation decays slowly and never below the point where
        # reinstatement could not revive it.
        decayed_exc = max(0.0, exc - self.decay_rate * 0.25)
        net = decayed_exc - inh
        # Inhibition is context-bound. In a different context it does
        # not apply at all -- this is renewal (route 1).
        if context is not None:
            ctxs = self.extinction_contexts.get(key, set())
            if ctxs and context not in ctxs:
                net = decayed_exc
        return max(0.0, min(1.0, net))

    # ── the three routes to return of fear ───────────────────────────

    def renewal(self, cue: str, new_context: str) -> float:
        """Route 1: fear returns when context changes.

        The safety signal was learned in a context; a different context
        removes it, so the original excitatory association is unmasked.
        """
        return self.net_association(cue, context=new_context)

    def spontaneous_recovery(self, cue: str, context: Optional[str] = None,
                             steps: int = 1) -> float:
        """Route 2: fear returns with time alone.

        Inhibitory associations decay faster than excitatory ones, so
        net association climbs back without any new pairing.
        """
        key = self._key(cue)
        for _ in range(steps):
            self.inhibitory[key] = max(
                0.0, self.inhibitory.get(key, 0.0) - self.decay_rate * 2)
        return self.net_association(cue, context=context)

    def reinstatement(self, cue: str) -> float:
        """Route 3: an isolated US reactivates the original association.

        The excitatory association was never erased, so presenting the
        unconditioned stimulus again restores it fully.
        """
        key = self._key(cue)
        # Reactivation strengthens the original, exactly as the vault
        # describes: the US drives the ORIGINAL threat association
        # directly, not the learned inhibition.
        self.associations[key] = min(1.0, self.associations.get(key, 0.0) + 0.2)
        return self.associations[key]

    # ── affective tagging ────────────────────────────────────────────

    def tag(self, text: str) -> Dict[str, float]:
        """Affective tag for a memory: valence and arousal, not sentiment.

        Negative valence comes from threat terms; arousal from both
        threat and unpredictability. A neutral sentence scores near zero
        on both, which a sentiment classifier would get wrong by
        reading tone where there is none.
        """
        severity, unpredict, _ = self._scan(text)
        return {
            "valence": -round(max(severity, unpredict * 0.5), 4),
            "arousal": round(min(1.0, (severity + unpredict) / 2.0), 4),
        }

    # ── introspection ────────────────────────────────────────────────

    @staticmethod
    def _key(cue: str) -> str:
        return " ".join(cue.strip().lower().split())

    def state(self) -> Dict[str, Any]:
        return {
            "associations": {k: round(v, 3) for k, v in self.associations.items()},
            "inhibitory": {k: round(v, 3) for k, v in self.inhibitory.items()},
            "low_road_threshold": self.low_road_threshold,
            "hyperdirect_enabled": self.enable_hyperdirect,
            "conditioned_cues": len(self.associations),
        }

    def reset(self) -> None:
        self.associations.clear()
        self.inhibitory.clear()
        self.extinction_contexts.clear()
        self.history.clear()
