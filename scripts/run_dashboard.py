#!/usr/bin/env python3
"""
Launcher script for the Hermes Brain Command Deck Dashboard.

Usage:
  python3 scripts/run_dashboard.py [--port 8088] [--host 0.0.0.0]

Environment variables:
  DASHBOARD_PORT (default: 8088)
  WS_PORT (default: 8089)
  DASHBOARD_HOST (default: 0.0.0.0 -- the Command Deck is meant to be
  reachable from the LAN; the dashboard has no auth layer, so this is a
  deliberate choice, not an oversight)
"""

import os
import sys
import argparse
from pathlib import Path

# Add repo root to path so we can import dashboard.dashboard_server
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import dashboard.dashboard_server as dashboard_server

def main():
    parser = argparse.ArgumentParser(description="Launch Hermes Brain Command Deck")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DASHBOARD_PORT", 8088)), help="Port to bind dashboard (default: 8088)")
    parser.add_argument("--host", type=str, default=os.environ.get("DASHBOARD_HOST", "0.0.0.0"), help="Host interface (default: 0.0.0.0)")
    args = parser.parse_args()

    dashboard_server.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
