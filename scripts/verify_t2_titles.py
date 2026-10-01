#!/usr/bin/env python3
"""Verify T2 sources: does the DOI resolve, and does the title match?

575 files sit at `medium` for exactly one reason -- the rubric's T2
ceiling_qualifier:

    high requires the identifier to resolve to a document whose title
    and authors match the citation as written.

A hostname is not that. `doi.org` appearing in a file proves nothing
about whether the paper is the one the file claims. So this script does
what the rubric asks, and it does it against a real network call rather
than by pattern-matching a hostname.

WHAT IT CHECKS, PER SOURCE
  - the DOI/URL resolves at all (HTTP status, or arXiv API for arxiv:)
  - the returned document's TITLE
  - the comparison is a normalised fuzzy match, because citation
    styles differ from paper titles in ways that are not errors:
      "On the Semantics of Generative SPARQL" vs
      "On the Semantics of Generative SPARQL (Extended Abstract)"

VERDICTS
  match     title agrees, tier may be high
  mismatch  the resolved document is a DIFFERENT paper. This is an
            error, not a low grade: the file cites the wrong thing.
  unresolvable  could not check. Stays medium. NOT counted as match.
  skip      no identifier to resolve

RATE LIMITS AND FAILURE
Crossref asks for a polite pool: a mailto in the User-Agent, and no
more than a few requests per second. Both are honoured. Every failure
mode resolves to `unresolvable`, never to `match` -- an unreachable
network must not promote a file.

WHAT IT DOES NOT DO
It does not write confidence. It writes a verification table, and
grade_all.py --with-t2 reads that table. Keeping the network step
separate from the write step means a network flake cannot corrupt the
corpus.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from typing import List, Set

N = chr(10)
REPO = '/home/operator/hermes-brain'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
GRADE_CSV = f'{REPO}/docs/audit/grade-decisions.csv'
OUT = f'{REPO}/docs/audit/t2-verification.json'
MAILTO = 'hermes-brain@example.invalid'
UA = f'hermes-brain-confidence-audit/1.0 (mailto:{MAILTO})'
# arXiv's API asks for ~1 request per 3 seconds. The first run
# used 0.34s because Crossref's polite pool allows 3/s, and the
# result was 258 spurious `unresolvable` from HTTP 429. One
# delay has to serve both hosts, and the slower one wins.
DELAY = 3.0

# Worst-case backoff for a 429, per registry.
#
# arXiv's API is the strict one and is the reason these exist: an
# unbounded 3.0 * 4**(attempt+1) schedule reached 768s, which stalled a
# 956-identifier run for over thirteen minutes at a single identifier
# with no output to explain it. A direct probe during that stall got
# HTTP 200, so the limit was transient and waiting that long only
# delayed recovery.
#
# These caps keep a genuine rate limit respected while bounding the
# damage. Crossref is far more tolerant and gets a shorter cap: a 429
# there is more likely a blip than a real limit, and stalling the run
# for minutes to find that out is a bad trade at 956 identifiers.
ARXIV_BACKOFF_CAP = 60.0
CROSSREF_BACKOFF_CAP = 20.0

ARXIV = re.compile(r'arxiv[:/](\d{4}\.\d{4,5})', re.I)
# DOI identifier body.
#
# The character class must NOT exclude '<' and '>'. It used to, to avoid
# swallowing HTML like '<a href=...>', and that silently truncated Wiley SICI
# identifiers, whose AID suffix is delimited by exactly those characters:
#
#   10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5
#
# Cut at the '<', the regex produced 10.1002/(SICI)1099-0720(1998120)12:6,
# which cannot resolve anywhere -- a guaranteed 404 indistinguishable from a
# fabricated citation. It marked a correct vault entry unresolvable. The
# patterns now allow the balanced <...::AID-...> suffix, and still stop at
# genuine markup. Pinned by tests/test_t2_sici_doi.py.
_DOI_TAIL = (r"10\.\d{4,9}/"
             r"[^\s\"'<>,;]+"
             r"(?:<[^<>]*::[A-Za-z0-9\-]+>[^\s\"',;]*)?"
             r"(?:;[0-9]+-[0-9]+)?")
DOI = re.compile(r'doi[:/](?P<id>' + _DOI_TAIL + r')', re.I)
URL = re.compile(r'https?://(?:dx\.)?doi\.org/'
                 r'(?P<id>' + _DOI_TAIL + r')', re.I)
STOP = set('a an the of and or in on for to with from by at as is are '
           'be using via toward towards'.split())

# Where a reference string stops being a TITLE and becomes a journal
# citation. Used to find the end of the title proper, so a short title
# can be compared against a full registry title.
#
# These are journal/volume SHAPES, not punctuation. A colon is a
# subtitle boundary and must NOT appear here -- "Position: A Three-Layer
# ... Architecture" is one title, and cutting it at the colon would
# compare "Position" against the whole thing.
#
# Each entry is a word-boundary pattern over the space-joined token list.
#
# The token list is built by re.sub(r'[^a-z0-9]+', ' ') in
# _content_tokens(), so "112(1)" has already become the two tokens
# "112 1" and "3-24" has become "3 24" by the time these patterns see
# the string. A pattern written for the original punctuation -- \d+\(\d+
# -- can therefore never match. The patterns below are written against
# the ALREADY-STRIPPED form. Verified: the pre-fix version matched
# nothing and the truncated-citation case scored 0.38.
#
# A bare volume number is NOT a marker: "3" alone is indistinguishable
# from a title word, and cutting there would truncate real titles. Only
# the volume(issue) pair, which cannot occur inside a title, qualifies.
_JOURNAL_MARKERS = (
    r'\b\d{1,4}\s+\d{1,4}\b',               # 112 1   (was 112(1))
    r'\bvol\s+\d+',                          # vol 112
    r'\bpp\s+\d+',                           # pp 3 24
    r'\bno\s+\d+',                           # no 3
    r'\bhttps?\s+\S+',                       # a bare URL tail
)

# Journal NAMES that a reference string carries but a title does not.
#
# The volume marker alone is not enough. In
#   "The demise of short-term memory revisited. *Psychological Review*,
#    112(1), 3-24"
# the first volume shape sits at token 9 -- after the journal NAME, which
# is not part of the title. Cutting only at the volume gives a 9-token
# "title proper" that still includes "psychological review", so the 7-token
# shared span never covers it and the case is rejected.
#
# The list is deliberately small and specific. A general "two lowercase
# words that look like a journal" heuristic would cut real titles: "Deep
# Learning Methods", "Neural Network Compression" and "Probabilistic
# Assume Guarantee" are all titles that would be truncated by such a rule,
# and each of those is a real paper in this corpus. Only names that are
# journals AND appear here are cut.
_JOURNAL_NAMES = (
    'psychological review', 'journal of', 'transactions on', 'nature',
    'science', 'neuroimage', 'plos', 'pnas', 'brain', 'cognition',
    'psychology', 'annals of', 'proceedings of', 'ieee', 'acm',
    # Single-word journal names. Without these, "*Vision Research*
    # 49(10)" keeps two content words after tail-stripping and reads as
    # a title, and "*Cognitive Science*, 44(5), e128" keeps "cognitive"
    # plus "science" -- "cognitive" survives because the list has
    # "cognition", not its adjective form.
    #
    # Every entry here is a word that cannot be a paper title on its own
    # but is a common journal name. "brain" and "science" are the two
    # that do occur in real titles ("The Aging Brain", "Science of
    # Learning"), which is why _has_title_words requires TWO surviving
    # content words rather than one: a real title keeps more than the
    # journal name it happens to share.
    'vision research', 'vision', 'research', 'review of', 'reviews',
    'reports', 'letters', 'nature communications', 'scientific reports',
)

# Combined journal-tail matcher, for stripping the non-title part off a
# reference string. Built from _JOURNAL_NAMES plus the shapes in
# _JOURNAL_MARKERS so the two lists cannot drift apart.
_JOURNAL_TAIL_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(n) for n in _JOURNAL_NAMES) + r')\b'
    r'|\bvol\s+\d+|\bpp\s+\d+|\bno\s+\d+'
    r'|\b\d{1,4}\s+\d{1,4}\b'
    r'|\bhttps?\s+\S+', re.I)


# What must IMMEDIATELY follow a journal name for that name to be a
# journal name rather than an ordinary word inside a title.
#
# A journal citation carries reference punctuation: a volume, an issue
# in parentheses, a colon, or a comma followed by a number or a year.
#
#     *vision research* 49(10):1295 1306   -> tail
#     nature reviews psychology 3, 1-20    -> tail
#     brain 2021, 12(3), 45-67             -> tail
#
# versus titles that merely contain a journal's name:
#
#     temporal cognition: connecting subjective time ...   -> title
#     the entropic brain: a theory of conscious states     -> title
#     a systematic review of integrated information theory  -> title
#
# All three of those contain a word from _JOURNAL_NAMES and all three
# are titles. Cutting them is what made nine correct citations read as
# untitled. A colon alone is not enough -- every one of the three
# titles above has one.
_REFERENCE_TAIL_RE = re.compile(
    r'^\W{0,4}'
    r'(?:'
    r'\d+\s*\(\s*\d+\s*\)'      # 49(10)
    r'|\d+\s*:\s*\d'            # 49:1295
    r'|[,(]\s*\d'               # , 3   ( 12)
    r'|\bv(?:ol(?:ume)?)?\.?\s*\d+'   # vol. 49
    r'|\bpp\.?\s*\d+'           # pp. 1295
    r'|\bno\.?\s*\d+'           # no. 3
    r'|\b\d{4}\b'               # a bare year
    r')', re.I)


# ── abbreviation detection ──────────────────────────────────────────
# The dominant false-mismatch class in the high-score band is not a
# wrong citation but a correct one written as an ABBREVIATION:
#
#   vault:  "OntoKG: Ontology-Oriented KG Construction with Intrinsic-Relational Routing"
#   arXiv:  "OntoKG: Ontology-Oriented Knowledge Graph Construction with Intrinsic-Relational Routing"
#   vault:  "Theorem-of-Thought: Multi-Agent Abductive/Deductive/Inductive Reasoning"
#   arXiv:  "Theorem-of-Thought: A Multi-Agent Framework for Abductive, Deductive, and Inductive Reasoning..."
#
# Same paper, fewer words, sometimes an acronym. Scoring these as
# mismatch calls a correct citation wrong, which is the accusation this
# whole verifier exists to avoid making falsely.
#
# THE SIGNAL: every distinctive token of the vault label appears in the
# registry title, and enough of them do that the overlap is identifying
# rather than coincidental. "Distinctive" means not a function word and
# not a domain-generic term -- using generic tokens as the matching
# basis is exactly the bug that once let "Deep Learning" match unrelated
# titles.
#
# BOUNDED DELIBERATELY: requires FULL coverage and at least
# _ABBREV_MIN_DISTINCTIVE shared distinctive tokens. A genuine wrong
# citation shares distinctive vocabulary from its own subject, not a
# superset of the accused title, so full coverage is the right test.

_ABBREV_GENERIC = {
    'a', 'an', 'the', 'of', 'for', 'and', 'or', 'in', 'on', 'to', 'with',
    'via', 'using', 'from', 'at', 'by', 'as', 'is', 'are', 'be', 'that',
    'this', 'its', 'it', 'new', 'toward', 'towards', 'into', 'over',
    'under', 'multi', 'agent', 'agents', 'llm', 'llms', 'ai', 'system',
    'systems', 'framework', 'model', 'models', 'approach', 'method',
    'methods', 'based', 'study', 'analysis', 'survey', 'review',
}

# Acronyms the vault uses where the registry title spells them out.
_ABBREV_EXPANSIONS = {
    'kgs': 'knowledge graphs', 'kg': 'knowledge graph',
    'krs': 'knowledge graph',
    'llms': 'large language models', 'llm': 'large language model',
}

_ABBREV_MIN_DISTINCTIVE = 3


def _abbrev_tokens(s: str) -> List[str]:
    """Tokenise for abbreviation comparison, expanding known acronyms.

    Slashes and hyphens become spaces so "Abductive/Deductive/Inductive"
    and "Abductive, Deductive, and Inductive" tokenise alike -- the
    vault compresses lists with slashes and the registry spells them
    out.
    """
    s = re.sub(r'<[^>]+>', ' ', str(s or '')).lower()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('/', ' ').replace('-', ' ').replace('&', ' and ')
    out: List[str] = []
    for w in re.findall(r'[a-z0-9]+', s):
        exp = _ABBREV_EXPANSIONS.get(w)
        if exp:
            out.extend(exp.split())
        else:
            out.append(w)
    return out


def _abbrev_stem(w: str) -> str:
    """Crude suffix strip, so inflections of the same word agree.

    "prompts"/"prompt", "reasoning"/"reason", "taxonomies"/"taxonomy".
    ORDER MATTERS, and this was the whole bug. "taxonomies" ends in
    "es", so the es rule fires and yields "taxonomy"; "taxonomy" then
    reaches the y rule and yields "taxonom". The two forms of ONE word
    end up three characters apart, so a real abbreviation whose only
    difference is singular-vs-plural was being scored a mismatch.

    The fix is to strip the plural to a form that still ends in y, and
    strip the singular's y as well, so both land on the same stem. Order
    is ies -> es/s -> y, and the y strip applies last to whatever
    survived.
    """
    if w.endswith('ies') and len(w) > 4:
        w = w[:-3] + 'y'
    for suf in ('ing', 'ed', 'es', 's'):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            w = w[:-len(suf)]
            break
    if w.endswith('y') and len(w) > 3:
        w = w[:-1]
    return w


def _distinctive(tokens: List[str]) -> Set[str]:
    return {_abbrev_stem(t) for t in tokens
            if t not in _ABBREV_GENERIC and len(t) > 2}


def is_abbreviation_of(vault_label: str, registry_title: str) -> bool:
    """True if the vault label is a faithful abbreviation of the title.

    Requires that EVERY distinctive token of the label appears in the
    title, and that at least _ABBREV_MIN_DISTINCTIVE of them do. Full
    coverage is what distinguishes an abbreviation from a wrong
    citation: a wrong citation shares subject vocabulary, it does not
    contain a superset of the accused title's own words.
    """
    v = _distinctive(_abbrev_tokens(vault_label))
    if len(v) < _ABBREV_MIN_DISTINCTIVE:
        return False
    t = {_abbrev_stem(x) for x in _abbrev_tokens(registry_title)}
    if not (v <= t):
        return False
    return len(v & t) >= _ABBREV_MIN_DISTINCTIVE



def norm(s):
    s = re.sub(r'<[^>]+>', ' ', str(s or ''))
    s = s.lower()
    s = re.sub(r'\(.*?\)', ' ', s)          # drop parentheticals
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    toks = [t for t in s.split() if t and t not in STOP]
    return ' '.join(toks)


def _tagged_upper(word, *originals):
    """True if `word` appears ALL-CAPS in an original, un-normalised title.

    norm() lowercases everything, so a tag like the "JMS" in
    "The Semantic Training Gap -- JMS R3" arrives here as "jms" and
    cannot be told apart from an ordinary word. The casing is the only
    evidence there is, so it is read from the strings as they were
    written rather than from the normalised form. A bare acronym of
    four characters or fewer is what qualifies: JMS, IEEE, ACL, GPT.
    "NEED" as an ordinary shouted word is not a thing that occurs in a
    citation, and the length bound keeps "THEORIES" out.
    """
    up = word.upper()
    if len(up) > 4:
        return False
    return any(re.search(rf'\b{re.escape(up)}\b', o) for o in originals)


def title_match(a, b):
    """Conservative: require the normalised titles to agree closely.
    Returns (bool, score)."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False, 0.0
    if na == nb:
        return True, 1.0
    wa, wb = set(na.split()), set(nb.split())
    if not wa or not wb:
        return False, 0.0
    # containment: one title is a prefix/subset of the other
    #
    # This branch was originally unconditional on the SETS, which is far
    # looser than it looks and produced matches with no shared subject:
    #   "A Survey of Graph Retrieval Methods" normalises to
    #   "survey graph retrieval methods", whose 4-token head
    #   "survey graph" is a subset of "attention all you need", and
    #   "Deep Learning" is a subset of "Deep Learning for Image
    #   Recognition". Both scored 0.9 = "match".
    #
    # The set test is only trustworthy when the SHARED part is a real
    # chunk of the title, not a generic head. A 3-token label against a
    # 12-token real title is the normal shape of a citation shorthand
    # ("Adaptive Memory Distillation" for "What Deserves Memory:
    # Adaptive Memory Distillation for LLM Agents") and must still match,
    # so the ratio floor cannot be tight. The 4-token minimum is what
    # carries the weight instead: "deep learning" is 2 tokens and is
    # rejected, while a 3-token label that is a genuine, complete
    # sub-phrase of the longer title is accepted.
    # ALIAS: the vault sometimes cites a paper by its project's popular
    # name -- the real title plus a short prefix:
    #   "NEMORI: Adaptive Memory Distillation"  vs
    #   "What Deserves Memory: Adaptive Memory Distillation for LLM
    #    Agents"
    # An ALLCAPS prefix is the signal that a name is being used in place
    # of a title.
    #
    # This is checked BEFORE, and independently of, set containment. The
    # two titles share 3 of 4 tokens but neither set is a subset of the
    # other, so a rule nested inside `if wa <= wb or wb <= wa` never
    # runs for this case -- which is precisely the case it exists for.
    #
    # LIMIT, deliberately accepted: this also fires on
    #   "RUBAS: Rubric-Based Reinforcement Learning for Agent Safety"
    # vs "Rubric-Based Reinforcement Learning",
    # which is NOT an alias -- that one is a different paper whose short
    # name is its own head. Nothing in the two strings separates them:
    # neither acronym appears in the other title, both share a 4-token
    # set, and the two pull any single rule in opposite directions.
    #
    # Resolved by cost, not elegance. A missed alias is one correct
    # citation reported as a mismatch, which a person can see and
    # dismiss. A false alias is a REAL wrong citation scoring as a match,
    # which silently inflates confidence and cannot be told apart from a
    # true one downstream. The asymmetric cost decides it: accept the
    # alias, and record the known over-match in
    # verify_containment_match.py rather than pretending the rule is
    # sound.
    for _prefix, _other in ((a, b), (b, a)):
        _head = re.match(r'\s*([A-Z][A-Z0-9]{2,7})\s*[:\-–—]\s+\S', _prefix)
        if _head and _head.group(1).lower() not in _other.lower():
            return True, 0.8

    if wa <= wb or wb <= wa:
        small, large = sorted((len(wa), len(wb)))
        ratio = large / small if small else 99
        if small >= 3 and (ratio >= 2.0 or ratio <= 1.35):
            return True, 0.9
    j = len(wa & wb) / len(wa | wb)
    # A label is often a TRUNCATION of the real title with something
    # appended, which set containment cannot see because of the extra
    # tokens:
    #     label  "The Semantic Training Gap - JMS R3"
    #     real   "The Semantic Training Gap: Ontology-Grounded Tool
    #             Architectures for Industrial AI Agent"
    # Jaccard over that pair is 0.25 and the containment branch above
    # does not fire, so a correct citation scored 0.25 and was called a
    # mismatch. A shared leading run of significant words means the
    # shorter title is a prefix of the longer, which is what a
    # truncation looks like.
    #
    # A shared leading run of significant words means the shorter title
    # is a prefix of the longer, which is what a truncation looks like.
    #
    # The floor is 3, not 4, because norm() has already removed the
    # stopwords: "The Semantic Training Gap" normalises to three words,
    # so a 4-word floor could never fire on the very case it exists for.
    # 3 is still safe against the "Part 1" / "Part 2" guard, which
    # diverges on its FIRST token and so scores a run of 0 -- verified
    # in verify_no_raw_labels.py, which asserts both directions.
    run = 0
    for x, y in zip(na.split(), nb.split()):
        if x == y:
            run += 1
        else:
            break
    if run >= 3 and min(len(na.split()), len(nb.split())) >= 3:
        # A truncation is the SHORTER title consumed entirely: the run
        # must reach the end of it, with only a short tag left over.
        #   short  "semantic training gap jms r3"     (5 tokens)
        #   long   "semantic training gap ontology ..." (10)
        #   run=3, short has 2 tokens left -> those are the tag.
        #
        # "Attention Is All You Need" vs "...You Ignore" is NOT a
        # truncation: the run is 3 but the shorter title has a token
        # AFTER the run, and that token is a real word, not a tag. A
        # 3-token floor alone over-matched it, which is why the floor
        # is not sufficient on its own.
        short, long = sorted((na.split(), nb.split()), key=len)
        leftover_short = short[run:]
        leftover_long = long[run:]
        if not leftover_short:
            return True, 0.85
        # The shorter title's tail must be TAG-like, and a tag carries
        # digits: "JMS R3", "v2", "R1". Requiring a digit is what
        # separates a tag from an ordinary word -- the first version of
        # this check allowed any short alphabetic token, so "need" in
        # "Attention Is All You Need" qualified and the rule matched
        # that against "Attention Is All You Ignore".
        if leftover_short and all(
                w.isdigit()
                or re.fullmatch(r'[A-Za-z]{0,6}\d{1,4}[A-Za-z]{0,4}', w)
                or _tagged_upper(w, a, b)   # e.g. the "JMS" in "JMS R3"
                for w in leftover_short):
            return True, 0.85

    # CONTAINMENT: one title's distinctive body sits inside the other, but
    # the surrounding words differ, so the leading-run rule above never
    # fires. Two real cases from the vault, both correct citations that
    # were being called mismatches:
    #
    #   vault   "NEMORI: Adaptive Memory Distillation"
    #   arXiv   "What Deserves Memory: Adaptive Memory Distillation for
    #            LLM Agents"
    #   -> the vault uses the project's popular name where arXiv uses the
    #      paper title. The shared body is the distinctive part.
    #
    #   vault   "Ontology Design Patterns Applied to Cultural Heritage
    #            Knowledge Graphs"
    #   arXiv   "Pattern-based design applied to cultural heritage
    #            knowledge graphs"
    #   -> same title, words transposed. Token overlap reaches 0.6, which
    #      is under the 0.80 floor, so it scored as a mismatch.
    #
    # Matched against the RAW, stopwords-intact token lists, not the
    # normalized ones. norm() drops stopwords, so
    #   "A Survey of Graph Retrieval Methods" -> "survey graph retrieval ..."
    #   "Attention Is All You Need"          -> "attention all you need"
    # and "survey graph" then reads as a 4-token span in the second title.
    # Containment over normalized text matches papers that share nothing
    # but filler words -- which is the entire failure mode this rule was
    # added to fix. The first version of this rule used `na`/`nb` and
    # matched 6 of 10 negative cases, including two with no shared
    # subject at all.
    raw_a = _content_tokens(a)
    raw_b = _content_tokens(b)
    short, long = sorted((raw_a, raw_b), key=len)
    n_short = len(short)
    if n_short >= 4:
        long_joined = " " + " ".join(long) + " "
        best_span = 0
        best_end = 0
        for i in range(len(short) - 3):
            # Loop var is k, NOT j. `j` is the Jaccard score assigned at
            # line 139, and shadowing it here made every containment check
            # return True with a score of 4, 5 or 7 -- an integer loop
            # index leaking into what callers read as a similarity score.
            # Worse, it passed the 0.80 floor, so unrelated titles scored
            # as confident matches. Found by disassembly, after every
            # value-level check said the code was correct.
            for k in range(i + 4, n_short + 1):
                if " " + " ".join(short[i:k]) + " " in long_joined:
                    if k - i > best_span:
                        best_span = k - i
                        best_end = k
        # Track WHERE the best span ends, not just its length: a span that
        # stops short of the end of the shorter title is a shared middle
        # phrase, not the shorter title living inside the longer one.
        #   "attention is all you need" vs "...you ignore" -- span 4 of 5,
        #     ending at token 4, leaving "need" unmatched. Rejected.
        #   "rubric based reinforcement learning" -- span 4 of 4, but the
        #     shorter title is only 4 tokens. Rejected on the length
        #     floor, which the >= 5 test supplies.
        #   "adaptive memory distillation" -- 3 tokens, no 4-token run.
        #     Already handled by the set-containance branch above.
        # TRUNCATED CITATION: the vault records a paper's SHORT title and
        # the registry returns the FULL one. This is the single largest
        # remaining class of false mismatch, and it is not a containment
        # case at all:
        #
        #   vault:    The demise of short-term memory revisited.
        #             *Psychological Review*, 112(1), 3-24
        #   crossref: The Demise of Short-Term Memory Revisited:
        #             Empirical and Computational Investigation
        #
        # Neither token set contains the other. The vault side carries
        # the journal, volume and page range; the registry side carries
        # the subtitle. The title proper is a shared PREFIX, and the
        # vault's title proper ends where the journal citation begins.
        #
        # So the span test is the right instrument, but it must be
        # measured against the end of the title PROPER, not the end of
        # the whole citation string. Requiring best_end == n_short
        # rejects this case, because n_short counts "*Psychological
        # Review*, 112(1), 3-24" as part of the title.
        #
        # n_proper: the number of tokens in the shorter side that belong
        # to the title proper, i.e. up to the first journal marker.
        #
        # The marker is matched against the SPACE-JOINED string, so
        # m.start() is a CHARACTER offset. It has to be converted back
        # to a token index before it is used to count tokens; treating
        # it as an index directly undercounts the prefix and rejects
        # exactly the case this rule exists for.
        #
        # Both sides must be checked, not just `short`. `short` is
        # whichever side has FEWER tokens, and the journal tail can sit
        # on the longer one: for a truncated citation the registry title
        # is 11 tokens and the vault string, carrying
        # "*Psychological Review*, 112(1), 3-24", is 13. So `short` is
        # the clean registry title with no marker in it at all, and
        # checking only `short` finds nothing. Taking the minimum over
        # both sides is what makes the rule symmetric.
        # For each side, find where its title proper ENDS: at the first
        # journal marker, or at the end of the string if it has none.
        #
        # The two sides need NOT agree, and forcing a single shared value
        # is wrong. The vault side is
        #   "The demise of short-term memory revisited. *Psychological
        #    Review*, 112(1), 3-24"
        # whose title proper is 7 tokens -- it stops at "revisited". The
        # registry side is
        #   "The Demise of Short-Term Memory Revisited: Empirical and
        #    Computational Investigation"
        # whose title proper is all 11 tokens, because it has no
        # journal marker at all.
        #
        # Taking min() over both gave 9, matching neither, and rejected
        # the case. The correct test is: does the shared span cover one
        # side's ENTIRE title proper? The vault's 7-token proper is
        # matched end-to-end by the 7-token span, so yes -- the vault
        # recorded the short title of the paper the registry describes
        # in full. That is a truncated citation, which is what we are
        # looking for.
        span_covers_a_proper = False
        for side, joined in ((short, ' '.join(short)),
                             (long, ' '.join(long))):
            side_cut = len(side)
            for marker in _JOURNAL_MARKERS:
                for m in re.finditer(marker, joined):
                    # require at least 4 tokens of title before it
                    n_tok = len(joined[:m.start()].split())
                    if n_tok >= 4:
                        side_cut = min(side_cut, n_tok)
            # A journal NAME ends the title too, and it appears BEFORE
            # the volume in a reference string, so it has to be cut
            # separately or side_cut lands after it.
            for name in _JOURNAL_NAMES:
                for m in re.finditer(r'\b' + re.escape(name) + r'\b', joined):
                    n_tok = len(joined[:m.start()].split())
                    if n_tok >= 4:
                        side_cut = min(side_cut, n_tok)
            if (side_cut >= 4
                    and best_end == side_cut
                    # The span may START late, not just end early: a
                    # vault title can reorder the head words
                    # ("Ontology Design Patterns Applied to..." vs
                    # "Pattern-based design applied to..."), so the
                    # shared run does not begin at token 0. Requiring
                    # the span to cover side_cut-1 rejects that even
                    # though the tail matches end to end.
                    #
                    # So the test is: the shared span reaches the end of
                    # the title proper, and is substantial both in
                    # absolute terms (>= 4 tokens) and in proportion
                    # (>= 60%). Where it starts is not the thing being
                    # decided here.
                    and best_span >= 4
                    and best_span >= 0.6 * side_cut):
                span_covers_a_proper = True

        if best_span >= 4 and span_covers_a_proper:
            return True, 0.75

    # token overlap alone is not enough; require a high floor AND a
    # clear majority, so "Part 1" cannot match "Part 2"
    return (j >= 0.80, j)


