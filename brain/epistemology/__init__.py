"""
brain.epistemology — Defeasible Epistemology, Pollock Defeaters, AGM Revision & Dialectics.
"""

from brain.epistemology.defeater_graph import DefeaterGraph
from brain.epistemology.agm import AGMBeliefRevision, BeliefItem
from brain.epistemology.dialectic import DialecticSynthesizer

__all__ = ["DefeaterGraph", "AGMBeliefRevision", "BeliefItem", "DialecticSynthesizer"]
