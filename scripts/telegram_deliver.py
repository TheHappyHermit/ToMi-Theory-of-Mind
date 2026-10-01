#!/usr/bin/env python3
"""
Deliver newsletter to Telegram via Bot API.
Uses TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS from .env file.
"""

import requests
import sys
import os
from pathlib import Path

# Load .env
env_path = str(Path(os.path.expanduser("~/.hermes/.env")))
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS')

# Read newsletter content
with open(str(Path(os.path.expanduser("~/.hermes/newsletter_output.md"))), 'r') as f:
    newsletter = f.read()

# Determine chat_id from allowed_users (first user)
if allowed_users:
    chat_id = allowed_users.split(',')[0].strip()
else:
    print("No allowed users configured")
    sys.exit(1)

# Check message length
max_len = 4000
if len(newsletter) <= max_len:
    chunks = [newsletter]
else:
    chunks = [newsletter[i:i+max_len] for i in range(0, len(newsletter), max_len)]

print(f"Sending newsletter ({len(newsletter)} chars) in {len(chunks)} chunk(s) to chat_id {chat_id}...")

# Send each chunk
for i, chunk in enumerate(chunks):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": chunk,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, json=payload, timeout=30)
    print(f"Chunk {i+1}/{len(chunks)}: {resp.status_code} - {resp.json()}")

print("✓ Newsletter delivered to Telegram successfully!")
