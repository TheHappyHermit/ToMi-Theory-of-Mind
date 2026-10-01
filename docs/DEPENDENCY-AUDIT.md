# Dependency Audit — bundled services, licences, and operational risk

**Date:** 2026-09-25
**Scope:** every service this repo bundles as a container, plus the memory and
inference components it recommends.
**Rule applied:** anything a hobbyist must run must be free to self-host, on
GitHub, and usable with no paid tier. That is the standing filter for this project.

Every figure here was checked at the primary source. Where a claim came from a
research report rather than the source itself, it says so and was re-verified before
being recorded. One claim was **retracted** after verification — see the end.

---

## Executive summary

| Dependency | Verdict | Single biggest risk |
|---|---|---|
| **Firecrawl** | Bundle only as optional, pinned, warned | 5 AGPL services, 12 GB RAM, and self-hosting is *not* feature-equivalent to Cloud |
| **SearXNG** | Yes, with warnings | Search engines block, CAPTCHA, rate-limit, and sometimes return nothing. "SearXNG is up" ≠ "search works" |
| **pgvector** | Yes | Effectively one maintainer, 0.x API, HNSW needs tuning |
| **Zep (Community Edition)** | **No — it is abandoned** | The OSS edition is not maintained; only the paid product is |
| **Graphiti** | Yes, as a non-authoritative index | Silently produces zero-edge episodes with no retry |
| **HippoRAG** | **No** | Alpha research artifact: `2.0.0a5`, no CI, one lab |
| **LiteLLM** | Yes, not on a critical path | Split licence; a hard pin on the proprietary `litellm-enterprise` |
| **vLLM** | Yes, pin everything | Regression churn across CUDA/driver/model/quantization |
| **Ollama** | Yes — safest local-inference default | Lowest footprint; bugs remain around GPU detection and sizing |
| **mem0** | Yes, non-authoritative | Cross-user leakage and silent empty retrieval |
| **Kuzu** | **No** | Archived, read-only, no maintenance path since 2025-10-10 |

---

## Firecrawl — the heaviest dependency, and the most overstated

### Licence: AGPL-3.0, confirmed from the LICENSE file

SPDX reports `AGPL-3.0`; the repository's `LICENSE` is the full AGPLv3 text. The
README says the project is "primarily licensed under the GNU Affero General Public
License v3.0" while SDKs and some UI pieces are MIT.

**What that obliges a wrapper repo.** This repo provides a Compose file that points
at an unmodified upstream image. It does not vendor Firecrawl source or build a
modified image, so it is not itself conveying Firecrawl. A user running that image
privately is not distributing to third parties.

The boundaries that matter:

- Vendoring Firecrawl source or a modified build → ordinary AGPL redistribution
  obligations attach.
- **Modifying** Firecrawl and exposing it over a network → AGPL §13 requires a
  prominent offer of the corresponding source.
- An HTTP client that calls Firecrawl is not automatically a derivative merely
  because it talks to the API. That is fact-specific and **not something to rely on
  without counsel** for a commercial product.

Recorded in `THIRD-PARTY-LICENSES.md`. A lawyer should confirm the boundary for any
commercial redistribution.

### The resource claim in our own files was wrong

This repo's Compose headers previously said *"HOST REQUIREMENTS: 2 CPUs, 8GB+ RAM.
Firecrawl uses up to 10GB RAM."*

**Verified against upstream's own `docker-compose.yaml`:**

```
playwright-service:  cpus: 2.0   mem_limit: 4G   memswap_limit: 4G
firecrawl-api:       cpus: 4.0   mem_limit: 8G   memswap_limit: 8G
```

**6 CPUs and 12 GB of configured limits, before Redis, RabbitMQ and Postgres.**
Upstream's own comment says "Increase if you have more CPU cores/RAM available" —
these are not a guaranteed minimum, they are a starting point.

Both headers are now corrected, and the numbers are cited in-file so the next reader
can re-check them.

### Self-hosting is not feature-equivalent to Cloud

Firecrawl's own capabilities documentation states that scrape, crawl, map and search
are self-hostable, while **agent, browser, interact, screenshots and page actions are
Cloud-only**. The fire-engine anti-bot behaviour is not in the default self-hosted
stack, and self-hosted structured extraction requires an OpenAI-compatible provider
or Ollama.

