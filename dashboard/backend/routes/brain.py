#!/usr/bin/env python3
"""
dashboard.backend.routes.brain — REST API Endpoints for HermesBrain Cognitive Engine.

Exposes endpoints for:
- Cognitive status inspection (Thalamus, Cortex, Limbic, Basal Ganglia, Hippocampus, Epistemology)
- Saliency gating & stimulus processing
- Basal Ganglia action checking & Miyake executive control
- Post-action reinforcement & hippocampal replay consolidation
- Epistemic belief revision & defeater lattices
- Causal counterfactual regret rollouts
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dashboard.backend.config import brain_engine

router = APIRouter(prefix="/api/brain", tags=["brain"])


# ---------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------

class StimulusRequest(BaseModel):
    text: str = Field(..., description="Perceptual or conversational input to evaluate")
    source: str = Field(default="user", description="Source of the stimulus (user, tool, system, cron)")
    session_id: str = Field(default="default_session", description="Conversation session ID")


class ActionCheckRequest(BaseModel):
    action: str = Field(..., description="Proposed tool or execution command")
    target: str = Field(default="", description="Target parameter or resource")
    expected_utility: float = Field(default=0.8, ge=0.0, le=1.0, description="Estimated utility")
    conflict_level: float = Field(default=0.0, ge=0.0, le=1.0, description="Detected goal conflict")
    emergency_alert: bool = Field(default=False, description="Emergency brake trigger")


class ActionOutcomeRequest(BaseModel):
    action: str = Field(..., description="Executed tool or command")
    target: str = Field(default="", description="Target parameter or resource")
    success: bool = Field(..., description="Whether execution succeeded")
    surprise_score: float = Field(default=0.2, ge=0.0, le=1.0, description="Surprise/novelty score")
    steps: Optional[List[str]] = Field(default=None, description="Sequence of actions taken for skill compiler")


class BeliefRequest(BaseModel):
    topic: str = Field(..., description="Knowledge topic or category")
    statement: str = Field(..., description="Propositional belief statement")
    credence: float = Field(default=1.0, ge=0.0, le=1.0, description="Epistemic credence [0.0 - 1.0]")
    provenance: str = Field(default="user", description="Source (user, tool, inference, wiki)")
    source_location: str = Field(
        ...,
        min_length=1,
        description="Where this belief came from: file path, page slug, or "
                    "message id. Required -- a belief with no address cannot be "
                    "re-read later to check it.",
    )


class DefeaterRequest(BaseModel):
    target_belief_id: int = Field(..., description="ID of belief being challenged")
    defeater_belief_id: int = Field(..., description="ID of defeating belief")
    defeater_type: str = Field(..., description="'rebutting' or 'undercutting'")
    justification: str = Field(..., description="Rationale for defeater")


class ConsolidateRequest(BaseModel):
    max_episodes: int = Field(default=5, ge=1, le=50, description="Number of episodes to consolidate in SWR replay")


class CounterfactualRequest(BaseModel):
    trigger_event: str = Field(..., description="The error or suboptimal event")
    actual_path: str = Field(..., description="What was actually done")
    counterfactual_path: str = Field(..., description="What could have been done instead")
    predicted_advantage: str = Field(..., description="Expected improvement of counterfactual")
    lesson_extracted: str = Field(..., description="Actionable rule learned")


class GoalRequest(BaseModel):
    goal: str = Field(..., description="New active goal for working memory")
    sub_goals: Optional[List[str]] = Field(default=None, description="Decomposed sub-goals")
    hypotheses: Optional[List[str]] = Field(default=None, description="Working hypotheses")


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.get("/status")
def get_brain_status() -> Dict[str, Any]:
    """Retrieve aggregate telemetry across all cognitive subsystems."""
    if not brain_engine:
        return {
            "status": "unavailable",
            "initialized": False,
            "message": "HermesBrain cognitive engine is not initialized",
        }

    try:
        beliefs = brain_engine.defeater_graph.get_grounded_beliefs() if brain_engine.defeater_graph else []
    except Exception:
        beliefs = []

    try:
        tom_discrepancies = brain_engine.tom.check_discrepancies() if brain_engine.tom else []
    except Exception:
        tom_discrepancies = []

    return {
        "status": "active",
        "initialized": True,
        "thalamus": {
            "buffer_size": len(brain_engine.thalamic_buffer.buffer),
            "buffer_maxlen": brain_engine.thalamic_buffer.buffer.maxlen,
            "saliency_threshold": brain_engine.thalamic_gate.saliency_threshold,
        },
        "cortex": {
            "active_goal": brain_engine.dl_pfc.active_goal,
            "sub_goals": brain_engine.dl_pfc.sub_goals,
            "hypotheses": brain_engine.dl_pfc.hypotheses,
            "slots_count": len(brain_engine.dl_pfc.slots),
            "slots": [slot.to_dict() for slot in brain_engine.dl_pfc.slots.values()],
            "system2_threshold": brain_engine.router.system2_threshold,
            "loop_threshold": brain_engine.executive.loop_threshold,
        },
        "limbic": {
            "affective_state": brain_engine.valence_engine.get_state(),
        },
        "basal_ganglia": {
            "go_threshold": brain_engine.action_gate.go_threshold,
            "compiled_skills_count": len(brain_engine.skill_compiler.compiled_skills),
        },
        "hippocampus": {
            "associative_nodes": len(brain_engine.associative_graph.nodes),
            "associative_edges": sum(len(v) for v in brain_engine.associative_graph.adjacency.values()),
            "episodic_buffer_count": len(brain_engine.replay_engine.episodic_traces),
        },
        "epistemology": {
            "grounded_beliefs_count": len(beliefs),
        },
        "social": {
            "discrepancies_count": len(tom_discrepancies),
            "discrepancies": tom_discrepancies,
        },
    }


@router.post("/stimulus")
def process_stimulus(req: StimulusRequest) -> Dict[str, Any]:
    """
    Run full cognitive pass over input text:
    saliency gating, pragmatics, somatic risk, dual-process routing, and working memory.
    """
    if not brain_engine:
        raise HTTPException(status_code=503, detail="HermesBrain engine is not available")

    result = brain_engine.process_incoming_stimulus(
        source=req.source,
        text=req.text,
        session_id=req.session_id,
    )
    return {
        "status": "success",
        "analysis": result,
    }


@router.post("/action-check")
def check_action(req: ActionCheckRequest) -> Dict[str, Any]:
    """
    Evaluate candidate action through Basal Ganglia Go/No-Go pathways and Somatic Markers.
    """
    if not brain_engine:
        raise HTTPException(status_code=503, detail="HermesBrain engine is not available")

    somatic_bias, somatic_warning = brain_engine.somatic_engine.assess(req.action, req.target)
    decision, net_drive, rationale = brain_engine.action_gate.evaluate_pathways(
        candidate_action=req.action,
        expected_utility=req.expected_utility,
        somatic_bias=somatic_bias,
        conflict_level=req.conflict_level,
        emergency_alert=req.emergency_alert,
    )

    return {
        "action": req.action,
        "target": req.target,
        "decision": decision,
        "net_drive": net_drive,
        "rationale": rationale,
        "somatic_bias": somatic_bias,
        "somatic_warning": somatic_warning,
    }


@router.post("/action-outcome")
def record_outcome(req: ActionOutcomeRequest) -> Dict[str, Any]:
    """
    Record post-execution feedback to update limbic valence, somatic markers, and replay buffer.
    """
    if not brain_engine:
        raise HTTPException(status_code=503, detail="HermesBrain engine is not available")

    brain_engine.record_action_outcome(
        action=req.action,
        target=req.target,
        success=req.success,
        surprise_score=req.surprise_score,
        steps=req.steps,
    )

    return {
        "status": "recorded",
        "action": req.action,
        "target": req.target,
        "success": req.success,
        "affective_state": brain_engine.valence_engine.get_state(),
    }


@router.get("/beliefs")
def get_beliefs(topic: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve grounded epistemic beliefs."""
    if not brain_engine or not brain_engine.defeater_graph:
        raise HTTPException(status_code=503, detail="Defeater graph is not available")

    beliefs = brain_engine.defeater_graph.get_grounded_beliefs(topic=topic)
    return {
        "count": len(beliefs),
        "topic": topic,
        "beliefs": beliefs,
    }


