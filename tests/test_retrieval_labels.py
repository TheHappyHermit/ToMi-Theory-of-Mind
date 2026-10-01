#!/usr/bin/env python3
"""
Tests for the rebuilt retrieval benchmark.

The defect being removed is subtle enough that it needs pinning down precisely.
The old labels were filename fragments matched by substring against the path,
which meant the labels and the keyword arm shared a matching rule. Three
consequences, one test each:

  1. A document could be labelled relevant by what it was CALLED.
  2. The "oracle" arm shared the keyword arm's matching rule, so "keyword
     achieves oracle ceiling" was a tautology rather than a result.
  3. Renaming a document could change its label.

There is also a test that the substring function is ABSENT from the source.
It is the obvious way to write this, it looks reasonable, and it will creep
back. A test that fails when the defect is reintroduced is the only thing that
keeps it out.

Run:  PYTHONPATH=<repo>:<repo>/scripts python3 tests/test_retrieval_labels.py
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import retrieval_labels as rl  # noqa: E402

Q = "thalamus gating sensory attention"
ON_TOPIC = ("the thalamus gates sensory input before it reaches the cortex. "
            "thalamic gating filters attention and the thalamic nuclei carry "
            "sensory signals. ") * 12
OFF_TOPIC = "a shopping list, some weather notes, and a bus timetable. " * 40


class TestLabelsAreJudgedOnContent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="labels-")
        self.root = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = self.root / name
        p.write_text(text)
        return p

    def test_a_document_discussing_the_topic_is_labelled(self):
        self.assertTrue(rl.judge_by_content(self.write("a.md", ON_TOPIC), Q))

    def test_a_document_not_discussing_it_is_not(self):
        self.assertFalse(rl.judge_by_content(self.write("b.md", OFF_TOPIC), Q))

    def test_a_misleading_filename_does_not_make_it_relevant(self):
        """The exact defect. A file called thalamus-gating.md whose text says
        nothing about the thalamus must not be labelled -- the old rule would
        have labelled it on the name alone."""
        p = self.write("thalamus-gating-sensory-attention.md", OFF_TOPIC)
        self.assertFalse(rl.judge_by_content(p, Q),
                         "filename alone decided relevance -- substring defect")

    def test_a_misleading_body_is_not_rescued_by_a_timid_filename(self):
        p = self.write("zzz.md", ON_TOPIC)
        self.assertTrue(rl.judge_by_content(p, Q),
                        "an uninformative filename must not hide relevant content")

    def test_one_passing_mention_is_not_enough(self):
        """A single occurrence is not a document about the thing."""
        p = self.write("c.md", "the thalamus is mentioned once. " + OFF_TOPIC)
        self.assertFalse(rl.judge_by_content(p, Q))

    def test_an_empty_document_is_not_labelled(self):
        self.assertFalse(rl.judge_by_content(self.write("d.md", ""), Q))

    def test_an_unknown_query_is_an_error_not_a_silent_false(self):
        """A typo'd query returning False would quietly remove a query's labels
        and read as a strategy failure."""
        p = self.write("e.md", ON_TOPIC)
        with self.assertRaises(KeyError):
            rl.judge_by_content(p, "a query nobody defined terms for")


class TestIdentityIsContent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hash-")
        self.root = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_renaming_does_not_change_identity(self):
        """Otherwise tidying filenames silently invalidates every label."""
        a = self.root / "original-name.md"
        b = self.root / "completely-different.md"
        a.write_text(ON_TOPIC)
        b.write_text(ON_TOPIC)
        self.assertEqual(rl.doc_hash(a), rl.doc_hash(b))

    def test_different_content_gives_different_identity(self):
        a = self.root / "one.md"
        b = self.root / "two.md"
        a.write_text(ON_TOPIC)
        b.write_text(OFF_TOPIC)
        self.assertNotEqual(rl.doc_hash(a), rl.doc_hash(b))

    def test_identity_is_stable_across_calls(self):
        a = self.root / "stable.md"
        a.write_text(ON_TOPIC)
        self.assertEqual(rl.doc_hash(a), rl.doc_hash(a))

    def test_an_unreadable_file_still_gets_a_distinct_identity(self):
        """Two unreadable files must not collide into one label."""
        a = self.root / "missing-one.md"
        b = self.root / "missing-two.md"
        self.assertNotEqual(rl.doc_hash(a), rl.doc_hash(b))

    def test_labels_survive_a_rename(self):
        """The point of hashing content: tidying filenames must not silently
        invalidate every label. Re-walk the directory so the label set is
        rebuilt from what is actually on disk -- a stale Path pointing at a file
        that no longer exists would make this pass for the wrong reason."""
        topic = self.root / "before.md"
        topic.write_text(ON_TOPIC)
        (self.root / "unrelated.md").write_text(OFF_TOPIC)

        before = rl.build_labels(sorted(self.root.glob("*.md")))[Q]
        self.assertEqual(len(before), 1)

        topic.rename(self.root / "after.md")
        after = rl.build_labels(sorted(self.root.glob("*.md")))[Q]
        self.assertEqual(before, after,
                         "a rename changed a document's relevance label")


class TestBuildLabelsIsIndependentOfStrategies(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="build-")
        self.root = Path(self.tmp)
        self.docs = []
        for i in range(6):
            p = self.root / f"doc{i}.md"
            p.write_text(ON_TOPIC if i < 3 else OFF_TOPIC)
            self.docs.append(p)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_every_query_gets_labels(self):
        labels = rl.build_labels(self.docs)
        self.assertEqual(set(labels), set(rl.QUERIES))

    def test_the_on_topic_documents_are_labelled(self):
        """These three files are byte-identical, so they share one label. That
        is the documented consequence of content identity, and the right
        behaviour: three copies of the same text are one document as far as
        relevance goes. Distinct content would give three labels."""
        labels = rl.build_labels(self.docs)[Q]
        self.assertEqual(len(labels), 1)

    def test_distinct_relevant_documents_get_distinct_labels(self):
        # Each must be genuinely distinct content, or they collapse to one
        # label -- which is the documented behaviour, not a bug to work around.
        for i, extra in enumerate([
            "The relay nuclei project widely to the cortex. ",
            "Pulvinar and reticular nuclei are involved too. ",
            "Thalamic gating shapes what reaches awareness. ",
        ]):
            (self.root / f"variant{i}.md").write_text(ON_TOPIC + extra * 6)
        labels = rl.build_labels(sorted(self.root.glob("*.md")))[Q]
        self.assertEqual(len(labels), 4)

    def test_a_label_is_a_hash_not_a_path(self):
        """Labels must not be recognisable as filenames, or the temptation to
        match on one returns."""
        for label in rl.build_labels(self.docs)[Q]:
            self.assertNotIn("/", label)
            self.assertNotIn(".md", label)
            self.assertRegex(label, r"^[0-9a-f]{16}$")

    def test_labelling_is_the_same_however_the_corpus_is_ordered(self):
        forward = rl.build_labels(self.docs)[Q]
        backward = rl.build_labels(list(reversed(self.docs)))[Q]
        self.assertEqual(forward, backward)


class TestTheSubstringTestStaysGone(unittest.TestCase):
    """The failure mode this module has to defend against is itself."""

    def test_no_is_relevant_function_exists(self):
        self.assertFalse(hasattr(rl, "is_relevant"))

    def test_no_is_relevant_in_the_benchmark_source(self):
        src = (REPO / "scripts" / "measure_retrieval_quality.py").read_text()
        code = "\n".join(
            line for line in src.splitlines()
            if not line.strip().startswith("#"))
        self.assertNotIn(
            "is_relevant", code,
            "the substring relevance test is back in the benchmark")

    def test_no_path_substring_matching_in_the_labeller(self):
        """A label must never be tested against a returned PATH."""
        src = (REPO / "scripts" / "retrieval_labels.py").read_text()
        code = "\n".join(
            line for line in src.splitlines()
            if not line.strip().startswith("#"))
        self.assertNotIn(".lower() in ", code,
                         "a case-insensitive substring test is back")

    def test_judgement_set_of_filename_fragments_is_gone(self):
        src = (REPO / "scripts" / "measure_retrieval_quality.py").read_text()
        self.assertNotIn('JUDGEMENT_SET: List', src,
                         "the filename-fragment judgement set is back")


class TestMultiHopGate(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import measure_retrieval_quality as mrq
        self.mrq = mrq

    def test_the_gate_fires_when_the_oracle_scores_too_well(self):
        """A perfect exhaustive keyword system scoring well means the labels
        are reachable by matching rather than by reading -- the original defect,
        and every other number is void."""
        ok, why = self.mrq.check_multi_hop_gate(
            {"strategy": "oracle", "recall": 0.5})
        self.assertFalse(ok)
        self.assertIn("void", why)

    def test_the_gate_passes_a_low_oracle_score(self):
        ok, _ = self.mrq.check_multi_hop_gate(
            {"strategy": "oracle", "recall": 0.03})
        self.assertTrue(ok)

    def test_the_gate_only_applies_to_the_oracle(self):
        ok, why = self.mrq.check_multi_hop_gate(
            {"strategy": "keyword", "recall": 0.9})
        self.assertTrue(ok, "a high keyword recall is not the gate's business")

    def test_both_control_arms_exist(self):
        """The plan calls them mandatory: without them every result is
        uninterpretable."""
        for name in ("control_full_context", "control_body_bm25"):
            self.assertTrue(hasattr(self.mrq, name),
                            f"missing mandatory control arm: {name}")

    def test_full_context_control_reports_an_upper_bound(self):
        labels = {"q": frozenset({"a", "b", "c"})}
        out = self.mrq.control_full_context([], labels, top_k=10)
        self.assertEqual(out["recall"], 1.0)
        self.assertIn("upper bound", out["note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
