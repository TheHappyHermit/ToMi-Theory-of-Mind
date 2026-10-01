#!/usr/bin/env python3
"""
scripts/decision_synthesis.py — Cron runner wrapper for decision synthesis.

Allows Hermes Agent's cron daemon to run decision synthesis while satisfying
the sandbox containment rule (requiring executed scripts to reside in $HERMES_HOME/scripts/).
"""

import os
import sys
from pathlib import Path

# Add repo root and plugins directory to sys.path to find plugins.decision_logger
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent

# Check potential locations for plugins:
# 1. Brain repository root
# 2. $HERMES_HOME / $HERMES_DATA_DIR parent
candidate_roots = [
    REPO_ROOT,
    CURRENT_DIR,
    Path(os.environ.get("HERMES_HOME", "")) if os.environ.get("HERMES_HOME") else None,
    Path(os.environ.get("HERMES_DATA_DIR", "")) if os.environ.get("HERMES_DATA_DIR") else None,
    Path.home() / ".hermes",
]
if os.environ.get("LOCALAPPDATA"):
    candidate_roots.append(Path(os.environ["LOCALAPPDATA"]) / "hermes")

for root in candidate_roots:
    if root and root.exists():
        if (root / "plugins").exists() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
        if (root / "plugins" / "decision_logger").exists() and str(root / "plugins" / "decision_logger") not in sys.path:
            sys.path.insert(0, str(root / "plugins" / "decision_logger"))

try:
    from plugins.decision_logger.synthesis import main as synthesis_main
except ImportError:
    try:
        from synthesis import main as synthesis_main
    except ImportError as e:
        print(f"[decision_synthesis] Error: Could not import decision synthesis module: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(synthesis_main())
