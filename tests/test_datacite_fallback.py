"""The resolver must ask DataCite as well as Crossref.

Crossref holds journal articles. DataCite is the other DOI
registration agency and holds Zenodo deposits, most institutional
repositories, and arXiv's DataCite records. Four identifiers in this
corpus live only in DataCite:

    10.5281/zenodo.19054914    crossref 404   handle 200
    10.34726/12041             crossref 404   handle 200
    10.48550/arxiv.2510.18407  crossref 404   handle 200
    10.5281/zenodo.18671158    crossref 404   handle 200

All four name real published items. Recording them `unresolvable`
asserts an identifier does not exist, which is false -- the resolver
simply never asked the right registry. That is a false accusation of
a broken citation, which is the specific thing this whole exercise
exists to prevent.

These tests use the real network. fetch_datacite() is expected to
return None -- not raise -- for anything it does not carry, so the
caller can treat a miss identically to a Crossref miss.
"""
import importlib.util
import os
import unittest

vs = importlib.util.spec_from_file_location(
    'v', os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'scripts', 'verify_t2_titles.py'))
V = importlib.util.module_from_spec(vs)
vs.loader.exec_module(V)


class TestDataciteFallback(unittest.TestCase):

    def test_a_zenodo_deposit_resolves(self):
        t = V.fetch_datacite('10.5281/zenodo.18671158')
        self.assertTrue(t, 'a real Zenodo DOI returned no title')
        self.assertIn('Concept Drift', t)

    def test_a_repository_deposit_resolves(self):
        t = V.fetch_datacite('10.34726/12041')
        self.assertTrue(t, 'a real repository DOI returned no title')
        self.assertIn('Hallucination', t)

    def test_an_arxiv_datacite_record_resolves(self):
        t = V.fetch_datacite('10.48550/arxiv.2510.18407')
        self.assertTrue(t, 'a real arXiv/DataCite DOI returned no title')
        self.assertIn('Adversarial', t)

    def test_a_journal_doi_is_not_in_datacite(self):
        """Returns None rather than raising, so the caller can treat a
        miss the same way it treats a Crossref miss."""
        self.assertIsNone(V.fetch_datacite('10.1038/nature12373'))

    def test_a_nonexistent_doi_returns_none(self):
        self.assertIsNone(V.fetch_datacite('10.9999/does-not-exist-xyz'))

    def test_the_returned_title_is_single_line(self):
        t = V.fetch_datacite('10.5281/zenodo.19054914')
        self.assertNotIn('\n', t or 'x')


if __name__ == '__main__':
    unittest.main()
