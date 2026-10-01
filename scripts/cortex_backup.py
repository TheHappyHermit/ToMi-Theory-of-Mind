#!/usr/bin/env python3
"""
Daily backup for Hermes Cortex / Hermes Brain.

Runs in no-agent cron (daily scheduled backup).
Exits 0 always — never breaks the cron chain.
Cross-platform: Windows, macOS, Linux (uses pure-Python tarfile with system tar acceleration).
"""

import sys
import os
import tarfile
import shutil
from pathlib import Path
from datetime import datetime

# ── Resolve base paths ──────────────────────────────────────────────────
def resolve_hermes_data_dir() -> Path:
    for env_var in ("HERMES_DATA_DIR", "HERMES_HOME", "CORTEX_HOME", "HERMES_HOME"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return Path(val).resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win_hermes.exists():
            return win_hermes
    default_hermes = Path.home() / ".hermes"
    if default_hermes.exists():
        return default_hermes
    legacy_hermes = Path.home() / ".hermes"
    if legacy_hermes.exists():
        return legacy_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return default_hermes

HERMES_DATA_DIR = resolve_hermes_data_dir()

def resolve_backup_dir() -> Path:
    env_backup = os.environ.get("BACKUP_ROOT_DIR", "").strip()
    if env_backup:
        return Path(env_backup).resolve()
    return HERMES_DATA_DIR / "backups"

BACKUP_DIR = resolve_backup_dir()
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Directories/files to back up (cross-platform paths)
def get_backup_targets() -> list[Path]:
    candidates = [
        HERMES_DATA_DIR / "personal-organizer",
        HERMES_DATA_DIR / "active-wiki",
        HERMES_DATA_DIR / "oracle",
        HERMES_DATA_DIR / "config.yaml",
        HERMES_DATA_DIR / "config",
        Path.home() / ".hermes" / "config.yaml",
        Path.home() / ".hermes" / "config",
    ]
    env_db = os.environ.get("ORGANIZER_DB_PATH", "").strip()
    if env_db:
        candidates.append(Path(env_db).resolve())

    # De-duplicate while preserving existing targets
    existing = []
    seen = set()
    for c in candidates:
        if c.exists() and str(c) not in seen:
            seen.add(str(c))
            existing.append(c)
    return existing

EXCLUDES = {
    ".pyc",
    "__pycache__",
    ".git",
    "state.db",
    "cache",
    ".db-wal",
    ".db-shm",
    ".log",
}

def _filter_tar(tarinfo: tarfile.TarInfo):
    name = tarinfo.name
    for exc in EXCLUDES:
        if exc in name:
            return None
    return tarinfo

def main() -> int:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    archive = BACKUP_DIR / f"hermes-cortex-{TIMESTAMP}.tar.gz"

    print(f"Starting backup at {datetime.now().isoformat()}")
    targets = get_backup_targets()

    if not targets:
        print(f"[notice] No targets found in {HERMES_DATA_DIR}. Creating placeholder backup.")
        archive_touch = BACKUP_DIR / f"hermes-cortex-{TIMESTAMP}.empty"
        archive_touch.write_text("hermes-cortex empty placeholder\n", encoding="utf-8")
        return 0

    try:
        with tarfile.open(archive, "w:gz") as tar:
            for t in targets:
                arcname = t.name
                if t.is_dir():
                    tar.add(t, arcname=arcname, filter=_filter_tar)
                else:
                    tar.add(t, arcname=arcname)
        print(f"Backup completed successfully: {archive}")
    except Exception as e:
        print(f"[warn] Backup creation error: {e}")

    # Clean up old backups — keep last 7
    try:
        archives = sorted(
            BACKUP_DIR.glob("hermes-cortex-*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for old in archives[7:]:
            old.unlink()
            print(f"[cleanup] Removed old backup: {old.name}")
    except Exception as e:
        print(f"[warn] Cleanup error: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
