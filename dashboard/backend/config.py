#!/usr/bin/env python3
"""
dashboard.backend.config — Shared configuration, paths, and database connections.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Resolve root directories
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = REPO_ROOT / "dashboard"
def _resolve_hermes_data_dir() -> Path:
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

HERMES_DATA_DIR = _resolve_hermes_data_dir()
HERMES_HOME = HERMES_DATA_DIR

def _resolve_organizer_db() -> Path:
    for env_var in ("ORGANIZER_DB_PATH", "ORGANIZER_DB"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return Path(val).resolve()
    return HERMES_DATA_DIR / "personal-organizer" / "data" / "organizer.db"

ORGANIZER_DB = _resolve_organizer_db()
EXPERIENCE_DB = Path(os.environ.get("EXPERIENCE_DB_PATH", os.environ.get("EXPERIENCE_DB", str(HERMES_DATA_DIR / "experience.db"))))
ACTIVE_WIKI = Path(os.environ.get("ACTIVE_WIKI_PATH", str(HERMES_DATA_DIR / "active-wiki")))
ORACLE_BRAIN = Path(os.environ.get("ORACLE_BRAIN_PATH", str(HERMES_DATA_DIR / "oracle" / "brain")))
BACKUP_ROOT_DIR = Path(os.environ.get("BACKUP_ROOT_DIR", str(HERMES_DATA_DIR / "backups")))
RESEARCH_EXCHANGE = Path(os.environ.get("RESEARCH_EXCHANGE_PATH", str(HERMES_DATA_DIR / "exchange" / "research")))
NOTIFICATIONS_LOG_FILE = Path(os.environ.get("NOTIFICATIONS_LOG_PATH", str(HERMES_DATA_DIR / "exchange" / "notifications_log.json")))
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/config/services.yaml"))

N8N_QUICK_ACTIONS_PRESETS = [
    {"id": "vault_sync", "name": "Sync Obsidian Vault", "description": "Index active wiki notes into pgvector 2000d embeddings", "icon": "📚", "category": "Knowledge", "last_run": "14m ago", "status": "idle"},
    {"id": "market_scrape", "name": "Scrape Watchlist Fundamentals", "description": "Fetch live financial metrics across all 7 provider APIs", "icon": "📈", "category": "Finance", "last_run": "45m ago", "status": "idle"},
    {"id": "deep_research", "name": "Run Frontier Topic Crawl", "description": "Synthesize next queued topic via SearXNG metasearch", "icon": "🔬", "category": "Research", "last_run": "2h ago", "status": "idle"},
    {"id": "memory_defrag", "name": "Consolidate Working Memory", "description": "Prune MEMORY.md and move cold facts to Active Wiki", "icon": "🧹", "category": "Agent", "last_run": "Yesterday", "status": "idle"},
    {"id": "hass_audit", "name": "Home Assistant IoT Audit", "description": "Verify entity reachable states & run security check", "icon": "🏡", "category": "Smart Home", "last_run": "4h ago", "status": "idle"},
    {"id": "postgres_backup", "name": "PostgreSQL Volume Snapshot", "description": "Dump pgvector embeddings & experience.db to backup", "icon": "📦", "category": "Database", "last_run": "1d ago", "status": "idle"}
]

# Import local helper bridges
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(DASHBOARD_DIR))

import calendar_sync
import email_sync
import check_reminders
from notify_dispatcher import dispatcher
import hermes_interface
import integrations_backend

# Initialize HermesBrain cognitive engine
try:
    from brain.hermes_brain import HermesBrain
    BRAIN_DB_PATH = os.environ.get("BRAIN_DB_PATH", str(REPO_ROOT / "brain" / "brain.db"))
    brain_engine = HermesBrain(db_path=BRAIN_DB_PATH)
except Exception as e:
    print(f"[config] Notice: HermesBrain init error: {e}")
    brain_engine = None


def _initialize_demo_databases():
    """Legacy no-op: demo data removed. Real databases only."""
    pass


def get_organizer_conn() -> sqlite3.Connection:
    """Connect to the real organizer database with concurrency protections and self-healing schema."""
    db_path = ORGANIZER_DB
    if not db_path.exists():
        alternatives = [
            HERMES_DATA_DIR / "personal-organizer" / "data" / "organizer.db",
            HERMES_DATA_DIR / "organizer.db",
            Path.home() / ".hermes" / "personal-organizer" / "data" / "organizer.db",
            Path.home() / ".hermes" / "organizer.db",
        ]
        for alt in alternatives:
            if alt.exists():
                db_path = alt
                break
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass

    # Self-healing: verify core tables exist, initialize if missing
    try:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
        if not row:
            import init_db
            init_db.init_database(conn=conn, seed=True)
    except Exception:
        pass

    # Ensure persistent chat_messages table exists
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user', 'bot', 'tool')),
                message TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_bot_session ON chat_messages(bot_id, session_id);")
        conn.commit()
    except Exception:
        pass
    return conn


def get_experience_conn() -> sqlite3.Connection:
    if not EXPERIENCE_DB.exists():
        import init_experience_db
        init_experience_db.init_experience_db()
    conn = sqlite3.connect(str(EXPERIENCE_DB))
    conn.row_factory = sqlite3.Row
    return conn

get_experience_conn = get_experience_conn  # backward-compat alias
