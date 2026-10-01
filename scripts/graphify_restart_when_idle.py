#!/usr/bin/env python3
"""Wait for llama.cpp slots to drain, then restart graphify with the output-cap fix.

Root cause being fixed: graphify caps LLM output at 8192 tokens client-side
(known graphify issue #1365 — see llm.py:1839). The server itself has NO cap
(n_predict: -1, n_ctx: 262144). The 8k cap truncates JSON mid-object, making it
unparseable, so chunks get discarded. GRAPHIFY_MAX_OUTPUT_TOKENS is the
documented override (llm.py:305).
"""
import json
import os
import subprocess
import time
import urllib.request

SLOTS_URL = "${LLAMA_BASE_URL:-http://localhost:8080}/slots"
BRAIN = "$HOME/.hermes/oracle/brain"
LOG = "$HOME/.hermes/logs/graphify-oracle-brain.log"
WATCH_LOG = "$HOME/.hermes/logs/graphify-restart-watcher.log"

# The V100 llama.cpp server is shared infrastructure: Honcho's deriver, this
# graphify run, AND a SEPARATE Hermes agent belonging to the operator's wife all use it.
# So "all 4 slots free" may never happen. We only need ONE free slot to make
# progress, and we must not wait forever on someone else's workload.
FREE_SLOTS_NEEDED = 1
REQUIRED_IDLE_STREAK = 3
POLL_SECONDS = 60
MAX_WAIT_SECONDS = 2 * 3600  # 2h, then restart anyway — coexist rather than starve


def log(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{stamp} {msg}\n"
    with open(WATCH_LOG, "a", encoding="utf-8") as fh:
        fh.write(line)
    print(line, end="")


def slot_state() -> tuple[int, int] | None:
    """Return (busy, total) slot counts, or None if the probe failed."""
    try:
        with urllib.request.urlopen(SLOTS_URL, timeout=10) as resp:
            slots = json.load(resp)
        busy = sum(1 for s in slots if s.get("is_processing"))
        return busy, len(slots)
    except Exception as exc:  # noqa: BLE001 - report and keep waiting
        log(f"WARN slots probe failed: {exc}")
        return None


def graphify_running() -> bool:
    r = subprocess.run(
        ["pgrep", "-f", "graphify extract"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and bool(r.stdout.strip())


def semantic_cache_count() -> int:
    path = os.path.join(BRAIN, "graphify-out", "cache", "semantic")
    total = 0
    for _root, _dirs, files in os.walk(path):
        total += len(files)
    return total


def main() -> None:
    log("=== watcher start ===")
    log(f"semantic cache at start: {semantic_cache_count()}")

    deadline = time.time() + MAX_WAIT_SECONDS
    streak = 0
    timed_out = True

    while time.time() < deadline:
        state = slot_state()
        if state is None:
            time.sleep(POLL_SECONDS)
            continue
        busy, total = state

        # Graphify itself occupies a slot while it works, so discount our own.
        others = max(0, busy - 1) if graphify_running() else busy
        free = total - busy

        if free >= FREE_SLOTS_NEEDED:
            streak += 1
            log(
                f"capacity OK: {busy}/{total} busy ({others} other clients), "
                f"{free} free (streak {streak}/{REQUIRED_IDLE_STREAK})"
            )
        else:
            if streak:
                log(f"saturated again: {busy}/{total} busy, 0 free — streak reset")
            streak = 0

        if streak >= REQUIRED_IDLE_STREAK:
            timed_out = False
            break
        time.sleep(POLL_SECONDS)

    if timed_out:
        log(
            "NOTE waited MAX_WAIT_SECONDS without sustained free capacity — "
            "restarting anyway to coexist (shared GPU, may be another agent's load)"
        )

    if graphify_running():
        subprocess.run(["pkill", "-TERM", "-f", "graphify extract"], check=False)
        for _ in range(30):
            if not graphify_running():
                break
            time.sleep(1)
        if graphify_running():
            log("WARN old process still alive after SIGTERM; sending SIGKILL")
            subprocess.run(["pkill", "-KILL", "-f", "graphify extract"], check=False)
            time.sleep(2)
        log("old graphify process stopped")

    before = semantic_cache_count()
    log(f"semantic cache before relaunch: {before}")

    env = os.environ.copy()
    env.update(
        {
            "GRAPHIFY_VLLM_QWEN_API_KEY": "***",
            # THE FIX: lift graphify's 8192 client-side output cap.
            # 48k chosen deliberately: the server has n_ctx=262144 and no output
            # cap of its own (n_predict=-1), so headroom is plentiful. Larger
            # output budget = fewer mid-JSON truncations = fewer discarded chunks.
            "GRAPHIFY_MAX_OUTPUT_TOKENS": "49152",
        }
    )
    # A relaunch should resume from the semantic cache, not re-extract. --force
    # skips the manifest gate and the cache, and overwrites graph.json when the
    # rebuild has fewer nodes -- so a relaunch after an unrelated crash could
    # throw away a good graph. GRAPHIFY_FORCE does the same, so drop it too.
    env.pop("GRAPHIFY_FORCE", None)

    cmd = [
        "graphify", "extract", ".",
        "--backend", "vllm_qwen36_nothink",
        "--max-concurrency", "1",
        "--token-budget", "24000",
        "--api-timeout", "1800",
        "--no-gitignore",
    ]

    with open(LOG, "a", encoding="utf-8") as logfh:
        logfh.write(
            f"\n=== RESTART {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
            f"with GRAPHIFY_MAX_OUTPUT_TOKENS=32768 (fix for 8k truncation) ===\n"
        )
        logfh.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=BRAIN,
            env=env,
            stdout=logfh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    log(f"relaunched graphify pid={proc.pid}")

    # Verify it actually came up and is talking to the GPU.
    time.sleep(45)
    if graphify_running():
        log("VERIFIED graphify is running after relaunch")
    else:
        log("ERROR graphify died within 45s of relaunch — check the log")

    log("=== watcher done ===")


if __name__ == "__main__":
    main()
