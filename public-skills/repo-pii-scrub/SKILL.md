---
name: repo-pii-scrub
description: Use when scrubbing PII and secrets from a git repo.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, github, security, pii, secrets, history-rewrite, git-filter-repo]
    related_skills: [github-workflow, github-repo-management, file-ops-safety, asset-migration]
---

# Repo PII Scrub & History Sanitization

Making a repository safe for public release: removing PII and secrets from both
the working tree **and** the full git history. A clean working tree with a dirty
history leaks just as badly — the blobs are still fetchable.

## When to Use

- Publishing a repo publicly, or adding a public remote.
- Real usernames, API keys, bearer tokens, SSH keys, hostnames, or internal
  IPs in tracked files or commit messages.
- As a routine gate before any push to a public remote.

## Prerequisites

- `git`; `git-filter-repo` (`pip install git-filter-repo`) for the history pass.
- Write access to the remote.
- A clean working tree, or an explicit stash/commit decision.
- **The user has explicitly authorized the destructive history rewrite.**
  `git filter-repo`, `reset --hard`, and force-push are all destructive; ask
  first, every time, even when the scrub itself was requested.

## Phase 1 — Working tree (non-destructive)

### 1.1 Inventory before changing anything

```bash
# The author's own name / handle
git grep -n "AUTHORNAME" 2>/dev/null || echo "CLEAN"

# Home paths, LAN addresses, hostnames
git grep -nE "(/home/[a-z0-9_-]+|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})" || echo "CLEAN"

# Credential-shaped strings
git grep -nE "(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9_+/=-]{20,})" \
  | grep -vE "CHANGE_ME|placeholder|example|YOUR_|xxx|sk-xxx|ghp_xx" || echo "CLEAN"

# Private keys
git grep -nE "(PRIVATE KEY|BEGIN (RSA|EC|DSA|OPENSSH) KEY|ssh-rsa|ssh-ed25519)" || echo "CLEAN"
```

Also check **filenames and paths** — a file named after a machine or a person
leaks as surely as its contents. And check **`.gitignore` before committing**,
not after: an untracked-but-present secret still reaches anyone with a copy of
the directory.

### 1.2 Parameterize, do not delete

Replace a machine-specific value with an environment variable or a documented
placeholder, and update the code that reads it. Deleting the value leaves a
broken reference; a placeholder plus a lookup leaves working software that
travels.

Fix `.gitignore` **before** the commit so the scrubbed patterns do not return
in the next commit.

### 1.3 Verify phase 1

Re-run every inventory command against the working tree. Confirm each returns
CLEAN. Then confirm the code still runs — a scrub that breaks the build is not
finished.

## Phase 2 — History rewrite (destructive)

1. **Back up a bare clone** of the full history somewhere outside the working
   tree. This is the only undo.
2. Write a replacement file mapping each secret to its replacement. Use exact
   literal matches; a loose regex can rewrite unrelated text.
3. Run `git filter-repo --replace-text` with that file.
4. **Scrub commit messages too** — author/committer names and emails are in
   every commit object. `--mailmap` for identities; replace-text for message
   bodies.
5. Re-add the remote and verify history length, tree contents, and authorship.
6. Force-push, only with explicit authorization.
7. **Verify the remote**, not the local clone: `git ls-remote`, a fresh clone
   into a temp dir, and a re-run of the inventory against that fresh clone.

## Identity on public repos

Public repos carry exactly one identity. A noreply address is the right choice
for the publishing account. Check authorship before pushing from any clone:

```bash
git log --format='%an <%ae>' | sort -u
```

Personal email addresses and secondary identities must not appear anywhere in
history — including in the committer column, which `git log --format='%an'`
alone will not show.

## Pitfalls

- **Verifying the local clone only.** The local tree is clean by construction;
  the remote is the artifact that matters.
- **Forgetting commit messages and author metadata.** The most common miss.
- **Regex where literals belong.** Over-broad replacement damages unrelated
  content and is hard to audit.
- **No backup before rewriting.** `filter-repo` is not undoable in place.
- **Force-pushing without asking.** Destructive, remote-visible, and explicitly
  gated on authorization.
- **Purging history when a fresh start was meant.** If the goal is simply "no
  PII in the public repo", a fresh public repo with a clean first commit is
  safer than a rewrite. Offer both.
- **Treating `.gitignore` as retroactive.** It only affects uncommitted files.
- **Leaving the clobbered artifact deleted.** If a scrub damaged a working
  file, preserve the damaged copy for inspection before restoring.

## Verification checklist

- [ ] Working tree: every inventory command returns CLEAN
- [ ] Filenames and paths contain no machine or person identifiers
- [ ] `.gitignore` updated, and the build still runs
- [ ] Commit messages and author/committer identities scrubbed
- [ ] Bare-clone backup exists and its location is known
- [ ] Fresh clone from the remote re-verified
- [ ] `git log --format='%an <%ae>' | sort -u` shows only the publishing identity
- [ ] Destructive step authorized by the user at the time it was run
