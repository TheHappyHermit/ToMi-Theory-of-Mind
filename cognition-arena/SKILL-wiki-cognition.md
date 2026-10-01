# SKILL-wiki-cognition — moved

**The canonical skill is `skills/wiki-cognition/SKILL.md` in this repository.**

This file used to hold a second copy of the skill. It was deleted and replaced with
this notice on 2026-09-26, because the copy was pre-split: it described rewriting
`ARENA.md` in place, with no `ARENA-EVIDENCE.md` and no `RUNLOG.jsonl`. A job or
person reading it would have re-created the accretion problem the split exists to
prevent. Two copies of the same instructions, one of them wrong, is worse than one.

**It is already installed.** `install.py` symlinks every `skills/*/SKILL.md`
into `~/.hermes/skills/`, so the canonical copy at `skills/wiki-cognition/SKILL.md`
*is* the installed one. There is no second file to keep in step with it.

The previous contents are recoverable from git at any commit before
`bb607aa` — `git show bb607aa^:audit/fullread/SKILL-wiki-cognition.md`.

**Do not recreate this file as a copy.** If the skill changes, change
`skills/wiki-cognition/SKILL.md` and re-run the installer. One source, one copy.
