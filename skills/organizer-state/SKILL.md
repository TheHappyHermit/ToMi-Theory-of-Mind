---
name: organizer-state
version: 2.0.0
description: >
  Manage organizer.db tasks, projects, subscriptions, and records.
  Use for CRUD operations on operational state.
---

# Organizer State Skill

## Purpose

Manage the organizer database for tasks, projects, subscriptions, and records.

## Database Path (Cross-Platform)

The organizer database path is resolved in this order:
1. `ORGANIZER_DB_PATH` environment variable (if set)
2. Default: `~/.hermes/personal-organizer/data/organizer.db`

This works on Linux, macOS, and Windows because `~` expands to the user's home directory on all three platforms.

### Creating the Database Directory

Only needed if the live directory is missing. Do NOT run this against the
retired cortex path — `~/.other-repo/` was decommissioned in the
2026-09-29 data-root migration, and recreating it resurrects a tree nothing
reads any more.

```bash
mkdir -p ~/.hermes/personal-organizer/data
```

### Custom Path Override

```bash
export ORGANIZER_DB_PATH="/custom/path/to/organizer.db"
```

## Workflow

### Creating Tasks (corpus corrected)

When creating a task for the user, the `description` field must be self-contained enough that a future session can reconstruct the full context without re-reading the originating conversation. Include:

- **What** — the concrete action (not just a label)
- **Why** — the reason this exists, so the user's intent is recoverable
- **Exact commands, paths, or configuration** — copy the actual command text, not a paraphrase
- **Environment/shell context** — if the user mentioned a specific shell, venv, conda env, or prompt prefix (e.g. `.b sync_env` appearing before their login), record it; this prevents "do you have access to what I need?" confusion later
- **Dependencies / prerequisites** — anything that must be true first (e.g. "sudo available", "package candidate is 3.45.1-1ubuntu2.7")
- **Done-condition** — how you and the user will know it's complete

A description that is just a short noun phrase ("Install sqlite3 CLI") loses the why and forces the next session to re-search history. Treat a weak description as a defect in the task record, not a finished task.

Example (good description):

> Run: `sudo apt install sqlite3` (candidate 3.45.1-1ubuntu2.7). Needed so DB integrity/schema checks can use the `sqlite3` CLI directly instead of routing through Python. User was prompted with `.b sync_env` before their login — verify the active shell/python environment has sqlite3 on PATH after install, and confirm the organizer DB path convention (`~/.hermes/personal-organizer/data/organizer.db`) is reachable from that environment before marking complete.

### 1. Read State

Query the database for current state:
```python
import sqlite3
import os
from pathlib import Path

# THE LIVE PATH. ~/.hermes/personal-organizer/data/organizer.db
#   Verified 2026-09-30: 180 KB, tables = chat_messages, intentions,
#   reminders, tasks, important_dates, projects, subscriptions,
#   waiting_states. 24 active tasks at last check.
#
# TWO DECOYS THAT HAVE COST TIME:
#   ~/organizer.db                        -> 0 bytes, no tables. Not it.
#   ~/.other-repo/personal-state/...   -> path does not exist. The
#     cortex root was retired in the 2026-09-29 data-root migration; this
#     fallback was never updated and silently opened an empty database,
#     which is how a task write can appear to succeed and vanish.
def organizer_db_path() -> Path:
    env = os.environ.get("ORGANIZER_DB_PATH")
    candidates = [Path(env)] if env else []
    candidates.append(
        Path.home() / ".hermes/personal-organizer/data/organizer.db")
    for c in candidates:
        if c.is_file() and c.stat().st_size > 0:
            return c
    # Never fall through to a default: an empty or missing DB would let a
    # write succeed into nothing. Fail where the mistake is visible.
    raise FileNotFoundError(
        "organizer.db not found. Tried: %s. Set ORGANIZER_DB_PATH if it "
        "lives elsewhere." % ", ".join(str(c) for c in candidates))

db_path = organizer_db_path()
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys=ON")
tasks = conn.execute(
    "SELECT * FROM tasks WHERE status != 'completed'").fetchall()
```

### 2. Update State

Create, update, or complete records:
```python
conn.execute("INSERT INTO tasks (title, status, priority) VALUES (?, ?, ?)",
             ("New task", "next", "high"))
conn.commit()
```

### 3. Generate Views

Refresh markdown views from the database using `generate_views.py`.

### 4. Audit Changes

Log significant state changes in the audit log:
```python
conn.execute("INSERT INTO audit_log (action, details, timestamp) VALUES (?, ?, ?)",
             ("task_completed", "Task X completed", datetime.now().isoformat()))
conn.commit()
```

## Database Schema

Key tables:
- `tasks` — Tasks with status, priority, deadlines
- `projects` — Projects with status and definitions of done
- `subscriptions` — Active subscriptions with billing info
- `purchases` — Purchase records with receipts
- `shipments` — Tracking info for orders
- `warranties` — Warranty coverage records
- `audit_log` — Change history

## Security

- Never expose database credentials
- Use parameterized queries to prevent SQL injection
- Back up before bulk operations
