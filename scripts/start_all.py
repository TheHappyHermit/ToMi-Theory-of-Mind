#!/usr/bin/env python3
"""
start_all.py — Unified launcher for Hermes Brain and Companion Applications.

Starts:
1. Hermes Brain Dashboard & API (default port: 8088)
2. Jared Rhodes' ai-visualizer (default port: 8790) if installed
3. Jared Rhodes' barehands 3D stage (default port: 8794) if installed

Handles graceful shutdown of all services on Ctrl+C.
"""

from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import List, Optional

brain_root = Path(__file__).resolve().parent.parent
if str(brain_root) not in sys.path:
    sys.path.insert(0, str(brain_root))

from plugins.adapters.visualizer import VisualizerAdapter
from plugins.adapters.barehands import BarehandsAdapter


def main():
    procs: List[subprocess.Popen] = []
    python_bin = sys.executable

    vis_adapter = VisualizerAdapter()
    bh_adapter = BarehandsAdapter()

    print("=" * 65)
    print(" ⚡ Hermes Brain & Companions Unified Launcher ⚡")
    print("=" * 65)

    # 1. Hermes Brain Dashboard
    if "--no-brain" not in sys.argv:
        print("[Hermes Brain] Starting Dashboard on http://localhost:8088 ...")
        p = subprocess.Popen(
            [python_bin, str(brain_root / "scripts" / "run_dashboard.py")],
            cwd=str(brain_root)
        )
        procs.append(p)

    # 2. AI Visualizer
    if "--no-visualizer" not in sys.argv and vis_adapter.is_installed:
        vis_dir = vis_adapter.visualizer_dir
        print(f"[AI Visualizer] Starting on http://localhost:8790 ({vis_dir}) ...")
        # Ensure config exists
        vis_adapter.ensure_config()
        p = subprocess.Popen(
            [python_bin, "server.py"],
            cwd=str(vis_dir)
        )
        procs.append(p)
    elif vis_adapter.is_installed is False:
        print("[AI Visualizer] Not found (clone to ../ai-visualizer to enable).")

    # 3. Barehands 3D Stage
    if "--no-barehands" not in sys.argv and bh_adapter.is_installed:
        bh_dir = bh_adapter.barehands_dir
        print(f"[Barehands 3D] Starting on http://localhost:8794 ({bh_dir}) ...")
        # Ensure config exists
        bh_adapter.ensure_config()
        p = subprocess.Popen(
            [python_bin, "server.py"],
            cwd=str(bh_dir)
        )
        procs.append(p)
    elif bh_adapter.is_installed is False:
        print("[Barehands 3D] Not found (clone to ../barehands to enable).")

    print("=" * 65)
    print("All requested services started. Press Ctrl+C to stop all.")
    print("=" * 65)

    def shutdown(sig, frame):
        print("\nShutting down all services...")
        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            for proc in procs:
                if proc.poll() is not None:
                    print(f"Process {proc.args} exited with code {proc.returncode}")
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
