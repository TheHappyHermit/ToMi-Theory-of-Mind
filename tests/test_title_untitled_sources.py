"""Regressions for the untitled-source titling pass.

Every case here was a real defect found while titling the 461 bare-URL
sources. They are written as unit tests against the real transform
rather than as a walkthrough, because the failures were SILENT: each
one produced a file that yaml.safe_load either accepted wrongly or
rejected in a way that looked unrelated to the line being edited.

The shared theme: writing a correct title into a source entry is easy,
and writing one that still parses as the same kind of thing it was is
not. A check that only asks "is a title present" passes all of these.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

import yaml

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts',
                      'title_untitled_sources.py')
spec = importlib.util.spec_from_file_location('titler', SCRIPT)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def sources_of(text):
    meta = yaml.safe_load(text[3:text.find('\n---', 3)]) or {}
    return meta.get('sources')


def run(lines, rows):
    """Apply the transform to a minimal frontmatter document."""
    body = 'x' * 200
    text = ('---\nid: "t"\ndescription: "d"\nsources:\n'
            + '\n'.join(lines) + '\nconfidence: medium\n---\n\n' + body)
    new, decisions, edits = T.transform('t.md', rows, text)
    return new, decisions, edits


class TestTitlePlacement(unittest.TestCase):

    def test_plain_url_gets_title(self):
        new, dec, edits = run(
            ['  - "https://doi.org/10.1037/0003-066X.59.1.7"'],
            [('doi:10.1037/0003-066X.59.1.7', 'On Interpreting Stereotype '
              'Threat as a Mediator', 0.0)])
        self.assertEqual(edits, 1)
        src = sources_of(new)
        self.assertIsInstance(src[0], str)
        self.assertIn('On Interpreting', src[0])

    def test_bare_arxiv_id_gets_title(self):
        new, _d, edits = run(
            ['  - arxiv:2406.06484'],
            [('arxiv:2406.06484', 'Some Paper Title Here', 0.0)])
        self.assertEqual(edits, 1)
        self.assertIn('Some Paper Title Here', sources_of(new)[0])


class TestYamlSafety(unittest.TestCase):
    """Each of these produced a document that parsed wrongly."""

    def test_colon_in_title_on_unquoted_entry_is_quoted(self):
        # An unquoted entry whose title contains ": " is read by YAML
        # as a MAPPING. safe_load does not raise, so the entry silently
        # becomes a dict and the source reads as untitled forever.
        new, _d, _e = run(
            ['  - arxiv:2608.22974'],
            [('arxiv:2608.22974', 'OaK: Ontology-as-a-Kernel', 0.0)])
        self.assertIsInstance(sources_of(new)[0], str,
                              'unquoted entry with a colon became a dict')

    def test_requotes_already_titled_unquoted_entry(self):
        # Already has a title, but unquoted with a colon -- the same
        # dict defect, reached through the already-titled path.
        new, _d, _e = run(
            ['  - arxiv:2608.22974 (OaK: Ontology-as-a-Kernel)'],
            [('arxiv:2608.22974', 'OaK: Ontology-as-a-Kernel', 0.0)])
        self.assertIsInstance(sources_of(new)[0], str)

    def test_double_quote_in_title_does_not_break_frontmatter(self):
        # A title containing a double quote terminates a double-quoted
        # scalar early, and safe_load then rejects the WHOLE block.
        new, _d, _e = run(
            ['  - "https://doi.org/10.1037/a0027958"'],
            [('doi:10.1037/a0027958',
              '"Evolving judgments": Correction to Fischhoff', 0.0)])
        self.assertIsInstance(sources_of(new), list)

    def test_newline_in_title_does_not_split_entry(self):
        new, _d, _e = run(
            ['  - "https://journals.sagepub.com/doi/10.1177/22104968261431521"'],
            [('doi:10.1177/22104968261431521',
              'schema-minerpro: Agentic AI\n for Ontology Grounding', 0.0)])
        self.assertEqual(len(sources_of(new)), 1)

    def test_pdf_suffix_stays_inside_quotes(self):
        # Otherwise the line ends as - "url (Title)".pdf
        new, _d, _e = run(
            ['  - url:https://arxiv.org/pdf/2608.30320.pdf'],
            [('arxiv:2608.30320', 'On the Design of Qwen3.8-Next', 0.0)])
        self.assertIsInstance(sources_of(new)[0], str)
        self.assertIn('.pdf', sources_of(new)[0])

    def test_prose_acronym_gets_the_full_title(self):
        # "PACT (arXiv:2605.11039)" used to be treated as already-titled
        # on the reasoning that PACT is the paper's own name. That was
        # wrong, and the real verifier proved it: the registry title for
        # 2605.11039 is "The Granularity Mismatch in Agent Security",
        # PACT is an acronym the body prose uses, and leaving the source
        # bare kept the row at verdict=mismatch, score 0.0.
        #
        # So a short capitalised lead-in before the identifier is a
        # nickname, not a title, and the full title is appended inside
        # the existing parentheses. Note the result NESTS parentheses --
        # "PACT (arXiv:2605.11039 (The Granularity ...))" -- so the
        # inner title must not be delimited by the first ")". The entry
        # is quoted because the resolved title contains ": " and an
        # unquoted YAML scalar with a colon-space parses as a mapping.
        title = ('The Granularity Mismatch in Agent Security: '
                 'Argument-Level Provenance Solves Enforcement')
        new, dec, edits = run(
            ['  - PACT (arXiv:2605.11039)'],
            [('arxiv:2605.11039', title, 0.0)])
        self.assertEqual(edits, 1)
        self.assertNotEqual(dec[0]['action'], 'already_titled')
        # balanced quotes around the WHOLE entry, and a string scalar
        # (not a dict, which is what an unquoted ": " produces)
        src = sources_of(new)
        self.assertIsInstance(src[0], str)
        self.assertIn('PACT', src[0])
        self.assertIn(title, src[0])
        # the transform must actually have changed the line
        self.assertIn('The Granularity Mismatch', new)


class TestNoDoubleTitling(unittest.TestCase):

    def test_does_not_append_second_title_to_titled_entry(self):
        new, dec, _e = run(
            ['  - https://doi.org/10.1/a (Existing Title Here)'],
            [('doi:10.1/a', 'Resolved Title From Crossref', 0.0)])
        # The entry is UNQUOTED with a colon, so the correct action is
        # "requoted" -- it gets quotes so it parses as a string, but no
        # second title is appended. What matters is that the existing
        # title survives and the new one is not added.
        self.assertIn(dec[0]['action'], ('already_titled', 'requoted'))
        self.assertIn('Existing Title Here', sources_of(new)[0])
        self.assertNotIn('Resolved Title', sources_of(new)[0])

    def test_does_not_double_title_inline_array_entry(self):
        text = ('---\nid: "t"\nsources: ["arXiv:2509.20021 '
                '(Embodied AI Survey)"]\n---\n' + 'x' * 100)
        new, dec, _e = T.transform('t.md', [
            ('arxiv:2509.20021', 'Embodied AI: From LLMs to World Models',
             0.0)], text)
        self.assertEqual(dec[0]['action'], 'already_titled')
        self.assertNotIn('From LLMs to World Models', new)


class TestEditScope(unittest.TestCase):

    def test_body_prose_is_not_edited(self):
        # The body repeats a source line verbatim. A whole-file replace
        # hits whichever comes first, which is how a YAML block came to
        # be broken by an edit made to the body.
        line = '  - arxiv:2505.10468'
        title = 'AI Agents vs. Agentic AI: A Conceptual Taxonomy'
        body = ('\nReferences\n\n' + line + ' - ' + title +
                ' is discussed at length here.\n')
        text = ('---\nid: "t"\nsources:\n' + line +
                '\nconfidence: medium\n---\n' + body)
        new, _d, _e = T.transform('t.md',
                                  [('arxiv:2505.10468', title, 0.0)], text)
        head = new[:new.find('\n---', 3)]
        self.assertIn(title, head, 'frontmatter should get the title')
        self.assertIn('is discussed at length here', new)


class TestCleanTitle(unittest.TestCase):

    def test_strips_publisher_markup_and_rejoins_name(self):
        # Verbatim Crossref title for doi:10.1177/22104968261431521.
        # The closing tag, the newline and the indentation all fall
        # inside the paper's own name.
        raw = ('<scp>schema-miner</scp>\n'
               '                    pro: Agentic AI for Ontology Grounding')
        got = T.clean_title(raw)
        self.assertNotIn('<', got)
        self.assertNotIn('\n', got)
        self.assertIn('schema-minerpro', got)


if __name__ == '__main__':
    unittest.main()
