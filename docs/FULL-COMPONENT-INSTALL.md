# Full Component Install Guide (2026-09-23 migration sync)

This document covers installing **every component** in this repository into a fresh Hermes Agent install. For the base install (Docker, model backend, database) see [INSTALL.md](INSTALL.md). For private state/credentials restore see the private `hermes-backup` repo's `docs/RESTORE.md`.

**Restore order**: (1) stock Hermes → (2) base install (INSTALL.md) → (3) this guide → (4) hermes-backup data restore.

---

## Component inventory (what this repo installs)

| # | Component | Location in repo | Installs to | Count |
|---|---|---|---|---|
| 1 | Skills | `skills/` | `~/.hermes/skills/` | 57 categories (62 dirs — 5 are repo-only extras) |
| 2 | Hooks | `hooks/` | `~/.hermes/hooks/` | 4 (to-do-capture, brain-cognitive-guard, brain-memory-consolidator, hermes-visualizer-sync) |
| 3 | Plugins | `plugins/` | `~/.hermes/plugins/` | 2 (decision_logger, cortex-control) |
| 4 | Profiles | `profiles/` | `~/.hermes/profiles/` | 14 (10 shared + 4 live researcher variants; `research` is a base) |
| 5 | Scripts | `scripts/` | `~/scripts/` (canonical) and `~/.hermes/scripts/` | 88 |
| 6 | Cron jobs | `cron/jobs.json` | `~/.hermes/cron/jobs.json` | 46 (7 paused) |
| 7 | Docker compose | `docker/` | anywhere (project dirs) | 7 stacks |
| 8 | Config templates | `config/` | `~/.hermes/config.yaml` sections | MCP + providers + memory |
| 9 | Brain subsystems | `brain/` | imported by hooks/plugins | 11 modules |
| 10 | Adapters | `plugins/adapters/` | visualizer/barehands integration | 2 |

---

## 1. Skills (57 live categories)

```bash
# Copy every skill category (this REPLACES the live set — verify first with --dry-run if unsure)
rsync -a --exclude='__pycache__' --exclude='.usage.json' --exclude='.archive' skills/ ~/.hermes/skills/

# Repo-only extras (barehands, first-principles, gsd-core, gstack, hermes-brain, search-first,
# structured-thinking) are included in the rsync above — they install alongside the live set.
```

**Notes:**
- Skills are real copies, not symlinks. The live set and this repo were synced 2026-09-23; live versions won.
- 45 of the 57 categories are custom (not stock Hermes). Stock categories (apple, creative, devops, email, media, mlops, note-taking, productivity, research, social-media, software-development, web, autonomous-ai-agents) were synced from the live set — if a stock Hermes update ships newer versions, prefer the stock ones and re-apply only the custom deltas.
- LAN IPs and home paths are scrubbed to `<GPU-HOST-IP>`, `<LLAMA-CPP-HOST-IP>`, `<HOME-ASSISTANT-IP>`, `<LAN-HOST-IP>`, `$HOME` — replace with real values from the private backup repo (`credentials/env`, `credentials/config.yaml`) after install.

## 2. Hooks (4)

```bash
for h in to-do-capture brain-cognitive-guard brain-memory-consolidator hermes-visualizer-sync; do
  rm -rf ~/.hermes/hooks/$h
  cp -r hooks/$h ~/.hermes/hooks/
done
```
- `to-do-capture` — passive to-do detection → organizer.db (agent:end hook)
- `brain-cognitive-guard` — cognitive guard over tool calls
- `brain-memory-consolidator` — memory consolidation
- `hermes-visualizer-sync` — broadcasts agent events to Hermes Visualizer (:8790) and Barehands (:8794); both adapters in `plugins/adapters/`. Verify those services are running if you want the event stream.

## 3. Plugins (2)

```bash
# decision_logger — logs decisions to brain-postgres:5433 (requires brain-postgres container)
rm -rf ~/.hermes/plugins/decision_logger && cp -r plugins/decision_logger ~/.hermes/plugins/

# cortex-control — action gate, epistemic protocol, experience tracking (writes ~/.hermes/experience.db)
rm -rf ~/.hermes/plugins/cortex-control && cp -r plugins/cortex-control ~/.hermes/plugins/
```
`hermes-achievements` is **built-in** to Hermes — only its state files need restoring (from hermes-backup `plugins-state/`).

## 4. Profiles (14)

```bash
for p in auditor coder default desktop-researcher desktop-worker oracle oracle-researcher \
         personal-organizer planner researcher research 3090-researcher 5060-researcher \
         google-researcher openrouter-researcher; do
  rm -rf ~/.hermes/profiles/$p && mkdir -p ~/.hermes/profiles/$p
  cp profiles/$p/config.yaml ~/.hermes/profiles/$p/ 2>/dev/null
  cp profiles/$p/SOUL.md ~/.hermes/profiles/$p/ 2>/dev/null
done
```
**Important**: each profile also has a full HERMES_HOME at `~/.hermes/<profile>/` (state.db, memories, cron). Those come from the hermes-backup repo (Phase 6 of RESTORE.md), not from here. After both restores, run each profile once (`hermes --profile <name>`) to provision remaining files.

