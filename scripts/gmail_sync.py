#!/usr/bin/env python3
"""
Gmail sync for Hermes Brain — fetches recent emails and caches them for the daily briefing.
Run at 6:30 AM so the 7 AM daily briefing has fresh data without competing for API calls.

Caches two things:
1. Recent emails (last 24h) → gmail_cache.json
2. Subscription-related emails → subscriptions_cache.json (for the briefing's cross-reference)

Python deps: uses the isolated google-sync venv (~/.hermes/google-sync-venv) so
`hermes update` can never break Gmail sync. Create it with scripts/setup_google_venv.sh
— or invoke this script with that venv's python directly.
"""

import json
import os
import re
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

# Cache locations
CACHE_DIR = Path.home() / ".hermes" / "exchange" / "gmail"
GMAIL_CACHE = CACHE_DIR / "gmail_cache.json"
SUBSCRIPTIONS_CACHE = CACHE_DIR / "subscriptions_cache.json"

# Google API scope for Gmail read-only
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# How many hours back to scan
SCAN_HOURS = 24
# Max results per query
MAX_RESULTS = 100


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
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except RefreshError as e:
            print(f"[ERROR] Token refresh failed: {e}")
            return None

    return creds


def fetch_messages(creds, query):
    """Fetch messages matching a Gmail search query."""
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)

    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=MAX_RESULTS,
    ).execute()

    messages = result.get("messages", [])

    # Fetch full message details
    full_messages = []
    for msg in messages[:MAX_RESULTS]:
        try:
            full = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            full_messages.append(full)
        except Exception as e:
            print(f"[WARN] Failed to fetch message {msg['id']}: {e}")

    return full_messages


def extract_email_text(message):
    """Extract plain text snippet from a Gmail message."""
    snippet = message.get("snippet", "")
    # Clean up HTML entities
    snippet = snippet.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    return snippet


def parse_sender(message):
    """Extract sender name and email from message headers."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "From":
            return h["value"]
    return "Unknown"


def parse_subject(message):
    """Extract subject from message headers."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Subject":
            return h["value"]
    return "(No Subject)"


def parse_date(message):
    """Extract date from message headers."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Date":
            return h["value"]
    return ""


def is_subscription_related(message):
    """Check if a message is subscription-related (receipts, invoices, renewals)."""
    subject = parse_subject(message).lower()
    sender = parse_sender(message).lower()
    snippet = extract_email_text(message).lower()

    keywords = [
        "receipt", "invoice", "payment", "subscription", "renewal",
        "charged", "billing", "order confirmation", "purchase",
        "your receipt", "thank you for your payment", "paid",
        "auto-renew", "renewed", "cancelled", "refund",
    ]

    for kw in keywords:
        if kw in subject or kw in sender or kw in snippet:
            return True

    return False


def extract_amount(text):
    """Try to extract a dollar amount from text."""
    # Match patterns like $12.99, $1,234.56, etc.
    matches = re.findall(r'\$[\d,]+\.?\d*', text)
    if matches:
        return matches[0]
    return None


def main():
    print(f"[INFO] Gmail sync started at {datetime.now().isoformat()}")

    creds = load_credentials()
    if not creds:
        print("[ERROR] Cannot authenticate with Gmail")
        sys.exit(1)

    # Build the search query for the last N hours
    # Gmail search: newer_than:1d for last 24 hours
    query = f"newer_than:{SCAN_HOURS // 24 or 1}d"

    try:
        messages = fetch_messages(creds, query)
        print(f"[INFO] Fetched {len(messages)} messages from Gmail")
    except Exception as e:
        print(f"[ERROR] Failed to fetch Gmail messages: {e}")
        sys.exit(1)

    # Transform all messages to a clean format
    all_emails = []
    subscription_emails = []

    for msg in messages:
        sender = parse_sender(msg)
        subject = parse_subject(msg)
        date = parse_date(msg)
        snippet = extract_email_text(msg)
        amount = extract_amount(f"{subject} {snippet}")

        email_entry = {
            "id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "sender": sender,
            "subject": subject,
            "date": date,
            "snippet": snippet,
            "amount": amount,
            "labels": msg.get("labelIds", []),
        }

        all_emails.append(email_entry)

        if is_subscription_related(msg):
            subscription_emails.append(email_entry)

    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Write full email cache
    gmail_cache_data = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "scan_hours": SCAN_HOURS,
        "total_emails": len(all_emails),
        "emails": all_emails,
    }
    with open(GMAIL_CACHE, "w", encoding="utf-8") as f:
        json.dump(gmail_cache_data, f, indent=2, ensure_ascii=False)

    # Write subscription-specific cache
    sub_cache_data = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "scan_hours": SCAN_HOURS,
        "total_subscription_emails": len(subscription_emails),
        "emails": subscription_emails,
    }
    with open(SUBSCRIPTIONS_CACHE, "w", encoding="utf-8") as f:
        json.dump(sub_cache_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Wrote {len(all_emails)} emails to {GMAIL_CACHE}")
    print(f"[OK] Wrote {len(subscription_emails)} subscription-related emails to {SUBSCRIPTIONS_CACHE}")

    # Print summary
    for e in subscription_emails[:5]:
        print(f"  - [{e['date']}] {e['subject']} — {e['sender']} ({e.get('amount', 'no amount')})")
    if len(subscription_emails) > 5:
        print(f"  ... and {len(subscription_emails) - 5} more")


if __name__ == "__main__":
    main()
