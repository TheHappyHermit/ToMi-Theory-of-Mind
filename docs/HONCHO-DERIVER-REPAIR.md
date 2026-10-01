# The Honcho deriver was silently failing on every message

Added 2026-09-28. The deriver had never successfully derived a peer
representation. It reported healthy the entire time.

## What it looked like from outside

    docker ps   -> honcho-deriver-1  Up (healthy)
    restart count -> 0

## What was actually happening

    docker logs honcho-deriver-1 | grep -c ValidationException
    941

Every representation batch failed, retried three times, and was marked
`processed = true` with the error recorded alongside. So the deriver believed
it had done the work. 2,337 messages sat unembedded and the queue held
nothing pending.

## Three separate faults, not one

### 1. The wrong model config

The deriver reads `DERIVER.MODEL_CONFIG`. It defaults to:

    model     = gpt-5.4-mini
    transport = openai
    overrides = api_key=None api_key_env=None base_url=None

`client_for_model_config()` then raises:

    ValidationException: Missing API key for openai model config

`LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_DIALECTIC_MODEL` are all
set in the compose file and none of them affect this path. Setting
`DIALECTIC_LEVELS__*` -- the obvious first guess, since the error mentions
"openai model config" and dialectic is the other big consumer -- parses
correctly and changes nothing. Verified by asking the running container what
it parsed rather than by reading the YAML.

### 2. The key nesting is `overrides`, not top level

    ConfiguredModelSettings.model_fields
    ['model', 'transport', 'fallback', ..., 'overrides']

There is no `base_url` or `api_key` on the model itself. They live under
`overrides`, which is why the working embedding config uses
`EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL`. The first attempt used the
flat form; the vars landed in the container and were silently ignored because
pydantic drops unknown keys under `extra="ignore"`.

### 3. The model is a reasoning model and was thinking itself out of the answer

With the config fixed, the next error appeared:

    src.utils.json_parser - ERROR - Repair failed: Expecting value: line 1 column 1

Not a malformed response -- an EMPTY one:

    "Say OK" -> finish_reason=length, content=''
               reasoning_content='Thinking Process: 1. **Analyze the Request:** ...'
               completion_tokens=20

Qwen3.5-4B spent the entire 20-token budget thinking and emitted nothing, so
Honcho received an empty string where it expected JSON. This is also what
produced the earlier `exceeds the available context size (2048 tokens)`
error: thinking tokens are counted against the budget, and with a small
context a long think overruns it.

Fix: `THINKING_EFFORT=none` on every model config. Same prompt, same server:

    max_tokens=800, thinking on   -> 90 completion tokens, content 'OK'
    chat_template_kwargs
      {enable_thinking:false}     ->  2 completion tokens, content 'OK'

Honcho exposes this as `thinking_effort` on `ConfiguredModelSettings`,
accepting none/minimal/low/medium/high/xhigh/max.

## The settings that were all wrong in the same way

`gpt-5.4-mini` is the default in five places in config.py, and every one had
no base_url and no key:

    DERIVER.MODEL_CONFIG                     <- the one that was failing
    DIALECTIC.LEVELS[<each of 5>].MODEL_CONFIG
    SUMMARY.MODEL_CONFIG
    DREAM.DEDUCTION_MODEL_CONFIG
    DREAM.INDUCTION_MODEL_CONFIG

All are now set to the local llama.cpp server rather than waiting to be
discovered one crash at a time.

## Requeueing the failed work

The rows were `processed = true`, so nothing would ever retry them. Scoped
UPDATE, no deletions, no payload changes:

    UPDATE queue SET processed = false, error = NULL
     WHERE task_type = 'representation' AND processed = true AND error IS NOT NULL;
    -- UPDATE 2337

`DERIVER_WORKERS` raised 1 -> 4; at 1 worker the backlog drained too slowly
to be useful.

## Verified after the fix

    errors in last 2m            : 0
    "Missing API key"            : 0
    "Repair failed"              : 0
    documents created            : 5 -> 28, still climbing
    queue pending                : 2338 -> 2266, still draining

Every model config confirmed from inside the running container:

    DERIVER     thinking_effort=none  model=Qwen3.5-4B-UD-Q4_K_XL.gguf  base_url=http://10.0.0.10:18081/v1
    SUMMARY     thinking_effort=none  model=Qwen3.5-4B-UD-Q4_K_XL.gguf  base_url=http://10.0.0.10:18081/v1
    DREAM.ded   thinking_effort=none  model=Qwen3.5-4B-UD-Q4_K_XL.gguf  base_url=http://10.0.0.10:18081/v1
    DREAM.ind   thinking_effort=none  model=Qwen3.5-4B-UD-Q4_K_XL.gguf  base_url=http://10.0.0.10:18081/v1
    DIAL.<all>  thinking_effort=none  model=Qwen3.5-4B-UD-Q4_K_XL.gguf  base_url=http://10.0.0.10:18081/v1

The embedding side was already correct and was not changed:
`LLM_EMBEDDING_BASE_URL=http://10.0.0.10:18082/v1` with
`Qwen3-Embedding-4B-Q8_0.gguf` at 2560 dimensions.

## The lesson, again

Three faults, each individually invisible, and the container reported healthy
throughout. A component that fails every time it is asked to do its job is
not a component that is working. The check that would have caught this is
"did the deriver create any representations in the last day", and nothing
like that existed.
