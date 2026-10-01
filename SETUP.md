# Configuration & Setup Guide for Hermes Brain 🧠

This document provides complete instructions for configuring Hermes Brain, connecting model providers, setting up the dual-engine database, and launching the modular telemetry dashboard.

---

## ⚙️ Configuration Files

### 1. `config.yaml`
The primary system configuration file is `config.yaml` at the project root. Key sections include:

```yaml
system:
  environment: "production"
  log_level: "INFO"
  device: "cuda"

models:
  primary:
    provider: "llamaCPP" # or "ollama", "openai", "vllm"
    model_name: "Qwen3.6-35B-A3B-Q4_K_M.gguf"
    base_url: "http://127.0.0.1:8080/v1"
    temperature: 0.2
    max_tokens: 4096
    context_window: 32768

embeddings:
  provider: "ollama" # or "openai", "local"
  model: "bge-m3"
  base_url: "http://127.0.0.1:11434"
  dimensions: 1024

brain:
  database_path: "brain/brain.db"
  thalamus:
    saliency_threshold: 0.35
  working_memory:
    slot_capacity: 7
    decay_rate: 0.15
  cognitive_router:
    system2_threshold: 0.50
  action_gate:
    go_threshold: 0.40
```

---

## 🗄️ Database Setup: Dual-Engine Support

### Option 1: SQLite (Default, Zero-Setup)
SQLite is enabled by default. The database file is placed at `brain/brain.db`. All tables defined in `brain/schema/brain_cortex.sql` (beliefs, defeaters, somatic markers, user mental models, counterfactual rollouts, working memory snapshots) will be automatically created on startup.

### Option 2: PostgreSQL with pgvector (Enterprise / Homelab)
For high-concurrency environments or multi-node clusters:

1. Create the database and enable `pgvector`:
```sql
CREATE DATABASE hermes_brain;
\c hermes_brain;
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Apply the cognitive cortex schema:
```bash
psql -U postgres -d hermes_brain -f brain/schema/brain_cortex.sql
```

3. Configure environment variables in `.env`:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/hermes_brain
BRAIN_STORAGE_BACKEND=postgres
```

---

## 🖥️ Launching the Modular Dashboard Server

Hermes Brain includes a lightweight, modular web dashboard providing real-time cognitive telemetry, task organization, agent chat, and system health metrics.

### Architecture of the Dashboard Backend
The backend is modularized into domain-specific FastAPI routers in `dashboard/backend/routes/`:
- `brain.py`: HermesBrain cognitive architecture (status, stimulus, action-check, action-outcome, beliefs, consolidate, counterfactual).
- `system.py`: Host telemetry, CPU/GPU stats, homelab status, settings.
- `organizer.py`: Task manager, project tracking, calendar, intentions, reminders.
- `agent_bots.py`: Hermes interactive chat, bot profiles, approval gates, checkpoints.
- `knowledge_memory.py`: Epistemic belief search, vault notes, decision logs, Honcho memory.
- `integrations.py`: Docker services, Home Assistant, n8n, SearXNG search proxy.
- `markets_voice.py`: Financial watchlists, market quotes, STT / TTS voice endpoints (Edge TTS neural voice fallback).
- `static.py`: UI static asset delivery.

### Running the Dashboard
```bash
python dashboard/dashboard_server.py --port 8088
# Or via Docker Compose:
docker compose up -d
```
Open your browser and navigate to:
```text
http://localhost:8088
```

---

## 🎛️ Dynamic Settings Engine (No Hardcoded Values)

The Command Deck includes an interactive settings manager (`Settings` view -> `System Settings & AI Providers`):
- **Operator Identity**: Set `HERMES_OPERATOR_NAME` dynamically.
- **Primary AI Inference Provider (LLM)**: Choose OpenRouter, OpenAI, Anthropic, Ollama, llama.cpp, vLLM, LM Studio, or a custom endpoint with custom API keys and model IDs. Includes a live **Test API Connection** probe.
- **Speech & Voice Engine**:
  - **Text-to-Speech (TTS)**: Native Microsoft Edge TTS (free, no API key required, neural voices like `en-US-GuyNeural` / `en-US-JennyNeural`), OpenAI TTS (`tts-1`), ElevenLabs, or Local Piper.
  - **Speech-to-Text (STT)**: Browser Web Speech API, OpenAI Whisper (`whisper-1`), Groq Whisper (`whisper-large-v3`), or Local Faster-Whisper.

---

## 🔗 Hermes Agent Hooks & Skills Integration

Hermes Brain seamlessly integrates with [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent):

### 1. Lifecycle Hooks (`hooks/`)
- **`brain-cognitive-guard`**: Intercepts `agent:step` and `command:*` events to check Basal Ganglia Go/No-Go pathways and Somatic Marker risk appraisal before executing consequential actions.
- **`brain-memory-consolidator`**: Captures conversation turns on `agent:end` and `session:reset`, updates working memory, reinforces somatic markers, and schedules hippocampal replay.
- **`to-do-capture`**: Automatically captures user task intentions and stores them in `organizer.db`.

To install or update hooks in Hermes Agent:
```bash
python install.py --link-only
```

### 2. Cognitive Skill (`skills/hermes-brain`)
Compliant with the `agentskills.io` standard. Allows Hermes Agent to inspect its own working memory (dlPFC Cowan chunks), evaluate action risk, record counterfactual regret lessons, and manage grounded beliefs.

---

## 🔄 Cognitive Synchronization & Offline Replay

To execute background memory synchronization, vector embedding sync, and hippocampal sharp-wave ripple (SWR) consolidation:

### 1. Hippocampal Replay Consolidation
Run offline consolidation to convert high-surprise episodic traces into long-term semantic rules:
```bash
curl -s -X POST http://localhost:8088/api/brain/consolidate -H "Content-Type: application/json" -d '{"max_episodes": 5}'
```

### 2. Autonomous Cron Scheduling
Seed and maintain background cognitive routines:
```bash
python scripts/setup_cron_jobs.py
```

---

## 🛡️ Security & Operational Guardrails

- **Miyake Prepotent Inhibition**: Hermes Brain actively checks proposed shell and database commands against destructive patterns (`rm -rf /`, `DROP DATABASE`, `format`, `git reset --hard`) before execution.
- **Damasio Somatic Marker Biasing**: Commands and tool calls that historically resulted in errors or crashes accumulate negative somatic valence, triggering automatic alerts or blocking execution via the Basal Ganglia No-Go pathway.
- **Theory of Mind False-Belief Calibration**: The agent monitors differences between user assumptions and grounded system reality to proactively prevent misunderstandings.
