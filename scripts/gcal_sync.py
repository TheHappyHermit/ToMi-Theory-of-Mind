#!/usr/bin/env python3
"""
Google Calendar sync for Hermes Brain dashboard.
Fetches upcoming events from Google Calendar and writes them to the cache file
that calendar_sync.py reads from.

Run via cron to keep the dashboard calendar fresh.

Python deps: uses the isolated google-sync venv (~/.hermes/google-sync-venv) so
`hermes update` can never break Calendar sync. Create it with scripts/setup_google_venv.sh
— or invoke this script with that venv's python directly.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Prefer the isolated google-sync venv's site-packages when not already running inside it
GOOGLE_VENV_SITE = Path.home() / ".hermes" / "google-sync-venv" / "lib"
if GOOGLE_VENV_SITE.exists() and "google-sync-venv" not in sys.executable:
    for _pydir in sorted(GOOGLE_VENV_SITE.glob("python*/site-packages"), reverse=True):
        if (_pydir / "googleapiclient").exists():
            sys.path.insert(0, str(_pydir))
            break

# Add the google-workspace skill scripts to the path
SKILL_SCRIPTS = Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

# The cache file location (read by dashboard/calendar_sync.py)
CALENDAR_CACHE = Path.home() / ".hermes" / "exchange" / "calendar" / "events_cache.json"

# Google API scope for calendar read-only
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# How many days ahead to fetch
DAYS_AHEAD = 90
# Max events to fetch
MAX_EVENTS = 200


def load_credentials():
    """Load OAuth credentials from the google-workspace skill token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError

    token_path = Path.home() / ".hermes" / "google_token.json"
    if not token_path.exists():
        print("[ERROR] No token file found. Run google-workspace setup first.")
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except Exception as e:
        print(f"[ERROR] Failed to load credentials: {e}")
        return None

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except RefreshError as e:
            print(f"[ERROR] Token refresh failed: {e}")
            return None

    return creds


def fetch_calendar_events(creds):
    """Fetch upcoming events from Google Calendar."""
    from googleapiclient.discovery import build

    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=DAYS_AHEAD)).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=MAX_EVENTS,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return events_result.get("items", [])


def transform_event(gcal_event):
    """Transform a Google Calendar event into the dashboard cache format."""
    start = gcal_event.get("start", {})
    end = gcal_event.get("end", {})

    # Determine if it's an all-day event
    is_all_day = "date" in start

    # Get start/end strings
    if is_all_day:
        start_str = start.get("date", "")
        end_str = end.get("date", "")
    else:
        start_str = start.get("dateTime", "")
        end_str = end.get("dateTime", "")

    # Determine category based on event properties
    category = "meeting"
    event_type = "calendar"
    color = "#3b82f6"  # blue default

    # Color-code by transparency/status
    transparency = gcal_event.get("transparency", "")
    status = gcal_event.get("status", "")
    attendees = gcal_event.get("attendees", [])

    if transparency == "transparent":
        # Free/transparent events get a muted color
        color = "#94a3b8"  # slate
    elif status == "cancelled":
        color = "#ef4444"  # red
        category = "cancelled"
    elif len(attendees) > 1:
        color = "#8b5cf6"  # purple for multi-person events
        category = "meeting"
    else:
        color = "#3b82f6"  # blue for personal events
        category = "personal"

    return {
        "id": f"gcal-{gcal_event.get('id', '')}",
        "title": gcal_event.get("summary", "Untitled Event"),
        "start": start_str,
        "end": end_str,
        "all_day": is_all_day,
        "category": category,
        "type": event_type,
        "color": color,
        "location": gcal_event.get("location", ""),
        "description": gcal_event.get("description", ""),
        "html_link": gcal_event.get("htmlLink", ""),
        "status": status,
        "attendee_count": len(attendees),
    }


def main():
    print(f"[INFO] Google Calendar sync started at {datetime.now().isoformat()}")

    creds = load_credentials()
    if not creds:
        print("[ERROR] Cannot authenticate with Google Calendar")
        sys.exit(1)

    try:
        raw_events = fetch_calendar_events(creds)
        print(f"[INFO] Fetched {len(raw_events)} events from Google Calendar")
    except Exception as e:
        print(f"[ERROR] Failed to fetch calendar events: {e}")
        sys.exit(1)

    transformed = [transform_event(ev) for ev in raw_events]

    # Ensure cache directory exists
    CALENDAR_CACHE.parent.mkdir(parents=True, exist_ok=True)

    # Write cache
    with open(CALENDAR_CACHE, "w", encoding="utf-8") as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False)

    print(f"[OK] Wrote {len(transformed)} events to {CALENDAR_CACHE}")

    # Print summary
    for ev in transformed[:5]:
        print(f"  - [{ev['start']}] {ev['title']} ({ev['category']})")
    if len(transformed) > 5:
        print(f"  ... and {len(transformed) - 5} more")


if __name__ == "__main__":
    main()
