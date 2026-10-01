#!/usr/bin/env python3
"""
Apply additive schema upgrades to Hermes Brain SQLite stores.

Idempotent: safe to run any time, a no-op when everything is already present.
Only CREATE INDEX IF NOT EXISTS and PRAGMA statements — no column changes, no
data rewrites, no DROP. See docs/SCHEMAS.md for the full assessment.

Usage: apply_schema_upgrades.py [--dry-run] [--strict]

Behaviour changes (2026-09-24):

* Paths resolve through scripts/_paths.py, so HERMES_HOME / HERMES_DATA_DIR /
  EXPERIENCE_DB_PATH / ORGANIZER_DB_PATH are honoured. The previous version
  hardcoded `os.path.expanduser("~/.hermes/...")`, which silently upgraded the
  wrong database (or none) on any non-default install.
* Foreign keys are enabled on every connection. Every writer in this project
  is required to do this or orphaned rows appear.
* A failed statement no longer results in a successful exit. Without --strict
  the script reports failures and exits 1 if any occurred, so a caller can act
  on the verdict. Previously it printed `[err]`, committed anyway, and exited 0.
* Applied migrations are recorded in a `_schema_migrations` table with a
  checksum, so re-runs can report what is already present.
"""

import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import experience_db_path, organizer_db_path  # noqa: E402

# Statements are additive by construction. If you need to add a column, add a
# new entry here rather than editing an existing one, and never emit DROP.
UPGRADES = {
    "experience.db": [
        "PRAGMA journal_mode=WAL;",
        "CREATE INDEX IF NOT EXISTS idx_ops_session ON operations(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_routing_timestamp ON routing_events(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_skill_timestamp ON skill_events(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_prospective_triggered ON prospective_log(triggered);",
        "CREATE INDEX IF NOT EXISTS idx_prospective_ts ON prospective_log(timestamp);",
    ],
    "organizer.db": [
        "PRAGMA journal_mode=WAL;",
        "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);",
        "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(remind_at) WHERE status = 'pending';",
        "CREATE INDEX IF NOT EXISTS idx_intentions_dormant ON intentions(status, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_waiting_followup ON waiting_states(follow_up_date);",
    ],
}

MIGRATION_TABLE = """
CREATE TABLE IF NOT EXISTS _schema_migrations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
"""


def _checksum(stmt: str) -> str:
    return hashlib.sha256(stmt.strip().encode("utf-8")).hexdigest()[:16]


def resolve_targets() -> dict:
    """Map a display label to an absolute path, honouring env overrides."""
    return {
        "experience.db": experience_db_path(),
        "organizer.db": organizer_db_path(),
    }


def already_applied(cur, label: str, stmt: str) -> bool:
    try:
        row = cur.execute(
            "SELECT 1 FROM _schema_migrations WHERE label = ? AND checksum = ?",
            (label, _checksum(stmt)),
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def record_applied(cur, label: str, stmt: str) -> None:
    try:
        cur.execute(
            "INSERT INTO _schema_migrations (label, checksum) VALUES (?, ?)",
            (label, _checksum(stmt)),
        )
    except sqlite3.Error:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be applied without changing anything")
    ap.add_argument("--strict", action="store_true",
                    help="Exit non-zero if any statement fails (default behaviour)")
    args = ap.parse_args()

    targets = resolve_targets()
    failures = 0
    applied = 0

    for label, statements in UPGRADES.items():
        db_path = targets[label]
        if not db_path.exists():
            print(f"[skip] {label}: not found at {db_path}")
            continue

        conn = sqlite3.connect(str(db_path))
        # Required for every writer in this project; without it SQLite accepts
        # orphaned rows that violate the schema's REFERENCES clauses.
        conn.execute("PRAGMA foreign_keys=ON")
        cur = conn.cursor()

        if not args.dry_run:
            try:
                cur.execute(MIGRATION_TABLE)
            except sqlite3.Error as e:
                print(f"[err] {label}: could not create _schema_migrations: {e}")
                failures += 1

        for stmt in statements:
            # Label the statement by its object name, not by a fixed token
            # index: stmt.split()[2] is "IF" for every CREATE INDEX, which made
            # the log read "index IF" instead of naming the index.
            if stmt.startswith("PRAGMA"):
                kind, name = "journal", stmt.split()[1].rstrip(";")
            else:
                kind = "index"
                parts = stmt.split()
                name = parts[5] if len(parts) > 5 else stmt[:40]

            if args.dry_run:
                print(f"[dry] {label}: {kind} {name}")
                continue

            if already_applied(cur, label, stmt):
                print(f"[=]  {label}: {kind} {name} (already applied)")
                continue

            try:
                cur.execute(stmt)
                record_applied(cur, label, stmt)
                applied += 1
                print(f"[ok] {label}: {kind} ensured ({name})")
            except sqlite3.Error as e:
                # Previously this printed and continued, then committed and
                # exited 0 -- reporting success for a failed migration.
                failures += 1
                print(f"[err] {label}: {kind} {name} failed: {e}")

        if not args.dry_run:
            conn.commit()
            try:
                mode = cur.execute("PRAGMA journal_mode").fetchone()[0]
                print(f"      {label} journal_mode={mode}")
            except sqlite3.Error:
                pass
        conn.close()

    if args.dry_run:
        print("dry-run complete; nothing was changed.")
        return 0

    if failures:
        print(f"\nDONE WITH {failures} FAILURE(S), {applied} applied. "
              f"A migration did not apply cleanly.")
        return 1

    print(f"done. {applied} statement(s) applied; all already present or applied cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
