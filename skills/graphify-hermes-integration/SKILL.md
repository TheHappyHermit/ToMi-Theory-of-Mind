---
name: graphify-hermes-integration
description: "Graphify as derived index in Hermes Brain with two graphs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [graphify, project, knowledge-graph, derived-index, retrieval-hierarchy]
metadata:
  hermes:
    related_skills: [graphify-semantic-ingestion, graphify-operations, wiki-ingestion, wiki-maintenance]
---

# Graphify Cortex Integration

Patterns for integrating Graphify as a **derived relationship/connectivity index** (not a canonical memory store) into the project cognitive architecture.

## Core Principle

> **Graphify is a derived index — disposable, rebuildable, and optional. If deleted, corrupted, stale, or unavailable, ALL underlying knowledge remains intact in the Markdown wikis.**

## Two Separate Graphs (Never Merged)

| Graph | Source Wiki | Temperature | Queried By | Refresh Cadence |
|-------|-------------|-------------|------------|-----------------|
| **Main Graph** | `/home/{USER}/.hermes/active-wiki/` | Hot/current | Main Hermes, Planner | Frequent (days/weeks) |
| **Oracle Graph** | `/home/{USER}/.hermes/oracle/brain/` | Cold/historical | Oracle Profile | Infrequent (weeks/months) |

**Critical**: Main and Oracle graphs are **logically separate** and **never automatically merged**. This preserves the hot vs cold knowledge hierarchy.

## Retrieval Hierarchy (Graphify is Optional/Specialized)

```
1. Structured task/date/state query → Honcho/SQLite/Personal Organizer
2. Main knowledge query → Active Wiki (ripgrep first)
3. Relationship/multi-hop question → Main Graphify (optional, specialized)
4. Need older/long-term knowledge → Oracle
5. Oracle relationship/multi-hop → Oracle Graphify (optional)
6. Still missing → Research Hermes
7. New durable knowledge → Canonical Wiki
8. Refresh derived graphs
```

**When to use Graphify**: Relationship/multi-hop questions ("What connects X to Y?", "How does this concept relate to others?", "Trace the flow from A to B through Z")

**When NOT to use Graphify**: Simple fact lookup, exact page retrieval, structured queries, autobiographical queries

## Fallback Behavior (NON-NEGOTIABLE)

If Graphify is unavailable, stale, returning no result, or returning incorrect results:

### Main Graph Fallback Order
1. Ordinary wiki search (`ripgrep /home/{USER}/.hermes/active-wiki/`)
2. Direct Markdown/source inspection
3. Oracle (if appropriate)
4. Research Hermes

### Oracle Graph Fallback Order
1. Ordinary wiki search (`ripgrep /home/{USER}/.hermes/oracle/brain/`)
2. Direct Markdown/source inspection
3. Brain Search semantic/hybrid retrieval (via brain-query skill)
4. Raw evidence search (`/home/{USER}/.hermes/oracle/raw/`)
5. Research Hermes

**CRITICAL**: A Graphify failure or empty result MUST NOT be interpreted as proof that information does not exist. Never say "the knowledge does not exist" solely because Graphify failed to find it.

## Ingestion Pipeline

### Main Graph (Active Wiki)
```bash
# Full semantic run — uses the Python wrapper (sets env vars + API key internally)
python3 ~/.hermes/scripts/graphify_active_wiki_py.py
# Or via the shell wrapper for manual runs:
bash ~/.hermes/scripts/graphify_active_wiki.sh
# Output lands in: /home/{USER}/.hermes/active-wiki/graphify-out/
```

### Oracle Graph (Oracle Wiki)
```bash
# Full semantic run
python3 ~/.hermes/scripts/graphify_oracle_brain_py.py
# Or via the shell wrapper:
bash ~/.hermes/scripts/graphify_oracle_brain.sh
# Output lands in: /home/{USER}/.hermes/oracle/brain/graphify-out/
```

**Current extraction parameters (both graphs):**
- `--token-budget 16000` — proven sweet spot for wiki corpora
- `--max-concurrency 1` — required for local llama.cpp backend
- `--api-timeout 1800` — per-chunk timeout
- `--no-gitignore --force` — re-scan all files
- `--backend vllm_qwen36_nothink` — custom provider (see LLM Backend Configuration below)
- Clustering **enabled** — Leiden community detection runs after extraction

**Do not** hand-run `graphify extract` with `--out .../graphify-main-out` or `--out .../graphify-oracle-out` — those paths are stale. Always use the scripts above.

### Long-Running Extraction Pattern

