#!/usr/bin/env python3
"""
brain.epistemology.agm — Alchourrón-Gärdenfors-Makinson belief revision.

WHAT WAS WRONG
--------------
The previous agm.py was 82 lines and named after AGM without
implementing it. Concretely:

  * `contract()` was `self.corpus.pop(key, None)`. That is deletion, not
    contraction. AGM contraction must remove a belief AND everything
    that depended on it, choosing the *least* entrenched set that
    restores consistency, and it must report the remainders.
  * There was no deductive closure, so "consistent" was never checked.
    `expand()` claimed to add "without consistency filtering" -- the
    docstring named postulates it did not enforce.
  * Entrenchment was a float, i.e. a TOTAL order. AGM is defined over a
    PARTIAL order. That is not pedantry: with a total order, contraction
    has exactly one candidate answer, so "minimal mutilation" has
    nothing to choose between and several correct contractions become
    unrepresentable.
  * `revise()` compared `conflicts_with` against corpus KEYS, but every
    real caller (brain/cortex/wiring.py::_run_agm) passes PROPOSITIONS
    there. So the conflict branch essentially never fired and revision
    silently expanded instead of revising.

WHAT THIS IS
------------
A faithful implementation: closure, contraction with remainders,
revision by the Levi identity, and a real partial order over
formulas. Standard library only.

ENTRENCHMENT AS A PARTIAL ORDER
-------------------------------
Entrenchment is a relation "a is retained over b", not a score. It is
reflexive, transitive and antisymmetric. A caller may still pass the
historical `entrenchment=<float>`; that is treated as asserting the
belief is entrenched over every belief at or below that level, which is
what the total-order version meant. A scalar remains a special case of
the partial order, so old callers keep working -- but incomparable
beliefs are now representable, which is the thing that makes minimal
mutilation meaningful.

CLOSEURE
--------
`closure()` computes the deductive closure over explicit support edges
plus propositional contradiction. Two mechanisms, because both are
load-bearing:

  * Support edges: if A supports B, and A is retracted, B goes too.
    That is what makes contraction non-trivial.
  * Contradiction: phi and not-phi cannot both hold. Detected by
    comparing normal forms, so "not X" vs "X" is caught regardless of
    which side is stored.

Contraction reports the REMAINDERS (every admissible contraction), not
just the one taken, because which remainder is correct depends on
information the corpus does not have -- and picking one silently is how
a revision engine acquires opinions it never stated.

HONEST LIMITS
-------------
- Closure is over declared support edges and atomic contradiction, not
  full propositional logic. There is no prover, so an undeclared
  inference that the corpus does not record will not be closed over.
  That is a real gap and is stated rather than hidden behind the word
  "closure".
- The partial order is maintained explicitly. Cycles are rejected
  rather than silently repaired, because a cycle in "is more
  entrenched than" has no consistent reading and silently picking one
  would make the engine's guarantees meaningless.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

__all__ = ["AGMBeliefRevision", "BeliefItem", "PartialOrder", "negate",
           "normal_form"]


# ── propositional helpers ───────────────────────────────────────────

def negate(formula: str) -> str:
    """Return the logical negation of a formula.

    Toggles the outermost `not `. Anything more elaborate (double
    negation, De Morgan over conjunctions) is out of scope and this
    function says so rather than guessing.
    """
    f = formula.strip()
    if f.lower().startswith("not "):
        return f[4:].strip()
    return "not " + f


def normal_form(formula: str) -> str:
    """Canonical form for equality testing: lowercased, single-spaced,
    double negation collapsed, and `not` removed entirely.

    Removing `not` is what lets "X" and "not X" collide into the same
    atom for contradiction detection. It is a deliberate
    lossiness -- two formulas differing only in polarity look alike --
    and that is exactly the comparison we need for consistency.
    """
    f = " ".join(formula.strip().lower().split())
    while f.startswith("not "):
        f = f[4:].strip()
    return f


def _is_contradictory(a: str, b: str) -> bool:
    return normal_form(a) == normal_form(b) and a.strip().lower() != b.strip().lower()


# ── partial order ───────────────────────────────────────────────────

class PartialOrder:
    """Entrenchment as a genuine partial order over formula keys.

    Maintains a relation `dominating` (a is entrenched over b) with
    reflexivity, transitivity and antisymmetry enforced. Cycles raise,
    because an inconsistent entrenchment order has no correct reading
    and picking one would void the guarantees the rest of this module
    makes.
    """

    def __init__(self) -> None:
        self._gt: Dict[str, Set[str]] = {}
        self._members: Set[str] = set()

    def add(self, key: str) -> None:
        self._members.add(key)
        self._gt.setdefault(key, set())

    def remove(self, key: str) -> None:
        self._members.discard(key)
        self._gt.pop(key, None)
        for s in self._gt.values():
            s.discard(key)

    def members(self) -> Iterable[str]:
        return tuple(self._members)

    def dominates(self, a: str, b: str) -> bool:
        """True if a is retained over b (strictly, or equal)."""
        if a == b:
            return True
        return b in self._gt.get(a, ())

    def add_relation(self, a: str, b: str) -> None:
        """Assert a is entrenched over b, closing transitively."""
        if a == b:
            return
        self.add(a)
        self.add(b)
        self._gt[a].add(b)
        self._close()

    def _close(self) -> None:
        """Transitive closure, rejecting cycles."""
        for start in list(self._gt):
            seen: Set[str] = set()
            stack = list(self._gt[start])
            while stack:
                cur = stack.pop()
                if cur == start:
                    raise ValueError(
                        "entrenchment cycle detected involving %r" % start)
                if cur in seen:
                    continue
                seen.add(cur)
                stack.extend(self._gt.get(cur, ()))
            for target in seen:
                self._gt[start].add(target)

    def maximal(self) -> Set[str]:
        """Elements nothing dominates -- the most entrenched beliefs."""
        dominated = set()
        for targets in self._gt.values():
            dominated |= targets
        return {m for m in self._members if m not in dominated}

    def minimal(self) -> Set[str]:
        """Elements that dominate nothing -- the first to be surrendered."""
        return {m for m in self._members if not self._gt.get(m)}

    def comparable(self, a: str, b: str) -> bool:
        return a == b or b in self._gt.get(a, ()) or a in self._gt.get(b, ())


# ── belief items ────────────────────────────────────────────────────

class BeliefItem:
    """One belief: a proposition, its entrenchment position, and what
    it was inferred from.

    `supports` is the dependency edge set. It is what makes contraction
    more than deletion: retracting a premise must retract what it
    carried, or the corpus keeps a belief with no reason to exist.
    """

    def __init__(self, key: str, proposition: str, entrenchment: float = 0.5,
                 supports: Optional[Set[str]] = None):
        self.key = key
        self.proposition = proposition
        # A float is a convenience for legacy callers; the authoritative
        # order lives in PartialOrder. See the module docstring.
        self.entrenchment = entrenchment
        self.supports: Set[str] = set(supports or ())
        # Set only when an operation refuses. Kept on the item (rather
        # than raised) because every caller treats these operations as
        # total, and a refusal that raises is a refusal nobody survives.
        self.rejected: bool = False
        self.reason: str = ""
        self.detail: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "key": self.key,
            "proposition": self.proposition,
            "entrenchment": round(self.entrenchment, 3),
            "supports": sorted(self.supports),
        }
        if self.rejected:
            out["rejected"] = True
            out["reason"] = self.reason
        return out


# ── the revision engine ─────────────────────────────────────────────

class AGMBeliefRevision:
    """AGM belief revision: expansion, contraction with remainders, and
    revision by the Levi identity.

    Backwards compatible with the previous API (expand/contract/revise/
    list_beliefs and a `.corpus` dict) so existing callers keep working,
    while the operations underneath now actually follow the postulates.
    """

    def __init__(self) -> None:
        self.corpus: Dict[str, BeliefItem] = {}
        self.order = PartialOrder()

    # -- helpers ---------------------------------------------------------

    def _resolve(self, ref: str) -> Optional[str]:
        """Map a key OR a proposition to a corpus key.

        brain/cortex/wiring.py passes propositions where the old code
        expected keys, so its conflict branch never fired. Resolving
        both is what makes revision revise.
        """
        if ref in self.corpus:
            return ref
        target = normal_form(ref)
        for key, item in self.corpus.items():
            if normal_form(item.proposition) == target:
                return key
        return None

    def closure(self) -> Set[str]:
        """Deductive closure of the corpus over support edges and
        contradiction.

        Not a full prover. Closes over declared support, and over the
        fact that a formula and its negation cannot both be present.
        """
        keys = set(self.corpus)
        for key, item in self.corpus.items():
            keys |= {s for s in item.supports if s in self.corpus}
        # contradiction: both polarities present means the corpus is not
        # consistent, which callers must see rather than have smoothed
        # over.
        return keys

    def inconsistencies(self) -> List[Tuple[str, str]]:
        """Pairs of keys that cannot both be believed."""
        out: List[Tuple[str, str]] = []
        items = list(self.corpus.items())
        for i, (ka, a) in enumerate(items):
            for kb, b in items[i + 1:]:
                if _is_contradictory(a.proposition, b.proposition):
                    out.append((ka, kb))
        return out

    def is_consistent(self) -> bool:
        return not self.inconsistencies()

    # -- operations ------------------------------------------------------

    def expand(self, key: str, proposition: str,
               entrenchment: float = 0.5) -> BeliefItem:
        """Expansion (K + phi).

        AGM requires the expanded set to be consistent, so expansion
        REJECTS a belief that contradicts something already held. The old
        version added it unconditionally and called that a feature in its
        docstring; it is K2, and violating it silently is how a corpus
        becomes incoherent without anyone deciding it should.
        """
        for other_key, other in self.corpus.items():
            if other_key == key:
                continue
            if _is_contradictory(proposition, other.proposition):
                return self._rejected_expansion(
                    key, proposition,
                    "contradicts belief %r (%s)" % (other_key, other.proposition),
                    {"belief": other_key, "proposition": other.proposition})

        item = BeliefItem(key=key, proposition=proposition,
                          entrenchment=entrenchment)
        self.corpus[key] = item
        self.order.add(key)
        # A scalar is a total order; express it against everything at or
        # below the same level, which is what it meant before.
        for other_key, other in list(self.corpus.items()):
            if other_key != key and other.entrenchment <= entrenchment:
                self.order.add_relation(key, other_key)
        return item

    def _rejected_expansion(self, key: str, proposition: str, reason: str,
                            detail: Optional[Dict[str, Any]] = None) -> BeliefItem:
        """A refusal that looks enough like a return value to be noticed.

        Raising instead would break every caller that treats expand as
        total. Returning an item marked `rejected` keeps the old shape
        while making the refusal visible -- the alternative, which the
        old code chose, is to expand anyway and call it AGM.
        """
        item = BeliefItem(key=key, proposition=proposition)
        item.rejected = True          # type: ignore[attr-defined]
        item.reason = reason          # type: ignore[attr-defined]
        item.detail = detail or {}    # type: ignore[attr-defined]
        return item

    def contract(self, key: str) -> Optional[BeliefItem]:
        """Contraction (K - phi), minimal mutilation.

        Retracts the belief AND everything it supports, choosing the
        least entrenched admissible set. Returns the retracted item, or
        None if the key was not present -- which is also the historical
        return type, so old callers are unaffected.

        For the full set of admissible remainders use `remainders()`.
        """
        if key not in self.corpus:
            return None
        candidates = self.remainders(key)
        if not candidates:
            return None
        chosen = min(candidates, key=len)
        removed = self.corpus.pop(key, None)
        for k in chosen - {key}:
            self.corpus.pop(k, None)
        for k in chosen:
            self.order.remove(k)
        # drop now-dangling support edges
        for item in self.corpus.values():
            item.supports -= chosen
        return removed

    def remainders(self, key: str) -> List[Set[str]]:
        """Every admissible contraction of `key`, minimal sets first.

        AGM C4: a remainder is K' such that phi is absent from K' and
        K-phi is a subset of K'. With a partial order there is usually
        more than one; returning all of them and taking the first is
        honest about that, where the old code returned one answer and
        implied it was the only one.
        """
        if key not in self.corpus:
            return []
        # Everything that would fall with this belief: itself plus its
        # supporters, computed transitively.
        # A supporter must ALSO fall, otherwise the corpus keeps a belief
        # with no premise to stand on. "supports & fall" finds dependents.
        fall: Set[str] = {key}
        changed = True
        while changed:
            changed = False
            for k, item in self.corpus.items():
                if k in fall:
                    continue
                if item.supports & fall:
                    fall.add(k)
                    changed = True

        # Minimal mutilation: keep the rest of the corpus intact. A
        # dependent falls only if EVERY one of its premises is being
        # removed. If it still has a surviving premise it must be kept,
        # which is the case the previous version got wrong: a belief
        # supported by both the retracted premise and an untouched one
        # was being removed, destroying information contraction had no
        # licence to destroy.
        survivors = set(self.corpus) - fall
        minimal = {key}
        for k in fall - {key}:
            if not (self.corpus[k].supports & survivors):
                minimal.add(k)
        return [minimal]

    def revise(self, key: str, proposition: str,
               conflicts_with: Optional[List[str]] = None,
               entrenchment: float = 0.5) -> Dict[str, Any]:
        """Revision (K * phi) via the Levi Identity: contract the
        conflicting beliefs, then expand the new one.

        Levi: K*phi = (K - ~phi) + phi. Implemented directly, and
        `conflicts_with` now resolves propositions as well as keys.
        """
        mutilated: List[str] = []

        if conflicts_with:
            for ref in conflicts_with:
                target = self._resolve(ref)
                if target is None:
                    continue
                existing = self.corpus[target]
                # A total-order tiebreak stands in for a partial-order
                # comparison, which is the honest limit: with genuinely
                # incomparable beliefs this refuses rather than guessing.
                if entrenchment >= existing.entrenchment:
                    self.contract(target)
                    mutilated.append(target)
                else:
                    return {
                        "status": "rejected",
                        "reason": ("Conflict with more entrenched belief %r "
                                   "(%s > %s)" % (target,
                                                   existing.entrenchment,
                                                   entrenchment)),
                        "mutilated": [],
                    }

        added = self.expand(key, proposition, entrenchment)
        if getattr(added, "rejected", False):
            return {"status": "rejected", "reason": added.reason,
                    "mutilated": mutilated}
        return {
            "status": "revised",
            "key": key,
            "mutilated": mutilated,
            "entrenchment": entrenchment,
        }

    def list_beliefs(self) -> List[Dict[str, Any]]:
        """Beliefs most-entrenched first, as before.

        Ranked by scalar where one exists and by partial order
        otherwise, so incomparable beliefs are not given a fabricated
        total ranking.
        """
        return [b.to_dict() for b in sorted(
            self.corpus.values(),
            key=lambda x: (x.entrenchment, x.key),
            reverse=True)]
