#!/usr/bin/env python3
"""Prove split_arena.py loses nothing.

WHY THIS TEST WAS REWRITTEN
---------------------------
The original compared the LIVE `ARENA.md` against an unversioned `/tmp`
snapshot of the pre-split file. That is the wrong comparison, and it reported
7 failures on a correctly-functioning arena:

  "27 areas x 3 slots: rank1=27"          -> the arena had grown to 29 areas
  "answer has 57/51" **Grade:** lines      -> passes had added grades
  "530 unexpected" content lines          -> passes had written new evidence

Every one of those was correct behaviour scored as data loss. A test that fails
on healthy output trains you to ignore it, which is worse than having no test.

The claim worth testing is not "the live arena still matches a snapshot from
this morning". It is: **running the splitter on the pre-split file produces two
files that together contain every line of the input, and the splitter refuses a
file it does not recognise.** That is reproducible, deterministic, and does not
depend on how much the arena has grown since.

So the splitter now runs against a temp copy of the snapshot, and the lossless
assertions compare THAT OUTPUT to the snapshot's input. The live arena gets
checks that are true regardless of its age.

A second defect fixed here: the "running the tests did not mutate the live
ARENA.md" check ended in `or True`, so it passed unconditionally. It is now a
real hash comparison.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(REPO, "cognition-arena")
ARENA = os.path.join(WS, "ARENA.md")
EVIDENCE = os.path.join(WS, "ARENA-EVIDENCE.md")
SPLIT = os.path.join(REPO, "scripts", "split_arena.py")
SOURCE = "/tmp/ARENA.pre-split.bak.md"

RANK = re.compile(r"^(\s*(?:[-*]\s+)?)\*\*Rank\s+([123])\b")
AREA_RE = re.compile(r"^###\s+Area\s+(\d+)\b")

RESULTS = []


def rec(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


def norm(lines):
    """Content lines, blank-stripped, for set comparison."""
    return {l.strip() for l in lines if l.strip()}


def run_splitter_on(source_text: str, tmpdir: str):
    """Run scripts/split_arena.py --apply against a copy of `source_text`.

    Returns (arena_lines, evidence_lines). The live workspace is never touched:
    the splitter's WS constant is rewritten to point at the temp dir.
    """
    ws2 = os.path.join(tmpdir, "ws")
    os.makedirs(ws2, exist_ok=True)
    with open(os.path.join(ws2, "ARENA.md"), "w", encoding="utf-8") as fh:
        fh.write(source_text)
    p2 = os.path.join(tmpdir, "split.py")
    src = open(SPLIT, encoding="utf-8").read()
    src = src.replace(f'WS = os.path.join(REPO, "cognition-arena")', f"WS = {ws2!r}")
    if f"WS = {ws2!r}" not in src:
        raise RuntimeError("could not redirect the splitter's workspace — "
                           "its WS assignment changed shape; refusing to run "
                           "it against the live arena instead")
    with open(p2, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, p2, "--apply"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"splitter failed: {(r.stdout + r.stderr)[-400:]}")
    a = open(os.path.join(ws2, "ARENA.md"), encoding="utf-8", errors="replace").read().splitlines()
    e = open(os.path.join(ws2, "ARENA-EVIDENCE.md"), encoding="utf-8", errors="replace").read().splitlines()
    return a, e


def main() -> int:
    # ---- A. the splitter's own losslessness, on the snapshot -----------
    if not os.path.exists(SOURCE):
        print(f"SKIP: pre-split snapshot not present at {SOURCE}.")
        print("  The split-losslessness proof needs the 10,116-line pre-split file.")
        print("  It is not versioned because it is large and single-use. Recover it")
        print("  from git history at the commit before the split, or re-create it")
        print("  by concatenating the answer and evidence files of that era.")
        print()
        print("  Live arena health does not depend on this file:")
        print("    python3 scripts/arena_invariants.py")
        return 0

    live_before = hashlib.sha256(open(ARENA, "rb").read()).hexdigest()
    src_text = open(SOURCE, encoding="utf-8", errors="replace").read()
    src = src_text.splitlines()
    with tempfile.TemporaryDirectory() as td:
        try:
            t_a, t_e = run_splitter_on(src_text, td)
        except RuntimeError as exc:
            rec("splitter runs against a temp copy without touching the live arena",
                False, str(exc)[:160])
            t_a, t_e = [], []
        if t_a:
            src_content = norm(src)
            out_content = norm(t_a) | norm(t_e)
            lost = src_content - out_content
            rec("splitter loses no content line", not lost,
                f"{len(lost)} lost, e.g. {sorted(lost)[:2]}")

            s_slots = [l for l in src if RANK.match(l)]
            a_slots = [l for l in t_a if RANK.match(l)]
            e_slots = [l for l in t_e if RANK.match(l)]
            rec("every rank slot lands in the answer, none in the evidence file",
                len(a_slots) == len(s_slots) and not e_slots,
                f"source={len(s_slots)} answer={len(a_slots)} evidence={len(e_slots)}")
            rec("rank slot label text is byte-identical",
                sorted(l.strip() for l in a_slots) == sorted(l.strip() for l in s_slots))

            s_grades = [l for l in src if "**Grade:**" in l]
            a_grades = [l for l in t_a if "**Grade:**" in l]
            e_grades = [l for l in t_e if "**Grade:**" in l]
            rec("every grade survives, and stays in the answer",
                sorted(s_grades) == sorted(a_grades) and not e_grades,
                f"source={len(s_grades)} answer={len(a_grades)} evidence={len(e_grades)}")

            s_areas = {AREA_RE.match(l).group(1) for l in src if AREA_RE.match(l)}
            a_areas = {AREA_RE.match(l).group(1) for l in t_a if AREA_RE.match(l)}
            rec("every area heading survives in the answer",
                s_areas == a_areas, f"missing={sorted(s_areas - a_areas)}")

            rec("the answer is smaller than the evidence trail",
                len(t_a) < len(t_e), f"answer={len(t_a):,} evidence={len(t_e):,}")
            rec("the answer shrank enough to reason over",
                len(t_a) < 2500, f"{len(t_a):,} lines")

    live_after = hashlib.sha256(open(ARENA, "rb").read()).hexdigest()
    rec("running the tests did not mutate the live ARENA.md",
        live_before == live_after,
        f"{live_before[:12]} -> {live_after[:12]}")

    # ---- B. the splitter refuses input it cannot read -------------------
    with tempfile.TemporaryDirectory() as td:
        fake = os.path.join(td, "ws")
        os.makedirs(fake)
        with open(os.path.join(fake, "ARENA.md"), "w") as fh:
            fh.write("no headings here\njust prose\n")
        p = os.path.join(td, "s.py")
        src_code = open(SPLIT, encoding="utf-8").read().replace(
            f'WS = os.path.join(REPO, "cognition-arena")', f"WS = {fake!r}")
        with open(p, "w") as fh:
            fh.write(src_code)
        r2 = subprocess.run([sys.executable, p, "--apply"], capture_output=True, text=True)
        rec("splitter refuses a file with no area headings rather than guessing",
            r2.returncode != 0 and "refusing to guess" in (r2.stdout + r2.stderr),
            f"rc={r2.returncode}")
        rec("...and wrote nothing in that case",
            not os.path.exists(os.path.join(fake, "ARENA-EVIDENCE.md")))

    # ---- C. the LIVE arena, checked without reference to any snapshot ---
    # These hold no matter how much the arena has grown.
    if os.path.exists(ARENA):
        a = open(ARENA, encoding="utf-8", errors="replace").read().splitlines()
        areas = {}
        cur = None
        for l in a:
            m = AREA_RE.match(l)
            if m:
                cur = m.group(1)
                areas[cur] = []
            elif cur and RANK.match(l):
                areas[cur].append(RANK.match(l).group(2))
        bad = {k: v for k, v in areas.items() if sorted(v) != ["1", "2", "3"]}
        rec(f"live arena: all {len(areas)} areas have exactly ranks 1,2,3",
            not bad, f"{len(bad)} malformed: {list(bad.items())[:3]}")
    if os.path.exists(EVIDENCE):
        e = open(EVIDENCE, encoding="utf-8", errors="replace").read().splitlines()
        rec("live evidence file is the larger of the two",
            len(e) > len(a), f"evidence={len(e):,} answer={len(a):,}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    w = max(len(n) for n, _, _ in RESULTS) + 2
    for n, ok, d in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {n.ljust(w)}" + (f"  {d[:140]}" if not ok else ""))
    print(f"\n{passed} passed, {len(RESULTS)-passed} failed, {len(RESULTS)} total")
    if any("SKIP" in n for n, _, _ in RESULTS):
        print("NOTE: snapshot-dependent checks were skipped, not passed.")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
