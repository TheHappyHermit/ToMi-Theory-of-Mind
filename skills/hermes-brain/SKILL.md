---
name: hermes-brain
description: Sovereign neuro-cognitive engine interface for Hermes Agent. Query working memory (dlPFC), inspect epistemic beliefs & defeater lattices, evaluate Basal Ganglia Go/No-Go action gating, assess somatic risk, and run counterfactual regret rollouts.
---

# Hermes Brain — Sovereign Neuro-Cognitive Engine

Hermes Brain is an advanced neuro-cognitive architecture providing Hermes Agent with persistent, human-like executive function, working memory, emotional/somatic appraisal, and defeasible reasoning.

## Cognitive Subsystems

| Subsystem | Brain Analogue | Function in Hermes Agent |
| :--- | :--- | :--- |
| **Thalamus** | Sensory Buffer & Gate | Filters incoming input, computes saliency score, drops or buffers noise. |
| **Cortex (dlPFC)** | Dorsolateral Prefrontal | Working memory scratchpad (Cowan 4-7 chunks), active goal stack, System 1/2 dual-process routing. |
| **Limbic Engine** | Amygdala & Insula | Cognitive valence (pleasure/displeasure), arousal, Damasio somatic marker risk appraisal. |
| **Basal Ganglia** | Striatum (Direct/Indirect) | Go/No-Go action arbitration, hyperdirect emergency brake, procedural skill compilation. |
| **Hippocampus** | CA3 / CA1 / Subiculum | HippoRAG associative graph, Personalized PageRank, Sharp-Wave Ripple (SWR) replay consolidation. |
| **Epistemology** | Pollock Defeater Lattice | Defeasible belief management, rebutting and undercutting defeater tracking, AGM belief revision. |
| **Default Mode (DMN)** | Precuneus & mPFC | Chronesthesia (mental time travel) and Pearl Level-3 causal counterfactual regret rollouts. |
| **Social Cognition** | Theory of Mind (ToM) | Tracks user beliefs, detects discrepancies with ground truth, Gricean pragmatic implicature decoding. |

---

## API Endpoints Reference

Hermes Brain is exposed via the local Command Deck REST API at `http://localhost:8088/api/brain` (or `$BRAIN_API_URL`).

### 1. Check Cognitive Status
```bash
curl -s http://localhost:8088/api/brain/status
```
Returns telemetry on active goal, working memory slots, limbic valence, hippocampal traces, and grounded beliefs.

### 2. Action Pre-Flight Check (Basal Ganglia Gating)
Before executing a consequential or potentially risky action (e.g. system commands, database modifications, mass deletions):
```bash
curl -s -X POST http://localhost:8088/api/brain/action-check \
  -H "Content-Type: application/json" \
  -d '{"action": "bash", "target": "rm -rf build", "expected_utility": 0.8, "conflict_level": 0.1}'
```
Returns:
- `decision`: `"GO"`, `"NO_GO"`, or `"HYPERDIRECT_BRAKE"`
- `net_drive`: Float drive score (>= 0.4 allows execution)
- `somatic_bias`: Prior risk penalty from past failures
- `somatic_warning`: Human-readable advisory if past failures occurred

### 3. Record Action Outcome (Reinforcement)
After executing any consequential tool or action:
```bash
curl -s -X POST http://localhost:8088/api/brain/action-outcome \
  -H "Content-Type: application/json" \
  -d '{"action": "bash", "target": "build", "success": true, "surprise_score": 0.1}'
```
Reinforces somatic markers, updates allostatic load, and records an episodic trace in the hippocampus.

### 4. Manage Working Memory Goal
When the user gives you a complex, multi-step objective:
```bash
curl -s -X POST http://localhost:8088/api/brain/working-memory/goal \
  -H "Content-Type: application/json" \
  -d '{"goal": "Refactor database migration", "sub_goals": ["audit schema", "write script", "verify"]}'
```

### 5. Grounded Epistemic Beliefs
Retrieve verified claims or record new defeasible beliefs:
```bash
# Query grounded beliefs
curl -s "http://localhost:8088/api/brain/beliefs?topic=deployment"

# Record a new belief
curl -s -X POST http://localhost:8088/api/brain/beliefs \
  -H "Content-Type: application/json" \
  -d '{"topic": "deployment", "statement": "Port 8088 is allocated to Dashboard", "credence": 1.0, "provenance": "user"}'
```

### 6. Causal Counterfactual Regret Analysis
When an operation fails or produces an unexpected outcome:
```bash
curl -s -X POST http://localhost:8088/api/brain/counterfactual \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_event": "Database connection timeout",
    "actual_path": "Retried immediately without checking service status",
    "counterfactual_path": "Checked docker service status and inspected healthcheck first",
    "predicted_advantage": "Would have avoided 3 cascading timeout errors",
    "lesson_extracted": "Always verify service health before re-triggering network calls"
  }'
```

---

## Repo Install Path — NEVER run it as a test

`install.py`, `setup.sh` and `start_all.sh` in this repo are **not
side-effect-free**. Running one to "see if it works" provisions the live
environment:

- They convert `~/.hermes/{skills,profiles,scripts,hooks,plugins}` entries from
  real directories into **symlinks pointing at wherever the repo was cloned
  from**. Test from a scratch clone and you have silently re-pointed ~160 live
  components at a throwaway directory. Deleting that clone then breaks every
  one of them — the symlink still exists, but `Path(p).exists()` is False and
  `verify_stack.py` reports skills missing.
- They start real services (they bind ports; 8088 collides with the live
  dashboard).
- The first run creates `~/.hermes/backups/install-<ts>/`.

To check an install-path change, read the code and exercise the *pure* pieces
in isolation — `argparse` definitions, path resolution — never the script. If
a clone is unavoidable to test a mode flag, clone with `git archive` piped
into a throwaway directory rather than `git clone`, and **never** invoke
anything from inside a test clone: `./setup.sh` and `./start_all.sh` both
provision, so testing them in a clone is what re-points live components at
it. Run installers only from the real repo checkout.

Audit afterwards — read-only, in Python, never `find | sh`:

```python
import os, pathlib
home = pathlib.Path.home() / ".hermes"
for sub in ("skills", "profiles", "scripts", "hooks", "plugins"):
    d = home / sub
    if not d.is_dir():
        continue
    for c in list(d.iterdir()) + [
        s for cat in d.iterdir() if cat.is_dir() and not cat.is_symlink()
        for s in cat.iterdir()
    ]:
        if c.is_symlink():
            if "cache/scratch" in os.readlink(c):
                print("STALE:", c, "->", os.readlink(c))
            if not c.exists():
                print("BROKEN:", c)
```

Match on the scratch path specifically, not the substring `clone` — a
legitimate clone directory name will otherwise trip it, and matching too
broadly against every symlink in `~/.hermes` floods the output with
thousands of valid relative links in `node_modules/` and `terminfo/`.

`install.py` now refuses to provision at all when no Hermes Agent harness is
present, so a clean machine fails loudly instead of appearing to succeed.
`--local` is exempt by design.

---

## Agent Operational Protocol

1. **Passive Consciousness**: The `brain-cognitive-guard` and `brain-memory-consolidator` hooks automatically monitor your execution steps and record outcomes in the background.
2. **Consult Before Consequential Changes**: When about to execute high-impact modifications, run an action-check to verify that somatic markers or active conflicts do not advise against it.
3. **Learn from Surprises**: Whenever an unexpected result occurs (high surprise score), record a counterfactual lesson so future decisions benefit from the experience.
