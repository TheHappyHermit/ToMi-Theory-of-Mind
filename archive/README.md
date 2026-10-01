# archive/ — kept on disk, out of git, recoverable

## What this is

the operator, 2026-09-28: "let's create an archive file that is git ignored and
move them into the archive file so that you don't get confused by them.
Later on accident we get to see if anything breaks without them and we
have them backed up just in case."

So nothing here is deleted. It is all on disk at the same path, just not
tracked. If something turns out to be load-bearing it can be moved back
and committed with no data loss.

## strays-2026-09-28/

| file | size | what it is |
|---|---|---|
| `file:p229?mode=memory&cache=shared` | 0 | Empty. A shell redirect wrote to a literal filename — `?mode=memory` was a query string that some tool treated as a directory. |
| `file:probe229?mode=memory&cache=shared` | 0 | Same bug, second attempt. |
| `SCRATCHPAD.md.bak.sleeptime` | 0 | Empty backup, superseded. |
| `research-resultideas.md.bak.sleeptime` | 34 KB | Real backup of `research-resultideas.md`. That file is already ignored under an earlier decision, and its history is tracked, so this copy is redundant. |
| `smoke_test_web_stack.sh.bak.job2` | 12 KB | Real backup of a tracked shell script. Point-in-time copy. |

None of these are read by any script. Verified by grep across `*.py`,
`*.sh`, and `cron/jobs.template.json` before moving.

## What is deliberately NOT in here

**`schemas/okf-queue.jsonl` (1.2 MB, 4,401 lines) is ignored in place, not
archived.** It looks like a stray but it is live state:

- `scripts/okf_repair.py` reads it at a fixed path (`QUEUE_DEFAULT`)
- a paused cron job reads it at that same path
- its newest entry is 2026-09-28T20:21:09Z, so it is being written today

Moving it would break both consumers for no benefit. The linter
regenerates it, so it does not belong in git — but it belongs on disk
where it is.

## The .gitignore rule

`archive/` was already ignored by a broad entry long before this archive
existed. The one addition is a tracked explanation of why, so the rule is
self-documenting in the repo rather than only in someone's memory:

    !archive/
    archive/**
    !archive/README.md

`archive/*` cannot be used for this. It would also match the
subdirectory and stop git descending, so the negation could never match
anything. `archive/**` ignores directory *contents* while leaving the
directory itself visible, which is the form that works.
