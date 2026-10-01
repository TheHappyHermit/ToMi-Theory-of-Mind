#!/usr/bin/env python3
"""
graph_retrieval.py — Multi-hop relational retrieval over the Graphify graphs.

Why this module exists
----------------------
`scripts/brain_query.py` performs hybrid BM25 + vector search with Reciprocal
Rank Fusion. That answers "which documents are *similar* to this text?" It
cannot answer "what *connects* these two things?", because similarity is a
single-hop operation over a bag of embeddings.

The repository has had a graph layer for some time and nothing ever called it:

* `brain/hippocampus/associative.py` implements Personalized PageRank over a
  concept-episode graph. It works -- a two-hop walk was verified by hand -- but
  `add_edge()` and `retrieve_relevant()` had zero callers outside tests.
* Graphify maintains real knowledge graphs over the two wiki vaults. Nothing in
  the repository read them.

So the capability was designed but not operational. This module is the missing
query path: it reads a Graphify `graph.json`, finds the nodes matching a query,
and walks the relationships outward to surface documents that are connected to
the query but not textually similar to it.

Relationship storage format
---------------------------
Graphify writes relationships under a **`links`** key, not `edges`. Reading
`edges` alone reports zero relationships for a perfectly healthy graph. This
module reads both, and `graphify_health.py` does the same.

Degradation
-----------
Everything here is optional. If a graph is missing, malformed, or empty, the
caller gets an empty result plus a reason -- never an exception. A relational
index that fails must not take down keyword search, which is the system's
primary retrieval path.
"""

import json
import math
import os
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# ── Path resolution ─────────────────────────────────────────────────────

# Output directory is configurable per source, so a different indexer writing the
# same node/edge JSON shape can be pointed at instead of Graphify without any
# change to the traversal, ranking, or caller code. See
# docs/GRAPH-SUBSTRATE-EVALUATION.md for why this indirection is deliberate
# rather than incidental: the producing tool is the replaceable part, and the
# graph format is the durable asset.
#
# Env: GRAPHIFY_OUT_DIRNAME (default "graphify-out"), or per-source overrides
# GRAPH_OUT_ACTIVE_WIKI / GRAPH_OUT_ORACLE_BRAIN.
# Defined before any path resolution, because _has_vault() needs it.
_OUT_DIRNAME = os.environ.get("GRAPHIFY_OUT_DIRNAME", "graphify-out")


def _has_vault(root: Path) -> bool:
    """True if this root actually contains a built graph, not an empty scaffold.

    Checking for the directory alone is not enough: ~/.hermes/oracle/brain
    exists but is empty, so a directory test passes on a root that has no graph
    at all. Test for graph.json, which is what the retriever actually needs.
    """
    return any((root / name).exists() for name in ("active-wiki", "oracle")) and any(
        (root / name / _OUT_DIRNAME / "graph.json").exists()
        for name in ("active-wiki", "oracle")
    )


def _hermes_home(strict: bool = False) -> Path:
    # An explicitly configured root wins, but only if it actually holds a vault.
    # HERMES_HOME is commonly exported as ~/.hermes while the real corpus lives in
    # ~/.hermes/oracle; trusting the env var unconditionally made every graph query
    # silently load nothing.
    #
    # `strict=True` disables the fallback entirely, so an explicit path that has
    # no vault is reported as empty rather than quietly replaced by a different
    # one. Measurement code needs this: a benchmark asked to score vault X must
    # fail loudly when X is missing, never silently score some other corpus.
    for var in ("HERMES_DATA_DIR", "HERMES_HOME"):
        val = os.environ.get(var, "").strip()
        if val:
            cand = Path(val).expanduser().resolve()
            if _has_vault(cand) or strict:
                return cand
            fallback = _hermes_fallback()
            if fallback is not None:
                print(f"[graph_retrieval] WARNING: {var}={cand} has no vault; "
                      f"using {fallback} instead", file=sys.stderr)
                return fallback
            return cand
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win.exists():
            return win
    return _hermes_fallback() or (Path.home() / ".hermes").resolve()


def _hermes_fallback() -> Optional[Path]:
    """Locate the vault under ~/.hermes if it exists there."""
    home_root = Path.home() / ".hermes"
    return home_root if _has_vault(home_root) else None


HERMES_HOME = _hermes_home()
ACTIVE_WIKI = Path(os.environ.get("ACTIVE_WIKI_PATH", str(HERMES_HOME / "active-wiki")))
ORACLE_BRAIN = Path(os.environ.get("ORACLE_BRAIN_PATH", str(HERMES_HOME / "oracle" / "brain")))

