---
name: brain-search
description: >-
  Use when the operator says "brain search", "search my brain", "find me notes on X",
  or "what do I have on X" — also proactively before asserting a non-trivial
  detail or writing a new note. Hybrid BM25 + vector search over the active
  wiki and Oracle vault.
platforms: [telegram, cli]
tags: [knowledge, search, brain, wiki, notes]
---

# Brain Search — Hybrid BM25 + Vector Search

Search your personal knowledge bases (Active Wiki + Oracle Brain) using hybrid full-text and semantic search with Reciprocal Rank Fusion.

## When to Use

Trigger when the user asks variations of:
- "Find me notes about X"
- "Search my brain for X"
- "What do I have on X?"
- "Brain search: X"
- "Do I have any notes about X?"
- "What did I write about X?"

**Also trigger proactively** (don't wait for the user to ask "search my brain"):
- An entity (person/company/project/place) is the **subject** of the message
- A name or term appears that you **don't recognize** and looks notable
- You're about to **assert a non-trivial detail** about an entity (attribution, status, history) — verify against the brain first
- You're about to **write new notes** — query first to find existing content and avoid duplication
- A brain-page pointer appears in context (the deterministic layer told you the page exists) — open it before relying on details

**Skip** trivial passing mentions, logistics pings, and anything already loaded in context.

## Prerequisites

1. `brain-postgres` Docker container running on `127.0.0.1:5433` (verify: `docker ps | grep brain-postgres`)
2. `pg8000` in the **system** `python3` — no venv needed (verified 1.31.5)
3. **Embedding server on `http://{LAN_IP}:18082`** — llama.cpp, OpenAI-compatible
4. Brain synced (`python3 "$HOME/scripts/brain_sync.py"`)

> **Not Ollama.** This skill used to say the embedding model was Ollama's
> `qwen3-embedding:8b` on `localhost:11434`. That is wrong now and the
> troubleshooting table still carried it. Ollama is not running on this box and
> brain search works fine. The default in `brain_query.py` is
> `http://{LAN_IP}:18082` via `INFERENCE_EMBED_URL` / `BRAIN_OLLAMA_URL`.
> The env var names still say "ollama" — that is legacy naming, not a hint
> that Ollama is involved.

## How to Search

> **Use the repo copy** — it is the maintained one:
>
> `$HERMES` below is your home directory. It is **not** `${HERMES_HOME}`, which
> is the config dir (`~/.hermes`) and would resolve to
> `~/.hermes/hermes-brain/...` — a path that does not exist.

```bash
python3 "$HOME/hermes-brain/scripts/brain_query.py" "query here"
```

> **Do not run `~/.hermes/scripts/brain_query.py`.** It is a 2026-09-07 copy
> that predates deduplication and returns the *same page twice* in the top
> results, which reads as two independent matches. The repo copy is the
> maintained version. If you must use the `~/.hermes` copy, treat duplicate
> paths in one result set as a copy defect, not as evidence.

With a source filter (`active-wiki`, `oracle-brain`, `exchange-research`):
```bash
python3 "$HOME/hermes-brain/scripts/brain_query.py" "query" --source oracle-brain
```

With custom top-k:
```bash
python3 "$HOME/hermes-brain/scripts/brain_query.py" "query" --top 5
```

### Graph layer — the cheap path

`--graph-only` needs **no database and no embedding server**, and is much
faster for relationship questions ("what is connected to X"). Verified live:
the active wiki has 737 nodes and the Oracle 23,315.

```bash
python3 "$HOME/hermes-brain/scripts/brain_query.py" "query" --graph-only --graph-top 5
```

Graph traversal returns *neighbours*, not semantic matches — a 1-hop result is
a link, not an answer. Use it for relationship context, not for "find the note
about X"; for that use the hybrid path.

## Retrieval Depth (Escalate Only As Needed)

1. **Pointer / metadata** — if a pointer is already in context (slug + one-line summary) and the task only needs identity, stop there.
2. **Full page** — when the entity is the subject or details matter, read the full page from the source wiki.
3. **Linked neighbors** — only when relationship context is needed, pull related pages via graphify or backlinks.

**Resolve only the name(s) the current task needs, use them, drop them.** No bulk-loading.

## Miss ≠ Absence (CRITICAL)

**A Brain Search miss does NOT prove that knowledge does not exist.** If brain search returns nothing:

1. **Don't say "I couldn't find anything"** — instead say "Brain Search didn't return results, let me check the source"
2. **Fall back to ripgrep:**
   ```bash
   rg -i "query" ~/.hermes/oracle/brain/
   rg -i "query" ~/.hermes/active-wiki/
   ```
3. **Fall back to direct page read** if you know the slug
4. **Only report absence** after exhausting all fallback methods

## Output Format

Each result includes:
- `source`: which knowledge base (`active-wiki` or `oracle-brain`)
- `title`: page title
- `slug`: file path within the source
- `chunk_text`: relevant text snippet
- `rrf_score`: combined relevance score

Format results concisely:

```
1. [oracle-brain] AI Safety and Alignment (AI-Safety/Alignment.md)
   Score: 0.0164
   <relevant snippet text>

2. [active-wiki] Homelab Infrastructure (homelab/infrastructure.md)
   Score: 0.0079
   <relevant snippet text>
```

**Always show the source** (`[active-wiki]` or `[oracle-brain]`) so the user knows where the result came from. Always show the file path so the user can open the full page if needed.

## Troubleshooting

| Symptom | Real cause and fix |
|---------|-------------------|
| `[error] Ollama embed failed` | **Misleading label** — the code path is generic. The real endpoint is llama.cpp at `{LAN_IP}:18082`. Check it: `curl -s http://{LAN_IP}:18082/v1/models`. If it is down, the hybrid path fails; `--graph-only` still works. |
| "Cannot connect to Postgres" | `docker ps \| grep brain-postgres` — container publishes `127.0.0.1:5433`. If absent: `docker compose -f "$HOME/hermes-brain/docker/docker-compose.brain.yml" up -d` |
| "No results found" | Index is stale. Resync: `python3 "$HOME/scripts/brain_sync.py" --source active-wiki` |
| `relation "brain_search" does not exist` | Schema not applied. Run the brain compose file, then resync. (Note: the chunks table is `embeddings`, and the page table is `pages` — there is no `brain_chunks` table.) |
| `pg8000 is not installed` | System `python3` lacks it. Do **not** create a venv — install into the interpreter you will actually run: `python3 -m pip install --user pg8000` |
| Same page returned twice | You ran the stale `~/.hermes/scripts/` copy. Use the repo copy. |
| `cd: ~/hermes-brain: No such file or directory` | This repo is gone. This skill no longer uses it. |

## Architecture

Brain Search uses:
- **llama.cpp on the inference node** (`{LAN_IP}:18082`) for embedding, via
  the OpenAI-compatible `/v1/embeddings` endpoint. Truncated to 2000 dimensions
  client-side, since llama.cpp does not take Ollama's `dimensions` parameter.
- **PostgreSQL + pgvector** for vector storage (HNSW index) and full-text
  search (GIN index), on `brain-postgres` at `127.0.0.1:5433`.
  Tables: `pages` (3,278 rows), `embeddings` (47,982 chunks), `sync_state`
  (freshness ledger), `conversation_history` (query log).
- **RRF fusion** (Reciprocal Rank Fusion) to combine BM25 and vector results.
- **Graphify** for the `--graph-only` path — a derived index over the same
  corpus, no embedding round-trip required.

Index freshness (2026-09-30): active-wiki 963 pages, oracle-brain 2,314 pages,
both last synced 2026-09-30 07:38 UTC.

The database is a **derived index** — if it breaks, it can be rebuilt from the
canonical Markdown corpus at any time. The Markdown is the source of truth;
`brain_sync.py` and `graphify` are both reconstructible from it.
