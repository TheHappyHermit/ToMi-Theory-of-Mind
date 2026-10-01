#!/usr/bin/env python3
"""
brain.social.pragmatics — Gricean Conversational Pragmatics & Implicature.

Implements Paul Grice's Cooperative Principle & Conversational Maxims:
1. Maxim of Quantity: Provide as much information as required, but not more.
2. Maxim of Quality: Do not state what lacks adequate evidence.
3. Maxim of Relation: Be relevant to the ongoing dialogue and active goal.
4. Maxim of Manner: Be perspicuous, orderly, and avoid unnecessary prolixity.

Also identifies indirect speech acts and pragmatic conversational implicature.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


class GriceanPragmatics:
    """
    Evaluates communication against Gricean conversational maxims and decodes implicatures.
    """

    def analyze_implicature(self, utterance: str) -> Dict[str, Any]:
        """
        Detect indirect speech acts (e.g., questions or statements that function as requests for action).
        """
        utterance_clean = utterance.strip()
        is_indirect_request = False
        implied_action = ""

        # Pattern: "X is broken / failing / not working" -> Request to fix X
        broken_match = re.search(r"^(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+(?:is\s+)?(?:broken|failing|down|throwing errors|crashing)", utterance_clean, re.IGNORECASE)
        if broken_match:
            is_indirect_request = True
            component = broken_match.group(1).strip()
            implied_action = f"Investigate, diagnose, and fix {component}"

        # Pattern: "Can we / Could we / Can you do X" -> Directive to execute X
        can_we_match = re.search(r"^(?:can|could|would)\s+(?:we|you)\s+(?:please\s+)?(.+)", utterance_clean, re.IGNORECASE)
        if can_we_match:
            is_indirect_request = True
            implied_action = f"Execute action: {can_we_match.group(1)}"

        # Pattern: "I want / I need X" -> Request to deliver X
        want_match = re.search(r"^i\s+(?:want|need)\s+(?:you\s+to\s+)?(.+)", utterance_clean, re.IGNORECASE)
        if want_match:
            is_indirect_request = True
            implied_action = f"Fulfill user intent: {want_match.group(1)}"

        return {
            "raw_utterance": utterance,
            "is_indirect_request": is_indirect_request,
            "inferred_directive": implied_action if is_indirect_request else utterance,
        }

    def audit_response_maxims(self, draft_response: str, query: str, grounded_facts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Audit draft output against the four Gricean maxims.
        """
        word_count = len(draft_response.split())
        query_word_count = len(query.split())

        # Maxim of Quantity
        quantity_status = "optimal"
        if word_count > 600 and query_word_count < 10:
            quantity_status = "overly_verbose"
        elif word_count < 5 and query_word_count > 30:
            quantity_status = "insufficient"

        # Maxim of Quality
        quality_status = "grounded"
        speculative_phrases = ["maybe", "perhaps", "i guess", "i think maybe", "probably not sure"]
        if any(sp in draft_response.lower() for sp in speculative_phrases):
            quality_status = "speculative_hedging"

        # Maxim of Relation
        relation_status = "relevant"
        query_terms = set(re.findall(r"\w+", query.lower()))
        response_terms = set(re.findall(r"\w+", draft_response.lower()))
        if query_terms and not query_terms.intersection(response_terms):
            relation_status = "tangential_risk"

        # Maxim of Manner
        manner_status = "clear"
        if draft_response.count("\n\n") == 0 and word_count > 150:
            manner_status = "wall_of_text"

        return {
            "quantity": quantity_status,
            "quality": quality_status,
            "relation": relation_status,
            "manner": manner_status,
            "overall_cooperative": (quantity_status == "optimal" and relation_status == "relevant"),
        }
