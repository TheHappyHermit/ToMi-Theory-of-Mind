#!/usr/bin/env python3
"""
brain.cortex.executive — Miyake Triad Executive Functions.

Implements the three core executive cognitive functions (Miyake et al., 2000):
1. Inhibition: Suppression of prepotent / impulsive responses (e.g. unverified actions, destructive commands).
2. Updating: Continuous monitoring and revision of working memory representations.
3. Shifting: Cognitive set shifting, switching sub-tasks, and breaking loop traps.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class ExecutiveControl:
    """
    Executive Function Controller for Metacognition.
    """

    def __init__(self, loop_threshold: int = 3):
        self.loop_threshold = loop_threshold
        self.action_history: List[str] = []
        self.failed_strategies: List[str] = []

    def check_inhibition(self, proposed_action: str, context: Optional[str] = None) -> Tuple[bool, str]:
        """
        Inhibition: Evaluates whether a proposed action should be inhibited.
        Returns: (should_inhibit: bool, reason: str)
        """
        # 1. Check for destructive/irreversible shell commands
        destructive_patterns = [
            (r"\brm\s+(-rf?|-fr?)\s+[/~]", "Root or home directory recursive deletion detected."),
            (r"\bdrop\s+database\b", "Unprotected DROP DATABASE command proposed."),
            (r"\bgit\s+reset\s+--hard\b", "Destructive git hard reset without branch checkpoint."),
            (r"\bformat\s+[c-z]:", "Drive format command detected."),
            (r"\bdd\s+if=.*of=/dev/", "Raw disk block overwrite detected."),
        ]
        for pattern, explanation in destructive_patterns:
            if re.search(pattern, proposed_action, re.IGNORECASE):
                return True, f"INHIBITION TRIGGERED: {explanation}"

        # 2. Check for premature declaration of task completion without verification
        premature_completion = [
            r"\b(all done|finished everything|everything is fixed)\b",
        ]
        if context and "test" not in context.lower() and "verify" not in context.lower():
            for pat in premature_completion:
                if re.search(pat, proposed_action, re.IGNORECASE) and len(proposed_action.split()) < 20:
                    return True, "INHIBITION TRIGGERED: Premature completion claim without verification."

        return False, "Clear to proceed."

    def monitor_updating(self, new_fact: str, existing_facts: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Updating: Determines if new incoming information supersedes or contradicts existing facts.
        Returns: (needs_update: bool, superseded_fact: Optional[str])
        """
        new_fact_lower = new_fact.lower()
        for existing in existing_facts:
            existing_lower = existing.lower()
            # Direct contradiction heuristics (e.g., status changed from error to success, or version upgrade)
            if "status:" in new_fact_lower and "status:" in existing_lower:
                if new_fact_lower != existing_lower:
                    return True, existing
            if "version:" in new_fact_lower and "version:" in existing_lower:
                return True, existing
        return False, None

    def evaluate_shifting(self, current_action: str) -> Tuple[bool, str]:
        """
        Shifting: Detects if the agent is stuck in an unproductive loop and must shift cognitive sets.
        Returns: (must_shift: bool, recommendation: str)
        """
        self.action_history.append(current_action)
        if len(self.action_history) > 20:
            self.action_history.pop(0)

        # Count identical recent actions
        recent = self.action_history[-self.loop_threshold:]
        if len(recent) >= self.loop_threshold and all(a == recent[0] for a in recent):
            self.failed_strategies.append(recent[0])
            return True, f"SHIFT REQUIRED: Repeated action '{recent[0]}' {self.loop_threshold} times. Switch to an alternative strategy or seek user clarification."

        return False, "Cognitive set remains viable."

    def reset_history(self):
        self.action_history.clear()
        self.failed_strategies.clear()
