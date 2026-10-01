"""Tests for the raw/ drift checker and the gate's directory handling.

Both exist because the obvious invocation of each failed:

  * `okf_gate.py <folder>` said "Is a directory". The natural way to run a
    schema check on a wiki folder was the way that did not work.
  * `check_raw_drift.py` had no raw sources yet, so a checker that finds
    nothing cannot be shown to find anything.

The drift tests therefore seed a temporary raw/ and assert on the three
outcomes. A hash that is never recomputed is documentation, not detection --
so the tamper case is the one that matters.
"""
import importlib.util
import os
import shutil
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_HERE)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


D = _load("check_raw_drift", os.path.join(REPO, "scripts",
                                          "check_raw_drift.py"))


class TestSha256Scope(unittest.TestCase):
    """The hash covers the body, never the frontmatter."""

    def test_hash_is_of_the_body(self):
        self.assertEqual(len(D.sha256_of("text\n")), 64)

    def test_hash_is_stable(self):
        self.assertEqual(D.sha256_of("same"), D.sha256_of("same"))

    def test_different_body_different_hash(self):
        self.assertNotEqual(D.sha256_of("a"), D.sha256_of("b"))

    def test_frontmatter_is_split_off(self):
        fm, body = D.split_frontmatter("---\nsha256: x\n---\nBODY\n")
        self.assertIn("sha256", fm)
        self.assertEqual(body, "BODY\n")

    def test_no_frontmatter_returns_none(self):
        fm, body = D.split_frontmatter("no frontmatter here")
        self.assertIsNone(fm)
        self.assertEqual(body, "no frontmatter here")

    def test_hashing_the_whole_file_would_never_match(self):
        """The self-reference this design avoids.

        The frontmatter carries the hash, so a whole-file hash could never
        equal the stored value. This pins the reason the body-only scope
        exists.
        """
        import hashlib
        body = "content\n"
        stored = D.sha256_of(body)
        whole = "---\nsha256: %s\n---\n%s" % (stored, body)
        self.assertNotEqual(hashlib.sha256(whole.encode()).hexdigest(), stored)


class TestStoredHashParsing(unittest.TestCase):
    def test_reads_a_64_hex_hash(self):
        h = "a" * 64
        self.assertEqual(D.stored_hash("sha256: %s\n" % h), h)

    def test_absent_when_missing(self):
        self.assertIsNone(D.stored_hash("source_url: https://x\n"))

    def test_set_hash_appends_when_absent(self):
        out = D.set_hash("source_url: https://x\n", "b" * 64)
        self.assertIn("sha256: %s" % ("b" * 64), out)

    def test_set_hash_replaces_when_present(self):
        out = D.set_hash("sha256: %s\n" % ("a" * 64), "c" * 64)
        self.assertIn("sha256: %s" % ("c" * 64), out)
        self.assertNotIn("sha256: %s" % ("a" * 64), out)


class TestDriftDetection(unittest.TestCase):
    """Seeded against a temporary raw/, never the live one."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.raw = os.path.join(self.tmp, "raw")
        self.articles = os.path.join(self.raw, "articles")
        os.makedirs(self.articles)
        self._orig_raw = D.RAW
        D.RAW = self.raw
        self._env = dict(os.environ)
        os.environ["HERMES_RAW_DIR"] = self.raw

    def tearDown(self):
        D.RAW = self._orig_raw
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, body, stored: str = "__AUTO__"):
        """Write a seeded raw file.

        `stored` defaults to the correct hash for the body. Pass an explicit
        value to simulate a stale hash, or the string "NONE" to write a file
        with no sha256 at all -- which needs a distinct sentinel, because
        None is falsy and would have been read as "compute it for me". That
        ambiguity is exactly what made the first version of this helper
        report OK for a file it was supposed to flag.
        """
        digest = D.sha256_of(body) if stored == "__AUTO__" else stored
        if digest == "NONE":
            digest = None
        path = os.path.join(self.articles, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\nsource_url: https://example.com/x\n"
                     "ingested: 2026-09-30\n"
                     + ("sha256: %s\n" % digest if digest else "")
                     + "---\n" + body)
        return path

    def _run(self, *argv):
        import subprocess
        return subprocess.run(
            ["python3", os.path.join(REPO, "scripts", "check_raw_drift.py")]
            + list(argv), capture_output=True, text=True)

    def test_untouched_file_is_ok(self):
        self._write("good.md", "original\n")
        r = self._run()
        self.assertIn("OK       1", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_edited_body_is_reported_as_changed(self):
        body = "original\n"
        self._write("tampered.md", "EDITED\n", stored=D.sha256_of(body))
        r = self._run()
        self.assertIn("CHANGED  1", r.stdout)
        self.assertIn("tampered.md", r.stdout)

    def test_missing_hash_is_reported(self):
        self._write("nohash.md", "content\n", stored="NONE")
        r = self._run()
        self.assertIn("NO HASH  1", r.stdout)

    def test_strict_exits_nonzero_on_drift(self):
        body = "original\n"
        self._write("tampered.md", "EDITED\n", stored=D.sha256_of(body))
        self.assertEqual(self._run("--strict").returncode, 1)

    def test_strict_exits_nonzero_on_missing_hash(self):
        self._write("nohash.md", "content\n", stored="NONE")
        self.assertEqual(self._run("--strict").returncode, 1)

    def test_strict_passes_on_a_clean_dir(self):
        self._write("good.md", "original\n")
        self.assertEqual(self._run("--strict").returncode, 0)

    def test_drift_is_never_silently_repaired(self):
        """A stored hash is evidence. Rewriting it destroys the evidence."""
        body = "original\n"
        self._write("tampered.md", "EDITED\n", stored=D.sha256_of(body))
        self._run()          # no --write
        after = open(os.path.join(self.articles, "tampered.md"),
                     encoding="utf-8").read()
        self.assertIn(D.sha256_of(body), after,
                      "the stored hash was rewritten without being asked")

    def test_write_adds_a_hash_and_keeps_it_stable(self):
        path = self._write("nohash.md", "content\n", stored="NONE")
        self._run("--write")
        self.assertIn("sha256:", open(path, encoding="utf-8").read())
        self.assertEqual(self._run("--strict").returncode, 0,
                         "a freshly written hash must match immediately")

    def test_index_md_is_not_treated_as_a_source(self):
        idx = os.path.join(D.RAW, "index.md")
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write("# Index\n")
        self._write("good.md", "original\n")
        r = self._run()
        self.assertNotIn("index.md", r.stdout)

    def test_empty_raw_dir_is_not_an_error(self):
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertIn("no source files", r.stdout)


if __name__ == "__main__":
    unittest.main()
