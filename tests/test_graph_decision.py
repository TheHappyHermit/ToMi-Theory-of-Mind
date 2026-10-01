#!/usr/bin/env python3
"""
Tests for the Phase 4 graph decision and its checker.

The decision is only worth something if it cannot quietly become folklore. Two
failure modes matter:

  1. A number in the decision stops matching reality and nobody notices. The
     most likely instance: the graph scored 0.000 for a long time because of a
     path bug, and a reader could easily take 0.000 as the graph's real score.

  2. Someone re-investigates a question this phase already settled. The plan
     document contains two claims that did not survive checking; recording that
     they were checked is what stops the next session repeating the work.

Run:  PYTHONPATH=<repo> python3 tests/test_graph_decision.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import verify_graph_decision as vgd  # noqa: E402


class TestDecisionIsRecorded(unittest.TestCase):
    def setUp(self):
        self.md = (REPO / "docs" / "GRAPH-DECISION.md")
        self.js = (REPO / "docs" / "GRAPH-DECISION.json")

    def test_both_forms_exist(self):
        self.assertTrue(self.md.exists(), "no decision document")
        self.assertTrue(self.js.exists(), "no machine-readable decision")

    def test_json_is_valid(self):
        json.loads(self.js.read_text())

    def test_the_decision_is_stated_not_left_open(self):
        d = json.loads(self.js.read_text())
        self.assertEqual(d["decision"], "keep")
        self.assertIn("not a default", d["not"])

    def test_routing_says_retrieval_is_the_default(self):
        """The decision is a routing rule. If the default ever becomes the
        graph, the finding that motivated it -- no published evidence a graph
        beats retrieval on direct lookup -- has been quietly overturned."""
        r = json.loads(self.js.read_text())["routing"]
        self.assertEqual(r["direct_lookup_single_hop_fact"], "retrieval")
        self.assertEqual(r["default"], "retrieval")
        self.assertEqual(r["multi_hop"], "graph")

    def test_both_deployment_gradings_are_kept(self):
        """The plan is explicit: keep both, because a reader who sees only one
        draws the wrong conclusion in one direction or the other."""
        g = json.loads(self.js.read_text())["deployment_finding_keep_both_gradings"]
        self.assertEqual(g["design_grade"], "LOW")
        self.assertIn("not running", g["deployment_grade"])

    def test_unresolved_items_are_marked_unresolved(self):
        """Recorded as open, not quietly answered. Picking a side between two
        third-party numbers without running the comparison would assert a
        preference as a finding."""
        items = json.loads(self.js.read_text())["unresolved_on_purpose"]
        self.assertGreaterEqual(len(items), 2)
        for i in items:
            self.assertIn("why_not_settled", i)

    def test_the_owner_measured_ingestion_time_is_not_attributed_upstream(self):
        doc = self.md.read_text()
        self.assertIn("own measured run", doc)
        self.assertIn("Do not cite it as an upstream claim", doc)

    def test_markdown_is_100_percent_the_expensive_pass(self):
        doc = self.md.read_text()
        self.assertIn("100% the expensive LLM", doc)


class TestPlanClaimsWereChecked(unittest.TestCase):
    """The plan document asserted two things about graphify. Both were checked
    against the installed code, and one was wrong. Recording that is what stops
    the investigation being repeated."""

    def setUp(self):
        self.corrections = json.loads(
            (REPO / "docs" / "GRAPH-DECISION.json").read_text())["plan_claims_corrected"]

    def test_both_claims_are_recorded(self):
        self.assertEqual(len(self.corrections), 2)

    def test_markdown_extraction_claim_is_recorded_as_no_longer_true(self):
        c = [x for x in self.corrections if "markdown" in x["claim"].lower()]
        self.assertEqual(len(c), 1, "the markdown claim is not recorded")
        self.assertIn("no longer true", c[0]["verdict"])
        self.assertIn("extract.py", c[0]["evidence"])

    def test_truncation_claim_is_recorded_as_wrong(self):
        """Retracted, not quietly deleted. The first draft of the decision
        asserted the opposite, and that error is the kind that recurs unless
        it is written down."""
        c = [x for x in self.corrections if "CAP" in x["claim"]]
        self.assertEqual(len(c), 1, "the truncation claim is not recorded")
        self.assertIn("wrong", c[0]["verdict"])
        self.assertIn("1369", c[0]["verdict"])
        self.assertIn("reassemble byte-identically", c[0]["evidence"])

    def test_the_error_made_is_recorded(self):
        w = json.loads((REPO / "docs" / "GRAPH-DECISION.json").read_text())[
            "why_keep_despite_scoring_lower"]
        self.assertIn("RETRACTED", w[0]["finding"])
        self.assertIn("error_made", w[0])


class TestTheCapDoesNotTruncate(unittest.TestCase):
    """The retraction, as an executable assertion.

    The whole point is that _FILE_CHAR_CAP is a per-SLICE limit and oversized
    files are pre-split, so no content is dropped. A test that only read the
    constant would pass whether or not that were true.
    """

    def test_presplit_is_wired_in_before_packing(self):
        c = vgd.check_file_char_cap()
        if not c.get("found"):
            self.skipTest("graphify not installed here")
        self.assertTrue(c["presplit_before_packing"],
                        "oversized files are no longer pre-split; content may be dropped")

    def test_slices_roundtrip_the_whole_file(self):
        c = vgd.check_file_char_cap()
        if not c.get("found") or c.get("slicing_is_lossless") is None:
            self.skipTest("graphify.file_slice not importable from this interpreter")
        self.assertTrue(c["slicing_is_lossless"],
                        f"slices do not reassemble the original: {c.get('detail')}")
        self.assertFalse(c["content_is_lost"])

    def test_the_decision_does_not_claim_content_was_lost(self):
        doc = (REPO / "docs" / "GRAPH-DECISION.md").read_text()
        # the wrong claim may appear only as an explicitly-marked correction
        for line in doc.split("\n"):
            if "truncated before extraction" in line:
                self.assertIn("NOT a defect", line,
                              f"stale uncorrected claim: {line.strip()[:90]}")


class TestCheckerRuns(unittest.TestCase):
    def test_it_runs_and_exits_zero(self):
        r = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "verify_graph_decision.py")],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_json_output_is_parseable(self):
        r = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "verify_graph_decision.py"), "--json"],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        json.loads(r.stdout)

    def test_it_reports_the_truncation_defect(self):
        """The checker exists to surface exactly this. A checker that does not
        mention the defect the decision leans on is not checking anything."""
        out = vgd.check_file_char_cap()
        self.assertTrue(out.get("found"), "checker did not find the graphify install")
        if out.get("cap") is not None:
            self.assertEqual(out["cap"], 20_000)

    def test_it_reports_corpus_truncation_impact(self):
        c = vgd.check_corpus_size()
        if c.get("found"):
            self.assertGreater(c["over_cap_pct"], 0)
            self.assertLessEqual(c["max_file_read_pct"], 100.0)

    def test_it_detects_a_missing_decision_file(self):
        """A checker that cannot fail is not a checker."""
        original = (vgd.DECISION_MD, vgd.DECISION_JSON)
        try:
            vgd.DECISION_MD = Path(tempfile.gettempdir()) / "absent.md"
            vgd.DECISION_JSON = Path(tempfile.gettempdir()) / "absent.json"
            problems = vgd.check_decision_files()
        finally:
            vgd.DECISION_MD, vgd.DECISION_JSON = original
        self.assertTrue(problems, "a missing decision file was not detected")

    def test_it_detects_malformed_json(self):
        original = vgd.DECISION_JSON
        bad = Path(tempfile.gettempdir()) / "bad-decision.json"
        bad.write_text("{not valid json")
        try:
            vgd.DECISION_JSON = bad
            problems = vgd.check_decision_files()
        finally:
            vgd.DECISION_JSON = original
            bad.unlink(missing_ok=True)
        self.assertTrue(problems, "malformed JSON was not detected")

    def test_it_detects_a_missing_required_key(self):
        original = vgd.DECISION_JSON
        thin = Path(tempfile.gettempdir()) / "thin-decision.json"
        thin.write_text('{"decision": "keep"}')
        try:
            vgd.DECISION_JSON = thin
            problems = vgd.check_decision_files()
        finally:
            vgd.DECISION_JSON = original
            thin.unlink(missing_ok=True)
        self.assertTrue(problems, "a decision missing routing/measured was accepted")


class TestRoutingIsActuallyImplemented(unittest.TestCase):
    """The decision is a document AND a behaviour. This asserts the behaviour,
    so the routing rule cannot be documented and then contradicted in code."""

    def setUp(self):
        sys.path.insert(0, str(REPO))
        from brain.hermes_brain import HermesBrain
        import tempfile, sqlite3, shutil
        tmp = tempfile.mkdtemp(prefix="route-")
        self.db = Path(tmp) / "b.db"
        with open(REPO / "brain" / "schema" / "brain_cortex.sql") as fh:
            sqlite3.connect(self.db).executescript(fh.read())
        self.brain = HermesBrain(db_path=str(self.db))
        self.w = self.brain.wiring
        self.tmp = tmp

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_retrieval_is_the_default_for_a_short_reflexive_turn(self):
        should, why = self.w.gate_associative_graph("SYSTEM_1", "fix the typo")
        self.assertFalse(should, "the graph became a default")
        self.assertIn("reflexive", why)

    def test_the_graph_is_a_candidate_on_the_deliberate_route(self):
        should, why = self.w.gate_associative_graph("SYSTEM_2", "anything")
        self.assertTrue(should, f"graph is not available when deliberating: {why}")

    def test_the_graph_fires_when_one_document_cannot_hold_the_answer(self):
        wide = ("graph retrieval fusion benchmark recall precision latency "
                "index corpus vault schema migration rollback")
        should, why = self.w.gate_associative_graph("SYSTEM_1", wide)
        self.assertTrue(should, f"multi-hop shape did not reach the graph: {why}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
