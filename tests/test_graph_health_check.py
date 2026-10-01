"""Tests for scripts/graph_health_check.py.

The specific failure this guards against: the previous version of this check
printed a green tick comparing 0 == 0 when neither the manifest nor the graph
could be read. A check that cannot fail is worse than no check, so these tests
assert the failure paths as carefully as the success path.
"""
import contextlib
import importlib.util
import os
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "graph_health_check.py"

spec = importlib.util.spec_from_file_location("graph_health_check", SCRIPT)
assert spec is not None and spec.loader is not None
ghc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ghc)


def write_graph(directory, nodes, hyperedges=None):
    """Write a graph.json containing exactly `nodes`.

    hyperedges defaults to covering every node, so a caller asking for N nodes
    gets N nodes back. Chunking in pairs is arbitrary but keeps the file
    structurally identical to what Graphify emits.
    """
    directory.mkdir(parents=True, exist_ok=True)
    nodes = list(nodes)
    if hyperedges is None:
        hyperedges = max(1, (len(nodes) + 1) // 2)
    payload = {
        "directed": False,
        "multigraph": False,
        "graph": {
            "hyperedges": [
                {"nodes": nodes[i:i + 2]} for i in range(0, len(nodes), 2)
            ][:hyperedges]
        },
    }
    (directory / "graph.json").write_text(json.dumps(payload))


def write_manifest(directory, count):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(
        json.dumps({f"file{i}.md": {} for i in range(count)})
    )


class TestGraphHealthCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.aw = self.tmp / "active-wiki" / "graphify-out"
        self.ob = self.tmp / "oracle" / "brain" / "graphify-out"

    def at_root(self, root):
        """Point main() at a temporary data root, then restore the env."""
        @contextlib.contextmanager
        def _ctx():
            previous = os.environ.get("HERMES_DATA_DIR")
            os.environ["HERMES_DATA_DIR"] = str(root)
            try:
                yield
            finally:
                if previous is None:
                    os.environ.pop("HERMES_DATA_DIR", None)
                else:
                    os.environ["HERMES_DATA_DIR"] = previous
        return _ctx()

    def test_reads_healthy_graph(self):
        write_graph(self.aw, ["A", "B", "C", "D"])
        write_manifest(self.aw, 2)
        result = ghc.analyze_graph(self.aw)
        self.assertNotIn("error", result)
        self.assertEqual(result["nodes"], 4)

    def test_missing_graph_is_an_error_not_a_zero(self):
        """A missing file must never look like a healthy empty graph."""
        result = ghc.analyze_graph(self.aw)
        self.assertIn("error", result)
        self.assertNotIn("nodes", result)

    def test_empty_graph_is_rejected(self):
        """Parses fine, but 0 nodes means the ingest did not produce a graph."""
        write_graph(self.aw, [])
        result = ghc.analyze_graph(self.aw)
        self.assertIn("error", result)
        self.assertIn("0 nodes", result["error"])

    def test_malformed_json_is_an_error(self):
        self.aw.mkdir(parents=True, exist_ok=True)
        (self.aw / "graph.json").write_text("{not json")
        result = ghc.analyze_graph(self.aw)
        self.assertIn("error", result)
        self.assertIn("not valid JSON", result["error"])

    def test_graph_without_graph_key_is_an_error(self):
        self.aw.mkdir(parents=True, exist_ok=True)
        (self.aw / "graph.json").write_text(json.dumps({"nodes": []}))
        result = ghc.analyze_graph(self.aw)
        self.assertIn("error", result)

    def test_missing_manifest_is_an_error(self):
        result = ghc.analyze_manifest(self.aw)
        self.assertIn("error", result)
        self.assertNotIn("count", result)

    def test_empty_manifest_is_rejected(self):
        self.aw.mkdir(parents=True, exist_ok=True)
        (self.aw / "manifest.json").write_text("{}")
        result = ghc.analyze_manifest(self.aw)
        self.assertIn("error", result)

    def test_verdict_is_missing_when_graph_absent(self):
        self.assertEqual(ghc.verdict({"error": "x"}, {"count": 3}), "MISSING")

    def test_verdict_is_degraded_when_manifest_absent(self):
        self.assertEqual(ghc.verdict({"nodes": 5}, {"error": "x"}), "DEGRADED")

    def test_verdict_is_healthy_when_both_load(self):
        self.assertEqual(ghc.verdict({"nodes": 5}, {"count": 5}), "HEALTHY")

    def test_main_exits_nonzero_when_nothing_exists(self):
        """The regression: two unreadable graphs used to report success."""
        with self.at_root(self.tmp):
            self.assertEqual(ghc.main(), 1)

    def test_main_exits_zero_when_healthy(self):
        for d in (self.aw, self.ob):
            write_graph(d, ["A", "B", "C", "D"])
            write_manifest(d, 2)
        with self.at_root(self.tmp):
            self.assertEqual(ghc.main(), 0)

    def test_script_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.exists())
        self.assertTrue(SCRIPT.stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
