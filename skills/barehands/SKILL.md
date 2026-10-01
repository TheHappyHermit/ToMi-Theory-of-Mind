---
name: barehands
description: Control the 3D webcam spatial air-board. Present notes, diagrams, glass cards, images, and 3D models directly onto the user's screen in 3D over their webcam, and inspect what is currently floating on the board.
---

# Barehands 🖐️ — 3D Spatial Air-Board Control

Barehands turns the user's webcam into a 3D hand-tracked spatial interface (`http://127.0.0.1:8794/stage.html`).
As Hermes Agent, you can reach out to the user's screen and present glass cards, system diagrams, reminders, and 3D models in mid-air. The user can grab, move, resize, or throw them with their bare hands.

---

## When to Use This Skill

Use this skill whenever the user asks:
- *"Show me the plan on screen"*
- *"Put that architecture diagram up"*
- *"Present the summary"*
- *"Clear the board"*
- *"What's currently on my screen?"*

---

## How to Control the Board

You can command the board either using the cross-platform CLI scripts included with this skill or via direct HTTP POST requests to `http://127.0.0.1:8794/cmd`.

### Method A: Using Cross-Platform Scripts (Recommended)

Located in `skills/barehands/scripts/`:

```bash
# Present a card (Spotlight center stage)
python skills/barehands/scripts/board.py '{"a":"present","title":"System Architecture","body":"Core subsystems active."}'

# Add a floating card to the ensemble
python skills/barehands/scripts/board.py '{"a":"add_card","title":"Checklist","body":"- [x] Tasks done"}'

# Clear the board
python skills/barehands/scripts/board.py '{"a":"clear"}'

# Explode / assemble 3D models
python skills/barehands/scripts/board.py '{"a":"explode"}'
python skills/barehands/scripts/board.py '{"a":"assemble"}'

# Inspect board state (what the user sees right now)
python skills/barehands/scripts/board_state.py
```

On Windows, `board.bat` and `board-state.bat` wrappers are also available.

---

### Method B: Direct HTTP API (`POST http://127.0.0.1:8794/cmd`)

If invoking directly via `curl` or Python `urllib`:

#### 1. Present a Card (Center Stage Spotlight)
Flies the card directly to the center of the user's screen, spotlit and enlarged:
```bash
curl -s -X POST http://127.0.0.1:8794/cmd \
  -H "Content-Type: application/json" \
  -d '{
    "a": "present",
    "title": "System Architecture",
    "body": "## Core Subsystems\n- **Thalamus**: Saliency gating\n- **dlPFC**: Working memory\n- **Basal Ganglia**: Action gating"
  }'
```

#### 2. Add an Ensemble Card
```bash
curl -s -X POST http://127.0.0.1:8794/cmd \
  -H "Content-Type: application/json" \
  -d '{
    "a": "add_card",
    "title": "Database Checklist",
    "body": "- [x] Schema initialized\n- [x] Migrations applied\n- [ ] Port verified"
  }'
```

#### 3. Clear the Board
```bash
curl -s -X POST http://127.0.0.1:8794/cmd \
  -H "Content-Type: application/json" \
  -d '{"a": "clear"}'
```

#### 4. Inspect Board State (`GET http://127.0.0.1:8794/state`)
```bash
curl -s http://127.0.0.1:8794/state
```

---

## Operational Guidelines

1. **Be Concise & Readable**: Keep card titles short (< 40 chars) and body text structured with markdown bullet points and headings.
2. **Visual Reinforcement**: When explaining complex multi-step plans or architectures verbally, proactively offer or present a card so the user has a spatial visual reference.
3. **Fail-Open**: If the Barehands server is not running (e.g. connection refused), simply output the text directly in chat without crashing.