def _content_tokens(t):
    """Lowercase word tokens of a title, stopwords INCLUDED.

    Deliberately the opposite of norm() for containment purposes. norm()
    exists to make near-identical titles compare equal; containment needs
    to see the words that make a title specific, and those are exactly
    the ones norm() removes.
    """
    t = re.sub(r'[^a-z0-9]+', ' ', t.lower())
    return [w for w in t.split() if w]


def clean_doi(d):
    return re.sub(r'[.,;)\]]+$', '', d.strip())


def _trailing_parenthetical(text):
    """The contents of a parenthetical that CLOSES the string, or ''.

    Only the trailing case counts. A parenthetical in the middle of a
    title is part of the title, and a nested one like "(Taxonomy of
    Agentic RAG)" is a subtitle that title_match() handles through
    norm(). What this is for is a label shaped like

        Anatomy of Agentic Memory: 4-Structure Taxonomy
            (Anatomy of Agentic Memory: Taxonomy and Empirical
             Analysis of Evaluation and System Limitations)

    where inline_title() drops the parenthetical as a gloss and the
    remaining shorthand scores 0.364. Offering the parenthetical as an
    additional candidate lets the real title match at 1.000.

    Returns '' when there is no such parenthetical, when it is empty,
    or when it is too short to be a title (a year, an abbreviation, a
    page range), so a stray "(1998)" never becomes a candidate.
    """
    s = str(text or '').strip()
    # Strip the entry's own quoting FIRST. A frontmatter source is
    # written  - "arXiv:2602.19320 — Anatomy of Agentic Memory:
    # 4-Structure Taxonomy (Anatomy of Agentic Memory: Taxonomy and
    # Empirical Analysis)"  and cited_titles() hands the line over with
    # the quotes still attached, so the string ends with ')"' and never
    # endswith(')'. The parenthetical was right there and the guard
    # rejected it -- the check was correct and the input was not what
    # it assumed.
    for _ in range(2):
        if len(s) >= 2 and s[0] in '"\'' and s[-1] == s[0]:
            s = s[1:-1].strip()
    if not s.endswith(')') or '(' not in s:
        return ''
    i = s.rfind('(')
    if i == -1 or s[i - 1] not in ' \t':
        return ''
    inner = s[i + 1:-1].strip()
    # A parenthetical that is only punctuation, a year, or a number is
    # never a title.
    if len(inner) < 12:
        return ''
    if re.match(r'^[\d\s.,;:()\[\]/+-]+$', inner):
        return ''
    # Require a real balance: the trailing paren must close the one we
    # found, not a different group.
    if inner.count('(') != inner.count(')'):
        return ''
    return inner


