#!/usr/bin/env python3
"""Verify dashboard Settings wiring: HTML fields <-> JS save/load <-> backend env maps <-> example.env.

Run from repo root:  python3 scripts/verify_settings_wiring.py
Exit 0 = all checks pass. Any FAIL prints details.

Keys in ENV_ONLY_KEYS are consumed directly via os.environ (notify_dispatcher.py,
hermes_interface.py, backend/routes/*) with no Settings UI field, by design.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard"

# Env vars read directly from os.environ by consumers; no Settings UI field by design.
ENV_ONLY_KEYS = {
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL",
    "SLACK_BOT_TOKEN", "HERMES_API_KEY", "JELLYFIN_TOKEN",
    "RADARR_API_KEY", "SONARR_API_KEY",
    # infra vars used by deploy scripts / external tooling, not dashboard settings
    "DATABASE_URL", "HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN",
    "OPENROUTER_API_KEY", "JINA_API_KEY", "MAX_ARTICLES", "LOOKBACK_HOURS",
    "HERMES_GATEWAY_URL", "ORACLE_CLOUD_IP", "WG_HOSTNAME", "WG_ADMIN_PASSWORD",
    "WG_WEBROOT", "WG_SOURCE_DIR", "FRESHRSS_HOST", "FRESHRSS_USERNAME",
    "FRESHRSS_API_PASSWORD", "SMTP_HOST", "SMTP_USER", "SMTP_PASS",
}
# Per-role model overrides are handled by the Model Roles card (prefix-mapped).
ROLE_PREFIXES = ("MODEL_ROLE_", "ALPHAVANTAGE", "MASSIVE", "FINNHUB", "FMP_", "TWELVEDATA", "FRED_")

# Files allowed to mention the personal domain (scrubber regexes must match it; script names).
WG_ALLOWED = {
    "scripts/config_backup_scrubbed.py",   # scrubber's own regex patterns
    "scripts/Gateway-deploy.sh",      # deploy script name (host from env)
    "dashboard/example.env",               # comment naming the deploy target
    "docs/FULL-COMPONENT-INSTALL.md",      # doc naming the script
}


# Files exempt from the PII sweep: the scrubber must contain the real patterns
# to match them in backups; this script must contain them to detect regressions.
PII_EXEMPT = {
    "scripts/config_backup_scrubbed.py",
    "scripts/verify_settings_wiring.py",
}


def main() -> int:
    html = (DASH / "index.html").read_text(encoding="utf-8", errors="replace")
    js = (DASH / "app-integrations.js").read_text(encoding="utf-8", errors="replace")
    py = (DASH / "integrations_backend.py").read_text(encoding="utf-8", errors="replace")
    syspy = (DASH / "backend" / "routes" / "system.py").read_text(encoding="utf-8", errors="replace")
    env = (DASH / "example.env").read_text(encoding="utf-8", errors="replace")
    n8n_skill = (ROOT / "skills/mcp/n8n-mcp-integration/SKILL.md").read_text(encoding="utf-8", errors="replace")
    ha_skill = (ROOT / "skills/mcp/home-assistant-mcp-integration/SKILL.md").read_text(encoding="utf-8", errors="replace")

    checks = []
    html_ids = set(re.findall(r'id="([a-z0-9-]+)"', html))
    js_ids = set(re.findall(r"getElementById\('([a-z0-9-]+)'\)", js))

    # 1. All settings field IDs referenced by JS exist in HTML
    missing = [i for i in js_ids if i not in html_ids
               and any(k in i for k in ("hass", "n8n", "mcp", "inference", "voice", "path", "pg", "brain", "telegram", "discord", "smtp", "port"))
               and i != "btn-n8n-refresh"]  # generated dynamically by JS
    checks.append(("JS settings field IDs exist in HTML", not missing, str(missing)))

    # 2. Voice gateway save wiring (JS collects fields into save payload)
    checks.append(("voice save wiring in JS",
                   "checkField(document.getElementById('input-url-voice'), 'voice_gateway_url')" in js, ""))

    # 3. Voice env mapping in backend get-map AND save-map
    checks.append(("voice env mapping in backend (get+save)",
                   py.count('"voice_gateway_url": "VOICE_GATEWAY_URL"') >= 2, ""))

    # 4. HASS MCP token full chain
    checks.append(("HASS MCP chain (HTML+JS+backend+env+docs)",
                   'id="input-mcp-token-hass"' in html
                   and "'hass_mcp_token'" in js
                   and py.count('"hass_mcp_token": "HASS_MCP_TOKEN"') >= 2
                   and "HASS_MCP_TOKEN=" in env
                   and "HASS_MCP_TOKEN=" in (DASH / "SETUP_ENV.md").read_text(encoding="utf-8", errors="replace"), ""))

    # 5. Skills reference env vars, not hardcoded hosts/tokens
    checks.append(("n8n skill references N8N_MCP_TOKEN",
                   "N8N_MCP_TOKEN" in n8n_skill and "Gateway" not in n8n_skill, ""))
    checks.append(("HA skill references HASS_MCP_TOKEN",
                   "HASS_MCP_TOKEN" in ha_skill and "Gateway" not in ha_skill
                   and "eyJhbGciOi" not in ha_skill, ""))

    # 6. Homelab mesh + inference cluster read from settings, not hardcoded IPs
    checks.append(("mesh reads hass_url/n8n_url",
                   '"config_key": "hass_url"' in syspy and '"config_key": "n8n_url"' in syspy, ""))
    checks.append(("inference cluster reads settings",
                   "_node_endpoint(" in syspy and "10.0.0.10" not in syspy, ""))

    # 7. example.env keys are either backend-mapped or whitelisted env-only
    env_keys = set(re.findall(r"^([A-Z][A-Z0-9_]+)=", env, re.M))
    py_map_keys = set(re.findall(r'"[a-z0-9_]+": "([A-Z][A-Z0-9_]+)"', py))
    unmapped = sorted(k for k in env_keys - py_map_keys - ENV_ONLY_KEYS
                      if not k.startswith(ROLE_PREFIXES))
    checks.append(("example.env keys mapped in backend", not unmapped, str(unmapped[:8])))

    # 8. PII sweep of tracked files (scrub guard)
    pii_hits = []
    tracked = [p for p in ROOT.rglob("*")
               if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts
               and "__pycache__" not in p.parts and p.suffix in {".py", ".js", ".html", ".md",
                                                                 ".yaml", ".yml", ".sh", ".env",
                                                                 ".txt", ".json", ".example"}]
    patterns = [
        ("plaintext SSH password", re.compile(r"<REDACTED_PASSWORD>")),
        ("Oracle Cloud IP", re.compile(r"161\.153\.112\.|129\.146\.44\.")),
        ("LAN IP", re.compile(r"10\.1\.1\.\d+")),
        ("scrypt password hash", re.compile(r"scrypt\$")),
        ("full JWT", re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{20,}")),
    ]
    for p in tracked:
        rel = p.relative_to(ROOT).as_posix()
        if rel in PII_EXEMPT:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for label, rx in patterns:
            if rx.search(text):
                pii_hits.append(f"{rel}: {label}")
    checks.append(("PII sweep clean (password/IPs/hashes/JWTs)", not pii_hits, str(pii_hits[:6])))

    # 9. Personal domain only in whitelisted files
    wg_hits = []
    for p in tracked:
        rel = p.relative_to(ROOT).as_posix()
        if rel in PII_EXEMPT or rel in WG_ALLOWED:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if "Gateway" in text:
            wg_hits.append(rel)
    checks.append(("personal domain only in whitelisted files", not wg_hits, str(wg_hits[:6])))

    all_ok = all(ok for _, ok, _ in checks)
    for name, ok, extra in checks:
        print(("PASS" if ok else "FAIL"), "|", name, extra if not ok else "")
    print("===", "ALL WIRING CHECKS PASS" if all_ok else "FAILURES PRESENT")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
