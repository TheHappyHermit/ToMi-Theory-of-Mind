# Graph Ingestion Bugs — Verified Against Source

**Date:** 2026-09-25
**Status:** All four confirmed by reading code + graph files directly. Not inferred.
**Authority:** `~/.hermes/oracle/brain/decisions/graphify-extract-not-update.md` (2026-09-10)
already established the extract-vs-update rule. The repo does not follow it.

---

## BUG 1 — `refresh_graphify.py` runs the command the vault says destroys the graph

**File:** `scripts/refresh_graphify.py:76`

```python
cmd = ["graphify", "update", str(source)]
```

**Why it's wrong.** The wiki decision record `graphify-extract-not-update.md` says:

> `graphify update` performs AST-only extraction — it parses markdown structure
> (headings, links, code blocks) but ignores semantic relationships
> ... For wiki corpora, AST-only extraction produces a near-empty graph because
> the semantic content (concepts, ideas, relationships) is what makes the wiki valuable

This is not theoretical. `concepts/graph-collapse-recovery.md` records the actual
incident: the Active Wiki graph went **4,393 nodes / 4,418 links → 68 nodes / 0 edges**
in a single refresh cycle, on 2026-09-09, caused by exactly this command.

The same decision record names `refresh_graphify.py` as the file that was fixed.
**The fix is not in the repo.** The repo version still runs `graphify update`.

**Fix:** use `graphify extract` with the flags the decision record specifies:
`--token-budget 16000 --max-concurrency 1 --no-cluster` (plus the repo's existing
`--api-timeout`).

---

## BUG 2 — Same file, plus two sibling scripts pass `--force`

**Files:**
- `scripts/graphify_active_wiki_py.py:71` — `'--force'`
- `scripts/graphify_oracle_brain_py.py:78` — `'--force'`

**Why it's wrong.** `system/graphify-policy.md` states the rule without exception:

> **Never use `--force`** — always incremental

`--force` skips both the manifest gate and the semantic cache reads, so a routine
refresh re-pays full LLM cost. Upstream Graphify issue **#3776** (confirmed OPEN) is
directly relevant: `--force` over a directory loses **64** cross-file edges, versus 0
on a clean rebuild — and the loss leaves no trace in `graph.json`.

**Fix:** remove `--force`. Use incremental extract.

---

## BUG 3 — Every edge count in the refresh scripts is silently zero

**Files:**
- `scripts/refresh_graphify.py:73` and `:94`
- `scripts/graphify_active_wiki_py.py:111`
- `scripts/graphify_oracle_brain_py.py:119`

All four do:

```python
edges = data.get("edges", [])
```

**Graphify writes relationships under `links`, not `edges`.** Verified on the real
active-wiki graph file:

```
keys: ['directed', 'multigraph', 'graph', 'nodes', 'links', 'hyperedges', 'built_at_commit']
nodes: 2535   edges-field: 0   links-field: 4440
```

So a **perfectly healthy 4,440-edge graph reports "0 edges."**

This is the exact failure already documented in
`concepts/graph-collapse-recovery.md` under "Prevention":

> Status cron must read `data["links"]` — wiki graphs store connections in `links`,
> not `edges`

`scripts/graph_retrieval.py` gets this right (line 146:
`raw.get("links") or raw.get("edges")`). The refresh scripts do not.

**Why this matters beyond cosmetics:** a health check that always reports 0 edges
cannot detect the 4,393 → 68 collapse it was built to catch. The check passes
vacuously.

**Fix:** `data.get("links") or data.get("edges", [])` everywhere.

---

## BUG 4 — `graph_retrieval.py` points at the wrong vault location

**File:** `scripts/graph_retrieval.py:50-68`

```python
return (Path.home() / ".hermes").resolve()
ACTIVE_WIKI = ... HERMES_HOME / "active-wiki"
ORACLE_BRAIN = ... HERMES_HOME / "oracle" / "brain"
```

The graphs actually live under `~/.hermes/`, not `~/.hermes/`. Verified:

```
active-wiki  /home/operator/.hermes/active-wiki/graphify-out/graph.json   exists=False
oracle-brain /home/operator/.hermes/oracle/brain/graphify-out/graph.json  exists=False
```

**Effect:** with no env override set, `Graph.load()` returns `False` with
`reason='no graph at ...'`, and the graph retrieval path yields zero results. Any
caller that does not check `.loaded` will report "no results found" rather than
"the graph failed to load." These are different failures and must be distinguishable.

**Fix:** default to the real path, or fail loudly when the graph is absent rather
than returning empty. `multi_hop_search` should surface `reason` to the caller.

---

## Why the existing benchmark cannot see any of this

`scripts/measure_retrieval_quality.py` — the benchmark that concluded the graph
"makes retrieval worse."

**Bug 5 (confirmed, highest impact).** `build_keyword_index` indexes **file paths only,
never document bodies**:

```python
for i, doc in enumerate(docs):
    # Index the path (not the body) so this stays fast on a large vault.
    for tok in set(tokenize(str(doc))):
        index[tok].add(i)
```

Meanwhile every one of the 24 relevance labels is a filename-shaped substring
(`"Implementation-Intentions"`, `"thalam"`, `"default-mode"`, `"retrieval-induced"`).

So the "keyword" arm is **filename matching scored against filename labels**, while
the graph arm resolves through real content provenance. The comparison is not
like-for-like. Verified: 97 of the first 6,000 corpus files mention "thalamus" in
the body; the index cannot see any whose filename lacks the string.

**Bug 6.** The "oracle" ceiling is computed by the *same* substring rule as the
labels:

```python
return [str(d) for d in docs if is_relevant(d, relevant)][:top_k]
```

An oracle derived from the identical matching rule is not an independent ceiling.
The reported "keyword achieves the oracle ceiling" is a tautology.

**Consequence:** the published result — keyword 0.792, graph 0.083, fused 0.708 —
does not establish that the graph degrades retrieval. It establishes that
filename-matching beats concept-provenance on filename-shaped questions. **All
three numbers are void pending a corrected benchmark.**

Per the owner's ruling: a broken benchmark cannot condemn a working tool. Fix the
ingestion bugs (1–4) and the benchmark (5–6), then measure.
