# Cognitive Evidence Review — Phase 2

**Date:** 2026-09-25
**Status:** study only. No implementation. This document records findings and
recommendations; nothing here has been built.
**Companion:** [`COGNITIVE-COVERAGE-REVIEW.md`](COGNITIVE-COVERAGE-REVIEW.md) covers
what the wikis know versus what the code implements. This one covers the external
evidence base, including what does **not** work.

---

## A correction to the research, made after reading the source tables

A research stream reported that in a multi-armed-bandit test, *"[ε-greedy] (0.490
mean reward) loses to plain greedy (0.506), to UCB (0.531), and to Thompson
sampling (0.512) — and costs more regret (21.80 vs 13.68)."*

**Those numbers do not come from one table.** Reading the paper directly
(arXiv:2604.17244v2), the figures come from at least two different experimental
setups, spliced together:

**Table 1** — Llama-3.1 8B, 5-arm Bernoulli bandit, T=500:

| Method | Mean reward | Suffix failure freq. | Best-arm frac. | Cumulative regret |
|---|---|---|---|---|
| Reference (upper bound) | 0.564 | 0.011 | 0.824 | 17.637 |
| **DORA (λ schedule)** | 0.548 | 0.000 | 0.743 | 25.686 |
| UCB | 0.503 | 0.465 | 0.515 | 48.502 |
| TS | 0.509 | 0.230 | 0.550 | 44.998 |
| Greedy | 0.414 | 0.900 | 0.100 | 90.000 |
| **ε-greedy** | **0.414** | **0.900** | **0.100** | **90.000** |
| τ=0 | 0.414 | 0.900 | 0.100 | 90.000 |
| τ=0.7 | 0.422 | 0.850 | 0.131 | 90.000 |
| τ=1 | 0.518 | 0.000 | 0.675 | 86.900 |
| τ=1.5 | 0.484 | 0.000 | 0.698 | 37.160 |
| τ (exponential) | 0.538 | 0.000 | 0.703 | 28.730 |

**Table 9** — 9-arm instance, T=200: ε-greedy 0.335 reward with **0.950** suffix
failure frequency and **131.250** regret. DORA 0.510 / 0.050 / 45.900.

**The corrected finding is actually *stronger* than the one reported.** ε-greedy
scores **0.414 — identical to plain greedy** — with a **90% suffix failure
frequency**: in 90% of runs it locks onto a suboptimal arm and never recovers. On
the harder 9-arm instance it degrades to 0.335 reward and 131.25 regret, the worst
result in the table by a wide margin.

So the conclusion holds and the mechanism is clearer: **ε-greedy's randomness does
not produce useful exploration at the sequence level.** It randomises token choice,
not which action to take, so the model commits early and stays committed. The
paper's own framing: *"For τ ≤ 1, the model behaves overly greedily, committing
early to a suboptimal arm."*

**Why this correction is recorded rather than quietly fixed:** a claim assembled
from two tables reads as precise and is wrong in a way that changes the numbers a
reader would quote. This is the same failure mode as the citation audit — synthesis
quality and factual accuracy are independent.

---

## 1. Prospective memory — the strongest evidence in the whole set

**Mechanism, plainly.** Carrying out a deferred intention at the right future cue
while other work continues. Not "remembering" in the recall sense — *doing* at the
right moment.

**This is the one mechanism with a purpose-built LLM benchmark, and the numbers
verify verbatim against arXiv:2607.12385 (PM-Bench).**

- **PM-Bench** (arXiv:2607.12385, Liu & Gabriel, submitted 2026-07-14) models a
  simulated seven-day week. Agents must sustain an ongoing activity while deciding
  whether a deferred task is due. **The best method, a GPT-5.4 agent, reaches only
  65.1% Set-F1**, across eight models and eight configurations. The paper's own
  words: *"no single strategy for improving prospective memory dominates across
  models."*

**The intervention result is the important one** (arXiv:2609.01272, *Making
Prospective Memory SLM-Shaped: Typed Intention Stores for Small-Model Agents*,
2026-09-01):

| Configuration | PM-Bench Set-F1 |
|---|---|
| Best published scaffold (frontier model) | 65.1% |
| **Typed Intention Store (PIS)** — DeepSeek-Chat | **82.9%** |
| Gemma-E2B, no store | 4.2% |
| Gemma-E2B, seven retrospective memory methods | ≤6.6% |
| **Gemma-E2B + PIS** | **66.2%** |

