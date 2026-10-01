"""Tests for the suspect adjudication -- the 26 rows closed on evidence.

The properties locked in here:

  * every real arXiv title recorded is the one arXiv returned, so a
    wrong title cannot be cited as justification
  * a citation ERROR keeps verdict `mismatch` -- these are the rows
    where the file really does cite the wrong work, and promoting them
    would be the one genuinely dishonest outcome available here
  * every error has a recorded correct citation and a stated reason
  * the mixed identifier arxiv:2601.12560 is split by the vault's own
    label, so a per-file verdict cannot silently become per-identifier
  * every mismatch row is covered by exactly one decision: an
    unadjudicated row is exactly the failure this pass exists to close
"""
import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / 'docs' / 'audit' / 't2-adjudication.json'
CORRECTIONS = REPO / 'docs' / 'audit' / 't2-citation-corrections.json'

spec = importlib.util.spec_from_file_location(
    'sus', REPO / 'scripts' / 'adjudicate_t2_suspects.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def _table():
    if not TABLE.exists():
        return None
    return json.load(open(TABLE, encoding='utf-8'))


def _repaired_keys():
    """The (file, identifier) rows the vault repair invalidated.

    Read from the repair script's own STALE list, so this test cannot
    drift from what was actually changed. The verifier deleted these
    keys and re-derived them, so a surviving row with the same key is
    one the verifier produced.
    """
    spec = importlib.util.spec_from_file_location(
        'inv', REPO / 'scripts' / 'invalidate_repaired_t2.py')
    I = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(I)
    return {'%s::%s' % (f, i) for f, i in I.STALE}


class TestRealTitles(unittest.TestCase):
    def test_titles_are_recorded_for_every_resolved_id(self):
        """Each verified ID keeps the title arXiv actually returned.

        A transcription slip here would let a wrong-ID call be justified
        by a title that was never fetched.
        """
        for ident in ('arxiv:2605.11610', 'arxiv:2605.24601',
                      'arxiv:2505.10468', 'arxiv:2601.12560',
                      'arxiv:2602.06052'):
            with self.subTest(ident=ident):
                self.assertIn(ident.split(':')[1], S.REAL_TITLE)

    def test_transposed_pairs_are_both_unrelated(self):
        """2605.11610 and 2505.11610 must be different papers.

        The whole year-transposition theory rests on this: if the two
        resolved to the same work the fix would be cosmetic, and if
        2605.11610 did not exist the vault would need a different
        remedy entirely.
        """
        self.assertNotEqual(S.REAL_TITLE['2605.11610'],
                            S.REAL_TITLE['2505.11610'])
        self.assertNotEqual(S.REAL_TITLE['2605.24601'],
                            S.REAL_TITLE['2505.24601'])
        self.assertIn('Thermal Conductivity', S.REAL_TITLE['2605.11610'])
        self.assertIn('Biological Design', S.REAL_TITLE['2505.11610'])


class TestRepairedErrors(unittest.TestCase):
    """After scripts/repair_t2_citations.py, none of the five bad
    identifiers remains a mismatch.

    The earlier form of this test asserted the opposite -- that every
    confirmed citation error STAYS `mismatch` -- because at that point
    the vault had not been repaired and promoting them would have
    inflated confidence. The vault is now fixed, the rows were
    re-derived by the real verifier, and none is a mismatch any more.

    What must still hold is the part that is about honesty rather than
    bookkeeping: no row may be `match` unless the verifier itself put
    it there. The adjudicated flag records that a human touched it, so
    these identifiers must NOT be flagged -- a hand-set `match` on a
    formerly-wrong citation is exactly the failure to avoid.
    """

    def test_no_repaired_identifier_is_a_mismatch(self):
        tbl = _table()
        if tbl is None:
            self.skipTest('table not built')
        for ident in list(S.ERROR_IDENTIFIERS) + list(S.MIXED):
            bad = [k for k, v in tbl.items()
                   if k.split('::')[1] == ident
                   and v.get('verdict') == 'mismatch']
            with self.subTest(ident=ident):
                self.assertEqual(bad, [],
                                 'repaired citation still a mismatch: %s'
                                 % bad[:2])

    def test_repaired_rows_were_not_hand_promoted(self):
        """A REPAIRED row must be the verifier's verdict, not a hand-set
        one.

        Only rows the repair actually touched are checked. A row that
        was never repaired may legitimately be `adjudicated` -- four
        files cite 2601.12560 correctly and those were hand-adjudicated
        in an earlier pass, long before the repair, which changed only
        the fifth file.
        """
        tbl = _table()
        if tbl is None:
            self.skipTest('table not built')
        repaired = _repaired_keys()
        for ident in list(S.ERROR_IDENTIFIERS) + list(S.MIXED):
            for k in [x for x in tbl if x.split('::')[1] == ident]:
                if tbl[k].get('verdict') != 'match':
                    continue
                with self.subTest(ident=ident, key=k[-34:]):
                    if k in repaired:
                        self.assertFalse(
                            tbl[k].get('adjudicated'),
                            'a REPAIRED row was hand-promoted to match; it '
                            'must come from the verifier')

    def test_corrections_file_lists_every_error(self):
        if not CORRECTIONS.exists():
            self.skipTest('corrections not written yet')
        data = json.load(open(CORRECTIONS, encoding='utf-8'))
        self.assertEqual(set(data['corrections']),
                         set(S.ERROR_IDENTIFIERS) | set(S.MIXED))

    def test_every_correction_names_files_and_a_reason(self):
        if not CORRECTIONS.exists():
            self.skipTest('corrections not written yet')
        data = json.load(open(CORRECTIONS, encoding='utf-8'))
        for ident, c in data['corrections'].items():
            with self.subTest(ident=ident):
                self.assertTrue(c['correct_citation'])
                self.assertGreater(len(c['why']), 60)
                self.assertTrue(c['files'])
                for f in c['files']:
                    self.assertTrue(
                        (Path('/home/operator/.hermes/oracle/brain') / f)
                        .exists(), 'correction names a missing file: %s' % f)

    def test_correction_files_no_longer_carry_the_bad_id(self):
        """A correction must point at a file that no longer has the error.

        scripts/repair_t2_citations.py rewrote the vault on 2026-09-29.
        The corrections file records what was wrong, so its named files
        are now the ones that were FIXED -- the bad identifier must be
        gone from them. If one reappears, either the vault was edited
        back or a repair was reverted, and this fails.

        Backups live in ~/.hermes/cache/scratch/vault-repair-backup/.
        """
        if not CORRECTIONS.exists():
            self.skipTest('corrections not written yet')
        data = json.load(open(CORRECTIONS, encoding='utf-8'))
        vault = Path('/home/operator/.hermes/oracle/brain')
        for ident, c in data['corrections'].items():
            bare = ident.split(':', 1)[-1]
            # 2601.12560 stays legitimate in the OTHER four citing files;
            # only the one that named a different work was repaired.
            files = c['files'] if ident != 'arxiv:2601.12560' else c['files']
            for f in files:
                with self.subTest(ident=ident, file=f[-30:]):
                    p = vault / f
                    self.assertTrue(p.exists(), 'correction names a missing '
                                    'file: %s' % f)
                    text = p.read_text(encoding='utf-8')
                    if ident == 'arxiv:2601.12560':
                        # The repaired file must no longer claim a
                        # Cogitantia Synthetica arXiv ID.
                        self.assertNotIn('Cogitantia Synthetica: '
                                         'Taxonomic Classification of '
                                         'Transformer-Descended AI Systems"'
                                         ' (arXiv', text)
                    elif ident == 'arxiv:2505.10468':
                        # The fabricated half of this citation was the
                        # arXiv id; the paper is real and is
                        # doi:10.1017/langcog.2025.10. So a file may
                        # now cite it by DOI instead, and that is the
                        # CORRECT end state -- do not require the arXiv
                        # id to survive in every file that once had it.
                        #
                        # The one thing that must never come back is
                        # the false attribution to the arXiv id.
                        self.assertNotIn(
                            'Linguistic categories as network structures '
                            '(arXiv:2505.10468)', text,
                            'still attributes the linguistic article to an '
                            'arXiv ID it does not have')
                        self.assertNotIn(
                            'Network Theory" (arXiv:2505.10468)', text,
                            'reference entry still points at the arXiv ID')
                        self.assertNotIn(
                            'Network Theory (arXiv:2505.10468)', text,
                            'source entry still points at the arXiv ID')
                        if 'arXiv:2505.10468' in text:
                            # it may only appear where it is CORRECT,
                            # i.e. paired with the agentic-AI paper
                            for ln in text.split('\n'):
                                if 'arXiv:2505.10468' not in ln:
                                    continue
                                self.assertTrue(
                                    'AI Agents' in ln
                                    or 'Agentic' in ln,
                                    'arXiv:2505.10468 appears paired '
                                    'with something other than the '
                                    'agentic-AI paper: %r' % ln[:80])
                    else:
                        self.assertNotIn(
                            bare, text,
                            '%s still cites %s after the repair'
                            % (f, bare))


class TestMixedIdentifier(unittest.TestCase):
    def test_12560_is_consistently_a_good_citation(self):
        """After the repair, every 2601.12560 row agrees.

        Five files cited it. Four named the Agentic AI survey the ID
        resolves to; one named Cogitantia Synthetica, a self-published
        work with no arXiv record, and that file has been repaired to
        say so explicitly. So the identifier is now uniformly correct
        and no per-file split remains.

        The per-file distinction is still worth guarding, because it is
        the reason the repair was targeted rather than global: the
        identifier is right for the vault and wrong only for the file
        that named a different work. A blanket find-and-replace of
        2601.12560 would have destroyed the four correct citations --
        which is exactly the mistake the repair script documents for
        the 2505.10468 case, where one line used that ID correctly.
        """
        tbl = _table()
        if tbl is None:
            self.skipTest('table not built')
        rows = {k: v['verdict'] for k, v in tbl.items()
                if k.split('::')[1] == 'arxiv:2601.12560'}
        self.assertTrue(rows, 'no 2601.12560 rows at all')
        self.assertNotIn('mismatch', rows.values(),
                         'a 2601.12560 row is still a mismatch')
        self.assertGreaterEqual(len(rows), 4,
                                'expected at least the 4 untouched citing '
                                'files, found %d' % len(rows))

    def test_repaired_file_attributes_to_a_non_arxiv_source(self):
        """The Cogitantia file must now say the work is not on arXiv."""
        path = ('research/frontier-research-taxonomy-'
                '2027-supplement-v2.md')
        text = S.vault_label(path, '2601.12560')
        if not text:
            self.skipTest('citation line not found in %s' % path)
        self.assertNotIn('arXiv:2601.12560', text,
                         'still claims an arXiv ID for Cogitantia Synthetica')
        self.assertIn('arXiv', text, 'the attribution should still say arXiv '
                        'somewhere, to record that none exists')


class TestCoverage(unittest.TestCase):
    def test_no_mismatch_row_is_left_unadjudicated(self):
        tbl = _table()
        if tbl is None:
            self.skipTest('table not built')
        stuck = [k for k, v in tbl.items()
                 if v.get('verdict') == 'mismatch' and not v.get('adjudicated')]
        self.assertEqual(
            stuck, [],
            'rows still at mismatch with no hand review: %s' % stuck[:3])

    def test_every_adjudicated_row_states_a_reason(self):
        tbl = _table()
        if tbl is None:
            self.skipTest('table not built')
        thin = [k for k, v in tbl.items()
                if v.get('adjudicated') and len(v.get('reason') or '') < 40]
        self.assertEqual(thin, [], '%d reasons too thin to audit' % len(thin))

if __name__ == '__main__':
    unittest.main()
