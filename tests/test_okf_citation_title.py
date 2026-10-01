"""Tests for the citation-title check in okf_lint.

The T2 verifier resolves an identifier, fetches the real document, and
compares its real title against the title written in the source entry. An
entry with an identifier and no title gives it nothing to compare, so the
row is recorded `untitled_citation` and the page is capped at medium
permanently.

The schema used to list `title` as OPTIONAL in a source entry, so a writer
could comply perfectly and still produce a file that could not pass. That
allowed 1,605 of 2,661 identifier-bearing entries corpus-wide to be
untitled. The schema and the verifier disagreed, and the schema was wrong.

Reported, never auto-fixed: a title has to come from the source document,
and inventing one is M2_identifier_mismatch, which caps at low.
"""
import importlib.util
import os
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(os.path.dirname(_HERE), "scripts", "okf_lint.py")
spec = importlib.util.spec_from_file_location("okf_lint", _MOD)
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

FM = """---
okf_version: "0.2"
id: {id}
type: research-report
status: stable
description: "A test page"
generated:
  by: "test"
  at: "2026-09-30T00:00:00Z"
tags: [test]
sources:
{sources}
confidence: medium
---

# Body

Some prose so the page is not a bare index.
"""


def page(sources, pid="test-page"):
    body = "\n".join("  - " + s if not s.startswith("  ") else s
                     for s in sources)
    return FM.format(id=pid, sources=body)


def findings_for(text, code: str | None = "citation_title_missing"):
    """Findings of `code`. Pass code=None to get every finding."""
    S = L.load_schema()
    excluded = set(S.get("excluded_dirs") or [])
    by_base, by_rel, by_base_lc = L.build_index(excluded)
    ctx = L.Ctx(S, False, by_base, by_rel, by_base_lc)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(text)
        path = fh.name
    rel = os.path.basename(path)
    try:
        L.check_file(path, rel, ctx)
        if code is None:
            return list(ctx.findings)
        return [f for f in ctx.findings if f["class"] == code]
    finally:
        os.unlink(path)


def codes_for(text):
    """Every finding code, for asserting a specific code is or isn't present."""
    return {f["class"] for f in findings_for(text, code=None)}


class TestTitledCitationsPass(unittest.TestCase):
    """Each of these must NOT produce a finding."""

    def test_bare_string_with_parenthetical_title(self):
        self.assertEqual(
            findings_for(page(['arXiv:2509.20021 (Embodied AI Survey)'])), [])

    def test_arxiv_url_with_title(self):
        self.assertEqual(
            findings_for(page(['https://arxiv.org/abs/2607.18704 (What the Waveform Knows)'])), [])

    def test_arxiv_pdf_url_with_title(self):
        self.assertEqual(
            findings_for(page(['https://arxiv.org/pdf/2607.01977v1 (Some Long Title Here)'])), [])

    def test_doi_url_with_title(self):
        self.assertEqual(
            findings_for(page(['https://doi.org/10.1109/PROC.1975.9939 (The protection of information in computer systems)'])), [])

    def test_dict_entry_with_title(self):
        src = ("  - resource: doi:10.1038/s41534-025-01078-x\n"
               "    title: Entanglement-induced provable and robust quantum learning advantages")
        self.assertEqual(findings_for(page([src])), [])


class TestUntitledCitationsFail(unittest.TestCase):
    """Each of these MUST produce exactly one finding."""

    def _one(self, sources):
        got = findings_for(page(sources))
        self.assertEqual(len(got), 1, f"expected 1 finding, got {got}")
        return got[0]

    def test_bare_arxiv_url_no_title(self):
        self._one(['https://arxiv.org/abs/2607.18704'])

    def test_bare_arxiv_prefix_no_title(self):
        self._one(['arxiv:2607.18704'])

    def test_doi_url_no_title(self):
        self._one(['https://doi.org/10.1109/PROC.1975.9939'])

    def test_doi_prefix_no_title(self):
        self._one(['doi:10.1371/journal.pone.0110274'])

    def test_dict_entry_missing_title(self):
        self._one(["  - resource: doi:10.1038/s41534-025-01078-x"])

    def test_parenthetical_too_short_is_not_a_title(self):
        """(v1) or (2024) must not count as a title."""
        self._one(['https://arxiv.org/pdf/2607.01977v1 (v1)'])

    def test_finding_is_report_only(self):
        """A missing title must block the write. It cannot be auto-fixed,
        because the title has to be fetched from the source."""
        f = self._one(['https://arxiv.org/abs/2607.18704'])
        self.assertFalse(f["auto_fixable"])


class TestNonCitationsAreNotFlagged(unittest.TestCase):
    """A source with no resolvable identifier is a pointer, not a
    citation, and needs no title. Flagging these would be pure noise."""

    def test_github_url(self):
        self.assertEqual(findings_for(page(['https://github.com/foo/bar'])), [])

    def test_session_provenance(self):
        self.assertEqual(findings_for(page(['session:abc-123'])), [])

    def test_nas_path(self):
        self.assertEqual(findings_for(page(['nas://media/movies'])), [])

    def test_plain_prose_source(self):
        self.assertEqual(findings_for(page(['see the paper'])), [])

    def test_empty_sources(self):
        self.assertEqual(findings_for(page([])), [])


