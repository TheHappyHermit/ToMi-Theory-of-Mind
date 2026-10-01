#!/usr/bin/env python3
"""Health check for the two Graphify graphs.

Reports whether each graph is present, parseable, and non-empty, and
cross-checks the manifest entry count against the graph node count.

Two rules this file exists to enforce:

1. A missing file is MISSING, not a pass. Anything unreadable reports as a
   failure rather than being folded into a default of zero.
2. The manifest/graph cross-check must never pass on empty input. If both
   sides read zero because nothing was loaded, that is a broken check, not a
   match -- it previously printed a green tick next to two MISSING graphs.

Paths resolve under HERMES_DATA_DIR, defaulting to ~/.hermes.
"""
import json
import os
import sys
from pathlib import Path

GRAPHS = [
    ("Active Wiki", "active-wiki/graphify-out"),
    ("Oracle Brain", "oracle/brain/graphify-out"),
]


def analyze_graph(directory):
    """Return node/hyperedge counts, or an error string. Never a silent zero."""
    path = directory / "graph.json"
    if not path.exists():
        return {"error": f"graph.json not found at {path}"}
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"graph.json is not valid JSON: {e}"}
    except OSError as e:
        return {"error": f"graph.json unreadable: {e}"}

    graph = data.get("graph")
    if graph is None:
        return {"error": "graph.json has no top-level 'graph' object"}

    hyperedges = graph.get("hyperedges", [])
    nodes = set()
    for edge in hyperedges:
        nodes.update(edge.get("nodes", []))

    if not nodes:
        return {"error": f"graph.json parsed but contains 0 nodes ({path.stat().st_size} bytes)"}

    return {
        "size": path.stat().st_size,
        "size_mb": f"{path.stat().st_size / 1024 / 1024:.2f} MB",
        "nodes": len(nodes),
        "hyperedges": len(hyperedges),
        "sample": sorted(nodes)[:3],
    }


def analyze_manifest(directory):
    path = directory / "manifest.json"
    if not path.exists():
        return {"error": f"manifest.json not found at {path}"}
    try:
        with open(path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"manifest.json is not valid JSON: {e}"}
    except OSError as e:
        return {"error": f"manifest.json unreadable: {e}"}

    if not isinstance(manifest, dict) or not manifest:
        return {"error": "manifest.json is empty or not an object"}
    return {"count": len(manifest), "sample": list(manifest)[:3]}


def verdict(graph, manifest):
    """HEALTHY / DEGRADED / MISSING, decided on what actually loaded."""
    if "error" in graph:
        return "MISSING"
    if "error" in manifest:
        return "DEGRADED"
    return "HEALTHY"


def main():
    # Resolve the root once, here, rather than baking it into GRAPHS at import
    # time. Resolving at import meant a caller could not retarget the check
    # without reloading the module, and the failure paths were untestable.
    root = Path(os.environ.get("HERMES_DATA_DIR", Path.home() / ".hermes"))
    results = []
    for name, relative in GRAPHS:
        directory = root / relative
        results.append((name, directory, analyze_graph(directory),
                        analyze_manifest(directory)))

    print("=" * 70)
    print("GRAPHIFY GRAPH STATUS")
    print(f"root: {root}")
    print("=" * 70)

    for name, directory, graph, manifest in results:
        print(f"\n{name}  ({directory})")
        if "error" in graph:
            print(f"  FAIL  {graph['error']}")
        else:
            print(f"  ok    {graph['size_mb']}  {graph['nodes']} nodes  "
                  f"{graph['hyperedges']} hyperedges")
            print(f"        sample: {graph['sample']}")
        if "error" in manifest:
            print(f"  FAIL  {manifest['error']}")
        else:
            print(f"  ok    manifest lists {manifest['count']} entries")
        print(f"  VERDICT: {verdict(graph, manifest)}")

    print("\n" + "=" * 70)
    print("CROSS-CHECK: manifest entries vs graph nodes")
    print("=" * 70)
    for name, _directory, graph, manifest in results:
        if "error" in graph or "error" in manifest:
            print(f"  ?  {name}: not comparable -- at least one input failed to load")
            continue
        expected, actual = manifest["count"], graph["nodes"]
        if expected == 0 or actual == 0:
            # The old bug. Both zero meant both files were missing.
            print(f"  FAIL  {name}: both sides are zero -- inputs did not load")
        elif expected == actual:
            print(f"  ok   {name}: {expected} == {actual}")
        else:
            print(f"  WARN {name}: manifest {expected} != graph {actual} "
                  f"(diff {actual - expected})")

    overall = [verdict(g, m) for _n, _d, g, m in results]
    failed = [n for n, _d, g, m in results if "error" in g]
    print("\n" + "=" * 70)
    print("OVERALL")
    print("=" * 70)
    for (name, _d, g, _m), v in zip(results, overall):
        print(f"  {name:14s} {v}")
    if failed:
        print(f"\n  {len(failed)} graph(s) unreadable: {', '.join(failed)}")
        return 1
    if "DEGRADED" in overall:
        print("\n  All graphs readable; at least one manifest is missing.")
        return 1
    print("\n  All graphs readable and non-empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
