# Cognitive Coverage Review — what the wiki knows that the system lacks

**Date:** 2026-09-25
**Method:** coverage scan across both vaults (every markdown file in each), then
mechanism-by-mechanism verification against the implemented code in `brain/`.
**Framing constraint:** this project is a *biologically inspired cognitive
architecture*, not a brain replica. Where a peer-reviewed win exists, the win is
attributable to an ordinary computational primitive; the cognitive vocabulary is
explanatory framing, not the cause. Every proposal below therefore states the
primitive separately from the analogy, and is marked with what the evidence
actually is.

---

## Part 1 — The scan was blunt, and that mattered

The first pass searched the vaults for 20 candidate cognitive topics and **every
one came back "covered."** Predictive processing: 3,671 mentions. Basal ganglia:
3,148. Curiosity: 812. Nothing looked missing.

That result was useless, and worth recording as a methodological finding: **keyword
frequency measures how much a vault talks about a topic, not whether the system
implements it.** A vault can hold 3,000 mentions of predictive processing and still
contribute nothing to the running code, because the code is a separate artifact.

So the real question is not *"is this in the wiki"* but *"is this in the wiki AND
absent from `brain/`."* That is what the rest of this document measures.

### A second problem: the wiki's own citations are unreliable

Verifying the strongest candidate surfaced something that affects how every claim
below should be read. See **[CITATION-AUDIT.md](CITATION-AUDIT.md)**.

In `oracle/brain/Prospective-Memory/Implementation-Intentions.md`, **8 of 8 DOIs
checked are broken.** Five return 404. Three resolve to papers on entirely
unrelated subjects — one to a biographical note, one to a paper on narrative ego
integrity, one to a meta-analysis of acute stress and memory. Correct DOIs for the
two most important works were recovered from Crossref and recorded.

**The scholarship in the vault is broadly sound. Its citation plumbing is not.** So
where this review says "strong evidence," it means the underlying literature is
strong — and it has been checked against a corrected DOI, not against whatever the
vault happened to write down.

---

## Part 2 — What is actually implemented

Nine subsystem directories, 29 Python modules. Verified wiring in
`brain/hermes_brain.py` by finding every `self.<attr> = ` construction and every
`self.<attr>.<method>(` call:

| Subsystem | Instance | Methods called | State |
|---|---|---|---|
| cortex (working memory) | `dl_pfc` | `upsert_slot`, `decay_all`, `render_context_summary` | **wired** |
| cortex (executive) | `executive` | `evaluate_shifting` | **wired** |
| cortex (routing) | `router` | `evaluate_route` | **wired** |
| thalamus | `thalamic_gate`, `thalamic_buffer` | `evaluate_admission`, `append` | **wired** |
| limbic (valence) | `valence_engine` | `record_outcome`, `get_state` | **wired** |
| limbic (somatic) | `somatic_engine` | `assess`, `record_experience` | **wired** |
| basal ganglia | `action_gate`, `skill_compiler` | `evaluate_pathways`, `observe_sequence` | **wired** |
| hippocampus (replay) | `replay_engine` | `record_episode` | **wired** |
| social | `tom`, `pragmatics` | `check_discrepancies`, `analyze_implicature` | **wired** |
| **dmn** | `counterfactual`, `chronesthesia` | — | **constructed; not in the agent loop** |
| **epistemology** | `agm`, `defeater_graph`, `dialectic` | — | **constructed; not in the agent loop** |
| **hippocampus (graph)** | `associative_graph` | — | **constructed; dashboard-visible only** |
| schema | — | — | **stub (`__init__.py` only, 18 lines)** |

**Finding 1 — six subsystems are constructed but never called from the agent loop.**
`hermes_brain.py` exposes exactly two public methods beyond `__init__`:
`process_incoming_stimulus` and `record_action_outcome`. Neither references
`counterfactual`, `chronostasis`, `agm`, `defeater_graph`, `dialectic` or
`associative_graph`; all six are assigned in `__init__` and nothing else.

**The honest qualifier, which matters:** three of them *are* reachable from
elsewhere, so "dead code" would be wrong.

