#!/bin/bash
# Graphify Active Wiki Ingestion wrapper
# Sets env vars for llama.cpp server then runs graphify extract
#
# --force was removed: it skips the incremental manifest gate and the semantic
# cache, so a scheduled ingest re-extracted the whole wiki and overwrote
# graph.json even when the rebuild came back with fewer nodes. GRAPHIFY_FORCE
# has the same effect, so it is unset here too. If a force rebuild is genuinely
# wanted after a refactor that deletes code, run graphify directly with it.

export GRAPHIFY_VLLM_QWEN_API_KEY="***"
export GRAPHIFY_MAX_OUTPUT_TOKENS=131072
export GRAPHIFY_MAX_RETRIES=0
export GRAPHIFY_API_TIMEOUT=1800
unset GRAPHIFY_FORCE || true

cd $HOME/.hermes

exec graphify extract $HOME/.hermes/active-wiki --token-budget 16000 --max-concurrency 1 --api-timeout 1800 --no-gitignore --backend vllm_qwen36_nothink
