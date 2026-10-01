# Cron Job Variables

`cron/jobs.template.json` is the canonical, PII-free definition of every
Hermes cron job: 50 jobs, each with its full prompt, schedule, skills,
profile and model.

It contains **no real hostnames, no IP addresses, no usernames, no chat
identifiers and no absolute home paths**. Everything deployment-specific is
a `${VARIABLE}` placeholder.

## How a variable reaches a job

```
dashboard Settings page  (operator types the value once)
        ↓
dashboard .env           (persisted)
        ↓
env_mappings registry     (dashboard/integrations_backend.py)
        ↓
${VARIABLE} in cron/jobs.template.json
```

An operator installs this repo, opens the dashboard, fills in the settings
below, and the cron jobs resolve them. No job prompt needs editing.

Four of the variables below are **already registered** in
`env_mappings`, so they appear on the dashboard's Settings page today with
no dashboard change required:

| Variable | Settings key | Example value |
|---|---|---|
| `HERMES_HOME` | `hermes_home` | `/home/operator` |
| `INFERENCE_NODE_MAIN` | `inference_node_main` | `http://inference-host:8080` |
| `TELEGRAM_CHAT_ID` | `telegram_chat_id` | *(not embedded — set in dashboard)* |

## Variables this template uses

| Variable | Replaces | Notes |
|---|---|---|
| `HERMES_HOME` | `/home/<user>` | Already in the registry. Absolute home path. |
| `INFERENCE_NODE_MAIN` | the LAN inference host, its port and `/v1` | Already in the registry. Includes scheme, host, port and API path as one value. |
| `HERMES_DATA_DIR` | `~/<data-dir>/` | The data directory holding `active-wiki/`, `oracle/brain/`, `exchange/`, `logs/`, `personal-organizer/`. Set to the dot-directory root, without a trailing slash. |
| `MODEL_DIR` | `/models/` | Directory holding local `*.gguf` files, when a model is served as a local file rather than over HTTP. |
| `MODEL_UTILITY` | the utility-tier model | Short deterministic jobs: lints, backups, status checks, newsletters. 17 jobs. |
| `MODEL_DEEP` | the deep-reasoning model | Long passes: consolidation, research lanes, audits, briefings. 17 jobs. |
| `MODEL_DESKTOP_A` | the first desktop worker's model | Served from the first desktop node. 1 job. |
| `MODEL_DESKTOP_B` | the second desktop worker's model | Served from the second desktop node. 1 job. |
| `DB_BRAIN` | the brain SQLite filename | e.g. `brain.db` → whatever the install calls it. |
| `SCRIPT_BACKUP` | the backup script filename | e.g. `backup.sh` → whatever the install calls it. |
| `SCRIPT_HEALTH` | the health-check script filename | e.g. `health.sh` → whatever the install calls it. |
| `SCRIPT_DB_CHECK` | the database integrity-checker filename | e.g. `check_databases.py` → whatever the install calls it. |
| `SCRIPT_DB_INIT` | the database initialiser filename | e.g. `init_experience_index.py` → whatever the install calls it. |
| `CLAUDE_CODE_SOCKET` | the Claude Code subscription socket path | Used by the researcher profiles. |

## Where a variable still needs adding

All eleven of these are now registered in `env_mappings`
(`dashboard/integrations_backend.py`), so each appears on the dashboard
Settings page with no further change:

```
MODEL_DIR  MODEL_UTILITY  MODEL_DEEP  MODEL_DESKTOP_A  MODEL_DESKTOP_B
DB_BRAIN  SCRIPT_BACKUP  SCRIPT_HEALTH  SCRIPT_DB_CHECK  SCRIPT_DB_INIT
CLAUDE_CODE_SOCKET
```

`HERMES_DATA_DIR` was already registered and appears in the table above.

An entry in `env_mappings` is what puts a variable on the Settings page; a
variable with no entry stays a literal `${...}` in `jobs.json` and the job
fails on an unexpanded string. When you add a variable to
`jobs.template.json`, add its mapping here at the same time.

The dashboard already has a single `llm_model` / `LLM_MODEL` setting. The
four `MODEL_*` tiers are deliberately separate from it: a job's model is a
choice of *which tier answers it*, and one global model setting cannot
express a 4B utility tier alongside a deep-reasoning tier. If you would
rather have exactly one model for everything, point all four tiers at
`LLM_MODEL` and add just the three extra keys.

They work without this — the template is correct either way — but without
the registry entry an operator has to hand-edit `.env` instead of using the
Settings page.

## Regenerating

The template is generated, never hand-edited:

```bash
python3 scripts/generate_cron_template.py \
    --live ~/.hermes/cron/jobs.json \
    --out  cron/jobs.template.json \
    --manifest cron/variables-manifest.json
```

The generator **only reads** the live `jobs.json`. It refuses to write
anything if residual PII is detected, so a template that lands on `main` is
one that passed the check.

Runtime bookkeeping (`last_run_at`, `next_run_at`, `dispatch_*`,
`model_snapshot`, and similar) is dropped: the scheduler rewrites it every
tick, so committing it would be noise and would make the template churn.

## The live file is not tracked

`cron/jobs.json` is the live scheduler state. It is **gitignored** and must
stay that way — it contains real hosts, paths and chat identifiers. Only the
generated template is committed.
