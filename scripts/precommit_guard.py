#!/usr/bin/env python3
"""Refuse to commit if an off-limits file is staged. Exit 1 = do not commit."""
import subprocess, sys

# Per the owner's standing rules and the project's own history table: these
# have been accidentally staged before (recorded failure #12).
FORBIDDEN = [
    "SCRATCHPAD.md",
    "research-resultideas.md",
    "scripts/fill_oracle_gaps.py",
]
FORBIDDEN_SUFFIX = [".bak.sleeptime", ".bak.job2"]


def staged():
    out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         capture_output=True, text=True).stdout
    return [f for f in out.split("\n") if f.strip()]


bad = []
for f in staged():
    if f in FORBIDDEN:
        bad.append((f, "explicitly off-limits"))
    elif any(f.endswith(s) for s in FORBIDDEN_SUFFIX):
        bad.append((f, "backup/sleeptime artifact"))

if bad:
    print("OFF-LIMITS FILES ARE STAGED — refusing to allow this commit:")
    for f, why in bad:
        print(f"  {f}  ({why})")
    print()
    print("Unstage them, then re-check:")
    for f, _ in bad:
        print(f"  git restore --staged '{f}'")
    sys.exit(1)

print(f"staging clean: {len(staged())} file(s), none off-limits")
