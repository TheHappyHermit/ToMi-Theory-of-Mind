# References

Every numbered entry here is cited from `README.md` as a superscript link
(e.g. <sup>[1](#ref-1)</sup>). Each one was **title-verified at source** — the
arXiv `/abs` page `<h1 class="title">` element was read, or the DOI was resolved
through Crossref. Numbers in the README that are not in this file are local
measurements, not literature.

**Standing citation rule for this repo:** a citation qualifies only after its
title has been read at source. The arXiv API returns *empty titles* for IDs that
do exist (HTTP 200), so the API alone is not verification. Automated literature
tools return topically-plausible but wrong papers for a given ID — in this
project's history, `2404.13171` was offered as a memory-systems paper and is
actually *"Generic low-atmosphere signatures of swirled-anemone jets"* (solar
physics). **Fetch the `/abs` page. Always.**

---

## Memory architecture & consolidation

<a id="ref-1"></a>**[1]** Lin, K., Snell, C., Wang, Y., Packer, C., Wooders, S., Stoica, I., & Gonzalez, J. E. (2025).
*"Sleep-time Compute: Beyond Inference Scaling at Test-time."* arXiv:2504.13171 — submitted 17 Apr 2025, v1 only, no DOI.
<https://arxiv.org/abs/2504.13171>
Precompute over context *before* the query arrives. Reports ~5× less test-time compute at equal accuracy, "up to 13%" on Stateful GSM-Symbolic, "up to 18%" on Stateful AIME, and up to 2.5× lower per-query cost at ~10 queries/context. **The 5× holds at low test-time budgets and reverses at high ones**; the agentic case study (SWE-Features) yields only ~1.5×.

<a id="ref-2"></a>**[2]** Lutz, M. C., Harkotte, L., & Born, J. (2026).
*"Sleep's contribution to memory formation."* Physiological Reviews, Jan 2026.
<https://doi.org/10.1152/physrev.00054.2024>
Current comprehensive review: systems consolidation as an active process concurring with "widespread synaptic downselection." States the field remains "controversial as to the nature of memory transformation."

<a id="ref-3"></a>**[3]** Rasch, B. & Born, J. (2013).
*"About sleep's role in memory."* Physiological Reviews 93(2):681–766.
<https://doi.org/10.1152/physrev.00032.2012>
The canonical review; establishes that sleep's role is active rather than passive protection.

<a id="ref-4"></a>**[4]** Pan, S., & Rihman, S. (2022).
*"Is the role of sleep in memory consolidation overrated?"* Neuroscience & Biobehavioral Reviews 140:104799.
<https://doi.org/10.1016/j.neubiorev.2022.104799>
**Counterweight.** Concludes "it is not sleep per se, but the engagement of plasticity mechanisms... that constitutes the critical factor."

<a id="ref-5"></a>**[5]** Klinzing, J. G., et al. (2023).
*"Sleep—A brain-state serving systems memory consolidation."* Neuron 111(7):1050–1075.
<https://doi.org/10.1016/j.neuron.2023.03.005>
Replay is "a basic mechanism triggering consolidation during sleep **and wakefulness**."

<a id="ref-6"></a>**[6]** Holdgraf, L. C., et al. (2019).
*"When does sleep affect veridical and false memory consolidation? A meta-analysis."* Psychonomic Bulletin & Review 26:387–400.
<https://doi.org/10.3758/s13423-018-1528-4>
**No overall effect** of sleep on either accurate or false memory consolidation; effects appear only under moderators.

<a id="ref-7"></a>**[7]** Tononi, G. & Cirelli, C. (2014).
*"Sleep and the Price of Plasticity: From Synaptic and Cellular Homeostasis to Memory Consolidation and Integration."* Neuron 81(1):12–34.
<https://doi.org/10.1016/j.neuron.2013.12.025>
Proposes sleep *globally weakens* synapses while preserving relative differences — consolidation and downscaling are the same event.

<a id="ref-8"></a>**[8]** Sinha, A., Arun, A., Goel, S., Staab, S., & Geiping, J. (2026).
*"The Illusion of Diminishing Returns: Measuring Long Horizon Execution in LLMs."* arXiv:2509.09677 — ICLR 2026.
<https://arxiv.org/abs/2509.09677>
Self-conditioning: models make more mistakes when context contains their own prior errors, and this does not shrink with scale. **Mitigation:** RL-trained reasoning models are largely immune.

<a id="ref-9"></a>**[9]** Behrouz, A., Hashemi, M. T., Javanmard, M., & Mirrokni, A. (2026).
*"Useful Memories Become Faulty When Continuously Updated by LLMs."* arXiv:2605.12978.
<https://arxiv.org/abs/2605.12978>
Consolidated memory "first rises, then degrades, and can fall below the no-memory baseline." From ground-truth solutions GPT-5.4 failed 54% of ARC-AGI problems it had previously solved. Agents preserving raw episodes **double** the accuracy of forced-consolidation counterparts.

---

## Retrieval & the graph question

<a id="ref-10"></a>**[10]** Liu, J. (2026).
*"More Is Not Always Better: Cross-Component Interference in LLM Agent Scaffolding."* arXiv:2605.05716.
<https://arxiv.org/abs/2605.05716>
Full 2⁵ factorial over {planning, tools, memory, self-reflection, retrieval}. In every setting the best proper subset **matches or exceeds** All-In.

<a id="ref-11"></a>**[11]** Zhang, Q., et al. (2026).
*"When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation."* arXiv:2506.05690 (GraphRAG-Bench).
<https://arxiv.org/abs/2506.05690>
Basic RAG matches GraphRAG on simple fact retrieval. Plain RAG's complex-reasoning recall collapses **58.64% → 43.20%** from 56k to 1,132k tokens while HippoRAG 2 holds flat. GraphRAG scores 13.4% lower than vanilla RAG on Natural Questions.

<a id="ref-12"></a>**[12]** (2026).
*"BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms."* arXiv:2607.26497.
<https://arxiv.org/abs/2607.26497>
Across 28 nested corpus tiers BM25 overtakes an agentic file-search pipeline at ~10M corpus tokens and leads by ~20 points at full scale, raising accuracy **36.9 → 69.4 at ~1/9 the query tokens** with no LLM-based construction.

<a id="ref-13"></a>**[13]** Li, M., et al. (2025/2026).
*"Stronger Baselines for Retrieval-Augmented Generation with Long-Context Language Models."* arXiv:2506.03989.
<https://arxiv.org/abs/2506.03989>
Under matched token budgets, simple retrieve-then-read preserving document order "consistently matches or outperforms more intricate methods" including RAPTOR and ReadAgent.

<a id="ref-14"></a>**[14]** (2026).
*"Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads."* arXiv:2606.06448 (Stanford + SJTU).
<https://arxiv.org/abs/2606.06448>
Ten systems profiled. BM25 built in <1s scores 55.8%; A-Mem needs ~17,666s of construction to score 42.1%. Break-even rule: high-volume queries against stable histories favour construction; continuous-ingestion with sparse queries favour low construction cost.

<a id="ref-15"></a>**[15]** Han, H., et al. (2025/2026).
*"RAG vs. GraphRAG: A Systematic Evaluation and Key Insights."* arXiv:2502.11371.
<https://arxiv.org/abs/2502.11371>
RAG and GraphRAG are complementary: RAG wins single-hop/detail, GraphRAG wins multi-hop. Also shows LLM-judge scoring is order-sensitive enough to flip conclusions.

<a id="ref-16"></a>**[16]** Jiménez Gutiérrez, B., Shu, Y., Qi, W., Zhou, S., & Su, Y. (2025).
*"From RAG to Memory: Non-Parametric Continual Learning for Large Language Models."* arXiv:2502.14802 — ICML 2025 (HippoRAG 2).
<https://arxiv.org/abs/2502.14802>
Reaches parity with strong dense retrieval on single-hop lookup and wins on multi-hop. Ablations: query-to-triple seeding 87.1 recall@5 vs NER-to-node 74.6; removing passage nodes drops 87.1 → 81.0; removing the LLM triple filter costs only 0.7 points.

<a id="ref-17"></a>**[17]** (2026).
*"A Triple-Robustness Analysis of Retrieval-Augmented Generation for Multi-Hop Requirements Traceability."* arXiv:2608.00705.
<https://arxiv.org/abs/2608.00705>
"Reported verdicts on GraphRAG versus vector RAG disagree, and the evidence is typically tied to a single corpus, embedder, and judge." A learned router on dense embeddings alone reaches macro-F1 0.86 on hop classification.

<a id="ref-18"></a>**[18]** (2026).
*"Temporal Validity in Retrieval Memory: Eliminating Stale-Fact Errors for AI Agents over Evolving Knowledge."* arXiv:2606.26511.
<https://arxiv.org/abs/2606.26511>
Cosine similarity distinguishes a *contradicted* fact from a *duplicated* one at **AUROC 0.59** — near chance. RAG serves superseded values 15–40% of the time.

<a id="ref-19"></a>**[19]** (2026).
*"MoM: Memory of Memory."* arXiv:2609.25054 (NUS).
<https://arxiv.org/abs/2609.25054>
Typed provenance graph with an "active frontier" exposing one current value per resolved key. Revision chains 100% where query-time reading collapses to 25%. Frames the problem as evidential status, not storage.

<a id="ref-20"></a>**[20]** (2026).
*"Ontology-Grounded Project Memory for Coding Agents."* arXiv:2608.13662.
<https://arxiv.org/abs/2608.13662>
Hand-modelled graph with supersession links scores 0.98–1.00 where a vector baseline manages 6–27% — but on ordinary relevance recall the two were "largely equivalent." Hand-modelling helps supersession and set-completeness queries specifically.

<a id="ref-21"></a>**[21]** (2026).
*"What It Costs to Compose, Rebuild, and Correct Precomputed Memory."* arXiv:2608.30647.
<https://arxiv.org/abs/2608.30647>
Amortisation requires many queries and a never-changing corpus. A correction served *beside* static precomputed memory is used on only ~⅓ of two-hop questions, under ⅒ at 512 revisions.

<a id="ref-22"></a>**[22]** (2026).
*"A Few Words Can Distort Graphs: Knowledge Poisoning Attacks on Graph-based Retrieval-Augmented Generation of Large Language Models."* arXiv:2508.04276.
<https://arxiv.org/abs/2508.04276>
Modifying **under 0.05% of the full text** collapses QA accuracy from 95% to 50%, and state-of-the-art defences fail to detect it. A graph converts one bad extraction into a structurally-supported wrong path.

<a id="ref-23"></a>**[23]** (2026).
*"Knowledge-Graph Grounding Helps LLMs Only for Out-of-Training Knowledge."* arXiv:2606.22419.
<https://arxiv.org/abs/2606.22419>
Over PrimeKG, all |Δ| ≤ 3.4. Grounding helps only when the decisive fact lies outside the model's training data — the boundary condition for graph value.

<a id="ref-24"></a>**[24]** (2026).
*"Storage Is Not Memory: A Retrieval-Centered Architecture for Agent Recall."* arXiv:2605.04897.
<https://arxiv.org/abs/2605.04897>
Reports 93.0% on LoCoMo with no graph store, no vector index, no GPU. "Extraction at ingestion is the wrong primitive for agent memory: content discarded before the query is known cannot be recovered at retrieval time." Author-run technical report.

---

## Memory benchmark & evaluation

<a id="ref-25"></a>**[25]** (2026).
*"Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions"* (introduces **MemoryAgentBench**). arXiv:2507.05257 — ICLR 2026.
<https://arxiv.org/abs/2507.05257>
> **Note:** the arXiv listing title was updated, but the abstract still introduces MemoryAgentBench. Both names refer to this paper.
Evaluated 22 memory systems. Overall: **BM25 41.5 · HippoRAG-v2 41.6 · MemGPT 28.3 · Cognee 20.6 · Self-RAG 18.7.** Single-hop FactConsolidation: BM25 48%, MemGPT/Cognee 28%, Mem0 18%, Zep/Graphiti 7%. Multi-hop <7% across all systems. Design guidance: "Do not assume graph or knowledge-graph infrastructure alone solves conflict resolution... without an explicit version-aggregation step." Deterministic conflict resolution 80.8% vs 61.0% for LLM judgement.

<a id="ref-26"></a>**[26]** (2026).
*"Anatomy of Agentic Memory: Taxonomy and Empirical Analysis of Evaluation and System Limitations."* arXiv:2602.19320.
<https://arxiv.org/abs/2602.19320>
"Current agentic memory systems often underperform their theoretical promise." Names underscaled benchmarks and overlooked system costs as the field's soft numbers.

<a id="ref-27"></a>**[27]** (2026).
*"GraphRAG-Bench: Challenging Domain-Specific Reasoning for Evaluating Graph Retrieval-Augmented Generation."* arXiv:2506.02404.
<https://arxiv.org/abs/2506.02404>
The principal published GraphRAG benchmark suite. **Cognee does not appear in it** (0 mentions, vs 13 for HippoRAG and 10 for LightRAG).

---

## Prospective memory & executive function

<a id="ref-28"></a>**[28]** Zhao, J. & Wu, C. (2026).
*"Making Prospective Memory SLM-Shaped: Typed Intention Stores for Small-Model Agents."* arXiv:2609.01272.
<https://arxiv.org/abs/2609.01272>
On PM-Bench, a typed intention store took Gemma-E2B from **4.2% → 66.2%** Set-F1, beating seven retrospective memory methods (max 54.4%). The win is lifecycle living in deterministic code, not model scale.

<a id="ref-29"></a>**[29]** Friedman, A. & Miyake, A. (2017).
*"Unity and Diversity of Executive Functions: Individual Differences as a Window on Cognitive Structure."* Cortex 104:147–166.
<https://doi.org/10.1016/j.cortex.2016.04.023>
The three executive functions are correlated but separable.

<a id="ref-30"></a>**[30]** Teicke, S.-C. & Bode, D. L. (2017).
*"The Stop-Signal Task—A Panoptic Measure of Goal-Initiated Selective Action."* Psychological Bulletin.
<https://doi.org/10.1037/bul0000091>
The SSRT paradigm and its controls; the basis for bounded-latency inhibitory gating.

---

## Cognitive architecture

<a id="ref-31"></a>**[31]** Bering, A. (2026).
*"ZenBrain: A Neuroscience-Inspired 7-Layer Memory Architecture for Autonomous AI Systems."* arXiv:2604.23878.
<https://arxiv.org/abs/2604.23878>
The project's most load-bearing finding. Under moderate load **14 of 15** subsystem ablations look costless; at higher decay **9 of 15** become individually critical, five moving from exactly 0% to below −89%. The authors call this *cooperative masking*. A brain-region subsystem you cannot detect working is not thereby dead.

<a id="ref-32"></a>**[32]** Hou, et al. (2026).
*"MRAgent."* arXiv:2606.06036.
<https://arxiv.org/abs/2606.06036>
**Theorem 4.1:** for any retrieval budget T ≥ 2, H_passive^LM(T) is a **strict subset** of H_active^LM(T) — no amount of tuning a passive retriever reaches the behaviours an active one can produce at equal cost. Cue→tag→content with a sufficiency-based termination rule; 118K retrieved tokens vs A-Mem's 632K (5×) and LangMem's 3.27M (27×).

---

## Software & tooling referenced by the setup

<a id="ref-33"></a>**[33]** ParadeDB, Inc. — `pg_search` extension. AGPL-3.0. v0.25.10.
<https://github.com/paradedb/paradedb> · <https://www.paradedb.com/docs>
True BM25 as a native Postgres index access method. `CREATE INDEX ... USING paradedb (...) WITH (key_field='id')`; transactionally consistent with the table. RRF constant `k=60`. Vector search is labelled **beta**.

<a id="ref-34"></a>**[34]** Graphify-Labs — `graphify` v0.9.67. Knowledge-graph extraction for Markdown corpora.
<https://github.com/Graphify-Labs/graphify>
Produces the `graph.json` graphs (Oracle Brain: 20,199 nodes / 28,946 edges). Pre-1.0, no shipped tests.

<a id="ref-35"></a>**[35]** Plastic Labs — Honcho. Self-hosted peer/autobiographical memory on PostgreSQL + pgvector.
<https://github.com/plastic-labs/honcho>
Deployed as `ghcr.io/plastic-labs/honcho:latest`, which is **not a pin** — the
tag moves. The running image resolved to
`sha256:39053cb3ccec1f6073b42e1bb4a7895c97de0c051589df91426deafe89ef1d18`
(built 2026-08-14), recorded here so the state is reproducible even though the
deployment is not. A future rebuild will pull whatever `latest` has become;
pin by digest before trusting a rebuild.

<a id="ref-36"></a>**[36]** ggml-org — `llama.cpp` server image, `ghcr.io/ggml-org/llama.cpp:server-vulkan`. Used for both the chat and embedding endpoints.
<https://github.com/ggml-org/llama.cpp> · <https://github.com/ggml-org/llama.cpp/pkgs/container/llama.cpp>
Published to **GitHub Container Registry, not Docker Hub** — `hub.docker.com/r/ggml-org/llama.cpp` does not exist and returns 404, which is an easy trap when copying a `docker run` line from a blog post. The embedding deployment runs `llama-server -m Qwen3-Embedding-4B-Q8_0.gguf --embedding --pooling last -ngl 99 -c 8192`. The `--embedding` flag switches the server from generation to embeddings; `--pooling last` matches how the GGUF was trained. The server exposes an OpenAI-compatible `/v1/embeddings` and **ignores a `dimensions` parameter**, so clients must truncate to the target column width themselves.

<a id="ref-37"></a>**[37]** ParadeDB, Inc. — `paradedb/paradedb:0.25.10-pg18`. Single image carrying PostgreSQL 18.6 with both `pg_search` and `pgvector`.
<https://hub.docker.com/r/paradedb/paradedb>
Chosen over `pgvector/pgvector:pgXX` so one container serves both retrieval paths. Two operational consequences are documented in [`INSTALL.md`](INSTALL.md): the container needs `shm_size: 2gb` (the Docker default `/dev/shm` of 64MB is too small for index builds under `maintenance_work_mem=1GB`), and index builds must run outside a transaction block.

<a id="ref-38"></a>**[38]** Zhang, Y., Li, M., Long, D., Zhang, X., Lin, H., Yang, B., Xie, P., Yang, A., Liu, D., Lin, J., Huang, F., & Zhou, J. (2025). *"Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models."* arXiv:2506.05176 — submitted 5 Jun 2025, v3 11 Jun 2025. Tongyi Lab, Alibaba Group.
<https://arxiv.org/abs/2506.05176>
The embedding model behind `Qwen3-Embedding-4B-Q8_0.gguf`, served here by llama.cpp. The series spans 0.6B/4B/8B with 32K context, and is positioned as an advance over the GTE-Qwen predecessor. **Dimension caveat that matters for this setup:** the paper's headline configuration reports 2560-dimension output for the 4B model, while this repo's `embeddings` column is 2000 — the llama.cpp server ignores a `dimensions` parameter, so `brain_sync.py` truncates client-side. Anyone comparing against the paper should know the truncation is ours, not the model's.

<a id="ref-39"></a>**[39]** Malkov, Yu. A., & Yashunin, D. A. (2016; rev. v4 Aug 2018). *"Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs."* arXiv:1603.09320 — submitted 30 Mar 2016; v2 May 2016, v3 Jul 2017, v4 14 Aug 2018. Published as: *IEEE TPAMI* **42**(4):824–836, 2020.
<https://arxiv.org/abs/1603.09320>
The algorithm behind pgvector's HNSW index, which serves the vector arm of retrieval here. Layered navigable small-world graphs give logarithmic-time search with a tunable `ef_search` recall/latency trade-off. Relevant to the corpus sizes discussed in this repo: HNSW is a *scale-up* strategy, and its advantage over flat search depends on the index fitting in memory alongside the vectors.

> The arXiv page uses sentence case (*"...using Hierarchical Navigable Small World graphs"*); the journal version is title case (*"...Using Hierarchical Navigable Small World Graphs"*). Same paper, not a conflict. This entry keys on the arXiv wording, since that is the page the link resolves to.

---

## Cited-but-quarantined

These are recorded so they are never reintroduced. **Do not cite these.**

- `arXiv:2404.13171` — *"Generic low-atmosphere signatures of swirled-anemone jets"* (solar physics). Previously offered as a memory-systems paper.
- `Cai et al., "Overthinking the thinking", Nature 2021`, DOI `10.1038/s41586-021-03589-3` — **not verifiable.** Crossref 404, zero PubMed hits.
- `withtai.com` "AI Context Switch: 23-Min Median Is Worst Case" — cites a nonexistent paper; `2601.12345` is an ambisonics audio paper.
- withtai.com "2026 Stanford Study: Retrieval Cues Cut Task-Switching 31%" — invented author ("Dr. Elena Vasquez") and system ("ContextStore").
- `ZenBrain`/`DORA Explorer` ID `2604.17244` — not a ToM paper.

---

## How to add a reference

1. Fetch the source and **read the title**. `curl -sL https://arxiv.org/abs/<ID>` and grep the `<h1 class="title">`; for DOIs use `https://api.crossref.org/works/<DOI>`.
2. Confirm the title matches the claim you are making. If it does not, the citation is refuted — say so.
3. Add the entry here with a stable `<a id="ref-N"></a>` anchor and the next free number.
4. Reference it from `README.md` as `<sup>[N](#ref-N)</sup>`.