The paper's argument: *"this loop is schema-constrained state tracking rather than
open-ended reasoning, and small models can execute it when the action space is
typed."* It puts **lifecycle logic in code** and scoped language work on the model.
Training-free, no fine-tuning.

**This is the single most actionable result in either stream**, and it is
independent of any brain analogy. Note the direction: a 2B model goes from 4.2% to
66.2% not by reasoning better but by *not being asked to reason*.

**The same benchmark shows the opposite intervention failing loudly:** a
multi-agent "monitor everything" design reached a **10.7%** cross-day hit rate with
**1,661 false-positive queries**. Forced auto-heartbeat polling **tripled cost and
lowered accuracy**. More monitoring is worse than none.

**Human evidence agrees, and adds a design rule.** External memory aids are the
strongest prospective-memory intervention (g = .805, meta-analytic), and offloading
helps **more when forced than when chosen** (Burnett & Richmond, *Memory &
Cognition*, 2025).

**Verdict: incorporate, as deterministic state with a typed action space.** Two
independent lines — a benchmark built for this exact skill, and a human
meta-analysis — point the same way. **Caveat: PM-Bench and the PIS result have no
independent replication.** The strongest human evidence is self-rated
methodologically weak.

---

## 2. Exploration — the clearest negative result, and it kills a popular idea

**Mechanism, plainly.** Trying alternatives instead of committing to the first
plausible action. Reinforcement learning's standard toolkit: ε-greedy (try
something random sometimes), UCB (try what looks under-explored), Thompson
sampling (sample from your uncertainty).

**Finding: for LLM agents, random exploration is worse than useless.** From the
verified tables above:

- **ε-greedy ties plain greedy** (0.414 reward) with a **90% failure-to-recover
  rate**. It is not a small penalty; it provides no benefit at all.
- On the harder instance it is the **worst method tested** — 0.335 reward, 131.25
  regret.
- **Temperature is not a substitute.** τ=0.7 reaches 0.422 with 85% suffix failure;
  only τ≥1.0 escapes, and τ=1 still carries 86.9 regret.
- The paper explains why: actions are chosen at the **sequence** level, but
  temperature randomises **tokens**. You get grammatical variety inside a
  committed plan, not a different plan.

**Deployment evidence agrees.** In costly coding-agent runs, roughly **half of file
actions are repeats of the same file**, and *"excessive cost is driven primarily by
redundant back-and-forth rather than increased task coverage"*
(arXiv:2604.22750).

**A learned novelty signal is worse still.** "The Dark Room in the Reward Channel"
(arXiv:2607.21273) shows that under group-normalised RL, a prediction-based reward
**destroys the policy**: across Qwen3-1.7B/4B/8B on ALFWorld, prediction accuracy
goes to 1.0 while **task success goes to 0** — the agent learns to predict its
environment perfectly while failing the task, an absorbing state the optimizer
builds by itself. The paper's conclusion: **the channel, not the content, decides
what works.** Removing only the std normalisation turns the same reward from 0% into
baseline parity.

**Verdict: reject random exploration and temperature-as-exploration. If exploration
is wanted, it must be at the action level and deterministic.** This bears directly on
the `valence_engine.curiosity` field identified in the coverage review — wiring that
field into action selection *as a randomiser* would import this exact failure.

---

## 3. Memory pruning — reject deletion, keep gating

**Mechanism, plainly.** Discarding memories that seem redundant or low-value, to
stay inside a budget.

**The evidence says deletion is mostly irreversible harm.** "What Eviction
Destroys" (arXiv:2609.08279) introduces a *restore counterfactual*: reinsert the
gold evidence after eviction, rerun the same reader, and classify each error as
recoverable, irreversible, or residual.

| Policy | Irreversible share of errors (80k budget, top-k) | At 8k budget |
|---|---|---|
| FIFO | 0.67–0.73 | **1.00** |
| random | 0.67–0.73 | **1.00** |
| redundancy-aware | 0.67–0.73 | **1.00** |
| LLM-importance | 0.60 | **1.00** |

**At a tight budget, every error is irreversible for all four policies.** And at
*matched accuracy*, no pruner is safer than any other.

**The constructive alternative is the same paper's companion result:** the best
pruning work (RD-Forget, arXiv:2609.10263) gains +8 to +19 points over ACE across
four models **by not deleting anything** — it keeps everything and gates at read
time.

