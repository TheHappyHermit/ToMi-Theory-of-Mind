# Third-Party Licences

This repo installs and configures third-party software. It does not vendor it. Each
service runs as a separate container from its own upstream image.

That distinction matters for three of the dependencies, which are **AGPL-3.0**.

## What AGPL-3.0 means here, in plain terms

AGPL is copyleft with a network clause. Running someone's AGPL software **for
yourself** carries no obligation to share anything. The obligation attaches when you
**convey** the software to other people — including by offering it to them over a
network as a service.

| What you do | Obligation |
|---|---|
| Run it on your own machine for your own use | None |
| Install this repo's compose files for personal use | None |
| Ship a product that *includes* the AGPL source | You must offer that source under AGPL |
| Operate a hosted service *using* an unmodified AGPL service as your backend | The AGPL service stays AGPL; your own separate code is not automatically pulled in |
| Run a **modified** AGPL service and let users reach it over a network | You must offer those users the source of your modified version (this is the clause AGPL adds over GPL) |

This repo's compose files **connect to** these services as external processes. That is
the "run it yourself" column, not the "ship it inside a product" column.

Two definitions from the licence text matter for reading that table:

> "To 'convey' a work means any kind of propagation that enables other parties to make
> or receive copies. **Mere interaction with a user through a computer network, with no
> transfer of a copy, is not conveying.**"

> "It requires the operator of a network server to provide the source code of the
> modified version running there to the users of that server."

So the network clause attaches to **modified** versions offered to users, and network
interaction alone is not conveyance. Running an unmodified upstream image is the
lowest-obligation case; patching it and exposing the patch is the one that triggers
source offer.

**This is not legal advice.** If you plan to redistribute or commercially host
anything that embeds these services, have a lawyer confirm the boundary for your
specific situation. Licences change; check the upstream repository before relying on
any statement here.

## The AGPL-3.0 dependencies in this repo

| Service | Upstream | Used for | Where |
|---|---|---|---|
| **Honcho** | `plastic-labs/honcho` | agent memory | `docker/docker-compose.honcho.yml`, `.brain.yml` |
| **Firecrawl** | `mendableai/firecrawl` | web scraping | `docker/docker-compose.firecrawl.yml`, `.web-stack.yml` |
| **SearXNG** | `searxng/searxng` | metasearch | `docker/docker-compose.searxng.yml`, `.firecrawl.yml`, `.web-stack.yml`, root `docker-compose.yml` |

## Permissively licensed dependencies

| Service | Upstream | Licence |
|---|---|---|
| pgvector | `pgvector/pgvector` | PostgreSQL Licence |
| graphify | `Graphify-Labs/graphify` | Apache-2.0 |
| LiteLLM | `BerriAI/litellm` | **verify before relying on it** — see `docs/DEPENDENCY-REGISTRY.md` |
| Neo4j (Community) | `neo4j/neo4j` | **GPL-3.0** — free to self-host unmodified; evaluated, not bundled |
| Ollama | `ollama/ollama` | MIT |
| vLLM | `vllm-project/vllm` | Apache-2.0 |

## Health, not just licence

Licence tells you what you owe. It says nothing about whether the software works or
will still exist in three years. For that, see
[`DEPENDENCY-REGISTRY.md`](DEPENDENCY-REGISTRY.md), which records maintenance
signals, risk tiers, and the specific known failure modes for each dependency.

Two entries there are worth reading before you rely on them:

- **graphify** carries a high risk tier: its repository is under a year old, it
  releases extremely often, and it has an open bug where incremental updates
  silently lose graph edges. Run `scripts/verify_graph_integrity.py` if you use it.
- **Kuzu** is archived upstream. Nothing here depends on it, but any design document
  still listing it as a live option is out of date.

## Refreshing this information

```bash
python3 scripts/refresh_dependency_health.py --diff
```

Set `GITHUB_TOKEN` first if you hit rate limits — the unauthenticated GitHub API
allows only ~60 requests per hour and this script needs about 38. It exits non-zero
when every fetch fails, so a check that measured nothing is never mistaken for a
check that found nothing wrong.
