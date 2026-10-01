"""A pruner that deletes evidence is worse than no pruner.

Repairing citations can leave the evidence table describing something
that is no longer true. It did, twice in one file:
apply_verified_dois_13.py replaced the bare stem 10.1016/0010-0285
with an unbounded re.sub, and the stem matched INSIDE two complete
valid DOIs:

    10.1016/0010-0285(80)90005-5   Treisman & Gelade 1980
    10.1016/0010-0285(82)90006-8   Treisman & Schmidt 1982

Both were restored from backup, so the file is correct again -- and the
table still carried rows for the CORRUPTED identifiers, which no file
cites any more. Those two `unresolvable` rows kept the T2 gate shut for
a file that is in fact 14/14 matched. A verifier must not be repairable
into a state where its own history of mistakes blocks it.

The interesting part is how nearly this pruner deleted live evidence.
Four rules were tried, and three of them were wrong:

  1. "a 34-char prefix of the identifier appears in the text"
     -> proposed to drop 19 LIVE rows, including the one untitled row.
  2. "some sibling identifier is a prefix of this one"
     -> dropped 10.1016/S0010-0277(85)80010-3, whose only fault is a
        wrong final character (disk has ...-X). A typo is exactly what
        this exercise exists to catch.
  3. "some sibling identifier extends this one"
     -> same class of error, other direction.
  4. siblings gathered by regex, then a substring test
     -> found 0, because the character class stopped AT the closing
        paren and could never capture an Elsevier DOI.

The rule that works is the corruption's own shape: the ghost carries an
article code, and a DIFFERENT identifier in the same file carries that
SAME article code. That can only happen when a completion was appended
to a suffix that already existed. Matching the tail against a live
identifier is what keeps it away from the -3/-X typo, where the tails
differ.

So these tests pin both directions: the ghosts go, and the live rows
stay -- including the typo, the untitled row, and every `match`.
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load(brain, table):
    """Load prune_ghost_t2_rows with BRAIN and TABLE redirected."""
    src = (REPO / 'scripts' / 'prune_ghost_t2_rows.py').read_text()
    src = src.replace(
        "TABLE = REPO / 'docs' / 'audit' / 't2-verification.json'",
        'TABLE = Path(%r)' % str(table))
    src = src.replace(
        "BRAIN = Path('/home/operator/.hermes/oracle/brain')",
        'BRAIN = Path(%r)' % str(brain))
    # REPO is no longer used for the backup path -- the script takes it
    # from TABLE.parent -- but redirect it anyway so nothing in the
    # module can reach the real audit directory from a test. Without
    # this the fixture wrote 7-row backup files into
    # docs/audit/ on every run.
    src = src.replace(
        "REPO = Path('/home/operator/hermes-brain')",
        'REPO = Path(%r)' % str(brain.parent))
    spec = importlib.util.spec_from_loader('pg', loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(src, 'prune_ghost_t2_rows', 'exec'), mod.__dict__)
    return mod


class TestGhostPruning(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ghost-'))
        self.brain = self.tmp / 'brain'
        self.brain.mkdir()
        self.table = self.tmp / 't2.json'
        # A file that has been correctly restored: the two real DOIs
        # are present and neither corrupted form appears.
        (self.brain / 'A.md').write_text(
            'sources:\n'
            '  - "https://doi.org/10.1016/0010-0285(80)90005-5 (A title)"\n'
            '  - "https://doi.org/10.1016/0010-0285(82)90006-8 (Another)"\n'
            '  - "https://doi.org/10.1016/S0010-0277(85)80010-3 (Typo)"\n'
            '  - "https://doi.org/10.1142/10269 (Unrelated)"\n',
            encoding='utf-8')
        (self.brain / 'B.md').write_text(
            'sources:\n'
            '  - "https://doi.org/10.1016/0010-0285(83)90101-1 (Third)"\n',
            encoding='utf-8')
        self.rows = {
            'A.md::doi:10.1016/0010-0285(80)90005-5': {'verdict': 'match'},
            'A.md::doi:10.1016/0010-0285(82)90006-8': {'verdict': 'match'},
            # debris from the corruption: absent from the file
            'A.md::doi:10.1016/0010-0285(74)90009-7(80)90005-5':
                {'verdict': 'unresolvable'},
            'A.md::doi:10.1016/0010-0285(74)90009-7(82)90006-8':
                {'verdict': 'unresolvable'},
            # live rows that must survive: one is a single-character typo,
            # one is the untitled finance DOI
            'A.md::doi:10.1016/S0010-0277(85)80010-3':
                {'verdict': 'unresolvable'},
            'A.md::doi:10.1142/10269': {'verdict': 'untitled_citation'},
            'B.md::doi:10.1016/0010-0285(83)90101-1': {'verdict': 'match'},
        }
        self.write_table()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_table(self):
        self.table.write_text(json.dumps(self.rows, indent=1,
                                         sort_keys=True), encoding='utf-8')

    def run_prune(self, apply=True):
        mod = load(self.brain, self.table)
        old = sys_argv()
        sys_set_argv(['prune', '--apply'] if apply else ['prune'])
        try:
            mod.main()
        finally:
            sys_set_argv(old)
        return json.load(open(self.table, encoding='utf-8'))

    # -- the ghosts go ------------------------------------------------
    def test_a_spliced_identifier_is_dropped(self):
        out = self.run_prune()
        self.assertNotIn(
            'A.md::doi:10.1016/0010-0285(74)90009-7(80)90005-5', out)
        self.assertNotIn(
            'A.md::doi:10.1016/0010-0285(74)90009-7(82)90006-8', out)

    def test_both_ghosts_go_together(self):
        out = self.run_prune()
        gone = [k for k in self.rows
                if '(74)90009-7(' in k and k not in out]
        self.assertEqual(len(gone), 2, 'expected both ghosts dropped')

    # -- the live rows stay -------------------------------------------
    def test_a_real_citation_is_never_dropped(self):
        out = self.run_prune()
        self.assertIn('A.md::doi:10.1016/0010-0285(80)90005-5', out)
        self.assertIn('A.md::doi:10.1016/0010-0285(82)90006-8', out)
        self.assertIn('B.md::doi:10.1016/0010-0285(83)90101-1', out)

    def test_a_single_character_typo_is_kept(self):
        """10.1016/S0010-0277(85)80010-3 against a disk value of ...-X.

        Two earlier rules deleted this row. A wrong final character is
        the most common citation defect there is, and removing it would
        discard exactly the evidence the work exists to produce.
        """
        out = self.run_prune()
        self.assertIn('A.md::doi:10.1016/S0010-0277(85)80010-3', out,
                      'a typo row was deleted as debris')

    def test_the_untitled_row_is_kept(self):
        out = self.run_prune()
        self.assertIn('A.md::doi:10.1142/10269', out,
                      'the one untitled row was deleted')

    def test_no_match_row_is_ever_dropped(self):
        """A `match` is positive evidence. Losing one silently shrinks
        the evidence base, and the first version of the pruner was
        prepared to delete 19 rows of exactly that."""
        out = self.run_prune()
        matches = {k for k, v in self.rows.items()
                   if v.get('verdict') == 'match'}
        for k in matches:
            self.assertIn(k, out, 'a match row was dropped: %s' % k)
            self.assertEqual(out[k].get('verdict'), 'match')

    def test_only_the_ghosts_are_dropped(self):
        out = self.run_prune()
        gone = set(self.rows) - set(out)
        self.assertEqual(len(gone), 2,
                         'dropped %d rows, expected 2: %s'
                         % (len(gone), sorted(gone)))

    def test_every_key_is_an_evidence_row(self):
        """No metadata key may live in the table.

        A first version recorded the prune as table['_pruned'], which
        made len(table) one greater than the row count and broke a test
        that counts rows. The gate survives it -- it looks rows up by
        path::identifier and never iterates -- but a consumer that does
        iterate would meet a dict with no 'verdict' and conclude it is
        a malformed citation. A consumer should not have to know that
        one key in this file is bookkeeping.
        """
        out = self.run_prune()
        for k, v in out.items():
            self.assertNotIn(k, ('_pruned', '_meta', '_note'),
                             'metadata key left in the table: %s' % k)
            self.assertIsInstance(v, dict)
            self.assertIn('verdict', v,
                          'table key %r is not an evidence row' % k)

    def test_the_prune_record_lives_beside_the_table(self):
        self.run_prune()
        notes = list(self.tmp.glob('t2-pruned.*.json'))
        self.assertTrue(notes, 'no prune record written beside the table')
        rec = json.loads(notes[0].read_text())
        self.assertEqual(len(rec['dropped']), 2)
        for k in rec['dropped']:
            self.assertIn('0010-0285(74)90009-7(', k)

    def test_the_row_count_is_exact(self):
        out = self.run_prune()
        self.assertEqual(len(out), len(self.rows) - 2)

    def test_it_is_dry_run_by_default(self):
        """Without --apply the table must be byte-identical."""
        before = self.table.read_text()
        self.run_prune(apply=False)
        self.assertEqual(self.table.read_text(), before,
                         'a dry run modified the table')

    def test_a_backup_is_written(self):
        self.run_prune()
        baks = list(self.tmp.glob('t2-verification.*.bak.json'))
        self.assertTrue(baks, 'no backup written')
        self.assertIn('0010-0285(80)90005-5', baks[0].read_text())


def sys_argv():
    import sys
    return list(sys.argv)


def sys_set_argv(v):
    import sys
    sys.argv = v


if __name__ == '__main__':
    unittest.main()
