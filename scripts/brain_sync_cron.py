#!/usr/bin/env python3
"""
brain_sync_cron.py — Cron wrapper for brain_sync.py.

Syncs each source separately with individual timeouts.
Exits 1 on failure so the cron system can track job health.

Sources: active-wiki, exchange-research (oracle-brain handled by separate monthly job)
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
BRAIN_SYNC = Path(__file__).resolve().parent / "brain_sync.py"
if not BRAIN_SYNC.exists():
    BRAIN_SYNC = REPO_DIR / "scripts" / "brain_sync.py"

PYTHON = Path(sys.executable)
SOURCES = ["active-wiki", "exchange-research"]

# Read embedding server & mode from environment.
#
# CHANGED 2026-09-27. Default was http://localhost:11434, where nothing
# listens. The cron job (50fd04244451) sets BRAIN_API_MODE but not the URL, and
# neither this wrapper nor brain_sync.py loads .env, so this default is what
# every scheduled run actually used -- and every one died on
# "Connection refused", then recorded a timestamp and reported success.
# Matches brain_sync.py's default; keep the two in step.
embed_url = (os.environ.get("BRAIN_OLLAMA_URL")
             or os.environ.get("INFERENCE_EMBED_URL")
             or "http://10.0.0.10:18082")
os.environ.setdefault("BRAIN_OLLAMA_URL", embed_url)
os.environ.setdefault("BRAIN_API_MODE", os.environ.get("BRAIN_API_MODE", "openai"))

# Per-source timeout — oracle-brain excluded (handled by separate monthly job)
OVERALL_TIMEOUT = 10800
PER_SOURCE_TIMEOUT = OVERALL_TIMEOUT // len(SOURCES) - 60


def rfc3339_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _verifier_sources(verify_script: Path) -> set:
    """
    Read the source names verify_brain_sync.py actually accepts.

    Parsed out of the verifier's own argparse `choices` rather than copied, so
    the two files cannot drift apart again -- which is exactly how
    "exchange-research" ended up being verified by a script that rejects it.
    If the pattern is not found, fall back to verifying nothing and say so,
    because a wrong "verified" is worse than an honest "skipped".
    """
    import re
    try:
        text = verify_script.read_text(encoding="utf-8")
    except OSError:
        return set()
    match = re.search(r'--source["\']\s*,\s*choices=\[([^\]]*)\]', text)
    if not match:
        print("  warning: could not read verify_brain_sync.py's accepted "
              "sources; skipping verification rather than guessing")
        return set()
    return {m.strip().strip("\"'") for m in match.group(1).split(",") if m.strip()}


def sync_source(source: str) -> bool:
    """Sync a single source. Returns True on success."""
    try:
        result = subprocess.run(
            [str(PYTHON), str(BRAIN_SYNC), "--source", source],
            capture_output=True, text=True, timeout=PER_SOURCE_TIMEOUT,
            cwd=str(REPO_DIR),
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Only print if there were actual changes (values > 0) or errors
        lines = stdout.split("\n")
        has_changes = False
        for line in lines:
            if not line.strip() or line.strip().startswith("Stats:"):
                continue
            # Check for "New: N" or "Updated: N" where N > 0
            for key in ["New:", "Updated:"]:
                if key in line:
                    try:
                        val = int(line.split(key)[1].strip().split()[0])
                        if val > 0:
                            has_changes = True
                            break
                    except (ValueError, IndexError):
                        pass
        
        if result.returncode != 0:
            print(f"[brain_sync_cron] {source}: ERROR rc={result.returncode}")
            if stderr:
                print(f"  stderr: {stderr[:200]}")
            return False
        
        if has_changes:
            # Print only the summary lines
            for line in lines:
                if any(k in line for k in ["New:", "Updated:", "Scanned:", "Errors:"]):
                    print(f"  {line.strip()}")
        
        return True
    except subprocess.TimeoutExpired:
        print(f"[brain_sync_cron] {source}: TIMEOUT after {PER_SOURCE_TIMEOUT}s")
        return False
    except Exception as e:
        print(f"[brain_sync_cron] {source}: ERROR {e}")
        return False


def main() -> int:
    if not BRAIN_SYNC.exists():
        print(f"[brain_sync_cron] brain_sync.py not found at {BRAIN_SYNC}")
        return 0

    if not PYTHON.exists():
        print(f"[brain_sync_cron] Python venv not found at {PYTHON}")
        return 0

    results = {}
    for source in SOURCES:
        results[source] = sync_source(source)

    # Run verification after sync
    print("\n[brain_sync_cron] Running post-sync verification...")
    verify_script = Path(__file__).resolve().parent / "verify_brain_sync.py"
    if not verify_script.exists():
        verify_script = REPO_DIR / "scripts" / "verify_brain_sync.py"
    if verify_script.exists():
        # Only verify sources the verifier actually accepts.
        #
        # verify_brain_sync.py takes `--source {active-wiki,oracle-brain}`, but
        # SOURCES here includes "exchange-research". Passing an unaccepted
        # value makes argparse exit 2 with a usage error, so every run printed
        # "exchange-research: X verification failed" and dumped the usage text.
        # That reads as a broken sync when the sync was fine -- and worse, it
        # trains you to ignore the verification line, so a REAL verification
        # failure would be invisible too.
        #
        # The accepted set is read from the verifier's own argparse definition
        # rather than duplicated here, so the two files cannot drift apart
        # again. A source with no verifier is reported as skipped, which is
        # the truth: it was not checked, it did not fail.
        verifiable = _verifier_sources(verify_script)
        for source in SOURCES:
            if source not in verifiable:
                print(f"  {source}: - no verifier defined (skipped, not a failure)")
                continue
            try:
                verify_result = subprocess.run(
                    [str(PYTHON), str(verify_script), "--source", source],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(REPO_DIR),
                )
                if verify_result.returncode == 0:
                    print(f"  {source}: ✓ verified")
                else:
                    print(f"  {source}: ✗ verification failed")
                    if verify_result.stderr:
                        print(f"    {verify_result.stderr.strip()[:200]}")
            except Exception as e:
                print(f"  {source}: verification error: {e}")
        unverifiable = [s for s in SOURCES if s not in verifiable]
        if unverifiable:
            print(f"  note: no verifier for {', '.join(unverifiable)} -- "
                  f"their sync result above is unverified, not unverified-because-failed")
    else:
        print(f"  verify_brain_sync.py not found, skipping verification")

    # Summary
    failures = [s for s, ok in results.items() if not ok]
    if failures:
        print(f"\n[brain_sync_cron] FAILURES: {', '.join(failures)}")
        return 1
    else:
        print(f"\n[brain_sync_cron] All sources synced OK ({len(SOURCES)} sources)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
