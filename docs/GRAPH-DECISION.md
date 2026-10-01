# Phase 4 — The Graph Decision

**Date:** 2026-09-26
**Status:** decided. Keep Graphify, as an associative-traversal view alongside
retrieval. Not a replacement, and not a default.
**Supersedes:** the "unresolved" framing in `research-resultideas.md` Part 8.

Every number below was measured on this machine on 2026-09-26, against the
graph built 2026-09-19. Nothing here is quoted from a paper without being
checked against the artifact it describes.

---

## The decision

**Keep the graph. Route between it and retrieval rather than choosing one.**

- **Direct lookup** (a single fact in one document) → retrieval. There is no
  published evidence that a graph beats hybrid retrieval here, and our own
  measurement agrees.
- **Multi-hop and cross-document association** → graph.
- **Default** → retrieval. The graph is consulted when retrieval's answer looks
  incomplete, not first.

This is a routing decision, not a ranking one. The graph is not competing to
return the best single document; it answers questions no single document
contains the answer to.

---

## What our own measurement says

Run against the vault the graph actually indexes, 2,104 files, 8 queries,
recall@10:

| arm | recall | note |
|---|---|---|
| full-context control | 1.000 | upper bound, not a measurement |
| body BM25 control | 0.046 | the floor that matters |
| **keyword** | **0.046** | |
| **fused** | **0.042** | |
| **graph** | **0.028** | |
| oracle | 0.068 | |

**Read: retrieval currently beats the graph on this corpus, and fusion is worse
than either.** That is the honest reading and it does not reverse the decision,
for reasons in the next section — but it does mean the graph is currently
earning nothing on direct lookup, which is exactly what the routing rule above
assumes.

The graph is not broken. It scored 0.000 for a while because the code read a
directory that never had a graph in it (fixed in `08042f4`). The current 0.028
is a real measurement of a real graph.

---

## Why keep something that currently scores lower

Three findings, in descending order of how much they should change your mind.

### 1. ~~Half the corpus is being silently truncated~~ CORRECTED — it is not

**This section was wrong when first written on 2026-09-26. A later read of the
installed source disproved it. The correction is kept rather than deleted,
because the original reasoning was reasonable and the error is instructive.**

The claim was that `_FILE_CHAR_CAP = 20_000` in `graphify/llm.py` truncates each
file before extraction, and that 48% of the corpus was therefore contributing at
most 20,000 characters.

**It does not.** The cap is a per-*slice* size limit, and oversized files are
pre-split so no content is lost. `llm.py:2619-2621`:

```python
# Split oversized splittable documents into slices that cover the whole file
# before packing, so content past _FILE_CHAR_CAP is extracted instead of
# silently dropped (#1369). Files at/under the cap pass through unchanged.
files = expand_oversized_files(files, _FILE_CHAR_CAP)
```

`slice_boundaries` returns **contiguous, gap-free, non-overlapping** ranges that
cover the whole text. Verified directly on this vault:

```
files checked (largest 250 of 1,017)   250
reassembled byte-for-byte identically  250
gaps, overlaps, or lost characters       0
```

A 540 KB file becomes 33 slices, median 5 for a typical large file, and all of
them are extracted. The `content[:_FILE_CHAR_CAP]` at `llm.py:633` is a no-op
for slices — the source comment says exactly that: *"slices are already bounded
to the cap, so the cap is a no-op."*

**Where the original reasoning went wrong:** it read the slice size limit as if
it were a whole-file size limit, and did not check whether oversized files were
pre-split. It also inferred "48% of the corpus is lost" from file sizes without
ever testing what the extractor actually receives.

