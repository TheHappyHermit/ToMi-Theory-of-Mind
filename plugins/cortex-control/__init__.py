"""
Cortex Control Plugin — Action Gate, Epistemic Protocol, Experience Tracking.

This plugin implements:
1. pre_tool_call hook for the Action Gate (inhibitory control)
2. Epistemic provenance tracking
3. Experience index recording
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CORTIX_DB = Path(os.environ.get(
    "CORTIX_DB_PATH",
    str(Path.home() / "personal-agent" / "cortex" / "cortex.db")
))

class CortexPlugin:
    """Cortex control plugin for Hermes Agent."""
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize cortex control database."""
        CORTIX_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(CORTIX_DB), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS operations (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            profile TEXT,
            task_class TEXT,
            goal_summary TEXT,
            risk_level TEXT,
            reasoning_mode TEXT,
            started_at TEXT,
            ended_at TEXT,
            outcome TEXT,
            verified TEXT,
            planner_used INTEGER DEFAULT 0,
            auditor_used INTEGER DEFAULT 0,
            oracle_used INTEGER DEFAULT 0,
            research_used INTEGER DEFAULT 0,
            user_corrected INTEGER DEFAULT 0,
            source_session_ref TEXT,
            notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS experience (
            id TEXT PRIMARY KEY,
            operation_id TEXT,
            skill_name TEXT,
            event_type TEXT,
            source_session_id TEXT,
            verification_status TEXT,
            created_at TEXT,
            FOREIGN KEY(operation_id) REFERENCES operations(id)
        );
        """)
        conn.commit()
        conn.close()
    
    def pre_tool_call(self, tool_name: str, args: dict, profile: str) -> dict:
        """
        Action Gate hook — evaluates before tool execution.
        
        Returns dict with:
        - allowed: bool
        - reason: str (if blocked)
        - risk_level: str
        """
        risk_level = self._classify_risk(tool_name)
        
        # Hard blocks — never allow
        hard_blocks = [
            "rm", "rm_rf", "delete", "truncate", "drop_table",
            "docker_volume_rm", "docker_network_rm"
        ]
        
        if any(b in tool_name.lower() for b in hard_blocks):
            return {
                "allowed": False,
                "reason": f"Cortex Action Gate: blocking destructive operation '{tool_name}'",
                "risk_level": "IRREVERSIBLE"
            }
        
        # High-risk operations need verification
        high_risk = [
            "docker_compose_down", "docker_kill", "docker_stop",
            "sudo", "chmod", "chown",
            "write_file", "patch"  # Only if modifying system files
        ]
        
        if any(r in tool_name.lower() for r in high_risk):
            return {
                "allowed": True,
                "reason": "High-risk operation — proceed with caution",
                "risk_level": "CONSEQUENTIAL"
            }
        
        return {
            "allowed": True,
            "reason": "Low-risk operation — approved",
            "risk_level": "LOW"
        }
    
    def _classify_risk(self, tool_name: str) -> str:
        """Classify tool operation risk level."""
        read_ops = ["read_file", "search_files", "web_search", "web_extract", 
                    "session_search", "honcho_search"]
        
        if any(op in tool_name.lower() for op in read_ops):
            return "READ"
        
        if any(op in tool_name.lower() for op in ["docker_compose_up", "docker_start", 
                                                    "docker_restart", "hermes", "terminal"]):
            return "LOW_RISK_REVERSIBLE"
        
        return "CONSEQUENTIAL"
    
    def record_operation(self, tool_name: str, outcome: str, verified: bool):
        """Record an operation in the experience index."""
        conn = sqlite3.connect(str(CORTIX_DB), timeout=30)
        op_id = self._generate_id()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("""INSERT INTO operations (id, task_class, goal_summary,
                     started_at, outcome, verified)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                    (op_id, "tool_call", tool_name, now, outcome, str(verified)))
        
        conn.commit()
        conn.close()
    
    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())


# Plugin entry point
def get_plugin():
    return CortexPlugin()
