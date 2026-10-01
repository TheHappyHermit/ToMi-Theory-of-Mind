"""Regression test: the DOI regex must not truncate a Wiley SICI identifier.

Found while resolving the last 15 T2 rows. The vault was CORRECT -- both the
frontmatter and the reference entry carried the full identifier

    10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5

but the evidence table recorded only

    10.1002/(SICI)1099-0720(199812)12:6

and reported it as an unresolvable citation. The vault was not at fault; the
verifier was.

Cause: verify_t2_titles.py's DOI and URL patterns excluded '<' and '>' from
the identifier, which is right for HTML (to avoid swallowing '<'a href=...>')
and wrong for Wiley's SICI DOIs, whose AID suffix is delimited by exactly
those characters. The regex stopped at the '<', producing a half-DOI that
cannot resolve in any registry -- a guaranteed 404 that looks exactly like a
fabricated citation.

This test pins the behaviour so the character class cannot silently lose the
suffix again. Run: python3 -m unittest tests.test_t2_sici_doi
"""
import importlib.util
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "verify_t2_titles.py"

SICI = "10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5"


def _load():
    spec = importlib.util.spec_from_file_location("verify_t2_titles", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSiciDoiSurvivesExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_bare_doi_pattern_keeps_sici_suffix(self):
        got = self.mod.DOI.search("doi:" + SICI)
        self.assertIsNotNone(got, "DOI pattern failed on a valid SICI identifier")
        self.assertEqual(got.group("id"), SICI)

    def test_url_pattern_keeps_sici_suffix(self):
        got = self.mod.URL.search("https://doi.org/" + SICI)
        self.assertIsNotNone(got, "URL pattern failed on a valid SICI identifier")
        self.assertEqual(got.group("id"), SICI)

    def test_extracted_identifier_is_not_the_truncated_form(self):
        """The exact failure: the old pattern yielded a half-DOI that 404s."""
        for pat, probe in ((self.mod.DOI, "doi:" + SICI),
                           (self.mod.URL, "https://doi.org/" + SICI)):
            with self.subTest(pattern=pat.pattern):
                m = pat.search(probe)
                self.assertIsNotNone(m)
                self.assertNotEqual(
                    m.group("id"),
                    "10.1002/(SICI)1099-0720(1998120)12:6",
                    "identifier truncated before the SICI AID suffix",
                )
                self.assertIn("AID-ACP542", m.group("id"))
                self.assertTrue(m.group("id").endswith("3.0.CO;2-5"),
                                "SICI ';<digits>-<digits>' tail was dropped")

    def test_ordinary_dois_are_unaffected(self):
        # The DOI pattern requires a 'doi:' or 'doi/' prefix, so a bare
        # https:// URL must be probed with the URL pattern. Feeding a URL to
        # DOI.search() correctly matches nothing -- that is a test bug, not a
        # regex bug, and asserting otherwise would invert the contract.
        for doi in ("10.1037/0278-7393.20.5.1063",
                    "10.1038/35066572",
                    "10.1016/S0079-7421(08)60536-8"):
            with self.subTest(doi=doi):
                self.assertEqual(self.mod.DOI.search("doi:" + doi).group("id"), doi)
                self.assertEqual(
                    self.mod.URL.search("https://doi.org/" + doi).group("id"), doi)

    def test_still_does_not_swallow_html(self):
        """The '<' exclusion existed to avoid eating markup; keep that."""
        line = '<a href="https://doi.org/10.1037/0033-295X.112.4.842">link</a>'
        m = self.mod.URL.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group("id"), "10.1037/0033-295X.112.4.842")
        self.assertNotIn("<a", m.group("id"))


if __name__ == "__main__":
    unittest.main()
