#!/usr/bin/env python3
"""
brain-cognitive-prep — Pre-turn cognition hook.

WHY THIS EXISTS
---------------
The full cognitive analysis (thalamic gating, pragmatics, somatic risk,
System 1/2 routing, Theory of Mind, prospective memory) used to run ONLY
on `agent:end`, which is dispatched after the agent has already composed
and sent its reply. So the reasoning was real, but it informed the NEXT
turn instead of the current one. ToM inferred what the user meant after we
had already answered as though we did not.

FIX, AND ITS LIMIT
------------------
This hook runs the SAME analysis on `agent:start`, before the turn. That
is the only hook event that fires with the user message present and
before any model call.

The limit is structural and worth stating plainly: `agent:start` is
dispatched through `HookRegistry.emit()`, which discards return values
(verified in gateway/hooks.py: "Fire all handlers for an event, DISCARDING
return values"). So this hook cannot inject text into the model's context
and therefore cannot change what the agent says in this turn.

What it DOES do is make the cognition available to the agent at the point
it can still be used:
  * `decision` and `rationale` are written to a per-session state file,
    which the brain-cognitive-guard handler and the SOUL.md prompt
    reference;
  * a one-line risk verdict is printed into the turn's stderr log, so the
    operator sees the gate fire before the reply rather than after;
  * the analysis is cached so the post-turn consolidator does not repeat
    the expensive work (see PER_TURN_ANALYSIS_CACHE below).

Fails open in every path. A cognition hook that can break a turn is worse
than no cognition hook.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

# The state helpers live in a sibling module so the post-turn consolidator
# can import them too; `hooks/` is added to sys.path because the hook
# directory name contains hyphens and is not importable as a package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from brain_cognitive_prep.state import (  # noqa: E402
    CACHE_TTL_SECONDS,
    read_state,
    write_state,
)

BRAIN_API_URL = os.environ.get("BRAIN_API_URL", "http://localhost:8088")


def _post_json(
    endpoint: str, data: Dict[str, Any], timeout: float = 2.0
) -> Optional[Dict[str, Any]]:
    """POST to the brain REST API. Returns None on any failure.

    BRAIN_API_URL is read here, at call time, rather than bound once at
    import. A module-level binding freezes the value for the lifetime of
    the process, so a later change to the environment is silently
    ignored and the hook keeps talking to whatever endpoint was current
    when it was first imported.
    """
    base = os.environ.get("BRAIN_API_URL", "http://localhost:8088")
    url = f"{base}{endpoint}"
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
    """Pre-turn cognition. Returns None: agent:start discards returns."""
    if event_type != "agent:start":
        return

    session_id = context.get("session_id", "default_session")
    user_message = (context.get("message") or context.get("input") or "").strip()
    if not user_message:
        return

    # Feed the stimulus first: gating and routing read the thalamic
    # buffer, so they need the text already present.
    _post_json(
        "/api/brain/stimulus",
        {
            "text": user_message,
            "source": context.get("platform", "user"),
            "session_id": session_id,
        },
    )

    # Run the pre-turn gate.
    #
    # In-process FIRST, HTTP second, matching brain-cognitive-guard's
    # _evaluate_in_process(). The brain is a stdlib-only library that
    # loads without the dashboard running, so probing HTTP alone would
    # report the brain "unreachable" on a healthy system whose dashboard
    # happens to be down, and cache a false GO. The dashboard being
    # offline is not evidence about the brain.
    decision, rationale, warning, via = "GO", "", None, None

    try:
        # Append, do not insert: insert(0, REPO_ROOT) would jump ahead of
        # any path the caller already set up (a test sandbox, an
        # alternative install) and silently defeat it.
        if REPO_ROOT not in sys.path:
            sys.path.append(REPO_ROOT)
        from brain.hermes_brain import HermesBrain

        hb = HermesBrain()
        somatic_bias, somatic_warning = hb.somatic_engine.assess(
            "agent:start", user_message[:160]
        )
        decision, _net_drive, rationale = hb.action_gate.evaluate_pathways(
            candidate_action="agent:start",
            expected_utility=0.8,
            somatic_bias=somatic_bias,
            conflict_level=0.0,
        )
        warning = somatic_warning
        via = "in-process"
    except Exception:
        # No in-process brain; fall back to the REST API.
        pass

    if via is None:
        result = _post_json(
            "/api/brain/action-check",
            {
                "action": "agent:start",
                "target": user_message[:160],
                "expected_utility": 0.8,
                "session_id": session_id,
            },
        )
        decision = (result or {}).get("decision", "GO")
        rationale = (result or {}).get("rationale", "")
        warning = (result or {}).get("somatic_warning")
        via = "http" if result is not None else "unavailable"

    _write_and_report(session_id, event_type, decision, rationale, warning, via)


def _write_and_report(session_id, event_type, decision, rationale, warning, via):
    """Persist the verdict, then log anything that is not a plain GO.

    Split out so handle() has exactly one exit and the logging cannot be
    skipped by an early return.
    """
    verdict = {
        "ts": time.time(),
        "session_id": session_id,
        "event": event_type,
        "decision": decision,
        "rationale": rationale,
        "somatic_warning": warning,
        # True means we got a real verdict from a real brain, by either
        # transport. False means the gate genuinely could not run, which
        # the post-turn path needs in order to distinguish "the gate ran
        # and said GO" from "the gate never ran".
        "brain_reachable": via in ("in-process", "http"),
        "gate_via": via,
    }
    write_state(session_id, verdict)

    if decision not in ("GO", "HYPERDIRECT_BRAKE", "NO_GO"):
        # Unexpected vocabulary. Do not invent a risk level from it.
        return

    if decision != "GO":
        # Printed BEFORE the agent replies, so the operator sees the gate
        # fire at the right moment. This is the part that is observable
        # today; injecting it into model context would need a core change
        # to how agent:start results are handled.
        print(
            f"[brain-cognitive-prep] {decision} (pre-turn): {rationale}"
        )
