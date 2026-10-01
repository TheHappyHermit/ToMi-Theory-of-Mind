# BRAIN ARCHITECTURE — SECTION E: WORKING MEMORY (C-1)
Read after Section A. Shortest gap, closest to done — and it contains a bug.

## WHAT EXISTS

`brain/cortex/dl_pfc.py` (200 lines) is the most complete single module in the
repo. It has: `WorkingMemorySlot` (key, value, importance, category, activation,
last_accessed), a capacity bound defaulting to **7** citing Miller/Cowan, a goal
stack, per-turn decay with goals exempted, eviction, context rendering, and
sqlite snapshot/restore. It is competently written.

**So the gap is not "build working memory." It is that the policy inside it is
unexamined, and one piece of it is provably wrong.**

## E1. A BUG: EVICTION SCORES THE WRONG WAY ROUND

```python
def _evict_lowest(self):
    sorted_slots = sorted(self.slots.items(),
                          key=lambda item: item[1].activation * item[1].importance)
    evict_key = sorted_slots[0][0]      # evicts the LOWEST activation*importance
```

`activation` decays toward 0 for everything not `touch()`ed. `importance` is a
static per-slot field. The product therefore falls monotonically with time for
untouched slots and the method evicts the **longest-untouched** slot. For a
*capacity* system that is a defensible LRU policy.

The problem is the interaction with decay. Because activation is a *decaying
multiplier* and importance is *fixed*, a slot with `importance=0.9` and
`activation=0.2` (score 0.18) is evicted **before** a slot with `importance=0.1`
and `activation=1.0` (score 0.10)? No — 0.18 > 0.10, so the low-importance fresh
slot dies. **A freshly-added, freshly-touched, low-importance scratchpad note is
evicted ahead of a long-lived, faded, high-importance goal-adjacent fact.** The
product form makes recency and importance trade off multiplicatively with no way
to express "this matters a lot even if I have not touched it in a while" — which
is precisely the case for a `constraint` or `fact` slot that was correct when
written and needs no re-touching.

Whether that is a bug depends on intent, and **the intent is written nowhere**. The
docstring says "Cowan/Miller capacity bounds" and nothing about the scoring rule.
That absence of a stated policy *is* the finding. Two candidate policies
(recent-first LRU vs. importance-first) produce opposite behaviour on exactly the
inputs this repo cares about, and the code silently picks one.

**Recommendation:** state the policy explicitly in the docstring, make the scoring
function a named, tested, swappable function (`_eviction_score(slot) -> float`),
and decide between LRU and importance-dominant with an actual test. This is a
20-minute fix and it converts an accident into a decision.

## E2. THE REAL GAP: NO INTERFERENCE MODEL

Working memory is not a cache. It is a **limited-capacity register with interference
between representations** — the reason humans get 4±1 items, not 7, is that
similar items collide, not that the register is physically small. Cowan's embedded-
figures work and Oberauer/Trick's binding studies are the canonical evidence, and
`Working-Memory-and-Executive-Function/` in the vault points at exactly this.

The current implementation has capacity but **no similarity notion**. Any two slots
can occupy the register regardless of overlap, and any two slots can be rendered
into the prompt regardless of whether they conflict. Consequences:

- Two slots holding **contradictory** versions of a fact both survive and both reach
  the prompt. The model is asked to reconcile them silently. This is the mechanism
  behind most "the agent contradicted itself an hour later" failures, and it is
  invisible because no code checks for it.
- Two slots holding **near-duplicate** facts consume two of seven slots and provide
  one unit of information. Capacity is spent on redundancy.
- `defeater_graph.py` tracks rebutting/undercutting defeaters over *beliefs*, but
  slots and beliefs are different stores and nothing connects them.

**This is the single most important thing to add to working memory**, and it is
where the vault's `Source-Monitoring-Framework` and `Confabulation` connect:
conflicting content in the register is the precondition for confabulation.

## TOP 3 CANDIDATES

