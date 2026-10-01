#!/usr/bin/env python3
"""
scripts/install_skills.py — Legacy compatibility wrapper for install.py.

Delegates directly to the universal cross-platform installer (install.py --link-only).
"""

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def main():
    cmd = [sys.executable, str(REPO_ROOT / "install.py"), "--link-only"] + sys.argv[1:]
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    sys.exit(main())
