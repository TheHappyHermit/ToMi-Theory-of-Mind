# Graph Substrate Evaluation — 2026-09-25

Decision record for the tool that indexes the wiki vaults into a knowledge graph
and feeds multi-hop retrieval. Written because the incumbent was never formally
evaluated: it was installed, and its output was assumed good.

**Scope note.** This evaluates the tool as a *foundation for a public open-source
repo* that other people install and depend on over time — not as a convenience
for one existing machine. Stability, maintenance risk, and third-party evidence
are first-order. A working local install is not evidence of fitness.

---

## Evidence gathered

### GitHub / PyPI project health

| Tool | Stars | Contributors | Open issues | License | Archived |
|---|---:|---:|---:|---|---|
| RAGFlow | 91,281 | 454 | 1,510 | Apache-2.0 | No |
| LightRAG | 39,847 | 314 | 278 | MIT | No |
| Graphiti | 31,144 | 63 | 518 | Apache-2.0 | No |
| Neo4j | 17,258 | 255 | 242 | **GPL-3.0** (Community) | No |
| FalkorDB | 6,292 | 67 | 917 | NOASSERTION | No |

Contributor figures are page-count from the GitHub API `contributors` link header.
**Neo4j Community Edition is GPL-3.0** — a licence obligation for a permissive
project, and the reason "just use Neo4j" is not a free choice.

### graphify — the incumbent, measured directly

Source: the installed wheel (`graphifyy` 0.9.67, PyPI) and the PyPI release API.

| Property | Value | Read |
|---|---|---|
| Version | 0.9.67 | **pre-1.0**, no stability guarantee |
| Licence | Apache-2.0 | Permissive ✓ |
| Total releases | 235 | — |
| Releases/month | Apr 2026: **89**, May: 54, Jun: 28, Jul: 28, Aug: 22, Sep: 14 | **Extreme churn** |
| Code size | 92 modules, 73,806 lines | Substantial |
| Test modules in the wheel | **0** | Correct, but see correction below |
| CI in the repository | `.github/workflows/ci.yml` runs `pytest tests/` on py3.10 + 3.12 | **Yes — I was wrong to imply otherwise** |
| Largest module | `extract.py` — **8,736 lines** (396 KB) | Monolith |
| Other large modules | `extractors/engine.py` 366 KB, `cli.py` 233 KB, `llm.py` 162 KB | — |

The source is genuine, not minified (46 bytes/line average, readable docstrings).

### CORRECTION (2026-09-25, second pass)

The first version of this document said graphify had "zero test modules" and used
that as evidence of poor discipline. **That was misleading, and I retract the
implication.** The measured fact is only that the *published wheel* ships no test
modules. The *repository* has a real `tests/` tree and a CI workflow
(`.github/workflows/ci.yml`) that installs with `.[mcp,pdf,watch]` and runs
`python -m pytest tests/ -q` on a Python 3.10 / 3.12 matrix, plus an end-to-end
install check. It also runs on `v1` and `main`, on both push and pull_request.

Tests and CI are the *strongest* part of this project. The concern is not
discipline; it is that test coverage and maintenance history are both six months
old, and that the open bugs below are in the layer tests are not catching.

### Open upstream bugs that affect a knowledge graph

Both verified by reading the issues directly, not from a summary.

**#3776 — incremental `--update` silently loses cross-file edges. OPEN.**
A graph maintained with `--update` ends up missing edges a clean build produces.
Measured on a ~130-file Python project: clean rebuild 0 missing edges, `--update`
**65 missing**, `--force` **64 missing**; only deleting `graphify-out` and
rebuilding reaches 0. The report is explicit that this leaves no trace in
`graph.json`, so a consumer cannot detect it: "the loss is silent: nothing in the
output indicates the graph is incomplete, and `graph.json` gives a consumer no way
to tell." Missing edges included 41 `imports`, 19 `imports_from`, 5 `calls`.
A consumer walking those relations "can produce false negatives — a reachability
query returning 'no path' when a path exists in the source."

