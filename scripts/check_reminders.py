#!/usr/bin/env python3
"""
Check reminders and due items in Personal Organizer.

This script checks for:
- Timed Reminders (dispatches via notify_dispatcher across Telegram, Discord, Email, SMS, Desktop)
- Tasks due today or overdue
- Subscriptions with upcoming renewals
- Important dates approaching
"""

import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

def _resolve_hermes_data_dir() -> Path:
    if os.environ.get("HERMES_DATA_DIR"):
        return Path(os.environ["HERMES_DATA_DIR"]).resolve()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).resolve()
    if os.environ.get("CORTEX_HOME"):
        return Path(os.environ["CORTEX_HOME"]).resolve()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win_hermes.exists():
            return win_hermes
    default_hermes = Path.home() / ".hermes"
    if default_hermes.exists():
        return default_hermes
    legacy_hermes = Path.home() / ".hermes"
    if legacy_hermes.exists():
        return legacy_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return default_hermes

HERMES_DATA_DIR = _resolve_hermes_data_dir()

def _resolve_organizer_db() -> str:
    for env_var in ("ORGANIZER_DB_PATH", "ORGANIZER_DB"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return os.path.abspath(val)
    return str(HERMES_DATA_DIR / "personal-organizer" / "data" / "organizer.db")

DB_PATH = _resolve_organizer_db()

# Import notify dispatcher
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from notify_dispatcher import dispatcher
except ImportError:
    dispatcher = None

def get_db():
    """Get database connection."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_timed_reminders():
    """Check and dispatch pending timed reminders whose trigger time has arrived."""
    conn = get_db()
    if not conn:
        return []
    
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT id, title, remind_at, channel, notes 
        FROM reminders 
        WHERE status = 'pending' AND (remind_at <= ? OR remind_at <= ?)
    """, (now_iso, now_local))
    due_reminders = cur.fetchall()

    dispatched = []
    for r in due_reminders:
        title = r["title"]
        channel = r["channel"] or "all"
        notes = r["notes"] or ""

        if dispatcher:
            results = dispatcher.dispatch(title, notes, channel=channel)
        else:
            print(f"[REMINDER] {title} {f'({notes})' if notes else ''}")
            results = {"local": "dispatched"}

        cur.execute("""
            UPDATE reminders 
            SET status = 'sent', sent_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') 
            WHERE id = ?
        """, (r["id"],))
        dispatched.append({"id": r["id"], "title": title, "channel": channel, "results": results})

    conn.commit()
    conn.close()
    return dispatched

def check_tasks():
    """Check for due and overdue tasks."""
    conn = get_db()
    if not conn:
        return []
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.execute(
        "SELECT id, title, due_at, priority FROM tasks WHERE status = 'active' AND due_at <= ? ORDER BY due_at",
        (today,)
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def check_subscriptions():
    """Check for upcoming subscription renewals."""
    conn = get_db()
    if not conn:
        return []
    
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    cursor = conn.execute(
        "SELECT id, name, next_billing_date, amount FROM subscriptions WHERE status = 'active' AND next_billing_date <= ? ORDER BY next_billing_date",
        (next_week,)
    )
    subs = cursor.fetchall()
    conn.close()
    return subs

def main():
    """Run all checks and dispatch alerts."""
    print("=== Personal Organizer Reminders & Schedule Check ===")
    print(f"Checked at: {datetime.now().isoformat()}\n")
    
    # 1. Timed Reminders
    reminders = check_timed_reminders()
    if reminders:
        print(f"DISPATCHED REMINDERS ({len(reminders)}):")
        for r in reminders:
            print(f"  [SENT] {r['title']} [Channel: {r['channel']}]")
    else:
        print("No pending timed reminders due right now.")
    
    print()
    
    # 2. Due Tasks
    tasks = check_tasks()
    if tasks:
        print(f"DUE/OVERDUE TASKS ({len(tasks)}):")
        for t in tasks:
            print(f"  - [{t['priority'].upper()}] {t['title']} (due: {t['due_at']})")
    else:
        print("No overdue tasks.")
    
    print()
    
    # 3. Subscriptions
    subs = check_subscriptions()
    if subs:
        print(f"UPCOMING SUBSCRIPTION RENEWALS ({len(subs)}):")
        for s in subs:
            print(f"  - {s['name']} (${s['amount']:.2f}, next billing: {s['next_billing_date']})")
    else:
        print("No upcoming subscriptions in the next 7 days.")

if __name__ == "__main__":
    main()
