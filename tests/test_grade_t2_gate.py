"""Tests for the T2 promotion gate in grade_all.py.

THE BUG THIS LOCKS DOWN
  t2_all_match() looked its verdict up with the bare identifier:

      v = table.get(i, {}).get('verdict', 'absent')

  but the evidence table is keyed `path::identifier`, because two
  files can cite one identifier and need not cite it equally well. So
  EVERY lookup missed, every file reported "N of N not matched:
  absent", and the T2 gate could never promote anything -- regardless
  of how good the citations actually were.

  That matters for how a green result should be read. If this test
  were the only thing between a broken gate and a passing one, then
  "T2 passed" could mean "the lookup stopped missing" rather than "the
  citations are right". test_pass_requires_real_matched_rows exists to
  keep those two meanings distinguishable.

  Live demonstration, from the table as it stood:
      t2_all_match(srcs, t, rel_path=p)  -> True,  "all 4 ... matched"
      t2_all_match(srcs, t)              -> False, "4 of 4 ... absent"
"""
import importlib.util
import json
import unittest
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / 'docs' / 'audit' / 't2-verification.json'
BRAIN = Path('/home/operator/.hermes/oracle/brain')

spec = importlib.util.spec_from_file_location('grade', REPO / 'scripts' /
                                              'grade_all.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def table():
    if not TABLE.exists():
        return None
    return json.load(open(TABLE, encoding='utf-8'))


class TestLookupKey(unittest.TestCase):
    def setUp(self):
        self.t = table()
        if self.t is None:
            self.skipTest('t2 table not built')

    def test_table_is_path_scoped(self):
        """If this ever fails, the identifier-only fallback in
        lookup_verdict is doing the work and the main path is dead."""
        keys = [k for k in self.t if '::' in k]
        self.assertEqual(len(keys), len(self.t),
                         'table is no longer path-scoped')

    def test_file_scoped_key_resolves(self):
        """A row that exists must be found via its file."""
        rows = [(k, v) for k, v in self.t.items()
                if v.get('verdict') == 'match' and '::' in k]
        self.assertTrue(rows, 'no matched rows to test against')
        key, _v = rows[0]
        path, ident = key.split('::', 1)
        self.assertEqual(G.lookup_verdict(self.t, path, ident), 'match')

    def test_vault_prefix_is_stripped(self):
        """grade_all walks absolute paths; the table stores relative."""
        key = next(k for k, v in self.t.items()
                   if v.get('verdict') == 'match' and '::' in k)
        path, ident = key.split('::', 1)
        self.assertEqual(
            G.lookup_verdict(self.t, 'oracle/brain/' + path, ident), 'match')

    def test_bare_identifier_does_not_silently_match(self):
        """A missing row must read 'absent', never default to 'match'.

        Defaulting would turn a lookup bug into a promotion.
        """
        self.assertEqual(
            G.lookup_verdict(self.t, 'research/does-not-exist.md',
                             'arxiv:9999.99999'), 'absent')


class TestGateBehaviour(unittest.TestCase):
    def setUp(self):
        self.t = table()
        if self.t is None:
            self.skipTest('t2 table not built')

    def _all_match_file(self):
        by_file = defaultdict(list)
        for k, v in self.t.items():
            if '::' in k:
                by_file[k.split('::')[0]].append(v.get('verdict'))
        for f, verdicts in by_file.items():
            if len(verdicts) >= 3 and all(x == 'match' for x in verdicts):
                return f
        return None

    def test_a_fully_matched_file_passes_with_its_path(self):
        """The positive case, end to end through derive()'s inputs.

        The fixture is built here rather than taken from the live table.
        The live table is invalidated and re-derived as part of the
        repair work, so a file can gain an unresolved identifier between
        two runs of this suite and the test then fails for a reason that
        has nothing to do with the gate it is testing -- which is what
        happened: it picked a real file whose sources list also carried
        a doi that had just been invalidated, and reported
        "fully matched file did not pass" for a row that was not in the
        fixture at all.
        """
        f = 'Attention/Load-Theory-Attention.md'
        ids = ('10.1037/0033-2909.115.7.439',
               '10.1037/a0046060',
               '10.1146/annurev-psych-010418-103041')
        fixture = {f + '::doi:' + d: {'verdict': 'match'} for d in ids}
        srcs = ['https://doi.org/' + d for d in ids]
        ok, why = G.t2_all_match(srcs, fixture, rel_path='oracle/brain/' + f)
        self.assertTrue(ok, 'fully matched file did not pass: %s' % why)
        # assert the gate's own words, not a guess at them
        self.assertIn('matched', why)
        self.assertNotIn('not matched', why)

    def test_one_mismatch_blocks_the_file(self):
        """The gate is all-or-nothing per file, by design."""
        by_file = defaultdict(list)
        for k, v in self.t.items():
            if '::' in k:
                by_file[k.split('::')[0]].append(
                    (k.split('::')[1], v.get('verdict')))
        mixed = [(f, r) for f, r in by_file.items()
                 if any(x[1] == 'match' for x in r)
                 and any(x[1] != 'match' for x in r)]
        if not mixed:
            self.skipTest('no mixed file available')
        f, rows = mixed[0]
        good = [i for i, v in rows if v == 'match']
        srcs = self._sources(f, only=good)
        ok, _why = G.t2_all_match(srcs, self.t, rel_path='oracle/brain/' + f)
        self.assertTrue(ok, 'a subset of matched identifiers should pass')

    def test_pass_requires_real_matched_rows(self):
        """A pass must be backed by rows that exist and say `match`.

        Without this, a fixed lookup plus an empty or absent-heavy table
        would read as a green T2 -- the failure mode this whole module
        is guarding.

        Note on the second assertion. It originally required the LIVE table to
        still contain at least one non-match row, on the reasoning that a
        table of all-matches cannot show the gate discriminating between
        verdicts. That stopped being true once the citation-repair work drove
        the live table to 946 match / 0 mismatch / 0 unresolvable -- the state
        this suite exists to reach. Asserting a defect still exists means the
        test now fails precisely because the work succeeded.

        The discrimination evidence is supplied here by a SYNTHETIC fixture
        instead, which is strictly better: it keeps testing the gate's ability
        to reject a bad row without depending on the corpus still containing
        one. The live table's cleanliness is asserted separately, by
        test_no_mismatches_remain.
        """
        self.assertGreater(
            sum(1 for v in self.t.values() if v.get('verdict') == 'match'),
            0, 'no matched rows at all')

        # Synthetic discrimination check: a table whose rows disagree with
        # the identifiers presented must NOT pass.
        mixed_fixture = {
            'oracle/brain/Synthetic/File.md::doi:10.0000/synthetic.1': {'verdict': 'match'},
            'oracle/brain/Synthetic/File.md::doi:10.0000/synthetic.2': {'verdict': 'mismatch'},
        }
        srcs = ['https://doi.org/10.0000/synthetic.1',
                'https://doi.org/10.0000/synthetic.2']
        ok, why = G.t2_all_match(srcs, mixed_fixture,
                                 rel_path='oracle/brain/Synthetic/File.md')
        self.assertFalse(ok, 'gate passed a table containing a mismatch row')
        self.assertIn('not matched', why)

    def test_no_mismatches_remain(self):
        """The state this work was for: 0 mismatches.

        Asserted rather than assumed, so a later edit that reintroduces
        one fails here instead of quietly lowering confidence.
        """
        bad = [k for k, v in self.t.items()
               if v.get('verdict') == 'mismatch']
        self.assertEqual(bad, [],
                         'mismatches remain: %s' % bad[:3])

    @staticmethod
    def _sources(path, only=None):
        """The real frontmatter sources, so t2_ids sees real strings."""
        import yaml
        p = BRAIN / path
        if not p.exists():
            return []
        text = p.read_text(encoding='utf-8')
        end = text.find('\n---', 3)
        if end == -1:
            return []
        meta = yaml.safe_load(text[3:end]) or {}
        srcs = [str(s) for s in (meta.get('sources') or [])]
        if only:
            keep = set(only)
            srcs = [s for s in srcs
                    if any(i.split(':')[-1] in s for i in keep)]
        return srcs


if __name__ == '__main__':
    unittest.main()
