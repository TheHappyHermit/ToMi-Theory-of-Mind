# Setting up Honcho: the two `.env` files

Added 2026-09-28. This is the setup instruction for anyone configuring the
LLM models, and it is a **Docker Compose** behaviour, not a Honcho one.
Honcho's source is unmodified.

## The trap

There are two `.env` files in play and they do not reach each other.

| File | Who reads it |
|------|--------------|
| `docker/.env` | Honcho's compose file, for `${...}` interpolation |
| `<repo root>/.env` | `install.py --env-file`, passed to every stack; also written by the Control Panel via `sync_env_file()` |
| `dashboard/.env` | The dashboard's integrations backend, holding the **main agent's** settings |

Docker Compose resolves `${VAR}` from a single location: the `.env` beside
the compose file, unless `--env-file` overrides it for that invocation. It
does not merge files. So:

```bash
# sets HONCHO_DERIVATION_MODEL in the ROOT .env
# then starts Honcho with plain `up`
docker compose -f docker/docker-compose.honcho.yml up -d
#   -> the root .env is ignored, the ${...} DEFAULT applies
```

This is the failure mode that produced the original bug. Someone set the
model, believed it took effect, and the deriver stayed on its built-in
default. Nothing warned, because pydantic is configured `extra="ignore"` and
Compose substitutes the default silently.

**Two working options:**

```bash
# A. put the variables in docker/.env (what this repo's live stack does)
cp .env.honcho.example .env
$EDITOR .env

# B. pass the root file explicitly on every invocation
docker compose --env-file ../.env -f docker-compose.honcho.yml up -d
```

## Verifying it worked

Ask the running container, not the YAML. Reading the compose file proves
nothing, because that is exactly what was misread before.

```bash
docker exec honcho-deriver-1 /app/.venv/bin/python -c "
from src.config import settings
d = settings.DERIVER.MODEL_CONFIG
e = settings.EMBEDDING.MODEL_CONFIG
print('deriver  ', d.model, d.overrides.base_url, d.thinking_effort)
print('embedding', e.model, e.overrides.base_url)
"
```

Expect two *different* models, because the jobs differ:

```
deriver   /models/Qwen3.6-35B-A3B-Q4_K_M.gguf  http://10.0.0.10:8080/v1  none
embedding Qwen3-Embedding-4B-Q8_0.gguf          http://10.0.0.10:18082/v1
```

## The three settings that matter

### 1. Derivation model — use the largest one the host serves

```bash
HONCHO_DERIVATION_MODEL=/models/Qwen3.6-35B-A3B-Q4_K_M.gguf
HONCHO_DERIVATION_BASE_URL=http://10.0.0.10:8080/v1
HONCHO_DERIVATION_API_KEY=sk-local
```

These three feed **every** model config in the compose file: `DERIVER`,
`SUMMARY`, `DREAM` deduction and induction, and all five `DIALECTIC` levels.
One place to change, no compose edit.

Derivation was originally pointed at a 4B (`Qwen3.5-4B-UD-Q4_K_XL.gguf` on
`:18081`) while a 35B sat idle on the same host at `:8080`. There is no
reason to use the small model for work the large one can do on the same
machine, and derivation quality is the single biggest lever on what Honcho
remembers.

### 2. Embedding model — must be an embedding model

Not interchangeable with the derivation model. An embedding model produces
vectors, not observations; a general model makes poor vectors. Swapping them
fails loudly, which is the good case.

`EMBEDDING_VECTOR_DIMENSIONS` must equal the model's **native** output width.
For `Qwen3-Embedding-4B` that is 2560.

Note: a `dimensions` request parameter is *ignored* by this server; the
client truncates client-side. That is the brain's approach too, and it is
why the column is 2000 while the server emits 2560.

### 3. `THINKING_EFFORT=none` on every model config

Required for any reasoning model. Left on, such a model spends its entire
token budget reasoning and returns an **empty string**, which Honcho reports
as:

```
src.utils.json_parser - ERROR - Repair failed: Expecting value: line 1 column 1
```

That is not malformed JSON, it is no JSON. The same overrun also produces
misleading context errors, since thinking tokens count against the budget:

```
BadRequestError: request (5780 tokens) exceeds the available context size (2048 tokens)
```

Measured for "Say OK" on the 4B: thinking on with `max_tokens=20` returned
`content=''`; thinking off returned `content='OK'` in 2 tokens.

## Variable names that do NOT work

An earlier version of `.env.honcho.example` documented these:

```
HONCHO_LLM_PROVIDER  HONCHO_LLM_BASE_URL  HONCHO_LLM_MODEL  HONCHO_LLM_API_KEY
```

**None of them are read by Honcho.** `config.py` uses `env_prefix` of
`"LLM_"`, `"DERIVER_"`, `"EMBEDDING_"`, `"SUMMARY_"`, `"DREAM_"` and
`"DIALECTIC_"`; grep for `HONCHO_LLM` in `config.py` returns nothing.
Setting them from the Control Panel had no effect whatsoever.

Two more traps in the same family:

- `DERIVER_MODEL_CONFIG__BASE_URL` (flat) is **silently ignored**.
  `ConfiguredModelSettings` has no top-level `base_url`/`api_key`; both live
  under `overrides`. Correct: `..._OVERRIDES__BASE_URL`.
- `LLM_MODEL` and `LLM_DIALECTIC_MODEL` are read by *other* subsystems, not
  by the deriver. The deriver reads `DERIVER_MODEL_CONFIG`.

Because pydantic is `extra="ignore"`, all three mistakes produce no warning
at all. They are indistinguishable from success unless you query the running
container with the snippet above.

## Confirming it is actually working

The deriver fails silently by default. It reports healthy while retrying in
a loop, and it marks failed batches `processed = true` so nothing ever
retries them.

```bash
# 1. no errors
docker logs honcho-deriver-1 --since 5m | grep -cE 'ERROR|Missing API key|Repair failed'

# 2. the old default must be gone
docker logs honcho-deriver-1 --since 5m | grep -c 'gpt-5.4-mini'

# 3. the queue must actually be draining
docker exec honcho-database-1 psql -U honcho -d honcho -tAc \
  "SELECT count(*) FROM documents;"
docker exec honcho-database-1 psql -U honcho -d honcho -tAc \
  "SELECT count(*) FROM queue WHERE NOT processed;"
```

All three, not just the first. Zero errors with a static queue means the
deriver is idle, not fixed.

## If a backlog was processed while broken

Failed rows are written with `processed = true` and the error text intact, so
they are never retried. Requeue them:

```sql
UPDATE queue SET processed = false, error = NULL
 WHERE task_type = 'representation' AND processed = true AND error IS NOT NULL;
```

Scoped, no deletions, no payload changes. This requeued 2,337 rows.
