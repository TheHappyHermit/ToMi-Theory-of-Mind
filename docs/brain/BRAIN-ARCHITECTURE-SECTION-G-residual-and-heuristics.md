# BRAIN ARCHITECTURE — SECTION G: RESIDUAL GAPS
C-6 social beyond ToM · C-7 language grounding · C-8 causal contradiction ·
C-10 tool-as-cognition · plus the heuristics library (C-H).
Read after Section A.

================================================================================
## C-6 SOCIAL COGNITION BEYOND THEORY OF MIND
================================================================================

`brain/social/` has two files: `tom.py` and `pragmatics.py`. The vault directory
`Social-Cognition/` has **19**. B-3 (ToM) is genuinely well-built — MetaMind, the
COKE/COLM citation, the Dynamic ToM tracker. The problem is that ToM is *one
narrow slice*, and the vault contains three findings that bear directly on how
this repo is built.

**G1. Collaborative inhibition — a named failure mode of the current design.**
Vault `Collaborative-Inhibition.md`: groups recall **less than the pooled
non-redundant output of the same people working alone** (Weldon & Bellinger 1997;
Marion & Thorley 2016 meta-analysis, 75 effect sizes / 64 studies). Dominant
mechanism is **retrieval strategy disruption** — each member organizes material
with idiosyncratic schemes, and hearing others' output forces abandonment of your
own optimal retrieval path. The vault says it is one of the most robust and
counterintuitive findings in social memory, and that the vault itself states the
computational parallel explicitly: **"computational parallels for multi-agent AI
systems where retrieval interference between agents mirrors human collaborative
inhibition."**

This repo runs 5 Hermes instances, a research queue, and a cron system that
gathers into shared stores. **That is the collaborative-inhibition setup.** The
architectural implication is specific and non-obvious: agents merging *retrieved
content* into a shared store corrupt each other's retrieval strategies. Merging
*conclusions with provenance* does not. This is a design constraint on the wiki/
graph refresh pipeline (which A-08 already shows is damaging the vault graph), and
it is not currently stated anywhere.

Basden et al. also give the fix condition: **collaborative inhibition disappeared
when participants retrieved non-overlapping list parts, or were forced to organize
by category.** Partition the work by category so agents do not collide in the same
retrieval space.

**G2. The argumentative theory of reasoning — the most practically important thing
in that directory, entirely absent from the repo.**
`Argumentative-Theory-of-Reasoning.md` (Mercier & Sperber). Humans reason poorly
when required to reason alone, and reason well when the task is argumentative —
myside bias is not a bug of individual reasoning but the *predicted outcome* of
reasoning's argumentative function. The vault file exists; the repo has zero trace.
For an agent with 5 instances, this is the mechanism that says **use the instances
adversarially, not as 5 agreeing votes.** An agent that asks 5 sub-agents the same
question and takes the majority reproduces myside bias with a vote count attached.
This is a concrete design rule the repo violates by default if ToM coordination is
built as consensus.

**G3. Cognitive dissonance** (`Cognitive-Dissonance-and-Self-Justification.md`,
Festinger 1957): inconsistency between held cognitions produces an aversive state
that drives reduction. For the agent: **the DCPM `supersedes` chain (B-1) is a
dissonance-reduction mechanism, and the repo has no signal that a conflict exists
and is unresolving.** A belief chain that keeps extending without ever superseding
is unresolved dissonance, stored indefinitely, consuming belief capacity while
changing nothing.

**I queried the store rather than guessing — the finding is worse than expected. [V, 2026-09-25]**
`brain/brain.db`, table `cognitive_beliefs` (note: the table is `cognitive_beliefs`,
there is no `beliefs` table and no `superseded_by` column — supersession is expressed
through the `epistemic_state` enum):

| measure | value |
|---|---|
| total beliefs | 106 |
| `provenance` values | **`test` (53), `firewall_scanner` (53)** |
| `epistemic_state` | `disputed` (53), `grounded` (53) |
| credence min / max / avg | 0.90 / 0.95 / **0.925** |
| `prospective_memory` rows | **0** |
| `user_mental_models` rows | **0** |
| `somatic_markers` rows | 1 |