This is a real, documented feature gap — not a "coming soon". #1028 is titled
"[Self-Host] Screenshots are not supported."

### User-reported problems, quoted

- **#4750** — *"`docker compose up` from the repo root intermittently fails because
  the `rabbitmq` healthcheck gives up before RabbitMQ finishes booting. The `api`
  service depends on `rabbitmq: service_healthy`, so it is left in `Created` and never
  starts; nothing listens on port 3002."*
- **#4527** — *"In production, ~6 hours of heavy load accumulated **467 zombies, all
  with `ppid=1`**; the main process then stayed alive but stopped serving HTTP and
  needed a restart."* (The reporter explicitly notes they had not proved causation.)
- **#4348** — *"A scrape job targeting an anti-bot-protected page … **hangs until the
  job timeout** instead of failing cleanly. The log shows an endless waterfall loop
  with **no terminal state**."*
- **#4653** — *"`generateCompletions` … builds the prompt from the full page markdown
  without trimming it to the model's input limit … Self-hosted users with a local
  model … typically have 8k-32k tokens of context."*
- **#4375** — self-hosted `/v2/search` *silently returns zero results* on a malformed
  percent escape in a result URL. Silent zero-result is the dangerous class: it looks
  like "nothing matches" rather than "we broke".

### CI is not a green release gate

31 workflows exist. Of the latest 50 Actions runs: **29 successful, 15 skipped, 6
failed** — including the latest server test suite and the latest production evaluation
run. Activity is not the same as a working gate.

### Release velocity is a risk in itself

35 GitHub Release objects, `v1.0.0` through `v2.11.0`, with tags reaching
`v2.11.403` — roughly 20 tags in four days around the audit date, while the official
self-hosting docs instruct users to pin `v2.11.162`.

**Action taken:** this repo's Compose files previously tracked `:latest` on four
Firecrawl-related images. They now default to a pin
(`FIRECRAWL_VERSION:-v2.11.162`) and document the override.

### Verdict

**Bundle only as an optional, pinned, explicitly warned integration.** It is the
single most memory-hungry service in the stack and the one most likely to consume a
small machine. It should not be on the critical path for a new install.

---

## SearXNG — sound container, unreliable results

### Licence: AGPL-3.0

Confirmed from `LICENSE`; the README carries `SPDX-License-Identifier:
AGPL-3.0-or-later`. Same obligation boundary as Firecrawl — this repo connects to it
as a separate container rather than vendoring it.

### The real risk is upstream, not the container

- **#5286** — *"I have also encountered google giving no results in searxng. In my
  case if google.com website opens in `google.com.(countrycode)` then no google
  results appear … But if i use vpn so google website opens with just `google.com`
  then searxng gives google results."*
- **#3929** — "qwant blocked by CAPTCHA"; *"Ive been getting a lot of captchas lately
  not just on qwant"*.
- **#1966** — a maintainer clarifies: *"This issue is about the rate limit from Google
  servers and not the issue about having less results than normal google."*
- **#6181** — the Docker image fails with *"can't register engine processor"*.
- **#3191** — a user restored behaviour by pinning an old image: *"the rollback its
  the only thing that has worked to me."*

The `searx.space` public-instance monitor reinforces it: of 94 listed instances, 83
had a measured success value, **52 of those were below 50%, and 45 reported no
result**. For Google specifically, 59 were below 50% with 63 reporting no result.
That is a snapshot of *public* instances, not a universal failure rate — but it
separates "SearXNG is available" from "search is reliable."

**This project should never describe a SearXNG result as evidence without noting
that a zero-result turn may be a blocked request rather than an absence of
information.** Every research dispatch in this project is exposed to that failure
mode.

### Footprint

The official recommended Compose is **two** containers — SearXNG plus Valkey (for
limiter/bot-protection). A small private instance is roughly 1 CPU and 512 MB–1 GB
RAM. Single-container `docker run` is also documented. Backup means preserving
`/etc/searxng`; cache loss is not equivalent to losing an application database.

### No semver, by design

SearXNG uses date/commit-based container versions, not semver releases. Tags move
continuously. Pin a date tag or a digest.

### Verdict

**Yes for a hobbyist, with warnings.** Pin the image. Document that engines block.
Do not treat a public instance as infrastructure.

