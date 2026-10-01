# BRAIN ARCHITECTURE — SECTION C: METACOGNITION (C-3)
The largest coherence gap. Read after Section A.

## THE GAP, STATED PLAINLY

The repo's own rules demand epistemic discipline: `epistemic-protocol` exists as a
skill, `epistemology/agm.py` and `defeater_graph.py` exist as code, and
SCRATCHPAD tags every claim [V]/[W]/[?]. **But nothing measures whether the agent
is right.** There is no calibrated confidence on retrieval, no signal for "I don't
know," and no controller that spends more effort when confidence is low.

This is a self-reference failure. The repo has built the apparatus for *labelling*
epistemic status and none of the apparatus for *detecting* it. Per A-12, the
detection half is not even wired.

Why it ranks above the other gaps: a brain that cannot tell what it does not know
cannot allocate search effort, cannot abstain credibly, and cannot learn from being
wrong. Every other cognitive function downstream — routing (C-6/B-6), belief
revision (B-1), consolidation scheduling (C-11) — takes a confidence signal as
input. **Metacognition is upstream of the whole architecture and currently absent.**

## WHAT THE VAULT HOLDS (10 files, `Metacognition/`)

The material is unusually good and unusually applicable. The mapping is direct:

| Vault file | Human phenomenon | Agent analogue it specifies |
|---|---|---|
| `Feeling-of-Knowing.md` | TOT / FOK — *prospective* metamemory, before retrieval | "Do we have this, even though I can't produce it now?" → decides whether to reformulate, search elsewhere, or defer |
| `Metacognitive-Sensitivity.md` | meta-d', gamma correlation, calibration curves | Post-answer confidence vs actual correctness. The calibration curve is the instrument |
| `Metacognitive-Monitoring-vs-Control.md` | Nelson-Narens: monitoring ≠ control | Feeling-of-knowing and *acting on it* are separable. Must be built as two modules, not one |
| `Source-Monitoring-Framework.md` | Johnson, Hashtrati, Lindsay — misattribution | Remembering the *content* vs remembering *where it came from*. Directly the vault-vs-wiki-vs-web provenance question |
| `Processing-Fluency-Illusions.md` | fluent = true (Zimmerman) | The single most important failure mode for an LLM: confident-sounding retrieval that is wrong. Fluency is the disease |
| `Confabulation.md` | honest self-ignorance vs confabulation | The exact line the agent must not cross: "I don't know" must be reachable |
| `Dunning-Kruger-Replication-Debates.md` | skill/competence miscalibration | Confidence must be *earned by track record*, not asserted. The file's replication caveats matter |
| `Epistemic-Emotions.md` | curiosity, surprise, boredom | Surprise is a usable novelty signal for the write gate (§F) |
| `Planning-Fallacy-Reference-Class-Forecasting.md` | planning fallacy; reference classes | Forecasting own work by base rates, not by wishful simulation |

`Feeling-of-Knowing.md` names the mechanism we need precisely: gamma correlations
around 0.3–0.5 for monitoring accuracy — "imperfect predictions of future
retrievability still beat blind search." **That is the design target. A weak
signal that beats no signal, with a known reliability.**

## TOP 3 CANDIDATES

**RANK 1 — Retrieval-confidence estimation, calibrated, over the existing stack.**
Self-consistency over sampled generations (token entropy + agreement across k
samples) as the confidence signal, fitted against a recorded correctness label
drawn from the A-03-prescribed benchmark once that exists.
- PRO: no new infrastructure; works over whatever retriever is in place;
  self-consistency is the most replicated confidence signal in the LLM literature;
  produces the calibration curve the vault asks for.
- PRO: it is the *only* candidate that directly attacks Processing-Fluency-Illusions,
  which is the dominant failure mode here.
- CON: self-consistency is confounded — a consistently wrong answer is confident.
  Weakens exactly where fluency hurts most.
- CON: needs a labelled correctness set to fit, which is blocked behind A-03.
- BUILD: `brain/cortex/confidence.py`. Emit `(confidence, evidence_ids, mechanism)`
  per answer. Log every (predicted, actual) pair to a new `confidence_log` table so
  the calibration curve is *measured from our own history* rather than assumed.

