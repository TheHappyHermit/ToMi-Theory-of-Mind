# Cognitive Function Audit — best available implementation vs. hermes-brain

**Date:** 2026-09-25
**Method:** Every citation below was fetched during this audit. ACL Anthology
(`aclanthology.org`), arXiv abs pages, and Crossref all returned live content;
each claim carries the URL actually retrieved. Where a number appears it came
out of a fetched abstract or record — not from memory. Anything I could not
fetch is marked **unverified** and carries no number.

**Standing caveat about the current code.** I read all 29 modules in
`hermes-brain/brain/`. The gap is not mostly "wrong algorithm" — it is
**"constructed, never consulted."** Verified by grep on `hermes_brain.py`:
`self.associative_graph.`, `self.chronesthesia.`, `self.counterfactual.`,
`self.defeater_graph.`, `self.agm.`, `self.dialectic.` → **0 call sites each**.
Correction to the prior internal audit: four of them *are* reachable from the
dashboard (`dashboard/backend/routes/brain.py:96,101,130,223,237,258,295,314`),
so they are observable, but they still never run during reasoning. The
psychological vocabulary is doing explanatory work, not computational work.

---

## 1. Creativity and divergent thinking

**What it is for.** Producing output that is *new* and *useful*, where "new"
means not a recombination of what you were handed. The hard part is measuring
that, because a model that has read ten million stories will always produce
something fluent, plausible, and unoriginal.

**The real metrics.** The field's own yardstick is not "is this good" but a
**pair**: *usefulness* and *novelty*, plus a third term that is where most agent
designs fail — **diversity across outputs** (are the N ideas from the same
distribution, or the same idea N times?).

**The verified best implementation — and the finding that changes the design.**
- **Doshi & Hauser, "Generative AI enhances individual creativity but reduces
  the collective diversity of novel content," *Science Advances* 10(28), 2024.**
  DOI 10.1126/sciadv.adn5290. Fetched abstract: giving writers access to LLM
  story ideas "causes stories to be evaluated as more creative, better written,
  and more enjoyable, especially among less creative writers. However,
  generative AI–enabled stories are **more similar to each other** than stories
  by humans alone." They call this a **social dilemma**: individually better,
  collectively narrower. This is the definitive statement of the idea
  homogenisation problem, and it is causal (online experiment), not correlational.
