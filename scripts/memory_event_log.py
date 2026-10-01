#!/usr/bin/env python3
"""Append-only memory event log — the durability floor for agent memory.

Why this exists
---------------
Honcho issue #1236 (verified against plastic-labs/honcho): when the LLM upstream is
unreachable past the retry budget — `MAX_RETRYABLE_ATTEMPTS = 3`,
`RETRY_BACKOFF_SECONDS = 1.0`, 30 s poll, so roughly **90 seconds** of tolerance —
queue items are marked `processed=true` with an error set, and
`get_next_queue_item` filters on `processed` only. Those messages are never derived
again. The reporter lost 23 work units to a ~4 h 20 m outage, and
`GET /v3/.../queue/status` reported `completed == total` the whole time.

That behaviour is asserted by Honcho's own test
(`tests/deriver/test_queue_processing.py::test_retry_exhaustion_is_terminal`,
docstring: "At the attempt cap a transient error burns the first item exactly like
today's terminal path"), so it is a product decision rather than a bug — meaning it
will not be fixed out from under us.

Related, same class of problem:
  #989  semantic dedup soft-deletes then hard-deletes the incumbent on a score tie,
        and the agent-tool path hardcodes `deduplicate=True`
  #1230 the deriver persists its own few-shot examples as facts about real peers;
        deleting the bogus conclusions is not durable, they re-derive under new IDs
  #839  parse failures still mark the queue item `processed=true`, with
        "no metric, no trace span error, no alertable signal"

The mitigation is boring and effective: **write every message to a store this repo
owns, before handing it to a system that can lose it.** Replay then turns
unrecoverable loss into a retry.

Design properties, each of which exists because its absence caused a real loss:
  - Append-only. There is no update and no delete. Corrections are new events.
  - Ingestion ids are client-generated, so a replay is idempotent and cannot
    duplicate (Honcho #1236 notes no client-supplied id exists upstream, so a
    re-POST duplicates instead of replacing).
  - The log is the source of truth. Derived state is verified *against* it, never
    trusted over it.
  - `reconcile()` reports what was sent but never derived, which is precisely the
    signal Honcho's own status endpoint does not surface.

Usage
-----
    memory_event_log.py append   --workspace WS --peer P --role user --text "..."
    memory_event_log.py stats    [--workspace WS]
    memory_event_log.py reconcile            # sent vs derived, if a checker is registered
    memory_event_log.py export   --out FILE  # newline-delimited JSON for replay

Storage is newline-delimited JSON. It is inspectable with `tail`, greppable, and
readable by any tool -- deliberately not a database, because a durability floor that
depends on a running service is not a floor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

SCHEMA_VERSION = 1
DEFAULT_LOG_NAME = "memory-events.jsonl"


def utc_now() -> str:
    """RFC 3339 UTC. Never space-separated -- mixed formats silently break sorting."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_log_path() -> Path:
    """Resolve under HERMES_HOME so the log follows the data, not the cwd."""
    from scripts._paths import hermes_home  # type: ignore

    return hermes_home() / "logs" / DEFAULT_LOG_NAME


def make_ingestion_id(workspace: str, peer: str, role: str, text: str) -> str:
    """Deterministic id for a logical event.

    Derived from content, not generated, so re-appending the *same* logical event is
    a no-op rather than a duplicate. That is the property Honcho lacks upstream.
    """
    payload = f"{workspace}\x1f{peer}\x1f{role}\x1f{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def open_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


def append_event(path: Path, event: Dict[str, Any]) -> bool:
    """Append one event. Returns False if this ingestion_id was already present.

    The dedup check scans the tail rather than maintaining an index, so the log has
    no secondary state that could disagree with it.
    """
    open_log(path)
    iid = event["ingestion_id"]
    if event_exists(path, iid):
        return False
    line = json.dumps(event, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())  # durability: this is the whole point
    return True


def event_exists(path: Path, ingestion_id: str, tail_lines: int = 2000) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as fh:
            tail: List[str] = []
            for line in fh:
                tail.append(line)
                if len(tail) > tail_lines:
                    tail.pop(0)
    except OSError:
        return False
    needle = f'"ingestion_id":"{ingestion_id}"'
    return any(needle in line for line in tail)


