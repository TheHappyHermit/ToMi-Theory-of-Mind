#!/usr/bin/env python3
"""Verify a graphify graph.json is trustworthy, or say plainly why it might not be.

Motivation
----------
graphify issue #3776 (OPEN): a graph maintained with `--update` silently loses
cross-file edges that a clean build produces. `--force` does not repair it; only
deleting the output directory and rebuilding does. The loss leaves no trace in
`graph.json`, so a consumer cannot detect it by inspecting the graph.

Issue #3105 (fixed in v0.9.51): hollow LLM responses were not counted as
incomplete, so a run could write 111 nodes over an existing 570-node graph with
exit code 0 and no warning.

Neither failure is visible by counting nodes or links. A degraded graph looks
structurally perfect. This script therefore checks the things that *do* discriminate
between a trustworthy graph and a silently drifted one:

  1. Provenance      - is `built_at_commit` present and does the corpus HEAD match?
  2. Freshness       - how stale is the graph relative to its source files?
  3. Completeness    - do source files exist that contributed no nodes at all?
  4. Integrity       - do all link endpoints resolve to real nodes?
  5. Density         - is the edge:node ratio plausible for this corpus?
  6. Incremental risk- is there evidence this graph was maintained incrementally?

Exit codes
----------
  0  no problems found
  1  problems found (graph should not be trusted as-is)
  2  bad usage / unreadable graph

This is a *detector*, not a repair tool. When it fails, the fix is a clean rebuild,
not a patch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


class Finding:
    __slots__ = ("severity", "check", "message", "detail")

    def __init__(self, severity: str, check: str, message: str, detail: str = ""):
        self.severity = severity
        self.check = check
        self.message = message
        self.detail = detail

    def __str__(self) -> str:
        base = f"[{self.severity.upper():<7}] {self.check}: {self.message}"
        return f"{base}\n            {self.detail}" if self.detail else base


def load_graph(path: Path) -> Optional[dict]:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ValueError(f"graph.json is not valid JSON: {exc}")


def corpus_files(vault: Path) -> List[Path]:
    """Markdown files that should be represented in the graph."""
    skip = {"graphify-out", ".git", "node_modules", ".obsidian", ".trash"}
    out = []
    for p in vault.rglob("*.md"):
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return out


def git_head(repo: Path) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


def check_provenance(graph: dict, vault: Path) -> List[Finding]:
    out: List[Finding] = []
    built = graph.get("built_at_commit")
    if not built:
        out.append(
            Finding(
                "error",
                "provenance",
                "graph.json has no built_at_commit",
                "Without build provenance a drifted graph is indistinguishable from a "
                "current one (graphify #3354). Rebuild to stamp it.",
            )
        )
        return out

    head = git_head(vault)
    if head and head != built:
        out.append(
            Finding(
                "warning",
                "provenance",
                f"graph was built at {str(built)[:12]}, corpus HEAD is {head[:12]}",
                "Normal after new commits. Expected if the refresh cron has not run; "
                "a problem only if the graph is treated as current.",
            )
        )
    return out


def check_freshness(graph: Path, vault: Path) -> List[Finding]:
    out: List[Finding] = []
    try:
        graph_mtime = graph.stat().st_mtime
    except OSError:
        return out
    newest_source, newest_path = 0.0, None
    for f in corpus_files(vault):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if m > newest_source:
            newest_source, newest_path = m, f

    if newest_source <= graph_mtime:
        return out

    import datetime as _dt

    age_h = (newest_source - graph_mtime) / 3600.0
    name = newest_path.name if newest_path else "?"
    sev = "error" if age_h > 24 * 30 else "warning"
    out.append(
        Finding(
            sev,
            "freshness",
            f"source files are newer than the graph by {age_h:.1f} h",
            f"Newest source: {name}. The graph does not reflect the corpus on disk.",
        )
    )
    return out


def check_completeness(graph: dict, vault: Path, graph_path: Path) -> List[Finding]:
    """Files that existed when the graph was built but contributed zero nodes.

    This is the check that would have caught #3105: ten of twenty-four files
    contributed nothing and the run still reported success.

    The staleness split matters. A file newer than the graph is simply not indexed
    yet, which is normal. A file OLDER than the graph that contributed nothing was
    present during extraction and was silently dropped -- that is a genuine gap.
    """
    out: List[Finding] = []
    represented = {
        n.get("source_file")
        for n in graph.get("nodes", [])
        if isinstance(n, dict) and n.get("source_file")
    }
    if not represented:
        return out

    try:
        built_at = graph_path.stat().st_mtime
    except OSError:
        built_at = 0.0

    rep_norm = {str(s).lstrip("./") for s in represented}
    rep_base = {Path(s).name for s in rep_norm}
    files = corpus_files(vault)

    absent = []
    for f in files:
        rel = f.relative_to(vault).as_posix()
        if rel in rep_norm or f.name in rep_base:
            continue
        if any(s.endswith("/" + rel) or s.endswith(rel) for s in rep_norm):
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            mtime = 0.0
        absent.append((rel, mtime))

    if not absent:
        return out

    stale = [rel for rel, m in absent if m >= built_at]          # not indexed yet
    gaps = [rel for rel, m in absent if built_at and m < built_at]  # should be present

    if gaps:
        pct = len(gaps) / len(files) * 100
        sev = "error" if pct > 5 else "warning"
        out.append(
            Finding(
                sev,
                "completeness",
                f"{len(gaps)} of {len(files)} source files ({pct:.1f}%) existed at build "
                f"time but contributed no nodes",
                "Examples: "
                + ", ".join(gaps[:5])
                + ("..." if len(gaps) > 5 else "")
                + "\n            These files predate the graph build, so extraction saw "
                "them and produced nothing. This is the #3105 signature. A clean "
                "rebuild is the fix -- --update will not repair it.",
            )
        )
    if stale:
        out.append(
            Finding(
                "info",
                "completeness",
                f"{len(stale)} source file(s) are newer than the graph",
                "Not indexed yet. Expected when the refresh job has not caught up.",
            )
        )
    return out


def check_integrity(graph: dict) -> List[Finding]:
    out: List[Finding] = []
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    dangling = [
        l
        for l in links
        if l.get("source") not in ids or l.get("target") not in ids
    ]
    if dangling:
        out.append(
            Finding(
                "error",
                "integrity",
                f"{len(dangling)} of {len(links)} links have an unresolvable endpoint",
                f"{len(dangling) / max(1, len(links)) * 100:.2f}% of edges. "
                "The graph is structurally inconsistent.",
            )
        )

    empties = sum(1 for n in nodes if not str(n.get("label", "")).strip())
    if empties:
        out.append(
            Finding(
                "error",
                "integrity",
                f"{empties} nodes have an empty label",
                "Empty labels usually indicate a truncated or failed extraction.",
            )
        )
    return out


def check_density(graph: dict) -> List[Finding]:
    out: List[Finding] = []
    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))
    if not nodes:
        out.append(Finding("error", "density", "graph contains no nodes", ""))
        return out
    ratio = len(links) / len(nodes)
    if ratio < 0.25:
        out.append(
            Finding(
                "warning",
                "density",
                f"edge:node ratio is {ratio:.2f}",
                "Low density for a concept graph. A degraded or partially-extracted "
                "graph can look exactly like this. Compare against a clean rebuild "
                "before trusting it.",
            )
        )
    return out


def check_incremental_risk(graph: dict) -> List[Finding]:
    """The #3776 warning: this check cannot prove a graph is correct.

    Always emitted as info when a graph looks usable, because the known open bug
    produces no detectable signal.
    """
    return [
        Finding(
            "info",
            "incremental-risk",
            "incremental-update edge loss is undetectable from graph.json (graphify #3776)",
            "If this graph has ever been maintained with `graphify --update`, it may be "
            "missing cross-file edges that a clean build would produce. No check here "
            "can detect that. Periodic clean rebuilds are the only defence.",
        )
    ]


def verify(graph_path: Path, vault: Optional[Path]) -> Tuple[int, List[Finding], dict]:
    graph = load_graph(graph_path)
    if graph is None:
        print(f"error: no graph at {graph_path}", file=sys.stderr)
        return 2, [], {}

    findings: List[Finding] = []
    findings += check_provenance(graph, vault) if vault else []
    findings += check_freshness(graph_path, vault) if vault else []
    if vault:
        findings += check_completeness(graph, vault, graph_path)
    findings += check_integrity(graph)
    findings += check_density(graph)
    findings += check_incremental_risk(graph)

    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    return (1 if errors or warnings else 0), findings, graph


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Verify a graphify graph is trustworthy (see graphify #3105, #3776)"
    )
    ap.add_argument("graph_json", help="path to graphify-out/graph.json")
    ap.add_argument(
        "--vault",
        default=None,
        help="corpus root the graph was built from; enables provenance, freshness "
        "and completeness checks",
    )
    ap.add_argument("--quiet", action="store_true", help="suppress the info finding")
    args = ap.parse_args(argv)

    graph_path = Path(args.graph_json).expanduser()
    if not graph_path.exists():
        print(f"error: no such file: {graph_path}", file=sys.stderr)
        return 2

    vault = Path(args.vault).expanduser() if args.vault else None
    if vault and not vault.is_dir():
        print(f"error: vault is not a directory: {vault}", file=sys.stderr)
        return 2

    try:
        code, findings, graph = verify(graph_path, vault)
    except ValueError as exc:
        # load_graph raises ValueError for malformed JSON; main must handle it
        # rather than surfacing a traceback to the caller.
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.quiet:
        findings = [f for f in findings if f.severity != "info"]

    nodes = len(graph.get("nodes", []))
    links = len(graph.get("links", graph.get("edges", [])))
    print(f"graph: {graph_path}")
    print(f"       {nodes:,} nodes, {links:,} relationships")
    if vault:
        print(f"corpus: {vault}")
    print()

    for f in findings:
        print(f"  {f}")
    print()

    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    if code == 0:
        print("VERDICT: no structural problems detected.")
    else:
        print(
            f"VERDICT: {errors} error(s), {warnings} warning(s). "
            f"Do not trust this graph without a clean rebuild."
        )
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
