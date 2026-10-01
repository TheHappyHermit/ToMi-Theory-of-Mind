#!/usr/bin/env python3
"""
Integrity checker for organizer.db.
Runs foreign key checks, integrity checks, and schema validation.
"""

import sqlite3
import os
import sys
import json
from datetime import datetime, timezone

def _resolve_hermes_data_dir() -> str:
    if os.environ.get("HERMES_DATA_DIR"):
        return os.path.abspath(os.environ["HERMES_DATA_DIR"])
    if os.environ.get("HERMES_HOME"):
        return os.path.abspath(os.environ["HERMES_HOME"])
    if os.environ.get("CORTEX_HOME"):
        return os.path.abspath(os.environ["CORTEX_HOME"])
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = os.path.join(os.environ["LOCALAPPDATA"], "hermes")
        if os.path.exists(win_hermes):
            return win_hermes
    default_hermes = os.path.join(os.path.expanduser("~"), ".hermes")
    if os.path.exists(default_hermes):
        return default_hermes
    legacy_hermes = os.path.join(os.path.expanduser("~"), ".hermes")
    if os.path.exists(legacy_hermes):
        return legacy_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return os.path.join(os.environ["LOCALAPPDATA"], "hermes")
    return default_hermes

HERMES_DATA_DIR = _resolve_hermes_data_dir()

def _resolve_organizer_db() -> str:
    for env_var in ("ORGANIZER_DB_PATH", "ORGANIZER_DB"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return os.path.abspath(val)
    return os.path.join(HERMES_DATA_DIR, "personal-organizer", "data", "organizer.db")

DB_PATH = _resolve_organizer_db()
REPORTS_DIR = os.environ.get("INTEGRITY_REPORTS", os.path.join(HERMES_DATA_DIR, "personal-organizer", "data", "integrity-reports"))


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_integrity(conn):
    """Run SQLite integrity check."""
    c = conn.cursor()
    result = c.execute("PRAGMA integrity_check").fetchone()
    return result[0] == "ok" if result else False


def check_foreign_keys(conn):
    """Check foreign key violations."""
    c = conn.cursor()
    violations = c.execute("PRAGMA foreign_key_check").fetchall()
    # Format tuple (table, rowid, parent_table, fkid)
    formatted = []
    for v in violations:
        formatted.append({
            "table": v[0],
            "rowid": v[1],
            "parent_table": v[2],
            "fkid": v[3]
        })
    return formatted


def check_tables(conn):
    """Verify all expected tables exist."""
    expected = [
        "tasks", "projects", "subscriptions",
        "important_dates", "intentions", "waiting_states"
    ]

    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in c.fetchall()}

    missing = [t for t in expected if t not in existing]
    return missing


def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        return 1

    os.makedirs(REPORTS_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    report = {
        "timestamp": utcnow(),
        "database": DB_PATH,
        "checks": {}
    }

    integrity_ok = check_integrity(conn)
    report["checks"]["integrity"] = "PASS" if integrity_ok else "FAIL"

    violations = check_foreign_keys(conn)
    report["checks"]["foreign_keys"] = "PASS" if not violations else f"FAIL ({len(violations)} violations)"
    if violations:
        report["checks"]["fk_violations"] = violations

    missing = check_tables(conn)
    report["checks"]["tables"] = "PASS" if not missing else f"FAIL (missing: {missing})"

    report["status"] = "HEALTHY" if (
        integrity_ok and not violations and not missing
    ) else "UNHEALTHY"

    report_path = os.path.join(REPORTS_DIR, f"integrity_{utcnow().replace(':', '-')}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")

    conn.close()

    return 0 if report["status"] == "HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(main())
