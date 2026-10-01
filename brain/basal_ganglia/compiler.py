#!/usr/bin/env python3
"""
brain.basal_ganglia.compiler — Procedural Skill Compiler.

Implements cognitive proceduralization (Anderson's ACT-R theory of skill acquisition):
Converts declarative, multi-step episodic problem solving into fast, compiled,
procedural skills (macros/scripts/tools) that execute with minimal cognitive overhead.
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional


class ProceduralRoutine:
    def __init__(self, skill_name: str, sequence: List[str], description: str = ""):
        self.skill_name = skill_name
        self.sequence = sequence
        self.description = description
        self.execution_count = 0
        self.success_count = 0

    def record_run(self, success: bool):
        self.execution_count += 1
        if success:
            self.success_count += 1

    @property
    def success_rate(self) -> float:
        return self.success_count / self.execution_count if self.execution_count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "sequence": self.sequence,
            "description": self.description,
            "execution_count": self.execution_count,
            "success_rate": round(self.success_rate, 3),
        }


class ProceduralSkillCompiler:
    """
    Monitors episodic trace sequences and compiles frequently recurring, successful sequences
    into procedural macros.
    """

    def __init__(self, compilation_threshold: int = 3):
        self.compilation_threshold = compilation_threshold
        self.sequence_frequencies: Dict[str, int] = defaultdict(int)
        self.compiled_skills: Dict[str, ProceduralRoutine] = {}

    def _hash_sequence(self, steps: List[str]) -> str:
        return " -> ".join(s.strip() for s in steps)

    def observe_sequence(self, steps: List[str], success: bool, suggested_name: Optional[str] = None):
        """
        Record observation of an executed multi-step sequence.
        If observed frequently enough and successful, compiles it into a skill.
        """
        if not success or len(steps) < 2:
            return

        seq_key = self._hash_sequence(steps)
        self.sequence_frequencies[seq_key] += 1

        if self.sequence_frequencies[seq_key] >= self.compilation_threshold and seq_key not in [s._hash_sequence(s.sequence) for s in self.compiled_skills.values()]:
            name = suggested_name or f"skill_{len(self.compiled_skills) + 1}_{steps[0].split()[0]}"
            routine = ProceduralRoutine(skill_name=name, sequence=steps, description=f"Compiled routine for {steps[0]}")
            routine.record_run(True)
            self.compiled_skills[name] = routine

    def get_skill(self, name: str) -> Optional[ProceduralRoutine]:
        return self.compiled_skills.get(name)

    def list_compiled_skills(self) -> List[Dict[str, Any]]:
        return [skill.to_dict() for skill in self.compiled_skills.values()]
