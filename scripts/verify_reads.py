#!/usr/bin/env python3
"""verify_reads.py — fail-closed audit of the corpus distillation ledger.

The rule this enforces: **one whole-file `read_file` per file marked `[x]`.**

A prompt is a soft constraint. The rule has been written into the skill in plain
English and has still been broken, because a run that bulk-reads the corpus also
*looks* successful: contiguous marks, real paths, a clean `completed` status, a
larger arena. Only the read-to-mark ratio exposes it.

This script is that check. It is deliberately mechanical and deliberately
independent of the run that produced the ledger.

USAGE
    python3 scripts/verify_reads.py                  # audit the whole ledger
    python3 scripts/verify_reads.py --run <id>       # audit one run id
    python3 scripts/verify_reads.py --ledger <path>  # audit a specific ledger

EXIT CODES
    0  compliant
    1  NON-COMPLIANT — the ledger claims reads that did not happen
    2  could not verify (missing inputs) — never reports success on missing data

CAVEATS, STATED PLAINLY
    * The read side is reconstructed from the agent log, not from a durable
      per-read receipt. A read that happened but was not logged is counted as
      not-read, so this can report a false failure. It does not report a false
      success, which is the direction that matters.
    * Reads the live log AND every rotated sibling (agent.log.1, .2, ...).
      Reading only the live file produced a false NON-COMPLIANT verdict with a
      0.27 reads-per-mark ratio; with rotation handled the ratio is 1.41.

    * Per-pass verification reads the job's own RUNLOG (`read_file_calls` vs
      `rows_flipped`), not the count of tool patches. A run that reads 26
      files and updates ARENA.md, ARENA-EVIDENCE.md and VERIFICATION.md shows
      ~29 patches honestly; patch count cannot detect batching.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

DEFAULT_LEDGER = "/home/operator/hermes-brain/cognition-arena/LEDGER.md"
DEFAULT_ORDER = "/home/operator/hermes-brain/cognition-arena/ORDER.txt"
DEFAULT_LOG = "/home/operator/.hermes/logs/agent.log"
DEFAULT_RUNLOG = "/home/operator/hermes-brain/cognition-arena/RUNLOG.jsonl"
DEFAULT_EXEC_DB = "/home/operator/.hermes/cron/executions.db"
DEFAULT_JOB = "49280b099b12"
CORPUS_ROOT = "/home/operator/.hermes"

# Session ids look like cron_49280b099b12_20260925_232624
RUN_RE = re.compile(r"cron_([0-9a-f]{12})_(\d{8}_\d{6})")
READ_RE = re.compile(r"tool read_file completed \(([\d.]+)s,\s*([\d,]+) chars\)")
LEDGER_RE = re.compile(r"^\s*[-*]?\s*\[([ x\-!])\]\s*(.*)$")

# A single read_file returning more than this would be a bulk window or a
# concatenation rather than one source document.
#
# The threshold must sit ABOVE the read_file tool's own cap, not equal to it.
# `file_tools.py` sets _DEFAULT_MAX_READ_CHARS = 100_000, so a 100,000-char
# threshold flagged every legitimate read of a large file that hit the cap —
# 26 false positives, all of them real corpus documents. The tool truncates and
# returns `next_offset`; it does not bulk-read. Anything strictly above the cap
# genuinely indicates more than one document in one call.
#
# Measured 2026-09-27 across all rotated agent logs (3,589 reads):
#   p50 7,354 · p90 41,063 · p99 100,600 · max 102,080 · over_200k: 0
# The max clustering at ~102k is the cap, not bulk behaviour. 21 corpus .md
# files exceed 100KB, so reads above the cap are expected and legitimate.
SUSPICIOUS_READ_CHARS = 150_000


def fail(msg: str, code: int = 2) -> None:
    print(f"\n  CANNOT VERIFY: {msg}")
    print(f"  exit {code} — this is NOT a pass. Fix the input and re-run.")
    sys.exit(code)


def read_ledger(path: str) -> list[tuple[str, str]]:
    p = Path(path)
    if not p.is_file():
        fail(f"ledger not found: {path}")
    rows = []
    for line in p.read_text(errors="ignore").splitlines():
        m = LEDGER_RE.match(line)
        if m:
            rows.append((m.group(1), re.sub(r"^\d+\s+", "", m.group(2).strip())))
    if not rows:
        fail(f"ledger has no rows: {path}")
    return rows


def read_order(path: str) -> list[str]:
    p = Path(path)
    if not p.is_file():
        fail(f"ORDER.txt not found: {path}")
    return [l.strip() for l in p.read_text(errors="ignore").splitlines() if l.strip()]


def parse_log(path: str, job: str) -> tuple[dict[str, dict], list[str]]:
    """Per run id: read_file call count, and the char count of each read.

    Reads the live log AND every rotated sibling (agent.log.1, .2, ...), oldest
    first. Reading only the live file is what made this audit report a false
    failure: a run whose reads landed in a rotated file looked like a run with
    no reads at all, which then read as "the ledger claims reads that did not
    happen". Returns (runs, files_read).
    """
    p = Path(path)
    if not p.is_file():
        fail(f"agent log not found: {path}")

    # Oldest first so that if a run spans a rotation boundary its counts
    # accumulate in chronological order.
    siblings = sorted(
        [q for q in p.parent.glob(p.name + "*") if q.is_file()],
        key=lambda q: (q.suffix == "" and "zz" or q.suffix, q.name),
        reverse=True,
    )
    if not siblings:
        siblings = [p]

    runs: dict[str, dict] = collections.defaultdict(
        lambda: {"reads": 0, "chars": [], "patches": 0, "terminal": 0}
    )
    for log_file in siblings:
        with log_file.open(errors="ignore") as fh:
            for line in fh:
                m = RUN_RE.search(line)
                if not m or m.group(1) != job:
                    continue
                rid = m.group(2)
                rm = READ_RE.search(line)
                if rm:
                    runs[rid]["reads"] += 1
                    runs[rid]["chars"].append(int(rm.group(2).replace(",", "")))
                if "tool patch completed" in line:
                    runs[rid]["patches"] += 1
                if "tool terminal completed" in line:
                    runs[rid]["terminal"] += 1
    return runs, [str(q) for q in siblings]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="audit a single run id, e.g. 20260925_232624")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--order", default=DEFAULT_ORDER)
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--runlog", default=DEFAULT_RUNLOG)
    ap.add_argument("--job", default=DEFAULT_JOB)
    ap.add_argument(
        "--max-read-chars",
        type=int,
        default=SUSPICIOUS_READ_CHARS,
        help="a read_file larger than this is flagged as a bulk window",
    )
    args = ap.parse_args()

    print("=" * 68)
    print("  CORPUS DISTILLATION — READ COMPLIANCE AUDIT")
    print("=" * 68)

    rows = read_ledger(args.ledger)
    order = read_order(args.order)

    marked = [path for state, path in rows if state == "x"]
    states = collections.Counter(state for state, _ in rows)
    print(f"\n  LEDGER   {len(rows)} rows: " + ", ".join(f"[{k}]={v}" for k, v in sorted(states.items())))
    print(f"  marked   {len(marked)} read")
    print(f"  ORDER    {len(order)} paths")

    # --- structural checks -------------------------------------------------
    problems: list[str] = []
    if len(rows) != len(order):
        problems.append(f"ledger has {len(rows)} rows but ORDER.txt has {len(order)} paths")

    unknown = [p for p in marked if p not in order]
    if unknown:
        problems.append(f"{len(unknown)} marked path(s) are not in ORDER.txt: {unknown[:3]}")

    # contiguity from the front
    idx = [order.index(p) for p in marked if p in order]
    gaps = [i for i, v in enumerate(idx) if i and v != idx[i - 1] + 1]
    contiguous = not gaps
    print(f"  order    contiguous from line 1: {contiguous}")

    missing = [p for p in marked if not (Path(CORPUS_ROOT) / p).is_file()]
    if missing:
        problems.append(f"{len(missing)} marked path(s) do not exist on disk: {missing[:3]}")
    print(f"  on disk  {len(marked) - len(missing)}/{len(marked)} marked files exist")

    # --- the decisive check: reads vs marks --------------------------------
    runs, log_files_read = parse_log(args.log, args.job)
    if not runs:
        fail(
            f"no log entries for job {args.job} in {args.log} (or its rotated "
            "siblings). If every rotated file was already reclaimed, coverage "
            "is partial — this cannot be a pass."
        )
    total_reads = sum(r["reads"] for r in runs.values())
    total_chars = [c for r in runs.values() for c in r["chars"]]
    suspicious = [c for c in total_chars if c > args.max_read_chars]

    print(f"\n  RUNS     {len(runs)} runs in the log for job {args.job}")
    print(f"  log      {len(log_files_read)} file(s) read, incl. rotated siblings")
    for lf in log_files_read:
        print(f"             {lf}")
    print(f"  reads    {total_reads} read_file calls across those runs")
    print(f"  marks    {len(marked)} in the ledger")
    print(f"  ratio    {total_reads / len(marked):.2f} reads per mark" if marked else "  ratio    n/a")

    if suspicious:
        problems.append(
            f"{len(suspicious)} read_file call(s) returned more than "
            f"{args.max_read_chars:,} chars — bulk window, not one document "
            f"(largest: {max(suspicious):,})"
        )

    ratio = total_reads / len(marked) if marked else 0
    if marked and ratio < 1.0:
        problems.append(
            f"ledger claims {len(marked)} reads but the log shows only "
            f"{total_reads} read_file calls (ratio {ratio:.2f})"
        )

    # patch-heavy runs are the batching signature
    #
    # A "patch" here is ANY tool patch, not a ledger mark. The job also patches
    # ARENA.md, ARENA-EVIDENCE.md and VERIFICATION.md in the same run, so a
    # perfectly honest run that reads 26 files and updates its three narrative
    # outputs can legitimately show 29 patches. Comparing patch COUNT to read
    # count therefore cannot detect batching — it detects narrative writing.
    #
    # The job's own RUNLOG is the authoritative record of ledger marks, and it
    # is checked directly below against the ledger. This per-run column is
    # diagnostic context only, and is no longer a pass/fail signal.
    print("\n  per-run detail (patch count is diagnostic, not a verdict)")
    print(f"  {'run':<16} {'reads':>6} {'patches':>8} {'terminal':>9}  note")
    for rid in sorted(runs):
        r = runs[rid]
        if args.run and rid != args.run:
            continue
        note = ""
        if r["reads"] == 0:
            note = "NO read_file calls in the log window"
        elif any(c > args.max_read_chars for c in r["chars"]):
            note = f"read above {args.max_read_chars:,} chars"
        print(f"  {rid:<16} {r['reads']:>6} {r['patches']:>8} {r['terminal']:>9}  {note}")

    # The aggregate ratio alone is not sufficient: one huge burst of legitimate
    # reads in a single run can mask a batched run in another.
    #
    # The authoritative per-run check is the job's own RUNLOG, which records
    # `read_file_calls` and `rows_flipped` per pass. Those are directly
    # comparable. A pass that flipped more ledger rows than it read files is
    # the real batching signature. Measured 2026-09-27: 0 of 49 passes.
    # A missing per-pass record is missing data, not a pass. The aggregate ratio
    # alone cannot exclude a batched run, so without the RUNLOG this check has
    # no per-pass evidence and must not report success.
    runlog_path = Path(args.runlog)
    if not runlog_path.is_file():
        fail(
            f"RUNLOG not found: {args.runlog}. The per-pass check is the only "
            "check that can exclude a batched run — without it this audit has "
            "no per-pass evidence and cannot be a pass."
        )
    mismatched: list[str] = []
    checked = 0
    for line in runlog_path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            # A JSON array/scalar is not a pass record. Skip it rather than
            # crashing — but it does not count as a verifiable pass either.
            continue
        reads_n = entry.get("read_file_calls")
        flipped = entry.get("rows_flipped")
        if isinstance(reads_n, bool) or isinstance(flipped, bool):
            continue
        if not isinstance(reads_n, int) or not isinstance(flipped, int):
            continue
        checked += 1
        if flipped > reads_n:
            mismatched.append(str(entry.get("run_id", "?")))

    if checked == 0:
        fail(
            f"RUNLOG at {args.runlog} has no pass with both read_file_calls "
            "and rows_flipped recorded. Per-pass verification is impossible "
            "and this is NOT a pass."
        )

    print(f"\n  RUNLOG   {checked} passes with comparable read/flip counts")
    if mismatched:
        problems.append(
            f"{len(mismatched)} RUNLOG pass(es) flipped more ledger rows "
            f"than they read files — the real batching signature: "
            f"{', '.join(mismatched)}"
        )
    else:
        print("            0 passed flipped more rows than they read  OK")

    # --- verdict -----------------------------------------------------------
    print("\n" + "=" * 68)
    if problems:
        print("  RESULT: NON-COMPLIANT")
        for p in problems:
            print(f"    - {p}")
        print("  The ledger is claiming reads that the log does not support.")
        print("  Reset the affected marks and re-read before trusting the arena.")
        print("=" * 68)
        return 1

    print("  RESULT: COMPLIANT")
    print(f"  {total_reads} read_file calls across {len(runs)} runs and "
          f"{len(log_files_read)} log file(s),")
    print(f"  covering {len(marked)} ledger marks (ratio {ratio:.2f} reads per mark).")
    print(f"  Per-pass: no pass flipped more ledger rows than it read files.")
    print("  Caveat: the read side is reconstructed from the log, which is")
    print("  authoritative only for the window those log files cover.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
