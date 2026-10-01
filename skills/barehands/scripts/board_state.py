#!/usr/bin/env python3
"""
board_state.py — Cross-platform CLI to inspect the Barehands 3D stage.
Part of Hermes Brain barehands skill.

Usage:
  python board_state.py
  python board_state.py --json
"""

import sys
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

# Add Brain root to path if needed to import plugin adapters
brain_root = Path(__file__).resolve().parent.parent.parent.parent
if str(brain_root) not in sys.path:
    sys.path.insert(0, str(brain_root))

try:
    from plugins.adapters.barehands import BarehandsAdapter
    ADAPTER = BarehandsAdapter()
except ImportError:
    ADAPTER = None


def get_port():
    if ADAPTER:
        return ADAPTER.get_port()
    candidates = [
        Path.home() / "barehands" / "barehands.json",
        Path.home() / ".hermes" / "barehands" / "barehands.json",
    ]
    for c in candidates:
        if c.is_file():
            try:
                return json.loads(c.read_text(encoding="utf-8")).get("port", 8794)
            except Exception:
                pass
    return 8794


def main():
    raw_json = "--json" in sys.argv

    if ADAPTER:
        data = ADAPTER.get_board_state()
        if raw_json:
            print(json.dumps(data or {}, indent=2))
        else:
            print(ADAPTER.format_board_state(data))
        sys.exit(0)

    port = get_port()
    url = f"http://127.0.0.1:{port}/state"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            content = resp.read().decode("utf-8")
            data = json.loads(content)
    except Exception:
        print("The board is dark — the barehands server isn't running.", file=sys.stderr)
        sys.exit(1)

    if raw_json:
        print(json.dumps(data, indent=2))
    else:
        items = data.get("items") or []
        if not items:
            print("The board is EMPTY (as of the tracker's last heartbeat).")
        else:
            print(f"ON THE BOARD — {len(items)} item(s), last tracker heartbeat:")
            for i in items:
                print(f"  - {i.get('type', '?')} {i.get('title') or i.get('src') or ''}")


if __name__ == "__main__":
    main()