**This is also a version fact, not a timeless one.** The graph was built by
graphify **0.9.46**; **0.9.67** is installed. The slicing fix (#1369) is present
in the installed version. Whether 0.9.46 sliced `.md` files — its splittable set
was `{.md,.mdx,.markdown,.txt,.rst}` — is the one thing that would determine
whether the *existing* graph was built from complete files. This corpus is 100%
`.md` plus two `.txt`, so it should have sliced correctly even then, but this has
not been confirmed against the 0.9.46 source.

**Net effect on the decision: none.** The reason for keeping the graph was that
its 0.028 was a floor measured on a truncated corpus. That premise is gone. The
0.028 is a real measurement, and the decision now rests on the association
argument below rather than on a defect.

### 1b. The real constraint is chunk locality, not the cap

The limit that *does* bind multi-hop is `--token-budget` (default 60,000).
`conceptually_related_to` is emitted by the LLM, and a prompt never contains two
chunks — so **relations between chunks are structurally invisible**. A concept
in slice 1 of a file and its referent in slice 9 are never co-visible.

Measured at the 60k budget on this corpus: 1,014 oversized files become ~2,628
units packed into ~168 chunks, and **991 of 1,014 oversized files have their
slices scattered across more than one chunk.**

This is a genuine relational-graph limitation, and it is a different one. The
knob that would address it is `--token-budget` (raise toward the model's
context) and `--mode deep` (adds INFERRED edges) — not the cap.

### 2. The graph captures association, which retrieval cannot

Edge relations actually present in the built graph:

```
references                19,203
conceptually_related_to    4,790
cites                      2,604
implements                 1,191
semantically_similar_to      529
```

That `conceptually_related_to` layer — 4,790 edges — is structure a keyword
index has no way to represent. It is the thing the graph is for, and it exists
regardless of the recall@10 number, which measures only single-document lookup.

Note also: **0 wikilink-derived edges.** The vault is full of `[[wikilinks]]`
and none appear as a distinct relation. Whether that is correct (links are
already captured as `references`) or a silent gap is unresolved, and is worth
one check before the next rebuild.

### 3. The negative result that constrains the design

AVA (arXiv 2609.00177) scored **0.739** on general triplet accuracy but **0.135
on hard negatives** — near random — over 171,007 triplets where anchor and
negative share ≥90% lexical similarity and differ only ontologically.
Fine-tuning reached near-perfect benchmark accuracy and **failed to transfer**.

Flat similarity retrieval cannot arbitrate whether two beliefs are the same
claim, and model scaling does not fix it. This is why the graph is kept at all:
it is a symbolic layer, and the symbolic layer is where identity arbitration
belongs. A pure-vector stack cannot do this job at any model size.

---

## What the plan document got wrong

The plan's Part 8 is the source for this phase, and two of its claims did not
survive checking against the code on this machine. Recording both so the next
reader does not re-investigate them.

### "Markdown extraction is unreachable on the normal path" — **no longer true**

The plan claimed `detect.py` classifies `.md` as DOCUMENT and `cli.py:3947`
only calls `_ast_extract` on code files, so `extract_markdown` is never reached
except via `watch.py`. It cited issue #2383 and PR #3614 as unmerged.

In the installed version:

```
extract.py:6678   ".md":  extract_markdown
extract.py:6679   ".mdx": extract_markdown
extract.py:6680   ".qmd": extract_markdown
```

`.md` is in the main extractor dispatch table. And the built graph confirms it
empirically — node types across 20,199 built nodes:

```
concept     16,218
document     2,377
paper        1,124
code           480
```

2,377 document nodes could not exist if markdown were being skipped. **Markdown
is being extracted.** The upstream defect appears fixed in this version.

### "_FILE_CHAR_CAP silently truncates every file" — **wrong, in this version**

The plan's version of this claim (a 229 KB file read to 8.7%) described a real
historical bug, fixed upstream as **#1369**. The installed 0.9.67 pre-splits
oversized files into gap-free slices covering the whole file, so no content is
dropped. The plan was written against the older behaviour.

I repeated this error in the first draft of this document, which is why the
correction is recorded above rather than quietly patched.

---

## The contradiction the plan asked us to settle

> LightRAG claims 67.6–84.8% win rates; the HippoRAG 2 paper's aligned
> reproduction scores it 16.6/2.4 direct and 1.6/11.6/2.4 multi-hop F1.

**Not settled here, and deliberately.** Both are third-party numbers about
LightRAG on someone else's datasets. Nothing in this repository can adjudicate
between them, and picking a side without running the comparison would be
asserting a preference as a finding.

What it does mean practically: **do not adopt LightRAG on the strength of its
own win-rate claim.** The reproduction in a peer-reviewed paper is 4–35× lower.
If LightRAG is ever evaluated here, evaluate it against the reproduction's
numbers as the prior, not the vendor's.

Similarly unresolved: whether 66.7% degrades to 39.06% under LLM-judge
order/length/trial correction. Same reasoning.

---

## Configuration defects to raise upstream

| item | evidence | status |
|---|---|---|
| `_FILE_CHAR_CAP = 20_000` | `graphify/llm.py:30`, `:2621` | **NOT a defect in 0.9.67.** Pre-slicing (#1369) means no content is dropped. Verified: 250/250 files reassemble byte-identically. |
| cap is not configurable | no `GRAPHIFY_*` env var overrides it; no config file loader | minor — but it should not need changing |
| cross-chunk relations invisible | 991 of 1,014 oversized files span >1 chunk at the 60k budget | **the real limitation.** Addressable via `--token-budget`, not the cap |
| no `wikilink` relation emitted | 0 in 28,946 edges | vault's own link structure may not be indexed as such |

The first two are retracted. The third and fourth stand.

---

## The deployment finding that must keep both gradings

The plan flagged this and it is worth repeating verbatim because it is easy to
half-remember:

Offline consolidation gated by surprisal has **six independent papers**
reporting trials on the mechanism. The locally-deployed instance prints a
complete, plausible config with `ENABLED = true` and
`TOP_PERCENT_SURPRISAL = 0.1` — and the same file records the dream cycle as
**404** and surprisal as **disabled**.

**Grade the design LOW. Grade the deployment UNTESTED and not running. Keep both
gradings permanently**, because a reader who sees only one will draw the wrong
conclusion in one direction or the other.

---

## What changes in the code

Routing, in `brain/cortex/wiring.py`, is where this becomes behaviour rather
than a document:

- `gate_associative_graph` already treats the associative graph as a **second
  candidate source, never a default** — it fires on the deliberative route or on
  a turn wide enough that one document is unlikely to hold the whole answer.
  That is the decision above, already implemented and already tested.
- Retrieval remains the default path. Nothing in this phase changes that.

## What does not change

- `~/.hermes/oracle/brain` is untouched. It is a 378-file partial copy; retiring
  it is a separate decision (organizer task 32).
- The Oracle graph rebuild job stays **off**. It is a week stale (organizer task
  31). Turning it on before the truncation defect is addressed upstream would
  spend tokens to rebuild a graph from a corpus that gets cut in half.
- `prose` and "free and local" do not apply. Markdown is 100% the expensive LLM
  pass; the free deterministic AST path is for code.
- The "13–22 hours" ingestion figure is the owner's own measured run. It is in
  no graphify doc, issue, or PR. Do not cite it as an upstream claim.

---

## Review trigger

This decision should be revisited when **any** of these becomes true:

1. A rebuild is run at a higher `--token-budget`, or with `--mode deep`. The
   graph's 0.028 was measured at the 60k default, where 991 of 1,014 large files
   have their slices split across chunks and relations between them are
   invisible. That is the most likely way this number improves.
2. The corpus grows substantially. Multi-hop needs enough documents for a path
   to exist; below some size it cannot pay.
3. A wikilink relation appears in the built graph, or its absence is explained.

Until then: retrieval by default, graph when the answer is not in one document.
