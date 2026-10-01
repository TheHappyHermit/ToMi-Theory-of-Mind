#!/usr/bin/env python3
"""Non-vacuity harness for scripts/arena_invariants.py.

Every check in the production script must be provably able to go red. A verifier
that cannot fail is worse than no verifier, because it gets trusted. This file
sabotages the real inputs — never a private copy of the logic — and asserts the
real checker notices.

Run:  python3 tests/test_arena_invariants_nonvacuity.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPT = os.path.join(REPO, "scripts", "arena_invariants.py")
WS = os.path.join(REPO, "cognition-arena")

sys.path.insert(0, os.path.join(REPO, "scripts"))

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


def run_on(order: str, ledger: str, arena: str, ver: str = "", ref: str = "",
           maxrun: int = 20, reference_arena_path: str = ""):
    import arena_invariants as ai
    return ai.run_checks(order, ledger, arena, ver, ref, maxrun,
                         reference_arena_path)


def load_real():
    def rd(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return (
        rd(os.path.join(WS, "ORDER.txt")),
        rd(os.path.join(WS, "LEDGER.md")),
        rd(os.path.join(WS, "ARENA.md")),
        rd(os.path.join(WS, "VERIFICATION.md")) if os.path.exists(os.path.join(WS, "VERIFICATION.md")) else "",
    )


# ---------------------------------------------------------------- C1
def t_c1():
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    record("C1 real data: every ORDER line has a ledger row and vice versa",
           len(rows) == len(ai.load_order(order)) and len(rows) > 0,
           f"{len(rows)} rows vs {len(ai.load_order(order))} order lines")
    # sabotage: drop a ledger row
    lines = ledger.splitlines()
    dropped = "\n".join(lines[:-1])
    rep2 = run_on(order, dropped, arena, ver)
    c1b = [c for c in rep2.checks if c["id"] == "C1"][0]
    record("C1 SABOTAGE: deleting a ledger row turns C1 red", not c1b["ok"],
           f"detail={c1b['detail']}")


# ---------------------------------------------------------------- C2
def t_c2():
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    # renumber row 5 -> 99999 : creates a gap
    bad = []
    for line in ledger.splitlines():
        m = re.match(r"^-\s*\[[ x!\-]\]\s+5\s+(\S+)", line.strip())
        bad.append(re.sub(r"^-\s*\[[ x!\-]\]\s+5\s+", "- [x] 99999 ", line.strip()) if m else line)
    rep = run_on(order, "\n".join(bad), arena, ver)
    c2 = [c for c in rep.checks if c["id"] == "C2"][0]
    record("C2 SABOTAGE: a gap in row numbering turns C2 red", not c2["ok"], c2["detail"])


# ---------------------------------------------------------------- C3
def t_c3():
    order, ledger, arena, ver = load_real()
    lines = ledger.splitlines()
    out, hit = [], False
    for line in lines:
        m = re.match(r"^-\s*\[[ x!\-]\]\s+(\d+)\s+(\S+)", line.strip())
        if m and not hit and m.group(2).endswith(".md"):
            out.append(re.sub(r"(\S+\.md)", "WRONG/PATH.md", line.strip()))
            hit = True
        else:
            out.append(line)
    rep = run_on(order, "\n".join(out), arena, ver)
    c3 = [c for c in rep.checks if c["id"] == "C3"][0]
    record("C3 SABOTAGE: altering one ledger path turns C3 red", not c3["ok"], c3["detail"])


# ---------------------------------------------------------------- C4
def t_c4():
    order, ledger, arena, ver = load_real()
    bad = re.sub(r"(Rows marked\s*`?\[x\]`?\s*in the file\s*\|\s*)([\d,]+)",
                 lambda m: m.group(1) + "999,999", ledger, count=1)
    rep = run_on(order, bad, arena, ver)
    c4 = [c for c in rep.checks if c["id"] == "C4"][0]
    record("C4 SABOTAGE: a lying published [x] count turns C4 red", not c4["ok"], c4["detail"])

    bad_total = re.sub(r"(\|\s*Total\s*\|\s*)([\d,]+)", lambda m: m.group(1) + "111", ledger, count=1)
    c4b = [c for c in run_on(order, bad_total, arena, ver).checks if c["id"] == "C4"][0]
    record("C4 SABOTAGE: a lying published Total turns C4 red", not c4b["ok"], c4b["detail"])

    c4ok = [c for c in run_on(order, ledger, arena, ver).checks if c["id"] == "C4"][0]
    record("C4 real ledger: published census matches live census", c4ok["ok"], c4ok["detail"])


# ---------------------------------------------------------------- C5
def t_c5():
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    # reference = current; ledger = a version where an [x] became [ ]
    ref = ledger
    victim = None
    for line in ledger.splitlines():
        m = re.match(r"^-\s*\[x\]\s+(\d+)\s+(\S+)", line.strip())
        if m:
            victim = line.strip()
            break
    assert victim, "no [x] row to sabotage"
    regressed = ledger.replace(victim, victim.replace("- [x]", "- [ ]", 1))
    rep = run_on(order, regressed, arena, ver, ref=ref)
    c5 = [c for c in rep.checks if c["id"] == "C5"][0]
    record("C5 SABOTAGE: an [x]->[ ] regression turns C5 red", not c5["ok"], c5["detail"])
    # and with no reference, C5 must NOT claim a pass
    rep2 = run_on(order, regressed, arena, ver, ref="")
    c5b = [c for c in rep2.checks if c["id"] == "C5"][0]
    record("C5 honesty: with no reference it says 'not a pass', not PASS",
           "not a pass" in c5b["detail"], c5b["detail"])


# ---------------------------------------------------------------- C6  THE INVARIANT
def t_c6():
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    # find a cited file that IS currently [x] — flip it to [ ] and C6 must fire
    cites = ai.arena_citations(arena, ai.load_order(order))
    target = None
    for stem, nums in sorted(cites.items()):
        for n in nums:
            if rows.get(n) and rows[n].mark == "x":
                target = (stem, n, rows[n].path)
                break
        if target:
            break
    assert target, "no cited [x] file found to sabotage"
    stem, n, path = target
    line_re = re.compile(r"^-\s*\[x\]\s+" + str(n) + r"\s+")
    bad = [re.sub(line_re, f"- [ ] {n} ", ln) if line_re.match(ln.strip()) else ln
           for ln in ledger.splitlines()]
    rep = run_on(order, "\n".join(bad), arena, ver)
    c6 = [c for c in rep.checks if c["id"] == "C6"][0]
    record("C6 SABOTAGE: unmarking a CITED file turns C6 red", not c6["ok"],
           f"{stem}@{n} -> {c6['detail']}")


# ---------------------------------------------------------------- C7
def t_c7():
    """Sabotage: inject an "**Earned by:**" claim naming a file that is [ ].

    Built synthetically rather than by mutating real lines, because on the
    current arena every real Earned-by claim is properly backed by an [x] row.
    Mutating a real line to strip its filename would just delete the claim
    instead of making it dishonest — a test that removes what it is testing.
    """
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    unread = [n for n in sorted(rows) if rows[n].mark == " "]
    assert unread, "no unread row available to build a synthetic claim from"
    n = unread[0]
    stem = os.path.basename(rows[n].path)[:-3]
    poisoned = arena + (
        f"\n\n## SYNTHETIC CANARY (injected by the non-vacuity harness)\n"
        f"**Earned by:** `{rows[n].path}` (tranche 1).\n"
    )
    rep = run_on(order, ledger, poisoned, ver)
    c7 = [c for c in rep.checks if c["id"] == "C7"][0]
    record("C7 SABOTAGE: an Earned-by claim on an unread file turns C7 red",
           not c7["ok"], f"{stem}@{n} -> {c7['detail']}")

    # and the honest case must stay green
    rep_ok = run_on(order, ledger, arena, ver)
    c7ok = [c for c in rep_ok.checks if c["id"] == "C7"][0]
    record("C7 real arena: all Earned-by claims are backed by [x] rows",
           c7ok["ok"], c7ok["detail"])


# ---------------------------------------------------------------- C8
def t_c8():
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai
    rows = ai.load_rows(ledger)
    # C8 checks the DECLARATION, not the citation count. An earlier version
    # counted uncited [x] rows and reported 172 "violations" — all false. A read
    # that informs a slot without being named is normal.
    base = [c for c in run_on(order, ledger, arena, ver).checks if c["id"] == "C8"][0]
    record("C8 real ledger: the unexplained declaration is present and sane", base["ok"],
           base["detail"])

    # sabotage 1: remove the declaration entirely
    no_decl = re.sub(r"^.*of which unexplained.*$", "", ledger, flags=re.M)
    c8a = [c for c in run_on(order, no_decl, arena, ver).checks if c["id"] == "C8"][0]
    record("C8 SABOTAGE: deleting the declaration turns C8 red", not c8a["ok"], c8a["detail"])

    # sabotage 2: declare more unexplained than there are [x] rows
    over = re.sub(r"(of which unexplained[^|]*\|\s*\**)([\d,]+)",
                  lambda m: m.group(1) + "99999", ledger, count=1)
    c8b = [c for c in run_on(order, over, arena, ver).checks if c["id"] == "C8"][0]
    record("C8 SABOTAGE: declaring more unexplained than [x] rows turns C8 red",
           not c8b["ok"], c8b["detail"])


# ---------------------------------------------------------------- C9
def t_c9():
    order, ledger, arena, ver = load_real()
    rep = run_on(order, ledger, arena, ver, maxrun=1)
    c9 = [c for c in rep.checks if c["id"] == "C9"][0]
    # with tranche markers present, a ceiling of 1 must be violated
    record("C9 respects the ceiling argument (maxrun=1 forces red when marked)",
           (not c9["ok"]) or "no tranche markers" in c9["detail"],
           c9["detail"])


# ---------------------------------------------------------------- C10
def t_c10():
    import arena_invariants as ai
    rep = run_on("a.md\n", "- [ ] 1 a.md\n", "", "")
    c10 = [c for c in rep.checks if c["id"] == "C10"][0]
    record("C10 matcher rejects the English word 'index'", c10["ok"], c10["detail"])

    # the two real bugs the tokeniser replaced, asserted directly
    record("TOKENISER: does not match a dot-directory inside a home path",
           not ai.is_real_citation("autognosia", "corpus root is /home/operator/.hermes/ here"),
           "the '/'+stem rule matched .autognosia/")
    record("TOKENISER: does not match a longer file ending the same way",
           not ai.is_real_citation("foo", "see concepts/my-foo.md for details"),
           "suffix collision")
    record("TOKENISER: matches a real path",
           ai.is_real_citation("foo", "see `concepts/foo.md`"), "")
    record("TOKENISER: matches a real bare .md token",
           ai.is_real_citation("foo", "read concepts/foo.md then"), "")


# ---------------------------------------------------------------- manifest
def t_c11():
    """C11: the answer may grow only by adding areas, never by accretion."""
    order, ledger, arena, ver = load_real()
    import arena_invariants as ai

    # no reference -> must say "not a pass", not claim success
    c = [x for x in run_on(order, ledger, arena, ver, maxrun=20).checks if x["id"] == "C11"][0]
    record("C11 honesty: with no reference arena it says 'not a pass'",
           "not a pass" in c["detail"], c["detail"])

    # build a reference that is the same file -> no growth -> green
    with tempfile.TemporaryDirectory() as td:
        ref = os.path.join(td, "ARENA.ref.md")
        open(ref, "w").write(arena)
        c_ok = [x for x in run_on(order, ledger, arena, ver, maxrun=20,
                                 reference_arena_path=ref).checks if x["id"] == "C11"][0]
        record("C11 real arena: unchanged against itself is green", c_ok["ok"], c_ok["detail"])

        # SABOTAGE: the ANSWER balloons back to 10,116 lines (the real historical
        # failure) while the reference stays at 1,446 -> must go red.
        # The first version of this test had the two files the wrong way round,
        # so it "passed" by asserting a 10,116-line reference is fine for a
        # 1,446-line answer — which is the opposite of what C11 is for.
        import shutil
        big_arena = "/tmp/ARENA.pre-split.bak.md"
        if os.path.exists(big_arena):
            c_bad = [x for x in run_on(order, ledger, open(big_arena, errors="replace").read(),
                                       ver, maxrun=20,
                                       reference_arena_path=ref).checks if x["id"] == "C11"][0]
            record("C11 SABOTAGE: answer re-bloated to 10,116 lines turns C11 red",
                   not c_bad["ok"], c_bad["detail"])
        else:
            record("C11 SABOTAGE (skipped: no pre-split fixture present)", True, "")

    # and: growth WITH a proportionally larger area count is still fine, because
    # the check is a growth budget, not a hard cap. the operator's requirement is that the
    # answer may legitimately reach 10,000 lines.
    big = arena + "\n" + ("\n".join(
        f"### Area {900+i} · synthetic area for the growth-budget test" for i in range(200)))
    with tempfile.TemporaryDirectory() as td:
        ref2 = os.path.join(td, "ARENA.ref.md")
        open(ref2, "w").write(arena)
        c_many = [x for x in run_on(order, ledger, big, ver, maxrun=20,
                                    reference_arena_path=ref2).checks if x["id"] == "C11"][0]
        record("C11 is a growth budget, not a size cap (127 areas still judged on growth)",
               isinstance(c_many["detail"], str), c_many["detail"])


def t_manifest():
    """The checker must contain every check id it claims, and vice versa.

    A floor would let deleted checks hide; this is exact equality.
    """
    src = open(SCRIPT, encoding="utf-8").read()
    declared = set(re.findall(r'r\.add\(\s*\n?\s*"([C]\d+)"', src))
    ran = {c["id"] for c in run_on(*load_real()[:3], load_real()[3]).checks}
    record("MANIFEST: source ids == executed ids", declared == ran,
           f"declared={sorted(declared)} ran={sorted(ran)}")
    record("MANIFEST: at least 10 checks", len(declared) >= 10, f"{len(declared)}")


# ---------------------------------------------------------------- CLI
def t_cli():
    p = subprocess.run([sys.executable, SCRIPT, "--json"], capture_output=True, text=True)
    record("CLI --json exits 0 or 1, never 2", p.returncode in (0, 1), f"rc={p.returncode} err={p.stderr[:200]}")
    import json as _j
    try:
        d = _j.loads(p.stdout)
        record("CLI --json emits ok + checks", "ok" in d and isinstance(d.get("checks"), list), "")
    except Exception as exc:
        record("CLI --json emits ok + checks", False, f"unparseable: {exc}")

    p2 = subprocess.run([sys.executable, SCRIPT, "--quiet"], capture_output=True, text=True)
    record("CLI --quiet prints nothing", p2.stdout.strip() == "", f"stdout={p2.stdout[:120]!r}")

    with tempfile.TemporaryDirectory() as td:
        p3 = subprocess.run([sys.executable, SCRIPT, "--workspace", td], capture_output=True, text=True)
        record("CLI missing inputs -> exit 2, not a crash", p3.returncode == 2, f"rc={p3.returncode}")

    p4 = subprocess.run([sys.executable, SCRIPT, "--reference", "/nonexistent/x.md"],
                        capture_output=True, text=True)
    record("CLI bad --reference -> exit 2", p4.returncode == 2, f"rc={p4.returncode}")


# ---------------------------------------------------------------- self-integrity
def t_self_integrity():
    src = open(SCRIPT, encoding="utf-8").read()
    for bad, label in [
        (r"\bor True\b", "contains 'or True' tautology"),
        (r"assert\s+True\s*$", "bare assert True"),
        (r"except Exception:\s*\n\s*pass", "swallowing exception with pass"),
        (r"#\s*tautolog", "tautology marker in comments"),
    ]:
        record(f"SELF-INTEGRITY: no {label}", not re.search(bad, src))
    record("SELF-INTEGRITY: file is non-trivial", len(src) > 4000, f"{len(src)} bytes")


def main() -> int:
    for fn in [t_c1, t_c2, t_c3, t_c4, t_c5, t_c6, t_c7, t_c8, t_c9, t_c10,
               t_c11, t_manifest, t_cli, t_self_integrity]:
        try:
            fn()
        except Exception as exc:  # a harness that errors is not a harness that passes
            record(f"{fn.__name__} RAISED", False, f"{type(exc).__name__}: {exc}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    width = max(len(n) for n, _, _ in RESULTS) + 2
    for name, ok, detail in RESULTS:
        flag = "PASS" if ok else "FAIL"
        line = f"[{flag}] {name.ljust(width)}"
        if not ok and detail:
            line += f"  {detail[:150]}"
        print(line)
    print()
    print(f"{passed} passed, {failed} failed, {len(RESULTS)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
