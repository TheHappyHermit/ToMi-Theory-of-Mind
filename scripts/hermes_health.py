#!/usr/bin/env python3
"""Hermes Brain Health script forwarding to cortex_health.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cortex_health import main

if __name__ == "__main__":
    sys.exit(main())
