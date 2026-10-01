# hermes-brain Retrieval Evaluation — Design for a Benchmark That Can Settle the Question

**Status:** design only. Nothing here has been run as a benchmark.
**Date:** 2026-09-25
**Supersedes:** `docs/RETRIEVAL-QUALITY-MEASUREMENT.md` (numbers there are not interpretable — see §0)
**Corpus:** 14,606 `.md` files under `~/.hermes` (14,876 including dot-dirs; the
retrieval corpus excludes dot-prefixed path components, per `iter_documents`)

---

## 0. Why the existing benchmark cannot be repaired by editing it

Three defects, all verified by reading the code and the graph.

**(a) The keyword arm never reads a document body.** `build_keyword_index` does
`tokenize(str(doc))` — the *path*. `iter_documents` returns `Path` objects and
`str(Path)` is the filesystem path. So the "keyword" arm is a filename index, and
`RETRIEVAL-QUALITY-MEASUREMENT.md`'s 0.792 is *filename matching quality*, not retrieval quality.

**(b) The labels are filename substrings, so (a) is not a handicap — it is the task.**
All 24 labels are filename-shaped (`"Complementary_Learning"`, `"thalam"`, `"gate"`).
`is_relevant` is `any(r.lower() in str(candidate).lower())`. The scoring rule and the
indexing rule are the same rule. A system that indexed bodies perfectly and a system
that indexed paths perfectly are indistinguishable under this metric. This is the
"shared matching rule" problem: the benchmark cannot express a distinction it never made.

**(c) The `oracle` arm is not a ceiling, it is a copy of the keyword arm.**
Oracle = "is a label-matching file present in the corpus", using the same
`is_relevant` substring test over the same `str(doc)` values. The reported
`oracle = keyword = 0.792` is not a coincidence and not a finding — it is the same
computation twice. There is currently **no independent upper bound anywhere in the harness.**

**And the diagnosis in the doc is factually wrong.** It states: *"0 of 20,199 nodes
in the oracle graph have a `file` or `source_file` field."* Measured on
`oracle/brain/graphify-out/graph.json`:

```
nodes                     20,199
nodes with source_file    20,067  (99.3%)
source_file values that resolve to a real file on disk, relative to
  the vault root        20,067 / 20,067  (100.0%)
distinct source files      1,697
```

