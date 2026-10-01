#!/usr/bin/env python3
"""
brain.thalamus.gate — Thalamic Saliency Gating & Attentional Filtering.
"""

import math
import re
from typing import Dict, Any, Tuple, Optional


class ThalamicGate:
    """
    Evaluates incoming sensory data, computes bottom-up surprise,
    and gates entry into the primary LLM working context.
    """

    def __init__(self, saliency_threshold: float = 0.35):
        self.saliency_threshold = saliency_threshold

    def compute_entropy(self, text: str) -> float:
        """Calculate normalized Shannon entropy of character distribution."""
        if not text:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        entropy = -sum([p * math.log2(p) for p in prob if p > 0])
        # Normalize roughly between 0 and 1
        return min(entropy / 8.0, 1.0)

    def compute_saliency(self, text: str, active_context: Optional[str] = None) -> float:
        """
        Estimate informational saliency based on:
        1. Shannon entropy (novelty/complexity).
        2. Keyword urgency/risk indicators.
        3. Contextual relevance overlap.
        """
        if not text:
            return 0.0

        entropy = self.compute_entropy(text)

        # Urgency / risk weighting
        urgent_pattern = re.compile(r'\b(error|critical|fatal|exception|emergency|alert|fail|security|breach|deadlock)\b', re.IGNORECASE)
        urgency_boost = 0.3 if urgent_pattern.search(text) else 0.0

        # Redundancy penalty (repetitive log lines or empty chatter)
        redundancy_penalty = 0.0
        if len(text.strip()) < 10 or text.strip() in ("ok", "done", "status: ok", "heartbeat"):
            redundancy_penalty = 0.4

        # Overlap with current attention
        overlap_score = 0.0
        if active_context:
            context_words = set(re.findall(r'\w+', active_context.lower()))
            text_words = set(re.findall(r'\w+', text.lower()))
            if context_words and text_words:
                overlap = len(context_words.intersection(text_words)) / min(len(context_words), len(text_words))
                overlap_score = overlap * 0.3

        saliency = (entropy * 0.4) + urgency_boost + overlap_score - redundancy_penalty
        return max(0.0, min(1.0, saliency))

    def evaluate_admission(self, text: str, active_context: Optional[str] = None) -> Tuple[bool, float, str]:
        """
        Determine if input should be admitted into working context.
        Returns: (admitted: bool, score: float, disposition: str)
        """
        score = self.compute_saliency(text, active_context)
        if score >= self.saliency_threshold:
            return True, score, "admit"
        elif score >= (self.saliency_threshold * 0.5):
            return False, score, "compress"
        else:
            return False, score, "attenuate"
