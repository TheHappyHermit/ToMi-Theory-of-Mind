"""cited_titles() has to see every source shape the corpus uses.

It recognised two shapes and silently ignored a third:

    sources:                      sources: ["arXiv:2509.20021 (Survey)",
      - "arXiv:... (...)"                         "arXiv:2604.14228 (...)"]

Both are ordinary YAML. A file using the flow-sequence form returned
ZERO labels from its own sources list, so every identifier in it was
recorded untitled -- indistinguishable, in the verdict table, from a
file that genuinely had no titles. That is the failure mode this whole
exercise is about: a correct citation recorded as a defect.

Three bugs were stacked in the first attempt at the flow form, each
found by testing the shape rather than reasoning about it:

  1. the bracket counter started at 0, so a wrapped array's closing
     bracket drove it to 0 one line early and every element after the
     first was dropped;
  2. the single-quoted elements were re-wrapped in quotes before being
     compared against the double-quoted set, so the dedup test could
     never match;
  3. the line-join helper matched on string IDENTITY while
     `scope.split(N)` builds fresh objects on every call, so it never
     matched and the join stopped at the first line.

Each of those produces a plausible-looking shorter list, not an error.
The tests below assert the full element count, because a partial list
is exactly the bug.
"""
import importlib.util
import unittest

vs = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
V = importlib.util.module_from_spec(vs)
vs.loader.exec_module(V)

ONE_LINE = ('---\ntitle: T\n'
            'sources: ["arXiv:2509.20021 (A Survey)", '
            '"arXiv:2604.14228 (Claude Code)"]\n---\n\nbody\n')
WRAPPED = ('---\ntitle: T\n'
           'sources: ["arXiv:2509.20021 (A Survey)",\n'
           '          "arXiv:2604.14228 (Claude Code)"]\n---\n\nbody\n')
BLOCK = ('---\ntitle: T\n'
         'sources:\n'
         '  - "arXiv:2509.20021 (A Survey)"\n'
         '  - "arXiv:2604.14228 (Claude Code)"\n'
         '---\n\nbody\n')
SINGLE_QUOTED = ('---\ntitle: T\n'
                 "sources: ['arXiv:2509.20021 (A Survey)',\n"
                 "          'arXiv:2604.14228 (Claude Code)']\n"
                 '---\n\nbody\n')


class TestCitedTitlesReadsEverySourceShape(unittest.TestCase):

    def ids(self, text):
        return {x for lab in V.cited_titles('/dev/null', text)
                for x in ('2509.20021', '2604.14228') if x in lab}

    def test_block_list(self):
        self.assertEqual(self.ids(BLOCK),
                         {'2509.20021', '2604.14228'})

    def test_flow_sequence_on_one_line(self):
        self.assertEqual(self.ids(ONE_LINE),
                         {'2509.20021', '2604.14228'})

    def test_flow_sequence_wrapped_across_lines(self):
        """The wrapped form dropped everything after the first element.

        Two separate causes: the depth counter started at 0, and the
        join helper compared strings by identity while split() builds
        new objects each call. Both produced a shorter list rather
        than an error, which is why this asserts the count.
        """
        labels = V.cited_titles('/dev/null', WRAPPED)
        self.assertEqual(len(labels), 2,
                         'wrapped flow sequence yielded %d labels, '
                         'expected 2: %r' % (len(labels), labels))
        self.assertEqual(self.ids(WRAPPED),
                         {'2509.20021', '2604.14228'})

    def test_flow_sequence_with_single_quotes(self):
        labels = V.cited_titles('/dev/null', SINGLE_QUOTED)
        self.assertEqual(self.ids(SINGLE_QUOTED),
                         {'2509.20021', '2604.14228'})

    def test_numbered_reference_line(self):
        """A plain "4. Title — arXiv:id" reference, title BEFORE id."""
        text = ('---\ntitle: T\n---\n\n4. Embodied AI: From LLMs to '
                'World Models — arXiv:2509.20021\n')
        labels = V.cited_titles('/dev/null', text)
        self.assertTrue(any('2509.20021' in l for l in labels),
                        'numbered reference not picked up: %r' % labels)
        self.assertEqual(
            V.inline_title('Embodied AI: From LLMs to World Models — '
                           'arXiv:2509.20021'),
            'Embodied AI: From LLMs to World Models')

    def test_bracket_index_line(self):
        text = ('---\ntitle: T\n---\n\n[12] Smith J. A real title. '
                'Journal. 2004;10:1-10.\n')
        labels = V.cited_titles('/dev/null', text)
        self.assertTrue(any('A real title' in l for l in labels),
                        'bracket index not picked up: %r' % labels)


if __name__ == '__main__':
    unittest.main()
