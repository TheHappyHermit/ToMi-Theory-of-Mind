#!/usr/bin/env python3
"""
brain.hermes_brain — Unified Neuro-Cognitive Brain Architecture for Hermes.

Orchestrates the complete suite of cognitive subsystems:
- Thalamus: Saliency gating & sensory buffering.
- Cortex (dlPFC & Executive): Working memory scratchpad, dual-process System 1/2 routing, Miyake triad.
- Limbic: Cognitive valence, allostatic load & Damasio somatic markers.
- Basal Ganglia: Striatal Go/No-Go action arbitration & procedural skill compilation.
- Hippocampus: HippoRAG associative graph with Personalized PageRank & SWR replay consolidation.
- Default Mode Network (DMN): Chronesthesia (mental time travel) & causal counterfactual regret rollouts.
- Epistemology: Pollock defeasible defeater lattice, AGM belief revision & Hegelian dialectics.
- Social Cognition: Recursive Theory of Mind & Gricean conversational pragmatics.
"""

import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from brain.thalamus import SensoryBuffer, ThalamicGate
from brain.cortex import DorsolateralPFC, CognitiveRouter, ExecutiveControl
from brain.cortex.wiring import CognitiveWiring
from brain.limbic import CognitiveValenceEngine, SomaticMarkerEngine, Amygdala
from brain.basal_ganglia import ActionGate, ProceduralSkillCompiler
from brain.hippocampus import HippoAssociativeGraph, HippocampalReplayEngine
from brain.dmn import ChronesthesiaEngine, CounterfactualEngine
from brain.epistemology import DefeaterGraph, AGMBeliefRevision, DialecticSynthesizer
from brain.social import TheoryOfMind, GriceanPragmatics
from brain.prospective import ProspectiveMemory
from brain.decisions import PlasticGains


