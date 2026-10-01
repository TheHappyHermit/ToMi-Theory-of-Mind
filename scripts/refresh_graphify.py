#!/usr/bin/env python3
"""
Graphify refresh for Active Wiki and Oracle Brain.

Runs a full `graphify extract` on the active-wiki and oracle-brain directories.
Uses local llama.cpp server for semantic extraction.
Scheduled: Sundays at 4:00 AM via cron job "Graphify Refresh"

Why extract and not update:
  `graphify update` performs STRUCTURAL extraction only (free, deterministic,
  code-only) and never calls the LLM. For a Markdown/wiki corpus that yields an
  empty graph. It destroyed the Active Wiki graph once already: 4,393 notes
  dropped to 68, and all connections dropped to 0. See
  ~/.hermes/oracle/brain/decisions/graphify-extract-not-update.md

Note: graphify extracts/writes to <source>/graphify-out/ by default when run
from within the source directory. The --graph flag (for graphify commands like
path, explain, etc.) defaults to graphify-out/graph.json in the CWD.
"""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

def _resolve_hermes_data_dir() -> Path:
    if os.environ.get("HERMES_DATA_DIR"):
        return Path(os.environ["HERMES_DATA_DIR"]).resolve()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).resolve()
    if os.environ.get("CORTEX_HOME"):
        return Path(os.environ["CORTEX_HOME"]).resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win_hermes.exists():
            return win_hermes
    default_hermes = Path.home() / ".hermes"
    if default_hermes.exists():
        return default_hermes
    legacy_hermes = Path.home() / ".hermes"
    if legacy_hermes.exists():
        return legacy_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return default_hermes

HERMES_DATA_DIR = _resolve_hermes_data_dir()
ACTIVE_WIKI = Path(os.environ.get("ACTIVE_WIKI_PATH", str(HERMES_DATA_DIR / "active-wiki")))
ORACLE_BRAIN = Path(os.environ.get("ORACLE_BRAIN_PATH", str(HERMES_DATA_DIR / "oracle" / "brain")))
# graph.json is written in-place at <source>/graphify-out/graph.json
MAIN_GRAPH_FILE = ACTIVE_WIKI / "graphify-out" / "graph.json"
ORACLE_GRAPH_FILE = ORACLE_BRAIN / "graphify-out" / "graph.json"

def refresh_graph(name, source, graph_file):
    """Refresh a single graph using graphify extract (full semantic re-extract)."""
    if not source.exists() or not any(source.iterdir()):
        print(f"[graphify-refresh] {name}: source empty, skipping")
        return True

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", "sk-local")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL", "")
    if not base_url:
        node = os.getenv("INFERENCE_NODE_MAIN", "localhost")
        base_url = f"http://{node}:8080/v1" if not node.startswith("http") else f"{node}:8080/v1"
    env["OPENAI_BASE_URL"] = base_url
    env["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "/models/Qwen3.5-4B-UD-Q4_K_XL.gguf")
    env["GRAPHIFY_DISABLE_THINKING"] = "1"
    env["GRAPHIFY_MAX_OUTPUT_TOKENS"] = "98304"

    # Back up the current graph before touching it, and remember its size so we
    # can detect a collapse afterwards. graphify can silently gut a graph
    # (upstream #3776 leaves no trace in graph.json), so we never overwrite the
    # only good copy without a rollback path.
    prev_total = None
    backup = graph_file.with_suffix(".json.pre-refresh.bak")
    if graph_file.exists():
        try:
            shutil.copy2(graph_file, backup)
        except Exception as e:
            print(f"[graphify-refresh] {name}: WARNING could not back up graph: {e}",
                  file=sys.stderr)

    if not graph_file.exists():
        print(f"[graphify-refresh] {name}: graph.json not found at {graph_file}, running initial extract")
        cmd = ["graphify", "extract", str(source), "--max-concurrency", "1", "--api-timeout", "600"]
    else:
        with open(graph_file) as f:
            data = json.load(f)
        nodes = data.get("nodes", [])
        edges = data.get("links", []) or data.get("edges", [])
        prev_total = len(nodes) + len(edges)
        print(f"[graphify-refresh] {name}: current graph: {len(nodes)} nodes, {len(edges)} edges")
        # DO NOT use `graphify update` for Markdown/wiki corpora.
        # Per decisions/graphify-extract-not-update.md (2026-09-10): `update` only
        # performs STRUCTURAL extraction (free/deterministic, code-only) and never
        # calls the LLM, so for a notes corpus it produces an empty graph. It
        # destroyed the Active Wiki graph: 4,393 notes -> 68, connections -> 0.
        # `extract` re-extracts meaning and rebuilds the graph correctly.
        cmd = ["graphify", "extract", str(source), "--max-concurrency", "1", "--api-timeout", "600"]

    print(f"[graphify-refresh] {name}: command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(source),
        env=env, timeout=3600
    )

    for line in (result.stdout or "").splitlines():
        print(f"[graphify-refresh] {name}: {line}")
    if result.stderr:
        for line in (result.stderr).splitlines():
            print(f"[graphify-refresh] {name}: STDERR: {line}", file=sys.stderr)

    if result.returncode == 0 and graph_file.exists():
        with open(graph_file) as f:
            data = json.load(f)
        nodes = data.get("nodes", [])
        edges = data.get("links", []) or data.get("edges", [])
        print(f"[graphify-refresh] {name}: SUCCESS: {len(nodes)} nodes, {len(edges)} edges")
        # COLLAPSE GUARD. A healthy graph that comes back with almost nothing
        # means the run silently destroyed it. Roll back to the backup instead
        # of leaving a gutted graph in place (see backup_graph above).
        if prev_total is not None and prev_total > 100:
            new_total = len(nodes) + len(edges)
            ratio = new_total / prev_total
            if ratio < 0.5:
                print(f"[graphify-refresh] {name}: !! COLLAPSE DETECTED — "
                      f"{prev_total} -> {new_total} ({ratio:.0%}). Restoring backup.")
                try:
                    shutil.copy2(backup, graph_file)
                    print(f"[graphify-refresh] {name}: backup restored to {graph_file}")
                except Exception as e:
                    print(f"[graphify-refresh] {name}: RESTORE FAILED: {e}", file=sys.stderr)
                return False
        return True
    else:
        print(f"[graphify-refresh] {name}: FAILED: exit {result.returncode}")
        return False

def main():
    print(f"[graphify-refresh] {datetime.now(timezone.utc).isoformat()}")

    if not ACTIVE_WIKI.exists():
        print(f"[graphify-refresh] ERROR: Active Wiki directory not found: {ACTIVE_WIKI}")
        sys.exit(1)

    success = True
    # Refresh Main Graph (from Active Wiki) — in-place at active-wiki/graphify-out/
    success &= refresh_graph("Main Graph", ACTIVE_WIKI, MAIN_GRAPH_FILE)
    # Refresh Oracle Graph (from Oracle Brain) — in-place at oracle/brain/graphify-out/
    success &= refresh_graph("Oracle Graph", ORACLE_BRAIN, ORACLE_GRAPH_FILE)

    if success:
        print("[graphify-refresh] ALL GRAPHS REFRESHED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("[graphify-refresh] ONE OR MORE GRAPHS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
