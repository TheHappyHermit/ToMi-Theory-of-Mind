# Installation Guide for Hermes Brain 🧠

This guide walks you through installing and verifying **Hermes Brain** on Linux, macOS, and Windows.

---

## 💻 Hardware Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Model** | Qwen3.6-35B (Q4_K_M) | Qwen3.6-35B (Q4_K_M or Q8_0) |
| **VRAM / GPU** | 16 GB VRAM + CPU offload | 24 GB VRAM (RTX 3090 / 4090 / A5000 / Mac Studio) |
| **System RAM** | 32 GB RAM | 64 GB RAM |
| **Storage** | 30 GB SSD (NVMe preferred) | 100 GB NVMe SSD |
| **Python** | Python 3.10, 3.11, or 3.12 | Python 3.11 (via `uv`) |

---

## 📦 Prerequisites

All dependencies are manifest-driven — you should not need to hunt for anything:

```bash
# 1. System tools (sqlite3 CLI, jq, rsync, sshpass, uv, gh check, docker check)
bash scripts/install_system_deps.sh

# 2. Python packages (CORE + SCRIPTS + DASHBOARD sections — see requirements.txt)
pip install -r requirements.txt        # or: uv pip install -r requirements.txt

# 3. Google sync isolation (gmail/gcal cron scripts — protects against hermes update)
bash scripts/setup_google_venv.sh
```

The only manual step left is a **model backend** — Hermes Brain is optimized for
**Qwen3.6-35B** via llama.cpp (`llama-server --model ./models/Qwen3.6-35B-A3B-Q4_K_M.gguf --ctx-size 32768 --n-gpu-layers 99 --port 8080`) or Ollama. Cloud APIs also work — set them on the dashboard **Settings** page (model roles default to your main Hermes model; no duplication).

**Database**: SQLite by default (zero config). For brain sync and retrieval, PostgreSQL via the compose file in `docker/`:

- **Image:** `paradedb/paradedb:0.25.10-pg18` — PostgreSQL **18.6** with both **pg_search** (BM25 lexical) and **pgvector** (HNSW vector). The two are complementary, not alternatives: `@@` for keyword search, `<=>` for semantic.
- **Start it:** `docker compose -f docker/docker-compose.brain.yml up -d`
- **Port:** `127.0.0.1:5433` → container `5432`
- **Volume:** `hermes-brain_brain-pgdata`

Two settings in that compose file are load-bearing, not decoration:

- **`shm_size: 2gb`** — Docker's default container `/dev/shm` is 64MB. Building the
  pg_search and HNSW indexes under `maintenance_work_mem=1GB` fails with
  `could not resize shared memory segment ... No space left on device` on a host with
  plenty of free disk. This error looks like a full disk and is not one.
- **Index builds** must run **outside a transaction block** (`CREATE INDEX CONCURRENTLY`),
  and with:
  ```bash
  PGOPTIONS="-c maintenance_work_mem=1GB -c max_parallel_maintenance_workers=4"
  ```

**Verify the database is actually working** — health status alone proves nothing:

```bash
docker exec brain-postgres psql -U brain -d brain -c "SELECT version(); SELECT extname, extversion FROM pg_extension ORDER BY extname;"
# expect pg_search and vector

# BM25 lexical — returns 1106 hits
docker exec brain-postgres psql -U brain -d brain -c \
  "SELECT count(*) FROM pages WHERE content @@ plainto_tsquery('memory');"

# vector semantic — returns 3 neighbours
docker exec brain-postgres psql -U brain -d brain -c \
  "SELECT count(*) FROM (SELECT e.page_id FROM embeddings e WHERE e.embedding IS NOT NULL
     ORDER BY e.embedding <=> (SELECT embedding FROM embeddings WHERE embedding IS NOT NULL LIMIT 1)
     LIMIT 3) t;"
```

