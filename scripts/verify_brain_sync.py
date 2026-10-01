#!/usr/bin/env python3
"""
Brain sync verification script.
Runs after brain_sync.py to confirm content is actually searchable.
Queries the brain-postgres API with a test query and verifies results.

Usage: python3 verify_brain_sync.py [--source active-wiki|oracle-brain] [--query "test query"]
"""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# Configuration
#
# CHANGED 2026-09-27. The default used to fall back to LLM_BASE_URL, which is
# the LANGUAGE MODEL endpoint (openrouter in .env), and then appended "/search".
# That was wrong twice over:
#
#   1. An LLM API has no /search route, so every query returned HTTP 404.
#   2. With LLM_BASE_URL unset it fell back to http://localhost:8080/v1 -- but
#      port 8080 is SearXNG, a web metasearch engine. It answers /search with
#      HTML, so json.loads() raised "Expecting value: line 1 column 1".
#
# Neither failure said "wrong service". Both looked like a broken brain.
#
# The brain search service is the Hermes dashboard on 8088, and its route is
# /api/brain/search -- verified live, returning 15 real results served from
# PostgreSQL 18. BRAIN_API_URL is now explicit and no longer inherits from
# LLM_BASE_URL, because a verifier must never silently borrow the LLM's config.
BRAIN_API_URL = os.environ.get("BRAIN_API_URL", "http://localhost:8088")
BRAIN_SEARCH_PATH = os.environ.get("BRAIN_SEARCH_PATH", "/api/brain/search")
BRAIN_API_KEY = os.environ.get("BRAIN_API_KEY", "")

# Test queries per source
TEST_QUERIES = {
    "active-wiki": [
        "ontology engineering",
        "dual memory system",
        "dynamic ontology",
    ],
    "oracle-brain": [
        "philosophy ontology",
        "BFO SUMO DOLCE",
        "AI ontology failures",
    ],
}


def search_brain(query, api_url=None, search_path=None):
    """
    Search the brain API for a query.

    The endpoint is a GET taking ?q=, not a POST with a JSON body. Sending a
    POST returned nothing useful and the old code never checked WHICH shape it
    got back -- it just tried json.loads() on whatever arrived, so a 404 page,
    an HTML error, or an empty body all surfaced as the same opaque message.
    """
    base = api_url or BRAIN_API_URL
    path = search_path or BRAIN_SEARCH_PATH
    try:
        url = f"{base.rstrip('/')}{path}?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        if BRAIN_API_KEY:
            req.add_header("Authorization", f"Bearer {BRAIN_API_KEY}")

        response = urllib.request.urlopen(req, timeout=30)
        body = response.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            # Say WHAT came back. "Expecting value: line 1 column 1" was the
            # whole error when the real problem was an HTML page from a
            # completely different service.
            preview = body[:120].replace("\\n", " ")
            return {"error": f"non-JSON response from {url} (HTTP "
                             f"{response.status}): {preview!r}"}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code} from {base}{path} -- wrong service or route?"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def verify_source(source):
    """Verify that a source's content is searchable in brain."""
    queries = TEST_QUERIES.get(source, ["test query"])
    
    results = []
    for query in queries:
        result = search_brain(query)
        results.append({
            "query": query,
            "result": result,
            "has_results": len(result.get("results", [])) > 0 if "error" not in result else False,
            "error": result.get("error", None),
        })
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify brain sync")
    parser.add_argument("--source", choices=["active-wiki", "oracle-brain"], required=True)
    parser.add_argument("--query", type=str, help="Custom test query")
    args = parser.parse_args()
    
    print(f"Verifying brain sync for: {args.source}")
    print(f"API URL: {BRAIN_API_URL}")
    
    if args.query:
        # Single custom query
        result = search_brain(args.query)
        print(f"\nQuery: {args.query}")
        print(json.dumps(result, indent=2)[:500])
    else:
        # Run test queries
        results = verify_source(args.source)
        
        success_count = 0
        for r in results:
            status = "✓" if r["has_results"] else "✗"
            if r["error"]:
                status = "✗ (error)"
            else:
                success_count += 1
            print(f"  {status} '{r['query']}'")
            if r["error"]:
                print(f"      Error: {r['error']}")
        
        print(f"\n--- Summary ---")
        print(f"Queries: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(results) - success_count}")
        
        if success_count == len(results):
            print("✓ All test queries returned results. Brain sync verified.")
            return 0
        else:
            print("✗ Some queries failed. Brain sync may be incomplete.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
