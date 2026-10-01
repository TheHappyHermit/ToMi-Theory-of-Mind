# Folder → note-type mapping for the active wiki

**Status:** proposed. Nothing created, moved, or renamed.
**Date:** 2026-09-30
**Schema change required: none.** Every `type:` below already exists in
`schemas/okf-schema.yaml`.

## The rule

The numbered folders are an **organisation** decision. The `type:` field is a
**classification** decision, and it uses only the 29 types the schema already
defines. New folder names do not imply new types.

Verified: 46 fixture notes, one per category below, linted individually by
`scripts/okf_gate.py` — **46 file(s), 0 blocked, exit 0**, across 19 distinct
pre-existing types. Nothing was added to the schema to make this work.

## Mapping

| Folder | Sub-folder | `type:` | `epistemic:` |
|---|---|---|---|
| **00_System** | index | `index` | `fact` |
| | Templates | `reference` | `fact` |
| | Proposals | `idea` | `hypothesis` |
| | Ontology | `technical-spec` | `fact` |
| | Routing-Rules | `technical-spec` | `fact` |
| | Write-Policy | `technical-spec` | `fact` |
| **01_Raw** | Web | `reference` | `observation` |
| | Conversations | `reference` | `observation` |
| | Quick-Captures | `idea` | `hypothesis` |
| | Documents | `reference` | `observation` |
| | Imports | `reference` | `observation` |
| | Attachments | `asset` | `observation` |
| **02_Log** | Daily | `log` | `observation` |
| | Agent-Sessions | `log` | `observation` |
| | Meetings | `log` | `observation` |
| | Experiments | `log` | `observation` |
| | Incidents | `incident` | `observation` |
| **10_Self** | profile | `profile` | `fact` |
| | goals | `project` | `decision` |
| | preferences | `profile` | `explicit-preference` |
| | constraints | `technical-spec` | `fact` |
| | principles | `lesson` | `explicit-preference` |
| **20_Areas** | standards | `technical-spec` | `fact` |
| | health | `routine` | `fact` |
| **30_Projects** | Active / Paused / Completed | `project` | `decision` |
| **40_Entities** | People | `person` | `fact` |
| | Organizations | `entity` | `fact` |
| | Systems | `system` | `fact` |
| | Products | `asset` | `observation` |
| | Models | `model-card` | `fact` |
| | Places | `entity` | `fact` |
| **50_Beliefs** | Claims | `reference` | `verified-inference` |
| | Hypotheses | `idea` | `hypothesis` |
| | Theses | `evergreen` | `verified-inference` |
| | Principles | `lesson` | `explicit-preference` |
| **60_Decisions** | any | `decision` | `decision` |
| **70_Questions** | any | `question` | `hypothesis` |
| **80_Models** | Syntheses | `evergreen` | `verified-inference` |
| | Mental-Models | `evergreen` | `verified-inference` |
| | Maps | `reference` | `verified-inference` |
| | Current-State | `temporal` | `observation` |
| **85_Procedures** | Human-Runbooks | `routine` | `fact` |
| | Policies | `technical-spec` | `fact` |
| | Skill-References | `reference` | `fact` |

**19 of 29 types used.** The 10 unused (`code`, `comparison`, `conference`,
`journal`, `paper`, `preprint`, `presentation`, `purchase`, `research-report`,
`trip`) are research-vault types. They stay in the schema; the active wiki
simply does not need them.

## The belief split is a field, not four types

The four sub-folders under `50_Beliefs/` all reuse pre-existing types, and the
distinction between them is carried by `epistemic:` — which already has exactly
the right values:

```
fact  observation  explicit-preference  verified-inference
hypothesis  prediction  decision
```

- **Claims** = `reference` + `epistemic: verified-inference` — backed, checkable
- **Hypotheses** = `idea` + `epistemic: hypothesis` — explicitly unconfirmed
- **Theses** = `evergreen` + `epistemic: verified-inference` — multi-claim interpretation
- **Principles** = `lesson` + `epistemic: explicit-preference` — normative

This is the resolution of one open question from the review. "Principles" is
not a weaker fact, so it does not belong on a status axis with Claims — it is a
different *kind* of object, and `lesson` says so without inventing a type.
Currently `epistemic:` is used on only 34 of 94 active-wiki notes
(`decision` 17, `verified-inference` 7, `fact` 4, `observation` 4,
`explicit-preference` 2), so there is headroom before it becomes noise.

## Lifecycle is `status:`, never a folder

The schema's `status` enum already covers every state the proposal's
sub-folders imply, and it is the better home for all of them:

| Proposed | Use instead |
|---|---|
| `30_Projects/Active`, `/Paused`, `/Completed` | `status: active` / `blocked` / `completed` |
| `90_Archive/` | `status: archived` (plus the existing gitignored `archive/`) |
| superseded decisions | `status: superseded` + the `supersedes` / `superseded_by` fields |
| contested beliefs | `status: disputed` |
| aged-out notes | `status: stale` + `stale_after` |

Every one of those values already exists. `supersedes`, `superseded_by`,
`review_after` and `stale_after` are already declared optional fields.

This removes 4 sub-folder splits (`Active`/`Paused`/`Completed`, and `Archive`
entirely) — which matters more than usual here, because the current schema has
no per-type `shapes`, so a folder boundary is the *only* thing a linter can
check. A `status` value is machine-checkable; a directory is not.

## Renames that earn their keep

Four of the proposed folders are renames of folders that already hold content:

| Now | Proposed | Notes |
|---|---|---|
| `system/` (13) | `00_System/` | unchanged type usage |
| `decisions/` (33) | `60_Decisions/` | 35% of the vault; rename is clearly worth it |
| `entities/` (13) | `40_Entities/` | needs `People`/`Systems`/… sub-split |
| `concepts/` (28) | `80_Models/` | most notes are `evergreen` — fits |
| `projects/` (2) | `30_Projects/` | |
| `beliefs/` (1) | `50_Beliefs/` | needs the 4-way sub-split |
| `raw/` (1) | `01_Raw/` | already built and drift-tested |
| — | `10_Self/` | new, `personal/` is empty |

## Migration risk

Only **6 live files** hardcode a folder the rename would touch (`system/` ×2,
`concepts/`, `personal/`, `projects/`, `raw/`). But **9 scripts contain both an
`active-wiki/<folder>` path and the string `oracle`** — a global find/replace
would corrupt them. Every edit is per-file and verified.

Both vaults read the single `schemas/okf-schema.yaml`. This mapping adds
nothing to it, so neither vault's existing notes are affected.