> **Two schema details that will bite you.** The BM25 index is on
> `(id, title, content)` — there is **no `description` column** on `pages`, and
> `id @@ query` fails because `id` is `bigint`; the operator goes on a text
> column. And **vectors are not on `pages`**: they live in a separate
> `embeddings` table joined on `page_id`. A query written against
> `pages.embedding` errors out.

**Data root**: everything the system writes — wiki, oracle brain, exchange, research, organizer, logs, databases — lives under `~/.hermes/`. A fresh install creates that directory and nothing else; there is no second data directory. Scripts should read the `HERMES_DATA_DIR` variable rather than hardcoding a path. If a tool reports a missing directory under `~/.hermes`, that is a real failure, not a stale reference. How this root was reached, and which older names are retired, is in [`docs/DATA-ROOT-RETIREMENT.md`](docs/DATA-ROOT-RETIREMENT.md).

### Source paths

The sync resolves three sources. Defaults are relative to `HERMES_DATA_DIR`; override in `docker/.env`:

| Source | Default path | Override |
| :--- | :--- | :--- |
| `active-wiki` | `~/.hermes/active-wiki` | `ACTIVE_WIKI_PATH` |
| `oracle-brain` | `~/.hermes/oracle/brain` | `ORACLE_BRAIN_PATH` |
| `exchange-research` | `~/.hermes/exchange/research` | `EXCHANGE_DIR` |

**Before your first sync, set these two.** The embedding server speaks
the OpenAI-compatible API only; without the mode the sync probes the
native Ollama path, gets a 404, and (before the fix) exited claiming the
host was unreachable:

```bash
export BRAIN_API_MODE=openai
export BRAIN_OLLAMA_URL=http://<host>:<port>
```

The server's context window is **2048 tokens** — longer input is
rejected with a deterministic `HTTP 400`, and `brain_sync.py` caps a
chunk at 7,500 characters and logs `[trunc] ... Tail not indexed.` If
you see that, content past the cut is **not searchable**. Raise the cap
only alongside the server's window. Note the server returns 2560
dimensions and ignores the `dimensions` parameter; the sync truncates to
2000 client-side because 2000 is the pgvector HNSW maximum. A dimension
mismatch in the log is not a bug.

For the wiki schema gates — the fourteen scripts that check frontmatter
before every commit, and the one that is *supposed* to fail — see
[`docs/WIKI-QUALITY-GATES.md`](docs/WIKI-QUALITY-GATES.md).

`brain_sync_cron.py` syncs `active-wiki` and `exchange-research`. `oracle-brain` is
excluded and handled separately — if you rely on it, confirm that job is actually
running:

```bash
python3 scripts/brain_sync.py --report-orphans
```

This is read-only. It reports pages in the database with no file on disk, and files on
disk that were never indexed. A large "never indexed" count means content is **missing**
from search — a worse problem than duplicates.

> **The sync never deletes pages.** There is no `DELETE FROM pages` in `brain_sync.py`;
> its only DELETEs are chunk-level. If a file is moved or removed, its page stays in the
> database and stays searchable, indefinitely. This is deliberate — pages are sometimes
> the only surviving copy of a file — but it means you must decide what to do about
> orphans yourself. See [`docs/ORPHAN-PAGES-TODO.md`](docs/ORPHAN-PAGES-TODO.md).
> There is intentionally no `--purge` flag.

---

## 🤖 Autonomous Hermes Agent Setup (Turnkey)

If you are using **Hermes Agent**, setup is 100% autonomous:
1. Provide the repository link to your Hermes Agent:
   ```text
   Set up Hermes Brain from https://github.com/TheHappyHermit/ToMi-Theory-of-Mind.git
   ```
2. Hermes Agent will automatically discover and execute [`AGENT.md`](AGENT.md).
3. The agent provisions all **profiles**, **skills**, **hooks**, **plugins** (`plugins/decision_logger`), **cron jobs**, and **Docker containers** automatically in under 60 seconds.

---

## 🚀 Human Quick Installation (Single Command)

