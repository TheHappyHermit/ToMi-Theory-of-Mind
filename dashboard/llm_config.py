#!/usr/bin/env python3
"""
Hermes Brain Command Deck — LLM Model & API Key Configuration

Reads and writes the **main Hermes model selection** so an operator can change the
model and its API key from the dashboard instead of editing `config.yaml` by hand.

Design notes
------------
- **The written file is `~/.hermes/config.yaml`, not this repo.** The dashboard
  configures the *installed Hermes instance*; the repo holds the code that drives
  it. Nothing in the repo is mutated at runtime.
- **The API key is never echoed back.** `get_llm_config()` returns `has_key` and a
  masked hint only. This matches the `n8n`/`ha` config pattern in
  `integrations_backend.py`, and it means a screenshot of the settings page or a
  browser-cached response cannot leak the key.
- **Writes are additive and fail-closed.** The YAML is round-tripped with
  `yaml.safe_load` / `safe_dump`, and a parse failure aborts the write rather than
  clobbering the file. A backup is taken before every write.
- **Keys are never invented.** An empty `api_key` in the payload means "leave the
  existing key alone", so a save that only changes the model cannot blank the key.
- Changing the model here affects the **main agent and every cron job that does not
  pin its own model**. Jobs with an explicit `model:` are unaffected — that is
  intentional and is reported back in the response.
"""

import os
import json
import shutil
import subprocess
import sys
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - fail closed rather than half-work
    yaml = None


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes"


def config_path() -> Path:
    return _hermes_home() / "config.yaml"


def auth_path() -> Path:
    return _hermes_home() / "auth.json"


# Providers offered in the picker. `env_var` is where a key is stored when the
# operator supplies one inline; `base_url` is the default endpoint so a new
# install works with only a key.
KNOWN_PROVIDERS: List[Dict[str, Any]] = [
    {"id": "nous",        "name": "Nous Research",      "base_url": "https://inference-api.nousresearch.com/v1", "env_var": "NOUS_API_KEY"},
    {"id": "openrouter",   "name": "OpenRouter",         "base_url": "https://openrouter.ai/api/v1",              "env_var": "OPENROUTER_API_KEY"},
    {"id": "openai",       "name": "OpenAI",             "base_url": "https://api.openai.com/v1",                  "env_var": "OPENAI_API_KEY"},
    {"id": "anthropic",    "name": "Anthropic",          "base_url": "https://api.anthropic.com/v1",               "env_var": "ANTHROPIC_API_KEY"},
    {"id": "openai_compat", "name": "OpenAI-compatible (local)", "base_url": "",                                  "env_var": ""},
    {"id": "llamacpp",     "name": "llama.cpp (local)",  "base_url": "http://127.0.0.1:8080/v1",                "env_var": ""},
]


def _mask(value: str) -> str:
    """
    Return a non-reversible hint. Never returns enough to reconstruct the key.

    Credentials can be long JWTs, so the mask is capped — a 1,700-character row of
    asterisks is useless in a settings UI and would push the real hint off screen.
    """
    if not value:
        return ""
    n = len(value)
    if n <= 8:
        return "*" * n
    keep = 3 if n <= 24 else 4
    return f"{value[:keep]}{'*' * 8}{value[-4:]}  ({n} chars)"


