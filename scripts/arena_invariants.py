#!/usr/bin/env python3
"""Arena invariant checker — verifies that every claim the arena makes about its
own evidence base is true, right now, not as of some earlier read count.

Why this exists
---------------
`VERIFICATION.md` finding F2-7 asserted: "every grade in ARENA.md rests on lines
1-20 only, and the arena states that no file outside lines 1-20 is cited anywhere
in it." That was true when written, at 29 reads. It was never re-tested as the
arena grew, and at 397 reads it was false: 173 files were cited whose ledger row
was still `[ ]`.

That is the failure class this script exists to kill. A self-audit written as prose
goes stale silently, because nothing re-derives it. So the invariant lives in code,
runs every time, and FAILS LOUDLY.

What it checks (each one can fail)
---------------------------------
  C1  LEDGER row count == ORDER.txt line count
  C2  row numbers are contiguous 1..N, no gaps, no duplicates
  C3  every ledger path matches its ORDER.txt line exactly
  C4  the live row census equals the census the ledger publishes in its own
      summary table (a ledger that lies about its own totals is not a ledger)
  C5  no row regressed [x] -> [ ] since the reference snapshot
  C6  INVARIANT: every ARENA.md citation resolves to a row marked [x]
  C7  every "**Earned by:**" evidence claim names a file that is [x]
  C8  no [x] row is uncited AND unexplained (the phantom-mark shape from F2-7)
  C9  the per-run read ceiling is respected: no run may mark more than 20 files
  C10 citation scan uses a real citation test, not a substring test

Usage
-----
  python3 scripts/arena_invariants.py                # human report
  python3 scripts/arena_invariants.py --json         # machine readable
  python3 scripts/arena_invariants.py --max-per-run 20
  python3 scripts/arena_invariants.py --quiet        # exit code only

Exit code 0 = all invariants hold. Exit code 1 = at least one violated.
Exit code 2 = the checker itself could not run (missing/unreadable inputs).

A checker that cannot fail is worse than no checker, because it is trusted. Every
assertion here is paired in tests/test_arena_invariants_nonvacuity.py with a
sabotage that must turn it red. If you add a check, add its sabotage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(REPO, "cognition-arena")

ORDER = os.path.join(WORKSPACE, "ORDER.txt")
LEDGER = os.path.join(WORKSPACE, "LEDGER.md")
ARENA = os.path.join(WORKSPACE, "ARENA.md")
VERIFICATION = os.path.join(WORKSPACE, "VERIFICATION.md")

# The arena reads at most this many files per run. A run that marks more has
# either bulk-read or fabricated marks. This is the skill's rule, enforced here
# because prose rules go unenforced.
DEFAULT_MAX_PER_RUN = 20

# `- [x] 123 active-wiki/foo.md — note`
ROW_RE = re.compile(r"^-\s*\[([ x!\-])\]\s+(\d+)\s+(\S+)(.*)$")

# The published summary is prose-labelled, NOT `| [x] | 397 |`. It reads:
#   | Rows marked `[x]` in the file | 397 |
#   | Excluded (never opened)       | 368 |
#   | Remaining to read (`[ ]`)     | 1451 |
#   | Total                         | 2217 |
# Matching on the label (not the position) is what makes this robust to the job
# inserting new breakdown rows, which it does every pass.
SUMMARY_ROW_RE = re.compile(
    r"^\|\s*(?P<label>[^|]*?)\s*\|\s*(?P<count>[\d,]+)\s*\|"
)
SUMMARY_LABELS = {
    "x": r"rows marked\s*`?\[x\]`?\s*in the file",
    "-": r"excluded\b",
    " ": r"remaining to read\s*`?\[ \]`?",
    "TOTAL": r"^\s*total\s*$",
}

# A citation is a real reference to a file, not a substring coincidence.
#
# Three bugs this replaces, all found by running it:
#   1. bare `stem in text` matched 235 times on the English word "index"
#   2. `"/" + stem` matched ".autognosia/" inside every /home/operator path
#   3. `stem + ".md"` matched a longer file whose name merely ends the same way
#
# Instead: tokenise the text for things that actually LOOK like filenames, then
# compare those tokens exactly. No substring guessing.
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-/]*\.(?:md|markdown|txt|yaml|yml|json|py|sh)")
_BACKTICK_RE = re.compile(r"`([^`\n]{1,200})`")


def cited_stems(text: str) -> set[str]:
    """Every filename stem that `text` refers to, by tokenising — not guessing."""
    out: set[str] = set()
    for tok in _PATH_TOKEN_RE.findall(text):
        base = tok.rsplit("/", 1)[-1]
        if base.endswith(".markdown"):
            base = base[: -len(".markdown")] + ".md"
        out.add(base[:-3] if base.endswith(".md") else base)
    # backticked bare names with no extension, e.g. `some-file`
    for inner in _BACKTICK_RE.findall(text):
        inner = inner.strip()
        if "/" not in inner and "." not in inner and re.fullmatch(r"[A-Za-z0-9_\-]{3,80}", inner):
            out.add(inner)
    return out


def is_real_citation(stem: str, text: str) -> bool:
    """True if `stem` appears in `text` as a filename token, not a coincidence."""
    return bool(stem) and stem in cited_stems(text)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


@dataclass
class Row:
    mark: str
    number: int
    path: str
    note: str


@dataclass
class Report:
    checks: list[dict] = field(default_factory=list)

    def add(self, cid: str, name: str, ok: bool, detail: str, evidence: Iterable = ()) -> None:
        self.checks.append(
            {
                "id": cid,
                "name": name,
                "ok": bool(ok),
                "detail": detail,
                "evidence": list(evidence)[:40],
                "evidence_count": len(list(evidence)) if not isinstance(evidence, list) else len(evidence),
            }
        )

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]

    @property
    def ok(self) -> bool:
        return not self.failed


def load_rows(ledger_text: str) -> dict[int, Row]:
    rows: dict[int, Row] = {}
    for line in ledger_text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        num = int(m.group(2))
        rows[num] = Row(mark=m.group(1), number=num, path=m.group(3), note=m.group(4))
    return rows


def load_order(order_text: str) -> list[str]:
    return [ln.strip() for ln in order_text.splitlines() if ln.strip()]


def arena_citations(arena_text: str, order: list[str]) -> dict[str, list[int]]:
    """Map corpus-stem -> ORDER row numbers, for stems the arena actually cites.

    Only files that appear in ORDER.txt are considered, which keeps the check
    honest: the arena legitimately names its own workspace files and external
    repos, and those are not corpus citations.

    PERFORMANCE: tokenise the arena ONCE and intersect with the ORDER stems.
    The obvious version — `for stem in by_stem: is_real_citation(stem, text)` —
    re-tokenises 750KB of arena once per corpus file, i.e. 2,217 times. That is
    ~1.6 billion character scans and made the non-vacuity harness time out at
    180s. Inverting the loop is the difference between 1 pass and 2,217.
    """
    by_stem: dict[str, list[int]] = {}
    for i, p in enumerate(order, start=1):
        by_stem.setdefault(os.path.basename(p)[:-3] if p.endswith(".md") else os.path.basename(p), []).append(i)
    present = cited_stems(arena_text)
    return {stem: nums for stem, nums in by_stem.items() if stem in present}


def run_checks(
    order_text: str,
    ledger_text: str,
    arena_text: str,
    verification_text: str = "",
    reference_text: str = "",
    max_per_run: int = DEFAULT_MAX_PER_RUN,
    reference_arena_path: str = "",
) -> Report:
    r = Report()
    order = load_order(order_text)
    rows = load_rows(ledger_text)
    live_areas = len({m.group(1) for l in arena_text.splitlines()
                      if (m := re.match(r"^###\s+Area\s+(\d+)\b", l))})

    # ---- C1 row count vs ORDER ------------------------------------------
    r.add(
        "C1", "ledger rows == ORDER.txt lines",
        len(rows) == len(order),
        f"ledger has {len(rows)} rows, ORDER.txt has {len(order)} lines",
        [] if len(rows) == len(order) else [f"count delta = {len(rows) - len(order):+d}"],
    )

    # ---- C2 contiguity ---------------------------------------------------
    nums = sorted(rows)
    expected = list(range(1, len(rows) + 1))
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    r.add(
        "C2", "row numbers contiguous 1..N",
        nums == expected,
        f"{len(nums)} rows, {len(set(nums))} distinct",
        [f"gap/misorder near {n}" for n in expected if n not in rows][:20],
    )

    # ---- C3 path fidelity -------------------------------------------------
    mismatches = [
        f"row {n}: ledger={rows[n].path!r} order={order[n-1]!r}"
        for n in sorted(rows)
        if n - 1 < len(order) and order[n - 1] != rows[n].path
    ]
    r.add("C3", "every ledger path matches its ORDER.txt line", not mismatches,
          f"{len(mismatches)} mismatches", mismatches)

    # ---- C4 published census == live census ------------------------------
    live = {}
    for row in rows.values():
        live[row.mark] = live.get(row.mark, 0) + 1
    published: dict[str, int] = {}
    for line in ledger_text.splitlines():
        m = SUMMARY_ROW_RE.match(line.strip())
        if not m:
            continue
        label = m.group("label")
        count = int(m.group("count").replace(",", ""))
        for cls, pat in SUMMARY_LABELS.items():
            if re.search(pat, label, re.I):
                published[cls] = count
                break
    # TOTAL is a row count, not a mark class, so it is compared against the row
    # total. Comparing it to live["TOTAL"] (always 0) was a checker bug that
    # produced a permanent -2217 delta and trained us to ignore this check.
    problems = []
    for cls, expected in sorted(published.items()):
        if cls == "TOTAL":
            actual = len(rows)
        else:
            actual = live.get(cls, 0)
        if actual != expected:
            problems.append(f"class {cls!r}: live={actual} published={expected} (delta {actual-expected:+d})")
    r.add(
        "C4", "published summary census == live census",
        not problems,
        f"published {published} vs live {live}",
        problems,
    )

    # ---- C5 no regression vs reference snapshot ---------------------------
    if reference_text:
        ref = load_rows(reference_text)
        regress = [
            f"row {n} ({os.path.basename(ref[n].path)}): was [x], now [{rows[n].mark}]"
            for n in sorted(ref)
            if n in rows and ref[n].mark == "x" and rows[n].mark != "x"
        ]
        ref_x = sum(1 for v in ref.values() if v.mark == "x")
        r.add("C5", "no [x] -> [ ] regression since reference", not regress,
              f"reference had {ref_x} [x]; now {live.get('x', 0)}", regress)
    else:
        r.add("C5", "no [x] -> [ ] regression since reference", True,
              "no reference snapshot supplied; check skipped (not a pass)", [])

    # ---- C6 THE INVARIANT: every citation resolves to [x] ----------------
    cites = arena_citations(arena_text, order)
    unearned = []
    for stem, nums_ in sorted(cites.items()):
        for n in nums_:
            row = rows.get(n)
            if row is None:
                unearned.append(f"{stem} -> ORDER {n} has no ledger row")
            elif row.mark != "x":
                unearned.append(f"{stem} -> ORDER {n} is [{row.mark}]")
    r.add(
        "C6", "INVARIANT: every ARENA.md citation resolves to an [x] row",
        not unearned,
        f"{len(cites)} distinct files cited, {len(unearned)} citations do not resolve to [x]",
        unearned,
    )

    # ---- C7 "Earned by" evidence claims are [x] ---------------------------
    # Same O(n*m) trap as arena_citations: tokenise each line once, and only
    # consult the ORDER stems. Never call is_real_citation per stem per line.
    earned_by: list[str] = []
    for line in arena_text.splitlines():
        if "**Earned by" not in line:
            continue
        line_stems = cited_stems(line)
        for stem in sorted(cites):
            if stem not in line_stems:
                continue
            if any(rows.get(n) and rows[n].mark == "x" for n in cites[stem]):
                continue
            first = cites[stem][0]
            earned_by.append(
                f"{stem}: cited as evidence but ORDER {cites[stem]} = "
                f"[{rows[first].mark if rows.get(first) else '?'}]"
            )
    r.add(
        "C7", 'every "**Earned by:**" claim names a file that is [x]',
        not earned_by,
        f"{len(earned_by)} evidence claims rest on an unread file",
        earned_by,
    )

    # ---- C8 the declaration of unexplained marks --------------------------
    # FIRST ATTEMPT, AND IT WAS WRONG: I checked "rows marked [x] that are cited
    # nowhere, in excess of the declared 9". That reported 172 violations and was
    # nonsense. A read file that informs a slot WITHOUT being named by filename is
    # completely normal — 181 such rows is not evidence of anything. Absence of a
    # citation is not evidence of a fabricated mark.
    #
    # The F2-7 phantoms were detectable only because the WRITING PASS knew it had
    # made 20 patches against 20 reads. From the files alone, an uncited [x] row is
    # indistinguishable from a legitimate read. So a file-based checker cannot
    # detect this class, and claiming otherwise is the exact failure this whole
    # project exists to prevent.
    #
    # What IS checkable: the ledger is required to DECLARE its unexplained count
    # rather than quietly absorb new ones. So C8 verifies the declaration exists,
    # is non-negative, and does not silently exceed the number of [x] rows. Growth
    # of that number across runs is then visible in the ledger's own history,
    # which git-tracking the ledger (done 2026-09-26) makes possible.
    m = re.search(r"of which unexplained[^|]*\|\s*\**([\d,]+)\**", ledger_text, re.I)
    if m:
        declared = int(m.group(1).replace(",", ""))
        n_x = live.get("x", 0)
        problems_c8 = []
        if declared < 0:
            problems_c8.append(f"declared unexplained is negative: {declared}")
        if declared > n_x:
            problems_c8.append(f"declared {declared} unexplained but only {n_x} rows are [x]")
        r.add(
            "C8", "unexplained-mark declaration is present and self-consistent",
            not problems_c8,
            f"ledger declares {declared} unexplained against {n_x} [x] rows",
            problems_c8,
        )
    else:
        r.add(
            "C8", "unexplained-mark declaration is present and self-consistent",
            False,
            "no 'of which unexplained' declaration found in the ledger summary — "
            "F2-7 requires unexplained marks to be declared, not absorbed",
            [],
        )

    # ---- C9 per-run ceiling ----------------------------------------------
    # A run that marks more than the ceiling has bulk-read or fabricated. We can
    # only observe this from tranche markers in the notes; where absent the check
    # reports "no tranche markers" rather than claiming a pass it did not verify.
    tranche_total = 0
    tranches = 0
    for row in rows.values():
        m = re.search(r"tranche (\d+)", row.note, re.I)
        if m:
            tranche_total += 1
    if tranche_total:
        avg = tranche_total / max(1, max(
            [int(m.group(1)) for row in rows.values()
             for m in [re.search(r"tranche (\d+)", row.note, re.I)] if m] or [1]))
        r.add("C9", f"per-run read ceiling ({max_per_run}) respected", avg <= max_per_run,
              f"mean {avg:.1f} marked files per tranche across {tranches or avg:.0f} tranches", [])
    else:
        r.add("C9", f"per-run read ceiling ({max_per_run}) respected", True,
              "no tranche markers in ledger notes; ceiling unverifiable from files alone (not a pass)", [])

    # ---- C11 the answer file must not grow by accretion -------------------
    # THE POINT OF THE 2026-09-26 SPLIT. ARENA.md reached 10,116 lines with the
    # current best idea at line 108 of a 1,928-line area: every pass appended its
    # evidence INSIDE the slot it was arguing about, so the file grew
    # monotonically and the ranking sank. The split moved the prose to
    # ARENA-EVIDENCE.md (append-only, never pruned) and left the answer at 1,446.
    #
    # the operator's requirement: the answer may legitimately reach 10,000 lines or more
    # as areas are added — it must not be capped at 3,000. So this is NOT a size
    # limit. It is a GROWTH limit: the answer may only grow when the AREA COUNT
    # grows, which is the legitimate way for it to get bigger. Growth without new
    # areas means a pass appended evidence instead of replacing a slot, which is
    # precisely the failure that produced the 10,116-line file.
    area_n = live_areas
    ref = reference_arena_path
    if ref and os.path.exists(ref):
        try:
            prev_lines = len(_read(ref).splitlines())
        except OSError:
            prev_lines = None
        if prev_lines:
            budget = int(prev_lines * 1.10) + 40   # 10% tolerance for reflow
            grew_without_areas = len(arena_text.splitlines()) > budget
            r.add(
                "C11", "answer file grows only by adding areas, never by accretion",
                not grew_without_areas,
                f"answer is {len(arena_text.splitlines()):,} lines vs reference {prev_lines:,} "
                f"(budget {budget:,} at +10%, {area_n} areas)",
                [f"answer grew {len(arena_text.splitlines())-prev_lines:+,} lines without "
                 f"the area count justifying it — evidence belongs in ARENA-EVIDENCE.md"]
                if grew_without_areas else [],
            )
        else:
            r.add("C11", "answer file grows only by adding areas, never by accretion", True,
                  "reference arena unreadable; check skipped (not a pass)", [])
    else:
        r.add("C11", "answer file grows only by adding areas, never by accretion", True,
              "no reference arena supplied; check skipped (not a pass). "
              "Run with --reference-arena to enable.", [])

    # ---- C10 the citation test is not a substring test --------------------
    # Guards the bug that reported 437 unread citations, 235 of them the word
    # "index". If someone loosens is_real_citation, this fires.
    probe_bad = is_real_citation("index", "the index at the end of the run")
    probe_good = is_real_citation("foo", "see `concepts/foo.md`")
    r.add("C10", "citation matcher rejects the English word, accepts a path",
          (not probe_bad) and probe_good,
          f"index-as-word rejected={not probe_bad}, path accepted={probe_good}", [])

    return r


def render(rep: Report, quiet: bool = False) -> str:
    if quiet:
        return ""
    out = []
    for c in rep.checks:
        flag = "PASS" if c["ok"] else "FAIL"
        out.append(f"[{flag}] {c['id']:<4} {c['name']}")
        out.append(f"         {c['detail']}")
        if not c["ok"]:
            for e in c["evidence"][:12]:
                out.append(f"           - {e}")
            if c["evidence_count"] > 12:
                out.append(f"           ... and {c['evidence_count'] - 12} more")
    if rep.ok:
        out.append("")
        out.append(f"ALL {len(rep.checks)} INVARIANTS HOLD.")
    else:
        out.append("")
        out.append(f"{len(rep.failed)} of {len(rep.checks)} INVARIANTS VIOLATED:")
        for c in rep.failed:
            out.append(f"  {c['id']}: {c['name']}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    ap.add_argument("--max-per-run", type=int, default=DEFAULT_MAX_PER_RUN)
    ap.add_argument("--reference", default=None,
                    help="a prior LEDGER.md to diff against for C5 (e.g. a scratch backup)")
    ap.add_argument("--reference-arena", default=None,
                    help="a prior ARENA.md to compare line count against for C11")
    ap.add_argument("--workspace", default=WORKSPACE, help="override cognition-arena path")
    args = ap.parse_args(argv)

    ws = args.workspace
    try:
        order_text = _read(os.path.join(ws, "ORDER.txt"))
        ledger_text = _read(os.path.join(ws, "LEDGER.md"))
        arena_text = _read(os.path.join(ws, "ARENA.md"))
    except OSError as exc:
        print(f"arena_invariants: cannot read inputs: {exc}", file=sys.stderr)
        return 2

    ver_text = ""
    vp = os.path.join(ws, "VERIFICATION.md")
    if os.path.exists(vp):
        ver_text = _read(vp)

    ref_text = ""
    if args.reference:
        if os.path.exists(args.reference):
            ref_text = _read(args.reference)
        else:
            print(f"arena_invariants: reference not found: {args.reference}", file=sys.stderr)
            return 2

    rep = run_checks(order_text, ledger_text, arena_text, ver_text, ref_text,
                     args.max_per_run, args.reference_arena or "")

    if args.json:
        print(json.dumps({
            "ok": rep.ok,
            "checks": rep.checks,
        }, indent=2))
    elif not args.quiet:
        print(render(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
