#!/usr/bin/env python3
"""
hermes-visualizer-sync — State Synchronization Hook for Hermes Visualizer & Barehands.

Hooks into Hermes Agent lifecycle events to broadcast live agent states:
- agent:start  -> "thinking"
- agent:step   -> "thinking"
- agent:end    -> "speaking" (if output) or "idle"
- session:reset -> "idle"

Uses Hermes Brain Adapters to drive:
1. ai-visualizer signal bus (.voice_state)
2. barehands stage ring (state/state)
3. HTTP fallback endpoints
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict

# Attempt to import Brain plugin adapters
brain_root = Path(__file__).resolve().parent.parent.parent
if str(brain_root) not in sys.path:
    sys.path.insert(0, str(brain_root))

try:
    from plugins.adapters.visualizer import VisualizerAdapter
    from plugins.adapters.barehands import BarehandsAdapter
    VIS_ADAPTER = VisualizerAdapter()
    BH_ADAPTER = BarehandsAdapter()
except ImportError:
    VIS_ADAPTER = None
    BH_ADAPTER = None

VISUALIZER_URL = os.environ.get("HERMES_VISUALIZER_URL", "http://127.0.0.1:8790")
BAREHANDS_URL = os.environ.get("HERMES_BAREHANDS_URL", "http://127.0.0.1:8794")


def _send_post(url: str, payload: Dict[str, Any], timeout: float = 0.5) -> None:
    """Send fire-and-forget HTTP POST."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except Exception:
        pass


def broadcast_state(state: str) -> None:
    """Broadcast agent state (idle, listening, thinking, speaking) across all adapters."""
    # 1. Update ai-visualizer via adapter
    if VIS_ADAPTER:
        VIS_ADAPTER.set_state(state)
    else:
        # Direct fallback for standard locations
        for p in [Path.home() / "ai-visualizer", Path.home() / ".hermes" / "ai-visualizer"]:
            bus_file = p / ".voice_state"
            if p.is_dir():
                try:
                    bus_file.write_text(state, encoding="utf-8")
                except Exception:
                    pass

    # 2. Update barehands ring via adapter
    if BH_ADAPTER:
        BH_ADAPTER.set_ring_state(state)
    else:
        for p in [Path.home() / "barehands", Path.home() / ".hermes" / "barehands"]:
            ring_file = p / "state" / "state"
            if p.is_dir():
                try:
                    ring_file.parent.mkdir(parents=True, exist_ok=True)
                    ring_file.write_text(state, encoding="utf-8")
                except Exception:
                    pass

    # 3. Optional HTTP post fallback if custom server is running
    _send_post(f"{VISUALIZER_URL}/state", {"state": state})


def handle(event_type: str, context: Dict[str, Any]) -> None:
    """
    Called by Hermes Agent runtime on agent events.
    """
    if event_type in ("agent:start", "agent:step"):
        broadcast_state("thinking")
    elif event_type == "agent:end":
        response = context.get("response") or ""
        if response:
            broadcast_state("speaking")
        else:
            broadcast_state("idle")
    elif event_type == "session:reset":
        broadcast_state("idle")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        broadcast_state(sys.argv[1])
        print(f"Broadcasted state: {sys.argv[1]}")
    else:
        print("Usage: python handler.py <idle|listening|thinking|speaking>")
