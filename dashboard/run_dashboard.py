#!/usr/bin/env python3
"""
Launcher script for the Hermes Brain Command Deck Dashboard.

Usage:
  python3 run_dashboard.py [--port 8088] [--host 0.0.0.0]

Environment variables:
  DASHBOARD_PORT (default: 8088)
  WS_PORT (default: 8089)
  DASHBOARD_HOST (default: 0.0.0.0)
"""

import os
import sys
import argparse
from pathlib import Path

# The package this launcher imports from is `dashboard.*` -- it lives in the
# PARENT of this file (repo_root/dashboard/), not here. Adding only
# SCRIPTS_DIR was enough when the module was flat; after the backend moved
# into a dashboard/ package it stopped being enough, and the launcher died
# with "No module named 'dashboard'" unless the caller happened to set
# PYTHONPATH or run from the repo root.
#
# REPO_ROOT goes on the path explicitly rather than relying on cwd, so the
# server starts the same way from any directory.
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT))

import dashboard_server

def main():
    parser = argparse.ArgumentParser(description="Launch Hermes Brain Command Deck")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DASHBOARD_PORT", 8088)), help="Dashboard port")
    parser.add_argument("--host", type=str, default=os.environ.get("DASHBOARD_HOST", "0.0.0.0"), help="Host interface")
    args = parser.parse_args()

    dashboard_server.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
