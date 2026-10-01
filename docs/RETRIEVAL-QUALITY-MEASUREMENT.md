# Retrieval Quality — the first measurement

**Date:** 2026-09-25
**Tool:** `scripts/measure_retrieval_quality.py`
**Corpus:** 14,589 markdown files, both graphs loaded
**Judgement set:** 8 hand-checked queries, 24 relevant-document labels

This is the number the project did not have. Until now the graph layer had been
verified to *run* — a two-hop walk checked by hand, a query path returning
connected documents with the path that reached them. Nothing had measured whether
adding it makes retrieval better.

---

## The result

Recall@10, meaning: of the documents a person marked relevant, how many appear in
the top ten results.

| Strategy | recall@10 | matched | corpus coverage |
|---|---|---|---|
| **keyword only** | **0.792** | 19/24 | 0.958 |
| graph only | 0.083 | 2/24 | 0.958 |
| **fused (what `--graph` does)** | **0.708** | 17/24 | 0.958 |
| oracle (coverage ceiling) | 0.792 | 19/24 | 0.958 |

**Fusing the graph makes retrieval worse, not better.** It loses 0.083 recall to
keyword search alone — roughly one relevant document in twelve.

The keyword baseline already achieves the oracle ceiling, so nothing is
outranking it. The graph is not adding recall; it is taking up room.

## The mechanism, measured

The fusion's top-10 across all eight queries:

| Where the result came from | Slots | Share |
|---|---|---|
| keyword only | 40 | 50% |
| graph only | 40 | 50% |
| found by both | 0 | 0% |

**Reciprocal rank fusion gives each strategy its own rank range, so each takes
roughly half the budget.** When the graph's half contains nothing relevant, it
displaces keyword hits that were scoring.

Note the last row: **the two strategies never once agreed.** They are not
corroborating each other. They are competing for the same slots.

This is a budget-allocation problem, not a weighting problem. Weighting the
keyword side higher would recover the loss by giving up the graph's multi-hop
reach instead — which is the thing the graph was added for.

## Why the graph scores 0.083 — a structural finding

This is not a misconfiguration and no amount of tuning fixes it. Two measured
facts:

**1. No node carries a file reference directly.** 0 of 20,199 nodes in the oracle
graph have a `file` or `source_file` field. A document is findable only if the
walk happens to land on a node that links *to* it.

**2. Document nodes are sinks.** The node representing the implementation-
intentions note has **11 outgoing `cites` links and 0 incoming** — a document
cites its sources, and nothing cites the document. Across the whole graph, 19% of
nodes have no incoming edge at all.

Personalised PageRank spreads mass outward from the seeds. For a natural-language
query the seeds are **concept** nodes — "Prospective Memory", "Gollwitzer (1999)
Implementation Intentions". Mass concentrates on concepts, and the document
containing the actual answer ranks below them:

```
0.16462  Implementation Intentions (Gollwitzer)      <- a concept
0.05219  Prospective Memory Cueing                   <- a concept
0.04646  Michael Graziano                            <- a concept
...
         [the citing document does not appear]
```

The target document was not merely missed at depth 2. It was absent at depths 1,
2, 3 and 4, and the node is definitely in the graph with degree 11.

**The graph is good at finding related concepts and weak at returning the document
a person wants to read.** Those are different jobs, and only the first one was
ever going to score well on a document-retrieval benchmark.

## What this does and does not say

**It does not say the graph is useless.** The path
`Hippocampus → Complementary Learning Systems Theory → Research Findings` is real
and took effort to build. Multi-hop reach is a genuine capability; it just does
not show up as *document recall*, which is what this benchmark measures.

**It does not say the sample is large enough to be sure.** Eight queries is small.
It can show a clear difference — and a 0.083 versus 0.792 gap is clear — but it
cannot establish one. A real evaluation wants dozens to hundreds of queries with
independently-labelled relevance.

**It does say the default is wrong.** The README describes the graph as a
fallback and `brain_query.py` exposes `--graph` as opt-in, which is defensible.
What is not defensible is any claim that the graph *improves* retrieval. That
claim does not currently have evidence behind it, and this is the evidence.

## Recommendation

**Do not enable the graph by default. Do not remove it.**

- Keep it available and keep the integrity checker. The capability is real and the
  cost of keeping it is low.
- Stop describing it as improving retrieval until a larger evaluation says so.
- If the graph's recall is to be raised, the fix is structural, not a setting:
  rank **document** nodes rather than concept nodes, or aggregate a concept's
  score onto the documents that cite it. Both are design changes.

## Two bugs this measurement caught in itself

Both are the same failure mode — a benchmark that looks like it ran while
measuring nothing or asserting a cause it had not checked.

**1. The corpus filter rejected dot-prefixed paths.** `iter_documents` filtered on
the absolute path, so any vault under `~/.something` returned zero documents. On
that search happened not to have a dot-prefixed *component* — the leading dot
was in a parent directory, which the relative-path check ignores. **Had the
vault sat under a dot-prefixed directory, it would have reported a confident
result having read nothing.** Caught by the self-test, which builds its
corpus in a temporary directory and therefore does have one.
in the parent directory, not a path component, so it happened to work. **Under a
dotted home directory it would have reported a confident result having read
nothing.** Caught by the self-test, which builds its corpus in a temp directory.

**2. The verdict asserted a cause.** The first version printed "fusion is
diluting the keyword result" as a conclusion. The actual cause is budget
allocation, and it is only distinguishable by looking at the top-k composition.
The script now reports the composition instead of asserting a mechanism.

**Both are now regression-tested** in `tests/test_measure_retrieval.py` (20 tests).
The general rule, and the reason the script exits 2 on an absent corpus: *a
measurement that measured nothing must not report success.*

## Reproducing

```bash
HERMES_HOME=<vault root> python3 scripts/measure_retrieval_quality.py
python3 scripts/measure_retrieval_quality.py --json
python3 scripts/measure_retrieval_quality.py --self-test
```

Not on cron. A retrieval benchmark needs a stable, versioned judgement set and a
corpus that does not move underneath it; a weekly run would mostly report corpus
churn.

## What would make this a real evaluation

1. **More queries.** Dozens minimum, ideally a few hundred.
2. **Independent labels.** Written by someone who did not build the retrieval
   system, or at least not by whoever tunes it.
3. **A held-out split.** Tune fusion weights on one set, report on another.
4. **Multi-hop-specific queries.** A document-recrieval benchmark structurally
   favours keyword search, because keywords are what documents contain. To test
   whether multi-hop helps, the queries must be ones whose answers require
   connecting documents — that is the only condition under which the graph layer
   can win, and this benchmark does not currently create it.
