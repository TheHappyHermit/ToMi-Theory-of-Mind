#!/usr/bin/env python3
"""Reference-list parser shared by the citation migration and its tests.

Extracted to the repo because a dry run proved the naive version silently
destroys knowledge: these wiki files use numbered CONTENT lists as well as
numbered reference lists, and the two are the same shape. Every guard here
was added after a failure, and scripts/verify_citation_parser.py holds a
control for each one.
"""
import re

MARKER = re.compile(r'\[\[(\d{1,3})\]\]')

# A reference-list line. These files use THREE forms and the state file
# recorded all three: "[[14]] Author (2017). Title.", "14. Author...", and
# "[14] Author...". The wikilink form is the important discovery: the
# reference list is itself made of wikilinks, which is why the linter counts
# every one of them as a broken link AND why the body marker and its
# definition look identical.
#
# The bare "N. " form is DANGEROUS and must not be accepted without a
# citation signal: these files also use numbered CONTENT lists ("1. **Self-
# organization without predefined ontologies.** ...") and a dry run caught
# that treating those as references deletes body content. So a bare-number
# reference is only accepted when the line also looks like a citation, i.e.
# it carries a year, a DOI, an arXiv id, or a journal-ish italic run.
REFLINE_WIKILINK = re.compile(r'^\s*(?:[-*]\s*)?\[\[(\d{1,3})\]\]\s+(.{6,})$')
REFLINE_BRACKET = re.compile(r'^\s*(?:[-*]\s*)?\[(\d{1,3})\]\s+(.{6,})$')
REFLINE_BARE = re.compile(r'^\s*(?:[-*]\s*)?(\d{1,3})[.)]\s+(.{6,})$')
CITATION_SIGNAL = re.compile(
    # Year in parens, a DOI/URL, an arXiv id, a journal-style italic run, a
    # volume:page or page range. The italic test must be a SINGLE-asterisk
    # run, not "**bold**": an earlier version used \\*\\w and matched the
    # "**S**" in "**Self-organization...**", which made the negative control
    # fail and would have treated numbered content lists as references.
    r'\(\d{4}\)|https?://|doi\.org|arXiv|'
    r'(?<!\*)\*[^*\n]{3,}\*(?!\*)|'
    r'\b\d+:\d+[-–]\d+|\bpp?\.\s?\d|\bISBN\b',
    re.I)

# ---------------------------------------------------------------------------
# PHASE 3.2 ADDITIONS -- three syntaxes found by READING files, not by
# reasoning about the format. Each one made the parser report a file that
# DOES have a reference list as having none.
#
#   bold bracket    **[1]** Anderson, J. R. (2007). *Title*. Press.
#                   85 markers, Cognitive-Architecture-Models.md
#   bullet bracket  - [1] Large Ontology Models -- arXiv 2602.00029
#                   17 markers, under a "## Key Works" heading
#   inline link     ...49% [[1]](https://example.org/paper)
#                   48 markers across 10 files: the number is a dead label
#                   on a link that already states its source, so the fix is
#                   to drop the number, NOT to build a footnote.
# ---------------------------------------------------------------------------
REFLINE_BOLD = re.compile(r'^\s*(?:[-*]\s*)?\*\*\[(\d{1,3})\]\*\*\s+(.{6,})$')

# Sections that legitimately hold a numbered reference list. "Key Works"
# and "Underlying Ideas" are not References headings, but in these files
# they hold exactly that.
#
# The heading may be NUMBERED: "## 7. Key Works" was missed entirely by an
# earlier pattern anchored at the first word, so the file was reported as
# having no reference list when it had five. The optional leading number
# plus its punctuation is required, not cosmetic.
LIST_HEADINGS = re.compile(
    r'^#{1,4}\s*(?:\d+[.)]\s*)?('
    r'References|Citations|Bibliography|Sources|Works Cited|'
    r'Key Works|Underlying Ideas|Key Sources|Selected References|'
    r'Primary Sources|Foundational Works)\b', re.I)

# [[N]](url): a dead number on an already-cited link.
INLINE_LINK = re.compile(
    r'\[\[(\d{1,3})\]\]\((\s*<?)((?:https?://|\.{0,2}/)[^)\s]+)(>?\s*)\)')

LINE_FORMS = (
    REFLINE_BOLD,
    REFLINE_WIKILINK,
    REFLINE_BRACKET,
)


def _match_line(line):
    """(number, text) for a reference line, or None.

    The trailing period of the NUMBER is stripped from the number syntax,
    never from the reference text. An earlier version called
    .rstrip('.') on the text, so a reference ending "ISBN 978-0262122962."
    lost its period on migration and the body gate reported a one-character
    difference on a correctly-migrated file. The gate was right; the
    parser was eating content.
    """
    for p in LINE_FORMS:
        m = p.match(line)
        if m:
            return int(m.group(1)), m.group(2).strip()
    m = REFLINE_BARE.match(line)
    if m and CITATION_SIGNAL.search(m.group(2)):
        return int(m.group(1)), m.group(2).strip()
    return None


def ref_entries(text):
    """Parse a numbered reference list into {number: reference_text}.

    Returns {} when the section does not hold a genuine list, which is the
    signal that this file's markers need judgement rather than a rewrite.
    """
    out = {}
    body = text.split('---', 2)[2] if text.startswith('---') and text.count('---') > 1 else text
    lines = body.splitlines()
    inrefs = False
    # Second, stronger guard: a real reference list is CONTIGUOUS and its
    # numbers ascend from 1. A file whose list section contains
    # non-ascending or gapped numbers is a numbered CONTENT list that
    # happens to sit under that heading, and nothing in it is a reference.
    cand = []
    for l in lines:
        if LIST_HEADINGS.match(l):
            inrefs = True
            cand = []
            continue
        if inrefs and re.match(r'^#{1,4}\s', l):
            inrefs = False
        if not inrefs:
            continue
        hit = _match_line(l)
        if hit:
            cand.append(hit)
    if not cand:
        return {}
    nums = [n for n, _ in cand]
    if nums != sorted(nums) or nums[0] != 1:
        return {}          # not a reference list; refuse to guess
    for n, t in cand:
        out.setdefault(n, t)
    return out


def inline_link_markers(text):
    """[[N]](url) occurrences -- the number is a dead label on a link that
    already carries its source, so it needs no reference list."""
    return INLINE_LINK.findall(text)


def key_for(reftext):
    """A short stable key from the reference's own text, so the footnote
    carries meaning rather than inheriting a position."""
    t = re.sub(r'\s+', ' ', reftext)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", t) if len(w) > 3]
    if not words:
        return 'ref'
    seen, out = set(), []
    for w in words[:6]:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) == 3:
            break
    return '-'.join(out) if out else 'ref'
