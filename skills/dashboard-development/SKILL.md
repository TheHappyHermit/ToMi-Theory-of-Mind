---
name: dashboard-development
description: "Build and iterate single-page dashboards — structured phases, modern CSS, FastAPI backends, and OpenCode collaboration."
---

# Dashboard Development

Use when building, refactoring, or iterating on a single-page dashboard (HTML/CSS/JS frontend + Python/Flask/FastAPI backend). Covers phase-based development, modern CSS techniques, backend API endpoints, and collaborating with OpenCode on iterative improvements.

## Phase-Based Approach

**Never dump everything at once.** Break changes into phases:

### Phase 0 — Foundation
- Read all existing files (CSS tokens, styles, HTML, JS, server)
- Identify the target architecture (single HTML, component framework, etc.)
- Document current state and known gaps

### Phase 1 — CSS Foundation (tokens.css + styles.css)
1. **tokens.css** — Add CSS custom properties for the visual language:
   - Glassmorphism: `--glass-bg`, `--glass-blur`, `--glass-border`
   - Glow effects: `--shadow-glow-accent`, `--shadow-glow-success`
   - Modern color: `light-dark()` function for theme-aware values
   - Typography scale: `--fs-xs` through `--fs-4xl`
   - Spacing scale: `--space-*` tokens
2. **styles.css** — Apply new tokens, add:
   - `animation-timeline: scroll()` for scroll-driven animations
   - `:has()` selector for parent-state styling
   - `backdrop-filter: blur()` for glass panels
   - Responsive `@media` breakpoints
   - Hover glow effects on interactive elements

### Phase 2 — HTML Structure (index.html)
- Add new semantic sections before existing ones (use `replace()` on a known comment anchor)
- Hero stats row: 6 key metrics in flex-wrap container
- Ensure aria-labels and roles on all regions
- Use BEM naming: `.panel--variant`, `.panel__header`, `.panel__body`

### Phase 3 — JavaScript (app.js)
- Add new fetch methods (`fetchSystemStats`, `fetchXxx`)
- Wire them into `refreshAllData()` via `Promise.all()`
- Add render methods for new HTML sections
- Keep the class-based `CommandDeck` pattern

### Phase 4 — Backend (dashboard_server.py)
- Add new `@app.get("/api/xxx")` endpoints
- Import `psutil` for system metrics
- Keep existing endpoints unchanged (additive only)
- Handle missing DB gracefully

### Phase 5 — Verification (MANDATORY)
- Start server on a fresh port
- Test each new API endpoint with curl
- **Open HTML in browser using `computer_use` capture** — screenshot or AX tree, NOT just curl
- Check all CSS classes render correctly
- **Never report "done" on a frontend without seeing it render in a real browser**

## Handoff Skepticism Rule

Handoff summaries from the user or past sessions are **context, not instructions**. They often contain inaccuracies (wrong line numbers, missing problems, incorrect root causes).

**Always verify independently:**
1. Read the actual file contents before forming a plan
2. Check for duplicate method definitions, missing utilities, wrong defaults
3. Run `node --check` or equivalent syntax check yourself
4. Don't trust claimed line numbers — search for the actual pattern

## Branch-First Workflow

**Never commit directly to main for non-trivial changes.** Multi-file changes, refactors, and anything that could break the build must go through a branch:

```bash
git checkout -b fix/dashboard-js-syntax
# ... make changes ...
# ... verify in browser ...
git push -u origin fix/dashboard-js-syntax
# ... create PR or merge after review ...
```

If the user asks to reset to a known-broken commit, ask why and suggest branching instead.

## Destructive Git Gate

**Ask before executing:** `git reset --hard`, `git rebase`, `git push --force`, `git clean -fd`.

When the user proposes a destructive operation:
1. Ask about the goal first
2. Suggest a safer alternative (branch from current, cherry-pick, etc.)
3. Only proceed after explicit confirmation

## Monolithic File Detection

Flag files >500 lines as technical debt. When working on a monolithic file:
1. Note it in the commit message ("refactor: split app.js — was 1566 lines")
2. Suggest splitting into modules (api.js, renderers.js, utilities.js, app.js)
3. Check for duplicate method definitions (common in large files)

## Modern CSS Techniques Used Here

| Technique | Use Case | Browser Support |
|-----------|----------|-----------------|
| `light-dark()` | Theme-aware colors | Safari 17.4+, Chrome 127+ |
| `:has()` | Parent state styling | All modern browsers |
| `backdrop-filter: blur()` | Glass panels | All modern browsers |
| `animation-timeline: scroll()` | Scroll-driven animations | Chrome 115+ |
| `oklch()` colors | Perceptually uniform | All modern browsers |
| `text-wrap: balance` | Balanced headlines | All modern browsers |

