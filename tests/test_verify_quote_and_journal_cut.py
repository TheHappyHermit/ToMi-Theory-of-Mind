"""Regression tests for two verifier bugs found by the real run.

Both were live defects in verify_t2_titles.py that had nothing to do
with the titling work, and both silently mis-scored CORRECT citations:

  1. inline_title() did not strip the surrounding quotes of a
     frontmatter source entry. The vault writes

         - "https://doi.org/10.1037/bul0000045 (Temporal cognition: ...)"

     and cited_titles() hands that line over with the quotes still on
     it, so the leading-URL rule never fired and norm() returned empty.
     Nineteen rows were recorded untitled_citation while carrying a
     perfectly good title.

  2. _has_title_words() cut a label at the first word that appears in
     _JOURNAL_NAMES, even though that list holds ordinary words --
     "brain", "cognition", "science", "review of". "Temporal cognition:
     Connecting subjective time to perception, attention, and memory"
     was cut at "cognition", leaving "temporal", and the title was
     discarded. Nine rows were lost this way.

Both are the same failure class: a check that cannot tell a title from
a reference tail discards a real title, and the citation is never
verified at all. That is invisible, which is why it needs a test.
"""
import importlib.util
import unittest

_spec = importlib.util.spec_from_file_location(
    'v2', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

TIMECOGNITION = ('https://doi.org/10.1037/bul0000045 (Temporal cognition: '
                 'Connecting subjective time to perception, attention, '
                 'and memory)')
TIMECOGNITION_TITLE = ('Temporal cognition: Connecting subjective time to '
                       'perception, attention, and memory')


class TestInlineTitleStripsQuotes(unittest.TestCase):
    """Bug 1: the vault's quotes defeated the URL/title parser."""

    def _reads_a_title(self, entry):
        t = V.inline_title(entry)
        return bool(t) and V._has_title_words(t)

    def test_quoted_entry_yields_its_title(self):
        self.assertTrue(self._reads_a_title('"%s"' % TIMECOGNITION))
        self.assertEqual(V.inline_title('"%s"' % TIMECOGNITION),
                         TIMECOGNITION_TITLE)

    def test_single_quoted_entry_yields_its_title(self):
        self.assertTrue(self._reads_a_title("'%s'" % TIMECOGNITION))

    def test_unquoted_entry_still_works(self):
        # the fix must not change the case that already worked
        self.assertTrue(self._reads_a_title(TIMECOGNITION))

    def test_quoted_bare_arxiv_id_yields_its_title(self):
        t = V.inline_title('"arXiv:2505.17335 (EverCBOR/EverCDDL, '
                           'Microsoft Research, 2025)"')
        self.assertIn('EverCBOR', t)

    def test_quoted_title_matches_unquoted_title(self):
        quoted = V.title_match(V.inline_title('"%s"' % TIMECOGNITION),
                               TIMECOGNITION_TITLE)
        plain = V.title_match(V.inline_title(TIMECOGNITION),
                              TIMECOGNITION_TITLE)
        self.assertEqual(quoted, plain)
        self.assertTrue(quoted[0])


class TestJournalCutNeedsEvidence(unittest.TestCase):
    """Bug 2: a journal NAME is not a journal marker without a tail."""

    TITLES = [
        TIMECOGNITION_TITLE,
        'Internal brain state regulates membrane potential synchrony '
        'in barrel cortex of behaving mice',
        'The entropic brain: a theory of conscious states informed by '
        'neuroimaging research',
        'A systematic review of integrated information theory: a '
        'perspective from artificial intelligence',
        'Against the brain time theory as a general theory of temporal '
        'binding',
    ]

    RESIDUE = [
        # what is left of a reference once the title has been stripped:
        # a journal, a volume, an issue, a page range and a DOI.
        '*Vision Research* 49(10):1295 1306, '
        '10.1016/j.visres.2009.06.037',
        '*Cognitive Science*, 44(5), e128',
    ]

    def test_real_titles_survive_the_journal_cut(self):
        for t in self.TITLES:
            self.assertTrue(V._has_title_words(t),
                            'discarded a real title: %r' % t[:60])

    def test_reference_residue_is_still_rejected(self):
        # the original purpose of the cut, which the fix must preserve
        for r in self.RESIDUE:
            self.assertFalse(V._has_title_words(r),
                             'accepted a title-less residue: %r' % r[:60])

    def test_multiword_journal_name_is_not_mistaken_for_a_tail(self):
        # "vision research" is a journal; "vision research" inside a
        # title is not. The tail test must look PAST the whole name.
        self.assertFalse(V._has_title_words('*Vision Research* 49(10):1295'))

    def test_volume_issue_after_a_journal_name_is_a_tail(self):
        self.assertTrue(V._JOURNAL_TAIL_RE.search('*cognitive science*'))
        self.assertTrue(
            V._REFERENCE_TAIL_RE.match('*, 44(5), e128'))


class TestTrailingParentheticalIsASubtitle(unittest.TestCase):
    """A trailing "(...)" is a subtitle, not bare metadata.

    The corpus writes some sources with a subtitle in parentheses after
    a dash separator:

        arXiv:2501.09136 -- Agentic RAG Survey (Taxonomy of Agentic RAG)

    inline_title() only unwrapped parentheses that WRAP the whole
    string, so nothing was unwrapped, the ")" survived, and the entry
    was scored against a registry title with no trailing paren. The row
    was recorded untitled even though the title was there and correct.
    """

    def reads(self, entry):
        t = V.inline_title(entry)
        return bool(t) and V._has_title_words(t)

    def test_dash_separated_entry_with_subtitle(self):
        self.assertTrue(self.reads(
            'arXiv:2501.09136 \u2014 Agentic RAG Survey '
            '(Taxonomy of Agentic RAG)'))
        self.assertEqual(
            V.inline_title('arXiv:2501.09136 \u2014 Agentic RAG Survey '
                           '(Taxonomy of Agentic RAG)'),
            'Agentic RAG Survey')

    def test_dash_separated_entry_without_subtitle(self):
        self.assertTrue(self.reads(
            'arXiv:2602.19320 \u2014 Anatomy of Agentic Memory: '
            'Taxonomy and Empirical Analysis'))

    def test_bare_date_parenthetical_is_not_a_title(self):
        # "(2025)" is metadata, so there is no title here at all
        self.assertFalse(self.reads('arXiv:2606.05339 (2025)'))

    def test_wrapped_title_still_works(self):
        self.assertTrue(self.reads('(Fully Wrapped Title Here)'))
        self.assertEqual(V.inline_title('(Fully Wrapped Title Here)'),
                         'Fully Wrapped Title Here')

    def test_simple_paren_title_still_works(self):
        self.assertEqual(
            V.inline_title('arXiv:2505.09388 (Qwen3 Technical Report)'),
            'Qwen3 Technical Report')

    def test_quoted_entry_with_leading_bullet_and_dash(self):
        """The quote strip has to run AFTER the bullet strip.

        A frontmatter entry starts with two spaces, so s[0] is a
        space when the first quote-strip pass runs and the pass is
        skipped. The quote then survives into the candidate and the
        real title scores below threshold. Measured on the corpus:
        six rows sat in that state.
        """
        self.assertEqual(
            V.inline_title('  - "arXiv:2602.19320 — Anatomy of Agentic '
                           'Memory: Taxonomy"'),
            'Anatomy of Agentic Memory: Taxonomy')
        self.assertEqual(
            V.inline_title("  - 'arXiv:2602.19320 — Anatomy of Agentic "
                           "Memory'"),
            'Anatomy of Agentic Memory')

    def test_quoted_paren_doi_entry_with_leading_bullet(self):
        """This form returned just '"' before the second quote strip.

        The bare-URL rule requires the string to begin with 'http', so
        a leading quote meant the parenthesised title was never read
        and the residue was reported as a title.
        """
        self.assertEqual(
            V.inline_title('  - "https://doi.org/10.1126/science.1069590 '
                           '(A Pathway in Primate Brain)"'),
            'A Pathway in Primate Brain')


class TestTrailingParentheticalAsAlternativeCandidate(unittest.TestCase):
    """A trailing parenthetical is sometimes the title, not a gloss.

    inline_title() drops it, which is right far more often -- it is
    what makes "https://doi.org/10.1 (Real Title Here)" work. But in

        Anatomy of Agentic Memory: 4-Structure Taxonomy
            (Anatomy of Agentic Memory: Taxonomy and Empirical
             Analysis of Evaluation and System Limitations)

    the text before the paren is a section shorthand and the paren is
    the real title: 0.364 versus 1.000, measured. The fix offers the
    parenthetical as a second candidate rather than changing the
    default, since a real title matches exactly one reading exactly.
    """

    def test_extracts_the_trailing_parenthetical(self):
        self.assertEqual(
            V._trailing_parenthetical(
                'Anatomy of Agentic Memory: 4-Structure Taxonomy '
                '(Anatomy of Agentic Memory: Taxonomy and Empirical '
                'Analysis of Evaluation and System Limitations)'),
            'Anatomy of Agentic Memory: Taxonomy and Empirical '
            'Analysis of Evaluation and System Limitations')

    def test_extracts_it_through_the_entrys_own_quotes(self):
        """The guard was right; the input was not what it assumed.

        cited_titles() returns a frontmatter line with its quotes still
        attached, so the string ends with ')"' and never endswith(')').
        Three rows sat at 0.364 and 0.273 because of that one
        character.
        """
        self.assertEqual(
            V._trailing_parenthetical(
                '"arXiv:2602.19320 — Anatomy of Agentic Memory: '
                '4-Structure Taxonomy (Anatomy of Agentic Memory: '
                'Taxonomy and Empirical Analysis)"'),
            'Anatomy of Agentic Memory: Taxonomy and Empirical Analysis')

    def test_rejects_a_year_only_parenthetical(self):
        """A stray "(1998)" must never become a candidate title."""
        self.assertEqual(V._trailing_parenthetical('Some Title (1998)'),
                         '')

    def test_rejects_a_volume_and_page_range(self):
        self.assertEqual(
            V._trailing_parenthetical(
                'A Pathway in Primate Brain (2002, 285:1183-1185)'),
            '')

    def test_rejects_when_there_is_no_trailing_parenthetical(self):
        self.assertEqual(V._trailing_parenthetical('No Parenthetical'), '')
        self.assertEqual(V._trailing_parenthetical(''), '')
        self.assertEqual(V._trailing_parenthetical(None), '')

    def test_the_real_title_wins_over_the_shorthand(self):
        """The whole point: 1.000 from the paren, 0.364 without."""
        reg = ('Anatomy of Agentic Memory: Taxonomy and Empirical '
               'Analysis of Evaluation and System Limitations')
        shorthand = 'Anatomy of Agentic Memory: 4-Structure Taxonomy'
        inner = V._trailing_parenthetical(
            shorthand + ' (' + reg + ')')
        self.assertEqual(inner, reg)
        ok, score_inner = V.title_match(inner, reg)
        ok2, score_short = V.title_match(shorthand, reg)
        self.assertTrue(ok, 'parenthetical reading should match exactly')
        # The shorthand does NOT match -- that is the premise of this
        # whole change. Asserting otherwise would be asserting the bug.
        self.assertFalse(ok2, 'the shorthand reading unexpectedly matched; '
                              'if it now matches, the extra candidate is '
                              'unnecessary')
        self.assertGreater(score_inner, score_short,
                           'the parenthetical must be the better reading')


class TestHyphensInsideAWordAreNotSeparators(unittest.TestCase):
    """A dash between IDENTIFIER and TITLE, never inside a word.

    The separator rule used \\s* on both sides, and \\s* matches ZERO
    spaces, so it fired inside "schema-miner" at offset 6 and inside
    "LLM-Discovered" -- splitting a real title at its own hyphens and
    returning ''. Require a space on the left so only a genuine
    separator matches.
    """

    SCHEMA = ('schema-miner pro: Agentic AI for Ontology Grounding Over '
              'LLM-Discovered Scientific Schemas in a Human-in-the-Loop '
              'Workflow')

    def test_a_hyphenated_title_survives(self):
        got = V.inline_title(self.SCHEMA)
        self.assertTrue(got, 'a hyphenated real title returned nothing')
        self.assertIn('LLM-Discovered', got)
        self.assertIn('schema-miner', got)

    def test_a_dash_between_words_still_separates(self):
        self.assertEqual(
            V.inline_title('10.1038/nrn2236 - Actin-binding proteins '
                           'take the reins'),
            '10.1038/nrn2236 Actin-binding proteins take the reins')


class TestAuthorRunNeedsARealRun(unittest.TestCase):
    """Two loose "Capitalised AB" pairs are not an author list.

    "schema-miner pro: Agentic AI for Ontology Grounding Over
    LLM-Discovered ..." contains "Agentic AI" and "Over LLM". Counting
    any two matches of \\b[A-Z][a-z]+\\s+[A-Z]{1,3}\\b fired the
    author-run branch, which returned '', and a correct citation was
    recorded as untitled. An author list has the initials
    comma-separated after the surnames.
    """

    def test_two_scattered_pairs_are_not_an_author_run(self):
        got = V.inline_title(TestHyphensInsideAWordAreNotSeparators.SCHEMA)
        self.assertTrue(got, 'scattered pairs were read as an author run')

    def test_a_real_author_run_is_still_detected(self):
        got = V.inline_title(
            '5. Bengtsson SL, Nagy Z, Skare S, Forsman L. Extensive '
            'piano practicing has regionally specific effects. '
            'Nat Neurosci.')
        self.assertEqual(got,
                         'Extensive piano practicing has regionally '
                         'specific effects. Nat Neurosci')


class TestIdentifierLabelFilterUsesBareForm(unittest.TestCase):
    """The label filter must test the BARE identifier.

    The verifier keeps, for each identifier, only the labels that
    mention it:

        own = [l for l in labels if ident in l or ...]

    `ident` is the full form, "doi:10.1126/science.1241224". A label
    is a source line carrying the BARE form:

        "https://www.science.org/doi/10.1126/science.1241224 (Sleep
         Drives Metabolite Clearance from the Adult Brain)"

    The prefixed string is not a substring of that, so `own` came back
    empty and the row was recorded untitled_citation while a correct
    title sat in the file. Twenty-two rows were in that state.
    """

    LABELS = [
        '"https://www.science.org/doi/10.1126/science.1241224 (Sleep '
        'Drives Metabolite Clearance from the Adult Brain)"',
        '"https://doi.org/10.1038/nature07150 (Internal brain state '
        'regulates membrane potential synchrony)"',
    ]

    def filter_own(self, labels, ident):
        bare = ident.split(':', 1)[-1]
        return [l for l in labels
                if bare in l or bare.lower() in l.lower()]

    def test_prefixed_identifier_matches_nothing(self):
        # the defect, asserted so the fix cannot be reverted silently
        old = [l for l in self.LABELS
               if 'doi:10.1126/science.1241224' in l]
        self.assertEqual(old, [],
                         'the prefixed form unexpectedly matched; if this '
                         'now fails, the input shape changed')

    def test_bare_identifier_finds_the_label(self):
        got = self.filter_own(self.LABELS, 'doi:10.1126/science.1241224')
        self.assertEqual(len(got), 1)
        self.assertIn('Sleep Drives', got[0])

    def test_arxiv_identifier_also_uses_the_bare_form(self):
        labels = ['"arXiv:2509.20021 (Embodied AI: From LLMs to World '
                  'Models)"']
        got = self.filter_own(labels, 'arxiv:2509.20021')
        self.assertEqual(len(got), 1)

    def test_a_label_without_the_identifier_is_still_excluded(self):
        got = self.filter_own(self.LABELS, 'doi:10.9999/nothing')
        self.assertEqual(got, [])


if __name__ == '__main__':
    unittest.main()
