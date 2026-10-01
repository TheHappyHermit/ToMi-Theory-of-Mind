"""Shared pre-turn cognition state.

Lives in its own module because two hook handlers need it and the hook
directory name contains hyphens (`brain-cognitive-prep`), which is not a
legal Python module name. Both handlers load it by inserting
`<repo>/hooks` on sys.path and importing `brain_cognitive_prep.state`.

The file it manages is a small per-session verdict, written atomically by
the pre-turn hook and read by the post-turn consolidator to avoid
re-posting a stimulus that was already analysed.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any, Dict, Optional

STATE_DIR = os.path.join(
    os.path.expanduser("~"), ".hermes", "cache", "brain", "cognition"
)

# A verdict older than this is treated as absent. The pre-turn hook runs
# once per turn, so anything staler than a few minutes belongs to a turn
# that already ended.
CACHE_TTL_SECONDS = 300


def _state_path(session_id: str) -> str:
    """Resolve a session id to a filesystem-safe path.

    Session ids come from the gateway and are not guaranteed to be
    filesystem-safe, so strip anything that is not alphanumeric, dash or
    underscore rather than interpolating it into a path directly.
    """
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_")
    return os.path.join(STATE_DIR, f"{safe or 'default'}.json")


def write_state(session_id: str, verdict: Dict[str, Any]) -> bool:
    """Persist a verdict atomically. Returns True on success.

    Atomic (write to a temp file in the same directory, then os.replace)
    because a concurrent reader that caught a half-written file would see
    invalid JSON, treat it as "no cognition data", and silently fall back
    to the ungated path.
    """
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        path = _state_path(session_id)
        fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(verdict, fh)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return True
    except Exception:
        # Bookkeeping must never break a turn.
        return False


def read_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the cached verdict, or None if absent, unreadable or stale."""
    path = _state_path(session_id)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    try:
        if time.time() - float(data.get("ts", 0)) > CACHE_TTL_SECONDS:
            return None
    except Exception:
        return None
    return data