**RANK 2 — Source-monitoring + provenance binding (SMF).**
Bind every retrieved span to its origin (vault file + line / wiki page / web URL +
retrieval strategy) and require the agent to name the source when it states a fact.
- PRO: the vault already mandates provenance (AGENTS.md rule 8: "Every important
  claim must preserve provenance"). This makes that rule mechanical.
- PRO: directly addresses Source-Monitoring-Framework misattribution — the failure
  where the agent recalls a fact but from the wrong place, which is worse than
  not recalling it.
- PRO: cheap. graphify already stamps `source_file` + `source_location` on every
  node (SCRATCHPAD A-05: 20,067 of 20,199 nodes carry `source_file`) — the raw
  material is already there and is one of the few things about the current graph
  that is verifiably good.
- CON: provenance is necessary, not sufficient. A correctly-sourced wrong claim is
  still wrong.
- CON: does nothing for the "I don't know" case, which is the harder half.
- BUILD: extend `epistemic-protocol` from a written rule into a schema. Every
  belief row already has `provenance` (see `defeater_graph.py` INSERT) — add
  `source_location` and `retrieval_strategy`, and make the answer path *require* it.

**RANK 3 — Latent-knowledge probing (P(true) head / pre-hoc assessment).**
Ask "do I know the answer to this?" *before* retrieval and read the probability
that the model would answer correctly if it tried.
- PRO: this is literally the FOK construct — prospective, pre-retrieval. It is the
  most faithful mapping in the vault.
- PRO: cheap to test — one extra forward pass, no retrieval, no labels required to
  *start* collecting signal.
- CON: needs a model exposing token-level probability for the answer, which
  constrains it to the local model rather than any API. The repo's local
  llama.cpp/GPU node makes this feasible (C-2/HippoRAG #3 already assume GPU).
- CON: the cheapest to build and the least reliable alone; it belongs *under*
  Rank 1 as a feature, not beside it as a strategy.
- BUILD: pilot in the existing `brain/hippocampus/` — a `probe()` that returns
  P(answer) given a question with no context, logged against eventual correctness.

### Why not the others
- **Self-Reflection-in-Humans-and-AI.md** (2 files) is a *discourse*, not a
  mechanism. It motivates; it does not specify. Rank 1-3 are mechanisms.
- **MetaMind** (B-3, ToM) models *other* agents' beliefs. Metacognition is
  first-person. Do not let the ToM pipeline be mistaken for a self-model.
- **Defeater graph as-is** reasons over stated beliefs; it does not calibrate
  confidence in retrieval, which is where the errors enter. Keep it (B-1), do not
  count it twice.

## HOW IT FITS THE WHOLE (the reason this is not a bolt-on)

- **Routing (B-6):** Sibelium's CE formula and LIMEN's auction both need an
  effort-allocation input. Confidence-below-threshold is the natural trigger to
  escalate deliberation. This replaces the current static routing with an adaptive one.
- **Retrieval:** when confidence is low *and* FOK is high, the correct action is to
  **reformulate the query, not re-run the same one** — the note's answer exists but
  is not reachable by this phrasing. This is the single highest-value behaviour
  available from this gap, and it is exactly what the A-03 benchmark's broken
  keyword arm cannot do.
- **Belief revision (B-1):** a confidence signal is the precondition for entrenchment
  ordering to mean anything. AGM ranks by how firmly a belief is held; entrenchment
  is currently a hand-supplied float defaulting to 0.5.
- **Consolidation (C-11):** sleep/nightly scheduling should promote high-confidence,
  high-consolidation items and quarantine low-confidence ones. Right now it is a timer.
- **Abstention:** the vault's `Confabulation.md` asks for honest self-ignorance as a
  reachable state. This is the mechanism that makes it reachable.

## THE INSTRUMENT THAT MAKES IT FALSIFIABLE

Non-negotiable, or this gap rebuilds into the same unfalsifiable prose the repo
already has 42 docs of:

1. Every answer logs `predicted_confidence` and, once judged, `actual_correct`.
2. A calibration curve is computed from our own log — not from a paper.
3. Gamma correlation between FOK and eventual correctness, reported over time.
   Target: >0.3, the vault's stated threshold for "beats blind search."
4. A **gated** escalation test: when confidence < threshold, does reformulate-then-
   retry beat retry? Measured on the A-03 benchmark once that is built.

Numbers 1–3 are instrumentation, not a performance claim, so R-J2 is not violated
by *recording* them. Producing an efficacy number requires a researcher.

## SEQUENCE

Phase 0 (no new build): wire `defeater_graph` and `agm` into the answer path (A-12),
  and make `source_location` mandatory (Rank 2). Both are small.
Phase 1: `confidence.py` + `confidence_log`. Rank 1 mechanism, no labels needed to start.
Phase 2: Rank 3 probe, feeding Rank 1 as a feature.
Phase 3: calibration-driven routing and consolidation scheduling.

**Dependency the owner must see:** Phase 1's value is capped until the A-03
benchmark exists, because "is it calibrated" is unanswerable without a correctness
label. Building the benchmark and building metacognition are the same project
seen from two ends. Recommend they be funded as one.
