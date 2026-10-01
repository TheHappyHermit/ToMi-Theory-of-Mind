# Memory Subsystem Evaluation — 2026-09-25

Decision record for the conversational/user memory layer of a public open-source
repo. Written for the same reason as `GRAPH-SUBSTRATE-EVALUATION.md`: the incumbent
was adopted, not evaluated, and adoption is not evidence.

**Scope.** What should the repo ship as its memory foundation for users installing
it in a fresh Hermes in 2026 or 2028. Not what is convenient on one machine.

**Hard filter from the repo owner:** the winner must be free to self-host, available
on GitHub, and require no payment for hobby or personal use. A project whose only
usable path is a paid cloud API is disqualified regardless of quality.

---

## What the knowledge base already contained

Found by querying the vault through the repo's own graph retrieval path
(`scripts/graph_retrieval.py "agent memory system"`), not by keyword search:

- `memory-architecture/Related-Work-Agent-Memory-SelfMem-DMem-MIA.md` (2026-08-31,
  `status: stable`, confidence high) — comparative analysis of SelfMem, D-Mem, MIA
  with benchmark numbers for Mem0 and MemGPT already tabulated.
- `Research/DCPM-Dual-Process-Cognitive-Memory.md`
- `concepts/belief-revision-ai-agent-memory.md`

The relevant finding is that **BEAM** is the current shared benchmark for agent
memory, and the vault already holds third-party numbers on it:

| System (BEAM, 100K tokens, GPT-5.4-nano) | Score | Cost |
|---|---:|---:|
| SelfMem | 0.504 | $0.984 |
| LoCoMo (as a system) | 0.306 | $2.904 |
| A-Mem | 0.302 | $3.116 |
| Mem0 | 0.282 | $1.697 |
| MemGPT | 0.291 | $6.434 |

These are SelfMem's own numbers against third-party systems, so they favour SelfMem
and should be read as "Mem0 sits below 0.30 on BEAM at 100K", not as an exact
ranking. The durable takeaway is that **Mem0's quality is contested and its cost
scales badly** — $1.70 at 100K, $9.37 at 500K, $18.83 at 1M.

D-Mem (2026-03) evaluates on LoCoMo/RealTalk and reports a result that matters for
any memory design: **quality-gated escalation recovers 96.7% of full-deliberation
accuracy at 35.8% of the tokens.** The architectural lesson is that a cheap fast
path plus a quality check beats paying for exhaustive retrieval on every query. This
is the same shape as the repo's own thalamus gating, arrived at independently.

---

## Incumbent: Honcho — measured directly

