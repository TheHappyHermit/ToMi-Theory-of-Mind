#!/usr/bin/env python3
"""
Initialize Cortex Experience Index database.

The Experience Index tracks operations, verification outcomes, routing events, and reflections.

Usage:
  python3 scripts/init_experience_db.py [--yes]
"""

import os
import sys
from pathlib import Path
import sqlite3
import argparse
from typing import List, Optional

# scripts/ on the path so the sibling import works whether this file is
# run directly or imported.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from secure_perms import secure_secrets_dir  # noqa: E402

def _resolve_hermes_data_dir() -> Path:
    for env_var in ("HERMES_DATA_DIR", "HERMES_HOME", "CORTEX_HOME"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return Path(val).resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win_hermes.exists():
            return win_hermes
    default_hermes = Path.home() / ".hermes"
    if default_hermes.exists():
        return default_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return default_hermes

HERMES_HOME = _resolve_hermes_data_dir()
DB_PATH = os.environ.get("EXPERIENCE_DB_PATH", os.environ.get("EXPERIENCE_DB", str(HERMES_HOME / "experience.db")))

def ensure_directories():
    """Create all required directory structure. Cross-platform."""
    dirs = [
        HERMES_HOME / "active-wiki" / "30_Projects",
        HERMES_HOME / "active-wiki" / ".meta",
        HERMES_HOME / "oracle" / "brain",
        HERMES_HOME / "oracle" / "raw" / "research",
        HERMES_HOME / "oracle" / "raw" / "documents",
        HERMES_HOME / "oracle" / "raw" / "articles",
        HERMES_HOME / "oracle" / "raw" / "transcripts",
        HERMES_HOME / "oracle" / "raw" / "conversations",
        HERMES_HOME / "oracle" / "raw" / "imports",
        HERMES_HOME / "oracle" / "raw" / "assets",
        HERMES_HOME / "secrets",
    ]
    created = []
    for d in dirs:
        if not d.exists():
            # See init_db.py: a default-mode secrets directory is 775, which
            # is world-readable the moment it exists. Create it 700 directly,
            # and chmod because mkdir's mode is masked by the umask.
            if d.name == "secrets":
                d.mkdir(parents=True, exist_ok=True, mode=0o700)
                secure_secrets_dir(d)
            else:
                d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))
    return created

SCHEMA = """
-- Drop any legacy temporary migration tables if present
DROP TABLE IF EXISTS operations_new;
DROP TABLE IF EXISTS routing_new;
-- Operations: what was done (every significant action)
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    profile TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    result TEXT CHECK(result IN ('success', 'failure', 'partial', 'aborted')) DEFAULT 'success',
    duration_ms INTEGER,
    tokens_used INTEGER,
    error_message TEXT,
    metadata TEXT
);

-- Verification Checks: did reality match the plan?
CREATE TABLE IF NOT EXISTS verification_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    operation_id INTEGER,
    expected_result TEXT NOT NULL,
    actual_result TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    notes TEXT,
    FOREIGN KEY (operation_id) REFERENCES operations(id) ON DELETE CASCADE
);

-- Routing Events: which profile handled what
CREATE TABLE IF NOT EXISTS routing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    input_summary TEXT NOT NULL,
    routed_to TEXT NOT NULL,
    route_reason TEXT,
    confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
    outcome TEXT
);

-- Skill Events: which skills were used and how
CREATE TABLE IF NOT EXISTS skill_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    skill_name TEXT NOT NULL,
    trigger TEXT,
    success BOOLEAN DEFAULT TRUE,
    duration_ms INTEGER,
    error_message TEXT
);

-- Reflections: what we learned from experience
CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    reflection_type TEXT CHECK(reflection_type IN ('pattern', 'lesson', 'warning', 'success', 'failure')),
    content TEXT NOT NULL,
    source_operation_id INTEGER,
    source_tool TEXT,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TEXT,
    FOREIGN KEY (source_operation_id) REFERENCES operations(id) ON DELETE SET NULL
);

-- Key Decisions: important choices made
CREATE TABLE IF NOT EXISTS key_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    decision TEXT NOT NULL,
    rationale TEXT,
    alternatives_considered TEXT,
    outcome TEXT,
    superseded_by INTEGER REFERENCES key_decisions(id)
);

-- Prospective Memory Log: intentions and outcomes
CREATE TABLE IF NOT EXISTS prospective_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    session_id TEXT,
    cue TEXT NOT NULL,
    intended_action TEXT,
    action_taken TEXT,
    triggered BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE
);

-- Proactive Actions: autonomously initiated background tasks
CREATE TABLE IF NOT EXISTS proactive_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT CHECK(status IN ('initiated', 'completed', 'failed', 'suppressed')) DEFAULT 'initiated',
    outcome TEXT,
    tokens_used INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ops_profile ON operations(profile);
CREATE INDEX IF NOT EXISTS idx_ops_result ON operations(result);
CREATE INDEX IF NOT EXISTS idx_verif_operation ON verification_checks(operation_id);
CREATE INDEX IF NOT EXISTS idx_routing_session ON routing_events(session_id);
CREATE INDEX IF NOT EXISTS idx_routing_to ON routing_events(routed_to);
CREATE INDEX IF NOT EXISTS idx_skill_name ON skill_events(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_session ON skill_events(session_id);
CREATE INDEX IF NOT EXISTS idx_ops_session ON operations(session_id);
CREATE INDEX IF NOT EXISTS idx_routing_timestamp ON routing_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_skill_timestamp ON skill_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_prospective_triggered ON prospective_log(triggered);
CREATE INDEX IF NOT EXISTS idx_prospective_ts ON prospective_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_reflections_type ON reflections(reflection_type);
CREATE INDEX IF NOT EXISTS idx_reflections_applied ON reflections(applied);
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON key_decisions(timestamp);
"""

