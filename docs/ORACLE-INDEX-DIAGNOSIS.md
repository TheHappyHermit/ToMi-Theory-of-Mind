# Oracle-brain indexing — diagnosis

Added 2026-09-27. Read-only investigation; nothing was changed.

## The short answer

**Not a missing index, and not a broken script.** A job exists, is enabled,
and points at a real script. The problem is that it has **never run** — and
the reason is a cron expression that fires once a month, on a date that had
already passed when it was created.

Second finding: the job everyone assumed did this work
(`3a11d29b7c57` "Oracle Index Rebuild") **has nothing to do with
PostgreSQL**. It is a file-copy script from Active Wiki to the Oracle vault
directory. Zero database references. Its `last_status: ok` is real, but it
is not indexing anything into PostgreSQL.

## The actual state

    source              runs   most recent            total files
    active-wiki         705    2026-09-28 05:13       1935
    exchange-research   593    2026-09-28 05:13          1
    decisions           303    2026-09-28 05:13          1
    oracle-brain         16    2026-09-03 04:40        241

`oracle-brain` last synced **2026-09-03**, 25 days ago. Its 16 runs were all
in a burst on Sep 1–3 (the initial backfill, 206 + 35 files), after which
every run reported `files_synced: 0` — correct at the time, because nothing
had changed yet.

## The job: `3139cb23f854` "Brain-Sync Oracle (Sunday Night)"

    schedule:  0 2 1 * *      -> 02:00 on the 1st of EVERY MONTH
    next_run:  2026-10-01T02:00:00-07:00
    last_run:  None           -> has never run
    enabled:   true

The prompt is correct and complete — it calls
`brain_sync.py --source oracle-brain` and then
`verify_brain_sync.py --source oracle-brain`. It would work.

**Two things are wrong with it:**

1. **The name says "Sunday Night"; the schedule is monthly.** `0 2 1 * *` is
   day-of-month 1, not day-of-week. A Sunday schedule would be `0 2 * * 0`.
2. **It was created after the 1st had already passed this month**, so its
   first fire is 2026-10-01. From creation until then it does nothing.

The prompt also says "This is the large archive (1,455 files)". The actual
scannable count today is **2,102** — the vault has grown ~45% since.

## The 632-file gap

    all .md under ~/.hermes/oracle/brain      2181
    excluded: a path part starts with "."        78   (.meta/)
    excluded: inside graphify-out                 1
    SCANNABLE — what a sync would see           2102
    already in the database                     1470
    never indexed                                632

The 78 `.meta/` files are correctly skipped by `scan_source`, which ignores
any path component starting with `.`. That filter is not the problem.

## What the other Oracle jobs actually do

| Job | Schedule | What it really does |
| :--- | :--- | :--- |
| `3a11d29b7c57` Oracle Index Rebuild | `30 3 * * *` (daily) | Copies `.md` from Active Wiki to `~/.hermes/oracle/brain`. **0 database references.** Runs fine daily (rebuild-log.md shows copies on Sep 21, 22, 23, 24, 27). Not an indexer. |
| `1983f8c1f638` Oracle Knowledge Expansion | `45 2 * * *` (daily) | `fill_oracle_gaps.py` — research request generation. Not an indexer. |
| `b0c1d2e3f4a0` Graphify Oracle Brain | `0 5 * * *` (daily) | Graphify graph extraction. Not a text index. |
| `3139cb23f854` Brain-Sync Oracle | `0 2 1 * *` (monthly) | **The real one.** Never run. |

So the name "Oracle Index Rebuild" is actively misleading: it is the one job
that looks like it should keep the index current, and it does nothing of the
kind.

## Options

1. **Run it once now** — closes the 632-file gap immediately:
   ```
   /home/operator/.hermes/hermes-agent/venv/bin/python3 \
     /home/operator/hermes-brain/scripts/brain_sync.py --source oracle-brain
   ```
   This embeds ~632 files. At the historical rate (206 files in 23s, plus
   35 in 2.5s) expect a few minutes.

2. **Fix the schedule.** Monthly is defensible for an archive that changes
   slowly, but the vault is growing fast (2,181 files, newest today at
   21:41). Weekly (`0 2 * * 0`) or daily matches how fast it actually moves.

3. **Rename `3a11d29b7c57`.** "Oracle Index Rebuild" should not describe a
   file-copy job. Something like "Oracle Vault File Sync".

4. **Add a staleness alarm.** `--report-orphans` already reports
   "never indexed"; nothing alerts on it. A cron check that fails when
   `max(last_run_at)` for `oracle-brain` is older than N days would have
   caught 25 days of silence.

## Note on the earlier claim

An earlier commit in this series said `sync_state` had "no row for
`oracle-brain` at all". **That was wrong** — there are 16 rows, ending
2026-09-03. The check that produced it matched the wrong column name
(`last_synced` instead of `last_run_at`) and returned nothing, which was
read as "never synced" rather than "query wrong". `sync_state` is an
append-only log, not a one-row-per-source state table, so a
`SELECT ... WHERE source='oracle-brain'` that returns rows is expected; the
question is the date on the most recent one.