@router.post("/beliefs")
def add_belief(req: BeliefRequest) -> Dict[str, Any]:
    """Add a new defeasible belief."""
    if not brain_engine or not brain_engine.defeater_graph:
        raise HTTPException(status_code=503, detail="Defeater graph is not available")

    belief_id = brain_engine.defeater_graph.add_belief(
        topic=req.topic,
        statement=req.statement,
        credence=req.credence,
        provenance=req.provenance,
        source_location=req.source_location,
    )
    return {
        "status": "created",
        "belief_id": belief_id,
        "topic": req.topic,
        "statement": req.statement,
    }


@router.post("/beliefs/defeater")
def add_defeater(req: DefeaterRequest) -> Dict[str, Any]:
    """Record a rebutting or undercutting defeater."""
    if not brain_engine or not brain_engine.defeater_graph:
        raise HTTPException(status_code=503, detail="Defeater graph is not available")

    try:
        brain_engine.defeater_graph.add_defeater(
            target_belief_id=req.target_belief_id,
            defeater_belief_id=req.defeater_belief_id,
            defeater_type=req.defeater_type,
            justification=req.justification,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "defeater_recorded",
        "target_belief_id": req.target_belief_id,
        "defeater_type": req.defeater_type,
    }


@router.post("/consolidate")
def consolidate_memory(req: ConsolidateRequest) -> Dict[str, Any]:
    """Trigger Sharp Wave Ripple (SWR) hippocampal replay consolidation."""
    if not brain_engine:
        raise HTTPException(status_code=503, detail="HermesBrain engine is not available")

    replayed = brain_engine.replay_engine.run_consolidation_replay(max_episodes=req.max_episodes)
    return {
        "status": "consolidated",
        "episodes_replayed": len(replayed),
        "replayed": replayed,
        "compiled_skills_count": len(brain_engine.skill_compiler.compiled_skills),
    }


