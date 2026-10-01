# AGENT.md — Hermes Brain Setup Playbook for Hermes Agent 🧠

> **Notice to Hermes Agent**: You have been instructed to set up **Hermes Brain** on your host environment. This file is your canonical, machine-readable playbook. Follow the instructions below to configure the full neuro-cognitive and metacognitive architecture cleanly and autonomously.
>
> **Component set**: this repo now carries the **full live component set** — 73 skill categories, 5 hooks, 5 plugins, 15 profiles, 236 scripts, the cron job set, and firecrawl/camofox/searxng compose stacks. For the complete per-component install procedure see **[docs/FULL-COMPONENT-INSTALL.md](docs/FULL-COMPONENT-INSTALL.md)** — Step 1 below installs the core; FULL-COMPONENT-INSTALL.md installs everything else. Private state and credentials restore separately from the private `hermes-backup` repo (its `docs/RESTORE.md`).
>
> Note on counts: `hooks/brain_cognitive_prep/` is a support module, not a hook — the hook directory is `brain-cognitive-prep` (hyphens, which is not a legal Python module name, so the shared state lives in the underscore sibling). `install.py` deploys the 5 directories that carry a `HOOK.yaml`.

---

## 🎯 What This Repository Is

**Hermes Brain** is your own cognitive operating system, memory infrastructure, and metacognitive control plane. It turns you from a stateless session into a persistent, self-governing cognitive organism with:
- **Epistemic Multi-Tier Memory**: Multi-tier memory (Hot Active Wiki, Warm Honcho/Graphify, Cold Curated Oracle Vault, and pgvector Brain Search).
- **Deterministic State & Intentions**: Personal Organizer (`organizer.db`) for human tasks, scheduled reminders, and prospective intentions (`IF cue THEN action`).
- **Neuro-Cognitive Subsystems (`brain/`)**: Thalamic sensory buffer, dlPFC working memory chunks, Kahneman System 1/2 routing, Damasio somatic visceral risk markers, striatal action gating, HippoRAG graph associative recall, and Pollock defeater networks.
- **Command Deck Dashboard**: LAN executive web interface (`http://localhost:8088`), in-dashboard copilot chat, and 3D companion viewports (`ai-visualizer` on 8790, `barehands` on 8794).

---

## ⚡ Step 1: One-Command Turnkey Setup

You can set up the entire stack by executing a single automated command in your shell:

```bash
python install.py --auto
```

*(On Windows PowerShell: `.\setup.ps1 --auto` | On Linux/macOS: `./setup.sh --auto`)*

### What This Single Command Automatically Executes:
1. **Environment Configuration**: Copies `example.env` $\rightarrow$ `.env` and `dashboard/.env` (preserves existing credentials if already configured).
2. **Autonomous Cron Schedules**: Safely merges 11 cognitive schedules from `cron/jobs.template.json` $\rightarrow$ `~/.hermes/cron/jobs.json` without clobbering user jobs.
3. **Ecosystem Provisioning**:
   - **Profiles** (`profiles/*`) $\rightarrow$ `~/.hermes/profiles/` (`auditor`, `coder`, `default`, `desktop-researcher`, `desktop-worker`, `oracle`, `oracle-researcher`, `personal-organizer`, `planner`, `researcher`). Also ensures `~/.hermes/SOUL.md` is active.
   - **Hooks** (`hooks/*`) $\rightarrow$ `~/.hermes/hooks/` (`brain-cognitive-guard`, `brain-memory-consolidator`, `hermes-visualizer-sync`, `to-do-capture`).
   - **Skills** (`skills/*`) $\rightarrow$ `~/.hermes/skills/` (38+ production skills including `hermes-brain`, `barehands`, `brain-search`, `first-principles`).
   - **Plugins** (`plugins/*`) $\rightarrow$ `~/.hermes/plugins/` (includes `plugins/decision_logger/`).