| Subsystem | Reachable from | In the agent loop? |
|---|---|---|
| `counterfactual` | `dashboard/backend/routes/brain.py` | **No** |
| `defeater_graph` | `dashboard/backend/routes/brain.py` | **No** |
| `associative_graph` | `dashboard/backend/routes/brain.py` (read-only stats) | **No** |
| `agm` | tests only | **No** |
| `dialectic` | tests only | **No** |
| `chronostasis` | **nothing repo-wide — 0 references outside its own construction** | **No** |

So the accurate statement is: **all six are observable, none participates in
reasoning.** An operator can inspect beliefs or graph size through the dashboard,
and a test can exercise AGM revision in isolation, but when `process_incoming_stimulus`
runs, none of them sees the input. For `chronostasis` there is no consumer anywhere,
including a dashboard.

That is a meaningful gap rather than a cosmetic one: the architecture document
describes belief revision, counterfactual simulation and the associative graph as
functioning parts of the system. They are constructed, inspectable, and inert.

**Finding 3 — the docstring count is stale.** The architecture's frontmatter says
"7 brain subsystems." There are nine directories and twelve instances.

---

## Part 3 — Mechanisms the wiki covers and the system lacks

Verified absent by grepping all 29 modules for the mechanism's vocabulary, then
manually reading every hit to rule out keyword noise.

| # | Mechanism | Brain system | In vault? | In code? |
|---|---|---|---|---|
| 1 | **Prospective memory / implementation intentions** | frontal lobes, basal ganglia | **Yes** — dedicated `Prospective-Memory/` area | **No** — 0 references |
| 2 | **Error correction from predicted-vs-actual** | cerebellum | Partly (270 mentions) | **No** — 0 references |
| 3 | **Predictive processing / free-energy** | cortex, cerebellum | **Yes** — dedicated `Predictive-Processing/` area, 7 files | **No** — 0 references |
| 4 | **Adaptive forgetting / pruning** | hippocampus, prefrontal cortex | **Yes** — `Consolidation/Adaptive-Forgetting.md`, 37 sources | **Partial** — activation decay exists, but not *forgetting of stored memory* |
| 5 | **Interleaving / desirable difficulty** | — | **Yes** — `learning/` area | **No** — 0 references |
| 6 | **Systematicity / compositional reasoning** | prefrontal cortex, hippocampus | Partly | **No** — 2 incidental references |

### 1. Prospective memory — the strongest candidate

**The idea, in plain language.** Humans do not reliably act on a stated intention
("I should email her"). What works is a conditional plan: *if situation X arises,
then do Y.* Gollwitzer calls these **implementation intentions** — they wire a
specific cue directly to an action so that encountering the cue fires the response
without deliberation.

For an agent this is remarkably direct. An agent already knows how to write
`if` statements. What it lacks is a *store of standing intentions with trigger
conditions*, checked against each turn.

**Why it is the strongest candidate:** the evidence base is the best in this entire
review, and the mapping to software is nearly one-to-one.

- Gollwitzer & Sheeran (2006), *"Implementation Intentions and Goal Achievement: A
  Meta-analysis of Effects"*, **Advances in Experimental Social Psychology**,
  DOI `10.1016/S0065-2601(06)38002-1`. A meta-analysis of the goal-attainment
  effect, and the medium- to large-effect findings are what made the if-then format
  a standard intervention.
- Gollwitzer (1999), *"Implementation intentions: Strong effects of simple plans"*,
  **American Psychologist** 54(7), DOI `10.1037/0003-066x.54.7.493`.

**Evidence tier:** peer-reviewed meta-analysis plus a large primary literature,
primarily in human health-behaviour studies. *Not* yet replicated in LLM agents —
that is the honest gap, and the reason this is a proposal rather than a shipped
feature.

**The primitive, independent of the biology:** a durable table of
`(trigger_condition, action, created_at, expires_at, state)` plus a matcher that
runs each turn. No model call required — the trigger is evaluated against turn
content, and only a match promotes the intention into the action path. That is
cheap, testable, and deterministic, which matters: a 2026 study (arXiv:2606.01435)
found model-judged freshness resolution scoring 7% against BM25's 48%, so anything
that can be a table lookup **should** be.