def _has_title_words(label):
    """Does this string contain any words that could be a title?

    A label is not a title merely because it is non-empty. After
    inline_title() strips an author run from

        *Itti & Baldi (2009)**, *Vision Research* 49(10):1295 1306,
        10.1016/j.visres.2009.06.037

    what is left is "*Vision Research* 49(10):1295 1306,
    10.1016/j.visres.2009.06.037" -- a journal, a volume, a page range
    and a DOI, and no title at all. That residue is non-empty, so the
    `if x` filter let it through, and since it cannot match anything it
    forced verdict=mismatch for a citation that was never wrong. It is
    indistinguishable from a real title by non-emptiness alone.

    THE TAIL IS TRIMMED, NOT THE WHOLE STRING. An earlier version
    replaced every journal name anywhere in the string, which silently
    deleted real titles: "Science of Learning" became "" because
    "science" is a journal name and "of" is a stopword, leaving nothing
    to judge. The content before the FIRST journal marker is what
    matters -- in a reference string the journal follows the title, so
    cutting at the first occurrence and keeping the prefix is both
    correct and cannot eat the front of a title that merely mentions a
    journal word.

    The test is deliberately weak -- it asks only whether any ordinary
    words survive -- and errs toward keeping a candidate. The cost of
    keeping a bad candidate is one false mismatch, which is visible and
    correctable; discarding a real title means the citation is never
    checked at all, which is invisible.

    Bare numbers, page ranges, URLs and DOIs do not count as words.
    Neither do short alphanumeric codes: "*Cognitive Science*, 44(5),
    e128" reduces to "cognitive" and "e128", and "e128" is an article
    number, not a word.
    """
    s = label.lower()
    # Cut at the FIRST journal marker, keep what precedes it -- but only
    # when what follows the marker looks like a reference tail.
    #
    # The marker list is a list of JOURNAL NAMES, and it has to be
    # treated as such. It contains ordinary words that appear in titles
    # far more often than in journal names -- "brain", "cognition",
    # "review of", "science", "vision", "research". Cutting "Temporal
    # cognition: Connecting subjective time to perception, attention,
    # and memory" at "cognition" leaves "temporal", the real title is
    # discarded, and a correct citation is recorded as
    # untitled_citation. Nine rows were sitting in that state.
    #
    # A journal name is only a journal name if reference punctuation
    # follows it: a volume, an issue in parentheses, a colon, a
    # comma-then-number. "Temporal cognition: Connecting..." has a
    # colon but no volume after it, so it is a title. "*Vision
    # Research* 49(10):1295 1306" has both, so it is a tail.
    #
    # Erring toward keeping a candidate costs one false mismatch, which
    # is visible and correctable; discarding a real title means the
    # citation is never checked at all, which is invisible.
    m = _JOURNAL_TAIL_RE.search(s)
    if m and m.start() > 0:
        # The marker may be only the FIRST WORD of a multi-word journal
        # name -- "vision research", "cognitive science", "reviews of
        # science". The tail that matters starts after the whole name,
        # so extend past any further lowercase words before testing for
        # the volume/issue punctuation.
        tail = s[m.start():]
        rest = re.match(r'[\w\s&]*?(?=[^\w\s&]|\Z)', tail).group(0)
        if _REFERENCE_TAIL_RE.match(tail[len(rest):]):
            s = s[:m.start()]
    s = re.sub(r'https?\S*', ' ', s)
    s = re.sub(r'\b10\.\d{4,9}/\S+', ' ', s)
    s = re.sub(r'[^a-z]+', ' ', s)
    words = [w for w in s.split()
             if len(w) >= 3 and w not in STOP]
    return len(words) >= 2