**RANK 1 — Interference-aware admission with contradiction detection.**
On admission, check the new slot against every existing slot for (a) semantic
contradiction and (b) near-duplication. Contradiction does not silently coexist —
it either supersedes (per the DCPM `superseded_by` chain already specced in B-1
Phase 1 #1) or is held with both versions marked and surfaced as a conflict.
- PRO: uses infrastructure that already exists or is already Phase 1
  (DCPM supersedes chains). Not a new mechanism — a *connection* between two
  existing ones that is currently missing.
- PRO: fixes a real, observable failure class (self-contradiction across turns) for
  very little code.
- PRO: near-duplicate detection is also a **cost** win — it stops the context window
  being filled with two copies of the same fact.
- CON: contradiction detection needs an LLM call or an NLI model. Cost is
  explicitly not a constraint (R-J1) but *latency* is a real concern on the turn path.
- CON: false positives on legitimately-revised beliefs (a fact that changed is not a
  contradiction). Mitigation: only compare within a category, and prefer the
  supersedes-chain over a contradiction verdict.
- BUILD: `admit(slot)` returns a verdict in {new, duplicate, supersedes, conflicts}.
  Log every verdict. Conflicts surface in `render_context_summary` as an explicit
  marker, not as two adjacent unmarked claims.

**RANK 2 — Chunked retrieval à la ACT-R / working-memory-as-partial-activation.**
Treat a slot as a partially-activated representation with a retrieval operator that
*completes* it from the store on demand, rather than a slot holding a whole
rendered fact. Vault: `Cognitive-Architecture-ACTR.md` maps ACT-R modules to agent
components directly and names Declarative Memory → Oracle Brain.
- PRO: matches how the evidence says capacity works — partial activation plus
  completion, not seven full items.
- PRO: composes with C-3 (metacognition): FOK is literally "partial activation that
  will complete on a proper cue."
- CON: a significant redesign of a working module that currently works.
- CON: the completion cue problem is hard and is really C-2/C-3 wearing a hat.
- RECOMMENDATION: **do not build this as a replacement.** Build it only after
  C-3's FOK signal exists, because partial activation without a completion signal
  is just lossy caching.

**RANK 3 — Explicit category partition (goal/constraint/fact/hypothesis/scratchpad
with per-category quotas).**
`category` already exists on the slot and is already exempted from decay for
`goal`. Give each category its own budget (e.g. goal: 1, constraints: 2, facts: 3,
hypothesis: 1, scratch: unbounded-and-cheap) so a flood of scratch facts cannot
evict the constraint that defines the task.
- PRO: nearly free — the field exists, the eviction path exists.
- PRO: fixes the sharpest version of the E1 problem (constraints being evicted by
  chatter) without any new machinery.
- PRO: matches how attention §D Rank 1 is going to bind goals anyway — the
  category is the natural home for a quota.
- CON: hand-chosen quotas are another unexamined default, in a different place.
  Mitigate by making them config, and by **measuring** slot-occupancy distribution
  over real runs before fixing values. That measurement is instrumentation, so it
  does not breach R-J2.
- BUILD: capacity becomes `Dict[str, int]`; `_evict_lowest` becomes per-category.

### Why not the rest
- **Hierarchical-Planning-Recursive-Decomposition** (vault) — planning, covered by
  the PLANNING slot (LLM+P) and §9. Not a working-memory mechanism.
- **Cognitive-Flexibility-Set-Shifting** — that is §D attention, not register policy.
- **Inhibitory-Control-Go-NoGo** — the action gate already covers it (B-6/B-3).

## THE COST CONNECTION, WHICH IS THE ACTUAL ARGUMENT FOR RANK 1
Every rank here is defensible on its own merits. Rank 1 wins because of a number the
repo already has: **A-03 establishes that the keyword arm indexes file paths only
and therefore cannot see body content.** A slot holding a fact that is *in the
corpus but not in any filename* is invisible to that index. Contradiction detection
and the proper binding of facts to slots is what makes body-derived content usable
at all. Ranks 2 and 3 improve how well the register works; Rank 1 determines
whether the register's contents are *true and non-redundant*, which is the
precondition for every downstream consumer.

## SEQUENCE
Phase 0: state the eviction policy; extract `_eviction_score`; add the test. (E1, trivial)
Phase 0: per-category quotas (Rank 3, trivial, same file).
Phase 1: contradiction/duplicate admission (Rank 1) + conflict markers in rendering.
Phase 2+: ACT-R partial activation (Rank 2), gated on C-3.