class TestIdentifierDetection(unittest.TestCase):
    """The arXiv alternation must include the URL forms. 'arxiv.org/abs/'
    has '.org/' between 'arxiv' and the slash, so `arxiv[:/]` alone misses
    every real arXiv URL -- the same shape of bug as in grade_all."""

    def test_all_arxiv_forms_detected(self):
        for s in ("arxiv:2607.18704", "arxiv/2607.18704",
                  "https://arxiv.org/abs/2607.18704",
                  "https://arxiv.org/pdf/2607.18704",
                  "https://arxiv.org/html/2607.18704"):
            with self.subTest(s=s):
                self.assertTrue(L.IDENTIFIER_RE.search(s))

    def test_all_doi_forms_detected(self):
        for s in ("doi:10.1109/PROC.1975.9939",
                  "https://doi.org/10.1109/PROC.1975.9939",
                  "https://dx.doi.org/10.1109/PROC.1975.9939"):
            with self.subTest(s=s):
                self.assertTrue(L.IDENTIFIER_RE.search(s))

    def test_non_identifiers_rejected(self):
        for s in ("https://github.com/foo/bar", "session:abc", "nas://x",
                  "https://example.com/page"):
            with self.subTest(s=s):
                self.assertFalse(L.IDENTIFIER_RE.search(s))


    def test_prose_reference_is_unresolvable(self):
        """'see the paper' has no identifier and no title.

        The documentation promises this fails the gate. The first version of
        the check only inspected entries carrying an identifier, so a prose
        reference slipped through -- the doc and the code disagreed, and the
        doc was the one a writer would read. Found by a negative control
        against the real gate, not by the unit tests.
        """
        txt = page(['doi:10.1038/s41586-021-03819-2 (Taming transformers)',
                    'see the paper'])
        self.assertIn("source_unresolvable", codes_for(txt))

    def test_provenance_entry_is_exempt(self):
        """A session marker records where a page came from. It is not a citation.

        52 of the 53 source entries in the active wiki are session
        provenance, and this check blocked every page carrying one -- four of
        the twelve entity pages, including hermes-brain and
        honcho-memory-stack. Demanding a title of a pointer to a session is
        the same category error as demanding a DOI of one.
        """
        for entry in ("session:20260924_162607_55ce9ddd",
                      "session:telegram:2026-09-28",
                      "user-provided",
                      "researcher:package-id",
                      "research:local-research-dispatch",
                      "oracle:vault-page-id",
                      "inherited:from-concepts",
                      "local:stack"):
            with self.subTest(entry=entry):
                self.assertNotIn("source_unresolvable", codes_for(page([entry])))

    def test_prose_starting_with_a_provenance_word_is_not_exempt(self):
        """The colon is what makes the exemption safe.

        A bare prefix test also matched "research paper on memory" and
        "local notes on the build" -- hand-waves that should fail. Only the
        namespaced form carries the separator.

        No parentheticals here on purpose. "research paper on memory (Title
        Here)" is legitimately ACCEPTED, because it does carry a title and
        the title branch runs before the prose branch. Asserting it fails
        would be asserting a bug.
        """
        for entry in ("research paper on memory",
                      "local notes on the build",
                      "session notes were good",
                      "oracle of the system",
                      "inherited from the old page"):
            with self.subTest(entry=entry):
                self.assertIn("source_unresolvable", codes_for(page([entry])))

    def test_prose_carrying_a_parenthetical_title_is_accepted(self):
        """The reason the case above is not flagged.

        Documented because it looks like a miss and is not: the title branch
        runs first, so a hand-wave carrying a real title in parentheses is
        treated as a titled citation.
        """
        txt = page(["research paper on memory (Title Here)"])
        self.assertNotIn("source_unresolvable", codes_for(txt))

    def test_titled_mapping_form_passes(self):
        # page() builds a FLAT list, so a mapping entry is written out by hand.
        # An earlier attempt passed the mapping through page(), which stripped
        # the continuation line and produced YAML that never parsed.
        txt = FM.format(id="map-titled", sources=(
            '  - resource: "doi:10.1038/s41586-021-03819-2"\n'
            '    title: "Taming transformers for high-accuracy '
            'long-text summarization"\n'))
        self.assertNotIn("citation_title_missing", codes_for(txt))

    def test_mapping_form_without_title_fails(self):
        txt = FM.format(id="map-untitled", sources=(
            '  - resource: "doi:10.1038/s41586-021-03819-2"\n'
            '    author: "Somebody"\n'))
        self.assertIn("citation_title_missing", codes_for(txt))


if __name__ == "__main__":
    unittest.main()
