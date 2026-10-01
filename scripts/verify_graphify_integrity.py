#!/usr/bin/env python3
"""
verify_graphify_integrity.py — Graphify graph integrity verification.

Checks graph.json and analysis files for structural integrity.
Supports both Oracle and Main graphify outputs.

Usage:
    python3 verify_graphify_integrity.py [--oracle | --main]

Defaults to --oracle if neither flag is given.
"""
import json
import os
import sys
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────
ORACLE_GRAPH = str(Path(os.path.expanduser("~/.hermes/oracle/brain/graphify-out/graph.json")))
ORACLE_ANALYSIS = str(Path(os.path.expanduser("~/.hermes/oracle/brain/graphify-out/.graphify_analysis.json")))
MAIN_GRAPH = str(Path(os.path.expanduser("~/.hermes/graphify-main-out/graphify-out/graph.json")))


def verify_graph(graph_path, analysis_path=None, label='graph'):
    """Verify a single graphify graph.json file."""
    if not os.path.exists(graph_path):
        print(f"[SKIP] {graph_path} does not exist")
        return False

    ok = True

    # Load graph
    with open(graph_path) as f:
        g = json.load(f)

    nodes = g.get('nodes', [])
    links = g.get('links', [])
    hyperedges = g.get('hyperedges', [])

    print(f"\n{'='*60}")
    print(f"{label} — Integrity Report")
    print(f"{'='*60}")
    print(f"Nodes: {len(nodes)}")
    print(f"Links: {len(links)}")
    print(f"Hyperedges: {len(hyperedges)}")
    print(f"Directed: {g.get('directed')}")
    print(f"Multigraph: {g.get('multigraph')}")
    print(f"built_at_commit: {g.get('built_at_commit')}")

    # Verify node structure
    bad_nodes = [n for n in nodes if 'id' not in n]
    if bad_nodes:
        print(f"WARNING: {len(bad_nodes)} nodes missing 'id'")
        ok = False
    else:
        print(f"All {len(nodes)} nodes have 'id' — OK")

    # Verify link structure
    bad_links = [l for l in links if 'source' not in l or 'target' not in l]
    if bad_links:
        print(f"WARNING: {len(bad_links)} links missing 'source' or 'target'")
        ok = False
    else:
        print(f"All {len(links)} links have 'source' and 'target' — OK")

    # Verify no duplicate nodes
    node_ids = [n['id'] for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        dups = len(node_ids) - len(set(node_ids))
        print(f"WARNING: {dups} duplicate node IDs")
        ok = False
    else:
        print(f"No duplicate node IDs — OK")

    # Verify no duplicate links
    link_set = set()
    dup_links = 0
    for l in links:
        key = (l['source'], l['target'])
        if key in link_set:
            dup_links += 1
        link_set.add(key)
    if dup_links:
        print(f"WARNING: {dup_links} duplicate links")
        ok = False
    else:
        print(f"No duplicate links — OK")

    # Verify community assignments
    if analysis_path and os.path.exists(analysis_path):
        with open(analysis_path) as f:
            a = json.load(f)
        comm_key = 'communities' if 'communities' in a else 'community'
        comm_val = a.get(comm_key, {})
        if isinstance(comm_val, dict):
            comm_count = len(comm_val)
            assigned = sum(len(v) for v in comm_val.values())
            print(f"Communities: {comm_count} groups, {assigned} total assigned nodes")
            if assigned != len(nodes):
                print(f"WARNING: {assigned} nodes assigned but {len(nodes)} total nodes")
                ok = False
            else:
                print(f"All {assigned} nodes assigned to communities — OK")
        else:
            print(f"Communities format: {type(comm_val).__name__} with {len(comm_val)} items")
    else:
        print("No analysis file found — skipping community check")

    # File size
    sz = os.path.getsize(graph_path)
    print(f"File size: {sz:,} bytes ({sz/1024/1024:.1f} MB)")

    # JSON round-trip
    try:
        raw = open(graph_path).read()
        json.loads(raw)
        print("Valid JSON — OK")
    except json.JSONDecodeError as e:
        print(f"WARNING: Invalid JSON — {e}")
        ok = False

    # Note: grep-based cross-checks removed — node objects can contain
    # fields like 'source' that cause false positives. JSON parsing is
    # authoritative; grep is unreliable for this check.

    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
    return ok


def main():
    mode = 'oracle'
    if '--main' in sys.argv:
        mode = 'main'
    elif '--oracle' in sys.argv:
        mode = 'oracle'

    if mode == 'oracle':
        graph = ORACLE_GRAPH
        analysis = ORACLE_ANALYSIS
        label = 'Oracle Graph'
    else:
        graph = MAIN_GRAPH
        analysis = None  # Main graph analysis not reliably located
        label = 'Main Graph'

    ok = verify_graph(graph, analysis, label)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
