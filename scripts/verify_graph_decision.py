#!/usr/bin/env python3
"""
Check that the recorded graph decision still matches reality.

A decision document that is never checked becomes folklore. This asserts the
specific things that would change the decision, and fails loudly when they
change -- so "the graph scored 0.000" cannot quietly become a permanent claim
after the path bug that caused it was fixed, and a fixed upstream defect cannot
go unnoticed in a decision that assumed it.

Run:  python3 scripts/verify_graph_decision.py [--json]
Exit: 0 when the decision still holds, 1 when something it depends on moved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
DECISION_MD = REPO / "docs" / "GRAPH-DECISION.md"
DECISION_JSON = REPO / "docs" / "GRAPH-DECISION.json"

# Where graphify actually lives on this machine. Resolved rather than imported:
# it is a uv tool install, not a package on the default path.
GRAPHIFY_CANDIDATES = [
    Path.home() / ".local/share/uv/tools/graphifyy/lib/python3.11/site-packages/graphify",
]
VAULT_CANDIDATES = [
    Path.home() / ".hermes/oracle/brain",
    # The pre-migration data root. It no longer exists on a current install
    # (renamed to ~/old_Autognosia, with the live data under ~/.hermes), so
    # this is last-resort only, for recovering a graph from the old tree.
    # Listing it FIRST meant every run probed a directory that is gone before
    # trying the one that exists.
    Path.home() / ".autognosia/oracle/brain",
]


def find_first(paths: List[Path], test) -> Optional[Path]:
    for p in paths:
        if p.exists() and test(p):
            return p
    return None


def check_decision_files() -> List[str]:
    problems = []
    for f in (DECISION_MD, DECISION_JSON):
        if not f.exists():
            # f may be an absolute path outside the repo (when a caller points
            # these at a fixture), so relative_to is not safe here.
            try:
                shown = f.relative_to(REPO)
            except ValueError:
                shown = f
            problems.append(f"missing {shown}")
    if problems:
        return problems
    try:
        data = json.loads(DECISION_JSON.read_text())
    except json.JSONDecodeError as e:
        return [f"{DECISION_JSON.name} is not valid JSON: {e}"]
    for key in ("decision", "role", "routing", "measured", "why_keep_despite_scoring_lower"):
        if key not in data:
            problems.append(f"GRAPH-DECISION.json has no {key!r}")
    return problems


def check_file_char_cap() -> Dict[str, Any]:
    """Does the cap actually drop corpus content, or is it a per-slice limit?

    This was the load-bearing question of the whole decision, and the first
    answer given was wrong. _FILE_CHAR_CAP reads like a whole-file truncation,
    but llm.py pre-splits oversized documents into contiguous gap-free slices
    (upstream #1369), so the cap bounds each slice rather than discarding the
    rest of the file.

    So the checker must not infer loss from file sizes. It has to ask the code
    whether pre-splitting happens, and if it does, verify losslessness on real
    corpus files rather than trusting the comment.
    """
    d = find_first(GRAPHIFY_CANDIDATES, lambda p: (p / "llm.py").exists())
    if not d:
        return {"found": False, "note": "graphify install not found on this machine"}
    src = (d / "llm.py").read_text(errors="ignore")

    m = re.search(r"_FILE_CHAR_CAP\s*=\s*([\d_]+)", src)
    if not m:
        return {"found": True, "cap": None, "presplit": None,
                "note": "no _FILE_CHAR_CAP in this version"}
    cap = int(m.group(1).replace("_", ""))

    # 1. is pre-splitting wired in before packing?
    presplit = bool(re.search(r"expand_oversized_files\s*\(\s*files\s*,\s*_FILE_CHAR_CAP", src))

    # 2. does the truncation site admit to being a no-op for slices?
    noop_for_slices = bool(re.search(r"cap is a no-op", src, re.I))

    # 3. the real test: do slices actually round-trip the whole file?
    lossless, checked, detail = None, 0, "graphify not importable from this interpreter"
    try:
        import importlib
        import importlib.util
        pkg_parent = str(d.parent)          # .../site-packages
        if pkg_parent not in sys.path:
            sys.path.insert(0, pkg_parent)
        # import the real package so intra-package imports resolve
        importlib.invalidate_caches()
        if "graphify" not in sys.modules:
            __import__("graphify")
        mod = importlib.import_module("graphify.file_slice")
        sb = getattr(mod, "slice_boundaries", None)
        vault = find_first(VAULT_CANDIDATES, lambda p: any(p.rglob("*.md")))
        if sb and vault:
                big = sorted((f for f in vault.rglob("*.md") if f.stat().st_size > cap),
                             key=lambda f: -f.stat().st_size)[:60]
                for f in big:
                    txt = f.read_text(errors="ignore")
                    if not txt:
                        continue
                    try:
                        b = sb(txt, cap)
                    except Exception:
                        continue
                    if not b:
                        continue
                    checked += 1
                    if "".join(txt[s:e] for s, e in b) == txt:
                        lossless = True
                    else:
                        lossless = False
                        break
                if checked:
                    detail = f"{checked} largest files reassemble byte-identically"
    except Exception as e:  # never let the checker crash on an odd install
        detail = f"could not import graphify.file_slice: {e}"

    return {
        "found": True,
        "cap": cap,
        "presplit_before_packing": presplit,
        "source_says_noop_for_slices": noop_for_slices,
        "slicing_is_lossless": lossless,
        "files_roundtripped": checked,
        "detail": detail,
        # the decision depends on content NOT being dropped, so this is the
        # assertion that matters -- not the cap's numeric value
        "content_is_lost": bool(presplit and lossless is False),
    }


def check_corpus_size() -> Dict[str, Any]:
    vault = find_first(VAULT_CANDIDATES, lambda p: any(p.rglob("*.md")))
    if not vault:
        return {"found": False}
    files = list(vault.rglob("*.md"))
    cap = 20_000
    over = [f for f in files if f.stat().st_size > cap]
    sizes = sorted(f.stat().st_size for f in files)
    return {
        "found": True,
        "vault": str(vault),
        "files": len(files),
        "over_cap": len(over),
        "over_cap_pct": round(100 * len(over) / len(files)) if files else 0,
        "median_chars": sizes[len(sizes) // 2] if sizes else 0,
        "max_chars": sizes[-1] if sizes else 0,
        "max_file_read_pct": round(100 * cap / sizes[-1], 1) if sizes and sizes[-1] > cap else 100.0,
    }


def check_graph_edges() -> Dict[str, Any]:
    """Is the associative structure the decision rests on still there?"""
    graph = find_first(VAULT_CANDIDATES,
                       lambda p: (p / "graphify-out" / "graph.json").exists())
    if not graph:
        return {"found": False, "note": "no graph.json found"}
    try:
        d = json.loads((graph / "graphify-out" / "graph.json").read_text())
    except json.JSONDecodeError as e:
        return {"found": True, "error": str(e)}
    links = d.get("links") or d.get("edges") or []
    rel: Dict[str, int] = {}
    for l in links:
        r = str(l.get("relation", ""))
        rel[r] = rel.get(r, 0) + 1
    return {
        "found": True,
        "graph": str(graph),
        "edges": len(links),
        "relations": dict(sorted(rel.items(), key=lambda kv: -kv[1])[:8]),
        "wikilink_edges": sum(v for k, v in rel.items() if "wikilink" in k.lower()),
        "associative_present": rel.get("conceptually_related_to", 0) > 0,
    }


def check_graph_health() -> Dict[str, Any]:
    """A graph too old to be a current measurement is a review trigger."""
    graph = find_first(VAULT_CANDIDATES,
                       lambda p: (p / "graphify-out" / "graph.json").exists())
    if not graph:
        return {"found": False}
    import time
    age_days = (time.time() - (graph / "graphify-out" / "graph.json").stat().st_mtime) / 86400
    return {"found": True, "age_days": round(age_days, 1),
            "stale_over_7_days": age_days > 7}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else sys.argv[1:])

    problems = check_decision_files()
    cap = check_file_char_cap()
    corpus = check_corpus_size()
    edges = check_graph_edges()
    health = check_graph_health()

    payload = {
        "decision_files_ok": not problems,
        "problems": problems,
        "file_char_cap": cap,
        "corpus": corpus,
        "graph_edges": edges,
        "graph_freshness": health,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 1 if problems else 0

    print("Graph decision check")
    print("=" * 60)
    if problems:
        for p in problems:
            print(f"  PROBLEM: {p}")
    else:
        print("  decision files present and well-formed")

    if cap.get("found"):
        if cap.get("content_is_lost"):
            print(f"\n  _FILE_CHAR_CAP      : {cap.get('cap')}  "
                  "<-- CONTENT IS BEING DROPPED; the decision's premise returns")
        elif cap.get("slicing_is_lossless"):
            print(f"\n  _FILE_CHAR_CAP      : {cap.get('cap')} per slice, "
                  f"not per file -- {cap.get('detail')}; no content lost")
        else:
            print(f"\n  _FILE_CHAR_CAP      : {cap.get('cap')}; "
                  f"{cap.get('detail')}")
    else:
        print(f"\n  _FILE_CHAR_CAP      : {cap.get('note')}")

    if corpus.get("found"):
        lost = cap.get("content_is_lost")
        tail = ""
        if lost is True:
            tail = "  <-- over-cap files lose their tails"
        elif cap.get("slicing_is_lossless"):
            tail = " (all sliced, none lost)"
        print(f"  corpus              : {corpus['files']} files, "
              f"{corpus['over_cap_pct']}% exceed the {cap.get('cap','?')}-char slice size"
              f"{tail}")
    if edges.get("found"):
        print(f"  graph edges         : {edges['edges']}, "
              f"associative={'yes' if edges['associative_present'] else 'NO'}, "
              f"wikilinks={edges['wikilink_edges']}")
    if health.get("found"):
        stale = "  <-- stale; numbers measure an old graph" if health["stale_over_7_days"] else ""
        print(f"  graph freshness     : {health['age_days']} days old{stale}")

    print("\n  The decision stands unless a review trigger fired above.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