def _read_config() -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is not installed; refusing to touch config.yaml")
    p = config_path()
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _read_keys() -> Dict[str, str]:
    """
    Collect provider credentials from auth.json and the environment.

    Hermes stores provider credentials under several field names depending on how
    the provider was authorised — `api_key` for plain keys, `access_token` for
    OAuth, and `agent_key` for the Nous agent credential. All three are read, and
    `agent_key` is preferred for `nous` because that is the credential the agent
    path actually uses. Values are never returned to the caller.
    """
    keys: Dict[str, str] = {}
    a = auth_path()
    if a.exists():
        try:
            with open(a, "r", encoding="utf-8") as f:
                data = json.load(f)
            for prov, pdata in (data.get("providers") or {}).items():
                if not isinstance(pdata, dict):
                    continue
                name = str(prov).lower()
                # agent_key is the credential the Nous agent path authenticates with.
                for field in ("agent_key", "api_key", "access_token", "token"):
                    val = pdata.get(field)
                    if val:
                        keys.setdefault(name, val)
                        break
                # An explicit inference_base_url means the key applies to that host.
                ib = pdata.get("inference_base_url")
                if ib:
                    keys.setdefault(f"{name}@{ib.rstrip('/')}", keys.get(name, ""))
        except Exception:
            pass
    for prov in KNOWN_PROVIDERS:
        var = prov.get("env_var")
        if var and os.environ.get(var):
            keys.setdefault(prov["id"], os.environ[var])
    return keys


def _credential_for(base_url: str, provider: str) -> str:
    """
    Pick the credential that actually authenticates this endpoint.

    Prefers a host-specific match (`provider@base_url`) so a provider whose key is
    scoped to one inference host is not confused with a generic provider key.
    """
    keys = _read_keys()
    host_key = f"{str(provider).lower()}@{str(base_url).rstrip('/')}"
    return keys.get(host_key) or keys.get(str(provider).lower()) or ""


def get_llm_config() -> Dict[str, Any]:
    """Current model selection plus provider list. Never returns a raw key."""
    cfg = _read_config()
    model = cfg.get("model") or {}
    if not isinstance(model, dict):
        model = {}
    provider_id = str(model.get("provider") or "")
    keys = _read_keys()
    cred = _credential_for(str(model.get("base_url") or ""), provider_id)

    # Which providers currently hold a key anywhere we can see.
    available = [
        {"id": p["id"], "name": p["name"], "base_url": p["base_url"], "has_key": bool(keys.get(p["id"]))}
        for p in KNOWN_PROVIDERS
    ]

    fallback = cfg.get("fallback_providers")
    return {
        "config_path": str(config_path()),
        "config_exists": config_path().exists(),
        "model": model.get("default"),
        "provider": provider_id,
        "base_url": model.get("base_url"),
        "api_mode": model.get("api_mode"),
        "has_key": bool(cred),
        "key_hint": _mask(cred),
        "providers": available,
        # Surfaced so the UI can warn before a save that orphans cron jobs.
        "fallback_count": len(fallback) if isinstance(fallback, list) else 0,
        "local_models": probe_local_models().get("servers", []),
    }


