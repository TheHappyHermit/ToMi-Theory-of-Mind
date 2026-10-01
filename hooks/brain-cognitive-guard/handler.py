#!/usr/bin/env python3
"""
brain-cognitive-guard — Basal Ganglia Action Gating & Executive Inhibition Hook.

Intercepts agent:step and command:* events to:
1. Assess somatic risk markers for candidate tools/commands.
2. Evaluate Basal Ganglia Direct (Go) vs Indirect (No-Go) pathways.
3. Detect repetitive execution loops (Miyake cognitive shifting).
4. Fail-open safely if Brain API is unreachable.
"""

from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

BRAIN_API_URL = os.environ.get("BRAIN_API_URL", "http://localhost:8088")

# Transport order: IN-PROCESS FIRST, HTTP second. Changed 2026-09-27.
#
# This function previously tried HTTP first and only fell back to a direct
# import. That made a systemd-run dashboard on port 8088 the primary path and
# the reliable one the exception, which is backwards: brain/ is a stdlib-only
# library that always loads, while the dashboard can be down for reasons that
# have nothing to do with the brain (reboot, crash, port conflict, a bad
# update). The hook is documented to fail open, so whenever the dashboard was
# down the C14 enforcement check silently stopped existing -- no error, no
# alert. That is exactly the failure Decision C5 names: a monitor that has
# never been caught failing is not a monitor that works.
#
# Order is now: try the local library, fall back to the HTTP API only if the
# import genuinely cannot work (e.g. brain/ not on sys.path for this process).
# The fail-open at the end is now genuinely last-resort rather than the common
# case. See IMPLEMENT-HANDOFF.md section 2.7.


def _evaluate_in_process(action: str, target: str, conflict_level: float = 0.0) -> Optional[Dict[str, Any]]:
    """Evaluate the action gate by importing brain/ directly. No network.

    Returns None only if brain/ cannot be imported at all.
    """
    try:
        from brain.hermes_brain import HermesBrain
    except Exception:
        return None

    try:
        brain = HermesBrain()
        somatic_bias, somatic_warning = brain.somatic_engine.assess(action, target)
        decision, net_drive, rationale = brain.action_gate.evaluate_pathways(
            candidate_action=action,
            expected_utility=0.8,
            somatic_bias=somatic_bias,
            conflict_level=conflict_level,
        )
        return {
            "decision": decision,
            "net_drive": net_drive,
            "rationale": rationale,
            "somatic_bias": somatic_bias,
            "somatic_warning": somatic_warning,
            "transport": "in_process",
        }
    except Exception:
        return None


def _query_brain_api(action: str, target: str, conflict_level: float = 0.0) -> Optional[Dict[str, Any]]:
    """Evaluate the action gate. In-process first, HTTP API as fallback."""
    result = _evaluate_in_process(action, target, conflict_level)
    if result is not None:
        return result

    url = f"{BRAIN_API_URL}/api/brain/action-check"
    payload = json.dumps({
        "action": action,
        "target": target,
        "expected_utility": 0.8,
        "conflict_level": conflict_level,
        "emergency_alert": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                out = json.loads(resp.read().decode("utf-8"))
                if isinstance(out, dict):
                    out["transport"] = "http"
                return out
    except Exception:
        pass

    return None


def handle(event_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Called by Hermes Agent runtime on agent:step or command:* events.
    """
    tool_name = context.get("tool_name") or context.get("command") or ""
    tool_args = context.get("tool_args") or context.get("args") or {}

    if not tool_name:
        return None

    # Derive target parameter for risk appraisal
    target = ""
    if isinstance(tool_args, dict):
        target = str(tool_args.get("path") or tool_args.get("command") or tool_args.get("target") or "")[:120]
    elif isinstance(tool_args, str):
        target = tool_args[:120]

    # Evaluate action
    result = _query_brain_api(action=tool_name, target=target)
    if not result:
        return None  # Fail-open: allow action if brain offline

    decision = result.get("decision", "GO")
    rationale = result.get("rationale", "")
    somatic_warning = result.get("somatic_warning")

    # ── Hook return contract, verified against Hermes core ──────────────
    #
    # ONLY `command:<name>` events consult a handler's return value, and
    # they read exactly these keys (gateway/run_inbound.py):
    #     {"decision": "deny"|"handled"|"rewrite", "message": str, ...}
    #
    # `agent:step` CANNOT block anything. It is dispatched via
    # HookRegistry.emit(), which is documented as "Fire all handlers for an
    # event, DISCARDING return values" (gateway/hooks.py), and the call
    # site additionally schedules it fire-and-forget via self._schedule().
    # So the previous `{"halt": True}` return here was a no-op exactly like
    # the `advisory` one it replaced -- two different key names, both
    # discarded, for the same underlying reason.
    #
    # The keys `advisory`, `halt`, `suppressOutput`, `systemMessage` and
    # `additionalContext` appear ZERO times in the Hermes hook dispatcher.
    # Do not add them back.
    if decision == "HYPERDIRECT_BRAKE":
        print(f"[brain-cognitive-guard] CRITICAL: {rationale}")
        return {
            "decision": "deny",
            "message": f"Emergency Brake: {rationale}",
        }

    if decision == "NO_GO":
        print(f"[brain-cognitive-guard] WARNING: {rationale}")
        warning = somatic_warning or "High risk detected."
        # Deny on the decision-style event, where the return is honoured.
        # On agent:step this dict is discarded by design, so the print
        # above is the only observable effect there.
        return {
            "decision": "deny",
            "message": (
                f"[Cognitive Guard Alert]: {rationale} "
                f"Somatic Warning: {warning}"
            ),
        }

    return None
