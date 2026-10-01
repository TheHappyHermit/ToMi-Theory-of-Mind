#!/usr/bin/env python3
"""Re-query GitHub for every dependency in docs/DEPENDENCY-REGISTRY.md and diff it.

The registry records point-in-time measurements. Prose goes stale, so this makes
drift visible on demand instead of assumed away.

Deliberately NOT wired into cron. A dependency-health change -- especially a
licence change -- should be reviewed by a human, never auto-accepted unattended.

Usage:
    python3 scripts/refresh_dependency_health.py            # table
    python3 scripts/refresh_dependency_health.py --diff     # changes vs registry
    python3 scripts/refresh_dependency_health.py --json     # machine-readable

Exit codes: 0 = no drift (or no --diff), 1 = drift detected, 2 = bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

# slug -> (display name, tier). Order here is the report order.
PROJECTS: List[Tuple[str, str, str]] = [
    ("NousResearch/hermes-agent", "Hermes agent", "foundation"),
    ("pgvector/pgvector", "pgvector", "foundation"),
    ("plastic-labs/honcho", "Honcho", "foundation"),
    ("Graphify-Labs/graphify", "graphify", "foundation"),
    ("mendableai/firecrawl", "Firecrawl", "component"),
    ("searxng/searxng", "SearXNG", "component"),
    ("ollama/ollama", "Ollama", "inference"),
    ("vllm-project/vllm", "vLLM", "inference"),
    ("BerriAI/litellm", "LiteLLM", "inference"),
    ("neo4j/neo4j", "Neo4j", "evaluated"),
    ("getzep/graphiti", "Graphiti", "evaluated"),
    ("getzep/zep", "Zep", "evaluated"),
    ("mem0ai/mem0", "mem0", "evaluated"),
    ("FalkorDB/FalkorDB", "FalkorDB", "evaluated"),
    ("kuzudb/kuzu", "Kuzu", "evaluated"),
    ("HKUDS/LightRAG", "LightRAG", "evaluated"),
    ("infiniflow/ragflow", "RAGFlow", "evaluated"),
    ("topoteretes/cognee", "cognee", "evaluated"),
    ("OSU-NLP-Group/HippoRAG", "HippoRAG", "evaluated"),
]

API = "https://api.github.com"
UA = {"User-Agent": "curl/8", "Accept": "application/vnd.github+json"}

# Unauthenticated GitHub allows ~60 requests/hour, which is not enough for the ~38
# calls this script makes (19 projects x repo + contributors). A token raises that
# to 5,000/hour. Set GITHUB_TOKEN or GH_TOKEN to use one; without it the script
# degrades honestly -- it reports every fetch as failed and exits 2 rather than
# pretending to have measured anything.
_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
if _TOKEN:
    UA["Authorization"] = f"Bearer {_TOKEN}"


def _get(url: str, timeout: int = 20) -> Tuple[Optional[dict], str, Dict[str, object]]:
    """Return (json_or_None, link_header, error)."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), resp.headers.get("Link", ""), {}
    except urllib.error.HTTPError as exc:
        return None, "", {"status": exc.code, "message": str(exc.reason)}
    except Exception as exc:  # network, timeout, JSON
        return None, "", {"message": str(exc)}


def contributor_count(slug: str) -> Optional[int]:
    """Total contributors, from the Link header's rel=last page (per_page=1)."""
    data, link, err = _get(f"{API}/repos/{slug}/contributors?per_page=1")
    if err:
        return None
    m = re.search(r"[?&]page=(\d+)>; rel=\"last\"", link)
    if m:
        return int(m.group(1))
    if isinstance(data, list):
        return len(data)
    return None


def _count_issues_only(slug: str) -> Optional[int]:
    """Count open issues excluding pull requests, via the search API.

    Returns None rather than guessing when the API is unavailable or rate-limited --
    an unknown count must not read as zero.
    """
    url = f"{API}/search/issues?q=repo:{slug}+type:issue+state:open&per_page=1"
    data, _, err = _get(url)
    if err or not isinstance(data, dict):
        return None
    val = data.get("total_count")
    return val if isinstance(val, int) else None


def fetch(slug: str) -> Optional[dict]:
    data, _, err = _get(f"{API}/repos/{slug}")
    if err or not isinstance(data, dict):
        return None
    return {
        "slug": slug,
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "contributors": contributor_count(slug),
        # GitHub's open_issues_count INCLUDES pull requests, so it is an activity
        # signal, not a defect count. Report the aggregate AND the real split, and
        # let the caller decide: comparing aggregates across repos is how vLLM's
        # 8,372 (2,505 issues + 5,867 PRs) gets mistaken for a defect signal.
        "open_issues_total": data.get("open_issues_count"),
        "open_issues_actual": _count_issues_only(slug),
        "created": (data.get("created_at") or "")[:10],
        "pushed": (data.get("pushed_at") or "")[:10],
        "license": ((data.get("license") or {}).get("spdx_id")) or "NONE",
        "archived": bool(data.get("archived")),
        "description": (data.get("description") or "")[:60],
    }