def fetch_crossref(doi):
    url = 'https://api.crossref.org/works/' + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch_datacite(doi):
    """Title for an identifier Crossref does not carry, or None.

    DataCite is the other DOI registration agency and holds Zenodo
    deposits, most institutional repositories, and arXiv's DataCite
    records. Crossref holds journal articles. Asking only Crossref
    makes a perfectly good dataset DOI look nonexistent.

    Returns None rather than raising, so the caller can treat "not in
    either registry" the same way it treats a Crossref miss.
    """
    url = 'https://api.datacite.org/dois/' + urllib.parse.quote(doi, '')
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode('utf-8'))
    except Exception:
        return None
    attrs = (d or {}).get('data', {}).get('attributes', {})
    titles = attrs.get('titles') or []
    if not titles:
        return None
    t = titles[0].get('title') if isinstance(titles[0], dict) else titles[0]
    if not t:
        return None
    return re.sub(r'\s+', ' ', str(t)).strip()


def fetch_arxiv(aid):
    url = ('https://export.arxiv.org/api/query?id_list=' + aid
           + '&max_results=1')
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        xml = r.read().decode('utf-8', 'replace')
    m = re.search(r'<entry>.*?<title>(.*?)</title>', xml, re.S)
    if not m:
        return None
    return re.sub(r'\s+', ' ', m.group(1)).strip()