The 4 researcher variants point at specific GPU backends:
- `3090-researcher`, `5060-researcher`, `desktop-worker` → vLLM `<GPU-HOST-IP>:18020` (qwen3.8-27b) / LM Studio `<GPU-HOST-IP>:1234`
- `google-researcher`, `openrouter-researcher` → cloud fallback chains (Nous/OpenRouter)

## 5. Scripts (88)

```bash
# Canonical home is ~/scripts/ (14 cron jobs reference it by absolute path)
mkdir -p ~/scripts && cp scripts/*.py scripts/*.sh scripts/*.txt ~/scripts/ 2>/dev/null

# Legacy home ~/.hermes/scripts/ also referenced by 7 jobs — copy there too
mkdir -p ~/.hermes/scripts && cp scripts/*.py scripts/*.sh scripts/*.txt ~/.hermes/scripts/ 2>/dev/null
```
**Virtual environments (three, each with its own job):**
- `~/.hermes/google-sync-venv` — Google API packages for gmail/gcal sync; isolated so `hermes update` can't break them. Create: `bash scripts/setup_google_venv.sh`. Cron jobs call its python directly.
- `~/.hermes/newsletter_venv` — newsletter pipeline deps (openai, python-telegram-bot, trafilatura, feedparser, beautifulsoup4). Create: `python3 -m venv ~/.hermes/newsletter_venv && ~/.hermes/newsletter_venv/bin/pip install openai python-telegram-bot trafilatura feedparser beautifulsoup4`. The two newsletter cron jobs hardcode this path.
- `~/.hermes/dashboard-venv` — dashboard server deps (fastapi, uvicorn, yfinance, …). Create: `python3 -m venv ~/.hermes/dashboard-venv && ~/.hermes/dashboard-venv/bin/pip install -r requirements.txt`.

Key scripts and what they do:
- `brain_sync.py` (+`brain_sync_cron.py`) — syncs wiki/oracle markdown → embeddings in brain-postgres (Ollama embed, sha256 dedup)
- `export_sessions.py` — weekly export of completed sessions → `~/.hermes/archives/sessions/` JSON
- `graphify_*.py/.sh` — build/refresh graphify graphs for active-wiki and oracle-brain (vLLM semantic extraction)
- `newsletter_builder.py`/`_v2`, `send_newsletter.py`, `_fetch_freshrss.py` — FreshRSS → newsletter pipeline
- `gmail_sync.py`, `gcal_sync.py` — Google sync (auto-detect `~/.hermes/google-sync-venv`); `calendar_sync.py`, `email_sync.py` — dashboard-side integrations
- `hermes_backup.py/.sh`, `backup_all.py`, `backup_databases.py`, `backup_config.py` — backup suite
- `health_check.py`, `hermes_health.py/.sh`, `integrity_check.py`, `check_db_integrity.py` — health checks
- `oracle_search.py`, `oracle_index_update.py`, `rebuild_oracle_index.py`, `fill_oracle_gaps*.sh` — oracle vault ops
- `Gateway-deploy.sh` — nightly CognitivePlatform dashboard deploy to Oracle Cloud (host from `$WG_HOSTNAME`/`$ORACLE_CLOUD_IP`, admin password from `$WG_ADMIN_PASSWORD`; SSH key `~/.ssh/oracle_cloud_key`)
- `telegram_deliver.py` — cron delivery helper
- `config_backup_scrubbed.py` — PII-scrubbed config backup (regex table replaces emails/keys/IPs)
- `model_roles.py` — per-role model resolver (Newsletter/Research/Oracle/Embedding): custom `MODEL_ROLE_*` env vars, falling back to the Hermes main model. Used by newsletter_builder and the dashboard Settings page
- `install_system_deps.sh` — system-layer deps (sqlite3 CLI, jq, rsync, sshpass, uv, gh/docker checks)
- `setup_google_venv.sh` — creates the isolated Google-sync venv

## 6. Cron jobs (46)

```bash
# cron/jobs.json is machine-specific and gitignored. The tracked file is
# cron/jobs.template.json, and setup_cron_jobs.py seeds the live schedule from
# it (existing jobs are preserved, not overwritten):
python scripts/setup_cron_jobs.py

# ${...} placeholders in the template are resolved from the dashboard Settings
# page, not by setup_cron_jobs.py. Every variable the template uses is listed
# in cron/VARIABLES.md -- fill them in there or the jobs carry literal
# ${...} strings.
hermes cron list   # verify the job count and paused set for your install
```
Plus the **system crontab** (outside Hermes):
```bash
crontab -l   # freshrss-summary.sh at 06:00 and 21:00 → scripts/workspace/freshrss-summary.sh
```
Job prompts reference absolute script paths (`~/scripts/...` in the live set — scrubbed to `$HOME/scripts/...` here). If the new install's username differs, sed the paths in jobs.json. Models: jobs inherit the main agent's model unless pinned; the `cron-model-audit` skill documents how to cognition-arena/repin.

## 7. Docker stacks (7 compose files)

