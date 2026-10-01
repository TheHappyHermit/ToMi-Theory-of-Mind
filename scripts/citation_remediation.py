#!/usr/bin/env python3
"""Build the remediation plan for arena citations that were never earned.

THE PROBLEM
-----------
`arena_invariants.py` check C6 requires every file cited in `ARENA.md` to have a
ledger row marked `[x]`. On 2026-09-26 it reported 190 such citations. After the
answer/evidence split that fell to 39, because the split moved most of the
unearned citations into `ARENA-EVIDENCE.md` where they belong as history.

The 39 that remain are load-bearing: they appear in the answer file, in
`Earned by:` lines, in `Backup document:` lines and in COVERAGE-style tables.
Verified against git history — **none of the 39 was ever marked `[x]` in any
commit in this repository.** They were not mis-marked or lost; they were never
read, and cited anyway.

the operator's instruction: if we cannot prove we looked at a file, we cannot move past
it. Prove it, or re-read it.

WHAT THIS DOES
--------------
It classifies all 39 and emits a work order the arena job can execute:

  PROVEN   a run's report names the ORDER line as read  -> nothing to do
  RE-READ  no such evidence, and the row is still `[ ]`   -> must be read
  STRIKE   no such evidence and the row is `[-]` or `[!]` -> citation is void

It reads the cron output reports, not the ledger, because the ledger is the thing
under suspicion. A file is only PROVEN if a *run report* names its ORDER line in
a read statement.

Output is a JSON work order plus a human summary. It writes nothing to the
workspace.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(REPO, "cognition-arena")
ARENA = os.path.join(WS, "ARENA.md")
LEDGER = os.path.join(WS, "LEDGER.md")
ORDER = os.path.join(WS, "ORDER.txt")
RUNLOG = os.path.join(WS, "RUNLOG.jsonl")
OUTDIR = os.path.expanduser("~/.hermes/cron/output")
ARENA_JOB = "49280b099b12"
CORPUS = os.path.expanduser("~/.hermes")

sys.path.insert(0, os.path.join(REPO, "scripts"))
import arena_invariants as ai  # noqa: E402


def read(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def load_order():
    return [l.strip() for l in read(ORDER).splitlines() if l.strip()]


def build_stem_index(order):
    """stem -> every ORDER row carrying that document.

    Keyed on the stem WITHOUT the .md suffix, because that is the form
    `arena_invariants.arena_citations()` returns. Keying one on the filename
    and the other on the stem silently yields zero matches, which is how the
    AMBIGUOUS branch shipped reporting 0 while 15 real cases existed.

    446 of 1,445 distinct basenames appear at more than one row, because the
    corpus publishes most documents twice: once under active-wiki/ and once
    under oracle/brain/. A bare filename therefore does NOT identify a file,
    and resolving a citation to a single row by name is a coin flip.
    """
    idx = {}
    for i, p in enumerate(order, 1):
        idx.setdefault(p.rsplit("/", 1)[-1][: -len(".md")] if p.endswith(".md")
                      else p.rsplit("/", 1)[-1], []).append(i)
    return idx


def unearned(order, rows, arena_text, stem_index=None):
    """ORDER numbers cited in the answer file whose row is not [x].

    A citation is only unearned if EVERY row that could mean it is unread.
    When a basename has a twin and the twin is [x], the document was read —
    the citation is ambiguous, not unsupported. Those are reported separately
    so a remediation pass does not re-read a file it already read in full.
    """
    stem_index = stem_index if stem_index is not None else build_stem_index(order)
    cites = ai.arena_citations(arena_text, order)
    out = {}
    for stem, nums in cites.items():
        for n in nums:
            row = rows.get(n)
            if row is None or row.mark == "x":
                continue
            candidates = stem_index.get(stem, [n])
            read_twins = [t for t in candidates
                          if t != n and rows.get(t) is not None and rows[t].mark == "x"]
            out.setdefault(n, {"order": n, "path": order[n - 1],
                               "stem": stem, "mark": row.mark,
                               "absolute": os.path.join(CORPUS, order[n - 1]),
                               "exists": os.path.exists(os.path.join(CORPUS, order[n - 1])),
                               "ambiguous": len(candidates) > 1,
                               "read_twins": read_twins,
                               "cited_as": []})
            out[n]["cited_as"].append(stem)
    return out


def proven_reads():
    """ORDER -> list of run reports naming it as read.

    Two independent sources, because reports are prose and prose is unreliable:
      1. RUNLOG.jsonl `order_numbers_read` (authoritative once the job writes it)
      2. cron output reports, patterns:
           "ORDER 419"                       a single line named
           "lines 399-419" / "399–419"        an explicit inclusive range
    """
    proven = {}

    if os.path.exists(RUNLOG):
        for line in read(RUNLOG).splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            src = rec.get("run_id", "runlog")
            for n in rec.get("order_numbers_read", []) or []:
                proven.setdefault(int(n), []).append(f"RUNLOG {src}")

    for p in sorted(glob.glob(os.path.join(OUTDIR, ARENA_JOB, "*.md"))):
        tag = os.path.basename(p)[:16]
        t = read(p)
        t = t.split("## Response", 1)[-1]
        for m in re.finditer(r"[Ll]ines?\s+(\d+)\s*[–\-—]\s*(\d+)", t):
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b - a < 400:
                for n in range(a, b + 1):
                    proven.setdefault(n, []).append(f"report {tag}")
        for m in re.finditer(r"ORDER\s+(\d+)", t):
            proven.setdefault(int(m.group(1)), []).append(f"report {tag}")
    return proven


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="write the work order here")
    args = ap.parse_args(argv)

    order = load_order()
    rows = ai.load_rows(read(LEDGER))
    arena_text = read(ARENA)

    todo = unearned(order, rows, arena_text)
    proven = proven_reads()

    plan = {"PROVEN": [], "RE-READ": [], "STRIKE": [], "AMBIGUOUS": []}
    for n, rec in sorted(todo.items()):
        ev = proven.get(n)
        # A citation to a duplicated basename whose twin is [x] is already
        # earned — the document was read under its other path. Re-reading it
        # would burn a slot on a file the pass has already read in full.
        if ev:
            rec["proof"] = sorted(set(ev))
            plan["PROVEN"].append(rec)
        elif rec["read_twins"]:
            rec["reason"] = ("basename is published at "
                             + ", ".join(f"ORDER {t}" for t in sorted(rec["read_twins"]))
                             + " and that twin is [x] — the document was read; "
                               "cite the full path, not the bare filename")
            rec["action"] = (f"disambiguate the citation: use the full relative path of "
                             f"ORDER {rec['read_twins'][0]} ({order[rec['read_twins'][0]-1]}), "
                             f"or mark ORDER {n} [x] only after reading it")
            plan["AMBIGUOUS"].append(rec)
        elif rec["mark"] in ("-", "!"):
            rec["reason"] = f"row is [{rec['mark']}] — excluded or blocked, so the citation is void"
            plan["STRIKE"].append(rec)
        else:
            rec["reason"] = "no run report or RUNLOG entry names this ORDER line as read"
            plan["RE-READ"].append(rec)

    for rec in plan["RE-READ"]:
        rec["action"] = (f"read_file {rec['absolute']} start to finish; "
                         f"patch LEDGER row {rec['order']} to [x] immediately; "
                         f"then confirm the arena citation is earned or strike it")

    summary = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "arena_lines": len(arena_text.splitlines()),
        "total_unearned_citations": len(todo),
        "proven": len(plan["PROVEN"]),
        "ambiguous_twins": len(plan["AMBIGUOUS"]),
        "must_reread": len(plan["RE-READ"]),
        "must_strike": len(plan["STRIKE"]),
        "duplicated_basenames": sum(1 for v in build_stem_index(order).values() if len(v) > 1),
        "work_order": plan,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"wrote {args.out}")

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print("=" * 74)
    print("UNEARNED CITATIONS IN THE ANSWER FILE")
    print("=" * 74)
    print(f"  arena is {len(arena_text.splitlines()):,} lines")
    print(f"  cited but not [x]: {len(todo)}")
    print(f"  corpus basenames published at >1 row: {summary['duplicated_basenames']}"
          "  <- a bare filename does not identify a file")
    print()
    print(f"  PROVEN read     : {len(plan['PROVEN'])}")
    print(f"  AMBIGUOUS twin  : {len(plan['AMBIGUOUS'])}   (read at another path; disambiguate)")
    print(f"  MUST RE-READ    : {len(plan['RE-READ'])}")
    print(f"  MUST STRIKE     : {len(plan['STRIKE'])}")
    print()
    if plan["RE-READ"]:
        print("--- must be read before the arena may claim them ---")
        for rec in plan["RE-READ"]:
            print(f"  ORDER {rec['order']:>4}  {rec['path'][:66]}")
    if plan["AMBIGUOUS"]:
        print("--- already read at a twin path; make the citation unambiguous ---")
        for rec in plan["AMBIGUOUS"]:
            t = rec["read_twins"][0]
            print(f"  ORDER {rec['order']:>4} {rec['stem'][:34]:<36} -> cite ORDER {t}: {order[t-1][:44]}")
    if plan["STRIKE"]:
        print("--- citation is void, strike it ---")
        for rec in plan["STRIKE"]:
            print(f"  ORDER {rec['order']:>4} [{rec['mark']}]  {rec['path'][:60]}")
    if plan["PROVEN"]:
        print("--- already proven, nothing to do ---")
        for rec in plan["PROVEN"][:10]:
            print(f"  ORDER {rec['order']:>4}  {rec['path'][:56]}  {rec['proof'][:2]}")
    print()
    print("NOTE: these must be read as their OWN pass, not folded into the")
    print("next tranche. A file read to legitimise an existing citation is read")
    print("with the answer already written, which is the condition that produced")
    print("the unearned citations in the first place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