---

## pgvector — permissively licensed, thinly maintained

GitHub's licence API reports `NOASSERTION`, which is a metadata limitation, **not** a
restrictive licence. The actual `LICENSE` is the PostgreSQL-style permissive licence:
*"Permission to use, copy, modify, and distribute this software and its
documentation for any purpose, without fee, and without a written agreement is hereby
granted…"* No network source-disclosure obligation.

**The 23-contributor count for a 23k-star project is not a red flag — it is what a
mature, narrow C extension looks like.** The work is finished and stable, so there is
less to do. The genuine risk is the opposite of bus factor: a stable library with a
small number of people who understand its internals.

Watch items: issue **#719** ("SELECT WHERE ORDER BY LIMIT no results") is a class of
bug that matters enormously here, because **a vector index returning no rows is
silently indistinguishable from "nothing matched."** Pin the extension version, test
against the exact PostgreSQL major version, and benchmark the actual HNSW
configuration rather than trusting defaults.

---

## Zep Community Edition — abandoned, and must not be presented as self-hostable

Verified from `getzep/zep`'s own README:

> | `legacy/` | Deprecated Zep Community Edition (unsupported) |
>
> **Zep Community Edition is no longer supported. Its code has been moved to the …**

Zero user issues plus disabled CE build workflows are the abandonment signature, not
a sign of quality.

**Any document describing "Zep, self-hosted" is describing software its maintainers
have disclaimed.** Graphiti is a different repository and a different situation.

## Graphiti — genuinely maintained, with one serious open bug

`getzep/graphiti` is first-party, actively released, and free. But it is a **graph
engine, not a feature-equivalent Zep Cloud**, and it must not be treated as durable
truth without ingestion verification.

**Issue #1911 is confirmed open and is the one to watch:** 242 of 686 episodes
produced **zero edges**, with no retry, no backoff, and no error counter. An
extraction pipeline that silently ingests nothing looks identical to one that
correctly found no relationships. Other open FalkorDB issues: #1876, #1892, #1893.

This compounds the arXiv:2606.01435 finding already recorded in
`GRAPH-SUBSTRATE-EVALUATION.md` — Zep/Graphiti scored **7.0%** on conflict
resolution against BM25's 48.0%.

---

## HippoRAG — the benchmark winner, and not production software

`setup.py` reports version **`2.0.0a5`**. It is MIT and genuinely free, and its
paper results are real. But:

- **No `.github/workflows`** — there is no CI at all.
- 15 contributors, dominated by a single lab; the great majority of the previous
  year's commits come from one author.
- The documented v2 example uses a 70B model on two GPUs — not a hobbyist footprint.

A project can be an excellent research contribution and a bad production dependency.
HippoRAG is the former. **It should be cited as prior art, not shipped as a
dependency.**

---

## LiteLLM — the NOASSERTION mystery, resolved

The `LICENSE` file is explicit rather than ambiguous:

> Portions of this software are licensed as follows:
> * All content that resides under the "enterprise/" directory … is licensed under
>   the license defined in "enterprise/LICENSE".
> * Content outside of the above mentioned directories or restrictions above is
>   available under the MIT license as defined below.

And `pyproject.toml` hard-pins `"litellm-enterprise==0.1.71"`, with
`litellm/proxy/enterprise` and `litellm/proxy/enterprise/**` in the package config,
and `litellm-enterprise` as a workspace member.

**So: the core router is MIT. The enterprise directory is proprietary, and the
`proxy` extra pulls in a pinned proprietary package.** Note the referenced
`enterprise/LICENSE` returns 404 in the public tree, so the proprietary terms are not
readable from the repository alone — another reason not to assume.

