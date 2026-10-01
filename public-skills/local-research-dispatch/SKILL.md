---
name: local-research-dispatch
version: 2.0.0
description: >-
  Use when dispatching multi-topic web research to local GPU profiles. Camofox-first
  tool chain, compaction-safe batching, and the correct wiki destination.
---

# Local Research Dispatch

> **Status: partially retired (2026-09-30).** Rewritten after an audit found
> that this skill's dispatch target, its orchestrator, and both of its
> reference files no longer exist. What is verified current is marked
> **LIVE**; what is not is marked **GONE** and must not be followed. Read the
> marked sections, not the original text.

## GONE — do not follow

- **The `desktop-researcher` profile does not exist as a live profile.** It
  survives only as a repo copy at `profiles/desktop-researcher/SOUL.md`, with
  no `~/.hermes/profiles/desktop-researcher/` directory and no cron job bound
  to it. Any command naming it will fail.
- **`research_batches.sh` does not exist.** The batch orchestrator this skill
  used to point at is gone from `~/.hermes/scripts/`. Batch chaining is
  currently done by hand, one completion at a time.
- **`references/web-tool-chain.md` and `references/batch-mode-research.md` do
  not exist.** The tool chain below is inline here because of that, not
  because the files moved.

The verified inference endpoint is gone too: `{LAN_IP}:1234` has no
connections, so the `ss` check in the original skill would silently pass its
"use the right profile" test while proving nothing.

## Which profile to dispatch to — LIVE

The live research profiles, all under `~/.hermes/profiles/`:

| Profile | Destination | Use for |
| :--- | :--- | :--- |
| `researcher` | `${HERMES_HOME}/active-wiki/research/` | What the operator asks for on demand, filed beside his own notes |
| `3090-researcher`, `5060-researcher` | `${HERMES_HOME}/active-wiki/research/` | Pinned to separate GPU endpoints so lanes run in parallel |
| `google-researcher`, `openrouter-researcher` | `${HERMES_HOME}/active-wiki/research/` | The Online Lane A/B cron jobs |
| `oracle-researcher` | `${HERMES_HOME}/oracle/brain/` | Feeding the research corpus directly |

`delegate_task` has no `profile` parameter and silently ignores one — verified
2026-08-25: `profile="researcher"` was accepted and ignored, and the subagent
ran on the parent model. Dispatch a pinned profile by shelling out:

```bash
cd "${HERMES_HOME:-/home/{USER}}" && hermes --profile 3090-researcher chat -q \
  "$(cat /tmp/task.txt)" > "${HERMES_HOME}/logs/research-batchN.log" 2>&1
```

Launch with `terminal(background=true, notify_on_complete=true)` and chain
batches manually on completion. Auto-chaining across a compaction boundary is
not possible.

## Output destination — LIVE, and corrected

This section was **backwards** before 2026-09-30. It said dashboard research
must never enter the Oracle. In fact `oracle/brain/dashboard-research/` already
held 18 finished pages, and the 09-28 decision puts long-form research in the
Oracle. The corrected rule:

- **Dashboard / agent-design research → `${HERMES_HOME}/oracle/brain/dashboard-research/`**
  Already populated (18 files, ~98 KB). Extend it; do not start a parallel tree.
- **Entity profiles / domain topics → `${HERMES_HOME}/oracle/brain/`**
- **On-demand research the operator asked for → `${HERMES_HOME}/active-wiki/research/`**
  This is the one exception, and it exists because the operator wants that research
  read together with his own notes. The split is deliberate; do not "fix" one
  destination into the other.

Confirm the destination per task rather than assuming. The previous version's
`active-wiki/dashboard-research/` never existed on disk.

## Web tool chain — Camofox-first (MANDATORY)

the operator's explicit rule (2026-08-26): curl is the LAST resort, not the default.
This is the rule that still stands, and it is baked into the researcher
profiles' SOUL.md rather than re-instructed per batch.

1. **Camofox** browser tool `http://127.0.0.1:9377` — PRIMARY. Navigate and READ pages.
2. **Firecrawl** `POST http://127.0.0.1:3002/v1/scrape` body `{"url":"U","formats":["markdown"]}`
3. **SearXNG** `GET http://127.0.0.1:8080/search?q=Q&format=json` (local metasearch)
4. **Tavily** — DISABLED this month (quota out). DO NOT USE.
5. **curl** raw fetch — LAST RESORT ONLY.

Never use `web_search` / `web_extract` (external internet) for these
local-stack tasks.

## Batch mode — survive compaction — LIVE

A single `chat -q` with a huge prompt dies at the context-compaction boundary
(~22 min / ~59 msgs observed: clean exit, no follow-up, silent incomplete). So:
split into small batches (≤6 services each) that each finish and write their
file inside one context window, then launch the next. Chain them by hand.

**Verify each batch actually ran** — a clean exit is not proof of output:

```bash
# the file must exist on disk, and be newer than the launch
ls -l "${HERMES_HOME}/oracle/brain/dashboard-research/<name>.md"
```

Self-report is not proof. A research lane that wrote nothing and said it did is
worse than one that failed loudly.

## Pitfalls

- **Dispatching to `desktop-researcher`** — the profile is gone. Pick from the
  live table above.
- **Following this skill's old destination rules** — they were inverted. The
  Oracle is where dashboard research goes.
- **One-shot `chat -q` dies at compaction** — use small batches.
- **curl-first output** — a regression of the Camofox rule; re-affirm the chain.
- **Two heavy GPU jobs at once** — running two research profiles simultaneously
  saturates the 3090. One at a time.
- **A retired data root in a path** — `.project` was retired in `4584b8b`.
  Any command still naming it writes into a directory that does not exist and
  fails silently rather than loudly. See the fixed paths above.