Three conclusions, and they are load-bearing:
1. **The belief store contains no real beliefs.** Every row is a test fixture —
   two sources, exactly 53/53, no real provenance category in use. The AGM
   machinery has never processed a belief the agent actually holds.
2. **The perfect 53/53 split and the 0.90–0.95 credence band are fixture
   artefacts, not a measurement of anything.** The average is 0.925 with a range
   of 0.05. **There is no confidence signal in this database** — which is exactly
   what Section C says is missing, now confirmed at the data layer rather than
   inferred from code.
3. **`prospective_memory` is empty.** The largest module in the repo (340 lines,
   intentions.py) has never had a row written. Combined with A-12 (six instances
   constructed, never called), the picture is that the cognitive architecture is
   **built, wired to nothing, and fed no real data.** Section C's premise is
   confirmed: the repo has apparatus for labelling epistemic status and none for
   detecting it.

### Top 3 for C-6
1. **Argumentative (adversarial) multi-instance protocol** — instances assigned
   *opposing* positions, not consensus votes. Directly from G2. Cheapest change with
   the largest expected effect on multi-agent quality. **Do this first.**
2. **Category-partitioned agent work + provenance-bearing merges** — from G1 and
   Basden. A rule for the wiki/refresh pipeline, not a module.
3. **Dissonance detection** — surface unresolving belief conflicts instead of
   letting them accumulate. Binds to E2 (working-memory contradiction) and B-1.

================================================================================
## C-7 LANGUAGE-THOUGHT GROUNDING
================================================================================
Vault: `Language-and-Thought/`, `Numerical-Cognition/`.

**G4. Vocabulary mismatch is a retrieval failure mode and nothing models it.**
The query says "recall", the document says "remember". The query says "why did the
job fail", the document says "root cause". This is the failure mode most likely to
explain a "the agent couldn't find it even though it was right there" report, and
the current retrieval stack has no synonym/embedding-alignment step that addresses
it. The A-03 benchmark's broken keyword arm (paths only) is an extreme version of
exactly this problem.

Candidate 1: **vocabulary-normalising query expansion** against a domain
synonym/embedding index, applied to the query before retrieval. Candidate 2:
hybrid lexical+dense with proper score fusion (RRF), which the architecture already
names for Phase 1 #4 — the *lexical* half of RRF is the mitigation and it is
currently absent. Candidate 3: a lightweight domain lexicon (Numerical-Cognition is
a ready-made source of the register mismatches this repo will actually hit).

Rank 1 above because it is the cheapest and it is the one that fixes a
user-visible symptom. ACT-R's Perceptual/Manual buffer distinction (vault
`Cognitive-Architecture-ACTR.md`) is the right frame: input arrives in a different
representation from storage, and the architecture has no encoder for that gap.

================================================================================
## C-8 CAUSAL REASONING — A CONTRADICTION TO RESOLVE, NOT A GAP
================================================================================

The architecture **rejects** causal inference: §9 Phase 4 says "DoWhy — data-science
causal inference, not agent cognition." But §3.2.4 builds a counterfactual engine
(C3→CRAFT, ActMem, frozen replay), and **counterfactual reasoning is a causal
operation** — you cannot evaluate "what would have happened if X had differed"
without a causal model. The vault holds `Causal-Reasoning/` (2 files) as well.