def parse_registry(path: str) -> Dict[str, dict]:
    """Pull the recorded measurements back out of the registry markdown.

    Parsed from the table rows rather than a second hardcoded copy, so the registry
    stays the single source of truth.
    """
    out: Dict[str, dict] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return out

    row = re.compile(r"^\|\s*`?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)`?\s*\|")
    for line in text.split("\n"):
        m = row.match(line)
        if not m:
            continue
        slug = m.group(1)
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rec: dict = {"cells": cells}
        for cell in cells[1:]:
            n = cell.replace(",", "").replace("—", "").strip()
            if n.isdigit():
                rec.setdefault("numbers", []).append(int(n))
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", n):
                rec.setdefault("dates", []).append(n)
        out[slug] = rec
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Refresh dependency health measurements")
    ap.add_argument("--registry", default="docs/DEPENDENCY-REGISTRY.md")
    ap.add_argument("--diff", action="store_true", help="report drift vs the registry")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--delay", type=float, default=0.25, help="seconds between calls")
    args = ap.parse_args(argv)

    results = []
    for slug, name, tier in PROJECTS:
        rec = fetch(slug)
        if rec is None:
            rec = {"slug": slug, "name": name, "tier": tier, "error": "fetch failed"}
        else:
            rec["name"] = name
            rec["tier"] = tier
        results.append(rec)
        time.sleep(args.delay)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    hdr = (f"{'project':<20}{'tier':<12}{'stars':>9}{'contrib':>8}  "
           f"{'created':<12}{'pushed':<12}{'licence':<16}arch")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        if r.get("error"):
            print(f"{r['name']:<20}{r['tier']:<12}  ERROR: {r['error']}")
            continue
        flag = "  ARCHIVED" if r["archived"] else ""
        contrib = r["contributors"] if r["contributors"] is not None else "?"
        print(
            f"{r['name']:<20}{r['tier']:<12}{r['stars']:>9,}{str(contrib):>8}  "
            f"{r['created']:<12}{r['pushed']:<12}{r['license']:<16}{flag}"
        )

    failed = [r for r in results if r.get("error")]
    archived = [r for r in results if r.get("archived")]

    if archived:
        print("\nARCHIVED (must be removed from any 'live options' list):")
        for r in archived:
            print(f"  - {r['name']} ({r['slug']}), last push {r['pushed']}")
    if failed:
        print(f"\n{len(failed)} fetch failure(s) -- likely rate limited;")
        print(
            "GitHub allows ~60 unauthenticated requests/hour. Re-run later, or set\n"
            "GITHUB_TOKEN in the environment to raise the limit to 5,000/hour."
        )

    if not args.diff:
        print("\n(issue counts are split: GitHub's aggregate includes pull requests.)")
        # A run where nothing was measured is not a clean run. Exiting 0 here would
        # let a scheduled check report success while having verified nothing.
        if len(failed) == len(PROJECTS):
            print("VERDICT: every fetch failed -- nothing was measured.")
            return 2
        return 0

    # Drift detection: compare against numbers parsed out of the registry tables.
    print("\n=== DRIFT vs registry ===")
    reg = parse_registry(args.registry)
    drift = 0
    for r in results:
        if r.get("error"):
            continue
        rec = reg.get(r["slug"])
        if not rec:
            print(f"  {r['name']:<18} not in registry table -- add it")
            drift += 1
            continue
        nums = rec.get("numbers", [])
        # Registry row order: stars, contributors, then dates.
        if len(nums) >= 2:
            rs, rc = nums[0], nums[1]
            if abs((r["stars"] or 0) - rs) > max(50, rs * 0.02):
                print(f"  {r['name']:<18} stars {rs:,} -> {r['stars']:,}")
                drift += 1
            if r["contributors"] and abs(r["contributors"] - rc) > max(5, rc * 0.15):
                print(f"  {r['name']:<18} contributors {rc:,} -> {r['contributors']:,}")
                drift += 1
        dates = rec.get("dates", [])
        if len(dates) >= 2 and dates[1] != r["pushed"]:
            print(f"  {r['name']:<18} last push {dates[1]} -> {r['pushed']}")
            drift += 1
        if r["archived"]:
            print(f"  {r['name']:<18} *** NOW ARCHIVED ***")
            drift += 1

    if drift:
        print(f"\n{drift} change(s). Update docs/DEPENDENCY-REGISTRY.md and review each by hand.")
        return 1
    if len(failed) == len(PROJECTS):
        print("\nVERDICT: every fetch failed -- drift could not be assessed.")
        return 2
    print("\nNo material drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
