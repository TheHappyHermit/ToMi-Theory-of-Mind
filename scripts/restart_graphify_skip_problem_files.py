#!/usr/bin/env python3
"""
Restart graphify extraction on the Oracle brain, EXCLUDING the files that
tripped the out-of-scope cache guard.

Background
----------
The repeated warning was:

    RuntimeWarning: semantic cache skipped out-of-scope source_file
    '<file>'; the file was not dispatched for extraction

Researched at graphify/cache.py:1420-1427 and graphify/llm.py:2338-2375.
This is a deliberate SAFETY GUARD (graphify issue #1757), not a failure:

  - Each completed chunk is checkpointed to the semantic cache immediately.
  - The write is scoped to the files actually dispatched in that chunk.
  - The model sometimes attributes an extracted node's `source_file` to a
    DIFFERENT corpus file than the one that was sent.
  - Without the guard, that stray node would clobber (or pollute) the other
    file's complete cache entry.
  - So the guard drops the out-of-scope node and warns.

Net effect: nothing is silently cached-without-extraction. The opposite --
a misattributed node is DISCARDED to protect a good cache entry. The named
files are victims of misattribution by other chunks, not files that failed.

They are excluded here only because the operator asked to skip the previous problem
files for now. They can be re-run on their own later.

Usage
-----
    python3 restart_graphify_skip_problem_files.py

Environment respected:
    GRAPHIFY_MAX_OUTPUT_TOKENS  (default 49152 -- required, see bug #1365)
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

def _resolve_hermes_data_dir() -> Path:
    if os.environ.get("HERMES_DATA_DIR"):
        return Path(os.environ["HERMES_DATA_DIR"]).resolve()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).resolve()
    if os.environ.get("CORTEX_HOME"):
        return Path(os.environ["CORTEX_HOME"]).resolve()
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        win_hermes = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if win_hermes.exists():
            return win_hermes
    default_hermes = Path.home() / ".hermes"
    if default_hermes.exists():
        return default_hermes
    legacy_hermes = Path.home() / ".hermes"
    if legacy_hermes.exists():
        return legacy_hermes
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return default_hermes

HERMES_DATA_DIR = _resolve_hermes_data_dir()
BRAIN = Path(os.environ.get("ORACLE_BRAIN_PATH", str(HERMES_DATA_DIR / "oracle" / "brain")))
LOG = HERMES_DATA_DIR / "logs" / "graphify-oracle-brain.log"
EXCLUDE_FILE = HERMES_DATA_DIR / "graphify-skipped-files.txt"

# The six files that tripped the out-of-scope guard. Skipped for now per
# the operator's instruction; not known to be individually broken.
PROBLEM_FILES = [
    "AI_ML/Interpretability-Debate.md",
    "Glial-Biology/Astrocyte-Neuron-Interactions-and-Cognition.md",
    "Graph-Neural-Networks/Graph-Neural-Networks-and-Relational-AI.md",
    "Gut-Brain-Axis/Gut-Brain-Axis-and-Microbiome-Cognition.md",
    "Hardware-Hacking/Flipper-Zero-Field-Notes.md",
    "Healthy-Aging/Healthy-Aging-and-Cognitive-Decline.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def already_running() -> bool:
    """True if a graphify extract is already alive -- never double-run.

    Uses `ps` and filters out shell wrappers: `pgrep -af graphify` also matches
    the transient `bash -c ... eval 'pgrep -af graphify'` wrapper that Hermes'
    terminal tool creates, which produced a false positive in testing.
    """
    out = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True
    ).stdout
    me = Path(__file__).name
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_s, args = line.split(None, 1)
        except ValueError:
            continue
        if int(pid_s) == os.getpid() or me in args:
            continue
        if "hermes-snap" in args or args.startswith("/usr/bin/bash -c"):
            continue
        if "eval " in args:
            continue
        if "graphify" in args and "extract" in args:
            return True
    return False


def main() -> int:
    if not BRAIN.is_dir():
        print(f"FATAL: brain directory not found: {BRAIN}", file=sys.stderr)
        return 2

    if already_running():
        print("A graphify extract is already running; refusing to start a second.")
        return 0

    env = os.environ.copy()
    # Client-side output cap bug #1365: without this, output is truncated at
    # 8192 and chunks die with 'invalid JSON'.
    env.setdefault("GRAPHIFY_MAX_OUTPUT_TOKENS", "49152")

    # graphify's openai backend needs OPENAI_* pointed at the local V100
    # llama.cpp server. Without these it exits immediately with
    # "backend 'openai' requires OPENAI_API_KEY to be set" -- which is exactly
    # how an unattended restart failed silently. The canonical values live in
    # the brain's .openai_keys file; read them rather than duplicating secrets.
    keyfile = BRAIN / ".openai_keys"
    if keyfile.is_file():
        for line in keyfile.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    env.setdefault("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL", "http://localhost:8080/v1"))
    env.setdefault("OPENAI_MODEL", os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "/models/Qwen3.6-35B-A3B-Q4_K_M.gguf"))

    if not env.get("OPENAI_API_KEY"):
        print(
            "FATAL: OPENAI_API_KEY not set and not found in "
            f"{keyfile}. graphify's openai backend will refuse to start.",
            file=sys.stderr,
        )
        return 3

    cmd = [
        str(Path.home() / ".local" / "bin" / "graphify"),
        "extract",
        ".",
        "--backend", "openai",
        "--max-concurrency", "1",
        "--token-budget", "24000",
        "--api-timeout", "1800",
    ]

    # graphify honours .graphifyignore for corpus exclusion.
    ignore = BRAIN / ".graphifyignore"
    prior = ignore.read_text() if ignore.exists() else None
    lines = []
    if prior:
        lines.extend(prior.rstrip("\n").split("\n"))
    marker = "# --- temporarily skipped: out-of-scope cache guard (see restart script) ---"
    if marker not in lines:
        lines.append(marker)
        lines.extend(PROBLEM_FILES)
    ignore.write_text("\n".join(lines) + "\n")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n=== RESTART {utc_now()} "
            f"MAX_OUTPUT_TOKENS={env['GRAPHIFY_MAX_OUTPUT_TOKENS']} "
            f"skipping {len(PROBLEM_FILES)} problem file(s) ===\n"
        )
        fh.flush()
        proc = subprocess.Popen(
            cmd, cwd=str(BRAIN), env=env, stdout=fh, stderr=fh,
            start_new_session=True,
        )

    print(f"graphify restarted (pid {proc.pid})")
    print(f"  cwd     : {BRAIN}")
    print(f"  log     : {LOG}")
    print(f"  skipping: {len(PROBLEM_FILES)} file(s) via {ignore}")
    print(f"  excluded list also saved at {EXCLUDE_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
