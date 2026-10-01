#!/bin/bash
# Honcho deriver entrypoint with LLM key-presence check and healthcheck
set -e

# Check for LLM key
if [ -z "$LLM_EMBEDDING_BASE_URL" ]; then
    echo "[deriver] ERROR: LLM_EMBEDDING_BASE_URL is not set. Deriver needs an LLM endpoint."
    echo "[deriver] Set LLM_EMBEDDING_BASE_URL in .env (e.g., http://<LLAMA-CPP-HOST-IP>:18082/v1)"
    exit 1
fi

# Check for API key
if [ -z "$LLM_EMBEDDING_API_KEY" ]; then
    echo "[deriver] WARNING: LLM_EMBEDDING_API_KEY is not set. Some providers may require it."
fi

# Check that the LLM endpoint is reachable
echo "[deriver] Checking LLM endpoint: $LLM_EMBEDDING_BASE_URL"
if ! curl -sf --max-time 5 "$LLM_EMBEDDING_BASE_URL/models" > /dev/null 2>&1; then
    echo "[deriver] WARNING: LLM endpoint $LLM_EMBEDDING_BASE_URL is not reachable."
    echo "[deriver] Deriver will start but may fail to derive until endpoint is available."
fi

echo "[deriver] LLM endpoint check complete. Starting deriver..."
exec "/app/.venv/bin/python" "-m" "src.deriver"
