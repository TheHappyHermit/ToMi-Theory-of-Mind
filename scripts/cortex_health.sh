#!/usr/bin/env bash
# Daily health check for the Hermes stack.
#
# This is the repo-side entry point. It delegates to the operational scripts
# in ~/.hermes/scripts rather than carrying its own copies, so there is one
# implementation of each check and no second tree to drift.
#
# The previous version called into ~/personal-agent: it `bash`ed a Python file
# (which cannot work), and grepped a personal_ops.py that does not exist. The
# grep meant a broken organizer could never fail this script, so a scheduled
# run looked green in its log while the check it performed was dead.
set -uo pipefail

SCRIPTS="${HERMES_SCRIPTS:-$HOME/.hermes/scripts}"

# Accumulate failures so one run reports everything wrong, rather than
# stopping at the first problem.
rc=0

echo "=== Daily Health Check ==="
echo "Time: $(date)"

if [ ! -x "$SCRIPTS/verify_stack.py" ] && [ ! -f "$SCRIPTS/verify_stack.py" ]; then
  echo "✗ verify_stack.py not found in $SCRIPTS"
  exit 1
fi

# verify_stack.py exits non-zero when any check fails, so its exit status is
# what gates this, not the printed text.
if python3 "$SCRIPTS/verify_stack.py" 2>&1; then
  echo "✓ Verification passed"
else
  echo "✗ Verification failed — see output above"
  rc=1
fi

# personal_ops.py health exits non-zero and prints "ok": false when the
# organizer API or database is unreachable. Its exit status is authoritative.
if [ -f "$SCRIPTS/personal_ops.py" ]; then
  if python3 "$SCRIPTS/personal_ops.py" health 2>&1; then
    echo "✓ Personal Ops healthy"
  else
    echo "✗ Personal Ops has issues"
    rc=1
  fi
else
  echo "- Personal Ops CLI not installed (skipped)"
fi

echo "=== Health check complete ==="
exit $rc