Graphify extraction on a full wiki takes hours. The Python wrapper scripts use `subprocess.Popen` + a streaming thread so output is written to the log **in real time** — not buffered until the process finishes (the old `capture_output=True` pattern hid all progress until completion, making runs look stuck).

Watch progress with:
```bash
tail -f ~/.hermes/logs/graphify-active-wiki.log
```

## LLM Backend Configuration

### Custom Provider: vllm_qwen36_nothink (REQUIRED)

Thinking-capable models (Qwen3.6) emit reasoning in `reasoning_content` by default, wasting tokens and sometimes leaving `content` empty. The solution is a **custom Graphify provider** that passes `chat_template_kwargs: { enable_thinking: false }` per-request — no server restart needed.

**Register the provider** (one-time setup):
```bash
mkdir -p ~/.graphify
cat > ~/.graphify/providers.json << 'EOF'
{
  "vllm_qwen36_nothink": {
    "base_url": "http://{LAN_IP}:8080/v1",
    "default_model": "/models/Qwen3.6-35B-A3B-Q4_K_M.gguf",
    "env_key": "GRAPHIFY_VLLM_QWEN_API_KEY",
    "temperature": 0.2,
    "max_tokens": 98304,
    "vision": false,
    "extra_body": {
      "chat_template_kwargs": {
        "enable_thinking": false
      }
    }
  }
}
EOF
```

**Set the API key** (the provider reads this env var; scripts set it internally):
```bash
export GRAPHIFY_VLLM_QWEN_API_KEY="***"
```

**Verify the provider is registered:**
```bash
graphify provider show vllm_qwen36_nothink
```

**Verify thinking is actually disabled** (before running a full extraction):
```bash
curl -s http://{LAN_IP}:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ***" \
  -d '{
    "model": "/models/Qwen3.6-35B-A3B-Q4_K_M.gguf",
    "messages": [{"role": "user", "content": "Think step by step: 60 mph + 80 mph trains 210 miles apart, when do they meet? Show reasoning."}],
    "temperature": 0.2,
    "max_tokens": 256,
    "chat_template_kwargs": {"enable_thinking": false}
  }' | python3 -c "import json,sys; d=json.load(sys.stdin); m=d['choices'][0]['message']; print('content:', repr(m.get('content','')[:80])); print('reasoning_content:', repr(m.get('reasoning_content','NOT PRESENT')[:80]))"
```

Expected: `content` has the answer, `reasoning_content` is NOT PRESENT.

**Confirm llama.cpp supports `enable_thinking: false`** — test with a reasoning prompt both with and without the flag. Without it, Qwen3.6 puts everything in `reasoning_content` and `content` is empty. With it, `content` has the answer and `reasoning_content` is absent. This was verified on the llama.cpp server at `{LAN_IP}:8080`.

### Environment Variables (Python wrapper scripts)

The Python wrapper scripts (`graphify_active_wiki_py.py`, `graphify_oracle_brain_py.py`) set env vars internally before launching graphify:

```python
os.environ['GRAPHIFY_VLLM_QWEN_API_KEY'] = '***'
os.environ['GRAPHIFY_MAX_OUTPUT_TOKENS'] = '131072'
os.environ['GRAPHIFY_MAX_RETRIES'] = '0'
os.environ['GRAPHIFY_API_TIMEOUT'] = '1800'
```

**Do NOT set `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, or `GRAPHIFY_DISABLE_THINKING`** — those were for the old `--backend openai` pattern. The custom provider carries its own base_url, model, and `enable_thinking: false` via `extra_body`. Setting the old vars alongside the new provider can cause conflicts. See `references/graphify-custom-provider.md` for the full setup and verification procedure.

### HARD RULE: Local Llama.cpp Only

Graphify runs ONLY on the local llama.cpp server at `http://{LAN_IP}:8080/v1` (`/models/Qwen3.6-35B-A3B-Q4_K_M.gguf`). It must NEVER fall back to OpenRouter, and it must NEVER use the desktop 3090 (`localhost:1234` / `{LAN_IP}:1234`) — that GPU is reserved for OpenCode / desktop-researcher. The custom provider and wrapper scripts bake in this constraint.

## Verification Protocol (DISK CHECK — Exit Code 0 ≠ Success)

> **⚠️ STALE-REPORT TRAP**: Graphify can leave `GRAPH_REPORT.md` with OLD mtime while re-extracting only a handful of files.

