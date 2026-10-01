#!/usr/bin/env python3
"""
dashboard/backend/routes/companions.py — FastAPI routes for Companion Applications
(Jared Rhodes' ai-visualizer and barehands).

Provides:
- Health and status telemetry for visualizer and 3D stage
- Proxy command routing to barehands /cmd (zero CORS issues)
- Visualizer state and face management
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from plugins.adapters.visualizer import VisualizerAdapter
from plugins.adapters.barehands import BarehandsAdapter

router = APIRouter(prefix="/api/companions", tags=["Companions"])

VIS_ADAPTER = VisualizerAdapter()
BH_ADAPTER = BarehandsAdapter()


def _check_port(port: int, timeout: float = 0.5) -> bool:
    """Check if a localhost port is actively listening via HTTP."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # Received HTTP response (even 404/403 means server is up)
    except Exception:
        return False


@router.get("/status")
async def get_companions_status():
    """
    Returns live connectivity and telemetry for both companion applications.
    """
    vis_port = 8790
    bh_port = BH_ADAPTER.get_port() if BH_ADAPTER.is_installed else 8794

    vis_online = _check_port(vis_port)
    bh_online = _check_port(bh_port)

    # Visualizer state
    vis_state = VIS_ADAPTER.get_state() if VIS_ADAPTER.is_installed else "offline"
    vis_face = "board"
    if VIS_ADAPTER.visualizer_dir:
        cfg_file = VIS_ADAPTER.visualizer_dir / "ai-visualizer.json"
        if cfg_file.is_file():
            try:
                vis_face = json.loads(cfg_file.read_text(encoding="utf-8")).get("face", "board")
            except Exception:
                pass

    # Barehands state
    bh_items_count = 0
    bh_scene = None
    if bh_online and BH_ADAPTER.is_installed:
        bh_scene = BH_ADAPTER.get_board_state(timeout=1.0)
        if bh_scene and "items" in bh_scene:
            bh_items_count = len(bh_scene.get("items") or [])

    return {
        "visualizer": {
            "installed": VIS_ADAPTER.is_installed,
            "online": vis_online,
            "port": vis_port,
            "state": vis_state,
            "face": vis_face,
            "dir": str(VIS_ADAPTER.visualizer_dir) if VIS_ADAPTER.visualizer_dir else None
        },
        "barehands": {
            "installed": BH_ADAPTER.is_installed,
            "online": bh_online,
            "port": bh_port,
            "items_count": bh_items_count,
            "scene": bh_scene,
            "dir": str(BH_ADAPTER.barehands_dir) if BH_ADAPTER.barehands_dir else None
        }
    }


@router.post("/barehands/cmd")
async def send_barehands_command(cmd: Dict[str, Any] = Body(...)):
    """
    Proxy command to Barehands /cmd endpoint without CORS issues.
    """
    if not cmd.get("a"):
        raise HTTPException(status_code=400, detail="Command must include 'a' action")

    port = BH_ADAPTER.get_port() if BH_ADAPTER.is_installed else 8794
    code = BH_ADAPTER.send_command(cmd)
    if code in (200, 204):
        return {"status": "ok", "code": code}
    elif code == 400:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Command rejected by Barehands stage (check action or airlock)"})
    else:
        return JSONResponse(status_code=502, content={"status": "error", "message": f"Could not connect to Barehands on port {port}. Is the server running?"})


@router.post("/barehands/present")
async def present_card_on_board(payload: Dict[str, Any] = Body(...)):
    """
    Helper to spotlight a card directly onto the user's 3D stage.
    """
    title = payload.get("title", "Hermes Card")
    body = payload.get("body", "")
    cmd = {
        "a": "present",
        "title": title,
        "body": body
    }
    return await send_barehands_command(cmd)


@router.post("/barehands/clear")
async def clear_board():
    """
    Helper to sweep the 3D board clean.
    """
    return await send_barehands_command({"a": "clear"})


@router.post("/visualizer/state")
async def set_visualizer_state(payload: Dict[str, Any] = Body(...)):
    """
    Directly set visualizer state (idle, listening, thinking, speaking).
    """
    state = payload.get("state", "idle")
    success = VIS_ADAPTER.set_state(state)
    return {"status": "ok" if success else "failed", "state": state}


@router.post("/visualizer/face")
async def set_visualizer_face(payload: Dict[str, Any] = Body(...)):
    """
    Change the active face in ai-visualizer.json (board, radial, rain, neural).
    """
    face = payload.get("face", "board")
    if not VIS_ADAPTER.visualizer_dir:
        raise HTTPException(status_code=404, detail="ai-visualizer directory not found")

    cfg_file = VIS_ADAPTER.visualizer_dir / "ai-visualizer.json"
    cfg = {}
    if cfg_file.is_file():
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    cfg["face"] = face
    try:
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return {"status": "ok", "face": face}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
