"""Tests for _has_title_words: is this string a title, or a citation tail?

A label is not a title merely because it is non-empty. The single most
common false mismatch in this verifier came from a reference whose
residue after author-stripping is a journal, a volume, a page range and
a DOI -- no title at all. It passed the `if x` filter, could not match
anything, and forced verdict=mismatch for a citation that was never
wrong.
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'vt2', REPO / 'scripts' / 'verify_t2_titles.py')
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

# (residue after inline_title, does it contain a title?)
CASES = [
    # ── NOT titles: journal + volume + pages + DOI, no title words
    ('*Vision Research* 49(10):1295 1306, 10.1016/j.visres.2009.06.037',
     False),
    ('*Psychological Review* 70(1):80 90, 10.1037/h0040127', False),
    ('*Journal of Neuroscience* 40(12):2201-2212', False),
    # an article number is not a word
    ('*Cognitive Science*, 44(5), e128', False),
    # bare identifiers carry no title
    ('arxiv:2403.01590', False),
    ('10.1016/j.culcom.2024.102384', False),
    ('', False),
    # ── real titles must survive
    ('Bayesian surprise attracts human attention', True),
    ('Attention: Some theoretical considerations', True),
    ('A critical period plasticity framework for the sensorimotor axis',
     True),
    ('Distributed practice in verbal recall tasks: A review', True),
]


class TestHasTitleWords(unittest.TestCase):
    def test_all_cases(self):
        for residue, want in CASES:
            with self.subTest(residue=residue[:50]):
                self.assertEqual(V._has_title_words(residue), want)

    def test_two_word_floor(self):
        """One content word is not enough.

        "brain" and "science" both occur in real titles AND both appear
        in journal names, so a single surviving word cannot decide
        whether a string is a title. A real title keeps more than the
        one word it shares with a journal.
        """
        self.assertFalse(V._has_title_words('brain'))
        self.assertFalse(V._has_title_words('science'))
        self.assertTrue(V._has_title_words('science of learning'))

    def test_untitled_citation_is_reachable(self):
        """The whole point: a journal-only label must yield no title.

        This is the property the caller relies on to record
        untitled_citation rather than mismatch.
        """
        raw = ('*Itti & Baldi (2009)**, *Vision Research* 49(10):1295 1306, '
               '10.1016/j.visres.2009.06.037')
        cleaned = V.inline_title(raw)
        self.assertFalse(
            V._has_title_words(cleaned),
            'a journal+volume+pages+DOI residue must not count as a title')

    def test_verifier_uses_the_filter(self):
        """The candidate filter must actually call it.

        Asserting on a key this test builds itself would pass no matter
        what the verifier does, so the assertion is against the real
        source.
        """
        src = (REPO / 'scripts' / 'verify_t2_titles.py').read_text(
            encoding='utf-8')
        self.assertIn(
            'if x and _has_title_words(x)', src,
            'the candidate filter must reject non-title residues, or every '
            'journal-only citation is recorded as a wrong citation')


if __name__ == '__main__':
    unittest.main()