**#3105 — a 570-node graph silently overwritten with 111. FIXED in v0.9.51.**
Hollow LLM responses were not counted as incomplete, so a run could discard ~80% of
nodes with `exit code 0, no warning`. Maintainer fixed it two days after the
report. Worth recording as evidence *for* the project: a user filed a precise
reproduction, and it was patched in 48 hours.

Also reported: #3616 (failed chunks reported as successful omissions), #3702
(extract_pdf_text returns `""` when the optional pdf extra is missing, so every PDF
becomes an empty document), #1805/#1568/#1742 (upgrading the package leaves the
installed skill at the old version), #2279 (fresh install `ImportError: AnyUrl`).

**Benchmark numbers are self-produced.** `BENCHMARKS.md` on the `v8` tag reports
LOCOMO QA accuracy 45.3%, recall@10 0.497, LongMemEval-S 76%, and states plainly
"graphify's own harness," with competitors run as adapters inside it using a shared
Kimi K2.6 model. The judge was blind-validated against a second judge (90.6%
agreement, Cohen's kappa 0.81) — better practice than most published benchmarks.
But no independent validation exists.

### Acting on it: a graph trust checker

Because a degraded graph is structurally indistinguishable from a good one, node
and link counts prove nothing. `scripts/verify_graph_integrity.py` checks the
things that actually discriminate: build provenance against corpus HEAD, source
freshness, files that existed at build time but contributed nothing, dangling
link endpoints, edge density, and an unconditional warning that #3776 is
undetectable by construction. 17 tests cover it.

### What it found on a real corpus

On its first run against a real corpus, it found a non-trivial share of source files
(single-digit percent) that **existed at build time but contributed no nodes** — not
stale files, but files extraction had already seen and produced nothing from, which
is the #3105 signature. A further group of files were simply newer than the build
and not indexed yet, which is normal and is reported separately at `info` level
rather than being conflated with a real gap.

That distinction is the point of the staleness split. The first version of the
checker reported both groups as one warning, which would have misled in both
directions: alarming about files that were not yet due, and quiet about the ones
that genuinely were dropped.

Structurally, that graph was otherwise sound — no dangling endpoints, no empty
labels, a healthy edge:node ratio, and `built_at_commit` present (#3354 is fixed).
The verdict was nonetheless **needs a clean rebuild**, because a structurally
perfect graph can still be semantically wrong.

Exact corpus figures are omitted deliberately: they describe one person's vault and
mean nothing to a repo reader. The method is the transferable part — run the
checker, and treat a non-zero exit as a rebuild instruction.

### Graphiti — the strongest alternative on paper

From the project's own research dossier (`active-wiki/research/graphiti-temporal-knowledge-graph.md`,
2026-09-17), which catalogues nine open issues:

- **#1166 — node attributes are destructively overwritten.** Edge validity windows work;
  node attributes do not. Cannot query a node's historical state. **Open, acknowledged
  as a feature gap, not a bug.**
- **"Deleted facts survive summaries"** — invalidated edges are still counted as active
  evidence in community summaries. A known semantic gap.
- **#1325** — FalkorDB single-group queries silently return empty results.
- **#1505** — NaN/Inf embeddings silently break entity deduplication.
- **#1506** — FalkorDB edge fulltext timeouts. Open.
- **#1513** — orphan task in `Neo4jDriver.init`. Open.
- Kuzu backend **deprecated — and KuzuDB itself is now ARCHIVED upstream.** Verified
  2026-09-25: `kuzudb/kuzu` has `archived: true` and its own README opens with
  "We are archiving the KuzuDB project here" and "Kuzu is working on something new!"
  The replacement is not named, the final release is 0.11.x, and prior releases
  "will continue to be usable" but receive no development. Anything still listing
  Kuzu as a live backend option is listing a dead one.

Graphiti is the only option in this set with a bi-temporal model. That is a real
capability, and the dossier is explicit that it is also the reason it exists.

---

## What the bi-temporal model is actually worth

The honest version: **partially worth it.**

Graphiti versions *edges* — each fact carries a validity window, so "this was
superseded" is recorded. What it does not reliably version is *nodes* (#1166) or
*derived summaries* (deleted facts still counted as evidence). So a temporal query
against Graphiti is trustworthy at the fact level and unreliable at the derived level.

This project already decided the same thing independently, in
`PROPOSED-BRAIN-ARCHITECTURE.md` §3.1.1: *"bi-temporal invalidation is
storage-level only; their read path has a documented default of returning superseded
facts — we would re-implement enforcement anyway, so build chains natively."*

That judgement still holds, and the dossier's issue list is the evidence for it.

---

## The compatibility point that decides most of this

The wikis are **Markdown files, versioned in git**. Every historical state of a
document already exists, addressably, with author and timestamp.

A bi-temporal knowledge graph re-derives, at inference cost, something git already
stores exactly. For a *decision log that gets revised*, the cheap answer is
`git log -p` on the file, not an LLM-extracted validity window.

The temporal capability is only worth its price if the underlying corpus is
**not** already versioned — chat transcripts, agent memory, live events. Those are
genuinely append-only and un-versioned. A wiki of markdown files is neither.

This is the single strongest argument in the whole evaluation, and it did not come
from any benchmark.

---

## Verdict

**Graphify is not disqualified, but it is not a foundation to build a public repo on
in its current form.** An independent research pass reached the same verdict on the
same grounds, and its risk ranking (by risk of abandonment, not features) put
graphify **last of six**, behind Neo4j, LightRAG, FalkorDB, Graphiti and RAGFlow.

The reasons are maintenance risk, not capability:

1. **0.x with 89 releases in a single month.** For a repo whose users install once
   and depend on for years, that cadence means the ground shifts under them. Every
   user is effectively on a moving target.
2. **Zero tests in the distributed artifact.** When we hit the `links`-vs-`edges`
   false diagnosis — which cost real time and produced a wrong conclusion twice —
   nothing in the project would have caught it. That class of bug is exactly what
   tests are for.
3. **Concentration risk, unquantified.** PyPI metadata declares no author or
   maintainer. Contributor count could not be read (GitHub rate limit). An
   unverified single-maintainer dependency at this criticality is a real risk, and
   it is unresolved rather than ruled out.
4. **Monolithic modules.** 8,736 lines in `extract.py` is a review and refactor
   hazard for upstream and for anyone vendoring it.
5. **An open silent-corruption bug (#3776).** Incremental `--update` loses
   cross-file edges with no detectable signal, and `--force` does not repair it.
   Only a clean rebuild does. For a project that wants users to keep their graph up
   to date incrementally, this is the most serious problem found — the failure mode
   is a graph that is quietly wrong, which is worse than one that is loudly absent.
6. **Repository age.** Created 2026-04-03. However large the star count, the project
   is under six months old. That is a very different risk profile from a tool with a
   decade of history, and it is the single fact that most constrains the
   "will this work in 2028" question.

None of this says graphify is bad. It says it is **unvalidated at the level of
stakes we are putting it at**, and that has not been shown otherwise.

### What to do

**Do not make any tool load-bearing yet.** Specifically:

- Keep the retrieval layer tool-agnostic. `scripts/graph_retrieval.py` reads a
  `graph.json`-shaped file and nothing else. Any alternative can be swapped in
  behind that interface without touching callers.
- Treat the current graph as **derived, rebuildable, disposable** — which is
  already the documented philosophy. That framing is what makes an uncertain
  foundation safe.
- Make the substrate swappable and say so publicly. A repo that declares
  "graphify today, any GraphRAG-shaped JSON tomorrow" can absorb a successor. One
  that hard-depends on a 0.x tool cannot.

### Re-evaluate when

- Temporal queries become a real requirement with a real query behind them
  (*"what did I believe about X in June?"*), **and** the corpus stops being
  git-versioned markdown; or
- graphify reaches 1.0 with a published test suite; or
- an alternative offers a drop-in `graph.json` with a stronger stability record.

**The honest position:** the retrieval layer and the graph format are the project's
durable assets. The tool that produces them is the replaceable part, and should be
treated as such — deliberately, in the documentation, not by accident.

---

## Addendum: the strongest evidence against migrating (2026-09-25)

A research pass returned benchmark data that was missing from the first version of
this evaluation. It changes the reasoning materially, so it is recorded here
rather than folded in silently.

### The key finding

Reddy & Challaram, *"Don't Ask the LLM to Track Freshness: A Deterministic Recipe for
Memory Conflict Resolution"* (arXiv:2606.01435, 31 May 2026, CC BY 4.0) evaluates
published memory systems on MemoryAgentBench's **FactConsolidation** task — a
conflict-resolution test where the same fact appears with contradictory values and
newer facts carry higher version markers.

| System | FC-SH (single-hop) |
|---|---:|
| HippoRAG-v2 | 54.0% |
| BM25 | 48.0% |
| Mem0 / Contriever | 18.0% |
| **Zep / Graphiti** | **7.0%** |

**The system purpose-built for temporal agent memory scored 7% — the lowest column in
the table — below BM25.** The multi-hop variant is "nearly unsolved (≤7% across all
22 evaluated systems)."

The paper's recommendation #3 to memory-framework designers:

> "Do not assume graph or knowledge-graph infrastructure alone solves conflict
> resolution. The empirical evidence is that an elaborate temporal KG (Zep /
> Graphiti) scores 7% on FC-SH despite being designed for temporal memory. Graph
> infrastructure may be appropriate for other reasons; conflict resolution is not a
> sufficient reason on its own without an explicit version-aggregation step."

### Verified at source, not taken on trust

Two claims were checked directly rather than accepted from the research summary.

**1. Graphiti does not filter superseded facts by default.** Read from
`graphiti-core` v0.30.2, `graphiti_core/search/search_filters.py`: all four temporal
filter fields — `valid_at`, `invalid_at`, `expired_at`, `created_at` — declare
`default=None`. With no filters supplied, a search returns invalidated and expired
edges. The bi-temporal data is stored; the current-only view is not applied for you.
This confirms independently what the project's own dossier and
`PROPOSED-BRAIN-ARCHITECTURE.md` §3.1.1 already concluded, and it is the mechanism
behind the 7% figure.

**2. The 7% number is the paper's own headline**, stated six times in the text
rather than buried in a table — it is not a marginal cell being over-read.

### What this changes

This does **not** argue for graphify on quality grounds. No public multi-hop QA
benchmark for graphify was found; its published example reports 71.5× token
reduction, not answer accuracy. **graphify remains unbenchmarked, not proven.**

What it does argue against is **migrating to Graphiti for temporal correctness** —
the main reason to consider it. The specific capability that justified the cost is
the one measured at 7%.

### The finding that transfers regardless of substrate

The paper's central mechanism is that **free-text LLM judgement fails at conflict
resolution when freshness is entangled with retrieval noise**, and that moving the
comparison into deterministic code is exact, cheaper, and testable
(deterministic 80.8% vs LLM judgement 61.0% at matched chunking, +19.8 pp).

That is a substrate-independent lesson, and it points the same direction as the git
argument above. For a wiki of version-controlled markdown:

- `git log -p` is the version-aggregation step, already built and already exact;
- RFC 3339 frontmatter and an explicit `status: active|superseded` +
  `supersedes: <note>` give a deterministic current-only filter;
- a `superseded` edge is traversable but filterable, so history stays reachable.

Adopt that convention now. It costs nothing, it is substrate-independent, and it is
the part the benchmark says actually matters. It also means that if a temporal
substrate is ever adopted, it is adopted on top of a working version-aggregation
step rather than in place of one.

**The strongest argument against this recommendation:** graphify is pre-1.0 with a
89-releases-in-one-month cadence and no shipped tests, and no amount of evidence
about Graphiti fixes that. If graphify's extraction quality or maintenance posture
degrades, there may be no mature drop-in that reads the same `graph.json` — the
swappable-substrate design is only an advantage if a credible alternative exists, and
today the credible alternatives are *lighter* (LightRAG, Cognee) or *benchmark-weak
on this exact task* (Graphiti).
