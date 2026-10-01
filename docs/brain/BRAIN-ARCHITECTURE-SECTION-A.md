# BRAIN ARCHITECTURE — SECTION A: RETRACTIONS, CORRECTIONS, AND INVENTORY
Appended 2026-09-25. Supersedes nothing. Read after SCRATCHPAD.md Sections 0-9.

Evidence tags per SCRATCHPAD Section 0: [V] verified by me · [W] wiki · [R] researcher
· [?] unverified · [X] refuted.

================================================================================
## A1. RETRACTIONS OF MY OWN WORK (read this before trusting any of it)
================================================================================

The session of 2026-09-25 produced two documents and several conclusions that are
WITHDRAWN. They are named here so no future session reuses them.

**A1.1 [X] "I could not find any repo named Semantica."**
FALSE, and it was the single most costly error of the session. The vault already
ranked Semantica **#2 in the graph slot** and flagged that it was "surfaced from
the VAULT, not from external search. Nobody in the external research pass found
this. VALIDATES the 'search the wiki' instruction." I searched externally,
found nothing, and reported its absence — while the answer sat in
`~/.hermes/oracle/brain/research/semantica-graph-native-infrastructure-brain-architecture.md`.
This is R-J4 violated in its purest form: external-only search, and a confident
negative claim where the local vault held the fact.
See SCRATCHPAD §3 SLOT: GRAPH LAYER, RANK 2.

