#!/usr/bin/env python3
"""
Database backup utility.
Creates transactionally safe backups of organizer.db.
"""

import sqlite3
import os
import sys
import glob
from datetime import datetime, timezone

def _resolve_hermes_data_dir() -> str:
    if os.environ.get("HERMES_DATA_DIR"):
        return os.path.abspath(os.environ["HERMES_DATA_DIR"])
    if os.environ.get("HERMES_HOME"):
        return os.path.abspath(os.environ["HERMES_HOME"])
    if os.environ.get("CORTEX_HOME"):
        return os.path.abspath(os.environ["CORTEX_HOME"])
    if os.environ.get("HERMES_HOME"):
        return os.path.abspath(os.environ["HERMES_HOME"])
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
BACKUP_ROOT = os.environ.get("BACKUP_ROOT_DIR", os.environ.get("BACKUP_ROOT", os.path.join(HERMES_DATA_DIR, "backups")))
DAILY_DIR = os.path.join(BACKUP_ROOT, "daily")
WEEKLY_DIR = os.path.join(BACKUP_ROOT, "weekly")
MONTHLY_DIR = os.path.join(BACKUP_ROOT, "monthly")

# Default database - try multiple paths in order
ORGANIZER_DB = os.environ.get("ORGANIZER_DB_PATH") or os.environ.get("ORGANIZER_DB")
if not ORGANIZER_DB:
    candidate = os.path.join(HERMES_DATA_DIR, "personal-organizer", "data", "organizer.db")
    if os.path.exists(candidate):
        ORGANIZER_DB = candidate
if not ORGANIZER_DB:
    candidate = os.path.join(HERMES_DATA_DIR, "personal-organizer", "organizer.db")
    if os.path.exists(candidate):
        ORGANIZER_DB = candidate
if not ORGANIZER_DB:
    ORGANIZER_DB = os.path.join(HERMES_DATA_DIR, "personal-organizer", "data", "organizer.db")

# Retention policy
DAILY_RETENTION = 14
WEEKLY_RETENTION = 8
MONTHLY_RETENTION = 12


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_sqlite(src, dest_dir, prefix=""):
    """Create a transactionally safe SQLite backup using the backup API."""
    os.makedirs(dest_dir, exist_ok=True)

    if not os.path.exists(src):
        print(f"Source not found: {src}", file=sys.stderr)
        return False

    timestamp = utcnow()
    filename = f"{prefix}{timestamp}.db" if prefix else f"{timestamp}.db"
    dest = os.path.join(dest_dir, filename)

    try:
        src_conn = sqlite3.connect(src)
        dst_conn = sqlite3.connect(dest)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        print(f"Backed up: {src} -> {dest}")
        return True
    except Exception as e:
        print(f"Backup failed for {src}: {e}", file=sys.stderr)
        if os.path.exists(dest):
            os.remove(dest)
        return False


def cleanup_old_backups(directory, retention, pattern="*.db"):
    """Remove backups older than retention count."""
    if not os.path.exists(directory):
        return

    files = sorted(glob.glob(os.path.join(directory, pattern)), key=os.path.getmtime)
    while len(files) > retention:
        old = files.pop(0)
        os.remove(old)
        print(f"Removed old backup: {old}")


def main():
    timestamp = utcnow()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_of_week = datetime.now(timezone.utc).weekday()
    day_of_month = datetime.now(timezone.utc).day

    success = True

    # Daily backup
    print(f"\n=== Daily Backup ({date}) ===")
    success &= backup_sqlite(ORGANIZER_DB, DAILY_DIR, "organizer_")

    # Weekly backup (Sunday)
    if day_of_week == 6:
        print(f"\n=== Weekly Backup ({date}) ===")
        success &= backup_sqlite(ORGANIZER_DB, WEEKLY_DIR, "organizer_")

    # Monthly backup (1st of month)
    if day_of_month == 1:
        print(f"\n=== Monthly Backup ({date}) ===")
        success &= backup_sqlite(ORGANIZER_DB, MONTHLY_DIR, "organizer_")

    # Cleanup
    print("\n=== Retention Cleanup ===")
    cleanup_old_backups(DAILY_DIR, DAILY_RETENTION)
    cleanup_old_backups(WEEKLY_DIR, WEEKLY_RETENTION)
    cleanup_old_backups(MONTHLY_DIR, MONTHLY_RETENTION)

    if success:
        print("\nBackup completed successfully.")
        return 0
    else:
        print("\nBackup completed with errors.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
