# Cognitive Function Audit — hermes-brain vs. state of the art

**Full report (6.2k words, all citations verified against fetched sources):**
`/home/operator/hermes-brain/docs/COGNITIVE-FUNCTION-BEST-PRACTICE-AUDIT.md`

**Method.** web_search was blocked, so all evidence came from `curl` against
aclanthology.org, arxiv.org/abs, and api.crossref.org. I downloaded the full ACL
Anthology bib (73MB, 124,522 inproceedings) as a local verified corpus. Every
number below was read out of a fetched abstract. 10 claims are explicitly
marked **unverified** where I could not fetch a source — I assert no numbers
for those.

**Two corrections to the prior internal audit**, found by grep on
`brain/hermes_brain.py`: `self.associative_graph.`, `self.chronesthesia.`,
`self.counterfactual.`, `self.defeater_graph.`, `self.agm.`, `self.dialectic.`
→ **0 call sites each**. But four of them *are* reachable from the dashboard
(`dashboard/backend/routes/brain.py:96,101,130,223,237,258,295,314`) — they are
observable, just never part of reasoning. `valence_engine.curiosity` is
confirmed **write-only** (no reader anywhere in the repo).

---

## The core diagnosis

The gap is not "wrong algorithm." It is **"constructed, never consulted"** — and
in three cases, **asserting a capability the code does not have**:

- `DialecticSynthesizer.synthesize()` returns a **fixed f-string**. It reads a
  conflict, ignores both contents, emits the same sentence, `resolution_strategy`
  hardcoded. Called 0 times.
- `CounterfactualEngine` is named for Pearl's third rung and docstrings itself
  as causal counterfactuals. It is a **SQLite INSERT of caller-supplied
  strings**. No structural causal model, no intervention. `predicted_advantage`
  is never compared to what happened.
- `ChronesthesiaEngine.prospection()` returns
  `min(100, step * (100 // horizons))` — arithmetic on the loop index, not a
  projection. Hazards are hardcoded.

These are worse than absent: a trace shows "dialectical synthesis" and
"counterfactual regret" and a reader concludes causal reasoning occurred.

## Per-function verdict (ahead / at / behind)

