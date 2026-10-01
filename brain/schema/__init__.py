"""
brain.schema — Database schema initialization for Hermes Brain cognitive cortex.
"""

import os
import sqlite3


def init_cortex_db(db_path: str):
    """Ensure all cognitive tables and indices exist in the specified SQLite database."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain_cortex.sql")
    if os.path.exists(schema_path):
        conn = sqlite3.connect(db_path)
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