@router.post("/counterfactual")
def analyze_counterfactual(req: CounterfactualRequest) -> Dict[str, Any]:
    """Record and evaluate a counterfactual regret rollout."""
    if not brain_engine or not brain_engine.counterfactual:
        raise HTTPException(status_code=503, detail="Counterfactual engine is not available")

    record = brain_engine.counterfactual.analyze_regret(
        trigger_event=req.trigger_event,
        actual_path=req.actual_path,
        counterfactual_path=req.counterfactual_path,
        predicted_advantage=req.predicted_advantage,
        lesson_extracted=req.lesson_extracted,
    )
    return {
        "status": "analyzed",
        "record": record,
    }


@router.get("/counterfactual/lessons")
def get_lessons(query: str = "", limit: int = 5) -> Dict[str, Any]:
    """Retrieve historical counterfactual lessons."""
    if not brain_engine or not brain_engine.counterfactual:
        raise HTTPException(status_code=503, detail="Counterfactual engine is not available")

    lessons = brain_engine.counterfactual.get_past_lessons(query=query, limit=limit)
    return {
        "count": len(lessons),
        "lessons": lessons,
    }


@router.post("/working-memory/goal")
def set_working_memory_goal(req: GoalRequest) -> Dict[str, Any]:
    """Set the active goal in Dorsolateral Prefrontal Cortex (dlPFC)."""
    if not brain_engine:
        raise HTTPException(status_code=503, detail="HermesBrain engine is not available")

    brain_engine.dl_pfc.set_active_goal(req.goal, req.sub_goals)
    if req.hypotheses:
        brain_engine.dl_pfc.hypotheses = req.hypotheses

    return {
        "status": "goal_set",
        "active_goal": brain_engine.dl_pfc.active_goal,
        "sub_goals": brain_engine.dl_pfc.sub_goals,
        "hypotheses": brain_engine.dl_pfc.hypotheses,
        "summary": brain_engine.dl_pfc.render_context_summary(),
    }
