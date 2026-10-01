#!/usr/bin/env python3
"""
scripts/run_scale_diagnostic.py — Scale decay diagnostic.

Monthly diagnostic that measures retrieval reliability as corpus grows.
Uses fixed test queries and logs results to scale_decay_diagnostic table.

Research shows 16-20pp retrieval reliability drop without this monitoring.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _paths import resolve_hermes_home

try:
    import pg8000
except ImportError:
    import psycopg2 as pg8000

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5433"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "brain")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "brain")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "brain")

# Fixed test queries — known-answer questions that should always retrieve
TEST_QUERIES = [
    {"question": "What is the project name?", "expected": "ToMi"},
    {"question": "What port does the dashboard run on?", "expected": "8088"},
    {"question": "What database does the brain use?", "expected": "Postgres"},
    {"question": "Where is the ToMi data home?", "expected": "~/.hermes/brain"},
    {"question": "What is the SWR schedule?", "expected": "04:00"},
]


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
        print(f"[Scale] Postgres connection failed: {e}")
        return None


def get_corpus_size(conn):
    """Get total page count as corpus size proxy."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pages")
        return cur.fetchone()[0]
    except:
        return 0


def run_diagnostic():
    """Run scale decay diagnostic."""
    conn = get_postgres_conn()
    if conn is None:
        return []

    corpus_size = get_corpus_size(conn)
    results = []
    try:
        cur = conn.cursor()
        for test in TEST_QUERIES:
            query = test["question"]
            expected = test["expected"]

            # BM25 search
            cur.execute("""
                SELECT p.title, e.chunk_text
                FROM embeddings e
                JOIN pages p ON e.page_id = p.id
                WHERE to_tsvector('english', e.chunk_text) @@ plainto_tsquery('english', %s)
                ORDER BY ts_rank(to_tsvector('english', e.chunk_text), plainto_tsquery('english', %s)) DESC
                LIMIT 5
            """, (query, query))

            rows = cur.fetchall()
            got_answer = None
            correct = False
            for r in rows:
                chunk = f"{r[0]} {r[1]}"
                if expected.lower() in chunk.lower():
                    got_answer = chunk[:200]
                    correct = True
                    break

            # Reliability = fraction of test queries that returned correct answer
            reliability = 0
            if rows:
                relevant = sum(1 for r in rows if expected.lower() in f"{r[0]} {r[1]}".lower())
                reliability = relevant / len(rows)

            cur.execute("""
                INSERT INTO scale_decay_diagnostic (corpus_size, query, expected_answer, got_answer, correct, reliability)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (corpus_size, query, expected, got_answer, correct, reliability))
            conn.commit()

            results.append({
                "query": query,
                "correct": correct,
                "reliability": reliability,
            })
            print(f"  [{corpus_size} pages] '{query}' -> correct={correct}, reliability={reliability:.2f}")

    finally:
        conn.close()

    overall = sum(1 for r in results if r["correct"]) / len(results) if results else 0
    print(f"[Scale] Corpus size: {corpus_size}, Overall reliability: {overall:.2f}")
    return results


if __name__ == "__main__":
    run_diagnostic()