Source: `plastic-labs/honcho` (7,331 stars, "Memory library for building stateful
agents"), confirmed canonical by GitHub search for `honcho memory agent`; the
ecosystem has already self-hosted it for Hermes (`elkimek/honcho-self-hosted`, 378
stars), which independently corroborates that self-hosting works in practice.

### Release and stability

| Property | Value | Read |
|---|---|---|
| PyPI `honcho` | **2.0.0** | **Post-1.0. Stable API.** |
| PyPI `honcho-core` | 1.11.0, Apache-2.0 | — |
| Licence | **AGPL-3.0** | See below — material |
| Release cadence | 1–5/month | Calm and steady |
| Self-host path | `honcho start --setup`, or Docker Compose from source | Documented |
| Store | **Postgres + pgvector** | Same shape the repo already runs |

Contrast with the graph substrate, which is pre-1.0 with 89 releases in one month.
**Honcho's release profile is materially healthier.** That is the single most
important difference from the graphify finding and it argues for keeping it.

### The free/self-host requirement: verified met

Read from the project's own `.env.template`:

```
# (OpenRouter, Together, Fireworks, vLLM, Ollama, LiteLLM), override
# MODEL_CONFIG__OVERRIDES__BASE_URL on each feature section
# DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=
# DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__BASE_URL=
...
```

- Self-hosting is a first-class documented path, not an afterthought.
- **Every LLM-using subsystem — deriver, dialectic at all five reasoning levels,
  summary, and both dream stages — accepts a per-module `BASE_URL` override, and the
  docs name Ollama and vLLM explicitly.** A hobbyist can run the entire memory
  pipeline against a local model at zero API cost.
- Embeddings likewise accept an override: `EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL`.
- The only uncommented key that looks key-shaped is `LLM_OPENAI_API_KEY`, used when
  `EMBEDDING_MESSAGES=true`; with a local embedding endpoint that too is avoidable.

**Verdict on the owner's filter: Honcho passes.** Free for self-host, GitHub-native,
no payment required for hobbyist use. A managed cloud exists at `api.honcho.dev`
but is not required and is not the only path.

### The AGPL-3.0 obligation

Honcho is **AGPL-3.0**, not Apache-2.0. This is a real constraint for a public
repo and must be a deliberate decision, not an accident:

- **Self-hosting for yourself or your own organisation: no obligation.** AGPL's
  network clause is about *conveying* modified software to users over a network.
- **Shipping Honcho inside a distributed product, or offering it as a hosted
  service: source-disclosure obligations attach.** A repo that merely installs Honcho
  as a separate service and instructs users to run it themselves is materially
  different from vendoring its source into a distributed artifact.

This does not disqualify Honcho for the repo's stated purpose, but the README and
`example.env` must say plainly which side of that line the project sits on. Getting
this wrong is a legal exposure for the repo's users, so it belongs in documentation
rather than in someone's memory.

### Fit alongside the existing Postgres/pgvector retrieval stack

This is the substantive architectural question, and Honcho is **complementary rather
than duplicative**:

| Concern | Honcho | Repo retrieval stack |
|---|---|---|
| What it stores | conversational turns, sessions, peers, **derived representations** | documents, chunks, embeddings |
| How it's built | **deriver** LLM pass in the background → peer cards, summaries, dialectic queries | deterministic indexing, no LLM |
| What it answers | "what does this agent know about *this person*" | "which documents are relevant to *this query*" |
| Time model | implicit recency over interactions | explicit supersedes chain (§`VERSION-AGGREGATION.md`) |

The distinction is **episodic/social memory versus document/semantic retrieval.**
Honcho's peer representation is a *model of a user* that improves with inference
time; the pgvector stack is a *model of a corpus* that is fixed until reindexed.
Those are genuinely different jobs, and the repo wants both.

The one place they overlap is belief currency, and the lesson from
`GRAPH-SUBSTRATE-EVALUATION.md` applies unchanged: **do not let a model decide which
version of a fact is current.** Honcho's dialectic is explicitly an LLM synthesis
layer, so its outputs must be treated as *inferred beliefs with provenance*, never
as authoritative current state. The deterministic `supersedes` convention and git
history remain the source of truth.

### Operational burden

Three processes, all of which the repo already runs or has compose files for:
Postgres+pgvector (already present), the Honcho server, and the deriver worker. No
GPU, no extra paid service, no cluster. Backup story is the existing Postgres one.
**This is a modest, well-bounded addition** — the same shape the repo already ships
for its other services.

---

## Where Honcho sits

**Keep it.** It clears the owner's filter decisively, is post-1.0 with a calm release
cadence, self-hosts cleanly, can run its entire LLM pipeline locally for free, and
occupies a genuinely different niche from document retrieval.

**Document two boundaries**, both of which are load-bearing:

1. **Licence.** AGPL-3.0. State which side of the network clause the project sits on
   so users can make their own call.
2. **Authority.** Honcho's derived representations are *inferences*, not facts.
   Version currency stays deterministic (`docs/VERSION-AGGREGATION.md`), and
   document retrieval stays the Postgres/pgvector path.

### The strongest argument against this recommendation

Honcho's quality is **unbenchmarked in this repo**. Every third-party number
available says Mem0 lands below 0.30 on BEAM at 100K tokens; there is no equivalent
public BEAM or LoCoMo number for Honcho, so "stable project" is not the same as
"good retrieval" and this recommendation rests on maintainability and fit, not on
measured quality. A self-hosted choice can be stable and still mediocre. The honest
way to settle it is a small local eval on the repo's own retrieval questions —
cheap now, because the substrate is already swappable and the questions can come from
real usage. Until that exists, this document is an engineering judgement about
operational risk, not a claim of superior memory quality.

---

## Addendum: memory-loss bugs found, and a package-name error I made (2026-09-25)

A deeper research pass returned evidence that **reverses the recommendation above.**
Verified at source rather than accepted from the summary.

### I cited the wrong PyPI package — retracting a load-bearing claim

The evaluation above says Honcho is at "PyPI `honcho` **2.0.0** — post-1.0, stable API"
with a "1–5 releases/month" cadence, and uses that as a main reason to keep it.
**That is wrong, and it was a name collision.**

- PyPI `honcho` 2.0.0 is *"a Python clone of Foreman. For managing Procfile-based
  applications"*, source `github.com/nickstenning/honcho`, **24 releases, last published
  2024-10-06**. It has nothing to do with agent memory.
- The real packages are **`honcho-ai`** (2.5.1, Apache-2.0, 46 releases since
  2024-01-18, last release 2026-09-24, 1–2/month) and **`honcho-cli`** (0.2.0, MIT, 7
  releases since 2026-04-20). The repo's own `pyproject.toml` declares
  `name = "honcho"`, `version = "3.2.1"` — which is exactly the trap.

**The cadence intuition turns out to be right, but for the wrong reason.** I verified
`honcho-ai` properly this time: steady 1–2 releases per month, post-1.0, actively
released. So the *conclusion* about release health survives; the *evidence* I cited
did not, and an unrelated package was nearly used to justify a dependency.

### Verified memory-loss defects (all in `plastic-labs/honcho`)

**#1236 — a provider outage permanently burns queued work. Confirmed as designed
behaviour.** When the LLM upstream is unreachable past the retry budget
(`MAX_RETRYABLE_ATTEMPTS = 3`, `RETRY_BACKOFF_SECONDS = 1.0`, 30 s poll — roughly
**90 seconds** of tolerance), work units are marked `processed=true` with an error,
and `get_next_queue_item` filters only on `processed`, not on `error`. Those messages
are never derived again and there is no supported recovery path: the reconciler does
not re-derive, the message-update endpoint does not enqueue, and no client-supplied
idempotency key exists (#982 is an open request), so re-POSTing duplicates instead.

The reporter's impact: a ~4h20 outage burned **23 work units across 3 workspaces**,
none of which produced a `message_embeddings` row. Worse,
`GET /v3/workspaces/{ws}/queue/status` reported `completed == total` (77/77) while 11
items sat in terminal error — the health endpoint reports a healthy queue during
silent data loss.

**This is not a coding slip, and that is the problem.** The issue points at
`tests/deriver/test_queue_processing.py::test_retry_exhaustion_is_terminal`, whose
docstring reads:

> "At the attempt cap a transient error burns the first item exactly like today's
> terminal path and clears the counter."

Read from the repository to confirm. The behaviour is asserted by their own test
suite, so changing it is a product decision, not a bug fix. **For a memory system,
burning a memory after 90 seconds of upstream downtime is the wrong default.**

**#989 — semantic deduplication can permanently delete the incumbent.** Reproduced on
v3.0.7 and v3.0.12, so it is long-standing rather than a regression. The path is
`create_documents(deduplicate=True)` → `is_rejected_duplicate()` soft-deletes the
existing row when `score_new >= score_existing` (note `>=`: **on a tie the incumbent
loses**) → the reconciler hard-deletes it after the retention cutoff. Because the
replacement need only be *semantically* similar, exact-content lookup cannot recover
the original. The agent-tool path also hardcodes `deduplicate=True`, so
`DERIVER_DEDUPLICATE=false` does not disable it.

For user memory this is the dangerous direction: semantic similarity is not evidence
that one memory is safely replaceable by another.

**#1230 — the deriver persists its own few-shot examples as facts about real people.**
Open, filed 2026-09-24, despite a prompt-level guard added in #1028. Bogus
conclusions appear on real peers, and **deleting them is not durable** — they are
re-derived under fresh IDs. PR #1229 proposes structural hardening (reserved
synthetic example entities, rejected before persistence).

Also reported: #1240 (usable observations dropped when validation sees an empty
representation), #839 (parse failure still marks the queue item `processed=true`,
"no metric, no trace span error, no alertable signal"), #1143 (peer cards silently
truncate at the cap and the model is not told its update was discarded), #913
(deriver stops advancing after restart), #1001 (dreamer goes quiet), #1075 (native
Windows broken), #721 (no official migration path between managed and self-hosted,
unclear whether vector state carries over).