# Output directory is configurable per source, so a different indexer writing the
# same node/edge JSON shape can be pointed at instead of Graphify without any
# change to the traversal, ranking, or caller code. See
# docs/GRAPH-SUBSTRATE-EVALUATION.md for why this indirection is deliberate
# rather than incidental: the producing tool is the replaceable part, and the
# graph format is the durable asset.
#
# Env: GRAPHIFY_OUT_DIRNAME (default "graphify-out"), or per-source overrides
# GRAPH_OUT_ACTIVE_WIKI / GRAPH_OUT_ORACLE_BRAIN.
_OUT_DIRNAME = os.environ.get("GRAPHIFY_OUT_DIRNAME", "graphify-out")


def _graph_path(vault: Path, override_var: str) -> Path:
    override = os.environ.get(override_var, "").strip()
    return vault / (override or _OUT_DIRNAME) / "graph.json"


GRAPH_SOURCES = {
    "active-wiki": _graph_path(ACTIVE_WIKI, "GRAPH_OUT_ACTIVE_WIKI"),
    "oracle-brain": _graph_path(ORACLE_BRAIN, "GRAPH_OUT_ORACLE_BRAIN"),
}

# Relations that express meaningful conceptual linkage. Structural relations
# (cites, references) are included because they *are* the cross-document links
# a multi-hop question is usually asking about.
DEFAULT_RELATIONS = None  # None = follow every relation type


# ── Graph loading ───────────────────────────────────────────────────────

