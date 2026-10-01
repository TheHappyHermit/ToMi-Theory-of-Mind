#!/bin/bash
# Nightly CognitivePlatform Dashboard Deployment for the Oracle Cloud target ($WG_HOSTNAME)
# Syncs latest dashboard files from local to oracle server
# Does NOT touch the public Wine & Gecko front page

set -euo pipefail

LOG_FILE="$HOME/.hermes/logs/Gateway-deploy.log"
SSH_KEY="$HOME/.ssh/oracle_cloud_key"
WG_HOST="${WG_HOSTNAME:-${ORACLE_CLOUD_IP:-<ORACLE-CLOUD-IP>}}"
SERVER="ubuntu@${WG_HOST}"
WEBROOT="${WG_WEBROOT:-/var/www/<SERVICE-DOMAIN>}"
SOURCE_DIR="${WG_SOURCE_DIR:-$HOME/.paperclip/instances/default/projects/f9eed7bd-177d-4bac-8a1d-a7a5aaa02f7f/c3f26a85-a271-4e50-9cfd-604acad5c2ff/_default}"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S PST')] $*" | tee -a "$LOG_FILE"
}

log "=== Starting nightly deployment ==="

# Step 1: Verify SSH connection
log "Testing SSH connection..."
if ! ssh $SSH_OPTS $SERVER "echo ok" > /dev/null 2>&1; then
    log "ERROR: SSH connection failed"
    exit 1
fi
log "SSH connection OK"

# Step 2: Upload dashboard files (front page untouched)
log "Uploading dashboard files..."
scp $SSH_OPTS "$SOURCE_DIR/index.html" $SERVER:/tmp/wf_index.html
scp $SSH_OPTS "$SOURCE_DIR/css/style.css" $SERVER:/tmp/wf_style.css
scp $SSH_OPTS "$SOURCE_DIR/js/main.js" $SERVER:/tmp/wf_main.js

# Step 3: Move files into place on server
log "Deploying files..."
ssh $SSH_OPTS $SERVER "
sudo cp /tmp/wf_index.html $WEBROOT/dashboard/index.html
sudo cp /tmp/wf_style.css $WEBROOT/dashboard/css/style.css
sudo cp /tmp/wf_main.js $WEBROOT/dashboard/js/main.js
sudo chown -R www-data:www-data $WEBROOT/dashboard/
rm -f /tmp/wf_index.html /tmp/wf_style.css /tmp/wf_main.js
"

# Step 4: Reload Nginx
log "Reloading Nginx..."
ssh $SSH_OPTS $SERVER "sudo systemctl reload nginx"

# Step 5: Verify deployment
log "Verifying deployment..."
FRONT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${WG_HOST}/)
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "admin:${WG_ADMIN_PASSWORD:-<WG_ADMIN_PASSWORD>}" http://${WG_HOST}/dashboard/)
AUTH_BLOCKED=$(curl -s -o /dev/null -w "%{http_code}" http://${WG_HOST}/dashboard/)

log "Front page: $FRONT_STATUS | Dashboard: $DASHBOARD_STATUS | Auth check: $AUTH_BLOCKED"

if [ "$FRONT_STATUS" = "200" ] && [ "$DASHBOARD_STATUS" = "200" ] && [ "$AUTH_BLOCKED" = "401" ]; then
    log "SUCCESS: Deployment verified"
    echo "DEPLOY_SUCCESS"
else
    log "WARNING: Verification failed - Front=$FRONT_STATUS Dashboard=$DASHBOARD_STATUS Auth=$AUTH_BLOCKED"
    echo "DEPLOY_WARNING"
fi

log "=== Deployment complete ==="