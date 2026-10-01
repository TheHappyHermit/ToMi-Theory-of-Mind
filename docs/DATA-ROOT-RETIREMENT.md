# Data Root Retirement: `~/.autognosia` → `~/.hermes`

**Status: complete. 2026-09-26.**

The data root was `~/.autognosia`. It is now `~/.hermes`. This file records
what moved, what was deliberately left behind, and which names are dead, so
that the old name does not creep back into a fresh install or a new script.

Nothing here is required to install Hermes Brain. A fresh clone provisions
into `~/.hermes` and never creates the old directory. This is a record of a
completed change on one machine.

---

## The current layout

| Path | What it is |
|---|---|
| `~/.hermes/` | The data root. Wiki, oracle brain, exchange, research, organizer, logs, databases. |
| `~/.hermes/autognosia.db` | Activity database. **The filename was kept deliberately — see below.** |
| `~/.hermes/oracle/brain/graphify-out/graph.json` | Oracle associative graph (~20 MB, 6,283 nodes). |
| `~/.hermes/active-wiki/graphify-out/graph.json` | Active Wiki graph (~3 MB, 1,007 nodes). |
| `~/.hermes/personal-organizer/data/organizer.db` | The populated organizer database (21 tasks). |

`HERMES_DATA_DIR` in [`cron/VARIABLES.md`](../cron/VARIABLES.md) is the
variable to set, not a literal path. It defaults to the dot-directory root.
Scripts should read it rather than hardcoding `~/.hermes`, so a non-default
install keeps working.

### Why `autognosia.db` kept its name

The database file was renamed before its consumers were rewritten, and the
consumers were numerous and live. Renaming the file would have broken every
one of them silently — a SQLite path that does not resolve is a file that is
created empty, not an error. Renaming the *directory* underneath it was the
safe half of the change: one path edit per consumer, and a missing directory
fails loudly.

So: the directory is `~/.hermes/`, and inside it the activity database is
still `autognosia.db`. If that file is ever renamed, every consumer has to be
moved in the same commit.

---

## What is retired

| Old name | State | Notes |
|---|---|---|
| `~/.autognosia/` | **Gone** | Held one orphaned script at the end. Removed after the replacement was verified. |
| `~/autognosia/` | **Renamed** to `~/old_Autognosia/` | 2.5 GB git clone of `github.com/TheHappyHermit/Autognosia`. Name changed so it reads as deletable later. |
| `~/bak_autognosia/` | **Kept** | 2.9 GB rollback copy of the pre-migration tree. Retain for a few days of stable operation, then decide. |
| `~/.local/bin/gbrain` | **Removed** | Shim for a tool no longer deployed. Moved to `migration-backup-20260926/removed-binaries/`. |

`~/old_Autognosia/` still has 376 modified files and 4 stashes in its working
tree. It was renamed, not cleaned. Nothing references it.

---

## Why the old directory was renamed and not deleted

The point was to make stale dependencies fail. If `~/.autognosia` still
existed, a script still pointing at it would keep working off three-week-old
data, and the system would look healthy while reading the wrong thing. Renaming
it means:

- a consumer that still uses the old path fails immediately and visibly;
- the data is still on disk if it turns out to be needed.

This is the reason `verify_stack.py` and `graph_health_check.py` are written to
fail rather than default to zero. A check that cannot fail is worse than no
check, because it converts a broken path into a green result.

---

## How the migration was done

1. **Pause every writer.** Nine cron jobs were paused: wiki cognition, Graphify
   ingestion, daily briefing, research exchange, Oracle night research, both
   online lanes, experience capture, integrity check. Verified no enabled job
   referenced the old root, and `lsof` showed no open handles.
2. **Wait for in-flight work.** A cognition run was already executing. It was
   allowed to finish before anything moved.
3. **Preserve conflicts.** 165 target-only or differing files were backed up
   before the source tree was merged in, so nothing was silently overwritten.
4. **Copy, verify, then rename.** `rsync -a` for six data trees plus the
   activity database, each verified, and only then was the old root renamed.
5. **Repoint consumers.** 15 scheduler entries, both script trees, the
   to-do hook, the organizer bind mount, and 20 repo files. The organizer
   container was stopped before its mount changed, and recreated after.
6. **Resume, then check for drift.** All nine jobs resumed, then
   `check_cron_drift.py` confirmed the live jobs match the template once
   machine-specific variables are expanded.

Docker Compose projects were separated at the same time (`honcho` and
`organizer`, previously sharing one project name and deleting each other's
services). Existing volume names are pinned in the compose files so the
PostgreSQL data is not orphaned by a project rename.

---

## Things that bit during this, worth not rediscovering

**A check that reads nothing reports success.** The old
`graphify_health_check.py` printed a green tick comparing `0 == 0` for both
graphs, immediately after reporting both as MISSING. It had read no files. The
replacement refuses to pass when either side is zero. See
`scripts/graph_health_check.py` and `tests/test_graph_health_check.py`.

**`mkdir` mode is masked by the umask.** `scripts/init_db.py` and
`scripts/init_experience_db.py` walk a list of directories including
`secrets`, so a fresh install created a world-readable secrets directory and
the health check then failed on a correct install. Both now create it 700 and
`chmod` explicitly, because passing `mode=` alone is not sufficient.

**Do not create a directory to satisfy a check.** `~/personal-agent/secrets`
exists, is empty, and is mode 700. It is the only secrets directory that
exists. `~/.hermes/secrets` was not created to make validation pass. Which
location is canonical is still undecided.

---

## Anything still carrying the old name

| Where | Kind | Should it change? |
|---|---|---|
| `~/.hermes/autognosia.db` | Live database | No — see above. |
| Docker volumes `autognosia-honcho_*` | Live data (137 MB Postgres) | No. Renaming orphans the data. |
| `cognition-arena/VERIFICATION.md` | Forensic record of the rename | No. It documents what happened. |
| `PROPOSED-BRAIN-ARCHITECTURE.md` | "Lost on main" history table, already marked superseded | No. |
| Old systemd units `autognosia-commanddeck`, `autognosia-dashboard` | Stopped and disabled, unit files retained | Optional cleanup. |
| `bak_autognosia`, `old_Autognosia` | Rollback and old repo | Delete once stable, on purpose. |

Cron job IDs and profile names were left alone. Renaming a job ID orphans its
execution history for no operational gain.
