#!/usr/bin/env bash
# ==============================================================================
# Hermes Brain — POSIX Shell Installer Wrapper
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python 3 is required but was not found in PATH."
    exit 1
fi

exec "$PYTHON_CMD" "$SCRIPT_DIR/install.py" "$@"
