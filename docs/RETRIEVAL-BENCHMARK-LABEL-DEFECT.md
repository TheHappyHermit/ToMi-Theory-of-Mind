# Why the corrected benchmark reports a LOWER keyword score

**Date:** 2026-09-25
**Status:** Reproduced. Not a regression. The measurement instrument is the problem.

## The observation

After fixing `build_keyword_index` to read document bodies instead of only
filenames, keyword recall@10 dropped from **0.792 to 0.208** on the same 8
queries / 24 labels / 14,589 documents. Graph stayed at 0.083, fused 0.000.

A better retriever scoring much worse is only possible when the scorer is
measuring the wrong thing. It is.

## The mechanism

A relevance label is a **filename fragment** (`"thalam"`, `"schema"`,
`"counterfactual"`), and `is_relevant()` decides a hit by substring-matching that
fragment against a **returned path**.

So the benchmark only awards credit for returning *the file with that name*.

Worked example — query `"thalamus gating sensory attention"`, label `thalam`:

| Document | Mentions thalamus in body | Gets credit |
|---|---|---|
| `Attention-Mechanisms-Deep-Dive.md` | yes | **no** |
| `Targeted-Memory-Reactivation.md` | yes | **no** |
| `Francis-Crick.md` | yes | **no** |
| `Working-Memory-Update-Mechanisms.md` | yes | **no** |
| `Neural-Oscillations-and-Synchrony.md` | yes | **no** |
| `Thalamic-Reticular-Gating-Mechanisms.md` | yes | yes |

Across the whole Oracle Brain: **71 documents discuss the thalamus in their
text; exactly 1 has "thalam" in its filename.**

The old path-only index could only ever find that 1. It scored 0.792 because it
was playing to the label. The body-aware index returns five genuinely relevant
documents and is marked wrong on all five.

**The 0.792 was the benchmark grading itself.** A higher number now means a
retriever that has learned to match filenames.

## What this invalidates

- The old headline `keyword 0.792 / graph 0.083 / fused 0.708`.
- Any comparison of those numbers to published GraphRAG/RAG figures.
- The `oracle` strategy as a recall ceiling — it answers "did you return the
  file with this name", not "did you return a relevant document".

`MEASUREMENT_CAVEAT` in `scripts/measure_retrieval_quality.py` now carries this
warning in every JSON payload the script emits.

## What is still valid

- Corpus coverage (0.958) and document counts — those are facts about the corpus.
- The **fused-vs-keyword mechanism**: RRF gives each strategy its own rank range,
  so each takes ~half the top-k, and the two strategies agreed on **zero**
  results. That diagnosis is independent of the label problem and still stands.
- Graph recall is genuinely low, but **this instrument cannot tell you by how
  much**, because a body-correct document may be scored as a miss for the graph
  too.

## The fix required before any number is quotable

Hand-label relevance against document *content*, not filenames. A label should
be a document path a human judged relevant after reading it. Concretely:

1. Sample candidates per query by pooling results from every strategy
   (keyword, graph, fused) so the label set is not biased toward one retriever.
2. Have a human or a strong model read each candidate and mark it relevant or not.
3. Keep the pooling step in the script so the judgement set is reproducible and
   extendable as queries are added.
4. Report per-query misses so a bad label is visible rather than averaged away.

Until that exists, treat these numbers as a smoke test that the pipeline runs and
loads a real graph — not as a quality measurement.
