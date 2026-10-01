# Dependency Health Registry

Machine-readable inventory of every third-party project this repo names, bundles, or
recommends. Sourced from the GitHub REST API and PyPI on **2026-09-25**.

This exists because prose goes stale. The evaluations in `docs/` carry the reasoning;
this file carries the measurements, so a refresh can diff against it instead of
re-deriving everything.

**Fields**

- `role` — what this repo uses it for
- `bundled` — does this repo ship a compose file or install path for it
- `tier` — `foundation` (load-bearing), `component` (swappable service), or
  `evaluated` (considered, not shipped)
- `licence` — SPDX id, with `notes` where the API is ambiguous
- `risk` — `low` / `medium` / `high`, with the single deciding reason
- `open_issues` — note that GitHub's `open_issues_count` **includes pull requests**,
  so it overstates the bug backlog. Treat as activity, not defect count.

---

## Tier 1 — Foundations (load-bearing; breakage here breaks the repo)

| Project | Role | Bundled | Stars | Contributors | Created | Last push | Licence | Risk |
|---|---|---|---:|---:|---|---|---|---|
| `NousResearch/hermes-agent` | host agent | yes | — | — | — | — | — | n/a — this *is* the host |
| `pgvector/pgvector` | vector index in Postgres | via image | 23,155 | 23 | 2021-04-20 | 2026-09-22 | PostgreSQL | **low** |
| `plastic-labs/honcho` | episodic/social memory | **yes** | 7,331 | 61 | 2023-09-10 | 2026-09-24 | **AGPL-3.0** | **high** |
| `Graphify-Labs/graphify` | concept-graph extraction | **yes** | 121,244 | 260 | **2026-04-03** | 2026-09-23 | Apache-2.0 | **high** |

### Notes

**pgvector** — 23 contributors for 23k stars is a concentration signal, but this is
what a mature, stable, narrowly-scoped C extension looks like: it does one job, it
has done that job since 2021, and it is still getting commits. Low risk *because* it
is small and boring, not despite it. API reports `NOASSERTION`; the actual licence is
the PostgreSQL Licence (permissive).

**Honcho** — post-1.0 on PyPI (`honcho` 2.0.0), 1–5 releases/month, self-hostable,
and every LLM subsystem takes a per-module `BASE_URL` override naming Ollama/vLLM,
so the full memory stack runs locally at no API cost. **AGPL-3.0** is the caveat:
self-hosting for yourself is unobligated, but shipping it inside a distributed
product or offering it as a hosted service triggers source disclosure. Documented in
`example.env` and `docs/MEMORY-SUBSYSTEM-EVALUATION.md`.
Risk **HIGH — raised from medium on 2026-09-25 after verified data-loss bugs.**
The deciding reason is no longer licence or benchmark position; it is that the
project burns queued work after roughly 90 seconds of LLM-provider unavailability
and has no recovery path:

- **#1236** — `MAX_RETRYABLE_ATTEMPTS = 3` at 1 s backoff on a 30 s poll. Past the
  cap, items are marked `processed=true` with an error, and the poller filters on
  `processed` only. Never derived again, and `queue/status` reports
  `completed == total` the whole time. Verified in the source: the behaviour is
  *asserted* by their own test
  (`test_retry_exhaustion_is_terminal`, docstring: "At the attempt cap a transient
  error burns the first item exactly like today's terminal path"), so it is a
  product decision and will not be fixed incidentally.
- **#989** — semantic dedup soft-deletes then hard-deletes the incumbent on a score
  tie (`>=`), and the agent-tool path hardcodes `deduplicate=True`. Long-standing,
  reproduced on two versions.
- **#1230** — the deriver persists its own few-shot examples as facts about real
  peers; deleting the bogus conclusions is not durable.

An API provider having a bad afternoon is not exotic. **Mitigation, not removal:**
`scripts/memory_event_log.py` provides an append-only, idempotent, client-id-keyed
log written *before* handing anything to Honcho, plus a `reconcile` command that
reports what was sent but never derived — precisely the signal Honcho's own status
endpoint omits. Replay converts unrecoverable loss into a retry.

See `docs/MEMORY-SUBSYSTEM-EVALUATION.md` for the full addendum, including a
retracted claim: the "post-1.0, calm cadence" evidence originally cited here came
from the **wrong PyPI package** (`honcho` is an unrelated Foreman clone). The real
package is `honcho-ai` 2.5.1, Apache-2.0, 1–2 releases/month — so the cadence
intuition survives, but the original evidence did not.

**graphify** — high risk despite enormous adoption signals. Deciding reasons:
1. Repository is **under six months old** (created 2026-04-03).
2. **235 PyPI releases in six months**, ~89 in April alone, still 0.9.x.
3. **Open issue #3776**: incremental `--update` silently loses cross-file edges
   (`--force` does not repair it; only a clean rebuild does). A silently wrong graph
   is worse than a loudly absent one.
4. Tests and CI *are* real and good (retracted an earlier claim to the contrary) —
   the problem is that both are six months old too.

Not disqualified, but **not load-bearing**. Treated as a derived, rebuildable,
disposable artifact. See `docs/GRAPH-SUBSTRATE-EVALUATION.md` and
`scripts/verify_graph_integrity.py`.

---

## Tier 2 — Bundled components (swappable services)

| Project | Role | Bundled | Stars | Contributors | Created | Last push | Licence | Risk |
|---|---|---|---:|---:|---|---|---|---|
| `mendableai/firecrawl` | web scraping | **yes** | 184,407 | 166 | 2024-04-15 | 2026-09-25 | **AGPL-3.0** | **high** |
| `searxng/searxng` | metasearch | **yes** | 37,614 | 278 | 2021-04-12 | 2026-09-23 | **AGPL-3.0** | **medium** |

### Notes

**firecrawl** — highest star count of anything in this registry and a paid cloud
exists alongside the OSS core, so the open question is whether the self-hosted path
is feature-complete or a trial. **AGPL-3.0**, and it is a heavy footprint (browser
automation plus supporting services) relative to what a hobbyist needs for a search
fallback. Highest-risk bundled component. **Flag for a docs warning.**

**searxng** — mature (2021), 278 contributors, single container, genuinely
self-hostable. **AGPL-3.0** like firecrawl. Medium risk, dominated by the same
licence question plus upstream search-engine breakage, which is inherent to
metasearch rather than a defect.

Both AGPL projects: running them yourself for your own use carries no obligation.
Redistributing them inside a product, or offering them as a hosted service, does.
**Not legal advice — a lawyer should confirm before commercial redistribution.**

---

## Tier 3 — Local inference (recommended to avoid paid APIs)

| Project | Role | Stars | Contributors | Created | Last push | Licence | Risk |
|---|---|---:|---:|---|---|---|---|
| `ollama/ollama` | local model serving | 181,660 | 451 | 2023-06-26 | 2026-09-25 | MIT | low |
| `vllm-project/vllm` | local model serving | 92,651 | 452 | 2023-02-09 | 2026-09-25 | Apache-2.0 | low |
| `BerriAI/litellm` | model proxy | 59,583 | 374 | 2023-07-27 | 2026-09-25 | **unresolved** | **medium** |

### Notes

**Ollama / vLLM** — both enormous contributor counts, both pushing same-day. vLLM
targets GPUs; Ollama targets consumer hardware. Either removes API cost, which is the
point of recommending them. `open_issues` of 8,372 (vLLM) and 4,076 (Ollama) are
dominated by feature requests and support load, characteristic of projects this size
— not a defect signal on their own.

**LiteLLM** — API reports `NOASSERTION` for the licence, which is **unresolved and
must be settled before it is named in a permissive repo.** Separately, a proxy sits
in the path of every model call, making it a single point of failure; its
self-hosted failure modes need documenting.

---

## Tier 4 — Evaluated, not shipped

| Project | Why considered | Stars | Licence | Verdict |
|---|---|---:|---|---|
| `neo4j/neo4j` | graph store | 17,258 | **GPL-3.0** Community | **Not cut on licence grounds** — CE is free and fully functional; see below |
| `getzep/graphiti` | bi-temporal KG | 31,144 | Apache-2.0 | Not adopted — see temporal findings. Open #1911: 242/686 episodes produced zero edges, no retry |
| `getzep/zep` | commercial host of graphiti | 4,931 | Apache-2.0 | **Community Edition abandoned upstream** — README: "no longer supported". Never describe Zep as self-hostable |
| `mem0ai/mem0` | agent memory | 65,963 | Apache-2.0 | Not adopted — contested benchmark position, see below |
| `FalkorDB/FalkorDB` | graph backend for graphiti | 6,292 | SSPLv1 (server) | Not adopted — licence, plus documented correctness bugs |
| `kuzudb/kuzu` | embedded graph backend | 4,025 | MIT | **DEAD — archived upstream 2025-10-10** |
| `HKUDS/LightRAG` | GraphRAG | 39,847 | MIT | Not adopted — weak independent multi-hop numbers |
| `infiniflow/ragflow` | RAG service | 91,281 | Apache-2.0 | Not adopted — disproportionate operational footprint |
| `topoteretes/cognee` | memory/graph | — | Apache-2.0 | Not adopted — same tier as honcho, less evidence |
| `OSU-NLP-Group/HippoRAG` | retrieval algorithm | 4,022 | MIT | Not bundled — version `2.0.0a5`, no CI, 15 contributors, one lab. Cite as prior art, don't depend on it |

### Notes

**Kuzu is archived.** Verified 2026-09-25: `archived: true`, last push 2025-10-10,
and its own README opens "We are archiving the KuzuDB project here" / "Kuzu is
working on something new!" with no replacement named. Nothing in this repo's code
depends on it. **Any doc still listing it as a live option is wrong.**

See `docs/neo4j-vs-current-graph.md` for the full layer-by-layer comparison.

**Neo4j Community Edition — licence risk CORRECTED.** An earlier version of this
registry cut Neo4j partly on copyleft grounds. That was too blunt for the
self-hosting case, and the correction matters:

- `neo4j/neo4j` `LICENSE.txt` is GPLv3, with a documented commercial escape if you
  hold an End User/OEM agreement with Neo4j Sweden AB.
- Neo4j's Operations Manual calls CE "a fully functional edition of Neo4j, suitable
  for single-instance deployments," supporting ACID transactions, Cypher, the
  language drivers (including Python), 450+ APOC procedures, and **offline backup**.
- GPLv3's copyleft obligation attaches to *conveying* the software. Running the
  official container unmodified for yourself is the lowest-obligation case — the
  same reasoning documented for the AGPL services in `docs/THIRD-PARTY-LICENSES.md`.
- CE omits online backup, clustering, failover, RBAC and LDAP. Fine for one user;
  not fine for a multi-tenant service.

**Not adopted anyway, but for a different reason: it is a different layer.** Neo4j is
a graph *database*; it does not extract concepts from prose. Adopting it means also
adopting a different extractor. And at the graph sizes this repo works with
(20k nodes, 96 MB resident, 1.1 s to load both graphs, sub-second queries) there is
no scale problem for a database server to solve.

**Revisit trigger:** if the design moves to *live* graph mutation — a write path
that adds edges as documents arrive — then transactional integrity and concurrent
writers become real requirements, and Neo4j CE is the right tool. Full analysis in
`docs/neo4j-vs-current-graph.md`.

**Graphiti** — Apache-2.0 and the strongest conceptual fit, but the bi-temporal
capability that justifies it is measured at **7.0%** on MemoryAgentBench
FactConsolidation, *below BM25's 48%* (arXiv:2606.01435). Verified at source:
`graphiti-core` v0.30.2 declares `valid_at`/`invalid_at`/`expired_at`/`created_at`
all as `default=None`, so a search with no filters returns superseded facts.

**mem0** — Apache-2.0 with 404 contributors, but the repo's own knowledge base
records third-party BEAM numbers of 0.282 (100K) and 0.303 (500K) with cost rising
$1.70 → $9.37. Directional, since those are a competitor's numbers, but not a
position worth adopting over Honcho.

**HippoRAG** — 15 contributors, 9 open issues, one lab (OSU-NLP). A research
artifact whose *algorithm* this repo borrows (graph + personalized PageRank), not
software to deploy. The repo implements PPR directly in
`scripts/graph_retrieval.py`.

---

## Refresh procedure

```bash
# Star/contributor/licence snapshot for every registry entry
python3 scripts/refresh_dependency_health.py
```

That script re-queries the GitHub API and prints a table diffed against the values
above, so drift is visible rather than assumed. It is deliberately **not** wired
into a cron: dependency health is reviewed, not auto-accepted, and a silent update
to a licence field should never land unattended.

## What is deliberately absent

No node counts, corpus sizes, or vault statistics. Those describe one person's
install and are meaningless — and actively misleading — to a repo reader.

---

## Correction: `open_issues_count` includes pull requests

GitHub's `open_issues_count` field counts **issues and pull requests together.**
This changes how any issue-count column in this registry should be read.

| Repo | `open_issues_count` | Issues | PRs |
|---|---|---|---|
| `getzep/zep` | 39 | **0** | 39 |
| `getzep/graphiti` | 518 | 284 | 234 |
| `OSU-NLP-Group/HippoRAG` | 9 | 8 | 1 |
| `BerriAI/litellm` | 5,256 | 1,747 | 3,509 |
| `vllm-project/vllm` | 8,372 | 2,505 | 5,867 |
| `ollama/ollama` | 4,076 | 2,510 | 1,566 |

Two consequences:

- **Zep's apparent "39 open issues" is zero issues.** For a project whose
  user-facing edition is unsupported, that is the expected signature, not a quality
  signal.
- **vLLM's 8,372 is mostly pull-request volume.** An earlier note in this repository
  described that number as "activity, not defects" while acknowledging it was
  inferred. It is now verified from the actual split — the conclusion holds, but on
  real evidence rather than an assumption.

`scripts/refresh_dependency_health.py` should record the issues/PRs split, not the
aggregate, when the API response exposes it. Until it does, do not compare issue
counts across repos without checking which field was read.

Full evidence in [DEPENDENCY-AUDIT.md](DEPENDENCY-AUDIT.md).
