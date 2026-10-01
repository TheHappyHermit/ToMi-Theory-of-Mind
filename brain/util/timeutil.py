#!/usr/bin/env python3
"""
brain.util.timeutil — one timestamp format, one place that produces it.

WHY THIS EXISTS
Every timestamp column in brain/schema/brain_cortex.sql is declared TEXT and
intended to hold RFC 3339 UTC, and several of those columns are indexed or
ordered by. SQLite's datetime('now') produces a space-separated string:
'2026-09-26 12:15:16'. That sorts wrongly against an RFC 3339 value
('2026-09-26T12:15:16Z') without raising, because the differing character is in
position 11 and the rest of the string still looks ordered. So a table ends up
with two formats in one column, and "most recent first" quietly returns the
wrong rows.

Rather than fix each call site and leave the next person to reintroduce it, the
format lives here. Anything writing a timestamp into the brain schema uses
utc_now_iso().

The rule is not cosmetic: mixed formats in a single column break sorting and
silently defeat any index over it.
"""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["utc_now_iso", "to_iso", "is_rfc3339"]

# The canonical shape. Zoned, second precision, no offset variants -- one format
# for one column.
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now_iso() -> str:
    """Current UTC time as RFC 3339, e.g. '2026-09-26T12:15:16Z'."""
    return datetime.now(timezone.utc).strftime(_FORMAT)


def to_iso(value: datetime) -> str:
    """Render a datetime in the canonical format.

    A naive datetime is treated as UTC rather than local time. Assuming local
    would mean the same wall-clock reading produces different stored strings
    depending on where the process runs, which defeats ordering entirely.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime(_FORMAT)


def is_rfc3339(value: str) -> bool:
    """True if the string is in the canonical format.

    Used by the schema drift check to catch a mixed-format column before it
    starts returning rows in the wrong order.
    """
    if not isinstance(value, str) or len(value) != 20:
        return False
    try:
        datetime.strptime(value, _FORMAT)
    except ValueError:
        return False
    return value.endswith("Z")