### Dashboard Not Running — Recovery Procedure

> **Which copy is live: `~/hermes-brain/dashboard/`.** A second, older copy
> exists at `~/dashboard/` (an project-era fork, 21 py files that have
> drifted). The running process is the repo copy. Verify before doing anything:
>
> ```bash
> ss -tlnp | grep 8088                      # then:
> tr '\0' ' ' < /proc/<PID>/cmdline         # expect .../hermes-brain/dashboard/run_dashboard.py
> ```
>
> If the cmdline names `~/dashboard/run_dashboard.py`, the wrong copy is
> running — that one still logs to `~/dashboard/dashboard.log` and its log
> predates the current process, so reading it for a current failure tells you
> about a server that is not serving.

When the dashboard is not responding on its expected port (default 8088):

### 1. Check if anything is listening
```bash
ss -tlnp | grep 8088
```
If nothing is listening, the server is down.

### 2. Check the log for import errors
```bash
tail -30 ~/.hermes/logs/dashboard.log 2>/dev/null || journalctl -n 30 --no-pager | grep -i uvicorn
```
The live process logs to `~/.hermes/logs/dashboard.log`. It does NOT write
`~/dashboard/dashboard.log`; that file belongs to the stale fork and stopped
updating 2026-09-26.
**The most common crash:** `ModuleNotFoundError: No module named 'fastapi'`. This happens when `run_dashboard.py` is launched with a Python that doesn't have the dashboard's dependencies. The shebang `#!/usr/bin/env python3` picks up the system Python (or whichever `python3` is first in PATH), which does NOT have `fastapi` or the other deps.

### 3. Which Python to use — check, do not assume

Two interpreters exist and **only one has the dependencies**. The dedicated venv
at `~/.hermes/dashboard-venv/` has fastapi and uvicorn but **not pg8000**,
which `backend/config.py` imports at module load. So it passes the obvious
`import fastapi` check and then the server dies on startup with
`ModuleNotFoundError: No module named 'pg8000'`.

Check for all three:

```bash
~/.hermes/dashboard-venv/bin/python -c "import fastapi, uvicorn, pg8000; print('venv OK')" 2>&1
```

If that fails, use the **Hermes agent venv**, which has everything:

```bash
~/.hermes/hermes-agent/venv/bin/python -c "import fastapi, uvicorn, pg8000; print('OK')"
```

This is the interpreter the currently-running server uses. Checking only
`fastapi` is how the wrong venv gets chosen.

### 4. Start the dashboard

Use the Python interpreter that passed the check above, binding to `0.0.0.0` for LAN access:

```bash
cd ~/hermes-brain
/path/to/python-with-deps dashboard/run_dashboard.py --host 0.0.0.0 --port 8088
```
`--host 0.0.0.0` is required for LAN access; the default binds loopback only.

**Pitfall:** If you start it in the foreground and it exits immediately, check the log. If you background it with `&` or `nohup` in a shell command, Hermes's `terminal()` will reject it — use `background=true` instead.

### 5. Verify

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088   # expect 200
curl -s http://127.0.0.1:8088/api/health                        # expect {"status":"ok",...}
ss -tlnp | grep 8088                                            # expect 0.0.0.0:8088, not 127.0.0.1:8088
```

### 6. Dependencies when reinstalling

If the venv needs to be populated and there's no `requirements.txt`, the canonical dependency list is in `dashboard/Dockerfile`:

```
fastapi
uvicorn[standard]
psutil
websockets
requests
pyyaml
pg8000
```

Install into the venv with:
```bash
~/.hermes/dashboard-venv/bin/pip install fastapi "uvicorn[standard]" psutil websockets requests pyyaml pg8000
```

## WebRTC Speech-to-Speech (S2S) Proxy Pattern

**When integrating a local S2S container that only speaks WebRTC** (no REST `/v1/audio/transcriptions` or `/v1/audio/speech`):

### Architecture
```
Browser (Voice Copilot)          Dashboard :8088                    S2S Container :8765
    │                                │                                  │
    │ getUserMedia + RTCPeerConnection                             │
    │────────────── SDP offer ──────────────────────────────────────►│
    │                                  POST /api/s2s/calls          │
    │                                  (proxied to /v1/realtime/calls)
    │◄──────────── SDP answer ─────────────────────────────────────│
    │                                  201 Created                  │
    │                                │                                  │
    │ Audio flows over WebRTC DataChannel (PCM16 24kHz)             │
    │                                │                                  │
    └─► STT: parakeet-tdt (NVIDIA)                                     │
    └─► LLM: Qwen via llama.cpp (GPU)                                 │
    └─► TTS: Kokoro-82M (ONNX, CPU)                                   │
