#!/usr/bin/env python3
"""
brain.cortex.router — Dual-Process System 1 vs System 2 Cognitive Router.

Routes tasks dynamically based on:
- Complexity / token length / syntactical structure
- Uncertainty / epistemic dispute
- Risk / somatic marker valence
- User explicit intent / urgency
"""

import re
from typing import Dict, Any, Tuple


class CognitiveRouter:
    """
    Kahneman Dual-Process Router:
    System 1: Fast, reflexive, low-compute heuristic response.
    System 2: Slow, deliberative, tree-of-thought / tool-orchestrated reasoning.
    """

    def __init__(self, system2_threshold: float = 0.5):
        self.system2_threshold = system2_threshold

    def evaluate_route(
        self,
        prompt: str,
        active_goal: str = "",
        somatic_risk: float = 0.0,
        unresolved_hypotheses_count: int = 0,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Evaluate whether the incoming prompt warrants System 1 or System 2 compute.
        Returns:
            (mode: "SYSTEM_1" | "SYSTEM_2", score: float, diagnostics: dict)
        """
        score = 0.0
        factors = {}

        # 1. Linguistic complexity & length
        word_count = len(prompt.split())
        length_score = min(1.0, word_count / 150.0) * 0.2
        factors["length_complexity"] = round(length_score, 3)
        score += length_score

        # 2. Deliberation keywords (code, debug, architect, prove, analyze, refactor, why, compare)
        deliberation_patterns = [
            r"\b(refactor|architect|debug|investigate|analyze|optimize|evaluate|synthesize)\b",
            r"\b(why|how does|what if|compare|contrast|tradeoff|difference between)\b",
            r"\b(implement|build|create|execute|migrate|rearchitect|benchmark)\b",
            r"```",  # Code blocks strongly suggest System 2
        ]
        keyword_hits = 0
        for pat in deliberation_patterns:
            matches = re.findall(pat, prompt, re.IGNORECASE)
            keyword_hits += len(matches)
        keyword_score = min(0.7, keyword_hits * 0.25)
        factors["deliberation_keywords"] = round(keyword_score, 3)
        score += keyword_score

        # 3. Somatic Risk / Danger
        # High somatic risk (negative valence / high warning) demands System 2 deliberation
        risk_score = max(0.0, abs(somatic_risk)) * 0.3 if somatic_risk < -0.2 else 0.0
        factors["somatic_risk_boost"] = round(risk_score, 3)
        score += risk_score

        # 4. Epistemic uncertainty (active unresolved hypotheses)
        epistemic_score = min(0.2, unresolved_hypotheses_count * 0.1)
        factors["epistemic_uncertainty"] = round(epistemic_score, 3)
        score += epistemic_score

        # 5. Reflex / Fast System 1 overrides (short greetings, acknowledgments)
        reflex_patterns = [
            r"^(hi|hello|hey|yo|greetings|good\s+(morning|afternoon|evening))\b",
            r"^(ok|okay|thanks|thank you|cool|got it|sounds good|understood)\.?$",
            r"^(what time is it|who are you|what is your name)\??$",
        ]
        is_reflex = any(re.search(pat, prompt.strip(), re.IGNORECASE) for pat in reflex_patterns)
        if is_reflex and word_count < 10:
            score = 0.1
            factors["reflex_override"] = True

        mode = "SYSTEM_2" if score >= self.system2_threshold else "SYSTEM_1"
        return mode, round(score, 3), factors
