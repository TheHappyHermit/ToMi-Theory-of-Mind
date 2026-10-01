#!/usr/bin/env python3
"""
Daily health check for Hermes Cortex / Hermes Brain.

Runs in no-agent cron (daily health verification).
Exits 0 if verification passes, 1 if it fails.
Cross-platform: Windows, macOS, Linux.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_stack.py"
if not VERIFY_SCRIPT.exists():
    alt = REPO_ROOT / "scripts" / "verify_stack.py"
    if alt.exists():
        VERIFY_SCRIPT = alt

DASHBOARD_PORT = os.environ.get("DASHBOARD_PORT", "8088")
PERSONAL_STATE_API = f"http://127.0.0.1:{DASHBOARD_PORT}/api/health"

def main() -> int:
    print("=== Daily Health Check ===")
    print(f"Time: {datetime.now().isoformat()}")
    ok = True

    # Run verify_stack.py
    if VERIFY_SCRIPT.exists():
        result = subprocess.run(
            [sys.executable, str(VERIFY_SCRIPT)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("[ok] Verification passed")
            print(result.stdout[-500:])  # Last 500 chars of output
        else:
            print("[fail] Verification failed")
            print(result.stdout[-500:])
            ok = False
    else:
        print(f"[skip] verify_stack.py not found at {VERIFY_SCRIPT}")

    # Check Personal State API / Dashboard health
    try:
        import urllib.request
        req = urllib.request.urlopen(PERSONAL_STATE_API, timeout=5)
        if req.status == 200:
            print(f"[ok] Command Deck API healthy ({PERSONAL_STATE_API})")
        else:
            print(f"[warn] Command Deck API: HTTP {req.status}")
    except Exception as e:
        print(f"[skip] Command Deck API offline ({PERSONAL_STATE_API}): {e}")

    print("=== Health check complete ===")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
