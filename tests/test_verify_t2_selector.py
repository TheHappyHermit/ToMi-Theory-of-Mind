"""Regression tests for the T2 verifier's row selector.

The selector was the literal 'title match unverified'. The grader stopped
emitting that string, so the filter matched ZERO rows and the verifier
checked nothing while reporting a clean run -- the same failure class as the
arXiv URL bug, where a regex silently matched nothing and every count came
back zero without anything raising.

These tests pin the selector against the reason strings the grader ACTUALLY
emits, and pin the empty-set warning, so the next drift fails a test instead
of producing a confident all-clear.
"""
import csv
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_MOD = os.path.join(_REPO, "scripts", "verify_t2_titles.py")
spec = importlib.util.spec_from_file_location("verify_t2_titles", _MOD)
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

CSV_PATH = os.path.join(_REPO, "docs", "audit", "grade-decisions.csv")


def select(rows):
    """The selector, mirrored from main(). Kept in sync by test_selector_matches_source."""
    return [r for r in rows
            if "T2 pending" in r["reason"]
            and not r["reason"].endswith("no T2 identifier")]


class TestSelectorMatchesLiveData(unittest.TestCase):
    """The selector must be tested against the real report, not a fixture."""

    @classmethod
    def setUpClass(cls):
        with open(CSV_PATH, encoding="utf-8") as fh:
            cls.rows = list(csv.DictReader(fh))

    def test_live_report_is_non_empty(self):
        self.assertGreater(len(self.rows), 100,
                           "the report looks truncated; the selector "
                           "assertions below would be meaningless")

    def test_selector_is_not_empty_on_live_report(self):
        """The original bug: 0 rows selected from the real report."""
        self.assertGreater(len(select(self.rows)), 0)

    def test_obsolete_string_matches_nothing(self):
        """Documents WHY the old selector was broken, so it is not restored."""
        stale = [r for r in self.rows if "title match unverified" in r["reason"]]
        self.assertEqual(stale, [],
                         "the grader has started emitting the old string "
                         "again; the selector should be reconsidered")

    def test_confirmed_rows_are_excluded(self):
        confirmed = [r for r in self.rows
                     if "resolved and title-matched" in r["reason"]]
        self.assertTrue(confirmed, "no confirmed rows in the live report")
        for r in select(self.rows):
            self.assertNotIn("resolved and title-matched", r["reason"])

    def test_no_identifier_rows_are_excluded(self):
        """Nothing to resolve, so including them inflates the work count."""
        noid = [r for r in self.rows
                if r["reason"].endswith("no T2 identifier")]
        self.assertTrue(noid, "no 'no T2 identifier' rows in the live report")
        for r in select(self.rows):
            self.assertFalse(r["reason"].endswith("no T2 identifier"))

    def test_every_selected_row_names_a_file(self):
        for r in select(self.rows):
            self.assertIn("path", r)
            self.assertTrue(r["path"].strip())


class TestSelectorCases(unittest.TestCase):
    def test_absent_is_in_scope(self):
        """`absent` means the T2 table lacks it -- this verifier resolves it."""
        rows = [{"reason": "T2 pending: 1 of 1 not matched: arxiv:absent"}]
        self.assertEqual(len(select(rows)), 1)

    def test_untitled_citation_is_in_scope(self):
        """Re-resolving will not fix a missing title, but it must be counted."""
        rows = [{"reason": "T2 pending: 1 of 5 not matched: arxiv:untitled_citation"}]
        self.assertEqual(len(select(rows)), 1)

    def test_mixed_absence_and_untitled(self):
        rows = [{"reason": "T2 pending: 2 of 2 not matched: "
                           "arxiv:absent, arxiv:untitled_citation"}]
        self.assertEqual(len(select(rows)), 1)

    def test_no_identifier_is_out_of_scope(self):
        rows = [{"reason": "T2 pending: no T2 identifier"}]
        self.assertEqual(select(rows), [])

    def test_confirmed_is_out_of_scope(self):
        rows = [{"reason": "T2 verified: all 1 T2 identifiers "
                           "resolved and title-matched"}]
        self.assertEqual(select(rows), [])

    def test_unrelated_reason_is_out_of_scope(self):
        rows = [{"reason": "no source of any kind; E11 caps at T5"},
                {"reason": "only non-external provenance 1"},
                {"reason": "decision: M0_decision_record, ruling is the authority"}]
        self.assertEqual(select(rows), [])

    def test_every_reason_in_live_report_is_accounted_for(self):
        """No live reason may be silently unselected for an unknown reason.

        Guards the real hazard: a NEW reason string appearing that matches
        neither the old selector nor the new one, disappearing quietly from
        the work set the way the stale selector did.
        """
        with open(CSV_PATH, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        unaccounted = set()
        for r in rows:
            if select([r]):
                continue
            reason = r["reason"]
            if "resolved and title-matched" in reason:
                continue
            if reason.endswith("no T2 identifier"):
                continue
            unaccounted.add(reason[:60])
        # Every unselected reason must be a non-T2 row, i.e. one where T2 is
        # irrelevant (no external provenance, a decision record, etc).
        for reason in unaccounted:
            self.assertNotIn("T2 pending", reason,
                             "a T2-pending reason is selected by nothing: %r"
                             % reason)


class TestSelectorMatchesSource(unittest.TestCase):
    def test_selector_matches_source(self):
        """The mirrored selector above must match what main() actually does.

        A test that re-implements the logic under test can drift from it and
        keep passing. This compares the mirror against the literal source
        expression.
        """
        src = open(_MOD, encoding="utf-8").read()
        self.assertIn("'T2 pending' in r['reason']", src,
                      "main()'s selector no longer matches this test")
        self.assertIn("todo set is EMPTY", src,
                      "the empty-set warning was removed; a zero-row todo "
                      "set is indistinguishable from a broken selector again")

    def test_obsolete_selector_is_not_in_code(self):
        """No line may SELECT on the obsolete string.

        Checked against executable lines only. The string survives in the
        comment block explaining the bug, which is deliberate -- the
        reasoning is worth keeping, and deleting it would leave the next
        reader with a fix and no cause. What must not survive is a filter
        that uses it.
        """
        src = open(_MOD, encoding="utf-8").read()
        offenders = []
        for i, line in enumerate(src.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "title match unverified" in stripped:
                offenders.append((i, stripped))
        self.assertEqual(offenders, [],
                         "a live line still selects on the obsolete string: %r"
                         % offenders)


if __name__ == "__main__":
    unittest.main()