| Function | Best available today (verified) | hermes-brain | Verdict |
|---|---|---|---|
| **1 Creativity** | Doshi & Hauser, *Sci Adv* 2024 (10.1126/sciadv.adn5290): LLM ideas make stories *more creative individually* but *more similar to each other* — a social dilemma. **Findings ACL 2026** (2026.findings-acl.915): adding reasoning chains **degrades** performance; "**deep semantic diversity, rather than surface-level lexical variation**, is the decisive prerequisite." ToT NeurIPS 2023: Game of 24 **4% → 74%** | No creativity function. Nearest = the f-string. `ThalamicGate.compute_entropy` is *character* Shannon entropy — unrelated to semantic novelty | **Behind** |
| **2 Metacognition** | Kuhn/Gal/Farquhar ICLR 2023 semantic entropy (2302.09664); Yona et al. EMNLP 2024: LLMs "are **poor at faithfully conveying their uncertainty**," failing *both* over- and under-hedging; SelfAware ACL 2023: self-knowledge exists and ICL+instruction-tuning **enhance** it; Steyvers *Nat Mach Intell* 2025: users overestimate, and **longer explanations raised confidence without improving accuracy**; Tu et al. Findings EMNLP 2023: self-eval tuning → CoQA **AUROC 74.61% → 80.25%** | **Absent.** `DefeaterGraph.credence` is display-only. Worse: `CognitiveRouter` weights unresolved hypotheses at `count*0.1` capped **0.2**, vs keywords up to **0.7** — so **systematic doubt can never trigger slow deliberation** | **Behind** |
| **3 Planning** | ReAct ICLR 2023 (2210.03629) — traces "update action plans and **handle exceptions**," working because actions return external ground truth. ToT (2305.10601) backtracks to last viable node | `ProceduralSkillCompiler` never called → nothing compiles. Key is `" -> ".join(raw strings)` → only byte-identical retries match, which never happen. No preconditions, no invalidation, no dependencies | **Behind** (slideshow) |
| **4 Decision-making** | Conformal prediction is the distribution-free standard (**guarantee statement unverified** — could not fetch primary). Verified that it's now live in NLP: Abstain-R1 (Findings ACL 2026), "Art of Saying 'Maybe'" (EACL 2026), Conformal LLM Routing (ACL 2026 SRW) | `ActionGate` thresholds `expected_utility` that **nothing ever computes**. No abstention state at all — "NO_GO" means queued for confirmation, the opposite of calibrated refusal | **Behind** |
| **5 Imagination** | Fluri/Paleka/Tramèr (2306.09983): counterfactuals have no ground truth, so score **internal consistency**, not correctness — surfaced "GPT-4 forecasting that sports records will evolve non-monotonically." Decompose-ToM COLING 2025 uses simulation as a reasoning primitive | `CounterfactualEngine` = SQLite INSERT. `prospection` = `step*(100//horizons)`. `chronesthesia` timeline is **in-memory only**. Bias warning (simulation inflates felt likelihood) is **plausible but unverified** here | **Behind + mislabelled** — highest integrity risk |
| **6 Emotion** | Human somatic-marker base is solid (Bechara 2011, 10.1093/acprof:oso/9780195395518.003.0048; Damasio 1998; North et al. *Neuropsychologia* 2001). **The AI-side question is an open problem** — I found no controlled study either way. Closest proposal: "Feeling First, Speaking Second," dual-process affective LLM agents (located, not read) | Valence = fixed-constant walk on a `success` bool, no world input. `SomaticMarkerEngine` is the **only affect module with a real update rule** (weighted mean + sample count) — right idea — but keys are opaque strings (table shatters to singletons) and `db_path=None` silently returns 0.0 | Valence **behind**; somatic **at the right idea**, behind on engineering |
| **7 Consolidation** | **CER, ACL 2025** (2025.acl-long.694), training-free: distil experiences into a buffer, retrieve into context. **31.9%** VisualWebArena (beats tree search, lower cost), **36.7%** WebArena = **+51.0% relative**. Plus RecMem, TiMem, FOREVER (located, not read) | `run_consolidation_replay()` **returns an f-string** and consolidates nothing. `pattern_separation` is a truncated SHA-256 — a hash gives **zero** interference protection (opposite of dentate-gyrus function). `pattern_completion` scores precision against the cue, ignoring trace length. Priority = surprise+valence, i.e. **replay what felt intense, not what was useful** | **Behind**, one good instinct |
| **8 Social** | **SymbolicToM, ACL 2023** (2023.acl-long.780): "**simply scaling up models will not imbue them with theory of mind**" — it's symbolic and implicit. Fix = decoding-time **multi-entity belief graph** with higher-order levels. Also **found spurious patterns in existing ToM benchmarks**. Negotiation: verified LLM work is mostly measuring **human biases** (anchoring Findings EMNLP 2025) and **framing sensitivity** (EACL 2026); no verified coordination capability result | `user_mental_models` **0 rows, no writer**. Models Level-1 only (user's belief about a fact), not Level-2+ multi-entity. Discrepancy = **string inequality** → "Postgres on 5432" vs "Postgres on port 5432" manufactures a false correction. `GriceanPragmatics`: 3 regexes; **penalises hedging as a Maxim-of-Quality defect**, inverting Yona et al. | **Behind**; pragmatics partly **inverted** |
| **9 Motivation** | RL exploration mature; LLM-era RL exploration active ("Low-probability Tokens Sustain Exploration in RL with Verifiable Reward," Findings ACL 2026). **Canonical novelty-seeking failure-mode citation unverified** | `curiosity` **never read**. Also inverted: curiosity *decreases* when `allostatic_load > 0.7`, so exploration is suppressed exactly when things are going badly | **Behind** (write-only stub) |
| **10 Executive** | Miyake triad; Friedman & Miyake, *Cortex* 2017 (10.1016/j.cortex.2016.04.023): the three are correlated but **separable**. Cost-based switching **unverified** | **Inhibition is the one place arguably at SOTA** — a 5-pattern irreversible-command blocklist is the right *kind* of rail, and the premature-completion heuristic is genuinely thoughtful. But: blocklist **fails open** (`find . -delete` uncaught); `monitor_updating` only fires if both strings contain literal `"status:"`/`"version:"`; `evaluate_shifting` counts **byte-identical** actions, so semantic loops never trigger — the one wired function is near-dead. No cost model; eviction is `activation*importance` LRU | **Behind**; inhibition **at SOTA** |
| **11 World models** | Ha & Schmidhuber 2018 (1803.10122): train agent "**entirely inside of its own hallucinated dream**." LLM-era: RAG+RL for LLM world models (Findings EMNLP 2025), world-model alignment (SIGDIAL 2026) — located, not read | **Nothing exists.** `dl_pfc` models the *agent*; a world model models the *environment*. `ThalamicGate` scores strings after the fact; `counterfactual_rollouts` records outcomes post-hoc. Neither predicts | **Behind — largest gap** |
| **12 Creativity-aware retrieval** | **DF-RAG, EACL 2026** (2026.findings-eacl.150): cosine retrieval "maximiz[es] relevance at the cost of introducing redundant content." **MMR**, diversity tuned per-query at test time, no fine-tuning. **4–10% F1** gain; captures **91.3%** of an estimated 18% oracle ceiling. **RELexED, NAACL 2025**: **determinantal point process** for exemplar diversity | Worst offender for this failure mode *because its job is to select what enters context*: `redundancy_penalty` fires only on strings **<10 chars** or exactly `ok`/`done`/`heartbeat`. Two near-identical long paragraphs both score **high** (high char entropy) and both get admitted — **zero item-to-item comparison**. And `overlap_score` *rewards* similarity to context, the exact mechanism DF-RAG shows is counterproductive | **Behind** (small diff, big payoff) |

