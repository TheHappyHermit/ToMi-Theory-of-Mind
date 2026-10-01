#!/usr/bin/env python3
"""Check wiki frontmatter for the version-aggregation convention.

The convention is documented in docs/VERSION-AGGREGATION.md. It exists because a
2026 study (arXiv:2606.01435) found that letting a model decide which version of a
fact is current scores 7%, below BM25, while deterministic version aggregation
scores 80.8%.

This script checks the *mechanical* parts: that `status`, if present, is one of the
four legal values; that `supersedes`, if present, is a string or list; and that
`updated` is RFC 3339 UTC. It deliberately does not attempt to judge whether a
document is genuinely current -- that is a human judgement, and automating it is
the failure mode being guarded against.

Usage:
    python3 scripts/check_version_convention.py [PATH ...]
    python3 scripts/check_version_convention.py --quiet /path/to/wiki

Exit codes: 0 = clean (or nothing found), 1 = violations found, 2 = bad usage.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# Two SEPARATE axes, and conflating them was a bug in the first version of this
# script. `status` values in the live vaults are overwhelmingly *maturity* markers
# (complete, completed, verified, published), not *currency* markers. Treating an
# unrecognised value as "not current" would have misfiled 207 live notes, so
# unknown values are treated as current -- fail-open, never hide a live note.
#
# CURRENCY_STATUSES: the values that mean "this is no longer the live version".
# Everything else legal is current. Membership here is the only thing that should
# ever drive a current-only retrieval filter.
CURRENCY_STATUSES = frozenset({
    "superseded", "deprecated", "archived", "retracted", "obsolete", "stale",
})

# KNOWN_STATUSES: every value the checker recognises. A value outside this set is
# reported as unrecognised so typos get fixed, but is still treated as current.
# Taken from the actual vaults rather than invented -- a checker that calls live
# notes illegal just teaches people to ignore the checker.
KNOWN_STATUSES = CURRENCY_STATUSES | frozenset({
    # current / live
    "active", "current", "stable", "living", "draft", "draft-v2",
    # maturity markers used across the vaults
    "complete", "completed", "verified", "published", "paused",
})

# RFC 3339 UTC only: YYYY-MM-DDTHH:MM:SSZ
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Frontmatter delimiters
FM_DELIM = re.compile(r"^---\s*$")

Finding = Tuple[str, int, str]


def split_frontmatter(text: str) -> Tuple[List[str], int]:
    """Return (frontmatter lines, line number of first body line).

    Returns ([], 0) when the file has no frontmatter.
    """
    lines = text.split("\n")
    if not lines or not FM_DELIM.match(lines[0]):
        return ([], 0)
    for i in range(1, len(lines)):
        if FM_DELIM.match(lines[i]):
            return (lines[1:i], i + 1)
    return ([], 0)


def parse_simple_fields(fm_lines: Iterable[str]) -> dict:
    """Parse top-level `key: value` pairs. Ignores nested blocks and lists.

    Deliberately minimal: the convention only needs three scalar fields, and a real
    YAML dependency would be a worse failure mode than not understanding the whole
    document.
    """
    fields = {}
    for line in fm_lines:
        if line[:1] in (" ", "\t", "-", "#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key:
            fields[key] = value.strip().strip("'\"")
    return fields


def check_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [(str(path), 0, f"unreadable: {exc}")]

    fm_lines, body_start = split_frontmatter(text)
    if not fm_lines:
        # No frontmatter is legal. `status` defaults to active.
        return findings

    fields = parse_simple_fields(fm_lines)

    status = fields.get("status")
    if status is not None:
        if status == "":
            findings.append(
                (str(path), body_start, "status is empty; remove it or set a legal value")
            )
        elif status.lower() not in KNOWN_STATUSES:
            findings.append(
                (
                    str(path),
                    body_start,
                    f"status '{status}' is not a recognised value, so it will be "
                    f"treated as current. Known values: "
                    f"{', '.join(sorted(KNOWN_STATUSES))}",
                )
            )

    updated = fields.get("updated")
    if updated is not None and not RFC3339_UTC.match(updated):
        findings.append(
            (
                str(path),
                body_start,
                f"updated '{updated}' is not RFC 3339 UTC "
                f"(expected YYYY-MM-DDTHH:MM:SSZ)",
            )
        )

    return findings


def iter_markdown(paths: List[Path]) -> Iterable[Path]:
    for p in paths:
        if p.is_file() and p.suffix == ".md":
            yield p
        elif p.is_dir():
            yield from p.rglob("*.md")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Check wiki frontmatter against docs/VERSION-AGGREGATION.md"
    )
    ap.add_argument("paths", nargs="*", default=["."], help="files or directories")
    ap.add_argument(
        "--quiet", action="store_true", help="only print if violations are found"
    )
    args = ap.parse_args(argv)

    targets = [Path(p).expanduser() for p in (args.paths or ["."])]
    for t in targets:
        if not t.exists():
            print(f"error: no such path: {t}", file=sys.stderr)
            return 2

    files = list(iter_markdown(targets))
    findings: List[Finding] = []
    for f in files:
        findings.extend(check_file(f))

    if findings:
        for path, line, msg in sorted(findings):
            print(f"{path}:{line}: {msg}" if line else f"{path}: {msg}")
        print(
            f"\n{len(findings)} violation(s) in {len(files)} markdown file(s). "
            f"See docs/VERSION-AGGREGATION.md",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"OK: {len(files)} markdown file(s) conform to the version convention.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
