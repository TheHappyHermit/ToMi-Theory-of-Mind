"""Tests for T2 cache-key scoping.

The bug these cover is not a string-matching bug. It is that two vault
files citing the SAME identifier were collapsed into one record, so one
file's verdict silently overwrote another's. Everything downstream
trusted the table, and the table said a correct citation was wrong.
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


class TestCacheKeyScoping(unittest.TestCase):
    """A verdict is a property of (file, identifier), not identifier."""

    def test_source_actually_scopes_the_key_to_the_file(self):
        """Read the real loop and assert the key includes `rel`.

        Asserting on a key this test file builds itself would pass no
        matter what the verifier does, so the assertion is made against
        the verifier's own source.
        """
        src = (REPO / 'scripts' / 'verify_t2_titles.py').read_text(
            encoding='utf-8')
        self.assertIn(
            "key = f'{rel}::{fetch_key}'", src,
            "the verdict key must be scoped to the citing file; without it "
            "two files citing one identifier collapse into one verdict")

    def test_title_cache_is_scoped_to_the_identifier(self):
        """The title may still be fetched once per identifier.

        Scoping the verdict to the file must not mean re-fetching the
        same DOI from every file that cites it, at a 3s rate limit.
        """
        src = (REPO / 'scripts' / 'verify_t2_titles.py').read_text(
            encoding='utf-8')
        self.assertIn('title_cache', src)
        self.assertIn('if fetch_key in title_cache:', src)


class TestRealVaultShape(unittest.TestCase):
    """Confirm the premise against the real vault, not a mock."""

    def test_duplicate_identifier_across_files_exists(self):
        ident = '2505.17335'
        root = Path('/home/operator/.hermes/oracle/brain')
        if not root.exists():
            self.skipTest('vault not present on this host')
        hits = []
        for p in root.rglob('*.md'):
            try:
                if ident in p.read_text(encoding='utf-8', errors='replace'):
                    hits.append(str(p.relative_to(root)))
            except Exception:
                continue
        self.assertGreaterEqual(
            len(hits), 2,
            'the duplicate-identifier premise must still hold in the vault')

    def test_one_file_has_the_real_title(self):
        """The 'correct' file must genuinely carry the title.

        Guards against the test passing because both files turned out to
        be annotations, which would make the keying untested.
        """
        f = (Path('/home/operator/.hermes/oracle/brain/research')
             / 'cboritem-2026-ecosystem-survey.md')
        if not f.exists():
            self.skipTest('vault file not present on this host')
        txt = f.read_text(encoding='utf-8', errors='replace')
        self.assertIn('Secure Parsing and Serializing', txt)
        labels = V.cited_titles(str(f), txt)
        own = [x for x in labels if '2505.17335' in x]
        self.assertTrue(own, 'expected a label owning the identifier')
        self.assertTrue(
            any('Secure Parsing' in V.inline_title(x or '') for x in own),
            'the title-bearing label must survive inline_title()')


if __name__ == '__main__':
    unittest.main()