class Graph:
    """A loaded Graphify graph with an adjacency index and a node->file map."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.nodes: List[dict] = []
        self.adjacency: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
        self.node_files: Dict[str, str] = {}
        self._index: Dict[str, str] = {}
        self.loaded = False
        self.reason = ""

    # -- construction --------------------------------------------------
    def _node_label(self, raw) -> str:
        if isinstance(raw, str):
            return raw
        if not isinstance(raw, dict):
            return str(raw)
        for key in ("label", "name", "title", "id"):
            v = raw.get(key)
            if isinstance(v, str) and v:
                return v
        return str(raw.get("id", ""))

    def _node_id(self, raw) -> str:
        if isinstance(raw, dict):
            return str(raw.get("id", ""))
        return str(raw)

    def load(self) -> bool:
        if not self.path.exists():
            self.reason = f"no graph at {self.path}"
            return False
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.reason = f"unreadable: {e}"
            return False

        self.nodes = raw.get("nodes") or []
        # Graphify uses "links"; other exports use "edges". Read both.
        links = raw.get("links") or raw.get("edges") or []

        # Graphify links reference node IDs ("tm_search"), not labels
        # ("tm_search.py"). Build the ID->label map first so traversal keys on
        # something human-readable and consistent with find_seeds().
        id_to_label: Dict[str, str] = {}
        for node in self.nodes:
            nid = self._node_id(node)
            if nid:
                id_to_label[nid] = self._node_label(node)

        def resolve(ref) -> str:
            """Accept a node ID or a label and return the label."""
            if ref is None:
                return ""
            if isinstance(ref, dict):
                return self._node_label(ref)
            key = str(ref)
            return id_to_label.get(key) or self._node_label(key)

        for node in self.nodes:
            nid = self._node_id(node)
            label = self._node_label(node)
            if nid:
                self._index[nid] = label
                self._index.setdefault(label.lower(), nid)
            if isinstance(node, dict):
                # Preserve the file/heading a node came from, when present, so
                # traversal can point at a real document.
                src = node.get("source_file") or node.get("file") or node.get("path") or ""
                if src and not str(src).startswith("graphify-out"):
                    self.node_files[label] = str(src)

        # Links often carry the source file even when the node does not.
        for link in links:
            if not isinstance(link, dict):
                continue
            src_file = link.get("source_file") or ""
            if not src_file or str(src_file).startswith("graphify-out"):
                continue
            for ref in (link.get("source"), link.get("target")):
                label = resolve(ref)
                if label:
                    self.node_files.setdefault(label, str(src_file))

        for link in links:
            if not isinstance(link, dict):
                continue
            s = resolve(link.get("source", link.get("from")))
            t = resolve(link.get("target", link.get("to")))
            if not s or not t or s == t:
                continue
            rel = link.get("relation") or link.get("label") or link.get("type") or "related"
            weight = link.get("weight", 1.0)
            try:
                weight = float(weight)
            except (TypeError, ValueError):
                weight = 1.0
            self.adjacency[s][t].append({"relation": rel, "weight": weight})
            # Undirected traversal: a connection is a connection.
            self.adjacency[t][s].append({"relation": rel, "weight": weight})

        if not self.nodes:
            self.reason = "graph has no nodes"
            return False
        if not links:
            self.reason = "graph has no relationships (run a semantic extract, not `update`)"
            return False

        self.loaded = True
        return True

    # -- queries -------------------------------------------------------
    @property
    def edge_count(self) -> int:
        return sum(len(v) for targets in self.adjacency.values() for v in targets.values())

    def find_seeds(self, query: str, limit: int = 8) -> List[Tuple[str, float]]:
        """
        Score nodes by lexical overlap with the query.

        A cheap, deterministic match -- deliberately no LLM call, because this
        runs on every query. A seed is a plausible entry point; PPR then does
        the real ranking.
        """
        terms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) > 2]
        if not terms:
            return []

        seeds: List[Tuple[str, float]] = []
        for node in self.nodes:
            label = self._node_label(node).lower()
            if not label:
                continue
            score = 0.0
            for t in terms:
                if t == label:
                    score += 3.0
                elif t in label:
                    score += 1.5
            if score > 0:
                seeds.append((self._node_label(node), score))
        seeds.sort(key=lambda x: -x[1])
        return seeds[:limit]

    def personalized_pagerank(
        self,
        seeds: Iterable[Tuple[str, float]],
        damping: float = 0.85,
        iterations: int = 30,
        relations: Optional[Set[str]] = None,
    ) -> Dict[str, float]:
        """
        Personalized PageRank seeded by the matched nodes.

        This is the HippoRAG-style read: similarity picks the entry point, graph
        diffusion finds what is connected to it. Pure standard library, so it
        adds no dependency and cannot fail on an absent service.
        """
        if not self.loaded or not seeds:
            return {}

        seed_scores: Dict[str, float] = defaultdict(float)
        for label, score in seeds:
            seed_scores[label] += score
        total = sum(seed_scores.values()) or 1.0
        current = {k: v / total for k, v in seed_scores.items()}

        # Restrict the walk to nodes that actually have relationships.
        active: Set[str] = set()
        for src, targets in self.adjacency.items():
            active.add(src)
            active.update(targets)

        # The seed distribution is held fixed across iterations. Reinjecting a
        # fraction of the *current* (renormalized) distribution instead let the
        # walk drift, and treating a dangling node as keeping 100% of its rank
        # meant a seed with no eligible edges outranked everything it pointed
        # at. Standard Personalized PageRank: teleport back to the seeds.
        for _ in range(iterations):
            nxt: Dict[str, float] = defaultdict(float)

            for node, rank in current.items():
                if node not in active:
                    continue
                targets = self.adjacency.get(node, {})
                edges = [
                    (t, e)
                    for t, elist in targets.items()
                    for e in elist
                    if relations is None or e["relation"] in relations
                ]
                if not edges:
                    # Dangling under this filter: its rank does not propagate
                    # along edges, but the teleport term below brings it back.
                    continue
                weight_sum = sum(e["weight"] for _, e in edges) or 1.0
                for t, e in edges:
                    nxt[t] += rank * damping * (e["weight"] / weight_sum)

            # Teleport: (1 - damping) back to the fixed seed distribution.
            for node, frac in seed_scores.items():
                nxt[node] += (1.0 - damping) * (frac / total)

            norm = sum(nxt.values()) or 1.0
            current = {k: v / norm for k, v in nxt.items() if v > 0}

        return {k: v for k, v in current.items() if v > 0}

    def paths_from(
        self,
        node: str,
        depth: int = 1,
        relations: Optional[Set[str]] = None,
    ) -> List[Tuple[str, List[str], int]]:
        """
        Breadth-first expansion returning the *actual path* to each node.

        Returns [(neighbor, [seed, "--rel-->", ..., neighbor], hops)].

        This previously returned a flat (neighbor, relation) pair, which made a
        node two hops away indistinguishable from one that was adjacent -- the
        hop count was therefore always 1 no matter what depth was requested.
        The connecting path is the useful output anyway: it is what lets a
        caller explain why a document surfaced.
        """
        seen: Set[str] = {node}
        out: List[Tuple[str, List[str], int]] = []
        queue: deque = deque([(node, [node], 0)])
        while queue:
            cur, path, d = queue.popleft()
            if d >= depth:
                continue
            for t, elist in self.adjacency.get(cur, {}).items():
                for e in elist:
                    if relations is not None and e["relation"] not in relations:
                        continue
                    if t in seen:
                        continue
                    seen.add(t)
                    new_path = path + [f"--{e['relation']}-->", t]
                    out.append((t, new_path, d + 1))
                    queue.append((t, new_path, d + 1))
        return out


# ── Public API ──────────────────────────────────────────────────────────

def load_graphs(sources: Optional[List[str]] = None) -> Tuple[Dict[str, Graph], List[str]]:
    """Load the requested graphs. Returns (graphs, notes-for-the-caller)."""
    wanted = sources or list(GRAPH_SOURCES)
    graphs: Dict[str, Graph] = {}
    notes: List[str] = []
    for name in wanted:
        path = GRAPH_SOURCES.get(name)
        if path is None:
            notes.append(f"{name}: unknown source")
            continue
        g = Graph(name, path)
        if g.load():
            graphs[name] = g
        else:
            notes.append(f"{name}: unavailable — {g.reason}")
            # A graph that fails to load used to be invisible: the caller got an
            # empty result set that looked identical to a genuine "no matches".
            # Warn on stderr so a misconfigured path or a gutted graph is
            # obvious in cron logs instead of silently degrading quality.
            print(f"[graph_retrieval] WARNING: {name} unavailable — {g.reason}",
                  file=sys.stderr)
    if not graphs:
        print("[graph_retrieval] ERROR: no graph could be loaded from any source; "
              f"tried: {', '.join(str(GRAPH_SOURCES.get(n)) for n in wanted)}",
              file=sys.stderr)
    return graphs, notes


def multi_hop_search(
    query: str,
    sources: Optional[List[str]] = None,
    top_k: int = 10,
    depth: int = 2,
    relations: Optional[Set[str]] = None,
) -> Dict:
    """
    Find documents connected to a query through the knowledge graph.

    Returns a dict with `results` (each carrying the path that connected it, so
    a result is explainable rather than a bare score) and `notes` explaining any
    graph that could not be used. Never raises.
    """
    graphs, notes = load_graphs(sources)
    results: List[dict] = []
    seen_files: Set[str] = set()

    for name, g in graphs.items():
        seeds = g.find_seeds(query)
        if not seeds:
            notes.append(f"{name}: no node matched the query terms")
            continue

        seed_labels = [s for s, _ in seeds]
        ranks = g.personalized_pagerank(seeds, relations=relations)

        # Record the shortest relation path from any seed, so the caller can say
        # *why* a document surfaced and how far away it was.
        provenance: Dict[str, List[str]] = {}
        hop_counts: Dict[str, int] = {}
        # Keep the SHORTEST connecting path per node: BFS visits in hop order,
        # so setdefault records the first (shortest) path seen.
        for seed in seed_labels:
            for t, path, hops in g.paths_from(seed, depth=depth, relations=relations):
                if t not in provenance:
                    provenance[t] = path
                hop_counts[t] = min(hop_counts.get(t, hops), hops)

        for node, score in sorted(ranks.items(), key=lambda x: -x[1])[: top_k * 3]:
            if node in seed_labels:
                continue
            src_file = g.node_files.get(node)
            if not src_file:
                continue
            if src_file in seen_files:
                continue
            seen_files.add(src_file)
            path = provenance.get(node)
            results.append({
                "source": name,
                "node": node,
                "file": src_file,
                "ppr_score": round(score, 6),
                "path": " ".join(path) if path else None,
                "hops": hop_counts.get(node, 0),
            })
            if len(results) >= top_k:
                break

    results.sort(key=lambda r: -r["ppr_score"])
    return {
        "query": query,
        "results": results[:top_k],
        "notes": notes,
        "graphs_consulted": {n: {"nodes": len(g.nodes), "relationships": g.edge_count}
                             for n, g in graphs.items()},
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Multi-hop relational search over the Graphify graphs",
    )
    ap.add_argument("query", help="Natural-language or concept query")
    ap.add_argument("--source", action="append", choices=list(GRAPH_SOURCES),
                    help="Restrict to a source (repeatable)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--depth", type=int, default=2, help="Traversal depth (default: 2)")
    ap.add_argument("--relation", action="append",
                    help="Only follow this relation type (repeatable)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    out = multi_hop_search(
        args.query,
        sources=args.source,
        top_k=args.top,
        depth=args.depth,
        relations=set(args.relation) if args.relation else None,
    )

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"graph_retrieval — multi-hop search")
        print(f"  Query: {args.query}")
        for name, stats in out["graphs_consulted"].items():
            print(f"  Graph '{name}': {stats['nodes']:,} nodes, "
                  f"{stats['relationships']:,} relationships")
        for n in out["notes"]:
            print(f"  [note] {n}")
        if not out["results"]:
            print("\n  No graph-linked documents found.")
            print("  This is not an error: the graph may not cover these terms,")
            print("  or the nodes carry no source-file provenance. Fall back to")
            print("  scripts/brain_query.py for lexical and vector search.")
            return 0
        print(f"\nTop {len(out['results'])} graph-linked results:\n")
        for i, r in enumerate(out["results"], 1):
            hops = f"{r['hops']}-hop" if r["hops"] else "seed"
            print(f"{i}. [{r['source']}] {r['node']}  ({hops}, ppr={r['ppr_score']:.5f})")
            print(f"   File: {r['file']}")
            if r["path"]:
                print(f"   Via:  {r['path']}")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
