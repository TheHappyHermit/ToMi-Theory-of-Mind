---
name: sqlite-schema-hygiene
description: Use when auditing SQLite schema conformance.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# SQLite Schema Hygiene

Class-level playbook distilled from the 2026-08-23 project remediation (24k rows normalized,
three live DBs, zero downtime). Reference implementation:
`~/.hermes/scripts/verify_schema_conformance.py`.

## Conformance checker design

Validate five axes per database: WAL journal mode, expected table set, FK orphan counts,
timestamp format conformance, and any envelope/package structure (e.g. versioned JSON in an
exchange dir). Rules:

1. **Derive expectations from actual schemas** — never guess column names. Read `PRAGMA table_info`
   / `foreign_key_list` first, then write checks. Guessing produced a broken validator once.
2. **Report violation COUNTS, never row dumps.** A validator that prints one line per bad row
   dumped 400 KB into context during a cron run and killed the session. Cap total output
   (~40 lines); per-column counts like `5595/5595 not RFC 3339` carry the same signal.
3. **Distinguish date-only columns from timestamps.** Columns like `due_at`, `next_billing_date`,
   `follow_up_date` legitimately hold `YYYY-MM-DD` — validate them against a DATE pattern, not
   RFC 3339, or every audit false-positives forever.
4. Exit 0/1 so cron health checks can gate on it.

## Backfill procedure (legacy formats → RFC 3339 UTC)

Root cause of legacy space-format stamps is almost always `DEFAULT (datetime('now'))` in DDL
(SQLite's `datetime('now')` emits `'YYYY-MM-DD HH:MM:SS'` UTC). Writers that omit the column
inherit it silently — find and fix ALL writers before backfilling, or drift returns:

```python
# Backup FIRST via the sqlite backup API (safe with WAL + open readers)
src = sqlite3.connect(db); dst = sqlite3.connect(bak_path); src.backup(dst)

conn.execute("PRAGMA foreign_keys=ON"); conn.execute("PRAGMA busy_timeout=15000")
SPACE_TS = "[0-9][0-9][0-9][0-9]-[0-9][0-2]-[0-9][0-2] [0-9][0-2]:[0-9][0-2]:[0-9][0-2]*"
# (a) space -> T + Z (SQLite datetime('now') is UTC, so appending Z is correct)
r1 = conn.execute(f"UPDATE {t} SET {c} = replace({c},' ','T') || 'Z' WHERE {c} GLOB '{SPACE_TS}'").rowcount
# (b) T-formatted but missing zone -> append Z
r2 = conn.execute(f"UPDATE {t} SET {c} = {c} || 'Z' WHERE {c} LIKE '____-__-__T__:__:__%' "
                  f"AND {c} NOT LIKE '%Z' AND {c} NOT LIKE '%+00:00'").rowcount
```

Microsecond variants (`2026-08-20T00:47:02.562660`) survive both guards — catch them with a
`LIKE '%.%'` pass truncating to 19 chars + `Z`. Commit per-DB inside try/rollback; re-run the
conformance checker afterward as proof.

## Writer-side fixes that prevent recurrence

- Schema DDL default: `strftime('%Y-%m-%dT%H:%M:%SZ','now')` instead of `datetime('now')`.
- For tables whose DEFAULT can't change without a rebuild (existing deployments), make INSERTs
  name the column explicitly with the same `strftime` expression.
- Naive writers: replace `datetime.now().isoformat()` (local time, +00:00 style) with
  `datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')`.
- After patching writers of long-running services (dashboard servers), RESTART them — old code
  keeps writing old formats until restarted.

## Inspecting live DBs safely

- **Read-only opens for any inspection**: `sqlite3.connect(f'file:{p}?mode=ro', uri=True)`.
  A plain `sqlite3.connect(path)` CREATES a 0-byte file if the path doesn't exist — this bit us
  when a diagnostic probe resurrected a deleted database file. Never point bare connects at
  retired/deleted paths.
- Parallel event logs happen when cron workdir resolution picks a different script copy
  than the one you edited. The 2026-08-23 remediation hit this: a writer existed at both
  `~/.hermes/scripts/x.py` and the same filename under the now-retired `~/.project/`
  data root, and both were appending. When two DBs hold overlapping data, grep every copy
  of the writer for its `DB_PATH` before assuming which is authoritative. Note the general
  shape rather than the specific paths: a retired data root does not delete the scripts
  that referenced it, and a renamed directory leaves the old copy live.
- Merging two event logs: offset child-table PKs by parent MAX(id) inside one transaction on the
  destination, preserve original timestamps verbatim, then `PRAGMA foreign_key_check` +
  `integrity_check` before retiring the source (keep a `.backup()` snapshot of the source first).

## Verification habit

After ANY schema/data change: run the conformance checker AND one functional probe (e.g. app
health endpoint, one INSERT through the patched writer path). Claimed ≠ done.
