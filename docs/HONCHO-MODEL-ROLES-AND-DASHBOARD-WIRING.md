# Which model does Honcho use, and can the dashboard configure it?

Added 2026-09-28. Answers two questions: what the local models are actually
doing, and whether the Command Deck dashboard can supply Honcho's LLM
settings so a new install does not have to hand-edit a .env file.

## Part 1: Honcho uses BOTH local models, for different jobs

This is not a mistake and not duplicated effort. They do genuinely different
things.

| Job | Port | Model | Purpose |
|-----|------|-------|---------|
| Embedding | `18082` | `Qwen3-Embedding-4B-Q8_0.gguf` | turns messages into 2560-dim vectors for search |
| Derivation | `18081` | `Qwen3.5-4B-UD-Q4_K_XL.gguf` | reads messages and writes the observations/representations |

Confirmed by asking the running container, not by reading the compose file:

    settings.EMBEDDING.MODEL_CONFIG.model      = Qwen3-Embedding-4B-Q8_0.gguf
    settings.EMBEDDING.VECTOR_DIMENSIONS       = 2560
    settings.EMBEDDING.MODEL_CONFIG.overrides.base_url = http://10.0.0.10:18082/v1

    settings.DERIVER.MODEL_CONFIG.model        = /models/Qwen3.5-4B-UD-Q4_K_XL.gguf
    settings.DERIVER.MODEL_CONFIG.overrides.base_url = http://10.0.0.10:18081/v1
    settings.DERIVER.MODEL_CONFIG.thinking_effort = none

And the two ports do serve different models:

    18081 -> /models/Qwen3.5-4B-UD-Q4_K_XL.gguf
    18082 -> /models/Qwen3-Embedding-4B-Q8_0.gguf

**Is this the right arrangement?** Yes. An embedding model cannot derive
observations -- it produces vectors, not text. A 4B general model produces
poor embeddings. Pointing either at the other's port fails immediately and
visibly. The one caveat is quality: Qwen3.5-4B is a small model, so the
observations it writes will be shallower than a frontier model would produce.
That is a deliberate speed/cost trade, and it is the same trade already made
for graphify and the brain.

## Part 2: Can the dashboard configure Honcho? Not by pointing at .env

The research question was whether the Honcho container could read the
Command Deck's `.env`. **It cannot, and the dashboard's LLM settings do not
live in a `.env` file at all.**

### What the dashboard actually writes

`dashboard/llm_config.py`:

    def config_path() -> Path:  return _hermes_home() / "config.yaml"
    def auth_path()   -> Path:  return _hermes_home() / "auth.json"

So the dashboard's LLM settings pane edits `~/.hermes/config.yaml` and
`~/.hermes/auth.json`. It has an `openai_compat` and a `llamacpp` provider
entry precisely so a local endpoint can be selected.

`dashboard/.env` is a *different* file, written by `sync_env_file()` in
`dashboard/integrations_backend.py` for the integrations backend, and it
currently holds:

    LLM_PROVIDER=openrouter
    LLM_BASE_URL=https://openrouter.ai/api/v1
    LLM_MODEL=anthropic/claude-sonnet-4

Those are the *main agent's* settings, not Honcho's. Reading them into Honcho
would point derivation at a paid cloud model, which is the opposite of the
intent.

### What a container can actually consume

Docker Compose reads a `.env` next to the compose file for
`${VAR}` interpolation, and `env_file:` passes a file's contents into the
container as environment variables. Both are per-stack. A container cannot
follow a symlink out of its own compose directory to a file the operator
edits elsewhere and expect re-resolution, because the values are read once at
`docker compose up` time.

So the workable options are:

1. **A shared env file passed to every stack that needs it.** Every service
   that needs these values gets the same `env_file:`. Works, but now one file
   gates several stacks and a new install must be told to create it.
2. **The dashboard writes a generated file and the stack includes it.**
   `env_file: [ .env, .env.generated ]`. The dashboard can regenerate
   `.env.generated` on save, so a new install only has to point the compose at
   a path the dashboard already owns.
3. **Hand-edit `.env`.** Zero machinery, but every new install repeats it.

Option 2 is the only one that gives a new install something working without
editing anything, and it does not require changing Honcho's base install: the
compose file gains one extra `env_file:` line, which is additive.

### What would be needed, concretely

- A `docker/.env.honcho.example` documenting the LLM block, since the existing
  `docker/.env.example` is for the Firecrawl/CamoFox web stack and does not
  cover Honcho at all.
- A settings section in the dashboard that writes the Honcho LLM block into
  whichever file the compose file reads.
- The compose file to list that file in `env_file:` for `api` and `deriver`.

None of this is done. The deriver is currently configured with literal values
in the compose file, which is the least portable arrangement -- it works on
this machine and gives a new installer nothing to copy.

**Recommendation:** do option 2, and treat it as a separate piece of work from
the deriver repair, because it touches a file that a fresh clone reads. The
deriver is functional now; the dashboard wiring is about portability and can
follow.
