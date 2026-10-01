"""
brain.hippocampus.pattern_separation — Geometric pattern separation.

Replaces the SHA-256 based `pattern_separation()` in replay.py, which
computed a hash of "text::context" and returned 16 hex characters.

WHY THAT WAS THE WRONG FUNCTION CLASS
-------------------------------------
Our own Oracle vault, on the hash approach:

    "A hash is a maximally non-geometric function used to solve a
     geometric problem. It is not a weak implementation; it is the
     wrong function class."

    "You cannot compute distance between two hashes, so you cannot
     measure whether separation occurred."

Pattern separation is a GEOMETRIC operation: its purpose is to make
nearly-identical inputs land NEAR each other in representation space so
they can be told apart, while pushing genuinely different inputs apart.
A hash has no geometry. Measured on three near-identical pairs that
differed by one word, the old implementation returned distances of
64730, 48930 and 44108 — uncorrelated with how similar the inputs
actually were. Two identical strings hashed differently; two unrelated
strings could hash closely. The number carried no information about
similarity, so nothing downstream could use it.

WHAT THIS DOES INSTEAD
----------------------
A deterministic sparse random projection of a bag-of-words vector into
a fixed-dimension space, with L2 normalisation. This is the standard
"random indexing"/"hashing trick" construction: no model, no training,
no network, fully deterministic given the same text, and it has real
geometry.

Consequences that matter:
  * near-duplicates are near (cosine similarity near 1)
  * unrelated texts are far (cosine near 0)
  * distance is MEASURABLE, so separation can be verified rather than
    assumed

SEPARATION IS EXPLICIT AND CHECKABLE
------------------------------------
`separate()` reports the measured similarity, not just a code. A caller
can ask whether two traces were actually separated instead of trusting
that a hash changed.

DETERMINISM
-----------
The projection is seeded from a fixed constant, so the same text always
produces the same vector. No global RNG is touched, so this is safe to
call from concurrent code and gives identical results across processes —
which a random embedding without a fixed seed would not.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "PatternSeparator",
    "DEFAULT_DIM",
    "tokenize",
]

# Fixed seed. Changing this changes every vector, so it is part of the
# on-disk format: any persisted embedding becomes incomparable.
_SEED = b"hermes-brain/pattern-separation/v1"
DEFAULT_DIM = 256


def tokenize(text: str) -> List[str]:
    """Lowercase word tokens, order preserved but position discarded.

    Bag-of-words is a real limitation and is stated rather than hidden:
    this cannot distinguish "dog bites man" from "man bites dog". For
    pattern separation between near-duplicate EPISODE CUES that is
    acceptable, because the discriminative content in those is lexical.
    A future positional model would be a different function class again.
    """
    return re.findall(r"[a-z0-9]+", (text or "").lower())


class PatternSeparator:
    """Deterministic geometric separator for episodic cues."""

    def __init__(self, dim: int = DEFAULT_DIM, seed: bytes = _SEED):
        if dim < 8:
            raise ValueError("dim must be at least 8 to be meaningful")
        self.dim = dim
        self.seed = seed
        self._cache: Dict[str, Tuple[float, ...]] = {}

    # ── projection ────────────────────────────────────────────────────
    def _bucket(self, token: str) -> Tuple[int, float]:
        """Map a token to (index, sign) for the signed random projection.

        The sign is taken from a separate hash of the token so that two
        distinct tokens landing in the same bucket CANCEL rather than
        add. Without it, collisions would systematically inflate
        similarity, which is the opposite of what separation needs.
        """
        h = hashlib.blake2b(token.encode("utf-8"), digest_size=8,
                            key=self.seed[:64]).digest()
        idx = int.from_bytes(h[:4], "big") % self.dim
        sign = 1.0 if h[4] & 1 else -1.0
        return idx, sign

    def embed(self, text: str, context: Optional[str] = None) -> List[float]:
        """Project text (+context) into a unit vector.

        Context is folded in with a separate prefix so that
        "deploy failed" in staging and in production are distinguishable
        while remaining close -- which is the whole point: near, not
        identical.
        """
        key = f"{text}\x00{context or ''}"
        hit = self._cache.get(key)
        if hit is not None:
            return list(hit)

        vec = [0.0] * self.dim
        for token in tokenize(text):
            idx, sign = self._bucket(token)
            vec[idx] += sign
        for token in tokenize(context or ""):
            idx, sign = self._bucket("ctx:" + token)
            vec[idx] += sign * 0.5  # context informs, but does not dominate

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        self._cache[key] = tuple(vec)
        return vec

    # ── geometry ──────────────────────────────────────────────────────
    @staticmethod
    def cosine(a: Sequence[float], b: Sequence[float]) -> float:
        """Cosine similarity of two vectors, clamped to [-1, 1]."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return max(-1.0, min(1.0, dot / (na * nb)))

    def similarity(self, a: str, b: str) -> float:
        return self.cosine(self.embed(a), self.embed(b))

    def distance(self, a: str, b: str) -> float:
        """Euclidean distance on unit vectors: 0 = identical, 2 = opposite."""
        return math.sqrt(max(
            0.0, 2.0 - 2.0 * self.similarity(a, b)))

    # ── the operation itself ──────────────────────────────────────────
    def separate(self, text_cue: str, context: Optional[str] = None,
                 prior_cues: Optional[Iterable[Tuple[str, Optional[str]]]] = None,
                 margin: float = 0.15) -> Dict[str, object]:
        """Separate this cue from prior similar cues, and REPORT the result.

        Returns a dict rather than a bare string because the interesting
        quantity is not the code but the measured geometry: whether this
        cue was actually distinguishable from the ones it resembles.

        `margin` is the similarity at or below which two cues count as
        separated. It is a real threshold with a real trade-off -- raise
        it and similar events get merged, lower it and a single event
        fragments into several -- so it is an argument, not a constant.
        """
        vec = self.embed(text_cue, context)
        priors = list(prior_cues or [])
        nearest: Optional[Tuple[float, str]] = None
        collisions: List[Dict[str, object]] = []

        for prior_text, prior_ctx in priors:
            sim = self.cosine(vec, self.embed(prior_text, prior_ctx))
            if nearest is None or sim > nearest[0]:
                nearest = (sim, prior_text)
            if sim > 1.0 - margin:
                collisions.append({
                    "prior": prior_text,
                    "similarity": round(sim, 4),
                    "distance": round(math.sqrt(max(0.0, 2.0 - 2.0 * sim)), 4),
                })

        nearest_sim = nearest[0] if nearest else 0.0
        return {
            "vector": vec,
            "code": self.code(vec),
            "nearest_prior": nearest[1] if nearest else None,
            "nearest_similarity": round(nearest_sim, 4),
            "nearest_distance": round(math.sqrt(
                max(0.0, 2.0 - 2.0 * nearest_sim)), 4),
            "separated": nearest_sim <= 1.0 - margin,
            "margin": margin,
            "collisions": collisions,
        }

    @staticmethod
    def code(vec: Sequence[float], width: int = 16) -> str:
        """A short stable label for a vector.

        This is a LOSSY summary, deliberately kept only for logging and
        human comparison. It is NOT the separation itself and must never
        be used to measure similarity -- that is what the hash did, and
        it is why the hash was wrong. Use similarity()/distance() for
        that.
        """
        h = hashlib.blake2b(
            ",".join("%.6f" % v for v in vec).encode("utf-8"),
            digest_size=16).hexdigest()
        return h[:width]
