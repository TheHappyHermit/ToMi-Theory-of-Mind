#!/usr/bin/env bash
# ==============================================================================
# install_system_deps.sh — system-layer dependencies for Hermes Brain
# ==============================================================================
# Installs the NON-pip tools the repo relies on. Run once on a fresh box,
# before `pip install -r requirements.txt`.
#
# Layers:
#   1. apt packages (sqlite3 CLI, jq, rsync, sshpass)
#   2. uv tool installs (none currently — graphify CLI is being replaced and
#      gbrain is deprecated/removed; do NOT install either)
#   3. Checks for tools that have their own installers (gh, docker, bun)
#
# Idempotent: safe to re-run. Skips anything already present.
# ==============================================================================
set -euo pipefail

log()  { echo "[deps] $*"; }
ok()   { echo "[deps] ✓ $*"; }
skip() { echo "[deps] · $* (already present)"; }

# ── 1. apt packages ──────────────────────────────────────────────────────────
APT_PKGS=(sqlite3 jq rsync sshpass)

if command -v apt-get >/dev/null 2>&1; then
    MISSING=()
    for pkg in "${APT_PKGS[@]}"; do
        command -v "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
    done
    if [ ${#MISSING[@]} -gt 0 ]; then
        log "Installing apt packages: ${MISSING[*]}"
        sudo apt-get update -qq && sudo apt-get install -y "${MISSING[@]}"
    else
        skip "apt packages ${APT_PKGS[*]}"
    fi
else
    echo "[deps] WARNING: apt-get not found (non-Debian system?)"
    echo "       Install manually: ${APT_PKGS[*]}"
    for pkg in "${APT_PKGS[@]}"; do
        command -v "$pkg" >/dev/null 2>&1 || echo "[deps] ✗ MISSING: $pkg"
    done
fi

# ── 2. uv tools ───────────────────────────────────────────────────────────────
# NOTE (2026-09): graphify CLI is scheduled for replacement — do not install.
# gbrain is deprecated and removed from this repo — do not install.

if command -v uv >/dev/null 2>&1; then
    skip "uv present (no uv tools to install currently)"
else
    echo "[deps] · uv not found — Hermes ships it at ~/.hermes/bin/uv; installing standalone:"
    curl -LsSf https://astral.sh/uv/install.sh | sh || echo "[deps] ✗ uv install failed (optional)"
fi

# ── 3. tools with their own installers ────────────────────────────────────────
# gh (GitHub CLI) — required for repo management skills and backups
if command -v gh >/dev/null 2>&1; then
    skip "gh"
else
    echo "[deps] · gh not found — install: https://cli.github.com/ (needed for github skills)"
fi

# docker — required for the container stack (brain-postgres, honcho, firecrawl, organizer)
if command -v docker >/dev/null 2>&1; then
    skip "docker"
else
    echo "[deps] · docker not found — install: https://docs.docker.com/engine/install/"
fi

# ── browser: a real Chromium BINARY (not a pip package) ──────────────────────
# Checks, in order: the documented override, a system Chrome/Chromium on PATH,
# then Playwright's cache. This mirrors hermes' own _chromium_installed() so the
# two cannot disagree.
_chromium_ok() {
    if [ -n "${AGENT_BROWSER_EXECUTABLE_PATH:-}" ] && [ -x "$AGENT_BROWSER_EXECUTABLE_PATH" ]; then
        return 0
    fi
    for c in google-chrome chromium chromium-browser chrome; do
        command -v "$c" >/dev/null 2>&1 && return 0
    done
    for root in "${PLAYWRIGHT_BROWSERS_PATH:-}" "$HOME/.cache/ms-playwright"; do
        [ -n "$root" ] && [ -d "$root" ] || continue
        ls "$root" 2>/dev/null | grep -qE '^(chromium|chromium_headless_shell)-' && return 0
    done
    return 1
}

if _chromium_ok; then
    skip "chromium (browser automation)"
else
    echo "[deps] · no Chromium binary found — browser automation will not start."
    echo "         npx playwright install chromium        # binary only, no root"
    echo "         npx playwright install-deps chromium   # system libs, needs sudo"
fi

# AppArmor blocks Chrome's zygote sandbox on Ubuntu. This is the single most
# common "browser is broken" report and it is NOT a missing install: the binary
# is present and Chromium still dies with a zygote_host FATAL. Check the sysctl
# and print the fix, because a stale AGENT_BROWSER_ARGS in the environment is
# also worth knowing about.
if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null)" = "1" ]; then
    echo "[deps] · AppArmor restricts unprivileged user namespaces (Ubuntu default)."
    if [ -n "${AGENT_BROWSER_ARGS:-}" ]; then
        echo "         AGENT_BROWSER_ARGS is set to: $AGENT_BROWSER_ARGS"
    else
        echo "         Chrome will fail with a zygote_host FATAL. Add to your shell profile:"
        echo "           export AGENT_BROWSER_ARGS=\"--no-sandbox,--disable-dev-shm-usage\""
    fi
fi

# ── 4. summary ────────────────────────────────────────────────────────────────
echo ""
ok "System deps done. Next steps:"
echo "    pip install -r requirements.txt          # Python deps (or uv pip install)"
echo "    bash scripts/setup_google_venv.sh        # isolated venv for gmail/gcal sync"
echo "    python install.py --auto                 # full stack install"
