# The 689 citation markers — what they are, so a scope decision can be made

Written 2026-09-28. Measured read-only; nothing was changed. No prompt has
been written yet, per the owner's instruction to settle this first.

## The one-sentence version

They are **real academic citations written with `[[n]]` instead of `[n]`**.
The reference each number points to usually exists in the same file. So this
is a *formatting* defect, not missing knowledge — with a small tail of
genuinely unresolvable ones that need a human or an agent to read the prose.

## What they actually are

Anatomy of one, from
`Memory-Architecture/Chronotopic-Sequence-Representation-Cortex.md`:

```
L31  The principle of **chronotopic organization** posits that the
     cerebral cortex is systematically arranged along a gradient of
     temporal receptive window ... [[7]]
...
     References
     [[15]] Rothschild, G., Eban, E., & Frank, L. M. (2017). A cortical-
            hippocampal-cortical loop...
     [[16]] Howard, M. W., & Kahana, M. J. (2002). A distributed
            representation of temporal context...
     [[17]] George, D., & Hawkins, J. (2009). Towards a mathematical
            theory of cortical micro-circuits...
```

`[[7]]` in the prose is a footnote pointer. The reference list at the bottom
is *itself* written as `[[15]]`, `[[16]]`, `[[17]]`. Both halves use wikilink
syntax for what is an ordinary numbered citation. The linter is correct that
these are not wikilinks — they are not, and that is the bug.

## The numbers

```
689 marker findings
 33 distinct files
 95 max in one file, 2 min, 16 median
 all 33 in the Oracle vault
 577 markers in files that still exist on disk
 30 distinct numbers used across the corpus, max 339
```

Two files carry a third of the problem:
`Chronotopic-Sequence-Representation-Cortex.md` (95) and
`Cognitive-Architecture-Models.md` (85).

## Why the fix splits into two very different jobs

**The reference lists are written in three different formats**, and which
format a file uses determines how hard it is to fix:

| Shape | Files | Fix difficulty |
|-------|------:|-----------------|
| B — plain numbered list (`1. Author...`) | 18 | **Mechanical.** Rewrite `[[n]]` → `[n]` |
| A — reference list itself in wikilinks (`[[n]] Author...`) | 13 | **Mechanical.** Rewrite both halves to `[n]` |
| C — references only in frontmatter `sources:` | 1 | **Mechanical**, but the mapping is positional |
| D — no reference list found in any form | 1 | **Needs judgement** |

**Resolution, measured per file:**

```
231 distinct numbers resolve to a real reference entry
 34 distinct numbers do NOT resolve
```

26 of 33 files have **every** number resolving. Those are safe to fix
mechanically. Seven files have gaps:

| File | Unresolvable of its findings |
|------|-----------------------------:|
| `Neuroplasticity/Dendritic-Spike-Plateau-Potential-Computation.md` | 13 |
| `research/frontier-research-ontology-llm-lifecycle-tools-experiential-2026-09-05.md` | 5 |
| `Social-Cognition/Epistemic-Trust-Testimony.md` | 5 |
| `Cognitive-Architecture/Hierarchical-Temporal-Memory.md` | 3 |
| `Prospective-Memory/Prospective-Memory-Cueing.md` | 3 |
| `Software-Defined-Radio/index.md` | 3 (of 3) |
| `research/band1-claude-context-working-memory.md` | 2 |

Example: the dendritic file cites `[[11]]`…`[[22]]` but its longest reference
list has 10 entries, so 12 numbers point past the end of the list. That is
not a formatting bug — the citation is missing, and only someone reading the
prose can say which source was meant.

## What a fix has to do, honestly

1. **Rewrite the citation syntax.** `[[n]]` → `[n]` in prose, and rewrite the
   reference lines from `[[n]] Author` to `n. Author`. Mechanical, and
   hash-verifiable so no body content changes beyond the bracket characters.
2. **Move the references into frontmatter `sources:`.** They are currently
   loose body text. The schema now has a `sources_shape` (adopted from Google
   OKF §5.1) which is where they belong — and it is what a derived
   `confidence` needs as input.
3. **Resolve the 34 dangling numbers.** Cannot be scripted. Requires reading
   the prose, identifying the intended source, and either finding it or
   recording the citation as unresolvable.
4. **Verify the DOIs.** 18 DOIs live in the worst file's references. The
   project's own `CITATION-AUDIT.md` records that 8 of 8 DOIs in one earlier
   sample were broken and 3 resolved to completely unrelated papers — so a
   DOI that resolves is not proof the citation is right.

## Why this is genuinely a scope question

- **Doing it in the same pass as everything else** means one agent
  sequentially editing 33 files, and the 34 dangling numbers need real
  reading. That is a lot of context for one window, and it is the phase most
  likely to be abandoned half-done.
- **Doing it separately** keeps the mechanical 26 files fast and safe, and
  isolates the 7 hard files as their own piece of work.

Both are defensible. The mechanical work is genuinely mechanical; the
dangling work is genuinely not.

## Also worth knowing

7 of the 33 files are under `.meta/archive/ontology-rounds/` — archived
round files, not active knowledge. They are **evidence** and covered by the
no-deletion rule, but they can still be format-corrected in place.

`Software-Defined-Radio/index.md` has 3 markers and 0 resolvable references:
it is an index, so it points at things rather than citing them. That one may
be legitimately wrong to "fix" at all.

## Numbers to trust

Every figure above came from `okf_lint.py --check --json` plus a per-file
resolution analysis. Two measurement errors were caught and corrected while
producing this, both of which would have produced a wrong scope estimate:

- The first comparison read every reference as "57 bytes", which was `psql`
  display truncation, not a data problem. Switching to md5 computed in the
  database fixed it.
- The first file list pointed at paths that did not resolve; the linter
  reports paths relative to the vault, not absolute.
