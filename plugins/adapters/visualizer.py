#!/usr/bin/env python3
"""
VisualizerAdapter — Bridge between Hermes Agent/Brain and ai-visualizer.

Works with Jared Rhodes' upstream ai-visualizer repository without modifying any
of its code files. Interfaces through the native file-based signal bus:
- .voice_state: idle | listening | thinking | speaking
- .voice_waveform: JSON {ts, samples: [64 floats]}
"""

from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Optional, Sequence

VALID_STATES = {"idle", "listening", "thinking", "speaking"}


class VisualizerAdapter:
    """Non-invasive adapter for ai-visualizer."""

    def __init__(self, visualizer_dir: Optional[Path | str] = None) -> None:
        self.visualizer_dir = self._resolve_dir(visualizer_dir)

    @staticmethod
    def _resolve_dir(explicit_dir: Optional[Path | str] = None) -> Optional[Path]:
        """Find the ai-visualizer directory using environment variables and standard paths."""
        candidates = []
        if explicit_dir:
            candidates.append(Path(explicit_dir))
        if "AI_VISUALIZER_DIR" in os.environ:
            candidates.append(Path(os.environ["AI_VISUALIZER_DIR"]))

        # Sibling directories
        brain_root = Path(__file__).resolve().parent.parent.parent  # plugins/adapters/ -> repo root
        candidates.extend([
            brain_root.parent / "ai-visualizer",
            Path.home() / "ai-visualizer",
            Path.home() / ".hermes" / "ai-visualizer",
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
        """Check if ai-visualizer was discovered."""
        return self.visualizer_dir is not None and (self.visualizer_dir / "server.py").is_file()

    def get_bus_dir(self) -> Path:
        """Return the directory where the .voice_* signal files live."""
        if self.visualizer_dir:
            # Check if ai-visualizer.json defines a custom bus_dir
            cfg_file = self.visualizer_dir / "ai-visualizer.json"
            if cfg_file.is_file():
                try:
                    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                    if cfg.get("bus_dir"):
                        return Path(cfg["bus_dir"]).expanduser().resolve()
                except Exception:
                    pass
            return self.visualizer_dir
        # Fallback to hermes voice bus
        fallback = Path.home() / ".hermes" / "voice_bus"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    def set_state(self, state: str) -> bool:
        """
        Write state directly to the .voice_state signal file.
        States: 'idle', 'listening', 'thinking', 'speaking'
        """
        state = state.strip().lower()
        if state not in VALID_STATES:
            state = "idle"

        bus_dir = self.get_bus_dir()
        target = bus_dir / ".voice_state"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(state, encoding="utf-8")
            return True
        except Exception:
            return False

    def get_state(self) -> str:
        """Read the current state from the signal bus."""
        bus_dir = self.get_bus_dir()
        target = bus_dir / ".voice_state"
        try:
            val = target.read_text(encoding="utf-8").strip().lower()
            return val if val in VALID_STATES else "idle"
        except Exception:
            return "idle"

    def set_waveform(self, samples: Sequence[float]) -> bool:
        """Write waveform sample buffer to .voice_waveform."""
        bus_dir = self.get_bus_dir()
        target = bus_dir / ".voice_waveform"
        payload = {
            "ts": time.time(),
            "samples": [float(s) for s in samples[:64]]
        }
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload), encoding="utf-8")
            return True
        except Exception:
            return False

    def ensure_config(
        self,
        name: str = "HERMES",
        face: str = "board",
        badge: str = "BRAIN",
        port: int = 8790,
        thinking_sound: bool = True
    ) -> bool:
        """
        Create or update ai-visualizer.json in the visualizer directory.
        ai-visualizer.json is gitignored upstream, leaving git status clean.
        """
        if not self.visualizer_dir:
            return False

        cfg_file = self.visualizer_dir / "ai-visualizer.json"
        cfg_data = {
            "name": name,
            "face": face,
            "badge": badge,
            "port": port,
            "thinking_sound": thinking_sound,
            "bus_dir": ""
        }
        try:
            cfg_file.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False


def main():
    adapter = VisualizerAdapter()
    if len(sys.argv) < 2:
        print("Usage: python -m adapters.visualizer [set-state <state> | get-state | setup | status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "set-state" and len(sys.argv) >= 3:
        success = adapter.set_state(sys.argv[2])
        print("OK" if success else "FAILED")
    elif cmd == "get-state":
        print(adapter.get_state())
    elif cmd == "status":
        print(f"Installed: {adapter.is_installed}")
        print(f"Directory: {adapter.visualizer_dir}")
        print(f"Bus Dir:   {adapter.get_bus_dir()}")
        print(f"State:     {adapter.get_state()}")
    elif cmd == "setup":
        if not adapter.visualizer_dir:
            print("Error: ai-visualizer folder not found.")
            sys.exit(1)
        adapter.ensure_config()
        print(f"Created/Updated {adapter.visualizer_dir / 'ai-visualizer.json'}")


if __name__ == "__main__":
    main()
