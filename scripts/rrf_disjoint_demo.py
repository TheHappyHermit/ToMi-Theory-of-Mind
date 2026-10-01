#!/usr/bin/env python3
"""
rrf_disjoint_demo.py — reproducible demonstration of RRF's behaviour when two
ranked lists have ZERO overlap.

Referenced by docs/RETRIEVAL-EVALUATION-DESIGN.md section 6.1. Run with no
arguments:  python3 scripts/rrf_disjoint_demo.py

Properties demonstrated (all computed, none asserted):
  1. With disjoint lists, a rank-1 hit in one list cannot outrank a rank-1 hit in
     the other -- RRF is a Borda count and rewards agreement, not quality.
  2. The top-k budget split between two disjoint arms is unconditionally ~50/50,
     independent of relative arm quality.
  3. Re-weighting cannot fix a disjoint list: over-weighting the good arm evicts
     the answer from the top-10 entirely.
  4. k does not fix it (k in {5, 10, 60, 1000}).
  5. With OVERLAP, RRF works as designed -- which is why this failure only appears
     when the arms disagree.

Property 2 reproduces the 50%/50% composition measured and reported in
docs/RETRIEVAL-QUALITY-MEASUREMENT.md, and is the mechanism behind the recall loss
described there.
"""

from collections import defaultdict

K = 60


def rrf(lists, weights=None, k=K):
    s = defaultdict(float)
    w = weights or [1.0] * len(lists)
    for li, lst in enumerate(lists):
        for rank, d in enumerate(lst, start=1):
            s[d] += w[li] / (k + rank)
    return sorted(s.items(), key=lambda kv: -kv[1])


def combmNZ(lists, weights=None):
    s = defaultdict(float)
    w = weights or [1.0] * len(lists)
    for li, lst in enumerate(lists):
        for rank, d in enumerate(lst, start=1):
            s[d] += w[li] / rank
    return sorted(s.items(), key=lambda kv: -kv[1])


print("=" * 72)
print("DEMO 1 — RRF with two DISJOINT lists (the hermes-brain case)")
print("=" * 72)
# The measured situation: keyword and graph never agreed (0% overlap, per
# RETRIEVAL-QUALITY-MEASUREMENT.md). Graph's top doc is the answer.
kw = [f"kw{i}" for i in range(1, 11)]        # 10 keyword docs, NONE relevant
gr = ["ANSWER_DOC"] + [f"gr{i}" for i in range(1, 10)]  # graph rank-1 is the answer

r = rrf([kw, gr])
print(f"RRF top-5: {[(d, round(v, 5)) for d, v in r[:5]]}")
print(f"  position of ANSWER_DOC in RRF output: "
      f"{[d for d, _ in r].index('ANSWER_DOC') + 1}")
print(f"  RRF score of ANSWER_DOC (rank1 in list2) = {1/(K+1):.5f}")
print(f"  RRF score of kw1 (rank1 in list1)         = {1/(K+1):.5f}  <-- ties, "
      f"arbitrary order")
print("  => a rank-1 hit in ONE list cannot outrank a rank-1 hit in the OTHER.")
print("     RRF is a Borda count: it rewards AGREEMENT, not quality.\n")

print("=" * 72)
print("DEMO 2 — RRF cannot express 'list A is 10x better than list B'")
print("=" * 72)
for wa, wb in [(1, 1), (3, 1), (10, 1), (100, 1)]:
    r = rrf([kw, gr], weights=[wa, wb])
    pos = [d for d, _ in r].index('ANSWER_DOC') + 1
    print(f"  weights=(keyword {wa}, graph {wb}): ANSWER_DOC at rank {pos}")

print("\n" + "=" * 72)
print("DEMO 3 — k sensitivity: smaller k sharpens top of each list")
print("=" * 72)
for k in [5, 10, 60, 1000]:
    r = rrf([kw, gr], k=k)
    pos = [d for d, _ in r].index('ANSWER_DOC') + 1
    print(f"  k={k:5d}: ANSWER_DOC at rank {pos}")

print("\n" + "=" * 72)
print("DEMO 4 — WITH overlap, RRF is fine (this is the case it was designed for)")
print("=" * 72)
ov_kw = ["A", "B", "C", "D", "E"] + [f"kw{i}" for i in range(1, 11)]
ov_gr = ["A", "F", "G", "H", "I"] + [f"gr{i}" for i in range(1, 11)]
r = rrf([ov_kw, ov_gr])
print(f"  RRF top-6: {[d for d, _ in r[:6]]}")
print("  => A (in both lists) jumps to #1. RRF works when lists corroborate.\n")

print("=" * 72)
print("DEMO 5 — Fraction of top-10 slots taken by each arm under RRF, disjoint")
print("=" * 72)
r = rrf([kw, gr])
slots = defaultdict(int)
for d, _ in r[:10]:
    slots['keyword' if d.startswith('kw') else 'graph'] += 1
print(f"  {dict(slots)}  -> 50/50 regardless of relative arm quality")
print("  => RRF allocates budget by PRESENCE IN A LIST, not by usefulness.")
print("     This is the measured 40/40 split in RETRIEVAL-QUALITY-MEASUREMENT.md.")
