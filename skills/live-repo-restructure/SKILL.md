---
name: live-repo-restructure
description: Use when renaming, moving, or deleting paths in a live repo.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, restructure, rename, cron, verification, migration]
    related_skills: [file-ops-safety, repo-pii-scrub, bulk-corpus-remediation]
---

# Restructuring a Live Repo

Renaming, moving, merging, flattening, or dissolving paths in a git repository
that scheduled jobs, services, or agents also write into.

## When to Use

- Renaming or moving a directory a cron job, service, or agent writes into.
- Repo cleanup passes, folder consolidation, renaming tracked output dirs.
- Moving a data root or a service path.

The extra care over ordinary git work is the case where **the checkout is also
a runtime working directory.**

## The rule that governs everything else

**Before moving any path, establish whether anything writes to it at runtime.**

A git checkout is frequently *both* the thing you push to *and* the live
working directory for automation. When that is true, `git mv` on a directory
moves live output, and the next run either recreates the old path, fails
silently, or writes into a directory the repo no longer tracks.

Pre-flight, in order:

1. **Grep the whole tree** — code, config, cron payloads, compose files,
   systemd units, skill files — for the old path. Include the string in its
   split-argument forms; a literal search misses `os.path.join(root, "sub")`.
2. **List the scheduled jobs and services** and read what each one actually
   executes. A job that reads a path is a dependency, not legacy branding.
3. **Establish which tree is authority.** For a repo with a GitHub remote, the
   remote is authority; a home-directory checkout or a stale clone is context,
   never a source of truth to sync to or preserve files for.
4. **Ask before touching a path a running job reads.** Renaming it breaks the
   job for no benefit. Repointing a live job needs explicit authorization;
   moving a file in the repo does not.

## Procedure

① **Inventory the references.** Every occurrence of the old path, with the
file and line. Report the count before changing anything.

② **Classify each reference**: code that must be repointed, config that must be
repointed, documentation that must be updated, and historical records that
must be left alone. Acting uniformly is wrong — a changelog entry naming the
old path is correct history, not a broken reference.

③ **Move, then repoint, then verify — in that order.** Do not repoint before
the move; you cannot prove the new path works until it exists.

④ **Verify from the live side, not the repo side.** Re-run the actual job or
read the actual service state. A clean `git status` proves the repo is
consistent; it does not prove the job still works.

⑤ **Check the old path did not come back.** The classic failure is a job
recreating the directory it used to write to, which then looks like an
unexplained untracked directory in the next run.

## Pitfalls

- **A literal-string search missing a split-argument path.** Search for the
  basename as well as the full path.
- **Treating a live data directory as legacy naming.** If a running job reads
  it, it is a dependency. Renaming buys tidiness and breaks the job.
- **Syncing *to* a stale clone** instead of pulling the authority first.
- **Assuming `git mv` is atomic with respect to running processes.** A process
  holding an open file descriptor keeps writing to the moved inode.
- **Verifying only that the repo is clean.** The runtime is the thing that
  breaks.
- **Untracked output directories reappearing** and being mistaken for a failed
  cleanup.