```

### Backend Router (`backend/routes/s2s_webrtc.py`)
```python
@router.post("/api/s2s/calls")
async def s2s_webrtc_call(request: Request):
    raw_settings = integrations_backend.get_system_settings_raw()
    base = _get_s2s_base_endpoint(raw_settings)  # http://{LAN_IP}:8765
    target = f"{base}/v1/realtime/calls"

    offer_sdp = await request.body()
    headers = {"Content-Type": "application/sdp"}
    if api_key := raw_settings.get("voice_api_key"):
        headers["Authorization"] = f"Bearer {api_key}"

    resp = requests.post(target, data=offer_sdp, headers=headers, timeout=30)
    if resp.status_code in (200, 201):
        return JSONResponse(content={
            "status": "ok",
            "sdp": resp.text,
            "call_id": resp.headers.get("Location", "").split("/")[-1],
            "server": target
        })
    return JSONResponse(status_code=resp.status_code, content={
        "status": "error", "message": f"S2S WebRTC HTTP {resp.status_code}"
    })
```

### Frontend (`app-bots.js` — `startWebRTCS2S()`)
```javascript
async startWebRTCS2S() {
    this.webrtcStream = await navigator.mediaDevices.getUserMedia({audio: true});
    this.webrtcPc = new RTCPeerConnection({iceServers: []});
    this.webrtcStream.getTracks().forEach(t => this.webrtcPc.addTrack(t, this.webrtcStream));
    this.webrtcPc.ondatachannel = e => this._handleDataChannel(e.channel);
    this.webrtcPc.onicecandidate = e => { if (e.candidate) this._sendIceCandidate(e.candidate); };
    const offer = await this.webrtcPc.createOffer();
    await this.webrtcPc.setLocalDescription(offer);
    const resp = await fetch('/api/s2s/calls', {method: 'POST', headers: {'Content-Type': 'application/sdp'}, body: offer.sdp});
    const {sdp, call_id} = await resp.json();
    this.webrtcCallId = call_id;
    await this.webrtcPc.setRemoteDescription({type: 'answer', sdp});
}
```

### Voice Gateway Settings (stored in `system_settings`)
```json
{
  "voice": {
    "gateway_url": "http://{LAN_IP}",
    "gateway_port": "8765",
    "provider": "openai_compatible",
    "configured": true
  }
}
```

### Critical Gotchas
| Gotcha | Impact | Fix |
|--------|--------|-----|
| S2S container has single pipeline | Second concurrent call returns 503 | Queue or reject concurrent calls in UI |
| S2S returns 201, not 200 | Proxy expects 200 | Accept both 200 and 201 in backend |
| No REST STT/TTS endpoints | Legacy `/api/voice/stt`, `/api/voice/tts` return 404 | Keep as fallbacks, document WebRTC is primary |
| ICE candidates need SSE | Browser won't connect without ICE | Proxy `GET /v1/realtime/calls/{id}/events` for ICE |
| Dashboard package needs `__init__.py` | ModuleNotFoundError on import | Add empty `dashboard/__init__.py` |

---

## FastAPI Port Binding Pitfall

**Symptom:** Dashboard server reports "address already in use" on the default port even after killing processes.

**Cause:** `dashboard_server.py` has a `run()` function with `port=8088` hardcoded, and if the `--port` CLI arg parsing isn't wired correctly, it always binds to 8088.

**Fix:**
1. Kill any process on the target port: `fuser -k 8088/tcp`
2. Check the `run()` function at the bottom of `dashboard_server.py` — it may ignore CLI args
3. Start fresh on a new port: `python3 dashboard_server.py --port 8091`
4. Verify with `curl http://127.0.0.1:8091/api/system` before opening browser

## OpenCode Collaboration Patterns

### Context Limit — Never dump >30KB
OpenCode (qwen3.8-27b via LM Studio) chokes on massive combined briefings. **Never pass more than 30KB of combined file content in one prompt.**

**Instead:**
1. Write focused research files (one per topic) in `$HOME/oc-work/dashboard-overhaul/`
2. Reference them in a concise task brief: `Read GAP_ANALYSIS.md and PHASE1_PROMPT.md`
3. Point at specific files: `Modify styles.css, app.js, and dashboard_server.py`
4. After each OpenCode run, review changes before launching the next phase

