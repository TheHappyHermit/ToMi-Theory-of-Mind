"""Tests for scripts/measure_retrieval_quality.py.

The bug this file guards against is a benchmark that silently measures nothing.
Two real instances were found and fixed while writing it:

  1. `iter_documents` filtered on the ABSOLUTE path, so any corpus living under a
     dot-prefixed directory (`~/.something`, or a tempdir in the self-test)
     returned zero documents -- and the benchmark would report a confident
     result having looked at nothing.
  2. The verdict text asserted fusion was "diluting" the keyword result without
     establishing the cause. It now reports the top-k composition so the
     mechanism is visible rather than assumed.

These tests exist so neither can come back.
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "measure_retrieval_quality.py"

sys.path.insert(0, str(REPO / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("measure_retrieval_quality", SCRIPT)
assert _spec is not None and _spec.loader is not None, "could not load the benchmark module"
mrq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mrq)

# The label module is imported by name rather than by path spec: the benchmark
# imports it as `import retrieval_labels as rl`, and loading it a second way
# would create a second copy of the module with its own constants.
import retrieval_labels as rl  # noqa: E402


class TestSelfTest(unittest.TestCase):
    def test_self_test_passes(self):
        r = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--self-test"],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


class TestCorpusDiscovery(unittest.TestCase):
    def test_finds_docs_in_a_dot_prefixed_directory(self):
        """Regression: the absolute-path filter rejected these entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".hidden-vault"
            root.mkdir()
            (root / "a.md").write_text("x")
            found = mrq.iter_documents(root)
            self.assertEqual(len(found), 1, "dot-prefixed corpus must still be scanned")

    def test_skips_dotfiles_relative_to_the_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.md").write_text("x")
            hidden = root / ".git"
            hidden.mkdir()
            (hidden / "skip.md").write_text("x")
            names = [p.name for p in mrq.iter_documents(root)]
            self.assertIn("keep.md", names)
            self.assertNotIn("skip.md", names)

    def test_missing_vault_returns_empty_not_error(self):
        self.assertEqual(mrq.iter_documents(Path("/nonexistent/path/xyz")), [])


