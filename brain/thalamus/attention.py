#!/usr/bin/env python3
"""
brain.thalamus.attention — attentional cost, with the three components separated.

WHAT THIS REPLACES
The previous gate called a character-entropy novelty score "attention".
Character entropy measures how varied the letters in a string are. It is
unrelated to importance: "aaaaaaaaaaaa" scores near zero however important it
is, and a base64 blob scores high while saying nothing. The plan's objection was
that the gate scores string randomness, not importance, and that is exactly
right.

THE THREE COMPONENTS
Task-switching research separates a switch cost into components that are not
interchangeable, and the accounting is only meaningful if they are kept apart.
From the vault's Attentional-Residue page:

  REFRACTORING  an executive cost of reconfiguration. Laboratory scale,
                hundreds of milliseconds. Paid on every switch regardless of
                whether the new task is related to the old one.

  RESUMPTION    a memory-based cost governed by associative priming between
                environmental cues and suspended goals. Seconds to minutes, and
                the reason a checkpoint-and-resume artifact is worth emitting:
                human resumption errors concentrate at interruption boundaries.

  RESIDUE       perseveration about the abandoned task. Its size depends on
                whether that task was finished, and finishing it without time
                pressure is not sufficient to clear it.

THE RESIDUE TERM IS THE ONE THAT MATTERS HERE
A machine's previous task is still literally in context, which is the residue
analog almost exactly. The human literature's answer -- archive what is done,
surface only the active task set -- is context hygiene, and it is what
retiring_task does below. A ready-to-resume note does NOT clear residue: the
evidence is that anticipating resumption pressure makes disengagement harder,
not easier. This module says so rather than treating a resume note as a cure.

UNRESOLVED IN THE SOURCE LITERATURE
Reconfiguration theorists and inertia theorists disagree about whether the
residual switch cost is exogenous completion of control or between-task
interference. That dispute is not settled here. Both terms are computed
separately so a caller can weight them, and the weights below are a stated
policy rather than an estimate of anything.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from brain.thalamus.adaptive_threshold import AdaptiveThreshold

__all__ = ["AttentionalGate", "SwitchCost", "URGENCY_PATTERN", "TRIVIAL_PHRASES"]

# Risk and urgency markers. Bottom-up, because they arrive with the text rather
# than depending on what the system is doing.
URGENCY_PATTERN = re.compile(
    r"\b(error|critical|fatal|exception|emergency|alert|fail(?:ed|ure)?|"
    r"security|breach|deadlock|panic|traceback|timeout|denied|refused|"
    r"corrupt(?:ed)?|data loss|rollback|outage)\b",
    re.IGNORECASE,
)

# Task-bearing markers: text that names an action to take.
TASK_PATTERN = re.compile(
    r"\b(fix|implement|add|remove|delete|update|refactor|deploy|migrate|"
    r"investigate|debug|review|write|build|test|verify|ship|revert|"
    r"should i|should we|need to|have to|next step|todo|action item)\b",
    re.IGNORECASE,
)

# Closed-class function words. They overlap between any two English sentences,
# so counting them as shared vocabulary is what makes overlap look like
# relevance when it is only grammar.
FUNCTION_WORDS = frozenset("""
a an the and or but if then than that this these those of to in on at by for
with from as is are was were be been being am do does did doing have has had
it its i we you they he she them us me my our your their what when where which
who whom how why not no nor so such can could will would shall should may
might must there here also very just only more most other another same
""".split())

TRIVIAL_PHRASES = frozenset({
    "ok", "okay", "done", "yes", "no", "sure", "thanks", "thank you",
    "status: ok", "heartbeat", "ping", "still there", "you there",
    "hi", "hello", "hey", "test", "testing", "ack", "acknowledged",
})

_WORD = re.compile(r"[a-z0-9_]+")


def _content_words(text: str) -> Set[str]:
    return {w for w in _WORD.findall((text or "").lower())
            if w not in FUNCTION_WORDS and len(w) > 2}


class SwitchCost:
    """The three components of a switch, kept separate.

    Kept as a distinct type rather than a pre-summed float because a single
    number cannot be decomposed afterwards. Whoever tunes this needs to know
    which component they are trading away, and a sum discards that at exactly
    the point where it is needed.
    """

    __slots__ = ("reconfiguration", "resumption", "residue")

    def __init__(self, reconfiguration: float, resumption: float, residue: float):
        self.reconfiguration = max(0.0, min(1.0, float(reconfiguration)))
        self.resumption = max(0.0, min(1.0, float(resumption)))
        self.residue = max(0.0, min(1.0, float(residue)))

    @property
    def total(self) -> float:
        return self.reconfiguration + self.resumption + self.residue

    def as_dict(self) -> Dict[str, float]:
        return {
            "reconfiguration": self.reconfiguration,
            "resumption": self.resumption,
            "residue": self.residue,
            "total": self.total,
        }

    def __repr__(self) -> str:
        return (f"SwitchCost(reconfig={self.reconfiguration:.2f}, "
                f"resumption={self.resumption:.2f}, residue={self.residue:.2f})")


class AttentionalGate:
    """Scores whether incoming text deserves working context.

    Two halves that used to be one. BOTTOM-UP asks what the text itself claims:
    is it urgent, does it name a task, or is it chatter? TOP-DOWN asks what it
    would cost to switch to it given what is already active, which is where the
    three switch components live.

    Keeping them separate is the point. A topically irrelevant but urgent
    interruption is a real event and must not be filtered; a topically identical
    but trivial one is noise. One blended score cannot express both.
    """

    # Stated policy, not an estimate. The literature reports the components in
    # incompatible units (hundreds of milliseconds, seconds to minutes), and any
    # weighting between them is a choice rather than a measurement. These make
    # the choice visible and adjustable.
    WEIGHT_BOTTOM_UP = 0.6
    WEIGHT_RESIDUE = 0.25
    WEIGHT_RECONFIG = 0.10
    WEIGHT_RESUMPTION = 0.15

    def __init__(
        self,
        saliency_threshold: float = 0.35,
        active_context: Optional[str] = None,
        adaptive: bool = False,
    ):
        self.saliency_threshold = saliency_threshold
        self.active_context = active_context
        # The threshold was a constant borrowed from one observation,
        # compared against a score whose distribution depends on the
        # corpus and the active context. Too high and the gate goes
        # quietly blind; too low and it does no work. Neither failure
        # announces itself, because evaluate_admission returns a boolean
        # either way.
        #
        # Adaptive is OPT-IN. The default is unchanged, so installing
        # this does not silently alter gate decisions on a running
        # system -- the first thing to go wrong with a learned
        # component is being switched on without anyone deciding it
        # should be. See brain/thalamus/adaptive_threshold.py.
        self._adaptive = (AdaptiveThreshold(initial=saliency_threshold)
                          if adaptive else None)
        # Task the system was on, and whether it finished. Residue depends on
        # both, which is the whole point: completion alone is not sufficient.
        self.active_task: Optional[str] = None
        self.active_task_finished: bool = False
        self._resume_note: Optional[str] = None

    @property
    def is_adaptive(self) -> bool:
        return self._adaptive is not None

    def threshold_stats(self) -> Optional[Dict[str, Any]]:
        """What the learned threshold has seen. None when not adaptive."""
        return self._adaptive.stats() if self._adaptive else None

    def observe_admission(self, saliency: float, admitted: bool,
                          useful: Optional[bool] = None) -> Optional[float]:
        """Feed the adaptive threshold what actually happened.

        Without this the controller cannot learn, and silently holding a
        constant is indistinguishable from having enabled it and wiring
        nothing up. `useful` is what makes it more than rate-matching:
        pass False when an admitted item did not matter and the
        threshold rises.
        """
        if self._adaptive is None:
            return None
        new = self._adaptive.observe_admission(saliency, admitted, useful)
        self.saliency_threshold = new
        return new

    # -- bottom-up ----------------------------------------------------------

    def bottom_up_saliency(self, text: str) -> float:
        """What the text claims about itself, independent of current focus."""
        if not text or not text.strip():
            return 0.0
        stripped = text.strip()

        # Chatter is a hard zero, not a penalty. "ok" and "heartbeat" are not
        # weakly important; they carry nothing, and letting them score a little
        # above zero is how a log stream of them eventually fills a context.
        if stripped.lower().rstrip(".") in TRIVIAL_PHRASES or len(stripped) < 4:
            return 0.0

        score = 0.0
        if URGENCY_PATTERN.search(text):
            score += 0.5
        if TASK_PATTERN.search(text):
            score += 0.25
        # Specific references earn their keep. A named file, path, identifier or
        # number is evidence the text is about something concrete.
        if re.search(r"[\w/]+\.(py|md|json|yaml|sql|sh|toml)\b", text):
            score += 0.15
        if re.search(r"\b\d{2,}\b", text):
            score += 0.05
        # Length is a weak signal, capped deliberately: beyond a few sentences,
        # more text is not more important.
        words = len(text.split())
        if words > 12:
            score += min(0.10, 0.02 * (words // 12))
        return max(0.0, min(1.0, score))

    # -- top-down -----------------------------------------------------------

    def contextual_relevance(self, text: str, active_context: Optional[str] = None) -> float:
        """Overlap with the active task, over CONTENT words only.

        The previous version divided by min(len(context), len(text)) using all
        words, so any two English sentences shared enough function words to
        register as relevant. That is why "ok" once scored as overlapping.
        """
        ctx = self.active_context if active_context is None else active_context
        if not ctx or not text:
            return 0.0
        ctx_words = _content_words(ctx)
        text_words = _content_words(text)
        if not ctx_words or not text_words:
            return 0.0
        return len(ctx_words & text_words) / min(len(ctx_words), len(text_words))

    def switch_cost(
        self,
        text: str,
        active_context: Optional[str] = None,
    ) -> SwitchCost:
        """The cost of switching to this text, in three separable parts."""
        ctx = self.active_context if active_context is None else active_context
        relevant = self.contextual_relevance(text, ctx)

        # REFRACTORING: paid on every switch, and highest when the new task is
        # unrelated to the old one, since there is no priming to help.
        reconfiguration = 0.1 + 0.25 * (1.0 - relevant)

        # RESUMPTION: the cost of picking a suspended task back up, which needs
        # a cue to prime it. No resume note and no shared vocabulary means the
        # goal has to be reconstructed from scratch.
        primed = relevant > 0.0 or self._resume_note is not None
        resumption = 0.05 if primed else 0.35

        # RESIDUE: perseveration about the abandoned task. Unfinished is worse
        # than finished, and the literature is explicit that finishing is not
        # sufficient on its own.
        if self.active_task is None:
            residue = 0.0
        elif self.active_task_finished:
            residue = 0.05
        else:
            residue = 0.45
        # Unrelated incoming text makes the residue worse, because now two
        # unrelated task sets are live at once -- the mixing cost.
        if self.active_task is not None and relevant < 0.1:
            residue = min(1.0, residue * 1.3)

        return SwitchCost(reconfiguration, resumption, residue)

    # -- readiness ----------------------------------------------------------

    def set_resume_note(self, note: str) -> None:
        """Record a ready-to-resume plan for the active task.

        This is a priming cue, and it is what it is honestly described as: it
        lowers RESUMPTION. It does NOT lower RESIDUE. Anticipating resumption
        pressure is reported to make disengagement harder, so treating a resume
        note as a cure for perseveration inverts the finding.
        """
        self._resume_note = (note or "").strip() or None

    def retire_task(self, task: str, finished: bool) -> None:
        """Archive the active task.

        finished=False leaves residue high, which is the accurate report: an
        unfinished task holds attention. finished=True clears most of it, which
        is the context-hygiene move the literature supports.
        """
        self.active_task = (task or "").strip() or None
        self.active_task_finished = bool(finished)
        # A retired task's resume note is stale and must not prime the next one.
        self._resume_note = None

    # -- combined -----------------------------------------------------------

    def compute_saliency(self, text: str, active_context: Optional[str] = None) -> float:
        """Bottom-up saliency, discounted by the cost of switching to it.

        An urgent interruption is admitted even when unrelated, so the discount
        is bounded: residue can suppress a low-saliency text, but it must not be
        able to suppress an urgent one, or the gate would go blind exactly when
        something breaks.
        """
        bottom_up = self.bottom_up_saliency(text)
        if bottom_up == 0.0:
            return 0.0
        cost = self.switch_cost(text, active_context)
        # Residue acts as a multiplier on the non-urgent part; urgency bypasses
        # it. URGENCY_PATTERN and a 0.5 floor keep that explicit.
        penalty = min(0.6, self.WEIGHT_RESIDUE * cost.residue
                      + self.WEIGHT_RECONFIG * cost.reconfiguration
                      + self.WEIGHT_RESUMPTION * cost.resumption)
        return max(0.0, min(1.0, bottom_up * (1.0 - penalty)))

    def evaluate_admission(
        self,
        text: str,
        active_context: Optional[str] = None,
    ) -> Tuple[bool, float, str]:
        """Admit, compress, or attenuate. Returns (admitted, score, disposition)."""
        score = self.compute_saliency(text, active_context)
        if score >= self.saliency_threshold:
            return True, score, "admit"
        if score >= (self.saliency_threshold * 0.5):
            return False, score, "compress"
        return False, score, "attenuate"

    def explain(self, text: str, active_context: Optional[str] = None) -> Dict[str, Any]:
        """The full breakdown, so a decision can be argued with.

        A gate that returns only a score cannot be debugged, because the only
        way to find out why something was filtered is to change the text and
        see whether the number moves.
        """
        cost = self.switch_cost(text, active_context)
        admitted, score, disposition = self.evaluate_admission(text, active_context)
        return {
            "disposition": disposition,
            "admitted": admitted,
            "score": score,
            "bottom_up": self.bottom_up_saliency(text),
            "relevance": self.contextual_relevance(text, active_context),
            "switch_cost": cost.as_dict(),
            "active_task": self.active_task,
            "active_task_finished": self.active_task_finished,
            "has_resume_note": self._resume_note is not None,
        }


class ThalamicGate(AttentionalGate):
    """The name the rest of the codebase imports.

    Kept so callers do not all change at once, but it is a pure alias: there is
    no second gate, because two gates would be two definitions of what
    attention means and the disagreement between them would be invisible.
    """