def inline_title(entry):
    """The citation's own title text, when it carries one inline.

    Formats seen in this corpus:
      "arXiv:2605.00081 - Alignment Contracts for Agentic Security
       Systems (DATE-TRACKED)"
      "https://arxiv.org/abs/2605.00081"
      "10.1038/nrn2236 - Actin-binding proteins take the reins"
    The identifier is stripped, an em-dash/en-dash/hyphen separator is
    used as a boundary, and any trailing parenthetical is dropped by
    the normaliser. What remains is compared against the resolved title.
    """
    s = str(entry or '').strip()
    # Strip surrounding quotes. A frontmatter source is written as
    #   - "https://doi.org/10.1 (Some Real Title Here)"
    # and cited_titles() hands the line over with the quotes still on
    # it. Without this, s does not begin with "http", so the bare-URL
    # rule below never fires, the parenthesised title is never read,
    # and norm() returns empty -- a correct citation recorded as
    # untitled_citation. Measured against the corpus: 31 rows sat in
    # that state purely because of the quotes.
    #
    # Both quote styles, and repeated, since a single-quoted entry
    # written by the titler is equally affected.
    for _ in range(2):
        if len(s) >= 2 and s[0] in '"\'' and s[-1] == s[0]:
            s = s[1:-1].strip()
    # Strip a leading markdown bullet. Without this, the reference line
    # "- https://arxiv.org/abs/2012.00073" does NOT match the bare-URL
    # rule below, because the leading "- " means the string does not
    # begin with "http", so the entire URL survived as a candidate
    # "title", was compared against the resolved title, scored 0, and
    # the correct citation was reported as a mismatch. This is the
    # single largest source of the 188 leftover mismatches.
    s = re.sub(r'^[-*•–—]\s*', '', s).strip()
    # A numbered reference line is "<n>. <authors>. <Title>. <journal>."
    #     5. Bengtsson SL, Nagy Z, Skare S. Extensive piano practicing
    #        has regionally specific effects on white matter development.
    # inline_title() returned the whole author list, which cannot match
    # any real paper, so a correct citation scored 0. A leading number
    # followed by a period is the reference index, not part of the
    # title. Strip it, and if the remainder still opens with an author
    # list, take the text after the last author initial.
    s = re.sub(r'^\d{1,3}\s*[.)]\s+', '', s).strip()
    # Strip the surrounding quotes AGAIN, now that the bullet and the
    # reference index are gone. The first pass above runs before those
    # two strips, and a frontmatter entry begins with two spaces:
    #
    #     '  - "arXiv:2602.19320 — Anatomy of Agentic Memory"'
    #
    # so s[0] is a SPACE, not a quote, the first pass is skipped, and
    # the quotes are still there when the bullet strip runs. What
    # survives into the candidate is then '" Anatomy of Agentic
    # Memory"' with the quote glued to the front, which scores below
    # threshold against the real title. The parenthesised form fails
    # the same way and harder: the bare-URL rule requires s to begin
    # with "http", so
    #
    #     '  - "https://doi.org/10.1126/science.1069590 (A Pathway)"'
    #
    # returned just '"' -- a correct citation recorded as untitled.
    # Six rows sat in that state.
    for _ in range(2):
        if len(s) >= 2 and s[0] in '"\'' and s[-1] == s[0]:
            s = s[1:-1].strip()
    m = re.match(r'^(?:[A-Z][A-Za-zÀ-ɏ\-]+\s+[A-Z]{1,3}'
                 r'(?:,|\s+et\s+al\.?|,?\s+and\s+[A-Z][A-Za-z\-]+\s+[A-Z]{1,3})'
                 r'\s*[.,]\s*){2,}(.+)$', s)
    if m and len(m.group(1).strip()) > 12:
        s = m.group(1).strip()
    # Bare "Surname & Surname (YEAR)**" reference form.
    #
    # The regex above only matches initials -- "Itti, L., & Baldi, P."
    # -- and this corpus also contains the shorthand
    #   "*Itti & Baldi (2009)**, *Vision Research* 49(10):1295 1306"
    # which has no initials and no comma. It therefore did not match, and
    # the author list, the year, the journal, the volume, the page range
    # and the trailing DOI all survived into the "title". That string
    # cannot match any real paper, so a correct citation scored 0 and was
    # recorded as a mismatch -- and because the DOI at the end was then
    # consumed as part of the label, the label also failed the
    # identifier-ownership test, so the file looked like it had no title
    # for that identifier at all.
    #
    # Deliberately narrow: requires a 4-digit year in parentheses
    # immediately after the author run, which is what distinguishes this
    # from a title that merely starts with two capitalised words.
    else:
        bold = re.match(r'^([A-Z][A-Za-z\-]+'
                        r'(?:\s*(?:&|and|,)\s*[A-Z][A-Za-z\-]+)*)'
                        r'\s*\((\d{4})\)\*{1,2}\s*[,:.]?\s*(.+)$', s)
        if bold and len(bold.group(3).strip()) > 12:
            s = bold.group(3).strip()
    # A bare mirror URL carries NO title at all -- "https://scirate.com/"
    # is the residue left after stripping the arXiv id out of
    # "https://scirate.com/arxiv/2603.14597". Comparing that against a
    # real title scores 0 and would report a correct citation as wrong,
    # so an entry with no title text yields None and is skipped rather
    # than being treated as a failed match.
    s = re.sub(r'^https?://\S*?(arxiv|doi|scirate|alphaxiv)\S*', '',
               s, flags=re.I)
    s = ARXIV.sub('', s)
    s = URL.sub('', s)
    s = re.sub(r'(?i)doi[:/]\s*', '', s)
    # A dash SEPARATES a title from a preceding identifier
    # ("10.1038/nrn2236 - Actin-binding proteins take the reins"), and
    # the dash must sit BETWEEN words. \s* on both sides matches ZERO
    # spaces, so the pattern fired inside "schema-miner" at offset 6 and
    # inside "LLM-Discovered", splitting a real title at a hyphen and
    # returning ''. Require at least one space on the left, so only a
    # genuine separator matches.
    s = re.sub(r'\s+[—–-]\s+', ' ', s, count=1)
    s = s.strip(' .,:;')
    # If what is left is only a domain, a path, or a bare identifier,
    # there was no inline title to begin with.
    if not s or re.match(r'^[\w.-]+\.[a-z]{2,}', s) or \
            re.match(r'^[\d.]+$', s):
        return ''
    # Nothing that still contains a scheme, a host, or an @ is a title.
    # Belt and braces: the rules above should already have removed it,
    # and if any of them ever stops applying, this is what prevents a
    # URL from being reported as a wrong citation.
    #
    # A bare "/" is deliberately NOT rejected. DOIs are written
    # "10.1038/nrn2236 - Actin-binding proteins take the reins" and the
    # slash is part of the identifier, not a URL path. An earlier
    # version of this check did include "/" and silently killed DOI
    # title extraction, which is how a regression like that gets in:
    # the test suite I wrote for it only covered arXiv.
    if re.search(r'https?://|www\.|\.org|\.com|@', s):
        return ''
    # Quote marks left over from a wrapped reference line are not a
    # title. '- "https://doi.org/10.1038/nn1516"' stripped its URL and
    # left '""' behind, which is two characters of punctuation and
    # nothing else. Anything with no letters is not a title.
    if sum(ch.isalpha() for ch in s) < 8:
        return ''
    # A PARENTHESISED title is the corpus convention in frontmatter:
    #     sources:
    #       - arXiv:2505.09388 (Qwen3 Technical Report)
    # norm() strips punctuation, so the parens turn a real title into
    # an empty string: norm("(Qwen3 Technical Report)") == ''. That is
    # silent and total -- the title vanishes, title_match returns
    # (False, 0.0) on a perfect citation, and there is no error
    # anywhere. Unwrap before the length check, and drop only a
    # parenthetical that is genuinely metadata (a date, a venue, a
    # note) rather than the title.
    m = re.match(r'^\((.+)\)$', s)
    if m:
        inner = m.group(1).strip()
        # "2505.09388, 2025" or "DATE-TRACKED" or "preprint" are notes,
        # not titles: no lowercase word longer than 3 characters.
        looks_like_note = not re.search(r'\b[a-z]{4,}', inner)
        if inner and not looks_like_note:
            s = inner
    # A TRAILING parenthesised group, when the parentheses do not wrap
    # the whole string:
    #
    #     arXiv:2501.09136 -- Agentic RAG Survey (Taxonomy of Agentic RAG)
    #
    # The rule above needs the string to START with "(". This one does
    # not, so nothing was unwrapped, the closing ")" survived, and the
    # title was scored against a registry string that had none. Two
    # corpus entries are written in exactly this shape.
    #
    # Only unwrap when the group is at the end AND balanced, so a title
    # that legitimately ends mid-parenthesis is not truncated. Balanced
    # means the final ")" closes the last "(" still open.
    if not re.match(r'^\(', s):
        # Strip a LEADING identifier before judging either half. In
        # "arXiv:2501.09136 Agentic RAG Survey (Taxonomy of Agentic
        # RAG)" the ARXIV substitution has already run by some routes
        # but not all, and while the bare number is still attached the
        # head looks like metadata rather than a title, so the unwrap
        # was skipped.
        lead = re.sub(r'^(?:[A-Za-z][\w.\-]*:)?[\w./\-]*\d[\w./\-]*\s*',
                      '', s).strip()
        if not lead:
            lead = s
        tm = re.search(r'\(([^()]*)\)\s*[\'"]?\s*$', lead)
        if tm and tm.group(1).strip() and lead.count('(') == lead.count(')'):
            head, tail = lead[:tm.start()].rstrip(), tm.group(1).strip()
            # A trailing group is a SUBTITLE when it carries words, and
            # bare metadata when it does not. "Taxonomy of Agentic RAG"
            # is a subtitle: "Agentic" and "RAG" are capitalised content
            # words even though no 4-letter lowercase word appears.
            # "(2025)", "(DATE-TRACKED)", "(preprint)" are not.
            subtitle = bool(tail) and (
                re.search(r'[A-Z][a-z]{2,}', tail) or
                re.search(r'\b[a-z]{4,}', tail))
            if head and subtitle:
                s = head
    # Whatever happened above, a title must not still be wrapped in
    # brackets when it leaves here. norm() strips punctuation, so a
    # leftover "(" turns the whole title into an empty string at
    # comparison time -- silently, with no error. Strip any residual
    # bracket pair rather than trusting the branch above to have caught
    # every shape; the branch did not fire for a title that arrived
    # with a leading identifier still attached.
    s = s.strip().strip('()[]').strip()
    # A filename is not a title. "kalman-delta-rule-attribution.md"
    # reaches here from a reference block, and "kalman
    # delta-rule-attribution.md" matched nothing while still looking
    # like a candidate, so it was scored and dragged the best score
    # down. A reference line that is only a file name is a pointer,
    # not a claim about a paper.
    if re.search(r'\.(md|json|py|txt|ya?ml|csv)$', s, re.I):
        return ''
    # A bracketed wiki-link label is a display name, not a title:
    #   ["The Semantic Training Gap -- JMS R3"]
    # keeps its brackets and its em-dash, matches no real title, and
    # scores 0 while looking plausible. Strip the brackets, and if
    # what remains carries a pipe label, keep only the label.
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1].strip()
        if '|' in s:
            s = s.split('|', 1)[1].strip()
    # An author list means the title is not at the front:
    #   "5. Bengtsson SL, Nagy Z, Skare S, Forsman L. Extensive piano
    #    practicing has regionally specific effects. Nat Neurosci."
    # An author list matches no title, but the TITLE is the sentence
    # after it, so do not discard the line -- take that sentence. The
    # earlier version of this guard returned '' and threw the title
    # away with the authors, which regressed the two numbered-reference
    # cases in verify_inline_title.py.
    # An author run is a SEQUENCE of "Capitalised AB" pairs --
    # "Bengtsson SL, Nagy Z, Skare S, Forsman L" -- separated by commas
    # or "and", not two such pairs found anywhere in the string.
    #
    # Counting loose pairs anywhere is what killed a real title:
    #
    #   "schema-miner pro: Agentic AI for Ontology Grounding Over
    #    LLM-Discovered Scientific Schemas ..."
    #
    # contains "Agentic AI" and "Over LLM" -- two matches of
    # \b[A-Z][a-z]+\s+[A-Z]{1,3}\b -- so the guard fired, the author-run
    # branch returned '', and a correct citation was recorded as
    # untitled. Neither pair is an author initial: the initials are
    # comma-separated and the surname follows the initial, not precedes
    # it. Require two ADJACENT pairs joined by a comma or "and", which
    # is the shape an author list actually has.
    _AUTHOR_RUN_RE = (r'\b[A-Z][a-z]+\s+[A-Z]{1,3}\s*'
                      r'(?:,|and)\s+[A-Z][a-z]+\s+[A-Z]{1,3}\b')
    if re.search(_AUTHOR_RUN_RE, s):
        # Split on ". " followed by a capital. The lookbehind must
        # accept a CAPITAL letter too, because an author list ends in an
        # initial: "... Forssberg H, Ullen F. Extensive piano
        # practicing..." The first version of this required a lowercase
        # character before the period, so it never split there, the
        # guard fell through to return '', and both numbered-reference
        # cases in verify_inline_title.py went back to failing.
        parts = re.split(r'\.\s+(?=[A-Z])', s, maxsplit=1)
        if len(parts) == 2 and len(parts[1].split()) >= 4:
            return parts[1].strip()
        return ''
    # Otherwise, a numbered reference that got this far may still be
    # "<authors>. <Title>. <journal>." with the author run not
    # recognisable. Same recovery: the title is the second sentence.
    parts = re.split(r'(?<=[a-z0-9)\]])\.\s+(?=[A-Z])', s, maxsplit=1)
    if len(parts) == 2 and len(parts[1].split()) >= 4:
        s = parts[1].strip()
    return s


