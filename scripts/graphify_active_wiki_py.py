#!/usr/bin/env python3
"""Graphify Active Wiki Ingestion — sets env vars and runs graphify CLI as subprocess.

Why subprocess instead of direct import:
graphify's CLI entry point (main/dispatch_command) is tightly coupled to
argparse and sys.exit. The reliable pattern is to set os.environ then
subprocess-run the graphify CLI — this matches what refresh_graphify.py does
and what worked in the earlier successful run.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

# Set env vars BEFORE launching graphify
# API key for the custom vllm_qwen36_nothink provider (registered in ~/.graphify/providers.json)
os.environ['GRAPHIFY_VLLM_QWEN_API_KEY'] = '***'
# Graphify-level settings (not backend-specific)
os.environ['GRAPHIFY_MAX_OUTPUT_TOKENS'] = '131072'
os.environ['GRAPHIFY_MAX_RETRIES'] = '0'
os.environ['GRAPHIFY_API_TIMEOUT'] = '1800'

ACTIVE_WIKI = Path.home() / '.hermes' / 'active-wiki'
LOG_DIR = Path.home() / '.hermes' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'graphify-active-wiki.log'

print(f"[graphify-active-wiki-py] Started at {datetime.now(timezone.utc).isoformat()}")
print(f"[graphify-active-wiki-py] Source: {ACTIVE_WIKI}")
print(f"[graphify-active-wiki-py] Full wiki extraction (all subdirectories)")
print(f"[graphify-active-wiki-py] Token budget: 16000 | Concurrency: 1 | API timeout: 1800s")
print(f"[graphify-active-wiki-py] Max output tokens: 131072 | Max retries: 0")
print(f"[graphify-active-wiki-py] Backend: vllm_qwen36_nothink (custom, thinking disabled)")
print()

# Run graphify extract as subprocess — stream output in real time so we
# can see progress and the run isn't held hostage by capture_output.
# Use nohup + tee so output goes to both stdout and the log file.
log_fh = open(LOG_FILE, 'a')
print(f"[graphify-active-wiki-py] Logging to {LOG_FILE}")
print()

# Never pass --force, and never let GRAPHIFY_FORCE leak in from the environment.
# Both cause a full re-scan: --force skips the incremental manifest gate and the
# semantic cache, and also overwrites graph.json when the rebuild comes back with
# fewer nodes. That is the correct behaviour after a refactor that deletes code,
# and the wrong behaviour for a scheduled nightly ingest of a growing wiki -- it
# discards ~6,300 extracted nodes and re-pays for every one of them.
# .graphifyignore (in the vault) excludes .meta/ and graphify-out/.
# Why: the 2026-09-30 rebuild found that a full-vault index put 1,759 of
# 2,672 nodes (66%) into .meta/ -- maintenance reports and cascade logs the
# tooling writes about itself. Retrieval over that competes with the actual
# notes. research/ is deliberately NOT excluded; the compiled notes cite it.
# The rebuilt graph is 737 nodes with all 13 numbered areas represented.

env = dict(os.environ)
env.pop("GRAPHIFY_FORCE", None)

proc = subprocess.Popen(
    [
        'graphify', 'extract', str(ACTIVE_WIKI),
        '--token-budget', '16000',
        '--max-concurrency', '1',
        '--api-timeout', '1800',
        '--no-gitignore',
        '--backend', 'vllm_qwen36_nothink',
    ],
    cwd=str(ACTIVE_WIKI),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

# Stream output to both stdout and log file in real time
import threading
stop_event = threading.Event()

def stream_output():
    for line in proc.stdout:
        if stop_event.is_set():
            break
        print(line, end='')
        log_fh.write(line)
        log_fh.flush()

thread = threading.Thread(target=stream_output, daemon=True)
thread.start()

# Wait for completion (or timeout)
try:
    proc.wait(timeout=72000)
    stop_event.set()
    thread.join(timeout=5)
    result = proc.returncode
except subprocess.TimeoutExpired:
    print("[graphify-active-wiki-py] WARNING: graphify extract timed out after 7200s — it may still be running in the background. Check the log.")
    result = -1
finally:
    log_fh.close()

# Rotate log if too large (10 MB cap)
if LOG_FILE.exists() and LOG_FILE.stat().st_size > 10 * 1024 * 1024:
    LOG_FILE.rename(LOG_FILE.with_suffix('.log.1'))

# Append to log (not overwrite — preserve history across runs)
# Read the log file we just wrote to for the final summary
log_content = []
log_content.append(f"=== graphify-active-wiki run started: {datetime.now(timezone.utc).isoformat()} ===")
log_content.append(f"Source: {ACTIVE_WIKI}")
log_content.append(f"Token budget: 16000 | Concurrency: 1 | API timeout: 1800s")
log_content.append(f"Max output tokens: 131072 | Max retries: 0 | Backend: vllm_qwen36_nothink")
log_content.append(f"Return code: {result}")
log_content.append(f"=== graphify-active-wiki run finished: {datetime.now(timezone.utc).isoformat()} ===")
log_content.append("")

# Also print to stdout
for line in log_content:
    print(line)

print(f"\n[graphify-active-wiki-py] Finished with exit code: {result}")

# Quick stats
try:
    g = json.loads(open(ACTIVE_WIKI / 'graphify-out' / 'graph.json').read())
    m = json.loads(open(ACTIVE_WIKI / 'graphify-out' / 'manifest.json').read())
    # Graphify writes relationships under 'links' (a NetworkX-style
    # node-link dump), not 'edges'. Reading 'edges' here always yielded 0
    # and printed "edges=0" beside a graph holding 3,474 links, so a
    # successful rebuild looked like a total loss of connectivity. Accept
    # either key so a future schema change degrades to a real number
    # rather than a silent zero.
    links = g.get('links')
    if links is None:
        links = g.get('edges', [])
    print(f"nodes={len(g.get('nodes',[]))} links={len(links)} "
          f"hyperedges={len(g.get('hyperedges',[]))} "
          f"sources={len(g.get('extracted_sources',[]))}")
    print(f"manifest entries={len(m)}")
    print(f"input_tokens={g.get('input_tokens')} output_tokens={g.get('output_tokens')}")

    # A graph with nodes but no links is the signature of the failure this
    # counter previously hid, so state it rather than leaving the reader
    # to notice. Applies to the incremental-gate build as well as a full
    # one: a run that ingests nothing new legitimately keeps old links.
    if g.get('nodes') and not links:
        print("WARNING: graph has nodes but zero links -- extraction produced no "
              "relationships. Check the extraction backend, not the cluster step.")

except Exception as e:
    print(f"Could not read graph stats: {e}")

sys.exit(result)
