#!/usr/bin/env bash
# ==============================================================================
# setup_google_venv.sh — isolated Python environment for Google sync scripts
# ==============================================================================
# Creates ~/.hermes/google-sync-venv with ONLY the Google API packages that
# gmail_sync.py and gcal_sync.py need. This isolation means `hermes update`
# (which can rebuild ~/.hermes/hermes-agent/venv) can never silently break
# Gmail/Calendar sync.
#
# After running, the sync scripts auto-detect this venv. Cron jobs should call:
#   ~/.hermes/google-sync-venv/bin/python3 ~/scripts/gmail_sync.py
#   ~/.hermes/google-sync-venv/bin/python3 ~/scripts/gcal_sync.py
#
# Idempotent: safe to re-run (upgrades in place).
# ==============================================================================
set -euo pipefail

VENV_DIR="${HOME}/.hermes/google-sync-venv"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[google-venv] Creating/updating ${VENV_DIR}"

if command -v uv >/dev/null 2>&1; then
    # uv is fast and Hermes ships it at ~/.hermes/bin/uv
    uv venv --python 3.11 --seed "${VENV_DIR}" 2>/dev/null || uv venv "${VENV_DIR}" --seed
    uv pip install --python "${VENV_DIR}/bin/python3" \
        "google-api-python-client>=2.100" \
        "google-auth>=2.20" \
        "google-auth-httplib2>=0.2.0" \
        "google-auth-oauthlib>=1.0.0"
else
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip -q
    "${VENV_DIR}/bin/pip" install \
        "google-api-python-client>=2.100" \
        "google-auth>=2.20" \
        "google-auth-httplib2>=0.2.0" \
        "google-auth-oauthlib>=1.0.0"
fi

# Smoke test: can the venv import everything the sync scripts need?
"${VENV_DIR}/bin/python3" - <<'PYEOF'
import googleapiclient, google.auth, google_auth_oauthlib, googleapiclient.discovery
print("[google-venv] ✓ all Google API packages import cleanly")
PYEOF

echo "[google-venv] Done. Sync scripts will auto-detect this venv."
echo "[google-venv] Cron job invocations should use:"
echo "    ${VENV_DIR}/bin/python3 \${HOME}/scripts/gmail_sync.py"
echo "    ${VENV_DIR}/bin/python3 \${HOME}/scripts/gcal_sync.py"