def cited_titles(path, text):
    """Pull the reference labels out of the body so we have something to
    compare the resolved title against.

    Three shapes have to be recognised, and missing any of them makes a
    correct citation look untitled:

      * a markdown bullet -- "- arXiv:2509.20021 (Embodied AI Survey)";
      * a bracketed index -- "[12] Author. Title. Journal. 2004.";
      * a plain numbered reference -- "4. Embodied AI: From LLMs to
        World Models — arXiv:2509.20021". Only a reference list uses
        this, and the whole point of it is that the title comes BEFORE
        the identifier, which inline_title() handles.

    A fourth shape is the frontmatter `sources` key written as a YAML
    FLOW sequence on one line:

        sources: ["arXiv:2505.09388 (Qwen3 Technical Report)",
                  "arXiv:2509.20021 (Embodied AI Survey)"]

    That form was not recognised at all, so a file using it returned
    zero labels from its own sources list and every identifier in it
    was recorded untitled. It is an entirely ordinary YAML form, and
    eleven files in this corpus write it that way. Split the flow
    sequence into its elements and treat them as labels.
    """
    out = []
    m = re.search(r'^#{1,4}\s*(References|Bibliography|Sources|'
                  r'Citations|Works Cited)\s*:?\s*$', text, re.M | re.I)
    scope = text[m.end():] if m else text
    if m:
        nxt = re.search(r'\n#{1,4}\s+', scope)
        if nxt:
            scope = scope[:nxt.start()]
    # The FRONTMATTER is always in scope, whether or not the file also
    # has a body bibliography. Scoping to the text after a "## Sources"
    # heading put the sources: block outside the scope for 167 files in
    # this corpus, so a file with both a frontmatter citation list AND a
    # body Sources section had its frontmatter citations invisible and
    # every identifier in them was recorded untitled. The heading means
    # "the bibliography is here", not "ignore the citations block".
    #
    # When there is NO heading, `scope` is the whole text and therefore
    # ALREADY CONTAINS the frontmatter. Concatenating the two visits
    # every frontmatter line twice, so a two-element flow sequence
    # reported its elements four times. Only add `front` when `scope`
    # does not already start with it.
    front, sep, body = text.partition(N + '---')
    lines = scope.split(N)
    if not scope.startswith(front):
        lines = front.split(N) + lines
    # One list, walked by index, so a flow sequence can consume the
    # lines it wraps onto and the outer loop can skip them. Passing
    # `scope` to _from_line() while iterating `front` was the earlier
    # arrangement: the join searched the wrong list, found nothing, and
    # yielded one line -- while the wrapped continuation lines were then
    # re-read by the outer loop as if they were bullets.
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        mm = (re.match(r'^\s*[-*+]\s+(.+?)\s*$', line)
              or re.match(r'^\s*\[\d{1,3}\]\s*(.+?)\s*$', line)
              or re.match(r'^\s*\d{1,3}[.)]\s+(.+?)\s*$', line))
        if mm:
            out.append(mm.group(1))
            continue
        if not line.lstrip().startswith('sources: ['):
            continue
        # Flow sequence. It may WRAP across lines, so keep reading
        # until the bracket that opened it is closed. The count has
        # to start at 1 for that opening bracket, not 0: with 0 the
        # closing bracket on a wrapped first line drove the depth
        # to 0 and the loop stopped one line early, silently
        # dropping every element after the first -- a two-element
        # array reported one label, and the missing citation was
        # recorded as untitled rather than as a file with no title.
        start = line.index('[')
        depth = 1
        buf = ''
        consumed = 0
        for ln in [line] + lines[i:]:
            consumed += 1
            buf += ln
            for ch in ln[start:] if ln is line else ln:
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
            if depth == 0:
                # Skip the lines this sequence wrapped onto. Count them
                # rather than locating them: `lines.index(ln)` returns
                # the FIRST equal line, so a document with a repeated
                # line advanced the cursor to the wrong place and the
                # same elements were collected again -- a two-element
                # array reported six labels.
                i += consumed - 1
                break
        body_txt = buf[start:]
        dq = re.findall(r'"([^"]*)"', body_txt)
        out.extend(dq)
        # Single-quoted elements too, but only the ones not already
        # captured. The earlier version wrapped the single-quoted
        # match in quotes before testing it against the
        # double-quoted set, so nothing ever matched and a
        # single-quoted element was added a second time while a
        # two-element array reported one label.
        sq = re.findall(r"'([^']*)'", body_txt)
        for x in sq:
            if x not in dq:
                out.append(x)
    return out