## Build order

1. **Rename or rebuild `CounterfactualEngine` + `DialecticSynthesizer`** — integrity before capability. A module that names a capacity it lacks is a trap for the next contributor.
2. **Confidence signal → abstention gate.** Everything downstream (routing, planning, exploration) improves. Highest verified return per unit of work in the audit (AUROC +5.6pts from tuning alone).
3. **MMR at the thalamic admission step.** Small diff, portable numbers.
4. **CER-shaped consolidation** — distil episodes into general rules via a model call, write to a separate generalised store, keep episodes append-only.
5. **Precondition→outcome table** — the cheap world model, with a measured hit rate. Needs no training pipeline; it's `somatic_markers` with the comparison step added.
6. **Wire `curiosity` or delete it.** Write-only state reads as implemented.

## Files
- **Created:** `/home/operator/hermes-brain/docs/COGNITIVE-FUNCTION-BEST-PRACTICE-AUDIT.md` (full report, 6.2k words)
- **Created:** `/home/operator/.hermes/cache/scratch/lit.py`, `bib.py`, `sr.py` (rate-limited fetchers + local ACL bib search), plus `/tmp/anth.bib` (73MB ACL corpus)
- **Modified:** nothing in the codebase

## Issues hit
- web_search blocked as instructed. arXiv API returned **406/429** persistently (even with a browser UA and backoff); Semantic Scholar and OpenAlex both **429** on the shared IP. **Worked around** by downloading the ACL Anthology bib as a local corpus and using direct `arxiv.org/abs` page fetches (verified working at ~3s spacing) plus Crossref. Multi-term arXiv HTML search silently returns 0 hits at ≥3 terms — a trap worth knowing about.
- Several plausible-looking arXiv IDs I guessed were wrong (e.g. 2404.13171 is an astrophysics paper, not sleep-time compute). **I discarded those rather than cite them**; the sleep-time compute reference is therefore absent rather than miscited.
