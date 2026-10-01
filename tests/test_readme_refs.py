"""README superscripts must reach a real, anchored citation.

Found 2026-09-30: all 62 superscript links in README.md were written as
`<sup>[N](#ref-N)</sup>` -- an in-page anchor -- while the 39 anchors they
target live in REFERENCES.md, a different file. Every one of them was a dead
link: the superscript rendered, the number looked like a citation, and nothing
was behind it. That is the exact shape the repo's own citation rule exists to
prevent, applied to the README that states the rule.

These tests resolve the links for real rather than pattern-matching, because
the failure mode is a link that looks correct.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO, 'README.md')
REFS = os.path.join(REPO, 'REFERENCES.md')

SUPERSCRIPT = re.compile(r'<sup>\[(\d+)\]\(([^)]+)\)</sup>')
LOCAL_ANCHOR = re.compile(r'<sup>\[\d+\]\(#ref-\d+\)</sup>')


class TestReadmeSuperscripts(unittest.TestCase):

    def setUp(self):
        self.readme = open(README, encoding='utf-8').read()
        self.refs = open(REFS, encoding='utf-8').read()
        self.anchors = set(re.findall(r'<a id="ref-(\d+)"', self.refs))

    def test_references_file_defines_anchors(self):
        self.assertGreater(len(self.anchors), 0,
                           'REFERENCES.md defines no ref-N anchors, so no '
                           'superscript in the README can resolve')

    def test_no_superscript_points_at_a_local_anchor(self):
        """The bug: an in-page anchor for a citation that lives elsewhere."""
        local = LOCAL_ANCHOR.findall(self.readme)
        self.assertEqual(
            local, [],
            'these superscripts point at #ref-N inside README.md, but the '
            'anchors are in REFERENCES.md: %s' % local[:5])

    def test_every_superscript_resolves_to_a_real_anchor(self):
        broken = []
        for num, url in SUPERSCRIPT.findall(self.readme):
            if url.startswith('REFERENCES.md#ref-'):
                if url.split('#ref-')[1] not in self.anchors:
                    broken.append((num, url))
            elif url.startswith('#ref-'):
                broken.append((num, url))  # local anchor, see the test above
            # anything else (a plain http link) is a different kind of
            # superscript and is not part of this contract
        self.assertEqual(broken, [],
                         'superscripts with no matching anchor: %s' % broken)

    def test_number_in_link_matches_number_in_text(self):
        for num, url in SUPERSCRIPT.findall(self.readme):
            if url.startswith('REFERENCES.md#ref-'):
                self.assertEqual(url.split('#ref-')[1], num,
                                 'superscript [%s] points at ref-%s'
                                 % (num, url.split('#ref-')[1]))

    def test_no_anchored_reference_is_orphaned(self):
        """A listed-but-uncited paper is fine to keep; an uncited anchor in
        REFERENCES.md usually means a superscript was renumbered away."""
        cited = {n for n, u in SUPERSCRIPT.findall(self.readme)
                 if u.startswith('REFERENCES.md#ref-')}
        orphans = sorted(self.anchors - cited, key=int)
        # Reported rather than failed: REFERENCES.md is allowed to carry
        # entries cited from docs other than the README.
        if orphans:
            print('  note: anchors not cited from README.md: %s' % orphans)

    def test_every_cited_entry_is_resolvable_at_source(self):
        """Every entry must carry a title OR a version+URL.

        Papers are titled; software releases are versioned and linked. A
        reference that is neither is a citation that resolved to nothing --
        the untitled_citation case this repo's rule exists to catch. The
        test that matters is that it can still fail, so the predicate is
        strict on purpose.

        A software pin may be a semver, a container tag, or an image
        digest: `v0.25.10`, `0.25.10-pg18`, and `server-vulkan` are all
        pins, and all three appear here.
        """
        parts = re.split(r'<a id="ref-(\d+)"></a>', self.refs)
        blocks = [parts[i + 1] for i in range(1, len(parts), 2)]
        unresolved = []
        PINNED = re.compile(
            r'v\d+\.\d+[\w.+-]*'          # v0.25.10
            r'|:\d+\.\d+[\w.-]*'          # image:0.25.10-pg18
            r'|sha256:[0-9a-f]{12,}'      # digest
            r'|:[a-z][\w.-]*'             # a named image tag, e.g.
        )                               # ghcr.io/.../llama.cpp:server-vulkan
        for i, b in enumerate(blocks, 1):
            quoted = re.search(r'\*"[^"]{8,}"\*', b)
            pinned = PINNED.search(b)
            has_url = 'http' in b
            if not ((quoted or pinned) and has_url):
                head = b.strip().split('\n')[0][:70]
                unresolved.append((i, head))
        self.assertEqual(
            unresolved, [],
            'references with neither a title nor a version, or no URL: %s'
            % unresolved[:5])

    def test_paper_entries_carry_a_quoted_title(self):
        """Of those, anything that looks like a paper must be titled.

        Entries whose first line names an author or a year are citations of
        literature rather than of a tool, and those need a real title.
        """
        parts = re.split(r'<a id="ref-(\d+)"></a>', self.refs)
        blocks = [parts[i + 1] for i in range(1, len(parts), 2)]
        untitled_papers = []
        for i, b in enumerate(blocks, 1):
            head = b.strip().split('\n')[0]
            looks_like_literature = re.search(r'\(\d{4}\)|&\s*\w|\bet al\.', head)
            if looks_like_literature and not re.search(r'\*"[^"]{8,}"\*', b):
                untitled_papers.append((i, head[:70]))
        self.assertEqual(
            untitled_papers, [],
            'literature citations with no title: %s' % untitled_papers[:5])


if __name__ == '__main__':
    unittest.main()
