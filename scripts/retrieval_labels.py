#!/usr/bin/env python3
"""
Retrieval relevance labels, judged from document CONTENT and keyed by hash.

WHY THIS EXISTS
The previous judgement set was a list of filename fragments, and relevance was
decided by `substring(label) in path`. That made the labels and the keyword arm
share a matching rule, so "oracle" was not an independent ceiling at all -- it
answered "did you return the file with this name", and a body-aware retriever
could be marked wrong for retrieving a document that discusses the topic
thoroughly but is not titled with the keyword. "thalam" in particular matches
any path containing those six letters.

Two changes, and the second matters more than the first:

1. LABELS ARE CONTENT HASHES. A document is identified by a hash of its bytes,
   so relevance cannot be decided by what a file is called. Renaming a document
   cannot change whether it is relevant, which is the property the substring
   test lacked.

2. THERE IS NO is_relevant ANYWHERE. The substring test is the original defect
   and it will creep back, because it is the obvious way to write this and it
   looks reasonable. `test_measure_retrieval.py` asserts that the name does not
   appear in this module's source, so reintroducing it fails the suite rather
   than passing quietly.

HOW THE LABELS WERE MADE
Not by string matching. For each query, documents are pooled from every
strategy's top results plus a body search, and each candidate is judged on
whether its TEXT discusses the query's subject. `judge_by_content` asks a
question with a defensible answer; `is_relevant` asked one whose answer was an
artefact of naming.

The judgement is a proxy, and saying so is the point: a keyword-density rule is
still a rule rather than a human reading each document. It is however
independent of the filename, which is the defect being removed. LABELS_ARE_PROXY
carries that caveat into every report.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, FrozenSet, List, Sequence, Tuple

__all__ = [
    "doc_hash",
    "CONCEPT_TERMS",
    "QUERIES",
    "judge_by_content",
    "label_for",
    "build_labels",
    "LABELS_ARE_PROXY",
    "CONTROL_ARMS_REQUIRED",
]

# Carried into every report. A density rule is a rule, not a human reading each
# document -- but it is independent of the filename, which is the defect being
# removed.
LABELS_ARE_PROXY = (
    "Labels are judged from document text by term density, not by a human "
    "reading each document. They are independent of filenames, which is the "
    "defect being removed, but they are still a rule. Read the per-query "
    "breakdown before quoting a number."
)

# The plan is explicit: without these two arms every result is uninterpretable.
# An arm that does not exist cannot be compared against.
CONTROL_ARMS_REQUIRED = (
    "Every reported recall must be shown alongside the full-context control and "
    "the body-BM25 control. A number without them is uninterpretable."
)

# Each query carries the terms that must appear in a document's BODY for it to be
# judged relevant. These are content concepts, deliberately not path fragments.
CONCEPT_TERMS: Dict[str, Tuple[str, ...]] = {
    "hippocampus complementary learning systems": (
        "complementary learning", "hippocampus", "neocortex", "replay",
        "catastrophic forgetting",
    ),
    "how does memory consolidation work": (
        "consolidation", "memory", "hippocampus", "replay", "sleep",
        "long-term",
    ),
    "prospective memory implementation intentions": (
        "implementation intention", "prospective memory", "if-then", "trigger",
        "intention",
    ),
    "retrieval induced forgetting evidence": (
        "retrieval-induced forgetting", "forgetting", "memory", "test",
        "retrieval practice",
    ),
    "default mode network counterfactual thinking": (
        "counterfactual", "default mode", "default-mode", "self-referential",
        "mental time travel",
    ),
    "thalamus gating sensory attention": (
        "thalamus", "thalamic", "gating", "sensory", "attention",
    ),
    "schema abstraction consolidation": (
        "schema", "abstraction", "consolidation", "knowledge",
    ),
    "graph retrieval pagerank": (
        "graph", "pagerank", "retrieval", "embedding", "vector",
    ),
}

QUERIES: Tuple[str, ...] = tuple(CONCEPT_TERMS)

# A term must clear this density to count. Low enough to admit a document that
# discusses the subject among other things, high enough that one passing
# mention is not a label.
_MIN_TERM_HITS = 2
# A document must satisfy at least this fraction of its query's terms.
_MIN_TERMS_MET = 0.5

_WORD = re.compile(r"[a-z0-9]+")


def doc_hash(path: Path, max_bytes: int = 200_000) -> str:
    """Stable identity for a document: a hash of its bytes.

    Identity by CONTENT, not by name. This is the whole point -- a label keyed
    by path is a label that renaming the file invalidates, and that a
    well-titled irrelevant file satisfies.

    The filename is deliberately NOT mixed in. Hashing the name alongside the
    bytes makes a rename change the identity of a document whose content never
    changed, which means a label silently stops matching after somebody tidies
    their filenames. That is precisely the coupling to the filename this module
    exists to remove, reintroduced through the back door.

    The consequence to know about: two files with byte-identical content are the
    same document as far as labels are concerned, and a label matching either
    one counts once. In a corpus of markdown pages that is rare, and collapsing
    true duplicates is the correct behaviour for a relevance label anyway.
    """
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(max_bytes))
    except OSError:
        # Unreadable. Hash the path so it still has a distinct, stable identity
        # rather than colliding with every other unreadable file.
        h.update(str(path).encode("utf-8", "ignore"))
    return h.hexdigest()[:16]


def _text_of(path: Path, max_bytes: int = 200_000) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")[:max_bytes]
    except OSError:
        return ""


def judge_by_content(path: Path, query: str) -> bool:
    """Is this document relevant to the query, judged on its text?

    The question has a defensible answer: does the body discuss the subject.
    The substring version's answer depended on what the file was called.
    """
    terms = CONCEPT_TERMS.get(query)
    if not terms:
        raise KeyError(f"no concept terms defined for query: {query!r}")
    text = _text_of(path).lower()
    if not text:
        return False
    met = 0
    for term in terms:
        # Count occurrences, not just presence: one passing mention is not a
        # document about the thing.
        if text.count(term) >= _MIN_TERM_HITS:
            met += 1
    return (met / len(terms)) >= _MIN_TERMS_MET


def label_for(path: Path, query: str) -> str:
    """The content hash of a document, if it is relevant to the query."""
    return doc_hash(path) if judge_by_content(path, query) else ""


def build_labels(
    docs: Sequence[Path],
    queries: Sequence[str] = QUERIES,
) -> Dict[str, FrozenSet[str]]:
    """Map each query to the set of content hashes that are relevant to it.

    Built by judging the whole corpus, not by pooling the strategies' own
    results. Pooling first would make each strategy's labels a function of that
    strategy's behaviour, so a strategy could not be marked wrong for missing
    something -- and a label set assembled from the answer cannot detect the
    answer being wrong.
    """
    labels: Dict[str, FrozenSet[str]] = {}
    for query in queries:
        labels[query] = frozenset(
            doc_hash(d) for d in docs if judge_by_content(d, query))
    return labels
