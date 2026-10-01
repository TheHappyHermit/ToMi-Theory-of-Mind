#!/usr/bin/env python3
"""Non-vacuity tests for citation_remediation's twin/ambiguity handling.

WHY THIS FILE EXISTS
--------------------
The AMBIGUOUS branch shipped reporting 0 while 15 real cases existed, because
`build_stem_index()` keyed on the filename with the `.md` suffix and
`arena_citations()` returns the stem without it. Every lookup missed, the
branch never ran, and it printed a confident 0.

That is the same failure mode this project has now hit three times: a control
that cannot fail. So the branch gets a sabotage test that must detect the
defect, not just a test that passes.

Run:  python3 tests/test_citation_remediation_twins.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import citation_remediation as cr  # noqa: E402
import arena_invariants as ai  # noqa: E402


ORDER = [
    "active-wiki/research/RESEARCH.md",   # 1  read
    "active-wiki/concepts/other.md",      # 2
    "oracle/brain/research/RESEARCH.md",  # 3  unread twin of 1
    "oracle/brain/concepts/other.md",     # 4  unread twin of 2
    "oracle/brain/concepts/solo.md",      # 5  unique stem, unread
    "active-wiki/concepts/second.md",     # 6  unique stem, read
]


def rows(marks):
    return {i: ai.Row(mark=m, number=i, path=p, note="")
            for i, (p, m) in enumerate(zip(ORDER, marks), 1)}


class TestStemIndex(unittest.TestCase):
    def test_keyed_on_stem_not_filename(self):
        """The defect that shipped: .md in the key, stem in the query."""
        idx = cr.build_stem_index(ORDER)
        self.assertIn("RESEARCH", idx, "stem must be the key")
        self.assertNotIn("RESEARCH.md", idx, "filename must not be the key")
        self.assertEqual(sorted(idx["RESEARCH"]), [1, 3])

    def test_collisions_grouped(self):
        idx = cr.build_stem_index(ORDER)
        self.assertEqual(sorted(idx["other"]), [2, 4])
        self.assertEqual(idx["solo"], [5])      # unique stem, one row
        self.assertEqual(idx["second"], [6])    # unique stem, one row

    def test_solo_stem_has_no_twin(self):
        idx = cr.build_stem_index(ORDER)
        self.assertEqual(idx["solo"], [5])
        self.assertEqual(idx["second"], [6])

    def test_every_citation_stem_resolves(self):
        """No citation may fall through the index — that is how 15 got missed."""
        idx = cr.build_stem_index(ORDER)
        cites = ai.arena_citations("see RESEARCH.md and solo.md and other.md", ORDER)
        self.assertTrue(cites, "fixture must produce citations")
        for stem in cites:
            self.assertIn(stem, idx, f"cited stem {stem!r} missing from index")


class TestUnearnedClassification(unittest.TestCase):
    def test_read_twin_makes_citation_ambiguous_not_unearned(self):
        r = cr.unearned(ORDER, rows("x  x     "), "see RESEARCH.md", cr.build_stem_index(ORDER))
        rec = r[3]
        self.assertTrue(rec["ambiguous"])
        self.assertEqual(rec["read_twins"], [1])
        self.assertEqual(rec["cited_as"], ["RESEARCH"])

    def test_unique_unread_file_is_truly_unearned(self):
        idx = cr.build_stem_index(ORDER)
        r = cr.unearned(ORDER, rows("     x "), "see solo.md", idx)
        # ORDER 5 is unread and has no twin -> must NOT be called ambiguous
        self.assertTrue(5 in r)
        self.assertFalse(r[5]["ambiguous"])
        self.assertEqual(r[5]["read_twins"], [])

    def test_excluded_twin_is_not_read_evidence(self):
        """A [-] twin is not a read. The citation still needs proving."""
        idx = cr.build_stem_index(ORDER)
        r = cr.unearned(ORDER, rows("-  x    "), "see RESEARCH.md", idx)
        self.assertEqual(r[3]["read_twins"], [], "[-] must not count as [x]")

    def test_sabotage_stem_key_breakage_is_detected(self):
        """Reintroduce the shipped bug; the test must fail, not pass quietly."""
        broken = {}
        for i, p in enumerate(ORDER, 1):
            broken.setdefault(p.rsplit("/", 1)[-1], []).append(i)  # .md kept
        cites = ai.arena_citations("see RESEARCH.md", ORDER)
        missed = [s for s in cites if s not in broken]
        self.assertTrue(missed, "sabotaged index should miss the stem")
        self.assertNotEqual(broken, cr.build_stem_index(ORDER))


class TestPlanBuckets(unittest.TestCase):
    """main() must route an ambiguous citation to AMBIGUOUS, not RE-READ."""

    def _plan(self, order, markstr, arena):
        todo = cr.unearned(order, cr.ai.load_rows(cr.read(cr.LEDGER)) if False else
                           {i: ai.Row(mark=m, number=i, path=p, note="")
                            for i, (p, m) in enumerate(zip(order, markstr), 1)},
                           arena, cr.build_stem_index(order))
        plan = {"PROVEN": [], "RE-READ": [], "STRIKE": [], "AMBIGUOUS": []}
        for n, rec in sorted(todo.items()):
            if rec["read_twins"]:
                plan["AMBIGUOUS"].append(rec)
            elif rec["mark"] in ("-", "!"):
                plan["STRIKE"].append(rec)
            else:
                plan["RE-READ"].append(rec)
        return plan

    def test_twin_routes_to_ambiguous(self):
        plan = self._plan(ORDER, "x  x     ", "see RESEARCH.md")
        self.assertEqual(len(plan["AMBIGUOUS"]), 1)
        self.assertEqual(plan["AMBIGUOUS"][0]["order"], 3)
        self.assertEqual(len(plan["RE-READ"]), 0, "must not demand a re-read")

    def test_two_unique_stems_one_read_one_not(self):
        """solo.md exists once and is unread -> a real re-read, not a twin."""
        plan = self._plan(ORDER, "x  x   x", "see solo.md")
        self.assertEqual(plan["AMBIGUOUS"], [])
        self.assertEqual(len(plan["RE-READ"]), 1)
        self.assertEqual(plan["RE-READ"][0]["order"], 5)

    def test_genuinely_unread_unique_routes_to_reread(self):
        order = ORDER + ["oracle/brain/concepts/unique.md"]
        marks = "x  x     " + " "
        plan = self._plan(order, marks, "see unique.md")
        self.assertEqual(len(plan["RE-READ"]), 1)
        self.assertEqual(plan["RE-READ"][0]["order"], 7)


class TestLiveWorkspace(unittest.TestCase):
    """Guards against the branch going dead on the real corpus again."""

    def test_ambiguous_branch_not_vacuous(self):
        if not os.path.exists(cr.ARENA):
            self.skipTest("live arena not present")
        order = cr.load_order()
        rows_ = cr.ai.load_rows(cr.read(cr.LEDGER))
        recs = cr.unearned(order, rows_, cr.read(cr.ARENA), cr.build_stem_index(order))
        ambiguous = [r for r in recs.values() if r.get("read_twins")]
        for r in ambiguous:
            self.assertTrue(r["exists"], f"ORDER {r['order']} path does not exist")
        # every cited stem must have produced a record OR been already [x]
        cites = ai.arena_citations(cr.read(cr.ARENA), order)
        idx = cr.build_stem_index(order)
        for stem in cites:
            self.assertIn(stem, idx, f"live citation {stem!r} does not resolve")


if __name__ == "__main__":
    unittest.main(verbosity=2)
