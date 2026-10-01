#!/usr/bin/env python3
"""
Export the Sept 13-27 conversation window out of Honcho to plain text.

Read-only against the database. Writes markdown files to the target
directory. This is a safety copy: Honcho's own search is broken (the deriver
cannot embed, so honcho_search returns nothing for this window), and the
conversation is currently only reachable by direct SQL.

Usage:
    export_honcho_window.py --start 2026-09-13 --end 2026-09-28
"""
import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

DB = "honcho-database-1"
PSQL = ["docker", "exec", DB, "psql", "-U", "honcho", "-d", "honcho", "-tA", "-F", "\x1f", "-c"]


def q(sql):
    r = subprocess.run(PSQL + [sql], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f"SQL failed: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-09-13")
    ap.add_argument("--end", default="2026-09-28")
    ap.add_argument("--out", default="/home/operator/.hermes/archives/conversation-export")
    args = ap.parse_args()

    rows = q(f"""
        SELECT created_at, content
        FROM messages
        WHERE created_at >= '{args.start}' AND created_at < '{args.end}'
        ORDER BY created_at;
    """)

    by_day = defaultdict(list)
    total = 0
    for line in rows.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) < 2:
            continue
        ts, content = parts[0].strip(), "\x1f".join(parts[1:])
        day = ts[:10]
        by_day[day].append((ts, content))
        total += 1

    if not total:
        print("  no messages in that window")
        return 1

    os.makedirs(args.out, exist_ok=True)
    index = []

    for day in sorted(by_day):
        path = os.path.join(args.out, f"{day}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Conversation log {day}\n\n")
            f.write(f"Exported from Honcho on {datetime.now():%Y-%m-%d %H:%M}. ")
            f.write(f"{len(by_day[day])} messages.\n\n---\n\n")
            for ts, content in by_day[day]:
                hhmm = ts[11:16]
                f.write(f"## {hhmm}\n\n{content.strip()}\n\n")
        size = os.path.getsize(path)
        index.append((day, len(by_day[day]), size))
        print(f"  {day}  {len(by_day[day]):4d} messages  {size/1024:8.1f} KB  -> {path}")

    meta = {
        "exported_at": datetime.now().isoformat(),
        "window": [args.start, args.end],
        "total_messages": total,
        "days": [{"date": d, "messages": n, "bytes": s} for d, n, s in index],
        "note": ("Honcho search (honcho_search / honcho_reasoning) does NOT cover this "
                 "window: the deriver cannot embed these messages, so they have no "
                 "vector and are not returned by semantic search. This export is the "
                 "retrieval path until the deriver is fixed."),
    }
    mpath = os.path.join(args.out, "EXPORT-MANIFEST.json")
    with open(mpath, "w") as f:
        json.dump(meta, f, indent=2)

    print()
    print(f"  total: {total} messages across {len(index)} days")
    print(f"  manifest: {mpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
