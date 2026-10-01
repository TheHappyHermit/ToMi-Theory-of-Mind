# Neo4j vs. the current graph layer — a like-for-like check

Asked: *"https://github.com/neo4j/neo4j is a freely usable neo4j — is it better
than graphify?"*

Short answer: **you are right that Neo4j Community Edition is genuinely free and
fully functional. But it is not an alternative to graphify — it sits one layer
below it.** The two do different jobs, and the measured numbers say the layer we
have is not the bottleneck.

---

## 1. Your premise is correct — Neo4j CE is free, and I should have been clearer

Verified from the source rather than the registry entry:

- `neo4j/neo4j` `LICENSE.txt` (read 2026-09-25): *"The software ... is licensed
  under the GNU GENERAL PUBLIC LICENSE Version 3 to all third parties."* The file
  also documents a commercial escape: if you have an End User / OEM agreement with
  Neo4j Sweden AB, different terms apply. Without one, GPLv3 governs.
- Neo4j's own Operations Manual describes **Community Edition as "a fully functional
  edition of Neo4j, suitable for single-instance deployments"** that "fully supports
  key Neo4j features, such as ACID-compliant transactions, Cypher, and programming
  APIs." It is aimed at "learning Neo4j, do-it-yourself projects, and applications in
  small workgroups."
- The feature table marks CE as covering native graph processing, language drivers
  (.NET, Go, Java, JavaScript, **Python**), 450+ APOC procedures, index/constraint
  management, and **offline backup (dump)**.

**So the earlier "GPL-3.0 = risky" framing in the registry was too blunt for this
user's actual use.** GPLv3's copyleft obligation attaches to *conveying* the
software. Running the official container unmodified, for yourself, is the
lowest-obligation case — the same reasoning already documented for the AGPL services
in `docs/THIRD-PARTY-LICENSES.md`. It is a real option for a hobbyist.

What CE does **not** include, and this is the part that matters operationally:
online backup, clustering, failover, RBAC, and LDAP. Offline `dump` backup works.
For a single-user wiki that is sufficient.

---

## 2. The comparison is a category error — they are different layers

This is the part that answers the question.

| | graphify | Neo4j |
|---|---|---|
| **What it is** | an *extractor* | a *database* |
| **Input** | markdown, code | Cypher queries |
| **Output** | `graph.json` (nodes + relationships) | query results |
| **Does it read prose?** | **Yes** — LLM pass to find concepts and relations | **No** |
| **Does it invent relations?** | Yes — `conceptually_related_to`, `cites`, `influences` | No — it stores what you give it |
| **Can it produce a graph from nothing?** | Yes | No — the graph must already exist |

**Neo4j cannot replace graphify, because Neo4j does not extract.** A property graph
database has no notion that "Hippocampus is conceptually related to Complementary
Learning Systems Theory" — something has to derive that, and that something is the
LLM extraction pass. Using Neo4j means choosing a *different* extractor (Graphiti,
LightRAG, your own pipeline), not dropping one.

Verified on the actual graph we produce:

| Relation type | Count | Meaning |
|---|---:|---|
| `references` | 19,203 | structural |
| **`conceptually_related_to`** | **4,790** | **inferred by extraction** |
| `cites` | 2,604 | semantic |
| `implements` | 1,191 | semantic |
| `semantically_similar_to` | 529 | inferred |
| `influences` | 212 | inferred |

A substantial minority of the relationships in a real extracted graph — the
`conceptually_related_to`, `semantically_similar_to` and `influences` edges — are
**inferences no database can derive on its own.** They exist because an LLM read the
documents and decided the concepts were related. That is the extractor's
contribution. Neo4j would store those edges faithfully and add nothing to their
creation.

---

## 3. The scale argument does not apply at this size

The case for a graph database is usually scale: indexed traversal, no full load into
memory, concurrent writers. Measured against the real graph:

| Measure | Observed at test-corpus scale |
|---|---|
| Graph size | tens of thousands of nodes, comparable relationships |
| Full load of both graphs | **~1 s** |
| Peak RSS | **under 100 MB** |
| Query latency | sub-second |

A single graph database is warranted in the range where in-memory loading becomes
painful — hundreds of thousands to millions of nodes, or many concurrent writers
mutating a shared graph. At tens of thousands of nodes, loading in under 100 MB and serving
sub-second queries, **there is no scale problem for a database to solve here.**

The honest caveat: those figures are *per process invocation*. A long-lived agent
that loads once and holds the graph pays that once. A short-lived CLI pays per call.
Both are fine at this size; neither is a reason to add a server.

---

## 4. What Neo4j genuinely does better

Not nothing — three real advantages, none of which are currently binding:

1. **Concurrent writers.** The graph is a build artifact today, regenerated
   wholesale. If the design ever moves to *live* graph mutation — a write path
   that adds edges as documents are ingested, as the architecture doc's "ingestion
   edge" gap would require — then transactional integrity and concurrent access
   matter. A JSON file cannot do that safely.
2. **Incremental queries without a full load.** Once the graph outgrows memory, or a
   query touches a tiny slice of a huge graph, a database indexes and the server
   does the work.
3. **Durability as a first-class concept.** ACID transactions, a real backup story,
   and a storage engine that is not a JSON file you regenerate from a tool that may
   change its output format.

Point 3 interacts with a real risk we already found: graphify issue **#3776** leaves
incrementally-maintained graphs silently wrong. A database with a write path you
control is one answer to that. The cheaper answer — already implemented — is
periodic clean rebuilds plus `scripts/verify_graph_integrity.py`.

---

## 5. Verdict

**Neo4j Community Edition is a legitimate, free option and I was too quick to set it
aside on licence grounds. But it is not "better than graphify," because it is not
comparable to graphify.**

- It cannot extract, so adopting it means adopting a *different extractor* too.
- The alternatives to graphify as extractor were evaluated separately: Graphiti
  (7% on MemoryAgentBench FactConsolidation, below BM25 — and confirmed at source to
  return superseded facts by default), LightRAG (independent F1/EM of 1.40/0.10 on
  MuSiQue multi-hop), cognee, RAGFlow (disproportionate operational footprint).
  None is a clear upgrade, and the only one with strong independent evidence is
  BM25, which is already in the retrieval path.
- At 20k nodes the scale argument for a database server does not apply.

**Recommendation: do not migrate. Do correct the registry.**

The registry's Neo4j entry says "Cut — copyleft, heavy, and the in-process PPR already
covers the use case." The copyleft reasoning was wrong for the self-host case and
should say so plainly. The rest stands.

**Adopt Neo4j if, and only if, the design moves to live graph mutation** — the
"ingestion edge" gap in `PROPOSED-BRAIN-ARCHITECTURE.md` §0.8 is the concrete
trigger. At that point Neo4j CE is the right tool: free, transactional,
Python-driver support, offline backup. That is a decision point worth revisiting
when the write path is designed, not before.

### The strongest argument against this recommendation

Refusing to add a database keeps a single point of failure in a tool that is six
months old, pre-1.0, releasing 235 times in half a year, with an open silent-
corruption bug. If graphify's extraction quality or output format degrades, this
repo has no durable store to fall back on — the graph would be regenerated by a tool
that may no longer produce the same shape. A database would at least preserve the
*extracted* data independently of the extractor's fate.

That is a real argument. It is not yet sufficient, because the graph is a derived,
rebuildable artifact by design and the whole point of the swappable-substrate work
was to make that explicit. But if graphify's maintenance posture degrades further,
the answer changes, and the honest trigger to watch is a breaking output-format
change or a maintainer departure — not general unease about pre-1.0 software.