Hermes Brain includes an automated, cross-platform installer for Linux, macOS, and Windows:

```bash
# Clone the repository
git clone https://github.com/TheHappyHermit/ToMi-Theory-of-Mind.git
cd hermes-brain

# Run the universal installer (Auto-detects Docker vs Local Python, links all components)
python install.py --auto
# Or on Linux/macOS: ./setup.sh --auto
# Or on Windows:      .\setup.ps1 --auto
```

### Interactive install

Run with no flags on a real terminal to be asked two questions:

```bash
python install.py
```

1. **SOUL.md** — asked first, before anything can write to it. If you already have
   one, you choose to append the operational facts, replace it with the repo default
   (the old file is moved into `~/.hermes/backups/install-<timestamp>/`, not
   deleted), or leave it alone. A `SOUL.md` already symlinked to the repo copy is
   recognised as ours and left alone. The facts to be appended are printed in full
   before the prompt.
2. **Components** — pick a subset of hooks, skills, plugins, profiles, scripts,
   databases, cron, companion apps, and the Docker stack. Each stage skips itself
   when its name is not selected; picking nothing falls back to a full install.
   Docker-only items are marked unavailable rather than offered and failing.

`--auto` and any run with piped or closed stdin skip both questions entirely and
proceed with a full install, so scripted and CI installs stay non-interactive.

The installer automatically:
1. Validates Python (3.9+) and checks for Docker / Docker Compose.
2. Creates `.env` and `dashboard/.env` from `example.env` if not present.
2b. **Credentials.** One `.env` at the repo root (mode 600, gitignored) holds
   every value the container stacks interpolate. `install.py`'s `ensure_env_file()`
   creates it and generates the two that compose *requires* —
   `HONCHO_PG_PASSWORD` and `SEARXNG_SECRET` — so a fresh clone deploys Honcho
   and SearXNG with nothing to edit. Every stack is started with
   `docker compose --env-file .env`, so there is one file, not one per stack.

   To change a value, either edit that `.env` or set it in the Control Panel
   (**Settings → Honcho** for the Honcho password), which writes back to the same
   file. No credential is ever committed: `example.env` documents the keys with
   no values for `HONCHO_PG_PASSWORD`.

   An existing value is never regenerated. Postgres keys its data directory on
   the password it was initialised with, so rotating one on a live volume means
   `initdb` — destructive. Set a new password deliberately, not by re-running
   the installer.

2c. **Command Deck as a durable service** (optional but recommended). The unit
    file is tracked at `deploy/hermes-command-deck.service`, so the LAN bind and
    the restart policy travel with the repo:

    ```bash
    mkdir -p ~/.config/systemd/user
    cp deploy/hermes-command-deck.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now hermes-command-deck.service
    ```

    It publishes on `0.0.0.0:8088` so the dashboard is reachable from the LAN.
    **The dashboard has no authentication layer** — anything that can reach
    8088 can read and write the settings holding API keys and database passwords
    (secrets are masked on read; the write endpoints are not protected). Treat
    it as a trusted-LAN service and do not port-forward it.

    The unit uses `%h` for the home directory, so the tracked copy carries no
    absolute path and no username.

3. Seeds the standard cognitive cron schedules from `cron/jobs.template.json` to `~/.hermes/cron/jobs.json` (via `scripts/setup_cron_jobs.py`; existing user jobs are preserved, not overwritten).
4. Provisions and links all Hermes Agent components into `~/.hermes/`:
   - **Profiles** (`profiles/*`): `auditor`, `coder`, `default`, `oracle`, `planner`, `researcher`, `personal-organizer`, etc.
   - **Hooks** (`hooks/*`): `brain-cognitive-guard`, `brain-memory-consolidator`, `hermes-visualizer-sync`, `to-do-capture`.
   - **Skills** (`skills/*`): 38+ production skills including `hermes-brain`, `barehands`, `brain-search`, `first-principles`.
   - **Plugins** (`plugins/*`): Standard plugins including `plugins/decision_logger/`.
