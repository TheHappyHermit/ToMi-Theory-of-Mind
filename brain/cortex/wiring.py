#!/usr/bin/env python3
"""
brain.cortex.wiring — gate the six unwired subsystems behind real signals.

WHAT THIS IS FOR
Six subsystems are constructed in HermesBrain.__init__ and never called. An
unconditional call is worse than no call: it costs tokens, returns something, and
gives the appearance of a working brain. So every gate below is a question about
the incoming stimulus that is occasionally true, and each subsystem is invoked
only when its answer is yes.

A gate that never fires is a defect, not a safety property. Each one therefore has
a test that drives it to fire, not merely a test that it does not crash. That is
the difference between a subsystem that is observably wired and one that is
unwired with extra steps.

THE ORDER IS THE ARGUMENT
  defeater_graph  detects that something must be surrendered
  agm             decides WHICH belief is surrendered, by entrenchment
  dialectic       synthesises when entrenchment cannot choose
  chronesthesia   mental time travel, only when the text points at a time
  counterfactual  rolls out the alternative at a real decision point
  associative_graph  a second candidate source, never a default

AGM runs only after the defeater graph found a contradiction. Running it without
one is meaningless: revision is a response to conflict, and with no conflict it
either does nothing or, worse, revises something for no stated reason.

NONE OF THIS MEASURES ANYTHING. It records what happened to the observation log.
Producing a quality number from these calls is a separate activity and is not
what this module does.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["CognitiveWiring", "GATE_NAMES"]

GATE_NAMES = (
    "defeater_graph",
    "agm",
    "dialectic",
    "chronesthesia",
    "counterfactual",
    "associative_graph",
)

# Tokens that mark an explicit reference to a point in time. Deliberately narrow.
# A broad net would fire on "recent" in any technical sentence and turn mental
# time travel into an expensive no-op that runs on most turns.
TEMPORAL_MARKERS = (
    "yesterday", "last week", "last month", "last year", "last time",
    "previously", "used to", "we switched", "we changed", "before that",
    "originally", "at the time", "back then", "earlier version",
    "what did we", "did we ever", "how did we", "since we", "since we switched",
    "no longer", "used to be",
)

# A decision point: the text commits to doing something. Counterfactual rollout
# is expensive and its output is only interesting where there was a real choice.
DECISION_MARKERS = (
    "should i", "should we", "do you think", "worth it", "better to",
    "let's ", "lets ", "i'll ", "we'll ", "going to", "plan to",
    "decision", "decide", "choose", "trade-off", "tradeoff",
    "instead of", "rather than", "option a", "alternative",
)

# Negation and hedge markers. A belief asserted in the negative is the strongest
# kind of contradiction to a stored positive, and it is also the easiest to
# mistake for agreement: "the graph is not faster" contains "graph" and
# "faster" and means the opposite of the stored belief.
NEGATION_MARKERS = (
    "not", "isn't", "is not", "aren't", "no longer", "never", "doesn't",
    "does not", "don't", "won't", "cannot", "can't", "stopped", "reverted",
    "actually", "wrong", "incorrect", "turned out",
)

_STOPWORDS = frozenset("""
a an the and or but if then than that this these those of to in on at by for with
from as is are was were be been being do does did have has had it its it's
i we you they he she them us me my our your their what when where which who
not no nor so such can could will would shall should may might must
""".split())


def _tokens(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if w not in _STOPWORDS]


class CognitiveWiring:
    """Decides which of the six subsystems to invoke, and invokes them.

    Holds no state of its own beyond counters. Every gate reads the stimulus and
    the brain's existing subsystems; nothing is cached, because a cached gate
    result would be a gate answering a question nobody asked.
    """

    def __init__(self, brain):
        self.brain = brain
        # Cumulative counts, for observability. A subsystem that has fired zero
        # times in a thousand turns is not working, and this is how you find out
        # without reading a log.
        self.fired: Dict[str, int] = {name: 0 for name in GATE_NAMES}
        self.skipped: Dict[str, int] = {name: 0 for name in GATE_NAMES}

    # -- gate predicates ----------------------------------------------------
    # Each returns (should_run, reason). The reason goes into the output so a
    # caller can see WHY a subsystem did or did not run, which is the difference
    # between a system you can debug and one you can only observe.

    def gate_defeater(self, text: str) -> Tuple[bool, str]:
        """Fire when the text might contradict something already believed.

        Two conditions, either sufficient: an explicit negation near a known
        belief term, or a known belief term restated with a confident assertion.
        Requires a term overlap with stored beliefs, so text about a topic nothing
        is believed about never fires this.
        """
        low = text.lower()
        negated = any(m in low for m in NEGATION_MARKERS)
        known = self._known_belief_terms()
        if not known:
            return False, "no stored beliefs to contradict"
        overlap = sorted(set(_tokens(low)) & known)
        if not overlap:
            return False, "no term overlap with any stored belief"
        if negated:
            return True, f"negation marker alongside stored belief terms: {overlap[:4]}"
        return False, f"belief terms present ({overlap[:4]}) but no contradiction signal"

    def gate_agm(self, defeater_result: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        """AGM decides which belief is surrendered. Only after a contradiction.

        It also needs two grounded beliefs on the same topic. With one belief
        there is nothing to choose between, and entrenchment ordering over a
        single element is a no-op dressed as a decision.
        """
        if not defeater_result or not defeater_result.get("contradiction"):
            return False, "no contradiction detected; revision has nothing to respond to"
        contested = defeater_result.get("contested") or []
        if len(contested) < 2:
            return False, "only one belief on the contested topic; nothing to choose between"
        return True, f"{len(contested)} contested beliefs to rank by entrenchment"

    def gate_dialectic(self, defeater_result: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        """Synthesis, not tie-breaking. Needs two or more live positions."""
        contested = (defeater_result or {}).get("contested") or []
        active = [c for c in contested if c.get("epistemic_state") != "superseded"]
        if len(active) < 2:
            return False, f"{len(active)} active position(s); synthesis needs two or more"
        return True, f"{len(active)} active, non-superseded positions"

    def gate_chronesthesia(self, text: str) -> Tuple[bool, str]:
        """Mental time travel. Only when the text names a time."""
        low = text.lower()
        hits = [m for m in TEMPORAL_MARKERS if m in low]
        if not hits:
            return False, "no temporal reference in the text"
        if not self.brain.chronesthesia.timeline_events:
            # Firing here would call retrospection with an empty timeline and
            # return None, which is indistinguishable from "asked and nothing
            # found" and costs a call. Say so instead.
            return False, f"temporal reference present ({hits[:2]}) but no timeline recorded yet"
        return True, f"temporal reference: {hits[:2]}, {len(self.brain.chronesthesia.timeline_events)} events"

    def gate_counterfactual(self, text: str, mode: str) -> Tuple[bool, str]:
        """Roll out the alternative, but only at a genuine decision point.

        SYSTEM_2 is required as well as a decision marker: the expensive
        subsystem should not run on a reflex.
        """
        if mode != "SYSTEM_2":
            return False, f"routed {mode}, not a deliberation point"
        low = text.lower()
        hits = [m for m in DECISION_MARKERS if m in low]
        if not hits:
            return False, "deliberative route but no decision language"
        return True, f"SYSTEM_2 and decision language: {hits[:3]}"

    def gate_associative_graph(self, mode: str, text: str) -> Tuple[bool, str]:
        """A second candidate source, never a default.

        Fires on the deliberate route, or when the text spans enough distinct
        concepts that a single document is unlikely to hold the whole answer.
        """
        if mode == "SYSTEM_2":
            return True, "deliberative route; association is a candidate source here"
        concepts = set(_tokens(text))
        if len(concepts) >= 12:
            return True, f"{len(concepts)} distinct concepts; single-document answer unlikely"
        return False, f"{len(concepts)} concepts, reflexive route; association not needed"

    # -- helpers ------------------------------------------------------------

    def _known_belief_terms(self) -> set:
        """Content words appearing in stored belief statements.

        Read from the defeater graph's own view of the beliefs, so the gate and
        the subsystem it gates always agree about what is believed.
        """
        try:
            beliefs = self.brain.defeater_graph.get_grounded_beliefs()
        except Exception:
            return set()
        terms = set()
        for b in beliefs or []:
            for field in ("statement", "topic"):
                value = b.get(field) if isinstance(b, dict) else None
                if value:
                    terms.update(_tokens(str(value)))
        return terms

    def _mark(self, name: str, ran: bool) -> None:
        (self.fired if ran else self.skipped)[name] += 1

    # -- the pass -----------------------------------------------------------

    def run(self, text: str, mode: str, session_id: str) -> Dict[str, Any]:
        """Invoke whichever gated subsystems apply. Returns an observable record.

        Every entry carries ran, why, and -- when it ran -- the output. A
        subsystem that ran and whose output is discarded is unwired with extra
        steps, so the output is always included.
        """
        out: Dict[str, Any] = {}

        # 1. Defeater graph: does this contradict something?
        should, why = self.gate_defeater(text)
        self._mark("defeater_graph", should)
        defeater_result = None
        if should:
            defeater_result = self._run_defeater(text)
        out["defeater_graph"] = {"ran": should, "why": why,
                                 "result": defeater_result}

        # 2. AGM: only after a contradiction, and only with something to choose.
        should, why = self.gate_agm(defeater_result)
        self._mark("agm", should)
        agm_result = None
        if should:
            agm_result = self._run_agm(defeater_result, text)
        out["agm"] = {"ran": should, "why": why, "result": agm_result}

        # 3. Dialectic: when positions cannot be ranked away.
        should, why = self.gate_dialectic(defeater_result)
        self._mark("dialectic", should)
        dialectic_result = None
        if should:
            dialectic_result = self._run_dialectic(defeater_result)
        out["dialectic"] = {"ran": should, "why": why, "result": dialectic_result}

        # 4. Chronesthesia.
        should, why = self.gate_chronesthesia(text)
        self._mark("chronesthesia", should)
        chrona_result = None
        if should:
            chrona_result = self._run_chronesthesia(text)
        out["chronesthesia"] = {"ran": should, "why": why, "result": chrona_result}

        # 5. Counterfactual.
        should, why = self.gate_counterfactual(text, mode)
        self._mark("counterfactual", should)
        cf_result = None
        if should:
            cf_result = self._run_counterfactual(text)
        out["counterfactual"] = {"ran": should, "why": why, "result": cf_result}

        # 6. Associative graph.
        should, why = self.gate_associative_graph(mode, text)
        self._mark("associative_graph", should)
        assoc_result = None
        if should:
            assoc_result = self._run_associative(text)
        out["associative_graph"] = {"ran": should, "why": why, "result": assoc_result}

        out["_counts"] = {"fired": dict(self.fired), "skipped": dict(self.skipped)}
        return out

    # -- invocations --------------------------------------------------------
    # Each is defensive. A subsystem that throws must not take down the
    # cognitive pass that was merely consulting it -- the seven steps that
    # already work are more valuable than the one that just failed. The failure
    # is recorded rather than swallowed.

    def _run_defeater(self, text: str) -> Dict[str, Any]:
        try:
            contested = []
            terms = set(_tokens(text.lower()))
            for belief in self.brain.defeater_graph.get_grounded_beliefs() or []:
                bt = set(_tokens(str(belief.get("statement", ""))))
                if terms & bt:
                    contested.append(belief)
            contradiction = bool(contested) and any(
                m in text.lower() for m in NEGATION_MARKERS)
            return {
                "contradiction": contradiction,
                "contested": contested,
                "checked": len(self.brain.defeater_graph.get_grounded_beliefs() or []),
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _run_agm(self, defeater_result: Optional[Dict[str, Any]], text: str) -> Dict[str, Any]:
        try:
            contested = (defeater_result or {}).get("contested") or []
            ranked = sorted(
                contested,
                key=lambda b: float(b.get("credence", 0.0)),
                reverse=True,
            )
            keeper = ranked[0]
            revised = self.brain.agm.revise(
                key=f"stm:{keeper.get('topic', 'unknown')}",
                proposition=text.strip()[:280],
                conflicts_with=[b.get("statement", "") for b in ranked[1:]],
                entrenchment=float(keeper.get("credence", 0.5)),
            )
            return {
                "retained": keeper.get("statement"),
                "surrendered": [b.get("statement") for b in ranked[1:]],
                "revision": revised,
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _run_dialectic(self, defeater_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            active = [b for b in ((defeater_result or {}).get("contested") or [])
                      if b.get("epistemic_state") != "superseded"]
            if len(active) < 2:
                return {"error": "fewer than two active positions"}
            return self.brain.dialectic.synthesize(
                thesis=str(active[0].get("statement", "")),
                antithesis=str(active[1].get("statement", "")),
                context=[str(b.get("statement", "")) for b in active[2:]],
            )
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _run_chronesthesia(self, text: str) -> Dict[str, Any]:
        try:
            return self.brain.chronesthesia.retrospection(text[:200])
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _run_counterfactual(self, text: str) -> Dict[str, Any]:
        try:
            # The real signature is analyze_regret(trigger_event, actual_path,
            # counterfactual_path, predicted_advantage, lesson_extracted). It
            # records what the CALLER already decided; it does not compute the
            # counterfactual. So this passes the text and the other four
            # arguments as empty strings rather than inventing values, because
            # a fabricated advantage here would be indistinguishable from a
            # derived one once it is in the table.
            return self.brain.counterfactual.analyze_regret(
                trigger_event=text[:200],
                actual_path="",
                counterfactual_path="",
                predicted_advantage="",
                lesson_extracted="",
            )
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _run_associative(self, text: str) -> Dict[str, Any]:
        try:
            seeds = _tokens(text)[:5]
            if not seeds:
                return {"seeds": [], "neighbours": []}
            found = self.brain.associative_graph.retrieve_relevant(seeds, top_k=5)
            return {"seeds": seeds,
                    "neighbours": [[str(a), float(b)] for a, b in (found or [])]}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
