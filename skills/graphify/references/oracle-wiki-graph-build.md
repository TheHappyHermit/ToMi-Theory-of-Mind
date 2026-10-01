# Graph Build: Worked Example and Operational Notes

A record of one successful large-corpus graph build, kept because the *technique* is
non-obvious and the *failure modes* are easy to hit again. Corpus-specific figures and local
API-key status are deliberately omitted — they describe one install, not the method.

## The technique that matters: run the build through `execute_code()` + `subprocess`

A graph build over a large corpus runs for minutes. Invoking it directly through the terminal
gateway gets the process killed partway through (observed at roughly 60s), which wastes the run
and can leave a partial graph behind.

The reliable path:

1. Split the corpus into chunks, grouped by directory so related files stay together.
2. Dispatch all extraction chunks **in a single response** rather than sequentially.
3. Run the graph build itself through `execute_code()` wrapping `subprocess.run()`, which is
   not subject to the terminal gateway's time limit.

A build of this shape completed in well under a minute once moved off the terminal path.

## Chunking

- ~100 files per chunk is a reasonable starting point.
- Expect some chunks to fail on timeouts, and note that a chunk reported as timed out may
  still have succeeded — verify by inspecting the output before re-running.
- A partial build leaves behind **isolated nodes** (nodes with no edges) from the failed
  chunks. These are the visible symptom of an incomplete run, and they inflate the node count
  without contributing any relationships. Check for them before trusting a graph.
- Keep task strings small. A dispatch goal containing a large embedded file list can time out
  even when the subagent actually started.

## Interpreting the output

- Graphify writes relationships under a **`links`** key, not `edges`. Reading `edges` alone
  reports zero relationships for a perfectly good graph — this has caused a false "the graph
  is empty" diagnosis more than once in this project. Check both.
- A large fraction of edges may be marked `INFERRED` at a default confidence level. These are
  model-suggested links, not extracted ones; they are useful for navigation but should not be
  read as established relationships.
- Community cohesion varies widely. Low-cohesion communities are not necessarily errors.
- "God nodes" (very high degree) are expected in a knowledge graph, but they can dominate
  traversal — if retrieval starts returning one hub concept for unrelated queries, that is
  usually hub bias rather than a bug.
- A build produces a report, an analysis JSON, an extract JSON, and a detect JSON alongside
  the graph. The extract file is by far the largest and can dominate disk usage.

## Verification

```bash
python3 scripts/graphify_health.py
```

Reads both `edges` and `links`, reports node/edge counts and the edge-to-node ratio, and exits
non-zero on a graph that cannot be traversed. Run this after every build.

## Cost and failure modes

Extraction calls an LLM once per chunk, so cost scales with corpus size. A full semantic
extract of a large vault is a real token expense, not an incidental one — plan for it, and
prefer incremental `update` where the AST-only result is genuinely adequate. Provider credit
exhaustion mid-build is a common way for a large run to fail partway; check the quota before
starting, not after half the chunks return 403s.

See [graphify-refresh-pitfall.md](graphify-refresh-pitfall.md) for when incremental versus full
extraction is the right call.