5. Launches Hermes Brain via Docker Compose (with PostgreSQL pgvector & SearXNG) or local Python server on port 8088.
6. Runs stack verification checks (`python scripts/verify_stack.py`).

---

## 🔍 Checking an existing install

A fresh install needs nothing extra: `install.py` symlinks every
`skills/*/SKILL.md` into `~/.hermes/skills/`, and seeds the cron jobs from
`cron/jobs.template.json`. The skills, the prompts, and the write-boundary rules
all arrive from the repo in that one pass.

To find out whether an **already-running** install has fallen behind the repo:

```bash
python scripts/check_cron_drift.py             # every job; writes nothing
python scripts/check_cron_drift.py --verbose   # show the differing lines
python scripts/check_cron_drift.py --job <id>  # one job
```

It expands the template's `${HERMES_HOME}`-style variables before comparing, so a
prompt that differs only by having those resolved to real paths on this machine is
reported as matching. It exits non-zero when anything has drifted, so it can gate
a commit or a deploy.

| Script | Does | Use when |
| :--- | :--- | :--- |
| `scripts/check_cron_drift.py` | Reports drift between the template and the live `jobs.json` | Checking a running install |
| `scripts/setup_cron_jobs.py` | Seeds the cron job set from the template | Called by `install.py`; safe to re-run |
| `scripts/install_wiki_schema.sh` | The canonical schema into both wikis | A wiki needs its schema re-synced |
| `scripts/verify_stack.py` | End-to-end health of the running stack; exits non-zero on any failure | A component looks up |
| `scripts/graph_health_check.py` | Both Graphify graphs: present, parseable, non-empty | Associative retrieval returns nothing |

There is deliberately no script that copies a repo file over a live one. A
fresh install has nothing to copy, and on an existing install a blind copy
replaces a working, machine-resolved file with a template one — which is how a
prompt full of unexpanded `${...}` variables gets written over a prompt that
worked. Inspect the difference, then change the job deliberately.

---

## 🐳 Docker Deployment (Recommended)

The services live in **separate compose files** under `docker/`, because the
database needs settings the others do not. Start them with the `-f` flag:

```bash
# Command Deck dashboard (API + UI) on :8088
docker compose up -d --build

# PostgreSQL 18.6 (ParadeDB) with pg_search + pgvector on :5433
docker compose -f docker/docker-compose.brain.yml up -d

# Sovereign privacy search proxy (SearXNG) on :8080
docker compose -f docker/docker-compose.searxng.yml up -d
```

Actual container names, which do **not** follow the compose service names:

| Service | Container | Port |
|---|---|---|
| Command Deck dashboard | `hermes-brain-dashboard` | `8088` |
| PostgreSQL / ParadeDB | **`brain-postgres`** | `5433` |
| SearXNG | **`searxng-core`** | `8080` |

> **Port 8080 is SearXNG, not the brain.** The brain search API is the dashboard on
> **8088**, at `/api/brain/search`. Anything that verifies brain sync must use that
> address — pointing a verifier at 8080 gets HTML from a web metasearch engine.

> **`docker compose up -d` alone starts only the dashboard.** The root
> `docker-compose.yml` defines `brain-dashboard` and nothing else. The database and
> search proxy need their own `-f docker/...` invocations, as above.

### Why Docker for all of it

Every service in this stack — dashboard, database, search proxy — is defined as a
container image, so the whole system brings up the same way on **Linux, macOS and
Windows** with Docker installed. A native install would need a different startup
path per platform; the container path does not.

---

