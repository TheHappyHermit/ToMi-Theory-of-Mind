"""
Hermes Brain Adapters for External Companion Applications.
Provides clean, non-invasive bridges to upstream open-source tools
(e.g., Jared Rhodes' ai-visualizer and barehands) without modifying their code.
"""

from .visualizer import VisualizerAdapter
from .barehands import BarehandsAdapter

__all__ = ["VisualizerAdapter", "BarehandsAdapter"]