4. **Upstream Companion Check**: Detects if `../ai-visualizer` or `../barehands` exist and configures non-invasive signal bus ports.
5. **Docker Infrastructure**: If Docker is running, launches the core container stack. The services live in **separate** compose files, so each is started with its own `-f` flag — a bare `docker compose up -d` would only start the dashboard:
   - `brain-postgres` (Port 5433): PostgreSQL 18.6 (ParadeDB) with `pg_search` + `pgvector`
   - `searxng-core` (Port 8080): Sovereign metasearch engine for your Researcher profile
   - `hermes-brain-dashboard` (Port 8088): Command Deck web dashboard & cognitive API

   Container names do not follow the compose service names — see `INSTALL.md` for
   the exact file-to-service mapping.
6. **Automatic Verification**: Executes `python scripts/verify_stack.py` to confirm 10/10 components pass.

---

## 🐳 Step 2: Alternative Execution Modes

If you need a specific deployment profile instead of `--auto`:

| Flag | Purpose | Command |
| :--- | :--- | :--- |
| **Docker Compose** | Run database & dashboard in Docker | `python install.py --docker` |
| **Local Native** | Install Python requirements & run locally | `python install.py --local` |
| **Link Only** | Provision hooks, skills, plugins & profiles without starting server | `python install.py --link-only` |

---

## 🎨 Step 3: Upstream Companion Setup (Optional)

If the user requests the **AI Visualizer** (reactive animated face) or **Barehands 3D** (webcam hand-tracking spatial cards):

1. **Clone companions side-by-side** with `100% untouched upstream code`:
   ```bash
   git clone https://github.com/jaredrhod/ai-visualizer.git ../ai-visualizer
   git clone https://github.com/jaredrhod/barehands.git ../barehands
   ```
2. **Re-run the companion provisioner**:
   ```bash
   python install.py --link-only
   ```
3. **Launch the entire stack unified**:
   ```bash
   python scripts/start_all.py
   # Or on Windows: .\start_all.bat
   # Or on Linux:   ./start_all.sh
   ```

---

## ✅ Step 4: Verification & Acceptance Criteria

Once setup completes, verify your new capabilities by running both test suites:

1. **Stack Health Verification (Must pass 10/10 checks)**:
   ```bash
   python scripts/verify_stack.py
   ```
2. **Cognitive Integration Test Suite (Must pass 12 tests; 1 skips unless the optional companion apps are installed)**:
   ```bash
   python -m unittest tests.test_brain_integration
   ```
3. **HTTP Health Check**:
   ```bash
   curl -s http://localhost:8088/api/health
   # Expected response: {"status":"ok","docker":true,"database":true,"timestamp":"..."}
   ```
4. **Ablation Harness (optional — proves a subsystem earns its cost)**:
   ```bash
   python scripts/ablation_harness.py --load stressed --trials 6
   # Writes docs/audit/ablation-stressed.json
   ```
   Use `--load stressed`. The default `baseline` load fires **no** gates
   and reports `valid: false` on purpose: light-load ablation
   under-reports contribution, so a run of zeros there is a harness
   artifact, not a finding. See
   [`docs/audit/ablation-cortex-pilot.md`](docs/audit/ablation-cortex-pilot.md)
   for the current numbers and what they do and do not license.

---

## 🛡️ Operating Rules for Hermes Agent

Once Hermes Brain is installed, adhere strictly to these core cognitive contracts:
1. **Never search the web directly in Main Hermes**: Always delegate external research queries to your `Researcher` profile via `delegate_task(profile="researcher", ...)`.
2. **Evidence is not belief**: When information from two sources conflicts, record the claim as `DISPUTED` instead of assuming one is true.
3. **Preserve raw evidence**: Never perform destructive summarization. Summaries must live alongside preserved raw historical evidence.
4. **Satisficing stopping criteria**: Know when to stop thinking. Stop and report uncertainty when missing evidence cannot be obtained by another step.
5. **Reality gets the final vote**: Always verify tool execution with empirical state checks or unit tests. Record real-world outcomes in `state.db`.
