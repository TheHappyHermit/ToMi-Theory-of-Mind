#!/usr/bin/env python3
"""Hermes Brain Backup script forwarding to cortex_backup.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cortex_backup import main

if __name__ == "__main__":
    sys.exit(main())
