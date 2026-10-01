"""
Thalamus Subsystem — Sensory Gating & Attentional Filtering.
Prevents cognitive context flooding by scoring bottom-up saliency and applying top-down attenuation.

ThalamicGate is defined in attention.py, not gate.py. The old gate scored
character entropy, which measures how varied a string's letters are and has
nothing to do with importance: "aaaaaaaaaaaa" scored near zero however important
it was, and a base64 blob scored high while saying nothing. The three separable
switch-cost components, and the reason the gate is split into a bottom-up and a
top-down half, are documented in attention.py.
"""

from .attention import AttentionalGate, SwitchCost, ThalamicGate
from .buffer import SensoryBuffer

__all__ = ["AttentionalGate", "SwitchCost", "ThalamicGate", "SensoryBuffer"]
