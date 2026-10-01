#!/usr/bin/env python3
"""
model_roles.py — resolve per-role model configuration.

Roles (Newsletter, Research, Oracle, Embedding) can each use either:
  - "default": the Hermes main model (read from ~/.hermes/config.yaml — no duplication)
  - "custom":  a dedicated provider/base_url/api_key/model set via the dashboard
               Settings page, stored as MODEL_ROLE_<ROLE>_* in .env

Scripts call resolve_model_role("newsletter") and get a ready-to-use config.
The dashboard imports the same resolver so the Settings page shows the truth.
"""

import os
from pathlib import Path

ROLES = ("newsletter", "research", "oracle", "embedding")

_ROLE_ENV_TEMPLATE = {
    "provider":  "MODEL_ROLE_{R}_PROVIDER",
    "base_url":  "MODEL_ROLE_{R}_BASE_URL",
    "api_key":   "MODEL_ROLE_{R}_API_KEY",
    "model":     "MODEL_ROLE_{R}_MODEL",
}


def _hermes_default_model() -> dict:
    """Read the main default model + provider from Hermes config.yaml."""
    cfg = Path.home() / ".hermes" / "config.yaml"
    try:
        import yaml
        with open(cfg) as f:
            c = yaml.safe_load(f) or {}
        m = c.get("model", {}) or {}
        return {
            "provider": m.get("provider", ""),
            "model": m.get("default", ""),
            "base_url": m.get("base_url", ""),
            "api_key": "",  # Hermes holds its own keys — never duplicate them here
            "source": "hermes-default",
        }
    except Exception:
        return {"provider": "", "model": "", "base_url": "", "api_key": "", "source": "hermes-default"}


def resolve_model_role(role: str) -> dict:
    """Return the effective model config for a role.

    Falls back to the Hermes main model whenever the role's custom fields
    are unset (or only partially set — model name is the trigger field).
    """
    role = (role or "").strip().lower()
    if role not in ROLES:
        raise ValueError(f"unknown model role: {role!r} (expected one of {ROLES})")

    custom = {k: os.environ.get(t.format(R=role.upper()), "").strip()
              for k, t in _ROLE_ENV_TEMPLATE.items()}

    if custom.get("model"):  # a custom model name is the minimum viable override
        custom["source"] = "custom"
        return custom

    return _hermes_default_model()


def role_env_var_names(role: str) -> dict:
    """The .env variable names for a role (used by the dashboard settings writer)."""
    role = (role or "").strip().lower()
    return {k: t.format(R=role.upper()) for k, t in _ROLE_ENV_TEMPLATE.items()}


if __name__ == "__main__":
    import json
    print(json.dumps({r: resolve_model_role(r) for r in ROLES}, indent=2))