**This project already has the "keep everything" half for free.** Git stores every
historical state with author and timestamp; `docs/VERSION-AGGREGATION.md` defines
deterministic aggregation. The finding says: **add the read-time gate, never the
deletion.**

**Verdict: reject deletion outright. Adopt read-time gating.** This is the clearest
case in the entire study where the evidence says the intuitive move (forget the
stale thing) is the destructive one.

---

## 4. Symbolic structure can destroy information — bears on the graph layer

**Finding.** On LongMemEval, graph-structured memory **loses** to a flat vector
store: F1 0.417 vs 0.468, 95% CI excluding zero. More damaging, judged correctness
on turn-recall collapses **0.911 → 0.607** with structure. The stated reason:
*"decomposing a turn into entities discards the surface form these questions
depend on."*

**This is directly relevant to this project's graph work.** The graph layer extracts
inferred relationships (`conceptually_related_to`, `semantically_similar_to`) from
documents. The finding does not say the graph is useless — it says **structure must
be added on top of raw text, never instead of it.**

Consistent with the graph substrate's existing standing: an index, never the system
of record. And with the extraction-gap finding: the graph is built from documents,
so the raw documents remain the ground truth.

**Verdict: keep raw text as the substrate; treat the graph as an index. Do not
decompose source records into entities as a storage strategy.**

---

## 5. Abstention is a two-sided metric or it is not a metric

**Finding.** XSTest (NAACL 2024) measured **38% full refusal on safe prompts** for
Llama-2 with its system prompt. Adding a guardrail prompt did not fix it — it traded
unsafe compliance for over-refusal.

BLINDSPOT (arXiv:2609.16305) shows Claude Opus 4.6 reaching 4% unsafe completion
**by completing only 74% of matched safe twins** — i.e. the safety gain was bought
with a large capability loss, and the headline number alone hides it.

Meanwhile "Language Models (Mostly) Know What They Know" found that adding a
"none of the above" option **reduced** accuracy and calibration, and that
self-knowledge does not calibrate out of distribution.

**Verdict: any abstention mechanism must be evaluated on both axes — unsafe
compliance and safe-prompt completion — or its number is uninterpretable.** A single
refusal percentage is not a measurement.

---

## 6. Neuromodulation — dead end as a principle, confirmed

**Verdict: reject as a design principle.** The evidence is thin and the one
benchmarked implementation is self-serving:

- **D-MEM** (arXiv:2603.14597) invents its own benchmark, and its own ablations show
  the bio-inspired signal is **not the load-bearing part** — the winning variant is
  the one with BM25 and a fallback buffer bolted on.
- The other "neuromodulation" papers are either non-LLM physics (arXiv:2512.13859)
  or a scalar conditioning variable evaluated by a **24-example, single-annotator**
  human study (arXiv:2604.01576).

**What *is* independently supported is a boring deterministic novelty counter** —
and in that same paper the reward-driven alternative *"did not improve the tested
primary outcomes"* over the reward-free one.

**This confirms the architecture document's existing "no benchmark evidence" marking
rather than overturning it.** A named brain chemical is not a mechanism.

---

## 7. Cerebellum-analog error correction — the best value-per-effort bet

**Mechanism, plainly.** Before acting, predict the outcome; after acting, compare
prediction to reality; store the residual. The cerebellum does this continuously
and very fast.

**The strongest available result** is not evidence that brain-like implementation is
required — it is evidence for **prediction → external verification → structured
residual → bounded correction**. That is ordinary software: assert, observe, diff,
record.

**Honest status: the evidence is strongest for tool-grounded correction, and this is
a pilot bet, not a proven win.** The strong human evidence concerns motor timing,
which is not obviously the same problem as a tool call returning an unexpected
shape.

---

## 8. Deferred, with reasons

| Mechanism | Why deferred |
|---|---|
| **Predictive processing / active inference** as a general agent architecture | RL and robotics evidence, but no convincing direct LLM-agent benchmark showing advantage. Most likely of all candidates to be elaborate and inert. |
| **Interleaving / desirable difficulty** | Cepeda et al.'s meta-analysis plus a randomized classroom trial — strong in humans, **no direct replicated LLM-agent evidence found.** Importing it would repeat the exact pattern that burned this project with ToM. |
| **Offline consolidation** (as distinct from gating) | Genuinely promising — replace, deduplicate, abstract, version, prune safely. But the pruning half is contradicted by §3, and `replay.py` currently selects episodes and marks them replayed without substantive consolidation. Worth revisiting with read-time gating in place. |
| **Curiosity / information gain** | Credible in RL, promising in LLM *training*, weak at *runtime*. Raw novelty is vulnerable to the "noisy television" problem and task drift. See §2 — a learned novelty signal collapsed agents to 0% task success. |