**Honest cost:** stale intentions firing at the wrong moment. Mitigations:
`expires_at`, explicit state, and a per-turn cap. The vault's own dossier flags the
rebound-risk literature from suppression research — repeated suppression of an
intention can produce the opposite of the intended effect — which argues for
expiry rather than indefinite triggers.

**Recommendation: incorporated.** Shipped in `brain/prospective/intentions.py` and
wired into `process_incoming_stimulus` as step 7b, so fired intentions surface as
`fired_intentions` in the response. 41 tests, including four that drive it through
the real hub rather than in isolation.

Implementation choices worth noting, because each answers a specific failure mode:

- **Deterministic matching, no model call.** Trigger matching is token-based, so
  this is a table lookup rather than a judgement call — deliberately, given the
  7%-vs-48% result in §4 of prospective memory above.
- **Substring matching, not whole-word.** An intention written as "postgres down"
  has to fire on "postgres appears to be down". A missed intention fails silently,
  which is worse than an occasional false positive.
- **`max_fires=3` per turn.** An intention store that can flood the prompt is worse
  than one that stays quiet.
- **Expiry is enforced lazily on the hot path.** The first version left a past-due
  intention in state `'pending'` until something remembered to sweep it, so any
  direct query on `state='pending'` returned dead rows. Caught by a test.
- **Nothing is ever deleted.** `cancel()` and `expire_due()` are state transitions.
  Modelled on Honcho #989, where semantic similarity permanently deleted the
  incumbent memory.
- **Fired intentions re-read after marking.** The response used to report
  `fired_count: 0` for the intention that had just fired. Caught by a test.

**What is still unproven:** that this improves outcomes for an LLM agent. The human
evidence is strong and the mapping is mechanical, but the measurement is absent.
Treat the feature as instrumented, not as proven.

### 2. Error correction from predicted-vs-actual — a bargain, if it works

**The idea, in plain language.** The cerebellum continuously compares what you
*meant* to do against what *happened*, and corrects the gap very fast — far faster
than deliberate reasoning allows. It is a prediction-and-correction loop, not a
planner.

**The primitive:** before a tool call, record the expected outcome. After it
returns, diff. A systematic mismatch is a signal that the agent's model of a tool
is wrong — which is worth far more than the answer to the current question, because
it prevents the *next* one being wrong the same way.

**Honest status:** this is the most conceptually appealing and the least evidenced
item here. The strong human evidence is for cerebellar timing and motor correction,
which is not obviously the same problem as a tool call returning an unexpected
shape. A pilot is cheap; a claim that it works is not available yet.

**Recommendation: pilot only.** Measure prediction accuracy per tool before
building anything elaborate. If the baseline is already high there is nothing to
learn; if it is low, the signal is worth a lot.

### 3. Predictive processing — theoretically elegant, empirically unproven

**The idea.** The brain is a hierarchical prediction engine: each level predicts the
level below, and the *error* between prediction and input drives learning. Under
this view, perception is not reading the world — it is resolving prediction error.

**The primitive:** retrieval as prediction. Instead of "find documents matching
these keywords," generate a prediction about what the answer should contain, then
treat retrieved material as evidence that confirms or refutes it.

**Honest status:** the vault holds seven dedicated files on this and they are good
synthesis. But the applied evidence is thin. Most of the literature is theoretical
(Friston, Clark and colleagues), and this project has previously recorded
neuromodulation-style mechanisms as having **no benchmark evidence**. Extrapolating
from theory to an implementable, measurable win is exactly the move that produces
architecture nobody can justify.

**Recommendation: defer.** Revisit if the retrieval layer needs a better idea than
hybrid BM25 + vector + graph fusion, which currently works and is measured.

### 4. Adaptive forgetting — the vault already grades this honestly

**The idea.** Forgetting is not a failure. Retrieval-induced forgetting (learning A
then recalling B impairs later recall of A) is a real effect with a real functional
role: it keeps the useful part of memory clean.

**What the vault already established, and it is good work:** the dossier documents a
genuine replication crisis.

- **Basden et al. (2014)** failed to replicate retrieval-induced forgetting at
  N=288 across multiple paradigm variants — no significant effect in any.
- **Huettl et al. (2021)**, preregistered, N=630, found a small but reliable effect
  (d ≈ 0.15–0.20) — far smaller than original reports.