class TestRelevanceMatching(unittest.TestCase):
    """Relevance is decided by content hash, not by substring on the path.

    The three cases below are the old test's cases inverted: each one is a
    situation the substring rule got wrong, and they are kept so the inversion
    is visible rather than just asserted in a commit message.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_filename_match_alone_is_not_relevance(self):
        """The substring rule called this relevant. It says nothing about the
        thalamus, so it is not."""
        p = self.root / "thalamus-gating-attention.md"
        p.write_text("a shopping list and a bus timetable. " * 40)
        self.assertFalse(rl.judge_by_content(p, "thalamus gating sensory attention"))

    def test_an_unrelated_filename_can_still_be_relevant(self):
        """The other inversion: a document that discusses the subject is
        relevant whatever it is called. The substring rule marked this wrong."""
        p = self.root / "Implementation-Intentions.md"
        p.write_text(
            "the thalamus gates sensory input before it reaches the cortex. "
            "thalamic gating filters attention and the thalamic nuclei carry "
            "sensory signals. " * 12)
        self.assertTrue(rl.judge_by_content(p, "thalamus gating sensory attention"))

    def test_content_hashing_handles_path_objects_and_strings_alike(self):
        """The oracle arm passes Path objects; hashing must accept both."""
        p = self.root / "x.md"
        p.write_text("content that is distinct from everything else here.")
        self.assertEqual(rl.doc_hash(p), rl.doc_hash(str(p)))


class TestKeywordIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "hippocampus.md").write_text("x")
        (self.root / "thalamus.md").write_text("x")
        self.docs = mrq.iter_documents(self.root)
        self.index = mrq.build_keyword_index(self.docs)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_planted_document(self):
        got = mrq.keyword_search("hippocampus", self.docs, self.index, 10)
        self.assertEqual(len(got), 1)
        self.assertIn("hippocampus", str(self.docs[got[0]]))

    def test_absent_term_returns_nothing(self):
        self.assertEqual(mrq.keyword_search("zzzznotpresent", self.docs, self.index, 10), [])

    def test_respects_top_k(self):
        got = mrq.keyword_search("md", self.docs, self.index, 1)
        self.assertLessEqual(len(got), 1)

    def test_empty_query_is_safe(self):
        self.assertEqual(mrq.keyword_search("", self.docs, self.index, 10), [])
        self.assertEqual(mrq.keyword_search("the a of", self.docs, self.index, 10), [])


class TestFusion(unittest.TestCase):
    def test_promotes_agreement(self):
        fused = mrq.fuse(["a", "b", "c"], ["x", "b", "y"], top_k=10)
        self.assertEqual(fused[0], "b")

    def test_respects_top_k(self):
        self.assertEqual(len(mrq.fuse(["a", "b", "c"], ["d", "e"], top_k=2)), 2)

    def test_empty_inputs_are_safe(self):
        self.assertEqual(mrq.fuse([], [], top_k=5), [])

    def test_single_strategy_still_ranks(self):
        self.assertEqual(mrq.fuse(["a", "b"], [], top_k=2), ["a", "b"])


class TestJudgementSetIntegrity(unittest.TestCase):
    """Integrity of the content-hash label set, replacing the same checks on the
    filename-fragment set."""

    def test_every_query_has_content_terms(self):
        for q in rl.QUERIES:
            self.assertTrue(rl.CONCEPT_TERMS[q], f"{q!r} has no terms defined")

    def test_queries_are_unique(self):
        self.assertEqual(len(rl.QUERIES), len(set(rl.QUERIES)))

    def test_every_query_has_at_least_one_term(self):
        for q in rl.QUERIES:
            self.assertGreaterEqual(len(rl.CONCEPT_TERMS[q]), 2,
                                    f"{q!r} has too few terms to judge on")

    def test_no_term_is_a_path_fragment(self):
        """A term containing a slash or a file extension is a filename, and
        reintroduces the coupling to naming this replaced."""
        for q, terms in rl.CONCEPT_TERMS.items():
            for term in terms:
                self.assertNotIn("/", term, f"{q!r}: {term!r} looks like a path")
                self.assertNotIn(".md", term)

    def test_build_labels_covers_every_query(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        p = root / "a.md"
        p.write_text("content. " * 50)
        labels = rl.build_labels([p])
        self.assertEqual(set(labels), set(rl.QUERIES))
        tmp.cleanup()


class TestNoCorpusMeansNoResult(unittest.TestCase):
    """A benchmark that cannot measure must not report success.

    Both vault paths are redirected, not just HERMES_HOME. The resolver reads
    ORACLE_BRAIN_PATH and ACTIVE_WIKI_PATH, so setting only HERMES_HOME left the
    real vault in place and the run succeeded -- which is a more dangerous
    version of this test, since it passed while measuring the wrong corpus.
    """

    def test_exits_2_when_corpus_absent(self):
        r = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)],
            capture_output=True, text=True, timeout=120,
            env={"PATH": "/usr/bin:/bin",
                 "HERMES_HOME": "/nonexistent/vault/path",
                 "ORACLE_BRAIN_PATH": "/nonexistent/vault/oracle",
                 "ACTIVE_WIKI_PATH": "/nonexistent/vault/wiki"},
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_the_corpus_is_never_silently_substituted(self):
        """Pointing at a nonexistent vault must not quietly measure some other
        one. The whole point of the resolver is that the corpus is the vault the
        graph indexes, and a silent fallback is how the two diverged."""
        r = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)],
            capture_output=True, text=True, timeout=120,
            env={"PATH": "/usr/bin:/bin",
                 "ORACLE_BRAIN_PATH": "/nonexistent/vault/oracle",
                 "ACTIVE_WIKI_PATH": "/nonexistent/vault/wiki"},
        )
        combined = r.stdout + r.stderr
        self.assertNotIn("autognosia", combined,
                         "a nonexistent corpus was silently replaced by a real one")
        self.assertIn("No markdown corpus", r.stderr)


class TestUnknownStrategy(unittest.TestCase):
    def test_raises_on_unknown_strategy(self):
        with self.assertRaises(ValueError):
            mrq.evaluate([], {}, "nonsense", 10)


if __name__ == "__main__":
    unittest.main()

class TestCorpusResolution(unittest.TestCase):
    """The benchmark must measure the vault the graph was built over.

    This is the third instance of the same failure: the graph returns paths
    relative to the vault it indexed, so pointing the benchmark at a different
    tree makes every path unresolvable and the graph arm scores 0.000 forever
    while looking like a genuine result. Three separate bugs had this shape --
    the graph read from the wrong vault, then from a vault that had never been
    indexed, then a corpus that was the Hermes install directory rather than a
    vault at all.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make(self, name, with_graph):
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "a.md").write_text("x" * 100)
        if with_graph:
            (d / "graphify-out").mkdir(exist_ok=True)
            (d / "graphify-out" / "graph.json").write_text('{"nodes":[],"links":[]}')
        return d

    def test_prefers_the_vault_that_actually_has_a_graph(self):
        """A directory existing is not evidence it was indexed. On this machine
        ~/.hermes/oracle/brain exists with 378 files and no graph, and choosing
        by existence picks it over the vault that has a 21MB one."""
        with_graph = self._make("indexed", True)
        self._make("not_indexed", False)
        original = (mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI)
        mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = with_graph, self.root / "not_indexed"
        try:
            self.assertEqual(mrq.resolve_corpus_root(), with_graph)
        finally:
            mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = original

    def test_warns_rather_than_scoring_silently_when_no_graph_exists(self):
        """Reporting 0.000 without saying why is how a path bug reads as a
        quality finding."""
        empty = self._make("no_graph", False)
        original = (mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI)
        mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = empty, self.root / "absent"
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                chosen = mrq.resolve_corpus_root()
        finally:
            mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = original
        self.assertEqual(chosen, empty)
        self.assertIn("WARNING", err.getvalue())
        self.assertIn("not pointed at these files", err.getvalue())

    def test_graph_and_corpus_agree_after_resolution(self):
        """The property that actually matters, asserted end to end: the graph
        file lives inside the corpus root the benchmark will walk."""
        with_graph = self._make("indexed", True)
        original = (mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI)
        mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = with_graph, self.root / "absent"
        try:
            root = mrq.resolve_corpus_root()
        finally:
            mrq.gr.ORACLE_BRAIN, mrq.gr.ACTIVE_WIKI = original
        self.assertTrue((root / "graphify-out" / "graph.json").exists(),
                        "corpus and graph are in different places again")

