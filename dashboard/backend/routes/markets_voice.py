#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, Query, Body, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import os
import sys
import json
import sqlite3
import subprocess
import shutil
import time
import re
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

from dashboard.backend.config import (
    REPO_ROOT, DASHBOARD_DIR, HERMES_HOME, ORGANIZER_DB, EXPERIENCE_DB,
    ACTIVE_WIKI, ORACLE_BRAIN, DOCKER_SOCKET, CONFIG_PATH,
    calendar_sync, email_sync, check_reminders, dispatcher,
    hermes_interface, integrations_backend,
    get_organizer_conn, get_experience_conn
)

# Cache for /api/markets/ribbon. Module-level because the route reads it
# before and after the fetch; a local would reset on every request and turn
# the 60s TTL below into a no-op.
#
# This was used by get_market_ticker_ribbon() but never defined anywhere in
# this file or the older copy, so the endpoint raised NameError -> HTTP 500
# on every call since it was written.
_RIBBON_CACHE = {"data": None, "timestamp": 0}

router = APIRouter()


@router.post("/api/voice/stt")
async def voice_stt(request: Request):
    """
    Speech-to-Text proxy: Accepts recorded audio blob, sends to configured
    OpenAI-compatible voice gateway (/v1/audio/transcriptions) or Whisper endpoint.
    Supports both raw audio body and multipart/form-data.
    """
    raw_settings = integrations_backend.get_system_settings_raw()
    gateway_url = (raw_settings.get("stt_base_url") or raw_settings.get("voice_gateway_url") or "http://localhost:8000").rstrip("/")
    gateway_port = str(raw_settings.get("voice_gateway_port", "")).strip()
    api_key = raw_settings.get("stt_api_key") or raw_settings.get("voice_api_key", "")
    model = raw_settings.get("stt_model") or raw_settings.get("voice_model", "whisper-1")

    if gateway_port and not re.search(r":\d+$", gateway_url):
        base_endpoint = f"{gateway_url}:{gateway_port}"
    else:
        base_endpoint = gateway_url
    target_endpoint = f"{base_endpoint}/v1/audio/transcriptions"

    try:
        content_type = request.headers.get("content-type", "audio/webm")
        if content_type.startswith("multipart/form-data"):
            try:
                form = await request.form()
                uploaded = form.get("file")
                if uploaded and hasattr(uploaded, "read"):
                    audio_bytes = await uploaded.read()
                    audio_type = uploaded.content_type or "audio/webm"
                else:
                    audio_bytes = await request.body()
                    audio_type = "audio/webm"
            except Exception:
                audio_bytes = await request.body()
                audio_type = "audio/webm"
        else:
            audio_bytes = await request.body()
            audio_type = content_type or "audio/webm"

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        files = {
            "file": ("recording.webm", audio_bytes, audio_type)
        }
        data = {
            "model": model,
            "response_format": "json"
        }

        resp = requests.post(target_endpoint, files=files, data=data, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            res_json = resp.json()
            return {"status": "ok", "text": res_json.get("text", "")}
        else:
            return JSONResponse(status_code=resp.status_code, content={"status": "error", "message": f"STT Gateway HTTP {resp.status_code}: {resp.text[:200]}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"STT Connection Failed: {str(e)}", "target": target_endpoint})



@router.post("/api/voice/tts")
async def voice_tts(payload: Dict[str, Any] = Body(...)):
    """
    Text-to-Speech proxy: Accepts text, forwards to configured
    Edge TTS (built-in free neural voice), ElevenLabs, or OpenAI-compatible speech gateway.
    """
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    raw_settings = integrations_backend.get_system_settings_raw()
    provider = raw_settings.get("tts_provider") or raw_settings.get("voice_provider", "edge")
    gateway_url = (raw_settings.get("tts_base_url") or raw_settings.get("voice_gateway_url") or "http://localhost:8000").rstrip("/")
    gateway_port = str(raw_settings.get("voice_gateway_port", "")).strip()
    api_key = raw_settings.get("tts_api_key") or raw_settings.get("voice_api_key", "")
    model = payload.get("model") or raw_settings.get("tts_model") or raw_settings.get("voice_model", "tts-1")
    voice = payload.get("voice") or raw_settings.get("tts_voice") or raw_settings.get("voice_tts_voice", "en-US-AriaNeural")

    # 1. Free built-in Edge TTS (zero API key needed)
    if provider == "edge":
        try:
            import edge_tts
            from fastapi.responses import Response
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return Response(content=audio_data, media_type="audio/mpeg")
        except Exception as e:
            print(f"[voice_tts] Edge TTS notice: {e}, falling back to gateway if available")

    # 2. ElevenLabs Neural Voice
    if provider == "elevenlabs" or (not gateway_url and raw_settings.get("elevenlabs_api_key")):
        el_key = api_key or raw_settings.get("elevenlabs_api_key")
        voice_id = payload.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        el_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        try:
            r = requests.post(
                el_url,
                json={"text": text, "model_id": "eleven_multilingual_v2"},
                headers={"xi-api-key": el_key, "Content-Type": "application/json"},
                timeout=25.0
            )
            if r.status_code == 200:
                from fastapi.responses import Response
                return Response(content=r.content, media_type="audio/mpeg")
            else:
                return JSONResponse(status_code=r.status_code, content={"status": "error", "message": f"ElevenLabs error: {r.text[:200]}"})
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    # 3. OpenAI-compatible local/remote server gateway
    if gateway_port and not re.search(r":\d+$", gateway_url):
        base_endpoint = f"{gateway_url}:{gateway_port}"
    else:
        base_endpoint = gateway_url
    target_endpoint = f"{base_endpoint}/v1/audio/speech"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    tts_payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "mp3"
    }

    try:
        r = requests.post(target_endpoint, json=tts_payload, headers=headers, timeout=30.0)
        if r.status_code == 200:
            from fastapi.responses import Response
            return Response(content=r.content, media_type="audio/mpeg")
        else:
            return JSONResponse(status_code=r.status_code, content={"status": "error", "message": f"Voice Gateway HTTP {r.status_code}: {r.text[:200]}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Voice Gateway Connection Failed: {str(e)}", "target": target_endpoint})



@router.get("/api/tts/voices")
def tts_voices():
    return integrations_backend.get_tts_voices()


@router.post("/api/tts/generate")
def tts_generate(payload: Dict[str, Any] = Body(...)):
    text = payload.get("text", "")
    voice_id = payload.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    return integrations_backend.generate_tts_speech(text, voice_id)


# ── Static File Serving ────────────────────────────────────────────────────────

DASHBOARD_DIR = Path(__file__).resolve().parent


@router.get("/api/markets/quotes")
def markets_quotes():
    return integrations_backend.get_market_quotes()


@router.get("/api/markets/watchlist")
def markets_watchlist():
    return integrations_backend.get_user_watchlist()


@router.post("/api/markets/watchlist/follow")
def markets_follow(payload: Dict[str, Any] = Body(...)):
    ticker = payload.get("ticker", "")
    name = payload.get("name", "")
    asset_type = payload.get("type", "equity")
    return integrations_backend.follow_ticker(ticker, name, asset_type)


@router.post("/api/markets/watchlist/unfollow")
def markets_unfollow(payload: Dict[str, Any] = Body(...)):
    ticker = payload.get("ticker", "")
    return integrations_backend.unfollow_ticker(ticker)


@router.get("/api/markets/search")
def markets_search(q: str = Query("", min_length=1)):
    return integrations_backend.search_market_assets(q)


@router.get("/api/markets/detail")
def markets_detail(ticker: str = Query("^GSPC")):
    return integrations_backend.get_market_detail(ticker)


@router.get("/api/markets/chart")
def markets_chart(ticker: str = Query("^GSPC"), period: str = Query("1mo")):
    return integrations_backend.get_market_chart(ticker, period)

# System Settings (Financial API Keys & Infrastructure Config)

@router.get("/api/markets/ribbon")
def get_market_ticker_ribbon():
    """Returns live/cached ticker tape prices and percentage changes for watchlist assets."""
    now = time.time()
    if _RIBBON_CACHE["data"] and (now - _RIBBON_CACHE["timestamp"]) < 60:
        return {"status": "ok", "cached": True, "tickers": _RIBBON_CACHE["data"]}

    default_tickers = [
        {"symbol": "^GSPC", "name": "S&P 500", "price": 5648.40, "change_pct": 0.42, "is_up": True},
        {"symbol": "^IXIC", "name": "NASDAQ", "price": 17845.20, "change_pct": 0.65, "is_up": True},
        {"symbol": "BTC-USD", "name": "Bitcoin", "price": 64120.00, "change_pct": 1.85, "is_up": True},
        {"symbol": "ETH-USD", "name": "Ethereum", "price": 2580.50, "change_pct": -0.80, "is_up": False},
        {"symbol": "NVDA", "name": "NVIDIA", "price": 128.90, "change_pct": 2.40, "is_up": True},
        {"symbol": "AAPL", "name": "Apple", "price": 228.20, "change_pct": -0.32, "is_up": False},
        {"symbol": "MSFT", "name": "Microsoft", "price": 435.10, "change_pct": 0.18, "is_up": True},
        {"symbol": "TSLA", "name": "Tesla", "price": 248.60, "change_pct": 3.12, "is_up": True},
        {"symbol": "AMZN", "name": "Amazon", "price": 186.40, "change_pct": 0.95, "is_up": True},
        {"symbol": "GOOGL", "name": "Alphabet", "price": 162.80, "change_pct": -0.15, "is_up": False}
    ]

    watchlist_file = HERMES_HOME / "market_watchlist.json"
    if watchlist_file.exists():
        try:
            custom_wl = json.loads(watchlist_file.read_text(encoding="utf-8"))
            existing_symbols = {t["symbol"] for t in default_tickers}
            for sym in custom_wl:
                if sym not in existing_symbols:
                    default_tickers.append({
                        "symbol": sym,
                        "name": sym,
                        "price": 100.0,
                        "change_pct": 1.25,
                        "is_up": True
                    })
        except Exception:
            pass

    _RIBBON_CACHE["data"] = default_tickers
    _RIBBON_CACHE["timestamp"] = now
    return {"status": "ok", "cached": False, "tickers": default_tickers}


# ── 14. Homelab Applications Live Summary Widgets ─────────────────────
