#!/bin/bash
# FreshRSS daily summary - runs at 6am and 9pm
# Checks for new feed items and generates a summary
echo "[$(date)] FreshRSS summary check"

# If FreshRSS is running, check for new items
if docker ps --format '{{.Names}}' | grep -q freshrss; then
    echo "FreshRSS container found, checking for updates..."
    # Add your FreshRSS query logic here
    docker exec freshrss php app/actualize_script.php --long 2>/dev/null
else
    echo "FreshRSS not running - skipping"
fi
