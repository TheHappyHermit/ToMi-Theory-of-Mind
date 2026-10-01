#!/usr/bin/env python3
"""
brain_query.py — hybrid BM25 + vector search with RRF fusion, optionally fused
with graph-backed multi-hop retrieval.

Similarity search answers "what is similar to this text?". It cannot answer
"what connects these two things?", because that needs a walk. With --graph, the
graph layer contributes a second, structurally different ranking: nodes are
matched to the query, Personalized PageRank walks the knowledge graph outward
from them, and the documents it surfaces are merged into the same Reciprocal
Rank Fusion pool as the lexical and vector hits.

Usage:
  python3 scripts/brain_query.py "memory architecture"
  python3 scripts/brain_query.py "what did I decide about models" --source oracle-brain
  python3 scripts/brain_query.py "chunking strategy" --top 5
  python3 scripts/brain_query.py "what connects X to Y" --graph
  python3 scripts/brain_query.py "..." --graph --graph-only   # skip BM25/vector

The graph layer is strictly additive and never required. With no graph built, an
unreadable graph, or a query the graph does not cover, the tool behaves exactly
as it did before and says so in the notes.

Environment (same as brain_sync.py):
  BRAIN_PG_HOST, BRAIN_PG_PORT, BRAIN_PG_USER, BRAIN_PG_PASSWORD, BRAIN_PG_DB
  BRAIN_OLLAMA_URL, BRAIN_EMBED_MODEL, BRAIN_API_MODE
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

try:
    import pg8000
except ImportError:
    pg8000 = None

# Graph-backed multi-hop retrieval. Optional: if it cannot load (no graph built,
# unreadable JSON, missing module) the hybrid path below is unaffected.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from graph_retrieval import multi_hop_search, load_graphs
    GRAPH_RETRIEVAL_AVAILABLE = True
except Exception:
    multi_hop_search = None
    load_graphs = None
    GRAPH_RETRIEVAL_AVAILABLE = False

# ── Configuration ───────────────────────────────────────────────────────

PG_HOST = os.environ.get("BRAIN_PG_HOST") or os.environ.get("POSTGRES_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("BRAIN_PG_PORT") or os.environ.get("POSTGRES_PORT", "5433"))
PG_USER = os.environ.get("BRAIN_PG_USER") or os.environ.get("POSTGRES_USER", "brain")
PG_PASSWORD = os.environ.get("BRAIN_PG_PASSWORD") or os.environ.get("POSTGRES_PASSWORD", "brain")
PG_DB = os.environ.get("BRAIN_PG_DB") or os.environ.get("POSTGRES_DB", "brain")

# The default was localhost:11434 (native Ollama), which is not what runs
# here: the live embedding service is llama.cpp on the inference node. Run
# without the env var set and search silently failed with "Connection refused"
# on the query embedding, which looks like a search outage rather than a
# config default. Matches brain_sync_cron.py, which already sets this.
OLLAMA_URL = (os.environ.get("BRAIN_OLLAMA_URL")
              or os.environ.get("INFERENCE_EMBED_URL", "http://10.0.0.10:18082"))
EMBED_MODEL = os.environ.get("BRAIN_EMBED_MODEL") or os.environ.get("MODEL_ROLE_EMBEDDING_MODEL", "/models/Qwen3-Embedding-4B-Q8_0.gguf")

# API mode: "ollama" for native Ollama, "openai" for llama.cpp / OpenAI-compatible
API_MODE = os.environ.get("BRAIN_API_MODE", "openai")


def get_db():
    if pg8000 is None:
        raise RuntimeError("pg8000 is not installed. Please run `pip install pg8000` to enable PostgreSQL brain query.")
    return pg8000.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASSWORD, database=PG_DB,
    )


def embed_query(text: str, dim: int = 2000) -> list[float]:
    """Embed a single query string via the embedding server with dimension truncation."""
    if API_MODE == "ollama":
        # Native Ollama API
        data = json.dumps({"model": EMBED_MODEL, "input": text, "dimensions": dim}).encode()
        url = f"{OLLAMA_URL}/api/embed"
    else:
        # OpenAI-compatible API (llama.cpp, vLLM, etc.)
        data = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        url = f"{OLLAMA_URL}/v1/embeddings"
    
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        if API_MODE == "ollama":
            embedding = result["embeddings"][0]
        else:
            embedding = result["data"][0]["embedding"]
        
        # Truncate embeddings to the target dimension (Ollama does this natively via dimensions param)
        if dim and len(embedding) > dim:
            embedding = embedding[:dim]
        
        return embedding


def hybrid_search(conn, query_embedding: list[float], query_text: str,
                  top_k: int = 10, source_filter: str = None,
                  fts_weight: float = 0.5, vector_weight: float = 0.5) -> list[dict]:
    """
    Perform hybrid search: full-text (ts_rank) + vector (cosine).
    Combine with Reciprocal Rank Fusion (RRF).
    """
    cur = conn.cursor()

    # Use the brain_search function from the schema
    cur.execute(
        "SELECT * FROM brain_search(%s, %s, %s, %s, %s, %s)",
        (str(query_embedding), query_text, top_k, fts_weight, vector_weight, source_filter)
    )

    results = []
    for row in cur.fetchall():
        results.append({
            "page_id": row[0],
            "chunk_id": row[1],
            "source": row[2],
            "slug": row[3],
            "title": row[4],
            "chunk_text": row[5],
            "chunk_index": row[6],
            "full_text_rank": row[7],
            "vector_rank": row[8],
            "rrf_score": row[9],
        })

    return results


def log_query(conn, query_text: str, query_embedding: list[float], results: list[dict]):
    """Log query to conversation_history for future reference."""
    cur = conn.cursor()
    results_json = json.dumps([{
        "page_id": r["page_id"],
        "chunk_index": r["chunk_index"],
        "score": r["rrf_score"],
        "slug": r["slug"],
    } for r in results[:5]])

    cur.execute("""
        INSERT INTO conversation_history (query_text, query_embedding, results, result_count, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (query_text, str(query_embedding), results_json, len(results),
          datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    conn.commit()


def format_results(results: list[dict]) -> str:
    """Format results for terminal output."""
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        # Truncate chunk text for display
        text = r["chunk_text"][:300].replace("\n", " ").strip()
        text = r.get("chunk_text") or ""
        if len(text) > 300:
            text += "..."

        lines.append(
            f"{i}. [{r['source']}] {r['title']}\n"
            f"   Path: {r['slug']}\n"
            f"   Score: {r['rrf_score']:.4f} (FTS: {r['full_text_rank']:.4f}, Vec: {r['vector_rank']:.4f})\n"
            f"   {text}\n"
        )

    return "\n".join(lines)

# ── Graph-backed multi-hop retrieval ─────────────────────────────────────

RRF_K = 60  # standard Reciprocal Rank Fusion constant


def graph_search(query: str, top_k: int = 10, source: str = None,
                 depth: int = 2) -> dict:
    """
    Multi-hop relational search over the Graphify graphs.

    Returns {"results": [...], "notes": [...]} and never raises: a missing or
    unreadable graph yields notes, not an exception. The relational index is
    optional and must never take down the primary retrieval path.
    """
    if not GRAPH_RETRIEVAL_AVAILABLE:
        return {"results": [], "notes": ["graph_retrieval module unavailable"]}
    try:
        return multi_hop_search(
            query,
            sources=[source] if source else None,
            top_k=top_k,
            depth=depth,
        )
    except Exception as e:
        return {"results": [], "notes": [f"graph retrieval failed: {e}"]}


def fuse_graph_results(results: list[dict], graph_hits: list[dict]) -> list[dict]:
    """
    Merge graph hits into an RRF-ranked result list.

    Graph hits carry a file path, not a page_id, so they are matched into the
    existing pool by slug/path. A graph hit that matches nothing is appended as
    a first-class result with its connecting path attached -- that provenance is
    the point of graph retrieval, and discarding it would throw away the only
    reason to use the graph.
    """
    by_slug = {r.get("slug", ""): r for r in results if r.get("slug")}

    for rank, hit in enumerate(graph_hits, start=1):
        path = hit.get("file", "")
        slug = path.rsplit("/", 1)[-1] if "/" in path else path
        rrf = 1.0 / (RRF_K + rank)

        existing = by_slug.get(path) or by_slug.get(slug)
        if existing is not None:
            # Boost an already-retrieved document for being graph-connected.
            existing["graph_rrf"] = rrf
            existing["graph_path"] = hit.get("path")
            existing["graph_hops"] = hit.get("hops")
            existing["graph_node"] = hit.get("node")
            continue

        results.append({
            "page_id": None,
            "chunk_id": None,
            "source": hit.get("source", ""),
            "slug": path,
            "title": hit.get("node", slug),
            "chunk_text": f"[graph] connected via {hit.get('path') or 'seed match'}",
            "chunk_index": None,
            "full_text_rank": None,
            "vector_rank": None,
            "graph_rrf": rrf,
            "graph_path": hit.get("path"),
            "graph_hops": hit.get("hops"),
            "graph_node": hit.get("node"),
        })

    # Re-sort: documents found by more than one method rank highest.
    def sort_key(r):
        base = r.get("rrf_score") or 0.0
        return -(base + (r.get("graph_rrf") or 0.0))

    results.sort(key=sort_key)
    return results


def main():
    parser = argparse.ArgumentParser(description="Search your brain (hybrid BM25 + vector)")
    parser.add_argument("query", help="Natural-language query")
    parser.add_argument("--source", choices=["active-wiki", "oracle-brain", "exchange-research"],
                        help="Filter by source")
    parser.add_argument("--top", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("--fts-weight", type=float, default=0.5, help="Full-text weight (default: 0.5)")
    parser.add_argument("--vector-weight", type=float, default=0.5, help="Vector weight (default: 0.5)")
    parser.add_argument("--no-log", action="store_true", help="Don't log query to history")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--graph", action="store_true",
                        help="Also search the knowledge graph (multi-hop relational retrieval)")
    parser.add_argument("--graph-only", action="store_true",
                        help="Skip BM25/vector and use only the graph. Implies --graph.")
    parser.add_argument("--graph-depth", type=int, default=2,
                        help="Graph traversal depth (default: 2)")
    parser.add_argument("--graph-top", type=int, default=10,
                        help="Graph candidates to fuse (default: 10)")
    args = parser.parse_args()

    if args.graph_only:
        args.graph = True

    print(f"brain_query.py — Brain Search")
    print(f"  Query: {args.query}")
    print(f"  Source filter: {args.source or 'none'}")
    if args.graph:
        print(f"  Graph layer: on (depth {args.graph_depth}, top {args.graph_top})")
    print()

    # ── Graph-only path: no database, no embedding server required ──
    if args.graph_only:
        gout = graph_search(args.query, top_k=args.graph_top,
                            source=args.source, depth=args.graph_depth)
        for note in gout["notes"]:
            print(f"  [note] {note}")
        for name, stats in gout.get("graphs_consulted", {}).items():
            print(f"  [graph] {name}: {stats['nodes']:,} nodes, "
                  f"{stats['relationships']:,} relationships")
        results = [{
            "source": r["source"], "slug": r["file"], "title": r["node"],
            "chunk_text": f"connected via {r['path'] or 'seed match'}",
            "graph_hops": r["hops"], "graph_path": r["path"],
        } for r in gout["results"]]
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        elif not results:
            print("\n  No graph-linked results. See the notes above.")
        else:
            print(f"\nTop {len(results)} graph results:\n")
            for i, r in enumerate(results, 1):
                hops = f"{r['graph_hops']}-hop" if r["graph_hops"] else "seed"
                print(f"{i}. [{r['source']}] {r['title']}  ({hops})")
                print(f"   File: {r['slug']}")
        return 0

    # Embed query
    print("Embedding query...", end=" ", flush=True)
    try:
        query_embedding = embed_query(args.query)
        print(f"{len(query_embedding)}-dim")
    except Exception as e:
        print(f"\n[error] Ollama embed failed: {e}")
        sys.exit(1)

    # Search
    try:
        conn = get_db()
    except Exception as e:
        print(f"[error] DB connection failed: {e}")
        sys.exit(1)

    try:
        results = hybrid_search(
            conn, query_embedding, args.query,
            top_k=args.top, source_filter=args.source,
            fts_weight=args.fts_weight, vector_weight=args.vector_weight,
        )

        # Fuse graph hits into the same pool. Additive: on any failure the
        # hybrid results stand unchanged.
        if args.graph:
            print("Searching knowledge graph...", flush=True)
            gout = graph_search(args.query, top_k=args.graph_top,
                                source=args.source, depth=args.graph_depth)
            for note in gout["notes"]:
                print(f"  [note] {note}")
            if gout["results"]:
                before = len(results)
                results = fuse_graph_results(results, gout["results"])
                added = sum(1 for r in results if r.get("page_id") is None)
                print(f"  [graph] fused {len(gout['results'])} hop candidates "
                      f"({added} new, {before} lexical/vector)")

        if not args.no_log and results:
            try:
                log_query(conn, args.query, query_embedding, results)
            except Exception:
                pass  # Non-critical

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"\nTop {len(results)} results:\n")
            print(format_results(results))

    except Exception as e:
        print(f"[error] Search failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