class HermesBrain:
    """
    Master Cognitive Architecture Controller.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain.db")

        # Create any missing table and add any column the schema file has gained
        # since this database was created. This has to happen first, before any
        # subsystem is handed a db_path, or a later write fails on a column that
        # should have been added here.
        self._init_database()

        # Initialize Cognitive Subsystems
        self.thalamic_buffer = SensoryBuffer(maxlen=200)
        self.thalamic_gate = ThalamicGate(saliency_threshold=0.35)

        self.dl_pfc = DorsolateralPFC(capacity=7, db_path=self.db_path)
        self.router = CognitiveRouter(system2_threshold=0.5)
        self.executive = ExecutiveControl(loop_threshold=3)

        self.valence_engine = CognitiveValenceEngine()
        self.somatic_engine = SomaticMarkerEngine(db_path=self.db_path)

        self.action_gate = ActionGate(go_threshold=0.4)
        self.skill_compiler = ProceduralSkillCompiler(compilation_threshold=3)

        # C4: the substrate the fixed constants above are replaced by. Held
        # here so there is ONE owner of every gain; a second copy is how two
        # subsystems end up disagreeing about the current threshold.
        #
        # The subsystems still receive the historical constants at
        # construction. What changes is that `retune()` can now move them, with
        # a recorded trigger, inside declared bounds. Constructing with the
        # default and adapting later is deliberately the same starting point
        # the fixed version had.
        self.gains = PlasticGains()

        self.associative_graph = HippoAssociativeGraph(damping_factor=0.85)
        # Standing intentions with trigger conditions (implementation intentions).
        self.prospective_memory = ProspectiveMemory(self.db_path)
        self.replay_engine = HippocampalReplayEngine()

        self.chronesthesia = ChronesthesiaEngine()
        self.counterfactual = CounterfactualEngine(db_path=self.db_path)

        self.defeater_graph = DefeaterGraph(db_path=self.db_path)
        self.agm = AGMBeliefRevision()
        self.dialectic = DialecticSynthesizer()

        self.tom = TheoryOfMind(db_path=self.db_path)
        self.pragmatics = GriceanPragmatics()

        # Amygdala: threat appraisal and affective tagging. Added when the
        # region was found absent entirely. It is a per-instance
        # conditioned object, so it is constructed per brain rather than
        # shared -- a learned fear association is state, and sharing one
        # across brains would leak conditioning between them.
        self.amygdala = Amygdala()

        # Gate for the six subsystems constructed above and previously never
        # called. Must come after all of them exist.
        self.wiring = CognitiveWiring(self)

    def retune(self, *, recent_error: float, allostatic_load: float,
               recent_oscillation: float = 0.0, headroom: float = 1.0,
               success_streak: int = 0, reason: str = "") -> Dict[str, Any]:
        """
        C4. Recompute the plastic gains from observed outcomes and push them
        into the live subsystems.

        This is the whole of C4 in one call: the constants that used to be
        literals in each subsystem become values derived from how the system is
        actually doing, bounded, rate-limited, and logged with the trigger that
        caused the move.

        `reason` is required and must be non-empty. A retune that cannot be
        explained later is indistinguishable from drift.
        """
        if not reason or not str(reason).strip():
            raise ValueError("retune() needs a reason; an unexplained retune is drift")

        proposals = {
            "go_threshold": self.gains.propose_go_threshold(recent_error, allostatic_load),
            "compilation_threshold": self.gains.propose_compilation_threshold(
                success_streak, headroom),
            "damping_factor": self.gains.propose_damping(recent_oscillation, headroom),
            "decay_rate": self.gains.propose_decay_rate(allostatic_load, headroom),
        }

        applied: Dict[str, Any] = {}
        for name, proposed in proposals.items():
            value, changed = self.gains.update(name, proposed, f"{reason} :: {name}")
            applied[name] = {"value": value, "changed": changed, "proposed": round(proposed, 4)}

        # Push into the live subsystems. These are the only places a gain is
        # allowed to take effect -- a gain that lives only in the registry has
        # changed nothing.
        self.action_gate.go_threshold = self.gains.get("go_threshold")
        self.skill_compiler.compilation_threshold = int(
            round(self.gains.get("compilation_threshold")))
        self.associative_graph.damping_factor = self.gains.get("damping_factor")

        return {
            "applied": applied,
            "reason": reason,
            "audit_trail": self.gains.history(),
        }

    # Columns added to existing tables after the schema file was first written.
    # CREATE TABLE IF NOT EXISTS does nothing when the table already exists, so
    # a column added to brain_cortex.sql is invisible to every database created
    # before that change. Without this list the code and the database disagree,
    # and the disagreement surfaces only as an OperationalError at the moment
    # something first uses the new column.
    #
    # ADDITIVE ONLY. Each entry is (table, column, definition). Nothing here may
    # drop or rewrite a column: a schema change that can lose data does not
    # belong in a constructor that runs on every start.
    #
    # 2026-09-27 -- Decisions C1, C10 and C12. Each is DEFAULT-valued rather
    # than NOT NULL because SQLite cannot add a NOT NULL column without a table
    # rebuild, and this constructor runs on every start. The requirement is
    # enforced at the writer, which is where it can actually hold; a CHECK that
    # always passes is worse than none because it reads like enforcement.
    #
    #   trust            C1. Provenance says WHERE a belief came from; trust says
    #                    how much the SOURCE's standing warrants. Kept separate
    #                    on purpose -- collapsing them means a quote from a
    #                    trusted author inherits the author's full credibility,
    #                    which is how a memory system ends up confident about
    #                    something nobody actually asserted.
    #   authority        C10. WHO asserted it, as distinct from where it was
    #                    written down. A retrieved_quote may never be promoted
    #                    to user_asserted by any path; see
    #                    SupersessionResolver.may_promote.
    #   scope            C10. Register and scope. "Always" and "usually" are the
    #                    same claim with different truth conditions, and one
    #                    column cannot hold both.
    #   provenance_span  C12. Bi-temporal: WHICH span of the source this belief
    #                    came from, so it can be re-read rather than trusted.
    #   valid_from/to    C12. Bi-temporal validity, RFC 3339 UTC. valid_to NULL
    #                    means currently binding, which is what the C7 resolver
    #                    selects on. A single created_at cannot distinguish "I
    #                    learned this Tuesday" from "this stopped being true on
    #                    Tuesday".
    _ADDITIVE_COLUMNS = (
        ("cognitive_beliefs", "source_location", "TEXT NOT NULL DEFAULT ''"),
        ("cognitive_beliefs", "trust", "REAL NOT NULL DEFAULT 0.5"),
        ("cognitive_beliefs", "authority", "TEXT NOT NULL DEFAULT 'retrieved_quote'"),
        ("cognitive_beliefs", "scope", "TEXT"),
        ("cognitive_beliefs", "provenance_span", "TEXT"),
        ("cognitive_beliefs", "valid_from", "TEXT"),
        ("cognitive_beliefs", "valid_to", "TEXT"),
        ("cognitive_beliefs", "supersedes_id", "INTEGER"),
    )

    def _init_database(self):
        """Create any missing table, then add any column gained since.

        Two steps, in order, both idempotent. The second exists because
        CREATE TABLE IF NOT EXISTS cannot add a column to a table that is
        already there -- which is exactly the case for every database that
        predates the column.
        """
        schema_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema", "brain_cortex.sql")
        if not (os.path.exists(schema_file) and self.db_path):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())

                # Additive column catch-up. ALTER TABLE ... ADD COLUMN errors if
                # the column is already present, so this check is not an
                # optimisation -- it is the difference between a clean start and
                # a crash on the first write.
                for table, column, definition in self._ADDITIVE_COLUMNS:
                    existing = {r[1] for r in conn.execute(
                        f"PRAGMA table_info({table})")}
                    if not existing or column in existing:
                        # No table means this is not a brain database and there
                        # is nothing to add; the column already being there is
                        # the common case.
                        continue
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            finally:
                conn.commit()
                conn.close()
        except Exception as e:
            # A schema that will not apply is worth saying out loud, because the
            # visible failure surfaces later as a column that does not exist.
            # A print is not enough for that; log it with the traceback.
            logging.getLogger(__name__).error(
                "brain schema init failed: %s: %s", type(e).__name__, e,
                exc_info=True)

    def process_incoming_stimulus(
        self,
        source: str,
        text: str,
        session_id: str = "default_session",
    ) -> Dict[str, Any]:
        """
        Full cognitive pass over an incoming stimulus/prompt:
        1. Thalamic buffer & saliency admission check.
        2. Pragmatic implicature & indirect speech act decoding.
        3. Somatic marker risk appraisal.
        4. Dual-process System 1 vs System 2 cognitive routing.
        5. Working memory (dlPFC) goal & context retrieval.
        6. Theory of Mind user calibration.
        7. Prospective memory: any standing intention whose trigger fired.
        8. Gated subsystems: defeater graph, AGM, dialectic, chronesthesia,
           counterfactual and associative graph, each behind its own signal.
        """
        # 1. Thalamus
        event = self.thalamic_buffer.append(source=source, payload=text)
        admitted, saliency_score, disposition = self.thalamic_gate.evaluate_admission(text)
        event.gated = admitted
        event.saliency_score = saliency_score

        # 2. Pragmatics
        implicature = self.pragmatics.analyze_implicature(text)
        effective_directive = implicature["inferred_directive"]

        # 3. Somatic Risk Assessment (extract rough action/target candidate)
        tokens = effective_directive.split()
        action_cand = tokens[0] if tokens else "think"
        target_cand = tokens[1] if len(tokens) > 1 else "general"
        somatic_bias, somatic_warning = self.somatic_engine.assess(action_cand, target_cand)

        # 4. Cognitive Router (System 1 vs 2)
        mode, route_score, factors = self.router.evaluate_route(
            prompt=effective_directive,
            active_goal=self.dl_pfc.active_goal or "",
            somatic_risk=somatic_bias,
        )

        # 5. Working Memory
        self.dl_pfc.decay_all(rate=0.1)

        # Interference, then the new input. Order matters: damping the slots
        # that are already competing BEFORE adding this one means the effect
        # reflects the state the newcomer actually interrupted, rather than
        # damping the newcomer against a set it never co-existed with.
        self.dl_pfc.apply_interference()
        self.dl_pfc.upsert_slot("latest_input", effective_directive, importance=0.8, category="context")

        # 6. Theory of Mind Check
        tom_discrepancies = self.tom.check_discrepancies()

        # 7b. Prospective memory: standing intentions whose trigger is present.
        # Deterministic and side-effect free -- surfacing is the caller's choice.
        fired_intentions = self.prospective_memory.check(text)
        if fired_intentions:
            self.prospective_memory.mark_fired([i.intention_id for i in fired_intentions])
            # Re-read so the surfaced payload reports the post-fire count. Returning
            # the pre-mark objects would claim fired_count=0 for an intention that
            # just fired, which is exactly the kind of quiet inaccuracy that makes a
            # status field useless.
            fired_intentions = [
                self.prospective_memory.get(i.intention_id) or i
                for i in fired_intentions
            ]

        # 7. Basal Ganglia Action Gate preview
        gate_action, net_drive, gate_rationale = self.action_gate.evaluate_pathways(
            candidate_action=action_cand,
            expected_utility=0.8 if mode == "SYSTEM_1" else 0.9,
            somatic_bias=somatic_bias,
            conflict_level=0.1 if not tom_discrepancies else 0.4,
        )

        # 8. Gated subsystems. Each of the six is invoked only when a real
        # signal is present, and each reports why it ran or did not. A subsystem
        # that runs and whose output is discarded is unwired with extra steps,
        # so the whole record is returned rather than a summary of it.
        gated = self.wiring.run(
            text=text, mode=mode, session_id=session_id)

        return {
            "gated_subsystems": gated,
            "saliency": {
                "admitted": admitted,
                "score": saliency_score,
                "disposition": disposition,
            },
            "pragmatics": implicature,
            "cognitive_route": {
                "mode": mode,
                "score": route_score,
                "factors": factors,
            },
            "somatic_appraisal": {
                "bias": somatic_bias,
                "warning": somatic_warning,
            },
            "action_gate": {
                "decision": gate_action,
                "net_drive": net_drive,
                "rationale": gate_rationale,
            },
            "working_memory_summary": self.dl_pfc.render_context_summary(),
            "fired_intentions": [i.to_dict() for i in fired_intentions],
            "tom_alerts": tom_discrepancies,
            "affective_state": self.valence_engine.get_state(),
        }

    def record_action_outcome(
        self,
        action: str,
        target: str,
        success: bool,
        surprise_score: float = 0.2,
        steps: Optional[List[str]] = None,
    ):
        """
        Post-execution feedback loop:
        1. Updates limbic valence & allostatic load.
        2. Reinforces somatic markers.
        3. Checks executive shifting/loop counters.
        4. Feeds hippocampal episodic replay buffer.
        5. Observes sequence for procedural compilation.
        """
        # Limbic
        self.valence_engine.record_outcome(success=success, magnitude=0.2, novelty=surprise_score)
        self.somatic_engine.record_experience(action, target, success, intensity=0.3)

        # Executive
        self.executive.evaluate_shifting(f"{action} {target}")

        # Hippocampus
        episode_id = f"ep_{int(os.times().system * 1000)}"
        self.replay_engine.record_episode(
            episode_id=episode_id,
            summary=f"Action: {action} {target}",
            details=f"Outcome: {'success' if success else 'failure'}",
            surprise_score=surprise_score,
            valence=0.5 if success else -0.5,
        )

        # Procedural skill compiler
        if steps:
            self.skill_compiler.observe_sequence(steps, success=success)