```bash
# Active wiki graph
OUT=/home/{USER}/.hermes/active-wiki/graphify-out
ls -la --time-style=full-iso "$OUT/GRAPH_REPORT.md"
find "$OUT/cache/semantic" -type f | wc -l
grep "semantic extraction on" /home/{USER}/.hermes/logs/graphify-active-wiki.log

# Oracle brain graph
OUT=/home/{USER}/.hermes/oracle/brain/graphify-out
ls -la --time-style=full-iso "$OUT/GRAPH_REPORT.md"
find "$OUT/cache/semantic" -type f | wc -l
grep "semantic extraction on" /home/{USER}/.hermes/logs/graphify-oracle-brain.log
```

**Success indicators**: edges > 0, communities > 0, semantic_similar_to edges > 0 for wikis.

## Clustering and Semantic Similarity

### What `--no-cluster` Actually Controls

**It does NOT control semantic similarity.** The `semantically_similar_to` edges that let Hermes traverse related concepts across files are created during the LLM `extract` pass — present whether `--no-cluster` is set or not. Those edges go into `graph.json` either way.

**What `--no-cluster` skips:** Leiden community detection — the step that groups nodes into topic clusters by edge density and generates the cluster report.

### Current Setting: Clustering Enabled

`--no-cluster` has been **removed** from both ingestion scripts. Communities are generated so Hermes can see topic structure across the wiki.

### No Embeddings Needed

Graphify does **not** use embeddings for anything — including clustering. Communities are found via the Leiden algorithm over graph topology (edge density) alone. The semantic similarity edges created by the LLM during extraction are already in the graph and influence community shape directly.

From the Graphify docs: "No embeddings needed. The semantic similarity edges that Claude extracts (`semantically_similar_to`) are already in the graph, so they influence community shape directly. The graph structure is the similarity signal — there's no separate embedding step or vector database."

### For Hermes Traversal of Ideas

The cross-concept edges (`semantically_similar_to`, `references`, `implements`, etc.) are what matter for traversal — and they come from the LLM extract pass, not from clustering. Removing `--no-cluster` adds community structure and a human-readable report, but doesn't change what Hermes can traverse.

## Sync Schedule

**Every night** (or after significant changes):
- If Active Wiki changed → incremental Main Graph update (AST only)
- If Oracle Wiki changed → incremental Oracle Graph update (AST only)

**Weekly**:
- Full Main Graph semantic refresh (with cache clear)
- Full Oracle Graph semantic refresh (with cache clear)

Use Hermes no-agent cron. No LLM needed for incremental.

## Query Operations

### Main Graph (Main Hermes / Planner)
```bash
graphify query "How does X connect to Y?" --graph /home/{USER}/.hermes/graphify-main-out
graphify explain "concept-name" --graph /home/{USER}/.hermes/graphify-main-out
graphify path "node-a" "node-b" --graph /home/{USER}/.hermes/graphify-main-out
```

### Oracle Graph (Oracle Profile)
```bash
graphify query "Trace compliance flow from A to B" --graph /home/{USER}/.hermes/graphify-oracle-out
graphify explain "historical-concept" --graph /home/{USER}/.hermes/graphify-oracle-out
graphify path "node-x" "node-y" --graph /home/{USER}/.hermes/graphify-oracle-out
```

## Related Skills

- `graphify-semantic-ingestion` — backend config, cache management, verification (in hermes-laptop/default)
- `graphify-operations` — query patterns, traversal, troubleshooting
- `wiki-ingestion` — feeds Active Wiki that Main Graph indexes
- `wiki-maintenance` — archives Active Wiki into Oracle Wiki

## Pitfalls

### AST-Only Refresh Produces Useless Graphs
The `refresh_graphify.py` cron runs `graphify update` which does incremental AST extraction only. For markdown wikis this produces graphs with 0 edges and 0 communities — functionally useless. A full semantic run with `graphify extract --backend openai --model <model-id>` is required for wiki corpora. See `references/graphify-refresh-pitfall.md` for the detailed troubleshooting guide, verification steps, and cadence recommendations.

### refresh_graphify.py Only Covers Active Wiki
The `refresh_graphify.py` script hardcodes `WIKI_DIR = ~/.hermes/active-wiki`. It does NOT refresh the Oracle Brain graph. To refresh Oracle Brain, use the canonical script:
```bash
bash ~/.hermes/scripts/graphify_oracle_brain.sh
```

For a cron job that refreshes BOTH graphs, create a wrapper script or use the individual `.sh` scripts.

## References

- `references/graphify-custom-provider.md` — custom provider setup, thinking-disable verification, env var cleanup
- `references/graphify-refresh-pitfall.md` — AST-only refresh pitfall (0 edges), full semantic run procedure, verification, cadence
- Graphify repo: https://github.com/Graphify-Labs/graphify