```bash
# Brain Postgres (pgvector, :5433) — embeddings/pages/decisions
docker compose -f docker/docker-compose.brain.yml up -d

# Honcho memory backend (api :8000, pgvector db, deriver, redis)
docker compose -f docker/docker-compose.honcho.yml up -d

# Personal organizer API (:8001) — organizer.db REST
docker compose -f docker/docker-compose.personal-organizer.yml up -d

# Firecrawl + Camofox (api :3002, playwright, rabbitmq, redis, nuq-postgres, camofox :9377)
docker compose -f docker/docker-compose.firecrawl.yml up -d

# SearXNG (metasearch, optional)
docker compose -f docker/docker-compose.searxng.yml up -d
```
Env files: `docker/.env.example`, `docker/.env.web-stack.example`, `docker/.env.searxng.example` — real values in hermes-backup `credentials/`.
⚠️ Legacy containers on the old box were labeled with compose paths under `hermes-clean/` — that path is gone; always recreate from these files.

## 7b. Model Roles & env-driven configuration

All scrubbed service endpoints now resolve from `.env` (dashboard Settings page writes them; `dashboard/example.env` documents every variable):

| Env var | Replaces placeholder | Used by |
|---|---|---|
| `INFERENCE_NODE_MAIN` | `<LLAMA-CPP-HOST-IP>` (:8080) | oracle_index_update, verify_deerflow_model |
| `INFERENCE_NODE_VISION` / `INFERENCE_NODE_VLLM` | `<GPU-HOST-IP>` (:1234 / :18020) | profiles, dashboard |
| `INFERENCE_EMBED_URL` | `BRAIN_OLLAMA_URL` hardcoded IPs (:18082) | brain_sync, brain_query, honcho_backfill_embeddings |
| `FRESHRSS_URL` | `freshrss_ip` hardcodes | newsletter_builder(_v2), _fetch_freshrss |
| `HASS_URL` / `HASS_TOKEN` | `<HOME-ASSISTANT-IP>` | dashboard, MCP config |
| `ORACLE_CLOUD_IP` / `WG_HOSTNAME` / `WG_ADMIN_PASSWORD` | `<ORACLE-CLOUD-IP>` + hardcoded admin password | Gateway-deploy.sh |

**Model roles** (`MODEL_ROLE_<ROLE>_{PROVIDER,BASE_URL,API_KEY,MODEL}` for newsletter/research/oracle/embedding): each role defaults to the **Hermes main model** (read live from `~/.hermes/config.yaml` — no duplication); set the four vars on the dashboard Settings → Model Roles card to override just that role. Resolver: `scripts/model_roles.py`.

## 8. Config templates

`docs/mcp-and-providers.example.yaml` — MCP servers (home-assistant, n8n-mcp), memory provider (honcho), model providers (llamaCPP), fallback chain. Tokens are `<TOKEN>` placeholders; real values in hermes-backup `credentials/config.yaml`.

Merge into `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  home-assistant:
    url: http://<HOME-ASSISTANT-IP>:8123/api/mcp
    headers: {Authorization: "Bearer <TOKEN>"}
    timeout: 30
    connect_timeout: 10
  n8n-mcp:
    url: https://<N8N-MCP-HOST>/mcp-server/http
    headers: {Authorization: "Bearer <TOKEN>"}
    timeout: 180
    connect_timeout: 60
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: honcho
```

## 9. Brain subsystems + adapters

`brain/` (11 modules: basal_ganglia, cortex, dmn, epistemology, hippocampus, limbic, schema, social, thalamus, hermes_brain.py) is imported by the hooks/plugins — installing components 2 and 3 activates it. `plugins/adapters/visualizer.py` + `plugins/adapters/barehands.py` are used by the hermes-visualizer-sync hook.

## 10. Verification checklist

```bash
hermes doctor
hermes cron list | wc -l                    # 46
ls ~/.hermes/skills/ | wc -l                # 57+
ls ~/.hermes/hooks/                         # 4 hooks
ls ~/.hermes/plugins/                       # decision_logger, cortex-control (+ built-ins)
docker ps --format '{{.Names}}'             # brain-postgres, honcho×4, firecrawl×6, camofox, organizer-api
curl -s http://127.0.0.1:8000/health        # honcho
sqlite3 ~/.hermes/experience.db "SELECT COUNT(*) FROM operations;"   # ~42k after data restore
hermes --profile oracle "ping"              # profile smoke test
```

## Remnants intentionally NOT included

From the migration audit: `.openclaw/` + `.openclaw.pre-migration/`, `~/wiki.bak-20260816`, `~/hermes-skills-backup`, `.env.bak-*`, `config.yaml.bak-*`, `honcho.json.bak-*`, `state.db.pre-update-emergency-*.bak` (4.7GB), `state.db.retired-wal-*`, 0-byte strays (`~/experience.db`, `~/organizer.db`, `~/.hermes/experience.db`, `~/.hermes/organizer.db`, `~/.hermes/sessions.db`, `~/.hermes/personal_state.db`), `~/oc-work/`, `~/archive/`, `~/.hermes/pets/`, `bot_relay/` (empty roster), `~/Active-Wiki/` (old copy), `~/.hermes/dashboard-venv`. None of these carry unique state.
