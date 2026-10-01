"""A transform must never claim an edit it did not make.

This is the most serious defect found in the whole titling work, and it
was silent in the worst way: the row was reported as successfully
titled, the caller moved on, and the citation stayed broken in the
vault. Nothing anywhere said a write had failed.

Two separate causes, both now fixed and both covered here:

  1. replace_in_frontmatter() returned the text untouched when it could
     not find a matching line -- no closing "---", or no exact line
     match -- and the caller went on to increment its edit counter. It
     now raises instead.

  2. source_lines() scanned the whole file, so a body reference line
     repeating a source entry was offered to the transform as if it
     were a source line. The body copy can never be edited correctly,
     and with two branches both attempting it, one of them recorded an
     edit for a substitution that never landed.

The general rule these tests encode: a check that can pass without the
work being done is not a check. Counting an edit is only meaningful if
the output actually differs.
"""
import importlib.util
import os
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts',
                      'title_untitled_sources.py')
spec = importlib.util.spec_from_file_location('titler2', SCRIPT)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

TITLE = 'AI Agents vs. Agentic AI: A Conceptual Taxonomy'


def doc(front_sources, body=''):
    return ('---\nid: "t"\ndescription: "d"\nsources:\n'
            + front_sources + '\nconfidence: medium\n---\n\n' + body)


class TestEditIsActuallyApplied(unittest.TestCase):

    def test_edit_count_matches_an_output_change(self):
        # the invariant: edits > 0 implies the text changed
        src = '  - arxiv:2505.10468'
        text = doc(src)
        new, _dec, edits = T.transform(
            't.md', [('arxiv:2505.10468', TITLE, 0.0)], text)
        self.assertEqual(edits, 1)
        self.assertNotEqual(new, text, 'edit counted but nothing changed')
        self.assertIn(TITLE, new)

    def test_missing_frontmatter_end_raises_instead_of_no_op(self):
        # no closing --- at all: previously returned the text unchanged
        broken = '---\nid: "t"\nsources:\n  - arxiv:2505.10468\n'
        with self.assertRaises(ValueError):
            T.transform('t.md', [('arxiv:2505.10468', TITLE, 0.0)],
                        broken)

    def test_no_matching_line_raises_instead_of_no_op(self):
        with self.assertRaises(ValueError):
            T.replace_in_frontmatter(doc('  - "https://doi.org/10.1/a"'),
                                     '  - "https://doi.org/10.1/NOPE"',
                                     '  - "https://doi.org/10.1/NOPE (X)"')

    def test_body_repeat_is_never_treated_as_a_source_line(self):
        # a body reference line that repeats a source entry verbatim
        src = '  - arxiv:2505.10468'
        body = ('\n## References\n\n' + src + ' - ' + TITLE +
                ' is discussed at length here.\n')
        text = doc(src, body)
        found = T.source_lines(text, ['2505.10468'])
        self.assertEqual(
            [ln for _n, ln in found], [src],
            'a body line was returned as a frontmatter source line')

    def test_repeated_body_line_cannot_cause_a_phantom_edit(self):
        src = '  - arxiv:2505.10468'
        body = ('\n## References\n\n' + src + ' - ' + TITLE +
                ' is discussed at length here.\n')
        text = doc(src, body)
        new, _dec, edits = T.transform(
            't.md', [('arxiv:2505.10468', TITLE, 0.0)], text)
        self.assertEqual(edits, 1)
        self.assertIn('is discussed at length here', new,
                      'the body copy must be left alone')
        # exactly one occurrence of the title: the frontmatter one
        self.assertEqual(new.count(TITLE), 2)  # frontmatter + body text


class TestProseFormIsTitled(unittest.TestCase):
    """The shape that no URL branch matched at all."""

    def test_nickname_paren_form_gets_the_real_title(self):
        text = doc('  - PACT (arXiv:2605.11039)')
        full = ('The Granularity Mismatch in Agent Security: '
                'Argument-Level Provenance Solves Enforcement')
        new, dec, edits = T.transform(
            't.md', [('arxiv:2605.11039', full, 0.0)], text)
        self.assertEqual(edits, 1)
        self.assertEqual(dec[0]['action'], 'titled')
        self.assertIn(full, new)
        self.assertIn('PACT', new)
        # no doubled space before the parenthesis
        self.assertNotIn('PACT  (', new)

    def test_prose_form_line_actually_changes(self):
        text = doc('  - PACT (arXiv:2605.11039)')
        new, _dec, edits = T.transform(
            't.md', [('arxiv:2605.11039', 'A Real Paper Title', 0.0)],
            text)
        self.assertEqual(edits, 1)
        self.assertNotEqual(new, text)


if __name__ == '__main__':
    unittest.main()
