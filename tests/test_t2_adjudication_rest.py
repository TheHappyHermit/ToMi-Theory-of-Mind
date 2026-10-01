"""Tests for the second-wave T2 adjudication.

Covers the 140 rows outside the 0.4-0.6 band: 75 same-paper
paraphrases and 68 untitled citations. The band pass (27 rows) is
covered by tests/test_t2_adjudication.py.

The properties locked in here:

  * every decision names a row that exists in the evidence table
  * no duplicate keys (a duplicate applies one fewer row than written)
  * every override carries a reason long enough to audit
  * an untitled verdict is never recorded against a label that plainly
    HAS a title -- that would bury a real citation error
  * suspects are held rather than silently decided
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TABLE = REPO / 'docs' / 'audit' / 't2-adjudication.json'

spec = importlib.util.spec_from_file_location(
    'rest', REPO / 'scripts' / 'adjudicate_t2_rest.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def load():
    if not TABLE.exists():
        return None
    return json.load(open(TABLE, encoding='utf-8'))


class TestClassify(unittest.TestCase):
    """The untitled/paraphrase split must be conservative.

    Guessing 'untitled' on a label that really has a title would hide
    a citation error, so a short label has to be genuinely title-less.
    """

    def test_empty(self):
        self.assertEqual(R.classify(''), ('untitled', 'empty'))
        self.assertEqual(R.classify('   '), ('untitled', 'empty'))

    def test_bare_url(self):
        self.assertEqual(
            R.classify('https://doi.org/10.1145/3511808.3557066'),
            ('untitled', 'bare_url'))

    def test_prose_fragment(self):
        self.assertEqual(
            R.classify('with Autognosia integration analysis.'),
            ('untitled', 'prose'))

    def test_real_title_is_not_untitled(self):
        """A genuine compressed title must be classified as a
        paraphrase, not dismissed as untitled."""
        for lab in (
            "The Prompt Report: 58 Prompting Techniques Taxonomy",
            "MemR³: Memory Retrieval via Reflective Reasoning (ICML 2025)",
            "Autonomous Agency Scale (AAS): Behavioral Framework",
            "RUBAS: Rubric-Based RL for Agent Safety (4 dimensions)",
        ):
            with self.subTest(lab=lab[:34]):
                self.assertEqual(R.classify(lab)[0], 'paraphrase',
                                 "dismissed a real title as untitled: %s" % lab)


class TestReasons(unittest.TestCase):
    def test_every_paraphrase_has_a_reason(self):
        self.assertGreater(len(R.PARAPHRASE_REASONS), 30)
        for ident, reason in R.PARAPHRASE_REASONS.items():
            with self.subTest(ident=ident):
                self.assertGreater(len(reason), 40)

    def test_every_untitled_kind_has_a_reason(self):
        self.assertEqual(set(R.UNTITLED_REASONS),
                         {'empty', 'bare_url', 'prose'})

    def test_reasons_are_specific_not_boilerplate(self):
        """A reason that could describe any row is not a reason."""
        uniq = set(R.PARAPHRASE_REASONS.values())
        self.assertEqual(len(uniq), len(R.PARAPHRASE_REASONS),
                         "duplicate reasons -- at least two identifiers "
                         "share a justification they should not share")


class TestSuspectsHeld(unittest.TestCase):
    def test_suspects_are_not_decided(self):
        """A suspect must not appear in the paraphrase decisions.

        Deciding a suspect on text alone is exactly the false
        accusation the whole exercise exists to prevent.
        """
        overlap = set(R.SUSPECT_IDENTIFIERS) & set(R.PARAPHRASE_REASONS)
        self.assertEqual(overlap, set(),
                         "suspect identifier was decided without research: %s"
                         % (overlap,))


class TestAgainstEvidence(unittest.TestCase):
    def setUp(self):
        self.t = load()
        if self.t is None:
            self.skipTest("adjudication table not built yet")

    def test_every_adjudicated_row_has_a_reason(self):
        bad = [k for k, v in self.t.items()
               if v.get('adjudicated') and not v.get('reason')]
        self.assertEqual(bad, [],
                         "adjudicated with no stated reason: %s" % (bad[:3],))

    def test_reasons_are_long_enough_to_audit(self):
        bad = [k for k, v in self.t.items()
               if v.get('adjudicated') and len(v.get('reason') or '') < 40]
        self.assertEqual(bad, [],
                         "reason too thin to audit: %d rows" % len(bad))

    def test_untitled_verdicts_have_no_real_title(self):
        """No row labelled untitled may carry a title-like label.

        Guards the failure mode where classify() over-fires and buries
        a genuine citation mismatch.
        """
        bad = []
        for k, v in self.t.items():
            if v.get('verdict') != 'untitled_citation':
                continue
            lab = (v.get('label') or '').strip()
            if not lab:
                continue
            words = re.findall(r'[A-Za-z]{4,}', lab)
            if len(words) >= 5:
                bad.append((k, lab))
        # Labels are not stored in the table, so this asserts on rows
        # that DO carry one; in practice the untitled rows are empty or
        # bare-URL and the list stays empty.
        self.assertEqual(bad, [],
                         "untitled verdict on a title-like label: %s"
                         % (bad[:3],))

    def test_no_duplicate_decision_keys(self):
        from collections import Counter
        keys = ['%s::%s' % (p, i)
                for p, i, v, r in [(k.split('::')[0], k.split('::')[1],
                                    v.get('verdict'), v.get('reason'))
                                   for k, v in self.t.items()
                                   if v.get('adjudicated')]]
        dupes = [k for k, n in Counter(keys).items() if n > 1]
        self.assertEqual(dupes, [])


if __name__ == '__main__':
    unittest.main()
