#!/usr/bin/env python3
"""
brain.hippocampus.replay — Pattern Separation, Completion & Offline Consolidation.

Models:
- Pattern Separation (Dentate Gyrus): Disambiguates highly similar perceptual cues
  to prevent catastrophic interference.
- Pattern Completion (CA3): Reconstructs full episodic experiences from partial or degraded cues.
- Sharp-Wave Ripple (SWR) Offline Replay: Prioritized replay of experiences with high
  emotional valence or surprise for neocortical consolidation.

PATTERN SEPARATION IS GEOMETRIC
-------------------------------
`pattern_separation` used to be a SHA-256 hash of "text::context", which
is the wrong FUNCTION CLASS, not a weak implementation. Our own Oracle
vault says so directly:

    "A hash is a maximally non-geometric function used to solve a
     geometric problem."
    "You cannot compute distance between two hashes, so you cannot
     measure whether separation occurred."

Measured on three near-identical pairs differing by one word, the hash
returned distances of 64730, 48930 and 44108 — uncorrelated with how
similar the inputs actually were, and identical text still produced a
different code. The number carried no information about similarity, so
nothing downstream could use it and "separation" was unverifiable.

Separation now delegates to PatternSeparator, a deterministic sparse
random projection with real geometry: near-duplicates land near, and the
similarity is measurable so the result can be checked rather than
trusted. See brain/hippocampus/pattern_separation.py.

`separation_report()` is the new entry point for callers that want the
measured geometry. The legacy string return is kept for compatibility
and is explicitly documented as a LOSSY label, not a distance.
"""

from typing import Dict, Any, List, Optional, Tuple

from brain.hippocampus.pattern_separation import PatternSeparator


class HippocampalReplayEngine:
    """
    Hippocampal memory consolidation and pattern processing engine.
    """

    def __init__(self, separator: Optional[PatternSeparator] = None):
        self.episodic_traces: List[Dict[str, Any]] = []
        self.separator = separator or PatternSeparator()

    def separation_report(self, text_cue: str, context: Optional[str] = None,
                          margin: float = 0.15) -> Dict[str, Any]:
        """Separate this cue from the traces already recorded, and report it.

        This is the real entry point. It measures this cue against every
        episode already in the buffer and reports the nearest one, the
        similarity, and whether separation actually succeeded.

        The old method could not answer any of those questions, which is
        precisely why it was not doing pattern separation.
        """
        priors = [(t.get("summary", ""), t.get("details") or None)
                  for t in self.episodic_traces]
        return self.separator.separate(text_cue, context, priors, margin)

    def pattern_separation(self, text_cue: str, context: Optional[str] = None) -> str:
        """A short stable label for this cue.

        COMPATIBILITY SHIM. The return value is a LOSSY label, not a
        representation and emphatically not a distance. Do not compare
        two of these to measure similarity -- that is the bug this
        module was rewritten to fix, and doing it here would reintroduce
        it through the back door.

        Use `separation_report()` (or the separator's similarity()/
        distance()) for anything geometric.
        """
        return self.separator.code(self.separator.embed(text_cue, context))

    def pattern_completion(self, partial_cue: str, threshold: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a full episode from a partial fragment cue.
        """
        if not self.episodic_traces or not partial_cue:
            return None

        cue_tokens = set(partial_cue.lower().split())
        best_match = None
        best_overlap = 0.0

        for trace in self.episodic_traces:
            trace_text = (trace.get("summary", "") + " " + trace.get("details", "")).lower()
            trace_tokens = set(trace_text.split())
            if not trace_tokens:
                continue

            overlap = len(cue_tokens.intersection(trace_tokens)) / len(cue_tokens)
            if overlap > best_overlap and overlap >= threshold:
                best_overlap = overlap
                best_match = trace

        return best_match

    def record_episode(self, episode_id: str, summary: str, details: str, surprise_score: float, valence: float):
        """Record an episode in the episodic buffer with priority metadata."""
        self.episodic_traces.append({
            "id": episode_id,
            "summary": summary,
            "details": details,
            "surprise": surprise_score,
            "valence": valence,
            "priority": round(abs(valence) * 0.5 + surprise_score * 0.5, 3),
            "replayed": False,
        })

    def run_consolidation_replay(self, max_episodes: int = 5) -> List[Dict[str, Any]]:
        """
        Sharp-Wave Ripple (SWR) replay: Prioritize episodes with high surprise or valence,
        replaying them to generate consolidated insights.
        """
        unreplayed = [e for e in self.episodic_traces if not e["replayed"]]
        if not unreplayed:
            return []

        # Sort by priority (highest surprise / emotional impact first)
        unreplayed.sort(key=lambda x: x["priority"], reverse=True)
        selected = unreplayed[:max_episodes]

        consolidated_lessons = []
        for ep in selected:
            ep["replayed"] = True
            lesson = {
                "episode_id": ep["id"],
                "consolidated_insight": f"Consolidated rule from '{ep['summary']}' (surprise={ep['surprise']}, valence={ep['valence']})",
                "priority": ep["priority"],
            }
            consolidated_lessons.append(lesson)

        return consolidated_lessons
