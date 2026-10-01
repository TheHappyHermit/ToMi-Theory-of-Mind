#!/usr/bin/env python3
"""
graphify_health.py — Report the health of the Graphify knowledge graphs.

Checks the Active Wiki graph and the Oracle Brain graph for the condition that
actually matters for relationship queries: **edges**.

Why edges and not nodes
-----------------------
A graph with nodes but no edges is a list, not a graph. Nodes alone can be
searched by name; without edges there are no paths to traverse, so every
multi-hop question ("what connects X to Y?") has nothing to walk. This is the
exact failure documented in docs/references/graphify-refresh-pitfall.md, where
`graphify update` performs AST-only extraction suitable for code repos and
produces 0-edge graphs over markdown wikis.

The previous version of this script:
  * used a literal unexpanded '$HOME/...' string, so it read a path named
    "$HOME" that does not exist and raised FileNotFoundError on every run;
  * judged health on `links`, a key graphify does not emit, so it always
    reported 0 links and therefore always said NEEDS ATTENTION even for a
    healthy graph;
  * crashed rather than reported when a graph was absent.

Exit status: 0 if both graphs have edges, 1 if either is missing or edgeless.
This makes it usable as a cron canary rather than a human-only eyeball.
"""

import json
import os
import sys
from pathlib import Path


def resolve_hermes_data_dir() -> Path:
    """Honour the same env precedence as scripts/_paths.py."""
    for var in ("HERMES_DATA_DIR", "HERMES_HOME", "CORTEX_HOME"):
        val = os.environ.get(var, "").strip()
        if val:
            return Path(val).expanduser().resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win.exists():
            return win
    return (Path.home() / ".hermes").resolve()


DATA_DIR = resolve_hermes_data_dir()
ACTIVE_WIKI = Path(os.environ.get("ACTIVE_WIKI_PATH", str(DATA_DIR / "active-wiki")))
ORACLE_BRAIN = Path(os.environ.get("ORACLE_BRAIN_PATH", str(DATA_DIR / "oracle" / "brain")))

GRAPHS = [
    ("Active Wiki", ACTIVE_WIKI / "graphify-out" / "graph.json"),
    ("Oracle Brain", ORACLE_BRAIN / "graphify-out" / "graph.json"),
]


def count_graph(path: Path):
    """Return (nodes, edges) or raise."""
    with open(path, encoding="utf-8") as f:
        g = json.load(f)
    nodes = g.get("nodes", []) or []
    # graphify emits 'edges'; some exports carry 'links' instead. Accept both
    # rather than reading a key that is not there.
    edges = g.get("edges") or g.get("links") or []
    communities = g.get("communities") or {}
    return len(nodes), len(edges), len(communities)


def verdict(nodes: int, edges: int):
    if edges == 0:
        return "EDGELESS", "no relationships extractable — run a full semantic extract, see docs/references/graphify-refresh-pitfall.md"
    if nodes == 0:
        return "EMPTY", "no nodes found"
    ratio = edges / nodes if nodes else 0.0
    if ratio < 0.1:
        return "THIN", f"edge-to-node ratio {ratio:.3f} is below the 0.1 floor for a usable wiki graph"
    return "HEALTHY", f"edge-to-node ratio {ratio:.3f}"


def main() -> int:
    print(f"graphify_health: data dir = {DATA_DIR}")
    failures = 0

    for label, path in GRAPHS:
        if not path.exists():
            print(f"\n{label}: MISSING — no graph at {path}")
            print("    Nothing to query. Run a full semantic extract to build one.")
            failures += 1
            continue

        try:
            nodes, edges, communities = count_graph(path)
        except (OSError, json.JSONDecodeError) as e:
            print(f"\n{label}: UNREADABLE — {path}: {e}")
            failures += 1
            continue

        state, detail = verdict(nodes, edges)
        if state != "HEALTHY":
            failures += 1
        print(f"\n{label}: nodes={nodes} edges={edges} communities={communities}")
        print(f"    {state}: {detail}")

    if failures:
        print(f"\n{failures} of {len(GRAPHS)} graph(s) need attention.")
        return 1

    print(f"\nAll {len(GRAPHS)} graphs have edges and are traversable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