## 🐍 Manual Local Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/TheHappyHermit/ToMi-Theory-of-Mind.git
cd hermes-brain
```

### Step 2: Create and Activate Virtual Environment
Using `uv` (recommended):
```bash
uv venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```
Or with standard Python:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Link Hooks & Skills to Hermes Agent
```bash
python install.py --link-only
```

### Step 5: Verify the Installation

Run the unit test suite:
```bash
python -m unittest discover tests
```

The full suite is documented in [`docs/SUITE-STATE.md`](docs/SUITE-STATE.md). Note that
one fixture (`test_arena_invariants_nonvacuity`) requires unread ledger rows and fails
once a corpus is exhausted — that is expected, and it fails identically on older
commits.

---

## ✅ First-time setup checklist

Work top to bottom. **Each step has a command that proves it** — do not skip ahead on
the assumption that a healthy-looking container means the layer works.

### 1. Database is up and both extensions loaded

```bash
docker exec brain-postgres psql -U brain -d brain -c \
  "SELECT version(); SELECT extname, extversion FROM pg_extension ORDER BY extname;"
```
Expect PostgreSQL **18.6**, and both `pg_search` and `vector` present. A container
reporting `healthy` does not prove extensions loaded.

### 2. Both retrieval paths work

```bash
# BM25 lexical — expect a large number (1106 on a populated corpus)
docker exec brain-postgres psql -U brain -d brain -c \
  "SELECT count(*) FROM pages WHERE content @@ plainto_tsquery('memory');"

# Vector semantic — expect 3
docker exec brain-postgres psql -U brain -d brain -c \
  "SELECT count(*) FROM (SELECT e.page_id FROM embeddings e WHERE e.embedding IS NOT NULL
     ORDER BY e.embedding <=> (SELECT embedding FROM embeddings WHERE embedding IS NOT NULL LIMIT 1)
     LIMIT 3) t;"
```

Note the two non-obvious bits: the BM25 `@@` operator goes on a **text** column
(`content`), and vectors live in the **`embeddings`** table, not on `pages`.

### 3. Embedding server answers

```bash
curl -s http://<host>:18082/v1/models
```
Must list your embedding model. If this fails, **stop here** — step 4 cannot work, and
the failure is silent downstream (see step 4).

### 4. Sync actually writes

```bash
python3 scripts/brain_sync.py --source active-wiki
```

`files=0` on a wiki you know has content means the embedding endpoint is unreachable.
The sync does not fail loudly — it records a timestamp and reports success. To prove a
write end to end rather than inferring it:

```bash
docker exec brain-postgres psql -U brain -d brain -tAc \
  "SELECT 'pages='||(SELECT count(*) FROM pages)||' embeddings='||(SELECT count(*) FROM embeddings);"
```
Create a test `.md` file, re-run the sync, and confirm **both counts increased**. A
timestamp change alone proves nothing.

### 5. Post-sync verification passes

```bash
python3 scripts/verify_brain_sync.py --source active-wiki
```
Expect 3/3 queries successful, exit 0.

> `exchange-research` has no verifier and reports `skipped, not a failure`. That is the
> truth — it was not checked. `brain_sync_cron.py` reads the accepted source list from
> the verifier itself, so the two cannot drift apart again.

### 6. Nothing is stranded

```bash
python3 scripts/brain_sync.py --report-orphans
```
Read-only. Check two numbers: **orphaned** (pages with no file) and **never indexed**
(files not in the database). A large *never indexed* count means content is missing from
search — worse than duplicates.

### Common first-time failures

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Embedding endpoint not reachable` | Wrong host/port | Step 3 |
| `files=0` but you have content | Endpoint down, failure is silent | Step 3 |
| `could not resize shared memory segment` | Container `/dev/shm` is 64MB | `shm_size: 2gb` in compose |
| `CREATE INDEX CONCURRENTLY` fails | Run inside a transaction block | Run it outside `BEGIN` |
| Verifier: `HTTP 404` | Pointed at an LLM API or SearXNG | Use dashboard 8088, `/api/brain/search` |
| Verifier: `Expecting value: line 1 column 1` | Got HTML, not JSON | Same as above |

Congratulations! Hermes Brain is now fully installed and operational. Proceed to [SETUP.md](SETUP.md) for configuration instructions.
