#!/usr/bin/env python3
"""
scripts/run_roi_canary.py — Memory ROI canary probes.

Weekly deterministic probes that measure retrieval hit-rate and precision@k
per domain. Writes results to the roi_canary_probes table.

This is a measurement-only script — no deletions, no curation policy.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import pg8000
except ImportError:
    import psycopg2 as pg8000

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5433"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "brain")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "brain")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "brain")

# Canary probes per domain — known-answer questions derived from wiki content
# These should be updated periodically as the knowledge base grows
CANARY_PROBES = {
    "ops": [
        {
            "question": "What port does the dashboard run on?",
            "expected_answer": "8088",
        },
        {
            "question": "What is the name of the Postgres container?",
            "expected_answer": "brain-db",
        },
    ],
    "research": [
        {
            "question": "What is the research lane for memory consolidation?",
            "expected_answer": "SWR",
        },
    ],
    "project": [
        {
            "question": "What is the project name?",
            "expected_answer": "ToMi",
        },
    ],
    "personal": [
        {
            "question": "Where is the ToMi data home?",
            "expected_answer": "~/.hermes/brain",
        },
    ],
}


def get_postgres_conn():
    try:
        return pg8000.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
        )
    except Exception as e:
        print(f"[ROI] Postgres connection failed: {e}")
        return None


def run_brain_search(conn, query_text, match_count=10):
    """Run BM25 search (canary doesn't need embeddings)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.source, p.slug, p.title, e.chunk_text
            FROM embeddings e
            JOIN pages p ON e.page_id = p.id
            WHERE to_tsvector('english', e.chunk_text) @@ plainto_tsquery('english', %s)
            ORDER BY ts_rank(to_tsvector('english', e.chunk_text), plainto_tsquery('english', %s)) DESC
            LIMIT %s
        """, (query_text, query_text, match_count))
        return [{"source": r[0], "slug": r[1], "title": r[2], "chunk_text": r[3]} for r in cur.fetchall()]
    except Exception as e:
        print(f"[ROI] Search failed: {e}")
        return []


def run_canary_probes():
    """Run canary probes and log results."""
    conn = get_postgres_conn()
    if conn is None:
        return []

    results = []
    try:
        cur = conn.cursor()
        for domain, probes in CANARY_PROBES.items():
            for probe in probes:
                question = probe["question"]
                expected = probe["expected_answer"]

                # Search
                search_results = run_brain_search(conn, question, match_count=10)

                # Check if expected answer appears in results
                hit = False
                got_answer = None
                for r in search_results:
                    chunk = r.get("chunk_text", "")
                    title = r.get("title", "")
                    if expected.lower() in chunk.lower() or expected.lower() in title.lower():
                        hit = True
                        got_answer = chunk[:200] if chunk else title
                        break

                # Compute precision@k (fraction of results that are relevant)
                precision = 0.0
                if search_results:
                    relevant = sum(1 for r in search_results
                                   if expected.lower() in r.get("chunk_text", "").lower()
                                   or expected.lower() in r.get("title", "").lower())
                    precision = relevant / len(search_results)

                # Log result
                cur.execute("""
                    INSERT INTO roi_canary_probes (domain, question, expected_answer, got_answer, hit, precision_at_k)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (domain, question, expected, got_answer, hit, precision))
                conn.commit()

                results.append({
                    "domain": domain,
                    "question": question,
                    "hit": hit,
                    "precision": precision,
                })
                print(f"  [{domain}] '{question}' -> hit={hit}, p@{len(search_results)}={precision:.2f}")

    finally:
        conn.close()

    print(f"[ROI] Completed {len(results)} canary probes")
    return results


if __name__ == "__main__":
    run_canary_probes()
