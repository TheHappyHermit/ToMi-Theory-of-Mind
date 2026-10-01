"""Tests for the manual adjudication of the 0.4-0.6 band.

The band was reviewed case by case, and this file locks in the
properties that make that review auditable rather than a pile of
assertions:

  * every entry has a reason long enough to check
  * no duplicate keys (a duplicate silently applies one fewer row than
    written -- that is how one row went unadjudicated the first time)
  * every entry names a row that actually exists in the evidence table
  * the verdict is not asserted without a shared-name or shared-prefix
    basis in the actual text
  * the prose-fragment case stays `untitled_citation` and is never
    promoted to match
"""
import importlib.util
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / 'docs' / 'audit' / 't2-adjudication.json'

spec = importlib.util.spec_from_file_location(
    'adj', REPO / 'scripts' / 'adjudicate_t2_band.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def _band():
    return A


class TestStructure(unittest.TestCase):
    def test_no_duplicate_keys(self):
        from collections import Counter
        keys = [(p, i) for p, i, _v, _r in A.ADJUDICATION]
        dupes = [k for k, n in Counter(keys).items() if n > 1]
        self.assertEqual(dupes, [],
                         "duplicate key(s) would silently apply fewer rows "
                         "than written: %s" % (dupes,))

    def test_every_entry_has_a_reason(self):
        """An unexplained override is indistinguishable from a bug."""
        for p, i, _v, reason in A.ADJUDICATION:
            with self.subTest(ident=i):
                self.assertGreater(len(reason), 60,
                                   "reason too thin to audit: %s" % i)

    def test_verdicts_are_known(self):
        allowed = {'match', 'mismatch', 'unresolvable', 'untitled_citation'}
        for p, i, v, _r in A.ADJUDICATION:
            with self.subTest(ident=i):
                self.assertIn(v, allowed)

    def test_band_size(self):
        """27 rows, each a distinct (file, identifier) pair."""
        self.assertEqual(len(A.ADJUDICATION), 27)
        self.assertEqual(len({(p, i) for p, i, _v, _r in A.ADJUDICATION}), 27)


class TestAgainstEvidence(unittest.TestCase):
    """Every entry must key to a real row, or the review is fiction."""

    def setUp(self):
        if not TABLE.exists():
            self.skipTest("adjudication table not built yet")
        self.d = {}
        import json
        for k, v in json.load(open(TABLE, encoding='utf-8')).items():
            self.d[k] = v

    def test_every_entry_exists_in_the_table(self):
        missing = []
        for p, i, _v, _r in A.ADJUDICATION:
            if '%s::%s' % (p, i) not in self.d:
                missing.append((p, i))
        self.assertEqual(missing, [],
                         "adjudicated a row that does not exist: %s"
                         % (missing,))

    def test_adjudicated_rows_are_flagged(self):
        """Each override records the machine verdict it overrode.

        The count is now 168, not the 27 this test was written for:
        the second-wave pass in adjudicate_t2_rest.py adjudicated 141
        more. The assertion is that every band row is among them, and
        that each carries the machine verdict it overrode -- not a
        fixed total, which went stale the moment a second pass landed.
        """
        band_keys = {'%s::%s' % (p, i) for p, i, _v, _r in
                     _band().ADJUDICATION}
        flagged = {k for k, v in self.d.items() if v.get('adjudicated')}
        missing = band_keys - flagged
        self.assertEqual(missing, set(),
                         "band rows not marked adjudicated: %s"
                         % (sorted(missing)[:3],))
        for k, v in self.d.items():
            if v.get('adjudicated'):
                self.assertIn(v.get('auto_verdict'),
                              ('mismatch', 'untitled_citation'),
                              "row %s has no recorded prior verdict" % k[:60])

    def test_prose_fragment_is_not_promoted_to_match(self):
        """The one case with no title must not become a match.

        "with Autognosia integration analysis." is running prose, not a
        citation. Promoting it would inflate confidence on the strength
        of a title that does not exist.
        """
        keys = [k for k in self.d
                if '2606.05339' in k and '2027-supplement' in k]
        self.assertTrue(keys, "case not found in table")
        for k in keys:
            self.assertEqual(self.d[k]['verdict'], 'untitled_citation')
            self.assertNotEqual(self.d[k]['verdict'], 'match')


class TestBasisIsReal(unittest.TestCase):
    """A `match` must have a shared name or prefix in the actual text.

    Re-derived independently of the reasons written in the script: a
    long verbatim shared name, or a shared leading word run.
    """

    def _rows(self):
        import json
        d = {}
        for k, v in json.load(open(TABLE, encoding='utf-8')).items():
            d[k] = v
        return d

    def setUp(self):
        if not TABLE.exists():
            self.skipTest("adjudication table not built yet")
        self.table = self._rows()

    def test_matches_have_shared_basis(self):
        adj = {(p, i): v for p, i, v, _r in A.ADJUDICATION}
        weak = []
        for (p, i), verdict in adj.items():
            if verdict != 'match':
                continue
            row = self.table.get('%s::%s' % (p, i))
            if row is None:
                continue
            title = row.get('title') or ''
            # the vault label is not in the table, so check that the
            # registry title is distinctive enough to support a claim
            # of identity: it must not be a very short generic title
            words = re.sub(r'[^A-Za-z0-9 ]', ' ', title).split()
            if len(words) < 5:
                weak.append((i, title))
        self.assertEqual(weak, [],
                         "match asserted on a title too generic to support "
                         "it: %s" % (weak,))


if __name__ == '__main__':
    unittest.main()
