---
name: version-aggregation
description: Use when deciding how a wiki document's currency is tracked, or when retrieval may return superseded content. Deterministic current-value filtering, not LLM judgement.
---

# Version Aggregation

How the repo marks which version of a document is current, and why it is
deterministic rather than model-judged.

## The rule

**Superseded documents stay in the graph. They are marked, not deleted, and the
marker is filterable.**

Three frontmatter fields, all optional, all plain strings/dates:

```yaml
---
updated: 2026-09-25T14:30:00Z        # RFC 3339 UTC, when the content last changed
status: superseded                    # currency axis: is this still live?
supersedes: "[[2026-08-14-foo]]"      # wiki-link to the note this replaces
---
```

`status` defaults to `active` when absent. A document with no `status` is current.

### Two separate axes

`status` in the live vaults is overwhelmingly a **maturity** marker
(`complete`, `completed`, `verified`, `published`), not a **currency** marker. The
first version of the checker conflated the two and would have misfiled 207 live
notes. Only the currency axis should ever drive a retrieval filter.

| Axis | Meaning | Values | Drives a filter? |
|---|---|---|---|
| **Currency** | is this still the live version? | `superseded`, `deprecated`, `archived`, `retracted`, `obsolete`, `stale` | **Yes — this list only** |
| Maturity | how finished is it? | `complete`, `completed`, `verified`, `published`, `draft`, `draft-v2`, `paused` | No |
| Current/live | unremarkable | `active`, `current`, `stable`, `living`, no `status` at all | No |

An unrecognised value is treated as **current** — deliberately fail-open, so a typo
can never hide a live note. `scripts/check_version_convention.py` reports unknown
values so typos get fixed rather than silently published.

Verified against the live vaults: 0 false positives, and real errors (a misspelled
`archieved`, a space-separated timestamp) are still caught.

## Why deterministic

A 2026 peer-reviewed study (Reddy & Challaram, arXiv:2606.01435) evaluated
published memory systems on MemoryAgentBench's FactConsolidation task, where the
same fact appears with contradictory values:

| System | FC-SH |
|---|---:|
| HippoRAG-v2 | 54.0% |
| BM25 | 48.0% |
| Mem0 / Contriever | 18.0% |
| Zep / Graphiti (purpose-built temporal KG) | 7.0% |

The system designed for temporal memory scored lowest. Their reported mechanism:
free-text LLM judgement fails at conflict resolution when freshness is entangled
with retrieval noise. Moving the comparison into deterministic code scored
**80.8% vs 61.0%** at matched chunking.

Their recommendation to framework designers, verbatim:

> "Do not assume graph or knowledge-graph infrastructure alone solves conflict
> resolution... conflict resolution is not a sufficient reason on its own without an
> explicit version-aggregation step."

## Why not a temporal knowledge graph

Checked directly in `graphiti-core` v0.30.2
(`graphiti_core/search/search_filters.py`): `valid_at`, `invalid_at`, `expired_at`,
and `created_at` all declare `default=None`. A search with no filters returns
invalidated and expired edges. The bi-temporal data is stored; the current-only view
is not applied for you.

For this repo's corpora, git already provides version aggregation exactly, with
author and timestamp, addressably. A temporal graph re-derives it at inference cost.

See `docs/GRAPH-SUBSTRATE-EVALUATION.md` for the full comparison.

## Applying it in retrieval

When returning documents, treat `status` as a filter, not a ranking hint:

1. If the query implies currency ("what is", "how do I", "current"), drop
   `status: superseded` before ranking.
2. If the query is explicitly historical ("what did I decide in June"), do **not**
   drop them — that is the point of keeping them.
3. When a superseded note is returned anyway, say so. A note marked superseded is
   evidence about the past, never about the present.

`git log -p --follow <file>` remains the authoritative history for any single
document. The frontmatter fields exist so that *retrieval* can filter cheaply
without shelling out to git.

## Pitfalls

- **Do not use an LLM to decide whether a document is current.** That is the exact
  failure the benchmark measures. Read the field.
- **Do not delete superseded notes.** They are the `supersedes` target and the
  reason history is navigable at all.
- **Do not invent a status value.** `active`, `draft`, `superseded`, `retracted`.
  Anything else is treated as `active` by default, so a typo silently publishes a
  dead note as current.
- **Timestamps are RFC 3339 UTC** (`YYYY-MM-DDTHH:MM:SSZ`). Never
  `datetime('now')`-style space-separated output; mixed formats silently break
  sorting.