### Terminal I/O Issues
OpenCode via `terminal()` with `background=true` can hang on terminal I/O. If it stalls for >2 minutes:
1. Kill the process: `process(action='kill', session_id=...)`
2. Check if it's actually running: `ps aux | grep opencode`
3. If running, it may be processing — wait longer
4. If not running, restart with a shorter prompt

### OpenCode Failures → Pivot to Direct Patching
OpenCode sessions frequently stall or produce silent failures with terminal I/O errors, especially when reading/writing large files (10KB+). **After 2 failed OpenCode attempts, stop trying and use `patch` + `execute_code` directly.** This session's OpenCode sessions all failed; Phase 1 was completed by direct patching instead. Do not retry OpenCode more than twice before switching.

### Static File Serving
A FastAPI backend with API-only endpoints (`/api/*`) does NOT serve static HTML/CSS/JS. You MUST add explicit routes:

```python
from fastapi.responses import FileResponse

DASHBOARD_DIR = Path(__file__).resolve().parent

@app.get("/")
def serve_dashboard():
    return FileResponse(str(DASHBOARD_DIR / "index.html"))

@app.get("/styles.css")
def serve_styles():
    return FileResponse(str(DASHBOARD_DIR / "styles.css"), media_type="text/css")
```

### Port Binding Gotcha
`dashboard_server.py` may have `run()` with a hardcoded `port=8088`. If `--port` CLI args are ignored (the parsing loop `break`s early on the first digit arg), the server always binds to 8088. Fix: check the `if __name__ == "__main__"` block and ensure `--port` parsing works. Always kill old processes before starting: `fuser -k 8088/tcp`.

### LAN Access
Bind to `0.0.0.0` not `127.0.0.1` so LAN clients can reach the dashboard:

```python
# In run() default and in __main__ block:
host = "0.0.0.0"
```

### escapeHtml() Utility
JavaScript render functions in `app.js` that output user data to the DOM MUST use an `escapeHtml()` utility to prevent XSS. Add it near the top of the file:

```javascript
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
```

### FileResponse Import
If `FileResponse` is used, ensure it's imported from `fastapi.responses`. A missing import causes a 500 on the first static file request.

## Graphify Config for Active Wiki

The active wiki graphify ingestion uses `GRAPHIFY_DISABLE_THINKING=1` for faster extraction:

```bash
# Launch graphify extract on active wiki
export OPENAI_BASE_URL="http://{LAN_IP}:8080/v1"
export OPENAI_API_KEY="sk-local"
export OPENAI_MODEL="/models/Qwen3.6-35B-A3B-Q4_K_M.gguf"
export GRAPHIFY_MAX_OUTPUT_TOKENS="98304"
export GRAPHIFY_DISABLE_THINKING=1

cd "${HOME}/.hermes/active-wiki"
python3 -c "
import os, sys
sys.path.insert(0, os.path.expanduser('~/hermes-brain/scripts'))
from graphify_api import extract_corpus
# ... extraction code ...
"
```

> **`~/hermes-brain` is gone.** The path this section used to add to
> `sys.path` was retired with the data root. The module lives in
> `~/hermes-brain/scripts/`. Use the `graphify` CLI directly where you can —
> it resolves its own paths and does not need a Python import.

Monitor with: `tail -f ${HOME}/.hermes/logs/graphify-active-wiki.log`

### Where the graphs actually live

Two indexes, kept strictly separate. The dashboard reads both, and its
`/api/graphify/data?graph=` parameter selects between them:

| Tier | Path | Nodes |
| :--- | :--- | ---: |
| Active wiki | `~/.hermes/active-wiki/graphify-out/graph.json` | 737 |
| Oracle vault | `~/.hermes/oracle/brain/graphify-out/graph.json` | 23,315 |

There is no third location. An earlier version of the dashboard also probed
`~/.hermes/graphify-main-out` as a "legacy" path; it never existed on this
host, so that probe contributed zero while implying a third source.

The active-wiki graph is rebuilt with `.meta/` excluded, so its node paths are
the numbered taxonomy (`00_System/`, `60_Decisions/`, …) and never
`system/` or `decisions/`. If a dashboard panel shows an old folder name, the
graph is stale, not the dashboard.

## Iteration Workflow

1. Read all active wiki research files
2. Compare against current dashboard
3. Write GAP_ANALYSIS.md with priorities
4. Launch OpenCode for Phase N
5. Review output in browser
6. Iterate with next phase
7. Repeat until satisfied or time runs out

See `references/opencode-briefing.md` for the briefing pattern.
See `references/graphify-configuration.md` for the disable-thinking setup.
See `references/phase-3-agent-intelligence.md` for Agent Intelligence panel patterns.
