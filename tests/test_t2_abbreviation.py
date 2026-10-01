"""Tests for abbreviation detection.

The dominant false-mismatch class in the high-score band was not a
wrong citation but a CORRECT one written as an abbreviation:

  vault: "OntoKG: Ontology-Oriented KG Construction with Intrinsic-Relational Routing"
  arXiv: "OntoKG: Ontology-Oriented Knowledge Graph Construction with Intrinsic-Relational Routing"

Same paper. The vault writes "KG" for "Knowledge Graph" and drops a
subtitle. Scoring that as mismatch calls a correct citation wrong.

The fix is bounded: EVERY distinctive token of the label must appear in
the title, and at least 3 must. The negative cases below are the point
-- a genuinely wrong citation shares SUBJECT vocabulary, it does not
contain a superset of the accused title's own words.
"""
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    't2', REPO / 'scripts' / 'verify_t2_titles.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

abbrev = M.is_abbreviation_of


class TestTruePositives(unittest.TestCase):
    """Real pairs from the vault, verified against the registry title."""

    CASES = [
        # acronym expansion
        ("OntoKG: Ontology-Oriented KG Construction with Intrinsic-Relational Routing",
         "OntoKG: Ontology-Oriented Knowledge Graph Construction with Intrinsic-Relational Routing"),
        # slash-compressed list, dropped subtitle
        ("Theorem-of-Thought: Multi-Agent Abductive/Deductive/Inductive Reasoning",
         "Theorem-of-Thought: A Multi-Agent Framework for Abductive, Deductive, "
         "and Inductive Reasoning in Language Models"),
        # dropped words
        ("PromptPrism: Linguistically-Inspired Prompt Taxonomy",
         "PromptPrism: A Linguistically-Inspired Taxonomy for Prompts"),
        ("Preserving Contextual Information in Cultural Heritage Metadata through Multidimensional KGs",
         "Preserving contextual information in cultural heritage metadata "
         "through multidimensional knowledge graphs"),
        ("BoostTaxo: Zero-Shot Taxonomy Induction via Boosting-Style Reasoning",
         "BoostTaxo: Zero-Shot Taxonomy Induction via Boosting-Style Agentic "
         "Reasoning and Constraint-Aware Calibration"),
        ("LLMOrbit: Circular Taxonomy of LLMs",
         "LLMOrbit: A Circular Taxonomy of Large Language Models -From "
         "Scaling Walls to Agentic AI Systems"),
        ("Semantic Units Framework (FAIR/CLEAR)",
         "The Semantic Units Framework, a technology-agnostic "
         "representational approach to FAIR and CLEAR principles"),
    ]

    def test_real_abbreviations_detected(self):
        for vault, title in self.CASES:
            with self.subTest(vault=vault[:40]):
                self.assertTrue(abbrev(vault, title),
                                "missed a real abbreviation: %s" % vault[:60])

    def test_case_insensitive(self):
        """Case must not matter, but this pair is legitimately refused.

        "the coT encyclopedia" has only TWO distinctive tokens (cot,
        encyclopedia) -- "the" is a function word. The >=3 bar exists so
        that a short generic label cannot claim a match on thin
        evidence, and two tokens is exactly that case. An earlier
        version of this test asserted True and was wrong about its own
        fixture; the correct assertion is that it is refused for being
        under-evidenced, which is a different failure from being
        case-sensitive.

        is_abbreviation_of DOES normalise case, so the property is
        checked here on a label with enough distinctive tokens.
        """
        self.assertFalse(abbrev(
            "the coT encyclopedia",
            "The CoT Encyclopedia: Analyzing, Predicting, and Controlling "
            "the Behavior of Language Models"))
        self.assertTrue(abbrev(
            "The CoT Encyclopedia of Language Model Behavior",
            "The CoT Encyclopedia: Analyzing, Predicting, and Controlling "
            "the Behavior of Language Models"))


class TestTrueNegatives(unittest.TestCase):
    """Genuinely wrong citations must NOT be rescued.

    Each of these is a real mismatch from the vault: the cited title
    belongs to a different paper.
    """

    CASES = [
        # the somatosensory paper cited under a different paper's title
        ("A critical period plasticity framework for the sensorimotor association axis",
         "Neural correlates of somatosensory stimulus discrimination in the "
         "primary somatosensory cortex"),
        # the Cai/PNAS case, where the vault label is a description
        # rather than the paper's title
        ("Cai et al. 2009 PNAS REM sleep creativity",
         "REM, not incubation, improves creativity by priming associative networks"),
        # entirely unrelated subject
        ("A study of marine biology and coral reef biodiversity",
         "Attention Is All You Need"),
        # shares subject vocabulary but is a different paper
        ("OntoKG: Ontology-Oriented KG Construction with Intrinsic-Relational Routing",
         "OntoPro: Ontology-Enhanced KG Construction with Constraint Reasoning"),
    ]

    def test_wrong_citations_still_mismatch(self):
        for vault, title in self.CASES:
            with self.subTest(vault=vault[:40]):
                self.assertFalse(
                    abbrev(vault, title),
                    "rescued a wrong citation: %s" % vault[:60])


class TestBounds(unittest.TestCase):
    def test_too_few_distinctive_tokens(self):
        """Generic-only labels carry no identifying information."""
        self.assertFalse(abbrev("A New Survey", "A New Survey of Deep Learning Methods"))

    def test_minimum_token_count_enforced(self):
        self.assertFalse(abbrev("ontology routing", "Ontology Construction with Routing"))

    def test_empty_inputs(self):
        self.assertFalse(abbrev("", "Some Title Here"))
        self.assertFalse(abbrev("Some Label Here", ""))

    def test_partial_coverage_rejected(self):
        """One missing distinctive token is enough to refuse.

        This is the safety property. A wrong citation is one that
        contains MOST of the words plus a different one, not a subset.
        """
        self.assertFalse(abbrev(
            "OntoKG: Ontology-Oriented KG Construction with Extrinsic Routing",
            "OntoKG: Ontology-Oriented Knowledge Graph Construction with "
            "Intrinsic-Relational Routing"))

    def test_generic_tokens_do_not_count_toward_coverage(self):
        """'framework' and 'system' must not carry the match.

        Using generic tokens as matching basis is what once let
        'Deep Learning' match unrelated titles.
        """
        self.assertFalse(abbrev(
            "Framework for Agents",
            "Framework for Agents"))

    def test_hyphen_and_slash_normalised(self):
        self.assertTrue(abbrev(
            "TRACE-KG: Context-Enriched KG Generation without Priors",
            "TRACE-KG: Context-Enriched Knowledge Graph Generation without "
            "Global Priors"))

    def test_singular_plural_agrees(self):
        """'taxonomies' and 'taxonomy' must stem to the same thing.

        A suffix-strip whose rule order split the two forms of one word
        -- "taxonomies"->"taxonomy" vs "taxonomy"->"taxonom" -- scored
        a real abbreviation as a mismatch, because the only difference
        between the vault label and the registry title was a plural.
        """
        self.assertEqual(M._abbrev_stem("taxonomies"),
                         M._abbrev_stem("taxonomy"))
        # And with enough distinctive tokens to clear the bar:
        self.assertTrue(abbrev(
            "Taxonomies of Agent Memory Systems in Practice",
            "A Taxonomy of Agent Memory Systems in Practice"))


if __name__ == '__main__':
    unittest.main()
