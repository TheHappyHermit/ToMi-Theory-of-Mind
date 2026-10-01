# Stale third vault — diffed, and the answer is "duplicates, leave alone"

Written 2026-09-28. Owner asked for a content diff of the 381 files against
the live vault, and for anything novel to be moved into the Oracle vault.

## Verdict: 0 novel. Nothing to move. Leave the whole directory alone.

```
381 files in /home/operator/personal-agent/oracle/brain
  380  present at the same relative path in the live Oracle vault
    1  no same path, but its title matches a live article
        (Visual-Cortex-Hierarchy.md -> Visual-Autognosia-Hierarchy.md)

of the 380 same-path files, comparing BODIES (frontmatter excluded, because
generated/verified timestamps differ between pipelines and would make every
file look different):
    98  body identical
  233  stale is an OLDER version of the live file
    0  live is an older version
   49  diverged in size
```

**No file contains knowledge the live vault lacks.** The 49 "diverged" files
are all cases where the stale copy is *older* and the live copy is *longer* —
more content, not less. The only substantial text unique to the stale copy is
in `index.md`, which is a 2026-08-12 directory listing that has since been
replaced by a shorter, current one.

## The reason this matters, and it is not the diff

While diffing, the stale files showed corrupted anatomy:

> "the cerebral **autognosia** is a massively parallel array of similar..."
> "The Somatosensory **Autognosia** — Mapping the Hand Area"
> "**Visual Autognosia** Hierarchy"

A retired-name replacement had run over file **content**, not just paths.
`cortex` had become `autognosia`.

I checked both live vaults immediately, because if this had reached them it
would be a serious knowledge-base defect.

**It did not reach them.** Measured with literal anatomy phrases only (a
first pass using "any anatomy word within 70 characters" over-counted badly,
because most `autognosia` occurrences are legitimate references to the
retired *project*):

| Vault | literal bad phrases | files |
|---|---:|---:|
| **LIVE oracle** | 31 | 27 |
| **LIVE active** | 15 | 14 |
| **STALE third** | **837** | **138** |
| backup `bak_autognosia` | 25 | 22 |

**All 46 in the live vaults are `"in the autognosia"`** — verified by sampling
each one, and every sample is a legitimate reference to the retired project
(*"the existing corpus in the Autognosia brain..."*). The live vaults are
**clean**.

## One real defect in the live vault, and it is a rename, not corruption

Six occurrences, all in one article:

```
Visual-Autognosia-Hierarchy/Visual-Autognosia-Hierarchy.md
  "V1 (Primary Visual Autognosia, Brodmann area 17)"
  "Predictive Coding in Visual Autognosia"
  id: visual-autognosia-hierarchy
```

That article should be **`Visual-Cortex-Hierarchy`** — and the correctly
named version **exists, in the stale vault**:

```
personal-agent/oracle/brain/Visual-Cortex-Hierarchy/Visual-Cortex-Hierarchy.md
```

So the corruption ran in the stale vault *before* the snapshot, and the
snapshot then carried the renamed article into the live vault via the KB
ingest (`d56ce52`, "Ingest agent-zero KB snapshot (305 reference pages)").

**This is the one item worth acting on, and it is a Phase-0 rename in the
handoff prompt, not a mass find-and-replace.** A blanket replacement of
`autognosia` → `cortex` across the corpus would be actively harmful: it would
destroy every legitimate reference to the retired project, of which there are
thousands. Only the 6 occurrences inside this one article, plus the 1
cross-reference from `Population-Coding-Direction-Tuning-Curves.md`, are wrong.

## The decision record explains the intent

`decisions/2026-09-26_autognosia-name-retired.md` (present in both live
vaults) records the owner's instruction: the name is retired, everything
carrying it is renamed to what it actually does, and the old directory is
renamed rather than deleted so that *surviving references fail loudly instead
of silently reading stale data*.

The author's stated principle — "I want to see things fail if they're going
to fail rather than to be fooled that things are working" — is the reason
this prompt is explicit about which directories are live. A directory that
resolves but holds stale data defeats exactly that intent.

## What the handoff prompt does with this

- The 381 files are **listed as OFF-LIMITS**. Not read for content to import,
  not used as a reference, not copied.
- The one genuine defect (`Visual-Autognosia-Hierarchy`) is a named,
  file-specific rename in Phase 0, with the correctly-named source identified.
- organizer.db **task 43** already tracks the directory. Recommendation
  stands: rename it to something unmistakable rather than delete it, because
  the 381 files have now been verified to contain nothing unique, but a
  future run should not have to repeat this diff to know that.
