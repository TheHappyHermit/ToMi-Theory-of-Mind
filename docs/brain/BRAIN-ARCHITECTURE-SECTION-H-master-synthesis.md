# BRAIN ARCHITECTURE — SECTION H: MASTER SYNTHESIS
The integration plan. Read last; Sections A–G are the inputs.

## THE ONE-PARAGRAPH VERSION

The repo has **2,318 lines of competent cognitive code that is wired to nothing and
fed no real data.** Six instances are constructed and never called; the 340-line
prospective-memory module has zero rows; all 106 belief rows are test fixtures with
a credence band of 0.90–0.95; three of seven architecture categories have no
component at all. Meanwhile the vault holds 2,065 files of well-sourced cognitive
science that is largely unread, and the three gaps that matter most —
**metacognition, attention, working-memory policy** — are the three the architecture
never mentions. The graph question is real but it is not the bottleneck; **a
correctness signal is**, because three separate missing capabilities (metacognition,
scheduled consolidation, and the retrieval benchmark) all reduce to "we do not
know when we are right."

## COVERAGE AFTER SECTIONS A–G

| brain function | state before | state after | section |
|---|---|---|---|
| belief revision / AGM | component exists, no data | same, **now quantified** | A2, G3 |
| counterfactual | component exists, unwired | contradiction with §9 resolved | C-8 |
| theory of mind | strongest component | + adversarial protocol | G2 |
| procedural / habit | component exists | unchanged | — |
| hippocampal indexing | component exists | + incubation role | F Rank 2 |
| cognitive routing | component exists | **needs confidence input** | C, D |
| valence / emotion | component exists, 1 marker row | + epistemic emotions | F C-5 |
| **working memory** | code, no policy | policy + interference model + 1 bug | **E** |
| **attention** | novelty filter mislabelled | top-down split + residue model | **D** |
| **metacognition** | **absent** | top-3, phased | **C** |
| **incubation** | **absent** | top-3, phased | **F** |
| **curiosity** | **absent** | top-3 + inverted-U rule | **F** |
| **social beyond ToM** | 2 files vs 19 vault | 3 candidates incl. CI warning | **G** |
| **language grounding** | **absent** | 3 candidates | **G** |
| causal | rejected *and* built | wording contradiction resolved | C-8 |
| **world models** | planning only | folded into incubation | F |
| embodied | deliberately rejected | **stays rejected** (correct) | C-10 |
| **tool-as-cognition** | swept into rejection | split out, transactive memory | C-10 |
| **circadian / sleep** | timer nobody chose | tagged scheduling + TMR | **F** |
| **heuristics library** | **no component at all** | 7 shortcuts + 3 rules | **G C-H** |

## THE CRITICAL PATH — ONE FOUNDATION, THREE CONSUMERS

Three separate components are blocked on the same absent thing. This is the single
most important structural fact in the whole build-out:

```
        ┌─────────────────────────────────────────┐
        │  retrieval_log + confidence_log        │
        │  append-only, written by the retriever │
        └───────────────┬─────────────────────────┘
                        │
        ┌───────────────┼───────────────┬────────────────┐
        ▼               ▼               ▼                ▼
   C metacognition   C-11 schedule   A-03 benchmark   C-H shortcuts
   (calibrate on     (tag + recall   (is the          (fire on high
    own history)      history)        retriever        confidence,
                                     correct?)         escalate when low)
```

Build it once, in Phase 0, and four components become possible. Skip it and each is
built blind, with no way to tell whether it works. **It is instrumentation, not a
performance claim, so building it does not breach R-J2** — logging what happened is
not measuring a hypothesis.

## PHASE ORDER — cheapest first, unblocking first

**PHASE 0 — wire what exists. No new components. This is the whole first milestone.**
1. Wire the six unwired instances (A-12: `agm`, `dialectic`, `chronesthesia`,
   `counterfactual`, `associative_graph`, `defeater_graph`). Each is already
   written; each currently costs nothing and does nothing.
2. `retrieval_log` + `confidence_log`. (Critical path.)
3. Fix the `_evict_lowest` policy in `dl_pfc.py` — state it, extract `_eviction_score`,
   add a test. (Section E1. 20 minutes.)
4. Per-category slot quotas. (Section E Rank 3. Same file.)
5. State the C-8 wording fix: reject DoWhy's *observational* causal inference, keep
   the counterfactual engine. Text-only.
6. Make `source_location` mandatory on the answer path. (Section C Rank 2. The vault
   rule already requires provenance — this makes it mechanical.)

Rationale for 0 existing: **steps 1, 3, 4 and 6 are all small, all unblock real
capability, and none depend on any research question.** Everything in Phase 1+ does.

**PHASE 1 — the confidence layer (C).**
`brain/cortex/confidence.py` emitting `(confidence, evidence_ids, mechanism)` per
answer; calibration computed from our own log. Depends on Phase 0 step 2. This is
the root component: routing, scheduling, and the shortcut library all consume it.

**PHASE 2 — attention (D) and working-memory interference (E).**
Rank 1 in each. The gate stops scoring character entropy; the slot register stops
accepting silent contradictions. Both make Phase 1's signal *usable*, because
confidence is meaningless if the register is full of unreconciled claims.

**PHASE 3 — the benchmark (A-03), correctly this time.**
Labels from document content. Exhaustive-keyword arm must score ≤0.20 on multi-hop
or the queries are discarded. Mandatory full-context and body-BM25 controls. No
"oracle ceiling" tautology. **Until this exists, every retrieval claim in the repo
is unmeasured** — including the graph-fusion question in A3.

**PHASE 4 — the graph decision, informed by Phase 3.**
Resolve the LightRAG-vs-HippoRAG contradiction (A3) with a correct instrument.
Whether the answer is "graphify" or "oxigraph" or "keep graphify for wikilinks and
Oxigraph for durability" is a Phase 4 output, not a Phase 0 input. **Do not revisit
it before Phase 3 lands** — the current benchmark says fusion hurts, the current
paper says it helps, and the instrument is known-broken.

**PHASE 5 — offline cluster (F).** Tags, interval scheduling, incubation queue,
curiosity priority, homeostatic downscale. Depends on Phase 1 for confidence.

**PHASE 6 — social protocol (G) and language grounding (G).** Adversarial
multi-instance, category-partitioned merges, transactive memory map, query expansion.

## WHAT THIS DOES NOT DECIDE

- **The graph winner.** Deferred to Phase 4 on purpose. A3 explains why.
- **Honcho replacement.** Infra track, explicitly decoupled (A-13). Must not distort
  cognitive design.
- **Any performance number.** R-J2. Where a section above says "measure X", that
  means *log X*, and the efficacy claim requires a researcher.
- **The 226 rejected embodied files.** The rejection is correct. Reopening it needs
  sensors, not arguments.

## THE FIVE THINGS THAT WERE WRONG IN MY OWN WORK, FOR THE RECORD

Listed in A1 so no future session reinstates them: the self-measured throughput
benchmark (breaches R-J2, and measured the wrong stage); "Semantica not found" (false
— the vault had it at #2); two files written to the home directory instead of the
scratch pad; the belief-table name in G3 (I wrote `beliefs`; it is
`cognitive_beliefs`) which I caught by querying instead of asserting; and the
underlying habit those share — **producing confident output before reading what
already existed.**

## READING ORDER FOR THE NEXT SESSION
1. This file.
2. A1 — do not reuse anything retracted there.
3. A3 — the one unresolved contradiction.
4. Phase 0 — it is six small tasks and none of them need research.
5. Sections C–G on demand, by component.