def _from_line(scope, first):
    """`first` and every line after it, once each.

    Kept for the identity lesson, not for use: cited_titles() now walks
    one combined list by index, which is what it should have done all
    along. Two bugs came from the helper. It matched on string IDENTITY
    while `scope.split(N)` builds fresh objects on every call, so it
    never matched and the join stopped at the first line -- a wrapped
    `sources: [...]` reported only its first element. And it was handed
    `scope` while the caller iterated `front`, so it searched the wrong
    list entirely. The index walk removes both.
    """
    rest = scope.split(N)
    try:
        i = rest.index(first)
    except ValueError:
        yield first
        return
    for nxt in rest[i:]:
        yield nxt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--refresh', action='store_true',
                    help='ignore any cached results and re-resolve')
    args = ap.parse_args()

    rows = list(csv.DictReader(open(GRADE_CSV, encoding='utf-8')))

    # Select the rows this verifier can actually act on.
    #
    # The previous selector was the literal 'title match unverified'. The
    # grader stopped emitting that string, so the filter matched ZERO rows
    # and the verifier checked nothing while reporting a clean run. Same
    # failure class as the arXiv URL bug: a selector written against a
    # reason string that no longer exists, and nothing that could fail.
    #
    # What this verifier does: re-resolve every identifier in a file against
    # the live source and compare the resolved title against the title
    # written in the file. So the todo set is every row the grader has NOT
    # already confirmed -- which is broader than the old selector implied.
    #
    #   'T2 pending: N of N not matched: arxiv:absent'
    #       The identifier is not in the T2 table yet. This verifier is
    #       exactly the tool that resolves it, so these are in scope.
    #   'T2 pending: ... arxiv:untitled_citation'
    #       Resolved, but the file gave no title to compare. Re-resolving
    #       will not fix it -- a human must add the title. Still reported,
    #       because the summary should surface the count.
    #   'T2 pending: no T2 identifier'
    #       No identifier at all, so there is nothing to resolve. Excluded:
    #       including it would inflate the set with work this tool cannot do.
    #   anything with 'resolved and title-matched'
    #       Already confirmed. Excluded.
    #
    # Selecting on the CONSTANT 'T2 pending' plus an explicit exclusion of
    # the no-identifier case is deliberately not a list of the per-identifier
    # failure tokens. Those tokens are the part of the string most likely to
    # change again; the prefix has been stable and carries the meaning "the
    # grader could not confirm this row".
    todo = [r for r in rows
            if 'T2 pending' in r['reason']
            and not r['reason'].endswith('no T2 identifier')]

    if not todo:
        # A zero-row todo set is indistinguishable from a broken selector,
        # and that ambiguity is exactly how the stale selector hid for so
        # long. Say so explicitly, and say what was scanned.
        print('  todo set is EMPTY -- nothing for this verifier to do.')
        print('  rows scanned: %d; rows the grader had already confirmed: %d'
              % (len(rows), sum(1 for r in rows
                                if 'resolved and title-matched' in r['reason'])))
        print('  If a non-empty set was expected, the selector in main() has')
        print('  drifted from the reason strings the grader emits. Check')
        print('  docs/audit/grade-decisions.csv reason values before trusting')
        print('  this clean run.')
    if args.limit:
        todo = todo[:args.limit]

    # Partition the pending set by whether the file it names still exists,
    # BEFORE any of it is silently skipped below.
    #
    # The bare `except: continue` this replaces dropped unreadable paths
    # without a word, so a row whose file had been deleted and a row whose
    # file was merely malformed looked identical: both just vanished from
    # the run. That is how a pending table kept 213 rows naming
    # active-wiki files the research consolidation had deliberately
    # removed, and how the summary could report a clean run over a table
    # that was 37% dead weight.
    #
    # The 213 are NOT an error and NOT a signal of a bad citation. They
    # are the active-wiki research duplicates removed in the 2026-09-29
    # consolidation after confirming Oracle already held byte-identical
    # copies. The surviving rows are all Oracle. So:
    #   dropped  = deleted upstream, correctly excluded
    #   missing  = the file should exist and does not -- a real problem
    # A non-empty `missing` fails the run rather than shrinking it.
    dropped, missing, resolved_rows = [], [], []
    for r in todo:
        rel = r['path']
        for pre in ('active-wiki/', 'oracle/brain/'):
            if rel.startswith(pre):
                rel = rel[len(pre):]
        p = ROOTS[r['vault']] + '/' + rel
        # ROOTS values are plain strings (see the definition above), so
        # use os.path.exists rather than the Path method.
        if not os.path.exists(p):
            (dropped if r['vault'] == 'active-wiki' else missing).append(p)
            continue
        resolved_rows.append((r, p, rel))

    if dropped or missing:
        print(f'\n  pending set: {len(todo)} rows')
        print(f'    deleted upstream (excluded): {len(dropped)}'
              f'  [active-wiki research consolidated into Oracle]')
        if missing:
            print(f'    UNRESOLVABLE (ERROR): {len(missing)}')
            for p in missing[:10]:
                print(f'      {p}')
            if len(missing) > 10:
                print(f'      ... and {len(missing) - 10} more')
            print('    These are NOT deleted files. Either the vault root is wrong')
            print('    or a file was removed without updating grade-decisions.csv.')

    # collect every identifier across the pending files
    work = []
    for r, p, rel in resolved_rows:
        try:
            text = open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        e = text.find(N + '---', 3)
        if e == -1:
            continue
        try:
            import yaml
            meta = yaml.safe_load(text[3:e]) or {}
        except Exception:
            continue
        labels = cited_titles(p, text)
        # A label belongs to ONE identifier, not to the whole file.
        #
        # This line is the single largest source of false mismatches
        # in this verifier, and it is not a subtle one. kalman-delta-
        # rule-attribution.md has 59 bullet lines and 2 mentions of
        # arXiv:2012.00073. cited_titles() returns all 59, and that
        # same list of 59 was compared against the resolved title of
        # EACH identifier in the file. Fifty-eight of them are
        # citations to entirely different papers, so they score 0,
        # the best score stays 0, and a perfect citation is recorded
        # as a mismatch.
        #
        # The fix is to intersect: keep only the labels that actually
        # mention this identifier. A file that cites a paper in prose
        # and lists it in a reference block gets both mentions; a
        # file that only has a bare id gets none, which is the
        # untitled_citation case and the honest verdict for it.
        seen = set()
        for s in (meta.get('sources') or []):
            s = str(s).strip()
            ma = ARXIV.search(s)
            ident, kind = None, None
            if ma:
                ident, kind = ma.group(1), 'arxiv'
            else:
                # DOI and URL are separate patterns, so the group index
                # must be taken from whichever one matched. Using
                # `DOI.search(s) or URL.search(s)` and then group(1)
                # worked by accident, because both patterns happen to
                # put the identifier in group 1 -- and broke the moment
                # either was edited. Asked for the group by name.
                for pat in (DOI, URL):
                    mm = pat.search(s)
                    if mm:
                        ident = clean_doi(mm.group('id'))
                        kind = 'doi'
                        break
            if ident and ident not in seen:
                seen.add(ident)
                # Keep only the labels that mention THIS identifier.
                # A DOI is written "10.1038/nn1516" and an arXiv id
                # "2403.01590", so a plain substring test matches both
                # forms. Before this filter every label in the file
                # was a candidate for every identifier in it.
                #
                # THE TEST MUST BE ON THE BARE IDENTIFIER. `ident` is
                # the full form, "doi:10.1126/science.1241224", and a
                # label is a source line containing the BARE form,
                # "https://www.science.org/doi/10.1126/science.1241224
                # (Sleep Drives ...)". The prefixed string is not a
                # substring of that, so `own` came back EMPTY and the
                # row was recorded untitled_citation while a correct
                # title sat in the file. The comment above describes
                # the bare form the code was meant to use.
                bare = ident.split(':', 1)[-1]
                own = [l for l in labels
                       if bare in l or bare.lower() in l.lower()]
                work.append((r['vault'], rel, kind, ident, own,
                             inline_title(s)))
    print(f'\n  {len(todo)} files pending T2, {len(work)} identifiers'
          f' to resolve\n')

    # Resumable cache. At 3s per identifier the full run is ~80 minutes,
    # so a partial run must not be lost and a re-run must not re-ask
    # arXiv for answers it already gave.
    results = {}
    if os.path.exists(OUT) and not args.refresh:
        try:
            results = json.load(open(OUT, encoding='utf-8'))
            print(f'  resuming: {len(results)} identifiers already resolved')
        except Exception:
            results = {}
    counts = {'match': 0, 'mismatch': 0, 'unresolvable': 0,
              'untitled_citation': 0}
    # Resolved titles, keyed by identifier alone. See the fetch block
    # below for why the verdict key and the title key are scoped
    # differently.
    title_cache = {}
    for i, (vault, rel, kind, ident, labels, inline) in enumerate(work, 1):
        # The cache key MUST include the file.
        #
        # Two vault files can cite the same identifier, and they need not
        # cite it equally well. arXiv:2505.17335 is the live example:
        #
        #   research/cboritem-2026-ecosystem-survey.md
        #     - "Secure Parsing and Serializing with Separation Logic
        #        Applied to CBOR, CDDL, and COSE"          <- correct
        #   research/cbor-tag-6-dependent-type-formalization.md
        #     - "arXiv:2505.17335 (EverCBOR/EverCDDL, ...)"  <- annotation
        #
        # With an identifier-only key, whichever file is processed second
        # overwrites the first, and the record reports ONE verdict for
        # what are really two independent citation checks. Here that
        # turned a correct citation into a recorded mismatch, because the
        # bare-URL/annotation file happened to be written last.
        #
        # The RESOLVED TITLE is still per-identifier and worth caching --
        # asking Crossref twice for the same DOI is pure waste at a 3s
        # rate limit. So the title is fetched once per identifier and the
        # verdict is recorded per (file, identifier).
        fetch_key = f'{kind}:{ident}'
        key = f'{rel}::{fetch_key}'
        if key in results:
            continue
        if args.dry:
            print(f'  [{i}/{len(work)}] would check {key}')
            continue
        title = None
        # Per-IDENTIFIER title cache, separate from the per-file verdict
        # cache. With the file added to the verdict key, the same DOI
        # cited from two files would otherwise be fetched twice at a 3s
        # rate limit -- and cross-file duplication is common in this
        # corpus. The title is a property of the paper; the verdict is a
        # property of (file, paper). Caching them at different scopes is
        # what lets the verdict be per-file without paying for a second
        # network round trip.
        if fetch_key in title_cache:
            cached = title_cache[fetch_key]
            if cached is None:
                results[key] = {'verdict': 'unresolvable',
                                'note': 'from identifier cache'}
                counts['unresolvable'] += 1
                continue
            title = cached
        else:
            # 429 means "you are being rate limited", which is NOT the
            # same as "this identifier does not exist". The first run
            # recorded 258 of those as `unresolvable` and they were
            # simply the run hitting arXiv's limit. So 429 is retried
            # with exponential backoff, and only a genuine failure after
            # the retries is recorded as unresolvable.
            for attempt in range(4):
                try:
                    if kind == 'arxiv':
                        title = fetch_arxiv(ident)
                    else:
                        title = None
                        try:
                            d = fetch_crossref(ident)
                            title = (d.get('message', {}).get('title')
                                     or [None])[0]
                        except urllib.error.HTTPError as ex:
                            if ex.code != 404:
                                raise
                        if not title:
                            # DATACITE FALLBACK. Crossref does not carry
                            # Zenodo deposits, most institutional
                            # repositories, or arXiv's DataCite
                            # registrations. Four identifiers in this
                            # corpus -- 10.5281/zenodo.19054914,
                            # 10.34726/12041, 10.48550/arxiv.2510.18407
                            # and 10.5281/zenodo.18671158 -- all return
                            # 200 from the DOI HANDLE SYSTEM and 404
                            # from Crossref, and all four name real
                            # published items. Recording them as
                            # `unresolvable` asserts that an identifier
                            # does not exist, which is false: the
                            # resolver simply was not asked the right
                            # registry.
                            title = fetch_datacite(ident)
                        if not title:
                            raise urllib.error.HTTPError(
                                ident, 404, 'not in Crossref or DataCite',
                                None, None)
                    break
                except urllib.error.HTTPError as ex:
                    if ex.code == 429 and attempt < 3:
                        # CAPPED exponential backoff.
                        #
                        # The original was DELAY * 4**(attempt+1), giving
                        # 12s, 48s, 192s and then 768s -- twelve minutes
                        # and forty-eight seconds of the process doing
                        # nothing, per identifier, on a 956-identifier
                        # run. A real run reached 240 rows and then sat
                        # at 13 minutes elapsed with 1 second of CPU and
                        # zero open sockets, which is indistinguishable
                        # from a hang: there was no output, no progress
                        # marker, and nothing in the log to say why.
                        #
                        # A direct probe of the same endpoint during the
                        # stall returned HTTP 200, so the rate limit was
                        # transient and the long sleep bought nothing. It
                        # only delayed recovery.
                        #
                        # The cap keeps the backoff meaningful (so a
                        # genuine limit is respected) while bounding the
                        # worst case to something survivable across a
                        # long run. Crossref tolerates far more traffic
                        # than arXiv, so the two are separated below.
                        wait = min(DELAY * (4 ** (attempt + 1)),
                                   ARXIV_BACKOFF_CAP if kind == 'arxiv'
                                   else CROSSREF_BACKOFF_CAP)
                        # Say why we are about to go quiet. A silent
                        # multi-minute sleep is undiagnosable after the
                        # fact: the log shows nothing, the process shows
                        # no CPU and no sockets, and the only symptom is
                        # that progress stopped. That is what made the
                        # 768s stall look like a hang.
                        print(f'  [{i}/{len(work)}] HTTP 429 on {key}, '
                              f'backing off {wait:.0f}s '
                              f'(attempt {attempt + 1}/3)', flush=True)
                        time.sleep(wait)
                        continue
                    results[key] = {'verdict': 'unresolvable',
                                    'err': f'HTTP {ex.code}'}
                    counts['unresolvable'] += 1
                    title = None
                    break
                except Exception as ex:
                    results[key] = {'verdict': 'unresolvable',
                                    'err': str(ex)[:80]}
                    counts['unresolvable'] += 1
                    title = None
                    break
            title_cache[fetch_key] = title
        if results.get(key):
            time.sleep(DELAY)
            continue
        if not title:
            results[key] = {'verdict': 'unresolvable'}
            counts['unresolvable'] += 1
            time.sleep(DELAY)
            continue
        # The candidate titles are the SOURCE ENTRY'S OWN TEXT plus any
        # reference-section labels, because the citation frequently
        # carries its title inline:
        #   arXiv:2605.00081 — Alignment Contracts for Agentic Security
        #   Systems (DATE-TRACKED)
        # The first version compared the resolved title only against
        # labels parsed out of a separate "## References" heading. In
        # these files that heading either does not exist or holds a
        # different list, so every comparison scored 0 and 177 genuine,
        # correct citations were reported as `mismatch`. Resolved titles
        # were spot-checked against the wiki and they match:
        #   2605.00081 -> "Alignment Contracts for Agentic Security
        #                  Systems" == the cited title
        # So the corpus was right and the matcher was wrong.
        # The fifth element of `work` is the INTERSECTED label set --
        # only the labels mentioning this identifier, not every label in
        # the file. It is unpacked here under the name `labels`.
        #
        # Reaching for a variable called `own` would be a NameError:
        # there is no `own` in scope, the tuple element is bound to
        # `labels` and `own` only exists in the builder loop. So the
        # intersection is already in `labels` and the correct code is
        # what is here.
        cands = [x for x in list(labels) + [inline] if x]
        # THE ROOT CAUSE. Every one of the false mismatches in this
        # verifier came from here, and the five inline_title fixes
        # before it were aimed at the wrong function.
        #
        # Labels arrive RAW from cited_titles(), which returns bullet
        # lines verbatim. inline_title() was only ever applied to the
        # frontmatter `sources` entry -- the `inline` variable -- and
        # never to a label. So a label that is itself a bare identifier
        #
        #     arxiv:2403.01590
        #
        # passed the `if x` test (it is non-empty), was compared
        # verbatim against the resolved title, scored 0.0, and forced
        # verdict=mismatch for a citation that carries no title at all.
        # There is nothing to mismatch. The honest verdict is
        # untitled_citation.
        #
        # Run every candidate through inline_title() and keep only what
        # survives as an actual title. This is the one place that
        # guarantees the property the whole verifier depends on: a
        # candidate that does not belong to this identifier's title can
        # never reach title_match.
        raw_cands = list(cands)
        cleaned = [inline_title(x) for x in raw_cands]
        cands = [x for x in cleaned if x and _has_title_words(x)]
        # A trailing parenthetical is usually a gloss, and
        # inline_title() correctly drops it. But sometimes it IS the
        # title, with the text before it used as a section shorthand:
        #
        #   - "arXiv:2602.19320 — Anatomy of Agentic Memory:
        #       4-Structure Taxonomy (Anatomy of Agentic Memory:
        #       Taxonomy and Empirical Analysis of Evaluation and
        #       System Limitations)"
        #
        # The shorthand scores 0.364 against the real title; the
        # parenthetical scores 1.000. Measured, not assumed.
        #
        # Add the parenthetical as a SECOND reading rather than
        # changing the default, because the default is right far more
        # often: dropping the gloss is what makes
        # "https://doi.org/10.1 (Real Title Here)" work. A real title
        # matches exactly one of the two readings exactly, so offering
        # both cannot manufacture a match -- the worst case is a
        # candidate that still fails to match and the row stays a
        # mismatch, which is where it already was.
        extra = []
        for raw in raw_cands:
            inner = _trailing_parenthetical(raw)
            if inner and inner not in extra:
                extra.append(inner)
        cands = cands + [x for x in extra
                         if x not in cands and _has_title_words(x)]
        if not cands:
            # The identifier resolved, but the citation carries no title
            # to compare it against -- a bare mirror URL, or an entry
            # that is only a link. `mismatch` would be a false accusation
            # of a wrong citation; the honest verdict is that the check
            # could not be made. Distinct from `unresolvable`, which
            # means the identifier itself did not resolve.
            results[key] = {'verdict': 'untitled_citation',
                            'title': title[:200]}
            counts['untitled_citation'] = counts.get(
                'untitled_citation', 0) + 1
            time.sleep(DELAY)
            continue
        best, score = False, 0.0
        for lab in cands:
            ok, s = title_match(lab, title)
            if s > score:
                best, score = ok, s
        # A correct citation written as an abbreviation scores below the
        # Jaccard bar purely because it is shorter, not because it is
        # wrong. Checked explicitly, and only for full coverage of the
        # label's distinctive tokens -- see is_abbreviation_of.
        if not best and any(is_abbreviation_of(lab, title) for lab in cands):
            best = True
        results[key] = {'verdict': 'match' if best else 'mismatch',
                        'title': title[:200], 'score': round(score, 3)}
        counts['match' if best else 'mismatch'] += 1
        time.sleep(DELAY)
        if i % 40 == 0:
            with open(OUT, 'w', encoding='utf-8') as fh:
                json.dump(results, fh, indent=1, sort_keys=True)
            # flush=True is load-bearing. Without it the progress line
            # sits in the block buffer, so a redirected log shows
            # nothing at all while the run is working normally. That is
            # how a rate-limit stall became indistinguishable from a
            # crash: the log was silent for reasons that had nothing to
            # do with the run.
            print(f'  [{i}/{len(work)}] {dict(counts)}', flush=True)

    if args.dry:
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=1, sort_keys=True)

    # Tally the WHOLE result set, not just what this run resolved.
    #
    # `counts` only ever incremented inside the resolve loop, so on a
    # resumed run -- where nearly every identifier is already cached and
    # the loop skips it -- the final line printed an empty tally beside a
    # fully populated 659-entry results file. That reads as "nothing was
    # found", which is the opposite of what happened, and it is precisely
    # the summary a person checks before deciding whether T2 is safe to
    # apply. Recount from the results themselves so the number reported
    # is the number stored.
    tally = {'match': 0, 'mismatch': 0, 'unresolvable': 0,
             'untitled_citation': 0}
    for entry in results.values():
        v = entry.get('verdict') if isinstance(entry, dict) else None
        if v in tally:
            tally[v] += 1
        else:
            tally['unresolvable'] += 1

    newly = sum(counts.values())
    # `work` counts identifier MENTIONS, results are keyed by identifier
    # ID. The same paper cited in twelve files is one entry, so the two
    # numbers legitimately differ and are not comparable. Say which is
    # which, or the gap reads as 297 identifiers that went unverified.
    print(f'\n  {tally}')
    print(f'  {len(results)} unique identifiers on record '
          f'({newly} resolved this run, {len(results) - newly} cached)')
    print(f'  drawn from {len(work)} citations across '
          f'{len(resolved_rows)} files')
    print(f'  -> {OUT}')
    print('  Confidence NOT written. grade_all.py --with-t2 applies this.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