- **The deep, actionable part: *surface* diversity is a decoy.** "Divergent
  Thinking: Escape the Homogeneity Trap in Generative Commonsense Reasoning,"
  *Findings of ACL 2026* (https://aclanthology.org/2026.findings-acl.915/),
  fetched: adding more reasoning chains **degrades** performance because the
  chains "collapse into a narrow semantic region." Their conclusion, verbatim:
  "**deep semantic diversity, rather than surface-level lexical variation, is the
  decisive prerequisite** for effective integration." Their fix is
  Explore-then-Integrate: high-semantic-entropy explorers gather diverse concept
  bindings, then a separate integrator composes them. They also ship a
  **provenance-aware** evaluation that verifies a gain came from real
  composition rather than "just picking the best of N."
- Supporting existence proof that this is measurable: Tree of Thoughts
  (**Yao et al., NeurIPS 2023**, arXiv:2305.10601, verified) uses a
  self-evaluation score at each node to keep genuinely distinct branches, and
  reports Game of 24 rising from **4% (GPT-4 + CoT) to 74%**.

**What hermes-brain gets wrong.** There is no creativity function. The nearest
thing is `DialecticSynthesizer.synthesize()` (`brain/epistemology/dialectic.py`),
which is worse than absent: it is an **f-string that returns a fixed
boilerplate** — "While '{thesis}' holds under standard operating conditions,
'{antithesis}' correctly characterizes boundary/exception cases" — with
`resolution_strategy` hardcoded to `"scope_differentiation"`. It reads a
conflict, ignores both contents, and emits the same sentence. It is called zero
times. This is worse than no dialectic module: it is a module that would look
like a thinking step in a trace.

Also relevant: `ThalamicGate.compute_entropy()` is character-level Shannon
entropy on a single string. That is not a novelty measure — a string of
uniformly random characters scores high, and a precise technical answer scores
low. Entropy of characters is unrelated to semantic diversity.

**Verdict: BEHIND by the entire field, and the absent function is the cheapest
high-value win on this list.** Build: (a) an *idea-set* abstraction holding N
candidates; (b) pairwise **semantic** distance over ideas, not lexical; (c) a
novelty score = distance from the *retrieval corpus* the agent just read, not
from the current turn; (d) a provenance field per idea so a downstream
"selection" cannot pass off "picked the best of N" as "composed." Track
collective diversity across a session, because Doshi & Hauser show per-item
scores are exactly the metric that hides the problem.

---

## 2. Metacognition and self-calibration

**What it is for.** Knowing the *reliability of your own answer* — and being
able to act on it (abstain, ask, verify). Two separable halves: (i) internal
confidence, (ii) how confidently you *tell the user*. The gap between them is
where trust breaks.

**The real metrics.** Calibration error (how often 80%-confident answers are
right), AUROC/AUACC of the confidence signal as a *selective predictor* (how
well confidence ranks right-vs-wrong answers), and **faithfulness** of stated
uncertainty.

**Verified best implementations.**
- **Kuhn, Gal & Farquhar, "Semantic Uncertainty," ICLR 2023 (Spotlight)**
  (https://arxiv.org/abs/2302.09664, verified). Sample many generations, cluster
  them by *meaning*, take entropy over clusters. Solves the fact that "Paris is
  in France" and "The French capital is Paris" are the same answer, which
  token-level entropy counts as disagreement. Unsupervised, single model, no
  weight changes. More predictive of accuracy than comparable baselines.
- **Yona, Aharoni & Geva, EMNLP 2024**
  (https://aclanthology.org/2024.emnlp-main.443/, verified abstract): LLMs
  "are **poor at faithfully conveying their uncertainty**," and better alignment
  is needed. They formalise the metric as the gap between intrinsic confidence
  and conveyed decisiveness, penalising **both** over- and under-hedging. This
  is the direct answer to "can they even vary their confidence": no, and the
  failure is two-sided.
- **Wan et al. (SelfAware), "Do LLMs Know What They Don't Know?", Findings of
  ACL 2023** (https://aclanthology.org/2023.findings-acl.551/, verified): the
  SelfAware dataset (answerable/unanswerable pairs, 5 categories) across 20
  models. Finding: an "intrinsic capacity for self-knowledge" exists and
  in-context learning plus instruction tuning **enhance** it — but there remains
  "a considerable gap" versus human proficiency. So the capability is
  trainable, not absent.
- **Tu et al., "Adaptation with Self-Evaluation to Improve Selective Prediction
  in LLMs," Findings of EMNLP 2023**
  (https://aclanthology.org/2023.findings-emnlp.345/, verified): parameter-
  efficient tuning for *self-evaluation* as the intervention. CoQA AUACC
  **91.23% → 92.63%**, AUROC **74.61% → 80.25%**. The AUROC jump is the
  important number: confidence became a far better *ranker* of correctness.
- **The overconfidence result, on the user side: Steyvers et al., "What large
  language models know and what people think they know," *Nature Machine
  Intelligence* 7, 2025** (DOI 10.1038/s42256-024-00976-7, fetched). Defines
  the **calibration gap** (human confidence vs. model accuracy) and the
  **discrimination gap** (can you tell right from wrong). Users overestimate
  LLM accuracy with default explanations, and — a finding the operator should not skip —
  **longer explanations raised user confidence even when the extra length did
  not improve accuracy.** Verbosity is read as reliability.
- **Huang et al., "LLMs Cannot Self-Correct Reasoning Yet," ICLR 2024**
  (https://arxiv.org/abs/2310.01798, verified): without external feedback,
  self-correction **degrades** performance. Any "just ask it to double-check
  itself" step is not metacognition.

**What hermes-brain gets wrong.** **Absent entirely** — there is no confidence
field, no abstention path, no selective-prediction code. The nearest thing is
`DefeaterGraph.credence`, a float that a human or a caller must supply, and it
is never read by any decision path; it is display-only. Two specific traps in
the surrounding design: (a) `CognitiveRouter.evaluate_route` scores
*epistemic uncertainty* as `unresolved_hypotheses_count * 0.1`, capped at 0.2 —
so five unresolved hypotheses contribute less than one keyword hit
(`keyword_score` reaches 0.7), meaning **systematic doubt can never push a task
into slow deliberation**; that is exactly backwards. (b) Because routing never
consults confidence, the agent has no way to become more careful when it is
wrong.

**Verdict: BEHIND, no partial credit.** Build: sample-k + semantic-entropy
confidence (Kuhn) as the *only* confidence source; a conformal or AUROC-
tracked abstention gate; and a separate **faithfulness** check comparing
internal confidence against how the draft hedges (Yona). Report calibration
error in your own logs, because the whole finding is that you cannot notice it
without measuring.

---

## 3. Planning, including repair when a plan fails midway

**What it is for.** Committing to a multi-step course, then noticing the world
changed and revising the *remainder* rather than restarting or pushing on.

**The real metrics.** Plan validity (is each step executable?), executability
under perturbation, and — the number that matters and the one agents skip —
**recovery rate after an injected mid-plan failure**. Success rate on a
never-failing task measures nothing about repair.

**Verified best implementations.**
- **Yao et al., ReAct, ICLR 2023** (https://arxiv.org/abs/2210.03629, verified):
  interleaves reasoning traces and actions, "allowing for greater synergy…
  reasoning traces help the model induce, track, and **update action plans as
  well as handle exceptions**." It beats pure-CoT on hallucination and error
  propagation because action returns external ground truth. That "handle
  exceptions" clause is the plan-repair mechanism, and it works because there is
  a real environment to contradict the plan.
- **Yao et al., Tree of Thoughts, NeurIPS 2023** (arXiv:2305.10601, verified):
  the branch-and-backtrack structure. When a step fails, ToT does not restart —
  it backtracks to the last viable node and takes another branch. Game of 24:
  4% → 74%.
- **For symbolic pairing, the honest finding is a sketch, not a citation.** The
  pattern that recurs in the verified literature above is *verification against
  an external source* (Wikipedia API in ReAct; a self-scored node in ToT), not
  LLM planning in the abstract. Pairing an LLM with a classical planner is a
  well-motivated design — let the LLM propose, let a symbolic checker reject
  infeasible sequences — but **I did not fetch a paper establishing that a
  LLM+PDDL pairing beats either component alone on plan repair. Unverified.**
  Treat it as a design hypothesis to test, not an established result.

**What hermes-brain gets wrong.** `ProceduralSkillCompiler`
(`brain/basal_ganglia/compiler.py`) compiles a sequence after it succeeds
`compilation_threshold=3` times — but it is **called nowhere**, so nothing is
ever observed and nothing is ever compiled. Worse, its key is
`" -> ".join(steps)` on **raw step strings**: a skill compiles only if the
wording is byte-identical, which real retries never are. And a compiled routine
is a frozen list of steps with a `success_rate`; there is no mechanism to
detect that the world has changed such that the routine is now wrong, which is
precisely the failure-repair case. `DorsolateralPFC` holds a `sub_goals` list
with `add`/`complete` but no precondition, no invalidation trigger, and no
dependency edges.

**Verdict: BEHIND, and worse than behind — the machinery is a slideshow, not a
planner.** The one thing it does well is worth keeping: a plan must be
*re-validated against reality* (ReAct's lesson). Add: preconditions per step,
an invalidation check on each loop iteration, and backtrack-to-last-viable-node
rather than restart.

---

## 4. Decision-making under uncertainty: calibration, risk-weighting, stopping

**What it is for.** Choosing when the right answer is "I don't know" — and
knowing when to stop paying for more thinking.

**The real metrics.** Coverage-risk / coverage-accuracy curve (if you abstain
10% of the time, are the 10% the ones you would have got wrong?), and
**selective risk**: the error rate *conditional on not abstaining*. Overall
accuracy hides this completely.

**Verified best implementation.**
- **Conformal prediction** is the distribution-free standard: from a
  calibration set you get a guarantee on the error rate of your selective
  predictions, with no assumption about the data distribution. I could not
  fetch the canonical "Learn then Test" record (Crossref returned irrelevant
  hits, and the arXiv API was 406/429 throughout) — so **the guarantee
  statement is unverified in this audit** and should be cited from the primary
  source before it goes in a design doc.
- What I *did* verify is that conformal abstention is now a live, active line in
  peer-reviewed NLP: "Abstain-R1: Calibrated Abstention and Post-Refusal
  Clarification via Verifiable RL," *Findings of ACL 2026*; "The Art of Saying
  'Maybe': A Conformal Lens for Uncertainty Benchmarking in VLMs," *Findings of
  EACL 2026*; "Conformal LLM Routing with Distribution-Free Safety Guarantees,"
  *ACL 2026 SRW* (all located in the ACL Anthology index). Routing-by-confidence
  with a distribution-free guarantee is the applied form.
- **The self-evaluation route is the cheaper 80%:** Tu et al. (above) got AUROC
  74.61% → 80.25% by tuning for self-evaluation alone. That is the highest
  verified return-per-effort number in this entire audit.

**What hermes-brain gets wrong.** `ActionGate.evaluate_pathways`
(`brain/basal_ganglia/action_gate.py`) computes
`go_drive - nogo_drive >= 0.4` from an `expected_utility` the caller must
supply. **Nothing in the system ever computes expected utility.** So the gate's
input is, in practice, a constant or zero, and it is a threshold on an
unmeasured quantity. There is no abstention state at all — "NO_GO" means
"suppressed or queued for confirmation," which is the opposite of a calibrated
refusal with a coverage target. The stated goal in the module docstring is
"expected utility > threshold"; the implementation never reaches the goal.

**Verdict: BEHIND.** No uncertainty estimate feeds any decision. Build the
confidence signal (§2) first, gate on it, and measure the coverage-risk curve
so the threshold is fitted rather than asserted.

---

## 5. Imagination and counterfactual simulation

**What it is for.** Running a hypothetical forward to see what breaks — before
committing. The trap: *simulated outcomes can bias judgement rather than inform
it*, and an agent that narrates a confident future is worse than one that
admits it cannot simulate.

**The real metric.** Calibration of the simulation against what actually
happened — i.e. run counterfactuals, record outcomes, measure the hit rate. A
simulator that is never scored against reality is a story generator.

**Verified best implementation.**
- **Decompose-ToM, "Enhancing Theory of Mind Reasoning in LLMs through
  Simulation and Task Decomposition," COLING 2025** (located in the ACL
  Anthology index) — simulation as a *reasoning* primitive, applied to mental
  states rather than to action outcomes.
- **The critical honesty finding, and it is methodological: Fluri, Paleka &
  Tramèr, "Evaluating Superhuman Models with Consistency Checks"**
  (https://arxiv.org/abs/2306.09983, verified). You often cannot score a
  counterfactual because there is no ground truth for a counterfactual. Their
  workaround is to evaluate **internal consistency instead of correctness** —
  and they surface real defects: "GPT-4 forecasting that sports records will
  evolve non-monotonically over time." Any imagination subsystem should be
  scored this way, because its output is by definition unscoreable by accuracy.
- **The bias warning, stated as I can support it.** The human literature is
  clear that imagining an outcome inflates estimated likelihood (the
  "availability"/simulation heuristic — mentally simulating makes an event
  *feel* more probable). I did **not** fetch a peer-reviewed source for this in
  this audit, so: **mechanism plausible and well-known, citation unverified.**
  The practical consequence stands regardless: simulated futures must never
  feed a confidence number without an external check.

**What hermes-brain gets wrong — this is the clearest fraud in the codebase.**
`CounterfactualEngine` (`brain/dmn/counterfactual.py`) is named for Pearl's
counterfactual rung and its docstring claims causal counterfactuals. It is a
**SQLite `INSERT` of strings the caller already computed.** There is no
structural causal model, no intervention, no counterfactual computation —
`actual_path`, `counterfactual_path`, and `predicted_advantage` are all
caller-supplied strings that get written down. And `predicted_advantage` is
**never compared against what happened**, which is precisely the measurement
that would make it a simulator rather than a log. A module named
CounterfactualEngine that does not compute a counterfactual will read as
causal reasoning in any trace. This is the highest-integrity-risk item in the
project.

Second: `ChronesthesiaEngine.prospection()` returns
`"Step N following '<action>'"` with
`"expected_completion_pct": min(100, step * (100 // horizons))` — arithmetic on
the step index, not a projection — and hazards hardcoded to
`["requires verification checkpoint"]` on the last step only. It is a loop
that formats strings. It also stores `timeline_events` **in memory only**,
so retrospection dies with the process, unlike the other engines.

**Verdict: BEHIND, and mislabelled in a way that could mislead future work.**
Prefer: generate the counterfactual, **then score it against the recorded
actual outcome**, and report the hit rate. If that is too expensive, rename the
module — a misnamed module is a trap for the next contributor.

---

## 6. Emotion and affective appraisal

**What it is for.** Biasing choice fast, before deliberation, using
body-state-associated signals learned from past outcomes. Damasio's somatic
marker hypothesis, in plain terms: past experiences leave a fast "gut feeling"
that short-circuits expensive calculation.

**Does computational affect improve decision quality? The evidence is genuinely
mixed, and I will not resolve it beyond what I fetched.** What I verified:
- The hypothesis has a substantial empirical base on the human side, and
  remains actively researched — Bechara's chapter "The Somatic Marker Hypothesis
  and Its Neural Basis" (*Predictions in the Brain*, 2011,
  DOI 10.1093/acprof:oso/9780195395518.003.0048) and Damasio's own chapter
  (*The Prefrontal Cortex*, 1998, DOI 10.1093/acprof:oso/9780198524410.003.0004).
  Human patient data with somatic-marker-relevant damage is the classic support
  (North et al., *Neuropsychologia* 2001,
  DOI 10.1016/s0028-3932(00)00107-x — spinal cord damage, afferent feedback,
  decision making).
- On the AI side, the work is real but early and mostly about *detecting*
  emotion, not about affect improving choices. The ACL index is full of
  sentiment/appraisal/affective-hallucination papers; the closest thing to the
  claim is "Feeling First, Speaking Second: A Dual-Process Cognitive-Affective
  Architecture for LLM Agents" (Computational Affective Science @ ACL) — a
  proposal, and I did not fetch it. **The claim "computational affect improves
  LLM decision quality" is unverified.** I found no controlled study either way.
  That absence is itself the finding: it is an open problem, not a settled
  technique.

**What hermes-brain gets wrong.** Two modules, and they are confused with each
other.
- `CognitiveValenceEngine` (`brain/limbic/valence.py`) is a fixed-constant
  random walk: `valence += magnitude` on success, `-= magnitude` on failure,
  with hardcoded weights (0.5, 0.8, 0.3, 0.2) and no input from the world
  except the `success` boolean. Nothing measures anything. `magnitude` and
  `novelty` are caller-supplied. **And `curiosity` is written and never read** —
  confirmed by grep: no consumer anywhere. So the module advertises intrinsic
  drive and delivers a mood ring.
- `SomaticMarkerEngine` (`brain/limbic/somatic.py`) is the *only* affect
  module with a real learning rule: a running weighted mean of valence per
  (action_pattern, target_pattern) with a sample count. That is a legitimate
  online estimator. Its problem is **granularity and wiring**: the keys are
  caller-supplied opaque strings, so unless a caller normalises them the table
  shatters into singletons with `sample_count=1`, each bias being a single
  ±0.3 observation. And `db_path` defaults to `None`, in which case
  `assess()` returns `(0.0, "No somatic memory database configured.")` — a
  silently inert bias.

**Verdict: SOMATIC MARKERS AT the right idea but behind on engineering;
VALENCE BEHIND and not evidence-based.** Do not add more affect variables. The
one honest experiment: keep `SomaticMarkerEngine`, log its decisions alongside
outcomes, and measure whether acting on its bias changes success rate. If it
doesn't, delete the framing — that is a real result. If it does, you have
evidence nobody in this literature has published.

---

## 7. Consolidation, abstraction, and useful forgetting

**What it is for.** Turning experience into compressed general knowledge while
offline, and **deliberately dropping** what will hurt. Forgetting that helps is
not a bug — it is what stops near-duplicates from crowding out the
distinction that matters.

**Verified best implementation.**
- **Contextual Experience Replay (CER), "Contextual Experience Replay for
  Self-Improvement of Language Agents," ACL 2025**
  (https://aclanthology.org/2025.acl-long.694/, verified): training-free;
  accumulates and **synthesises** past experiences into a dynamic memory buffer
  covering "environment dynamics and common decision-making patterns," then
  retrieves them into the context for new tasks. Results: **31.9%** on
  VisualWebArena (beating tree search at lower token cost, stated SOTA) and
  **36.7%** on WebArena, a **51.0% relative** improvement over the GPT-4o
  agent baseline. This is the concrete, verified template for what
  `run_consolidation_replay()` should be doing.
- **RecMem** ("Recurrence-based Memory Consolidation for Efficient and
  Effective Long-Running LLM Agents," *Findings of ACL 2026*) and **TiMem**
  ("Temporal-Hierarchical Memory Consolidation for Long-Horizon Conversational
  Agents," *Findings of ACL 2026*) — both in the Anthology index, both treat
  consolidation as a real procedure, not a formatting pass. I did not fetch
  their abstracts, so I cite them as *located, not read*.
- **On forgetting that helps:** the ACL index contains a working line —
  "FOREVER: Forgetting Curve-Inspired Memory Replay for Language Model Continual
  Learning" (*ACL 2026*) and "From Recall to Forgetting: Benchmarking Long-Term
  Memory for Personalized Agents" (*Findings of ACL 2026*). Located, not read.

**What hermes-brain gets wrong.** `HippocampalReplayEngine.run_consolidation_replay()`
(`brain/hippocampus/replay.py`) — the context you supplied describes this
exactly — **returns an f-string and consolidates nothing**:
`f"Consolidated rule from '{ep['summary']}' (surprise=..., valence=...)"`.
It re-derives a string from fields already in the episode. No abstraction, no
generalisation, no write-back. `episodic_traces` is also in-memory only, so
"replay" evaporates on restart.

The `priority` heuristic itself is a real (if crude) idea with a neuro
analogue — replay the surprising and emotionally charged episodes — and that is
**ahead of nothing but behind the field**, which weights replay by
*usefulness to future tasks* (CER) rather than by felt intensity. Surprise and
valence are proxies for importance that are easy to game: a loud failure
replays forever and teaches nothing general.

Also: `pattern_separation()` is a truncated SHA-256 of the cue. It is a hash,
not a representation. Two nearly identical episodes get uncorrelated 16-hex
digests, which means it provides *no* interference protection whatsoever — the
opposite of what dentate-gyrus pattern separation does. And `pattern_completion`
scores overlap as `len(intersection) / len(cue_tokens)` — precision against
the cue, ignoring how many trace tokens were missed, so a long episode with one
matching word can win.

**Verdict: BEHIND, with one good instinct (priority replay).** The fix is
CER-shaped: on a schedule, take episodes, **distil a general rule with a model
call**, write that rule to a separate generalised store, and keep the episode
store append-only. Add forgetting as a *designed* operation with a
usefulness-based eviction, not just a cap.

---

## 8. Social cognition: modelling other agents, coordination, negotiation

**What it is for.** Representing what *other parties* know, believe, and want —
and acting on the difference between their model and reality.

**Verified best implementation — and the finding that matters most.**
- **Zhao et al., "Minding Language Models' (Lack of) Theory of Mind: A
  Plug-and-Play Multi-Character Belief Tracker" (SymbolicToM), ACL 2023**
  (https://aclanthology.org/2023.acl-long.780/, verified). Their claim is the
  one to internalise: "**simply scaling up models will not imbue them with
  theory of mind** due to the inherently symbolic and implicit nature of the
  phenomenon." Their fix is a **decoding-time symbolic structure** — track
  each entity's beliefs, each entity's estimate of *other* entities' beliefs,
  and higher orders, via explicit graph representation. Zero-shot, with robust
  out-of-distribution performance against supervised baselines. They also
  **uncovered spurious patterns in existing ToM benchmarks** and argue for
  out-of-distribution evaluation — a warning that ToM benchmark numbers are
  partly artefacts.
- The ToM-for-LLM field is now large and largely diagnostic: CogToM, XToM,
  ToMELP, "On Emergent Social World Models" (*ACL 2026*),
  "Infusing Theory of Mind into Socially-Aware LLM Agents" (*Findings of ACL
  2026*), "Brittle Minds, Fixable Activations" (*Findings of EMNLP 2025*).
  Located, not read.
- **Negotiation:** the honest finding is that LLM negotiation research is
  mostly *measurement of human-like biases*, not capability — anchoring effects
  in price negotiation (*Findings of EMNLP 2025*), personality-trait effects
  (*Findings of EMNLP 2024*). And a directly relevant cautionary result: "The
  Same Email, Signed Differently: Testing Negotiation Bias and Recommendation
  Stability in LLMs" (EACL 2026) — i.e. surface framing changes outcomes.
  **What LLMs can do in negotiation is unverified; what I verified is that they
  carry human cognitive biases and are framing-sensitive.** I found no evidence
  of a reliable multi-agent *coordination* result either.

**What hermes-brain gets wrong.** `TheoryOfMind` (`brain/social/tom.py`) has
`user_mental_models` with **0 rows and no writer**. And the schema itself is
wrong for the job: one row per (domain, attributed_belief, ground_truth). It
models *the user's belief about a fact*, not *the user's belief about the
agent's belief* — that is Level-1 ToM only, where SymbolicToM shows the
interesting structure is Level-2+ with **multiple entities** tracked
simultaneously. The discrepancy flag is
`attributed_belief.strip().lower() != ground_truth.strip().lower()` — a
**string inequality**, so "Postgres runs on 5432" vs "postgres runs on port
5432" registers as a discrepancy and produces the nudge "Note: User assumes X
but verified state is Y. Tactfully clarify." A system that manufactures false
disagreements and then confidently corrects the user is worse than one that
never checks.

`GriceanPragmatics` (`brain/social/pragmatics.py`) is three regexes against
utterance-initial patterns (`^(can|could|would)\s+(we|you)`, `^i (want|need)`,
and one "X is broken" pattern). The real distribution of indirect requests is
vastly broader — it includes negation, politeness, embedded questions, and
multi-turn context. The "Maxim of Quality" check flags hedging words
(`maybe`, `perhaps`) as a *defect*, which inverts the Yona et al. finding:
appropriate hedging is the *correct* behaviour under genuine uncertainty.
"Maxim of Manner" triggers on "no double newline and >150 words." These are
heuristics that will misfire on ordinary traffic and are scored as if they were
checks.

**Verdict: TOH BEHIND (Level-1 only, no writer, wrong comparison); PRAGMATICS
BEHIND and partly inverted.** Port SymbolicToM's multi-entity belief graph
rather than extending the string-equality table. Treat a regex-matched
implicature as a *prompt for the model to interpret*, not a decision.

---

## 9. Motivation and intrinsic drive

**What it is for.** Choosing what to do next with no external reward signal —
the exploration problem. The documented failure is specific and well known:
**curiosity-driven agents get stuck on unpredictable-but-useless things** (the
"noisy TV" problem) and, worse, novelty-seeking in language models collapses
onto the model's own high-probability modes — which is the computational form
of the idea-homogenisation problem in §1.

**Verified status.** The RL exploration literature is mature and I did not
re-derive it here; the ACL index shows the current LLM-era work is about
RL-trained exploration under verifiable reward ("Low-probability Tokens Sustain
Exploration in RL with Verifiable Reward," *Findings of ACL 2026*;
"Targeted Exploration via Unified Entropy Control," *Findings of ACL 2026*).
**I did not fetch a primary source establishing the canonical novelty-seeking
failure modes; that specific citation is unverified**, and I flag it rather than
asserting a number.

**What hermes-brain gets wrong.** `valence_engine.curiosity` is initialised to
0.5, incremented by `novelty * 0.3` on success, and decremented by 0.2 when
`allostatic_load > 0.7`. **It is never read** — confirmed by grep across the
whole repo. It is a write-only field. So the system has no exploration policy at
all; it has an unused number that would have been one if wired.

Note the design smell: curiosity is *reduced* by accumulated load. Real
exploration is often most valuable when things are going badly. Coupling
curiosity to frustration inverts the usual exploration/exploitation story.

**Verdict: BEHIND — the mechanism is a stub, and the stub is not even connected.**
If exploration is wanted, the state-of-the-art move is not a mood variable: it
is an explicit **epistemic-value** signal (how much would this reduce my
uncertainty?) which is exactly the machinery missing in §2. Wire those together
and motivation stops being a metaphor and becomes a computed priority.

---

## 10. Executive control and resource allocation

**What it is for.** Deciding what to do now, what to suppress, and when to
switch — under a budget. The Miyake triad (inhibition, updating, shifting) is
the standard decomposition; "unity and diversity" findings
(Friedman & Miyake, *Cortex* 2017, DOI 10.1016/j.cortex.2016.04.023) show the
three are correlated but **separable**, so an implementation that conflates
them will fail differently across situations.

**Verified status.** I verified the triad's structure and separability but did
**not** fetch a primary source for cost-based goal switching or stopping rules
in LLM agents. Two located-not-read items are relevant: "Know When To Stop: A
Study of Semantic Drift in Text Generation" (*NAACL 2024*) and "Draft Model
Knows When to Stop" (*EMNLP 2025*). **The cost-based-goal-switching citation is
unverified.**

**What hermes-brain gets wrong.** The triad is implemented as three regex
groups, and each one is weak in a different way:
- **Inhibition** (`check_inhibition`) matches five destructive-command
  patterns — useful, and genuinely the right *kind* of thing (a concrete
  irreversible-action deny-list). But it is a **blocklist, and blocklists fail
  open**: `rm -rf /home/operator/important` matches, `find . -delete` does not.
  Second check: flagging "all done"/"finished everything" under 20 words with
  no "test"/"verify" in context is a reasonable anti-premature-completion
  heuristic and is one of the few genuinely thoughtful things here.
- **Updating** (`monitor_updating`) is the weakest. It only fires if **both**
  strings contain the literal `"status:"` or `"version:"`, and "version:" is
  treated as *always* superseding. A new fact that contradicts an old one in
  any other form is invisible. This is the function most likely to produce
  confidently stale state.
- **Shifting** (`evaluate_shifting`) counts **byte-identical** consecutive
  actions (`all(a == recent[0])`, threshold 3). Real loops are not
  byte-identical — they are *semantically* identical with varying arguments.
  This will essentially never fire, so the one wired executive function is
  close to dead code.

Cost-based goal switching is **absent**: nothing assigns a cost to a task, and
`DorsolateralPFC._evict_lowest()` evicts by `activation * importance` with
**no notion of task value, cost, or opportunity** — it is LRU-with-a-decay, not
allocation. There is no stopping rule: nothing compares remaining budget to
progress.

**Verdict: BEHIND, but the inhibition half is the one place where the project
is arguably at the state of the art for a safety rail.** Fix shifting with
semantic (not string) loop detection — you already have
`HippoAssociativeGraph.personalized_pagerank`; that is a distance function
sitting unused. Fix updating with real contradiction detection, not
`"status:" in s`. Add cost: a task is worth continuing if
expected_value × probability_of_success > token_cost × switching_cost.

---

## 11. World models — models of the *environment*, not the agent

**Status: entirely absent, and this is the largest single gap in the project.**

**What it is for.** A generative simulator of the environment that the agent
can *roll forward* to test consequences before acting. The distinction the operator
asked for is the right one: the existing `dl_pfc` models the agent's own
working memory; a world model models **the external system** — what will happen
if I run this command, if the service is up, if the user's file is where I
think.

**Verified best implementation.**
- **Ha & Schmidhuber, "World Models," 2018** (https://arxiv.org/abs/1803.10122,
  verified): train a generative network unsupervised to learn a compressed
  spatial and temporal representation of the environment; use its features to
  train a small policy; and — the part that matters for an agent —
  "train our agent **entirely inside of its own hallucinated dream** generated
  by its world model, and transfer this policy back into the actual
  environment." Cheap imagined rollouts as a training substrate.
- Current LLM-era direction, located in the Anthology index: "Efficient
  Integration of External Knowledge to LLM-based World Models via
  Retrieval-Augmented Generation and Reinforcement Learning" (*Findings of
  EMNLP 2025*), "Belief Propagation in LLM World Models" (UkrNLP 2026),
  "Embodied Multi-Agent Coordination by Aligning World Models Through Dialogue"
  (SIGDIAL 2026). Located, not read.

**What hermes-brain gets wrong.** Nothing, because there is nothing — and that
is the finding. There is no environment model anywhere in `brain/`. The nearest
misses are (a) `ThalamicGate`, which scores a *string* by character entropy and
keyword urgency, and (b) `counterfactual_rollouts`, which stores outcomes
*after the fact* rather than predicting them. Neither predicts the future of the
world; both react to it.

Sketch of what to build, honest about the cost: the cheapest useful version is
not a neural world model but a **recorded precondition→outcome table**. For
each action pattern, record the state changes it caused; on a repeat, *predict*
them, compare to actual, and record the error. That gives a calibrated
predictor over "what happens when I do X in this environment" — a world model
over the parts of the environment the agent actually touches — with a
measurable hit rate. That is a one-table version of `somatic_markers` with the
comparison step added. It is achievable, and unlike Ha & Schmidhuber's VAE it
does not need a training pipeline.

**Verdict: BEHIND (absent), and the highest-leverage build.**

---

## 12. Creativity-aware retrieval

**What it is for.** Retrying in a way that escapes the obvious. Standard
retrieval optimises relevance, and relevance is exactly what produces the
homogeneous, safe answer — the retrieval-side twin of §1's homogenisation
finding.

**Verified best implementation.**
- **DF-RAG, "Query-Aware Diversity for Retrieval-Augmented Generation,"
  Findings of EACL 2026** (https://aclanthology.org/2026.findings-eacl.150/,
  verified): cosine-similarity retrieval "maximiz[es] relevance at the cost of
  introducing redundant content." The fix is **Maximal Marginal Relevance** —
  select chunks that are relevant *and maximally dissimilar from each other* —
  with the diversity level tuned **per query at test time, no fine-tuning**.
  Results: **4–10% F1** gain over vanilla cosine RAG on reasoning-intensive QA,
  against an estimated oracle ceiling of up to 18% absolute, of which DF-RAG
  captures **up to 91.3%**.
- **RELexED, "Retrieval-Enhanced Legal Summarization with Exemplar Diversity,"
  Findings of NAACL 2025** (verified): same principle for *few-shot exemplars* —
  a **determinantal point process** balancing exemplar similarity to the query
  against diversity *among* exemplars, with scores from influence functions.
  Beat both no-exemplar and similarity-only selection.
- **SOLAR, "Serendipity Optimized Language Model Aligned for Recommendation,"
  Findings of EMNLP 2025** (verified): serendipity as a first-class objective.

**What hermes-brain gets wrong.** `ThalamicGate.evaluate_admission()` is the
retrieval gate, and it is the **worst offender in the codebase for this
failure mode**, because its stated purpose is to select what enters context.
Its `redundancy_penalty` fires only on strings shorter than 10 characters or
exactly equal to `ok`/`done`/`status: ok`/`heartbeat`. Two *near-identical long
paragraphs* — the actual redundancy case — both score high saliency (high
character entropy) and are both admitted, because there is **no
item-to-item comparison at all**. Meanwhile the one signal it does compute,
character-level entropy, is anti-correlated with usefulness: a long repetitive
log dump scores high. And `overlap_score` *rewards* similarity to the current
context, which is an explicit similarity objective — the exact mechanism DF-RAG
shows to be counterproductive.

**Verdict: BEHIND, and this one is a small diff with a large payoff.** Port MMR
(diversify the candidate set) and a similarity-to-already-admitted check. You
already have PPR over an associative graph; PPR concentrates on a dense
neighbourhood and is a *relevance* signal, not a *diversity* signal, so add
MMR at the admission step rather than trying to fix PPR.

---

## Summary table

| # | Function | Best available today | hermes-brain | Verdict |
|---|---|---|---|---|
| 1 | Creativity / divergence | Doshi & Hauser, *Sci Adv* 2024; deep-semantic-diversity (Findings ACL 2026); ToT NeurIPS 2023 | `DialecticSynthesizer` returns a fixed f-string, 0 call sites | **Behind** (absent; the stub is actively misleading) |
| 2 | Metacognition / calibration | Kuhn et al. ICLR 2023 semantic entropy; Yona et al. EMNLP 2024; SelfAware ACL 2023; Steyvers *Nat MI* 2025 | No confidence, no abstention. Router makes doubt *less* likely to trigger deliberation | **Behind** (absent) |
| 3 | Planning + repair | ReAct ICLR 2023; ToT NeurIPS 2023 (4%→74%) | Compiler never called, matches byte-identical strings, no invalidation | **Behind** (slideshow, not planner) |
| 4 | Decision-making / abstention | Conformal prediction (guarantee **unverified**); Tu et al. Findings EMNLP 2023 (AUROC 74.6→80.3) | Gate thresholds an `expected_utility` nothing computes; no abstention state | **Behind** |
| 5 | Imagination / counterfactual | Fluri et al. consistency checks 2023; Decompose-ToM COLING 2025 | `CounterfactualEngine` = SQLite INSERT of caller strings; `prospection` = `step*(100//horizons)` | **Behind + mislabelled** (highest integrity risk) |
| 6 | Emotion / affect | Human SMH literature solid; **AI-side evidence absent — open problem** | Valence = fixed-constant walk, `curiosity` never read; Somatic has a real update rule but silent when `db_path=None` | **Behind**; somatic **at the right idea** |
| 7 | Consolidation / forgetting | CER ACL 2025 (31.9% / 36.7%, +51.0% rel.); RecMem, TiMem, FOREVER (located) | `run_consolidation_replay()` returns an f-string; in-memory only; hash ≠ pattern separation | **Behind**, one good instinct (priority replay) |
| 8 | Social cognition | SymbolicToM ACL 2023 — scaling alone won't give ToM; explicit multi-entity belief graph | Level-1 only, 0 rows, no writer; discrepancy = string inequality (manufactures false corrections); hedging penalised | **Behind**; pragmatics partly **inverted** |
| 9 | Motivation / drive | RL exploration mature; LLM-era RL exploration active (located). Failure-mode citation **unverified** | `curiosity` is write-only; curiosity *decreases* with frustration | **Behind** (write-only stub) |
| 10 | Executive control | Miyake triad; Friedman & Miyake *Cortex* 2017 (separable). Cost-switching **unverified** | 5-pattern blocklist (good instinct), but updating misses most contradictions, shifting never fires on semantic loops, no cost model | **Behind**; inhibition half arguably **at SOTA** for a safety rail |
| 11 | World models | Ha & Schmidhuber 2018 ("hallucinated dream"); LLM-era world-model work (located) | **Nothing.** No environment model exists | **Behind** (largest gap) |
| 12 | Creativity-aware retrieval | DF-RAG EACL 2026 (4–10% F1, 91.3% of oracle); RELexED NAACL 2025 (DPP) | Saliency = character entropy + urgency keywords; **no item-to-item comparison**; rewards overlap with context | **Behind** (small diff, big payoff) |

## What I would build first, in order

1. **Rename or rebuild `CounterfactualEngine` and `DialecticSynthesizer`.** Both
   currently assert a cognitive capability they do not have. This is an
   integrity problem before it is a capability problem.
2. **Confidence signal → abstention gate** (§2 + §4). Everything downstream —
   routing, planning, exploration — is better if this exists. Highest verified
   return per unit of work in the whole audit.
3. **MMR at the thalamic admission step** (§12). Small diff, directly portable
   numbers (4–10% F1).
4. **CER-shaped consolidation** (§7): distil episodes into general rules with a
   model call, write to a separate store, keep episodes append-only.
5. **A precondition→outcome table** (§11) — the cheap world model, with a
   measured hit rate.
6. **Wire `curiosity`, or delete it** (§9). Write-only state is worse than
   absent because it reads as implemented.