def probe_local_models() -> Dict[str, Any]:
    """Reuse the dashboard's existing local-inference probe."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from hermes_interface import probe_local_models as _probe  # type: ignore
        result = _probe()
        return result if isinstance(result, dict) else {"servers": []}
    except Exception as e:
        return {"servers": [], "error": str(e)}


def _pinned_cron_jobs() -> List[Dict[str, str]]:
    """Cron jobs with an explicit model. These keep it across a default change."""
    jobs_file = _hermes_home() / "cron" / "jobs.json"
    if not jobs_file.exists():
        return []
    try:
        with open(jobs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = data if isinstance(data, list) else data.get("jobs", data)
        if isinstance(jobs, dict):
            jobs = list(jobs.values())
        out = []
        for j in jobs:
            if isinstance(j, dict) and j.get("model"):
                out.append({"id": j.get("id", ""), "name": j.get("name", ""), "model": j.get("model", "")})
        return out
    except Exception:
        return []


def save_llm_config(
    model: Optional[str],
    provider: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update the main model selection. `api_key=None` or "" leaves the key untouched.

    Returns a status dict. On any failure the file is left exactly as it was.
    """
    if yaml is None:
        return {"status": "error", "message": "PyYAML not installed; config.yaml not modified"}
    p = config_path()
    if not p.exists():
        return {"status": "error", "message": f"config.yaml not found at {p}"}

    try:
        cfg = _read_config()
    except Exception as e:
        return {"status": "error", "message": f"config.yaml is not valid YAML ({e}); not modified"}

    before = ((cfg.get("model") or {}) if isinstance(cfg.get("model"), dict) else {}).get("default")

    # Backup first. Never overwrite a config we cannot restore.
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    try:
        shutil.copy2(p, f"{p}.bak-llmsettings-{stamp}")
    except Exception as e:
        return {"status": "error", "message": f"could not write backup ({e}); config.yaml not modified"}

    model_cfg = cfg.get("model")
    if not isinstance(model_cfg, dict):
        model_cfg = {}
    if model:
        model_cfg["default"] = model
    if provider:
        model_cfg["provider"] = provider
    if base_url is not None:
        model_cfg["base_url"] = base_url
    cfg["model"] = model_cfg

    key_written = False
    if api_key:
        # Store in auth.json (0600) rather than config.yaml, matching how Hermes
        # keeps credentials, so the key never lands in a file people commit.
        a = auth_path()
        try:
            a.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if a.exists():
                with open(a, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            providers = data.get("providers") or {}
            entry = providers.get(provider or "", {})
            if not isinstance(entry, dict):
                entry = {}
            entry["api_key"] = api_key
            providers[provider or ""] = entry
            data["providers"] = providers
            tmp = a.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.chmod(tmp, 0o600)
            os.replace(tmp, a)
            key_written = True
        except Exception as e:
            return {"status": "error", "message": f"api key could not be stored ({e}); config.yaml not modified"}

    tmp = p.with_suffix(".yaml.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, default_flow_style=False)
        # Verify the round-trip before it becomes the live file.
        with open(tmp, "r", encoding="utf-8") as f:
            check = yaml.safe_load(f)
        if not isinstance(check, dict) or "model" not in check:
            raise RuntimeError("round-trip verification failed")
        os.replace(tmp, p)
    except Exception as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        # Restore from the backup so a failed write cannot truncate the config.
        try:
            shutil.copy2(f"{p}.bak-llmsettings-{stamp}", p)
        except Exception:
            pass
        return {"status": "error", "message": f"write failed ({e}); config.yaml restored from backup"}

    after = cfg["model"].get("default")
    return {
        "status": "ok",
        "message": f"model changed: {before} -> {after}" if before != after else "settings saved",
        "model": after,
        "provider": cfg["model"].get("provider"),
        "base_url": cfg["model"].get("base_url"),
        "key_written": key_written,
        "backup": f"{p}.bak-llmsettings-{stamp}",
        "note": "Applies to the main agent and to cron jobs that do not pin a model.",
        "pinned_jobs": _pinned_cron_jobs(),
    }


def test_llm_connection() -> Dict[str, Any]:
    """
    Probe the configured endpoint with a 1-token request.

    Reports whether the endpoint and the key actually work, which is the only way
    to know a save did not just write a broken configuration.
    """
    import requests

    cfg = _read_config()
    model_cfg = cfg.get("model") or {}
    if not isinstance(model_cfg, dict):
        model_cfg = {}
    base = (model_cfg.get("base_url") or "").rstrip("/")
    model = model_cfg.get("default")
    provider = str(model_cfg.get("provider") or "")
    if not base or not model:
        return {"status": "error", "message": "no base_url or model configured"}

    keys = _read_keys()
    key = _credential_for(base, provider)
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            timeout=20,
        )
    except Exception as e:
        return {"status": "error", "message": f"could not reach {base}: {e}"}

    if r.status_code == 200:
        return {"status": "ok", "message": f"{model} responded on {base}"}
    if r.status_code in (401, 403):
        return {"status": "error", "message": f"key rejected by {provider} (HTTP {r.status_code})"}
    if r.status_code == 404:
        return {
            "status": "error",
            "message": f"HTTP 404 — model '{model}' not available on {provider}. "
                       "A retired or renamed model is the usual cause.",
        }
    return {"status": "error", "message": f"HTTP {r.status_code}: {r.text[:200]}"}
