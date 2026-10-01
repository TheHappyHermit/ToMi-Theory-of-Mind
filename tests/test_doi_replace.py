"""A DOI repair must not match inside a LONGER identifier.

This is not hypothetical. apply_verified_dois_13.py replaced

    10.1016/0010-0285   ->   10.1016/0010-0285(74)90009-7

with an unbounded re.sub, and the stem matched inside two complete,
valid DOIs in Attention/Feature-Integration-Theory.md:

    10.1016/0010-0285(80)90005-5   Treisman & Gelade 1980
    10.1016/0010-0285(82)90006-8   Treisman & Schmidt 1982

Both became 10.1016/0010-0285(74)90009-7(80)90005-5 and
...(82)90006-8. The vault was correct before the repair and wrong
after it, and nothing raised: the script reported the lines it wrote
and moved on.

The other half of the bug is silence. A no-op and a partial match both
look like success unless the caller says how many substitutions it
expected, so replace_doi() takes `expected` and raises on a mismatch.

The same failure shape has now appeared three times in this work: a
titler that counted edits it never made, an invalidation that deleted
nothing, and this. Each is silent and each makes the next stage
believe the work is done.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from doi_replace import replace_doi  # noqa: E402


class TestReplaceDoiIsBounded(unittest.TestCase):

    STEM = '10.1016/0010-0285'
    FULL = '10.1016/0010-0285(74)90009-7'

    def test_it_does_not_splice_a_longer_identifier(self):
        text = ('- "https://doi.org/10.1016/0010-0285(80)90005-5 '
                '(A feature-integration theory of attention)"\n')
        out, n = replace_doi(text, self.STEM, self.FULL)
        self.assertEqual(n, 0,
                         'the stem matched inside a complete DOI')
        self.assertEqual(out, text, 'a valid citation was rewritten')

    def test_it_does_replace_the_bare_stem(self):
        text = '- "https://doi.org/10.1016/0010-0285 (Some title)"\n'
        out, n = replace_doi(text, self.STEM, self.FULL)
        self.assertEqual(n, 1)
        self.assertIn(self.FULL, out)

    def test_every_longer_variant_is_left_alone(self):
        for suffix in ('(80)90005-5', '(82)90006-8', '(74)90009-7'):
            text = '  - "https://doi.org/%s%s (Title)"\n' % (self.STEM,
                                                             suffix)
            out, n = replace_doi(text, self.STEM, self.FULL)
            self.assertEqual(n, 0, 'spliced onto %s' % suffix)
            self.assertIn(suffix, out)

    def test_it_reports_the_count(self):
        text = ('- "https://doi.org/10.1016/0010-0285 (One)"\n'
                '- "https://doi.org/10.1016/0010-0285 (Two)"\n')
        out, n = replace_doi(text, self.STEM, self.FULL)
        self.assertEqual(n, 2)
        self.assertNotIn(self.STEM + ' (', out)

    def test_a_wrong_expected_count_raises(self):
        """The silence is the bug, so the count has to be enforced."""
        text = '- "https://doi.org/10.1016/0010-0285 (One)"\n'
        with self.assertRaises(SystemExit):
            replace_doi(text, self.STEM, self.FULL, expected=2)

    def test_a_doi_after_a_colon_is_still_found(self):
        text = '  doi:10.1016/0010-0285\n'
        out, n = replace_doi(text, self.STEM, self.FULL)
        self.assertEqual(n, 1, 'a bare "doi:" prefix blocked the match')
        self.assertIn(self.FULL, out)

    def test_it_does_not_match_inside_a_longer_stem(self):
        text = '  - "https://doi.org/10.1016/0010-02859 (Other)"\n'
        out, n = replace_doi(text, self.STEM, self.FULL)
        self.assertEqual(n, 0, 'matched a prefix of a longer number')


if __name__ == '__main__':
    unittest.main()
