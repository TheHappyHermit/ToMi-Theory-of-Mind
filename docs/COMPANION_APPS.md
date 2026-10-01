# Companion Applications Integration Guide

Hermes Brain includes built-in adapters for Jared Rhodes' open-source spatial and visual tools (located in `plugins/adapters/`):
1. **[ai-visualizer](https://github.com/jaredrhod/ai-visualizer)**: Animated procedural faces (circuit board, radial starburst, matrix code rain, neural core) that react in real-time to Hermes Agent thinking, speaking, and idling.
2. **[barehands](https://github.com/jaredrhod/barehands)**: 3D webcam hand-tracking spatial interface that allows Hermes Agent to project glass cards, diagrams, notes, and 3D models into the air on the user's screen.

---

## Architectural Principle: 100% Untouched Upstream Code

Hermes Brain connects to these applications through a **non-invasive adapter architecture**:
* **Zero code modifications**: We do not fork, edit, or patch Jared Rhodes' code files.
* **Effortless updates**: You can run `git pull` inside `ai-visualizer` or `barehands` at any time to get upstream bug fixes, new faces, and gesture improvements without merge conflicts.
* **Clean licensing**: Jared's code remains standalone AGPLv3, while Hermes Brain remains clean MIT.
* **Communication via standard interfaces**:
  * `ai-visualizer` communicates via its native `.voice_state` signal bus.
  * `barehands` communicates via its native `state/state` bus and HTTP `POST /cmd` / `GET /state` endpoints.

---

## Installation & Setup

### Step 1: Clone the Upstream Repositories

Clone both repositories as siblings to `Brain` (or in your user home directory):

```bash
# In your coding or agent directory (e.g. c:\Coding or ~/):
git clone https://github.com/jaredrhod/ai-visualizer.git
git clone https://github.com/jaredrhod/barehands.git
```

Recommended directory structure:
```
Coding/ (or ~/my-agent/)
├── Brain/           # Hermes Brain (this repository)
├── ai-visualizer/   # Upstream AI Visualizer (port 8790)
└── barehands/       # Upstream Barehands 3D stage (port 8794)
```

---

### Step 2: Initialize Configuration Files

Both applications use JSON configuration files (`ai-visualizer.json` and `barehands.json`) which are **gitignored upstream**, so creating them does not modify git-tracked code.

You can initialize them automatically using the Hermes Brain adapter:

```bash
# From the Brain directory:
python -m plugins.adapters.visualizer setup
python -m plugins.adapters.barehands setup
```

Or configure them manually:

#### `ai-visualizer/ai-visualizer.json`
```json
{
  "name": "HERMES",
  "face": "board",
  "badge": "BRAIN",
  "port": 8790,
  "thinking_sound": true,
  "bus_dir": ""
}
```

#### `barehands/barehands.json`
```json
{
  "name": "HERMES",
  "port": 8794,
  "orbs": [
    { "title": "Props", "path": "media", "kind": "media" }
  ]
}
```

---

### Step 3: Install Hermes Brain Hooks and Skills

Run the Hermes Brain installer to link hooks and skills into `~/.hermes/`:

```bash
python install.py
```

This installs:
* **Hook (`hermes-visualizer-sync`)**: Listens to Hermes Agent lifecycle events (`agent:start`, `agent:step`, `agent:end`, `session:reset`) and broadcasts state (`thinking`, `speaking`, `idle`) directly to `.voice_state` and `state/state`.
* **Skill (`barehands`)**: Teaches Hermes Agent how to use `skills/barehands/scripts/board.py` and `POST /cmd` to present glass cards, explode 3D models, and inspect the board.

---

## Running the Stack

You can run each component in separate terminals:

```bash
# Terminal 1: Hermes Brain Dashboard & API
python -m hermes.server

# Terminal 2: AI Visualizer
cd ../ai-visualizer && python server.py

# Terminal 3: Barehands 3D Stage
cd ../barehands && python server.py
```

Or run all three together using the unified launcher:
```bash
python scripts/start_all.py
```

---

## Verifying Integration

1. Open **AI Visualizer** at `http://127.0.0.1:8790/`.
2. Open **Barehands 3D Stage** at `http://127.0.0.1:8794/stage.html` in Google Chrome (with webcam enabled).
3. Test state sync from the command line:
   ```bash
   python -m plugins.adapters.visualizer set-state thinking
   python -m plugins.adapters.barehands set-ring thinking
   ```
   * The visualizer face should light up with thinking pulses.
   * The barehands ring on the stage should spin and pulse.
4. Test presenting a 3D glass card:
   ```bash
   python skills/barehands/scripts/board.py '{"a":"present","title":"HERMES ONLINE","body":"Spatial bridge operational."}'
   ```
   * A glass card should fly into the center of your webcam feed.
