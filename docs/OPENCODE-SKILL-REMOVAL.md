# OpenCode skill removed

Date: 2026-09-26

## What was removed

The `opencode` **skill** is gone. It existed in 8 places, one per skill tree:

```
~/.hermes/skills/autonomous-ai-agents/opencode/SKILL.md
~/.hermes/profiles/{oracle,planner,coder,auditor,research}/skills/autonomous-ai-agents/opencode/SKILL.md
~/.hermes/hermes-agent/skills/autonomous-ai-agents/opencode/SKILL.md
~/.hermes/research/skills/autonomous-ai-agents/opencode/SKILL.md
~/.hermes/oracle/skills/autonomous-ai-agents/opencode/SKILL.md
```

It was never tracked in this repository, so no repo file was deleted for it.

## What was NOT removed

**The `opencode` CLI is still installed** at `~/.npm-global/bin/opencode`. The skill was
documentation about how to drive that binary; the binary itself is a separate tool and
several unrelated skills still reference it correctly:

- `skills/dashboard-development/` — a debugging recipe for when `opencode` hangs on
  terminal I/O, and `references/opencode-briefing.md`
- `skills/devops/troubleshoot-failed-cronjob-external-deps/` — where OpenCode stores
  per-provider API keys
- `skills/git-hygiene/references/gitignore-audit-checklist.md` — lists `.opencode/`
  among things to ignore

Do not "clean up" these. They are about the tool, not the skill, and they are still
correct. If the CLI is ever uninstalled, these become the things to revisit.

## Dangling `related_skills` pointers

35 `SKILL.md` files across the profile trees carried `opencode` in their
`related_skills` frontmatter, pointing at a skill that no longer exists. All 35 were
rewritten to drop only that entry; every other entry was preserved:

```
before:  related_skills: [claude-code, codex, opencode]
after:   related_skills: [claude-code, codex]
```

Each edited file was backed up before the change. Verified afterwards: 35/35 lists
parse, 35/35 are non-empty. (A skill whose list was *only* `opencode` would have been
left with `[]`; none were — the `[]` lists elsewhere in the tree predate this change.)

## Cron

No cron job referenced the skill. Checked all 50 jobs in `~/.hermes/cron/jobs.json`:
zero matches.

The three copies of `scripts/opencode_idle_graphify_watch.py` — which watches for the
opencode *process* — are not referenced by any cron job or shell script, and were left
in place rather than deleted. They are inert without a scheduler entry.

## Restore

Everything deleted or edited is backed up under:

```
~/.hermes/cache/scratch/migration-backup-20260926/removed-opencode/
├── skills/                 8 SKILL.md copies, byte-identical
├── related-skills/         35 SKILL.md copies, pre-edit
└── watcher/                3 opencode_idle_graphify_watch.py copies
```

## Health after removal

- `verify_stack.py` — 10/10 (was already 10/10; opencode was never in the expected set)
- skill validation — 14/14
- `python3 -m unittest discover -s tests` — 410 pass, 1 skipped