Prepaid gateway, plus gating on reporting, priority reservation, some logging,
pass-through authentication and governance. Documented proxy failure modes include a
permanently blocked event loop (#24512) and a "system bricked" no-fallback condition
(#43000).

**Verdict: usable, never as an unreplicated single point of failure on a critical
path.** This project already prefers direct provider calls with a fallback chain,
which is the right posture.

## vLLM and Ollama — the local-inference options

**vLLM:** Apache-2.0, no paywall, excellent hardware CI — substantially on Buildkite
rather than GitHub Actions, so a GitHub-only CI check will understate its health. The
real risk is regression churn across CUDA, kernels, quantization and model support.
Pin vLLM + driver + CUDA + model + quantization *together*; they are a tested
combination, not independent choices.

**Ollama:** MIT, no paywall, lowest operational footprint — the safest default for a
hobbyist. Real bugs persist around GPU detection, memory sizing, context limits and
driver compatibility (#14366, #14083, #14020).

## mem0 — usable, non-authoritative

Apache-2.0. The OSS SDK, client and self-hosted server are complete enough to run;
the paid Platform adds MCP, extra memory types, multimodal/procedural memory,
advanced filtering and cloud operations. **The free path is a working product, not a
trial** — the gap is capability breadth, not function.

Real risks: cross-user leakage (#4218) and silent empty retrieval (#4232). Same
lesson as Honcho — cross-tenant leakage is the failure mode that makes an
authoritative memory layer unsafe.

## Kuzu — archived, remove from new designs

Verified previously and reconfirmed: `archived: true`, last push **2025-10-10**,
README opens *"We are archiving the KuzuDB project here"* and *"Kuzu is working on
something new!"* — **with no successor named.** Last release `v0.11.3`; a `0.12.0`
issue sat at 16 of 33 items complete at archival. Final CI: 22 successful, 21 failed,
7 cancelled, all activity ending on the archival date.

Independent reporting (The Register, 2025-10-14) indicates the sponsor abandoned the
project rather than announcing a technical replacement; community forks exist but are
not an official continuation.

**Already actioned:** no code, compose file or requirements entry depends on Kuzu, and
the architecture document's mention is marked archived with the evidence.

---

## A correction: GitHub's `open_issues_count` includes pull requests

This changes how several numbers above should be read, and it corrects a framing used
earlier in this project:

| Repo | `open_issues_count` | Actual issues | PRs |
|---|---|---|---|
| getzep/zep | 39 | **0** | 39 |
| getzep/graphiti | 518 | 284 | 234 |
| HippoRAG | 9 | 8 | 1 |
| LiteLLM | 5,256 | 1,747 | 3,509 |
| vLLM | 8,372 | 2,505 | 5,867 |
| ollama | 4,076 | 2,510 | 1,566 |

**Zep's "39 open issues" is zero issues and 39 pull requests** — consistent with a
project whose user-facing component no longer receives bug reports because it is
unsupported. And vLLM's 8,372, cited elsewhere in this repo as a risk signal, is
mostly pull-request volume, not defects. `DEPENDENCY-REGISTRY.md` has been corrected.

**This retracts an earlier claim in this repo that vLLM's high open-issue count was
"activity, not defects" on the basis of the aggregate number alone.** The conclusion
happens to survive — but it now rests on the actual split, not on an assumption about
how GitHub counts.

---

## Actions taken from this audit

1. **Firecrawl images pinned** in both Compose files (four `:latest` tags → version
   variables with a pinned default).
2. **Resource claim corrected** in both files from "2 CPUs, 8GB+" to the verified
   6 CPU / 12 GB, with the upstream citation in-file.
3. **13 undocumented environment variables added to `example.env`**, including all
   three Firecrawl credentials (`FC_PG_USER`, `FC_PG_PASS`, `FC_RABBITMQ_PASS`) and
   `FC_API_KEY`. All 26 referenced variables are now documented; previously 13 —
   including every password the stack needs — were not.
4. **All five Compose files re-validated** with `docker compose config -q`.
5. **`DEPENDENCY-REGISTRY.md` corrected** for the issues-vs-PRs split, Zep CE's
   abandonment, and HippoRAG's alpha status.

## One near-miss worth recording

While auditing, `read_file` displayed a RabbitMQ connection string as
`amqp://firecrawl:***@rabbitmq:5672` — which looked exactly like the credential-redaction
bug that file's own comment warns about, committed as real config.

**It was not real.** Checking the raw bytes showed the on-disk value is
`${FC_RABBITMQ_PASS}`; the `***` was the *tool output* being redacted.

This is worth stating plainly because the failure mode is nasty: a redaction layer
that hides secrets in output can also *manufacture* the appearance of a committed
credential. Had I trusted the rendered text, I would have "fixed" correct config and
added a misleading warning to the docs. **Verify with raw bytes before acting on
anything that looks like a leaked secret in this environment.**
