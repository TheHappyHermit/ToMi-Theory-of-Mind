#!/usr/bin/env python3
"""
Staleness check for brain sync sources. READ-ONLY. Exits non-zero when a
source has gone too long without syncing, so cron reports a failure.

Why this exists
---------------
oracle-brain stopped syncing on 2026-09-03 and nothing noticed for 25 days.
The sync itself never failed -- it simply was not scheduled to run again.
Its job was created after the month's only fire date had already passed, so
`last_run_at` stayed None and the gap was invisible from the job list.

`brain_sync.py --report-orphans` shows *what* is missing. This shows *how
long* it has been missing, which is the thing that would have surfaced it.

A source that stops syncing produces no error, no failed run, and no output.
The only evidence is the age of its last successful run.

Usage:
    check_sync_staleness.py              # check, print report
    check_sync_staleness.py --quiet      # print nothing unless stale

Exit codes:
    0  every source synced within its threshold
    1  at least one source is stale
    2  could not connect to the database
"""
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

# A source is stale if its last successful run is older than this.
# oracle-brain is a large, slow-moving archive, so it gets a longer window
# than the sources that back active work.
THRESHOLDS_HOURS = {
    "active-wiki": 48,
    "exchange-research": 48,
    "decisions": 72,
    "oracle-brain": 24 * 14,   # fortnightly
}

QUIET = "--quiet" in sys.argv


def main():
    try:
        import brain_sync
    except ImportError:
        print("cannot import brain_sync.py -- run from the repo scripts dir",
              file=sys.stderr)
        return 2

    try:
        conn = brain_sync.get_db()
    except Exception as e:
        print(f"[error] cannot connect to PostgreSQL: {e}", file=sys.stderr)
        return 2

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT source, max(last_run_at) FROM sync_state "
            "WHERE status = 'success' GROUP BY source"
        )
        last = {src: ts for src, ts in cur.fetchall()}
        cur.close()
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    stale = []
    unknown = []

    for source, limit_h in sorted(THRESHOLDS_HOURS.items()):
        ts = last.get(source)
        if ts is None:
            unknown.append(source)
            row = f"  {source:<20} NEVER SYNCED   (threshold {limit_h}h)"
        else:
            age_h = (now - ts).total_seconds() / 3600.0
            if age_h > limit_h:
                stale.append((source, age_h, limit_h))
                row = (f"  {source:<20} STALE         {age_h:8.1f}h old "
                       f"(threshold {limit_h}h)  last: {ts:%Y-%m-%d %H:%M}")
            else:
                row = f"  {source:<20} ok            {age_h:8.1f}h old"

        if not QUIET or ts is None or "STALE" in row:
            print(row)

    for source in unknown:
        print(f"  [warn] {source} has no successful run on record at all.",
              file=sys.stderr)

    if stale or unknown:
        print()
        print("  Sync staleness detected. The sync job for the source(s) above "
              "may not be firing.")
        print("  Compare against the cron schedule: a source that stops "
              "syncing produces no error, only silence.")
        return 1

    print()
    print("  All sources synced within threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