**A1.2 [X] The self-measured 14,589-file throughput benchmark — RETRACTED AS EVIDENCE.**
I generated a synthetic 14,589-file vault, ran graphify's markdown extractor, and
reported "4.6–4.7 s / 3,109–3,187 files/sec, nodes 58,356, edges 131,295, frontmatter
nested-key survival 0%". This violates **R-J2**: "You're not going to do any
measuring yourself... rely on lab grade measurements from outside researchers
rather than running the risk that you get something wrong again." The number is
not usable as a decision input and must not be cited in the architecture.
Note it also measured **only the deterministic structural pass**, while
SCRATCHPAD A-07 records the real corpus ingest at **13–22 hours** (A-10: a Markdown
corpus is a 100% LLM pass, A-08: the vault graph is currently being damaged by the
repo's own refresh script). A 4.6-second figure is off by four orders of magnitude
from the thing that matters, which is exactly the error R-J2 exists to prevent.

**A1.3 [?] The pyyaml packaging finding — KEPT AS A LEAD, NOT PROMOTED.**
That `pyyaml` is absent from graphify's declared dependencies, so nested
frontmatter and `aliases:` degrade under a fallback regex, is a code-reading
observation, not a measurement, and it is checkable by anyone. It is plausible and
worth one issue. It is **not** evidence about graphify's fitness. Tag [?] and let a
researcher confirm or kill it.

**A1.4 [V] What survived from that session (the only two facts worth keeping).**
Both are code-level, not performance-level, and both are cheap to re-verify:
  1. Graphify's markdown extractor is the **only** one in the compared set that
     parses `[[wikilinks]]` and YAML frontmatter. Verified by `gh api search/code`
     plus shallow-clone grep across LightRAG, cognee, Graphiti, microsoft/graphrag,
     RAGFlow. LightRAG's parser treats `---` as a GFM **table delimiter**.
  2. **RAGFlow's wikilink subsystem is a page GENERATOR, not a parser.** Its
     `knowledge_compiler/wiki` emits `related_kb_pages` slugs; `wiki-link-util.ts`
     parses internal app hrefs (`artifact/{id}/{type}/{slug}`), not `[[...]]` text.
     The 14 grep hits are not a counterexample to (1). This correction matters
     because a grep-based audit without reading the source would have looked like
     a contradiction.
Note: (1) and (2) say nothing about retrieval QUALITY on a Markdown+wikilink corpus.
No such published number exists for any candidate. That gap is recorded in B1.

**A1.5 Process failure to not repeat.** Two files were written to
`/home/operator/` instead of the scratch pad. The repo's working document is
`/home/operator/hermes-brain/SCRATCHPAD.md`; scratch is
`/home/operator/.hermes/cache/scratch/`. Neither is the home directory. Moved.

================================================================================
## A2. THE INVENTORY — EVERY BRAIN FUNCTION, AND WHO OWNS IT
================================================================================

Method: 32 build components from PROPOSED-BRAIN-ARCHITECTURE §4.1, cross-checked
against 225 vault topic dirs and the 10 modules in `brain/`. Coverage state per
function. "COVERED" = has a build component. "PARTIAL" = touched, no component.
"ABSENT" = vault has material, architecture has **no** component for it. The
ABSENT list is the actual work queue for Sections B–F.

--- ALREADY COVERED BY EXISTING WORK (do not redo) ---
B-1  Belief revision / AGM ............ DCPM chains, Atlas, IJCAI-2025, belief_set  §3.1
B-2  Counterfactual reasoning ......... C3→CRAFT engine, ActMem, frozen replay  §3.2
B-3  Theory of Mind .................. MetaMind, COKE/COLM, Dynamic ToM  §3.3
B-4  Procedural / habit ............... HiCL, MEMTIER, AWM, GraSP, SkillDAG  §3.4
B-5  Hippocampal indexing ............ HippoRAG PPR, mokosh SDR, HRR, CA3  §3.5
B-6  Cognitive routing / thalamus .... Sibelium CE, LIMEN, Gated-Memory  §3.6
B-7  Valence / emotion ................ swaylq, TOAQ, Maxim, pyClarion  §3.7

--- THE GAPS. Each gets a full dossier in Sections C–F. ---

C-1  **WORKING MEMORY** (dlPFC) — 7 slots + decay EXISTS (`cortex/dl_pfc.py`, 200
     lines) but there is no SLOT ALLOCATION POLICY, no interference model, no
     capacity law grounded in Cowan's 4±1 / Miller's 7±2. Vault:
     Working-Memory-and-Executive-Function/ (2), Executive-Control/ (9).
     The code exists; the *theory of how to use it* does not. §C.

C-2  **ATTENTION** — vault has 11 files in Attention/ (Feature Integration Theory,
     Attentional Residue, Frontoparietal Attention Networks) and 2 in
     Attention-Mechanisms/. The repo has a thalamus entropy gate (`thalamus/gate.py`,
     73 lines) and that is the whole of it. **There is no attention model, no
     selectivity-by-priority, no attention residue handling.** Top-down and
     bottom-up salience are collapsed into one entropy number. §D.

C-3  **METACOGNITION** — vault has 10 files (Feeling of Knowing, Confabulation,
     Dunning-Kruger replication debates, Epistemic Emotions) + 2 in
     Self-Reflection-and-Metacognition. The repo has `epistemic-protocol` as a
     *skill* and an `epistemology/` module, but no calibrated
     confidence-on-retrieval, no knowing-what-you-don't-know signal, no
     Feeling-of-Knowing analogue. **This is the single largest coherence gap**:
     the repo's own rules demand epistemic discipline and nothing implements the
     measurement that would let the agent know when it is wrong. §E.

C-4  **INCUBATION / INSIGHT** — vault Creativity-and-Insight/ has an
     `Insight-Problem-Solving-and-**Incubation Effects**.md` file. The DMN module
     has chronesthesia + counterfactual, but **nothing implements incubation** —
     the deliberate "stop thinking about it" loop that produces insight. One of the
     most reliably replicated findings in cognitive psychology, entirely absent.
     §F.

C-5  **CURIOSITY / INTRINSIC MOTIVATION** — vault Motivation-and-Curiosity/ (4)
     incl. Temporal-Discounting-Procrastination.md. Information gain is the
     textbook driver and the repo has no curiosity signal. The retrieval layer
     has no "I don't know enough about this" trigger. §F.

C-6  **SOCIAL COGNITION beyond ToM** — `brain/social/` has tom.py + pragmatics.py.
     Vault Social-Cognition/ (19) includes Argumentative-Theory-of-Reasoning,
     Cognitive-Dissonance-and-Self-Justification, Collaborative-Inhibition,
     Barnum-Effect. The **argumentative theory of reason** (Mercier & Sperber)
     is the most practically important thing in that directory — humans reason
     badly alone and well when arguing — and the repo has zero trace of it. §G.

C-7  **LANGUAGE-THOUGHT GROUNDING** — vault Language-and-Thought/, Numerical-
     Cognition/. How a word becomes a concept handle; the neural-symbolic gap.
     Relevant to the retrieval slot because **vocabulary mismatch is a retrieval
     failure mode** (query says "recall", doc says "remember"). Not modelled
     anywhere. §G.

C-8  **CAUSAL REASONING** — explicitly rejected in the architecture
     ("DoWhy — data-science causal inference, not agent cognition", §9). The
     counterfactual engine (§3.2.4) is a causal mechanism anyway, so the
     rejection and the build are in tension. Also vault Causal-Reasoning/ (2).
     Flagged in §G as a contradiction to resolve, not a gap to fill.

C-9  **WORLD MODELS / INTERNAL SIMULATION** — vault World-Models/ (3) incl.
     Model-Based-RL-and-Imagination-Based-Planning. Planning is covered by the
     PLANNING slot (LLM+P) but **prospective simulation before acting** is not.
     Related to C-4. §F.

C-10 **EMBODIED / GROUNDED SITUATION** — §5.14 deliberately excludes 226 files
     with the reasoning "our agent has no body; revisit only if the brain grows
     sensors." That is a defensible decision and it is recorded. But **Tool-Use-
     and-Extended-Mind/** (2, incl. Extended-Mind-Theorem files in
     Distributed-Cognition/) is the *non-biological* cousin: tools as cognitive
     scaffolding is squarely in scope for a tool-using agent and is currently
     unexploited. Split out from the embodied rejection. §G.

C-11 **CIRCADIAN / ULTRADIAN RHYTHM** — vault Circadian-Rhythms/ (2) + Sleep-and-
     Cognition/ (2) + Sleep-and-Offline-Processing/ (2) + Consolidation/ (6).
     Gaps G19/G31 say the NREM/REM mapping is [CONJECTURE]. The repo runs nightly
     consolidation on a cron. **Whether the schedule is right has never been
     analysed** — consolidation timing is one of the best-replicated findings in
     the whole memory literature (spacing effect), and it is currently a default
     value nobody chose deliberately. §F.

C-12 **SLEEP / OFFLINE REPLAY** — `hippocampus/replay.py` (92 lines) + dreaming
     plugin exist. Related to C-11; the phases are engineering, the *ordering and
     spacing* of them is unexamined. §F.

================================================================================
## A3. THE CONFLICT THAT MUST BE RESOLVED BEFORE ANY GRAPH DECISION
================================================================================

SCRATCHPAD §3 GRAPH LAYER, RANK 3 records an unreconciled contradiction:

> LightRAG's own paper claims 67.6–84.8% win rates.
> Third-party reproduction in the HippoRAG 2 paper scores it
> 16.6 / 2.4 direct and 1.6 / 11.6 / 2.4 multi-hop F1 — far below.
> "VERDICT PENDING: the two numbers cannot both be right. Must resolve."

**Why this matters more than the rank ordering:** the architecture's Phase 1 #4
is "HippoRAG multi-hop — fix graphify semantic pass → PPR over Neo4j → RRF merge
with pgvector." If graph fusion measurably *hurts* retrieval, that Phase 1 item
needs a different shape. The repo's own benchmark (commit 39e9fb6) found fused
0.708 vs keyword-only 0.792 — fusion LOSES 0.083. **But that benchmark is
self-flagged as void** (SCRATCHPAD A-03: the keyword arm indexes file PATHS only,
all three numbers are not like-for-like; A-04: the "oracle ceiling" is a
tautology). So the repo has a negative result from a broken instrument and a
pending positive from a paper. Neither is usable yet.

**Resolution requires (a) a correctly-built benchmark per A-03's own prescription
— labels from document CONTENT, exhaustive-keyword arm scoring ≤0.20 on the
multi-hop category or the queries are discarded, and mandatory full-context and
body-BM25 controls — and (b) the HippoRAG 2 tables fetched to see what
configuration was actually measured.** Both are researcher tasks under R-J2.
I do not resolve it here and I do not guess.

================================================================================
## A4. WHAT THE REPO ALREADY HAS (the base I build on, not re-invent)
================================================================================

`brain/` = 2,318 lines, 10 module dirs, 130 passing tests, `brain.db` + 3 schemas.
Working code exists for: thalamic gate + ring buffer · dlPFC (7 slots, decay) ·
executive control (Miyake triad) · router · AGM belief ops · defeater graph ·
dialectic · hippocampal associative (PPR stand-in) + replay · basal-ganglia
action gate (Go/No-Go, threshold 0.4) + compiler (threshold-3 skill compilation) ·
limbic somatic markers + valence · DMN chronesthesia + counterfactual ·
prospective intentions (340 lines, the largest file) · social ToM + pragmatics.

**A-12: six instances are constructed but never called in reasoning** — agm,
dialectic, chronesthesia, counterfactual, associative_graph, defeater_graph. Each
appears exactly once in `hermes_brain.py`, on the constructor line. The
infrastructure is built and unwired. **Wiring existing code is a cheaper first
win than any new build in the matrix**, and it is the correct Phase 0.

**A-13: `brain/` does not import Honcho.** Only a docstring mentions it. Honcho
replacement is an infra track, decoupled from brain architecture — do not let it
distort cognitive design decisions.