---

## The cross-cutting lesson

Across eleven mechanisms, the pattern is consistent and it is not what a
"biologically inspired" architecture usually claims:

> **Deterministic code should own state, lifecycle, counting, and timing. The model
> should own language.**

The largest measured effects all point the same way:

- Lifecycle in code: 65.1% → 82.9% on prospective memory
- Gating at read time instead of deleting: +8 to +19 points, and it is the only
  variant that is not irreversible
- Rejecting random exploration: ε-greedy provides **zero** benefit over greedy and
  fails to recover 90% of the time
- A learned novelty reward: task success **0%**

**Human cognitive findings transfer here as *what to measure*, not as *what improves
an agent*.** The ToM result in this project's own evidence — 0.0% Pass^3 across
seven frontier models — is the clearest example of a robust human finding becoming
an active liability.

**The honest framing for a biologically inspired architecture:** the brain is a
source of *hypotheses about what to measure*. Where a hypothesis has been tested on
agents, the brain-shaped version usually loses to the boring deterministic one. That
is worth stating plainly rather than resolving in favour of the analogy.

## Which claims were verified at source, and which were not

Stated explicitly because the citation audit showed why it matters.

**Read from the paper or abstract directly this session:**

- **arXiv:2607.12385** (PM-Bench) — the 65.1% Set-F1 ceiling and the "no single
  strategy dominates" claim, verified against the abstract verbatim.
- **arXiv:2609.01272** (typed intention store) — 82.9%, 4.2% → 66.2%, and the
  ≤6.6% seven-methods figure, verified against the abstract verbatim.
- **arXiv:2604.17244** (DORA Explorer) — the full Table 1 and Table 9 numbers read
  out of the HTML, which is what caught the spliced-table error above.
- **arXiv:2609.08279** (eviction audit) — the 0.67–0.73 irreversible share and the
  1.00 figure at 8k, verified against the abstract.
- **arXiv:2607.21273** (dark room) — the collapse to 0% task success and the
  std-normalisation ablation, verified against the abstract.

**Taken from the research reports and not independently re-verified:**

- `2609.10263` (RD-Forget, +8 to +19 points)
- `2604.22750` (repeated file actions, ~50%)
- `2609.16305` (BLINDSPOT, 4% / 74%)
- `2603.14597`, `2604.01576`, `2512.13859` (neuromodulation)
- `2607.12385`'s companion "monitor everything" failure (10.7%, 1,661 false
  positives) — the abstract does not contain these figures
- The LongMemEval graph-vs-flat result (0.417 vs 0.468, 0.911 → 0.607)
- XSTest's 38% safe-prompt refusal figure

These are plausible and internally consistent, and they are marked as report-sourced
rather than presented as verified. Anyone relying on one should read the paper.

## Evidence-quality caveat, stated once and applying throughout

Four of the strongest results above are **2025–26 preprints on author-built
benchmarks**, with no independent replication. PM-Bench, the typed-store result, the
eviction audit, and the dark-room result are all recent and unreplicated. The
human-subject literature is better established but its transfer to agents is
unestablished. Treat this document as a map of where to measure, not as a set of
settled facts.


---

## Addendum: the project's own graph layer, measured

The evidence above says deterministic retrieval beats clever structure. The
project's own graph layer has now been measured against that standard, and it
**fails it**:

| Strategy | recall@10 |
|---|---|
| keyword only | 0.792 |
| graph only | 0.083 |
| fused | 0.708 |

This is the cross-cutting principle turning back on the project itself. The graph
is built by an LLM reading documents — the expensive, clever part — and then
queried by a deterministic walk, which is the part the evidence endorses. But the
deterministic walk is optimising for the wrong target: it ranks concept nodes,
because that is what a query's words match, and the document a person wants is a
*sink* in the citation graph with nothing pointing back at it.

**A structure can be principled, expensive to build, and still lose to the boring
option.** The honest reading is that document nodes need to be first-class in the
walk, not that the graph should be abandoned.

Full numbers, mechanism, and reproduction in
`RETRIEVAL-QUALITY-MEASUREMENT.md`.
