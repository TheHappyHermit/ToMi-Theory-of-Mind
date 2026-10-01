#!/usr/bin/env python3
"""
BarehandsAdapter — Bridge between Hermes Agent/Brain and barehands.

Works with Jared Rhodes' upstream barehands repository without modifying any
of its code files. Interfaces through:
1. File bus: writes to state/state (idle | listening | thinking | speaking)
2. Native HTTP POST: sends commands to http://127.0.0.1:8794/cmd
3. Native HTTP GET: reads scene state from http://127.0.0.1:8794/state
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_STATES = {"idle", "listening", "thinking", "speaking"}


class BarehandsAdapter:
    """Non-invasive adapter for barehands."""

    def __init__(self, barehands_dir: Optional[Path | str] = None) -> None:
        self.barehands_dir = self._resolve_dir(barehands_dir)

    @staticmethod
    def _resolve_dir(explicit_dir: Optional[Path | str] = None) -> Optional[Path]:
        """Find the barehands directory using environment variables and standard paths."""
        candidates = []
        if explicit_dir:
            candidates.append(Path(explicit_dir))
        if "BAREHANDS_DIR" in os.environ:
            candidates.append(Path(os.environ["BAREHANDS_DIR"]))

        brain_root = Path(__file__).resolve().parent.parent.parent  # plugins/adapters/ -> repo root
        candidates.extend([
            brain_root.parent / "barehands",
            Path.home() / "barehands",
            Path.home() / ".hermes" / "barehands",
        ])

        for c in candidates:
            try:
                resolved = c.expanduser().resolve()
                if resolved.is_dir() and (resolved / "server.py").is_file():
                    return resolved
            except Exception:
                continue
        return None

    @property
    def is_installed(self) -> bool:
        """Check if barehands was discovered."""
        return self.barehands_dir is not None and (self.barehands_dir / "server.py").is_file()

    def get_port(self) -> int:
        """Retrieve port from barehands.json or default to 8794."""
        if self.barehands_dir:
            cfg_file = self.barehands_dir / "barehands.json"
            if cfg_file.is_file():
                try:
                    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                    return int(cfg.get("port", 8794))
                except Exception:
                    pass
        return 8794

    def set_ring_state(self, state: str) -> bool:
        """
        Write state directly to barehands/state/state.
        Drives the assistant ring on the 3D stage.
        """
        state = state.strip().lower()
        if state not in VALID_STATES:
            state = "idle"

        if not self.barehands_dir:
            return False

        target = self.barehands_dir / "state" / "state"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(state, encoding="utf-8")
            return True
        except Exception:
            return False

    def send_command(self, cmd: Dict[str, Any], timeout: float = 3.0) -> int:
        """
        Send a JSON command to the Barehands server's native /cmd endpoint.
        Returns HTTP status code (204 on success, 400 on reject, 0 on failure).
        """
        port = self.get_port()
        url = f"http://127.0.0.1:{port}/cmd"
        data = json.dumps(cmd).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return 0

    def get_board_state(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """Fetch current 3D stage scene state from native /state endpoint."""
        port = self.get_port()
        url = f"http://127.0.0.1:{port}/state"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def format_board_state(d: Optional[Dict[str, Any]]) -> str:
        """Render board state in human and LLM-readable format."""
        if d is None:
            return "The board is dark — the barehands server isn't running."
        items = d.get("items") or []
        if not items:
            return "The board is EMPTY (as of the tracker's last heartbeat)."

        def zone(x, y):
            h = "left" if x < 0.33 else ("center" if x < 0.67 else "right")
            v = "top" if y < 0.33 else ("middle" if y < 0.67 else "bottom")
            return "center" if (h == "center" and v == "middle") else f"{v}-{h}"

        lines = [f"ON THE BOARD — {len(items)} item(s), last tracker heartbeat:"]
        for i in items:
            t = i.get("type", "?")
            title = i.get("title") or ""
            src = os.path.basename(i.get("src") or "")
            if t == "card":
                body = (i.get("body") or "").replace("\n", " ")[:70]
                desc = f'card "{title}"' + (f" — {body}" if body else "")
            elif t == "img":
                desc = f"image {src}" + (" (fx, frameless)" if i.get("fxf") else "") \
                       + (" (video)" if i.get("vd") else "")
            elif t == "model":
                mode = "hologram wireframe" if i.get("mm") == "holo" else "solid"
                desc = f"3D model {src} ({mode})"
                ex = i.get("ex") or 0
                if ex > 0.02:
                    desc += f", EXPLODED {round(ex * 100)}%"
            elif t == "panel":
                desc = f'open note "{title}"'
            elif t == "browser":
                desc = f'file browser "{title}"'
            elif t == "widget":
                desc = "the assistant ring"
            elif t == "orb":
                desc = f'orb "{title}"'
            else:
                desc = f'{t} "{title or src}"'

            flags = []
            if i.get("g"):
                flags.append("IN THE USER'S HAND")
            sc = i.get("scale") or 1
            if sc >= 1.6:
                flags.append("blown up large")
            elif sc <= 0.55:
                flags.append("shrunk small")
            op = i.get("op", 1)
            if op is not None and op < 0.5:
                flags.append("faded out")

            pos = zone(i.get("x") or 0.5, i.get("y") or 0.5)
            line = f"  - {desc} @ {pos}"
            if flags:
                line += "  [" + ", ".join(flags) + "]"
            lines.append(line)
        return "\n".join(lines)

    def ensure_config(
        self,
        name: str = "HERMES",
        port: int = 8794,
        orbs: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Create or update barehands.json in the barehands directory.
        barehands.json is gitignored upstream, leaving git status clean.
        """
        if not self.barehands_dir:
            return False

        cfg_file = self.barehands_dir / "barehands.json"
        cfg_data = {
            "name": name,
            "port": port,
            "orbs": orbs or [
                {"title": "Props", "path": "media", "kind": "media"}
            ]
        }
        try:
            cfg_file.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False


def main():
    adapter = BarehandsAdapter()
    if len(sys.argv) < 2:
        print("Usage: python -m adapters.barehands [send <json> | state | set-ring <state> | setup | status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "send" and len(sys.argv) >= 3:
        try:
            payload = json.loads(sys.argv[2])
            code = adapter.send_command(payload)
            print(code)
            sys.exit(0 if code in (200, 204) else 1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif cmd == "state":
        state_data = adapter.get_board_state()
        if "--json" in sys.argv:
            print(json.dumps(state_data or {}, indent=2))
        else:
            print(adapter.format_board_state(state_data))
    elif cmd == "set-ring" and len(sys.argv) >= 3:
        success = adapter.set_ring_state(sys.argv[2])
        print("OK" if success else "FAILED")
    elif cmd == "status":
        print(f"Installed: {adapter.is_installed}")
        print(f"Directory: {adapter.barehands_dir}")
        print(f"Port:      {adapter.get_port()}")
    elif cmd == "setup":
        if not adapter.barehands_dir:
            print("Error: barehands folder not found.")
            sys.exit(1)
        adapter.ensure_config()
        print(f"Created/Updated {adapter.barehands_dir / 'barehands.json'}")


if __name__ == "__main__":
    main()