The graph **is** document-anchored, on nearly every node, and every anchor resolves.
The doc's central structural claim — "no node carries a file reference directly" —
is false, and the recommendation derived from it ("rank document nodes rather than
concept nodes … these are design changes") is aimed at a defect that does not exist.

The real reason the graph arm scored 0.083 is visible in its own output. For
`"thalamus gating sensory attention"` the top hits are:

```
0.07428  Consciousness-Studies/Consciousness-Studies-Complete.md
0.05968  research/frontier-research-ontology-temporal-geometric-memory-...md
0.05008  research/frontier-research-ai-ontology-failures-llm-structured-...md
```

Three *different topics*, all mega-hub documents. Measured hub structure:

| node | out-deg | in-deg | file |
|---|---|---|---|
| Descartes | 325 | 0 | `Entities/Descartes.md` |
| Michael Graziano | 316 | 3 | `GAP-ANALYSIS-ROUND3.md` |
| OSINT Agent Design | 314 | 19 | `_archive/.../osint_agent_design.md` |
| Francis Crick | 301 | 4 | `Consciousness-Studies-...-Complete.md` |
| Wireless Chipsets Doc | 296 | 5 | `Software-Defined-Radio/wireless-chipsets.md` |

`GAP-ANALYSIS-ROUND3.md` contributes 522 nodes to a 20,199-node graph from **one file**.
Nodes with zero incoming edges: 4,027 (19.9%).

Personalised PageRank seeded on a query rewards *high-degree* nodes. The graph arm is
not failing to reach documents; it is returning a hub lottery, because the graph is a
**concept graph whose nodes are filed under documents**, and a handful of compendium
documents own a disproportionate share of the concept mass. Any evaluation that
reports this as "the graph is weak" is measuring degree bias with a filename metric.

**Conclusion for the implementer: do not tune anything until the graph is fixed, and
do not report a number from the current harness.** Everything below is built so that
the *first* thing the harness reports is a graph-health gate (§7), which must pass
before any retrieval metric is printed at all.

---

## 1. Corrected judgement-set design

### 1.1 The anti-triviality rule

A query is admissible only if it passes a **filename-blindness test**: run BM25 over
*paths only* and over *bodies only*. If the path-only arm scores ≥ 0.8 of the body-only
arm's recall@10, the query is trivially answerable by filename and is **rejected**.

This is a mechanical filter, not a judgement call, and it must be implemented as a CI
gate over the query file. Target: **≥ 40% of retained queries must be ones where the
body-only arm beats the path-only arm by ≥ 0.3 absolute recall@10.** If the retained
set cannot hit that, the corpus is not suitable and the harness must say so.

### 1.2 Breaking the shared-matching rule

Three independent mechanisms, all required:

1. **Labels are document IDs (content hashes), never strings.** A label is
   `sha256(normalized_body)[:16]` of the judged document. Relevance is
   `retrieved_doc_id in judged_doc_ids`. No substring test exists anywhere in the
   codebase. Path and label live in different universes, so they cannot share a rule.
2. **The pooler is body-only and stopworded.** Tokenise body text, strip YAML
   frontmatter and the `sources:` URL list (this corpus puts 15+ citation URLs in
   frontmatter on most research notes — those are pure lexical noise that would let
   BM25 cheat). Index the body only.
3. **The ceiling is computed by a person, not a rule.** `oracle@k` = the best any
   system could do *given the judged set*, obtained by exhaustively ranking the
   judged-relevant set to the top: `oracle_recall@k = 1.0` whenever every judged doc
   is in the pool, and the **pool-coverage** number (`|judged ∩ pool| / |judged|`) is
   reported separately as a corpus-coverage diagnostic. Coverage is *not* a ceiling
   and must never be printed as one.

### 1.3 Scale, composition, annotation

| | |
|---|---|
| **Total queries** | **300** |
| Categories | 7 (§2); see split below |
| Labels per query | graded 0/1/2/3 — see below |
| Labellers | **2 independent, plus 1 adjudicator** for disagreements |
| Labeller pool | ≥ 3 people, none of whom wrote the queries for the set they label |
| Judged pool depth | top-30 pooled from **all six** arms, plus 10 random non-retrieved docs (pooling bias control) |
| Agreement gate | **Cohen's κ ≥ 0.62** on 3-way grade; adjudication log committed |

**300 is not arbitrary** — it is the power requirement (§5): to detect a
+0.10 absolute nDCG@10 difference at 80% power, α=0.05, paired, you need ≈ 90–110
queries; 300 gives that with room for per-category breakdown (≈ 40/category is
enough for a within-category test at the same effect size, which is where the
graph's case has to be won or lost).

**Graded relevance** is mandatory, not optional, because nDCG is meaningless on
binary labels and because "partially useful" is the normal case for a knowledge base:

- **3 — necessary**: a complete answer to the question is in this document.
- **2 — strong support**: the document contains the specific claim, but the answer
  needs another document too.
- **1 — contextual**: relevant topic, does not contain the answer.
- **0 — not relevant** (must be *explicitly* assigned, not left implicit — unjudged
  is a third state, `U`, and metrics treat `U` as 0 for recall, and exclude from nDCG).

Annotators label from the **document**, given the query — never from a candidate list
produced by the system under test, except within the pooled set (TREC-style pooling
is acceptable here *because pooling is over all six arms*, so no single arm is
privileged).

### 1.4 Held-out discipline

Three disjoint splits, committed as files, never re-derived at runtime:

| Split | n | Use |
|---|---|---|
| `dev` | 100 | tuning fusion weights, reranker thresholds, chunk size, PPR α |
| `test` | 150 | **reported numbers, once** |
| `challenge` | 50 | frozen, published, for future graph/retriever changes |

- Fusion weights, normalisation method, and RRF `k` are fitted on **`dev` only**.
  Selecting them on `test` and reporting `test` is the single most common way an
  IR benchmark lies to itself.
- Every reported number carries the split name in the output line.
- `scripts/eval_retrieval.py --split test` refuses to run if `--tuned-on test` is
  passed; the config records a hash of the tuning config alongside each result.
- The `challenge` 50 are **never** used for any tuning decision, ever, including
  when a new retrieval arm is added.

---

## 2. Required query categories, with worked examples from this corpus

Category proportions of the 300: direct 60, multi-hop 60, conceptual 45, comparative
40, temporal 30, synthesis 35, troubleshooting 30.

Worked examples are drawn from files that verifiably exist in `~/.hermes`.

### 2.1 Direct lookup (60) — *where is the specific fact*
> "What `k1` and `b` values does the vault's own BM25 implementation use, and what
> does the document say about why they were chosen?"
> → `oracle/brain/research/bm25-normalization-failure-analysis.md` (it states
> Okapi BM25 `k₁=1.5, b=0.75` in its signal table).
>
> Note: a *good* direct-lookup query still passes the filename-blindness test,
> because the answer (the parameter values and the justification) is in the body,
> not the filename. Grade 3 only if the values + rationale are both present.

### 2.2 Multi-hop / associative (60) — **the only category a graph can win**
> "What connects the thalamic reticular gating mechanism to the club-consolidation
> account of sleep, given that neither note cites the other?"
> Bridge: `Neuroscience/Thalamic-Reticular-Gating-Mechanisms.md` ←conceptual link→
> memory-consolidation note.

**Why keyword search structurally cannot answer this — the construction rule:**

A multi-hop query is admissible only if it satisfies **all three** conditions. This is
the design core of the whole evaluation, so it is stated as a testable predicate:

- **(M1) No single document contains all bridge entities.** For the query's entity set
  *E*, require `∀ d ∈ corpus: |E ∩ entities(d)| < |E|`. Verified by running each
  candidate bridge entity through the entity index and checking co-occurrence counts.
- **(M2) No single document contains all query terms.** A BM25 hit is impossible if
  the *conjunctive* term set is unsatisfiable in any one document. Enforce by
  construction: the query is written as the **union of terms from two documents that
  are not co-present**, joined by a relation word ("connects", "relates to",
  "in tension with") that appears in *neither* source document. This is what makes
  the query lexically unanswerable rather than merely hard.
- **(M3) The bridge is discoverable in the graph.** Require a path of length ≤ 3
  between anchor nodes *A* and *B* in `graph.json`, verified at query-authoring time.
  If no path exists, the query is discarded — otherwise it is unanswerable by *any*
  arm and just adds noise.

Additionally, **M4 — the "no shared vocabulary" variant.** For at least 40 of the 60,
the two anchor documents must have Jaccard similarity < 0.1 on content-word sets.
Shared vocabulary is what lets a lexical retriever cheat across a bridge.

**Sanity gate, and it is a real one:** a *perfect* keyword system (exhaustive term
matching over all 14,606 bodies, no ranking) must score **≤ 0.20 recall@10** on this
category. If it scores higher, the queries leaked and the whole category is
discarded and rewritten. This gate is a required CI check. A multi-hop category
where lexical search scores 0.9 is not a hard category; it is a broken one.

### 2.3 Conceptual / definitional (45)
> "What is the retrieval-limited regime, as this vault defines it?"
> → `bm25-normalization-failure-analysis.md` §"Retrieval-Limited Regime: Formal
> Characterization", which gives an explicit four-condition definition.
>
> These deliberately ask for *this corpus's* definition, which may differ from the
> literature's. Grading is against the document, so a vault-specific definition is the
> correct answer, not the textbook one.

### 2.4 Comparative (40)
> "How does the vault's `wireless-chipsets` note differ from `wireless_chipsets.md` in
> the archived agent_zero import — same hardware coverage or different?"
> Both exist: `Software-Defined-Radio/wireless-chipsets.md` (296 nodes) and
> `_archive/agent_zero_kb_import/a0/usr/shared/knowledge_base/wireless_chipsets.md`
> (209 nodes). Graded 2 for each doc individually, 3 only for the doc that carries
> the actual contrast.
>
> Comparative queries need ≥ 2 documents by construction, so they are pooled across
> arms and are naturally grade-2. This is also where **content near-duplicates** must
> be handled: I checked for them (5-gram-shingle Jaccard > 0.6 over 300 random
> research notes) and found **zero** near-duplicate pairs, so comparative queries
> will not accidentally be "find the copy" tasks. Re-run this check when the corpus
> grows; the `frontier-research-ontology-*` family (217 files, 1.5% of corpus) is
> the risk area.

### 2.5 Temporal (30)
> "Which is the most recent note that revises the memory-consolidation account, and
> what did it change?"
> Uses `generated:` / `verified:` / `stale_after:` frontmatter, which this corpus
> populates consistently. Requires reading frontmatter *as data*, and the label must
> pin a specific revision, not a topic.
>
> Temporal is a category where the graph can help via `influences` edges (212 in the
> graph) but where lexical can win on dates — so it is a genuine contest, and is
> included precisely to see the graph *lose* somewhere.

### 2.6 Synthesis / aggregation (30)
> "Across the vault's own retrieval research, what is the evidence that reweighting
> an auxiliary signal cannot raise recall, and which papers report it?"
> Aggregates `bm25-normalization-failure-analysis.md`,
> `retrieval-failure-mode-taxonomy.md`, `adaptive-fusion-with-suppression.md`,
> `layer-type-aware-ceqe-fusion-weight-learning.md`, etc.
>
> Synthesis needs **≥ 5** relevant documents, all grade 2, none grade 3. This is the
> category that most rewards recall depth and is the best test of whether top-10 is
> even the right cut — report recall@10 *and* recall@50 for this category.

### 2.7 Troubleshooting (30)
> "Retrieval returns high-precision, low-recall results and adding a second fusion
> arm changes nothing — what does the vault say causes that?"
> → the "monotonic transformations preserve top-k" theorem and the zero-variance
> trap in `bm25-normalization-failure-analysis.md`, plus `retrieval-failure-mode-taxonomy.md`.
>
> This is the highest-value category for the actual product: it is what a user asks
> when the system is misbehaving, and it is the category where the graph's
> "related concept" reach is genuinely useful rather than decorative.

---

## 3. Retrieval arms and what each controls for

Seven arms. **A, B are mandatory in every report.** A result table without A and B is
uninterpretable and the harness must refuse to print one.

| # | Arm | Controls for | Rationale |
|---|---|---|---|
| **A** | **Full context** — whole vault in the prompt (or a 1M-token map+select over it) | The ceiling a graph would have to beat to be *worth it* | If A wins, the graph is solving a problem you can solve by paying for tokens. the operator's cost-is-not-a-constraint stance makes A the *decisive* baseline, not a formality. |
| **B** | **BM25 over bodies** (stemmed, stopworded, frontmatter-stripped, body-only pooler) | The honest lexical floor | The existing 0.792 is a *path* index. B is the number the graph must beat. Must be a real BM25 (k1, b fitted on `dev`), not token-overlap. |
| **C** | Hybrid lexical + dense (RRF, k=60) | Whether *any* fusion helps | Reproduces the documented behaviour; also the "fusion ≠ graph" control. |
| **D** | Hybrid + cross-encoder reranker (monoBERT-style, top-50 → top-10) | How much of any gain is just reranking | Mandatory. A graph that merely pre-filters candidates will look good until D shows a reranker gets the same candidates. |
| **E** | **Graph only** (seed → personalised PageRank → document, hubs suppressed per §7) | The graph's standalone value | Reported, but **never** as a headline — a graph-only arm has no lexical competitor, so it cannot be interpreted alone. |
| **F** | **Graph + lexical** (RRF and score-fusion variants, both reported) | The actual product question | The only arm that corresponds to `--graph`. |
| **G** | Full-context + graph (A with graph-selected context) | Whether the graph's value is *selection* under a big context window | This is the arm that matters most given A is a strong baseline. |

**Mandatory reporting rules**
- Every table row set includes A and B, plus the C→D delta and the B→F delta.
- F is reported as **two** sub-rows: `F-RRF` and `F-ScoreFusion` (see §6). Reporting
  only one fusion method and calling it "graph+lexical" is not acceptable.
- Report per-category, not just aggregate. The graph's case is won or lost on
  multi-hop; an aggregate that mixes 240 easy queries with 60 hard ones will hide
  both a real win and a real regression.
- Report **mean latency and index cost per arm**. A graph that wins nDCG by 0.02 at
  40× the build cost is a different engineering decision than one that wins by 0.02 free.

---

## 4. Metrics

### 4.1 Standard ranking metrics (all per-query, all per-category)
- **nDCG@10** with gains `2^grade − 1` and `log2(rank+1)` discount, the standard
  formulation (Järvelin & Kekäläinen, *ACM TOIS* 2002, DOI `10.1145/582415.582418`).
  Primary metric. Requires graded labels — see §1.3.
- **MRR@10** — first-relevant rank. Robust to grade disagreements at the top, which
  is where labeller κ is weakest. Report as co-primary.
- **recall@10 / @50** — kept from the old harness for continuity, but demoted: it
  cannot distinguish a rank-1 hit from a rank-10 hit, and it is what made the
  original 0.083-vs-0.792 framing look starker than it was.
- **MAP** if graded labels permit; otherwise skip rather than approximate.

### 4.2 Answer quality on the retrieved set
Two levels, both required, because retrieval metrics alone can flatter a bad ranker:

1. **Grounded answer accuracy.** Given the top-10, an LLM answers the query with
   citations into the retrieved docs. Scored by a judge (0–3) on *correctness* and
   *groundedness* separately, plus a **citation-precision** fraction: of the cited
   documents, how many are judged grade ≥ 2. This catches a system that retrieves
   irrelevant-but-topically-adjacent documents that happen to contain a confusable
   passage.
2. **Judge calibration.** Fixed judge model, pinned version, temperature 0, judge
   prompt committed to the repo, and a **human-checked 10% sample** of judge scores
   reported every run. An unvalidated LLM judge reporting deltas of 0.02 is noise.

### 4.3 The graph's actual job: Connection & Novelty Discovery (CND)

This is the metric the current benchmark has no way to express, and the one that
decides whether the graph earns its keep. It is **not** a label-hit metric.

**Definition.** For each multi-hop / synthesis / troubleshooting query, the graph arm
surfaces a ranked list of *(document, path)* pairs — the path being the relation chain
that reached the document. For each surfaced connection we measure three things:

**(a) Surprisal** — was this connection findable by lexical means?
`Surprisal(c) = 1 − max_lexical_affinity(c)`, where `max_lexical_affinity` is the
best normalised BM25 score the *body-only* index gives to that document for any of
the query's terms or bridge entities. A connection surfaced by the graph that BM25
scores near zero is *structurally new information*. Report the **CND-novelty rate**:
fraction of surfaced connections with `Surprisal > 0.8`.

**(b) Usefulness** — an independent labeller, shown *only* the connection
`(doc A, relation, doc B)` and the original question, and **not** the path's
provenance, answers on a 4-point scale:

| Grade | Meaning |
|---|---|
| 3 | Reveals a relationship I would not have found and that changes what I'd do |
| 2 | Genuinely interesting, mildly useful |
| 1 | Plausible but obvious once seen |
| 0 | Noise / spurious edge |

**Report: mean usefulness, and CND-precision = fraction of grade ≥ 2.**
The `graph+lexical` arm is the reference: a graph connection that lexical search
would also have surfaced is not a discovery.

**(c) Justification rate** — fraction of surfaced connections where the reported path
is *verifiable*: the named relation actually exists between those two entities in
`graph.json`. This is a **correctness** metric for the graph itself and needs no
query judgement at all — it is free, deterministic, and should be computed on every
run. A low justification rate means the graph is emitting plausible-looking paths
that aren't there, which no relevance metric will reveal.

**Aggregate reporting.** Report CND as a 3-tuple
`(novelty rate, mean usefulness, justification rate)` on the multi-hop + synthesis +
troubleshooting subset, for E and F, **plus the lexical baseline's own numbers on the
same subset** so the comparison is like-for-like. Define the headline go/no-go as:

> The graph earns default-on status if, on the multi-hop subset, it shows
> **justification ≥ 0.9** (it isn't hallucinating edges) **and** either
> **(novelty ≥ 0.5 ∧ usefulness ≥ 2.0)** or **a significant nDCG@10 gain over arm B**
> — and it must not regress arm B by more than 0.02 nDCG@10 on the aggregate.

That rule is falsifiable, decided in advance, and cannot be moved after seeing data.

---

## 5. Statistical requirements

**Paired tests only.** Every arm is evaluated on the identical query set, so the
comparison is paired. Report the per-query delta and a paired test on it.

- **Test:** Wilcoxon signed-rank on per-query nDCG@10 deltas (two-sided, α = 0.05),
  plus the **randomised paired bootstrap** (10,000 resamples of queries) for the
  confidence interval on the mean delta. Both are standard; Smucker, Allan &
  Carterette, *CIKM* 2007 (DOI `10.1145/1321440.1321528`) is the canonical reference
  for test-choice agreement in IR, and Carterette's *SIGIR* 2015 Bayesian treatment
  is the right follow-up if the bootstrap interval straddles zero.
- **Multiple comparisons:** 7 arms × 7 categories is 49 cells. Apply **Holm–Bonferroni**
  within each family of comparisons against arm B, and state the corrected α.
  Uncorrected mass-testing on a 49-cell table will produce a "significant" result by
  construction.
- **Effect size, not just p.** Report the mean delta and the bootstrap CI. A p-value
  on 300 queries will happily declare a 0.005 nDCG difference significant. The
  decision rule uses the CI, not the p.

**How many queries — the arithmetic.**
Two-sided paired t-test, α = 0.05, power 0.80, to detect Δ with paired SD σ_d:
`n ≈ (1.96 + 0.842)² · σ_d² / Δ² = 7.85 · σ_d² / Δ²`.

- Realistic target Δ = **+0.10 nDCG@10** (a large, unambiguous win — if the graph
  delivers less than this it is not worth enabling by default).
- Realistic paired SD for nDCG@10 deltas on a heterogeneous query mix: **σ_d ≈ 0.20**
  (nDCG@10 per query is heavily right-skewed; this is the standard order of
  magnitude, and it must be *measured* on the first 100 queries, not assumed).
- ⇒ `n ≈ 7.85 × 0.04 / 0.01 = **31 queries**` for the clean case.
- Realistically σ_d is larger on the multi-hop subset (bimodal: 0 for most queries,
  large for wins) — assume **σ_d ≈ 0.35** there ⇒ `n ≈ 7.85 × 0.1225 / 0.01 = **96 queries**`.

**Therefore: 300 total, with ≥ 60 in multi-hop, gives ~3× the required n on the
category that actually decides the question.** If you want to detect Δ = +0.05 on
multi-hop, you need `n ≈ 385` multi-hop queries — state that as the cost of a
smaller claim rather than quietly lowering the bar.

**Bootstrap the power, don't assume it.** Before the full run, resample from the
first-100 dev queries to get an empirical distribution of σ_d, and report the
*n detectable* at n = 300. If it is below 0.10, say so in the report.

**Never tune on what you report.** Covered in §1.4; the enforcement is mechanical
(config hash + split name in every output line), and `--tuned-on test` is a hard error.

---

## 6. Literature this design must reproduce or beat

All citations below were verified against Crossref and the ACL Anthology bibliography
during this design pass (venue + year + DOI). Numbers attributed to papers are those
stated in the papers' own abstracts or reproduced computationally here.

### 6.1 RRF's failure mode under disjoint ranked lists — must be reproduced

Cormack, Clarke & Büttcher, *"Reciprocal rank fusion outperforms Condorcet and
individual rank learning methods"*, **SIGIR 2009**, DOI `10.1145/1571941.1572114`
(600+ citations). Defines `RRF(d) = Σ 1/(k + rank_i(d))`, k = 60.

The failure mode is **structural, not a tuning problem**, and I verified it
computationally (`scratch/hb_rrf_demo.py` in this session's scratch; reproduce with
the same function). With two **disjoint** lists of 10 documents each, where the single
correct answer is rank-1 in the graph list and appears in *no* keyword document:

```
RRF(kw1)      = 0.01639
RRF(ANSWER)   = 0.01639     <-- exact tie; ordering is arbitrary
=> ANSWER_DOC lands at rank 2 purely on tie-break
```

Four properties, each reproduced:

1. **A rank-1 hit in one list cannot outrank a rank-1 hit in another.** RRF is a
   Borda count; it rewards *agreement*, not quality. Disjoint lists ⇒ zero agreement
   ⇒ RRF degenerates to "interleave two lists."
2. **The 50/50 budget split is unconditional.** Measured: `{'keyword': 5, 'graph': 5}`
   — independent of relative arm quality. This **exactly reproduces** the 40/40
   (50%/50%) composition measured and reported in
   `RETRIEVAL-QUALITY-MEASUREMENT.md`. The documented 0.083 loss is this mechanism,
   and the doc's "budget-allocation problem, not a weighting problem" reading is correct.
3. **Weights cannot fix it.** At `weights=(3,1)`, `(10,1)`, `(100,1)` the answer is
   pushed *out* of the top-10 entirely (rank 11). Over-weighting the good arm simply
   evicts the other arm's contribution. There is no weight that recovers a disjoint
   list without also destroying it.
4. **k does not fix it.** k ∈ {5, 10, 60, 1000} — answer stays at rank 2 in every case.

**With overlap, RRF works fine** (also reproduced: a doc in both lists jumps to #1).
That is exactly the regime RRF was designed for, and it is *not* the regime
`hermes-brain --graph` operates in when the two arms disagree.

**The corpus itself already contains this analysis.**
`oracle/brain/research/bm25-normalization-failure-analysis.md` states the same
limination independently: *"Neither normalization nor RRF can retrieve documents that
BM25 misses. Both operate on the same candidate pool."* It also proves (Theorem +
proof, monotonic-transformation-invariance) that log/min-max/z-score normalisation
**cannot change top-k at all** — measured on N=50 questions, all five variants gave
*identical* Acc = 0.320. So re-weighting the graph signal on the existing candidate
set is provably futile. Only changing *which documents are candidates* can help.

### 6.2 Score fusion outperforming RRF — must be measured, not assumed

Hsu & Taksa, *"Comparing Rank and Score Combination Methods for Data Fusion in
Information Retrieval"*, **Information Retrieval (Springer) 2005**, DOI
`10.1007/s10791-005-6994-4` (148 citations) — the direct rank-vs-score comparison;
their result is that **score-based combination retains score-magnitude information
that rank-based fusion discards**, and wins when input lists are not of comparable
quality — precisely the hermes-brain case, where one arm is a 0.79-quality lexical
index and the other is a 0.08-quality hub lottery.

Also directly on point: Wang, Zhuang & Zuccon, *"BERT-based Dense Retrievers Require
Interpolation with BM25 for Effective Passage Retrieval"*, **SIGIR 2021**, DOI
`10.1145/3471158.3472233` (58 citations) — a strong dense retriever *fails* against
BM25 out-of-domain and is rescued only by **interpolation**, not by either method
alone. And the corpus's own measurement: hybrid RRF (BM25 + dense) gave
**+0.030 overall / +0.077 on multi-session** where BM25's lexical matching failed.

**Consequence for the design:** arm F **must** be reported as both `F-RRF` and
`F-ScoreFusion` (z-score or min-max per arm, then weighted sum, weights fitted on
`dev`). The corpus's formal result says monotone rescaling of one arm is provably
pointless, but *combining* two differently-normalised arms is not — the proof covers
single-arm rescaling, not cross-arm fusion. Do not collapse these into one row.

### 6.3 Reranking gains — the mandatory confound

- **DPR** (Karpukhin et al., **EMNLP 2020**, arXiv `2004.04906`): dense retrieval
  "outperforms a strong Lucene-BM25 system largely by **9%–19% absolute** in
  top-20 passage retrieval accuracy." (quoted from the paper's abstract)
- **ColBERT** (Khattab & Zaharia, **SIGIR 2020**, DOI `10.1145/3397271.3401075`,
  1,100+ citations): late interaction over BERT.
- **Sentence-BERT** (Reimers & Gurevych, **EMNLP 2019**, arXiv `1908.10084`): cuts
  BERT's 65 hours for a 10k-sentence nearest-neighbour search to ~11 seconds
  (abstract's figure), which is what makes dense retrieval *affordable* at 14.6k docs.
- **MTEB** (arXiv `2210.07316`): embedding-behaviour caveat — a single-task score does
  not predict general retrieval quality. Relevant to choosing the dense model.

**Consequence:** arm **D is mandatory**. If F (graph+lexical) beats B, D (hybrid +
cross-encoder) is the control that decides whether the graph earned it or a reranker
would have. A 10–20 point gain from reranking is well within the literature's normal
range, so omitting D makes a "graph win" uninterpretable.

### 6.4 Multi-hop evaluation precedent

HotpotQA (Yang et al., **EMNLP 2018**, arXiv `1809.09600`): 113k QA pairs built
specifically so that questions *require multiple supporting documents* and cannot be
answered from one — the same structural principle as §2.2's M1/M2, and the precedent
for treating multi-hop as a distinct, separately-powered category. The ACL Anthology
index for this corpus shows a large, active 2024–2026 literature on KG-grounded
multi-hop retrieval (e.g. *Query-Aware Graph Attention for Precise Subgraph Retrieval*,
Findings of ACL 2026; *TagRAG*, Findings of ACL 2026) — a graph that cannot be shown
to help here is not competing against nothing.

---

## 7. Graph-health gate (runs first; blocks the report)

The benchmark must not print retrieval numbers for a graph that is unhealthy. These
gates are cheap, deterministic, and must run first. They are also what would have
caught the two false claims in the current doc.

| Gate | Threshold | Rationale |
|---|---|---|
| **G1 Anchor coverage** | ≥ 95% of nodes carry a `source_file` **and ≥ 99% of those resolve to a real file** | Currently 99.3% / 100% — **passes**. This gate exists to catch the doc's false "0 of 20,199" claim automatically. |
| **G2 Hub concentration** | No single file contributes > 5% of nodes; report top-10 file shares | **Currently FAILS**: `GAP-ANALYSIS-ROUND3.md` = 522/20,199 = 2.6% of nodes but 522 of the highest-degree nodes; `Consciousness-Studies-Complete.md` = 430. Degree distribution must be reported. |
| **G3 Degree-bias probe** | PPR on 20 neutral seed queries: **effective rank concentration** (Gini of returned document scores) below a threshold | Directly measures the hub lottery seen in §0. |
| **G4 Path validity** | ≥ 0.9 of connections emitted by the CND metric have a verifiable relation in `graph.json` | CND(c) justification rate, computed every run. |
| **G5 Path-format** | All arms emit **the same canonical document ID** (content hash), never mixed absolute/relative paths | **Currently a live bug**: `graph_retrieval` returns paths relative to the *sub-vault* (`research/research_findings.md`) while the keyword arm returns absolute paths. These never match as strings, so `fuse()` and the top-10-overlap analysis were comparing incompatible identifiers. Must be fixed by canonicalising to content-hash IDs at the arm boundary. |

**G5 is the most important engineering item in this document.** Until every arm emits
the same identifier, no fusion and no overlap analysis is meaningful — including the
"found by both = 0%" row in the current doc, which is *at least partly* a path-format
artifact rather than a pure retrieval finding. (After normalising graph paths against
the correct sub-vault root I still measured 0 overlap, so the substantive finding
survives — but the measurement was previously incapable of distinguishing the two.)

**If any gate fails, the harness exits non-zero with the failing gate named** —
the same rule the existing script already applies for an absent corpus
(*"a measurement that measured nothing must not report success"*), extended from
"measured nothing" to "measured a broken thing".

---

## 8. Implementation checklist

1. Canonical document identity: `doc_id = sha256(normalised_body)[:16]`, computed
   once into `eval/doc_index.jsonl` with `{doc_id, path, title, body_len, mtime}`.
2. `eval/queries/{dev,test,challenge}.jsonl` — 300 total, per §2, each with
   `category`, `entities`, `bridge` (multi-hop only), `rationale`.
3. `eval/judgements/{doc_id}-graded.jsonl` — 2 labellers + adjudication, κ report
   committed alongside.
4. `eval/build_index.py` — body-only BM25 (frontmatter and `sources:` URLs stripped),
   dense index, graph index; all keyed on `doc_id`.
5. `eval/graph_health.py` — gates G1–G5. Exits non-zero on failure.
6. `eval/run_arms.py` — arms A–G. Every arm returns a list of `doc_id`s. **No arm
   may return a path or a string match.**
7. `eval/metrics.py` — nDCG@10, MRR@10, recall@10/@50, MAP, CND triple, judge
   scoring with the 10% human audit.
8. `eval/significance.py` — Wilcoxon + paired bootstrap (10k) + Holm–Bonferroni.
9. `eval/report.py` — refuses to print without arms A and B; prints split name and
   tuning-config hash on every number; prints the go/no-go rule from §4.3 verbatim.
10. Regression tests: a synthetic corpus with a known planted answer, asserting each
    arm's expected ordering, plus a negative test asserting the harness *fails* when
    a gate is violated (the current suite already tests the absent-corpus path —
    extend that pattern).

**Definition of done:** the harness runs end-to-end on a fixed, healthy graph and
prints a table containing A and B; the multi-hop lexical-ceiling gate (§2.2) passes;
and a graph change that *should* help moves the multi-hop nDCG@10 by a
Holm-corrected significant amount while the aggregate does not regress.

---

## Appendix — what I verified vs. what is design

**Verified against the repo/corpus:** the path-only keyword index; filename-substring
labels; oracle ≡ keyword; the false "0 of 20,199" node claim (actual: 20,067 with
`source_file`, 100% resolving); the hub-degree table; 19.9% zero-in-degree nodes;
217 `frontier-research-ontology-*` files; **zero** near-duplicate research pairs at
Jaccard > 0.6; the G5 path-format mismatch; the RRF disjoint-list properties
(computed).

**Verified bibliographically:** Cormack/Clarke/Büttcher SIGIR 2009; Järvelin &
Kekäläinen TOIS 2002; Hsu & Taksa IRJ 2005; Wang/Zhuang/Zuccon SIGIR 2021; Khattab &
Zaharia SIGIR 2020; Smucker/Allan/Carterette CIKM 2007; DPR EMNLP 2020; HotpotQA
EMNLP 2018; Sentence-BERT EMNLP 2019; MTEB; PyTerrier SIGIR 2021.

**Not yet run:** every number in this document. The thresholds in §4.3 and the
power arithmetic in §5 are design targets and must be re-derived from the first
100 dev queries before they are trusted. No retrieval result is claimed here.