- **Depret, Erlbaum & Eerland (2020)**, meta-analysis of 105 experiments and 39,000+
  participants, put the effect at d=0.31 — falling to roughly **0.15 once
  publication bias is corrected**.

The dossier's own effect-size table lists d=0.47–0.72 for the original small-N
studies, which the replication work does not support. **So the honest headline is
that active forgetting is real but much smaller than the foundational literature
claims, and whether it is active or passive remains contested.**

**What exists in code:** activation decay and eviction in `cortex/dl_pfc.py` —
working-memory pressure, refreshed on use, decaying otherwise. That is *not* the
same thing. Nothing forgets a stored long-term memory; nothing merges duplicates;
nothing judges a memory low-utility and retires it.

**Recommendation: incorporate, conservatively.** The evidence says forgetting helps
only modestly and implementation errors can cost real data — recall Honcho issue
#989, where semantic similarity permanently deleted the incumbent memory. Any
pruning here must be reversible and must never delete the only copy. Log
everything, require a utility threshold, and prefer *demotion* to deletion.

### 5. Interleaving and desirable difficulty — human evidence, no transfer yet

**The idea.** Mixing practice types (interleaving) beats blocking them, even though
it feels worse. Spacing repetitions out beats massing them. Both are among the most
replicated findings in the learning sciences, and both contradict intuition.

**Honest status:** robust in humans; **not established for LLM agents.** There is no
credible evidence that an agent improves by deliberately interleaving its own
practice. Adopting it on the strength of the human literature would be importing a
finding across a gap that has not been tested.

**Recommendation: defer.** Cheap to revisit if the project ever gets a
self-improvement or skill-acquisition loop that could plausibly be measured.

### 6. Systematicity / compositional reasoning

**The idea.** People apply a known rule to new combinations. Models often fail
exactly here — learning that A relates to B, and B to C, but not inferring A to C.
This is the "both/and" problem, and it is the classic justification for graph
retrieval.

**Status:** the associative graph is **constructed and never called** (Finding 1).
The graph *exists*; the multi-hop reasoning it enables is not reachable. And the
project's own evidence bears directly on this — arXiv:2606.01435 measures
multi-hop at **≤7% across all 22 evaluated systems**, noting it is "nearly
unsolved." So the opportunity is real and so is the difficulty.

**Recommendation: wire the existing capability before building anything new.** The
graph retrieval path is built, tested, and works. It needs a call site.

---

## Part 4 — Ranked

| Rank | Proposal | Evidence | Effort | Verdict |
|---|---|---|---|---|
| 1 | Wire six inert subsystems into the agent loop | Code-verified defect | Trivial — they exist | **Do first** |
| 2 | Prospective memory / if-then triggers | Meta-analytic, human | Small | **Shipped — unmeasured** |
| 3 | Adaptive forgetting (reversible) | Real but small after bias correction | Medium | **Incorporate carefully** |
| 4 | Prediction-error feedback loop | Conceptual appeal, thin evidence | Small pilot | **Pilot** |
| 5 | Make curiosity drive something | Write-only field today | Trivial | **Fix or delete** |
| 6 | Predictive processing as retrieval | Mostly theory | Large | **Defer** |
| 7 | Interleaving / desirable difficulty | Human-only | Small | **Defer** |

**Items 1 and 5 cost almost nothing and either fix real defects or remove dead
weight.** They are first because they are not research questions.

## The strongest argument against this review

The top two proposals rest on human behavioural research, and this project has
already been burned translating human findings into agent architecture — the
`PROPOSED-BRAIN-ARCHITECTURE.md` evidence audit found that theory-of-mind and
multi-agent belief merging, the most brain-like proposals available, score **0.0%
and 30.1%** respectively in independent evaluation, *worse than not doing them*.
Prospective memory could be the same story: a robust effect in people that does not
transfer to agents.

The counter-argument is that implementation intentions are unusually mechanical —
an if-then rule with a trigger condition needs no inference at all, so it avoids the
failure mode that kills the ToM proposals. **But that is an argument, not
evidence.** The only way to settle it is to build the small version and measure it,
which is why item 2 is ranked on effort-adjusted value rather than enthusiasm.
