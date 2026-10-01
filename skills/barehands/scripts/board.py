#!/usr/bin/env python3
"""
board.py — Cross-platform CLI to send commands to the Barehands 3D stage.
Part of Hermes Brain barehands skill.

Usage:
  python board.py '{"a":"present","title":"HELLO","body":"first card"}'
  python board.py '{"a":"clear"}'
  python board.py '{"a":"explode"}'
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
    # Direct fallback
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
    if len(sys.argv) < 2:
        if not sys.stdin.isatty():
            payload_str = sys.stdin.read().strip()
        else:
            print("usage: board.py <json-command>", file=sys.stderr)
            sys.exit(1)
    else:
        payload_str = sys.argv[1].strip()

    if not payload_str:
        print("usage: board.py <json-command>", file=sys.stderr)
        sys.exit(1)

    try:
        cmd = json.loads(payload_str)
    except Exception as e:
        print(f"Error: Invalid JSON payload: {e}", file=sys.stderr)
        sys.exit(1)

    if ADAPTER:
        code = ADAPTER.send_command(cmd)
        print(code)
        sys.exit(0 if code in (200, 204) else 1)

    port = get_port()
    url = f"http://127.0.0.1:{port}/cmd"
    data = json.dumps(cmd).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(resp.status)
            sys.exit(0 if resp.status in (200, 204) else 1)
    except urllib.error.HTTPError as e:
        print(e.code)
        sys.exit(1)
    except Exception as e:
        print(f"Error connecting to Barehands on port {port}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
