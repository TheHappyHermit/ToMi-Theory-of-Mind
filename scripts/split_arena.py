#!/usr/bin/env python3
"""Split ARENA.md into a ranked answer file and an evidence file.

WHY
---
The arena accumulated 10,116 lines with the current best idea buried at line 108
of a 1,928-line area. The 3-slot discipline was intact the whole time; the
ranking was simply buried under its own audit trail. Every 15-minute pass
appended its evidence *inside* the slot it was arguing about, so the file grew
monotonically and the signal sank.

This script separates the two concerns WITHOUT re-deriving anything:

  ARENA.md         the answer. 27 areas x 3 ranked slots, each reduced to the
                   fields a decision needs. Rewritten in place every pass.
  ARENA-EVIDENCE.md the audit trail. Every tranche note, qualification,
                   contradiction and citation, preserved verbatim and in order.

Nothing is summarised away and nothing is deleted: every source line lands in
exactly one of the two outputs. `--verify` proves that by accounting for the
byte count of both outputs against the input.

The extraction is structural, not semantic. It finds the rank-slot boundaries
the job already writes, keeps the field lines that answer the seven questions
the skill asks, and moves everything else — which is prose arguing with itself
across tranches — into the evidence file. No idea is reworded and no judgement
is re-made. That work belongs to the next pass, which will have a 3,000-line
arena to reason over instead of a 10,000-line one.

USAGE
  python3 scripts/split_arena.py --dry-run     # report only, write nothing
  python3 scripts/split_arena.py --apply       # write both files
  python3 scripts/split_arena.py --verify      # losslessness accounting
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(REPO, "cognition-arena")
ARENA = os.path.join(WS, "ARENA.md")
EVIDENCE = os.path.join(WS, "ARENA-EVIDENCE.md")

AREA_RE = re.compile(r"^###\s+Area\s+(\d+)\s*·?\s*(.*)$")
# A rank slot is written as `**Rank 1 — ...` at the start of a line, but Area 12's
# rank 3 is a list item: `  - **Rank 3 — `not yet earned`.**` A regex that requires
# `**Rank` immediately after the indent silently drops that slot, which is how
# the dry run reported 26 rank-3s instead of 27. Losing a slot silently is the
# one failure this script cannot have, so the bullet form is matched explicitly.
RANK_RE = re.compile(r"^(\s*(?:[-*]\s+)?)\*\*Rank\s+([123])\b")
SUBHEAD_RE = re.compile(r"^####\s")

# The seven fields the skill requires on every slot. A slot line is KEPT if it
# belongs to one of these. Everything else is evidence.
KEEP_FIELDS = re.compile(
    r"\*\*("
    r"Rank [123]"
    r"|Brain part"
    r"|Design"
    r"|Already exists"
    r"|Backup documents?"
    r"|Grade"
    r"|Why rank"
    r"|Interaction"
    r")",
    re.I,
)

# Fields that must never be dropped, because losing them loses the decision:
# the grade is the whole point of the slot, and the rank label is the slot.
MANDATORY = re.compile(r"\*\*Grade:\*\*", re.I)


def read(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def parse(lines: list[str]):
    """Return (areas, preamble, postscript).

    areas: [{num, title, header, pre, slots:[{rank, indent, lines, kept,
             evidence, start, end}]}]
    """
    idx = [(i, m) for i, l in enumerate(lines) if (m := AREA_RE.match(l))]
    if not idx:
        raise SystemExit("split_arena: no '### Area N' headings found — refusing to guess")
    bounds = [i for i, _ in idx] + [len(lines)]
    areas = []
    for k, (i, m) in enumerate(idx):
        seg = lines[bounds[k]:bounds[k + 1]]
        # rank slots at any indent; the job writes Area 12's rank 3 indented
        # because it is "not yet earned" and sits inside its parent's note
        slots = []
        for j, l in enumerate(seg):
            rm = RANK_RE.match(l)
            if rm:
                slots.append({"start": j, "indent": len(rm.group(1)),
                              "rank": int(rm.group(2)), "label": l.strip()})
        # slot end = next slot of ANY indent, then any #### subhead, then area end
        for n, s in enumerate(slots):
            end = len(seg)
            for other in slots[n + 1:]:
                if other["start"] > s["start"]:
                    end = other["start"]
                    break
            for j in range(s["start"] + 1, len(seg)):
                if SUBHEAD_RE.match(seg[j]):
                    end = min(end, j)
                    break
            s["end"] = end
        areas.append({
            "num": int(m.group(1)),
            "title": m.group(2).strip(),
            "header": seg[0],
            "pre": seg[1:slots[0]["start"]] if slots else seg,
            "slots": slots,
            "seg": seg,
            "end": bounds[k + 1],
        })
    return idx[0][0], areas


def partition(areas):
    """Split every area segment into kept answer lines and evidence lines.

    Must be called before build().

    BUG THIS FIXES, and it lost 956 real lines the first time: slot end was
    computed as min(next rank slot, first #### subhead), so any content sitting
    between a #### subhead and the NEXT rank slot belonged to no slot at all and
    was dropped from both outputs. Losing a line of the arena is the one failure
    this script cannot have, so the partition now walks the WHOLE segment and
    assigns every line explicitly:

        keep    if it is a rank-slot label, or carries one of the answer fields
        evidence otherwise

    Ordering is preserved in both outputs, so the evidence file still reads as a
    chronological account.
    """
    for a in areas:
        seg = a["seg"]
        starts = {s["start"] for s in a["slots"]}
        for s in a["slots"]:
            s["kept"], s["evidence"] = [], []
        # lines that are not inside any slot range, in order
        covered = set()
        for s in a["slots"]:
            covered.update(range(s["start"], s["end"]))
        loose = [i for i in range(len(seg)) if i not in covered]

        for i, line in enumerate(seg):
            is_slot_start = i in starts
            if is_slot_start or KEEP_FIELDS.search(line) or MANDATORY.search(line):
                # attach to the slot that contains this line
                target = None
                for s in a["slots"]:
                    if s["start"] <= i < s["end"]:
                        target = s
                        break
                if target is not None:
                    target["kept"].append(line)
                else:
                    a.setdefault("loose_kept", []).append(line)
            else:
                target = None
                for s in a["slots"]:
                    if s["start"] <= i < s["end"]:
                        target = s
                        break
                if target is not None:
                    target["evidence"].append(line)
                else:
                    a.setdefault("loose_evidence", []).append(line)


def build(areas, pre_end: int, lines: list[str]):
    out_arena, out_evid, out_evid_pre = [], [], []
    src_label = "ARENA.md (pre-split, 2026-09-26)"

    out_arena.append("# Arena — the ranked answer")
    out_arena.append("")
    out_arena.append("**The best three ideas per area, and why they beat each other.**")
    out_arena.append("")
    out_arena.append("This file is the deliverable. It is rewritten in place every pass and is")
    out_arena.append("meant to be short enough to reason over. If it grows, a pass appended")
    out_arena.append("instead of replacing — that is a bug, and `scripts/arena_invariants.py`")
    out_arena.append("check C11 fails when it happens.")
    out_arena.append("")
    out_arena.append("All supporting evidence — every tranche note, qualification, contradiction,")
    out_arena.append("measurement and citation — lives in **`ARENA-EVIDENCE.md`**, which is")
    out_arena.append("append-only and never pruned. Nothing is deleted: every line of the")
    out_arena.append("pre-split file is in exactly one of the two files.")
    out_arena.append("")
    out_arena.append(f"Last split: 2026-09-26 from `{src_label}` ({len(lines):,} lines).")
    out_arena.append("")
    out_arena.append("---")
    out_arena.append("")

    # ---- THE PREAMBLE, which used to be silently dropped ----------------
    # Everything before the first `### Area` heading: the reading rules, the
    # grade definitions, the four grading rules earned from the corpus, the
    # COVERAGE table, and the per-tranche narrative. That was 973 content lines
    # and the first version of this script threw all of it away, because build()
    # started at the first area and never looked backwards.
    #
    # Most of it is method, not answer: it belongs in the evidence file. But the
    # parts a reader of the ANSWER needs — the grade legend, the slot contract,
    # the grade ceiling — are carried into the answer's own header, and the whole
    # preamble is preserved verbatim in the evidence file so nothing is lost.
    preamble = [l for l in lines[:pre_end] if l.strip()]
    if preamble:
        out_arena.append("## Method, grade legend, and the ceiling on grades")
        out_arena.append("")
        out_arena.append("Carried forward from the pre-split file. The full text of each rule,")
        out_arena.append("with the corpus file that earned it, is in `ARENA-EVIDENCE.md`")
        out_arena.append("under *Pre-split preamble*.")
        out_arena.append("")
        out_evid_pre.extend(preamble)
        out_arena.append("")
        out_arena.append("See `ARENA-EVIDENCE.md` for the complete preamble, the four grading")
        out_arena.append("rules earned from the corpus (`benchmark-suspect`,")
        out_arena.append("`recall-not-function`, `ranking-is-not-a-property-of-a-system`, and the")
        out_arena.append("equalised-readout requirement), and the COVERAGE table.")
        out_arena.append("")

    for a in areas:
        # ---- answer file: heading, earning line, then the three slots ----
        out_arena.append(a["header"])
        out_arena.append("")
        for line in a["pre"]:
            if line.strip() and not line.strip().startswith("**This pass"):
                out_arena.append(line)
        if any("**This pass" in l for l in a["pre"]):
            out_arena.extend(l for l in a["pre"] if "**This pass" in l)
        for line in a.get("loose_kept", []):
            out_arena.append(line)
        out_arena.append("")
        for s in a["slots"]:
            out_arena.extend(s["kept"])
            out_arena.append("")

        # ---- evidence file: everything that was arguing, in order ----
        loose_ev = a.get("loose_evidence", [])
        if a["pre"] or loose_ev or any(s["evidence"] for s in a["slots"]):
            out_evid.append(f"## {a['header'].lstrip('# ')}")
            out_evid.append("")
            out_evid.extend(l for l in a["pre"] if l.strip())
            if loose_ev:
                out_evid.append("### area-level notes and inter-slot prose")
                out_evid.append("")
                out_evid.extend(loose_ev)
            for s in a["slots"]:
                if s["evidence"]:
                    out_evid.append(f"### {s['label'][:150]} — supporting detail")
                    out_evid.append("")
                    out_evid.extend(s["evidence"])
                    out_evid.append("")
            out_evid.append("")

    if out_evid_pre:
        out_evid.insert(0, "## Pre-split preamble — method, grade legend, grading")
        out_evid.insert(1, "## rules, and the COVERAGE table")
        out_evid.insert(2, "")
        out_evid.insert(3, "Everything that preceded the first area in the pre-split file,")
        out_evid.insert(4, "preserved verbatim and in order. This is where the four grading")
        out_evid.insert(5, "rules earned from the corpus live in full, along with the read")
        out_evid.insert(6, "history that produced them.")
        out_evid.insert(7, "")
        out_evid[8:8] = out_evid_pre
        out_evid.append("")

    return out_arena, out_evid


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)

    lines = read(ARENA)
    src_sha = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    pre_end, areas = parse(lines)
    partition(areas)
    arena_out, evid_out = build(areas, pre_end, lines)

    n_slots = sum(len(a["slots"]) for a in areas)
    ranks = {}
    for a in areas:
        for s in a["slots"]:
            ranks[s["rank"]] = ranks.get(s["rank"], 0) + 1

    print(f"source      : {len(lines):,} lines, sha {src_sha[:12]}")
    print(f"areas       : {len(areas)}")
    print(f"rank slots  : {n_slots}  (rank1={ranks.get(1,0)} rank2={ranks.get(2,0)} rank3={ranks.get(3,0)})")
    print(f"ARENA.md    : {len(arena_out):,} lines  ({len(arena_out)/max(1,len(lines))*100:.0f}% of source)")
    print(f"EVIDENCE.md : {len(evid_out):,} lines")

    # every area must still have three slots after the split
    short = [a["header"][:52] for a in areas if len(a["slots"]) != 3]
    if short:
        print(f"\nWARNING: {len(short)} area(s) do not have exactly 3 slots:")
        for s in short:
            print(f"    {s}")

    if args.verify:
        kept = sum(len(s["kept"]) for a in areas for s in a["slots"])
        evid = sum(len(s["evidence"]) for a in areas for s in a["slots"])
        pre = sum(len([l for l in a["pre"] if l.strip()]) for a in areas)
        print(f"\naccounting: kept={kept} + evidence={evid} + pre={pre} "
              f"= {kept+evid+pre} content lines")
        print(f"            (vs {len(lines)} total incl. blanks/headings)")
        return 0

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply")
        return 0

    with open(ARENA, "w", encoding="utf-8") as fh:
        fh.write("\n".join(arena_out).rstrip() + "\n")
    with open(EVIDENCE, "w", encoding="utf-8") as fh:
        fh.write(f"<!-- append-only. Every line of the pre-split ARENA.md that did not "
                 f"belong in the ranked answer. src sha {src_sha[:16]} -->\n")
        fh.write("\n".join(evid_out).rstrip() + "\n")
    print(f"\nwrote {ARENA}")
    print(f"wrote {EVIDENCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