### Revised verdict

The project is not abandoned: 61 contributors, active triage, tests, CI, a working
self-host path, and a genuinely calm release cadence once you read the right package.
**But it currently demonstrates silent, unrecoverable memory loss under conditions a
hobbyist will hit routinely** — an API provider having a bad afternoon is not exotic,
and OpenRouter rate limits or an upstream outage are ordinary events.

So the earlier "keep it" recommendation is **withdrawn**. Honcho is not disqualified
as a component; it is disqualified as the *sole durable store* of user memory.

**Use it behind an append-only event log.** Concretely, if it stays at all:
write every raw message to an append-only store the repo controls *before* posting
to Honcho, with a client-generated ingestion id, so re-derivation is possible when
#1236's terminal state is hit. That single change converts unrecoverable loss into a
replay. Add a reconciliation check comparing raw-log count against derived
embeddings, and treat Honcho's derived representations as **inferred, never
authoritative** — which the #1230 hallucinated-fact bug makes non-negotiable.

**The strongest argument against this reversal:** these are all reported issues, not
independently reproduced failures, and several may already be fixed in `3.2.1`
(#1236 was filed against 3.2.1, #989 against 3.0.x, #1230 has PR #1229 pending).
Calling the system unsafe on issue text alone risks discarding a well-maintained
project over reports that are stale or in-flight. The honest position is that the
*reported failure modes are severe enough to require a mitigation*, not that the
software is bad.

**Separately, a packaging finding that affects this repo directly:** the current
`pyproject.toml` declares `requires-python = ">=3.13"`, while the documented minimum
elsewhere in the project and the ecosystem baseline is 3.10–3.12. Anyone installing
Honcho on Python 3.11 or 3.12 must confirm which interpreter is actually used. The
repo's own compose stack uses `pgvector/pgvector:pg15` plus Redis, Prometheus and
Grafana — four services, not the three this evaluation assumed.
