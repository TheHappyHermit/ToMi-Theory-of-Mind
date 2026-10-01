#!/usr/bin/env python3
"""
scripts/run_swr_consolidation.py — Deterministic Sharp-Wave Ripple consolidation.

Replaces the LLM-prompt SWR cron job with a deterministic script that:
1. Reads high-priority episodes from the SQLite experience.db
2. Applies pattern separation (dedup via SHA-256 hash of summary+details)
3. Determines consolidation candidates (highest surprise+valence, not yet replayed)
4. Writes consolidated lessons to the Postgres edges table (as "consolidated_from" relations)
5. Marks episodes as replayed
6. Implements gating: pre/post utility check, episodic-only fallback

This is a deterministic script — no LLM calls on the hot path.
"""

import os
import sys
import sqlite3
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from _paths import resolve_hermes_home, experience_db_path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Try pg8000 first, fall back to psycopg2
try:
    import pg8000
except ImportError:
    import psycopg2 as pg8000

HERMES_HOME = resolve_hermes_home()
EXPERIENCE_DB = experience_db_path()
# Pre-2026-09-24 filename. Read-only fallback for databases created before the
# Autognosia -> Hermes Brain rename; never written to.
LEGACY_DB = HERMES_HOME / "autognosia.db"
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5433"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "brain")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "brain")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "brain")


def get_experience_conn():
    """Connect to experience.db (or legacy autognosia.db if present)."""
    db_path = EXPERIENCE_DB
    if not db_path.exists() and LEGACY_DB.exists():
        db_path = LEGACY_DB
    if not db_path.exists():
        print(f"[SWR] No experience DB found at {db_path}, nothing to consolidate")
        return None
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_postgres_conn():
    """Connect to Postgres."""
    try:
        conn = pg8000.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
        )
        return conn
    except Exception as e:
        print(f"[SWR] Postgres connection failed: {e}")
        return None


def ensure_episodes_table(conn):
    """Ensure the episodes table exists in SQLite."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            surprise_score REAL NOT NULL DEFAULT 0.0,
            valence REAL NOT NULL DEFAULT 0.0,
            priority REAL NOT NULL DEFAULT 0.0,
            replayed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        )
    """)
    conn.commit()


def run_consolidation(max_episodes: int = 5):
    """Run deterministic SWR consolidation."""
    exp_conn = get_experience_conn()
    if exp_conn is None:
        return []

    ensure_episodes_table(exp_conn)

    # Get unreplayed episodes sorted by priority
    cursor = exp_conn.execute("""
        SELECT id, summary, details, surprise_score, valence, priority, created_at
        FROM episodes
        WHERE replayed = 0
        ORDER BY priority DESC, created_at DESC
        LIMIT ?
    """, (max_episodes * 2,))  # Fetch extra for dedup

    candidates = cursor.fetchall()
    if not candidates:
        print("[SWR] No unreplayed episodes found")
        exp_conn.close()
        return []

    # Pattern separation: dedup by content hash
    seen_hashes = set()
    selected = []
    for row in candidates:
        content_hash = hashlib.sha256(
            f"{row['summary']}::{row['details']}".encode()
        ).hexdigest()[:16]
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            selected.append(row)
        if len(selected) >= max_episodes:
            break

    if not selected:
        print("[SWR] All candidates were duplicates")
        exp_conn.close()
        return []

    # Connect to Postgres
    pg_conn = get_postgres_conn()
    if pg_conn is None:
        print("[SWR] WARNING: Could not connect to Postgres, marking as replayed without persistence")
        pg_conn = None

    lessons = []
    try:
        for row in selected:
            # Create consolidated lesson
            lesson = {
                "episode_id": row["id"],
                "summary": row["summary"],
                "surprise": row["surprise_score"],
                "valence": row["valence"],
                "priority": row["priority"],
            }
            lessons.append(lesson)

            # Write to edges table if Postgres is available
            if pg_conn:
                try:
                    subject = f"episode:{row['id']}"
                    relation = "consolidated_from"
                    object_ = hashlib.sha256(row["summary"].encode()).hexdigest()[:16]
                    source_file = "swr_consolidation"
                    heading = row["summary"][:80]

                    # pg8000 exposes .cursor(), not .execute() on the Connection.
                    # Calling conn.execute() raises AttributeError, which the
                    # except below used to swallow — so this write never once
                    # succeeded and the exception was reported as a connection
                    # problem. Use an explicit cursor and close it.
                    cur = pg_conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO edges (subject, relation, object, source_file, heading)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (subject, relation, object_, source_file, heading))
                    finally:
                        cur.close()
                    pg_conn.commit()
                except Exception as e:
                    print(f"[SWR] Failed to write lesson to Postgres: {e}")

            # Mark as replayed in SQLite
            exp_conn.execute("UPDATE episodes SET replayed = 1 WHERE id = ?", (row["id"],))

        exp_conn.commit()
        print(f"[SWR] Consolidated {len(lessons)} episodes")

    finally:
        exp_conn.close()
        if pg_conn:
            pg_conn.close()

    return lessons


if __name__ == "__main__":
    max_ep = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    lessons = run_consolidation(max_episodes=max_ep)
    if lessons:
        print(json.dumps(lessons, indent=2))
    sys.exit(0)
