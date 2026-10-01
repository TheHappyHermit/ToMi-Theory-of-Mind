"""Tests for the confidence grader's T2 promotion path.

The bug this file exists for was silent and looked exactly like a legitimate
demotion. grade_all.derive() was handed the ABSOLUTE path while the T2
evidence table is keyed by the vault-RELATIVE path, so lookup_verdict()'s
prefix strip was a no-op, every lookup returned 'absent', and every
T2-bearing file was reported as "T2 pending: N of N not matched" -- 946/946
matching identifiers included.

A grading tool that can never promote is worse than one that never runs,
because its output is a plausible-looking penalty rather than an error.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(os.path.dirname(_HERE), "scripts", "grade_all.py")
spec = importlib.util.spec_from_file_location("grade_all", _MOD)
ga = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ga)

DOI = "doi:10.1109/PROC.1975.9939"


class TestRelativePathKeying(unittest.TestCase):
    """The table key is `vault-relative-path::identifier`."""

    TABLE = {
        "research/batch264-the-verdict-nobody-reads.md::" + DOI: {"verdict": "match"},
        "oracle/brain/research/other.md::doi:10.1/x": {"verdict": "match"},
        "active-wiki/concepts/thing.md::doi:10.1109/dddd.4": {"verdict": "match"},
    }

    def test_relative_path_hits(self):
        v = ga.lookup_verdict(
            self.TABLE, "research/batch264-the-verdict-nobody-reads.md", DOI)
        self.assertEqual(v, "match")

    def test_full_vault_prefixed_path_hits(self):
        """What main() actually passes: path after '/.hermes/', which still
        carries the vault directory, and lookup_verdict must strip it."""
        rel = "oracle/brain/research/batch264-the-verdict-nobody-reads.md"
        v = ga.lookup_verdict(self.TABLE, rel, DOI)
        self.assertEqual(v, "match")

    def test_absolute_path_is_rejected(self):
        """An absolute path does NOT match -- which is exactly the bug.
        Pinned so the failure mode stays visible if the strip is changed."""
        absolute = ("/home/operator/.hermes/oracle/brain/research/"
                    "batch264-the-verdict-nobody-reads.md")
        v = ga.lookup_verdict(self.TABLE, absolute, DOI)
        self.assertEqual(v, "absent",
                         "if this now returns 'match', lookup_verdict learned "
                         "to handle absolute paths -- the main() fix at the "
                         "derive() call site may then be removable")

    def test_unknown_identifier_is_absent_not_crash(self):
        v = ga.lookup_verdict(self.TABLE, "research/batch264-the-verdict-nobody-reads.md",
                               "doi:10.999/nope")
        self.assertEqual(v, "absent")


class TestT2AllMatch(unittest.TestCase):

    TABLE = {
        "research/batch264.md::doi:10.1109/aaaa.1": {"verdict": "match"},
        "research/batch264.md::doi:10.1109/bbbb.2": {"verdict": "match"},
    }
    SRCS = ["https://doi.org/10.1109/aaaa.1", "https://doi.org/10.1109/bbbb.2"]

    def test_all_match_promotes(self):
        ok, why = ga.t2_all_match(self.SRCS, self.TABLE,
                                   rel_path="research/batch264.md")
        self.assertTrue(ok, why)

    def test_one_bad_identifier_blocks(self):
        srcs = self.SRCS + ["https://doi.org/10.1109/cccc.3"]
        ok, why = ga.t2_all_match(srcs, self.TABLE, rel_path="research/batch264.md")
        self.assertFalse(ok)
        self.assertIn("not matched", why)

    def test_no_identifier_is_not_a_pass(self):
        """A T2-venue file with no resolvable identifier must not be
        promoted -- absence of evidence is not evidence."""
        ok, why = ga.t2_all_match(["https://nature.com/articles/x"],
                                  self.TABLE, rel_path="research/batch264.md")
        self.assertFalse(ok)
        self.assertIn("no T2 identifier", why)


class TestEndToEndDerivePath(unittest.TestCase):
    """derive() must be handed the relative path, or the promotion is
    structurally impossible no matter how good the citations are."""

    def _doc(self, sources):
        return ("---\ntype: research-report\nconfidence: medium\n"
                "sources:\n" + sources +
                "\n---\n\nBody text with a doi.org source and little else here.\n")

    def test_derive_with_relative_path_can_reach_high(self):
        ga.T2_TABLE = {"research/p.md::" + DOI: {"verdict": "match"}}
        try:
            srcs = "  - https://doi.org/10.1109/PROC.1975.9939"
            band, why = ga.derive("research/p.md", self._doc(srcs), {
                "type": "research-report", "sources": [DOI.replace("doi:", "https://doi.org/")]})
        finally:
            ga.T2_TABLE = {}
        self.assertEqual(band, "high", why)

    def test_derive_with_absolute_path_degrades_to_medium(self):
        """Documents the original failure: absolute path -> 'absent' -> medium."""
        ga.T2_TABLE = {"research/p.md::" + DOI: {"verdict": "match"}}
        try:
            band, why = ga.derive("/home/x/.hermes/oracle/brain/research/p.md",
                                  self._doc(""), {"type": "research-report", "sources": []})
        finally:
            ga.T2_TABLE = {}
        self.assertNotEqual(band, "high")


class TestArxivShapes(unittest.TestCase):
    """arXiv citations appear in three shapes and the original pattern
    matched only the bare prefix.

    `arxiv[:/]` looks like it covers the URLs, but 'arxiv.org/abs/' has
    '.org/' between 'arxiv' and the slash, so neither branch fired. On this
    corpus that hid 1,413 arXiv citations, and a file whose only strong
    evidence was an arXiv URL was graded "T2 pending: no T2 identifier"
    and demoted.
    """

    ALL_SHAPES = [
        "https://arxiv.org/abs/2607.18704",
        "https://arxiv.org/pdf/2607.18704",
        "https://arxiv.org/html/2607.18704",
        "http://arxiv.org/abs/2607.18704",
        "arxiv.org/abs/2607.18704",
        "arxiv:2607.18704",
        "arXiv:2607.18704",
    ]

    def test_every_shape_normalizes_to_the_same_key(self):
        for src in self.ALL_SHAPES:
            with self.subTest(src=src):
                self.assertEqual(ga.t2_ids([src]), {"arxiv:2607.18704"})

    def test_version_suffix_is_stripped(self):
        """The table is keyed on the bare identifier, so a suffixed form
        would miss every lookup."""
        for src in ("https://arxiv.org/pdf/2607.01977v1",
                    "https://arxiv.org/abs/2601.23014v2",
                    "https://arxiv.org/abs/2607.18704v3"):
            with self.subTest(src=src):
                self.assertNotIn("v", list(ga.t2_ids([src]))[0].split(".")[-1])

    def test_five_digit_serial_is_accepted(self):
        self.assertEqual(ga.t2_ids(["https://arxiv.org/abs/2607.18704"]),
                         {"arxiv:2607.18704"})

    def test_doi_shapes_still_work(self):
        for src in ("https://doi.org/10.1109/PROC.1975.9939",
                    "doi:10.1371/journal.pone.0110274",
                    "https://dx.doi.org/10.1000/xyz123"):
            with self.subTest(src=src):
                self.assertTrue(ga.t2_ids([src]))

    def test_non_identifiers_yield_nothing(self):
        """A URL with no identifier must not become one."""
        for src in ("https://github.com/foo/bar", "https://prometheus.io/docs/",
                    "session:abc", "nas://media/movies",
                    "https://nature.com/articles/x"):
            with self.subTest(src=src):
                self.assertEqual(ga.t2_ids([src]), set())


class TestBackupNaming(unittest.TestCase):
    """The backup directory must not flatten paths to basenames.

    The two vaults hold mirrored copies of the same page
    (active-wiki/concepts/X.md and oracle/brain/concepts/X.md). A
    basename-flat backup made the second overwrite the first, so a
    109-file write produced 106 backups -- three files silently
    unrecoverable, while the run still reported "written: 109 failed: 0".

    A backup that cannot restore what it claims to have backed up is worse
    than none, because it invites you to skip the manual copy.
    """

    MIRRORED = [
        "concepts/brain-region-build-vs-adopt.md",
        "concepts/structural-pass-is-not-a-content-pass.md",
        "entities/honcho-memory-stack.md",
    ]

    def test_mirrored_basenames_would_collide(self):
        """Guards the premise: if this ever stops holding, the collision
        cannot happen and the fix is unnecessary."""
        from collections import Counter
        both = [f"active-wiki/{n}" for n in self.MIRRORED] + \
               [f"oracle/brain/{n}" for n in self.MIRRORED]
        counts = Counter(os.path.basename(p) for p in both)
        self.assertTrue(all(v == 2 for v in counts.values()))

    def test_flattened_name_would_be_lossy(self):
        """The old scheme mapped 6 distinct paths onto 3 filenames."""
        both = [f"active-wiki/{n}" for n in self.MIRRORED] + \
               [f"oracle/brain/{n}" for n in self.MIRRORED]
        flat = {os.path.basename(p) for p in both}
        self.assertEqual(len(flat), len(both) // 2)

    def test_collision_free_name_preserves_distinctness(self):
        """The replacement scheme must map distinct paths to distinct names."""
        both = [f"active-wiki/{n}" for n in self.MIRRORED] + \
               [f"oracle/brain/{n}" for n in self.MIRRORED]
        names = {p.replace('/', '__') for p in both}
        self.assertEqual(len(names), len(both))


if __name__ == "__main__":
    unittest.main()
