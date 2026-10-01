"""Tests for scripts/verify_graph_integrity.py.

Covers the two graphify failure modes the checker exists to catch:
- #3105 (fixed in 0.9.51): a file present at build time contributes no nodes
- #3776 (OPEN): incremental edge loss leaves no detectable signal, so the
  checker must always warn that a graph cannot be proven correct
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import verify_graph_integrity as vgi  # noqa: E402


def write(path: Path, content: str, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def graph(nodes, links, built="abc123"):
    return {
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": nodes,
        "links": links,
        "built_at_commit": built,
    }


def node(i, label, src):
    return {"id": i, "label": label, "source_file": src}


class TestIntegrity(unittest.TestCase):
    def test_clean_graph_has_no_errors(self):
        g = graph([node("1", "A", "a.md"), node("2", "B", "b.md")],
                  [{"source": "1", "target": "2", "relation": "cites"}])
        findings = vgi.check_integrity(g)
        self.assertEqual([f for f in findings if f.severity == "error"], [])

    def test_dangling_endpoint_is_an_error(self):
        g = graph([node("1", "A", "a.md")],
                  [{"source": "1", "target": "ghost", "relation": "cites"}])
        findings = vgi.check_integrity(g)
        self.assertTrue(any("unresolvable endpoint" in f.message for f in findings))

    def test_empty_label_is_an_error(self):
        g = graph([node("1", "   ", "a.md")], [])
        findings = vgi.check_integrity(g)
        self.assertTrue(any("empty label" in f.message for f in findings))

    def test_edges_key_accepted_as_well_as_links(self):
        g = {
            "nodes": [node("1", "A", "a.md"), node("2", "B", "b.md")],
            "edges": [{"source": "1", "target": "2"}],
        }
        findings = vgi.check_integrity(g)
        self.assertEqual([f for f in findings if f.severity == "error"], [])


class TestDensity(unittest.TestCase):
    def test_sparse_graph_warns(self):
        nodes = [node(str(i), f"N{i}", "a.md") for i in range(100)]
        g = graph(nodes, [{"source": "0", "target": "1"}])  # ratio 0.01
        findings = vgi.check_density(g)
        self.assertTrue(any(f.severity == "warning" for f in findings))

    def test_healthy_density_is_quiet(self):
        nodes = [node(str(i), f"N{i}", "a.md") for i in range(10)]
        links = [{"source": str(i), "target": str((i + 1) % 10)} for i in range(20)]
        findings = vgi.check_density(graph(nodes, links))
        self.assertEqual([f for f in findings if f.severity == "warning"], [])

    def test_empty_graph_is_an_error(self):
        findings = vgi.check_density(graph([], []))
        self.assertTrue(any(f.severity == "error" for f in findings))


class TestProvenance(unittest.TestCase):
    def test_missing_built_at_commit_is_an_error(self):
        g = graph([node("1", "A", "a.md")], [])
        g.pop("built_at_commit")
        findings = vgi.check_provenance(g, None)
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_provenance_present_no_finding(self):
        g = graph([node("1", "A", "a.md")], [])
        findings = vgi.check_provenance(g, None)
        self.assertEqual(findings, [])


class TestCompletenessStalenessSplit(unittest.TestCase):
    """The distinction that makes this check honest.

    A file newer than the graph is not indexed yet -- normal. A file OLDER than
    the graph that contributed nothing was seen by extraction and silently
    dropped -- that is the #3105 signature.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.graph_path = self.vault / "graph.json"
        # graph "built" at t=2000
        os.utime(self.graph_path, (2000, 2000)) if self.graph_path.exists() else None

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, represented):
        g = graph([node(str(i), f"N{i}", s) for i, s in enumerate(represented)], [])
        write(self.graph_path, json.dumps(g), 2000.0)

    def test_file_older_than_graph_that_is_absent_is_a_gap(self):
        write(self.vault / "indexed.md", "# a", 1000.0)   # older, represented
        write(self.vault / "dropped.md", "# b", 1000.0)   # older, NOT represented
        self._build(["indexed.md"])
        findings = vgi.check_completeness(
            json.loads(self.graph_path.read_text()), self.vault, self.graph_path
        )
        errors = [f for f in findings if f.severity == "error"]
        self.assertTrue(errors, "an older absent file must be flagged as a gap")
        self.assertIn("existed at build time", errors[0].message)

    def test_file_newer_than_graph_is_only_info(self):
        write(self.vault / "indexed.md", "# a", 1000.0)
        write(self.vault / "future.md", "# c", 3000.0)    # newer than the build
        self._build(["indexed.md"])
        findings = vgi.check_completeness(
            json.loads(self.graph_path.read_text()), self.vault, self.graph_path
        )
        self.assertEqual([f for f in findings if f.severity == "error"], [])
        self.assertTrue(any(f.severity == "info" for f in findings))

    def test_fully_represented_graph_is_quiet(self):
        write(self.vault / "a.md", "# a", 1000.0)
        write(self.vault / "b.md", "# b", 1000.0)
        self._build(["a.md", "b.md"])
        findings = vgi.check_completeness(
            json.loads(self.graph_path.read_text()), self.vault, self.graph_path
        )
        self.assertEqual([f for f in findings if f.severity in ("error", "warning")], [])

    def test_basename_matching_avoids_false_positive(self):
        """graphify may store a longer relative path; match on basename too."""
        write(self.vault / "deep" / "nested" / "a.md", "# a", 1000.0)
        self._build(["deep/nested/a.md"])
        findings = vgi.check_completeness(
            json.loads(self.graph_path.read_text()), self.vault, self.graph_path
        )
        self.assertEqual([f for f in findings if f.severity == "error"], [])


class TestIncrementalRiskAlwaysWarns(unittest.TestCase):
    """#3776 leaves no signal. The checker must never imply it proved correctness."""

    def test_always_emits_info(self):
        g = graph([node("1", "A", "a.md")], [])
        findings = vgi.check_incremental_risk(g)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "info")
        self.assertIn("3776", findings[0].message)


class TestMainExitCodes(unittest.TestCase):
    def _write_graph(self, g):
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name) / "graph.json"
        p.write_text(json.dumps(g), encoding="utf-8")
        return tmp, p

    def test_missing_file_is_exit_2(self):
        self.assertEqual(vgi.main(["/nonexistent/graph.json"]), 2)

    def test_clean_graph_exits_0(self):
        tmp, p = self._write_graph(
            graph([node("1", "A", "a.md"), node("2", "B", "b.md")],
                  [{"source": "1", "target": "2", "relation": "cites"}])
        )
        try:
            self.assertEqual(vgi.main([str(p), "--quiet"]), 0)
        finally:
            tmp.cleanup()

    def test_corrupt_json_exits_2(self):
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name) / "graph.json"
        p.write_text("{not json", encoding="utf-8")
        try:
            self.assertEqual(vgi.main([str(p)]), 2)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
