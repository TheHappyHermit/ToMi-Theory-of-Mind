---
name: large-repo-git-workarounds
description: Workarounds for git operations that timeout on large repos. Copy files directly to target repo when git commands hang.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Large Repository Git Workarounds

**When to use:** When git operations (`git status`, `git fetch`, `git pull`, `git merge`, `git push`) timeout or hang on very large repositories (e.g., `~/.hermes` with 200k+ files).

## Problem

Large Hermes data roots — `.hermes`, and the retired `.project` it replaced — often
have so many files that standard git commands timeout:
- `git status` — hangs scanning 200k+ files
- `git pull` — hangs on fetch + merge
- `git merge --allow-unrelated-histories` — hangs on merge
- `git push` — hangs on upload

## Workaround: Direct File Copy + Target Repo Commit

When git operations timeout, use direct file copy into the target repository:

```bash
# 1. Copy changed files from source to target repo
cp /home/{USER}/.hermes/scripts/check_project_dbs.py \
   /home/{USER}/other-repo/scripts/check_project_dbs.py

cp /home/{USER}/.hermes/cron/jobs.json \
   /home/{USER}/other-repo/cron/jobs.json

# 2. Commit and push from target repo
cd /home/{USER}/other-repo
git add scripts/check_project_dbs.py cron/jobs.json
git commit -m "rename: replace 'cortex' with 'project'"
git push origin main
```

This bypasses all git operations on the source repo entirely.

## Pattern: Checkpoint/Config Migration

When migrating config/state files from a renamed repo:

```bash
# Copy all changed files at once
for f in scripts/check_project_dbs.py config.yaml cron/jobs.json \
         checkpoints/store/projects/*.json pending/skills/*.json; do
    cp "/home/{USER}/$f" "/home/{USER}/other-repo/$f"
done

# Verify what's staged
cd /home/{USER}/other-repo
git status --short
```

## Remote URL Migration

When GitHub accounts change (e.g., `{USER}` → `TheHappyHermit`):

```bash
cd /path/to/repo
git remote set-url origin https://github.com/NewAccount/repo.git
git remote -v  # verify
git push origin main
```

## When NOT to Use Workaround

- Small repos (< 10k files): use normal git commands
- When you need to pull remote changes: fetch first, then copy merged state
- For `other-repo` repo specifically: it's clean and small enough for normal operations

## Pitfalls

- **Don't copy entire `.hermes/` directory** to `other-repo/` — only copy changed files
- **Verify file contents before committing** — a copy mistake won't be caught by git
- **Clear stale git errors** on cron jobs after fixing: set `last_error` and `last_status` to `None` in `jobs.json`
- **Unrelated histories**: if repos share a root commit but diverged, `--allow-unrelated-histories` merge can hang — use file copy instead

## References

- `references/large-repo-cron-push.md` — transcript of the `.hermes` → `other-repo` push with timeout issues