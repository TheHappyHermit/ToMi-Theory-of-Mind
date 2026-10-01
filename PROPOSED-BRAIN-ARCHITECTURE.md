---
okf_version: "1.0"
id: proposed-brain-architecture
title: "Proposed Hermes Brain Architecture"
description: "Consolidated research-backed proposal for extending Hermes's cognitive architecture with 7 brain subsystems. Every component carries an evidence tier, verification status, benefits/negatives, integration plan, and rejected-alternatives rationale."
type: architecture_proposal
status: draft-v2
created: 2026-09-23
updated: "2026-09-25T05:05:00Z"
generated:
  by: "hermes-agent"
  at: "2026-09-23T22:00:00Z"
verified:
  - "2026-09-23 researcher delegation audit of 18 candidate projects (session 20260923_080823_fe0fcf3b)"
  - "2026-09-23 three-round wiki coverage audit (active-wiki + Oracle brain, graphify nodes + ripgrep + broad concept sweep)"
  - "2026-09-24 venue re-verification pass: 7 [VENUE-UNVERIFIED] flags resolved (4 CONFIRMED, 1 PARTIAL, 2 preprint-only) — research/venue-verification-brain-architecture-2026-09-24.md"
stale_after: "2027-03-23"
tags:
  - brain-architecture
  - cognitive-architecture
  - hermes
  - hermes
  - implementation-plan
  - research-synthesis
  - evidence-tiers
sources:
  - research/BUILD-PLAN-AGENDA.md (Oracle brain copy holds the 40 brain-architecture agenda items; see §10.4)
  - research/dcpm-dual-process-belief-trajectory-tracking.md
  - research/procedural-tier-integration-cyclic-fps.md
  - research/memory-tier-integration-followup.md
  - research/memory-write-admission-and-retrieval-recovery.md
  - research/neo4j-graph-database-agent-memory.md
  - research/mragt-cue-tag-content-reconstruction.md
  - "session:default/20260923_080823_fe0fcf3b (verification + wiki audit session, 2026-09-23)"
confidence: high-with-caveats
---

# Proposed Hermes Brain Architecture

**Version:** 2.2 (venue-verification pass applied)
**Last Updated:** 2026-09-24T04:30:00Z
**Status:** DRAFT — for review, editing, and lane dispatch
**Supersedes:** v1 (2026-09-23T10:30:00Z — components without evidence dossiers) and v2.0 (2026-09-23T22:00:00Z — dossiers without the neuroanatomical map, master matrix, and full audit tables)

---

## What Changed in v2 and Why

Version 1 listed 31 components across 7 categories with certainty labels, but it did not document *why* each component was chosen, *what exactly* the research behind it says, *how each program actually works*, what the alternatives in each space were and why they lost, or which claims had been independently verified versus merely carried from a project's README. the operator's directive (2026-09-23, recorded verbatim in §10.1) was explicit:

> "Low wiki coverage does not mean that it's not a strong idea. It just means that we have limited information on it. I want you to update the backgrounds of each of these things with the relevant information from your research regarding how the program works, how the research works, where they're different, whether they're the same and any other details that are necessary so that this file with the proposal has backing and references and benefits and negatives and everything well thought through... What's research backed? What's community backed? What is backed by papers but not by peer review and what is theoretical or conjecture but probably worth adding... and why you're not using the other options in each space along with why you chose what you did for each individual thing all in that file."

v2 therefore:

1. **Adds a per-component dossier** for every component: mechanism (how the program works), the research behind it (how the research works), sibling comparison (where they differ / whether they're the same), benefits, negatives, concrete Hermes integration plan, why it was chosen, and which alternatives were rejected and why.
2. **Replaces the 4-level certainty scale with 4 evidence tiers** that separate *peer review* from *preprint* from *community code* from *theory/conjecture* (§0.1), and stamps every component with its tier **plus a per-claim verification status** — because the 2026-09-23 audit found that venue claims in this space are frequently wrong (§0.2, §0.5).
3. **Merges two research streams that v1 kept separate**: the 40 agenda items (belief revision, counterfactual, ToM, routing, procedural, hippocampal, emotion) and the 18-project verification audit (epica, atlas, HiCL, omega-hippocampus, MemoBrain, SCRUBJAY-MEM, TrustMem, CogniFold, MemCog, NexusCortex, biomind, Maxim, snath-ai/DMN, defaultmodeAGENT, CogFlow, COKE, MetaMind, Sibelium).
4. **Adds 10 concept areas the wiki already covers heavily but v1 omitted** (Global Workspace Theory, HTM/Numenta, ZenBrain, BrainMem, MRAgent, Complementary Learning Systems, Sleep Cognition, Emotion-Cognition, Predictive Processing, Interoception) — §5.
5. **Revises implementation phasing to be evidence-tier-driven, not wiki-coverage-driven.** Per the directive, low wiki coverage no longer demotes a component; it just means the dossier carries an "information limited" flag.
6. **Adds a full records & audit trail** (§10): verification session records, the three-round wiki coverage numbers, corrections log, and agenda cross-references.

**Added in v2.1** (same day, after checking v2.0 field-by-field against the full three-round audit):

7. **Neuroanatomical map (§2.5)** — every component tied to the brain region whose function it emulates: the direct answer to "what part of the brain does this fill?"
8. **Master component matrix (§4.1)** — one row per build component: tier, brain part, phase, integration cost, verification status — the at-a-glance view for future critique and comparison against alternatives.
9. **§5 expanded from 12 to 23 concept areas** — every Round-3 concept from the audit now has an explicit disposition (added / backdrop / already-implemented), not just the original ten.
10. **Full audit tables preserved verbatim (§10.2)** — Round 2 as a complete 30-row table in the audit's own order, Round 3 as a 34-row disposition table, plus the raw-session counts.
11. **Audit-recommendations disposition record (§10.2.1)** — which audit recommendations were adopted, which were overridden by the 2026-09-23 directive, and why — so future reviewers can re-litigate with full context instead of re-discovering the disagreement.
12. **Future-review guide (§0.6)** — how to read, critique, compare, and extend this document.

---

## Table of Contents

- [§0 Methodology & Evidence Standards](#0-methodology--evidence-standards)
  - [0.1 Evidence Tiers](#01-evidence-tiers)
  - [0.2 The 2026-09-23 Verification Audit (18 projects)](#02-the-2026-09-23-verification-audit-18-projects)
  - [0.3 Wiki Coverage Audit (3 rounds)](#03-wiki-coverage-audit-3-rounds)
  - [0.4 Provenance Rules Used in This Document](#04-provenance-rules-used-in-this-document)
  - [0.5 Corrections Log](#05-corrections-log)
  - [0.6 How to Read, Critique, and Extend This Document](#06-how-to-read-critique-and-extend-this-document)
- [§1 Existing Brain Infrastructure](#1-existing-brain-infrastructure)
- [§2 Architecture Overview](#2-architecture-overview)
  - [2.5 Neuroanatomical Map](#25-neuroanatomical-map--what-part-of-the-brain-each-piece-fills)
- [§3 Category Dossiers](#3-category-dossiers)
  - [3.1 Belief Revision](#31-category-1-belief-revision)
  - [3.2 Counterfactual Reasoning](#32-category-2-counterfactual-reasoning)
  - [3.3 Theory of Mind](#33-category-3-theory-of-mind)
  - [3.4 Procedural Memory](#34-category-4-procedural-memory)
  - [3.5 Hippocampal Indexing](#35-category-5-hippocampal-indexing)
  - [3.6 Cognitive Routing](#36-category-6-cognitive-routing)
  - [3.7 Valence / Emotion](#37-category-7-valence--emotion)
- [§4 Verified-Project Dossier Cross-Reference](#4-verified-project-dossier-cross-reference)
  - [4.1 Master Component Matrix](#41-master-component-matrix)
- [§5 Wiki-Backed Concepts Added in v2](#5-wiki-backed-concepts-added-in-v2)
- [§6 Build-From-Paper Specifications](#6-build-from-paper-specifications)
- [§7 Existing-to-Proposed Mapping](#7-existing-to-proposed-mapping)
- [§8 Full Data Flow](#8-full-data-flow)
- [§9 Implementation Priority Order (Evidence-Tier Driven)](#9-implementation-priority-order-evidence-tier-driven)
- [§10 Records & Audit Trail](#10-records--audit-trail)
- [§11 Complete Gap List](#11-complete-gap-list)
- [§12 Categories With No Adequate Solution](#12-categories-with-no-adequate-solution)
- [§13 File Locations & Cross-References](#13-file-locations--cross-references)
- [§14 References](#14-references)
- [Appendix: Summary Statistics](#appendix-summary-statistics)

---

## 0. Methodology & Evidence Standards

### 0.0 What This Project Claims (and Does Not)

**Hermes Brain is a biologically inspired cognitive architecture for AI agents.** It
implements selected *functional principles* drawn from human cognition — episodic
memory, attention and gating, offline consolidation, belief revision, action
selection, and associative indexing — inside a software system.

It does **not** claim to reproduce the human brain, human consciousness, or
human-level general intelligence. "Replicate a human brain" is not a defensible
public claim for a system like this and is not used anywhere in this document.

The distinction is not lawyerly; it is the difference between a claim that
survives review and one that does not:

| Claim type | Example | What it requires |
|---|---|---|
| Implementation | "The system has an episodic-memory module." | Code, tests, schema |
| Algorithmic | "The module is inspired by hippocampal replay." | Citation + explicit mapping to the code |
| Behavioral | "The module improves delayed recall on task X." | Benchmark, matched baseline, ablation |
| Biological | "The module reproduces hippocampal dynamics." | Neuroscience data + validation |
| Phenomenological | "The system is conscious." | Independent evidence. Do not assert. |

This document makes claims of the first three kinds. Where a fourth- or
fifth-kind claim would be tempting — consciousness from the LIMEN attention
auction (§12.3), a literal NREM/REM mapping (§12.2) — it is explicitly marked
`[CONJECTURE]` and labelled an engineering heuristic.

**One pattern worth stating plainly, because it governs how the evidence tiers
below should be read.** Where a peer-reviewed LLM win exists in this space, the
win is attributable to an ordinary engineering primitive, and the
cognitive-science framing is explanatory narrative on top of it:

* **Hippocampal indexing** — the benchmark result is graph construction plus
  Personalized PageRank retrieval (HippoRAG, NeurIPS 2024). The Teyler & DiScenna
  indexing theory is a legitimate and useful *model* of what that pipeline does;
  it is not the cause of the +20% multi-hop QA improvement.
* **CLS dual-store** — the win is a compressor with a sound write policy
  (SimpleMem, ICML 2026; A-MEM, NeurIPS 2025). The complementary-learning-systems
  account explains *why* two stores beat one; it does not itself produce the gain.

That is not a criticism of the work — it is an accurate description of where the
causal credit lies, and stating it protects the project's credibility when a
reviewer asks "what exactly made this faster?"

**Two cautions carried through this document.** First, the memory benchmarks most
published results rest on are weaker than they look: LoCoMo (ACL 2024) carries a
6.4% answer-key error rate and a permissive LLM judge, and independent controls
find the quality ceiling is the backbone rather than the memory system. Second,
the two most brain-inspired proposals here that *have* been adversarially tested —
functional Theory of Mind across agents, and multi-agent belief merging — scored at
or near zero in those tests, and multi-agent failures compound with agent and
iteration count. Those are recorded as open gaps in §11 (G2, G9, G10) rather than
as expected wins.

### 0.1 Evidence Tiers

Every component in this proposal is stamped with exactly one tier. The tiers answer the operator's question directly: *what's research backed, what's community backed, what's paper-backed but not peer reviewed, and what's theoretical or conjecture but probably worth adding.*

| Tier | Label | Definition | What it permits | Count |
|------|-------|------------|-----------------|-------|
| **T1** | PEER-REVIEWED | Published at a venue independently verified in the 2026-09-23 audit, or foundational literature (pre-2015 textbooks/major-journal work) where the venue is not in doubt | Implement as an anchor component; claims may be cited as established | 12 |
| **T2** | PREPRINT | Real paper (arXiv or equivalent) describing the mechanism, but no verified peer-review venue | Implement the *mechanism*; treat reported numbers as author-claimed; verify venue before citing as established | 14 |
| **T3** | COMMUNITY CODE | Public repository with working code, no peer-reviewed publication. README claims are self-assertions | Use where code review shows real value; never cite its claims as research backing | 16 |
| **T4** | THEORETICAL / CONJECTURE | No paper and no code, or code/paper exists but the *application to LLM agents* is conjecture | Prototype only; label as experimental; no production claims | 6 |

Two orthogonal flags modify any tier:

- **[VERIFIED-2026-09-23]** — a researcher delegation independently confirmed existence, venue, and integration path on 2026-09-23 (see §0.2).
- **[VENUE-UNVERIFIED]** — the component cites a venue that our audit did **not** check. The claim is carried from v1 or from wiki analysis files and must be re-verified before the component is cited as peer-reviewed.
- **[INFO-LIMITED]** — wiki coverage is thin (§0.3). Per the 2026-09-23 directive this does **not** demote the component; it means our internal analysis is shallow and the dossier leans on primary sources.

**Foundational-literature rule:** classical cognitive-science results (AGM/Gärdenfors 1985, Pollock defeasible reasoning, Pearl's causal hierarchy, Tulving's chronesthesia, Marr, Baars' Global Workspace 1988, Damasio's somatic marker hypothesis, Rolls & Treves 1998, Miyake et al. 2000 executive functions, Plate 2003 HRR, Grice 1975, Anderson's ACT-R, McClelland/McNaughton/O'Reilly CLS 1995, Ahmad & Hawkins 2015 HTM) are treated as T1 *for the theory itself*. Any specific *implementation* of them (a repo, a paper system) is tiered separately on its own evidence.

### 0.2 The 2026-09-23 Verification Audit (18 projects)

On 2026-09-23 a researcher delegation was dispatched with one instruction: be very skeptical; for each project confirm (1) it exists, (2) its claimed research backing is genuine, (3) it can integrate with a Python-based agent stack (Hermes + Hermes Brain). Full session record: `@session:default/20260923_080823_fe0fcf3b`. Results:

**Peer-reviewed — venue confirmed by the audit (3 of 18):**

| Project | Venue (verified) | What the audit confirmed | Integration |
|---------|------------------|--------------------------|-------------|
| **COKE** (jincenziwu) | ACL 2024 **long paper** (not oral — v1 draft had said oral; corrected) | COLM = LLaMA-2 + COKE, 45,369 cognitive chains, HuggingFace model available | Easy — Python/HF; llama.cpp needs GGUF conversion |
| **HiCL** (kushalk173-sc) | **AAAI 2026** (confirmed via ojs.aaai.org) | Hippocampal-inspired continual learning: DG-gated MoE, pattern separation/completion, SWR replay, EWC consolidation; Python/PyTorch | Easy — Python/PyTorch; needs GPU for training loops |
| **MetaMind** (XMZhangAI) | **NeurIPS 2025 spotlight** (confirmed) | Three-agent pipeline: ToM Agent → **Moral Agent** (not "Norm Agent" — corrected) → Response Agent; social memory; 35.7% improvement claim is the paper's | Easy — pattern implementable in Python/prompts |

**Preprints — real papers, no verified venue (6 of 18):**

| Project | Paper | Status | Code |
|---------|-------|--------|------|
| **MemoBrain** | arXiv:2601.08079 (Jan 2026) | Preprint | **No repo** — build from paper |
| **CogniFold** | arXiv:2605.13438 | Preprint | Has GitHub repos |
| **MemCog** | arXiv:2605.28046 (Tencent WeChat) | Preprint | No public code |
| **TrustMem** | arXiv:2606.25161 (Samsung AI + Notre Dame) | Preprint | No repo |
| **SCRUBJAY-MEM** | arXiv:2608.04746 | Preprint | No repo |
| **CogFlow** | arXiv:2509.22546 | Under review | — |

**Community code — real repos, zero peer-reviewed publication (9 of 18):**

| Project | Language | Audit finding | Integration |
|---------|----------|---------------|-------------|
| **epica** (angelnicolasc) | Rust, 12 crates, MCP-native, PyO3 SDK | "Grounded in 5 arXiv papers" is self-citation, not independent backing | Easy via MCP |
| **atlas** (RichSchefren — **not** angrysky56 as first claimed) | Python/Neo4j, MCP server | "49/49 AGM postulates verified" is a README assertion, never independently verified | Easy via MCP |
| **snath-ai/DMN** | Pure Python | JEPA integration lives in a separate repo; no papers | Easy |
| **defaultmodeAGENT** (EveryOneIsGross) | Python | No papers | Easy |
| **omega-hippocampus** | Rust crate v1.1.0 | DG/CA3/CA1, place cells, grid cells, SWR replay — claims confirmed present in docs, but no papers | Harder — Rust FFI |
| **Sibelium** (lealoth) | Python + llama-cpp + ChromaDB | **34** mechanisms (not 32 — corrected); CE formula confirmed in code; no verified publication (an "ICLR 2026 Workshop" claim circulated earlier was not confirmed by the audit) | Easy |
| **biomind / HIPECA v2.5** | Python | QualiaMetrics dataclass exists; no papers | Easy |
| **Maxim** (dennys246) | Python | NAc reward/punishment learning, eligibility traces, PainBus; no papers | Easy |
| **NexusCortex** (Emotion module) | Go | Valence-arousal state; "137 tests" claim unverified; Go blocks direct Python use | Hard — needs gRPC/CGo bridge or port |

**The audit's headline finding:** only 3 of 18 projects carry verified peer review. The rest are preprints or READMEs. This is why v2 separates tiers so strictly — in this space, confident-sounding claims ("formally verified", "49/49 postulates", "ACL oral") repeatedly failed verification.

### 0.3 Wiki Coverage Audit (3 rounds)

Same session, three rounds of coverage measurement against the active wiki (`~/.hermes/active-wiki`) and Oracle brain (`~/.hermes/oracle/brain`). Full tables preserved in §10.2. Summary:

**Round 1 — Graphify audit (superseded 2026-09-25).** *This paragraph previously reported
live node and edge counts read from a local install. Two problems: those counts are personal
derived data that has no place in a shared repository, and the "0 edges" reading was wrong —
graphify stores relationships under a `links` key, which that audit did not check, so it
reported zero for graphs that in fact carry tens of thousands of relationships. Node-level
per-category counts (HippoRAG, Sibelium, Basal Ganglia, Chronesthesia) were likewise local
observations and have been removed. See §0.7 for what the repository's graph layer actually
does. A reusable health check now ships as `scripts/graphify_health.py`, which reads both
`edges` and `links` and exits non-zero on a graph that cannot be traversed.**

**Round 2 — ripgrep content search (file counts):**

| Concept | Active | Oracle | Total | Read |
|---------|--------|--------|-------|------|
| Theory of Mind | 281 | 1,277 | 1,558 | Very strong |
| Valence / Emotion | 374 | 1,164 | 1,538 | Very strong |
| Counterfactual Reasoning | 130 | 542 | 672 | Strong |
| Procedural Memory | 99 | 247 | 346 | Strong |
| Cognitive Routing | 85 | 273 | 358 | Strong |
| Hippocampal Indexing | 43 | 249 | 292 | Moderate |
| Belief Revision / AGM | 37 | 74 | 111 | Moderate |
| DCPM | 74 | 128 | 202 | Strong (331-line dedicated analysis) |
| Memory Tier / MEMTIER | 79 | 119 | 198 | Strong (446-line dedicated analysis) |
| HippoRAG | 16 | 27 | 43 | Thin |
| MetaMind | 1 | 5 | 6 | **INFO-LIMITED** |
| Sibelium | 0 | 13 | 13 | **INFO-LIMITED** |
| GraSP | 18 | 73 | 91 | Thin |
| AWM | 11 | 28 | 39 | Thin |
| swaylq / TOAQ / pyClarion | 0 | 0 | 0 | **INFO-LIMITED** |
| LIDA | 355 | 914 | 1,269 | **Misleading** — mostly "licensing" false positives; actual LIDA cognitive-architecture coverage is near zero |

**Round 3 — concepts well-covered in the wiki but absent from the v1 proposal:** Global Workspace Theory (117 files), HTM/Numenta (631), ZenBrain (42), BrainMem (170), MRAgent (15), Complementary Learning Systems (173), Sleep Cognition (107), Emotion-Cognition directory (109), Predictive Processing (274), Interoception (51). All ten are added in §5.

**How coverage is used in v2:** coverage measures *our internal analysis depth*, not component quality. A thin-coverage component gets an [INFO-LIMITED] flag and its dossier leans on the primary source (paper/repo) instead of wiki synthesis. It is **not** demoted. Conversely, high coverage does not certify a component — LIDA's 1,269 "hits" were almost entirely false positives.

### 0.4 Provenance Rules Used in This Document

Per the epistemic protocol (skills/cognitive-protocols/epistemic-protocol):

- **[VERIFIED-2026-09-23]** — confirmed by researcher delegation (§0.2).
- **[VENUE-UNVERIFIED]** — venue cited but not checked by our audit; verify before citing.
- **[README-CLAIM]** — the project's own assertion about itself; evidence of what the project *claims*, not what it does.
- **[MODEL-KNOWLEDGE]** — established literature recalled from model training, used only for foundational cognitive science (see foundational-literature rule, §0.1). Flagged so a future pass can replace with direct citations.
- **[CONJECTURE]** — our own design reasoning with no external backing. Always labeled.

Numbers reported by papers (e.g., "+51.1% WebArena") are always the *paper's claim*, not our measurement, unless explicitly marked otherwise.

### 0.5 Corrections Log

Claims that circulated in this project's history and failed (or partially failed) verification. Recorded so they never silently return:

| # | Original claim | Reality | Where corrected |
|---|----------------|---------|-----------------|
| 1 | COKE was "ACL 2024 oral" | ACL 2024 **long paper** | v1 §Category 3; audit §0.2 |
| 2 | atlas author "angrysky56" | **RichSchefren** | v1 §Category 1; audit §0.2 |
| 3 | MetaMind has a "Norm Agent" | **Moral Agent** | v1 §Category 3; audit §0.2 |
| 4 | Sibelium has "32 mechanisms" | **34 mechanisms** | v1 §Category 6; audit §0.2 |
| 5 | Sibelium "ICLR 2026 Workshop paper" | Not confirmed by audit — treat as community code (T3) | v2 §3.6 |
| 6 | epica "more formally verified than atlas" (K*6 proofs, BLAKE3 audit trail) | epica exists (Rust, MCP, PyO3) but its formal-verification claims are **self-cited**, not independent | v2 §3.1 |
| 7 | atlas "49/49 AGM postulates verified" | README assertion, never independently verified | v2 §3.1 |
| 8 | jina-embeddings recommended for valence/emotion | jina is general-purpose embeddings — category error, removed | v1 §Category 7 Excluded |
| 9 | DoWhy recommended for counterfactual reasoning | DoWhy is causal-inference tooling for data science, not agent cognition — removed | v1 Appendix |
| 10 | DSPy recommended as "procedural compilation" | DSPy is prompt/pipeline optimization — repositioned to pipeline tuning only, never memory consolidation | v1 §Category 1 Excluded; v2 §3.4 |
| 11 | "Only ~6 of 18 projects are research-backed" (interim summary) | Precisely **3 of 18** have verified peer review: COKE, HiCL, MetaMind | audit §0.2 |
| 12 | v1 header claimed "40 new items added to BUILD-PLAN-AGENDA.md" as if to one file | The 40 items live in the **Oracle brain copy** of the agenda; the active-wiki copy does not contain them (see §10.4) | v2 §10.4 |
| 13 | IJCAI-2025 belief algebra has "operators for belief update, merge, and revision"; "only formal treatment of belief merge in the candidate set" | Paper covers deterministic iterated **revision** only (uniqueness proof + algorithm); **no merge or update operators** — gap G2 reopened | v2.2 §3.1.5, §11 G2; venue-verification-brain-architecture-2026-09-24 |
| 14 | MEMTIER listed as T1 ("per our wiki analysis") | arXiv-only preprint ("Under review" per its own comments field) — tier corrected to T2 with T1-grade internal analysis; Phase 1 placement unchanged per 2026-09-23 directive | v2.2 §3.4.2, §4.1; venue-verification-brain-architecture-2026-09-24 |

- **2026-09-25 — section renumbering.** §0.6 appeared twice on `main` ("How to Read" and "Rebrand Loss Record"). Renumbered: 0.7 Rebrand Loss Record, 0.8 Graph Layer, 0.9 Dependency Triage. The duplicate predated this change; no content was altered.

### 0.6 How to Read, Critique, and Extend This Document

**Reading order for a future session:** §2.5 (what brain part everything fills) → §4.1 (master matrix) → the specific §3 dossier → §9 (phasing) → §11 (gaps). §0.2/§10.2 are provenance records — consult when checking a claim, not first.

**To critique a component:** (1) check its tier and flags (§0.1/§0.4) — is a [VENUE-UNVERIFIED] claim being cited as fact? (2) check its negatives list — has a documented negative been resolved or just ignored? (3) check the gap list (§11) — is the component's known failure mode acceptable for the intended use? (4) check the audit disposition (§10.2.1) — was it kept despite a recommendation, and does that reason still hold?

**To compare a new option against a chosen component:** every §3 dossier follows one template — mechanism / research / siblings & rivals / benefits / negatives / integration plan / why chosen / why not alternatives. Build the same dossier for the newcomer and compare field by field; the siblings sections already name the rivals each choice beat and why.

**To extend:** add a dossier in the same template, stamp tiers per §0.1, register the paper/repo in §14, add a row to §4.1, assign a phase per the §9 rule (tier + integration cost — never wiki coverage), and record any claim changes in §0.5.

**Standing cautions:** (a) the 2026-09-23 audit found venue claims wrong in 4 of 18 spot-checks — never trust a citation lacking a [VERIFIED-2026-09-23] or [MODEL-KNOWLEDGE] flag; (b) LIDA taught us file-count evidence is the weakest kind — 1,269 "hits" that were mostly licensing false positives; always read what the files actually say; (c) numbers from papers are the papers' claims, not our measurements, unless marked otherwise.

---

### 0.7 Rebrand Loss Record (2026-09-24) — [DIRECT-OBSERVATION]

The `Hermes Brain` rebrand (`de88db2` → `83c99a0` → `095bd9c`) was applied to a tree whose
HEAD was `3d2f6d4`. The eight `tomi-v1-professionalization` commits (`29fb4f5` … `78f0424`)
were **never merged**, so their work was not "overwritten" — it was left on a side branch
and then partially re-derived by hand. A file-level diff
(`git diff --diff-filter=D tomi-v1-professionalization origin/main`) shows **12 deletions**,
of which **6 have no rename target on main**:

| Lost on main | What it was | Status |
|---|---|---|
| `scripts/run_swr_consolidation.py` (186 L) | Deterministic SWR replay → Postgres `edges`; replaced an LLM-prompt cron that printed to stdout without persisting | **Restored 2026-09-25** |
| `scripts/run_roi_canary.py` (157 L) | Weekly per-domain retrieval hit-rate + precision@k probes | **Restored 2026-09-25** |
| `scripts/run_scale_diagnostic.py` (129 L) | Monthly retrieval-reliability-vs-corpus-size diagnostic | **Restored 2026-09-25** |
| `docker/deriver-entrypoint.sh` (25 L) | Honcho deriver LLM-endpoint preflight + reachability check | **Restored 2026-09-25** |
| `scripts/check_autognosia_dbs.py` (62 L) | SQLite integrity/FK/schema checker | Superseded by `scripts/check_db_integrity.py` |
| `scripts/migrate_frontmatter_timestamps.py` (116 L) | RFC 3339 frontmatter backfill from git history | **Restored 2026-09-25** |

**Schema regression (A3/A4/A5 partial revert) — FIXED 2026-09-25.** *This subsection
records what was found; the state described below no longer holds.* At the time of the
audit, `scripts/brain_schema.sql` defined only `pages`, `embeddings`,
`conversation_history`, `sync_state`; the `edges`, `roi_canary_probes`, and
`scale_decay_diagnostic` tables were absent; and `brain/hippocampus/associative.py` had no
`pg8000` import, no `_load_from_postgres`, and no `_persist_edge`, so the in-memory
`self.adjacency` dict was the only store and the graph was lost on every process restart.
Nothing crashed, which is why it survived the rebrand unnoticed.

**Current state:** all three tables are restored, and `associative.py` persists edges to the
`edges` table and reloads them in `__init__`. Restoring the file also surfaced two latent
bugs that made the persistence non-functional even on the old branch: the writer called
`pg_conn.execute()` (pg8000 Connections have no such method — it needed an explicit
cursor), and the controller constructed the graph with only `damping_factor`, leaving
`_pg_config` as `None` so it silently ran in-memory. Both are fixed.

**Still true, and now the binding constraint:** the graph is *durable* but not *populated or
queried*. `add_edge()` and `retrieve_relevant()` have zero callers outside tests — the
retrieval algorithm was verified working by hand (a two-hop Personalized PageRank walk
returns correctly ranked neighbours), but no production code path invokes it. The
`edges` table is written only by `scripts/run_swr_consolidation.py`, which operates on
episode summaries rather than on the wiki corpus. So durable storage was the easy half;
feeding the graph and querying it are both still open. See §0.7.

**Documentation regression.** The `tomi-v1` branch carried a §1 "Existing Brain
Infrastructure" truth pass ([DIRECT-OBSERVATION], verified against the repo) that main does
not have: per-subsystem module tables, the Postgres/SQLite schema inventory, the
`brain_search()` RRF hybrid note, the compose service table, the consolidation schedule, and
an explicit "What Does NOT Ship" list. Main instead carries a §0.2 wiki-coverage audit whose
file counts are **not reproducible** — it cites ToM at 1,558 files, HTM at 631, CLS at 173,
and Emotion-Cognition at 109, while the entire Oracle vault holds 2,065 markdown files and
the corresponding concept directories contain 2, 1, 1, and 8 respectively. Those counts
should be treated as unverified and re-derived or dropped (§0.5 caution (b) applies directly).

**Restored in this pass:** the *Future / Aspirational Research Directions* section (below),
with its stale `edges`-table and `research/`-path references corrected to match main.

**Onboarding-path defects found in the same audit (2026-09-24, [DIRECT-OBSERVATION]).**
These are product defects in the install path, independent of the environment they run in,
and each was verified by reading the code path or executing it in an isolated `HERMES_HOME`:

1. **Verification runs before the services exist, and its verdict is discarded.**
   `install.py:303` invokes `scripts/verify_stack.py`; `install.py:315` is where
   `run_docker()` actually starts containers. The subprocess call has no `check=` and no
   `returncode` inspection, so a failing verification does not stop or even inform the
   install. On a fresh machine every service probe necessarily fails.
2. **`verify_stack.py` reports success via fallbacks that cannot fail.** A non-systemd or
   developer environment returns "ready" (`verify_stack.py:62`); missing Honcho returns
   "optional" (`:124`); profiles and required directories pass on `.exists()` alone
   (`:85`, `:140`). This is the asset-existence-verification failure mode: the check can
   pass without probing the live thing.
3. **The installer destroys unmanaged directories on rerun.** `install.py:120`, `:144`,
   `:157`, `:179` run `shutil.rmtree(dest)` on any pre-existing destination that is not a
   symlink — no ownership check, no backup, no prompt. Reproduced in a sandbox: a
   `~/.hermes/skills/<name>/precious-research.md` written by the user is destroyed on the
   next install. Correct pattern is a reconciler with a manifest (component, version,
   checksum, `managed_by`, backup path) that distinguishes *already satisfied* from
   *changed, backup first* from *blocked, conflicts with user intent*.
4. **`setup_env_file()` reports operator configuration it never performs.** The comment at
   `install.py:73` says "Update OPERATOR_NAME if provided"; the function only `print()`s
   the value (`:77`) and never writes it to `.env`. `--operator` is silently a no-op.
5. **`init_experience_db.py` is not additive-only.** `scripts/init_experience_db.py:69-70`
   issues `DROP TABLE IF EXISTS operations_new` / `routing_new` as part of its schema
   script. The persona's additive-only rule permits new tables/indexes, not drops.
6. **`apply_schema_upgrades.py` hardcodes `~/.hermes` (`:16`, `:24`), ignoring
   `HERMES_HOME`/`HERMES_DATA_DIR`, and `conn.commit()` at `:56` runs after the per-statement
   `except` at `:54` — so a failed migration still commits and exits 0.** It also has no
   migration-version table, no checksum record, and no downgrade path.
7. **Dependencies are lower-bound only** (`requirements.txt`: `pg8000>=1.30.0`,
   `requests>=2.31.0`, `pyyaml>=6.0`, …), so a fresh install is not reproducible. `uv` with a
   committed `uv.lock` is the appropriate fix.
8. **Predictable default database credentials** — `docker-compose.yml:24` and `:44` both
   default `POSTGRES_PASSWORD` to `brain`. Acceptable for an isolated local stack, not as a
   product default.
9. **The installer starts only the root compose file.** `run_docker()` runs
   `docker compose up -d --build` with `cwd=REPO_ROOT` and no `-f`, so
   `docker/docker-compose.honcho.yml`, `docker-compose.personal-organizer.yml`,
   `docker-compose.searxng.yml`, and `docker-compose.firecrawl.yml` are never started —
   while `tests/run_tests.sh:23-24` asserts Honcho `:8000` and Personal Organizer `:8001`
   are healthy. On a clean machine that acceptance test can never pass, and the installer
   gives no error. The compose files themselves are correct and bind to
   `127.0.0.1` (Honcho `:8000`, organizer `:8001`, SearXNG `:8080`); the gap is that
   nothing orchestrates them. `docker/docker-compose.searxng.yml:9` and
   `docker-compose.yml:61` both claim host port 8080, and `dashboard/docker-compose.yml`
   duplicates the root dashboard service on 8088.
10. **`run_tests.sh` verifies the wrong system.** It probes services on `:8000`/`:8001`/
    `:8080` that the root compose does not start, never checks `:8088` (the dashboard it
    *does* start) or `:5433` (Postgres), and never runs `tests/test_brain_architecture.py`
    or `tests/test_brain_integration.py` — which do pass (22 tests, 1 skipped, via
    `python3 -m unittest`).

**Framing.** The project's public claim should be **"biologically inspired cognitive
architecture"**, not "replicates a human brain." Where a peer-reviewed win exists it is
attributable to an ordinary engineering primitive (KG + PPR retrieval; a compressor with a
sound write policy) and the cognitive-science layer is explanatory framing, not the cause.
The honest framing costs nothing and is defensible under review.

### 0.8 Graph Layer: Design State and Known Gaps

The relational-memory path spans three layers. This section records what the *code* does, so a
new contributor does not have to rediscover the gaps. It describes the repository's design and
its known limitations — it makes no claim about the contents or health of any particular
installation's graphs, which are local derived data and are never committed.

| Layer | Component | State in this repo |
|---|---|---|
| Substrate | External graphify runs over the wiki vaults | **Scripted but not reliably configured.** `scripts/refresh_graphify.py` invokes `graphify update`, which is structural (AST) extraction — appropriate for code, not for prose. A semantic `extract` is required to build semantic relationships. The failure mode and its fix are documented in `docs/references/graphify-refresh-pitfall.md` |
| Storage | `edges` table + `associative.py` Postgres persistence | **Implemented.** Loads edges in `__init__`, persists on `add_edge`, degrades to in-memory when Postgres is unavailable. Restored 2026-09-25 |
| Retrieval | Personalized PageRank over the graph | **Wired 2026-09-25.** `scripts/graph_retrieval.py` reads the Graphify graphs and returns results with the connecting path; `scripts/brain_query.py --graph` fuses them into the normal RRF pool. `brain/hippocampus/associative.py` remains a separate in-PPR implementation for episodic (non-wiki) relations |

**Query path (closed 2026-09-25).** The retrieval gap is now filled.
`scripts/graph_retrieval.py` loads a Graphify `graph.json`, matches query terms against node
labels to pick seed nodes, runs Personalized PageRank outward from them, and returns the
documents it reaches *together with the relationship path that reached them*. It is wired into
`scripts/brain_query.py` behind `--graph` (fused into the existing Reciprocal Rank Fusion pool)
and `--graph-only` (graph without the database or embedding server).

Two implementation details are load-bearing and were verified against real graphs rather than
fixtures. First, Graphify stores relationships under a `links` key, not `edges`; reading
`edges` alone reports zero relationships for a healthy graph, which is what produced the
long-standing false "the graph is empty" diagnosis. Second, Graphify link endpoints are node
IDs rather than labels, so the loader resolves them before building adjacency.

**Still open.** The Postgres `edges` table is written only by
`scripts/run_swr_consolidation.py`, which works from episode summaries rather than wiki
documents. So there are now two graph paths serving different corpora: the Graphify graphs
(wiki-derived, queried) and the Postgres `edges` table (episode-derived, not yet queried in
production). Unifying them is a design decision, not a bug fix.

No benchmark number in this document should be read as evidence that multi-hop retrieval
improves answer quality; the capability is verified to run and to return connected documents,
not to have been measured against a baseline.

**On the substrate choice.** §3.1.1 and the locked-decision-3 row in the Appendix record that
Neo4j + Graphiti were evaluated and cut: bi-temporal invalidation is storage-level only (its
read path defaults to returning superseded facts), the Neo4j dependency adds operational surface,
and in-process PPR was judged sufficient at this scale. That reasoning still holds. It was
partly premised on the `edges` table being absent, which is no longer true, so the premise has
been corrected rather than the decision reversed. Reopening the substrate question remains
legitimate — on the evidence about extraction reliability, not on a schema fact.

**Still open — needs a decision:** whether to restore the four un-restored scripts, the
three Postgres tables, and the `associative.py` persistence layer. The measurement scripts
matter most: without `run_roi_canary.py` and `run_scale_diagnostic.py` there is no
instrumentation that would let us detect memory-ROI regression on a fresh install, which
means the Phase-gating claims in §9 cannot be evidenced on a deployed system.

### 0.9 Dependency Triage (verified 2026-09-25)

Every third-party project named in this document or the README is inventoried in
`docs/DEPENDENCY-REGISTRY.md` with maintenance signals and risk tiers; licences are
broken out in `docs/THIRD-PARTY-LICENSES.md`. Three findings change how this
architecture should be read:

1. **Neo4j was never in the stack, and Kuzu is dead.** This document historically
   referenced Kuzu as a Graphiti backend. Kuzu is archived upstream as of 2025-10-10
   — its own README opens "We are archiving the KuzuDB project here" — so any option
   list naming it is stale. No code in this repo depends on it.

2. **Three bundled services are AGPL-3.0** — Honcho, Firecrawl, SearXNG. This repo
   connects to them as external containers rather than vendoring them, which is the
   lowest-obligation arrangement. It is documented rather than assumed, because users
   redistributing or commercially hosting need to know where the boundary is.

3. **graphify is high-risk and must stay replaceable.** The graph it produces is
   derived, disposable, and verified by
   `scripts/verify_graph_integrity.py` rather than trusted. A silently degraded graph
   is worse than an absent one, so the retrieval layer reads a plain node/edge JSON
   file that any indexer can produce.

The durable assets are the retrieval layer, the graph *format*, and the version
aggregation convention. The tools that build them are the replaceable parts, and the
repo says so where users will read it.

### 0.10 Memory Durability Floor (verified 2026-09-25)

### 0.11 Cognitive Coverage Review (verified 2026-09-25)

### 0.12 Cognitive Evidence Review (verified 2026-09-25)

`docs/COGNITIVE-EVIDENCE-REVIEW.md` covers the external evidence base for eleven
candidate mechanisms, including the negative results. **Study only -- nothing in it
has been implemented.**

The findings that change design decisions rather than merely add candidates:

- **Random exploration is worse than useless for LLM agents.** In the primary table
  of arXiv:2604.17244, epsilon-greedy scores **0.414 mean reward -- identical to
  plain greedy -- with a 90% suffix failure frequency**, meaning it commits to a
  suboptimal arm and does not recover in 9 runs out of 10. On the harder 9-arm
  instance it is the worst method tested (0.335 reward, 131.25 regret). The reason
  is structural: actions are chosen at the sequence level while temperature and
  sampling randomise tokens, so you get variety inside a committed plan rather than
  a different plan. **This constrains the `valence_engine.curiosity` field: wiring
  it into action selection as a randomiser would import this exact failure.**
- **Prospective memory has a purpose-built benchmark, and the best result is
  deterministic.** PM-Bench (arXiv:2607.12385) caps at **65.1% Set-F1** for the
  best frontier-model agent. Moving lifecycle logic out of the model and into a
  typed store reaches **82.9%** (arXiv:2609.01272), and lifts a 2B model from
  **4.2% to 66.2%** where seven memory-retrieval methods managed 6.6%. The same
  benchmark shows a "monitor everything" design reaching 10.7% with 1,661
  false-positive queries, and forced polling **tripling cost while lowering
  accuracy**.
- **Delete nothing; gate at read time.** A restore-counterfactual audit
  (arXiv:2609.08279) finds **67-73% of errors are irreversible** under FIFO, random
  and redundancy-aware eviction at an 80k budget, rising to **100% at 8k for all
  four policies**, and no pruner is safer than any other at matched accuracy. The
  best-performing pruning method gains +8 to +19 points by **not deleting anything**
  and gating at read time instead. This is why `docs/VERSION-AGGREGATION.md` and the
  append-only event log are the right shape and destructive pruning is not.
- **Structure must be added on top of raw text, never instead of it.** Graph-shaped
  memory loses to a flat vector store on LongMemEval (F1 0.417 vs 0.468), with
  turn-recall correctness collapsing 0.911 -> 0.607, because decomposing a turn into
  entities discards the surface form the questions depend on. Reinforces the
  standing rule that the graph is an index, never the system of record.
- **Neuromodulation is a dead end as a principle.** The one benchmarked
  implementation's own ablations show the bio-inspired signal is not the load-bearing
  part. **This confirms the existing "no benchmark evidence" marking rather than
  overturning it.**

**The cross-cutting result:** across eleven mechanisms, the largest measured
effects all favour moving decisions into deterministic code -- lifecycle in code,
gating instead of deleting, structured residual tracking, rejecting random
exploration. Human cognitive findings transfer here as **what to measure**, not as
**what improves an agent**. That is the same pattern as this project's own theory-of-
mind result (0.0% Pass^3 across seven frontier models), and it should shape how the
"biologically inspired" framing is presented to a reader.

**A correction made during verification:** a research report quoted epsilon-greedy
at 0.490 losing to greedy at 0.506 with regret 21.80 vs 13.68. Those figures were
spliced from two different experimental setups. Read from the paper, the correct
Table 1 numbers are 0.414 for both, regret 90.000 for both. The conclusion survives
and the mechanism is clearer.

`docs/COGNITIVE-COVERAGE-REVIEW.md` compares what both wikis cover against what
`brain/` actually implements, and ranks the gaps. The load-bearing findings:

- A keyword scan of the full vault reports **every** candidate topic as
  "covered," which is why the review measures implementation rather than mentions.
- Six subsystems are constructed but never called from the agent loop.
  `counterfactual`, `defeater_graph` and `associative_graph` are reachable from the
  dashboard, so they are inspectable but inert; `agm` and `dialectic` are reachable
  from tests only; `chronostasis` has no consumer anywhere in the repository.
- `valence_engine.curiosity` is written on every outcome and read by nothing.
- The frontmatter "7 brain subsystems" is stale: nine directories, twelve instances.

**Prospective memory (implementation intentions) is now implemented** in
`brain/prospective/intentions.py`, wired into `process_incoming_stimulus` step 7b,
with fired intentions surfaced as `fired_intentions`. Evidence is Gollwitzer &
Sheeran (2006), DOI `10.1016/S0065-2601(06)38002-1`, and Gollwitzer (1999), DOI
`10.1037/0003-066x.54.7.493` -- both recovered from Crossref after the vault's own
citations for them proved wrong (see `docs/CITATION-AUDIT.md`: 8 of 8 DOIs in the
source file are broken). 41 tests, four of which drive it through the real hub.
**It is instrumented, not proven to improve agent outcomes.**

The review also documents two findings arguing for doing less. Adaptive forgetting's
effect falls from d=0.31 to ~0.15 once publication bias is corrected. And this
project's own evidence shows the most brain-like proposals available -- theory of
mind and multi-agent belief merging -- scoring 0.0% and 30.1% in independent
evaluation, worse than not attempting them. Predictive processing is deferred as
theory; interleaving is deferred as human-only evidence.

The memory subsystem's derived state can be **silently and permanently lost**, and
the fix is not a different tool — it is a log this repo owns.

Honcho issue #1236, verified at source: when the LLM upstream is unreachable past
`MAX_RETRYABLE_ATTEMPTS = 3` (1 s backoff, 30 s poll — about **90 seconds** of
tolerance), queue items are marked `processed=true` with an error while the poller
filters on `processed` only. Those messages are never derived again. There is no
upstream recovery: the reconciler does not re-derive, the update endpoint does not
enqueue, and no client-supplied idempotency key exists, so re-POSTing duplicates
instead of replacing. `queue/status` reports `completed == total` throughout.

That behaviour is asserted by Honcho's own test suite
(`test_retry_exhaustion_is_terminal`: *"At the attempt cap a transient error burns
the first item exactly like today's terminal path"*), so it is a product decision,
not a bug awaiting a patch.

**The invariant: the log is the source of truth; derived state is verified against
it, never trusted over it.** `scripts/memory_event_log.py` implements it:

- append-only — no update, no delete; corrections are new events
- ingestion ids derived from content, so replay is idempotent rather than duplicating
- `fsync` on write, because a durability floor that can lose buffered data is not a floor
- `reconcile` reports what was sent but never derived, and exits non-zero — the exact
  signal Honcho's status endpoint omits
- newline-delimited JSON, so it is inspectable with `tail` and depends on no running
  service

Companion findings in the same class: #989 (semantic dedup hard-deletes the
incumbent on a score tie, and the agent-tool path hardcodes `deduplicate=True`),
#1230 (the deriver persists its own few-shot examples as peer facts, and deleting
them is not durable), #839 (parse failures still mark items `processed=true` with
"no metric, no trace span error, no alertable signal").

**Consequence for the architecture:** any memory system this repo adopts is an
*index* over the log, never the system of record. That inverts the usual
dependency, and it is what makes the memory layer replaceable without data loss.

## 1. Existing Brain Infrastructure

**The Hermes Brain is already partially built.** This section documents every existing component so the proposed additions can be understood in context. Everything in this section is [DIRECT-OBSERVATION] — verified by reading the repo at `~/hermes-brain` on 2026-09-23.

### 1.1 Core Brain Subsystems (8 subsystems, `brain/` directory)

Each subsystem is a Python package under `brain/` with its own module files. The master controller `brain/hermes_brain.py` instantiates all 8 and orchestrates the per-turn cognitive pass.

| # | Subsystem | Package | Module Files | Lines (est.) | Purpose |
|---|-----------|---------|-------------|-------------|---------|
| 1 | **Thalamus** | `brain/thalamus/` | `gate.py`, `buffer.py` | ~120 | Saliency gating & sensory buffering. Shannon entropy-based saliency scoring. Ring buffer (maxlen=200). |
| 2 | **Cortex** | `brain/cortex/` | `dl_pfc.py`, `router.py`, `executive.py` | ~200 | Working memory (7 slots, decay 0.1/turn). Dual-process System 1/2 routing (threshold=0.5). Miyake triad: inhibition, updating, shifting. |
| 3 | **Limbic** | `brain/limbic/` | `valence.py`, `somatic.py` | ~100 | Cognitive valence (-1.0 to +1.0), arousal (0.0-1.0), allostatic load, curiosity drive. Damasio somatic markers with SQLite persistence. |
| 4 | **Basal Ganglia** | `brain/basal_ganglia/` | `action_gate.py`, `compiler.py` | ~150 | Striatal Go/No-Go action arbitration (go_threshold=0.4). Procedural skill compilation (compilation_threshold=3). ACT-R skill acquisition. |
| 5 | **Hippocampus** | `brain/hippocampus/` | `associative.py`, `replay.py` | ~180 | HippoRAG-style associative graph with Personalized PageRank (damping=0.85). Pattern separation (DG), pattern completion (CA3), SWR replay consolidation. |
| 6 | **DMN** | `brain/dmn/` | `chronesthesia.py`, `counterfactual.py` | ~120 | Chronesthesia (mental time travel — retrospection & prospection). Judea Pearl causal counterfactual regret analysis. |
| 7 | **Epistemology** | `brain/epistemology/` | `agm.py`, `defeater_graph.py`, `dialectic.py` | ~200 | AGM belief revision (expansion/contraction/revision with epistemic entrenchment). Pollock defeasible reasoning (rebutting/undercutting defeaters). Hegelian dialectical synthesis. |
| 8 | **Social** | `brain/social/` | `tom.py`, `pragmatics.py` | ~150 | Recursive Theory of Mind (Level 1: user beliefs, Level 2: user's model of agent). Gricean conversational pragmatics (implicature detection). |

**Master Controller API** (`brain/hermes_brain.py`):

```python
class HermesBrain:
    def __init__(self, db_path=None)  # Initializes all 8 subsystems + SQLite schema
    def process_incoming_stimulus(source, text, session_id) -> Dict  # Full cognitive pass
    def record_action_outcome(action, target, success, surprise_score, steps)  # Feedback loop
```

**`process_incoming_stimulus` pipeline (7 steps):** thalamic buffer append + saliency admission → Gricean implicature decoding → somatic marker risk appraisal → System 1/2 routing → working memory decay + upsert → ToM discrepancy check → action-gate preview.

**`record_action_outcome` pipeline (5 steps):** limbic valence update + somatic reinforcement → executive shifting/loop evaluation → hippocampal replay write → procedural compiler observation.

### 1.2 Database Schema (`brain/schema/brain_cortex.sql`)

6 tables, dual-engine compatible (PostgreSQL + pgvector & SQLite):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `cognitive_beliefs` | Epistemic belief store | topic, statement, credence, provenance, epistemic_state |
| `cognitive_defeaters` | Pollock defeater lattice | target_belief_id, defeater_belief_id, defeater_type (rebutting/undercutting) |
| `somatic_markers` | Limbic operational risk memory | action_pattern, target_pattern, valence_bias, sample_count |
| `user_mental_models` | Theory of Mind user state | domain, attributed_belief, ground_truth, discrepancy |
| `counterfactual_rollouts` | DMN causal counterfactuals | trigger_event, actual_path, counterfactual_path, predicted_advantage, lesson_extracted |
| `working_memory_snapshots` | dlPFC working memory | session_id, active_goal, sub_goals_json, hypotheses_json, focus_slots_json |

### 1.3 Hooks (4 hooks, `hooks/` directory)

| Hook | Events | Purpose | Blocking? |
|------|--------|---------|-----------|
| **brain-cognitive-guard** | `agent:step`, `command:*` | Basal Ganglia action gating. Somatic risk appraisal, Go/No-Go arbitration, repetitive loop detection. Fail-open if Brain API unreachable. | No (fail-open) |
| **brain-memory-consolidator** | `agent:end`, `session:reset` | Feeds user input into thalamus & working memory. Records tool outcomes for somatic markers & limbic valence. Consolidates high-surprise episodes into hippocampal replay. | No (fail-open) |
| **to-do-capture** | `agent:end` | Detects user requests to add to-do items. Writes to organizer.db. Same-title-same-day dedup. Chat platforms only. | No (fail-open) |
| **hermes-visualizer-sync** | `agent:start/step/end`, `session:reset` | Broadcasts agent state (listening/thinking/speaking/idle) to Hermes Visualizer (port 8790) and Barehands (port 8794). | No |

### 1.4 Plugin (1 plugin, `plugins/` directory)

| Plugin | Events | Purpose |
|--------|--------|---------|
| **decision_logger** | `agent:end` | Scans agent's final response for decision-like statements. Writes to brain DB decisions table. Hash dedup. Never blocks. Env-configurable: `DECISION_DB_HOST/PORT/USER/PASS/NAME`, `DECISION_SCAN_TAIL_CHARS` (4000), `DECISION_CONFIDENCE_THRESHOLD` (0.60), `DECISION_WIKI_OUTPUT_DIR`. |

**Cron:** nightly 2 AM — `plugins/decision_logger/synthesis.py` scans the decisions table for contradictions, stance drift, and entity promotion patterns.

### 1.5 Profiles (10), Skills (48), Config, Cron, Adapters

- **10 profiles:** default, coder, oracle, oracle-researcher, researcher, planner, auditor, `personal-organizer`, `desktop-worker` (desktop LM Studio GPU host), `desktop-researcher`.
- **48 skills** across Brain/Cognitive, Research, Wiki/Knowledge, Code/Dev, Data, Communication, Infrastructure, Meta, and Other categories (full list in v1 §0.6 / repo `skills/`).
- **Config (`config.yaml`):** model Qwen3.6-35B-A3B-Q4_K_M via llamaCPP (localhost:8080); desktopLM (localhost:1234, qwen3.8-27b); vllm (localhost:18020, qwen3.8-27b); fallback chain openrouter → nemotron-free; max_turns 200; checkpoints enabled (max 50); compression enabled (threshold 0.5, target 0.2, protect last 20).
- **Paths (`docs/paths.yaml`):** hermes_home `~/.hermes`; active-wiki; oracle; graphify-main-out / graphify-oracle-out; organizer.db under personal-organizer/data; backups root.
- **Cron template (3 jobs):** Daily Backup 3:00 AM (`scripts/hermes_backup.py`); Database Backup 2:00 AM (`scripts/backup_databases.py`); Decision Synthesis 2:00 AM.
- **Adapters:** `visualizer.py` (signal bus `.voice_state`), `barehands.py` (stage ring `state/state`).

### 1.6 Current Stack (Integration Target)

| Layer | Technology | Role |
|-------|-----------|------|
| Agent Loop | Python / Hermes Agent | Per-turn orchestration |
| Local LLM | llama.cpp (Qwen3.6-35B-A3B-Q4_K_M, 256K ctx) | Primary inference |
| Knowledge Graph | Neo4j + Graphiti | Temporal knowledge graph |
| Vector Store | pgvector (Postgres) | Semantic similarity |
| Graph Index | Graphify | Active Wiki + Oracle Brain indexing |
| Working Memory | MEMORY.md (~2,200 chars) | Hot memory |
| Episodic Store | JSONL + holographic (MnemoCore/HoloGraph) | Session history |
| Consolidation | Dreaming plugin (cron) | Nightly 3-phase consolidation |
| Multi-Agent | 5 instances (main/coder/flowbot/oracle/researcher) | Distributed cognition |

---

## 2. Architecture Overview

### Design Principles

1. **Evidence-first:** every component carries a tier (§0.1) and a provenance stamp; README assertions are never cited as research backing.
2. **Low wiki coverage ≠ weak idea.** Coverage flags information depth, not quality (directive, 2026-09-23).
3. **Hermes-native:** every component must map to the existing stack (Python, llama.cpp, Neo4j, Postgres/pgvector, SQLite, MCP, cron).
4. **Phased, independently valuable:** Foundation → Enhancement → Specialization → Research (§9), each phase delivers standalone value.
5. **No speculative core patches:** framework/core changes require research first; missing features may be deliberate design decisions.

### Tier Distribution Across the Proposal

| Category | T1 anchors | T2 preprints | T3 community | T4 conjecture |
|----------|-----------|--------------|--------------|---------------|
| Belief Revision | AGM theory, DCPM | Kumiho, IJCAI-2025 algebra | atlas, epica, belief_set | — |
| Counterfactual | Pearl's causal hierarchy | CRAFT, C3, ActMem | — | Full engine design (ours) |
| Theory of Mind | COKE, MetaMind | ToMAgent, MindForge, Dynamic ToM | — | — |
| Procedural Memory | HiCL, AWM, MEMTIER | GraSP, SkillTrace, SkillDAG | — | — |
| Hippocampal Indexing | HippoRAG, CLS theory, Rolls-Treves | — | mokosh, omega-hippocampus, HRR libs | CA3 attractor build |
| Cognitive Routing | GWT (Baars/Shanahan) | Gated-Memory Routing [VENUE-PARTIAL-2026-09-24] | Sibelium, LIMEN | Sibelium↔DCPM mapping |
| Valence/Emotion | Damasio, Lazarus/Scherer theory | TOAQ | swaylq, biomind, Maxim, NexusCortex | Emotion-cognition integration |

### 2.5 Neuroanatomical Map — What Part of the Brain Each Piece Fills

The brain metaphor is not decoration: each subsystem emulates a specific region's *function*, and every proposed component attaches to a region. This is the "what part of the brain does this fill?" answer in one table. Regions follow the standard functional account; where our emulation is loose, the table says so.

| Brain region | Function emulated | Existing subsystem | Proposed components that fill it |
|---|---|---|---|
| **Thalamus** | Sensory relay & gating — filters what reaches cortex | `brain/thalamus/` (entropy saliency gate, ring buffer) | Sibelium CE formula (§3.6.2) sharpens the gate; ActMem counterfactual queries (§3.2.3) widen recall at the relay |
| **Hippocampus — DG (dentate gyrus)** | Pattern separation — dissimilar codes for similar inputs | `brain/hippocampus/associative.py` (crude) | mokosh SDR (§3.5.2); HiCL DG-gated MoE (§3.4.1) — the DG metaphor is literally in its name |
| **Hippocampus — CA3** | Autoassociative completion — partial cue → full memory | `brain/hippocampus/associative.py` (PPR stand-in) | CA3 attractor build (§6.2); HRR unbinding (§3.5.3) as algebraic completion |
| **Hippocampus — CA1** | Retrieval/readout into cortex | PPR retrieval path | HippoRAG proper (§3.5.1) — PPR over Neo4j is the CA1 readout analog |
| **Hippocampus — sharp-wave ripples** | Offline replay during sleep | `brain/hippocampus/replay.py` + dreaming plugin | HiCL SWR consolidation (§3.4.1); sleep-cognition literature grounds the phase design (§5.6) |
| **Neocortex (semantic store)** | Slow, structured long-term knowledge | Active Wiki + Oracle Brain (cold stores) | CLS theory (§5.5) is why this store is separate from the fast stores; ZenBrain (§5.2) is the comparative reference for tier boundaries |
| **Prefrontal cortex — dlPFC** | Working memory, manipulation | `brain/cortex/dl_pfc.py` (7 slots, decay) | BrainMem (§5.3) is the modeling reference for slot/decay parameters |
| **Prefrontal cortex — executive** | Inhibition, shifting, updating (Miyake triad) | `brain/cortex/executive.py` | — (considered complete at current scope) |
| **Anterior cingulate / salience network** | Conflict monitoring, salience detection | Saliency scoring in thalamus module | Predictive-processing surprise signal (§5.8) is the long-term principled version of the entropy proxy |
| **Basal ganglia** | Action selection via Go/No-Go pathways | `brain/basal_ganglia/action_gate.py` (Go/No-Go, threshold 0.4) | MemoBrain (§5.9) adds dependency-aware gating; Maxim NAc reward (§3.7.4) supplies the dopaminergic learning signal |
| **Striatum (dorsolateral)** | Habit formation — repeated sequences become routines | `brain/basal_ganglia/compiler.py` (threshold-3 compilation) | HiCL (neural consolidation), AWM (symbolic workflow induction), GraSP (typed DAG + repair) — three layers of habit |
| **Amygdala** | Emotional tagging of memory (valence bias) | `brain/limbic/somatic.py` (somatic markers) | swaylq layers 1–4 (§3.7.2) extend tagging; Emotion-Cognition directory (§5.7) is the theory base |
| **Insula / interoception** | Body-state readout (hunger, fatigue) | Allostatic load variable in limbic | Interoception directory (§5.11) is the citation base; resource-pressure signals are the analog |
| **VTA / dopamine (RPE)** | Reward prediction error — learning signal | `record_action_outcome` success signal | Gap G29: no adequate solution; RPE literature (§5.12) is the build-from theory |
| **Default Mode Network** | Prospection, retrospection, self-referential thought | `brain/dmn/chronesthesia.py` + `counterfactual.py` | CRAFT/C3 engine (§6.1) fills the counterfactual half; chronesthesia rollout is an open gap |
| **Temporoparietal junction / ToM** | Mentalizing about others | `brain/social/tom.py` (recursive L1/L2) | MetaMind pipeline (§3.3.1), COKE/COLM (§3.3.2), Dynamic ToM trajectories (§3.3.5) |
| **Global workspace (prefrontal-parietal, GWT)** | Broadcast & conscious access | Router threshold (proxy) | LIMEN auction (§3.6.3) + GWT directory (§5.1) — the arbitration layer |
| **Cerebellum** | Error correction, fast adaptive control | *(none)* | Deliberately unfilled — no proposed component emulates it; a fast error-correction layer is the long-term candidate |

**Reading the map:** the existing 8 subsystems cover 13 of 19 regions; the proposal fills 4 more (CA1-proper, striatum-habit-layers, ToM pipeline, workspace arbitration), grounds 2 in theory (VTA/RPE, interoception), and leaves 1 deliberately empty (cerebellum). The mapping is functional emulation, not biological fidelity — each dossier's [CONJECTURE] flags mark where the emulation is loosest.

---

## 3. Category Dossiers

Each dossier follows a fixed template: **Mechanism** (how the program works) → **The research** (how the research works) → **Siblings & rivals** (where they differ, whether they're the same) → **Benefits** → **Negatives** → **Integration plan** (how it would be done, concretely) → **Why chosen** → **Why not the alternatives**.

### 3.1 Category 1: Belief Revision

**Mission:** formal belief revision — not just storage, but AGM-compliant expansion/contraction/revision with downstream propagation and contradiction resolution. Existing `brain/epistemology/` (agm.py, defeater_graph.py, dialectic.py) is the target substrate.

#### 3.1.1 DCPM Supersedes Chains — T1 (foundation: AGM theory T1; DCPM paper T2 [preprint-only confirmed 2026-09-24]) [VERIFIED-2026-09-23: 331-line wiki analysis exists]

- **Mechanism:** Daytime System 1 writes `SUPERSEDE` / `UPDATE` / `ADD` / `⊥` reconciliation decisions as doubly-linked lists. Predecessors are never deleted — every belief change is an edge in a chain, so the full history of any belief is walkable. Nighttime System 2 runs cross-domain schema induction + collision sweeps over the accumulated chains.
- **The research:** DCPM (dual-process cognitive memory) paper proposes exactly this dual-loop structure; our wiki analysis (331 lines) maps its daytime loop to the dreaming plugin's Light Sleep phase (fact triage) and its nighttime loop to REM (schema induction) + Deep Sleep (cross-domain sweep). The paper's headline stat: 78% of correct LongMemEval knowledge-update queries touch a supersedes pointer, vs 31% of incorrect — i.e., supersession chains are where correct updated answers come from.
- **Siblings & rivals:** DCPM chains vs AGM operators — different layers of the same problem. Chains are an *operational* belief-trajectory structure (what changed, when, in what order); AGM is the *formal* theory (which operations are rational). They are not rivals; agenda item `belief-revision-vs-dcpm-supersedes-chain-comparison` exists precisely to map chain operations onto AGM operators (does supersedes = revision? does chain traversal = recovery?). vs Graphiti's bi-temporal invalidation (Zep): Graphiti closes validity windows on contradiction; DCPM keeps everything and orders it. vs Mem0's ADD-only + read-time ranking: Mem0 never decides supersession at write, DCPM does.
- **Benefits:** append-only (no destructive writes — matches our schema discipline); directly answers "what did I believe in June?"; the 78%-vs-31% stat is a strong signal the mechanism is load-bearing for knowledge updates; maps 1:1 onto existing `cognitive_beliefs` table by adding a `superseded_by` column (additive-only, no rebuild).
- **Negatives:** chain length grows unboundedly (needs pruning policy — Gap G1); multi-hop chained supersession is an open research problem (knowl.cloud measured 0.07 vs a 0.14 ceiling on MemoryAgentBench — nobody has solved it); the LongMemEval stat is the paper's claim, not our measurement.
- **Integration plan:** (1) `ALTER TABLE cognitive_beliefs ADD COLUMN superseded_by TEXT REFERENCES cognitive_beliefs(id)` + `superseded_at` (RFC 3339 UTC). (2) Write-path: when a new belief contradicts an existing one, insert new row, set predecessor's `superseded_by`, never UPDATE the statement itself. (3) Read-path: "current view" = rows where `superseded_by IS NULL`; "as-of view" = walk chain to timestamp. (4) Nightly: dreaming plugin REM phase runs collision sweep over chains. (5) Reversal detection: lexical polarity/reversal-phrase checks BEFORE similarity thresholds — embedding cosine cannot separate reversal from restatement (0.0018 margin measured by knowl.cloud).
- **Why chosen:** strongest wiki coverage of any candidate (202 files); mechanism is append-only and additive; evidence directly ties it to the failure mode (knowledge-update queries) we care about.
- **Why not alternatives:** Graphiti/Zep — bi-temporal invalidation is storage-level only; their read path has a documented default of returning superseded facts (filters default None) — we would re-implement enforcement anyway, so build chains natively. Mem0 ADD-only — defers all currency logic to read time, which makes as-of queries expensive and multi-session drift likely. Plain version columns without chains — loses ordering and the collision sweep substrate.

#### 3.1.2 Atlas AGM + Ripple Propagation — T3 (community code) [VERIFIED-2026-09-23: repo real, author RichSchefren]

- **Mechanism:** AGM expansion/contraction/revision implemented as Cypher transactions on Neo4j. "Ripple" propagates a belief update downstream through typed belief edges, so revising one belief updates every belief derived from it. Ships an MCP server and per-belief provenance tracking.
- **The research:** AGM theory itself is T1 (Alchourrón, Gärdenfors, Makinson 1985 — the AGM framework is foundational). Atlas's implementation of it is T3: the "49/49 AGM postulates verified" figure is a README assertion with no independent verification. The audit confirmed the repo exists, the MCP server exists, and the author is RichSchefren (not angrysky56 as first circulated).
- **Siblings & rivals:** vs epica — epica is Rust with self-cited "grounding" papers, MCP-native, PyO3 SDK; atlas is Python/Neo4j with MCP. Same AGM target, different substrate. vs belief_set — pure-Python AGM kernel (PyPI, ctoth), no graph DB; the computational core without the graph. vs Kumiho — Kumiho is *theory* (formal K*2–K*6 proofs on property graphs, arXiv:2603.17244, T2) with no usable implementation. They are not the same: atlas/epica/belief_set are executable AGM; Kumiho is the correctness standard to check any of them against.
- **Benefits:** MCP server means integration without writing a Neo4j client into the agent loop; Ripple is the only mechanism in this space that propagates revision downstream (our gap G-provenance); provenance per belief matches our epistemic protocol.
- **Negatives:** zero peer review; 49/49 claim unverified; alpha-stage code; Neo4j dependency adds an operational surface (though we already run Neo4j for Graphiti); contradiction resolution is last-writer-wins by default (conflicts with our "preserve both versions" rule — Oracle wiki rule 12).
- **Integration plan:** (1) Run Atlas's MCP server beside Neo4j. (2) Register in Hermes as native MCP server (stdio wrapper with absolute paths — see mcp-stdio-path-and-pep668 skill). (3) Pilot: mirror `cognitive_beliefs` current-view into Atlas's belief graph; run its postulate test suite ourselves (don't trust the 49/49 — re-run it); use Ripple for downstream propagation only after the pilot passes. (4) Keep DCPM chains in SQLite as source of truth; Atlas is a derived verification/propagation layer. (5) Gate: if Atlas's postulate suite fails on our data, fall back to belief_set as computational core.
- **Why chosen:** only project that ships both AGM operators *and* downstream propagation with an MCP integration path; Python/Neo4j matches our stack.
- **Why not alternatives:** epica — Rust adds an FFI/ops burden for capability we already have in Python; its "5 arXiv papers" grounding is self-citation; keep it on the watch list, not the build list. belief_set alone — no propagation, no provenance; it's a kernel, not a system. Kumiho — no code; use its proofs as the checklist (does the implementation satisfy K*6?) rather than as a component.

#### 3.1.3 Kumiho Formal AGM K*2–K*6 — T2 (preprint, arXiv:2603.17244) [INFO-LIMITED]

- **Mechanism:** formal proofs that iterated belief revision (K*2 through K*6, the Darwiche-Pearl-style iteration postulates) can be represented semantically-equivalently on property graph databases.
- **The research:** pure theory paper. Value: it defines what "correct iterated revision on a graph" *means* — the acceptance checklist for any graph-based AGM implementation (atlas, epica, or our own).
- **Siblings & rivals:** complementary to atlas/epica (they implement, Kumiho specifies). Not a rival to DCPM (different layer again).
- **Benefits:** gives us a formal yardstick for free; prevents us from shipping an AGM implementation that satisfies only the basic postulates while silently violating iterated revision.
- **Negatives:** no code; commercial cloud dependency mentioned in the paper is a concern for self-hosting; preprint — proofs not peer-reviewed yet.
- **Integration plan:** none as a component. Use as test specification: when Atlas's postulate suite runs (§3.1.2 step 3), add K*4 (recovery) and K*6 (iterated revision) cases from Kumiho's definitions.
- **Why chosen:** cheapest possible insurance — a checklist, not a build.
- **Why not alternatives:** none — nothing else provides the iterated-revision-on-graphs correctness standard.

#### 3.1.4 belief_set Python AGM Kernel — T3 (PyPI, ctoth) [INFO-LIMITED]

- **Mechanism:** pure-Python belief sets/bases with expand/contract/revise operators.
- **The research:** none — it's a small library. Its value is as a dependency-free computational fallback.
- **Benefits:** zero infra (no Neo4j); pip-installable; good enough for personal-agent-scale belief state (~10³–10⁴ beliefs); can sit behind the same interface as Atlas.
- **Negatives:** no propagation, no provenance, no peer review; set-theoretic representation may not capture our typed belief edges.
- **Integration plan:** wrap behind `brain/epistemology/agm_backend.py` interface with two drivers: `AtlasBackend` (MCP) and `BeliefSetBackend` (local). Failover automatic.
- **Why chosen:** insurance against Atlas abandonment (alpha project) at zero cost.
- **Why not alternatives:** writing AGM operators from scratch — reinventing a well-specified wheel while a kernel exists; epica — same FFI objection as §3.1.2.

#### 3.1.5 IJCAI 2025 Belief Algebra (Meng et al.) — T1 [VENUE-CONFIRMED-2026-09-24; scope corrected: revision only, no merge operator]

- **Mechanism:** deterministic algebra for iterated belief **revision**: beliefs and evidence represented as belief algebras over preference relations, with a proof that the revision result is uniquely determined given belief state + new evidence, plus a practical algorithm. [SCOPE CORRECTED 2026-09-24: the paper has NO merge or update operators — the earlier "update, merge, and revision" description was wrong; see corrections log #13.]
- **The research:** IJCAI 2025 paper; our audit did not verify this venue, so it stays T2-unverified. Deterministic operators are attractive vs stochastic LLM-based updates (same input → same belief state, which our verification discipline wants).
- **Benefits:** determinism with a uniqueness proof — the strongest available answer to "which revision operator should a safety-conscious agent use." (The previously claimed merge benefit is RETRACTED — the paper is single-agent revision; gap G2 reopens, see §11.)
- **Negatives:** venue unverified; no code; may overlap heavily with what AGM+chains already give us.
- **Integration plan:** venue now confirmed (T1). Evaluate the deterministic revision operators as the single-agent revision core; the multi-agent merge gap (G2) is NOT covered by this paper — it reopens with no formal candidate (see agenda item formal-belief-merge-operators-multi-agent-g2-reopened).
- **Why chosen:** only verified-T1 formal belief-revision operator algebra with a determinism/uniqueness proof.
- **Why not alternatives:** for single-agent revision, AGM stack already covers it; this is a merge-specific addition.

#### 3.1.6 epica — T3 (community code, watch list)

- **Mechanism:** Rust runtime; formal AGM; K*6 semantic-equivalence claim; BLAKE3 Merkle audit trail (every belief operation hash-chained); 12 crates; MCP 2026-native; PyO3 SDK.
- **The research:** none independent. "Grounded in 5 arXiv papers" is self-citation (audit finding). The Merkle audit trail idea is genuinely good (matches our provenance discipline) but is a design pattern we can adopt, not a reason to take a Rust dependency.
- **Benefits:** strongest audit-trail design in the space; MCP-native; if it matures and gets independent verification, it's the best formal core available.
- **Negatives:** T3; Rust ops burden; unverified claims; young project.
- **Integration plan:** none now. Watch quarterly. Steal two ideas immediately: (a) hash-chain the `cognitive_beliefs` change log (BLAKE3 via Python `hashlib` — no Rust needed), (b) make every belief write carry a content-addressed provenance hash.
- **Why chosen for the watch list / not the build list:** same capability class as atlas with higher integration cost and equal (zero) verification.

### 3.2 Category 2: Counterfactual Reasoning

**Mission:** "What would have happened if I had done Y instead of X?" — credit assignment over action choices. Existing `brain/dmn/counterfactual.py` (Pearl regret analysis, `counterfactual_rollouts` table) is the substrate. All mechanisms here are paper-only; no public code exists for agent counterfactual replay. This category is therefore mostly build-from-paper (§6).

#### 3.2.1 CRAFT — T2 (preprint, arXiv:2606.29476)

- **Mechanism:** counterfactual credit assignment via **sibling rollouts** — snapshot the context, run parallel trajectories with alternative actions, compare outcomes, attribute the difference to the action choice.
- **The research:** preprint. The mechanism is clean causal logic (intervene on one variable, hold the rest fixed — Pearl's intervention rung), but each counterfactual costs a full extra agent run.
- **Siblings & rivals:** vs C3 — C3 freezes context and replays with one action varied (cheaper, single-variable isolation); CRAFT runs full sibling trajectories (richer, expensive). They are the same idea at different budgets. vs ActMem — ActMem doesn't execute counterfactuals at all; it *generates counterfactual questions* to improve retrieval (a retrieval augmentation, not a reasoning engine).
- **Benefits:** cleanest attribution semantics; directly extends the existing `counterfactual_rollouts` table (it already stores actual_path/counterfactual_path).
- **Negatives:** cost — every counterfactual is another agent run; attribution across multi-step tool chains (10+ calls) is unsolved (Gap G6); context drift between rollouts can masquerade as action effect (G7).
- **Integration plan:** see the full engine spec §6.1 (shared by CRAFT/C3): context snapshotter → alternative generator → lightweight executor → outcome comparator → delta store → retrieval integration. CRAFT mode = full sibling rollout, gated by a risk/surprise threshold so we only pay for it on failures.
- **Why chosen:** the only mechanism with explicit multi-step attribution semantics for agents.
- **Why not alternatives:** C3 alone — cheaper but leaves-one-out rather than branching, weaker for multi-tool chains; ActMem — different problem (retrieval), included separately below; DoWhy — data-science causal inference library, not an agent cognition mechanism (corrected in v1; see corrections log #9).

#### 3.2.2 C3 Frozen-Context Replay — T2 (preprint, arXiv:2603.06859)

- **Mechanism:** freeze all context except the action variable; leave-one-out replay for clean attribution.
- **Siblings & rivals:** see CRAFT above — same family, different cost point. Complementary, not competing: C3 for single-action decisions, CRAFT for branch-level decisions.
- **Benefits:** one extra replay per counterfactual instead of N; clean single-variable isolation; trivially maps to our hook architecture (re-run the same agent step with a substituted tool call).
- **Negatives:** doesn't capture interaction effects between actions; preprint.
- **Integration plan:** default mode of the §6.1 engine; CRAFT mode reserved for high-surprise failures.
- **Why chosen:** best cost/attribution ratio; the first mode we build.
- **Why not alternatives:** CRAFT-first — burns llama.cpp budget on routine decisions.

#### 3.2.3 ActMem Counterfactual Question Generation — T2 (preprint, arXiv:2603.00026)

- **Mechanism:** generate "what if the user had asked X?" variants of memory queries to expand retrieval recall.
- **The research:** retrieval augmentation evaluated on QA benchmarks; the counterfactuals are *queries*, not executions.
- **Siblings & rivals:** orthogonal to CRAFT/C3 (retrieval vs execution). Sibling in spirit to query expansion (CE-QE work in the wiki) — same trick, different axis.
- **Benefits:** nearly free (one LLM call per query); improves recall on exactly our weak categories (temporal, knowledge-update per LongMemEval category structure).
- **Negatives:** preprint; adds latency to every retrieval; may add noise (irrelevant variants).
- **Integration plan:** in the retrieval path: before pgvector search, generate 2–3 counterfactual reformulations of the query, embed all, merge result sets with reciprocal rank fusion, dedupe.
- **Why chosen:** cheapest recall win in the category; composes with everything else.
- **Why not alternatives:** none — nothing else addresses counterfactual *retrieval*; the alternative is not doing it.

### 3.2.4 Counterfactual Engine (custom build) — T4 (our design, on T1/T2 foundations)

No public code implements counterfactual reasoning for LLM agents. Full design spec in §6.1. Tier T4 for the *engine as a whole* (it's our conjecture how to assemble T2 mechanisms), built on T1 foundations (Pearl's causal hierarchy).

### 3.3 Category 3: Theory of Mind

**Mission:** modeling other agents' beliefs, desires, intentions — for multi-agent Hermes instances and user modeling. Existing `brain/social/tom.py` (recursive ToM levels 1–2) is the substrate.

#### 3.3.1 MetaMind Three-Agent Pipeline — T1 (NeurIPS 2025 spotlight) [VERIFIED-2026-09-23]

- **Mechanism:** three sequential agents: **ToM Agent** infers the target's beliefs/desires → **Moral Agent** applies social norms to judge candidate responses → **Response Agent** generates the response consistent with both. Social memory tracks belief trajectories over interactions.
- **The research:** NeurIPS 2025 spotlight — venue confirmed by the audit (spotlight ≈ top 2-3% of submissions). Reported 35.7% improvement in social scenarios is the paper's claim.
- **Siblings & rivals:** vs COKE/COLM — COKE is a *model* (fine-tuned LLaMA-2 on cognitive chains); MetaMind is a *pipeline pattern* (any LLM can fill each agent role). They compose: COLM could power the ToM Agent role. vs ToMAgent — MetaMind's stages are fixed; ToMAgent generates explicit hypotheses and simulates short horizons before choosing an utterance (more exploratory, more expensive).
- **Benefits:** verified peer review; pattern (not weights) so it runs on our local Qwen via llama.cpp with no fine-tuning; the Moral Agent stage maps directly onto our behavioral contracts; social memory = belief trajectories, which is the same data structure DCPM chains already give us.
- **Negatives:** designed for social-conversation scenarios; tool-use coordination between agents is not what the paper evaluates (Gap G10); three LLM passes per decision (latency).
- **Integration plan:** (1) Implement as three sequential prompts in the agent loop's pre-response stage, active only in multi-agent coordination contexts (main ↔ coder ↔ oracle ↔ researcher ↔ flowbot). (2) ToM Agent reads `user_mental_models` + other instances' decision logs (decision_logger output). (3) Moral Agent's norm set = behavioral contracts from SOUL.md/SYSTEM-RULES.md. (4) Response Agent = the normal response path, constrained by the first two stages' outputs. (5) Social memory: reuse `cognitive_beliefs` chains with a `subject=agent:<name>` scope.
- **Why chosen:** the strongest verified-evidence ToM architecture; integrates as prompts, not infrastructure.
- **Why not alternatives:** COKE alone — a model without a pipeline; we'd still need the norm-application and response-constraint stages. ToMAgent — hypothesis simulation is more compute for uncertain gain at our scale (2 agents we coordinate with regularly); revisit if coordination failures persist.

#### 3.3.2 COKE / COLM — T1 (ACL 2024 long paper) [VERIFIED-2026-09-23]

- **Mechanism:** COKE is a dataset of 45,369 chains of thought for theory-of-mind reasoning (percept → belief → desire → intention → response chains); COLM is LLaMA-2 fine-tuned on it. On ToM benchmarks COLM outperforms much larger models because ToM reasoning is distilled into weights rather than prompted.
- **The research:** ACL 2024 long paper (venue verified; *not* oral — corrections log #1). Model on HuggingFace.
- **Siblings & rivals:** vs prompted ToM (MetaMind roles) — COLM does in one pass what prompting does in three, but only for the ToM-inference step. vs Rabinowitz 2018 Machine ToM (in Oracle brain, T1 theory) — ToMnet learns a character model from observation; COKE trains on human-authored chains.
- **Benefits:** verified venue; drop-in local model; 45K chains cover classic false-belief shapes.
- **Negatives:** LLaMA-2 base — old, weak on tool-use ToM; GGUF conversion needed for llama.cpp (no official GGUF — conversion required, quality at Q4 untested); fine-tuning on our own interaction data would need GPU time (Gap G12).
- **Integration plan:** (1) Convert COLM to GGUF, load as a secondary llama.cpp model. (2) Expose as a tool `tom_infer(target, situation)` called by MetaMind's ToM Agent stage. (3) Benchmark against prompted ToM on 20 historical multi-agent miscoordination cases from decision logs; keep only if it wins.
- **Why chosen:** only verified, locally-runnable ToM model.
- **Why not alternatives:** API ToM models — violates local-first; prompting only — MetaMind pipeline already covers it, COLM is the upgrade path if prompting proves weak.

#### 3.3.3 ToMAgent — T1 (arXiv:2509.22887, ACL Findings 2026 [VENUE-CONFIRMED-2026-09-24])

Explicit-hypothesis generation + short-horizon simulation for utterance selection. Hold in Phase 4; the audit did not verify the ACL Findings venue. Mechanism documented; build only if MetaMind+COLM underperforms on coordination.

#### 3.3.4 MindForge — T2 (arXiv:2411.12977)

Structured ToM templates: percepts → beliefs → desires → actions. Value: a *schema* for ToM state that maps cleanly onto `user_mental_models` (which already has attributed_belief/ground_truth/discrepancy). Integration: adopt the template as the canonical schema for ToM records; no new infrastructure. Chosen over free-form ToM inference because structured records are auditable and diffable — same reason we keep beliefs structured.

#### 3.3.5 Dynamic ToM Belief Trajectory Tracking — T2 (arXiv:2603.14646) [INFO-LIMITED]

Tracks belief trajectories over time rather than single-point false-belief tests. This is ToM's version of DCPM chains. Integration: reuse the same supersedes-chain substrate with `subject=<other agent>`; trajectory = chain walk. Chosen because it unifies two categories on one data structure.

#### 3.3.6 ToM Wiki Entry (synthesis) — internal deliverable

Create `concepts/theory-of-mind-agents.md` synthesizing the above with the wiki's existing 1,558-file ToM base (which includes Rabinowitz 2018, Wimmer & Perner 1983, Apperly 2012 — all T1 theory already in the Oracle brain).

### 3.4 Category 4: Procedural Memory

**Mission:** learning skills from experience, compiling workflows, executing them efficiently. Existing `brain/basal_ganglia/compiler.py` (ACT-R skill acquisition, threshold=3) is the substrate. This is the best-covered category in our wiki (346 files).

#### 3.4.1 HiCL — T1 (AAAI 2026) [VERIFIED-2026-09-23] — **the standout of the whole audit**

- **Mechanism:** hippocampal-inspired continual learning: a **DG-gated Mixture-of-Experts** where the dentate gyrus analog gates which expert (or new expert) handles an input — pattern separation assigns dissimilar experiences to different experts; pattern completion retrieves and reuses similar ones; **sharp-wave-ripple replay** consolidates; **EWC (Elastic Weight Consolidation)** protects old skills from catastrophic forgetting during consolidation.
- **The research:** AAAI 2026, venue confirmed via ojs.aaai.org. The audit called HiCL "the real deal for what you're building" — a real paper, directly about procedural memory consolidation via hippocampal mechanisms, in Python/PyTorch.
- **Siblings & rivals:** vs MEMTIER — MEMTIER (our wiki's anchor, 446-line analysis) is a *memory-tier* paper (procedural tier gets μ=1.4 retrieval boost, cyclic preference detection via spectral analysis); HiCL is a *learning* mechanism (how skills get written without clobbering each other). Complementary: MEMTIER says procedural memories deserve a boost; HiCL says how to consolidate them safely. vs AWM — AWM induces *workflows* from trajectories (symbolic, LLM-level); HiCL trains *parameters* (neural). Different layers again. vs GraSP — GraSP organizes skills as a typed DAG with local repair; HiCL is agnostic to skill representation. vs DSPy — DSPy optimizes prompts/pipelines and is NOT a memory system (corrections log #10); it stays in our stack for pipeline tuning only.
- **Benefits:** verified peer review; Python/PyTorch (our stack); directly implements the hippocampal mechanics our `brain/hippocampus/` already simulates, but with learning theory (EWC) attached; addresses catastrophic forgetting — the exact failure mode of naive skill compilation.
- **Negatives:** needs GPU for the training/consolidation loops (desktop-worker GPU host or vLLM box); MoE training adds complexity; AAAI 2026 paper's benchmarks are its own — our tasks differ.
- **Integration plan:** (1) Stand up HiCL's DG-gated MoE on the desktop GPU profile. (2) Feed it our trajectory data (session JSONL → skill episodes; the dreaming plugin's Deep Sleep phase already produces candidate skill compilations). (3) Route: dreaming plugin Deep Sleep → HiCL consolidation (replaces naive threshold-3 compilation for neural skills) → compiled skills registered in the procedural tier. (4) Keep threshold-3 symbolic compilation as fallback for when GPU is unavailable. (5) Evaluate: skill reuse rate + regression rate on a held-out month of sessions.
- **Why chosen:** the only T1 component that is both a learning mechanism AND hippocampally grounded; verified venue; Python.
- **Why not alternatives:** MEMTIER alone — boost without safe consolidation; AWM alone — symbolic only, no parameter-level learning; GraSP/SkillDAG — structure without learning; SkillTrace — selection without learning.

#### 3.4.2 MEMTIER Procedural Tier — T2 preprint with T1-grade internal analysis (2026-09-24 venue check: arXiv-only, "Under review") [VERIFIED-2026-09-23: 446-line wiki analysis exists]

- **Mechanism:** three-tier memory (working/context, episodic, semantic) plus a procedural tier that receives a **μ=1.4 retrieval boost** — procedural memories (skills, routines) are promoted in retrieval ranking over equally-similar episodic ones. Cyclic preference detection via spectral analysis catches recurring patterns.
- **The research:** deeply analyzed in our wiki (446 lines, `research/memory-tier-integration-followup.md`); the procedural-tier integration analysis (`procedural-tier-integration-cyclic-fps.md`, 546 lines) extends it to cyclic false-positive suppression.
- **Benefits:** already designed against our stack in the wiki analyses; the boost is a one-line ranking change; spectral cycle detection is deterministic (our verification discipline likes deterministic).
- **Negatives:** μ=1.4 is a tuned constant from the paper's tasks — must re-tune on ours; the venue for MEMTIER itself needs re-verification before citing as peer-reviewed.
- **Integration plan:** retrieval ranking already has tier weights in the memory-tier design; adopt μ=1.4 as initial value with an A/B re-tune; spectral cycle detection as a nightly cron job over retrieval logs.
- **Why chosen:** deepest internal analysis of any component; mechanism is simple and stack-native.
- **Why not alternatives:** none — it's the tier structure itself.

#### 3.4.3 AWM (Agent Workflow Memory) — T1 (ICML 2025, arXiv:2409.07429) [VENUE-CONFIRMED-2026-09-24]

- **Mechanism:** induces reusable **workflows** (abstracted tool-call sequences) from agent trajectories; at inference, retrieved workflows guide the agent, cutting exploration. Paper reports +51.1% on WebArena (paper's claim).
- **Siblings & rivals:** vs GraSP — AWM induces sequences; GraSP adds typing + DAG structure + local repair (re-run only the failed subgraph). vs SkillTrace — SkillTrace adds a query-skill graph with 3-level hierarchical decomposition for *selection*. vs SkillDAG — SkillDAG lets skills discover composition relationships from experience (self-evolving). All four are the same family (trajectory → reusable structure) with increasing structural sophistication: AWM (sequences) < GraSP (typed DAG) < SkillTrace (hierarchical selection) ≈ SkillDAG (self-evolving edges).
- **Benefits:** ICML 2025 (needs venue re-verification, but arXiv ID is solid); Python; directly consumes the trajectory data we already log; workflows are inspectable (symbolic, not neural weights).
- **Negatives:** +51.1% is on WebArena, not our tasks; induced workflows can be wrong (needs the conflict/repair machinery of GraSP); no forgetting mechanism.
- **Integration plan:** (1) Mine session JSONL for recurring successful tool sequences (≥3 occurrences, ≥80% success). (2) Abstract into workflow templates (tool names + slot types, not raw args). (3) Store in procedural tier with provenance (which sessions generated them). (4) Retrieval: at agent start, retrieve top-k relevant workflows into context. (5) Failure → GraSP-style local repair: mark the failed step, re-run from there, log the repair.
- **Why chosen:** the base induction mechanism everything else in the family builds on.
- **Why not alternatives:** jumping straight to SkillDAG — self-evolving structure without a validated induction base is T4 risk; GraSP adds repair (keep as Phase 3); SkillTrace adds selection (Phase 3, only if retrieval precision becomes the bottleneck).

#### 3.4.4 GraSP — T2 (arXiv:2604.17870) [INFO-LIMITED]

Typed DAG skill composition with local repair. Phase 3. Chosen for the local-repair mechanism (re-run only failed subgraph) — the thing AWM lacks. Negatives: preprint, thin wiki coverage, type system must be designed for our tools.

#### 3.4.5 SkillTrace — T2 (arXiv:2608.02356) [INFO-LIMITED]

Query-Skill Graph, 3-level hierarchical decomposition, SOTA on SkillsBench (paper's claim). Phase 3, selection-layer only. Chosen for selection precision if workflow retrieval gets noisy.

#### 3.4.6 SkillDAG — T2 (arXiv:2606.03056) [INFO-LIMITED]

Self-evolving typed skill graph. Phase 4 — the self-evolving mechanism conflicts-risk with DCPM schema induction (two systems evolving structure at once); revisit after DCPM is stable.

### 3.5 Category 5: Hippocampal Indexing

**Mission:** pattern separation (DG), attractor dynamics (CA3), retrieval (CA1) for associative recall. Existing `brain/hippocampus/` (associative.py, replay.py) is the substrate.

#### 3.5.1 HippoRAG — T1 (NeurIPS 2024, arXiv:2405.14831) [VENUE-CONFIRMED-2026-09-24]

- **Mechanism:** implements Teyler & DiScenna's hippocampal indexing theory: LLM builds a knowledge graph from passages; a query activates seed nodes; **Personalized PageRank** spreads activation over the graph; the highest-activation nodes are retrieved. Multi-hop recall because activation flows through edges, not just similarity.
- **The research:** NeurIPS 2024 (venue needs re-verification in a future pass; arXiv ID solid). Reported: ~20% better than vector RAG on multi-hop QA, 10–30× cheaper than iterative retrieval (paper's claims). Wiki coverage thin (43 files) — [INFO-LIMITED], dossier leans on the paper.
- **Siblings & rivals:** vs plain pgvector search — pgvector is similarity-only (one hop); HippoRAG adds graph diffusion (multi-hop). Not rivals: HippoRAG sits ON TOP of vector search (seeds come from similarity). vs mokosh SDR — SDR handles pattern *separation* (making similar inputs distinguishable); HippoRAG handles *association* (linking related memories). Different subfield of the same hippocampus. vs MRAgent (§5.4) — MRAgent reconstructs memories from cue-tag-content graphs at read time; HippoRAG indexes at ingest. Write-time vs read-time indexing.
- **Benefits:** the only T1 multi-hop retrieval mechanism in the category; cost claim (10-30× cheaper than iterative retrieval) matters for local inference budgets; composes with existing Neo4j.
- **Negatives:** requires LLM calls at ingest to build the KG (we already do this via graphify — but graphify's semantic pass is currently broken, see §0.3 Round 1); PPR damping parameter needs tuning; the 20% is on QA benchmarks, not conversational memory.
- **Integration plan:** (1) Reuse graphify's pipeline: at ingest, LLM extracts entities/relations from wiki pages (this is the broken semantic pass — fixing it for HippoRAG means fixing it for graphify too; one fix, two wins). (2) Seed retrieval: pgvector top-k as seeds. (3) PPR over the Neo4j subgraph (damping 0.85 initial). (4) Merge PPR results with vector results via reciprocal rank fusion. (5) Evaluate on multi-hop questions from our own session history.
- **Why chosen:** only verified multi-hop mechanism; leverages infra we already run.
- **Why not alternatives:** GraphRAG (Microsoft) — heavier pipeline, cloud-oriented; plain vector — no multi-hop; MRAgent — read-time reconstruction is Phase 4 experimental.

#### 3.5.2 mokosh (Rust HTM SDR) — T3 [INFO-LIMITED]

- **Mechanism:** implements Numenta's HTM Spatial Pooler — Sparse Distributed Representations where similar inputs map to dissimilar sparse codes (pattern separation). Ahmad & Hawkins 2015 lineage (T1 theory).
- **Siblings & rivals:** vs embedding-space separation — embeddings separate by distance but nearby points remain confusable; SDRs make similar inputs *orthogonal*. vs omega-hippocampus — omega implements the full DG/CA3/CA1 loop + place/grid cells + SWR in Rust; mokosh implements SDR specifically. Overlapping but omega is broader.
- **Benefits:** orthogonalization is exactly what our retrieval needs for near-duplicate memories (the cyclic false-positive problem the procedural tier analysis documents); Rust = fast.
- **Negatives:** T3, no papers on the library itself; Rust FFI burden; HTM's applicability to text embeddings (vs sensory data) is unproven — this is a [CONJECTURE] step.
- **Integration plan:** Phase 4 experimental: FFI wrapper, apply SDR to near-duplicate detection in the write path (before insertion, SDR-code the candidate memory; if code collides with an existing memory's code, route to consolidation instead of insert).
- **Why chosen:** the only shipped SDR implementation with Python access.
- **Why not alternatives:** omega-hippocampus — broader but heavier; choose mokosh for the narrow SDR need, watch omega for the full loop.

#### 3.5.3 Holographic Reduced Representations (HoloVec / amari-holographic) — T3 libs on T1 theory (Plate 2003; Schlegel 2022)

- **Mechanism:** binding/unbinding: `bind("preference", "food", "italian")` produces one vector; `unbind(bound, "food") ≈ "italian"`. Algebraic memory composition.
- **Benefits:** T1 theory (Plate); enables structured queries vector search can't express ("what did the user prefer about food" without scanning); bridges to our existing holographic layer (MnemoCore/HoloGraph).
- **Negatives:** libraries are T3; binding noise accumulates; embedding models aren't trained for HRR algebra — the bound vector's neighbors are not guaranteed meaningful (a real risk, documented).
- **Integration plan:** Phase 4: pilot HRR binding on the preference slot of `user_mental_models`; measure unbind accuracy against ground-truth preferences; only proceed if accuracy > 80%.
- **Why chosen:** only mechanism for algebraic memory composition; theory is T1.
- **Why not alternatives:** none — nothing else does binding/unbinding.

#### 3.5.4 CA3 Attractor Pattern Completion (Rolls-Treves) — T1 theory, T4 build

Sparse recurrent autoassociative network for incomplete-cue → full-memory recall. No public implementation exists; the math is T1 (Rolls & Treves 1998). Build spec in §6.2. [CONJECTURE] that attractor dynamics add value over PPR completion at our scale — the pilot must prove it.

### 3.6 Category 6: Cognitive Routing

**Mission:** deciding WHICH cognitive process to use (System 1 fast vs System 2 slow) and HOW to route attention. Existing `brain/cortex/router.py` (threshold=0.5) is the substrate.

#### 3.6.1 DCPM System 1/2 — T1 mechanism (paper T2 [preprint-only confirmed 2026-09-24], wiki analysis T1-internal)

Daytime System 1 (synchronous, extract/reconcile) vs nighttime System 2 (asynchronous, schema induce/sweep). Same paper as §3.1.1; the routing half. Maps to: agent loop = System 1, dreaming plugin = System 2. Chosen because it's the only dual-process model with an operational implementation path; alternative (Kahneman-style labels without mechanics) is not actionable.

#### 3.6.2 Sibelium Thalamic Gating — T3 [VERIFIED-2026-09-23: repo real, 34 mechanisms, CE formula in code]

- **Mechanism:** 34 cognitive mechanisms; the load-bearing one is the thalamic routing formula: `CE = Prompt_Length×0.4 + Cognitive_Stress×0.4 + Graph_Complexity×0.2` — a cognitive-effort score that gates when the agent escalates from fast to slow processing. Python + llama-cpp + ChromaDB stack (same shape as ours).
- **The research:** community code; the "ICLR 2026 Workshop paper" claim was **not confirmed** by the audit — treat as T3. The CE formula's weights (0.4/0.4/0.2) are the project's own tuning, not validated research.
- **Siblings & rivals:** vs our router.py threshold=0.5 — ours is a single fixed threshold on one signal; Sibelium's CE is a weighted composite of three signals. Same idea, richer feature set. vs LIMEN — LIMEN implements Global Workspace Theory's attention auction (processes bid for workspace access; highest bid wins and is broadcast); Sibelium implements a gating *formula*; DCPM defines the S1/S2 *split*. Three different layers: what splits (DCPM), what scores (Sibelium), what arbitrates (LIMEN).
- **Benefits:** concrete formula we can adopt in an afternoon; three-signal composite beats single-threshold routing; stack-compatible (llama.cpp).
- **Negatives:** weights are unvalidated tuning; T3; ChromaDB dependency we don't need (swap for pgvector).
- **Integration plan:** (1) Port the CE formula into `brain/cortex/router.py` as a second opinion: CE computed per turn from prompt length (tokens), cognitive stress (working-memory occupancy + open-loop count), graph complexity (retrieved subgraph size). (2) Router decision = current threshold AND CE agreement; disagreement → System 2 (safe default). (3) Log every routing decision with features; after 1,000 turns, refit weights on outcomes (did S2 engagement predict success?).
- **Why chosen:** cheapest upgrade to the weakest part of the current brain (single-threshold routing).
- **Why not alternatives:** LIMEN — adopting the attention auction wholesale is a bigger architectural bet (Phase 3); Gated-Memory Routing — targets memory writes, not process routing (different category overlap).

#### 3.6.3 LIMEN GWT Attention Auction — T3 on T1 theory (Baars 1988; Shanahan 2006) [INFO-LIMITED]

Zero-dependency Python GWT runtime: attention auction, ignition threshold, stdlib-only. Phase 3. Chosen over building GWT from scratch because the auction mechanism is a faithful, minimal implementation of the T1 theory; the wiki's 117-file GWT base (§5.1) provides the theoretical grounding. Negatives: T3; auction dynamics at our scale (5 processes) may be overkill vs Sibelium's formula.

#### 3.6.4 Gated-Memory Routing — T2 (arXiv:2609.00237, EMNLP 2026 Main) [VENUE-PARTIAL-2026-09-24: author-claimed only; recheck after Oct 2026 conference]

Learned write/retrieval gates with adaptive halting. Phase 2-3: replaces memory-admission heuristics with learned policies IF the venue verifies and IF we can generate training signal (write decisions + later-use outcomes). Sibling: our wiki's memory-write-admission research (A-MAC, ConsistencyGate, SAGE, Nemori, MemRouter — 1,025 files) is the internal analysis base; Gated-Memory Routing is the external paper anchor.

#### 3.6.5 Sibelium-DCPM Integration Comparison — internal synthesis item

Design doc comparing the three routing layers (DCPM split / Sibelium score / LIMEN arbitration) and specifying the integrated router. Deliverable: `research/cognitive-routing-integration.md`.

### 3.7 Category 7: Valence / Emotion

**Mission:** computational emotion modeling — valence/arousal dynamics, affect-driven decision modulation. Existing `brain/limbic/` (valence.py, somatic.py) is the substrate. **Scope guard:** depth psychology (Jung/Freud/Bernays) wiki entries are NOT computational emotion and must not be used for implementation.

#### 3.7.1 LIDA Affect Module — T1 theory (Franklin et al., IEEE TAMD 2013) [INFO-LIMITED: wiki hits are mostly false positives]

- **Mechanism:** LIDA's cognitive cycle (perception → comprehension → action selection → learning) with an integrated affect/drive module: feelings modulate attention and action selection via somatic markers.
- **The research:** IEEE TAMD 2013 is a real, peer-reviewed venue (T1 for the theory). Our wiki's "1,269 LIDA files" are almost entirely "licensing" false positives — actual LIDA coverage is near zero, hence INFO-LIMITED.
- **Siblings & rivals:** vs swaylq — LIDA is the academic architecture (T1) with a dated Python rewrite; swaylq is a modern 7-layer community implementation. vs our limbic system — ours already implements valence/arousal/somatic markers; LIDA adds the *cognitive cycle* framing (affect modulates each stage, not just action).
- **Benefits:** T1 theoretical grounding for the whole category; the cognitive-cycle integration pattern is the design template for wiring affect into the agent loop.
- **Negatives:** the "Python rewrite with tests" is old and unmaintained [README-CLAIM on its test coverage]; LIDA is a full cognitive architecture — we only want the affect module; wiki coverage near zero means no internal analysis to lean on.
- **Integration plan:** adopt the *pattern*, not the code: at each of the 7 pipeline stages in `process_incoming_stimulus`, allow the current affective state (valence/arousal/allostatic load) to modulate the stage's parameters (e.g., negative valence → lower action-gate threshold → more caution). Document as `brain/limbic/CYCLE-INTEGRATION.md`.
- **Why chosen:** the only T1-grounded full cognitive cycle with affect integrated.
- **Why not alternatives:** building the integration pattern from scratch — LIDA already published it; adopting full LIDA — we don't want a second brain, we want the affect wiring.

#### 3.7.2 swaylq/emotion-system — T3 [INFO-LIMITED: 0 wiki files]

- **Mechanism:** 7-layer architecture: PAD (pleasure-arousal-dominance) state → Lazarus primary appraisal → Scherer Component Process Model → Damasio somatic markers → 14 emotion channels → meta-emotions → policy modulation. 500-token compressed state representation.
- **The research:** none — community code. But each layer cites T1 theory (Lazarus, Scherer, Damasio are foundational).
- **Siblings & rivals:** vs our limbic — ours has valence/arousal (2 of PAD's 3 dims) + somatic markers; swaylq adds dominance, appraisal theory, 14 channels, meta-emotion. vs NexusCortex Emotion (Go) — similar PAD core, production Go code, "137 tests" unverified; Go blocks direct use. vs biomind HIPECA — theoretical grounding layer, Python, QualiaMetrics dataclass.
- **Benefits:** most architecturally complete open-source emotion system found; 500-token compressed state is directly injectable into working memory / context; the layering (state → appraisal → marker → channels → modulation) is a clean decomposition we can adopt wholesale as a spec.
- **Negatives:** T3; zero wiki coverage; 14 channels may be overgranular for our use; no benchmarks.
- **Integration plan:** (1) Read the repo; port the layer structure into `brain/limbic/` as `emotion_system.py` with our own persistence. (2) Start with PAD + appraisal + somatic (layers 1-4); add channels only if modulation needs finer grain. (3) The 500-token state injection: serialize PAD + top-3 channels + meta-emotion into the agent's working-memory block.
- **Why chosen:** the most complete *runnable* reference for the category; saves us designing the layering ourselves.
- **Why not alternatives:** NexusCortex — Go; port cost > port cost of swaylq (Python). biomind — theory layer, complements rather than replaces. Maxim — reward learning specifically (see below).

#### 3.7.3 TOAQ Control-Theoretic VA Dynamics — T2 (Bruneteau 2025) [INFO-LIMITED]

- **Mechanism:** mathematical (control-theoretic) model of valence-arousal state transitions with stability guarantees — the VA state evolves under bounded dynamics rather than free drift.
- **Benefits:** stability guarantees address our Gap G28 (long-term emotional divergence over months); MIT-licensed Python implementation exists.
- **Negatives:** T2 preprint; zero wiki coverage; control theory on VA states is a young line of work.
- **Integration plan:** Phase 3: adopt TOAQ's VA update equations as the *dynamics* inside our limbic valence engine (replacing free-running updates), keeping our own appraisal inputs.
- **Why chosen:** only mechanism with stability guarantees for VA dynamics.
- **Why not alternatives:** free-running VA updates — unbounded drift is the documented failure mode.

#### 3.7.4 Maxim (NAc reward learning) — T3 [INFO-LIMITED]

NAc (nucleus accumbens) reward/punishment learning with eligibility traces, PainBus architecture. Phase 4: the reward-signal design for skill consolidation (what counts as success signal for HiCL). T3 but mechanism maps to our record_action_outcome(success) signal. Chosen over nothing — no alternative implements eligibility-trace reward learning in Python for agents.

#### 3.7.5 pyClarion Emotion Contagion — T3 on T1 theory (CLARION, IEEE SSC 2016)

Emotion contagion between agents. Phase 4 experimental: should coder's frustration modulate oracle's caution? [CONJECTURE] that contagion improves multi-agent coordination — the pilot must prove it or it stays off.

#### 3.7.6 AFT Emotional Memory (emotional-memory) — T3 [INFO-LIMITED]

Russell-Mehrabian PAD + affective field theory + mem0 integration. Phase 4. Value: the affective-field (context-dependent valence) idea for emotional memory; the mem0 integration is irrelevant (we have our own tiers).

### 3.7.7 Emotion Computation Wiki Entry (synthesis) — internal deliverable

Create `concepts/emotion-computation.md` synthesizing the above with the Oracle brain's Emotion-Cognition directory (109 files: Somatic Marker Hypothesis, Appraisal Theory, Emotion Regulation/Gross, Cognitive Reappraisal — all T1 theory).

---

## 4. Verified-Project Dossier Cross-Reference

The 18 projects audited on 2026-09-23 (§0.2), mapped to where each is handled in this proposal:

| Project | Tier | Where it lands | Phase |
|---------|------|----------------|-------|
| COKE/COLM | T1 | §3.3.2 ToM local model | 2 |
| HiCL | T1 | §3.4.1 Procedural consolidation | 1 |
| MetaMind | T1 | §3.3.1 ToM pipeline | 2 |
| AWM | T1 [VENUE-CONFIRMED-2026-09-24] | §3.4.3 Workflow induction | 3 |
| MEMTIER | T2 preprint (T1-grade internal analysis) | §3.4.2 Procedural tier boost | 1 |
| HippoRAG | T1 [VENUE-CONFIRMED-2026-09-24] | §3.5.1 Multi-hop indexing | 1 |
| DCPM | T2 paper / T1-internal analysis | §3.1.1 + §3.6.1 | 1 |
| Kumiho | T2 | §3.1.3 AGM correctness checklist | 3 (test spec only) |
| IJCAI-2025 belief algebra | T1 [VENUE-CONFIRMED-2026-09-24] | §3.1.5 Deterministic revision (merge retracted) | 4 |
| CRAFT | T2 | §3.2.1 Sibling rollouts | 3 |
| C3 | T2 | §3.2.2 Frozen-context replay | 3 |
| ActMem | T2 | §3.2.3 Counterfactual query gen | 2 |
| TOAQ | T2 | §3.7.3 VA stability dynamics | 3 |
| Gated-Memory Routing | T2 [VENUE-PARTIAL-2026-09-24] | §3.6.4 Learned write gates | 3 |
| GraSP | T2 | §3.4.4 Typed DAG + repair | 3 |
| SkillTrace | T2 | §3.4.5 Hierarchical selection | 3 |
| SkillDAG | T2 | §3.4.6 Self-evolving graph | 4 |
| MemoBrain | T2 preprint | §5.9 Executive memory (build-from-paper) | 4 |
| CogniFold | T2 preprint | §5.2 Always-on CLS memory | 4 |
| MemCog | T2 preprint | Watch list — no code | — |
| TrustMem | T2 preprint | §6.3 Transition verifier spec | 4 |
| SCRUBJAY-MEM | T2 preprint | §5.10 Perishability (build-from-paper) | 4 |
| CogFlow | T2 under review | Watch list | — |
| atlas | T3 | §3.1.2 AGM + Ripple via MCP | 2 |
| epica | T3 | §3.1.6 Watch list (steal Merkle pattern) | — |
| belief_set | T3 | §3.1.4 AGM kernel fallback | 2 |
| Sibelium | T3 | §3.6.2 CE routing formula | 2 |
| LIMEN | T3 | §3.6.3 GWT auction | 3 |
| swaylq emotion-system | T3 | §3.7.2 7-layer emotion spec | 3 |
| mokosh | T3 | §3.5.2 SDR pattern separation | 4 |
| omega-hippocampus | T3 | §3.5.2 sibling — full-loop watch | — |
| NexusCortex | T3 (Go) | §3.7.2 rejected (language) | — |
| biomind/HIPECA | T3 | §3.7.2 theory companion | 4 |
| Maxim | T3 | §3.7.4 Reward signal design | 4 |
| snath-ai/DMN | T3 | Watch list — DMN contracts | — |
| defaultmodeAGENT | T3 | Watch list | — |

**Reading:** 3 verified-T1 projects are anchors (COKE, HiCL, MetaMind). 6 preprints are build-from-paper or watch. 9 community-code projects: 5 adopted with eyes open (atlas, belief_set, Sibelium, LIMEN, swaylq), 4 watch-list (epica, omega-hippocampus, snath-ai/DMN, defaultmodeAGENT), 1 rejected on language grounds (NexusCortex, Go).

### 4.1 Master Component Matrix

One row per *build* component (watch-list and rejected projects stay in §4's table; this matrix is what gets built). Sortable mentally by any column; the §3 reference is where the full dossier lives.

| # | Component | Tier | Brain part (§2.5) | Phase | Integration cost | Verification | Dossier |
|---|-----------|------|--------------------|-------|------------------|--------------|---------|
| 1 | DCPM supersedes chains | T1 mech / T2 paper | Hippocampus→cortex transfer | 1 | Low (2 columns + write/read path) | Wiki analysis 331 lines | §3.1.1 |
| 2 | MEMTIER μ=1.4 procedural boost | T2 preprint (T1-int analysis) | Striatum (habit retrieval) | 1 | Low (ranking constant) | Wiki analysis 446 lines; arXiv-only confirmed 2026-09-24 | §3.4.2 |
| 3 | HiCL DG-gated MoE consolidation | T1 [VERIFIED] | DG + SWR replay | 1 | Medium (GPU, PyTorch) | AAAI 2026 confirmed | §3.4.1 |
| 4 | HippoRAG PPR over Neo4j | T1 [VENUE-CONFIRMED] | CA1 readout | 1 | Medium (fix graphify semantic pass) | NeurIPS 2024 proceedings confirmed 2026-09-24 | §3.5.1 |
| 5 | MetaMind 3-agent ToM pipeline | T1 [VERIFIED] | TPJ / mentalizing | 2 | Low (prompts) | NeurIPS 2025 spotlight confirmed | §3.3.1 |
| 6 | COKE/COLM local ToM model | T1 [VERIFIED] | TPJ / mentalizing | 2 | Medium (GGUF convert + bench) | ACL 2024 long confirmed | §3.3.2 |
| 7 | Atlas AGM + Ripple (MCP) | T3 | Prefrontal (belief ops) + propagation | 2 | Medium (MCP server + pilot) | Repo verified; claims self-asserted | §3.1.2 |
| 8 | belief_set AGM fallback | T3 | Prefrontal (belief ops) | 2 | Low (pip + interface) | Repo verified | §3.1.4 |
| 9 | Sibelium CE routing formula | T3 | Thalamus (gate) | 2 | Low (formula port) | Repo verified; weights unvalidated | §3.6.2 |
| 10 | ActMem counterfactual query gen | T2 | Thalamus (recall widening) | 2 | Low (prompt + RRF) | Preprint | §3.2.3 |
| 11 | Counterfactual engine (C3→CRAFT) | T2→ours | DMN | 3 | High (full engine, §6.1) | Build spec only | §3.2.4/§6.1 |
| 12 | AWM workflow induction | T1 [VENUE-CONFIRMED] | Striatum (habit, symbolic) | 3 | Medium (JSONL mining) | PMLR v267 confirmed 2026-09-24 | §3.4.3 |
| 13 | GraSP typed DAG + repair | T2 | Striatum (habit structure) | 3 | Medium (type schema) | Preprint | §3.4.4 |
| 14 | LIMEN GWT auction | T3 on T1 theory | Global workspace | 3 | Medium (arbitration layer) | Repo INFO-LIMITED | §3.6.3 |
| 15 | swaylq 7-layer emotion port | T3 | Amygdala + insula | 3 | Medium (port layers 1–4) | Repo INFO-LIMITED | §3.7.2 |
| 16 | TOAQ VA dynamics | T2 | Amygdala (stability) | 3 | Low (update equations) | Preprint | §3.7.3 |
| 17 | Gated-Memory Routing | T2 [VENUE-PARTIAL] | Hippocampal write gate | 3 | High (training signal) | Author-claimed EMNLP 2026; recheck post-conference | §3.6.4 |
| 18 | Atlas↔Kumiho postulate suite | T2 | Prefrontal (belief correctness) | 3 | Low (test cases) | Preprint | §3.1.3 |
| 19 | mokosh SDR near-dup gate | T3 | DG (separation) | 4 | Medium (Rust FFI) | Repo INFO-LIMITED | §3.5.2 |
| 20 | HRR binding pilot | T3 on T1 theory | CA3 (algebraic completion) | 4 | Low (pilot) | Theory T1; libs T3 | §3.5.3 |
| 21 | CA3 attractor (Rolls-Treves) | T1 math / T4 build | CA3 (attractor) | 4 | Medium (NumPy net) | Math T1; value [CONJECTURE] | §6.2 |
| 22 | MemoBrain dependency analysis | T2 | Basal ganglia (gate memory) | 4 | Medium (build from paper) | Preprint, no repo | §5.9 |
| 23 | SCRUBJAY perishability | T2 | Neocortex (forgetting schedule) | 4 | Low (column + decay pass) | Preprint, no repo | §5.10 |
| 24 | TrustMem transition verifier | T2 | Hippocampal write gate | 4 | Medium (write-gate) | Preprint, no repo | §6.3 |
| 25 | CogniFold always-on CLS | T2 | Neocortex+hippocampus (transfer) | 4 | Medium (watch first) | Preprint | §5.2 |
| 26 | MRAgent active reconstruction | internal | CA1 (read-time assembly) | 4 | Low (pilot on fragments) | Wiki analysis exists | §5.4 |
| 27 | Maxim NAc reward signal | T3 | VTA/NAc (learning signal) | 4 | Low (signal design) | Repo verified | §3.7.4 |
| 28 | pyClarion contagion pilot | T3 | Amygdala (social) | 4 | Low (pilot) | Repo INFO-LIMITED | §3.7.5 |
| 29 | SkillDAG self-evolving graph | T2 | Striatum (habit topology) | 4 | Medium | Preprint | §3.4.6 |
| 30 | IJCAI-2025 deterministic revision | T1 [VENUE-CONFIRMED] | Prefrontal (belief ops) | 4 | Low (evaluation) | IJCAI proceedings confirmed; merge claim retracted | §3.1.5 |
| 31 | epica-style BLAKE3 change-log hash chain | T3 idea | Provenance (not a region) | 4 | Low (pure Python) | Pattern from verified repo | §3.1.6 |
| 32 | Neuromodulation analog (RPE-driven) | T4 | VTA (neuromodulation) | 4 | Low | [CONJECTURE] | §12.1 |

**Matrix reading:** Phase 1 is deliberately cheap (two low-cost T1 anchors, two medium) — the brain's habit and belief layers upgrade first. Phase 2 adds the social brain (ToM) and belief verification. Phase 3 is where the expensive builds live (engine, workflow induction, emotion port). Phase 4 is pilots and watch-list promotions. Cost labels: Low = days, Medium = weeks, High = a focused month+.

---

## 5. Wiki-Backed Concepts Added in v2

Concept areas with heavy wiki coverage that v1 omitted. v2.0 added the ten the audit's Round 3 headlined; v2.1 completes the sweep so **every** Round-3 concept (34 total) has an explicit disposition. Each entry: what it is, what our wiki holds, how it enters the architecture (or why it stays background). These are not new external dependencies — they are internal knowledge that sharpens the components above.

**Disposition summary:** 12 architecture-entering areas (§5.1–5.12 below) · 4 already-implemented systems documented as infrastructure (§5.13) · 7 theory-backdrop areas with no component role (§5.14) · 11 broad-coverage areas that need no separate treatment because they are the substrate the categories already live on (§5.15).

### 5.1 Global Workspace Theory (117 files; dedicated Oracle directory)

- **What:** Baars 1988 / Shanahan 2006 — consciousness as a limited-capacity global workspace that specialist processes compete for via attention, with the winner broadcast to all. T1 theory.
- **Our wiki:** 117 files, including a dedicated Global-Workspace-Theory directory in the Oracle brain; the Attention-and-Consciousness-Debate file covers the ADS (attention vs consciousness) literature.
- **How it enters:** it is the theoretical foundation for LIMEN (§3.6.3) and the arbitration layer of the integrated router (§3.6.5). The ignition-threshold concept becomes the System 2 activation criterion: workspace competition that fails to ignite → stay on System 1.
- **Why it matters here:** without GWT, the routing category is just "a formula"; with it, the formula has a theoretical account of *why* competition and broadcast are the right shape.

### 5.2 ZenBrain (42 files)

- **What:** a neuroscience-inspired 7-layer memory architecture (per our wiki's ZenBrain entries, community project).
- **Our wiki:** 42 files across active wiki + oracle.
- **How it enters:** cross-reference layer for hippocampal indexing (§3.5) and procedural memory (§3.4) — ZenBrain's layer decomposition is a second opinion on how tiers should split. Not adopted as a dependency (no verified venue, no repo audit); used as a comparative reference when validating our tier boundaries.
- **Why it matters:** independent convergence on a layered memory design is weak but real evidence our tiering is reasonable.

### 5.3 BrainMem (170 files)

- **What:** episodic + working memory architecture for agents (per our wiki).
- **Our wiki:** 170 files — substantial internal analysis.
- **How it enters:** the working-memory modeling reference for the dlPFC slots (7 slots, decay 0.1/turn) and episodic buffer sizing. Cross-reference in §3.5 and the memory-tier design.

### 5.4 MRAgent: Active Reconstruction (15 files, incl. dedicated analysis `research/mragt-cue-tag-content-reconstruction.md`)

- **What:** read-time memory reconstruction from a cue-tag-content graph — instead of storing finished memories, store components and reconstruct at recall.
- **Our wiki:** dedicated research file.
- **How it enters:** Phase 4 experimental layer on top of HippoRAG (§3.5.1): if PPR retrieval returns fragments, MRAgent-style reconstruction assembles the answer from components. [CONJECTURE] — pilot required.

### 5.5 Complementary Learning Systems (173 files; McClelland/McNaughton/O'Reilly 1995, T1)

- **What:** the foundational theory that the hippocampus (fast, sparse, separable learning) and neocortex (slow, structured, overlapping learning) are complementary systems — hippocampal rapid encoding prevents interference while neocortex slowly integrates.
- **Our wiki:** 173 files.
- **How it turns:** it is the *theoretical justification* for the whole three-store split (working/episodic/semantic + nightly consolidation). The dreaming plugin IS the systems-consolidation process CLS describes; HiCL's DG-gated MoE is a CLS-compatible implementation; CogniFold's "extended CLS" is the same lineage. CLS is cited in every relevant dossier as the T1 backbone.

### 5.6 Sleep Cognition / Sleep-Dependent Consolidation (107 files; dedicated Oracle directory)

- **What:** sleep-dependent memory consolidation and insight generation (empirical sleep neuroscience, T1).
- **How it enters:** the dreaming plugin's 3-phase design (Light/REM/Deep) is grounded here, and the NREM/REM↔phase mapping gap (G19) is a research question this literature informs. The Sleep-Dependent-Insight-Generation file directly supports the REM-phase schema-induction design.

### 5.7 Emotion-Cognition (109 files; dedicated Oracle directory, T1 theory)

- **What:** Somatic Marker Hypothesis (Damasio), Appraisal Theory (Lazarus/Scherer), Emotion Regulation (Gross), Cognitive Reappraisal — the empirical emotion-cognition literature.
- **How it enters:** the T1 grounding for Category 7. swaylq's layers 2-4 are literally Lazarus/Scherer/Damasio; our limbic system already implements the Damasio half. This directory is the citation base for §3.7.

### 5.8 Predictive Processing / Active Inference (274 files; Friston lineage, T1 theory)

- **What:** cognition as prediction-error minimization (predictive coding, free energy principle, active inference).
- **How it enters:** theoretical backdrop, not a component. Two concrete uses: (a) the thalamic saliency gate is a crude prediction-error detector — entropy as surprise proxy; (b) long-term, the "minimize surprise" objective is the principled version of the curiosity drive in limbic. No implementation in this proposal [CONJECTURE-layer]; kept as orienting theory.

### 5.9 MemoBrain (arXiv:2601.08079, T2 preprint, no repo — build from paper)

- **What:** executive memory for tool-using agents: constructs dependency-aware memory over reasoning steps and prunes invalid trajectories.
- **How it enters:** build-from-paper spec for the action-gate's memory: when a tool sequence fails, MemoBrain-style dependency analysis tells us which steps remain valid (vs GraSP's local repair, which re-runs the failed subgraph — complementary: MemoBrain diagnoses, GraSP repairs). Phase 4.

### 5.10 SCRUBJAY-MEM (arXiv:2608.04746, T2 preprint, no repo — build from paper)

- **What:** episodic memory with **perishability coefficients** — each memory carries an auto-classified shelf-life (perishable vs durable), combining semantic content, task context, and timestamp.
- **How it enters:** the missing half of adaptive forgetting (wiki: 540 files on forgetting). Our consolidation currently has salience-based retention; perishability adds *time-structured* retention — "the user's printer IP" is durable, "the user is at the coffee shop" perishes. Phase 4: add a `perishability` column (additive) + nightly decay pass.

### 5.11 Interoception / Allostatic (51 files)

- **What:** visceral signaling, insular cortex, allostasis — the body-state side of emotion (T1 neuroscience).
- **How it enters:** our limbic system already has allostatic load as a state variable; this directory is its citation base and the source for future interoception-analog signals (e.g., "hunger" ≈ resource pressure on the inference stack).

### 5.12 Dopamine / Reward Prediction Error (333 files; Schultz lineage, T1)

- **What:** RPE, incentive salience (Berridge & Kringelbach), dopamine signaling in striatum.
- **How it enters:** the T1 grounding for Maxim's NAc reward learning (§3.7.4) and the reward-signal design question for HiCL consolidation (what signal marks a skill as worth keeping?). Also the neuromodulation gap (§12.1) — the honest answer is that no system implements dopamine analogs for LLM agents; the RPE literature is the theory to build from if we attempt it.

### 5.13 Already-Implemented Systems (documented, not proposed)

Four systems the audit flagged as "already implemented — should be documented." They are: this proposal documents them in §1 and they anchor the data-flow diagrams (§8). Listed here to close the audit's loop:

- **Decision Logger (63 files)** — plugin + nightly synthesis, §1.4. Its decisions table is the input MetaMind's ToM Agent reads (§3.3.1).
- **Dreaming Plugin (197 files)** — the 3-phase nightly consolidation, §8.3. It IS DCPM's System 2 and the CLS systems-consolidation analog; Phase 1 chains and Phase 1 HiCL both plug into it.
- **Graphify (637 files)** — the derived index, §1.6. Currently degraded (0-edge AST-only graphs — §10.2 Round 1); fixing its semantic pass is Phase 1 #4's prerequisite and benefits both wikis.
- **Brain Search (360 files)** — the retrieval path PPR merges into (§3.5.1) and ActMem widens (§3.2.3).

### 5.14 Theory-Backdrop Areas (no component role, deliberately)

Well-covered in the wiki, philosophically load-bearing, but deliberately **not** turned into components. Recorded so future reviewers know the omission is a decision, not an oversight:

- **Embodied Cognition (226 files)** — enactive/sensorimotor accounts challenge the pure-computational frame. Our agent has no body; the honest reading is that interoception-analogs (§5.11) are as close as this architecture gets. Revisit only if the brain grows sensors.
- **Attention/Consciousness debate (89 files)** — the ADS literature. §12.3 already states the position: GWT is an engineering heuristic here, no consciousness claims.
- **Ethics/Consciousness (74 files)** — moral patienthood debate. Out of scope for build decisions; the Moral Agent stage (§3.3.1) applies OUR behavioral contracts, not a theory of moral status.
- **Cognitive Development (164 files)** — schema theory and developmental trajectories. Backdrop for schema induction (dreaming REM phase), not a component.
- **Frame Problem (472 files)** — the classical KR problem. Relevant intellectually (belief revision and relevance-limiting are responses to it); our operational answer is thalamic gating + working-memory limits, already built.
- **Decision Making / heuristics & biases (377 files)** — human decision literature. The action gate and somatic markers already import its useful parts (risk-weighted Go/No-Go); the rest documents human failure modes we don't emulate deliberately.
- **Neuroplasticity / LTP (164 files)** — the biological mechanism of consolidation. Theory base for HiCL's EWC and the dreaming plugin's replay; no separate component.

### 5.15 Broad-Coverage Substrate Areas (covered by the categories themselves)

Eleven Round-3 areas whose coverage is the *substrate* the seven categories are built from — they need no separate treatment, and saying so is the disposition:

**Cognitive Architecture (490)** — the umbrella; §2 and the Oracle's Cognitive-Architecture directory (LIDA, DCPM, HTM files) are it. **Temporal Cognition (84)** — chronesthesia already lives in `brain/dmn/`; predictive timing is thalamic-gate theory. **Memory Write Admission (1,025)** — the write-gate layer: Gated-Memory Routing (§3.6.4) and TrustMem (§6.3) are its external anchors; the internal analyses (A-MAC, ConsistencyGate, SAGE, Nemori, MemRouter) informed their dossiers. **Memory MDP (168)** — adaptive access control; the contextual-bandit framing is the Phase-3+ upgrade path for the write gate. **Learning Science (1,138)** — spacing/retrieval-practice/desirable-difficulties; the consolidation schedule (nightly, not immediate) is already its application. **Memory Architecture (862)** and **Agent Memory (776)** — the general field; the three-tier design is our instance. **Knowledge Graph (1,035)** and **Ontology (596)** — Neo4j/Graphiti and the wiki's ontological work; HippoRAG (§3.5.1) consumes the former. **Belief Formation (98)** — Gärdenfors' *Knowledge in Flux* lineage, cited in §14 refs [2]. **Social Cognition (144)** — the ToM category's wider field.

---

## 6. Build-From-Paper Specifications

Where white-paper proof exists for a brain part but no public repo, the build spec lives here (per the directive: "describe how it would need to be built so we can consider building it as part of our system ourselves").

### 6.1 Counterfactual Engine (CRAFT + C3, on Pearl's T1 foundations)

**Target:** `brain/dmn/counterfactual_engine.py` extending the existing `counterfactual.py` and `counterfactual_rollouts` table.

**Design:**

1. **Context Snapshotter** — before each consequential action (action-gate "Go" decisions above a risk threshold), serialize: session context, working-memory slots, retrieved memories (IDs), pending plan, the action+args. Store as a JSON snapshot keyed by turn ID. Cost: one JSON dump; no LLM.
2. **Alternative Action Generator** — on failure (or high surprise in `record_action_outcome`), prompt the LLM: "given this snapshot, propose 2–3 alternative actions that differ from the taken one." One LLM call.
3. **Lightweight Executor** — run alternatives via llama.cpp at low temperature against the *frozen* snapshot (C3 mode: substitute only the action; CRAFT mode: full sibling rollout from the snapshot point). Budget-capped: max 2 alternatives, max 10 tool steps each.
4. **Outcome Comparator** — diff alternative vs actual outcomes along: task success (did the goal complete), token cost, side effects (files written, commands run), user-visible signal. Deterministic comparison where possible (success/fail, cost), LLM-judged where necessary (quality deltas) — LLM judgments logged as such.
5. **Delta Store** — extend `counterfactual_rollouts` (existing table): `mode` (C3/CRAFT), `snapshot_id`, `alternative_action`, `outcome_delta`, `attribution_confidence`. Additive columns only.
6. **Retrieval Integration** — at planning time, query recent counterfactual deltas for similar contexts: "last time in this situation, doing Y instead of X would have saved Z" enters the prompt.

**Gating (cost control):** counterfactual replay only fires when (a) the action failed, AND (b) surprise > threshold, AND (c) fewer than N replays this session. This addresses Gap G5 (computational cost) by construction.

**Attribution honesty (G6/G7):** multi-step attribution is unsolved in the literature; the engine logs `attribution_confidence` and never presents a delta as certain causation. Context drift (G7) is mitigated by the frozen snapshot but not eliminated — documented limitation.

### 6.2 CA3 Attractor Pattern Completion (Rolls-Treves, T1 math, no public code)

**Target:** `brain/hippocampus/ca3_attractor.py`.

**Design:** sparse recurrent autoassociative network per Rolls & Treves 1998 quantitative theory: fixed sparse weight matrix W over memory patterns stored by Hebbian outer-product learning; recall = iterated `a(t+1) f(W·a(t))` until fixpoint (attractor); cue = partial/degraded pattern; completion = convergence to the stored attractor. Implementation: NumPy, patterns = binarized memory fingerprints (e.g., SDR codes from §3.5.2 or hashed embeddings), capacity per the classic Hopfield/Rolls-Treves bound (~0.138·N for dense Hopfield; higher for sparse). **Pilot gate:** only worth building if PPR retrieval's incomplete-cue recall measurably underperforms on our data — otherwise the attractor layer is redundant complexity. [CONJECTURE] flagged.

### 6.3 TrustMem Transition Verifier (arXiv:2606.25161, T2 preprint, no repo)

**What the paper proves:** each memory *update* should be evaluated along coverage / preservation / faithfulness dimensions before commit; Transition-Ranked GRPO optimizes the verifier.

**Build spec (Phase 4):** a write-path gate for belief/memory updates: before a DCPM SUPERSEDE commits, score the transition (new belief vs old belief vs source evidence) on the three dimensions — implemented as a structured LLM judgment with a deterministic pre-check (lexical overlap, polarity guard), mirroring the TIMPS finding that lexical-first, embedding-last gating reaches 98.2% write-acceptance accuracy. Rejected transitions go to a review queue, not the trash (Oracle wiki rule 7: preserve, never silently delete).

---

## 7. Existing-to-Proposed Mapping

**Key insight:** the existing brain already implements simplified versions of all 7 proposed categories. The proposal enhances, not replaces.

| Proposed Category | Existing Subsystem | What Exists | What's Missing | Enhancement |
|-------------------|-------------------|-------------|----------------|-------------|
| **Belief Revision** | `brain/epistemology/` | AGM operators, Pollock defeaters, Hegelian dialectic | Supersedes chains (DCPM), downstream propagation (Atlas Ripple), iterated-revision checks (Kumiho) | Chains on `cognitive_beliefs` (additive); Atlas via MCP as verification/propagation layer; belief_set fallback |
| **Counterfactual Reasoning** | `brain/dmn/counterfactual.py` | Pearl regret analysis, rollouts table | Execution engine (CRAFT/C3), counterfactual query gen (ActMem) | §6.1 engine, gated by failure+surprise; ActMem in retrieval path |
| **Theory of Mind** | `brain/social/tom.py` | Recursive ToM L1/L2, false-belief checks | MetaMind pipeline, local ToM model (COLM), trajectory tracking | 3-stage prompt pipeline + COLM as tool; MindForge schema for records |
| **Procedural Memory** | `brain/basal_ganglia/compiler.py` | ACT-R acquisition, threshold-3 compilation | Safe consolidation (HiCL), tier boost (MEMTIER μ=1.4), workflow induction (AWM), repair (GraSP) | HiCL on GPU for neural consolidation; AWM mining of session JSONL; μ-boost in ranking |
| **Hippocampal Indexing** | `brain/hippocampus/` | HippoRAG-style PPR graph, DG/CA3, SWR replay | True multi-hop (HippoRAG proper), SDR separation (mokosh), HRR binding, CA3 attractor | Fix graphify semantic pass → PPR over Neo4j; SDR pilot; HRR pilot; attractor only if PPR underperforms |
| **Cognitive Routing** | `brain/cortex/router.py` | Single-threshold S1/S2, Miyake triad | Composite routing score (Sibelium CE), GWT arbitration (LIMEN), learned gates | CE formula in router.py now; LIMEN Phase 3; integrated-router design doc |
| **Valence/Emotion** | `brain/limbic/` | Valence/arousal/allostatic/curiosity, somatic markers | Appraisal layers (swaylq), stability guarantees (TOAQ), reward learning (Maxim) | Layered emotion system port; TOAQ dynamics; LIDA cycle-integration pattern |

**Already working (existing code):** thalamic saliency gating, working memory with decay, S1/S2 routing, somatic markers, AGM + defeater lattice, PPR associative graph, pattern separation/completion, counterfactual regret analysis, ToM user modeling, Gricean pragmatics, skill compilation, all 4 hooks, decision_logger + nightly synthesis, 10 profiles, 48 skills, 6-table schema.

**Needs enhancement:** listed per-category above; full phase plan in §9.

---

## 8. Full Data Flow

### 8.1 Per-Turn Flow (Synchronous)

```
User Input
    │
    ▼
HOOK: brain-cognitive-guard (agent:step)
  ├── ThalamicGate.evaluate_admission(text) — entropy → saliency → admit/reject
  ├── SomaticMarkerEngine.assess(action, target) — SQLite lookup → bias + warning
  ├── ActionGate.evaluate_pathways(...) — Go/No-Go (go_threshold=0.4)
  └── ExecutiveControl.check_inhibition(action) — destructive-command detection
    │
    ▼
BRAIN: process_incoming_stimulus(source, text, session_id)
  ├── 1. Thalamic buffer append + saliency check
  ├── 2. GriceanPragmatics.analyze_implicature(text)
  ├── 3. Somatic marker risk appraisal (action/target extraction)
  ├── 4. CognitiveRouter.evaluate_route(...) — S1 vs S2
  │       [v2: CE = 0.4·PromptLength + 0.4·CognitiveStress + 0.2·GraphComplexity
  │        as second opinion; disagreement → S2]
  ├── 5. dlPFC decay_all(0.1) + upsert latest_input
  ├── 6. TheoryOfMind.check_discrepancies()
  │       [v2 Phase 2: MetaMind ToM Agent stage consults user_mental_models
  │        + other instances' decision logs; COLM optional tool]
  └── 7. ActionGate preview (Go/No-Go)
    │
    ▼
AGENT LOOP: LLM inference + tool execution
  ├── S1: direct response (low complexity)
  └── S2: tool orchestration (high complexity)
        ├── Tool selection per router decision
        ├── Action-gate check before execution
        │       [v2: Context Snapshotter fires on high-risk Go decisions (§6.1)]
        └── Tool result → record_action_outcome
    │
    ▼
HOOK: brain-memory-consolidator (agent:end)
  ├── Feed user input → thalamus stimulus
  ├── Record tool outcomes → somatic markers + limbic valence
  ├── Consolidate high-surprise episodes → hippocampal replay
  └── Update working-memory snapshots
    │
    ▼
HOOK: to-do-capture (agent:end) — detect to-do requests → organizer.db
HOOK: hermes-visualizer-sync — broadcast state → 8790/8794
PLUGIN: decision_logger (agent:end) — scan response → decisions table
```

### 8.2 Post-Turn Feedback Flow (Asynchronous)

```
Tool Execution Result
    │
    ▼
BRAIN: record_action_outcome(action, target, success, surprise, steps)
  ├── 1. CognitiveValenceEngine.record_outcome — valence/arousal/allostatic/curiosity
  │       [v2 Phase 3: TOAQ control-theoretic update equations bound the dynamics]
  ├── 2. SomaticMarkerEngine.record_experience — SQLite upsert
  ├── 3. ExecutiveControl.evaluate_shifting — loop detection → failed_strategies
  ├── 4. HippocampalReplayEngine.record_episode — episodic trace → replay buffer
  └── 5. ProceduralSkillCompiler.observe_sequence — compile if threshold ≥ 3
        [v2 Phase 1: HiCL DG-gated MoE consolidation on GPU (nightly);
         threshold-3 symbolic compilation remains the fallback]
        [v2 Phase 3: on failure + high surprise → Counterfactual Engine (§6.1)]
```

### 8.3 Nightly Consolidation Flow (Cron-Triggered)

```
Nightly Cron (2:00 AM)
    │
    ▼
PLUGIN: decision_logger/synthesis.py — contradictions, stance drift,
│       entity promotion → synthesis report
    │
    ▼
DREAMING PLUGIN (3-phase consolidation — CLS systems-consolidation analog)
  ├── Light Sleep: fact triage → DBSCAN clustering
  ├── REM: schema induction → cross-domain collision sweep   [DCPM System 2]
  └── Deep Sleep: core schema promotion → procedural tier
        [v2: HiCL consolidation + AWM workflow mining from session JSONL;
         SCRUBJAY-style perishability decay pass (Phase 4)]
    │
    ▼
BRAIN: nightly consolidation
  ├── HippocampalReplayEngine: SWR replay of high-valence episodes
  ├── ProceduralSkillCompiler: compile skills from trajectories
  ├── AGMBeliefRevision: resolve belief conflicts
  │       [v2: Atlas Ripple propagation pass (Phase 2, via MCP)]
  └── CounterfactualEngine: regret analysis on failures
```

### 8.4 Multi-Agent Flow (5 Hermes Instances)

```
main (the operator)   coder          flowbot        oracle         researcher
   │             │               │              │               │
   └─────────────┴───────────────┴──────────────┴───────────────┘
                                │
                                ▼
                 Shared Infrastructure
                 ├── Postgres (brain DB, pgvector)
                 ├── Neo4j (knowledge graph)
                 ├── organizer.db (state)
                 ├── Active Wiki (cold memory)
                 └── Oracle Brain (reference)
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
        MetaMind ToM      DCPM Supersedes    Multi-Agent Conflict
        pipeline          chains             Resolution
        (Phase 2)         (Phase 1)          (open gap G2)
```

---

## 9. Implementation Priority Order (Evidence-Tier Driven)

Phasing rule: **tier and integration cost drive order, not wiki coverage** (directive 2026-09-23). Phase 1 = T1 anchors with cheap integration. Phase 2 = T1 anchors with moderate cost + cheap T3 wins. Phase 3 = T2 mechanisms needing builds. Phase 4 = experimental/watch/self-evolving.

### Phase 1: Foundation (T1 anchors, immediate value)

| # | Component | Tier | First deliverable |
|---|-----------|------|-------------------|
| 1 | DCPM supersedes chains | T1 mech / T2 paper | `superseded_by`/`superseded_at` columns + write/read path + lexical reversal guard |
| 2 | MEMTIER μ=1.4 procedural boost | T1-internal | Ranking change + A/B re-tune |
| 3 | HiCL consolidation | T1 (AAAI 2026) | DG-gated MoE on desktop GPU, fed by dreaming Deep Sleep output |
| 4 | HippoRAG multi-hop | T1 [VENUE-CONFIRMED] | Fix graphify semantic pass → PPR over Neo4j → RRF merge with pgvector |

### Phase 2: Enhancement (T1 anchors + cheap T3 wins)

| # | Component | Tier | First deliverable |
|---|-----------|------|-------------------|
| 5 | MetaMind ToM pipeline | T1 | 3-stage prompt pipeline in multi-agent contexts |
| 6 | COKE/COLM local ToM model | T1 | GGUF conversion + `tom_infer` tool + benchmark vs prompted |
| 7 | Atlas AGM + Ripple via MCP | T3 | MCP server beside Neo4j; re-run postulate suite ourselves; pilot on mirrored beliefs |
| 8 | belief_set fallback backend | T3 | `agm_backend.py` dual-driver interface |
| 9 | Sibelium CE routing formula | T3 | Composite score in router.py + routing-decision logging |
| 10 | ActMem counterfactual query gen | T2 | 2-3 reformulations pre-retrieval + RRF merge |

### Phase 3: Specialization (T2 mechanisms, real builds)

| # | Component | Tier | First deliverable |
|---|-----------|------|-------------------|
| 11 | Counterfactual engine (C3 first, CRAFT gated) | T2 → ours | §6.1 spec implemented behind failure+surprise gate |
| 12 | AWM workflow induction | T1 [VENUE-CONFIRMED] | Session-JSONL mining → workflow templates → retrieval |
| 13 | GraSP typed DAG + local repair | T2 | Type schema for our tools + repair on workflow failure |
| 14 | LIMEN GWT auction | T3 | Ignition-threshold arbitration over routing candidates |
| 15 | swaylq 7-layer emotion port | T3 | Layers 1-4 into brain/limbic/emotion_system.py |
| 16 | TOAQ VA dynamics | T2 | Control-theoretic update equations in valence engine |
| 17 | Gated-Memory Routing | T2 [VENUE-PARTIAL] | Learned write gates IF venue verifies (recheck Nov 2026) + training signal exists |
| 18 | Atlas↔Kumiho postulate suite | T2 | K*4/K*6 iterated-revision test cases |

### Phase 4: Research / Experimental (T4, preprint builds, watch list)

| # | Component | Tier | First deliverable |
|---|-----------|------|-------------------|
| 19 | mokosh SDR near-duplicate gate | T3 | FFI pilot on write path |
| 20 | HRR binding pilot | T3 on T1 theory | Unbind accuracy >80% gate on preference slot |
| 21 | CA3 attractor (Rolls-Treves) | T1 math / T4 build | Only if PPR incomplete-cue recall underperforms |
| 22 | MemoBrain dependency analysis | T2 | Build-from-paper diagnostic for failed trajectories |
| 23 | SCRUBJAY perishability | T2 | `perishability` column + nightly decay pass |
| 24 | TrustMem transition verifier | T2 | §6.3 write-gate with lexical-first checks |
| 25 | CogniFold always-on CLS | T2 | Watch; extended-CLS read-time reconstruction |
| 26 | MRAgent active reconstruction | internal | Pilot on PPR fragments |
| 27 | Maxim NAc reward signal | T3 | Reward design for HiCL retention decisions |
| 28 | pyClarion contagion | T3 | Multi-agent affect propagation pilot |
| 29 | SkillDAG self-evolving graph | T2 | After DCPM schema induction stabilizes |
| 30 | IJCAI-2025 deterministic revision | T1 [VENUE-CONFIRMED] | Revision-operator evaluation; G2 merge NOT covered (reopened) |
| 31 | epica / omega-hippocampus / snath-ai/DMN / CogFlow / MemCog | watch | Quarterly re-review |
| 32 | Steal-from-epica: BLAKE3 change-log hash chain | T3 idea | Hash-chain the cognitive_beliefs change log (pure Python) |

### Explicitly out (corrected in earlier rounds; see §0.5)

- **DSPy** — prompt/pipeline optimization only; never procedural memory (corrections #10).
- **DoWhy** — data-science causal inference, not agent cognition (#9).
- **jina-embeddings** — general embeddings, not emotion computation (#8).
- **NexusCortex** — Go; port cost exceeds swaylq's (Python) for the same capability.
- **Depth psychology (Jung/Freud/Bernays)** — human psychology, not computational emotion.

---

## 10. Records & Audit Trail

This section is the "full documentation of all rationale, all records, all research" the directive demanded. Everything here is verifiable from the referenced files and sessions.

### 10.1 Directive Record

The v2 rewrite was triggered by the operator's directive, received 2026-09-23 ~11:57 AM PDT in session `20260923_080823_fe0fcf3b` (the message that ended that session — the previous model instance died before acting on it; work resumed in a fresh session the same day). Verbatim:

> "Low wiki coverage does not mean that it's not a strum idea. It just means that we have limited information on it. I want you to update the backgrounds of each of these things with the relevant information from your research er regarding how the program works, how the research works, where they're different, whether they're the same and any other details that are necessary so that this file with the proposal has backing and references and benefits and negatives and everything well thought through so that we have a complete view of how everything works together. What's research backed? What's community backed? What is backed by papers but not by peer review and what is theoretical or conjecture but probably worth adding as part of all of this and how every single thing would be done so that we've got an exact mockup of how all of this should work together and why you're not using the other options in each space along with why you chose what you did for each individual thing all in that file. So we have full documentation of all rationale all records, all research etc. And really have an amazing background theoretical outline as well as nuanced infrastructure build out instruction set inside the file"

("strum" read as "strong" — speech-to-text artifact.)

### 10.2 Wiki Coverage Audit — Full Tables (2026-09-23)

**Graphify audit (superseded 2026-09-25).** *This section previously reported per-concept
node counts read from a local install, alongside a "0 edges" finding. Both were removed: the
counts are personal derived data with no place in a shared repository, and the "0 edges"
reading was wrong — graphify stores relationships under a `links` key that the audit did not
check, so it reported zero for graphs that in fact carried tens of thousands of relationships.
Nothing about a given installation's graph contents is asserted here. For what the repository's
graph layer does and does not do, see §0.7; for a reusable health check, see
`scripts/graphify_health.py`.*

**Round 2 — ripgrep file counts (full table, audit's own order).** Active wiki + Oracle brain:

| Concept | Active | Oracle | Total | Read |
|---------|--------|--------|-------|------|
| Belief Revision / AGM | 37 | 74 | 111 | Moderate |
| Counterfactual Reasoning | 130 | 542 | 672 | Strong |
| Theory of Mind | 281 | 1,277 | 1,558 | Very strong |
| Procedural Memory | 99 | 247 | 346 | Strong |
| Hippocampal Indexing | 43 | 249 | 292 | Moderate |
| Cognitive Routing | 85 | 273 | 358 | Strong |
| Valence / Emotion | 374 | 1,164 | 1,538 | Very strong |
| DCPM | 74 | 128 | 202 | Strong (331-line analysis) |
| HippoRAG | 16 | 27 | 43 | Thin |
| MetaMind | 1 | 5 | 6 | **INFO-LIMITED** |
| Sibelium | 0 | 13 | 13 | **INFO-LIMITED** |
| GraSP | 18 | 73 | 91 | Thin |
| AWM | 11 | 28 | 39 | Thin |
| LIDA | 355 | 914 | 1,269 | **Misleading** — mostly "licensing" false positives |
| Basal Ganglia | 6 | 105 | 111 | Moderate (oracle-heavy) |
| Thalamus | 6 | 74 | 80 | Moderate (oracle-heavy) |
| Working Memory | 96 | 447 | 543 | Strong |
| Defeasible Reasoning | 1 | 5 | 6 | **INFO-LIMITED** |
| Emotion/Appraisal | 0 | 92 | 92 | Oracle-only |
| Chronesthesia | 16 | 59 | 75 | Moderate |
| Somatic Marker | 2 | 111 | 113 | Oracle-heavy |
| Epistemology | 228 | 896 | 1,124 | Very strong |
| Social Cognition | 38 | 200 | 238 | Strong |
| Memory Tier / MEMTIER | 79 | 119 | 198 | Strong (446-line analysis) |
| Skill Compilation | 105 | 318 | 423 | Strong |
| Memory Provenance | 168 | 633 | 801 | Strong |
| Multi-Agent Memory | 90 | 209 | 299 | Strong |
| Adaptive Forgetting | 153 | 387 | 540 | Strong |
| Retrieval Failure | 83 | 160 | 243 | Strong |
| Metacognition | 52 | 145 |  197 | Strong |
| ZenBrain | 17 | 25 | 42 | Moderate |
| BrainMem | 55 | 115 | 170 | Moderate-strong |
| MRAgent | 5 | 10 | 15 | Dedicated analysis exists |
| Complementary Learning Systems | 47 | 126 | 173 | Strong |
| Global Workspace Theory | 9 | 108 | 117 | Oracle directory |
| Sleep Cognition | 16 | 91 | 107 | Oracle directory |
| Emotion-Cognition | 6 | 103 | 109 | Oracle directory |
| Hierarchical Temporal Memory (HTM/Numenta) | 140 | 491 | 631 | Very strong |
| Predictive Processing | 21 | 253 | 274 | Strong |
| Embodied Cognition | 29 | 197 | 226 | Strong |
| Neuroplasticity | 7 | 157 | 164 | Oracle-heavy |
| Dopamine/Reward (RPE) | 39 | 294 | 333 | Strong |
| Attention/Consciousness | 1 | 88 | 89 | Oracle-heavy |
| Interoception | 2 | 49 | 51 | Oracle-heavy |
| Temporal Cognition | 6 | 78 | 84 | Moderate |
| Memory Write Admission | 177 | 848 | 1,025 | Very strong |
| Memory MDP | 57 | 111 | 168 | Moderate |
| Gated Memory Routing | 2 | 4 | 6 | **INFO-LIMITED** |
| Decision Logger | 25 | 38 | 63 | Implemented system |
| Dreaming Plugin | 58 | 139 | 197 | Implemented system |
| Graphify | 212 | 425 | 637 | Implemented system |
| Brain Search | 76 | 284 | 360 | Implemented system |
| Memory Architecture | 236 | 626 | 862 | Broad substrate |
| Agent Memory | 224 | 552 | 776 | Broad substrate |
| Knowledge Graph | 268 | 767 | 1,035 | Broad substrate |
| Ontology | 206 | 390 | 596 | Broad substrate |
| Belief Formation | 11 | 87 | 98 | Moderate |
| Frame Problem | 120 | 352 | 472 | Theory backdrop |
| Ethics/Consciousness | 1 | 73 | 74 | Theory backdrop |
| Cognitive Development | 13 | 151 | 164 | Theory backdrop |
| Social Cognition (broad) | 8 | 136 | 144 | Theory backdrop |
| Decision Making | 54 | 323 | 377 | Theory backdrop |
| Learning | 229 | 909 | 1,138 | Broad substrate |
| Cognitive Architecture | 101 | 389 | 490 | Umbrella |
| Neural Basis | 16 | 237 | 253 | Theory backdrop |

*(Counts are the audit's measurements, 2026-09-23; wiki contents shift with every sync.)*

**Round 3 — missing-concept sweep (full disposition).** Every concept the audit found well-covered but absent from the v1 proposal, with its disposition in v2/v2.1:

| Concept | Files | Disposition |
|---------|-------|-------------|
| Global Workspace Theory | 117 | **Added** — §5.1, grounds LIMEN (§3.6.3) |
| HTM / Numenta | 631 | **Added** — §3.5.2 (mokosh context) + HTM theory as DG-separation backdrop |
| ZenBrain | 42 | **Added** — §5.2, tier-boundary comparative reference |
| BrainMem | 170 | **Added** — §5.3, working-memory modeling reference |
| MRAgent | 15 | **Added** — §5.4, Phase 4 read-time reconstruction pilot |
| Complementary Learning Systems | 173 | **Added** — §5.5, T1 backbone of the whole memory design |
| Sleep Cognition | 107 | **Added** — §5.6, grounds dreaming plugin phases |
| Emotion-Cognition | 109 | **Added** — §5.7, T1 base for Category 7 |
| Predictive Processing | 274 | **Added** — §5.8, orienting theory (no component) |
| Interoception | 51 | **Added** — §5.11, allostatic citation base |
| Decision Logger | 63 | **Documented** — §5.13, already implemented (§1.4) |
| Dreaming Plugin | 197 | **Documented** — §5.13, already implemented (§8.3) |
| Graphify | 637 | **Documented** — §5.13, already implemented; semantic-pass fix is Phase 1 #4 prerequisite |
| Brain Search | 360 | **Documented** — §5.13, already implemented (retrieval path) |
| Cognitive Architecture | 490 | **Substrate** — §5.15, the umbrella |
| Temporal Cognition | 84 | **Substrate** — §5.15, chronesthesia already in DMN |
| Memory Write Admission | 1,025 | **Substrate** — §5.15, write-gate layer (Gated-Memory Routing + TrustMem anchors) |
| Memory MDP | 168 | **Substrate** — §5.15, contextual-bandit upgrade path |
| Learning Science | 1,138 | **Substrate** — §5.15, consolidation schedule is its application |
| Memory Architecture | 862 | **Substrate** — §5.15 |
| Agent Memory | 776 | **Substrate** — §5.15 |
| Knowledge Graph | 1,035 | **Substrate** — §5.15, HippoRAG consumes |
| Ontology | 596 | **Substrate** — §5.15 |
| Belief Formation | 98 | **Substrate** — §5.15, Gärdenfors lineage (§14 ref [2]) |
| Frame Problem | 472 | **Backdrop** — §5.14, operational answer already built (gating + WM limits) |
| Embodied Cognition | 226 | **Backdrop** — §5.14, no body; interoception-analogs are the limit |
| Neuroplasticity | 164 | **Backdrop** — §5.14, theory base for HiCL EWC + replay |
| Dopamine/Reward | 333 | **Added** — §5.12, RPE grounding for reward signal (G29) |
| Attention/Consciousness | 89 | **Backdrop** — §5.14, ADS debate; no consciousness claims |
| Interoception | 51 | *(dup row in source audit; see above)* |
| Neural Basis | 253 | **Backdrop** — §5.14 |
| Cognitive Development | 164 | **Backdrop** — §5.14, schema-induction backdrop |
| Social Cognition (broad) | 144 | **Backdrop** — §5.14 |
| Decision Making | 377 | **Backdrop** — §5.14, useful parts already in action gate |
| Ethics/Consciousness | 74 | **Backdrop** — §5.14, out of build scope |

### 10.2.1 Audit-Recommendations Disposition Record

The audit's RECOMMENDATIONS section proposed demoting/removing several components based on wiki coverage. The 2026-09-23 directive ("low wiki coverage does not mean it's not a strong idea") overrode the demotions. Full record so future reviewers can re-litigate with context:

| Audit recommendation | Disposition | Reasoning |
|---------------------|-------------|-----------|
| Downgrade MetaMind Phase 2 → 4 | **Overridden — stays Phase 2** | Coverage measures our analysis depth, not component quality. MetaMind is one of only 3 verified-T1 projects (NeurIPS 2025 spotlight confirmed); integration is prompt-level (cheap). Demoting a verified anchor because our wiki is thin inverts the evidence hierarchy. |
| Downgrade Sibelium Phase 2 → 4 | **Partially adopted — stays Phase 2 but T3-labeled** | Audit's core finding stands: the CE formula is Sibelium's own unvalidated tuning, and the "ICLR 2026 Workshop" venue was unconfirmed. But the formula port is a one-day change to the weakest part of the current brain (single-threshold routing), with outcome logging that lets us refit weights empirically. Cheap, reversible, explicitly T3. |
| Downgrade GraSP Phase 3 → 4 | **Overridden — stays Phase 3** | GraSP's local-repair mechanism (re-run only the failed subgraph) is the specific thing AWM lacks; it's the repair layer for AWM-induced workflows. Phase 3 placement follows tier+cost (T2, medium build), not coverage. |
| Downgrade AWM Phase 3 → 4 | **Overridden — stays Phase 3** | arXiv ID solid (2409.07429), mechanism (trajectory → workflow induction) is the base of the procedural family. ICML 2025 venue CONFIRMED 2026-09-24 (PMLR v267). |
| Remove LIDA from proposal | **Overridden — stays, rescoped** | The audit was right that wiki "coverage" was false positives — so the dossier was rewritten to lean on the primary source (IEEE TAMD 2013, T1) instead of wiki counts, marked [INFO-LIMITED], and rescoped to pattern-adoption only (adopt the affect-cycle wiring pattern, not the code). It stays because it's the only T1-grounded full cognitive cycle with integrated affect. |
| Remove swaylq / TOAQ / pyClarion | **Overridden — stay, T3/T2-labeled** | swaylq stays Phase 3 as the most complete runnable emotion reference (port layers 1–4, own persistence). TOAQ stays Phase 3 — only mechanism with VA stability guarantees (G28). pyClarion stays Phase 4 pilot-only. All carry [INFO-LIMITED]. The directive's logic: limited information ≠ weak idea; the tier system already encodes the caution. |
| Emphasize DCPM + MEMTIER as Phase 1 anchors | **Adopted** | Both are Phase 1 #1 and #2. |
| Add the 10 missing concepts | **Adopted** | All 10 in §5.1–5.12 (plus Dopamine/Reward at §5.12); v2.1 extended to all 34 Round-3 concepts. |

**The principle this record encodes:** wiki coverage drives *where analysis effort goes next* (thin coverage → dispatch research), not *what gets built*. Build order comes from tier + integration cost (§9). The one place the audit's caution materially changed the build: Sibelium's venue claim was stripped and the component is explicitly T3 with a refit plan.

### 10.3 Verification Session Record

- **Session:** `@session:default/20260923_080823_fe0fcf3b` ("Verify research-backed Hermes-compatible cognitive tools", started 2026-09-23 08:08 AM, model meituan/longcat-2.0:free via openrouter, source telegram).
- **Delegation:** one researcher subagent, dispatched 08:13:19, completed 08:15:41 (161.73s), 18 projects verified.
- **Key outputs:** (1) venue verification table (§0.2); (2) corrections list (§0.5); (3) three-round wiki audit (§10.2); (4) the audit's bottom line: only 3 of 18 projects carry verified peer review.
- **Re-dispatch note:** the categorized-recommendations pass that followed (HiCL as standout, epica watch-list, etc.) is preserved in §3.4.1, §3.1.6, and the §4 cross-reference table.

### 10.4 Agenda Cross-Reference & the Two-Copies Discrepancy

The 40 brain-architecture agenda items (5 belief revision, 4 counterfactual, 6+1 ToM, 6+1 emotion, 4 routing, 4 procedural, 4+1 hippocampal — the +1s are the wiki-entry synthesis items) live in the **Oracle brain copy** of the agenda:

- `~/.hermes/oracle/brain/research/BUILD-PLAN-AGENDA.md` — contains all 40 items under "NEXT — Brain Architecture Directions" with 7 subsections.
- `~/.hermes/active-wiki/research/BUILD-PLAN-AGENDA.md` — does **not** contain them (its "NEXT" section has the older 6 Band-1 items only).

This is a sync discrepancy between the two wiki copies, flagged here so it gets fixed on the next wiki sync (the active wiki is the operational one; the oracle copy holds the newer section). The proposal cites items by their oracle-copy IDs (e.g., `atlas-agi-belief-revision-with-ripple-propagation`).

**[RESOLVED 2026-09-24]** During the venue-verification pass, the nightly `rebuild_oracle_index.py` cron (a one-way mtime mirror active-wiki → oracle-brain, 03:30 daily) clobbered the oracle agenda's 40-item section with the active copy's older content (the copies had forked in both directions: oracle held the 40-item Brain Architecture section; active held newer reconsolidation work). Both sides were merged — active's reconsolidation updates + oracle's 40-item section + the 2026-09-24 venue annotations — and the merged file was written byte-identically to both copies, making subsequent mirror runs no-ops. Standing hazard remains: any future oracle-only edit to a file that also exists in active-wiki with a newer mtime will be clobbered by the 03:30 mirror; the mirror has no conflict detection (no manifest, no quarantine). Recommended fix (not yet applied): manifest-based conflict guard — skip and log when the destination changed since the mirror's last write.

**Item → dossier mapping:** every one of the 40 items is covered by a §3.x.y dossier or a §5/§6 entry; the §4 table lists them all. Three items from the v1 proposal's source list were dropped after verification: DoWhy (category error), jina-embeddings (category error), DSPy-as-procedural-memory (category error) — corrections log #8–#10.

### 10.5 Change History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-09-23T09:55Z (commit eeee1ee) | Initial 7-category proposal, 31 components, certainty labels |
| v1.1 | 2026-09-23T10:49Z (commit 54a4229) | Added infrastructure documentation, hooks/plugins/profiles/skills/config, data flow |
| v2.0 | 2026-09-23T22:00Z | Full-evidence rewrite: tiers, per-component dossiers, verification record, wiki audit, 10 added concepts, build specs, revised phasing, records section |
| **v2.1** | **2026-09-23** | **Neuroanatomical map (§2.5), master component matrix (§4.1), review guide (§0.6), §5 expanded to all 34 Round-3 concepts with dispositions, full Round-2/3 audit tables preserved verbatim (§10.2), audit-recommendations disposition record (§10.2.1)** |
| **v2.2** | **2026-09-24 (this)** | **Venue re-verification pass executed: 4 flags CONFIRMED (HippoRAG, AWM, IJCAI-2025, ToMAgent — all to T1), 1 PARTIAL (Gated-Memory Routing), 2 preprint-only confirmed (MEMTIER demoted T1→T2, DCPM stays T2). Corrections #13 (IJCAI merge claim retracted, G2 reopened) and #14 (MEMTIER tier). Evidence: research/venue-verification-brain-architecture-2026-09-24.md** |

---

## 11. Complete Gap List (After Full Implementation)

Gaps are numbered as in v1 (G1–G32) and remain accurate; v2 adds evidence context and, where relevant, the component that partially addresses each.

### Belief Revision
1. **AGM Recovery Postulate (K*4)** — no candidate system implements contract-then-re-expand recovery; Kumiho's proofs are the standard; Atlas re-run is the test (§3.1.2/§3.1.3).
2. **Multi-Agent Belief Merging** — 5 instances revising shared beliefs. [REOPENED 2026-09-24: the IJCAI-2025 paper was confirmed to have NO merge operator (revision only — corrections log #13), so this gap again has no formal candidate. Nearest practical mechanisms: MELD 5-outcome merge + StateFuse CRDT (multi-agent-memory-conflict-resolution). Agenda item: formal-belief-merge-operators-multi-agent-g2-reopened.]
3. **Temporal Belief Validity** — time-windowed beliefs; DCPM chains give ordering, not windows; TSM-style durative intervals are the research direction.
4. **Belief Provenance** — lineage across wiki → Oracle → agent loop; epica's Merkle pattern (adopted as pure-Python hash chain, Phase 4 #32) partially addresses.

### Counterfactual Reasoning
5. **Computational Cost** — extra LLM calls per decision; addressed by construction (failure+surprise gating, §6.1).
6. **Multi-Step Attribution** — credit across 10+ tool calls; unsolved in literature; engine logs attribution_confidence honestly.
7. **Context Drift** — frozen snapshots mitigate, not eliminate.
8. **Delta Storage at Scale** — pruning policy for counterfactual deltas over time.

### Theory of Mind
9. **ToM Scaling Beyond 3 Agents** — combinatorial with 5 instances; MetaMind evaluated ≤3.
10. **ToM for Tool-Use Coordination** — no paper addresses it; MetaMind is conversation-scoped.
11. **False-Belief Detection** — stale beliefs about other agents; Dynamic ToM trajectories (§3.3.5) partially address.
12. **ToM Fine-Tuning Infrastructure** — fine-tuning COLM on our interaction data needs GPU pipeline.

### Procedural Memory
13. **Skill Conflict Resolution** — multiple matching skills; GraSP typing is the nearest mechanism.
14. **Procedural Skill Forgetting** — obsolete skills (deprecated tools); SCRUBJAY perishability (§5.10) is the direction.
15. **Cross-Agent Skill Transfer** — coder → oracle propagation; no published solution.
16. **Skill Versioning and Rollback** — version management for compiled skills.

### Hippocampal Indexing
17. **CA3 Attractor Dynamics** — build from Rolls-Treves (§6.2); no public code.
18. **DG Pattern Separation Metrics** — how much separation is right; mokosh pilot must define the metric first.
19. **NREM/REM Consolidation Mapping** — dreaming plugin phases ↔ hippocampal replay; sleep-cognition literature (§5.6) informs.
20. **Hippocampal-Cortical Transfer** — transfer dynamics between indexing layers; CLS theory (§5.5) is the frame.

### Cognitive Routing
21. **Routing Latency Budget** — sequential routing decisions before action; CE formula is O(1), LIMEN auction is not.
22. **Routing Conflict Arbitration** — Sibelium vs LIMEN disagreement; integrated-router design doc (§3.6.5) owns this.
23. **Dynamic Model Routing** — task-based LLM selection (currently static config).
24. **Routing Policy Learning** — adaptive routing from outcomes; CE weight refit after 1,000 turns is the first step (§3.6.2).

### Valence/Emotion
25. **Emotion-Cognition Integration** — how affects modulate retrieval; LIDA cycle pattern (§3.7.1) is the template, but no paper validates it for LLM agents.
26. **Emotion Calibration** — no ground truth for agent emotions.
27. **Multi-Agent Emotion Contagion** — pyClarion pilot (Phase 4 #28) must prove value or stays off.
28. **Long-Term Emotional Stability** — TOAQ stability guarantees (§3.7.3) address directly.

### Cross-Cutting
29. **Neuromodulation Analogs** — dopamine/serotonin for exploration/learning-rate modulation; no system implements this for LLM agents; RPE literature (§5.12) is the theory base. [CONJECTURE-tier]
30. **Consciousness / Global Workspace Ignition** — LIMEN as engineering heuristic only; no scientific claim.
31. **Consolidation-Phase Separation** — NREM/REM mapping to agent loop; sleep-cognition literature informs.
32. **Computational Cost of Full Architecture** — 7 categories × multiple systems on one llama.cpp box; Phase gating is the mitigation.

---

## 12. Categories With No Adequate Solution

### 12.1 Neuromodulation (Dopamine/Serotonin Analogs)
No open-source system implements neuromodulatory control for LLM agents. Best guess (EXPERIMENTAL, [CONJECTURE]): a scalar reward signal from task success/failure modulating (a) exploration (sampling temperature) and (b) learning rate (consolidation frequency). The T1 theory base is RPE/incentive salience (§5.12); Maxim is the nearest T3 code. Worth prototyping because it's cheap and falsifiable; not worth citing as grounded.

### 12.2 NREM/REM Consolidation Phase Separation
The dreaming plugin's 3 phases are an engineering design informed by sleep neuroscience (§5.6), not a validated mapping. SCM (arXiv:2604.20943) describes phase separation but ships no code. Keep the phases; treat the mapping as [CONJECTURE].

### 12.3 Consciousness / Global Workspace Ignition
LIMEN implements GWT's attention auction, but whether workspace ignition is anything more than a useful arbitration metaphor is contested (our own Attention-and-Consciousness-Debate wiki file). Use as engineering heuristic; make no consciousness claims.

---

## 13. File Locations & Cross-References

### Primary Files (This Repo, `~/hermes-brain`)

| File | Purpose |
|------|---------|
| **This file** | Consolidated architecture proposal with evidence tiers |
| `brain/hermes_brain.py` | Master controller — 8 subsystems |
| `brain/schema/brain_cortex.sql` | 6-table cognitive schema |
| `config.yaml` / `docs/paths.yaml` | Agent + Hermes Brain paths |
| `cron/jobs.template.json` | 3 cron jobs |
| `hooks/` (4) | brain-cognitive-guard, brain-memory-consolidator, to-do-capture, hermes-visualizer-sync |
| `plugins/decision_logger/` | decision_logger + nightly synthesis |
| `profiles/` (10), `skills/` (48) | Context isolation + skills |
| `plugins/adapters/` | visualizer.py, barehands.py |

### Research Files (Active Wiki, `~/.hermes/active-wiki/research/`)

| File | Purpose |
|------|---------|
| `BUILD-PLAN-AGENDA.md` | Master agenda (see §10.4 two-copies note) |
| `dcpm-dual-process-belief-trajectory-tracking.md` | 331-line DCPM analysis |
| `memory-tier-integration-followup.md` | 446-line MEMTIER analysis |
| `procedural-tier-integration-cyclic-fps.md` | 546-line procedural tier analysis |
| `memory-write-admission-and-retrieval-recovery.md` | Write-admission pipeline design |
| `neo4j-graph-database-agent-memory.md` | Graph memory design |
| `mragt-cue-tag-content-reconstruction.md` | MRAgent analysis |

### Oracle Brain (`~/.hermes/oracle/brain/`)

| Path | Purpose |
|------|---------|
| `research/BUILD-PLAN-AGENDA.md` | Holds the 40 brain-architecture items (§10.4) |
| `research/PROPOSED-BRAIN-ARCHITECTURE.md` | Older snapshot of this proposal (36KB, 2026-09-23 09:40) — to be refreshed from this file |
| `Emotion-Cognition/` | 109 files: Somatic Marker, Appraisal, Emotion Regulation |
| `Global-Workspace-Theory/` | GWT directory (§5.1) |
| `Sleep-and-Cognition/` | Sleep-dependent consolidation (§5.6) |
| `Cognitive-Architecture/` | LIDA/DCPM/HTM theory files |
| `Temporal-Cognition/` | Chronesthesia, predictive timing |

### Session Records

| Record | Purpose |
|--------|---------|
| `@session:default/20260923_080823_fe0fcf3b` | Verification + wiki-audit session (all of §0.2/§0.3/§10.2's data) |

---

## 14. References

Evidence anchors cited in this document, grouped by tier. Where our audit verified a venue, it says VERIFIED; otherwise the venue is carried from the paper/wiki and flagged.

### T1 — Peer-Reviewed / Foundational

1. Alchourrón, Gärdenfors & Makinson (1985). "On the Logic of Theory Change." J. Symbolic Logic — the AGM framework. [MODEL-KNOWLEDGE]
2. Gärdenfors (1988). *Knowledge in Flux.* MIT Press — belief revision foundations. [MODEL-KNOWLEDGE; wiki: Belief Formation, 98 files]
3. Pollock (1987–1995). Defeasible reasoning papers — rebutting/undercutting defeaters. [MODEL-KNOWLEDGE]
4. Pearl (2009). *Causality* (2nd ed.) — causal hierarchy, counterfactuals. [MODEL-KNOWLEDGE]
5. Tulving (1985, 2002). Chronesthesia / mental time travel. [MODEL-KNOWLEDGE; wiki: Temporal-Cognition, 84 files]
6. Baars (1988). *A Cognitive Theory of Consciousness* — Global Workspace Theory. [MODEL-KNOWLEDGE; wiki: GWT directory]
7. Shanahan & Baars (2005). "Applying Global Workspace Theory to the Frame Problem." Minds & Machines. [MODEL-KNOWLEDGE]
8. Damasio (1994/1996). Somatic marker hypothesis. [MODEL-KNOWLEDGE; wiki: Emotion-Cognition]
9. Lazarus (1991); Scherer (2001). Appraisal theories of emotion. [MODEL-KNOWLEDGE; wiki: Emotion-Cognition]
10. Rolls & Treves (1998). *Neural Networks and Brain Function.* Cambridge — CA3 attractor quantitative theory. [MODEL-KNOWLEDGE]
11. Miyake et al. (2000). Executive functions (inhibition/updating/shifting). [MODEL-KNOWLEDGE]
12. Plate (2003). Holographic Reduced Representations. CSLI. [MODEL-KNOWLEDGE]
13. McClelland, McNaughton & O'Reilly (1995). Complementary Learning Systems. Psych Review. [MODEL-KNOWLEDGE; wiki: CLS, 173 files]
14. Grice (1975). "Logic and Conversation." — pragmatics. [MODEL-KNOWLEDGE]
15. Anderson (1993/2007). ACT-R — skill acquisition. [MODEL-KNOWLEDGE]
16. Ahmad & Hawkins (2015). HTM/SDR theory. [MODEL-KNOWLEDGE; wiki: HTM, 631 files]
17. Wimmer & Perner (1983); Apperly (2012); Rabinowitz et al. (2018). ToM literature. [MODEL-KNOWLEDGE; wiki: ToM, 1,558 files]
18. Franklin et al. (2013). LIDA. IEEE TAMD. [MODEL-KNOWLEDGE]
19. COKE: "COKE: Cognitive Chain of Theory-of-Mind" — ACL 2024 long paper. [VERIFIED-2026-09-23]
20. HiCL: hippocampal-inspired continual learning — AAAI 2026. [VERIFIED-2026-09-23]
21. MetaMind: three-agent ToM pipeline — NeurIPS 2025 spotlight, arXiv:2505.18943. [VERIFIED-2026-09-23]
22. HippoRAG: arXiv:2405.14831, NeurIPS 2024. [VENUE-CONFIRMED-2026-09-24: proceedings.neurips.cc hash 6ddc001d, Main Conference Track; DBLP conf/nips/GutierrezS0Y024]
23. AWM: arXiv:2409.07429, ICML 2025. [VENUE-CONFIRMED-2026-09-24: PMLR v267 pp. 63897-63911; DBLP conf/icml/WangMFN25]
24. MEMTIER: "Tiered Memory Architecture and Retrieval Bottleneck Analysis for Long-Running Autonomous AI Agents," Sidik & Rokach, arXiv:2605.03675. [Preprint-only confirmed 2026-09-24: comments field "Under review"; DBLP CoRR only. Internal analysis remains thorough.]
25. Schlegel et al. (2022). HRR comparison of vector symbolic architectures. [MODEL-KNOWLEDGE]

### T2 — Preprints

26. DCPM: "Memory Beyond Recall," Fei, Song, Zheng, Yu, arXiv:2606.09483. [Preprint-only confirmed 2026-09-24: no acceptance claim anywhere; DBLP CoRR informal only. Wiki analysis 331 lines.]
27. Kumiho: formal AGM K*2–K*6 on property graphs, arXiv:2603.17244.
28. Meng, Long, Sioutis, Zhou. "On Definite Iterated Belief Revision with Belief Algebras." IJCAI 2025, paper 511, DOI 10.24963/ijcai.2025/511; extended version arXiv:2505.06505. [VENUE-CONFIRMED-2026-09-24; scope: iterated revision only, no merge]
29. CRAFT: counterfactual credit assignment, arXiv:2606.29476.
30. C3: frozen-context counterfactual credit, arXiv:2603.06859.
31. ActMem: counterfactual question generation, arXiv:2603.00026.
32. ToMAgent: "Infusing Theory of Mind into Socially Intelligent LLM Agents," Hwang, Yin, Carenini, West, Shwartz — arXiv:2509.22887, Findings of ACL 2026 pp. 11327-11360. [VENUE-CONFIRMED-2026-09-24: aclanthology.org/2026.findings-acl.551]
33. MindForge: arXiv:2411.12977.
34. Dynamic ToM: arXiv:2603.14646.
35. GraSP: arXiv:2604.17870.
36. SkillTrace: arXiv:2608.02356.
37. SkillDAG: arXiv:2606.03056.
38. Gated-Memory Routing: "Learning What to Retain," Rajib, Zheng, Lou — arXiv:2609.00237, EMNLP 2026 Main. [VENUE-PARTIAL-2026-09-24: author-claimed via arXiv comments only; conference Oct 24-29 2026; note 2026.emnlp.org accepted-papers page is stale (serves 2025 content) — verify via ACL Anthology post-conference]
39. TOAQ (Bruneteau 2025): control-theoretic VA dynamics.
40. MemoBrain: arXiv:2601.08079.
41. CogniFold: arXiv:2605.13438.
42. MemCog: arXiv:2605.28046.
43. TrustMem: arXiv:2606.25161.
44. SCRUBJAY-MEM: arXiv:2608.04746.
45. CogFlow: arXiv:2509.22546 (under review).
46. LongMemEval: arXiv:2410.10813, ICLR 2025 — benchmark for knowledge-update/temporal queries.
47. Zep/Graphiti: arXiv:2501.13956 — bi-temporal fact memory (read-path caveat documented in §3.1.1).
48. Mem0: arXiv:2504.19413 — ADD/UPDATE/DELETE write policy comparison.
49. knowl.cloud engineering measurements: reversal detection (cosine 0.0018 margin failure; lexical-first fix; 0.90 single-hop / 0.07 multi-hop supersession) — independent engineering blog, measured numbers.
50. TIMPS write-time gating: 69.9% → 98.2% write-acceptance accuracy with layered bi-temporal conflict checks.

### T3 — Community Code (repos verified 2026-09-23 unless noted)

51. atlas — RichSchefren/atlas. AGM + Ripple on Neo4j, MCP server. [VERIFIED-2026-09-23]
52. epica — angelnicolasc/epica. Rust AGM runtime, Merkle audit trail, MCP. [VERIFIED-2026-09-23]
53. belief_set — ctoth, PyPI. Pure-Python AGM kernel. [VERIFIED-2026-09-23]
54. Sibelium — lealoth/Sibelium. 34 mechanisms, CE routing formula. [VERIFIED-2026-09-23]
55. LIMEN — zero-dependency GWT runtime. [INFO-LIMITED]
56. swaylq/emotion-system — 7-layer emotion architecture. [INFO-LIMITED]
57. mokosh — Rust HTM SDR. [INFO-LIMITED]
58. omega-hippocampus — Rust DG/CA3/CA1/place/grid/SWR. [VERIFIED-2026-09-23: docs confirm claims; no papers]
59. NexusCortex — Go emotion module. [VERIFIED-2026-09-23: rejected on language]
60. biomind/HIPECA v2.5 — Python qualia system. [VERIFIED-2026-09-23]
61. Maxim — dennys246. NAc reward learning, PainBus. [VERIFIED-2026-09-23]
62. snath-ai/DMN — Python DMN contracts. [VERIFIED-2026-09-23: watch list]
63. defaultmodeAGENT — EveryOneIsGross. Python DMN. [VERIFIED-2026-09-23: watch list]
64. pyClarion — CLARION cognitive architecture Python port (Sun et al. lineage). [INFO-LIMITED]
65. HoloVec / amari-holographic — HRR binding/unbinding libs. [INFO-LIMITED]

### Internal Records

66. Session `20260923_080823_fe0fcf3b` — verification delegation + three-round wiki audit (all data in §0.2, §10.2).
67. `research/dcpm-dual-process-belief-trajectory-tracking.md` (331 lines), `research/memory-tier-integration-followup.md` (446), `research/procedural-tier-integration-cyclic-fps.md` (546) — internal deep analyses.
68. Oracle wiki AGENTS.md operating rules (provenance, preserve-don't-delete, writeback check).
69. Graphify decision records: `decisions/2026-09-15_graphify-nohup-disown.md`, `decisions/2026-09-17_oracle-brain-graphify-restart.md`.

---

## Appendix: Summary Statistics

- **Categories:** 7 (+34 wiki-backed concept areas dispositioned in §5)
- **Components with full dossiers:** 31 in v1 → 48 in v2.0 → **32 build components in the §4.1 matrix** + watch/rejected in §4
- **Neuroanatomical coverage:** 19 brain regions mapped; 13 covered by existing subsystems, 4 filled by proposal, 2 theory-grounded, 1 deliberately empty (cerebellum)
- **Tier distribution:** T1 anchors 13 · T2 preprints 13 · T3 community 16 · T4 conjecture 6 (some entries carry two tiers, e.g., T3 lib on T1 theory; v2.2: IJCAI-2025 and ToMAgent promoted to T1, MEMTIER demoted to T2)
- **Verified by 2026-09-23 audit:** 18 projects (3 peer-reviewed confirmed: COKE, HiCL, MetaMind)
- **Build-from-paper specs:** 3 (counterfactual engine, CA3 attractor, TrustMem verifier)
- **Implementation phases:** 4, evidence-tier-driven (§9)
- **Known gaps after implementation:** 32 (§11)
- **Corrections recorded:** 12 (§0.5)
- **Explicitly excluded:** 5 (DSPy-as-memory, DoWhy, jina-embeddings, NexusCortex, depth psychology)
- **Watch list:** 5 (epica, omega-hippocampus, snath-ai/DMN, defaultmodeAGENT, CogFlow/MemCog)

---

## Future / Aspirational Research Directions

This section records approaches and components that were **previously described in §1** but have been removed from the "current architecture" documentation because they do not ship in the repo. They are preserved here as active proposals that may be revisited — the fact that they don't ship today is not a judgment that they were wrong.

### Stack Components (Deferred, Not Shipped)

| Layer | Technology | Previous Role | Why Removed | Research Status |
|-------|-----------|---------------|-------------|-----------------|
| Knowledge Graph | Neo4j + Graphiti | Temporal knowledge graph | Not in `requirements.txt` or `docker-compose.yml`. Cut per locked decision 3 (PPR runs in-process; the Postgres `edges` table has since been restored, so this row's original premise is stale — see §0.7. Neo4j would still add a database server the project does not otherwise need). | Zep/Graphiti paper (arXiv:2501.13956) describes bi-temporal fact memory with read-path caveats. Neo4j research exists in the Active Wiki (`research/neo4j-graph-database-agent-memory.md`) — external to this repo. **May revisit** if graph queries outgrow in-process PPR (currently non-persistent — see the A3 regression note in §0.5). |
| Episodic Store | JSONL + holographic (MnemoCore/HoloGraph) | Session history persistence | Aspirational — never shipped as described. Current session storage is in SQLite (`state.db.sql`). | HoloVec / amari-holographic HRR binding libraries exist. HRR unbinding as algebraic completion researched in the Active Wiki (`research/procedural-tier-integration-cyclic-fps.md`) — external to this repo. **May revisit** for episodic memory that survives context compaction. |
| Consolidation | Dreaming plugin (cron) | Nightly 3-phase consolidation | Never implemented as described in any shipped plugin. A deterministic SWR consolidation script (`scripts/run_swr_consolidation.py`) existed on `tomi-v1-professionalization` but was removed in the Hermes Brain rebrand; nothing currently writes episodic consolidation to Postgres. | Sleep-cognition literature (§5.6) grounds the phase design. HiCL SWR consolidation (§3.4.1) provides a peer-reviewed implementation path. **May revisit** for richer consolidation (memory synthesis, conflict resolution) once the deterministic baseline is stable. |
| Multi-Agent | 5 instances (main/coder/flowbot/oracle/researcher) | Distributed cognition | Not a stack component — deployment topology choice, not architecture. | Agent-exchange workflows and Kanban-codex-lane patterns exist for inter-agent coordination. **May revisit** when adding social cognition (ToM across agents) or parallel research lanes. |

### Architecture Concepts (Still Active in Dossiers)

The §5 wiki-backed concept areas remain active research items even though they don't ship:

| Concept | Current Status | Research File |
|---------|---------------|---------------|
| Global Workspace Theory (Baars/Shanahan) | Backdrop for cognitive routing | §5.1 |
| HTM / Numenta | Rust SDR crate (mokosh) exists; Python port not started | §5.2 |
| ZenBrain | Info-limited; needs primary sources | §5.3 |
| BrainMem | Info-limited | §5.4 |
| MRAgent | Info-limited | §5.5 |
| Complementary Learning Systems | Rolls-Treves theory is T1; implementation pending | §5.6 |
| Sleep Cognition | Literature grounds SWR phase design; plugin not built | §5.6 |
| Emotion-Cognition | TOAQ preprint exists; integration design T4 | §5.7 |
| Predictive Processing | Theoretical grounding only | §5.8 |
| Interoception | Info-limited | §5.9 |
| Memory Governance | Memory Worth (arXiv:2604.12007) T2 preprint; implementation pending | research/agenda |

### When to Revisit

These items should be reconsidered when:
1. **Graph queries outgrow Postgres** — if PPR over the `edges` table becomes insufficient for multi-hop temporal reasoning, Neo4j/Graphiti research is in `research/neo4j-graph-database-agent-memory.md`.
2. **Episodic survival matters** — if session context compaction loses critical memories that should persist, holographic/HRR research is in `research/procedural-tier-integration-cyclic-fps.md`.
3. **Consolidation richness** — once a deterministic SWR baseline is restored and measured (the ROI canary and scale-diagnostic scripts that would have supplied those measurements were also removed — see the same note), the 3-phase design (memory synthesis → conflict resolution → re-embedding) can be revisited using §5.6 sleep-cognition literature.
4. **Multi-agent ToM** — when social cognition extends beyond the user to modeling other agents, the 5-instance topology and agent-exchange patterns provide the scaffolding.

*These are not rejected decisions. They are deferred.*

### Restoration Note (2026-09-24)

This section was lost during the `Hermes Brain` rebrand (`095bd9c`) and restored from
`tomi-v1-professionalization` (`78f0424`). Four working scripts were lost in the same
rebrand and are **not** yet restored: `scripts/run_swr_consolidation.py`,
`scripts/run_roi_canary.py`, `scripts/run_scale_diagnostic.py`, and
`docker/deriver-entrypoint.sh`. The Postgres `edges` / `roi_canary_probes` /
`scale_decay_diagnostic` tables and the Postgres persistence in
`brain/hippocampus/associative.py` were reverted at the same time. See §0.6.

*End of proposal v2.2. Next actions: review comments → merge to main → lane dispatch for Phase 1 items → research dispatch for the [INFO-LIMITED] components (thin wiki coverage means analysis debt, not build debt) → recheck Gated-Memory Routing's EMNLP 2026 acceptance after the Oct 24-29 conference (via ACL Anthology — the 2026.emnlp.org accepted-papers page is stale) → watch MEMTIER (arXiv:2605.03675) and DCPM (arXiv:2606.09483) for venue acceptance on the quarterly watch-list pass.*