def init_experience_db(db_path: Path = None, seed: bool = True) -> List[str]:
    """Programmatic initialization of Experience Index database schema."""
    target_path = Path(db_path) if db_path else Path(DB_PATH)
    ensure_directories()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.executescript(SCHEMA)
    conn.commit()

    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    if seed and conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0:
        conn.executescript("""
            INSERT INTO operations (id, timestamp, session_id, profile, action, target, result, duration_ms, metadata)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'default', 'setup', 'databases', 'success', 150, '{}');
            
            INSERT INTO verification_checks (id, timestamp, operation_id, expected_result, actual_result, passed, notes)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 1, 'all healthy', 'all healthy', 1, 'Initial verification passed');
            
            INSERT INTO routing_events (id, timestamp, session_id, input_summary, routed_to, route_reason, confidence, outcome)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'verify systems', 'oracle', 'reference query', 0.95, 'success');
            
            INSERT INTO skill_events (id, timestamp, session_id, skill_name, trigger, success, duration_ms)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'verify_stack', 'health_check', 1, 250);
            
            INSERT INTO reflections (id, timestamp, session_id, reflection_type, content, applied)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'pattern', 'Setup works reliably', 0);
            
            INSERT INTO key_decisions (id, timestamp, session_id, decision, rationale)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'Use SQLite for Personal Organizer', 'Deterministic, no external deps');
            
            INSERT INTO prospective_log (id, timestamp, session_id, cue, action_taken, triggered)
            VALUES (1, strftime('%Y-%m-%dT%H:%M:%SZ','now'), 'setup-001', 'monthly billing', 'check dates', 0);
        """)
        conn.commit()

    conn.close()
    return tables

# Backward compatibility alias
init_experience_db = init_experience_db


def main():
    parser = argparse.ArgumentParser(description="Initialize Cortex Experience Index database.")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm without prompting")
    args = parser.parse_args()

    # Ensure all directory structure exists (cross-platform)
    created = ensure_directories()
    if created:
        for d in created:
            print(f"  [created] {d}")
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    if os.path.exists(DB_PATH) and not args.yes:
        if sys.stdin.isatty():
            response = input(f"Database already exists at {DB_PATH}. Re-apply schema? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                return 0
        else:
            print(f"Database exists at {DB_PATH}. Applying schema updates.")
    
    tables = init_experience_db(Path(DB_PATH), seed=True)
    
    print(f"[OK] Experience Index database initialized at: {DB_PATH}")
    print(f"[OK] Tables: {', '.join(tables)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
