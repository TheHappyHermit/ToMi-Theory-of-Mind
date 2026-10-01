#!/usr/bin/env python3
"""Graphify Oracle Brain Ingestion — sets env vars and runs graphify CLI as subprocess.

Modeled after graphify_active_wiki_py.py. Processes the Oracle Brain wiki
(~/.hermes/oracle/brain/) and appends to the existing graph.json + manifest.json.

The Oracle Brain has ~1,558 tracked files in manifest.json. This wrapper:
- Sets env vars internally (GRAPHIFY_*)
- Runs graphify extract on the full wiki (all subdirectories), incrementally:
  the manifest gate and semantic cache are used so a run only extracts what is
  new or changed. --force is deliberately NOT passed, and GRAPHIFY_FORCE is
  stripped from the environment, because forcing would re-extract the whole
  wiki and overwrite graph.json even if the rebuild came back with fewer nodes.
- Writes progress to ~/.hermes/logs/graphify-oracle-brain.log
- Expected runtime: many hours (thousands of files across ~30K nodes)

Do NOT run this concurrently with the active wiki ingestion — they both hit
the same llama.cpp server. The cron schedule is set to 5 AM (after active wiki's
3 AM run).
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

# Set env vars BEFORE launching graphify
# API key for the custom vllm_qwen36_nothink provider (registered in ~/.graphify/providers.json)
os.environ['GRAPHIFY_VLLM_QWEN_API_KEY'] = os.environ.get('GRAPHIFY_VLLM_QWEN_API_KEY', 'sk-local')
# Graphify-level settings (not backend-specific)
os.environ['GRAPHIFY_MAX_OUTPUT_TOKENS'] = '131072'
os.environ['GRAPHIFY_MAX_RETRIES'] = '0'
os.environ['GRAPHIFY_API_TIMEOUT'] = '1800'

ORACLE_BRAIN = Path('$HOME/.hermes/oracle/brain')
LOG_DIR = Path('$HOME/.hermes/logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'graphify-oracle-brain.log'

print(f"[graphify-oracle-brain-py] Started at {datetime.now(timezone.utc).isoformat()}")
print(f"[graphify-oracle-brain-py] Source: {ORACLE_BRAIN}")
print(f"[graphify-oracle-brain-py] Full wiki extraction (all subdirectories)")
print(f"[graphify-oracle-brain-py] Token budget: 16000 | Concurrency: 1 | API timeout: 1800s")
print(f"[graphify-oracle-brain-py] Max output tokens: 131072 | Max retries: 0")
print(f"[graphify-oracle-brain-py] Backend: vllm_qwen36_nothink (custom, thinking disabled)")
print()

# Run graphify extract as a fully detached subprocess.
# The cron agent session has a timeout — if we wait for graphify in the
# foreground, the session dies and takes graphify with it. Instead, we:
# 1. Open the log file
# 2. Launch graphify with start_new_session=True (new process group)
# 3. Redirect stdout/stderr to the log file
# 4. Exit immediately — graphify runs independently
#
# This matches the active wiki pattern where the cron agent launches with
# nohup ... & and exits, leaving graphify running independently.

log_fh = open(LOG_FILE, 'a')
log_fh.write(f"\n=== graphify-oracle-brain run started: {datetime.now(timezone.utc).isoformat()} ===\n")
log_fh.write(f"Source: {ORACLE_BRAIN}\n")
log_fh.write(f"Token budget: 16000 | Concurrency: 1 | API timeout: 1800s\n")
log_fh.write(f"Max output tokens: 131072 | Max retries: 0 | Backend: vllm_qwen36_nothink\n\n")
log_fh.flush()

# Launch graphify detached — new session, output to log file
#
# Never pass --force, and never let GRAPHIFY_FORCE leak in from the environment.
# Both cause a full re-scan: --force skips the incremental manifest gate and the
# semantic cache, and also overwrites graph.json when the rebuild comes back with
# fewer nodes. This is the graph with 6,283 nodes in it, so a forced rebuild
# discards all of them and re-pays the extraction cost for every one.
_env = dict(os.environ)
_env.pop("GRAPHIFY_FORCE", None)

subprocess.Popen(
    [
        'graphify', 'extract', str(ORACLE_BRAIN),
        '--token-budget', '16000',
        '--max-concurrency', '1',
        '--api-timeout', '1800',
        '--no-gitignore',
        '--backend', 'vllm_qwen36_nothink',
    ],
    cwd=str(ORACLE_BRAIN),
    env=_env,
    stdout=log_fh,
    stderr=log_fh,
    text=True,
    bufsize=1,
    start_new_session=True,  # Detach from parent process group
)

print(f"[graphify-oracle-brain-py] Launched graphify detached (new session)")
print(f"[graphify-oracle-brain-py] Logging to {LOG_FILE}")
print(f"[graphify-oracle-brain-py] Exiting — graphify runs independently")
sys.exit(0)

# Rotate log if too large (10 MB cap)
if LOG_FILE.exists() and LOG_FILE.stat().st_size > 10 * 1024 * 1024:
    LOG_FILE.rename(LOG_FILE.with_suffix('.log.1'))

print(f"\n[graphify-oracle-brain-py] Finished with exit code: {result}")

# Quick stats
try:
    g = json.loads(open(ORACLE_BRAIN / 'graphify-out' / 'graph.json').read())
    m = json.loads(open(ORACLE_BRAIN / 'graphify-out' / 'manifest.json').read())
    # 'links', not 'edges' -- see the same fix in
    # graphify_active_wiki_py.py. Reading 'edges' printed 0 beside a graph
    # holding thousands of links, making a good build look empty.
    links = g.get('links')
    if links is None:
        links = g.get('edges', [])
    print(f"nodes={len(g.get('nodes',[]))} links={len(links)} hyperedges={len(g.get('hyperedges',[]))} sources={len(g.get('extracted_sources',[]))}")
    print(f"manifest entries={len(m)}")
    if 'input_tokens' in g:
        print(f"input_tokens={g['input_tokens']} output_tokens={g['output_tokens']}")
except Exception as e:
    print(f"Could not read graph stats: {e}")

sys.exit(result)