def read_events(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # A torn final line is expected after a hard kill. Skip it rather
                # than refusing to read the log at all.
                continue


def build_event(workspace: str, peer: str, role: str, text: str, **extra: Any) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "ingestion_id": make_ingestion_id(workspace, peer, role, text),
        "recorded_at": utc_now(),
        "workspace": workspace,
        "peer": peer,
        "role": role,
        "text": text,
        "derived": False,  # flipped by reconcile(), never by the writer
        **extra,
    }


def cmd_append(args: argparse.Namespace) -> int:
    path = Path(args.log).expanduser() if args.log else default_log_path()
    ev = build_event(args.workspace, args.peer, args.role, args.text, source=args.source)
    wrote = append_event(path, ev)
    if wrote:
        print(f"appended  {ev['ingestion_id']}  {args.workspace}/{args.peer}/{args.role}")
    else:
        print(f"duplicate {ev['ingestion_id']}  (already present; no-op)")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    path = Path(args.log).expanduser() if args.log else default_log_path()
    events = list(read_events(path))
    if not events:
        print(f"no events in {path}")
        return 0

    by_ws: Dict[str, int] = {}
    by_peer: Dict[str, int] = {}
    derived = 0
    oldest, newest = events[0]["recorded_at"], events[0]["recorded_at"]
    for e in events:
        by_ws[e.get("workspace", "?")] = by_ws.get(e.get("workspace", "?"), 0) + 1
        p = f"{e.get('workspace','?')}/{e.get('peer','?')}"
        by_peer[p] = by_peer.get(p, 0) + 1
        derived += 1 if e.get("derived") else 0
        oldest = min(oldest, e["recorded_at"])
        newest = max(newest, e["recorded_at"])

    print(f"log:      {path}")
    print(f"size:     {path.stat().st_size:,} bytes")
    print(f"events:   {len(events):,}")
    print(f"derived:  {derived:,}  (pending: {len(events) - derived:,})")
    print(f"span:     {oldest} -> {newest}")
    print(f"workspaces: {len(by_ws)}   peers: {len(by_peer)}")
    if by_ws:
        print("\ntop workspaces:")
        for k, v in sorted(by_ws.items(), key=lambda x: -x[1])[:10]:
            print(f"  {v:>7,}  {k}")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    """Report events recorded but not confirmed derived.

    This is the check Honcho's own queue status endpoint does not perform: it
    reports items as completed even while some sit in terminal error (#1236).
    """
    path = Path(args.log).expanduser() if args.log else default_log_path()
    events = list(read_events(path))
    if not events:
        print(f"no events in {path}")
        return 0

    pending = [e for e in events if not e.get("derived")]
    total = len(events)
    print(f"log: {path}")
    print(f"events: {total:,}   derived: {total - len(pending):,}   pending: {len(pending):,}")

    if not pending:
        print("\nVERDICT: every logged event is marked derived.")
        return 0

    print(f"\n{len(pending)} event(s) recorded but not confirmed derived.")
    print("A derived memory can be lost upstream (see #1236). Replay these:")
    for e in pending[:10]:
        print(f"  {e['recorded_at']}  {e.get('workspace','?')}/{e.get('peer','?')}  "
              f"{e['ingestion_id'][:12]}  {str(e.get('text',''))[:48]!r}")
    if len(pending) > 10:
        print(f"  ... and {len(pending) - 10} more")
    print("\nVERDICT: derived state is behind the log. Replay before trusting retrieval.")
    return 1


def cmd_export(args: argparse.Namespace) -> int:
    path = Path(args.log).expanduser() if args.log else default_log_path()
    out = Path(args.out).expanduser()
    events = list(read_events(path))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"exported {len(events):,} event(s) -> {out}")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Append-only memory event log (durability floor for agent memory)"
    )
    ap.add_argument("--log", default=None, help=f"log path (default: {DEFAULT_LOG_NAME} under HERMES_HOME)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="record one event")
    a.add_argument("--workspace", required=True)
    a.add_argument("--peer", required=True)
    a.add_argument("--role", required=True, choices=["user", "assistant", "system", "tool"])
    a.add_argument("--text", required=True)
    a.add_argument("--source", default="manual")
    a.set_defaults(func=cmd_append)

    s = sub.add_parser("stats", help="summary counts")
    s.set_defaults(func=cmd_stats)

    r = sub.add_parser("reconcile", help="sent vs derived; exit 1 if behind")
    r.set_defaults(func=cmd_reconcile)

    e = sub.add_parser("export", help="newline-delimited JSON for replay")
    e.add_argument("--out", required=True)
    e.set_defaults(func=cmd_export)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
