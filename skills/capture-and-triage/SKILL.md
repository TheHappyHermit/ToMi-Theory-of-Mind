---
name: capture-and-triage
description: Triage incoming content to wiki, db, or discard.
---

# Capture and Triage

Handle all incoming content (Telegram messages, Discord messages, voice notes, images, files, links, Web Clipper captures, email forwards) through a single triage workflow.

## Where findings go — the scratchpad is OURS, not the operator's

`~/hermes-brain/SCRATCHPAD.md` is the **agent's** working pad. the operator's ruling
(2026-09-30): "There should never be any notes for me in the scratch pad.
Those are for you. My to-do is go on my to-do list and organizer.db."

- **Agent-owned findings** → write them to the scratchpad yourself. That is
  what it exists for: surviving context resets, carrying forward what was
  learned.
- **Anything that is a task for the operator** → his to-do list or `organizer.db`
  (`~/.hermes/personal-organizer/data/organizer.db`, `tasks` table). Note
  `~/organizer.db` is a 0-byte decoy, not the live database.
- **Never** stage work for his decision, and never emit "Candidate for
  SCRATCHPAD (not written)" or any equivalent. A finding is either ours to do,
  or already in his task system. A report that ends with a list of items
  awaiting his approval is a failure, not a handoff.

## Workflow

1. **Receive input** — Determine source channel (Telegram, Discord, Web Clipper, file, voice note, email).

2. **Classify input** as one of:
   - ordinary conversation
   - personal fact
   - preference
   - idea
   - decision
   - project update
   - task
   - deadline
   - waiting item
   - troubleshooting observation
   - purchase research
   - raw source
   - question to revisit

3. **Apply writeback check**:
   - Did the user state a durable personal fact?
   - Did the user state an explicit preference?
   - Did a decision become final?
   - Did a commitment, task, deadline, or waiting item emerge?
   - Did a project state change?
   - Did a test produce a verified result?
   - Did an approach fail in a reusable way?
   - Would losing this information cause future rework?

   If all answers are no, do not write anything.

4. **Route classified content**:
   - **personal fact** → Update or create page in Active Wiki (`~/.hermes/active-wiki/10_Self/`)
   - **preference** → Update `system/core-preferences.md` or relevant page
   - **decision** → Create page in `active-wiki/10_Self/decisions/` folder
   - **task/deadline/waiting item** → Add to `organizer.db` via `organizer-state` skill
   - **project update** → Update existing project page in `active-wiki/30_Projects/`
   - **troubleshooting** → Update project page or create troubleshooting record
   - **purchase research** → Add to `active-wiki/10_Self/purchases/` folder with dated prices
   - **raw source** → Save to `~/.hermes/exchange/raw/YYYY/MM/` with metadata frontmatter
   - **idea** → Add to `active-wiki/10_Self/ideas/` folder
   - **question** → Add to `active-wiki/10_Self/questions/` folder
   - **specialist reference** (technical, factual, domain-specific) → Route to Oracle Vault (`~/.hermes/oracle/brain/`) via library-onboarding skill

5. **Raw source captures** must include:
   ```yaml
   ---
   source_id: unique-stable-source-id
   capture_channel: telegram|discord|web-clipper|email
   captured_at: full-timestamp
   source_url:
   title:
   author:
   published:
   content_type:
   content_hash:
   why_saved:
   ---
   ```

6. **Record in organizer.db** — Add source record, mark processing status, update `log.md`.

7. **Support natural overrides**:
   - "Remember this" → Force save to appropriate location
   - "Capture this" → Save as raw source
   - "Add this to the project" → Route to specific project
   - "This is only a hypothesis" → Mark as hypothesis, do not save as fact
   - "Do not save this" → Discard
   - "Research this deeply" → Create research request
   - "Ask Oracle" → Route to Oracle profile

## Raw Source Ingestion Limits

- Update no more than 3 durable personal pages
- Create no more than 1 new durable page
- Exceed these limits only when the source genuinely requires it and record why

## Raw Source Processing

1. Detect new raw files in `~/.hermes/exchange/raw/`
2. Compute and store content hash
3. Reject or flag duplicates
4. Read Active Wiki schema, index, and recent log
5. Find relevant existing pages
6. Determine whether source adds durable information
7. Update existing page before creating new page
8. Preserve provenance
9. Create review items for conflicts or uncertainty
10. Append concise entry to `log.md`
11. Mark source processed in `organizer.db`
