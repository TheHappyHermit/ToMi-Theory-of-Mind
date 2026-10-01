#!/usr/bin/env bash
#
# Graphify extraction — Oracle Brain only
# Runs semantic extraction on ~/.hermes/oracle/brain
# Parameters tuned for Qwen3.6-35B-A3B-Q4_K_M on the configured llama.cpp endpoint
#
# Usage: bash ~/.hermes/scripts/graphify_oracle_brain.sh
#
# --force was removed here. It skips the incremental manifest gate and the
# semantic cache, and overwrites graph.json even when the rebuild comes back
# with fewer nodes. This graph currently holds 6,283 nodes; a forced run
# discards all of them and re-pays the extraction cost for every one. For a
# scheduled ingest of a growing wiki that is data and token loss, not a
# refresh. If a force rebuild is genuinely wanted -- after a refactor that
# deletes code -- run graphify directly with --force rather than putting it
# back in this path. GRAPHIFY_FORCE does the same thing, so unset it below.
#

set -euo pipefail

SOURCE="$HOME/.hermes/oracle/brain"

LOG_DIR="$HOME/.hermes/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/graphify-oracle-brain.log"

unset GRAPHIFY_FORCE || true

# Rotate if too large
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 10485760 ]; then
    mv "$LOG_FILE" "${LOG_FILE}.1"
fi

{
echo "=== graphify-oracle-brain started at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "Source: $SOURCE"
echo "Token budget: 16000 | Concurrency: 1 | API timeout: 1800s"
echo "Max output tokens: 131072 | Max retries: 0 | Backend: vllm_qwen36_nothink (thinking disabled)"
echo ""

graphify extract "$SOURCE" \
  --token-budget 16000 \
  --max-concurrency 1 \
  --api-timeout 1800 \
  --no-gitignore \
  --backend vllm_qwen36_nothink

echo ""
echo "=== graphify-oracle-brain finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=$? ==="
} >> "$LOG_FILE" 2>&1