So the repo rejects a category while building an instance of it. The decision
should be stated as: *reject observational causal inference over event logs
(DoWhy's domain); keep and develop counterfactual simulation over the agent's own
action history, which is a different problem with a different data model and is
directly relevant to the goal-reflex arc.* That is a coherent position. The current
text is not. **Fix the wording, keep the counterfactual engine** — and note that
the engine is one of the six unwired instances (A-12).

================================================================================
## C-10 TOOL-AS-COGNITION (split out from the embodied rejection)
================================================================================

§5.14 rejects 226 files of embodied cognition with "our agent has no body; revisit
only if the brain grows sensors." That reasoning is sound for sensorimotor files
and I am not reopening it.

But it should **not** sweep in `Tool-Use-and-Extended-Mind/Tool-Use-and-Extended-
Mind.md` or `Distributed-Cognition/Extended-Mind-Theories.md` and
`Transactive-Memory-Systems.md`. The extended-mind thesis in its Clark-and-Chalmers
form is about *external resources doing cognitive work* — notebooks, tools, other
people — and an agent that runs 5 instances, keeps a scratchpad, a graph, a cron
system, a wiki, and a retrieval log is a textbook extended cognitive system. This is
*descriptive of the current architecture*, not an abstraction.

The immediately actionable part is **transactive memory** (the vault's file of that
name): in a group, individuals do not each store everything; they store *who
knows what*, and retrieve by asking. The repo has 5 instances, a cron system and
jogs. **There is no directory of "who knows what" and no retrieval-by-asking.**
Concretely: the research queue, the newsletter builder, the oracle, and the
notion/wikilink graphs are partly redundant *because* nothing tracks which one is
authoritative for which topic. A small transactive-memory table — topic → owning
subsystem — would (a) reduce duplicated effort across crons, (b) give the router a
real "where do I ask this" signal, and (c) is about 50 lines.

Candidate 1: **transactive-memory map (topic → authoritative subsystem)**.
Candidate 2: external-cognition-as-scaffold — the scratchpad and scratch dir ARE
external memory in the extended-mind sense; formalising their role means treating
the scratchpad as a cognitive buffer with a retention policy, not a temp folder.
Candidate 3: tool-selection-as-habit — covered by B-4, do not duplicate.

================================================================================
## C-H. THE HEURISTICS AND MENTAL SHORTCUT LIBRARY
================================================================================
*This is the item with no home in the existing 32-component matrix. It is not a
tool slot — it is the fast-path layer that decides whether the slow path runs at
all. Listed here because the architecture has no component for it.*

**Why it belongs in the brain and not in the prompt.** A human brain does not
deliberate about most things. System 1 is fast, automatic, and usually right, and
its failures are the reason System 2 exists. In the repo, the analogue of
deliberation is an LLM call and the analogue of intuition is... a skill trigger.
**The repo's entire "fast path" is 249 skill descriptions matched by the model
itself**, which means every turn pays deliberation cost on what should be
autonomy. And per the vault, System 1's errors are *systematic and predictable*
(confabulation, myside bias, fluency illusion, base-rate neglect) — which is
exactly why a deliberate shortcut library is valuable rather than merely fast.

**The design.** A shortcut is a named trigger → pre-compiled response pair, with an
explicit validity condition. The validity condition is the whole point: a shortcut
without one is a heuristic, and heuristics are what the repo's epistemic rules
forbid. Format:

| Trigger (cheap, observable) | Shortcut | Validity condition | Fails when |
|---|---|---|---|
| User names a known-broken tool/service | Run the matching diagnostic skill | symptom string matches a known incident | novel failure mode |
| Repo task is "which X for Y" | Load slot ranking from SCRATCHPAD, don't re-research | slot file is < N days stale | vault gained a newer candidate |
| Retrieved answer has no provenance | Reject, re-retrieve with source binding | always | — (hard rule, not a shortcut) |
| Corpus lookup returns 0 exact hits | Reformulate, don't retry identically (C-3) | FOK signal says knowledge exists | answer genuinely absent |
| Repeated failure on a structured problem | Incubate (F Rank 2), don't retry | impasse, not a resource failure | — |
| High confidence + high impact claim | Force contradiction search before committing | impact > threshold | trivia |
| Contradictory facts in working memory | Surface as conflict, don't let model reconcile silently | always (E2) | — |

**Three rules that keep this from becoming the thing the repo already has too much
of:** (1) every shortcut carries a validity condition, else it is a rule and goes
in the prompt; (2) every shortcut logs when it fires and whether the outcome was
good — a shortcut with a bad hit-rate gets retired, and there is no way to know
that without the log; (3) the library is capped and reviewed, or it becomes the
prompt by another route.

**Interaction with metacognition:** the shortcut layer is exactly the mechanism
that makes a *confidence* signal actionable. A shortcut fires on high confidence;
the absence of a shortcut plus low confidence is the trigger for deliberation. C-3
is what makes the boundary non-arbitrary. **These two must ship together.**
