#!/usr/bin/env bash
#
# Graphify extraction — Active Wiki only
# Runs semantic extraction on ~/.hermes/active-wiki
# Parameters: vllm_qwen36_nothink provider (thinking disabled), token budget 16000, clustering enabled
#
# Usage: bash ~/.hermes/scripts/graphify_active_wiki.sh
#
# NOTE: This script is superseded by graphify_active_wiki_py.py which uses
# a Python wrapper that sets env vars internally (more reliable). The cron job
# uses the Python wrapper. This shell script is kept for manual runs.
#
# --force was removed here. It skips the incremental manifest gate and the
# semantic cache, so every manual run re-extracted the whole wiki and
# overwrote graph.json even when the rebuild came back with fewer nodes. For a
# growing wiki that is data and token loss, not a refresh. If a force rebuild
# is genuinely wanted -- after a refactor that deletes code -- run graphify
# directly with --force rather than putting it back in the scheduled path.
#

set -euo pipefail

export GRAPHIFY_VLLM_QWEN_API_KEY="***"
export GRAPHIFY_MAX_OUTPUT_TOKENS=131072
export GRAPHIFY_MAX_RETRIES=0
export GRAPHIFY_API_TIMEOUT=1800

# GRAPHIFY_FORCE has the same effect as the flag; make sure it is not inherited.
unset GRAPHIFY_FORCE || true

cd $HOME/.hermes

graphify extract $HOME/.hermes/active-wiki \
  --token-budget 16000 \
  --max-concurrency 1 \
  --api-timeout 1800 \
  --no-gitignore \
  --backend vllm_qwen36_nothink
