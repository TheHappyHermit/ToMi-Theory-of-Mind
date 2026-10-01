---
name: oracle-routing
description: Oracle retrieval protocol — Graphify graph first, ripgrep fallback, evidence-preserving.
---

# Oracle Routing

## Oracle Retrieval Order

1. **Brain Search semantic/hybrid retrieval** — best for concept-level questions
2. **Brain Search lexical/entity retrieval** — best for specific names/paths
3. **Literal ripgrep against Oracle Markdown** — best for exact text/UUID
4. **Direct page read** — best for known page slugs
5. **Raw-evidence search** — best for source verification
6. **MISS or STALE** — only when all methods exhausted

## Oracle Output Contract

```
STATUS: FOUND | PARTIAL | MISS | STALE
FRESHNESS: <date or "unknown">
ANSWER: <concise synthesis>
IMPORTANT_DETAILS: <bullet list>
SOURCE_PAGES: <list of page slugs>
RAW_EVIDENCE_REFERENCES: <citations>
EPISTEMIC_STATUS: <provenance class>
UNCERTAINTY: <high/medium/low>
NEEDS_RESEARCH: yes | no
```

## Important
A graph miss does NOT prove absence. Always try ripgrep fallback.
GBrain was removed from the deployment and is not coming back. It used to hold
the first two positions in this order. There is no GBrain step to wait on, and
a GBrain miss is no longer a possible result — if the graph returns nothing,
go straight to ripgrep, then report MISS.

## Retrieval Depth
- Simple historical question: 8K-20K evidence if required
- Normal synthesis: up to ~25K
- Complex synthesis: 20K-40K
- Exceptional deep history: 40K-60K when justified
- Stop when sufficient evidence exists
