#!/usr/bin/env python3
"""
scripts._paths — Canonical Hermes Brain path resolution.

Single source of truth for every script that needs to locate Hermes Brain
state. Resolves, in order:

  1. $HERMES_DATA_DIR       — explicit data root (wins over everything)
  2. $HERMES_HOME           — Agent home, which is also the data root by default
  3. Windows %LOCALAPPDATA%\\hermes
  4. ~/.hermes

Every script in scripts/ should import from here rather than re-deriving the
path. The pre-2026-09-24 scripts each carried their own copy of this logic and
several hardcoded `~/.hermes` via `os.path.expanduser`, which silently ignored
`HERMES_HOME` and broke non-default installs.

All paths are absolute. Callers should not assume the CWD.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

__all__ = [
    "HERMES_HOME",
    "resolve_hermes_home",
    "experience_db_path",
    "organizer_db_path",
    "active_wiki_path",
    "oracle_brain_path",
    "backup_root",
    "exchange_dir",
]


def resolve_hermes_home() -> Path:
    """Return the Hermes Brain data root as an absolute Path."""
    if os.environ.get("HERMES_DATA_DIR"):
        return Path(os.environ["HERMES_DATA_DIR"]).expanduser().resolve()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).expanduser().resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return (Path(os.environ["LOCALAPPDATA"]) / "hermes").resolve()
    return (Path.home() / ".hermes").resolve()


HERMES_HOME = resolve_hermes_home()


def _env_path(name: str, default: Path) -> Path:
    """Prefer an explicit env override, else a path under the data root."""
    val = os.environ.get(name)
    if val:
        return Path(val).expanduser().resolve()
    return default


def experience_db_path() -> Path:
    return _env_path("EXPERIENCE_DB_PATH", HERMES_HOME / "experience.db")


def organizer_db_path() -> Path:
    return _env_path(
        "ORGANIZER_DB_PATH", HERMES_HOME / "personal-organizer" / "data" / "organizer.db"
    )


def active_wiki_path() -> Path:
    return _env_path("ACTIVE_WIKI_PATH", HERMES_HOME / "active-wiki")


def oracle_brain_path() -> Path:
    return _env_path("ORACLE_BRAIN_PATH", HERMES_HOME / "oracle" / "brain")


def backup_root() -> Path:
    return _env_path("BACKUP_ROOT_DIR", HERMES_HOME / "backups")


def exchange_dir() -> Path:
    return _env_path("EXCHANGE_DIR", HERMES_HOME / "exchange" / "research")
