#!/usr/bin/env python3
"""
Tests for scripts/graph_retrieval.py — graph-backed multi-hop retrieval.

The module's contract is that it never raises and never breaks the primary
retrieval path: a missing, unreadable, or relationship-free graph must degrade
to "no results plus a note". These tests hold that line, and cover the two
format details that have caused false diagnoses in this project:

  * graphify stores relationships under `links`, not `edges`;
  * graphify links reference node IDs, not labels.

Run:  python3 -m unittest tests.test_graph_retrieval
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import graph_retrieval as gr  # noqa: E402


def write_graph(root: Path, name: str, nodes, links) -> Path:
    """Create <root>/<vault>/graphify-out/graph.json with a real Graphify shape."""
    if name == "active-wiki":
        vault = root / "active-wiki"
    else:
        vault = root / "oracle" / "brain"
    out = vault / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "graph.json"
    # Deliberately mirror Graphify: relationships live under "links", and link
    # endpoints are node IDs rather than labels.
    path.write_text(json.dumps({"nodes": nodes, "links": links}), encoding="utf-8")
    return path


class TestGraphLoading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_links_not_edges(self):
        """A healthy graph must not be reported as relationship-free."""
        write_graph(
            self.root, "active-wiki",
            nodes=[{"id": "a", "label": "Alpha", "source_file": "alpha.md"},
                   {"id": "b", "label": "Beta", "source_file": "beta.md"}],
            links=[{"source": "a", "target": "b", "relation": "cites", "weight": 1.0}],
        )
        gr.HERMES_HOME = self.root
        gr.ACTIVE_WIKI = self.root / "active-wiki"
        gr.ORACLE_BRAIN = self.root / "oracle" / "brain"
        gr.GRAPH_SOURCES = {
            "active-wiki": gr.ACTIVE_WIKI / "graphify-out" / "graph.json",
            "oracle-brain": gr.ORACLE_BRAIN / "graphify-out" / "graph.json",
        }
        graphs, notes = gr.load_graphs(["active-wiki"])
        self.assertIn("active-wiki", graphs, f"graph failed to load: {notes}")
        self.assertEqual(len(graphs["active-wiki"].nodes), 2)
        # Both directions are indexed, so 1 link = 2 traversable edges.
        self.assertEqual(graphs["active-wiki"].edge_count, 2)

    def test_resolves_node_ids_to_labels(self):
        """Link endpoints are IDs; adjacency must key on labels."""
        write_graph(
            self.root, "active-wiki",
            nodes=[{"id": "hippo", "label": "Hippocampus", "source_file": "h.md"},
                   {"id": "ppr", "label": "PageRank", "source_file": "p.md"}],
            links=[{"source": "hippo", "target": "ppr", "relation": "implements",
                    "weight": 1.0, "source_file": "h.md"}],
        )
        g = gr.Graph("t", self.root / "active-wiki" / "graphify-out" / "graph.json")
        self.assertTrue(g.load(), g.reason)
        self.assertIn("Hippocampus", g.adjacency)
        self.assertIn("PageRank", g.adjacency["Hippocampus"])

    def test_missing_graph_is_not_fatal(self):
        gr.GRAPH_SOURCES = {"active-wiki": self.root / "nope" / "graph.json"}
        graphs, notes = gr.load_graphs(["active-wiki"])
        self.assertEqual(graphs, {})
        self.assertTrue(notes and "unavailable" in notes[0])

    def test_malformed_json_is_not_fatal(self):
        bad = self.root / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        g = gr.Graph("t", bad)
        self.assertFalse(g.load())
        self.assertIn("unreadable", g.reason)

    def test_nodes_without_relationships_is_not_fatal(self):
        write_graph(self.root, "active-wiki",
                    nodes=[{"id": "a", "label": "Alpha"}], links=[])
        g = gr.Graph("t", self.root / "active-wiki" / "graphify-out" / "graph.json")
        self.assertFalse(g.load())
        self.assertIn("no relationships", g.reason)

    def test_edges_key_also_accepted(self):
        """Non-Graphify exports use 'edges'; accept both."""
        p = self.root / "e.json"
        p.write_text(json.dumps({
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"source": "a", "target": "b", "relation": "r", "weight": 1.0}],
        }), encoding="utf-8")
        g = gr.Graph("t", p)
        self.assertTrue(g.load(), g.reason)
        self.assertEqual(g.edge_count, 2)


class TestTraversal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        # A -> B -> C -> D, so hop distances are unambiguous.
        write_graph(
            root, "active-wiki",
            nodes=[
                {"id": "a", "label": "Hippocampus", "source_file": "h.md"},
                {"id": "b", "label": "PageRank", "source_file": "p.md"},
                {"id": "c", "label": "Consolidation", "source_file": "c.md"},
                {"id": "d", "label": "Schema", "source_file": "d.md"},
            ],
            links=[
                {"source": "a", "target": "b", "relation": "implements", "weight": 1.0},
                {"source": "b", "target": "c", "relation": "cites", "weight": 1.0},
                {"source": "c", "target": "d", "relation": "references", "weight": 1.0},
            ],
        )
        self.path = root / "active-wiki" / "graphify-out" / "graph.json"
        self.g = gr.Graph("t", self.path)
        self.assertTrue(self.g.load(), self.g.reason)
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_matching(self):
        seeds = self.g.find_seeds("hippocampus")
        self.assertTrue(seeds)
        self.assertEqual(seeds[0][0], "Hippocampus")

    def test_pagerank_is_normalized_and_converged(self):
        """
        Personalized PageRank spreads mass from the seed outward and converges to
        a fixed distribution.

        It deliberately does NOT guarantee the seed ranks first: PPR is
        degree-normalized, so a degree-1 seed in a chain is outranked by its
        higher-degree neighbours. That is correct behaviour, not a bug -- and
        seeds are excluded from search results anyway, since a document that
        matched the query lexically is not a discovery.
        """
        seeds = self.g.find_seeds("Hippocampus")
        ranks = self.g.personalized_pagerank(seeds)
        self.assertTrue(ranks)
        self.assertAlmostEqual(sum(ranks.values()), 1.0, places=5)

        # Mass reaches the far end of the chain, which is the whole point.
        self.assertIn("Schema", ranks)
        self.assertGreater(ranks["Schema"], 0.0)

        # Converged: the fixed point does not depend on the iteration budget.
        # Compare rankings and distribution shape rather than exact per-node
        # floats, which are sensitive to dict iteration order during load.
        more = self.g.personalized_pagerank(seeds, iterations=400)
        self.assertEqual(
            [n for n, _ in sorted(ranks.items(), key=lambda x: -x[1])],
            [n for n, _ in sorted(more.items(), key=lambda x: -x[1])],
            "ranking changed with more iterations",
        )
        self.assertAlmostEqual(sum(more.values()), 1.0, places=5)

    def test_seed_itself_is_excluded_from_results(self):
        """A lexical match is not a discovery; results must be newly connected."""
        gr.GRAPH_SOURCES = {"active-wiki": self.path}
        out = gr.multi_hop_search("Hippocampus", sources=["active-wiki"], top_k=10, depth=3)
        self.assertNotIn("Hippocampus", {r["node"] for r in out["results"]})

    def test_hop_counts_are_accurate(self):
        """
        Regression: the previous neighbors() returned a flat (node, relation)
        list, so every result reported 1 hop regardless of the depth requested.
        """
        for t, path, hops in self.g.paths_from("Hippocampus", depth=3):
            expected = (len(path) - 1) // 2
            self.assertEqual(hops, expected, f"path {path} reported {hops} hops")

    def test_depth_is_respected(self):
        d1 = self.g.paths_from("Hippocampus", depth=1)
        d2 = self.g.paths_from("Hippocampus", depth=2)
        self.assertEqual({t for t, _, _ in d1}, {"PageRank"})
        self.assertIn("Consolidation", {t for t, _, _ in d2})
        self.assertNotIn("Schema", {t for t, _, _ in d2})

    def test_relation_filter_excludes_other_edge_types(self):
        """
        The filter gates EVERY edge in the path, not just the final one. From
        Hippocampus the only outgoing edge is 'implements', so restricting to
        'cites' correctly yields nothing -- traversal cannot reach PageRank, and
        therefore cannot see the 'cites' edge beyond it.
        """
        self.assertEqual(self.g.paths_from("Hippocampus", depth=3, relations={"cites"}), [])

        # Starting one hop in, the 'cites' edge IS reachable.
        from_pagerank = self.g.paths_from("PageRank", depth=2, relations={"cites"})
        self.assertEqual({t for t, _, _ in from_pagerank}, {"Consolidation"})

        # And an unfiltered walk includes every edge type.
        unfiltered = {t for t, _, _ in self.g.paths_from("Hippocampus", depth=3)}
        self.assertEqual(unfiltered, {"PageRank", "Consolidation", "Schema"})

    def test_multi_hop_search_end_to_end(self):
        gr.GRAPH_SOURCES = {"active-wiki": self.path}
        out = gr.multi_hop_search("Hippocampus", sources=["active-wiki"], top_k=5, depth=3)
        files = {r["file"] for r in out["results"]}
        self.assertIn("p.md", files)
        self.assertTrue(any(r["path"] for r in out["results"]),
                        "results must carry a connecting path")

    def test_unknown_query_returns_nothing_without_raising(self):
        gr.GRAPH_SOURCES = {"active-wiki": self.path}
        out = gr.multi_hop_search("zzzznonexistentterm", sources=["active-wiki"])
        self.assertEqual(out["results"], [])
        self.assertTrue(out["notes"])


if __name__ == "__main__":
    unittest.main()
