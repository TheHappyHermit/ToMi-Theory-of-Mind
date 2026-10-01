# AGENTS.md — read this first

This file is the map for any agent working in this repo. It answers the
question that actually costs time: **what am I allowed to use, and where
does each kind of thing go?**

## The scratchpad — you have one, use it

**`~/hermes-brain/SCRATCHPAD.md`** (untracked, gitignored — it is yours, not
the repo's).

It is a throwaway working pad, the equivalent of the paper notepad beside a
project. Write in it freely when it helps:

- notes on what you are reading
- where you are in a long document, so a fresh agent can resume
- state you need to hold mid-task
- half-formed ideas, scratch arithmetic, dead ends
- **checklists for the job in front of you**

**Empty it when you start a new project, and keep nothing long-term in it.**
It is not storage. Before reusing it for new work, clear the previous
project's entries — the header is a template, the sections are yours to
reuse or delete.

Use it when it is useful. Ignore it when it is not. Nothing in it is
required, and nothing in it is permanent.

If a finding is worth keeping beyond the project, it goes in the repo, the
wiki, or git — not the pad.

## Where things go

| Thing | Destination |
|---|---|
| Your working notes, mid-task state, checklists | `SCRATCHPAD.md` (above) |
| Research findings for the brain project | `research-agenda-brain-architecture.md` (in `$HOME`, not this repo) |
| Per-batch research deliverables | `~/.hermes/oracle/brain/research/` |
| the operator's tasks | his to-do list and `~/.hermes/personal-organizer/data/organizer.db` (`tasks` table) |
| Code, tests, docs | this repo |

**Never leave work for the operator in the scratchpad, and never end a report with
items "awaiting the operator's decision."** That is retired behaviour. A finding is
either yours to act on, or already captured in the agenda. His tasks live in
his task system; `~/organizer.db` is a 0-byte decoy, and
`~/.hermes-cortex/personal-state/` no longer exists.

## The live data root

Everything moved from `~/.hermes-cortex/` to `~/.hermes/` on 2026-09-29. The
cortex path is dead — skills that still reference it were looking at a
graveyard of 3 orphaned files instead of the real 223-file wiki.

| Live | Retired — do not use |
|---|---|
| `~/.hermes/active-wiki/` | `~/.hermes-cortex/active-wiki/` |
| `~/.hermes/oracle/` | `~/.hermes-cortex/oracle/` |
| `~/.hermes/personal-organizer/` | `~/.hermes-cortex/personal-state/` |
| `~/.hermes/exchange/` | `~/.hermes-cortex/exchange/` |

## Publishing changes back here

The live copies live outside the repo, so a local edit does not reach GitHub
on its own. Two commands, both fail-closed and both scrubbed:

```bash
python3 scripts/publish_profiles_and_skills.py --check   # drift report
python3 scripts/publish_profiles_and_skills.py           # publish skills + profile SOULs
python3 scripts/sync_skills_to_repo.py --check           # public-skills drift
```

`SOUL.md` at the repo root is a **selectively published** copy of
`~/.hermes/SOUL.md` — not a mirror, and deliberately not kept in sync by
any command. the operator curates what goes in: the live file carries material
that is private to this machine, so the published copy is scrubbed with
`scrub()` in `scripts/config_backup_scrubbed.py` and then chosen by hand.

**Do not regenerate it wholesale from the live file.** Publishing a section
is the operator's call, not a sync side effect. If a live ruling should be
published, ask him which parts. To see what has drifted since the last
publication, diff the scrubbed live file against the repo copy and *report*
the difference — do not resolve it by overwriting.

## Before you commit

- Repo is **public**; PII is strictly forbidden.
  Commit identity is `TheHappyHermit <260156429+TheHappyHermit@users.noreply.github.com>`.
  Check `git log --format='%an %ae'` before pushing.
- `SCRATCHPAD.md` must never be committed. It is gitignored on purpose.
- One git operation per terminal call — bundling trips the consent gate.
- Never pass `--force` to a scheduled graphify extract.
