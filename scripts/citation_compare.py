#!/usr/bin/env python3
"""Title comparison with an explicit, testable failure mode.

Why this module exists
----------------------
The original `title_overlap` in verify_citations.py measured

    |shorter_tokens INTERSECT longer_tokens| / |shorter_tokens|

and called the result OK at >= 0.6. That is vacuous in a specific, provable
way: a claimed title of one content word scores 1.00 against ANY real paper
containing that word, and an empty claimed title scores 0.00 — which the
caller then read as MISMATCH, i.e. a *confident wrong verdict* rather than
"I have nothing to compare". Both failure directions produce a number that
looks like evidence.

So the comparison here is built around three rules:

  R1  MIN_CONTENT_WORDS — a comparison with fewer than this many content words
      on the claimed side is not a comparison. It returns UNVERIFIABLE, never
      OK and never MISMATCH.
  R2  Asymmetric coverage is reported separately from the headline score, so a
      1-word claim against a 20-word real title cannot masquerade as a match.
  R3  The verdict is a pure function of its arguments, so the non-vacuity
      harness can mutate it and prove the mutation changes the verdict.

Exit-status discipline is enforced by tests/test_verify_citations_nonvacuity.py,
which mutates the decision function and asserts the mutation is DETECTED. A
verifier that cannot fail is not a verifier.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Set

# Words too common to carry signal when matching titles.
STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "in", "on", "for", "to", "with", "by",
    "from", "at", "as", "is", "are", "be", "its", "it", "that", "this", "via",
    "using", "towards", "toward", "between", "into", "over", "under", "new",
    "can", "does", "do", "we", "our", "their", "these", "those", "than",
}

# R1. Below this many content words on the claimed side, no verdict is possible.
MIN_CONTENT_WORDS = 3

# Coverage of the claimed title's content words needed to call it a match.
MATCH_THRESHOLD = 0.6

# OK | MISMATCH | UNVERIFIABLE
OK = "OK"
MISMATCH = "MISMATCH"
UNVERIFIABLE = "UNVERIFIABLE"


def norm_tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


@dataclass
class Verdict:
    status: str
    coverage: float          # fraction of claimed content words found in actual
    precision: float         # fraction of actual content words found in claimed
    claimed_words: int
    actual_words: int
    reason: str = ""

    @property
    def score(self) -> float:
        """Headline number, kept for backwards-compatible reporting.

        This is the MINIMUM of coverage and precision, not the max and not
        coverage alone. Using min() is the load-bearing choice: a one-word
        claim against a long real title scores low precision and therefore
        cannot pass on coverage alone. The original used coverage of the
        shorter side, which is what made the bug invisible.
        """
        return min(self.coverage, self.precision)


def compare_titles(claimed: str, actual: str,
                   threshold: float = MATCH_THRESHOLD,
                   min_words: int = MIN_CONTENT_WORDS) -> Verdict:
    """Compare a claimed title against the title a registry actually returned.

    Pure function of its arguments (R3) so it can be mutation-tested.
    """
    tc, ta = norm_tokens(claimed), norm_tokens(actual)

    if not tc:
        return Verdict(UNVERIFIABLE, 0.0, 0.0, len(tc), len(ta),
                       "claimed title has no content words to compare")
    if not ta:
        return Verdict(UNVERIFIABLE, 0.0, 0.0, len(tc), len(ta),
                       "registry returned no content words")
    if len(tc) < min_words:
        return Verdict(UNVERIFIABLE, 0.0, 0.0, len(tc), len(ta),
                       f"only {len(tc)} content word(s) on claimed side; "
                       f"need {min_words} for a verdict")

    coverage = len(tc & ta) / len(tc)
    precision = len(tc & ta) / len(ta)

    if min(coverage, precision) >= threshold:
        return Verdict(OK, coverage, precision, len(tc), len(ta))

    return Verdict(MISMATCH, coverage, precision, len(tc), len(ta),
                   f"coverage={coverage:.2f} precision={precision:.2f} "
                   f"threshold={threshold:.2f}")


def compare_years(claimed: str, actual, tolerance: int = 1):
    """Return (ok, note). An absent or unparseable year is UNVERIFIABLE, not OK."""
    if actual in (None, ""):
        return None, "registry returned no year"
    if not claimed:
        return None, "no claimed year"
    try:
        c, a = int(str(claimed)[:4]), int(actual)
    except (TypeError, ValueError):
        return None, "unparseable year"
    delta = abs(c - a)
    if delta <= tolerance:
        return True, f"delta={delta}"
    return False, f"claimed {c} vs actual {a} (delta {delta} > {tolerance})"
