#!/usr/bin/env python3
"""
tests/test_brain_architecture.py — Comprehensive test suite for Hermes Brain subsystems.
"""

import os
import shutil
import tempfile
import unittest

from brain import HermesBrain
from brain.schema import init_cortex_db
from brain.thalamus import SensoryBuffer, ThalamicGate
from brain.cortex import DorsolateralPFC, CognitiveRouter, ExecutiveControl
from brain.limbic import CognitiveValenceEngine, SomaticMarkerEngine
from brain.basal_ganglia import ActionGate, ProceduralSkillCompiler
from brain.hippocampus import HippoAssociativeGraph, HippocampalReplayEngine
from brain.dmn import ChronesthesiaEngine, CounterfactualEngine
from brain.epistemology import DefeaterGraph, AGMBeliefRevision, DialecticSynthesizer
from brain.social import TheoryOfMind, GriceanPragmatics
import gc


class TestBrainArchitecture(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_cortex.db")
        init_cortex_db(self.db_path)

    def tearDown(self):
        gc.collect()
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_thalamus(self):
        buf = SensoryBuffer(maxlen=5)
        event = buf.append("terminal", "error: out of memory", {"pid": 1234})
        self.assertEqual(len(buf.get_recent()), 1)
        self.assertEqual(event.source, "terminal")

        gate = ThalamicGate(saliency_threshold=0.35)
        admitted, score, disp = gate.evaluate_admission("critical error: system deadlock")
        self.assertTrue(admitted)
        self.assertGreater(score, 0.35)
        self.assertEqual(disp, "admit")

        # Noise should be attenuated
        admitted_noise, score_noise, disp_noise = gate.evaluate_admission("ok")
        self.assertFalse(admitted_noise)
        self.assertEqual(disp_noise, "attenuate")

    def test_cortex_dl_pfc(self):
        pfc = DorsolateralPFC(capacity=3, db_path=self.db_path)
        pfc.set_active_goal("Refactor cognitive architecture", ["task1", "task2"])
        pfc.upsert_slot("item1", "value1", importance=0.8)
        pfc.upsert_slot("item2", "value2", importance=0.9)
        pfc.upsert_slot("item3", "value3", importance=0.4)

        # Capacity eviction: adding 4th item when capacity=3 evicts lowest activation*importance
        pfc.upsert_slot("item4", "value4", importance=0.95)
        self.assertLessEqual(len(pfc.slots), 4) # goal + up to capacity items

        summary = pfc.render_context_summary()
        self.assertIn("CURRENT ACTIVE GOAL", summary)
        self.assertIn("task1", summary)

    def test_cortex_router(self):
        router = CognitiveRouter(system2_threshold=0.5)
        mode_simple, score_simple, _ = router.evaluate_route("hello there")
        self.assertEqual(mode_simple, "SYSTEM_1")

        mode_complex, score_complex, _ = router.evaluate_route(
            "Please refactor the database schema, investigate deadlocks, and architect a solution."
        )
        self.assertEqual(mode_complex, "SYSTEM_2")

    def test_cortex_executive(self):
        exec_ctrl = ExecutiveControl(loop_threshold=3)
        # Inhibition check
        inhibited, reason = exec_ctrl.check_inhibition("rm -rf /")
        self.assertTrue(inhibited)
        self.assertIn("INHIBITION TRIGGERED", reason)

        # Shifting check (loop detection)
        for _ in range(2):
            exec_ctrl.evaluate_shifting("python run.py")
        shift_needed, _ = exec_ctrl.evaluate_shifting("python run.py")
        self.assertTrue(shift_needed)

    def test_limbic_valence_and_somatic(self):
        val = CognitiveValenceEngine()
        val.record_outcome(success=True, magnitude=0.4)
        self.assertGreater(val.valence, 0.0)

        val.record_outcome(success=False, magnitude=0.8)
        self.assertLess(val.valence, 0.2)
        self.assertGreater(val.allostatic_load, 0.0)

        # Somatic marker with DB
        # Create schema first
        brain = HermesBrain(db_path=self.db_path)
        somatic = brain.somatic_engine
        somatic.record_experience("git push", "main", outcome_success=False, intensity=0.8)
        bias, warning = somatic.assess("git push", "main")
        self.assertLess(bias, -0.5)
        self.assertIn("Aversive Somatic Warning", warning)

    def test_basal_ganglia(self):
        gate = ActionGate(go_threshold=0.4)
        disp, net_drive, _ = gate.evaluate_pathways(
            candidate_action="deploy",
            expected_utility=0.8,
            somatic_bias=0.2,
            conflict_level=0.1,
        )
        self.assertEqual(disp, "GO")

        # Emergency brake
        disp_brake, _, _ = gate.evaluate_pathways(
            candidate_action="deploy",
            expected_utility=0.8,
            somatic_bias=0.2,
            conflict_level=0.1,
            emergency_alert=True,
        )
        self.assertEqual(disp_brake, "HYPERDIRECT_BRAKE")

        compiler = ProceduralSkillCompiler(compilation_threshold=2)
        compiler.observe_sequence(["fetch", "parse", "save"], success=True, suggested_name="data_pipeline")
        compiler.observe_sequence(["fetch", "parse", "save"], success=True, suggested_name="data_pipeline")
        skill = compiler.get_skill("data_pipeline")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.execution_count, 1)

    def test_hippocampus(self):
        graph = HippoAssociativeGraph(damping_factor=0.85)
        graph.add_episode("ep_101", ["auth", "jwt", "bug"])
        graph.add_episode("ep_102", ["jwt", "token_expiry", "fix"])
        results = graph.retrieve_relevant(["auth"], top_k=3)
        self.assertTrue(len(results) > 0)

        replay = HippocampalReplayEngine()
        replay.record_episode("ep_1", "Auth crash", "Stack trace...", surprise_score=0.9, valence=-0.8)
        consolidated = replay.run_consolidation_replay(max_episodes=1)
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0]["episode_id"], "ep_1")

    def test_dmn(self):
        chron = ChronesthesiaEngine()
        chron.record_timeline_event("t1", "Initial server start", {"status": "ok"})
        retrospect = chron.retrospection("server start")
        self.assertIsNotNone(retrospect)

        cf = CounterfactualEngine(db_path=self.db_path)
        record = cf.analyze_regret(
            trigger_event="DB deadlock",
            actual_path="Immediate restart",
            counterfactual_path="Inspect lock graph",
            predicted_advantage="Identified root query without service restart",
            lesson_extracted="Always dump pg_locks prior to restarting database",
        )
        self.assertEqual(record["trigger_event"], "DB deadlock")

    def test_epistemology(self):
        # Defeater Graph
        brain = HermesBrain(db_path=self.db_path)
        defeater_graph = brain.defeater_graph
        b1 = defeater_graph.add_belief("system", "Postgres is running on port 5432",
                               credence=1.0, source_location="test:architecture")
        b2 = defeater_graph.add_belief("system", "Port 5432 is bound by another service",
                               credence=0.9, source_location="test:architecture")
        defeater_graph.add_defeater(b1, b2, "rebutting", "Port scan revealed foreign PID")

        disputed = defeater_graph.get_disputed_beliefs()
        self.assertEqual(len(disputed), 1)
        self.assertEqual(disputed[0]["belief_id"], b1)

        # AGM Revision
        agm = AGMBeliefRevision()
        agm.expand("b1", "Server is live", entrenchment=0.4)
        agm.revise("b2", "Server is offline", conflicts_with=["b1"], entrenchment=0.8)
        self.assertNotIn("b1", agm.corpus)
        self.assertIn("b2", agm.corpus)

        # Dialectic Synthesizer
        dialectic = DialecticSynthesizer()
        syn = dialectic.synthesize("Monoliths are easier to deploy", "Microservices scale better")
        self.assertIn("Synthesis:", syn["synthesis"])

    def test_social(self):
        brain = HermesBrain(db_path=self.db_path)
        tom = brain.tom
        tom.update_model("build_status", "User believes build succeeded", "Build failed with exit code 1")
        discrepancies = tom.check_discrepancies("build_status")
        self.assertEqual(len(discrepancies), 1)

        pragmatics = GriceanPragmatics()
        implicature = pragmatics.analyze_implicature("the auth service is broken")
        self.assertTrue(implicature["is_indirect_request"])
        self.assertIn("Investigate, diagnose, and fix auth", implicature["inferred_directive"])

    def test_hermes_brain_orchestration(self):
        brain = HermesBrain(db_path=self.db_path)
        result = brain.process_incoming_stimulus(
            source="user_chat",
            text="Can you please optimize the database queries and fix the slow response times?",
        )
        self.assertIn("saliency", result)
        self.assertIn("cognitive_route", result)
        self.assertEqual(result["cognitive_route"]["mode"], "SYSTEM_2")
        self.assertIn("action_gate", result)


if __name__ == "__main__":
    unittest.main()
