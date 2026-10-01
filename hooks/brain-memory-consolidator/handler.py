#!/usr/bin/env python3
"""
brain-memory-consolidator — Episodic Memory & Working Memory Consolidation Hook.

Fires on agent:end and session:reset events to:
1. Feed user input into HermesBrain thalamus & working memory.
2. Record action outcomes for executed tools to update somatic markers & limbic valence.
3. Consolidate high-surprise episodes into hippocampal replay.
4. Fail-open safely so agent execution is never blocked.
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional

BRAIN_API_URL = os.environ.get("BRAIN_API_URL", "http://localhost:8088")


def _post_json(endpoint: str, data: Dict[str, Any], timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """Helper to post JSON data to HermesBrain REST API."""
    url = f"{BRAIN_API_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return None


def handle(event_type: str, context: Dict[str, Any]) -> None:
    """
    Called by Hermes Agent runtime on agent:end or session:reset events.
    """
    session_id = context.get("session_id", "default_session")
    user_message = context.get("message") or ""
    agent_response = context.get("response") or ""
    tools_called = context.get("tools_called") or []
    has_error = context.get("has_error", False)

    # 1. Update working memory and thalamic buffer with stimulus.
    #
    # SKIPPED when brain-cognitive-prep already ran on agent:start. Both
    # hooks posted the same user_message to /api/brain/stimulus, so the
    # thalamic buffer saw the text twice per turn and surprise scores were
    # computed against a duplicated stimulus. The pre-turn hook's cached
    # verdict is the marker that it already happened; absence of the file
    # means the old single-hook path still works unchanged.
    #
    # Persistence of outcomes (step 2 onward) still runs here, on
    # agent:end, where the results actually exist.
    pre_turn_ran = False
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from brain_cognitive_prep.state import read_state
        pre_turn_ran = read_state(session_id) is not None
    except Exception:
        # Import or state failure must not skip the stimulus: falling
        # back to posting it is the safe direction, since duplicating a
        # stimulus is recoverable and dropping one loses the input.
        pre_turn_ran = False

    if user_message and not pre_turn_ran:
        _post_json("/api/brain/stimulus", {
            "text": user_message,
            "source": context.get("platform", "user"),
            "session_id": session_id,
        })

    # 2. Record tool outcomes to reinforce somatic markers and limbic valence
    for tool_call in tools_called:
        tool_name = tool_call.get("name") or "tool"
        tool_target = str(tool_call.get("target") or tool_call.get("args") or "")[:100]
        success = not tool_call.get("error", False) and not has_error
        surprise = 0.6 if not success else 0.1

        _post_json("/api/brain/action-outcome", {
            "action": tool_name,
            "target": tool_target,
            "success": success,
            "surprise_score": surprise,
        })

    # 3. If session reset or completed with surprise, run a quick consolidation replay
    if event_type == "session:reset" or has_error:
        _post_json("/api/brain/consolidate", {"max_episodes": 3})
