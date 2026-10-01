#!/usr/bin/env python3
"""
tests/test_brain_integration.py — Integration test suite for Hermes Brain REST API,
dynamic settings, and Hermes Agent lifecycle hooks.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add project root and dashboard to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "dashboard"))

from fastapi.testclient import TestClient
from dashboard.dashboard_server import app
import integrations_backend


class TestBrainIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_brain_status_endpoint(self):
        """Verify /api/brain/status returns full cognitive telemetry."""
        res = self.client.get("/api/brain/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "active")
        self.assertTrue(data.get("initialized"))
        self.assertIn("thalamus", data)
        self.assertIn("cortex", data)
        self.assertIn("limbic", data)
        self.assertIn("basal_ganglia", data)
        self.assertIn("hippocampus", data)
        self.assertIn("epistemology", data)
        self.assertIn("social", data)

    def test_brain_stimulus_endpoint(self):
        """Verify /api/brain/stimulus processes text through full cognitive pass."""
        payload = {
            "text": "Please refactor the database indexing to improve latency",
            "source": "user",
            "session_id": "test_session_1",
        }
        res = self.client.post("/api/brain/stimulus", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        analysis = data.get("analysis", {})
        self.assertIn("saliency", analysis)
        self.assertIn("cognitive_route", analysis)
        self.assertIn("action_gate", analysis)
        self.assertIn("affective_state", analysis)

    def test_brain_action_check_endpoint(self):
        """Verify /api/brain/action-check evaluates Basal Ganglia Go/No-Go pathways."""
        payload = {
            "action": "bash",
            "target": "ls -la",
            "expected_utility": 0.85,
            "conflict_level": 0.0,
        }
        res = self.client.post("/api/brain/action-check", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("decision"), ["GO", "NO_GO", "HYPERDIRECT_BRAKE"])
        self.assertIn("net_drive", data)
        self.assertIn("rationale", data)

    def test_brain_action_outcome_endpoint(self):
        """Verify /api/brain/action-outcome records post-execution feedback."""
        payload = {
            "action": "bash",
            "target": "ls -la",
            "success": True,
            "surprise_score": 0.1,
            "steps": ["ls -la"],
        }
        res = self.client.post("/api/brain/action-outcome", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "recorded")
        self.assertIn("affective_state", data)

    def test_brain_working_memory_goal(self):
        """Verify /api/brain/working-memory/goal updates active goal in dlPFC."""
        payload = {
            "goal": "Audit security vulnerabilities",
            "sub_goals": ["scan ports", "check auth", "review logs"],
            "hypotheses": ["unauthenticated endpoints may exist"],
        }
        res = self.client.post("/api/brain/working-memory/goal", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "goal_set")
        self.assertEqual(data.get("active_goal"), "Audit security vulnerabilities")
        self.assertEqual(len(data.get("sub_goals")), 3)

    def test_brain_beliefs_and_defeaters(self):
        """Verify epistemic belief creation and defeater evaluation."""
        # 1. Add belief
        belief_payload = {
            "topic": "networking",
            "statement": "Service is reachable on port 8088",
            "credence": 0.95,
            "provenance": "test",
            # Required since 0.6: a belief must name where it came from, or it
            # cannot be re-read later to check it.
            "source_location": "tests/test_brain_integration.py::networking",
        }
        res = self.client.post("/api/brain/beliefs", json=belief_payload)
        self.assertEqual(res.status_code, 200)
        belief_data = res.json()
        belief_id = belief_data.get("belief_id")
        self.assertIsNotNone(belief_id)

        # 2. Add defeating belief
        defeater_belief_payload = {
            "topic": "networking",
            "statement": "Port 8088 firewall is closed",
            "credence": 0.9,
            "provenance": "firewall_scanner",
            "source_location": "tests/test_brain_integration.py::firewall",
        }
        res2 = self.client.post("/api/brain/beliefs", json=defeater_belief_payload)
        self.assertEqual(res2.status_code, 200)
        defeater_belief_id = res2.json().get("belief_id")

        # 3. Add defeater relationship
        defeater_rel = {
            "target_belief_id": belief_id,
            "defeater_belief_id": defeater_belief_id,
            "defeater_type": "rebutting",
            "justification": "Firewall logs show port 8088 dropped packets",
        }
        res3 = self.client.post("/api/brain/beliefs/defeater", json=defeater_rel)
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json().get("status"), "defeater_recorded")

    def test_brain_counterfactual_rollout(self):
        """Verify Pearl Level-3 counterfactual regret rollout analysis."""
        payload = {
            "trigger_event": "HTTP 502 Bad Gateway",
            "actual_path": "Retried request immediately 5 times",
            "counterfactual_path": "Checked container logs and restarted service",
            "predicted_advantage": "Would have recovered in 5 seconds instead of timing out for 2 minutes",
            "lesson_extracted": "Inspect backend container health on 502 before repeating queries",
        }
        res = self.client.post("/api/brain/counterfactual", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "analyzed")
        self.assertEqual(data.get("record", {}).get("lesson_extracted"), payload["lesson_extracted"])

    def test_system_settings_dynamic_engine(self):
        """Verify dynamic settings API saves and retrieves LLM and voice configurations."""
        original_settings = integrations_backend.get_system_settings_raw()

        # Update settings with custom provider
        update_payload = {
            "operator_name": "TestOperator",
            "llm_provider": "openrouter",
            "llm_model": "nousresearch/hermes-3-llama-3.1-70b",
            "llm_base_url": "https://openrouter.ai/api/v1",
            "tts_provider": "edge",
            "tts_voice": "en-US-GuyNeural",
            "stt_provider": "browser",
        }
        save_res = self.client.post("/api/system/settings", json=update_payload)
        self.assertEqual(save_res.status_code, 200)

        # Retrieve settings
        get_res = self.client.get("/api/system/settings")
        self.assertEqual(get_res.status_code, 200)
        saved = get_res.json()
        self.assertEqual(saved.get("operator_name"), "TestOperator")
        self.assertEqual(saved.get("llm_provider"), "openrouter")
        self.assertEqual(saved.get("tts_provider"), "edge")

        # Restore original settings
        integrations_backend.save_system_settings(original_settings)

    def test_hermes_lifecycle_hooks(self):
        """Verify Hermes Agent hooks handle events safely (fail-open, non-blocking)."""
        # 1. brain-cognitive-guard hook
        import importlib.util
        guard_spec = importlib.util.spec_from_file_location(
            "guard_handler", str(REPO_ROOT / "hooks" / "brain-cognitive-guard" / "handler.py")
        )
        guard_mod = importlib.util.module_from_spec(guard_spec)
        guard_spec.loader.exec_module(guard_mod)

        # Test safe command
        safe_ctx = {"tool_name": "read_file", "tool_args": {"path": "README.md"}}
        safe_res = guard_mod.handle("agent:step", safe_ctx)
        self.assertIsNone(safe_res)  # None indicates allowed to proceed

        # 2. brain-memory-consolidator hook
        consolidator_spec = importlib.util.spec_from_file_location(
            "consolidator_handler", str(REPO_ROOT / "hooks" / "brain-memory-consolidator" / "handler.py")
        )
        consolidator_mod = importlib.util.module_from_spec(consolidator_spec)
        consolidator_spec.loader.exec_module(consolidator_mod)

        end_ctx = {
            "session_id": "test_turn_1",
            "message": "List recent files",
            "response": "Here are your files: a, b, c",
            "tools_called": [{"name": "list_dir", "args": "."}],
            "has_error": False,
        }
        # Should execute cleanly without raising exceptions
        consolidator_mod.handle("agent:end", end_ctx)

    def test_companion_adapters_and_sync_hook(self):
        """Verify companion adapters (visualizer and barehands) and lifecycle sync hook."""
        from plugins.adapters.visualizer import VisualizerAdapter
        from plugins.adapters.barehands import BarehandsAdapter

        vis = VisualizerAdapter()
        bh = BarehandsAdapter()

        # Companion apps are optional; skip gracefully when not installed
        if not (vis.is_installed and bh.is_installed):
            self.skipTest("companion apps (ai-visualizer, barehands) not installed")

        # Test state broadcasting via adapters
        self.assertTrue(vis.set_state("thinking"))
        self.assertEqual(vis.get_state(), "thinking")
        self.assertTrue(vis.set_state("idle"))
        self.assertEqual(vis.get_state(), "idle")

        self.assertTrue(bh.set_ring_state("thinking"))
        self.assertTrue(bh.set_ring_state("idle"))

        # Test hook execution
        import importlib.util
        sync_spec = importlib.util.spec_from_file_location(
            "sync_handler", str(REPO_ROOT / "hooks" / "hermes-visualizer-sync" / "handler.py")
        )
        sync_mod = importlib.util.module_from_spec(sync_spec)
        sync_spec.loader.exec_module(sync_mod)

        # Should execute cleanly across all lifecycle events
        sync_mod.handle("agent:start", {})
        self.assertEqual(vis.get_state(), "thinking")

        sync_mod.handle("agent:end", {"response": "Task completed successfully."})
        self.assertEqual(vis.get_state(), "speaking")

        sync_mod.handle("session:reset", {})
        self.assertEqual(vis.get_state(), "idle")

    def test_companion_api_endpoints(self):
        """Verify /api/companions REST endpoints on dashboard server."""
        # 1. GET /api/companions/status
        res = self.client.get("/api/companions/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("visualizer", data)
        self.assertIn("barehands", data)
        # Companion apps are optional; verify honest status reporting either way
        for companion in ("visualizer", "barehands"):
            self.assertIn(data[companion]["installed"], (True, False))
            self.assertIn("online", data[companion])
            self.assertIn("port", data[companion])

        # 2. POST /api/companions/visualizer/state
        res_state = self.client.post("/api/companions/visualizer/state", json={"state": "thinking"})
        self.assertEqual(res_state.status_code, 200)
        self.assertEqual(res_state.json().get("state"), "thinking")

        # 3. POST /api/companions/visualizer/face — 200 when installed, 404 when not
        res_face = self.client.post("/api/companions/visualizer/face", json={"face": "board"})
        if data["visualizer"]["installed"]:
            self.assertEqual(res_face.status_code, 200)
            self.assertEqual(res_face.json().get("face"), "board")
        else:
            self.assertEqual(res_face.status_code, 404)

    def test_belief_without_a_location_is_refused(self):
        """0.6 is only real if the API enforces it. A route that accepts an
        unsourced belief and stores it makes the requirement decorative."""
        res = self.client.post("/api/brain/beliefs", json={
            "topic": "networking",
            "statement": "A belief with no address",
            "credence": 0.9,
            "provenance": "user",
        })
        self.assertEqual(res.status_code, 422,
                         "an unsourced belief must be refused")


if __name__ == "__main__":
    unittest.main()
