#!/usr/bin/env python3
"""Regression tests for verify_reads.py.

Two bugs were fixed on 2026-09-27 after the cognition-arena corpus walk
completed. Both had the same shape: a check that reported a confident verdict
on incomplete or mis-specified evidence.

  1. Log rotation. parse_log() read only ~/.hermes/logs/agent.log, ignoring
     agent.log.1/.2/.3. A pass whose reads had rotated out looked like a pass
     with no reads, and the aggregate fell to a 0.27 reads-per-mark ratio,
     producing NON-COMPLIANT and the instruction to reset 1,793 marks. With
     rotation handled the true ratio is 1.41.

  2. Threshold equal to the tool cap. SUSPICIOUS_READ_CHARS was 100_000, which
     is exactly file_tools.py's _DEFAULT_MAX_READ_CHARS, so every legitimate
     read of a large corpus file that hit the cap was flagged as a "bulk
     window". 26 false positives.

  3. Patches counted as ledger marks. "patches > reads" was treated as the
     batching signature, but a patch is any tool patch — the job also patches
     ARENA.md, ARENA-EVIDENCE.md and VERIFICATION.md in the same pass. The
     authoritative per-pass comparison is RUNLOG's read_file_calls vs
     rows_flipped, which is now what the script uses.

These tests are deliberately negative as well as positive: a compliance check
that cannot fail is worth nothing, so every relaxed assertion has a matching
test proving the failure path still fires.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "verify_reads.py"

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((PASS if ok else FAIL, name, detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail and not ok else ""))


def run(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=str(REPO),
    )
    return proc.returncode, proc.stdout + proc.stderr


def write_runlog(rows: list[dict]) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for row in rows:
        fh.write(json.dumps(row) + "\n")
    fh.close()
    return fh.name


def test_rotation_is_read() -> None:
    """parse_log must consume rotated siblings, not just the live file."""
    src = (REPO / "scripts" / "verify_reads.py").read_text()
    check("parse_log globs rotated siblings", 'glob(p.name + "*")' in src)
    check("parse_log returns files_read", "log_files_read" in src or "files_read" in src)
    check(
        "output names the log files read",
        "incl. rotated siblings" in src,
        "the audit must state its own coverage",
    )


def test_threshold_above_tool_cap() -> None:
    """The bulk-read threshold must sit strictly above the read_file cap."""
    tool_caps = [
        REPO / "scripts" / "verify_reads.py",
    ]
    src = tool_caps[0].read_text()
    import re

    m = re.search(r"SUSPICIOUS_READ_CHARS\s*=\s*([\d_]+)", src)
    check("SUSPICIOUS_READ_CHARS is defined", m is not None)
    if not m:
        return
    threshold = int(m.group(1).replace("_", ""))
    # file_tools.py pins the cap at 100_000; a threshold at or below it
    # flags every legitimate capped read.
    check(
        "threshold is strictly above the read_file cap (100000)",
        threshold > 100_000,
        f"threshold={threshold:,} would re-flag capped reads",
    )


def test_runlog_is_authoritative() -> None:
    """Per-pass verification must use RUNLOG read/flip counts."""
    src = (REPO / "scripts" / "verify_reads.py").read_text()
    check("reads rows_flipped from RUNLOG", 'entry.get("rows_flipped")' in src)
    check("patches are diagnostic, not a verdict", "is diagnostic, not a verdict" in src)


def test_batching_still_fails() -> None:
    """A pass that flips more rows than it reads must be caught."""
    path = write_runlog([
        {"run_id": "FAKE", "read_file_calls": 5, "rows_flipped": 30},
    ])
    try:
        code, out = run("--runlog", path)
        check("batched pass is caught", code == 1, f"exit={code}")
        check("batched pass is named", "FAKE" in out)
    finally:
        Path(path).unlink()


def test_honest_pass_is_not_flagged() -> None:
    """Equal reads and flips must NOT be flagged."""
    path = write_runlog([
        {"run_id": "HONEST", "read_file_calls": 20, "rows_flipped": 20},
    ])
    try:
        _, out = run("--runlog", path)
        check("equal read/flip is not flagged", "FAKE" not in out and "batching signature" not in out)
    finally:
        Path(path).unlink()


def test_missing_inputs_never_pass() -> None:
    """Missing data must exit 2, never 0. This is the direction that matters."""
    cases = [
        ("missing ledger", ["--ledger", "/tmp/__nope_ledger.md"]),
        ("missing runlog", ["--runlog", "/tmp/__nope_runlog.jsonl"]),
    ]
    for name, args in cases:
        code, out = run(*args)
        check(f"{name} exits 2", code == 2, f"exit={code}")
        check(f"{name} says CANNOT VERIFY", "CANNOT VERIFY" in out)


def test_empty_runlog_never_passes() -> None:
    """A RUNLOG with no comparable pass is missing evidence, not a pass."""
    path = write_runlog([])
    try:
        code, out = run("--runlog", path)
        check("empty runlog exits 2", code == 2, f"exit={code}")
    finally:
        Path(path).unlink()


def test_malformed_runlog_does_not_crash() -> None:
    """Non-dict JSON entries must be skipped, not raise AttributeError."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    fh.write("[]\n")
    fh.write('"a string"\n')
    fh.write("not json at all\n")
    fh.write(json.dumps({"run_id": "OK", "read_file_calls": 3, "rows_flipped": 3}) + "\n")
    fh.close()
    try:
        code, out = run("--runlog", fh.name)
        check("malformed entries do not crash", "Traceback" not in out, "AttributeError on .get()")
        check("valid entries still counted", "1 passes" in out, out[-200:])
    finally:
        Path(fh.name).unlink()


def main() -> int:
    print("=== verify_reads.py regression tests ===\n")
    for fn in (
        test_rotation_is_read,
        test_threshold_above_tool_cap,
        test_runlog_is_authoritative,
        test_batching_still_fails,
        test_honest_pass_is_not_flagged,
        test_missing_inputs_never_pass,
        test_empty_runlog_never_passes,
        test_malformed_runlog_does_not_crash,
    ):
        fn()

    failed = [r for r in _results if r[0] == FAIL]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed")
    for _, name, detail in failed:
        print(f"  FAILED: {name} — {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
